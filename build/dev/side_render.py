#!/usr/bin/env python3
"""Ортографический «чертёж» Ми-8 сбоку с метровой сеткой (для разметки ливреи):
   python3 build/dev/side_render.py <текстура> <выход.png> [right|left|top]"""
import sys, os
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'import'))
import mi8_geom
TEX, OUT = sys.argv[1], sys.argv[2]; VIEW = sys.argv[3] if len(sys.argv) > 3 else 'right'
G = mi8_geom.load('build/import/mi8amtsh/scene.gltf')
tex = np.array(Image.open(TEX).convert('RGB')); TH, TW = tex.shape[:2]
PX = 0.012
X0, X1, Y0, Y1 = -14.0, 6.5, -0.2, 6.5
if VIEW == 'top': Y0, Y1 = -4.0, 4.0
W, H = int((X1 - X0) / PX), int((Y1 - Y0) / PX)
img = np.zeros((H, W, 3)); zb = np.full(H * W, -1e9); lightv = np.array([0.3, 0.6, 0.75]); lightv /= np.linalg.norm(lightv)
for g, P, N, UV, I in G['prims']:
    if g in mi8_geom.MAIN_ROTOR: continue
    T = I.reshape(-1, 3); A, B, C = P[T[:, 0]], P[T[:, 1]], P[T[:, 2]]
    e = np.max(np.stack([np.linalg.norm(B - A, axis=1), np.linalg.norm(C - B, axis=1), np.linalg.norm(A - C, axis=1)]), 0)
    k = np.clip(np.ceil(e / (PX * 0.7)).astype(int) + 1, 2, 300)
    for kk in np.unique(k):
        sel = np.where(k == kk)[0]; gg = np.linspace(0, 1, kk); s, t = np.meshgrid(gg, gg); m = s + t <= 1 + 1e-9; s, t = s[m], t[m]
        for ch in np.array_split(sel, max(1, len(sel) * len(s) // 400000 + 1)):
            tri = T[ch]
            def interp(V): return V[tri[:, 0], None] + (V[tri[:, 1], None] - V[tri[:, 0], None]) * s[None, :, None] + (V[tri[:, 2], None] - V[tri[:, 0], None]) * t[None, :, None]
            p = interp(P).reshape(-1, 3); n = interp(N).reshape(-1, 3); uv = interp(UV).reshape(-1, 2)
            if VIEW == 'right': a, b, d = p[:, 0], p[:, 1], p[:, 2]
            elif VIEW == 'left': a, b, d = p[:, 0], p[:, 1], -p[:, 2]
            else: a, b, d = p[:, 0], p[:, 2], p[:, 1]
            ix = ((a - X0) / PX).astype(int); iy = ((Y1 - b) / PX).astype(int)
            ok = (ix >= 0) & (ix < W) & (iy >= 0) & (iy < H)
            ix, iy, d, n, uv = ix[ok], iy[ok], d[ok], n[ok], uv[ok]
            lin = iy * W + ix
            order = np.argsort(d); lin, d, n, uv = lin[order], d[order], n[order], uv[order]
            upd = d > zb[lin]; lin, d, n, uv = lin[upd], d[upd], n[upd], uv[upd]
            zb[lin] = d   # последний (самый ближний) выигрывает благодаря сортировке
            tx = np.clip((uv[:, 0] * TW).astype(int), 0, TW - 1); ty = np.clip((uv[:, 1] * TH).astype(int), 0, TH - 1)   # glTF: v от верха
            col = tex[ty, tx] * (0.55 + 0.45 * np.clip(np.abs(n @ lightv), 0, 1))[:, None]
            img.reshape(-1, 3)[lin] = col
bg = zb.reshape(H, W) < -1e8; img[bg] = (235, 240, 245)
im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)); d = ImageDraw.Draw(im)
for xm in range(int(np.ceil(X0)), int(X1) + 1):
    x = (xm - X0) / PX; d.line([(x, 0), (x, H)], fill=(255, 0, 0) if xm == 0 else (255, 120, 120), width=1); d.text((x + 2, 2), str(xm), fill=(200, 0, 0))
for ym in range(int(np.ceil(Y0)), int(Y1) + 1):
    y = (Y1 - ym) / PX; d.line([(0, y), (W, y)], fill=(120, 120, 255), width=1); d.text((2, y + 2), str(ym), fill=(0, 0, 200))
im.save(OUT); print(OUT, im.size)
