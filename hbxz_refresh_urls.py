"""重新取护宝寻踪 36 集 CDN 直链（PikPak 中文件已就绪）"""
import json, asyncio
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
    files = await client.file_list(parent_id=inbox_id)

    targets = {}
    for f in files.get('files', []):
        n = f.get('name', '')
        if '护宝寻踪' in n and f.get('kind') == 'drive#file':
            targets[n] = f['id']

    print(f'PikPak 中护宝寻踪文件: {len(targets)} 个')
    urls = {}
    for name, fid in sorted(targets.items()):
        try:
            info = await client.get_download_url(fid)
            urls[name] = info.get('web_content_link') or ''
            print(f'  ✅ {name}')
        except Exception as e:
            print(f'  ❌ {name}: {str(e)[:50]}')
        await asyncio.sleep(0.3)

    json.dump(urls, open('/tmp/hbxz_urls.json','w'), ensure_ascii=False, indent=1)
    print(f'\n共取得 {len(urls)} 个直链')

asyncio.run(run())
