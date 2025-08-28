# NoneBot Plugin AkashGen

[![License](https://img.shields.io/github/license/006lp/nonebot-plugin-akashgen)](https://github.com/006lp/nonebot-plugin-akashgen/blob/main/LICENSE)
[![PyPI](https://img.shields.io/pypi/v/nonebot-plugin-akashgen)](https://pypi.org/project/nonebot-plugin-akashgen/)

一个使用 [Akash Network](https://gen.akash.network/) 为 NoneBot2 提供 AI 图像生成功能的插件。

## 功能

- 通过简单的命令调用 AI 进行画图。
- 支持自定义参数，如负面提示词、采样器和调度器。
- 内置速率限制和权限控制。
- 显示生成任务的详细信息（GPU、地理位置、耗时等）。

## 安装

通过 `pip` 或 `nb-cli` 安装：

```bash
pip install nonebot-plugin-akashgen
```

```bash
nb plugin install nonebot-plugin-akashgen
```

## 配置

在你的 NoneBot 项目的 `.env` 或 `.env.*` 文件中添加以下配置项：

```dotenv
# Akash Network API Base URL (默认为官方地址)
# AKASH_API_BASE_URL="https://gen.akash.network"

# 请求超时时间 (秒)
# AKASH_REQUEST_TIMEOUT=60

# 最大重试次数
# AKASH_MAX_RETRIES=3

# 任务状态轮询间隔 (秒)
# AKASH_POLL_INTERVAL=1.0

# 默认负面提示词
# AKASH_NEGATIVE_PROMPT=""

# 默认采样器
# AKASH_SAMPLER="dpmpp_2m"

# 默认调度器
# AKASH_SCHEDULER="sgm_uniform"

# 最大提示词长度
# AKASH_MAX_PROMPT_LENGTH=500

# 命令冷却时间 (秒)
# AKASH_COOLDOWN_SECONDS=30

# 是否显示队列信息
# AKASH_ENABLE_QUEUE_INFO=True

# 是否仅限超级用户使用
# AKASH_SUPERUSER_ONLY=False

# 允许使用的群组列表 (留空则不限制)
# AKASH_ALLOWED_GROUPS=[]

# 禁用用户列表
# AKASH_BLOCKED_USERS=[]
```

## 使用

- `/draw <描述>`: 生成一张图片。
- `/画图 <描述>`: `/draw` 的别名。

**高级用法:**

你可以在命令中使用参数来微调生成过程：

- `-n <负面提示词>`: 指定不希望在图片中出现的内容。
- `-s <采样器>`: 指定使用的采样器。
- `-c <调度器>`: 指定使用的调度器。

**示例:**

- `/draw a beautiful sunset over the mountains`
- `/画图 一只可爱的猫`
- `/draw -n blurry,ugly -s dpmpp_sde a robot holding a flower`

**管理命令:**

- `/draw_help`: 显示帮助信息。
- `/draw_status`: (仅限超级用户) 显示插件的运行状态。
