#!/usr/bin/env python3
"""Загрузка открытых данных вокруг площадки «Карасук» (51°33′36″ N, 85°55′03″ E) в build/terrain/cache:
   • рельеф — AWS Terrain Tiles (terrarium PNG; источники SRTM и др., открытые данные), z=13;
   • снимок — Sentinel-2 cloudless 2016 от EOX (s2maps.eu, CC BY 4.0), z=14.
   python3 build/terrain/fetch_tiles.py"""
import math, os, subprocess, sys
LAT, LON = 51.5600, 85.9175
RADIUS_M = 9000
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cache')
def tile_xy(lat, lon, z):
    n = 2 ** z; return (lon + 180) / 360 * n, (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n
def fetch(url, path):
    if os.path.exists(path) and os.path.getsize(path) > 0: return False
    subprocess.run(['curl', '-s', '-f', '--max-time', '60', '-o', path, url], check=True); return True
def tiles(z):
    mpp = 156543.03 * math.cos(math.radians(LAT)) / 2 ** z; r = RADIUS_M / (256 * mpp)
    fx, fy = tile_xy(LAT, LON, z)
    return [(x, y) for y in range(int(fy - r), int(fy + r) + 1) for x in range(int(fx - r), int(fx + r) + 1)]
if __name__ == '__main__':
    os.makedirs(D, exist_ok=True); n = 0
    for x, y in tiles(13):
        n += fetch('https://s3.amazonaws.com/elevation-tiles-prod/terrarium/13/%d/%d.png' % (x, y), os.path.join(D, 'dem_13_%d_%d.png' % (x, y)))
    for x, y in tiles(14):
        n += fetch('https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless_3857/default/g/14/%d/%d.jpg' % (y, x), os.path.join(D, 's2_14_%d_%d.jpg' % (x, y)))
    print('скачано новых файлов:', n, '| всего в кэше:', len(os.listdir(D)))
