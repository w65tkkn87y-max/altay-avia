#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Запекание затенения (ambient occlusion) в текстуру по 3D-координатам текселей.
   Для ~48 равномерных направлений строятся ортогональные карты глубины модели; тексель «видит небо» в направлении d,
   если вдоль d над ним ничего нет. AO = доля открытых направлений полусферы над нормалью (с весом cos).
   У моделей Ми-8 обшивка двусторонняя (нормали бывают внутрь) — берётся лучшая из двух сторон: снаружи открыто,
   значит это наружная поверхность; в щелях и под баками закрыты обе."""
import numpy as np
from livery_as350 import Visibility

def fib_dirs(n):
    i = np.arange(n) + 0.5; phi = np.arccos(1 - 2 * i / n); th = np.pi * (1 + 5 ** 0.5) * i
    return np.stack([np.cos(th) * np.sin(phi), np.cos(phi), np.sin(th) * np.sin(phi)], -1)

class AO:
    def __init__(self, tris, n=48, px=0.035, eps=0.07):
        P = np.stack(tris).astype(np.float64)
        pts = Visibility._sample(P, px * 0.55).astype(np.float32)
        self.px, self.eps, self.maps = px, eps, []
        for v in fib_dirs(n).astype(np.float32):
            up = np.array([0, 1, 0], np.float32) if abs(v[1]) < 0.9 else np.array([1, 0, 0], np.float32)
            e1 = np.cross(up, v); e1 /= np.linalg.norm(e1); e2 = np.cross(v, e1)
            a, b, h = pts @ e1, pts @ e2, pts @ v
            a0, b0 = a.min() - 2 * px, b.min() - 2 * px
            nx, ny = int((a.max() - a0) / px) + 3, int((b.max() - b0) / px) + 3
            D = np.full(nx * ny, -1e9, np.float32)
            np.maximum.at(D, ((b - b0) / px).astype(np.int64) * nx + ((a - a0) / px).astype(np.int64), h)
            self.maps.append((e1, e2, v, a0, b0, nx, ny, D))

    def _one(self, P, N):
        acc = np.zeros(len(P), np.float32); ws = np.zeros(len(P), np.float32)
        for e1, e2, v, a0, b0, nx, ny, D in self.maps:
            w = np.clip(N @ v, 0, None)
            if not w.any(): continue
            ia = np.clip(((P @ e1 - a0) / self.px).astype(np.int64), 0, nx - 1); ib = np.clip(((P @ e2 - b0) / self.px).astype(np.int64), 0, ny - 1)
            acc += w * ((P @ v) >= D[ib * nx + ia] - self.eps); ws += w
        return acc / np.maximum(ws, 1e-6)

    def __call__(self, P, N, two_sided=True, chunk=400000):
        P = P.astype(np.float32); N = N.astype(np.float32); out = np.zeros(len(P), np.float32)
        for s in range(0, len(P), chunk):
            p, n = P[s:s + chunk], N[s:s + chunk]
            a = self._one(p, n)
            if two_sided: a = np.maximum(a, self._one(p, -n))
            out[s:s + chunk] = a
        return out

def bake(pos, nrm, mask, occluder_tris, step=2, **kw):
    """pos/nrm — карты текстуры (H, W, 3), mask — где считать. Счёт на сетке с шагом step, затем растяжка
       с заполнением пустот (без тёмных ореолов на швах развёртки). → карта AO (H, W), 1 — открыто."""
    H, W = mask.shape
    sub = mask[::step, ::step]; ps = pos[::step, ::step][sub]; ns = nrm[::step, ::step][sub]
    ao = AO(occluder_tris, **kw)(ps, ns)
    a = np.full(sub.shape, np.nan, np.float32); a[sub] = ao
    # заполнение пустот соседями (8 шагов «расширения»)
    for _ in range(8):
        nanm = np.isnan(a)
        if not nanm.any(): break
        p = np.pad(a, 1, mode='edge'); stack = np.stack([p[1:-1, :-2], p[1:-1, 2:], p[:-2, 1:-1], p[2:, 1:-1]])
        with np.errstate(all='ignore'): fill = np.nanmean(stack, 0)
        a[nanm] = fill[nanm]
    a = np.nan_to_num(a, nan=1.0)
    from PIL import Image
    big = np.array(Image.fromarray(a).resize((W, H), Image.BILINEAR), np.float32)
    return np.clip(big, 0, 1)
