"""等待护宝寻踪 36 集在 PikPak 下载完成，然后取 CDN 直链"""
import json, asyncio, sys, time
from pikpakapi import PikPakApi

async def run():
    token = json.load(open('/opt/data/.pikpak_token.json'))
    client = PikPakApi(encoded_token=token['encoded_token'])
    client.access_token = token['access_token']
    client.refresh_token = token['refresh_token']
    client.user_id = token['user_id']
    client.device_id = token['device_id']

    r = await client.path_to_id('/Inbox-JAV')
    inbox_id = r[0]['id']

    # 列出 Inbox-JAV 中所有护宝寻踪文件
    files = await client.file_list(parent_id=inbox_id)
    hbxz = {}
    for f in files.get('files', []):
        n = f.get('name', '')
        if '护宝寻踪' in n and f.get('kind') == 'drive#file':
            hbxz[n] = f

    print(f'PikPak 中护宝寻踪文件: {len(hbxz)} 个')
    # 检查是否有文件夹（磁链可能是文件夹）
    for f in files.get('files', []):
        if '护宝寻踪' in f.get('name','') and f.get('kind') == 'drive#folder':
            print(f'  文件夹: {f["name"]} (id={f["id"]})')
            # 列出文件夹内容
            inner = await client.file_list(parent_id=f['id'])
            for i2 in inner.get('files', []):
                if i2.get('kind') == 'drive#file':
                    hbxz[i2['name']] = i2
                    print(f'    ├─ {i2["name"]} | {int(i2.get("size",0))/1024**3:.2f}GB')

    # 取 CDN 直链
    urls = {}
    for name, f in sorted(hbxz.items()):
        try:
            info = await client.get_download_url(f['id'])
            url = info.get('web_content_link') or ''
            urls[name] = url
            print(f'  ✅ {name}: URL 已取')
        except Exception as e:
            print(f'  ❌ {name}: {str(e)[:60]}')
        await asyncio.sleep(0.5)

    json.dump(urls, open('/tmp/hbxz_urls.json','w'), ensure_ascii=False, indent=1)
    print(f'\n共取得 {len(urls)} 个直链，保存到 /tmp/hbxz_urls.json')

asyncio.run(run())
