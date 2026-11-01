#!/usr/bin/env python3
"""静态服务 + 单页回退（SPA fallback）—— 让 /xzzwsjml 这类路由能直接访问、也能刷新。

为什么需要它：`python3 -m http.server` 遇到没这个文件的路径会直接 404，
浏览器里就是"页面打不开"，路由等于白做。本脚本把未命中的路径一律回退到 index.html，
由前端路由按 location.pathname 落屏。

用法：python3 serve.py [端口，默认 8080]
只监听 127.0.0.1 —— 保密类原型不出本机，不要 --bind 0.0.0.0。
"""
import http.server
import os
import socketserver
import sys
import urllib.parse

ROOT = os.path.dirname(os.path.abspath(__file__))
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8080


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)

    def do_GET(self):
        path = urllib.parse.unquote(urllib.parse.urlparse(self.path).path)
        fp = os.path.join(ROOT, path.lstrip('/'))
        # 首页或「不是真实文件」的路径 -> 统一交给 index.html（前端路由再落屏）
        if path in ('', '/') or not os.path.isfile(fp):
            self.path = '/index.html'
        return super().do_GET()

    def end_headers(self):
        # 换版后别让浏览器拿旧页面（现场演示最忌讳"改了却看不到"）
        self.send_header('Cache-Control', 'no-store')
        super().end_headers()

    def log_message(self, fmt, *args):
        sys.stderr.write('  %s\n' % (fmt % args))


def main():
    socketserver.TCPServer.allow_reuse_address = True
    srv = socketserver.ThreadingTCPServer(('127.0.0.1', PORT), Handler)
    print('服务已启动：http://localhost:%d/   （按 Ctrl+C 结束）' % PORT)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print('\n已停止。')
    finally:
        srv.server_close()


if __name__ == '__main__':
    main()
