#!/usr/bin/env python3
"""Постоянная входная точка для показа сайта: любой запрос → редирект на текущий адрес туннеля
   из build/tunnel_url.txt (pinggy меняет адрес раз в час, а этот сервер публикуется через bore.pub
   на фиксированном порту, поэтому ссылка для друзей не меняется).  python3 build/redirect_server.py [3001]"""
import os, sys
from http.server import BaseHTTPRequestHandler, HTTPServer
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL_FILE = os.path.join(ROOT, 'build', 'tunnel_url.txt')
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 3001
class H(BaseHTTPRequestHandler):
    def do_GET(self):
        try: url = open(URL_FILE, encoding='utf-8').read().strip()
        except OSError: url = ''
        if not url:
            self.send_response(503); self.send_header('Content-Type', 'text/html; charset=utf-8'); self.send_header('Retry-After', '10'); self.end_headers()
            self.wfile.write('<meta charset="utf-8"><meta http-equiv="refresh" content="10"><p style="font:18px sans-serif;padding:40px">Сайт поднимается, подождите 10 секунд…</p>'.encode()); return
        target = url.rstrip('/') + self.path
        self.send_response(302); self.send_header('Location', target); self.send_header('Cache-Control', 'no-store'); self.send_header('Content-Type', 'text/html; charset=utf-8'); self.end_headers()
        self.wfile.write(('<meta charset="utf-8"><meta http-equiv="refresh" content="0;url=%s"><a href="%s">Открыть сайт</a>' % (target, target)).encode())
    do_HEAD = do_GET
    def log_message(self, *a): pass
HTTPServer(('127.0.0.1', PORT), H).serve_forever()
