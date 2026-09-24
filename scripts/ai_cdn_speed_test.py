#!/usr/bin/env python3
"""测 PikPak CDN 速度 — 恢复提醒
输出: 速度 > 1MB/s 时打印提醒（触发通知），否则静默
"""
import json, os, sys, time, asyncio

sys.path.insert(0, '/opt/data/.venv/lib/python3.13/site-packages')
from pikpakapi import PikPakApi

async def test():
    with open('/opt/data/.pikpak_token.json') as f:
        state = json.load(f)
    api = PikPakApi.from_dict(state)

    # 取 AI短剧 清单里一个 100-300MB 的文件
    data = json.load(open('/opt/data/ai_drama_manifest.json'))
    videos = [f for f in data['files'] if f['ext'] == '.mp4' and 100*1024*1024 < f['size'] < 300*1024*1024]
    if not videos:
        print("无合适测试文件")
        return
    test_f = videos[0]

    # 获取直链
    info = await api.get_download_url(test_f['id'])
    url = info.get('web_content_link', '')
    if not url:
        print("❌ 获取直链失败")
        return

    # 用 curl 下载前 20MB 测速
    import subprocess
    t0 = time.time()
    r = subprocess.run(
        ['curl', '-s', '-o', '/dev/null', '-w', '%{speed_download}', '-r', '0-20971520',
         '--max-time', '30', url],
        capture_output=True, text=True, timeout=40)
    dt = time.time() - t0
    try:
        speed = float(r.stdout) / 1024 / 1024
    except ValueError:
        print(f"❌ 测速失败: {r.stdout[:100]}")
        return

    # 恢复判断: > 1MB/s 才提醒; 低速完全静默 (no_agent cron 空输出=不打扰)
    if speed > 1.0:
        print(f"✅ CDN 已恢复 ({speed:.2f} MB/s)，可以继续下载 AI短剧 了！")
    return

asyncio.run(test())
