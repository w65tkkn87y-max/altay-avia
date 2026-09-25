#!/usr/bin/env python3
"""Обрезка прозрачных полей у статичных рендеров img/3d/<m>.png, <m>-side.png и приведение к ширине 1400 px.
   python3 build/dev/trim_renders.py as350"""
import sys, os
from PIL import Image
D = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'site', 'img', '3d')
for key in sys.argv[1:]:
    for name in (key + '.png', key + '-side.png'):
        p = os.path.join(D, name); im = Image.open(p).convert('RGBA')
        a = im.split()[3].point(lambda v: 255 if v > 8 else 0); x0, y0, x1, y1 = a.getbbox()
        pad = 24; im = im.crop((max(0, x0 - pad), max(0, y0 - pad), min(im.width, x1 + pad), min(im.height, y1 + pad)))
        if im.width > 1400: im = im.resize((1400, round(im.height * 1400 / im.width)), Image.LANCZOS)
        im.save(p, optimize=True); print(name, im.size, round(os.path.getsize(p) / 1024), 'КБ')
