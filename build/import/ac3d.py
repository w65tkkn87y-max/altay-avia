#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Минимальный парсер AC3D (.ac) — формат моделей FlightGear.
   load(path) → (materials, root); узел: dict(name, type, texture, texrep, texoff, rot(3x3), loc, crease, verts(N,3), surfs[(flags, mat, [(vi,u,v),…])], kids)
   world_meshes(root) → [(path, node, M4)] — мировые матрицы с учётом rot/loc всех родителей."""
import re, shlex
import numpy as np

def load(path):
    lines = open(path, 'rb').read().decode('latin-1').replace('\r\n', '\n').replace('\r', '\n').split('\n')
    i = 0
    mats = []
    def nxt():
        nonlocal i
        while i < len(lines) and not lines[i].strip(): i += 1
        l = lines[i] if i < len(lines) else ''; i += 1; return l
    head = nxt()
    assert head.startswith('AC3D'), head
    def parse_obj(first):
        nonlocal i
        node = {'type': first.split()[1], 'name': '', 'texture': None, 'texrep': (1.0, 1.0), 'texoff': (0.0, 0.0),
                'rot': np.eye(3), 'loc': np.zeros(3), 'crease': 61.0, 'verts': np.zeros((0, 3)), 'surfs': [], 'kids': []}
        while True:
            l = nxt(); t = l.split()
            if not t: continue
            k = t[0]
            if k == 'name': node['name'] = l.split(None, 1)[1].strip().strip('"')
            elif k == 'data':
                n = int(t[1]); s = ''
                while len(s) < n: s += lines[i] + '\n'; i += 1
            elif k == 'texture':
                m = re.match(r'texture\s+"([^"]*)"', l)
                if m: node['texture'] = m.group(1)          # битые строки без закрывающей кавычки пропускаем — берётся последняя целая
            elif k == 'texrep': node['texrep'] = (float(t[1]), float(t[2]))
            elif k == 'texoff': node['texoff'] = (float(t[1]), float(t[2]))
            elif k == 'rot': node['rot'] = np.array([float(x) for x in t[1:10]]).reshape(3, 3)
            elif k == 'loc': node['loc'] = np.array([float(x) for x in t[1:4]])
            elif k == 'crease': node['crease'] = float(t[1])
            elif k in ('url', 'subdiv', 'hidden', 'locked', 'folded'): pass
            elif k == 'numvert':
                n = int(t[1]); vs = np.empty((n, 3))
                for j in range(n): vs[j] = [float(x) for x in nxt().split()[:3]]
                node['verts'] = vs
            elif k == 'numsurf':
                for _ in range(int(t[1])):
                    s = nxt().split(); flags = int(s[1], 16); mat = 0; refs = []
                    while True:
                        l2 = nxt().split()
                        if l2[0] == 'mat': mat = int(l2[1])
                        elif l2[0] == 'refs':
                            for _r in range(int(l2[1])):
                                r = nxt().split(); refs.append((int(r[0]), float(r[1]) if len(r) > 1 else 0.0, float(r[2]) if len(r) > 2 else 0.0))
                            break
                    node['surfs'].append((flags, mat, refs))
            elif k == 'kids':
                for _ in range(int(t[1])):
                    node['kids'].append(parse_obj(nxt()))
                return node
            else:
                raise ValueError('неизвестный токен %r в строке %d' % (k, i))
    root = None
    while i < len(lines):
        l = nxt()
        if not l: break
        if l.startswith('MATERIAL'):
            name = re.match(r'MATERIAL\s+"([^"]*)"', l).group(1)
            t = l.split('"', 2)[2].split(); d = {}
            j = 0
            while j < len(t):
                key = t[j]
                if key in ('rgb', 'amb', 'emis', 'spec'): d[key] = [float(x) for x in t[j + 1:j + 4]]; j += 4
                else: d[key] = float(t[j + 1]); j += 2
            d['name'] = name; mats.append(d)
        elif l.startswith('OBJECT'):
            root = parse_obj(l)
    return mats, root

def world_meshes(root):
    out = []
    def walk(n, M, path):
        L = np.eye(4); L[:3, :3] = n['rot'].T; L[:3, 3] = n['loc']   # AC3D: rot — строки матрицы, v' = v·rot + loc
        W = M @ L; p = path + [n['name'] or n['type']]
        if len(n['verts']) and n['surfs']: out.append(('/'.join(p), n, W))
        for k in n['kids']: walk(k, W, p)
    walk(root, np.eye(4), [])
    return out
