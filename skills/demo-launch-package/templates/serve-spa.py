#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""静态文件服务 + 单页应用回退。把本文件与 index.html 一起交付。

任何未命中文件的路径都返回 index.html —— 这样地址栏里的每屏路由
（如 http://localhost:8080/sjqxjgmx）都能直接打开与刷新。
只监听 127.0.0.1，不对外暴露。
用法：python3 serve.py [端口，默认 8080]
"""
import http.server
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8080


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)

    def _fallback(self):
        p = self.path.split('?')[0].split('#')[0]
        fp = os.path.join(ROOT, p.lstrip('/'))
        if p == '/' or os.path.isdir(fp) or not os.path.isfile(fp):
            self.path = '/index.html'

    def do_GET(self):
        self._fallback()
        return super().do_GET()

    def do_HEAD(self):
        self._fallback()
        return super().do_HEAD()

    def log_message(self, *a):
        pass


if __name__ == '__main__':
    print('服务已启动：http://localhost:%d/' % PORT)
    http.server.ThreadingHTTPServer(('127.0.0.1', PORT), Handler).serve_forever()
