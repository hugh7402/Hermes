"""碟中谍8 → PikPak 离线（DreamHD 4K 版 + 1080p 备选）"""
import json, asyncio
from pikpakapi import PikPakApi

MAGNETS = {
    "MI8_4K_30.18G_DreamHD": "magnet:?xt=urn:btih:a1f4bdc5ddeaec9a05657fcac86e99984fbe7a48&dn=%E3%80%90%E9%AB%98%E6%B8%85%E5%BD%B1%E8%A7%86%E4%B9%8B%E5%AE%B6%E5%8F%91%E5%B8%83%20www.WHATMV.com%E3%80%91%E7%A2%9F%E4%B8%AD%E8%B0%8D8%EF%BC%9A%E6%9C%80%E7%BB%88%E6%B8%85%E7%AE%97%5B%E5%9B%BD%E8%8B%B1%E5%A4%9A%E9%9F%B3%E8%BD%A8%2B%E7%AE%80%E7%B9%81%E8%8B%B1%E5%8F%8C%E8%AF%AD%E7%89%B9%E6%95%88%E5%AD%97%E5%B9%95%5D.2025.2160p.iTunes.WEB-DL.DDP.5.1.Atmos.HDR10%2B.H.265-DreamHD&tr=http://tracker1.itzmx.com:8080/announce&tr=udp://tracker.openbittorrent.com:80&tr=udp://tracker.opentrackr.org:1337/announce&tr=udp://open.tracker.cl:1337/announce",
    "MI8_1080p_13.48G_DreamHD": "magnet:?xt=urn:btih:ace3158d3bf5b08b9899896e1697126f82ea6843&dn=%E3%80%90%E9%AB%98%E6%B8%85%E5%BD%B1%E8%A7%86%E4%B9%8B%E5%AE%B6%E5%8F%91%E5%B8%83%20www.WHATMV.com%E3%80%91%E7%A2%9F%E4%B8%AD%E8%B0%8D8%EF%BC%9A%E6%9C%80%E7%BB%88%E6%B8%85%E7%AE%97%5B%E5%9B%BD%E8%8B%B1%E5%A4%9A%E9%9F%B3%E8%BD%A8%2B%E7%AE%80%E7%B9%81%E8%8B%B1%E5%8F%8C%E8%AF%AD%E7%89%B9%E6%95%88%E5%AD%97%E5%B9%95%5D.2025.1080p.iTunes.WEB-DL.DDP.5.1.Atmos.H.264-DreamHD&tr=http://tracker1.itzmx.com:8080/announce&tr=udp://tracker.openbittorrent.com:80&tr=udp://tracker.opentrackr.org:1337/announce",
}

async def run():
    token = json.load(open('/opt/data/.pikpak_token.json'))
    client = PikPakApi(encoded_token=token['encoded_token'])
    client.access_token = token['access_token']
    client.refresh_token = token['refresh_token']
    client.user_id = token['user_id']
    client.device_id = token['device_id']

    r = await client.path_to_id('/Inbox-JAV')
    inbox = r[0]['id']
    print('离线目标目录 Inbox-JAV:', inbox)

    for name, url in MAGNETS.items():
        try:
            await client.offline_download(url, parent_id=inbox)
            print(f'  ✅ {name} 已加入离线')
        except Exception as e:
            print(f'  ❌ {name} 失败: {str(e)[:150]}')
        await asyncio.sleep(3)

asyncio.run(run())
