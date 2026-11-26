#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PikPak 客户端 —— 自动处理 token 失效。

为什么要这个模块：
  PikPak 的 access/refresh token 大约 1 小时就失效，报 "invalid refresh token"。
  一晚上踩了三次，每次都要手工重新登录，导致后台任务在跑到一半时崩掉。
  这里统一封装：拿 client 时先验活，失效就用 token 文件里的账号密码重登，
  并把新 token 写回 /opt/data/.pikpak_token.json。所有脚本都该用这里的 client()。

用法:
    from pk_login import client
    c = await client()
"""
import asyncio
import json
import pathlib

from pikpakapi import PikPakApi

TOKEN_PATH = pathlib.Path('/opt/data/.pikpak_token.json')


def _make(st):
    c = PikPakApi(encoded_token=st.get('encoded_token', ''))
    c.access_token = st.get('access_token', '')
    c.refresh_token = st.get('refresh_token', '')
    c.user_id = st.get('user_id', '')
    c.device_id = st.get('device_id', '')
    return c


async def relogin():
    """用 token 文件里的账号密码重新登录，并写回新 token。"""
    st = json.loads(TOKEN_PATH.read_text(encoding='utf-8'))
    c = PikPakApi(username=st['username'], password=st['password'])
    await c.login()
    st['access_token'] = c.access_token
    st['refresh_token'] = c.refresh_token
    st['user_id'] = c.user_id
    st['encoded_token'] = c.encoded_token
    st['device_id'] = c.device_id
    TOKEN_PATH.write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding='utf-8')
    return _make(st)


async def client(verify=True):
    """返回可用的 PikPak 客户端。默认先验活（列根目录），失效自动重登一次。"""
    st = json.loads(TOKEN_PATH.read_text(encoding='utf-8'))
    c = _make(st)
    if not verify:
        return c
    try:
        await c.file_list(parent_id='*')
        return c
    except Exception as e:
        if 'refresh token' not in str(e).lower() and 'invalid' not in str(e).lower():
            return c          # 其它错误（网络等）先原样返回，让调用方自己处理
        print('  🔑 token 失效，自动重新登录…', flush=True)
        return await relogin()


async def _smoke():
    c = await client()
    inbox = (await c.path_to_id('/Inbox-JAV'))[0]['id']
    fs = (await c.file_list(parent_id=inbox))['files']
    print(f'  ✅ 客户端可用，Inbox-JAV 共 {len(fs)} 项')


if __name__ == '__main__':
    asyncio.run(_smoke())
