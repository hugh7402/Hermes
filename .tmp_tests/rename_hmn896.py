"""重命名 PikPak 中的 HMN-896.mp4 为用户指定名称"""
import asyncio, json, sys

sys.path.insert(0, '/opt/data/.venv/lib/python3.13/site-packages')

NEW_NAME = "HMN-896-愛花未滿-多P轮奸中出 被高薪职位诱骗被下药后被轮奸中出的极品尤物.mp4"
FILE_ID = "VP019V1Tuvo7wnlQt31tIyg8o2"

async def main():
    from pikpakapi import PikPakApi
    state = json.load(open('/opt/data/.pikpak_token.json'))
    client = PikPakApi(encoded_token=state['encoded_token'])
    client.access_token = state.get('access_token', '')
    client.refresh_token = state.get('refresh_token', '')
    client.user_id = state.get('user_id', '')
    client.device_id = state.get('device_id', '')

    r = await client.file_rename(FILE_ID, NEW_NAME)
    print(json.dumps(r, ensure_ascii=False)[:300])

asyncio.run(main())
