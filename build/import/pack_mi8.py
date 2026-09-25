#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Сборка Ми-8АМТ «АлтайАвиа» из модели Mil Mi-8AMTSh (Sketchfab, 42manako, CC BY 4.0):
   удаление вооружения и военного оборудования (список — в mi8_geom.py), единая текстура ливреи,
   приведение к метрам/осям сайта (нос +X, верх +Y, земля y=0), квантование (KHR_mesh_quantization),
   узлы винтов MainRotor / TailRotor для анимации.
   python3 build/import/pack_mi8.py build/import/mi8amtsh/scene.gltf build/import/mi8amt_texture.png site/models/mi8amt.glb
"""
import json, struct, sys, os, math
import numpy as np

SRC, TEX, DST = sys.argv[1:4]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mi8_geom
G = mi8_geom.load(SRC)
prims, main_c, tail_c = G['prims'], G['main_c'], G['tail_c']
mi8_geom.apply_gear_palette(prims)          # стойки / шины / диски — плашки палитры (краска в livery_mi8.py)
MAIN_ROTOR, TAIL_ROTOR = mi8_geom.MAIN_ROTOR, mi8_geom.TAIL_ROTOR
allP = np.vstack([p[1] for p in prims]); mn, mx = allP.min(0), allP.max(0)
print('габариты, м: %.2f × %.2f × %.2f' % tuple(mx - mn), 'треугольников:', sum(len(p[4]) // 3 for p in prims))
print('MainRotor центр', main_c.round(2), 'TailRotor центр', tail_c.round(2))

# --- сборка glTF: квантование, один материал с запечённой текстурой ---
out = {'asset': {'version': '2.0', 'generator': 'AltayAvia pack_mi8.py', 'extras': {
        'source': 'Mil Mi-8AMTSh by 42manako — https://sketchfab.com/3d-models/mil-mi-8amtsh-cde7d5bf30eb470688f268935561996f',
        'license': 'CC-BY-4.0', 'note': 'Вооружение удалено, ливрея «АлтайАвиа» запечена в текстуру'}},
       'extensionsUsed': ['KHR_mesh_quantization'], 'extensionsRequired': ['KHR_mesh_quantization'],
       'buffers': [], 'bufferViews': [], 'accessors': [], 'meshes': [], 'nodes': [], 'scenes': [{'nodes': []}], 'scene': 0,
       'images': [], 'textures': [], 'samplers': [{'magFilter': 9729, 'minFilter': 9987, 'wrapS': 10497, 'wrapT': 10497}],
       'materials': [{'name': 'AltayAvia_livery', 'doubleSided': True, 'pbrMetallicRoughness': {'baseColorTexture': {'index': 0}, 'metallicFactor': 0.05, 'roughnessFactor': 0.42}}]}
binp = bytearray()
def add_view(data, target=None, stride=None):
    while len(binp) % 4: binp.append(0)
    v = {'buffer': 0, 'byteOffset': len(binp), 'byteLength': len(data)}
    if target: v['target'] = target
    if stride: v['byteStride'] = stride
    binp.extend(data); out['bufferViews'].append(v); return len(out['bufferViews']) - 1
def add_acc(view, ctype, count, atype, mn=None, mx=None, normalized=False):
    a = {'bufferView': view, 'componentType': ctype, 'count': count, 'type': atype}
    if normalized: a['normalized'] = True
    if mn is not None: a['min'] = [float(x) for x in mn]; a['max'] = [float(x) for x in mx]
    out['accessors'].append(a); return len(out['accessors']) - 1

pivots = {'MainRotor': main_c, 'TailRotor': tail_c}
node_by_group = {}
def add_prim(name, P, N, UV, I, pivot):
    P = P - pivot
    pmn, pmx = P.min(0), P.max(0); size = np.maximum(pmx - pmn, 1e-6)
    scale = size / 32766.0; offset = (pmn + pmx) / 2
    q = np.round((P - offset) / scale).astype(np.int16)         # позиции → int16, масштаб/смещение в узле
    q = np.hstack([q, np.zeros((len(q), 1), np.int16)])           # выравнивание элемента до 8 байт (требование glTF)
    nq = np.clip(np.round(N * 127), -127, 127).astype(np.int8)  # нормали → int8 normalized
    nq = np.hstack([nq, np.zeros((len(nq), 1), np.int8)])         # выравнивание до 4 байт
    uq = np.clip(np.round(UV * 65535), 0, 65535).astype(np.uint16)
    ityp = 5123 if len(P) < 65535 else 5125
    idx = I.astype(np.uint16 if ityp == 5123 else np.uint32)
    vp = add_view(q.astype('<i2').tobytes(), 34962, 8)
    va = add_acc(vp, 5122, len(q), 'VEC3', q[:, :3].min(0), q[:, :3].max(0))
    vn = add_view(nq.astype('<i1').tobytes(), 34962, 4); na = add_acc(vn, 5120, len(nq), 'VEC3', normalized=True)
    vu = add_view(uq.astype('<u2').tobytes(), 34962); ua = add_acc(vu, 5123, len(uq), 'VEC2', normalized=True)
    vi = add_view(idx.tobytes(), 34963); ia = add_acc(vi, ityp, len(idx), 'SCALAR')
    out['meshes'].append({'name': name, 'primitives': [{'attributes': {'POSITION': va, 'NORMAL': na, 'TEXCOORD_0': ua}, 'indices': ia, 'material': 0}]})
    out['nodes'].append({'name': name, 'mesh': len(out['meshes']) - 1, 'translation': [float(x) for x in offset], 'scale': [float(x) for x in scale]})
    return len(out['nodes']) - 1

root_children = []
rot_nodes = {k: [] for k in pivots}
for g, P, N, UV, I in prims:
    if g in MAIN_ROTOR: rot_nodes['MainRotor'].append(add_prim(g, P, N, UV, I, pivots['MainRotor']))
    elif g in TAIL_ROTOR: rot_nodes['TailRotor'].append(add_prim(g, P, N, UV, I, pivots['TailRotor']))
    else: root_children.append(add_prim(g, P, N, UV, I, np.zeros(3)))
for k, piv in pivots.items():
    out['nodes'].append({'name': k, 'translation': [float(x) for x in piv], 'children': rot_nodes[k]}); root_children.append(len(out['nodes']) - 1)
out['nodes'].append({'name': 'Mi8AMT_AltayAvia', 'children': root_children}); out['scenes'][0]['nodes'] = [len(out['nodes']) - 1]
# текстура
img = open(TEX, 'rb').read(); iv = add_view(img)
out['images'].append({'bufferView': iv, 'mimeType': 'image/jpeg' if TEX.lower().endswith(('.jpg', '.jpeg')) else 'image/png', 'name': 'altayavia_livery'}); out['textures'].append({'sampler': 0, 'source': 0})
out['buffers'].append({'byteLength': len(binp)})
jb = json.dumps(out, separators=(',', ':'), ensure_ascii=False).encode('utf-8'); jb += b' ' * ((4 - len(jb) % 4) % 4)
while len(binp) % 4: binp.append(0)
with open(DST, 'wb') as f:
    f.write(struct.pack('<III', 0x46546C67, 2, 12 + 8 + len(jb) + 8 + len(binp)))
    f.write(struct.pack('<II', len(jb), 0x4E4F534A)); f.write(jb); f.write(struct.pack('<II', len(binp), 0x004E4942)); f.write(binp)
print('записано', DST, '%.1f МБ' % (os.path.getsize(DST) / 1e6))
