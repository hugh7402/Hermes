#!/usr/bin/env python3
"""验证 Hermes 自定义 web provider 插件是否被加载、注册、可用。

用法:
    /opt/hermes/.venv/bin/python verify_provider.py doubao
    /opt/hermes/.venv/bin/python verify_provider.py tavily

输出:
    PLUGIN: web/doubao | enabled=True | error=None
    provider registered: True
    config search_backend = doubao
    name=doubao | available=True | search=True | extract=False
    search success=... / 实际结果条目

诊断:
    - 插件不在列表 → 目录位置错（用户插件应在 $HERMES_HOME/plugins/web/，本机 /opt/data/plugins/web/）
      或 plugins.enabled 被存成字符串（hermes config set 的坑，需 python yaml 改回列表）
    - error= No module named 'plugins.web.xxx' → __init__.py 用了绝对导入，
      必须改相对导入 from .provider import ...
"""
import sys

provider_name = sys.argv[1] if len(sys.argv) > 1 else "doubao"
sys.path.insert(0, "/opt/hermes")

from hermes_cli.plugins import PluginManager  # noqa: E402
from agent.web_search_registry import get_provider, _read_config_key  # noqa: E402

pm = PluginManager()
pm.discover_and_load()

found = False
for key, loaded in pm._plugins.items():
    if provider_name in key:
        found = True
        print(f"PLUGIN: {key} | enabled={loaded.enabled} | error={getattr(loaded, 'error', None)}")
if not found:
    print(f"PLUGIN {provider_name} NOT FOUND in loaded plugins")

print("config search_backend =", _read_config_key("web", "search_backend"))
prov = get_provider(provider_name)
print("provider registered:", prov is not None)
if prov:
    print(f"name={prov.name} | available={prov.is_available()} | "
          f"search={prov.supports_search()} | extract={prov.supports_extract()}")
    r = prov.search("测试查询", limit=3)
    print("search success=", r.get("success"), "| error=", r.get("error"))
    if r.get("success"):
        for item in r["data"]["web"]:
            print(" -", item["position"], "|", item["title"][:40], "|", item["url"][:60])
