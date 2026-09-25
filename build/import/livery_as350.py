#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ливрея «АлтайАвиа» для AS350 (борт RA-04062, по фото из галереи сайта) — дорисовка в исходных текстурах.
   Каждый треугольник растеризуется в пространстве своей текстуры; для каждого текселя известны 3D-точка и нормаль
   (оси сайта: нос +X, верх +Y, правый борт +Z), по ним выбирается цвет:
     • белый корпус; тёмно-синяя «волна» снизу задней части фюзеляжа, переходящая в полностью синюю хвостовую балку и киль;
     • полозья шасси — тёмно-синие;
     • «ALTAY AVIA» синим на обоих бортах под окнами, «RA-04062» белым на балке, флаг России на киле;
   панельные швы, лючки и заклёпки исходной текстуры сохраняются (яркость относительно локальной медианы)."""
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

WHITE = np.array([244, 246, 248], float)
NAVY = np.array([22, 36, 88], float)
TEXT_BLUE = np.array([33, 80, 184], float)
FONT_BOLD = '/System/Library/Fonts/Supplemental/Arial Bold.ttf'

# ---------- видимость снаружи: ортографические карты глубины с 10 направлений ----------
class Visibility:
    VIEWS = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1), (1, 0, 1), (1, 0, -1), (-1, 0, 1), (-1, 0, -1)]
    def __init__(self, tris, px=0.012, eps=0.03):
        P = np.stack(tris).astype(np.float64)                       # (n,3,3)
        self.px, self.eps = px, eps
        pts = self._sample(P, px * 0.6)
        self.maps = []
        for v in self.VIEWS:
            v = np.array(v, float); v /= np.linalg.norm(v)
            up = np.array([0, 1.0, 0]) if abs(v[1]) < 0.9 else np.array([1.0, 0, 0])
            e1 = np.cross(up, v); e1 /= np.linalg.norm(e1); e2 = np.cross(v, e1)
            a, b, h = pts @ e1, pts @ e2, pts @ v
            a0, b0 = a.min() - 2 * px, b.min() - 2 * px
            nx, ny = int((a.max() - a0) / px) + 3, int((b.max() - b0) / px) + 3
            ia, ib = ((a - a0) / px).astype(int), ((b - b0) / px).astype(int)
            D = np.full(nx * ny, -1e9); np.maximum.at(D, ib * nx + ia, h)
            self.maps.append((e1, e2, v, a0, b0, nx, ny, D))
    @staticmethod
    def _sample(P, step):
        out = []
        e = np.max(np.linalg.norm(P - np.roll(P, 1, 1), axis=2), 1)
        k = np.clip(np.ceil(e / step).astype(int) + 1, 2, 400)
        for kk in np.unique(k):
            T = P[k == kk]; g = np.linspace(0, 1, kk)
            s, t = np.meshgrid(g, g); m = s + t <= 1 + 1e-9; s, t = s[m], t[m]
            out.append((T[:, None, 0] + (T[:, None, 1] - T[:, None, 0]) * s[None, :, None] + (T[:, None, 2] - T[:, None, 0]) * t[None, :, None]).reshape(-1, 3))
        return np.vstack(out)
    def visible(self, p):
        """Сколько из 10 направлений «видят» точку (0 — скрыта внутри)."""
        cnt = np.zeros(len(p), np.float32)
        for e1, e2, v, a0, b0, nx, ny, D in self.maps:
            ia = np.clip(((p @ e1 - a0) / self.px).astype(int), 0, nx - 1); ib = np.clip(((p @ e2 - b0) / self.px).astype(int), 0, ny - 1)
            cnt += (p @ v) >= D[ib * nx + ia] - self.eps
        return cnt

# ---------- растеризация 3D-точек в пространство текстуры ----------
def rasterize(W, H, tris, vis=None):
    pos = np.zeros((H, W, 3), np.float32); nrm = np.zeros((H, W, 3), np.float32); cov = np.zeros((H, W), bool)
    prio = np.full((H, W), -1.0, np.float32)    # один кусок текстуры бывает общим для обшивки и скрытых граней — побеждает обшивка
    for P3, N3, UV3 in tris:
        uv = np.clip(UV3, 0, 1)
        px = uv[:, 0] * W; py = (1.0 - uv[:, 1]) * H
        x0, x1 = int(max(0, np.floor(px.min() - 1.5))), int(min(W - 1, np.ceil(px.max() + 1.5)))
        y0, y1 = int(max(0, np.floor(py.min() - 1.5))), int(min(H - 1, np.ceil(py.max() + 1.5)))
        if x1 < x0 or y1 < y0: continue
        gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        (ax, bx, cx), (ay, by, cy) = px, py
        den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(den) < 1e-9: continue
        l0 = ((by - cy) * (gx - cx) + (cx - bx) * (gy - cy)) / den
        l1 = ((cy - ay) * (gx - cx) + (ax - cx) * (gy - cy)) / den
        l2 = 1 - l0 - l1
        # допуск ~1.2 px за границу треугольника (против щелей на швах развёртки)
        e = [np.hypot(bx - cx, by - cy), np.hypot(cx - ax, cy - ay), np.hypot(ax - bx, ay - by)]
        area2 = abs(den)
        tol = [1.2 * ei / area2 for ei in e]
        m = (l0 >= -tol[0]) & (l1 >= -tol[1]) & (l2 >= -tol[2])
        if not m.any(): continue
        L = np.stack([np.clip(l0, 0, 1), np.clip(l1, 0, 1), np.clip(l2, 0, 1)], -1)[m]; L /= L.sum(1, keepdims=True)
        yy, xx = (gy[m] - 0.5).astype(int), (gx[m] - 0.5).astype(int)
        inside = (l0[m] >= 0) & (l1[m] >= 0) & (l2[m] >= 0)
        p3 = L @ P3
        pr = (vis.visible(p3).astype(np.float32) if vis is not None else np.zeros(len(p3), np.float32)) + np.where(inside, 0.0, -0.001)   # видна снаружи — значит обшивка
        # точные попадания важнее «допусковых»; из двух точных — та грань, что снаружи
        keep = (~cov[yy, xx]) | (inside & (pr >= prio[yy, xx]))
        yy, xx, L, p3, pr = yy[keep], xx[keep], L[keep], p3[keep], pr[keep]
        pos[yy, xx] = p3; n = L @ N3; nrm[yy, xx] = n / (np.linalg.norm(n, axis=1, keepdims=True) + 1e-9); cov[yy, xx] = True; prio[yy, xx] = pr
    return pos, nrm, cov

# ---------- декали ----------
def text_image(text, color, height_px=260, pad=20, font=FONT_BOLD, tracking=0.06):
    f = ImageFont.truetype(font, height_px)
    widths = [f.getlength(ch) for ch in text]; tw = int(sum(widths) + tracking * height_px * (len(text) - 1)) + 2 * pad
    asc, desc = f.getmetrics(); th = asc + desc + 2 * pad
    img = Image.new('L', (tw, th), 0); d = ImageDraw.Draw(img); x = pad
    for ch, w in zip(text, widths): d.text((x, pad), ch, font=f, fill=255); x += w + tracking * height_px
    bbox = img.getbbox(); img = img.crop(bbox)
    rgba = np.zeros((img.height, img.width, 4), float); rgba[..., :3] = color; rgba[..., 3] = np.array(img, float) / 255
    return rgba

def flag_image(w=300, h=200):
    a = np.zeros((h, w, 4), float); a[..., 3] = 1
    a[:h // 3, :, :3] = (250, 250, 250); a[h // 3:2 * h // 3, :, :3] = (0, 57, 166); a[2 * h // 3:, :, :3] = (213, 43, 30)
    return a

class Decal:
    """Прямоугольник на борту: x0..x1 (вдоль фюзеляжа), yc — центр по высоте, высота h — по высоте картинки;
       side: +1 правый, -1 левый борт (текст читается слева направо на обоих бортах)."""
    def __init__(self, img, x_front, x_rear, yc, side, height=None, zmax=None, nz=0.3):
        self.img, self.side, self.nz = img, side, nz
        self.xf, self.xr = x_front, x_rear
        L = x_front - x_rear
        self.h = height if height else L * img.shape[0] / img.shape[1]
        self.y0 = yc - self.h / 2; self.zmax = zmax
    def apply(self, col, pos, nrm):
        side_ok = (pos[:, 2] * self.side > 0.02) & (np.abs(nrm[:, 2]) > self.nz)   # у дверей нормали бывают внутрь — сторону берём по координате
        if self.zmax is not None: side_ok &= np.abs(pos[:, 2]) < self.zmax
        L = self.xf - self.xr
        if self.side > 0: u = (pos[:, 0] - self.xr) / L       # правый борт: нос справа от зрителя
        else: u = (self.xf - pos[:, 0]) / L                    # левый борт: нос слева
        v = 1.0 - (pos[:, 1] - self.y0) / self.h              # строка картинки сверху вниз
        m = side_ok & (u >= 0) & (u <= 1) & (v >= 0) & (v <= 1)
        if not m.any(): return col
        H, W = self.img.shape[:2]
        fx = np.clip(u[m] * (W - 1), 0, W - 1); fy = np.clip(v[m] * (H - 1), 0, H - 1)
        x0 = np.floor(fx).astype(int); y0 = np.floor(fy).astype(int); x1 = np.minimum(x0 + 1, W - 1); y1 = np.minimum(y0 + 1, H - 1)
        ax = (fx - x0)[:, None]; ay = (fy - y0)[:, None]
        s = (self.img[y0, x0] * (1 - ax) * (1 - ay) + self.img[y0, x1] * ax * (1 - ay) + self.img[y1, x0] * (1 - ax) * ay + self.img[y1, x1] * ax * ay)
        a = s[:, 3:4]
        col[m] = col[m] * (1 - a) + s[:, :3] * a
        return col

def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t)

def livery_color(pos, nrm):
    x, y, z = pos[:, 0], pos[:, 1], pos[:, 2]
    # граница «волны»: у днища за задней дверью (x≈0.3) → поднимается к верху балки у x≈-1.95
    yb = -0.52 + (0.98 + 0.52) * smoothstep(-0.15, -1.95, x) ** 1.6
    navy = (y < yb) | (x < -1.9)
    navy |= (y < -0.58)                                        # полозья и поперечины шасси
    t = np.clip((yb - y) / 0.012, 0, 1)                        # мягкий край (~1 см)
    t = np.where(x < -1.9, 1.0, t); t = np.where(y < -0.58, 1.0, t)
    col = WHITE[None, :] * (1 - t[:, None]) + NAVY[None, :] * t[:, None]
    return col

DECALS = None
def decals():
    global DECALS
    if DECALS is None:
        name = text_image('ALTAY AVIA', TEXT_BLUE)
        reg = text_image('RA-04062', (246, 248, 250), tracking=0.04)
        flag = flag_image()
        DECALS = [
            Decal(name, 0.90, -0.46, 0.06, +1), Decal(name, 0.38, -0.98, 0.06, -1),       # за дверями, над «волной»
            Decal(reg, -2.15, -4.05, 0.50, +1, zmax=0.45, nz=0.55), Decal(reg, -2.15, -4.05, 0.50, -1, zmax=0.45, nz=0.55),
            Decal(flag, -7.00, -7.29, 1.70, +1, height=0.19), Decal(flag, -7.00, -7.29, 1.70, -1, height=0.19),
        ]
    return DECALS

# ---------- исходная текстура: что считать «краской» ----------
def paint_mask_and_detail(src, pos=None, cov=None):
    a = src.astype(float); r, g, b = a[..., 0], a[..., 1], a[..., 2]
    lum = 0.299 * r + 0.587 * g + 0.114 * b; sat = a.max(-1) - a.min(-1)
    white = (lum > 90) & (sat < 45)          # белая краска, в т.ч. с запечённой тенью (серые тона)
    navy = (b > r + 18) & (lum < 115) & (b > 45)
    light_blue = (b > r + 45) & (lum >= 100)
    m = white | navy | light_blue
    if pos is not None:
        boom = cov & (pos[..., 0] < -1.45)
        metal = (lum > 110) & (lum < 222) & (sat < 30)
        colored = (sat > 60) & ~(b > r + 18)
        m |= boom & ~metal & ~colored
    mi = Image.fromarray((m * 255).astype(np.uint8))
    mi = mi.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.MinFilter(5))       # закрытие: швы внутри окраски — тоже окраска
    m = np.array(mi) > 127
    li = Image.fromarray(np.clip(lum, 0, 255).astype(np.uint8))
    med = np.array(li.filter(ImageFilter.MedianFilter(9)), float)
    # яркость относительно исходного цвета краски: для белой/серой — относительно чистого белого (сохраняет тени и объём),
    # для синей/голубой — относительно локальной медианы (сохраняет только швы)
    neutral = (sat < 45) & (lum > 90)
    detail = np.where(neutral, lum / 232.0, lum / np.maximum(med, 20))
    detail = np.clip(detail, 0.42, 1.08)
    return m, detail

def paint(tex, painted, occluders=None):
    vis = Visibility(occluders) if occluders else None
    by_tex = {}
    for tname, P3, N3, UV3 in painted: by_tex.setdefault(tname, []).append((P3, N3, UV3))
    for tname, tris in by_tex.items():
        img = tex[tname]; W, H = img.size
        src = np.array(img)
        pos, nrm, cov = rasterize(W, H, tris, vis)
        m, detail = paint_mask_and_detail(src, pos, cov)
        sel = cov & m
        P = pos[sel].astype(float); N = nrm[sel].astype(float)
        col = livery_color(P, N)
        for d in decals(): col = d.apply(col, P, N)
        col = col * detail[sel][:, None]
        out = src.astype(float); out[sel] = col
        tex[tname] = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))
        print('  ливрея: %s — окрашено %.1f%% текстуры' % (tname, 100.0 * sel.mean()))
