#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Декоративная топокарта для фона секций: настоящие горизонтали рельефа вокруг «Карасука» (SRTM, ±7 км, шаг 50 м,
   утолщённые — каждые 250 м). Изолинии — marching squares по сетке высот, сегменты склеиваются в полилинии.
     python3 build/terrain/topo_svg.py  → site/img/topo.svg"""
import os, sys, math
sys.setrecursionlimit(20000)
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import geo
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
L, N, STEP, W, H = 7000.0, 260, 50.0, 1600, 1000       # полуразмер (м), узлов, шаг горизонталей, размер viewBox

def blur(a, k=2):
    for _ in range(k):
        p = np.pad(a, 1, mode='edge')
        a = (p[1:-1, 1:-1] + p[:-2, 1:-1] + p[2:, 1:-1] + p[1:-1, :-2] + p[1:-1, 2:]) / 5
    return a

def contours(h, level):
    """Marching squares → список полилиний в координатах сетки (i — строка, j — столбец)."""
    b = h > level; ny, nx = h.shape; segs = []
    def ip(p, q):   # точка на ребре между узлами p и q
        (i0, j0), (i1, j1) = p, q; v0, v1 = h[i0, j0], h[i1, j1]; t = (level - v0) / (v1 - v0 + 1e-12)
        return (i0 + (i1 - i0) * t, j0 + (j1 - j0) * t)
    idx = (b[:-1, :-1] * 1) | (b[:-1, 1:] * 2) | (b[1:, 1:] * 4) | (b[1:, :-1] * 8)
    for i, j in zip(*np.nonzero((idx != 0) & (idx != 15))):
        c = idx[i, j]; tl, tr, br, bl = (i, j), (i, j + 1), (i + 1, j + 1), (i + 1, j)
        T, R_, B, Lf = ip(tl, tr), ip(tr, br), ip(bl, br), ip(tl, bl)
        tab = {1: [(Lf, T)], 2: [(T, R_)], 3: [(Lf, R_)], 4: [(R_, B)], 5: [(Lf, T), (R_, B)], 6: [(T, B)], 7: [(Lf, B)],
               8: [(B, Lf)], 9: [(B, T)], 10: [(T, R_), (B, Lf)], 11: [(B, R_)], 12: [(R_, Lf)], 13: [(R_, T)], 14: [(T, Lf)]}
        segs += tab[c]
    # склейка сегментов в полилинии
    key = lambda p: (round(p[0], 4), round(p[1], 4))
    ends = {}
    for k, (a, b2) in enumerate(segs): ends.setdefault(key(a), []).append(k); ends.setdefault(key(b2), []).append(k)
    used = [False] * len(segs); lines = []
    for k in range(len(segs)):
        if used[k]: continue
        used[k] = True; line = [segs[k][0], segs[k][1]]
        for direction in (1, 0):
            while True:
                tip = line[-1] if direction else line[0]; nxt = None
                for m in ends.get(key(tip), []):
                    if not used[m]: nxt = m; break
                if nxt is None: break
                used[nxt] = True; a, b2 = segs[nxt]; p = b2 if key(a) == key(tip) else a
                if direction: line.append(p)
                else: line.insert(0, p)
        lines.append(line)
    return lines

def simplify(pts, eps):
    if len(pts) < 3: return pts
    a, b = np.array(pts[0]), np.array(pts[-1]); P = np.array(pts)
    ab = b - a; n = np.linalg.norm(ab)
    d = np.abs(ab[0] * (P[:, 1] - a[1]) - ab[1] * (P[:, 0] - a[0])) / n if n > 1e-6 else np.linalg.norm(P - a, axis=1)
    i = int(np.argmax(d))
    if d[i] > eps: return simplify(pts[:i + 1], eps)[:-1] + simplify(pts[i:], eps)
    return [pts[0], pts[-1]]

def main():
    ar = W / H; xs = np.linspace(-L, L, N); zs = np.linspace(-L / ar, L / ar, int(N / ar))
    zz, xx = np.meshgrid(zs, xs, indexing='ij')
    h = blur(geo.height(xx, zz).astype(float), 2)
    lo, hi = math.ceil(h.min() / STEP) * STEP, math.floor(h.max() / STEP) * STEP
    ny, nx = h.shape; sx, sy = W / (nx - 1), H / (ny - 1)
    thin, thick = [], []
    for lev in np.arange(lo, hi + 1, STEP):
        for line in contours(h, lev):
            if len(line) < 4: continue
            pts = simplify([(j * sx, i * sy) for i, j in line], 0.9)
            d = 'M' + 'L'.join('%.1f %.1f' % p for p in pts)
            (thick if lev % (STEP * 5) == 0 else thin).append(d)
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" preserveAspectRatio="xMidYMid slice">'
           '<g fill="none" stroke="#1E6FD9" stroke-linejoin="round" stroke-linecap="round">'
           '<path stroke-width="0.8" stroke-opacity=".5" d="%s"/><path stroke-width="1.5" stroke-opacity=".8" d="%s"/></g></svg>') % (W, H, ''.join(thin), ''.join(thick))
    out = os.path.join(ROOT, 'site', 'img', 'topo.svg'); open(out, 'w').write(svg)
    print('горизонталей: %d тонких, %d утолщённых; высоты %.0f–%.0f м; %s %d КБ' % (len(thin), len(thick), h.min(), h.max(), out, os.path.getsize(out) // 1024))

if __name__ == '__main__':
    main()
