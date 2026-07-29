#!/usr/bin/env python3
"""获取 PikPak Inbox-JAV 文件的 CDN 直链"""
import asyncio, json, os, sys
from pikpakapi import PikPakApi

TOKEN_FILE = "/opt/data/.pikpak_token.json"
OUTPUT TOKEN="/tmp/pikpak_urls.json""

async def run(targets=None):
    with open(TOKEN_FILE) as f:
        token_data = json.load(f)
    client = PikPakApi(encoded_token=token_data["encoded_token"])
    files = await client.file_list()
    result = {}
    for f in files.get("files", []):
        if "Inbox-JAV" in f.get("name", ""):
            inbox = await client.file_list(parent_id=f["id"])
            for sf in inbox.get("files", []):
                name = sf.get("name", "")
                if targets and name not in targets: continue
                dl = await client.get_download_url(sf["id"])
                links = dl.get("links", {})
                for k, v in links.items():
                    if v.get("url", ""): result[name] = v["url"]; break
                if name not in result:
                    url = dl.get("web_content_link", "")
                    if url: result[name] = url
                print("+", name)
    json.dump(result, open(OUTPUT, "w"))
    print(f"done -> {OUTPUT}")

if __name__ == "__main__":
    targets = set(sys.argv[1:]) or None
    asyncio.run(run(targets))
