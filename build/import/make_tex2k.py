#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Облегчённые текстуры бортов для телефонов: site/models/<key>_2k.jpg (вдвое меньше по стороне) и поле "tex2k"
   в данных модели (site/models/<key>.js). Просмотрщик берёт их при lowTex (экран ≤ 820 px или экономия трафика).
     python3 build/import/make_tex2k.py [key …]   (по умолчанию — все модели в site/models)"""
import os, sys, json, glob
from PIL import Image
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
M = os.path.join(ROOT, 'site', 'models')
keys = sys.argv[1:] or [os.path.basename(p)[:-3] for p in glob.glob(os.path.join(M, '*.js'))]
for key in keys:
    path = os.path.join(M, key + '.js'); s = open(path, encoding='utf-8').read()
    head = 'AltayModels[%s]=' % json.dumps(key); i = s.index(head) + len(head)
    data = json.loads(s[i:].rstrip().rstrip(';'))
    src = os.path.join(M, data['tex']); name2k = data['tex'].rsplit('.', 1)[0] + '_2k.jpg'
    im = Image.open(src).convert('RGB'); im = im.resize((im.width // 2, im.height // 2), Image.LANCZOS)
    im.save(os.path.join(M, name2k), quality=86, optimize=True, progressive=True)
    data['tex2k'] = name2k
    open(path, 'w', encoding='utf-8').write(s[:s.index(head)] + head + json.dumps(data, separators=(',', ':')) + ';\n')
    print('%s: %s %d КБ → %s %d КБ' % (key, data['tex'], os.path.getsize(src) // 1024, name2k, os.path.getsize(os.path.join(M, name2k)) // 1024))
