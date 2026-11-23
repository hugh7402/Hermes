"""阿里百炼 DashScope (国内版) provider profile."""

from providers import register_provider
from providers.base import ProviderProfile

bailian = ProviderProfile(
    name="bailian",
    aliases=("bailian", "aliyun-bailian", "dashscope-cn"),
    env_vars=("BAILIAN_API_KEY",),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

register_provider(bailian)
