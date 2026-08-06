"""取心灵猎人 10 集 CDN 直链"""
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

    xllr = {}
    for f in files.get('files', []):
        n = f.get('name', '')
        if '心灵猎人' in n and f.get('kind') == 'drive#file':
            xllr[n] = f

    print(f'PikPak 中心灵猎人文件: {len(xllr)} 个')
    urls = {}
    for name, f in sorted(xllr.items()):
        try:
            info = await client.get_download_url(f['id'])
            url = info.get('web_content_link') or ''
            urls[name] = url
            print(f'  ✅ {name}: URL 已取')
        except Exception as e:
            print(f'  ❌ {name}: {str(e)[:60]}')
        await asyncio.sleep(0.5)

    json.dump(urls, open('/tmp/xllr_urls.json','w'), ensure_ascii=False, indent=1)
    print(f'\n共取得 {len(urls)} 个直链')

asyncio.run(run())
