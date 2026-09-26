# -*- coding: utf-8 -*-
"""Адаптивные картинки: WebP в нескольких ширинах (site/img/_opt/…) и обёртка <img> → <picture> при записи страниц.
   Браузер сам выбирает файл под ширину экрана и плотность пикселей; старые браузеры берут исходный JPG/PNG.
   Варианты пересобираются, только если исходник новее (быстро при повторной сборке)."""
import os, re
from PIL import Image

SITE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'site')
OPT = os.path.join(SITE, 'img', '_opt')
WIDTHS = (480, 960, 1600)
SKIP = ('img/misc/', 'img/_opt/')          # логотипы и значки — маленькие PNG, оставляем как есть
_info = {}

def variants(rel):
    """rel — путь от site/ (img/…/x.jpg) → [(ширина, путь webp от site/)], размеры исходника; None — не обрабатываем."""
    if rel in _info: return _info[rel]
    src = os.path.join(SITE, rel)
    if rel.startswith(SKIP) or not os.path.isfile(src): _info[rel] = None; return None
    im = Image.open(src); W, H = im.size
    widths = sorted({w for w in WIDTHS if w < W * 0.85} | {min(W, WIDTHS[-1])})
    out = []
    base = os.path.splitext(rel[len('img/'):])[0]
    for w in widths:
        dst_rel = 'img/_opt/%s-%d.webp' % (base, w); dst = os.path.join(SITE, dst_rel)
        if not os.path.exists(dst) or os.path.getmtime(dst) < os.path.getmtime(src):
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            im2 = im.convert('RGBA' if im.mode in ('RGBA', 'LA', 'P') else 'RGB')
            if w < W: im2 = im2.resize((w, round(H * w / W)), Image.LANCZOS)
            im2.save(dst, 'WEBP', quality=78 if im2.mode == 'RGB' else 86, method=6)
        out.append((w, dst_rel))
    _info[rel] = (out, W, H)
    return _info[rel]

# «sizes» по классу ближайшего родителя: какую долю ширины экрана занимает картинка
SIZES = [
    (('page-band', 'bg', 'takeoff-bg', 'legs-bg', 'route-hero'), '100vw'),
    (('dest-pic',), '(max-width: 900px) 80vw, 380px'),
    (('porthole',), '(max-width: 900px) 78vw, 460px'),
    (('service-pic',), '(max-width: 520px) 100vw, (max-width: 980px) 50vw, 25vw'),
    (('about-main', 'dir-card'), '(max-width: 900px) 100vw, 50vw'),
    (('about-sub',), '(max-width: 900px) 50vw, 25vw'),
    (('pic',), '(max-width: 600px) 100vw, (max-width: 980px) 50vw, 33vw'),
    (('gallery-grid', 'photo-strip'), '(max-width: 900px) 50vw, 25vw'),
    (('docs-row',), '(max-width: 900px) 33vw, 15vw'),
    (('thumb',), '(max-width: 900px) 100vw, 220px'),
]
DEFAULT = '(max-width: 700px) 100vw, 50vw'
IMG = re.compile(r'<img\b[^>]*>')

def picturize(html, root):
    out, last = [], 0
    for m in IMG.finditer(html):
        tag = m.group(0)
        if 'class="keep"' in tag or 'data-no-opt' in tag or html[max(0, m.start() - 60):m.start()].rstrip().endswith('>') and '<picture' in html[max(0, m.start() - 200):m.start()] and '</picture>' not in html[max(0, m.start() - 200):m.start()]:
            continue
        sm = re.search(r'\bsrc="([^"]+\.(?:jpe?g|png))"', tag)
        if not sm or sm.group(1).startswith('http'): continue
        rel = sm.group(1)[len(root):] if root and sm.group(1).startswith(root) else sm.group(1)
        info = variants(rel)
        if not info: continue
        vs, W, H = info
        before = html[max(0, m.start() - 400):m.start()]
        cls = re.findall(r'class="([^"]*)"', before); cls = cls[-1] if cls else ''
        sizes = next((sz for keys, sz in SIZES if any(c == k or c.startswith(k + '-') for c in cls.split() for k in keys)), DEFAULT)
        srcset = ', '.join('%s%s %dw' % (root, p, w) for w, p in vs)
        new = tag
        if ' width=' not in tag: new = new.replace('<img', '<img width="%d" height="%d"' % (W, H), 1)
        if ' decoding=' not in new: new = new.replace('<img', '<img decoding="async"', 1)
        out.append(html[last:m.start()]); out.append('<picture><source type="image/webp" srcset="%s" sizes="%s">%s</picture>' % (srcset, sizes, new)); last = m.end()
    out.append(html[last:])
    return ''.join(out)
