#!/usr/bin/env python3
"""WeChat QR login helper - generates QR code for scanning."""
import asyncio
import os
import sys

# Ensure Hermes packages are importable
sys.path.insert(0, "/opt/hermes/.venv/lib/python3.13/site-packages")
sys.path.insert(0, "/opt/hermes")

# Set HERMES_HOME for the weixin module
hermes_home = os.environ.get("HERMES_HOME", "/opt/data")
os.environ["HERMES_HOME"] = hermes_home

from gateway.platforms.weixin import qr_login, save_weixin_account

async def main():
    print("正在获取微信二维码...")
    result = await qr_login(hermes_home)
    if result is None:
        print("登录失败或超时")
        return
    
    token = result.get("token", "")
    account_id = result.get("account_id", "")
    base_url = result.get("base_url", "https://ilinkai.weixin.qq.com")
    
    if not token or not account_id:
        print(f"登录结果缺少必要字段: {result}")
        return
    
    print(f"\n✅ 登录成功!")
    print(f"   Account ID: {account_id}")
    print(f"   Token: {token[:20]}...")
    
    # Save to account file
    save_weixin_account(
        hermes_home,
        account_id=account_id,
        token=token,
        base_url=base_url,
    )
    print(f"\n已保存到: {hermes_home}/weixin/accounts/{account_id}.json")
    print(f"\n请将此 token 更新到 .env 文件中的 WEIXIN_TOKEN 变量，然后重启 gateway。")
    print(f"新 WEIXIN_ACCOUNT_ID={account_id}")
    print(f"新 WEIXIN_TOKEN={token}")

if __name__ == "__main__":
    asyncio.run(main())
