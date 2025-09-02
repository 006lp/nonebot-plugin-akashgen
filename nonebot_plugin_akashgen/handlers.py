import asyncio
import time
from typing import Dict, Any

from nonebot import on_command, logger, get_plugin_config
from nonebot.adapters.onebot.v11 import (
    Bot,
    GroupMessageEvent,
    PrivateMessageEvent,
    Message,
    MessageSegment,
)
from nonebot.params import CommandArg
from nonebot.permission import SUPERUSER

from .api import akash_client, AkashAPIError
from .config import Config

plugin_config = get_plugin_config(Config)


# Rate limiting storage
_user_last_request: Dict[str, float] = {}
_user_locks: Dict[str, asyncio.Lock] = {}


def get_user_lock(user_id: str) -> asyncio.Lock:
    """Get or create a lock for a user."""
    if user_id not in _user_locks:
        _user_locks[user_id] = asyncio.Lock()
    return _user_locks[user_id]


async def check_rate_limit(user_id: str) -> bool:
    """Check if user is rate limited."""
    current_time = time.time()
    last_request = _user_last_request.get(user_id, 0)
    
    if current_time - last_request < plugin_config.akash_cooldown_seconds:
        return False
    
    _user_last_request[user_id] = current_time
    return True


async def check_permissions(bot: Bot, event: GroupMessageEvent | PrivateMessageEvent) -> bool:
    """Check if user has permission to use the plugin."""
    user_id = str(event.user_id)

    # Check superuser status first, as they bypass other checks
    if await SUPERUSER(bot, event):
        return True
    
    # Check blocked users
    if (plugin_config.akash_blocked_users and
        user_id in plugin_config.akash_blocked_users):
        return False
    
    # Check superuser only mode
    if plugin_config.akash_superuser_only:
        return await SUPERUSER(bot, event)
    
    # Check allowed groups for group messages
    if (isinstance(event, GroupMessageEvent) and
        plugin_config.akash_allowed_groups):
        group_id = str(event.group_id)
        return group_id in plugin_config.akash_allowed_groups
    
    return True


def parse_draw_args(args: str) -> Dict[str, Any]:
    """解析绘图参数"""
    result = {
        "prompt": "",
        "negative": plugin_config.akash_negative_prompt,
        "sampler": plugin_config.akash_sampler,
        "scheduler": plugin_config.akash_scheduler
    }
    
    parts = args.split()
    i = 0
    prompt_parts = []
    
    while i < len(parts):
        part = parts[i]
        if part == "-n" and i + 1 < len(parts):
            result["negative"] = parts[i + 1]
            i += 2
        elif part == "-s" and i + 1 < len(parts):
            result["sampler"] = parts[i + 1]
            i += 2
        elif part == "-c" and i + 1 < len(parts):
            result["scheduler"] = parts[i + 1]
            i += 2
        else:
            prompt_parts.append(part)
            i += 1
    
    result["prompt"] = " ".join(prompt_parts)
    return result


# Command matcher
draw = on_command(
    "draw",
    aliases={"画图", "生成图片", "ai画图"},
    priority=65,
    block=True
)


@draw.handle()
async def handle_draw_command(
    bot: Bot,
    event: GroupMessageEvent | PrivateMessageEvent,
    args=CommandArg()
):
    """Handle the /draw command."""
    user_id = str(event.user_id)
    raw_args = args.extract_plain_text().strip()
    
    # Check permissions
    if not await check_permissions(bot, event):
        await draw.finish("❌ 你没有权限使用此功能")
    
    # Validate prompt
    if not raw_args:
        await draw.finish(
            "🎨 请提供图像描述！\n"
            "用法: /draw <描述>\n"
            "支持参数：\n"
            "-n 负面提示词\n"
            "-s 采样器\n"
            "-c 调度器\n"
            "示例: /draw -n blurry a beautiful sunset"
        )
    
    parsed_args = parse_draw_args(raw_args)
    prompt = parsed_args["prompt"]
    
    if not prompt:
        await draw.finish("🎨 请提供图像描述！")

    if len(prompt) > plugin_config.akash_max_prompt_length:
        await draw.finish(
            f"❌ 描述过长！最大长度为 {plugin_config.akash_max_prompt_length} 字符"
        )
    
    # Check rate limit
    if not await check_rate_limit(user_id):
        remaining_time = (
            plugin_config.akash_cooldown_seconds -
            (time.time() - _user_last_request.get(user_id, 0))
        )
        await draw.finish(
            f"⏰ 请稍等 {int(remaining_time)} 秒后再次使用"
        )
    
    # Use lock to prevent concurrent requests from same user
    async with get_user_lock(user_id):
        await process_image_generation(bot, event, parsed_args)


