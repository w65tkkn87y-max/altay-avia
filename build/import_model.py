#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Импорт готовой glTF/GLB-модели вертолёта в сайт «АлтайАвиа»:
удаление военных элементов, перекраска в ливрею, приведение к системе координат сайта.
Чистый Python, без зависимостей (правит JSON-часть GLB; геометрия не трогается).

  python3 build/import_model.py list  model.glb                   # дерево узлов и материалы
  python3 build/import_model.py apply model.glb site/models/mi8amt.glb --config build/import/mi8amtsh.json
  python3 build/import_model.py apply model.glb out.glb --delete pylon,rocket --color "Fuselage=#F5F7F9"

Конфиг (JSON):
{
  "delete": ["pylon", "rocket", "launcher", "gun", "armor"],     # подстроки/регэкспы имён узлов (без учёта регистра)
  "materials": {                                                  # подстрока имени материала → окраска
    "body":  {"color": "#F5F7F9", "metallic": 0.0, "roughness": 0.35, "drop_texture": true},
    "glass": {"color": "#0E1A24", "roughness": 0.05, "alpha": 0.9}
  },
  "default_material": {"color": "#F5F7F9"},                       # применить ко всем остальным (необязательно)
  "transform": {"scale": 1.0, "rotate_y_deg": 0, "rotate_x_deg": 0, "translate": [0, 0, 0]}
}
Ожидания сайта: метры, нос по +X, верх по +Y, модель стоит на земле (y=0) — сдвиг на землю
делается автоматически по габаритам (accessor min/max), если "ground": true (по умолчанию).
Только .glb (бинарный glTF). Если у вас .gltf + .bin + текстуры — выберите при скачивании GLB.
"""
import json, re, struct, sys, math, os

MAGIC = 0x46546C67  # 'glTF'

def read_glb(path):
    with open(path, 'rb') as f: data = f.read()
    magic, version, length = struct.unpack_from('<III', data, 0)
    if magic != MAGIC: raise SystemExit('Не GLB-файл: ' + path)
    off = 12; chunks = []
    while off < length:
        clen, ctype = struct.unpack_from('<II', data, off); off += 8
        chunks.append((ctype, data[off:off + clen])); off += clen
    js = json.loads(chunks[0][1].decode('utf-8'))
    bins = [c[1] for c in chunks[1:] if c[0] == 0x004E4942]
    return js, (bins[0] if bins else b'')

def write_glb(path, js, binary):
    jb = json.dumps(js, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    jb += b' ' * ((4 - len(jb) % 4) % 4)
    bb = binary + b'\x00' * ((4 - len(binary) % 4) % 4)
    total = 12 + 8 + len(jb) + (8 + len(bb) if bb else 0)
    with open(path, 'wb') as f:
        f.write(struct.pack('<III', MAGIC, 2, total))
        f.write(struct.pack('<II', len(jb), 0x4E4F534A)); f.write(jb)
        if bb: f.write(struct.pack('<II', len(bb), 0x004E4942)); f.write(bb)

def hex_to_rgb(h):
    h = h.lstrip('#'); return [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
def srgb_to_linear(c): return [((x / 12.92) if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4) for x in c]

def node_tree(js):
    nodes = js.get('nodes', []); parent = {}
    for i, n in enumerate(nodes):
        for c in n.get('children', []): parent[c] = i
    roots = [i for i in range(len(nodes)) if i not in parent]
    return nodes, parent, roots

def cmd_list(path):
    js, _ = read_glb(path)
    nodes, parent, roots = node_tree(js)
    mats = js.get('materials', []); meshes = js.get('meshes', [])
    print('Узлы (%d):' % len(nodes))
    def walk(i, d):
        n = nodes[i]; m = n.get('mesh')
        mat_names = []
        if m is not None:
            for p in meshes[m].get('primitives', []):
                if 'material' in p: mat_names.append(mats[p['material']].get('name', '#%d' % p['material']))
        print('  ' * d + '- [%d] %s%s%s' % (i, n.get('name', '(без имени)'), (' mesh=' + meshes[m].get('name', '#%d' % m)) if m is not None else '', (' mat=' + ','.join(sorted(set(mat_names)))) if mat_names else ''))
        for c in n.get('children', []): walk(c, d + 1)
    for r in roots: walk(r, 0)
    print('\nМатериалы (%d):' % len(mats))
    for i, mt in enumerate(mats):
        pbr = mt.get('pbrMetallicRoughness', {})
        print('  [%d] %s color=%s tex=%s metal=%s rough=%s' % (i, mt.get('name', ''), pbr.get('baseColorFactor'), 'да' if 'baseColorTexture' in pbr else 'нет', pbr.get('metallicFactor'), pbr.get('roughnessFactor')))
    print('\nБуферы:', [b.get('byteLength') for b in js.get('buffers', [])], 'изображений:', len(js.get('images', [])))

def bounds(js, binary):
    """Габариты по accessor.min/max позиций (без учёта трансформаций узлов — достаточно для оценки)."""
    mn = [1e9] * 3; mx = [-1e9] * 3
    for mesh in js.get('meshes', []):
        for p in mesh.get('primitives', []):
            a = js['accessors'][p['attributes']['POSITION']]
            if 'min' in a and 'max' in a:
                mn = [min(mn[i], a['min'][i]) for i in range(3)]; mx = [max(mx[i], a['max'][i]) for i in range(3)]
    return mn, mx

def cmd_apply(src, dst, cfg):
    js, binary = read_glb(src)
    nodes, parent, roots = node_tree(js)
    # --- удаление узлов по имени ---
    pats = [re.compile(p, re.I) for p in cfg.get('delete', [])]
    doomed = set()
    def mark(i):
        doomed.add(i)
        for c in nodes[i].get('children', []): mark(c)
    for i, n in enumerate(nodes):
        name = n.get('name', '')
        if any(p.search(name) for p in pats): mark(i)
    for i, n in enumerate(nodes):
        if 'children' in n: n['children'] = [c for c in n['children'] if c not in doomed]
    for sc in js.get('scenes', []):
        sc['nodes'] = [r for r in sc.get('nodes', []) if r not in doomed]
    for i in doomed: nodes[i].pop('mesh', None)  # узел остаётся, но без геометрии
    print('Удалено узлов:', len(doomed), sorted(nodes[i].get('name', '#%d' % i) for i in doomed)[:40])
    # --- материалы ---
    rules = cfg.get('materials', {}); default = cfg.get('default_material')
    changed = 0
    for mt in js.get('materials', []):
        name = mt.get('name', '')
        rule = None
        for key, r in rules.items():
            if re.search(key, name, re.I): rule = r; break
        if rule is None: rule = default
        if not rule: continue
        pbr = mt.setdefault('pbrMetallicRoughness', {})
        if 'color' in rule:
            rgb = srgb_to_linear(hex_to_rgb(rule['color']))
            pbr['baseColorFactor'] = rgb + [rule.get('alpha', 1.0)]
            if rule.get('drop_texture', True): pbr.pop('baseColorTexture', None)
        if 'metallic' in rule: pbr['metallicFactor'] = rule['metallic']
        if 'roughness' in rule: pbr['roughnessFactor'] = rule['roughness']
        if rule.get('alpha', 1.0) < 1.0: mt['alphaMode'] = 'BLEND'
        for k in ('emissiveTexture',):
            if rule.get('drop_texture', True): mt.pop(k, None)
        changed += 1
    print('Перекрашено материалов:', changed)
    # --- трансформация корня: масштаб, повороты, посадка на землю ---
    tr = cfg.get('transform', {})
    mn, mx = bounds(js, binary)
    s = float(tr.get('scale', 1.0))
    ry = math.radians(tr.get('rotate_y_deg', 0)); rx = math.radians(tr.get('rotate_x_deg', 0))
    t = list(tr.get('translate', [0, 0, 0]))
    if cfg.get('ground', True) and mn[1] < 1e8:
        # после поворота по X ось «вверх» может смениться — простейший случай: без поворота X
        if abs(rx) < 1e-6: t[1] -= mn[1] * s
    # кватернион из поворотов (сначала X, затем Y)
    qx = [math.sin(rx / 2), 0, 0, math.cos(rx / 2)]; qy = [0, math.sin(ry / 2), 0, math.cos(ry / 2)]
    def qmul(a, b):
        ax, ay, az, aw = a; bx, by, bz, bw = b
        return [aw * bx + ax * bw + ay * bz - az * by, aw * by - ax * bz + ay * bw + az * bx, aw * bz + ax * by - ay * bx + az * bw, aw * bw - ax * bx - ay * by - az * bz]
    q = qmul(qy, qx)
    root = {'name': 'AltayAvia_root', 'children': [r for r in roots if r not in doomed], 'scale': [s, s, s], 'rotation': q, 'translation': t}
    js['nodes'].append(root)
    ri = len(js['nodes']) - 1
    for sc in js.get('scenes', []): sc['nodes'] = [ri]
    js.setdefault('asset', {})['generator'] = 'AltayAvia import_model.py'
    js['asset'].setdefault('extras', {})['altayavia'] = {'source': os.path.basename(src), 'license_note': cfg.get('license_note', '')}
    write_glb(dst, js, binary)
    size = (mx[0] - mn[0]) * s, (mx[1] - mn[1]) * s, (mx[2] - mn[2]) * s
    print('Записано:', dst, '%.1f МБ' % (os.path.getsize(dst) / 1e6), '· габариты после масштаба: %.1f × %.1f × %.1f м' % size)

def main(argv):
    if len(argv) < 2 or argv[0] not in ('list', 'apply'):
        print(__doc__); return 1
    if argv[0] == 'list': cmd_list(argv[1]); return 0
    src, dst = argv[1], argv[2]; cfg = {}
    args = argv[3:]
    while args:
        a = args.pop(0)
        if a == '--config': cfg = json.load(open(args.pop(0), encoding='utf-8'))
        elif a == '--delete': cfg.setdefault('delete', []).extend(args.pop(0).split(','))
        elif a == '--color':
            k, v = args.pop(0).split('='); cfg.setdefault('materials', {})[k] = {'color': v}
        elif a == '--scale': cfg.setdefault('transform', {})['scale'] = float(args.pop(0))
        elif a == '--rotate-y': cfg.setdefault('transform', {})['rotate_y_deg'] = float(args.pop(0))
    cmd_apply(src, dst, cfg); return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
