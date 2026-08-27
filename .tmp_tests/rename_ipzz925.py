"""PikPak Inbox-JAV 中查找并重命名 IPZZ-925"""
import asyncio, json, sys

sys.path.insert(0, '/opt/data/.venv/lib/python3.13/site-packages')

NEW_NAME = "IPZZ-925-瀬緒凛-多P轮奸中出 被社长强奸调教并被轮奸中出的极品尤物前台小姐.mp4"

async def main():
    from pikpakapi import PikPakApi
    state = json.load(open('/opt/data/.pikpak_token.json'))
    client = PikPakApi(encoded_token=state['encoded_token'])
    client.access_token = state.get('access_token', '')
    client.refresh_token = state.get('refresh_token', '')
    client.user_id = state.get('user_id', '')
    client.device_id = state.get('device_id', '')

    result = await client.path_to_id('/Inbox-JAV')
    inbox_id = result[0]['id']
    files = await client.file_list(parent_id=inbox_id)
    for f in files.get('files', []):
        if 'IPZZ' in f['name'].upper() or 'ipzz' in f['name'].lower():
            print(f"找到: {f['id']} | {f['name']}")
            r = await client.file_rename(f['id'], NEW_NAME)
            print(f"重命名结果: {r.get('name')}")

asyncio.run(main())