async def process_image_generation(
    bot: Bot,
    event: GroupMessageEvent | PrivateMessageEvent,
    gen_params: Dict[str, Any]
):
    """Process the image generation request."""
    prompt = gen_params["prompt"]
    try:
        # Send initial message
        await bot.send(
            event,
            f"🎨 开始生成图片...\n📝 描述: {prompt[:50]}{'...' if len(prompt) > 50 else ''}"
        )
        
        # Generate image
        logger.info(f"User {event.user_id} requested image: {prompt}")
        
        image_data, status_response = await akash_client.generate_image(
            prompt=prompt,
            negative=gen_params["negative"],
            sampler=gen_params["sampler"],
            scheduler=gen_params["scheduler"],
        )
        
        # Prepare result message
        info_text = ""
        if plugin_config.akash_enable_queue_info:
            info_text = (
                f"🖥️ GPU: {status_response.worker_gpu}\n"
                f"🌍 位置: {status_response.worker_city}, {status_response.worker_country}\n"
                f"⏱️ 耗时: {status_response.elapsed_time:.2f}s\n"
                f"🏗️ 服务商: {status_response.worker_name}"
            )
        
        # Send the generated image
        message_segments = []
        if info_text:
            message_segments.append(MessageSegment.text(f"✅ 图片生成完成！\n{info_text}"))
        
        message_segments.append(MessageSegment.image(image_data))
        
        # Combine message segments into a single message
        message_to_send = Message(message_segments)
        await bot.send(event, message_to_send)
        
        logger.info(
            f"Image generated successfully for user {event.user_id}, "
            f"job_id: {status_response.job_id}"
        )
        
    except AkashAPIError as e:
        logger.error(f"Akash API error for user {event.user_id}: {e}")
        await bot.send(event, f"❌ 生成失败: {str(e)}")
        
    except Exception as e:
        logger.error(f"Unexpected error for user {event.user_id}: {e}")
        await bot.send(event, "❌ 生成失败，请稍后重试")


# Help command
help_cmd = on_command("draw_help", aliases={"draw帮助", "画图帮助"}, priority=10, block=True)


@help_cmd.handle()
async def handle_help():
    """Show help information."""
    help_text = (
        "🎨 AI图像生成帮助\n\n"
        "📋 命令:\n"
        "• /draw <描述> - 生成AI图像\n"
        "• /画图 <描述> - 生成AI图像\n"
        "• /draw_help - 显示此帮助\n\n"
        "💡 示例:\n"
        "• /draw a cute cat sitting on a table\n"
        "• /画图 一只可爱的猫坐在桌子上\n"
        "• /draw cyberpunk cityscape at night, neon lights\n\n"
        f"⚙️ 设置:\n"
        f"• 冷却时间: {plugin_config.akash_cooldown_seconds}秒\n"
        f"• 最大描述长度: {plugin_config.akash_max_prompt_length}字符\n\n"
        "🌐 由 Akash Network 强力驱动"
    )
    
    await help_cmd.finish(help_text)


# Status command (for admins)
status_cmd = on_command("draw_status", permission=SUPERUSER, priority=5, block=True)


@status_cmd.handle()
async def handle_status():
    """Show plugin status information."""
    active_users = len(_user_last_request)
    locked_users = len(_user_locks)
    
    status_text = (
        "📊 插件状态\n\n"
        f"👥 活跃用户: {active_users}\n"
        f"🔒 锁定用户: {locked_users}\n"
        f"🌐 API地址: {plugin_config.akash_api_base_url}\n"
        f"⏱️ 轮询间隔: {plugin_config.akash_poll_interval}s\n"
        f"🔄 最大重试: {plugin_config.akash_max_retries}\n"
        f"❄️ 冷却时间: {plugin_config.akash_cooldown_seconds}s"
    )
    
    await status_cmd.finish(status_text)