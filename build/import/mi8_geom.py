#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Геометрия Ми-8АМТ/Ми-171 из модели Mil Mi-8AMTSh (Sketchfab, 42manako, CC BY 4.0) в осях сайта.
   Общая часть для pack_mi8.py (упаковка) и livery_mi8.py (ливрея): чтение glTF, удаление военного оборудования,
   масштаб в метры, поворот (нос +X, верх +Y, правый борт +Z), посадка на землю, центры втулок винтов."""
import json, os, struct
import numpy as np

SCALE = 147.0                       # единицы модели → метры
# вооружение, пилоны, блоки НАР, ЭВУ (экраны-подавители ИК-излучения на выхлопе), кассеты ловушек, бронеплиты
DELETE = ['object_004_0', 'object_029_0', 'object_040_0', 'object_041_0', 'object_042_0', 'object_053_0', 'object_054_0',
          'object_077_0', 'object_078_0', 'object9_0', 'object11_0', 'object_000_0', 'object_013_0', 'object_014_0', 'object_015_0',
          'object_002_0', 'object_063_0', 'object_064_0', 'object_075_0',      # ЭВУ: у гражданских бортов — круглые патрубки
          'object_055_0',                                                      # кассеты отстрела ловушек на бортах
          'object_030_0']                                                      # бронеплиты по бортам кабины (под ними — нижние окна)
# выхлопные патрубки двигателей (строятся в mi8_extras.py): точка на капоте, направление (правый борт), радиусы, вылет, глубина
EXHAUST = dict(x=0.36, y=3.50, z=0.769, d=(-0.36, 0.14, 0.92), Ro=0.30, Ri=0.255, L=0.22, D=0.45)
def _exhaust_hole(c):
    """Треугольники капота внутри патрубка — вырезаем, иначе обшивка закрывает его глубину."""
    e = EXHAUST; out = np.zeros(len(c), bool)
    for side in (+1, -1):
        d = np.array(e['d'], float) * [1, 1, side]; d /= np.linalg.norm(d)
        S = np.array([e['x'], e['y'], e['z'] * side]); r = c - S; t = r @ d
        dist = np.linalg.norm(r - t[:, None] * d, axis=1)
        out |= (dist < e['Ro'] - 0.02) & (t > -0.4) & (t < 0.3)
    return out
# треугольники, которые убираем внутри группы: глухая часть сдвижных панелей-блистеров кабины (на их место — стекло),
# обшивка капота под выхлопными патрубками
DROP_TRIS = {'sub02_0': lambda c: (c[:, 0] > 3.3) & (c[:, 1] > 1.6) & (np.abs(c[:, 2]) > 0.8),
             'sub01_0': _exhaust_hole}
MAIN_ROTOR = ['object_025_0', 'sub0191_0', 'sub0292_0', 'object_024_0', 'object_021_0', 'object_022_0', 'object_026_0', 'object_027_0']
TAIL_ROTOR = ['object_020_0', 'object_019_0', 'object_017_0', 'object_018_0']
Ry = np.array([[0, 0, 1], [0, 1, 0], [-1, 0, 0]], float)   # +90° вокруг Y: нос модели (+Z) → +X

CT = {5120: ('b', 1), 5121: ('B', 1), 5122: ('h', 2), 5123: ('H', 2), 5125: ('I', 4), 5126: ('f', 4)}
NC = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4}

def _local_matrix(n):
    if 'matrix' in n: return np.array(n['matrix'], float).reshape(4, 4).T
    t = n.get('translation', [0, 0, 0]); x, y, z, w = n.get('rotation', [0, 0, 0, 1]); s = n.get('scale', [1, 1, 1])
    R = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)], [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)], [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
    M = np.eye(4); M[:3, :3] = R * np.array(s); M[:3, 3] = t; return M

def load(src, delete=DELETE):
    """→ dict(prims=[[группа, P(м), N, UV, I]], main_c, tail_c): позиции уже в осях сайта, модель стоит на y=0."""
    base = os.path.dirname(src)
    js = json.load(open(src, encoding='utf-8'))
    buf = open(os.path.join(base, js['buffers'][0]['uri']), 'rb').read()
    acc, bvs, nodes, meshes = js['accessors'], js['bufferViews'], js['nodes'], js['meshes']
    def read(i):
        a = acc[i]; v = bvs[a['bufferView']]; off = v.get('byteOffset', 0) + a.get('byteOffset', 0)
        fmt, sz = CT[a['componentType']]; n = NC[a['type']]; stride = v.get('byteStride', sz * n)
        dt = np.dtype('<' + fmt)
        if stride == sz * n:
            return np.frombuffer(buf, dt, a['count'] * n, off).reshape(a['count'], n).astype(np.float64 if fmt == 'f' else np.int64)
        out = np.empty((a['count'], n), np.float64)
        for k in range(a['count']): out[k] = struct.unpack_from('<' + fmt * n, buf, off + k * stride)
        return out
    world = [None] * len(nodes); parent = {}
    def walk(i, M):
        world[i] = M @ _local_matrix(nodes[i])
        for c in nodes[i].get('children', []): parent[c] = i; walk(c, world[i])
    for r in js['scenes'][0]['nodes']: walk(r, np.eye(4))
    def group_name(i):  # имя «объекта» (родителя mesh-узла)
        n = nodes[i]; p = parent.get(i)
        return n.get('name', '') if 'mesh' not in n or p is None else nodes[p].get('name', n.get('name', ''))
    prims = []
    for i, n in enumerate(nodes):
        if 'mesh' not in n: continue
        g = group_name(i)
        if g in delete: continue
        W = world[i]; L = Ry @ (W[:3, :3] * SCALE); Nm = np.linalg.inv(L).T
        for p in meshes[n['mesh']]['primitives']:
            P = read(p['attributes']['POSITION']) @ L.T + (Ry @ W[:3, 3] * SCALE)
            N = read(p['attributes']['NORMAL']) @ Nm.T; N /= np.linalg.norm(N, axis=1, keepdims=True) + 1e-9
            UV = read(p['attributes']['TEXCOORD_0']); UV = UV - np.floor(UV)
            I = read(p['indices'])[:, 0].astype(np.int64)
            prims.append([g, P, N, UV, I])
    allP = np.vstack([p[1] for p in prims]); mn = allP.min(0)
    shift = np.array([0.0, -mn[1], 0.9])          # на землю; фюзеляж по оси z=0
    for p in prims: p[1] = p[1] + shift
    for pr in prims:                                   # сдвижные панели кабины — целиком стеклянные (у исходника — глухие)
        if pr[0] in DROP_TRIS:
            T = pr[4].reshape(-1, 3); keep = ~DROP_TRIS[pr[0]](pr[1][T].mean(1)); pr[4] = T[keep].ravel()
    def center_of(names):
        pts = np.vstack([p[1] for p in prims if p[0] in names]); return (pts.min(0) + pts.max(0)) / 2
    main_c = center_of(['object_021_0', 'object_022_0']); main_c[1] = 0   # ось Y через центр втулки НВ
    tail_c = center_of(['object_019_0'])                                   # втулка РВ
    return {'prims': prims, 'main_c': main_c, 'tail_c': tail_c}

# ---------------- палитра однотонных цветов в свободном углу атласа (4096 px, пустая область сверху, x≥2432) ----------------
PAL_X0, PAL_Y0, PAL_CELL = 2448, 16, 16
PAL_NAMES = ['strut', 'tire', 'hub', 'frame', 'rim', 'exh_metal', 'exh_soot', 'radome']
EXH_STRIP = (2448, 64, 256, 32)     # градиент внутренней поверхности выхлопного патрубка: бронза у среза → копоть в глубине
def exh_uv(t, tex_size=4096):
    """UV точки градиента патрубка, t=0 — срез, t=1 — глубина."""
    x0, y0, w, h = EXH_STRIP
    return np.stack([(x0 + 4 + np.asarray(t) * (w - 8)) / tex_size, np.full(np.shape(t), (y0 + h / 2) / tex_size)], -1)
def pal_uv(name, tex_size=4096):
    """UV центра плашки палитры (glTF: v от верха)."""
    i = PAL_NAMES.index(name)
    return ((PAL_X0 + (i % 8) * PAL_CELL + PAL_CELL / 2) / tex_size, (PAL_Y0 + (i // 8) * PAL_CELL + PAL_CELL / 2) / tex_size)
def pal_rect(name):
    i = PAL_NAMES.index(name); x = PAL_X0 + (i % 8) * PAL_CELL; y = PAL_Y0 + (i // 8) * PAL_CELL
    return x, y, x + PAL_CELL, y + PAL_CELL

# шасси: у исходника все детали шасси ссылаются на один тексель (0,0) — раздаём им плашки палитры
GEAR_ROLE = {'object_062_0': 'tire', 'object_085_0': 'tire',                                    # шины основных и передних колёс
             'object_060_0': 'hub', 'object_061_0': 'hub', 'object_084_0': 'hub',               # диски
             **{g: 'strut' for g in ('object_056_0', 'object_057_0', 'object_058_0', 'object_059_0', 'object_079_0',
                                     'object_080_0', 'object_081_0', 'object_082_0', 'object_083_0')}}
def apply_gear_palette(prims):
    for p in prims:
        if p[0] in GEAR_ROLE:
            u, v = pal_uv(GEAR_ROLE[p[0]]); p[3] = np.tile([u, v], (len(p[3]), 1))

# круглые окна салона (найдены по граничным петлям обшивки sub01_0): центр x, y; радиус проёма 0.20 м; оба борта
CABIN_WINDOWS = [(-1.494, 2.076), (-0.538, 2.076), (0.219, 2.094), (1.165, 2.094)]
WINDOW_R = 0.201

# ---------------- остекление кабины: проёмы в обшивке (граничные петли sub01_0 / sub02_0) ----------------
SKIN = ('sub01_0', 'sub02_0')
def cockpit_loops(G):
    """Проёмы остекления кабины: лобовые стёкла, боковые окна, сдвижные блистеры (проём панели целиком), нижние окна.
       → список массивов (n, 3) — замкнутые контуры по кромке обшивки."""
    import mi8_loops
    out = []
    for name in ('sub01_0',):
        Ps, Is, off = [], [], 0
        for g, P, N, UV, I in G['prims']:
            if g == name: Ps.append(P); Is.append(I + off); off += len(P)
        loops, Pw = mi8_loops.boundary_loops(np.vstack(Ps), np.concatenate(Is))
        for L in loops:
            q = Pw[L]; per = np.linalg.norm(np.diff(np.vstack([q, q[:1]]), axis=0), axis=1).sum()
            # 0.8–4.2 м по периметру, в носовой части, выше пола
            if 0.8 < per < 4.2 and q[:, 0].max() > 3.8 and q[:, 1].min() > 1.1: out.append(q)
    return out
