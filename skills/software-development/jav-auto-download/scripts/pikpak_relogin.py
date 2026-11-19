#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PikPak refresh_token 被吊销后的重新登录（幂等，可反复跑）

用法:
    export PATH=/opt/data/.venv/bin:$PATH
    python3 scripts/pikpak_relogin.py

何时需要跑（看到任一种就说明 refresh 这条路已死，重试 refresh 没用）:
    - invalid_grant, error_code 4126, invalidate refresh token token index N not found
    - invalidate refresh token token index 18 not found   （短形态，无 invalid_grant 前缀同样是吊销）
    - pikpakapi.PikpakException: invalid refresh token

为什么能直接重登：账号密码就明文存在 /opt/data/.pikpak_token.json 里，
不需要问用户，也不要去 .env 找。

验收：**不能只看 login() 返回**。真登录成功的判据是随后 path_to_id('/Inbox-JAV')
能拿到 folder id、file_list 能列出文件。本脚本把这一步内置了，拿不到就非零退出。
"""
import asyncio
import json
import pathlib
import sys

TP = pathlib.Path('/opt/data/.pikpak_token.json')
FIELDS = ('access_token', 'refresh_token', 'encoded_token', 'user_id', 'device_id')


async def main() -> int:
    if not TP.exists():
        print(f'  ✗ 找不到 {TP}', file=sys.stderr)
        return 2

    old = json.loads(TP.read_text(encoding='utf-8'))
    user = old.get('username') or old.get('email')
    pwd = old.get('password')
    if not user or not pwd:
        print('  ✗ token 文件里没有 username/password，只能请用户重新登录',
              file=sys.stderr)
        return 2

    print(f'  账号: {user[:6]}****')

    from pikpakapi import PikPakApi
    c = PikPakApi(username=user, password=pwd,
                  device_id=old.get('device_id') or None)
    await c.login()
    print('  ✓ login() 返回成功')

    # 先备份再覆盖：写坏了还能回退
    bak = TP.with_suffix('.json.bak')
    bak.write_text(json.dumps(old, ensure_ascii=False), encoding='utf-8')

    new = dict(old)
    for k in FIELDS:
        v = getattr(c, k, None)
        if v:
            new[k] = v
    new['username'] = user
    new['password'] = pwd
    TP.write_text(json.dumps(new, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'  ✓ token 已写回（旧版备份 {bak.name}）')

    # 真验收：能列目录才算通
    inbox = (await c.path_to_id('/Inbox-JAV'))[0]['id']
    files = (await c.file_list(parent_id=inbox))['files']
    print(f'  ✓ 验收通过: /Inbox-JAV id={inbox}，{len(files)} 项')
    for f in files[:8]:
        gb = int(f.get('size') or 0) / 1024 ** 3
        print(f'      {gb:6.2f}GB  {f["name"][:56]}')
    return 0


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
