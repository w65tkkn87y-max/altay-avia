#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ливреи Ми-8АМТ (RA-24187) и Ми-171 (RA-25565) «АлтайАвиа» — по фото бортов компании (галерея сайта).
   Перекраска исходной текстуры Mi-8AMTSh (камуфляж, 4096 px) по 3D-координатам текселей, как в livery_as350.py:
   каждый треугольник растеризуется в пространстве текстуры, цвет выбирается по точке на фюзеляже (оси сайта:
   нос +X, верх +Y, правый борт +Z, земля y=0). Швы, лючки, заклёпки сохраняются (яркость относительно
   локальной медианы — края камуфляжных пятен и военные знаки при этом исчезают).
     python3 build/import/livery_mi8.py mi8amt   → build/import/mi8amt_texture.jpg
     python3 build/import/livery_mi8.py mi171    → build/import/mi171_texture.jpg
"""
import os, sys
import numpy as np
from PIL import Image, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mi8_geom, mi8_nose
from livery_as350 import rasterize, Visibility, Decal, text_image, flag_image, smoothstep, FONT_BOLD

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, 'build', 'import', 'mi8amtsh', 'scene.gltf')
TEX = os.path.join(ROOT, 'build', 'import', 'mi8amtsh', 'textures', 'wire_140088225_baseColor.png')

def hexc(h): h = h.lstrip('#'); return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], float)

# роли деталей (имена узлов модели бессмысленны — определены по габаритам и подсветке на рендере)
GEAR = {'object_056_0', 'object_057_0', 'object_058_0', 'object_059_0', 'object_060_0', 'object_061_0', 'object_062_0',
        'object_079_0', 'object_080_0', 'object_081_0', 'object_082_0', 'object_083_0', 'object_084_0', 'object_085_0'}
TANKS = {'object_007_0'}
PZU = {'object_009_0', 'object_010_0', 'object_067_0'}           # пылезащитные устройства перед двигателями
ROTORS = set(mi8_geom.MAIN_ROTOR) | set(mi8_geom.TAIL_ROTOR)
FRAMES = {'object_072_0', 'object_074_0'}                          # рамки окон кабины (верхние и нижние)
EXH_GRAD = [(0.0, '#B8864F'), (0.22, '#936038'), (0.5, '#5A3D29'), (0.78, '#2E231C'), (1.0, '#1A1512')]   # побежалость → копоть

# ---------------- Ми-8АМТ RA-24187: белый верх, голубой → синий низ, синяя балка, белый пилон ----------------
class Mi8AMT:
    name = 'mi8amt'
    white, light, deep = hexc('#F3F6F9'), hexc('#1A93E2'), hexc('#1541C4')
    gear = hexc('#1D4FC9'); pzu = hexc('#EEF1F4'); blade = hexc('#5A5E63')
    palette = {'strut': '#1D4FC9', 'tire': '#1B1C1F', 'hub': '#E6E9EC', 'frame': '#CDD2D8', 'rim': '#DDE1E5',
               'exh_metal': '#B3B7BB', 'exh_soot': '#1C1714', 'radome': '#F3F6F9'}
    silver = None    # окантовка остекления — нет (кабина белая)
    nose_windows = False   # у Ми-8АМТ нос — обтекатель радара, сплошной; нижнее окно только сбоку (штатный проём)
    # материал по деталям: (лак 0..1, шероховатость, металличность) → карта ORM для просмотрщика
    M = {'paint': (1.0, 0.36, 0.02), 'tank': (1.0, 0.36, 0.02), 'frame': (1.0, 0.36, 0.02), 'pzu': (0.5, 0.32, 0.35), 'rotor': (0.0, 0.55, 0.25),
         'strut': (1.0, 0.4, 0.02), 'tire': (0.0, 0.92, 0.0), 'hub': (0.4, 0.3, 0.6), 'glass_frame': (0.4, 0.3, 0.6), 'rim': (0.4, 0.3, 0.6),
         'exh_metal': (0.0, 0.42, 0.75), 'exh_soot': (0.0, 0.95, 0.0), 'radome': (1.0, 0.36, 0.02)}
    def boundary(self, x):
        """Высота границы белого и синего вдоль фюзеляжа."""
        nose = 2.36 - 0.26 * smoothstep(3.4, 5.9, x)                        # под остеклением кабины
        cab = np.full_like(x, 2.46)                                          # вдоль двери и окон
        rise = 2.46 + (4.05 - 2.46) * smoothstep(0.7, -4.2, x) ** 1.25        # за окнами «волна» уходит вверх к балке
        return np.where(x >= 3.4, nose, np.where(x >= 0.7, cab, rise))
    def body(self, P, N):
        x, y = P[:, 0], P[:, 1]
        yb = self.boundary(x)
        d = yb - y
        t_blue = np.clip(d / 0.015, 0, 1)
        t_deep = smoothstep(0.12, 0.75, d)
        blue = self.light[None] * (1 - t_deep[:, None]) + self.deep[None] * t_deep[:, None]
        col = self.white[None] * (1 - t_blue[:, None]) + blue * t_blue[:, None]
        tail = x < -11.05 + 0.55 * (y - 3.6)                                 # пилон рулевого винта — белый, граница по диагонали
        col[tail] = self.white
        return col
    def decals(self):
        reg = text_image('RA-24187', (246, 248, 250), tracking=0.03)
        flag = flag_image(); typ = text_image('Ми-8АМТ', (20, 22, 26), tracking=0.02)
        return [Decal(reg, -5.15, -8.25, 3.42, +1, nz=0.5), Decal(reg, -5.15, -8.25, 3.42, -1, nz=0.5),
                Decal(flag, 1.55, 0.98, 3.64, +1, height=0.38), Decal(flag, 1.55, 0.98, 3.64, -1, height=0.38),
                Decal(typ, 3.72, 3.12, 2.58, +1, zmax=1.2), Decal(typ, 3.72, 3.12, 2.58, -1, zmax=1.2)]   # zmax — не на обтекатель выше
    tank = None      # баки — как фюзеляж (синие)

# ---------------- Ми-171 RA-25565 (VIP): вишнёвый металлик, серебристая линия, бронзовые баки ----------------
class Mi171:
    name = 'mi171'
    body_c = hexc('#3B1618'); stripe = hexc('#C8CCD1')
    gear = hexc('#3B191C'); pzu = hexc('#C9CED4'); blade = hexc('#4E5257'); tank = hexc('#5C4636')
    palette = {'strut': '#3B191C', 'tire': '#1B1C1F', 'hub': '#A08C78', 'frame': '#B4BAC1', 'rim': '#C8CCD1',
               'exh_metal': '#5E3A33', 'exh_soot': '#1C1714', 'radome': '#3B1618'}
    silver = hexc('#A9AFB6')     # серебристая окантовка всего остекления кабины (рамки, стойки)
    nose_windows = True          # остекление почти всей кабины, внизу по центру — обтекатель радара
    # «вишня металлик» под лаком, бронзовые баки (металл), серебристые рамки, матовая резина
    M = {'paint': (1.0, 0.4, 0.22), 'tank': (0.6, 0.4, 0.55), 'frame': (0.7, 0.3, 0.75), 'pzu': (0.5, 0.34, 0.35), 'rotor': (0.0, 0.55, 0.25),
         'strut': (1.0, 0.4, 0.2), 'tire': (0.0, 0.92, 0.0), 'hub': (0.5, 0.32, 0.7), 'glass_frame': (0.6, 0.26, 0.85), 'rim': (0.6, 0.26, 0.85),
         'exh_metal': (0.4, 0.34, 0.5), 'exh_soot': (0.0, 0.95, 0.0), 'radome': (1.0, 0.3, 0.45)}
    def line_y(self, x):
        return np.where(x > 3.55, 1.84 - 0.24 * smoothstep(3.55, 5.85, x), 1.84)
    def body(self, P, N):
        x, y = P[:, 0], P[:, 1]
        col = np.repeat(self.body_c[None], len(P), 0)
        side = np.abs(N[:, 2]) > 0.3
        dl = np.abs(y - self.line_y(x))
        a = np.clip((0.02 - dl) / 0.006, 0, 1) * side * smoothstep(-3.6, -3.0, x) * (x < 5.8)
        col = col * (1 - a[:, None]) + self.stripe[None] * a[:, None]
        return col
    def decals(self):
        # по фото борта: номер крупнее (высота букв ≈0,30 м, длина 2 м), центр — под антенной на балке (x≈−6),
        # флаг отдельно, ближе к хвосту, с просветом ≈0,7 м; оба — чуть выше середины балки
        reg = text_image('RA-25565', (246, 248, 250), tracking=0.03)
        flag = flag_image()
        return [Decal(reg, -5.0, -7.0, 3.35, +1, nz=0.5), Decal(reg, -5.0, -7.0, 3.35, -1, nz=0.5),
                Decal(flag, -7.64, -8.10, 3.37, +1, height=0.31), Decal(flag, -7.64, -8.10, 3.37, -1, height=0.31)]

LIVERIES = {'mi8amt': Mi8AMT(), 'mi171': Mi171()}

def frame_band(P, loops, width, soft):
    """Доля окраски полосы вокруг контуров: 1 ближе width к ломаной, мягкий край soft (только возле кабины)."""
    A = np.vstack([q for q in loops]); B = np.vstack([np.roll(q, -1, 0) for q in loops])
    lo, hi = np.minimum(A, B).min(0) - width - soft, np.maximum(A, B).max(0) + width + soft
    near = np.all((P > lo) & (P < hi), 1)
    out = np.zeros(len(P)); idx = np.where(near)[0]
    AB = B - A; L2 = np.maximum((AB ** 2).sum(1), 1e-12)
    for k in range(0, len(idx), 4000):
        Q = P[idx[k:k + 4000]]
        t = np.clip(((Q[:, None, :] - A[None]) * AB[None]).sum(-1) / L2[None], 0, 1)
        d = np.linalg.norm(Q[:, None, :] - (A[None] + t[..., None] * AB[None]), axis=-1).min(1)
        out[idx[k:k + 4000]] = np.clip((width + soft - d) / soft, 0, 1)
    return out

# зоны военной маркировки исходника («52», звезда, «ВВС РОССИИ», знак на балке) — там швы не переносим, иначе проступают контуры
ERASE = [(-3.75, -2.35, 1.95, 2.95), (-0.95, 0.55, 2.75, 3.45), (-8.6, -5.6, 3.15, 3.75), (-10.2, -9.2, 3.3, 3.75)]
def erase_mask(P):
    m = np.zeros(len(P), bool)
    for x0, x1, y0, y1 in ERASE: m |= (P[:, 0] > x0) & (P[:, 0] < x1) & (P[:, 1] > y0) & (P[:, 1] < y1)
    return m

def detail_map(src):
    """Яркость относительно локальной медианы 5 px: швы и заклёпки сохраняются, края пятен камуфляжа — нет."""
    lum = (0.299 * src[..., 0] + 0.587 * src[..., 1] + 0.114 * src[..., 2]).astype(np.float32)
    med = np.array(Image.fromarray(np.clip(lum, 0, 255).astype(np.uint8)).filter(ImageFilter.MedianFilter(5)), np.float32)
    return np.clip(lum / np.maximum(med, 12), 0.6, 1.12), lum

def main(key):
    L = LIVERIES[key]
    G = mi8_geom.load(SRC)
    src = np.array(Image.open(TEX).convert('RGB')); H, W = src.shape[:2]
    # треугольники: позиции/нормали по углам и UV (glTF: v от верха → для rasterize переводим к v от низа)
    groups = {}
    occ = []
    for g, P, N, UV, I in G['prims']:
        T = I.reshape(-1, 3)
        tris = [(P[t], N[t], np.stack([UV[t, 0], 1.0 - UV[t, 1]], -1)) for t in T]
        groups.setdefault(g, []).extend(tris)
        if g not in ROTORS: occ.extend(P[t] for t in T)
    print('треугольников: %d, групп: %d' % (sum(len(v) for v in groups.values()), len(groups)))
    vis = Visibility(occ, px=0.02, eps=0.05)
    all_tris = []; role = []
    for g, tris in groups.items():
        r = ('rotor' if g in ROTORS else 'gear' if g in GEAR else 'tank' if g in TANKS else 'pzu' if g in PZU else
             'frame' if g in FRAMES else 'skin' if g in mi8_geom.SKIN else 'body')
        all_tris.extend(tris); role.extend([r] * len(tris))
    # растеризация по ролям (карта «какая роль у текселя»)
    role_map = np.zeros((H, W), np.uint8); ROLE = {'body': 1, 'tank': 2, 'gear': 3, 'pzu': 4, 'rotor': 5, 'skin': 6, 'frame': 7}
    pos = np.zeros((H, W, 3), np.float32); nrm = np.zeros((H, W, 3), np.float32); cov = np.zeros((H, W), bool)
    for r in ROLE:
        sub = [t for t, rr in zip(all_tris, role) if rr == r]
        if not sub: continue
        p, n, c = rasterize(W, H, sub, vis)
        pos[c] = p[c]; nrm[c] = n[c]; cov |= c; role_map[c] = ROLE[r]
        print('  %-5s треугольников %7d, текселей %8d' % (r, len(sub), c.sum()))
    np.save(os.path.join(ROOT, 'build', 'import', '_mi8_cov.npy'), np.packbits(cov))
    detail, lum = detail_map(src)
    out = src.astype(np.float32)
    dark = lum < 28                                                   # отверстия, решётки, резина — не красим
    # фюзеляж (обшивка + прочие детали)
    sel = cov & np.isin(role_map, (1, 6, 7)) & ~dark
    P = pos[sel].astype(float); Nn = nrm[sel].astype(float)
    col = L.body(P, Nn)
    for d in L.decals(): col = d.apply(col, P, Nn)
    # под нижними стёклами носа (у исходника там глухая обшивка) — тёмный «салон», стекло над ним прозрачное
    dk = (mi8_nose.inside(P) & (role_map[sel] == 6)) if L.nose_windows else np.zeros(len(P), bool)
    col[dk] = hexc('#1B2024')
    if L.silver is not None:
        # серебристая окантовка остекления: полоса ≈6 см вокруг каждого проёма (стойки между стёклами — целиком)
        rm = role_map[sel]
        a = frame_band(P, mi8_geom.cockpit_loops(G) + (mi8_nose.outlines(G) if L.nose_windows else []), 0.06, 0.008) * (rm == 6) * ~dk
        a = np.maximum(a, (rm == 7).astype(float))
        col = col * (1 - a[:, None]) + L.silver[None] * a[:, None]
    det = detail[sel].copy(); det[erase_mask(P)] = np.clip(det[erase_mask(P)], 0.97, 1.03)
    out[sel] = col * det[:, None]
    # баки
    sel = cov & (role_map == 2) & ~dark
    if L.tank is None:
        P = pos[sel].astype(float); col = L.body(P, nrm[sel].astype(float))
    else:
        col = np.repeat(L.tank[None], sel.sum(), 0)
    out[sel] = col * detail[sel][:, None]
    # шасси: стойки в цвет ливреи, шины остаются тёмными
    sel = cov & (role_map == 3) & (lum > 45)
    out[sel] = L.gear[None] * detail[sel][:, None]
    # ПЗУ
    sel = cov & (role_map == 4) & ~dark
    out[sel] = L.pzu[None] * detail[sel][:, None]
    # винты: серые лопасти (без жёлтых законцовок), детали втулки — по яркости исходника
    sel = cov & (role_map == 5)
    g = (lum[sel] / 110.0)[:, None]
    out[sel] = np.clip(L.blade[None] * np.clip(g, 0.55, 1.5), 0, 255)
    # затенение (AO): щели, днище над баками, ниши шасси, воздухозаборники — по геометрии всей модели (кроме винтов)
    import bake_ao
    aomask = cov & (role_map != 5)
    ao = bake_ao.bake(pos, nrm, aomask, occ)
    f = np.clip(ao / 0.9, 0, 1) ** 1.1
    out[aomask] *= (0.36 + 0.64 * f[aomask])[:, None]
    print('  AO: среднее %.2f, доля затенённых (<0.6) %.1f%%' % (ao[aomask].mean(), 100 * (ao[aomask] < 0.6).mean()))
    # карта материалов ORM: R — лак, G — шероховатость, B — металличность
    orm = np.zeros((H, W, 3), np.float32); orm[:] = (0, 0.8, 0)
    for rid, mk in ((1, 'paint'), (6, 'paint'), (7, 'frame'), (2, 'tank'), (3, 'strut'), (4, 'pzu'), (5, 'rotor')):
        orm[cov & (role_map == rid)] = L.M[mk]
    orm[cov & dark & (role_map != 5)] = (0, 0.85, 0)                  # решётки, отверстия, резина исходника
    for name in L.palette:
        x0, y0, x1, y1 = mi8_geom.pal_rect(name); orm[y0:y1, x0:x1] = L.M['glass_frame' if name == 'frame' else name]
    ex0, ey0, ew, eh = mi8_geom.EXH_STRIP; tt = (np.arange(ew) - 4) / (ew - 8)
    orm[ey0:ey0 + eh, ex0:ex0 + ew] = np.stack([np.zeros(ew), 0.45 + 0.5 * tt, 0.6 * (1 - tt)], -1)[None]
    Image.fromarray(np.clip(orm[::2, ::2] * 255, 0, 255).astype(np.uint8)).save(os.path.join(ROOT, 'build', 'import', key + '_orm.png'), optimize=True)
    # палитра (шасси, рамки окон, патрубки, обтекатель) — в свободном углу атласа
    for name, hx in L.palette.items():
        x0, y0, x1, y1 = mi8_geom.pal_rect(name); out[y0:y1, x0:x1] = hexc(hx)
    x0, y0, w, h = mi8_geom.EXH_STRIP                      # градиент внутренней поверхности выхлопных патрубков
    t = (np.arange(w) - 4) / (w - 8)
    ts = np.array([k for k, _ in EXH_GRAD]); cs = np.array([hexc(c) for _, c in EXH_GRAD])
    grad = np.stack([np.interp(t, ts, cs[:, i]) for i in range(3)], -1)
    out[y0:y0 + h, x0:x0 + w] = grad[None]
    img = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))
    dst = os.path.join(ROOT, 'build', 'import', key + '_texture.jpg')
    img.save(dst, quality=90); print('записано', dst)

if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'mi8amt')
