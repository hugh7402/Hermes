"""怪奇物语 S1 SHORTBREHD: 取 8 集 MKV + 16 字幕文件 CDN 直链"""
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
        if 'SHORTBREHD' in n and f.get('kind') == 'drive#folder':
            inner = await client.file_list(parent_id=f['id'])
            for i2 in inner.get('files', []):
                if i2.get('kind') == 'drive#file' and i2['name'].endswith('.mkv'):
                    targets[i2['name']] = i2['id']
                elif i2.get('name') == 'Subs' and i2.get('kind') == 'drive#folder':
                    subs = await client.file_list(parent_id=i2['id'])
                    for s in subs.get('files', []):
                        targets[s['name']] = s['id']

    print(f'共 {len(targets)} 个文件待取直链')
    urls = {}
    for name, fid in sorted(targets.items()):
        try:
            info = await client.get_download_url(fid)
            url = info.get('web_content_link') or ''
            urls[name] = url
            print(f'  ✅ {name}')
        except Exception as e:
            print(f'  ❌ {name}: {str(e)[:50]}')
        await asyncio.sleep(0.4)

    json.dump(urls, open('/tmp/gqwy_urls.json','w'), ensure_ascii=False, indent=1)
    print(f'\n共取得 {len(urls)} 个直链 → /tmp/gqwy_urls.json')

asyncio.run(run())
