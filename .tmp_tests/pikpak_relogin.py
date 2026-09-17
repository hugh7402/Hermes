"""重新登录 PikPak 刷新 token（旧 refresh_token 失效）"""
import json, asyncio
from pikpakapi import PikPakApi

async def run():
    old = json.load(open('/opt/data/.pikpak_token.json'))
    print('账号:', old['username'][:6] + '****')

    client = PikPakApi(
        username=old['username'],
        password=old['password'],
        device_id=old['device_id'],
    )
    await client.login()
    print('✅ 登录成功')
    print('  user_id:', client.user_id)
    print('  access_token:', (client.access_token or '')[:20] + '...')
    print('  refresh_token:', (client.refresh_token or '')[:20] + '...')

    new = {
        'username': old['username'],
        'password': old['password'],
        'user_id': client.user_id,
        'access_token': client.access_token,
        'refresh_token': client.refresh_token,
        'encoded_token': getattr(client, 'encoded_token', '') or old.get('encoded_token', ''),
        'device_id': client.device_id or old['device_id'],
    }
    json.dump(new, open('/opt/data/.pikpak_token.json', 'w'), ensure_ascii=False, indent=1)
    print('✅ 新 token 已保存')

    # 验证：列根目录
    files = await client.file_list(parent_id='')
    names = [f.get('name') for f in files.get('files', [])]
    print('根目录:', names[:10])

asyncio.run(run())
