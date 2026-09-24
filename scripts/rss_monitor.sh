#!/bin/bash
cd /opt/data
uv run --with feedparser --with requests python3 /opt/data/rss_monitor.py
