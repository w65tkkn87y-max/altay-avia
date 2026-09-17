#!/usr/bin/env python3
"""Сборка итоговой текстуры Ми-8: запечённая ливрея + стекло и мелкие детали из оригинала.
   python3 build/import/compose_texture.py <bake.png> <original.png> <out.png> [size]"""
import sys, numpy as np
from PIL import Image, ImageFilter
bake_p, orig_p, out_p = sys.argv[1:4]; size = int(sys.argv[4]) if len(sys.argv) > 4 else 2048
bake = Image.open(bake_p).convert('RGBA').transpose(Image.FLIP_TOP_BOTTOM)   # WebGL: v=0 внизу → glTF: v=0 сверху
orig = Image.open(orig_p).convert('RGB').resize(bake.size, Image.LANCZOS)
B = np.asarray(bake).astype(np.float32); O = np.asarray(orig).astype(np.float32)
rgb = B[..., :3]; a = B[..., 3] > 8
# 1) дилатация: незакрашенные тексели заполняем ближайшим цветом (убирает швы на границах островов)
col = rgb.copy(); cov = a.copy()
for _ in range(10):
    acc = np.zeros_like(col); cnt = np.zeros(col.shape[:2], np.float32)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dx == 0 and dy == 0: continue
            sc = np.roll(np.roll(col, dy, 0), dx, 1); sm = np.roll(np.roll(cov, dy, 0), dx, 1)
            acc += sc * sm[..., None]; cnt += sm
    fill = (~cov) & (cnt > 0)
    col[fill] = acc[fill] / cnt[fill][:, None]; cov = cov | fill
col[~cov] = O[~cov]  # совсем далёкие тексели — из оригинала
# 2) стекло: в оригинале окна сине-серые (b > r, g); сохраняем их, слегка затемнив
r, g, b = O[..., 0], O[..., 1], O[..., 2]
glass = (b > r * 1.12) & (b > g * 1.04) & (b > 60) & a
gl = np.asarray(Image.fromarray(glass.astype(np.uint8) * 255).filter(ImageFilter.MaxFilter(3))) > 0
col[gl] = O[gl] * 0.75 + np.array([8, 14, 24], np.float32)
# 3) лёгкие детали (стыки панелей, заклёпки) из оригинала — везде, кроме островов фюзеляжа с военными знаками
lum = O.mean(-1); blur = np.asarray(Image.fromarray(lum.astype(np.uint8)).filter(ImageFilter.GaussianBlur(6))).astype(np.float32) + 1
det = np.clip(lum / blur, 0.90, 1.06)
H, W = lum.shape
fus = np.zeros_like(a); fus[int(H * 0.70):, :int(W * 0.73)] = True   # два профиля фюзеляжа (низ слева в оригинале)
det[fus | gl] = 1.0
col = np.clip(col * det[..., None], 0, 255)
out = Image.fromarray(col.astype(np.uint8), 'RGB')
if size != out.width: out = out.resize((size, size), Image.LANCZOS)
out.save(out_p, quality=88, optimize=True) if out_p.lower().endswith('.jpg') else out.save(out_p, optimize=True); print('saved', out_p, out.size)
