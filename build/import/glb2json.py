#!/usr/bin/env python3
"""GLB → .json (glTF с бинарным буфером в data-URI). Нужен для хостингов, которые не отдают model/gltf-binary
   (сайт сначала пробует models/<key>.glb, затем models/<key>.json).  python3 glb2json.py in.glb out.json"""
import sys, struct, json, base64
src, dst = sys.argv[1:3]
d = open(src, 'rb').read(); n = struct.unpack_from('<I', d, 12)[0]; js = json.loads(d[20:20 + n])
off = 20 + n; blen, btype = struct.unpack_from('<II', d, off); binary = d[off + 8:off + 8 + blen]
js['buffers'][0]['uri'] = 'data:application/octet-stream;base64,' + base64.b64encode(binary).decode('ascii')
open(dst, 'w', encoding='utf-8').write(json.dumps(js, separators=(',', ':')))
print(dst, round(len(open(dst, 'rb').read()) / 1e6, 1), 'МБ')
