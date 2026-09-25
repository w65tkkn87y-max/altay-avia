#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Нижнее остекление носа Ми-8АМТ / Ми-171: у Mi-8AMTSh нос глухой (бронированный), у гражданских бортов под лобовыми
   стёклами — большие окна, огибающие нос (на фото RA-25565 и RA-24187). Контур окна задаётся в развёртке носа
   (s — дуга вокруг вертикальной оси кабины, y — высота) и переносится на обшивку лучами от оси."""
import math
import numpy as np
import mi8_geom

AXIS = (4.9, 0.0)          # вертикальная ось развёртки (x, z)
R_S = 0.8                  # s = φ·R_S — дуга в метрах
PHI0, PHI1 = 9.0, 60.0     # от стойки по оси носа до переднего края нижнего бокового окна (проём обшивки, φ≈64°)

def skin(G):
    T, N = [], []
    for g, P, Nn, UV, I in G['prims']:
        if g != 'sub01_0': continue
        t = I.reshape(-1, 3); m = P[t][:, :, 0].max(1) > 4.3
        T.append(P[t][m]); N.append(Nn[t][m])
    return np.concatenate(T), np.concatenate(N)

def raycast(T, TN, O, D):
    """Самое дальнее (наружная обшивка) пересечение лучей O + tD с треугольниками → точки и нормали."""
    v0 = T[:, 0]; e1 = T[:, 1] - v0; e2 = T[:, 2] - v0
    P = np.zeros_like(O); N = np.zeros_like(O); ok = np.zeros(len(O), bool)
    for k in range(len(O)):
        d = D[k]; p = np.cross(d, e2); det = (e1 * p).sum(1)
        good = np.abs(det) > 1e-12; inv = np.where(good, 1.0 / np.where(good, det, 1), 0)
        s = O[k] - v0; u = (s * p).sum(1) * inv; q = np.cross(s, e1); v = (q @ d) * inv; t = (e2 * q).sum(1) * inv
        hit = good & (u >= 0) & (v >= 0) & (u + v <= 1) & (t > 0)
        if not hit.any(): continue
        i = np.where(hit)[0][np.argmax(t[hit])]
        P[k] = O[k] + d * t[i]
        n = TN[i, 0] * (1 - u[i] - v[i]) + TN[i, 1] * u[i] + TN[i, 2] * v[i]; n /= np.linalg.norm(n)
        N[k] = n if n @ d > 0 else -n; ok[k] = True
    return P, N, ok

H = 0.36                   # высота окна в развёртке (м), по месту — от to_sy

def outline(n_corner=12):
    """Контур стекла в развёртке (s, y), м: скруглённый прямоугольник; y — 0..H, по месту пересчитывается to_sy."""
    s0, s1 = math.radians(PHI0) * R_S, math.radians(PHI1) * R_S
    w = s1 - s0
    pts = []   # углы: сзади-снизу, сзади-сверху, спереди-сверху, спереди-снизу (спереди — у оси носа)
    for cx, cy, a0, r in ((w - 0.07, 0.07, -90, 0.07), (w - 0.06, H - 0.06, 0, 0.06), (0.09, H - 0.09, 90, 0.09), (0.13, 0.13, 180, 0.13)):
        for i in range(n_corner + 1):
            a = math.radians(a0 + 90 * i / n_corner); pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    q = np.array(pts); q[:, 0] += s0
    return q

def to_sy(q):
    """Высота 0..H → y по месту: низ 1.52 у оси носа (ниже — обтекатель радара) → 1.40 сбоку, верх 1.84 → 1.80."""
    s0, s1 = math.radians(PHI0) * R_S, math.radians(PHI1) * R_S
    f = np.clip((q[:, 0] - s0) / (s1 - s0), 0, 1)
    yb = 1.52 - 0.12 * f; yt = 1.84 - 0.04 * f
    return np.stack([q[:, 0], yb + q[:, 1] / H * (yt - yb)], -1)

def project(Tt, TN, sy, side):
    phi = sy[:, 0] / R_S
    O = np.stack([np.full(len(sy), AXIS[0]), sy[:, 1], np.full(len(sy), AXIS[1])], -1)
    D = np.stack([np.cos(phi), np.zeros(len(sy)), np.sin(phi) * side], -1)
    P, N, ok = raycast(Tt, TN, O, D)
    if not ok.all(): print('  нос: лучей мимо обшивки %d' % (~ok).sum())
    return P, N

def inside(P):
    """Точки обшивки под стеклом (по развёртке) — их красим тёмным «салоном»: стекло прозрачное, как остальное остекление."""
    phi = np.arctan2(np.abs(P[:, 2]), P[:, 0] - AXIS[0]); sq = phi * R_S
    s0, s1 = math.radians(PHI0) * R_S, math.radians(PHI1) * R_S
    f = np.clip((sq - s0) / (s1 - s0), 0, 1); yb = 1.52 - 0.12 * f; yt = 1.84 - 0.04 * f
    yn = (P[:, 1] - yb) / (yt - yb) * H
    poly = outline(); x0, y0 = poly[:, 0], poly[:, 1]; x1, y1 = np.roll(x0, -1), np.roll(y0, -1)
    res = np.zeros(len(P), bool)
    for a, b, c, d in zip(x0, y0, x1, y1):             # чётность пересечений горизонтального луча
        cond = ((b > yn) != (d > yn))
        xi = a + (yn - b) * (c - a) / np.where(d != b, d - b, 1e-12)
        res ^= cond & (sq < xi)
    return res & (P[:, 0] > AXIS[0])

def scaled(q, k):
    c = q.mean(0); return c + (q - c) * k

def outlines(G):
    """3D-контуры стёкол (оба борта) — для окантовки краской в livery_mi8.py."""
    Tt, TN = skin(G); q = outline()
    return [project(Tt, TN, to_sy(q), side)[0] for side in (+1, -1)]

def parts(G, frame_uv, Part):
    """→ (рамка, стекло): рамка — полоса 3.5 см (в развёртке) вокруг стекла, стекло — m:'glass' (под ним обшивка
       окрашена тёмным — см. inside()); сетка плотная и приподнята над обшивкой — на изгибе носа хорды не утопают."""
    Tt, TN = skin(G); q = outline()
    frame = Part('nose_window_frames', None, 'paint'); glass = Part('nose_windows', None, 'glass')
    # наружный контур рамки: сдвиг по нормали контура на 3.5 см в развёртке
    c = q.mean(0); d = q - c
    t = np.roll(q, -1, 0) - np.roll(q, 1, 0); nrm = np.stack([t[:, 1], -t[:, 0]], -1); nrm /= np.linalg.norm(nrm, axis=1, keepdims=True)
    if ((nrm * d).sum(1) < 0).mean() > 0.5: nrm = -nrm
    outer = q + nrm * 0.035
    rings = [q] + [scaled(q, k) for k in np.linspace(0.9, 0.1, 9)]
    n = len(q)
    for side in (+1, -1):
        # рамка
        P0, N0 = project(Tt, TN, to_sy(outer), side); P1, N1 = project(Tt, TN, to_sy(q), side)
        P = np.vstack([P0, P1]); N = np.vstack([N0, N1]); P = P + N * 0.016
        for i in range(n):
            j = (i + 1) % n
            for tri in ((i, j, n + j), (i, n + j, n + i)):
                tri = np.array(tri); p3 = P[tri]; n3 = N[tri]
                if np.cross(p3[1] - p3[0], p3[2] - p3[0]) @ n3.sum(0) < 0: p3, n3 = p3[::-1], n3[::-1]
                frame.add(p3, n3, np.tile(frame_uv, (3, 1)))
        # стекло: кольца к центру + центр
        pts = np.vstack(rings + [q.mean(0)[None]])
        P, N = project(Tt, TN, to_sy(pts), side); P = P + N * 0.012
        tris = []
        for k in range(len(rings) - 1):
            b = k * n
            for i in range(n):
                j = (i + 1) % n; tris += [(b + i, b + j, b + n + j), (b + i, b + n + j, b + n + i)]
        cidx = len(rings) * n
        for i in range(n): tris.append(((len(rings) - 1) * n + i, (len(rings) - 1) * n + (i + 1) % n, cidx))
        for tri in tris:
            tri = np.array(tri); p3 = P[tri]; n3 = N[tri]
            if np.cross(p3[1] - p3[0], p3[2] - p3[0]) @ n3.sum(0) < 0: p3, n3 = p3[::-1], n3[::-1]
            glass.add(p3, n3, np.tile(frame_uv, (3, 1)))
    return frame, glass
