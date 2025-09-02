from nonebot.plugin import PluginMetadata

from .config import Config
from .handlers import *  # noqa: F403,F401

__version__ = "0.1.1"
__plugin_meta__ = PluginMetadata(
    name="Akash Image Generator",
    description="AI image generation using Akash Network",
    usage=(
        "使用方法:\n"
        "/draw <prompt> - 生成AI图像\n"
        "示例: /draw a beautiful sunset over mountains"
    ),
    type="application",
    homepage="https://github.com/006lp/nonebot-plugin-akashgen",
    config=Config,
    supported_adapters={"~onebot.v11"},
    extra={
        "author": "006lp",
        "version": __version__,
    },
)