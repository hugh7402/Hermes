"""心灵猎人 S1 磁力熊版: 取 10 集 MKV CDN 直链"""
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
        n = f.get('name','')
        if 'Mindhunter' in n and f.get('kind') == 'drive#folder':
            inner = await client.file_list(parent_id=f['id'])
            for i2 in inner.get('files', []):
                if i2.get('kind') == 'drive#file' and i2['name'].endswith('.mkv'):
                    targets[i2['name']] = i2['id']

    print(f'共 {len(targets)} 集待取直链')
    urls = {}
    for name, fid in sorted(targets.items()):
        try:
            info = await client.get_download_url(fid)
            urls[name] = info.get('web_content_link') or ''
            print(f'  ✅ {name}')
        except Exception as e:
            print(f'  ❌ {name}: {str(e)[:50]}')
        await asyncio.sleep(0.4)

    json.dump(urls, open('/tmp/xllr_mh_urls.json','w'), ensure_ascii=False, indent=1)
    print(f'\n共取得 {len(urls)} 个直链 → /tmp/xllr_mh_urls.json')

asyncio.run(run())
