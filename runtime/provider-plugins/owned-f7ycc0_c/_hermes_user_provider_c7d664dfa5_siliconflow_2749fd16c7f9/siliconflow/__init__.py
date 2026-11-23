"""硅基流动 SiliconFlow provider profile (DeepSeek 等模型)."""

from providers import register_provider
from providers.base import ProviderProfile

siliconflow = ProviderProfile(
    name="siliconflow",
    aliases=("siliconflow", "sf", "silicon-flow", "硅基流动"),
    env_vars=("SILICONFLOW_API_KEY",),
    base_url="https://api.siliconflow.cn/v1",
)

register_provider(siliconflow)
