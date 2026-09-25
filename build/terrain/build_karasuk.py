#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Сцена «Карасук» (вертолётная площадка «АлтайАвиа», с. Чепош, долина Катуни) для 3D-просмотра на сайте.
   Данные (build/terrain/fetch_tiles.py): рельеф AWS Terrain Tiles (SRTM и др.), снимок Sentinel-2 cloudless 2016
   (EOX, s2maps.eu, CC BY 4.0). Планировка базы (ангары, перрон, рулёжки, площадки) — по спутниковому снимку и фото.
   Выход:
     site/scene/karasuk.js       — window.AltayScenes.karasuk: сетка высот, деревья, постройки, разметка
     site/scene/karasuk_sat.jpg  — снимок ±9 км (4096 px; _2k — 2048 px для телефонов)
     site/scene/karasuk_near.jpg — ближняя текстура базы ±400 м (2048 px)
     site/scene/karasuk_water.png — маска воды (Катунь) ±9 км
   Оси: x — восток, z — юг, y — вверх, метры; начало — центр площадки P3.
   python3 build/terrain/build_karasuk.py"""
import base64, json, math, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import geo

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, 'site', 'scene')
R = 9000.0            # радиус сцены, м
N = 321               # вершин сетки по стороне
A = 0.18              # «сгущение» сетки к центру: x(u) = R·(A·u + (1−A)·u³)
NEAR = 400.0          # полуразмер ближней текстуры, м
H0 = float(geo.height(0.0, 0.0))
rng = np.random.default_rng(20260922)

def smoothstep(e0, e1, x):
    t = np.clip((np.asarray(x, float) - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t)

def warp(u): return R * (A * u + (1 - A) * u ** 3)

def blur(a, sigma):
    """Гауссово размытие 2D-массива (float) — разделимая свёртка numpy."""
    r = int(3 * sigma + 1); k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2); k /= k.sum()
    a = np.pad(a, r, mode='edge')
    a = np.apply_along_axis(lambda v: np.convolve(v, k, 'valid'), 0, a)
    return np.apply_along_axis(lambda v: np.convolve(v, k, 'valid'), 1, a)

# ---------------- планировка базы (координаты P3; по снимку 0.74 м/px и фото) ----------------
# ангары: x0, x1 (запад→восток), z0, z1 (север→юг), высота, тип фасада (фасад — восточная стена к перрону)
FACADE_X = -88.0        # все ангары фасадами (восточная стена) на одной линии
HANGARS = [
    dict(name='north', x=(-110, FACADE_X), z=(-116, -90), h=9.0, kind='dark', doors=[(0.5, 12.0, 6.5)]),
    dict(name='long', x=(-108, FACADE_X), z=(-80, -21), h=8.5, kind='white', doors=[(0.12, 4.2, 4.6), (0.25, 4.2, 4.6), (0.38, 4.2, 4.6), (0.6, 13.0, 6.2), (0.85, 4.2, 4.6)]),
    dict(name='small', x=(-106, FACADE_X), z=(-21, -4), h=7.0, kind='white', doors=[(0.35, 4.5, 4.6), (0.72, 4.5, 4.6)]),
    dict(name='south', x=(-115, FACADE_X), z=(0, 36), h=11.5, kind='white', doors=[(0.28, 13.0, 7.4), (0.72, 13.0, 7.4)], step=True),
]
APRON = dict(x=(FACADE_X, -54), z=(-123, 40))
# площадки — в одну линию по x=0, рулёжка — строго по меридиану x=−14, отводы — под прямым углом
TAXI_X = -14.0
PADS = [dict(x=0, z=-113, s=16, kind='H'), dict(x=0, z=-58, s=14, kind='H'), dict(x=0, z=0, s=20, kind='big'),
        dict(x=0, z=56, s=12, kind='H'), dict(x=0, z=110, s=12, kind='H')]
TAXIWAYS = [((TAXI_X, -118), (TAXI_X, 115), 5.0),                           # магистральная рулёжка
            ((-54, -115), (TAXI_X, -115), 5.0), ((-54, 0), (-10, 0), 6.0)]  # отводы с перрона
TAXIWAYS += [((TAXI_X, p['z']), (-p['s'] / 2, p['z']), 4.0) for p in PADS if p['kind'] != 'big']
ROAD = [(-141, -2000), (-139, -300), (-136, 0), (-134, 300), (-128, 900), (-110, 2000)]   # Чуйский тракт (≈ меридиан)
PARKING = dict(x=(-102, -77), z=(70, 97))
BROWN = dict(x=(20, 51), z=(-146, 52))                 # полоса восточнее площадок (сенокос; на снимке — другой оттенок)
# постройки кроме ангаров — только два дома у стоянки (как на снимке); посёлок не строим
SMALL_BUILDINGS = [dict(x=(-112, -104), z=(80, 94), h=5.0, roof='#8a3b2e'), dict(x=(-74, -66), z=(99, 106), h=3.4, roof='#3a4048')]
CARS = [dict(x=-98.4, z=74.0, r=1.5708, c='#e8e9eb'), dict(x=-98.4, z=79.2, r=1.5708, c='#26292e'), dict(x=-80.6, z=86.9, r=-1.5708, c='#8a1f23')]
WINDSOCK = (26, -30)

def road_x(z):
    zs = np.array([p[1] for p in ROAD], float); xs = np.array([p[0] for p in ROAD], float)
    return np.interp(z, zs, xs)

def base_mask(x, z, pad=70.0):
    """1 — территория базы (плоско, без леса), плавно 0 за её пределами."""
    return smoothstep(-190 - pad, -190, x) * smoothstep(150 + pad, 150, x) * smoothstep(-300 - pad, -300, z) * smoothstep(230 + pad, 230, z)

# ---------------- снимок: цветокоррекция под фото (S2 2016 тёмный и «ядовито-зелёный») ----------------
def grade(rgb):
    """S2 2016 → ближе к фото: тёмный хвойный лес, светлые луга, тёплая зелень, локальный контраст (рисунок леса)."""
    a = np.clip(rgb / 255.0 * 1.6, 0, 1) ** 0.9
    a = a * np.array([1.08, 0.97, 0.72])                         # к жёлто-зелёной, без «бирюзы»
    out = np.clip(a * 255, 0, 255)
    lum = out.mean(-1)
    bl = blur(lum, 5.0)
    out = out + (0.45 * (lum - bl))[..., None]                   # локальный контраст: кроны, поляны, тени склонов
    return np.clip(out, 0, 255)

def sat_texture(size):
    s2 = geo.Mosaic('s2', 14)
    xs = (np.arange(size) + 0.5) / size * 2 * R - R
    out = np.zeros((size, size, 3), np.float32)
    for j0 in range(0, size, 256):
        zz, xx = np.meshgrid(xs[j0:j0 + 256], xs, indexing='ij')
        lat, lon = geo.to_latlon(xx, zz); out[j0:j0 + 256] = s2.sample(lat, lon)
    return out

def water_mask(raw, size):
    """Катунь на снимке — серо-бирюзовая: светлее леса, синий ≈ зелёному, низкая насыщенность; плюс дно долины по рельефу."""
    a = raw.astype(np.float32); r, g, b = a[..., 0], a[..., 1], a[..., 2]
    lum = 0.299 * r + 0.587 * g + 0.114 * b; sat = a.max(-1) - a.min(-1)
    w = ((lum > 70) & (b > r + 6) & (sat < 45)).astype(np.float32)      # Катунь на S2: (69,100,85) — светлая, серо-зелёная
    xs = (np.arange(size) + 0.5) / size * 2 * R - R
    zz, xx = np.meshgrid(xs, xs, indexing='ij')
    h = geo.height(xx, zz) - H0
    w *= (h < -4.0)                                              # вода только в русле (ниже террасы)
    img = Image.fromarray((w * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(1.2))
    return np.array(img, np.float32) / 255.0

# ---------------- маска леса (по снимку лес и луг одной яркости — нужна крутизна и фактура) ----------------
def forest_mask(raw, size, water):
    """Лес на S2 (замеры по точкам): темнее поля (яркость ~42–48 против ~55), синевато-зелёный (g−b 7–10 против 12–15),
       зернистый от крон (разброс 2.7–3.4 против 1.2); плюс крутизна — склоны долины почти сплошь в тайге."""
    a = raw.astype(np.float64); r, g, b = a[..., 0], a[..., 1], a[..., 2]
    lum = a.mean(-1)
    m1 = blur(lum, 2.0); m2 = blur(lum ** 2, 2.0); std = np.sqrt(np.maximum(m2 - m1 ** 2, 0))
    gb = blur(g - b, 2.0)
    xs = (np.arange(size) + 0.5) / size * 2 * R - R
    zz, xx = np.meshgrid(xs, xs, indexing='ij')
    h = geo.height(xx, zz); px = 2 * R / size
    hb = blur(h, 2.0); gz, gx = np.gradient(hb, px); slope = np.hypot(gx, gz)
    f = 0.35 * smoothstep(52, 40, m1) + 0.25 * smoothstep(14, 8, gb) + 0.25 * smoothstep(1.5, 3.0, std) + 0.35 * smoothstep(0.10, 0.28, slope)
    n = blur(np.random.default_rng(4).random((size, size)), 14.0); n = (n - n.min()) / (n.max() - n.min())
    f = f - 0.3 * smoothstep(0.6, 0.8, n)                                            # поляны и прогалины
    f = f * (1 - water) * (1 - base_mask(xx, zz, pad=160))
    return np.clip(smoothstep(0.38, 0.62, f), 0, 1)

# ---------------- сетка высот ----------------
def heights(water, wsize):
    u = np.linspace(-1, 1, N); xs = warp(u)
    zz, xx = np.meshgrid(xs, xs, indexing='ij')
    h = geo.height(xx, zz) - H0
    # сглаживание шума SRTM на дне долины: вспомогательный растр 10 м ±1.6 км
    L = 1600.0; M = 321; g = np.linspace(-L, L, M)
    gz, gx = np.meshgrid(g, g, indexing='ij'); hg = geo.height(gx, gz) - H0
    hs = blur(hg.astype(np.float64), 3)
    inner = (np.abs(xx) < L) & (np.abs(zz) < L)
    ix = np.clip(((xx + L) / (2 * L) * (M - 1)), 0, M - 1); iz = np.clip(((zz + L) / (2 * L) * (M - 1)), 0, M - 1)
    x0 = np.floor(ix).astype(int).clip(0, M - 2); z0 = np.floor(iz).astype(int).clip(0, M - 2); fx = ix - x0; fz = iz - z0
    hsv = hs[z0, x0] * (1 - fx) * (1 - fz) + hs[z0, x0 + 1] * fx * (1 - fz) + hs[z0 + 1, x0] * (1 - fx) * fz + hs[z0 + 1, x0 + 1] * fx * fz
    slope = np.hypot(np.gradient(hs, axis=0), np.gradient(hs, axis=1)) / 10.0
    sl = slope[z0, x0]
    w_s = np.where(inner, smoothstep(0.12, 0.05, sl), 0.0)       # пологие места — сглаженный рельеф
    h = h * (1 - w_s) + hsv * w_s
    # вода: ровная поверхность чуть ниже берегов
    wi = np.clip(((xx + R) / (2 * R) * (wsize - 1)).astype(int), 0, wsize - 1); wj = np.clip(((zz + R) / (2 * R) * (wsize - 1)).astype(int), 0, wsize - 1)
    wv = water[wj, wi]
    h = np.where((wv > 0.35) & inner, np.minimum(h, hsv - 0.6), h)
    # территория базы — строго плоская (y = 0)
    bm = base_mask(xx, zz)
    h = h * (1 - bm)
    return xs, h

# ---------------- ближняя текстура базы (±400 м, 2048 px ≈ 0.39 м/px) ----------------
def fbm(size, octaves, seed, base=64):
    r = np.random.default_rng(seed); acc = np.zeros((size, size), np.float32); amp = 1.0; tot = 0
    for o in range(octaves):
        n = base * 2 ** o
        if n > size: break
        s = r.random((n, n)).astype(np.float32)
        acc += amp * np.array(Image.fromarray(s, 'F').resize((size, size), Image.BICUBIC)); tot += amp; amp *= 0.55
    return acc / tot

def near_texture(sat_graded, size=2048):
    px = 2 * NEAR / size
    xs = (np.arange(size) + 0.5) * px - NEAR
    zz, xx = np.meshgrid(xs, xs, indexing='ij')
    # основа — снимок (для окрестностей: посёлок, поля)
    S = sat_graded.shape[0]
    si = ((xx + R) / (2 * R) * S).astype(int).clip(0, S - 1); sj = ((zz + R) / (2 * R) * S).astype(int).clip(0, S - 1)
    base = sat_graded[sj, si]
    base = np.array(Image.fromarray(base.astype(np.uint8)).filter(ImageFilter.GaussianBlur(3)), np.float32)
    n1 = fbm(size, 6, 1, 16); n2 = fbm(size, 5, 2, 128); n3 = fbm(size, 3, 3, 512)
    # трава поверх снимка: модуляция яркости/оттенка (без подмены цвета — нет видимой рамки), полосы покоса на поле
    grassmod = (0.84 + 0.32 * n2) * (0.92 + 0.16 * n3)
    stripes = 0.5 + 0.5 * np.sign(np.sin(xx / 5.0 * math.pi))
    field = smoothstep(-40, -30, xx) * smoothstep(420, 380, xx) * base_mask(xx, zz, pad=120)
    grassmod = grassmod * (1 + 0.08 * (stripes - 0.5) * field)
    img = base * grassmod[..., None]
    # на территории базы трава ухоженнее и свежее (как на фото), с сухими проплешинами
    fresh = np.stack([108 + 30 * n1, 138 + 30 * n1, 64 + 14 * n1], -1) * grassmod[..., None]
    bm = (base_mask(xx, zz, pad=110) * (0.75 + 0.25 * n1))[..., None]
    img = img * (1 - bm * 0.6) + fresh * bm * 0.6
    dry = (smoothstep(0.64, 0.8, n1) * base_mask(xx, zz, pad=60))[..., None]
    img = img * (1 - dry * 0.35) + np.array([150, 142, 92]) * dry * 0.35
    # полоса сосен: тёмная подстилка
    pines = smoothstep(-205, -190, xx) * smoothstep(-128, -140, xx)
    img = img * (1 - pines[..., None] * 0.55) + np.array([62, 72, 44]) * pines[..., None] * 0.55
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)); d = ImageDraw.Draw(im)
    def P(x, z): return ((x + NEAR) / px, (z + NEAR) / px)
    def rect(x0, x1, z0, z1, fill): d.rectangle([P(x0, z0), P(x1, z1)], fill=fill)
    # распаханная полоса
    rect(BROWN['x'][0], BROWN['x'][1], BROWN['z'][0], BROWN['z'][1], (128, 138, 78))     # сенокос — желтовато-зелёный
    # дорога, обочины, разметка
    zline = np.linspace(-NEAR, NEAR, 400); xline = road_x(zline)
    for w, col in ((13.0, (150, 140, 118)), (9.0, (78, 80, 82))):
        pts_l = [P(x - w / 2, z) for x, z in zip(xline, zline)]; pts_r = [P(x + w / 2, z) for x, z in zip(xline, zline)][::-1]
        d.polygon(pts_l + pts_r, fill=col)
    for off in (-4.1, 4.1):
        d.line([P(x + off, z) for x, z in zip(xline, zline)], fill=(215, 215, 208), width=max(1, int(0.16 / px)))
    for k in range(0, len(zline) - 1, 4):
        d.line([P(xline[k], zline[k]), P(xline[k + 1], zline[k + 1])], fill=(225, 225, 215), width=max(1, int(0.14 / px)))
    # стоянка, перрон, рулёжки, площадки (бетон; крупная разметка — отдельными мешами в браузере)
    rect(PARKING['x'][0], PARKING['x'][1], PARKING['z'][0], PARKING['z'][1], (88, 88, 88))
    rect(APRON['x'][0], APRON['x'][1], APRON['z'][0], APRON['z'][1], (176, 172, 162))
    for (x0, z0), (x1, z1), w in TAXIWAYS:
        d.line([P(x0, z0), P(x1, z1)], fill=(170, 166, 155), width=int(w / px))
    for p in PADS:
        s = p['s'] / 2; rect(p['x'] - s, p['x'] + s, p['z'] - s, p['z'] + s, (178, 174, 164))
    # отмостки у ангаров и дорожка вдоль них
    for hg in HANGARS: rect(hg['x'][0] - 3, hg['x'][1] + 1, hg['z'][0] - 2, hg['z'][1] + 2, (150, 147, 140))
    out = np.array(im, np.float32)
    # мелкая «зернистость» по всему (бетон, земля)
    out *= (0.94 + 0.12 * n3)[..., None]
    return np.clip(out, 0, 255).astype(np.uint8)

# ---------------- деревья ----------------
PINE, SPRUCE, BIRCH = 0, 1, 2
def trees(forest, sat_size, water, xs_grid, hgrid):
    """Позиции деревьев: по маске леса (крутизна + фактура + тень) + полоса сосен вдоль тракта."""
    def f_at(x, z):
        i = ((x + R) / (2 * R) * sat_size).astype(int).clip(0, sat_size - 1); j = ((z + R) / (2 * R) * sat_size).astype(int).clip(0, sat_size - 1)
        return forest[j, i], water[(j * water.shape[0] // sat_size), (i * water.shape[0] // sat_size)]
    def h_at(x, z):
        # высота по сетке (билинейно по неравномерной сетке)
        ix = np.interp(x, xs_grid, np.arange(N)); iz = np.interp(z, xs_grid, np.arange(N))
        x0 = np.floor(ix).astype(int).clip(0, N - 2); z0 = np.floor(iz).astype(int).clip(0, N - 2); fx = ix - x0; fz = iz - z0
        return hgrid[z0, x0] * (1 - fx) * (1 - fz) + hgrid[z0, x0 + 1] * fx * (1 - fz) + hgrid[z0 + 1, x0] * (1 - fx) * fz + hgrid[z0 + 1, x0 + 1] * fx * fz
    pts = []
    for r0, r1, cell, dens in ((0, 450, 7.5, 0.85), (450, 1200, 9.0, 0.95), (1200, 1900, 11.0, 0.95)):
        n = int(2 * r1 / cell)
        gx, gz = np.meshgrid((np.arange(n) + 0.5) * cell - r1, (np.arange(n) + 0.5) * cell - r1)
        gx = gx.ravel() + rng.uniform(-0.45, 0.45, gx.size) * cell; gz = gz.ravel() + rng.uniform(-0.45, 0.45, gz.size) * cell
        d = np.hypot(gx, gz); m = (d >= r0) & (d < r1)
        gx, gz = gx[m], gz[m]
        f, w = f_at(gx, gz)
        keep = (rng.random(gx.size) < f * dens) & (w < 0.2) & (base_mask(gx, gz, pad=25) < 0.05)
        pts.append(np.stack([gx[keep], gz[keep]], -1))
    # полоса высоких сосен между трактом и базой, и вдоль тракта (как на аэрофото)
    zs = np.arange(-420, 420, 6.5)
    for xa, xb in ((-205, -146), (-130, -120)):
        for zz_ in zs:
            for xx_ in np.arange(xa, xb, 7.0):
                if rng.random() < 0.82: pts.append(np.array([[xx_ + rng.uniform(-2, 2), zz_ + rng.uniform(-2, 2)]]))
    P = np.vstack(pts)
    # вид и высота; на склонах гор деревьев нет (лес там — полог в шейдере рельефа)
    x, z = P[:, 0], P[:, 1]; y = h_at(x, z)
    flat = ((x < -118) & (x > -210) & (np.abs(z) < 430)) | (y < 12.0)
    P, x, z, y = P[flat], x[flat], z[flat], y[flat]
    d = np.hypot(x, z)
    strip = (x < -118) & (x > -210) & (np.abs(z) < 430)
    rr = rng.random(len(P))
    # по фото: на террасе и в излучине — сосняк с берёзой, на склонах — сосна и темнохвойные (ель, пихта, кедр)
    kind = np.where(strip, np.where(rr < 0.88, PINE, BIRCH),
                    np.where(y > 260, np.where(rr < 0.7, SPRUCE, PINE),
                             np.where(y > 25, np.where(rr < 0.5, PINE, np.where(rr < 0.88, SPRUCE, BIRCH)),
                                      np.where(rr < 0.55, PINE, np.where(rr < 0.8, BIRCH, SPRUCE)))))
    height = np.where(kind == PINE, rng.uniform(17, 27, len(P)), np.where(kind == SPRUCE, rng.uniform(13, 24, len(P)), rng.uniform(11, 19, len(P))))
    height = np.where(strip & (kind == PINE), rng.uniform(22, 30, len(P)), height)
    print('деревьев: %d (сосна %d, ель/кедр %d, берёза %d)' % (len(P), (kind == PINE).sum(), (kind == SPRUCE).sum(), (kind == BIRCH).sum()))
    arr = np.stack([np.round(x * 10), np.round(z * 10), np.round(y * 10), (kind.astype(int) << 12) | np.round(height * 10).astype(int)], -1).astype('<i2')
    return arr

# ---------------- посёлок: коттеджи восточнее и южнее базы ----------------
def houses(hgrid, xs_grid):
    H = []
    # южный посёлок (по снимку — плотная застройка к югу/юго-востоку)
    for zz_ in np.arange(245, 470, 26):
        for xx_ in np.arange(-70, 330, 24):
            if rng.random() < 0.62: H.append((xx_ + rng.uniform(-5, 5), zz_ + rng.uniform(-5, 5)))
    # восточные участки (редкие дома)
    for zz_ in np.arange(-300, 100, 55):
        for xx_ in np.arange(150, 420, 50):
            if rng.random() < 0.3: H.append((xx_ + rng.uniform(-8, 8), zz_ + rng.uniform(-8, 8)))
    out = []
    for x, z in H:
        w = rng.uniform(7, 11); l = rng.uniform(8, 13); h = rng.uniform(3.2, 6.5); rot = rng.choice([0, 0, math.pi / 2]) + rng.uniform(-0.08, 0.08)
        roof = rng.choice(['#8a3b2e', '#7a3328', '#4d5560', '#6b4a3a', '#2f5fa8', '#8f2a2a', '#5b6b3a'])
        out.append(dict(x=round(x, 1), z=round(z, 1), w=round(w, 1), l=round(l, 1), h=round(h, 1), r=round(rot, 3), roof=roof))
    print('домов:', len(out))
    return out

def main():
    os.makedirs(OUT, exist_ok=True)
    SAT = 4096
    print('снимок...'); raw = sat_texture(SAT)
    graded = grade(raw)
    print('вода...'); water = water_mask(raw, SAT)
    WS = 1024
    wsmall = np.array(Image.fromarray((water * 255).astype(np.uint8)).resize((WS, WS), Image.LANCZOS), np.float32) / 255
    # на снимке вода — тусклая: подкрашиваем бирюзой Катуни (как на фото туров)
    wcol = np.array([96, 152, 150], np.float32)
    graded = graded * (1 - water[..., None] * 0.65) + wcol * water[..., None] * 0.65
    print('рельеф...'); xs, h = heights(wsmall, WS)
    print('  высоты: %.0f … %.0f м относительно площадки (%.0f м над морем)' % (h.min(), h.max(), H0))
    print('ближняя текстура...'); near = near_texture(graded)
    print('лес...'); forest = forest_mask(raw, SAT, water)
    print('  лесистость: %.0f%% площади' % (100 * forest.mean()))
    print('деревья...'); tr = trees(forest, SAT, wsmall, xs, h)
    fsmall = np.array(Image.fromarray((forest * 255).astype(np.uint8)).resize((WS, WS), Image.LANCZOS), np.float32) / 255
    hs = []                                                   # посёлок не строим (по просьбе заказчика)
    Image.fromarray(graded.astype(np.uint8)).save(os.path.join(OUT, 'karasuk_sat.jpg'), quality=82, optimize=True, progressive=True)
    Image.fromarray(graded.astype(np.uint8)).resize((2048, 2048), Image.LANCZOS).save(os.path.join(OUT, 'karasuk_sat_2k.jpg'), quality=82, optimize=True, progressive=True)
    Image.fromarray(near).save(os.path.join(OUT, 'karasuk_near.jpg'), quality=84, optimize=True, progressive=True)
    # маски: R — вода (Катунь), G — лес
    Image.fromarray(np.stack([wsmall * 255, fsmall * 255, np.zeros_like(wsmall)], -1).astype(np.uint8)).save(os.path.join(OUT, 'karasuk_water.png'), optimize=True)
    data = {
        'v': 1, 'R': R, 'N': N, 'A': A, 'near': NEAR, 'h0': round(H0, 1),
        'h': base64.b64encode(np.round(h * 10).astype('<i2').tobytes()).decode(),      # дециметры, строка — z (с севера на юг)
        'trees': base64.b64encode(tr.tobytes()).decode(),
        'hangars': HANGARS, 'apron': APRON, 'pads': PADS, 'taxiways': TAXIWAYS, 'parking': PARKING,
        'small': SMALL_BUILDINGS, 'houses': hs, 'cars': CARS, 'windsock': WINDSOCK,
        'tex': {'sat': 'karasuk_sat.jpg', 'sat2k': 'karasuk_sat_2k.jpg', 'near': 'karasuk_near.jpg', 'water': 'karasuk_water.png'},
        'credit': 'Рельеф: AWS Terrain Tiles (SRTM); снимок: Sentinel-2 cloudless 2016 by EOX (s2maps.eu), CC BY 4.0',
    }
    js = 'window.AltayScenes=window.AltayScenes||{};AltayScenes["karasuk"]=%s;\n' % json.dumps(data, separators=(',', ':'), ensure_ascii=False)
    open(os.path.join(OUT, 'karasuk.js'), 'w', encoding='utf-8').write(js)
    for f in ('karasuk.js', 'karasuk_sat.jpg', 'karasuk_sat_2k.jpg', 'karasuk_near.jpg', 'karasuk_water.png'):
        print('  %-20s %.2f МБ' % (f, os.path.getsize(os.path.join(OUT, f)) / 1e6))

if __name__ == '__main__':
    main()
