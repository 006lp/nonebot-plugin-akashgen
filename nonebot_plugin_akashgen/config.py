from typing import List, Optional

from nonebot import get_driver
from pydantic import BaseModel


class Config(BaseModel):
    """Plugin configuration."""
    
    # Akash Network API settings
    akash_api_base_url: str = "https://gen.akash.network"
    akash_request_timeout: int = 60
    akash_max_retries: int = 3
    akash_poll_interval: float = 1.0  # seconds between status checks
    
    # Image generation settings
    akash_negative_prompt: str = ""
    akash_sampler: str = "dpmpp_2m"
    akash_scheduler: str = "sgm_uniform"
    akash_preferred_gpus: List[str] = [
        "RTX4090",
        "A10", 
        "A100",
        "V100-32Gi",
        "H100"
    ]
    
    # Plugin behavior settings
    akash_max_prompt_length: int = 500
    akash_cooldown_seconds: int = 30
    akash_enable_queue_info: bool = True
    
    # Permission settings
    akash_superuser_only: bool = False
    akash_allowed_groups: Optional[List[str]] = None
    akash_blocked_users: Optional[List[str]] = None

