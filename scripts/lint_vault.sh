#!/bin/bash
# 知识库健康巡检
# 说明：原先用 `uv run --with pyyaml`，但 uv 不在 cron 的 PATH 里（装在 /opt/hermes/tools/），
#      导致 2026-11-01 月度巡检失败（exit 127）。/opt/data/.venv 已带 pyyaml 6.0.3，直接用。
cd /opt/data || exit 1
exec /opt/data/.venv/bin/python3 /opt/data/lint_vault.py
