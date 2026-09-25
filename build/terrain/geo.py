#!/usr/bin/env python3
"""Геопривязка сцены «Карасук»: локальные метры (x — восток, z — юг, y — вверх) с началом в центре
   большой площадки P3 (на ней на аэрофото стоит Ми-171); выборка рельефа (terrarium z13) и снимка (S2 z14)."""
import glob, math, os, re
import numpy as np
from PIL import Image
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cache')
LAT_REF, LON_REF = 51.5600, 85.9175               # точка с сайта компании (51°33′36″ N, 85°55′03″ E)
P3_FROM_REF = (22.0, -82.0)                        # площадка P3 относительно неё, м (x восток, z юг) — по снимку
M_PER_DEG_LAT = 111230.0
M_PER_DEG_LON = 111320.0 * math.cos(math.radians(LAT_REF))
LAT0 = LAT_REF - P3_FROM_REF[1] / M_PER_DEG_LAT
LON0 = LON_REF + P3_FROM_REF[0] / M_PER_DEG_LON

def to_latlon(x, z):
    return LAT0 - np.asarray(z) / M_PER_DEG_LAT, LON0 + np.asarray(x) / M_PER_DEG_LON

class Mosaic:
    def __init__(self, prefix, z):
        fs = glob.glob(os.path.join(D, '%s_%d_*' % (prefix, z)))
        xy = [tuple(map(int, re.findall(r'_(\d+)_(\d+)\.', f)[0])) for f in fs]
        self.x0 = min(a for a, b in xy); self.y0 = min(b for a, b in xy)
        W = (max(a for a, b in xy) - self.x0 + 1) * 256; H = (max(b for a, b in xy) - self.y0 + 1) * 256
        img = np.zeros((H, W, 3), np.float32)
        for f, (x, y) in zip(fs, xy):
            img[(y - self.y0) * 256:(y - self.y0 + 1) * 256, (x - self.x0) * 256:(x - self.x0 + 1) * 256] = np.array(Image.open(f).convert('RGB'), np.float32)
        self.img, self.z = img, z
    def pix(self, lat, lon):
        n = 2 ** self.z
        X = (np.asarray(lon) + 180) / 360 * n * 256 - self.x0 * 256
        Y = (1 - np.arcsinh(np.tan(np.radians(lat))) / np.pi) / 2 * n * 256 - self.y0 * 256
        return X - 0.5, Y - 0.5
    def sample(self, lat, lon, arr=None):
        a = self.img if arr is None else arr
        X, Y = self.pix(lat, lon); H, W = a.shape[:2]
        x0 = np.clip(np.floor(X).astype(int), 0, W - 2); y0 = np.clip(np.floor(Y).astype(int), 0, H - 2)
        fx = np.clip(X - x0, 0, 1); fy = np.clip(Y - y0, 0, 1)
        if a.ndim == 3: fx, fy = fx[..., None], fy[..., None]
        return (a[y0, x0] * (1 - fx) * (1 - fy) + a[y0, x0 + 1] * fx * (1 - fy) + a[y0 + 1, x0] * (1 - fx) * fy + a[y0 + 1, x0 + 1] * fx * fy)

_dem = None
def dem():
    global _dem
    if _dem is None:
        m = Mosaic('dem', 13); a = m.img
        m.h = a[..., 0] * 256 + a[..., 1] + a[..., 2] / 256 - 32768
        _dem = m
    return _dem
def height(x, z):
    m = dem(); lat, lon = to_latlon(x, z); return m.sample(lat, lon, m.h)
