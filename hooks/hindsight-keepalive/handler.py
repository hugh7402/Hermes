#!/usr/bin/env python3
"""每轮对话结束（agent:end）后确保 Hindsight 守护进程在跑。

设计要点：
1. 立刻返回——健康检查与拉起都丢到后台线程，绝不拖慢对话回复；
2. 已健康则什么都不做（正常情况 99% 走这条）；
3. 3 分钟内不重复拉起，防止连续对话时堆积多个启动进程；
4. 拉起用 hindsight_start.sh（内含 HOME/实例名/去代理变量等关键参数）。
"""

from __future__ import annotations

import logging
import threading
import time
import urllib.request
from pathlib import Path

logger = logging.getLogger("hooks.hindsight-keepalive")

HEALTH_URL = "http://127.0.0.1:9177/health"
START_SCRIPT = "/opt/data/scripts/hindsight_start.sh"
LOG_PATH = Path("/opt/data/.hindsight/keepalive.log")
SPAWN_COOLDOWN = 180  # 秒

_lock = threading.Lock()
_last_spawn = 0.0


def _log(msg: str) -> None:
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}\n")
    except Exception:
        pass


def _healthy(timeout: float = 2.0) -> bool:
    try:
        with urllib.request.urlopen(HEALTH_URL, timeout=timeout) as resp:
            return resp.status == 200
    except Exception:
        return False


def _spawn_if_needed(event_type: str) -> None:
    global _last_spawn

    if _healthy():
        return

    with _lock:
        now = time.time()
        if now - _last_spawn < SPAWN_COOLDOWN:
            _log(f"{event_type} unhealthy, spawn skipped (cooldown)")
            return
        _last_spawn = now

    import os
    import subprocess

    env = dict(os.environ)
    env["HOME"] = "/opt/data"
    for var in ("https_proxy", "http_proxy", "all_proxy",
                "HTTPS_PROXY", "HTTP_PROXY", "ALL_PROXY"):
        env.pop(var, None)

    try:
        subprocess.Popen(
            ["bash", START_SCRIPT],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            env=env,
            cwd="/opt/data",
        )
        _log(f"{event_type} unhealthy -> launched hindsight_start.sh")
    except Exception as exc:  # pragma: no cover
        _log(f"{event_type} launch failed: {exc!r}")


def handle(event_type: str, context: dict) -> None:
    """网关在每轮对话结束时调用；立刻返回，实际工作放后台线程。"""
    try:
        threading.Thread(
            target=_spawn_if_needed,
            args=(event_type,),
            daemon=True,
            name="hindsight-keepalive",
        ).start()
    except Exception as exc:  # pragma: no cover
        logger.warning("hindsight-keepalive dispatch failed: %s", exc)
