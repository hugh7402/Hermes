#!/bin/bash
# 知识库健康巡检 — 通过 uv 运行确保 pyyaml 可用
cd /opt/data
uv run --with pyyaml python3 /opt/data/lint_vault.py
