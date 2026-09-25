#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Доработка упакованных Ми-8АМТ / Ми-171 (site/models/<key>.js после glb2js.py):
   • окна салона: у исходника это сквозные круглые проёмы. Накладываем по обшивке (проекцией вдоль бортовой оси):
       Ми-8АМТ — круглое тёмное стекло со светлым ободком (как на RA-24187);
       Ми-171 VIP — прямоугольные окна со скруглёнными углами в серебристых рамках (как на RA-25565);
     стекло — меши m:'window' (непрозрачное тонированное с отражениями), рамки — плашки палитры атласа;
   • остекление кабины: стекло в проёмах обшивки (лобовые, боковые, блистеры, нижние окна носа) — m:'glass';
   • выхлопные патрубки двигателей под несущим винтом (у Mi-8AMTSh на их месте были экраны ЭВУ — удалены);
   • Ми-171: обтекатель метеорадара под носом;
   • материал модели: у Ми-171 — металлик (краска «вишня металлик»).
     python3 build/import/mi8_extras.py mi8amt|mi171
"""
import os, sys, json, math
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mi8_geom
from pack_as350 import Part, pack_mesh

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, 'build', 'import', 'mi8amtsh', 'scene.gltf')
SKIN = ('sub01_0', 'sub02_0')

def skin_triangles(G):
    T = []
    for g, P, N, UV, I in G['prims']:
        if g in SKIN: T.append(P[I.reshape(-1, 3)])
    return np.concatenate(T)

class Projector:
    """Поверхность обшивки вокруг окна: z = f(x, y) — квадратичная аппроксимация по вершинам обшивки
       в радиусе 0.55 м (в самом проёме обшивки нет — там дыра, поэтому не лучом, а по гладкой поверхности)."""
    def __init__(self, tris, center, side, rad=0.55):
        V = tris.reshape(-1, 3); cx, cy = center
        m = (np.hypot(V[:, 0] - cx, V[:, 1] - cy) < rad) & (V[:, 2] * side > 0.3)
        q = V[m]
        # на своей стороне берём только внешнюю поверхность (максимальная |z| в окрестности)
        self.c = np.array(center)
        X, Y = q[:, 0] - cx, q[:, 1] - cy
        A = np.stack([np.ones_like(X), X, Y, X * X, X * Y, Y * Y], -1)
        zs = q[:, 2] * side; keep = np.ones(len(q), bool)
        for _ in range(8):   # итерации: отбрасываем точки под внешней огибающей (стенки проёма, внутренняя обшивка)
            k, *_ = np.linalg.lstsq(A[keep], zs[keep], rcond=None)
            res = zs - A @ k
            keep = res > -0.006
        self.k = k * side
        self.rms = float(np.sqrt(np.mean(res[keep] ** 2))); self.side = side; self.n_used = int(keep.sum())
    def project(self, xy, side):
        X, Y = xy[:, 0] - self.c[0], xy[:, 1] - self.c[1]; k = self.k
        z = k[0] + k[1] * X + k[2] * Y + k[3] * X * X + k[4] * X * Y + k[5] * Y * Y
        fx = k[1] + 2 * k[3] * X + k[4] * Y; fy = k[2] + k[4] * X + 2 * k[5] * Y
        n = np.stack([-fx, -fy, np.ones_like(fx)], -1) * side
        n /= np.linalg.norm(n, axis=1, keepdims=True)
        return np.stack([xy[:, 0], xy[:, 1], z], -1), n

def rounded_rect(w, h, r, n_corner=10):
    """Контур прямоугольника со скруглёнными углами (против часовой, начиная справа-снизу)."""
    pts = []
    for cx, cy, a0 in ((w / 2 - r, -h / 2 + r, -90), (w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90), (-w / 2 + r, -h / 2 + r, 180)):
        for i in range(n_corner + 1):
            a = math.radians(a0 + 90 * i / n_corner); pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return np.array(pts)

def circle(r, n=48):
    a = np.linspace(0, 2 * np.pi, n, endpoint=False); return np.stack([r * np.cos(a), r * np.sin(a)], -1)

def ring_tris(outer, inner):
    """Полоса между двумя контурами с одинаковым числом точек → треугольники (индексы 2n точек)."""
    n = len(outer); t = []
    for i in range(n):
        j = (i + 1) % n
        t += [(i, j, n + j), (i, n + j, n + i)]
    return np.array(t)

def disc_tris(contours):
    """Вложенные контуры (от внешнего к внутреннему) + центр — «веером» по кольцам (без провисания на изгибе обшивки)."""
    n = len(contours[0]); t = []; base = 0
    for k in range(len(contours) - 1):
        for i in range(n):
            j = (i + 1) % n
            t += [(base + i, base + j, base + n + j), (base + i, base + n + j, base + n + i)]
        base += n
    c = base + n
    for i in range(n): t.append((base + i, base + (i + 1) % n, c))
    return np.array(t)

def patch(proj, center, side, shape2d_list, tris_idx, offset):
    """Контуры в локальных (dx, dy) → точки на обшивке + сдвиг по нормали."""
    xy = np.vstack(shape2d_list) + np.array(center)
    P, N = proj.project(xy, side)
    P = P + N * offset
    T = tris_idx if side > 0 else tris_idx[:, ::-1]        # на левом борту — обратный обход (лицевая сторона наружу)
    return P[T], N[T]

# ---------------- остекление кабины: стекло в проёмах обшивки (у исходника проёмы пустые) ----------------
def ear_clip(p2):
    """Триангуляция простого многоугольника (2D, любой обход) отсечением «ушей»."""
    n = len(p2)
    area = 0.5 * np.sum(p2[:, 0] * np.roll(p2[:, 1], -1) - np.roll(p2[:, 0], -1) * p2[:, 1])
    idx = list(range(n)) if area > 0 else list(range(n))[::-1]
    cross = lambda a, b, c: (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    def inside(p, a, b, c):
        return cross(a, b, p) >= -1e-12 and cross(b, c, p) >= -1e-12 and cross(c, a, p) >= -1e-12
    tris = []
    while len(idx) > 3:
        for k in range(len(idx)):
            i0, i1, i2 = idx[k - 1], idx[k], idx[(k + 1) % len(idx)]
            a, b, c = p2[i0], p2[i1], p2[i2]
            if cross(a, b, c) <= 1e-12: continue
            if any(inside(p2[j], a, b, c) for j in idx if j not in (i0, i1, i2)): continue
            tris.append((i0, i1, i2)); idx.pop(k); break
        else:                                   # вырожденный остаток — веером
            tris += [(idx[0], idx[k], idx[k + 1]) for k in range(1, len(idx) - 1)]; idx = []
    if len(idx) == 3: tris.append(tuple(idx))
    return np.array(tris)

def membrane(q, levels=2, iters=160):
    """Стекло по замкнутому контуру: триангуляция в плоскости наилучшего приближения, измельчение и
       гармоническое сглаживание внутренних вершин (плёнка, натянутая на кромку проёма, — повторяет её изгиб)."""
    c = q.mean(0); _, _, Vt = np.linalg.svd(q - c)
    V = [v for v in q]; T = [tuple(t) for t in ear_clip((q - c) @ Vt[:2].T)]
    fixed = set(range(len(q)))
    bedges = {(i, (i + 1) % len(q)) for i in range(len(q))}; bedges |= {(b, a) for a, b in bedges}
    for _ in range(levels):
        mid = {}; T2 = []
        def m(a, b):
            k = (min(a, b), max(a, b))
            if k not in mid:
                mid[k] = len(V); V.append((V[a] + V[b]) / 2)
                if (a, b) in bedges: fixed.add(mid[k]); bedges.update({(a, mid[k]), (mid[k], a), (b, mid[k]), (mid[k], b)})
            return mid[k]
        for a, b, cc in T:
            ab, bc, ca = m(a, b), m(b, cc), m(cc, a)
            T2 += [(a, ab, ca), (ab, b, bc), (ca, bc, cc), (ab, bc, ca)]
        T = T2
    V = np.array(V); T = np.array(T)
    nb = [set() for _ in V]
    for a, b, cc in T: nb[a] |= {b, cc}; nb[b] |= {a, cc}; nb[cc] |= {a, b}
    free = [i for i in range(len(V)) if i not in fixed]
    nbl = [list(nb[i]) for i in free]
    for _ in range(iters):
        V[free] = np.array([V[l].mean(0) for l in nbl])
    return V, T

def vertex_normals(V, T):
    fn = np.cross(V[T[:, 1]] - V[T[:, 0]], V[T[:, 2]] - V[T[:, 0]])
    N = np.zeros_like(V)
    for k in range(3): np.add.at(N, T[:, k], fn)
    return N / (np.linalg.norm(N, axis=1, keepdims=True) + 1e-12)

def cockpit_glass(G):
    glass = Part('cockpit_glass', None, 'glass')
    uv = np.array(mi8_geom.pal_uv('frame'))
    for q in mi8_geom.cockpit_loops(G):
        V, T = membrane(q)
        c = q.mean(0); out = c - np.array([c[0] - 1.0, 1.9, 0.0])       # «наружу»: вперёд и в сторону от оси кабины
        N = vertex_normals(V, T)
        if (N @ out).mean() < 0: T = T[:, ::-1]; N = -N
        for t in T: glass.add(V[t], N[t], np.tile(uv, (3, 1)))
    print('  остекление кабины: проёмов %d, треугольников %d' % (len(mi8_geom.cockpit_loops(G)), sum(len(p) for p in glass.P)))
    return glass

# ---------------- обтекатель метеорадара под носом (Ми-171 RA-25565) ----------------
def radome():
    part = Part('radome', None, 'paint'); uv = np.array(mi8_geom.pal_uv('radome'))
    C = np.array([5.60, 1.27, 0.0]); af, ar, b, cz = 0.62, 0.95, 0.21, 0.33      # передняя/задняя полуось, высота, ширина
    nu, nv = 28, 40
    u = np.linspace(0, np.pi, nu); v = np.linspace(0, 2 * np.pi, nv, endpoint=False)
    U, W = np.meshgrid(u, v, indexing='ij')
    a = np.where(np.cos(U) >= 0, af, ar)
    X = np.stack([C[0] + a * np.cos(U), C[1] + b * np.sin(U) * np.cos(W), C[2] + cz * np.sin(U) * np.sin(W)], -1)
    Nn = np.stack([(X[..., 0] - C[0]) / a ** 2, (X[..., 1] - C[1]) / b ** 2, (X[..., 2] - C[2]) / cz ** 2], -1)
    Nn[0] = [1, 0, 0]; Nn[-1] = [-1, 0, 0]
    Nn /= np.linalg.norm(Nn, axis=-1, keepdims=True)
    for i in range(nu - 1):
        for j in range(nv):
            j2 = (j + 1) % nv
            for t in (((i, j), (i + 1, j), (i + 1, j2)), ((i, j), (i + 1, j2), (i, j2))):
                P3 = np.array([X[k] for k in t]); N3 = np.array([Nn[k] for k in t])
                if np.linalg.norm(np.cross(P3[1] - P3[0], P3[2] - P3[0])) < 1e-10: continue
                if np.dot(np.cross(P3[1] - P3[0], P3[2] - P3[0]), N3.sum(0)) < 0: P3 = P3[::-1]; N3 = N3[::-1]
                part.add(P3, N3, np.tile(uv, (3, 1)))
    return part

# ---------------- выхлопные патрубки двигателей под несущим винтом (ЭВУ у гражданских бортов нет) ----------------
def tube(part, A, d, r, length, n, uvf, inward=False):
    """Цилиндр радиуса r от точки A вдоль d на length; uvf(t) — UV по доле длины; inward — нормали к оси."""
    e1 = np.cross(d, [0, 1, 0]); e1 /= np.linalg.norm(e1); e2 = np.cross(d, e1)
    ang = np.linspace(0, 2 * np.pi, n, endpoint=False)
    ring = np.cos(ang)[:, None] * e1 + np.sin(ang)[:, None] * e2
    ts = np.linspace(0, 1, 7)
    for k in range(len(ts) - 1):
        for j in range(n):
            j2 = (j + 1) % n
            quad = [(k, j), (k + 1, j), (k + 1, j2), (k, j2)]
            P = np.array([A + d * length * ts[a] + ring[b] * r for a, b in quad])
            N = np.array([ring[b] * (-1 if inward else 1) for a, b in quad])
            UV = np.array([uvf(ts[a]) for a, b in quad])
            for t in ((0, 1, 2), (0, 2, 3)):
                t = np.array(t)
                P3, N3, U3 = P[t], N[t], UV[t]
                if np.dot(np.cross(P3[1] - P3[0], P3[2] - P3[0]), N3.sum(0)) < 0: P3, N3, U3 = P3[::-1], N3[::-1], U3[::-1]
                part.add(P3, N3, U3)
    return ring, e1, e2

def annulus(part, C, d, r0, r1, n, uv0, uv1):
    e1 = np.cross(d, [0, 1, 0]); e1 /= np.linalg.norm(e1); e2 = np.cross(d, e1)
    ang = np.linspace(0, 2 * np.pi, n, endpoint=False); ring = np.cos(ang)[:, None] * e1 + np.sin(ang)[:, None] * e2
    for j in range(n):
        j2 = (j + 1) % n
        P = np.array([C + ring[j] * r0, C + ring[j] * r1, C + ring[j2] * r1, C + ring[j2] * r0])
        UV = np.array([uv0, uv1, uv1, uv0])
        for t in ((0, 1, 2), (0, 2, 3)):
            t = np.array(t); P3 = P[t]; U3 = UV[t]
            if np.dot(np.cross(P3[1] - P3[0], P3[2] - P3[0]), d) < 0: P3, U3 = P3[::-1], U3[::-1]
            part.add(P3, np.tile(d, (3, 1)), U3)

def exhausts():
    """Патрубок: наружная труба (жаростойкая сталь), кромка среза, внутренняя поверхность с цветами побежалости
       (бронза у среза → копоть в глубине), дно с конусом. Направлен наружу, немного назад и вверх."""
    part = Part('exhausts', None, 'paint')
    metal = np.array(mi8_geom.pal_uv('exh_metal')); soot = np.array(mi8_geom.pal_uv('exh_soot'))
    e = mi8_geom.EXHAUST; Ro, Ri, L, D = e['Ro'], e['Ri'], e['L'], e['D']
    for side in (+1, -1):
        d = np.array(e['d'], float) * [1, 1, side]; d /= np.linalg.norm(d)
        S = np.array([e['x'], e['y'], e['z'] * side])          # точка на капоте (обшивка внутри патрубка вырезана — mi8_geom)
        E = S + d * L                                          # срез
        tube(part, S - d * 0.30, d, Ro, L + 0.30, 40, lambda t: metal)              # наружная труба (корень — в капоте)
        annulus(part, E, d, Ri, Ro, 40, metal, metal)                                # кромка
        tube(part, E - d * D, d, Ri, D, 40, lambda t: mi8_geom.exh_uv(1 - t), inward=True)   # внутренняя поверхность
        annulus(part, E - d * D, d, 0.0, Ri, 40, soot, soot)                          # дно
        # конус выходного устройства в глубине
        cone = Part('tmp', None, 'paint'); tube(cone, E - d * D, d, 0.11, 0.12, 24, lambda t: soot)
        annulus(cone, E - d * (D - 0.12), d, 0.0, 0.11, 24, soot, soot)
        for P3, N3, U3 in zip(cone.P, cone.N, cone.UV): part.add(P3, N3, U3)
    return part

def build(key):
    G = mi8_geom.load(SRC)
    tris = skin_triangles(G)
    glass = Part('windows', None, 'window'); frame = Part('window_frames', None, 'paint')
    uv_frame = np.array(mi8_geom.pal_uv('frame' if key == 'mi171' else 'rim'))
    for cx, cy in mi8_geom.CABIN_WINDOWS:
        for side in (+1, -1):
            proj = Projector(tris, (cx, cy), side)
            print('  окно x=%.2f %s борт: отклонение поверхности %.1f мм' % (cx, 'правый' if side > 0 else 'левый', proj.rms * 1000))
            if key == 'mi171':
                W, Hh, R, F = 0.50, 0.62, 0.10, 0.042
                outer = rounded_rect(W, Hh, R); inner = rounded_rect(W - 2 * F, Hh - 2 * F, R - F * 0.6)
                rings = [inner * s for s in (1.0, 0.72, 0.45, 0.2)] + [np.zeros((1, 2))]
            else:
                outer = circle(mi8_geom.WINDOW_R + 0.028); inner = circle(mi8_geom.WINDOW_R + 0.004)
                rings = [inner * s for s in (1.0, 0.66, 0.33)] + [np.zeros((1, 2))]
            # рамка / ободок
            P3, N3 = patch(proj, (cx, cy), side, [outer, inner], ring_tris(outer, inner), 0.010)
            for p, n in zip(P3, N3): frame.add(p, n, np.tile(uv_frame, (3, 1)))
            # стекло (слегка утоплено относительно рамки)
            P3, N3 = patch(proj, (cx, cy), side, rings, disc_tris(rings[:-1]), 0.008)
            for p, n in zip(P3, N3): glass.add(p, n, np.tile(uv_frame, (3, 1)))
    import mi8_nose
    nf, nw = mi8_nose.parts(G, np.array(mi8_geom.pal_uv('frame' if key == 'mi171' else 'strut')), Part)
    parts = [frame, glass, cockpit_glass(G), nf, nw, exhausts()]
    if key == 'mi171': parts.append(radome())
    return parts

def main(key):
    path = os.path.join(ROOT, 'site', 'models', key + '.js')
    s = open(path, encoding='utf-8').read()
    head = 'AltayModels[%s]=' % json.dumps(key)
    i = s.index(head) + len(head); data = json.loads(s[i:].rstrip().rstrip(';'))
    data['meshes'] = [m for m in data['meshes'] if m['n'] not in ('windows', 'window_frames', 'cockpit_glass', 'radome', 'exhausts', 'nose_windows', 'nose_window_frames')]   # повторный запуск
    for part in build(key):
        m, t, b = pack_mesh(part, np.zeros(3)); data['meshes'].append(m)
        print('  %s: треугольников %d' % (part.name, t))
    if key == 'mi171': data['mat'] = {'metalness': 0.45, 'roughness': 0.3}     # «вишня металлик»
    else: data.pop('mat', None)
    data['glass'] = {'color': 0x0c1318, 'opacity': 0.5}                          # остекление кабины: салон просвечивает, как на фото
    out = s[:s.index(head)] + head + json.dumps(data, separators=(',', ':')) + ';\n'
    open(path, 'w', encoding='utf-8').write(out)
    print('записано', path, '%.2f МБ' % (len(out.encode()) / 1e6))

if __name__ == '__main__':
    main(sys.argv[1])
