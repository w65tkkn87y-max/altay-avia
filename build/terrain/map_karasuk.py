#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Карта расположения вертодрома «Карасук» для страниц «Площадки» и «Контакты» — по реальным данным:
   рельеф SRTM (отмывка + горизонтали), снимок Sentinel-2 (EOX, CC BY 4.0), реки, дороги и населённые пункты
   OpenStreetMap (© участники OpenStreetMap, ODbL; выгрузка Overpass в build/terrain/cache/osm_karasuk.json).
   Направление и расстояние до Горно-Алтайска: по прямой — геодезически, по дороге — маршрут OSRM по данным OSM.
     python3 build/terrain/map_karasuk.py → site/img/map/karasuk-relief.jpg, karasuk-sat.jpg, build/terrain/karasuk_map.svg"""
import json, math, os, sys
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import geo
from topo_svg import contours, simplify, blur
sys.setrecursionlimit(20000)

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HERE = os.path.dirname(os.path.abspath(__file__))
X0, X1 = -9000.0, 7000.0          # запад … восток, м от вертодрома
Z0, Z1 = -8800.0, 4000.0          # север … юг (z — на юг)
W = 800; H = round(W * (Z1 - Z0) / (X1 - X0))
S = W / (X1 - X0)                 # единиц viewBox на метр
KARASUK = (51.5607, 85.9176)      # центр вертодрома (OSM: aerodrome UNCX «Карасук (АлтайАвиа)»)
GA = (51.957775, 85.963653)       # Горно-Алтайск
ROAD_KM, ROAD_MIN = 77, 75        # OSRM: Горно-Алтайск → Чуйский тракт → Усть-Сема → Чемальский тракт → Карасук

def xy(lat, lon):
    x = (np.asarray(lon) - geo.LON0) * geo.M_PER_DEG_LON; z = (geo.LAT0 - np.asarray(lat)) * geo.M_PER_DEG_LAT
    return (x - X0) * S, (z - Z0) * S

def backgrounds():
    n = 2; gw, gh = W * n, H * n
    xs = np.linspace(X0, X1, gw); zs = np.linspace(Z0, Z1, gh); zz, xx = np.meshgrid(zs, xs, indexing='ij')
    h = geo.height(xx, zz).astype(float)
    # отмывка: несколько источников света (мягко), + лёгкая гипсометрия
    px = (X1 - X0) / gw
    gy, gx = np.gradient(blur(h, 1), px)
    shade = np.zeros_like(h)
    for az, wgt in ((315, .55), (270, .2), (0, .25)):
        a = math.radians(az); alt = math.radians(42)
        lx, ly, lz = math.cos(alt) * math.sin(a), -math.cos(alt) * math.cos(a), math.sin(alt)   # y (строки) — на юг
        nrm = np.sqrt(gx ** 2 + gy ** 2 + 1)
        shade += wgt * np.clip((-gx * lx - gy * ly + lz) / nrm, 0, 1)
    t = np.clip((h - 350) / 900, 0, 1)[..., None]
    low, high = np.array([236, 243, 238], float), np.array([222, 231, 244], float)
    base = low * (1 - t) + high * t
    rgb = base * (0.72 + 0.34 * shade[..., None])
    rgb = np.clip(rgb, 0, 255).astype(np.uint8)
    out = os.path.join(ROOT, 'site', 'img', 'map'); os.makedirs(out, exist_ok=True)
    Image.fromarray(rgb).save(os.path.join(out, 'karasuk-relief.jpg'), quality=84, optimize=True, progressive=True)
    # снимок Sentinel-2
    s2 = geo.Mosaic('s2', 14); lat, lon = geo.to_latlon(xx, zz)
    sat = np.clip(s2.sample(lat, lon) * 1.12 + 6, 0, 255).astype(np.uint8)
    Image.fromarray(sat).save(os.path.join(out, 'karasuk-sat.jpg'), quality=80, optimize=True, progressive=True)
    return h, xs, zs

def path_d(pts, close=False):
    pts = simplify([(float(a), float(b)) for a, b in pts], 0.35)
    return 'M' + 'L'.join('%.1f %.1f' % p for p in pts) + ('Z' if close else '')

def main():
    h, xs, zs = backgrounds()
    osm = json.load(open(os.path.join(HERE, 'cache', 'osm_karasuk.json'), encoding='utf-8'))['elements']
    geom = lambda e: xy([p['lat'] for p in e['geometry']], [p['lon'] for p in e['geometry']])
    water, rivers, streams, roads_main, roads_minor, places = [], [], [], [], [], []
    for e in osm:
        t = e.get('tags', {})
        if e['type'] == 'relation' and t.get('natural') == 'water':
            # мультиполигон: участки контура — отдельные линии, склеиваем их в замкнутые кольца (внешние и острова)
            rings = []
            for role in ('outer', 'inner'):
                segs = [[(p['lat'], p['lon']) for p in m['geometry']] for m in e.get('members', []) if m.get('role') == role and m.get('geometry')]
                while segs:
                    ring = segs.pop(0)
                    while ring[0] != ring[-1]:
                        for k, sg in enumerate(segs):
                            if sg[0] == ring[-1]: ring += sg[1:]; segs.pop(k); break
                            if sg[-1] == ring[-1]: ring += sg[::-1][1:]; segs.pop(k); break
                        else: break
                    if ring[0] == ring[-1]:
                        X, Y = xy([a for a, b in ring], [b for a, b in ring]); rings.append(list(zip(X, Y)))
            if rings: water.append(rings)
        elif e['type'] == 'way' and t.get('natural') == 'water' and e.get('geometry'):
            X, Y = geom(e); water.append([list(zip(X, Y))])
        elif e['type'] == 'way' and t.get('waterway') == 'river':
            X, Y = geom(e); rivers.append((t.get('name', ''), list(zip(X, Y))))
        elif e['type'] == 'way' and t.get('waterway') == 'stream' and t.get('name'):
            X, Y = geom(e); streams.append(list(zip(X, Y)))
        elif e['type'] == 'way' and t.get('highway') in ('trunk', 'primary', 'secondary', 'secondary_link'):
            X, Y = geom(e); roads_main.append((t.get('name', ''), list(zip(X, Y))))
        elif e['type'] == 'way' and t.get('highway') in ('tertiary', 'unclassified'):
            X, Y = geom(e); roads_minor.append(list(zip(X, Y)))
        elif e['type'] == 'node' and t.get('place') in ('village', 'hamlet', 'town'):
            X, Y = xy(e['lat'], e['lon']); places.append((t['name'], t['place'], float(X), float(Y)))
    # горизонтали 100 м (утолщённые — 500 м) в координатах карты
    hh = blur(h, 2); ny, nx = hh.shape; sx, sy = W / (nx - 1), H / (ny - 1); cth, ctk = [], []
    for lev in range(400, int(hh.max()) + 1, 100):
        for line in contours(hh, lev):
            if len(line) < 6: continue
            d = path_d([(j * sx, i * sy) for i, j in line]); (ctk if lev % 500 == 0 else cth).append(d)
    kx, ky = [float(v) for v in xy(*KARASUK)]
    # Горно-Алтайск: по прямой (азимут) и выход дороги с карты (Чемальский тракт на северо-запад, к Усть-Семе)
    gx, gy = [float(v) for v in xy(*GA)]
    brg = (math.degrees(math.atan2(gx - kx, -(gy - ky))) + 360) % 360
    dist = math.hypot((gx - kx) / S, (gy - ky) / S) / 1000
    exit_pt = None   # где Чемальский тракт уходит за край карты в сторону Усть-Семы (запад/север)
    inside = lambda p: 0 <= p[0] <= W and 0 <= p[1] <= H
    for name, pts in roads_main:
        if 'Чемальский' not in name: continue
        for a, b in zip(pts[:-1], pts[1:]):
            if inside(a) == inside(b): continue
            pin, pout = (a, b) if inside(a) else (b, a)
            for k in np.linspace(0, 1, 200):
                q = (pin[0] + (pout[0] - pin[0]) * k, pin[1] + (pout[1] - pin[1]) * k)
                if not inside(q): break
                c = q
            if exit_pt is None or c[0] + c[1] < exit_pt[0] + exit_pt[1]: exit_pt = c
    if exit_pt: exit_pt = (max(exit_pt[0], 4), max(exit_pt[1], 4))
    parts = []
    A = parts.append
    A('<svg class="geo-map" viewBox="0 0 %d %d" preserveAspectRatio="xMidYMid slice" role="img" aria-label="Карта: вертодром «Карасук» в долине Катуни, 44 км к югу от Горно-Алтайска">' % (W, H))
    A('<defs><radialGradient id="kpulse"><stop offset="0" stop-color="#1E6FD9" stop-opacity=".35"/><stop offset="1" stop-color="#1E6FD9" stop-opacity="0"/></radialGradient>'
      '<marker id="arr" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L10 5L0 10z" fill="#0B2350"/></marker></defs>')
    A('<image class="map-relief" href="__ROOT__img/map/karasuk-relief.jpg" width="%d" height="%d" preserveAspectRatio="none"/>' % (W, H))
    A('<image class="map-sat" href="__ROOT__img/map/karasuk-sat.jpg" width="%d" height="%d" preserveAspectRatio="none"/>' % (W, H))
    A('<g class="map-vec">')
    A('<g fill="none" stroke="#6B80A0" stroke-linejoin="round"><path stroke-width=".45" stroke-opacity=".35" d="%s"/><path stroke-width=".9" stroke-opacity=".45" d="%s"/></g>' % (''.join(cth), ''.join(ctk)))
    A('<g fill="#9CC3F5" stroke="#6FA6E8" stroke-width=".6" fill-rule="evenodd">' + ''.join('<path d="%s"/>' % ''.join(path_d(r, True) for r in rings) for rings in water) + '</g>')
    A('<g fill="none" stroke="#6FA6E8" stroke-linecap="round" stroke-linejoin="round"><path stroke-width=".8" stroke-opacity=".8" d="%s"/><path stroke-width="2.4" d="%s"/></g>' % (
        ''.join(path_d(p) for p in streams), ''.join(path_d(p) for n, p in rivers)))
    A('<g fill="none" stroke-linecap="round" stroke-linejoin="round"><path stroke="#fff" stroke-width="2.2" d="%s"/><path stroke="#9AA8BC" stroke-width="1" d="%s"/></g>' % (
        ''.join(path_d(p) for p in roads_minor), ''.join(path_d(p) for p in roads_minor)))
    main_d = ''.join(path_d(p) for n, p in roads_main)
    A('<g fill="none" stroke-linecap="round" stroke-linejoin="round"><path stroke="#fff" stroke-width="5" d="%s"/><path class="map-road" stroke="#F4B23E" stroke-width="3" d="%s"/></g>' % (main_d, main_d))
    A('</g>')
    # подписи рек и дорог
    A('<g class="map-lbl">')
    # населённые пункты
    shown = {'Чепош', 'Узнезя', 'Аскат', 'Анос', 'Бешпельтир', 'Турбаза «Катунь»', 'Усть-Сема', 'Барангол', 'Элекмонар'}
    for name, kind, px, py in places:
        if name not in shown or not (8 < px < W - 8 and 8 < py < H - 8): continue
        big = kind == 'village'
        A('<g class="map-place" transform="translate(%.1f %.1f)"><circle r="%s"/><text x="7" y="4"%s>%s</text></g>' % (px, py, '3.6' if big else '2.6', '' if big else ' class="small"', name))
    A('</g>')
    # Горно-Алтайск: выход трассы и направление по прямой
    if exit_pt:
        ex, ey = exit_pt; ex = max(ex, 64); ey = min(max(ey, 96), H - 140)   # подпись — в безопасной зоне (карта обрезается по размеру блока)
        A('<g class="map-exit" transform="translate(%.1f %.1f)"><rect x="6" y="10" width="206" height="42" rx="9" fill="rgba(255,255,255,.92)" stroke="#C2D5EE"/>'
          '<text x="30" y="28">Горно-Алтайск</text><text class="sub" x="30" y="44">%d км по трассе · ~%d ч %02d мин</text>'
          '<path d="M22 40V20L10 8" fill="none" stroke="#0B2350" stroke-width="1.8" marker-end="url(#arr)"/></g>' % (ex, ey, ROAD_KM, ROAD_MIN // 60, ROAD_MIN % 60))
    # компас с направлением на Горно-Алтайск по прямой
    cx, cy = W - 110, 110
    A('<g class="map-compass" transform="translate(%d %d)"><circle r="34" fill="rgba(255,255,255,.88)" stroke="#C2D5EE"/><path d="M0 -26L6 0L0 -4L-6 0Z" fill="#0B2350"/><path d="M0 26L6 0L0 4L-6 0Z" fill="#C2D5EE"/>'
      '<text y="-38" text-anchor="middle">С</text>'
      '<g transform="rotate(%.1f)"><path d="M0 -8V-31" stroke="#1E6FD9" stroke-width="2" stroke-dasharray="3 3"/></g>'
      '<text class="sub" x="36" y="54" text-anchor="end">до Горно-Алтайска по прямой</text><text class="sub" x="36" y="67" text-anchor="end">%d км · азимут %d°</text></g>' % (cx, cy, brg, round(dist), round(brg)))
    # масштаб 2 км
    L = 2000 * S; bx, by = 70, H - 70
    A('<g class="map-scale" transform="translate(%d %d)"><path d="M0 0H%.1f" stroke="#0B2350" stroke-width="2"/><path d="M0 -5V0M%.1f -5V0M%.1f -3V0" stroke="#0B2350" stroke-width="1.5"/><text y="-9">2 км</text></g>' % (bx, by, L, L, L / 2))
    # вертодром
    A('<g class="map-pad" transform="translate(%.1f %.1f)"><circle class="pulse" r="30" fill="url(#kpulse)"/><circle class="pulse p2" r="30" fill="url(#kpulse)"/>'
      '<circle r="11" fill="#1E6FD9" stroke="#fff" stroke-width="2.5"/><text y="4.6" text-anchor="middle" class="h">H</text>'
      '<g transform="translate(16 -40)"><rect x="0" y="-20" width="198" height="44" rx="10" fill="#fff" stroke="#C2D5EE"/>'
      '<text x="12" y="-2" class="t">Вертодром «Карасук»</text><text x="12" y="15" class="sub">UNCX · 51°33′36″ N 85°55′03″ E</text></g></g>' % (kx, ky))
    A('<text class="map-attr" x="%d" y="%d" text-anchor="end">© участники OpenStreetMap · рельеф SRTM · снимок Sentinel-2 © EOX</text>' % (W - 70, H - 52))
    A('</svg>')
    svg = ''.join(parts)
    open(os.path.join(HERE, 'karasuk_map.svg'), 'w', encoding='utf-8').write(svg)
    print('карта %dx%d, %d КБ; Горно-Алтайск %.1f км, азимут %.0f°, выход трассы %s; воды %d, рек %d, дорог %d/%d, пунктов %d' % (
        W, H, len(svg.encode()) // 1024, dist, brg, exit_pt, len(water), len(rivers), len(roads_main), len(roads_minor), len(places)))

if __name__ == '__main__':
    main()
