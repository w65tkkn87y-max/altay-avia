#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Граничные петли сетки (сварка вершин по позиции) — для поиска проёмов остекления кабины Ми-8."""
import numpy as np
from collections import defaultdict

def weld(P, I, tol=1e-4):
    key = np.round(P / tol).astype(np.int64)
    _, inv = np.unique(key, axis=0, return_inverse=True)
    inv = inv.ravel()
    Pw = np.zeros((inv.max() + 1, 3)); Pw[inv] = P
    return Pw, inv[I]

def boundary_loops(P, I):
    """P (n,3), I (m*3) → список петель (массивы индексов в сваренной сетке) и сваренные позиции."""
    Pw, Iw = weld(P, I)
    T = Iw.reshape(-1, 3)
    cnt = defaultdict(int); directed = {}
    for a, b, c in T:
        for u, v in ((a, b), (b, c), (c, a)):
            if u == v: continue
            k = (min(u, v), max(u, v)); cnt[k] += 1; directed[k] = (u, v)
    nxt = defaultdict(list)
    for k, n in cnt.items():
        if n == 1: u, v = directed[k]; nxt[u].append(v)
    loops = []; used = set()
    for s in list(nxt):
        for v0 in nxt[s]:
            if (s, v0) in used: continue
            loop = [s]; u, v = s, v0; ok = False
            for _ in range(100000):
                used.add((u, v))
                if v == s: ok = True; break
                loop.append(v)
                cand = [w for w in nxt[v] if (v, w) not in used]
                if not cand: break
                u, v = v, cand[0]
            if ok and len(loop) >= 3: loops.append(np.array(loop))
    return loops, Pw
