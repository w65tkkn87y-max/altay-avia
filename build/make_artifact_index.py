#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Готовит главную страницу для публикации как артефакт claude.ai (build/artifact-index.html):
   обёртка <!DOCTYPE>/<html>/<head>/<body> убирается (её добавляет сам сервис), а атрибуты <html data-models data-v>
   переносятся в инлайн-скрипт. Остальные страницы публикуются как есть (supporting files).
   Также пишет build/artifact_files.json — карту файлов для публикации (html/css/js/models)."""
import re, os, json
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, 'site')
s = open(os.path.join(SITE, 'index.html'), encoding='utf-8').read()
m = re.search(r'<html[^>]*data-models="([^"]*)"[^>]*data-v="([^"]*)"', s)
models, v = (m.group(1), m.group(2)) if m else ('', '1')
s = re.sub(r'<!DOCTYPE html>\s*', '', s); s = re.sub(r'<html[^>]*>\s*', '', s); s = s.replace('</html>', '')
s = re.sub(r'<head>\s*', '', s); s = s.replace('</head>', ''); s = re.sub(r'<body>\s*', '', s); s = s.replace('</body>', '')
s = re.sub(r'<meta charset="utf-8">\s*<meta name="viewport"[^>]*>\s*', '', s)
inject = f'<script>document.documentElement.dataset.models="{models}";document.documentElement.dataset.v="{v}";</script>'
s = re.sub(r'(<link rel="stylesheet" href="css/main\.css[^"]*">)', r'\1\n' + inject, s, 1)
open(os.path.join(ROOT, 'build', 'artifact-index.html'), 'w', encoding='utf-8').write(s.strip() + '\n')
files = {}
for d, _, fs in os.walk(SITE):
    for f in fs:
        rel = os.path.relpath(os.path.join(d, f), SITE)
        if rel == 'index.html' or f.startswith('.'): continue
        if rel.endswith(('.html', '.css', '.js', '.jpg')) and (rel.startswith(('css/', 'js/', 'models/', 'vertolety/', 'ekskursii/')) or '/' not in rel):
            files[rel] = rel
for old in ('models/mi171.json', 'models/mi8amt.json'): files[old] = None   # убрать устаревшие файлы из артефакта
json.dump(files, open(os.path.join(ROOT, 'build', 'artifact_files.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
print('artifact-index.html:', round(os.path.getsize(os.path.join(ROOT, 'build', 'artifact-index.html')) / 1e3), 'КБ; models =', models, '; v =', v, '; files:', len(files))
