#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Eurocopter AS350 «АлтайАвиа» из модели FGUK AS350 Squirrel (FlightGear, GPL-2.0, build/import/as350src):
   AC3D → компактный формат сайта (site/models/as350.js + as350.jpg, см. glb2js.py / Viewer.loadPacked).
   • оси сайта: метры, нос +X, верх +Y, правый борт +Z (AC3D: x — к хвосту, y — вверх, z — влево);
   • все текстуры сводятся в один атлас 4096×2048 (борта 2048 px, хвост/верх 1024, салон 512/256);
   • ливрея «АлтайАвиа» (RA-04062) дорисовывается в текстурах по 3D-координатам (livery_as350.py);
   • стекло кабины — отдельные меши с флагом m:'glass' (прозрачный материал в heli3d.js);
   • узлы MainRotor / TailRotor с осями в центрах втулок — для вращения винтов.
   python3 build/import/pack_as350.py            (из корня проекта)
"""
import os, sys, json, base64, math
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ac3d

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, 'build', 'import', 'as350src')
OUT_JS = os.path.join(ROOT, 'site', 'models', 'as350.js')
OUT_TEX = os.path.join(ROOT, 'site', 'models', 'as350.jpg')
NO_LIVERY = '--no-livery' in sys.argv

AC_TO_SITE = np.diag([-1.0, 1.0, -1.0])        # поворот на 180° вокруг вертикали: нос к +X, правый борт к +Z

# ---------------- атлас: ячейки по 512 px, 8×4 ----------------
AW, AH = 4096, 2048
TILES = {  # имя → (x, y, размер) в пикселях атласа
    'as350b_01.jpg': (0, 0, 2048),
    'as350b_03.jpg': (2048, 0, 1024), 'as350b_02.jpg': (3072, 0, 1024),
    'as350b_04.jpg': (2048, 1024, 512), 'as350b_06.jpg': (2560, 1024, 512),
    'as350bi_09.jpg': (3072, 1024, 512), 'as350bi_08.jpg': (3584, 1024, 512),
    'as350bi_04.jpg': (2048, 1536, 512), 'as350bi_01.jpg': (2560, 1536, 512),
    'as350bi_02.jpg': (3072, 1536, 256), 'as350bi_03.jpg': (3328, 1536, 256),
    'as350bi_05.jpg': (3072, 1792, 256), 'as350bi_06.jpg': (3328, 1792, 256),
    'as350bi_07.jpg': (3584, 1536, 256), 'colors.png': (3840, 1536, 256),
    '_palette': (3584, 1792, 256), '_blade': (3840, 1792, 256),
}
PAD = {2048: 6, 1024: 4, 512: 3, 256: 2}

def tile_uv(name, u, v):
    """UV исходной текстуры (AC3D: v от низа) → UV атласа (flipY=false: v от верха)."""
    x0, y0, s = TILES[name]; p = PAD[s]; inner = s - 2 * p
    u = np.clip(u, 0.0, 1.0); v = np.clip(v, 0.0, 1.0)
    return np.stack([(x0 + p + u * inner) / AW, (y0 + p + (1.0 - v) * inner) / AH], -1)

# палитра однотонных цветов: 16×16 плашек по 16 px
PALETTE = {
    'white': '#F4F5F6', 'frame': '#C9CED4', 'dark': '#3A3D42', 'black': '#141518', 'navy': '#14224F',
    'metal': '#8C9196', 'hub': '#5E6369', 'glass': '#1B2733',
}
PAL_IDX = {k: i for i, k in enumerate(PALETTE)}
def palette_uv(name):
    i = PAL_IDX[name]; cx, cy = (i % 16) * 16 + 8, (i // 16) * 16 + 8
    return tile_uv('_palette', cx / 256.0, 1.0 - cy / 256.0)

def hex_rgb(h): h = h.lstrip('#'); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

# ---------------- геометрия ----------------
def polygon_normal(P):
    n = np.zeros(3)
    for a, b in zip(P, np.roll(P, -1, 0)):
        n += np.array([(a[1] - b[1]) * (a[2] + b[2]), (a[2] - b[2]) * (a[0] + b[0]), (a[0] - b[0]) * (a[1] + b[1])])
    l = np.linalg.norm(n); return n / l if l > 1e-12 else np.array([0.0, 1.0, 0.0])

class Part:
    """Набор треугольников одного вида (материал + группа винта) с позициями/нормалями/UV по углам."""
    def __init__(self, name, group, kind):
        self.name, self.group, self.kind = name, group, kind
        self.P, self.N, self.UV = [], [], []
    def add(self, P3, N3, UV3):
        self.P.append(P3); self.N.append(N3); self.UV.append(UV3)

def object_triangles(node, M):
    """Треугольники объекта в координатах сайта: позиции, сглаженные нормали (crease), исходные UV, номер материала."""
    V = node['verts'] @ M[:3, :3].T + M[:3, 3]
    V = V @ AC_TO_SITE.T
    rep, off = node['texrep'], node['texoff']
    tris = []   # (i0,i1,i2), (uv0,uv1,uv2), mat, smooth, face_normal
    for flags, mat, refs in node['surfs']:
        if flags & 0xF or len(refs) < 3: continue           # линии не нужны
        idx = [r[0] for r in refs]
        uvs = [(r[1] * rep[0] + off[0], r[2] * rep[1] + off[1]) for r in refs]
        fn = polygon_normal(V[idx])
        for k in range(1, len(refs) - 1):
            tris.append(((idx[0], idx[k], idx[k + 1]), (uvs[0], uvs[k], uvs[k + 1]), mat, bool(flags & 0x10), fn))
    # сглаживание по углу излома
    cosc = math.cos(math.radians(min(node['crease'], 89.0)))
    tn = np.array([t[4] for t in tris]) if tris else np.zeros((0, 3))
    area = []
    for t in tris:
        a, b, c = V[list(t[0])]; area.append(np.linalg.norm(np.cross(b - a, c - a)) + 1e-9)
    area = np.array(area)
    inc = {}
    for ti, t in enumerate(tris):
        if t[3]:
            for vi in t[0]: inc.setdefault(vi, []).append(ti)
    out = []
    for ti, t in enumerate(tris):
        ns = []
        for vi in t[0]:
            if not t[3]: ns.append(tn[ti]); continue
            cand = inc[vi]; nn = tn[cand]; ok = nn @ tn[ti] >= cosc
            s = (nn[ok] * area[cand][ok, None]).sum(0); l = np.linalg.norm(s)
            ns.append(s / l if l > 1e-12 else tn[ti])
        out.append((V[list(t[0])], np.array(ns), np.array(t[1], float), t[2]))
    return out

def load_scene():
    mats, root = ac3d.load(os.path.join(SRC, 'as350a-test.ac'))
    objs = [(path, n, M, mats) for path, n, M in ac3d.world_meshes(root)]
    # рулевой винт: tailrotor.ac + две лопасти blade.ac (второй — поворот на 180° вокруг оси винта)
    tm, troot = ac3d.load(os.path.join(SRC, 'TailRotor', 'tailrotor.ac'))
    bm, broot = ac3d.load(os.path.join(SRC, 'TailRotor', 'blade.ac'))
    # локальные оси (AC3D): лопасть вдоль x, ось вращения y, хорда z → на сайте ось = +Z (правый борт),
    # положение втулки и масштаб 0.76 — из AS350-Squirrel.xml (x 6.1, y 0.373, z 0.7 в осях FlightGear)
    Rl = np.array([[1.0, 0, 0], [0, 0, -1.0], [0, 1.0, 0]])            # локальные → сайт (перед «разворотом» AC_TO_SITE)
    hub_site = np.array([-6.1, 0.7, 0.373]); s = 0.76
    def placed(M_local, extra=np.eye(3)):
        W = np.eye(4); W[:3, :3] = AC_TO_SITE.T @ (Rl @ extra) * s          # AC_TO_SITE снимется в object_triangles
        W[:3, 3] = AC_TO_SITE.T @ hub_site
        return W @ M_local
    tail = []
    for path, n, M in ac3d.world_meshes(troot): tail.append(('tail/' + path, n, placed(M), tm))
    R180 = np.diag([-1.0, 1.0, -1.0])
    for k, extra in enumerate((np.eye(3), R180)):
        for path, n, M in ac3d.world_meshes(broot):
            if n['name'] in ('propblur', 'propdisc'): continue
            tail.append(('tailblade%d/' % k + path, n, placed(M, extra), bm))
    return objs, tail, hub_site

def main_rotor_hub(blade_tris):
    P = np.vstack([t[0] for t in blade_tris])
    c = np.array([0.0, 0.0, 0.0])          # ось вала в модели FlightGear: x=0, y=0 → на сайте x=0, z=0
    for _ in range(3):   # центр описанной окружности по трём концам лопастей
        d = P[:, [0, 2]] - c[[0, 2]]; r = np.hypot(d[:, 0], d[:, 1]); ang = np.arctan2(d[:, 1], d[:, 0])
        far = r > r.max() * 0.6
        tips = []
        for k in range(3):
            if k == 0: a0 = ang[far][np.argmax(r[far])]
            sel = far & (np.abs(((ang - a0 - k * 2 * np.pi / 3) + np.pi) % (2 * np.pi) - np.pi) < 0.5)
            if not sel.any(): sel = far & (np.abs(((ang - a0 + k * 2 * np.pi / 3) + np.pi) % (2 * np.pi) - np.pi) < 0.5)
            q = P[sel]; tips.append(q[np.argmax(np.hypot(q[:, 0] - c[0], q[:, 2] - c[2]))][[0, 2]])
        (ax, az), (bx, bz), (cx, cz) = tips
        dd = 2 * (ax * (bz - cz) + bx * (cz - az) + cx * (az - bz))
        ux = ((ax * ax + az * az) * (bz - cz) + (bx * bx + bz * bz) * (cz - az) + (cx * cx + cz * cz) * (az - bz)) / dd
        uz = ((ax * ax + az * az) * (cx - bx) + (bx * bx + bz * bz) * (ax - cx) + (cx * cx + cz * cz) * (bx - ax)) / dd
        c = np.array([ux, c[1], uz])
    d = np.hypot(P[:, 0] - c[0], P[:, 2] - c[2])
    c[1] = P[d < 0.25, 1].mean() if np.any(d < 0.25) else P[:, 1].max()
    R = d.max()
    return c, R, [np.array(t) for t in tips]

def blade_uv(P, hub, R, tips):
    """Своя развёртка лопастей: u — доля радиуса, v — положение по хорде (текстура _blade)."""
    d = P[:, [0, 2]] - hub[[0, 2]]; r = np.hypot(d[:, 0], d[:, 1])
    dirs = [(t - hub[[0, 2]]) / np.linalg.norm(t - hub[[0, 2]]) for t in tips]
    best = np.argmax(np.stack([d @ di for di in dirs], 1), 1)
    perp = np.array([[-dirs[b][1], dirs[b][0]] for b in best])
    c = (d * perp).sum(1)
    u = np.clip(r / R, 0, 1); v = np.clip(0.5 + c / 0.8, 0, 1)
    return u, v

# ---------------- текстуры ----------------
def load_textures():
    tex = {}
    for name in TILES:
        if name.startswith('_'): continue
        p = os.path.join(SRC, 'TailRotor', name) if name == 'colors.png' else os.path.join(SRC, name)
        tex[name] = Image.open(p).convert('RGB')
    return tex

def make_blade_texture(size=256):
    """Лопасть несущего винта: серый композит, металлическая оковка передней кромки, тёмные законцовки."""
    u = np.linspace(0, 1, size)[None, :].repeat(size, 0)          # по радиусу (слева направо)
    v = np.linspace(1, 0, size)[:, None].repeat(size, 1)          # по хорде (v=1 — верх картинки)
    base = np.array(hex_rgb('#62676D'), float)
    img = np.ones((size, size, 3)) * base
    img *= (0.92 + 0.08 * np.cos((v - 0.5) * np.pi))[..., None]          # лёгкий объём по хорде
    lead = np.clip((v - 0.8) / 0.12, 0, 1)[..., None]                    # оковка передней кромки
    img = img * (1 - lead * 0.6) + np.array(hex_rgb('#A7ACB1')) * lead * 0.6
    tip = np.clip((u - 0.955) / 0.01, 0, 1)[..., None]                   # законцовка
    img = img * (1 - tip) + np.array(hex_rgb('#26282C')) * tip
    hub = np.clip((0.13 - u) / 0.02, 0, 1)[..., None]                    # втулка/стаканы — металл
    img = img * (1 - hub) + np.array(hex_rgb('#7E8388')) * hub
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))

def make_palette():
    img = Image.new('RGB', (256, 256), (128, 128, 128))
    arr = np.array(img)
    for name, i in PAL_IDX.items():
        x, y = (i % 16) * 16, (i // 16) * 16; arr[y:y + 16, x:x + 16] = hex_rgb(PALETTE[name])
    return Image.fromarray(arr)

def build_atlas(tex):
    atlas = np.zeros((AH, AW, 3), np.uint8); atlas[:] = (128, 128, 128)
    srcs = dict(tex); srcs['_palette'] = make_palette(); srcs['_blade'] = make_blade_texture()
    for name, (x0, y0, s) in TILES.items():
        p = PAD[s]; inner = s - 2 * p
        im = np.array(srcs[name].resize((inner, inner), Image.LANCZOS))
        im = np.pad(im, ((p, p), (p, p), (0, 0)), mode='edge')     # поля от «протекания» соседних плиток на мип-уровнях
        atlas[y0:y0 + s, x0:x0 + s] = im
    return Image.fromarray(atlas)

# ---------------- упаковка в формат сайта ----------------
def pack_mesh(part, pivot):
    P = np.concatenate(part.P).reshape(-1, 3) - pivot
    N = np.concatenate(part.N).reshape(-1, 3)
    UV = np.concatenate(part.UV).reshape(-1, 2)
    key = np.hstack([np.round(P * 2000), np.round(N * 300), np.round(UV * 65535)])
    _, first, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
    inv = inv.reshape(-1)
    P, N, UV = P[first], N[first], UV[first]
    I = inv.astype(np.int64)
    pmn, pmx = P.min(0), P.max(0); size = np.maximum(pmx - pmn, 1e-6)
    scale = size / 32766.0; offset = (pmn + pmx) / 2
    q = np.round((P - offset) / scale).astype('<i2')
    N = N / (np.linalg.norm(N, axis=1, keepdims=True) + 1e-9)
    nq = np.clip(np.round(N * 127), -127, 127).astype('<i1')
    uq = np.clip(np.round(UV * 65535), 0, 65535).astype('<u2')
    it = 16 if len(P) < 65535 else 32
    idx = I.astype('<u2' if it == 16 else '<u4')
    b = bytearray(q.tobytes())
    while len(b) % 4: b.append(0)
    b += uq.tobytes()
    while len(b) % 4: b.append(0)
    b += idx.tobytes(); b += nq.tobytes()
    m = {'n': part.name, 'g': part.group, 'c': int(len(P)), 'i': int(len(I)), 'it': it,
         's': [float('%.6g' % x) for x in scale], 'o': [float('%.5g' % x) for x in offset],
         'd': base64.b64encode(bytes(b)).decode('ascii')}
    if part.kind != 'paint': m['m'] = part.kind
    return m, len(I) // 3, len(b)

def main():
    objs, tail, tail_hub = load_scene()
    tex = load_textures()
    parts = {}
    def part(name, group, kind):
        k = (name, group, kind)
        if k not in parts: parts[k] = Part(name, group, kind)
        return parts[k]
    painted = []            # (имя текстуры, позиции, нормали, исходные UV) — для ливреи
    occluders = []          # непрозрачные грани корпуса — для оценки видимости снаружи
    blade_tris = []
    SKIP_OBJ = {'blurred', 'mirrors_2'}
    for path, n, M, mats in objs:
        if n['name'] in SKIP_OBJ: continue
        tris = object_triangles(n, M)
        tname = n['texture']
        grp = 'MainRotor' if n['name'] == 'blades' else None
        for P3, N3, UV3, mat in tris:
            m = mats[mat] if mat < len(mats) else {'trans': 0, 'rgb': [1, 1, 1]}
            if m.get('trans', 0) >= 0.99: continue
            if n['name'] == 'blades': blade_tris.append((P3, N3)); continue
            if not (m.get('trans', 0) > 0.3 and not tname): occluders.append(P3)
            if m.get('trans', 0) > 0.3 and not tname:                     # стекло (Material__10, прозрачность 0.55)
                part('glass', None, 'glass').add(P3, N3, np.tile(palette_uv('glass'), (3, 1))); continue
            if tname in TILES:
                uv = tile_uv(tname, UV3[:, 0], UV3[:, 1])
                part('body', None, 'paint').add(P3, N3, uv)
                if tname in ('as350b_01.jpg', 'as350b_02.jpg', 'as350b_03.jpg'): painted.append((tname, P3, N3, UV3))
                continue
            # без текстуры: цвет по материалу и месту
            e = [np.linalg.norm(P3[i] - P3[(i + 1) % 3]) for i in range(3)]
            if P3[:, 1].mean() < -0.56: col = 'navy'                                       # полозья и поперечины шасси
            elif max(e) > 0.2 and min(e) < 0.012: col = 'dark'                            # тросорезы, антенны, поручни
            elif m['rgb'][0] < 0.5: col = 'dark'
            elif mat == 2: col = 'white'
            else: col = 'frame'
            part('body', None, 'paint').add(P3, N3, np.tile(palette_uv(col), (3, 1)))
    # несущий винт: своя развёртка
    hub, R, tips = main_rotor_hub(blade_tris)
    for P3, N3 in blade_tris:
        u, v = blade_uv(P3, hub, R, tips)
        part('rotor', 'MainRotor', 'paint').add(P3, N3, tile_uv('_blade', u, v))
    # рулевой винт
    for path, n, M, mats in tail:
        for P3, N3, UV3, mat in object_triangles(n, M):
            part('tailrotor', 'TailRotor', 'paint').add(P3, N3, tile_uv('colors.png', UV3[:, 0], UV3[:, 1]))

    if not NO_LIVERY:
        import livery_as350
        livery_as350.paint(tex, painted, occluders)
    atlas = build_atlas(tex)
    atlas.save(OUT_TEX, quality=86, optimize=True, progressive=True)

    pivots = {'MainRotor': hub, 'TailRotor': tail_hub}
    # side:'front' — грани AC3D односторонние (как в FlightGear); иначе стенки салона, лежащие вплотную к обшивке, «пробивают» наружу
    out = {'v': 1, 'side': 'front', 'tex': os.path.basename(OUT_TEX), 'pivots': {k: [round(float(x), 4) for x in v] for k, v in pivots.items()}, 'meshes': []}
    tri = raw = 0
    for p in parts.values():
        m, t, b = pack_mesh(p, pivots[p.group] if p.group else np.zeros(3))
        out['meshes'].append(m); tri += t; raw += b
    txt = 'window.AltayModels=window.AltayModels||{};AltayModels["as350"]=%s;\n' % json.dumps(out, separators=(',', ':'))
    open(OUT_JS, 'w', encoding='utf-8').write(txt)
    allP = np.vstack([np.concatenate(p.P).reshape(-1, 3) for p in parts.values()])
    print('габариты, м: %.2f × %.2f × %.2f' % tuple(allP.max(0) - allP.min(0)), '| несущий винт R=%.2f м, втулка' % R, hub.round(3), '| рулевой', tail_hub)
    print('мешей %d, треугольников %d, бинарно %.1f МБ → %s (%.1f МБ), атлас %s (%.1f МБ)' % (
        len(out['meshes']), tri, raw / 1e6, OUT_JS, os.path.getsize(OUT_JS) / 1e6, OUT_TEX, os.path.getsize(OUT_TEX) / 1e6))

if __name__ == '__main__':
    main()
