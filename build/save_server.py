"""Мини-сервер для сохранения PNG-рендеров из браузера: POST /save?name=file.png (тело — data URL)."""
import base64, os, re, sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'site', 'img', '3d')
class H(BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header('Access-Control-Allow-Origin', '*'); self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS'); self.send_header('Access-Control-Allow-Headers', 'Content-Type')
    def do_OPTIONS(self):
        self.send_response(204); self._cors(); self.end_headers()
    def do_POST(self):
        q = parse_qs(urlparse(self.path).query); name = re.sub(r'[^a-z0-9_.-]', '', q.get('name', ['x.png'])[0])
        n = int(self.headers.get('Content-Length', 0)); body = self.rfile.read(n).decode()
        data = base64.b64decode(body.split(',', 1)[1])
        os.makedirs(OUT, exist_ok=True)
        with open(os.path.join(OUT, name), 'wb') as f: f.write(data)
        self.send_response(200); self._cors(); self.end_headers(); self.wfile.write(b'ok')
        sys.stderr.write('saved %s %d bytes\n' % (name, len(data)))
    def log_message(self, *a): pass
HTTPServer(('127.0.0.1', 8766), H).serve_forever()
