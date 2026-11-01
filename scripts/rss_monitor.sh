#!/bin/bash
# RSS 政策监控
# 说明：同 lint_vault.sh，uv 不在 cron PATH 里；/opt/data/.venv 已带 feedparser + requests。
cd /opt/data || exit 1
exec /opt/data/.venv/bin/python3 /opt/data/rss_monitor.py
