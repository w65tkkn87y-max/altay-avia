#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GLB (несжатый, после gltf-transform simplify) → компактный JS-файл модели для сайта.
   Формат не зависит от GLTFLoader/WebAssembly/fetch: файл подключается обычным <script src>,
   геометрия распаковывается кодом heli3d.js (Viewer.loadPacked), текстура грузится как <img>.
   python3 build/import/glb2js.py in.glb site/models/mi171.js mi171.jpg
   Структура: window.AltayModels[key] = {v, tex, pivots:{MainRotor:[x,y,z],TailRotor:[..]},
     meshes:[{n, g, c, i, it, s, o, d}]}  d = base64: pos int16×3 | pad4 | uv uint16×2 | pad4 | idx | nrm int8×3
"""
import sys, os, json, struct, base64
import numpy as np

SRC, DST, TEX = sys.argv[1:4]
KEY = os.path.splitext(os.path.basename(DST))[0]
data = open(SRC, 'rb').read()
n = struct.unpack_from('<I', data, 12)[0]; js = json.loads(data[20:20 + n])
off = 20 + n; blen, btype = struct.unpack_from('<II', data, off); buf = data[off + 8:off + 8 + blen]
acc, bvs, nodes, meshes = js['accessors'], js['bufferViews'], js['nodes'], js['meshes']
CT = {5120: ('b', 1, 127.0), 5121: ('B', 1, 255.0), 5122: ('h', 2, 32767.0), 5123: ('H', 2, 65535.0), 5125: ('I', 4, 1.0), 5126: ('f', 4, 1.0)}
NC = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4}

def read(i):
    a = acc[i]; v = bvs[a['bufferView']]; o = v.get('byteOffset', 0) + a.get('byteOffset', 0)
    fmt, sz, mx = CT[a['componentType']]; k = NC[a['type']]; stride = v.get('byteStride', sz * k)
    dt = np.dtype('<' + fmt)
    if stride == sz * k: arr = np.frombuffer(buf, dt, a['count'] * k, o).reshape(a['count'], k).astype(np.float64)
    else:
        arr = np.empty((a['count'], k), np.float64)
        for r in range(a['count']): arr[r] = struct.unpack_from('<' + fmt * k, buf, o + r * stride)
    if a.get('normalized'): arr = arr / mx
    return arr

def local_matrix(nd):
    if 'matrix' in nd: return np.array(nd['matrix'], float).reshape(4, 4).T
    t = nd.get('translation', [0, 0, 0]); x, y, z, w = nd.get('rotation', [0, 0, 0, 1]); s = nd.get('scale', [1, 1, 1])
    R = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)], [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)], [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
    M = np.eye(4); M[:3, :3] = R * np.array(s); M[:3, 3] = t; return M

world = [None] * len(nodes); parent = {}
def walk(i, M):
    world[i] = M @ local_matrix(nodes[i])
    for c in nodes[i].get('children', []): parent[c] = i; walk(c, world[i])
for r in js['scenes'][js.get('scene', 0)]['nodes']: walk(r, np.eye(4))

PIVOT_NAMES = ('MainRotor', 'TailRotor')
def rotor_group(i):  # имя группы винта среди предков
    while i in parent:
        i = parent[i]
        if nodes[i].get('name') in PIVOT_NAMES: return nodes[i]['name']
    return None
pivots = {nd['name']: world[i][:3, 3] for i, nd in enumerate(nodes) if nd.get('name') in PIVOT_NAMES}

out = {'v': 1, 'tex': TEX, 'pivots': {k: [round(float(x), 4) for x in v] for k, v in pivots.items()}, 'meshes': []}
tri = 0; verts = 0; raw = 0
for i, nd in enumerate(nodes):
    if 'mesh' not in nd: continue
    W = world[i]; L = W[:3, :3]; Nm = np.linalg.inv(L).T
    g = rotor_group(i); piv = pivots[g] if g else np.zeros(3)
    for p in meshes[nd['mesh']]['primitives']:
        P = read(p['attributes']['POSITION']) @ L.T + W[:3, 3] - piv
        N = read(p['attributes']['NORMAL']) @ Nm.T; N /= np.linalg.norm(N, axis=1, keepdims=True) + 1e-9
        UV = read(p['attributes']['TEXCOORD_0']); UV = UV - np.floor(UV)
        I = read(p['indices'])[:, 0].astype(np.int64)
        pmn, pmx = P.min(0), P.max(0); size = np.maximum(pmx - pmn, 1e-6)
        scale = size / 32766.0; offset = (pmn + pmx) / 2
        q = np.round((P - offset) / scale).astype('<i2')
        nq = np.clip(np.round(N * 127), -127, 127).astype('<i1')
        uq = np.clip(np.round(UV * 65535), 0, 65535).astype('<u2')
        it = 16 if len(P) < 65535 else 32
        idx = I.astype('<u2' if it == 16 else '<u4')
        b = bytearray(q.tobytes())
        while len(b) % 4: b.append(0)
        b += uq.tobytes()
        while len(b) % 4: b.append(0)
        b += idx.tobytes(); b += nq.tobytes()
        out['meshes'].append({'n': nd.get('name', ''), 'g': g, 'c': int(len(P)), 'i': int(len(I)), 'it': it,
                              's': [float('%.6g' % x) for x in scale], 'o': [float('%.5g' % x) for x in offset],
                              'd': base64.b64encode(bytes(b)).decode('ascii')})
        tri += len(I) // 3; verts += len(P); raw += len(b)
txt = 'window.AltayModels=window.AltayModels||{};AltayModels[%s]=%s;\n' % (json.dumps(KEY), json.dumps(out, separators=(',', ':')))
open(DST, 'w', encoding='utf-8').write(txt)
print('%s: мешей %d, вершин %d, треугольников %d, бинарно %.1f МБ, файл %.1f МБ' % (DST, len(out['meshes']), verts, tri, raw / 1e6, len(txt.encode()) / 1e6))
