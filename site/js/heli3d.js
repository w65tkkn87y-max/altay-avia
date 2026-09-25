/* ============================================================
   Heli3D v2 — 3D-модели вертолётов парка «АлтайАвиа»
   Eurocopter AS350 B3 (H125), Ми-8АМТ, Ми-171
   Построены по заводским размерам и фотографиям бортов компании.
   Требует three.js r128 (window.THREE). Необязательно: THREE.GLTFLoader —
   если в site/models/<key>.glb лежит готовая модель, она заменит процедурную.
   Система координат: X — вперёд (нос), Y — вверх, Z — правый борт. Земля y=0.
   ============================================================ */
(function (global) {
  'use strict';
  const T = global.THREE;
  if (!T) { console.error('Heli3D: THREE не найден'); return; }

  /* ---------- Лофт: корпус из последовательных сечений ----------
     station: { x, y, z, w, wb, h, hb, n, nb, u }
       w  — полуширина верхней половины, wb — нижней (по умолчанию = w)
       h  — полувысота вверх, hb — вниз
       n  — показатель суперэллипса верха (2 — эллипс, 3.5–4 — «коробка»), nb — низа
  ------------------------------------------------------------- */
  function loft(stationsIn, opts) {
    opts = opts || {};
    const segs = opts.segs || 48;
    let st = stationsIn.slice().sort((a, b) => a.x - b.x);
    if (opts.caps !== false) {
      const a = st[0], b = st[st.length - 1], eps = 0.003;
      st = [Object.assign({}, a, { x: a.x - eps, w: eps, wb: eps, h: eps, hb: eps, u: 0 }), ...st, Object.assign({}, b, { x: b.x + eps, w: eps, wb: eps, h: eps, hb: eps, u: 1 })];
    }
    const N = st.length, pos = [], uv = [], idx = [];
    const xmin = st[0].x, xmax = st[N - 1].x;
    for (let i = 0; i < N; i++) {
      const s = st[i];
      const n = s.n || 2, nb = s.nb || n;
      const hb = s.hb !== undefined ? s.hb : s.h;
      const wb = s.wb !== undefined ? s.wb : s.w;
      const uCoord = s.u !== undefined ? s.u : (s.x - xmin) / Math.max(1e-6, xmax - xmin);
      for (let j = 0; j <= segs; j++) {
        const t = j / segs, th = t * Math.PI * 2;
        const c = Math.cos(th), sn = Math.sin(th);
        const up = sn >= 0;
        const hh = up ? s.h : hb, ww = up ? s.w : wb, e = up ? n : nb;
        const pz = Math.sign(c) * Math.pow(Math.abs(c), 2 / e) * ww;
        const py = Math.sign(sn) * Math.pow(Math.abs(sn), 2 / e) * hh;
        pos.push(s.x, (s.y || 0) + py, (s.z || 0) + pz);
        uv.push(uCoord, t);
      }
    }
    for (let i = 0; i < N - 1; i++) for (let j = 0; j < segs; j++) {
      const a = i * (segs + 1) + j, b = a + 1, c = a + segs + 1, d = c + 1;
      idx.push(a, c, b, b, c, d);
    }
    const g = new T.BufferGeometry();
    g.setAttribute('position', new T.Float32BufferAttribute(pos, 3));
    g.setAttribute('uv', new T.Float32BufferAttribute(uv, 2));
    g.setIndex(idx);
    g.computeVertexNormals();
    return g;
  }

  /* Плоская деталь с контуром в плоскости XY, толщина по Z, с фаской */
  function slab(points, thickness, bevel) {
    const sh = new T.Shape();
    points.forEach((p, i) => i ? sh.lineTo(p[0], p[1]) : sh.moveTo(p[0], p[1]));
    sh.closePath();
    const b = bevel !== undefined ? bevel : thickness * 0.35;
    const g = new T.ExtrudeGeometry(sh, { depth: Math.max(0.001, thickness - 2 * b), bevelEnabled: true, bevelThickness: b, bevelSize: b, bevelSegments: 3, curveSegments: 16 });
    g.translate(0, 0, -(thickness - 2 * b) / 2);
    return g;
  }

  /* Лопасть: профиль, вытянутый вдоль +X (локально), корень в x=0 */
  function bladeGeometry(len, chord, thick, taper, droop) {
    taper = taper === undefined ? 1 : taper; droop = droop || 0;
    const st = [], n = 10;
    for (let i = 0; i <= n; i++) {
      const t = i / n, c = chord * (1 - (1 - taper) * t);
      st.push({ x: t * len, y: -droop * t * t, z: 0, w: c / 2, h: thick / 2 * (1 - 0.45 * t), hb: thick / 2 * (1 - 0.45 * t) * 0.55, n: 2.4 });
    }
    st.push({ x: len + chord * 0.1, y: -droop, z: 0, w: chord * taper * 0.3, h: thick * 0.1, hb: thick * 0.06, n: 2 });
    return loft(st, { segs: 14 });
  }

  function cyl(r1, r2, h, seg, open) { return new T.CylinderGeometry(r1, r2, h, seg || 24, 1, !!open); }
  function mesh(g, m, shadow) { const o = new T.Mesh(g, m); o.castShadow = shadow !== false; o.receiveShadow = false; return o; }
  function tube(points, r, closed, seg) {
    const curve = new T.CatmullRomCurve3(points.map(p => new T.Vector3(p[0], p[1], p[2])), !!closed, 'catmullrom', 0.3);
    return new T.TubeGeometry(curve, seg || 48, r, 12, !!closed);
  }
  function straight(a, b, r, mat, r2) {
    const A = new T.Vector3(a[0], a[1], a[2]), B = new T.Vector3(b[0], b[1], b[2]);
    const g = new T.CylinderGeometry(r2 !== undefined ? r2 : r, r, A.distanceTo(B), 14);
    const m = mesh(g, mat);
    m.position.copy(A).add(B).multiplyScalar(0.5);
    m.quaternion.setFromUnitVectors(new T.Vector3(0, 1, 0), B.clone().sub(A).normalize());
    return m;
  }

  /* ---------- Текстуры-ливреи через canvas ----------
     Развёртка лофта: u — вдоль оси X (0 = xmin, 1 = xmax); v — угол вокруг оси:
     v=0 правый борт (середина), 0.25 верх, 0.5 левый борт, 0.75 низ.
  --------------------------------------------------------------- */
  function makeCanvas(w, h) { const c = document.createElement('canvas'); c.width = w; c.height = h; return c; }
  function canvasTexture(c, aniso) {
    const t = new T.CanvasTexture(c); t.encoding = T.sRGBEncoding; t.anisotropy = aniso || 8;
    t.wrapS = T.RepeatWrapping; t.wrapT = T.RepeatWrapping; return t;
  }
  function painter(ctx, W, H) {
    const P = {
      ctx, W, H, X: u => u * W, Y: v => (1 - v) * H,
      rect(u0, v0, u1, v1, color) { ctx.fillStyle = color; ctx.fillRect(P.X(u0), P.Y(v1), (u1 - u0) * W, (v1 - v0) * H); },
      rrPath(u0, v0, u1, v1, r) {
        const x = P.X(u0), y = P.Y(v1), w = (u1 - u0) * W, h = (v1 - v0) * H; r = Math.min(r, w / 2, h / 2);
        ctx.beginPath(); ctx.moveTo(x + r, y); ctx.lineTo(x + w - r, y); ctx.quadraticCurveTo(x + w, y, x + w, y + r);
        ctx.lineTo(x + w, y + h - r); ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
        ctx.lineTo(x + r, y + h); ctx.quadraticCurveTo(x, y + h, x, y + h - r); ctx.lineTo(x, y + r); ctx.quadraticCurveTo(x, y, x + r, y); ctx.closePath();
      },
      rrect(u0, v0, u1, v1, r, color) { ctx.fillStyle = color; P.rrPath(u0, v0, u1, v1, r); ctx.fill(); },
      poly(pts, color) { ctx.fillStyle = color; ctx.beginPath(); pts.forEach((p, i) => i ? ctx.lineTo(P.X(p[0]), P.Y(p[1])) : ctx.moveTo(P.X(p[0]), P.Y(p[1]))); ctx.closePath(); ctx.fill(); },
      polyPath(pts) { ctx.beginPath(); pts.forEach((p, i) => i ? ctx.lineTo(P.X(p[0]), P.Y(p[1])) : ctx.moveTo(P.X(p[0]), P.Y(p[1]))); ctx.closePath(); },
      line(pts, color, width) { ctx.strokeStyle = color; ctx.lineWidth = width; ctx.lineCap = 'round'; ctx.lineJoin = 'round'; ctx.beginPath(); pts.forEach((p, i) => i ? ctx.lineTo(P.X(p[0]), P.Y(p[1])) : ctx.moveTo(P.X(p[0]), P.Y(p[1]))); ctx.stroke(); },
      text(str, u, v, size, color, o) {
        o = o || {}; ctx.save(); ctx.translate(P.X(u), P.Y(v));
        if (o.flip) ctx.scale(-1, -1); // левый борт: u и v развёрнуты → поворот на 180°
        if (o.rot) ctx.rotate(o.rot);
        ctx.fillStyle = color; ctx.font = (o.weight || '700') + ' ' + size + 'px ' + (o.font || '"Arial Narrow", Arial, Helvetica, sans-serif');
        ctx.textAlign = o.align || 'center'; ctx.textBaseline = 'middle';
        if (o.stretch) ctx.scale(o.stretch, 1);
        if (o.italic) ctx.transform(1, 0, -0.15, 1, 0, 0);
        ctx.fillText(str, 0, 0); ctx.restore();
      },
      glassFill(x, y, w, h) {
        const g = ctx.createLinearGradient(x, y, x + w * 0.5, y + h);
        g.addColorStop(0, '#7f9db8'); g.addColorStop(0.3, '#2b3d4f'); g.addColorStop(0.65, '#121c26'); g.addColorStop(1, '#0b1119');
        return g;
      },
      /* окно с бликом и рамкой */
      glass(u0, v0, u1, v1, r, frame) {
        const x = P.X(u0), y = P.Y(v1), w = (u1 - u0) * W, h = (v1 - v0) * H; r = r || Math.min(w, h) * 0.2;
        ctx.save(); P.rrPath(u0, v0, u1, v1, r); ctx.clip(); ctx.fillStyle = P.glassFill(x, y, w, h); ctx.fillRect(x, y, w, h);
        // блик
        ctx.fillStyle = 'rgba(255,255,255,0.10)'; ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x + w * 0.55, y); ctx.lineTo(x + w * 0.2, y + h); ctx.lineTo(x, y + h); ctx.closePath(); ctx.fill();
        ctx.restore();
        ctx.strokeStyle = frame || 'rgba(14,18,22,0.95)'; ctx.lineWidth = Math.max(2, W * 0.002); P.rrPath(u0, v0, u1, v1, r); ctx.stroke();
      },
      glassPoly(pts, frame) {
        const xs = pts.map(p => P.X(p[0])), ys = pts.map(p => P.Y(p[1]));
        const x = Math.min(...xs), y = Math.min(...ys), w = Math.max(...xs) - x, h = Math.max(...ys) - y;
        ctx.save(); P.polyPath(pts); ctx.clip(); ctx.fillStyle = P.glassFill(x, y, w, h); ctx.fillRect(x, y, w, h);
        ctx.fillStyle = 'rgba(255,255,255,0.10)'; ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x + w * 0.55, y); ctx.lineTo(x + w * 0.2, y + h); ctx.lineTo(x, y + h); ctx.closePath(); ctx.fill();
        ctx.restore();
        ctx.strokeStyle = frame || 'rgba(14,18,22,0.95)'; ctx.lineWidth = Math.max(2, W * 0.002); ctx.lineJoin = 'round'; P.polyPath(pts); ctx.stroke();
      },
      porthole(u, v, ru, rv) {
        const x = P.X(u), y = P.Y(v);
        ctx.fillStyle = '#d9dde2'; ctx.beginPath(); ctx.ellipse(x, y, ru * W * 1.16, rv * H * 1.16, 0, 0, Math.PI * 2); ctx.fill();
        ctx.fillStyle = '#0a0f14'; ctx.beginPath(); ctx.ellipse(x, y, ru * W * 1.06, rv * H * 1.06, 0, 0, Math.PI * 2); ctx.fill();
        const g = ctx.createRadialGradient(x - ru * W * 0.4, y - rv * H * 0.4, 0, x, y, ru * W);
        g.addColorStop(0, '#7f9db8'); g.addColorStop(0.45, '#1c2a37'); g.addColorStop(1, '#0b1117');
        ctx.fillStyle = g; ctx.beginPath(); ctx.ellipse(x, y, ru * W, rv * H, 0, 0, Math.PI * 2); ctx.fill();
      },
      seam(pts, width) { P.line(pts, 'rgba(0,0,0,0.30)', width || Math.max(1.5, W * 0.0011)); },
      rivets(u0, v, u1, n) { ctx.fillStyle = 'rgba(0,0,0,0.18)'; for (let i = 0; i <= n; i++) { ctx.beginPath(); ctx.arc(P.X(u0 + (u1 - u0) * i / n), P.Y(v), Math.max(1, W * 0.0008), 0, Math.PI * 2); ctx.fill(); } },
      flagRU(u, v, w, h) { const cols = ['#ffffff', '#2a52be', '#d52b1e']; for (let i = 0; i < 3; i++) P.rect(u, v - h * (i + 1) / 3, u + w, v - h * i / 3, cols[i]); },
      flagAltai(u, v, w, h) { P.rect(u, v - h, u + w, v, '#4aa3df'); P.rect(u, v - h * 0.8, u + w, v - h * 0.7, '#fff'); P.rect(u, v - h * 0.7, u + w, v - h * 0.6, '#4aa3df'); P.rect(u, v - h * 0.6, u + w, v - h * 0.5, '#fff'); }
    };
    return P;
  }

  /* ---------- Материалы ---------- */
  function paintMaterial(tex, extra) {
    return new T.MeshPhysicalMaterial(Object.assign({ map: tex, color: 0xffffff, roughness: 0.34, metalness: 0.0, clearcoat: 1.0, clearcoatRoughness: 0.10, envMapIntensity: 1.0 }, extra || {}));
  }
  const MAT = {
    metal: () => new T.MeshStandardMaterial({ color: 0xa4a9b0, metalness: 0.85, roughness: 0.32 }),
    darkMetal: () => new T.MeshStandardMaterial({ color: 0x3b3f45, metalness: 0.7, roughness: 0.45 }),
    rubber: () => new T.MeshStandardMaterial({ color: 0x17181a, metalness: 0.0, roughness: 0.92 }),
    blade: () => new T.MeshStandardMaterial({ color: 0x24272b, metalness: 0.25, roughness: 0.5 }),
    bladeOlive: () => new T.MeshStandardMaterial({ color: 0x33372f, metalness: 0.2, roughness: 0.55 }),
    // цвета задаются в sRGB → переводим в линейное пространство (r128 не делает этого сам)
    solid: (c, r, m) => new T.MeshPhysicalMaterial({ color: new T.Color(c).convertSRGBToLinear(), roughness: r === undefined ? 0.4 : r, metalness: m || 0, clearcoat: 0.8, clearcoatRoughness: 0.15 }),
    exhaust: () => new T.MeshStandardMaterial({ color: 0x7d6a4a, metalness: 0.9, roughness: 0.4 }),
    glass: () => new T.MeshPhysicalMaterial({ color: 0x0e1a24, roughness: 0.05, metalness: 0.15, clearcoat: 1, clearcoatRoughness: 0.03 }),
    light: (c) => new T.MeshStandardMaterial({ color: new T.Color(c).convertSRGBToLinear(), emissive: new T.Color(c).convertSRGBToLinear(), emissiveIntensity: 0.9, roughness: 0.3 }),
    disc: (c) => new T.MeshBasicMaterial({ color: c || 0x222222, transparent: true, opacity: 0.14, side: T.DoubleSide, depthWrite: false })
  };

  /* ============================================================
     ЛИВРЕИ (по фотографиям бортов компании)
     ============================================================ */
  const LIVERY = {
    as350: { base: '#f7f8f9', accent: '#0f2a6b', accent2: '#1a3f8f', reg: 'RA-04062', skid: 0x0f2a6b },
    mi8amt: { top: '#f5f7f9', mid: '#3b9de6', low: '#0e3fa0', reg: 'RA-24187', tank: '#0e3fa0', gear: 0x1d3f8a, type: 'Ми-8АМТ', windows: 'round' },
    mi171: { top: '#4b1a1c', mid: '#4b1a1c', low: '#3d1315', reg: 'RA-25565', tank: '#b9a27a', stripe: '#d1b06a', gear: 0x2a2a2a, type: 'Ми-171', windows: 'square' }
  };

  /* ============================================================
     EUROCOPTER AS350 B3 (H125) «ÉCUREUIL»
     Длина фюзеляжа 10,93 м · высота 3,34 м · НВ Ø10,69 м · РВ Ø1,86 м · кабина 1,87 м
     Начало координат — ось несущего винта.
     ============================================================ */
  function buildAS350(liv) {
    liv = liv || LIVERY.as350;
    const G = new T.Group(); G.name = 'AS350';
    const rotors = [];

    /* --- кабина + задний фюзеляж (единый лофт от носа x=3.62 до корня балки x=-2.45) --- */
    const F = [
      { x: 3.62, y: 1.16, w: 0.12, h: 0.10, hb: 0.10, n: 2.2 },
      { x: 3.52, y: 1.15, w: 0.34, wb: 0.30, h: 0.24, hb: 0.22, n: 2.3 },
      { x: 3.28, y: 1.18, w: 0.56, wb: 0.50, h: 0.40, hb: 0.36, n: 2.3 },
      { x: 2.98, y: 1.28, w: 0.76, wb: 0.66, h: 0.62, hb: 0.48, n: 2.4 },
      { x: 2.60, y: 1.40, w: 0.89, wb: 0.77, h: 0.78, hb: 0.60, n: 2.55 },
      { x: 2.15, y: 1.46, w: 0.935, wb: 0.81, h: 0.76, hb: 0.68, n: 2.7 },
      { x: 1.40, y: 1.46, w: 0.94, wb: 0.82, h: 0.74, hb: 0.70, n: 2.8 },
      { x: 0.50, y: 1.46, w: 0.94, wb: 0.82, h: 0.74, hb: 0.70, n: 2.8 },
      { x: -0.30, y: 1.48, w: 0.92, wb: 0.80, h: 0.68, hb: 0.68, n: 2.7 },
      { x: -0.90, y: 1.53, w: 0.80, wb: 0.70, h: 0.54, hb: 0.62, n: 2.5 },
      { x: -1.50, y: 1.60, w: 0.62, wb: 0.56, h: 0.42, hb: 0.52, n: 2.3 },
      { x: -2.10, y: 1.67, w: 0.42, wb: 0.40, h: 0.33, hb: 0.37, n: 2.1 },
      { x: -2.45, y: 1.71, w: 0.32, wb: 0.32, h: 0.31, hb: 0.31, n: 2 }
    ];
    const fus = mesh(loft(F, { segs: 64 }), paintMaterial(canvasTexture(paintAS350Fuselage(liv)))); G.add(fus);

    /* --- хвостовая балка x∈[-7.05,-2.45], слегка поднимается к хвосту --- */
    const B = [];
    for (let i = 0; i <= 8; i++) { const t = i / 8; B.push({ x: -2.45 - t * 4.6, y: 1.71 + t * 0.26, w: 0.31 - t * 0.13, h: 0.30 - t * 0.12, n: 2 }); }
    G.add(mesh(loft(B, { segs: 36 }), paintMaterial(canvasTexture(paintAS350Boom(liv)))));

    /* --- капот двигателя Arriel 2D над кабиной + воздухозаборник --- */
    const E = [
      { x: 1.35, y: 2.28, w: 0.28, h: 0.08, hb: 0.06, n: 2.2 },
      { x: 1.15, y: 2.36, w: 0.42, h: 0.26, hb: 0.14, n: 2.6 },
      { x: 0.70, y: 2.40, w: 0.47, h: 0.34, hb: 0.20, n: 2.8 },
      { x: 0.10, y: 2.42, w: 0.48, h: 0.35, hb: 0.22, n: 2.8 },
      { x: -0.60, y: 2.41, w: 0.46, h: 0.32, hb: 0.20, n: 2.6 },
      { x: -1.20, y: 2.36, w: 0.38, h: 0.24, hb: 0.16, n: 2.4 },
      { x: -1.70, y: 2.28, w: 0.24, h: 0.12, hb: 0.10, n: 2.2 },
      { x: -1.95, y: 2.22, w: 0.06, h: 0.05, hb: 0.04, n: 2 }
    ];
    G.add(mesh(loft(E, { segs: 40 }), paintMaterial(canvasTexture(paintAS350Cowl(liv)))));
    // короб воздухозаборника (характерный «ящик» перед редуктором) с сеткой
    const intake = mesh(new T.BoxGeometry(0.36, 0.20, 0.62), MAT.solid(0xf7f8f9, 0.35)); intake.position.set(1.22, 2.42, 0); G.add(intake);
    const grill = mesh(new T.BoxGeometry(0.02, 0.16, 0.56), MAT.darkMetal()); grill.position.set(1.41, 2.42, 0); G.add(grill);
    // выхлопная труба — назад-вправо-вверх
    const ex = mesh(cyl(0.15, 0.185, 0.6, 24, true), MAT.exhaust()); ex.material.side = T.DoubleSide;
    ex.rotation.z = Math.PI / 2 + 0.3; ex.rotation.y = -0.25; ex.position.set(-2.05, 2.24, 0.05); G.add(ex);
    const exIn = mesh(cyl(0.125, 0.125, 0.55, 20, true), new T.MeshStandardMaterial({ color: 0x0d0d0d, side: T.BackSide, roughness: 1 })); exIn.rotation.copy(ex.rotation); exIn.position.copy(ex.position); G.add(exIn);

    /* --- вал, втулка Starflex, 3 лопасти --- */
    const mastFair = mesh(cyl(0.16, 0.22, 0.32, 24), MAT.solid(0xf7f8f9, 0.35)); mastFair.position.set(0.0, 2.88, 0); G.add(mastFair);
    const mast = mesh(cyl(0.085, 0.10, 0.5, 20), MAT.darkMetal()); mast.position.set(0.0, 3.05, 0); G.add(mast);
    const rotor = new T.Group(); rotor.position.set(0.0, 3.26, 0);
    rotor.add(mesh(cyl(0.30, 0.30, 0.06, 32), MAT.solid(0x2d3136, 0.5, 0.4)));
    const hubTop = mesh(cyl(0.10, 0.15, 0.20, 20), MAT.darkMetal()); hubTop.position.y = 0.12; rotor.add(hubTop);
    for (let i = 0; i < 3; i++) {
      const arm = new T.Group(); arm.rotation.y = i * Math.PI * 2 / 3;
      const star = mesh(new T.BoxGeometry(0.66, 0.045, 0.15), MAT.solid(0x2d3136, 0.5, 0.4)); star.position.x = 0.36; arm.add(star);
      const grip = mesh(cyl(0.065, 0.055, 0.5, 14), MAT.darkMetal()); grip.rotation.z = Math.PI / 2; grip.position.set(0.74, 0.0, 0); arm.add(grip);
      const pl = mesh(new T.BoxGeometry(0.2, 0.04, 0.04), MAT.metal()); pl.position.set(0.5, -0.09, 0.14); arm.add(pl);
      const bl = mesh(bladeGeometry(4.5, 0.35, 0.055, 0.97, 0.05), MAT.blade()); bl.position.set(0.88, 0.0, 0); bl.rotation.x = 0.05; arm.add(bl);
      rotor.add(arm);
    }
    const disc = mesh(new T.CircleGeometry(5.35, 72), MAT.disc(0x3a3f45), false); disc.rotation.x = -Math.PI / 2; disc.position.y = 0.0; disc.visible = false; rotor.add(disc);
    G.add(rotor); rotors.push({ obj: rotor, axis: 'y', dir: 1, disc, rpm: 390 });

    /* --- стабилизатор с концевыми шайбами (x≈-5.1) --- */
    const stab = mesh(slab([[0.30, -1.25], [0.30, 1.25], [-0.30, 1.25], [-0.30, -1.25]], 0.08, 0.025), MAT.solid(0xf7f8f9, 0.35));
    stab.rotation.x = Math.PI / 2; stab.position.set(-5.05, 1.95, 0); G.add(stab);
    [-1, 1].forEach(s => {
      const pm = mesh(slab([[0.40, -0.10], [0.28, 0.45], [-0.30, 0.45], [-0.42, -0.28], [0.20, -0.28]], 0.05, 0.015), MAT.solid(new T.Color(liv.accent).getHex(), 0.42, 0));
      pm.position.set(-5.05, 1.98, s * 1.26); G.add(pm);
    });

    /* --- киль: стреловидный верхний + вентральный; окраска по ливрее --- */
    const finTex = canvasTexture(paintAS350Fin(liv));
    const finU = mesh(slab([[-5.9, 1.95], [-6.9, 3.42], [-7.5, 3.38], [-7.6, 2.9], [-7.38, 1.95]], 0.17, 0.05), paintMaterial(finTex));
    G.add(finU);
    const finL = mesh(slab([[-6.15, 1.62], [-7.28, 1.62], [-7.20, 0.92], [-6.95, 0.86], [-6.50, 1.25]], 0.13, 0.04), MAT.solid(new T.Color(liv.accent).getHex(), 0.42, 0));
    G.add(finL);
    G.add(straight([-7.25, 0.9, 0], [-7.05, 0.74, 0], 0.03, MAT.darkMetal())); // хвостовая опора
    const beacon = mesh(new T.SphereGeometry(0.05, 12, 8), MAT.light(0xff3b30)); beacon.position.set(-7.25, 3.43, 0); G.add(beacon);

    /* --- рулевой винт, левый борт, 2 лопасти + обтекатель редуктора --- */
    const tgb = mesh(cyl(0.10, 0.13, 0.30, 16), MAT.solid(new T.Color(liv.accent).getHex(), 0.42, 0)); tgb.rotation.x = Math.PI / 2; tgb.position.set(-6.95, 2.42, -0.16); G.add(tgb);
    const tr = new T.Group(); tr.position.set(-6.95, 2.42, -0.36);
    const trHub = mesh(cyl(0.06, 0.06, 0.16, 12), MAT.metal()); trHub.rotation.x = Math.PI / 2; tr.add(trHub);
    for (let i = 0; i < 2; i++) {
      const a = new T.Group(); a.rotation.z = i * Math.PI;
      const bl = mesh(bladeGeometry(0.86, 0.19, 0.03, 1), MAT.blade()); bl.rotation.set(0, Math.PI / 2, Math.PI / 2); bl.position.set(0, 0.07, 0); a.add(bl); tr.add(a);
    }
    const trDisc = mesh(new T.CircleGeometry(0.95, 40), MAT.disc(0x3a3f45), false); trDisc.visible = false; tr.add(trDisc);
    G.add(tr); rotors.push({ obj: tr, axis: 'z', dir: -1, disc: trDisc, rpm: 2085 });
    G.add(mesh(tube([[-7.35, 2.42, -0.4], [-7.55, 2.15, -0.4], [-7.5, 1.85, -0.4]], 0.02), MAT.darkMetal())); // защитная скоба

    /* --- полозковое шасси: полозья, дуги, ступени, колёса перекатки --- */
    const skidMat = MAT.solid(liv.skid, 0.42, 0);
    [-1, 1].forEach(s => {
      const z = s * 1.12;
      G.add(mesh(tube([[-1.75, 0.06, z], [-0.5, 0.05, z], [1.0, 0.05, z], [2.15, 0.06, z], [2.65, 0.2, z], [2.95, 0.46, z]], 0.045, false, 48), skidMat));
      const step = mesh(new T.BoxGeometry(1.7, 0.03, 0.24), MAT.darkMetal()); step.position.set(0.85, 0.36, z); G.add(step);
      G.add(straight([0.2, 0.06, z], [0.2, 0.36, z], 0.02, MAT.darkMetal())); G.add(straight([1.5, 0.06, z], [1.5, 0.36, z], 0.02, MAT.darkMetal()));
      const wheel = mesh(new T.TorusGeometry(0.11, 0.045, 10, 24), MAT.rubber()); wheel.position.set(-0.7, 0.19, z + s * 0.2); G.add(wheel);
    });
    [1.75, -0.95].forEach(x => G.add(mesh(tube([[x, 0.06, -1.12], [x, 0.50, -0.98], [x, 0.72, -0.40], [x, 0.74, 0], [x, 0.72, 0.40], [x, 0.50, 0.98], [x, 0.06, 1.12]], 0.05, false, 48), skidMat)));

    /* --- носовые детали: ПВД, фара, стеклоочистители, антенны, поручни --- */
    G.add(straight([3.4, 1.3, 0.3], [3.95, 1.32, 0.3], 0.014, MAT.metal()));
    const lamp = mesh(new T.SphereGeometry(0.12, 16, 10, 0, Math.PI * 2, 0, Math.PI / 2), MAT.light(0xfff2c0)); lamp.rotation.x = Math.PI / 2; lamp.position.set(2.7, 0.66, 0); G.add(lamp);
    [-0.28, 0.28].forEach(z => { const w = mesh(new T.BoxGeometry(0.015, 0.34, 0.03), MAT.darkMetal()); w.position.set(3.32, 1.55, z); w.rotation.z = 0.35; G.add(w); });
    const ant1 = mesh(new T.BoxGeometry(0.30, 0.22, 0.02), MAT.darkMetal()); ant1.position.set(-1.4, 0.98, 0); G.add(ant1);
    const ant2 = mesh(new T.BoxGeometry(0.02, 0.22, 0.20), MAT.darkMetal()); ant2.position.set(-3.8, 1.6, 0); G.add(ant2);
    const gps = mesh(new T.BoxGeometry(0.14, 0.03, 0.14), MAT.solid(0xf7f8f9)); gps.position.set(-0.5, 2.79, 0.3); G.add(gps);
    [-1, 1].forEach(s => G.add(mesh(tube([[0.9, 2.3, s * 0.52], [0.1, 2.38, s * 0.57], [-0.7, 2.3, s * 0.52]], 0.012), MAT.metal())));
    // зеркала заднего вида на носу
    [-1, 1].forEach(s => { G.add(straight([3.0, 1.35, s * 0.55], [3.05, 1.2, s * 0.85], 0.012, MAT.darkMetal())); const m = mesh(new T.BoxGeometry(0.02, 0.12, 0.16), MAT.darkMetal()); m.position.set(3.05, 1.18, s * 0.88); G.add(m); });

    G.userData.rotors = rotors;
    G.userData.bounds = { length: 12.9, height: 3.4, width: 10.7, center: -1.7, reach: 7.0 };
    return G;
  }

  /* ---- ливрея AS350: фюзеляж (u: 0 = x=-2.45 корень балки, 1 = x=3.62 нос) ---- */
  function paintAS350Fuselage(liv) {
    const W = 2048, H = 1024, c = makeCanvas(W, H), ctx = c.getContext('2d'), P = painter(ctx, W, H);
    const ux = x => (x + 2.45) / 6.07;
    P.rect(0, 0, 1, 1, liv.base);
    /* тёмно-синий низ: граница проходит по нижней кромке окон и уходит вверх к хвосту (задний фюзеляж полностью синий) */
    const belly = (center, sgn) => {
      const top = [], bot = [];
      for (let i = 0; i <= 80; i++) {
        const u = i / 80, x = -2.45 + u * 6.07;
        let v;
        if (x > 2.2) v = 0.15 - (x - 2.2) * 0.06;            // нос: граница уходит вниз
        else if (x > 0.3) v = 0.15;                           // под дверями кабины
        else v = 0.15 + Math.min(0.20, (0.3 - x) * 0.16);     // резко поднимается к балке (задний фюзеляж синий)
        top.push([u, center + sgn * v]);
      }
      ctx.fillStyle = liv.accent; ctx.beginPath(); ctx.moveTo(P.X(top[0][0]), P.Y(top[0][1]));
      top.forEach(p => ctx.lineTo(P.X(p[0]), P.Y(p[1])));
      ctx.lineTo(P.X(1), P.Y(center + sgn * 0.30)); ctx.lineTo(P.X(0), P.Y(center + sgn * 0.30)); ctx.closePath(); ctx.fill();
      P.line(top, liv.accent2, 4);
    };
    belly(0.0, -1); ctx.save(); ctx.translate(0, -H); belly(0.0, -1); ctx.restore(); // правый борт (низ = v<0 → wrap на 0.75..1)
    belly(0.5, 1);                                                                     // левый борт (низ = v 0.5→0.75)
    P.rect(0, 0.735, 1, 0.765, liv.accent); // шов по килевой линии
    /* остекление: лобовое стекло оборачивает нос (u∈[ux(2.25),ux(3.45)], v∈[0.09,0.41]) */
    const u0 = ux(2.25), u1 = ux(3.45);
    P.glassPoly([[u0, 0.09], [u1 - 0.01, 0.16], [u1, 0.25], [u1 - 0.01, 0.34], [u0, 0.41]]);
    P.line([[u0 + 0.004, 0.25], [u1 - 0.006, 0.25]], '#0e1216', 13);        // центральная стойка
    P.line([[ux(2.62), 0.10], [ux(2.68), 0.40]], '#0e1216', 9);              // стойка двери пилота
    // окна передних дверей (выпуклые): по бортам ниже лобового
    P.glass(ux(2.05), 0.005, ux(2.6), 0.115, 26); P.glass(ux(2.05), 0.385, ux(2.6), 0.495, 26);
    // окна пассажирских (сдвижных) дверей — большие, до кромки крыши
    P.glass(ux(0.55), 0.005, ux(1.98), 0.125, 34); P.glass(ux(0.55), 0.375, ux(1.98), 0.495, 34);
    // задние окошки багажника
    P.glass(ux(-0.5), 0.03, ux(0.42), 0.105, 18); P.glass(ux(-0.5), 0.395, ux(0.42), 0.47, 18);
    /* швы дверей и люков */
    P.seam([[ux(2.02), -0.02], [ux(2.02), 0.13], [ux(0.5), 0.13], [ux(0.5), -0.02]]);
    P.seam([[ux(2.02), 0.52], [ux(2.02), 0.37], [ux(0.5), 0.37], [ux(0.5), 0.52]]);
    P.seam([[ux(2.72), -0.02], [ux(2.72), 0.135], [ux(2.05), 0.135]]); P.seam([[ux(2.72), 0.52], [ux(2.72), 0.365], [ux(2.05), 0.365]]);
    P.seam([[ux(-1.1), 0.60], [ux(-0.1), 0.60], [ux(-0.1), 0.70], [ux(-1.1), 0.70], [ux(-1.1), 0.60]]);
    P.rivets(ux(-2.3), 0.245, ux(2.2), 60); P.rivets(ux(-2.3), 0.255, ux(2.2), 60);
    /* логотипы «ALTAY AVIA» на дверях и флаг */
    P.text('ALTAY AVIA', ux(1.27), 0.175, 30, liv.accent, { weight: '900', stretch: 1.05 });
    P.text('ALTAY AVIA', ux(1.27), 0.325, 30, liv.accent, { weight: '900', stretch: 1.05, flip: true });
    P.flagRU(ux(-0.05), 0.20, 0.022, 0.03); P.flagRU(ux(-0.05), 0.31, 0.022, 0.03);
    return c;
  }
  function paintAS350Boom(liv) {
    const W = 1024, H = 256, c = makeCanvas(W, H), ctx = c.getContext('2d'), P = painter(ctx, W, H);
    P.rect(0, 0, 1, 1, liv.accent); // балка целиком тёмно-синяя
    P.text(liv.reg, 0.55, 0.16, 62, '#ffffff', { weight: '900', stretch: 1.1 });
    P.text(liv.reg, 0.55, 0.34, 62, '#ffffff', { weight: '900', stretch: 1.1, flip: true });
    P.text('www.altay-avia.ru', 0.30, 0.19, 22, 'rgba(255,255,255,0.85)', { weight: '600' });
    P.text('www.altay-avia.ru', 0.30, 0.31, 22, 'rgba(255,255,255,0.85)', { weight: '600', flip: true });
    for (let i = 1; i < 5; i++) P.seam([[i / 5, 0], [i / 5, 1]], 2);
    return c;
  }
  function paintAS350Cowl(liv) {
    const W = 512, H = 256, c = makeCanvas(W, H), ctx = c.getContext('2d'), P = painter(ctx, W, H);
    P.rect(0, 0, 1, 1, liv.base);
    for (let i = 0; i < 7; i++) { P.rect(0.30 + i * 0.045, 0.04, 0.315 + i * 0.045, 0.16, 'rgba(0,0,0,0.35)'); P.rect(0.30 + i * 0.045, 0.34, 0.315 + i * 0.045, 0.46, 'rgba(0,0,0,0.35)'); }
    P.seam([[0.62, 0], [0.62, 1]], 3); P.seam([[0.22, 0], [0.22, 1]], 3);
    return c;
  }
  function paintAS350Fin(liv) {
    const W = 512, H = 512, c = makeCanvas(W, H), ctx = c.getContext('2d'), P = painter(ctx, W, H);
    P.rect(0, 0, 1, 1, liv.accent);
    return c;
  }

  /* ============================================================
     Ми-8АМТ / Ми-171 (Улан-Удэ)
     Длина фюзеляжа 18,47 м · ширина 2,5 м · высота до втулки 4,76 м · НВ Ø21,29 м · РВ Ø3,91 м
     Колея 4,51 м · база 4,28 м. Начало координат — ось несущего винта.
     ============================================================ */
  function buildMi8(liv) {
    liv = liv || LIVERY.mi8amt;
    const G = new T.Group(); G.name = liv.type;
    const rotors = [];
    const topHex = new T.Color(liv.top).getHex();

    /* --- фюзеляж: тупой остеклённый нос x=8.3 → коробчатая середина → сужение к балке x=-5.6 --- */
    const F = [
      { x: 8.30, y: 2.08, w: 0.30, wb: 0.36, h: 0.30, hb: 0.42, n: 2.5, nb: 2.2 },
      { x: 8.12, y: 2.10, w: 0.78, wb: 0.82, h: 0.68, hb: 0.76, n: 2.6, nb: 2.3 },
      { x: 7.80, y: 2.16, w: 1.04, wb: 1.06, h: 0.95, hb: 0.96, n: 2.9, nb: 2.5 },
      { x: 7.30, y: 2.24, w: 1.18, wb: 1.20, h: 1.08, hb: 1.10, n: 3.3, nb: 2.8 },
      { x: 6.60, y: 2.28, w: 1.24, wb: 1.24, h: 1.14, hb: 1.16, n: 3.6, nb: 3.0 },
      { x: 5.60, y: 2.28, w: 1.25, wb: 1.25, h: 1.15, hb: 1.17, n: 3.8, nb: 3.2 },
      { x: 2.00, y: 2.28, w: 1.25, wb: 1.25, h: 1.15, hb: 1.17, n: 3.8, nb: 3.2 },
      { x: -1.60, y: 2.28, w: 1.25, wb: 1.25, h: 1.15, hb: 1.17, n: 3.8, nb: 3.2 },
      { x: -2.50, y: 2.36, w: 1.20, wb: 1.18, h: 1.06, hb: 1.02, n: 3.4, nb: 3.0 },
      { x: -3.40, y: 2.56, w: 1.02, wb: 0.98, h: 0.90, hb: 0.80, n: 3.0, nb: 2.7 },
      { x: -4.30, y: 2.78, w: 0.80, wb: 0.76, h: 0.70, hb: 0.60, n: 2.6, nb: 2.4 },
      { x: -5.10, y: 2.92, w: 0.60, wb: 0.58, h: 0.55, hb: 0.50, n: 2.3 },
      { x: -5.60, y: 2.97, w: 0.52, wb: 0.52, h: 0.50, hb: 0.48, n: 2.1 }
    ];
    G.add(mesh(loft(F, { segs: 72 }), paintMaterial(canvasTexture(paintMi8Fuselage(liv)))));

    /* --- хвостовая балка x∈[-11.5,-5.6] --- */
    const B = [];
    for (let i = 0; i <= 10; i++) { const t = i / 10; B.push({ x: -5.6 - t * 5.9, y: 2.97 + t * 0.40, w: 0.52 - t * 0.25, h: 0.50 - t * 0.24, n: 2 }); }
    G.add(mesh(loft(B, { segs: 40 }), paintMaterial(canvasTexture(paintMi8Boom(liv)))));

    /* --- концевая балка (киль): изгиб вверх к редуктору РВ --- */
    const K = [];
    for (let i = 0; i <= 10; i++) {
      const t = i / 10, x = -11.5 - t * 1.25, y = 3.37 + Math.pow(t, 1.1) * 1.28;
      K.push({ x, y, w: 0.27 - t * 0.10, h: 0.28 + t * 0.62, hb: 0.26 - t * 0.02, n: 2.4 });
    }
    const finTex = canvasTexture(paintMi8Fin(liv));
    G.add(mesh(loft(K, { segs: 36 }), paintMaterial(finTex)));
    const tgb = mesh(new T.SphereGeometry(0.30, 20, 14), paintMaterial(finTex)); tgb.scale.set(1.5, 1, 1); tgb.position.set(-12.72, 4.65, 0); G.add(tgb);

    /* --- стабилизатор (по бокам балки перед килем) --- */
    [-1, 1].forEach(s => {
      const g = slab([[0.48, 0], [0.34, 1.45], [-0.34, 1.45], [-0.52, 0]], 0.10, 0.03);
      const m = mesh(g, MAT.solid(topHex, 0.35)); m.rotation.x = s > 0 ? -Math.PI / 2 : Math.PI / 2; m.position.set(-10.55, 3.1, s * 0.32); G.add(m);
    });

    /* --- двигательный отсек: 2×ТВ3-117 с ПЗУ, редуктор, вентилятор, ВСУ --- */
    const deckMat = paintMaterial(canvasTexture(paintMi8Deck(liv)));
    const D = [
      { x: 6.35, y: 3.40, w: 0.95, h: 0.10, hb: 0.08, n: 3 },
      { x: 5.90, y: 3.50, w: 1.12, h: 0.42, hb: 0.20, n: 3.3 },
      { x: 5.00, y: 3.54, w: 1.16, h: 0.50, hb: 0.22, n: 3.5 },
      { x: 3.20, y: 3.56, w: 1.16, h: 0.54, hb: 0.22, n: 3.5 },
      { x: 1.60, y: 3.60, w: 1.14, h: 0.62, hb: 0.24, n: 3.3 },
      { x: 0.60, y: 3.66, w: 1.02, h: 0.74, hb: 0.26, n: 3.0 },
      { x: -0.40, y: 3.66, w: 0.98, h: 0.74, hb: 0.26, n: 3.0 },
      { x: -1.40, y: 3.58, w: 0.92, h: 0.52, hb: 0.22, n: 2.8 },
      { x: -2.40, y: 3.48, w: 0.80, h: 0.32, hb: 0.16, n: 2.6 },
      { x: -3.20, y: 3.40, w: 0.50, h: 0.10, hb: 0.08, n: 2.4 }
    ];
    G.add(mesh(loft(D, { segs: 56 }), deckMat));
    [-1, 1].forEach(s => {
      const z = s * 0.58;
      const pzu = mesh(new T.SphereGeometry(0.36, 28, 18), MAT.solid(topHex, 0.35)); pzu.scale.set(1.2, 1, 1); pzu.position.set(6.95, 3.75, z); G.add(pzu);
      const ring = mesh(new T.TorusGeometry(0.33, 0.05, 10, 32), MAT.darkMetal()); ring.rotation.y = Math.PI / 2; ring.position.set(6.55, 3.75, z); G.add(ring);
      const exh = mesh(cyl(0.25, 0.28, 0.6, 24, true), MAT.exhaust()); exh.material.side = T.DoubleSide;
      exh.rotation.z = Math.PI / 2; exh.rotation.y = s * 0.6; exh.position.set(1.55, 3.62, s * 1.36); G.add(exh);
      const exhIn = mesh(cyl(0.22, 0.22, 0.55, 22, true), new T.MeshStandardMaterial({ color: 0x0a0a0a, side: T.BackSide, roughness: 1 })); exhIn.rotation.copy(exh.rotation); exhIn.position.copy(exh.position); G.add(exhIn);
    });
    const fan = mesh(new T.BoxGeometry(0.9, 0.55, 1.5), deckMat); fan.position.set(-1.1, 4.3, 0); G.add(fan);
    const fanGrill = mesh(new T.BoxGeometry(0.02, 0.4, 1.2), MAT.darkMetal()); fanGrill.position.set(-0.64, 4.3, 0); G.add(fanGrill);
    const apu = mesh(cyl(0.16, 0.16, 0.6, 16), MAT.exhaust()); apu.rotation.z = Math.PI / 2; apu.position.set(-3.0, 3.6, 0.35); G.add(apu);

    /* --- несущий винт: 5 лопастей с провисом --- */
    const mast = mesh(cyl(0.16, 0.20, 0.7, 24), MAT.darkMetal()); mast.position.set(0.0, 4.6, 0); G.add(mast);
    const rotor = new T.Group(); rotor.position.set(0, 4.98, 0);
    rotor.add(mesh(cyl(0.42, 0.46, 0.32, 28), MAT.darkMetal()));
    const cap = mesh(cyl(0.22, 0.30, 0.16, 24), MAT.solid(0xe9c23a, 0.5)); cap.position.y = 0.24; rotor.add(cap);
    const swash = mesh(cyl(0.55, 0.55, 0.06, 32), MAT.metal()); swash.position.y = -0.3; rotor.add(swash);
    const bladeMat = MAT.bladeOlive(), tipMat = MAT.solid(0xf2c230, 0.5);
    for (let i = 0; i < 5; i++) {
      const arm = new T.Group(); arm.rotation.y = i * Math.PI * 2 / 5;
      const grip = mesh(new T.BoxGeometry(0.9, 0.16, 0.24), MAT.darkMetal()); grip.position.x = 0.72; arm.add(grip);
      const damper = mesh(cyl(0.05, 0.05, 0.5, 10), MAT.metal()); damper.rotation.z = Math.PI / 2; damper.rotation.y = 0.6; damper.position.set(0.55, 0.05, 0.3); arm.add(damper);
      const bl = mesh(bladeGeometry(9.3, 0.52, 0.09, 1, 0.55), bladeMat); bl.position.set(1.15, 0.0, 0); arm.add(bl);
      const tip = mesh(new T.BoxGeometry(0.5, 0.05, 0.5), tipMat); tip.position.set(10.4, -0.56, 0); arm.add(tip);
      rotor.add(arm);
    }
    const disc = mesh(new T.CircleGeometry(10.65, 80), MAT.disc(0x2f3438), false); disc.rotation.x = -Math.PI / 2; disc.position.y = -0.25; disc.visible = false; rotor.add(disc);
    G.add(rotor); rotors.push({ obj: rotor, axis: 'y', dir: 1, disc, rpm: 192 });

    /* --- рулевой винт: 3 лопасти, левый борт --- */
    const tr = new T.Group(); tr.position.set(-12.72, 4.65, -0.46);
    const trHub = mesh(cyl(0.14, 0.14, 0.32, 16), MAT.darkMetal()); trHub.rotation.x = Math.PI / 2; tr.add(trHub);
    for (let i = 0; i < 3; i++) {
      const a = new T.Group(); a.rotation.z = i * Math.PI * 2 / 3;
      const bl = mesh(bladeGeometry(1.75, 0.30, 0.05, 0.9), bladeMat); bl.rotation.set(0, Math.PI / 2, Math.PI / 2); bl.position.set(0, 0.15, 0); a.add(bl);
      const tip = mesh(new T.BoxGeometry(0.08, 0.3, 0.3), tipMat); tip.position.set(0, 1.85, 0); a.add(tip); tr.add(a);
    }
    const trDisc = mesh(new T.CircleGeometry(1.95, 48), MAT.disc(0x2f3438), false); trDisc.visible = false; tr.add(trDisc);
    G.add(tr); rotors.push({ obj: tr, axis: 'z', dir: 1, disc: trDisc, rpm: 1124 });

    /* --- подвесные топливные баки (правый длиннее) --- */
    const tankMat = MAT.solid(new T.Color(liv.tank).getHex(), 0.3, liv.stripe ? 0.45 : 0.05);
    const makeTank = (x0, x1, z) => {
      const L = x0 - x1, st = [];
      for (let i = 0; i <= 12; i++) { const t = i / 12, x = x0 - t * L, r = 0.46 * Math.sqrt(Math.max(0.02, 1 - Math.pow((t - 0.5) * 2, 8))); st.push({ x, y: 1.36, z, w: r, h: r, n: 2 }); }
      G.add(mesh(loft(st, { segs: 32 }), tankMat));
      [0.2, 0.5, 0.8].forEach(k => { const x = x0 - k * L; G.add(straight([x, 1.62, z * 0.82], [x, 1.45, z], 0.04, MAT.darkMetal())); G.add(straight([x, 1.10, z * 0.82], [x, 1.25, z], 0.03, MAT.darkMetal())); });
    };
    makeTank(5.2, -3.5, 1.58); makeTank(2.5, -3.5, -1.58);

    /* --- шасси: носовая спаренная стойка, основные пирамиды, хвостовая опора --- */
    const gearMat = MAT.solid(liv.gear, 0.45, 0.2);
    const tyre = (r, w) => mesh(new T.CylinderGeometry(r, r, w, 30), MAT.rubber());
    G.add(straight([5.7, 1.12, 0], [5.7, 0.42, 0], 0.07, gearMat)); G.add(straight([4.9, 1.15, 0], [5.7, 0.55, 0], 0.035, gearMat));
    [-1, 1].forEach(s => { const w = tyre(0.30, 0.17); w.rotation.x = Math.PI / 2; w.position.set(5.7, 0.30, s * 0.3); G.add(w); const hub = mesh(cyl(0.12, 0.12, 0.19, 14), MAT.metal()); hub.rotation.x = Math.PI / 2; hub.position.copy(w.position); G.add(hub); });
    G.add(straight([5.7, 0.30, -0.42], [5.7, 0.30, 0.42], 0.05, MAT.darkMetal()));
    [-1, 1].forEach(s => {
      const wz = s * 2.25, wx = 1.4;
      const w = tyre(0.48, 0.24); w.rotation.x = Math.PI / 2; w.position.set(wx, 0.48, wz); G.add(w);
      const hub = mesh(cyl(0.2, 0.2, 0.27, 18), MAT.metal()); hub.rotation.x = Math.PI / 2; hub.position.copy(w.position); G.add(hub);
      G.add(straight([wx + 1.0, 1.5, s * 1.18], [wx, 0.48, wz - s * 0.17], 0.07, gearMat));
      G.add(straight([wx - 1.0, 1.5, s * 1.18], [wx, 0.48, wz - s * 0.17], 0.07, gearMat));
      G.add(straight([wx - 0.2, 2.85, s * 1.3], [wx, 0.55, wz - s * 0.13], 0.075, MAT.metal(), 0.09));
      G.add(straight([wx, 0.48, wz - s * 0.17], [wx, 0.48, wz + s * 0.02], 0.06, MAT.darkMetal()));
    });
    G.add(straight([-9.6, 2.7, 0], [-10.1, 1.8, 0], 0.045, gearMat)); G.add(straight([-8.7, 2.6, 0], [-10.1, 1.8, 0], 0.035, gearMat));
    const tailSkid = mesh(new T.SphereGeometry(0.1, 10, 8), MAT.rubber()); tailSkid.position.set(-10.1, 1.77, 0); G.add(tailSkid);

    /* --- детали: трап у сдвижной двери, ПВД, фары, антенны, маяки, лебёдка --- */
    const stepMat = MAT.metal();
    for (let i = 0; i < 3; i++) { const st = mesh(new T.BoxGeometry(0.5, 0.03, 0.2), stepMat); st.position.set(4.1, 1.05 - i * 0.28, -1.5 - i * 0.14); G.add(st); }
    G.add(straight([3.85, 1.2, -1.35], [3.85, 0.25, -1.9], 0.02, stepMat)); G.add(straight([4.35, 1.2, -1.35], [4.35, 0.25, -1.9], 0.02, stepMat));
    [-1, 1].forEach(s => G.add(straight([8.0, 2.62, s * 0.55], [8.7, 2.66, s * 0.6], 0.02, stepMat)));
    const l1 = mesh(new T.SphereGeometry(0.14, 16, 10), MAT.light(0xfff2c0)); l1.position.set(7.2, 1.05, 0); G.add(l1);
    const a1 = mesh(new T.BoxGeometry(0.02, 0.35, 0.35), MAT.darkMetal()); a1.position.set(-6.8, 3.25, 0); G.add(a1);
    const a2 = mesh(new T.BoxGeometry(0.02, 0.3, 0.25), MAT.darkMetal()); a2.position.set(4.6, 1.02, 0.4); G.add(a2);
    const a3 = mesh(new T.BoxGeometry(0.02, 0.3, 0.25), MAT.darkMetal()); a3.position.set(-2.6, 1.02, -0.4); G.add(a3);
    const bc1 = mesh(new T.SphereGeometry(0.07, 12, 8), MAT.light(0xff3b30)); bc1.position.set(-8.3, 3.42, 0); G.add(bc1);
    const bc2 = mesh(new T.SphereGeometry(0.07, 12, 8), MAT.light(0xff3b30)); bc2.position.set(-3.5, 1.12, 0); G.add(bc2);
    const dop = mesh(new T.BoxGeometry(0.9, 0.16, 0.5), MAT.solid(new T.Color(liv.low).getHex(), 0.4)); dop.position.set(-6.3, 2.3, 0); G.add(dop);
    const winch = mesh(new T.BoxGeometry(0.35, 0.3, 0.3), MAT.darkMetal()); winch.position.set(4.6, 3.15, -1.36); G.add(winch);

    G.userData.rotors = rotors;
    G.userData.bounds = { length: 25.3, height: 5.65, width: 21.3, center: -2.2, reach: 12.8 };
    return G;
  }

  /* ---- ливрея Ми-8: фюзеляж (u: 0 = x=-5.6, 1 = x=8.3) ---- */
  function paintMi8Fuselage(liv) {
    const W = 2048, H = 1024, c = makeCanvas(W, H), ctx = c.getContext('2d'), P = painter(ctx, W, H);
    const ux = x => (x + 5.6) / 13.9;
    P.rect(0, 0, 1, 1, liv.top);
    if (liv.windows === 'round') {
      /* сине-белая ливрея: светло-синяя полоса по иллюминаторам, поднимающаяся к носу; тёмно-синий низ */
      const drawSide = (center, sgn) => {
        const vv = off => center + sgn * off;
        const top = [], bot = [];
        for (let i = 0; i <= 80; i++) { const u = i / 80, x = -5.6 + u * 13.9; const rise = x > 5.6 ? (x - 5.6) * 0.03 : (x < -2.5 ? (-2.5 - x) * 0.012 : 0); top.push([u, vv(-0.02 - rise)]); bot.push([u, vv(0.085 + rise * 0.4)]); }
        ctx.fillStyle = liv.mid; ctx.beginPath(); ctx.moveTo(P.X(top[0][0]), P.Y(top[0][1])); top.forEach(p => ctx.lineTo(P.X(p[0]), P.Y(p[1])));
        for (let i = bot.length - 1; i >= 0; i--) ctx.lineTo(P.X(bot[i][0]), P.Y(bot[i][1])); ctx.closePath(); ctx.fill();
        ctx.fillStyle = liv.low; ctx.beginPath(); ctx.moveTo(P.X(bot[0][0]), P.Y(bot[0][1])); bot.forEach(p => ctx.lineTo(P.X(p[0]), P.Y(p[1])));
        ctx.lineTo(P.X(1), P.Y(vv(0.30))); ctx.lineTo(P.X(0), P.Y(vv(0.30))); ctx.closePath(); ctx.fill();
        P.line(top, '#ffffff', 5);
      };
      drawSide(0.5, 1); drawSide(0.0, -1);
      ctx.save(); ctx.translate(0, -H); drawSide(0.0, -1); ctx.restore();
      ctx.save(); ctx.translate(0, H); drawSide(1.0, -1); ctx.restore();
      P.rect(0, 0.70, 1, 0.80, liv.low);
    } else {
      /* бордовая VIP-ливрея с золотыми полосами */
      P.rect(0, 0.60, 1, 0.90, liv.low);
      P.line([[0, 0.60], [1, 0.60]], liv.stripe, 7); P.line([[0, 0.90], [1, 0.90]], liv.stripe, 7);
      P.line([[ux(-4.0), 0.13], [ux(7.4), 0.13]], liv.stripe, 5); P.line([[ux(-4.0), 0.37], [ux(7.4), 0.37]], liv.stripe, 5);
    }
    /* остекление кабины экипажа: «теплица» из панелей, оборачивает нос */
    const g0 = ux(6.45), g1 = ux(8.22);
    P.glassPoly([[g0, 0.01], [ux(7.3), 0.03], [ux(7.9), 0.09], [g1, 0.17], [g1, 0.33], [ux(7.9), 0.41], [ux(7.3), 0.47], [g0, 0.49]]);
    const post = (u, v0, v1, w) => P.line([[u, v0], [u, v1]], '#0e1216', w || 11);
    P.line([[g0 + 0.003, 0.25], [g1 - 0.004, 0.25]], '#0e1216', 11);
    post(ux(7.0), 0.03, 0.47); post(ux(7.55), 0.05, 0.45); post(ux(7.95), 0.10, 0.40);
    P.line([[g0, 0.12], [ux(7.9), 0.13]], '#0e1216', 9); P.line([[g0, 0.38], [ux(7.9), 0.37]], '#0e1216', 9);
    P.line([[g0, 0.20], [ux(8.1), 0.21]], '#0e1216', 7); P.line([[g0, 0.30], [ux(8.1), 0.29]], '#0e1216', 7);
    // сдвижные блистеры пилотов
    P.glass(ux(5.55), 0.035, ux(6.38), 0.125, 22); P.glass(ux(5.55), 0.375, ux(6.38), 0.465, 22);
    /* сдвижная дверь левого борта (v 0.5→ низ) с окном */
    P.seam([[ux(4.85), 0.39], [ux(4.85), 0.62], [ux(3.45), 0.62], [ux(3.45), 0.39], [ux(4.85), 0.39]], 4);
    if (liv.windows === 'round') P.porthole(ux(4.15), 0.45, 0.02, 0.05); else P.glass(ux(3.75), 0.41, ux(4.55), 0.49, 16);
    /* окна салона */
    const xsR = liv.windows === 'round' ? [3.8, 2.6, 1.4, 0.2, -1.0] : [3.9, 2.7, 1.5, 0.3, -0.9];
    const xsL = liv.windows === 'round' ? [2.6, 1.4, 0.2, -1.0] : [2.7, 1.5, 0.3, -0.9];
    xsR.forEach(x => liv.windows === 'round' ? P.porthole(ux(x), 0.05, 0.02, 0.05) : P.glass(ux(x - 0.36), 0.015, ux(x + 0.36), 0.09, 16));
    xsL.forEach(x => liv.windows === 'round' ? P.porthole(ux(x), 0.45, 0.02, 0.05) : P.glass(ux(x - 0.36), 0.41, ux(x + 0.36), 0.485, 16));
    /* правая передняя дверь, створки грузового люка, панели */
    P.seam([[ux(5.1), 0.0], [ux(5.1), 0.11], [ux(4.0), 0.11], [ux(4.0), 0.0]], 4);
    P.seam([[ux(-1.9), 0.62], [ux(-5.3), 0.75]], 4); P.seam([[ux(-1.9), 0.88], [ux(-5.3), 0.75]], 4); P.seam([[ux(-1.9), 0.62], [ux(-1.9), 0.88]], 4);
    for (let i = 0; i < 7; i++) P.seam([[ux(5.4 - i * 1.2), 0.62], [ux(5.4 - i * 1.2), 0.88]], 2);
    P.rivets(ux(-5.0), 0.22, ux(6.2), 90); P.rivets(ux(-5.0), 0.28, ux(6.2), 90);
    /* надписи и флаги */
    const txt = liv.windows === 'round' ? liv.low : liv.stripe;
    P.text(liv.type, ux(5.15), 0.15, 30, txt, { weight: '700' }); P.text(liv.type, ux(5.15), 0.35, 30, txt, { weight: '700', flip: true });
    P.flagRU(ux(6.0), 0.19, 0.03, 0.045); P.flagRU(ux(5.4), 0.31, 0.03, 0.045);
    P.text('ALTAY AVIA', ux(1.1), 0.165, 44, txt, { weight: '900', stretch: 1.05 });
    P.text('ALTAY AVIA', ux(1.1), 0.335, 44, txt, { weight: '900', stretch: 1.05, flip: true });
    return c;
  }
  function paintMi8Boom(liv) {
    const W = 1024, H = 256, c = makeCanvas(W, H), ctx = c.getContext('2d'), P = painter(ctx, W, H);
    P.rect(0, 0, 1, 1, liv.top);
    if (liv.windows === 'round') { P.rect(0, 0.55, 1, 0.95, liv.low); P.line([[0, 0.55], [1, 0.55]], '#ffffff', 4); P.line([[0, 0.95], [1, 0.95]], '#ffffff', 4); }
    else { P.line([[0, 0.15], [1, 0.15]], liv.stripe, 4); P.line([[0, 0.35], [1, 0.35]], liv.stripe, 4); }
    const col = liv.windows === 'round' ? liv.low : liv.stripe;
    P.text(liv.reg, 0.45, 0.14, 56, col, { weight: '900', stretch: 1.1 }); P.text(liv.reg, 0.45, 0.36, 56, col, { weight: '900', stretch: 1.1, flip: true });
    P.flagRU(0.16, 0.185, 0.05, 0.075); P.flagRU(0.16, 0.395, 0.05, 0.075);
    for (let i = 1; i < 7; i++) P.seam([[i / 7, 0], [i / 7, 1]], 2);
    return c;
  }
  function paintMi8Fin(liv) {
    const W = 512, H = 256, c = makeCanvas(W, H), ctx = c.getContext('2d'), P = painter(ctx, W, H);
    P.rect(0, 0, 1, 1, liv.top);
    if (liv.windows === 'round') P.rect(0, 0.56, 1, 0.94, liv.low); else { P.line([[0, 0.2], [1, 0.2]], liv.stripe, 4); P.line([[0, 0.3], [1, 0.3]], liv.stripe, 4); }
    P.seam([[0.5, 0], [0.5, 1]], 2);
    return c;
  }
  function paintMi8Deck(liv) {
    const W = 1024, H = 512, c = makeCanvas(W, H), ctx = c.getContext('2d'), P = painter(ctx, W, H);
    P.rect(0, 0, 1, 1, liv.top);
    for (let i = 0; i < 9; i++) { P.rect(0.56 + i * 0.03, 0.14, 0.575 + i * 0.03, 0.22, 'rgba(0,0,0,0.3)'); P.rect(0.56 + i * 0.03, 0.28, 0.575 + i * 0.03, 0.36, 'rgba(0,0,0,0.3)'); }
    [0.2, 0.42, 0.62, 0.8].forEach(u => P.seam([[u, 0], [u, 1]], 3)); P.seam([[0, 0.25], [1, 0.25]], 3);
    return c;
  }

  /* ============================================================
     ОКРУЖЕНИЕ: небо для отражений, площадка
     ============================================================ */
  function makeEnvironment(renderer) {
    const pm = new T.PMREMGenerator(renderer);
    const sc = new T.Scene();
    const skyGeo = new T.SphereGeometry(50, 48, 24);
    const top = new T.Color(0x86b9ea), horizon = new T.Color(0xeaf1f7), ground = new T.Color(0x9aa5b1);
    const pa = skyGeo.attributes.position, cols = [], tmp = new T.Color();
    for (let i = 0; i < pa.count; i++) { const h = pa.getY(i) / 50; if (h > 0) tmp.copy(horizon).lerp(top, Math.pow(h, 0.6)); else tmp.copy(horizon).lerp(ground, Math.pow(-h, 0.5)); cols.push(tmp.r, tmp.g, tmp.b); }
    skyGeo.setAttribute('color', new T.Float32BufferAttribute(cols, 3));
    sc.add(new T.Mesh(skyGeo, new T.MeshBasicMaterial({ side: T.BackSide, vertexColors: true })));
    const addPanel = (x, y, z, w, h, i) => { const m = new T.Mesh(new T.PlaneGeometry(w, h), new T.MeshBasicMaterial({ color: new T.Color().setScalar(i) })); m.position.set(x, y, z); m.lookAt(0, 0, 0); sc.add(m); };
    addPanel(10, 25, 8, 22, 10, 2.4); addPanel(-20, 14, -10, 14, 8, 1.5); addPanel(12, 6, -25, 16, 6, 1.2);
    const tex = pm.fromScene(sc, 0.04).texture; pm.dispose(); return tex;
  }

  function makeHelipad(radius, opts) {
    opts = opts || {};
    const g = new T.Group();
    const W = 1024, c = makeCanvas(W, W), ctx = c.getContext('2d');
    ctx.fillStyle = opts.dark ? '#2b3a55' : '#c9cfd6'; ctx.fillRect(0, 0, W, W);
    for (let i = 0; i < 5000; i++) { ctx.fillStyle = 'rgba(' + (Math.random() > 0.5 ? '255,255,255' : '0,0,0') + ',' + (Math.random() * 0.05) + ')'; ctx.fillRect(Math.random() * W, Math.random() * W, 2, 2); }
    ctx.strokeStyle = opts.dark ? 'rgba(255,255,255,0.10)' : 'rgba(40,50,70,0.22)'; ctx.lineWidth = 3;
    for (let i = 0; i <= 8; i++) { ctx.beginPath(); ctx.moveTo(i * W / 8, 0); ctx.lineTo(i * W / 8, W); ctx.stroke(); ctx.beginPath(); ctx.moveTo(0, i * W / 8); ctx.lineTo(W, i * W / 8); ctx.stroke(); }
    ctx.strokeStyle = '#f0c419'; ctx.lineWidth = 22; ctx.beginPath(); ctx.arc(W / 2, W / 2, W * 0.36, 0, Math.PI * 2); ctx.stroke();
    ctx.lineWidth = 34; ctx.lineCap = 'butt';
    const hx = W / 2, hy = W / 2, hw = W * 0.07, hh = W * 0.11;
    ctx.beginPath(); ctx.moveTo(hx - hw, hy - hh); ctx.lineTo(hx - hw, hy + hh); ctx.moveTo(hx + hw, hy - hh); ctx.lineTo(hx + hw, hy + hh); ctx.moveTo(hx - hw, hy); ctx.lineTo(hx + hw, hy); ctx.stroke();
    const tex = new T.CanvasTexture(c); tex.encoding = T.sRGBEncoding; tex.anisotropy = 8;
    const pad = new T.Mesh(new T.CircleGeometry(radius, 64), new T.MeshStandardMaterial({ map: tex, roughness: 0.95, metalness: 0, envMapIntensity: 0.25 }));
    pad.rotation.x = -Math.PI / 2; pad.receiveShadow = true; g.add(pad);
    const ground = new T.Mesh(new T.CircleGeometry(radius * 6, 64), new T.MeshStandardMaterial({ color: opts.dark ? 0x172742 : 0xdbe4ec, roughness: 1, envMapIntensity: 0.2 }));
    ground.rotation.x = -Math.PI / 2; ground.position.y = -0.02; ground.receiveShadow = true; g.add(ground);
    return g;
  }


  /* ============================================================
     ПЕЙЗАЖ: долина Катуни — площадка «Карасук», река, тайга, горы со снежниками
     (процедурная фрактальная местность, цвета по высоте и уклону, лес — InstancedMesh)
     ============================================================ */
  function hash2(x, y) { const s = Math.sin(x * 127.1 + y * 311.7) * 43758.5453; return s - Math.floor(s); }
  function vnoise(x, y) {
    const xi = Math.floor(x), yi = Math.floor(y), xf = x - xi, yf = y - yi;
    const u = xf * xf * xf * (xf * (xf * 6 - 15) + 10), v = yf * yf * yf * (yf * (yf * 6 - 15) + 10);
    const a = hash2(xi, yi), b = hash2(xi + 1, yi), c = hash2(xi, yi + 1), d = hash2(xi + 1, yi + 1);
    return a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v;
  }
  function fbm(x, y, oct) { let s = 0, a = 0.5, f = 1, n = 0; for (let i = 0; i < oct; i++) { s += a * vnoise(x * f, y * f); n += a; a *= 0.5; f *= 2.03; } return s / n; }
  function ridged(x, y, oct) { let s = 0, a = 0.5, f = 1, n = 0; for (let i = 0; i < oct; i++) { const v = 1 - Math.abs(vnoise(x * f, y * f) * 2 - 1); s += a * v * v; n += a; a *= 0.5; f *= 2.1; } return s / n; }
  const smooth = (a, b, x) => { const t = Math.max(0, Math.min(1, (x - a) / (b - a))); return t * t * (3 - 2 * t); };
  const LERP = (c1, c2, t) => new T.Color().copy(c1).lerp(c2, t);

  /* высота местности (м) в точке (x,z): равнина у площадки, предгорья с 400 м, хребты 1–2 км с пиками до 650 м */
  function terrainHeight(x, z) {
    const d = Math.hypot(x, z), ang = Math.atan2(z, x);
    const back = 0.5 + 0.5 * Math.cos(ang - 2.4);                        // самые высокие горы — сзади-слева
    const amp = smooth(1200, 3000, d) * (420 + 420 * back);
    const r = ridged(x * 0.00055 + 3.1, z * 0.00055 + 7.7, 5) * 0.65 + ridged(x * 0.0026 + 9.3, z * 0.0026 + 1.7, 4) * 0.35;
    const f = fbm(x * 0.0022 + 11, z * 0.0022 + 5, 4);
    let h = amp * (0.3 + 0.7 * r) + smooth(600, 1700, d) * 80 * f;
    h += 2.5 * fbm(x * 0.03, z * 0.03, 3) * smooth(20, 90, d) + smooth(1300, 3200, d) * 60 * fbm(x * 0.006, z * 0.006, 3);
    return h;
  }
  function riverDist(x, z) {
    const zc = -160 + 90 * Math.sin(x * 0.0042 + 0.6) + 32 * Math.sin(x * 0.013 + 2.0);
    return Math.abs(z - zc);
  }
  function colorAt(x, z, h, slope, palette, out) {
    const P = palette, n = fbm(x * 0.03 + 50, z * 0.03 + 9, 3), n2 = fbm(x * 0.0025 + 3, z * 0.0025 + 8, 3);
    out.copy(P.grass).lerp(P.grass2, n);
    const forest = smooth(0.2, 0.6, 0.5 * n + 0.5 * n2) * smooth(30, 110, h + 60 * n) * (1 - smooth(280, 360, h));
    out.lerp(P.forest, forest);
    out.lerp(P.alp, smooth(280, 380, h) * (1 - smooth(380, 460, h)));
    const rock = smooth(0.22, 0.42, slope) * 0.95 + smooth(400, 500, h) * 0.6;
    out.lerp(n > 0.5 ? P.rock : P.rock2, Math.min(1, rock));
    const snowLine = 450 + 90 * n2;
    out.lerp(P.snow, smooth(snowLine - 15, snowLine + 30, h) * (1 - smooth(0.62, 0.85, slope)));
    const rd = riverDist(x, z);
    if (h < 70) { if (rd < 28) out.lerp(P.sand, 1 - smooth(18, 28, rd)); if (rd < 17) out.lerp(P.water, 1 - smooth(10, 17, rd)); }
    const d = Math.hypot(x, z);
    if (d < 46) out.lerp(P.concrete, 1 - smooth(32, 46, d));
    return out;
  }
  function makeLandscape(opts) {
    opts = opts || {};
    const g = new T.Group();
    const L = h => new T.Color(h).convertSRGBToLinear();
    const P = { grass: L(0x8aab5c), grass2: L(0x6d9447), forest: L(0x3b6636), alp: L(0x9fb56b), rock: L(0x8d9095), rock2: L(0x6b6d72), snow: L(0xf7fbff), water: L(0x3fa6bd), sand: L(0xc9c0a4), concrete: L(0xb9bcc0) };
    const mat = new T.MeshStandardMaterial({ vertexColors: true, roughness: 0.95, metalness: 0, envMapIntensity: 0.25 });
    const tmp = new T.Color();
    const paint = geo => {
      const pos = geo.attributes.position, cols = new Float32Array(pos.count * 3);
      for (let i = 0; i < pos.count; i++) {
        const x = pos.getX(i), z = pos.getZ(i); let h = terrainHeight(x, z);
        const rd = riverDist(x, z); if (h < 70 && rd < 17) h -= 3.5 * (1 - rd / 17);
        pos.setY(i, h);
      }
      geo.computeVertexNormals();
      if (geo.index && geo.attributes.normal.getY(0) < 0) {           // обход по часовой → развернуть треугольники
        const ix = geo.index.array; for (let i = 0; i < ix.length; i += 3) { const t = ix[i + 1]; ix[i + 1] = ix[i + 2]; ix[i + 2] = t; }
        geo.index.needsUpdate = true; geo.computeVertexNormals();
      }
      const nrm = geo.attributes.normal;
      for (let i = 0; i < pos.count; i++) {
        colorAt(pos.getX(i), pos.getZ(i), pos.getY(i), 1 - nrm.getY(i), P, tmp);
        cols[i * 3] = tmp.r; cols[i * 3 + 1] = tmp.g; cols[i * 3 + 2] = tmp.b;
      }
      geo.setAttribute('color', new T.Float32BufferAttribute(cols, 3));
      const m = new T.Mesh(geo, mat); m.receiveShadow = true; return m;
    };
    /* ближняя равнина — мелкая сетка; дальний пояс гор — полярное кольцо с растущим шагом */
    const inner = new T.PlaneGeometry(820, 820, 190, 190); inner.rotateX(-Math.PI / 2);
    g.add(paint(inner));
    const A = 320, R = 120, r0 = 395, r1 = 5200, pos = [], idx = [];
    for (let j = 0; j <= R; j++) {
      const t = j / R, r = r0 + (r1 - r0) * t * t;
      for (let i = 0; i <= A; i++) { const a = i / A * Math.PI * 2; pos.push(Math.cos(a) * r, 0, Math.sin(a) * r); }
    }
    for (let j = 0; j < R; j++) for (let i = 0; i < A; i++) { const a = j * (A + 1) + i, b = a + 1, c = a + A + 1, d = c + 1; idx.push(a, c, b, b, c, d); }
    const ring = new T.BufferGeometry(); ring.setAttribute('position', new T.Float32BufferAttribute(pos, 3)); ring.setIndex(idx);
    const outer = paint(ring); outer.position.y = -0.35; g.add(outer);
    /* площадка «H» */
    const pad = makeHelipad(14, { dark: false }); pad.children[1].visible = false; pad.position.y = 0.02; g.add(pad);
    /* тайга: низкополигональные ели с цветом по экземплярам */
    const tree = new T.ConeGeometry(1.6, 6, 6); tree.translate(0, 5.2, 0);
    const trunk = new T.CylinderGeometry(0.28, 0.4, 2.6, 5); trunk.translate(0, 1.3, 0);
    const N = opts.trees || 3200;
    const im = new T.InstancedMesh(tree, new T.MeshStandardMaterial({ roughness: 0.9, metalness: 0, envMapIntensity: 0.2 }), N);
    const tm = new T.InstancedMesh(trunk, new T.MeshStandardMaterial({ color: L(0x4a3b2a), roughness: 1 }), N);
    const M = new T.Matrix4(), q = new T.Quaternion(), sc = new T.Vector3(), pv = new T.Vector3(), col = new T.Color(), up = new T.Vector3(0, 1, 0);
    const cT1 = L(0x2f5a34), cT2 = L(0x4f7d3a);
    let k = 0, tries = 0;
    while (k < N && tries < N * 14) {
      tries++;
      const x = (hash2(tries, 3.3) - 0.5) * 2400, z = (hash2(tries, 9.1) - 0.5) * 2400;
      const h = terrainHeight(x, z), d = Math.hypot(x, z);
      if (d < 118 || h > 280 || (riverDist(x, z) < 24 && h < 70)) continue;
      const n = fbm(x * 0.03 + 50, z * 0.03 + 9, 3), n2 = fbm(x * 0.0025 + 3, z * 0.0025 + 8, 3);
      const cover = smooth(0.2, 0.6, 0.5 * n + 0.5 * n2) * smooth(30, 110, h + 60 * n);
      if (hash2(tries, 1.7) > 0.08 + 0.92 * cover) continue;
      const s = 0.75 + hash2(tries, 5.5) * 0.7 + smooth(400, 1200, d) * 1.6;
      pv.set(x, h - 0.3, z); q.setFromAxisAngle(up, hash2(tries, 2.2) * 6.28); sc.set(s, s * (0.9 + hash2(tries, 8.8) * 0.5), s);
      M.compose(pv, q, sc); im.setMatrixAt(k, M); tm.setMatrixAt(k, M);
      im.setColorAt(k, col.copy(cT1).lerp(cT2, hash2(tries, 4.4)));
      k++;
    }
    im.count = k; tm.count = k; g.add(im); g.add(tm);
    g.userData.height = terrainHeight;
    return g;
  }

  /* ============================================================
     VIEWER — интерактивный просмотр: только вращение (без зума),
     режимы винтов, авто-облёт, анимация прилёта, связь со скроллом
     ============================================================ */
  function Viewer(container, opts) {
    opts = opts || {};
    this.container = container; this.opts = opts;
    const w = container.clientWidth || 800, h = container.clientHeight || 500;
    const renderer = new T.WebGLRenderer({ antialias: true, alpha: !!opts.transparent, powerPreference: 'high-performance' });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, opts.maxDpr || 2));
    renderer.setSize(w, h);
    renderer.outputEncoding = T.sRGBEncoding; renderer.toneMapping = T.ACESFilmicToneMapping; renderer.toneMappingExposure = opts.exposure || 1.0;
    renderer.shadowMap.enabled = true; renderer.shadowMap.type = T.PCFSoftShadowMap;
    container.appendChild(renderer.domElement);
    Object.assign(renderer.domElement.style, { display: 'block', width: '100%', height: '100%' });
    this.renderer = renderer;

    const scene = new T.Scene();
    if (!opts.transparent) scene.background = new T.Color(opts.background || 0xeaf1f7);
    scene.environment = makeEnvironment(renderer);
    this.scene = scene;
    this.camera = new T.PerspectiveCamera(opts.fov || 30, w / h, 0.1, opts.helipad ? 14000 : 500);

    scene.add(new T.HemisphereLight(0xdbe9f7, 0x8a94a0, 0.5));
    const sun = new T.DirectionalLight(0xfff3e0, 1.3); sun.position.set(18, 30, 14); sun.castShadow = true;
    sun.shadow.mapSize.set(2048, 2048); sun.shadow.camera.near = 1; sun.shadow.camera.far = 120; sun.shadow.bias = -0.0004; sun.shadow.normalBias = 0.02;
    scene.add(sun); this.sun = sun;
    const fill = new T.DirectionalLight(0xcfe3ff, 0.35); fill.position.set(-20, 8, -10); scene.add(fill);
    if (opts.helipad) {
      const S0 = opts.scene && global.Heli3D && global.Heli3D.scenes && global.Heli3D.scenes[opts.scene];
      // дымка: у реальной площадки — воздушная перспектива (дальние хребты голубеют), у процедурной — как раньше
      scene.fog = S0 ? new T.Fog(opts.fogColor !== undefined ? opts.fogColor : 0xcddcec, 500, 11000) : new T.Fog(opts.fogColor !== undefined ? opts.fogColor : 0xdcebff, 2200, 9000);
      const S = opts.scene && global.Heli3D && global.Heli3D.scenes && global.Heli3D.scenes[opts.scene];
      if (S) { this.pad = S.placeholder(); scene.add(this.pad); S.load(this, opts.sceneBase || 'scene/', opts.sceneVer); }   // реальная площадка (Карасук)
      else { this.pad = makeLandscape({ trees: opts.trees }); scene.add(this.pad); }                                      // процедурный пейзаж
    }
    this.viewOffsetX = opts.viewOffsetX || 0.5;   // доля ширины, где стоит цель (0.5 — центр)
    if (opts.shadowPlane !== false && !opts.helipad) { const sh = new T.Mesh(new T.PlaneGeometry(80, 80), new T.ShadowMaterial({ opacity: opts.shadowOpacity || 0.18 })); sh.rotation.x = -Math.PI / 2; sh.receiveShadow = true; scene.add(sh); }
    if (opts.dark && opts.fog !== false && !opts.helipad) { scene.fog = new T.Fog(opts.fogColor !== undefined ? opts.fogColor : 0x11244a, 20, 90); this._fog = true; }

    this.model = null; this.rig = new T.Group(); scene.add(this.rig); // rig — контейнер для анимаций прилёта/скролла
    this.rotorState = opts.rotorState || 'idle';
    this.orbit = { theta: opts.theta !== undefined ? opts.theta : 0.65, phi: opts.phi !== undefined ? opts.phi : 1.22, dist: 20, target: new T.Vector3(0, 1.5, 0) };
    this.auto = opts.autoRotate !== false; this.autoSpeed = opts.autoSpeed || 0.12;
    this.idleTimer = 0; this.clock = new T.Clock(); this.running = true; this._first = true; this._visible = true;
    this.fly = null; this.scrollP = 0; this._hoverAmp = opts.hover ? 1 : 0;
    this._bindControls();
    this._ro = new ResizeObserver(() => this.resize()); this._ro.observe(container); this.resize();
    this._loop = this._loop.bind(this); requestAnimationFrame(this._loop);
  }
  Viewer.prototype.setModel = function (model, view) {
    if (this.model) { this.rig.remove(this.model); disposeGroup(this.model); }
    this.model = model; this.rig.add(model);
    const b = model.userData.bounds || { length: 12, height: 3.5, width: 10, center: 0 };
    // view.fitRef — габариты эталонного борта: камера одна для всех моделей, поэтому борта видны в истинном масштабе
    this._fitRef = view && view.fitRef ? Object.assign({}, b, view.fitRef) : null;
    const hb = this._fitRef || b;
    const ty = view && view.tyRel ? hb.height * view.tyRel : (view && view.ty) || b.height * 0.42;   // tyRel — доля высоты модели (эталона)
    this.orbit.target.set(view && view.tx !== undefined ? view.tx : (b.center || 0), ty, 0);
    /* fit:'auto' — дистанция по описанной сфере: модель целиком в кадре при любом угле поворота */
    this._autoFit = (view && view.fit === 'auto') ? (view.margin || 1.06) : 0;
    const fit = this._autoFit ? this._fitDistance(hb) : Math.max(hb.length, hb.width || 0) * (view && view.fit || 0.95);
    this._bounds = b;
    this.orbit.dist = fit;
    if (view && view.theta !== undefined) this.orbit.theta = view.theta;
    if (view && view.phi !== undefined) this.orbit.phi = view.phi;
    if (this._fog) { this.scene.fog.near = fit * 1.1; this.scene.fog.far = fit * 4.2; }
    const s = this.sun.shadow.camera; s.left = -b.length * 0.8; s.right = b.length * 0.8; s.top = b.length * 0.8; s.bottom = -b.length * 0.8; s.updateProjectionMatrix();
    this.setRotorState(this.rotorState);
    this._first = true;
    return this;
  };
  /* Общая обработка результата GLTFLoader: границы, поиск винтов по именам узлов, применение модели. */
  function onDoneGLTF(self, gltf, view, onDone) {
    const m = gltf.scene; m.traverse(o => { if (o.isMesh) { o.castShadow = !o.material.transparent; } });   // стекло тени не отбрасывает
    const box = new T.Box3().setFromObject(m); const size = box.getSize(new T.Vector3()); const c = box.getCenter(new T.Vector3());
    m.position.y -= box.min.y; m.position.x -= c.x; m.position.z -= c.z;
    m.userData.bounds = { length: size.x, height: size.y, width: size.z, center: 0, reach: Math.hypot(size.x, size.z) / 2 };
    const rotors = [];
    m.traverse(o => {
      const n = (o.name || '').toLowerCase(); if (!/rotor|prop|blade/.test(n)) return;
      if (o.parent && rotors.some(r => r.obj === o.parent || r.obj === o)) return;
      const tail = /tail|tr_|anti/.test(n);
      const disc = new T.Object3D(); disc.visible = false;
      rotors.push({ obj: o, axis: tail ? 'z' : 'y', dir: 1, disc, rpm: tail ? 1100 : 300 });
    });
    m.userData.rotors = rotors;
    self.setModel(m, view); onDone && onDone(null, m);
  }

  /* Компактный формат моделей сайта (build/import/glb2js.py): обычный <script src="models/<key>.js">,
     геометрия в base64 (int16 позиции, int8 нормали, uint16 UV), текстура — обычная картинка <img>.
     Не зависит от GLTFLoader, WebAssembly, fetch() и blob: — работает в любой песочнице, где работают скрипты и картинки. */
  function b64ToBuffer(str) {
    const bin = atob(str); const u8 = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) u8[i] = bin.charCodeAt(i);
    return u8.buffer;
  }
  function packedToGroup(data, texture) {
    const root = new T.Group(); root.name = 'PackedModel';
    const groups = {};
    Object.keys(data.pivots || {}).forEach(n => { const g = new T.Group(); g.name = n; g.position.fromArray(data.pivots[n]); root.add(g); groups[n] = g; });
    // data.side === 'front' — модель из односторонних граней (AS350): обратные стороны отсекаются; иначе (Ми-8) — двусторонние
    const mm = data.mat || {};   // data.mat — металлик/шероховатость краски модели (Ми-171 — «вишня металлик»)
    const mat = new T.MeshStandardMaterial({ map: texture, metalness: mm.metalness !== undefined ? mm.metalness : 0.05, roughness: mm.roughness !== undefined ? mm.roughness : 0.42, side: data.side === 'front' ? T.FrontSide : T.DoubleSide });
    // двусторонняя обшивка: изнанка (видна сквозь остекление кабины) — серая, как отделка салона, а не ливрея наружу
    if (data.side !== 'front') mat.onBeforeCompile = sh => { sh.fragmentShader = sh.fragmentShader.replace('#include <map_fragment>', '#include <map_fragment>\n  if (!gl_FrontFacing) diffuseColor.rgb = vec3(0.075, 0.085, 0.09);'); };
    let glass = null;   // md.m === 'glass': остекление кабины — тонированное, с отражениями неба, салон просвечивает
    const gm = data.glass || {};   // data.glass — тонировка остекления модели (цвет/прозрачность), по умолчанию — тёмная, как у AS350
    const glassMat = () => glass || (glass = new T.MeshStandardMaterial({ color: new T.Color(gm.color !== undefined ? gm.color : 0x0a1016).convertSRGBToLinear(), metalness: 0.35, roughness: 0.04, transparent: true, opacity: gm.opacity !== undefined ? gm.opacity : 0.8, envMapIntensity: 1.8, side: T.DoubleSide, depthWrite: false }));
    let win = null;     // md.m === 'window': окна салона — непрозрачное тонированное стекло с отражениями неба
    const winMat = () => win || (win = new T.MeshStandardMaterial({ color: new T.Color(0x16202b).convertSRGBToLinear(), metalness: 0.55, roughness: 0.07, envMapIntensity: 1.5, side: T.DoubleSide }));
    const al4 = n => (n + 3) & ~3;
    data.meshes.forEach(md => {
      const bin = b64ToBuffer(md.d), c = md.c, ni = md.i; let off = 0;
      const pos = new Int16Array(bin, 0, c * 3); off = al4(c * 6);
      const uv = new Uint16Array(bin, off, c * 2); off = al4(off + c * 4);
      const idx = md.it === 32 ? new Uint32Array(bin, off, ni) : new Uint16Array(bin, off, ni); off += ni * (md.it / 8);
      const nrm = new Int8Array(bin, off, c * 3);
      const g = new T.BufferGeometry();
      g.setAttribute('position', new T.BufferAttribute(pos, 3));
      g.setAttribute('normal', new T.BufferAttribute(nrm, 3, true));
      g.setAttribute('uv', new T.BufferAttribute(uv, 2, true));
      g.setIndex(new T.BufferAttribute(idx, 1));
      const isGlass = md.m === 'glass';
      const mesh = new T.Mesh(g, isGlass ? glassMat() : md.m === 'window' ? winMat() : mat); mesh.name = md.n || ''; mesh.position.fromArray(md.o); mesh.scale.fromArray(md.s);
      if (isGlass) { mesh.renderOrder = 2; mesh.castShadow = false; }
      (md.g && groups[md.g] ? groups[md.g] : root).add(mesh);
    });
    return root;
  }
  const _packedTex = {};
  Viewer.prototype.loadPacked = function (key, url, texBase, view, onDone) {
    const self = this;
    const build = data => {
      // метка версии сборки: иначе браузер отдаст старую текстуру из кэша к новой геометрии
      const ver = (url.match(/[?&]v=([^&]+)/) || [])[1] || (document.documentElement.dataset.v || '');
      const texUrl = texBase + data.tex + (ver ? '?v=' + ver : '');
      const finish = tex => { try { onDoneGLTF(self, { scene: packedToGroup(data, tex) }, view, onDone); } catch (e) { onDone && onDone(e); } };
      if (_packedTex[texUrl]) return finish(_packedTex[texUrl]);
      const tex = new T.TextureLoader().load(texUrl, () => finish(tex), undefined, () => finish(tex));
      tex.flipY = false; tex.encoding = T.sRGBEncoding; tex.wrapS = tex.wrapT = T.RepeatWrapping; tex.anisotropy = 8;
      _packedTex[texUrl] = tex;
    };
    const have = global.AltayModels && global.AltayModels[key];
    if (have) return build(have);
    const s = document.createElement('script'); s.src = url; s.async = true;
    s.onload = () => { const d = global.AltayModels && global.AltayModels[key]; if (d) build(d); else onDone && onDone(new Error('Нет данных модели ' + key)); };
    s.onerror = () => onDone && onDone(new Error('Не удалось загрузить ' + url));
    (document.head || document.documentElement).appendChild(s);
  };

  /* Разбор уже загруженного glTF (JSON-строка или объект) — без единого сетевого запроса.
     Используется для моделей, встроенных прямо в HTML страницы (надёжнее fetch() в песочнице артефакта). */
  Viewer.prototype.parseGLTF = function (json, view, onDone) {
    const self = this;
    if (!T.GLTFLoader) { onDone && onDone(new Error('GLTFLoader не подключён')); return; }
    const loader = new T.GLTFLoader();
    if (global.MeshoptDecoder && loader.setMeshoptDecoder) loader.setMeshoptDecoder(global.MeshoptDecoder);
    const text = typeof json === 'string' ? json : JSON.stringify(json);
    loader.parse(text, '', gltf => onDoneGLTF(self, gltf, view, onDone), err => onDone && onDone(err));
  };
  /* Загрузка внешней glTF-модели по URL (fetch). Ожидается масштаб в метрах, нос по +X. */
  Viewer.prototype.loadGLTF = function (url, view, onDone) {
    const self = this;
    if (!T.GLTFLoader) { onDone && onDone(new Error('GLTFLoader не подключён')); return; }
    const loader = new T.GLTFLoader();
    if (global.MeshoptDecoder && loader.setMeshoptDecoder) loader.setMeshoptDecoder(global.MeshoptDecoder);
    loader.load(url, gltf => onDoneGLTF(self, gltf, view, onDone), undefined, err => {
      // хостинг может не отдавать .glb — пробуем JSON-вариант (glTF с data-URI буфером)
      if (/\.glb(\?|$)/.test(url)) self.loadGLTF(url.replace(/\.glb(\?|$)/, '.json$1'), view, onDone); else onDone && onDone(err);
    });
  };
  Viewer.prototype.setRotorState = function (s) {
    this.rotorState = s; if (!this.model) return;
    (this.model.userData.rotors || []).forEach(r => { r.disc.visible = (s === 'fast'); if (!r.disc.isMesh) return; r.obj.traverse(o => { if (o.isMesh && o !== r.disc) { o.material.transparent = (s === 'fast'); o.material.opacity = (s === 'fast') ? 0.3 : 1; } }); });
  };
  /* Анимация прилёта: модель влетает со стороны, снижается, гасит крен и зависает */
  Viewer.prototype.flyIn = function (duration, from) {
    this.fly = { t: 0, dur: duration || 3.2, from: from || { x: 20, y: 7, z: -10, roll: -0.35, pitch: 0.18 } };
    this.setRotorState('fast'); this.idleTimer = -duration;
  };
  Viewer.prototype.setScroll = function (p) { this.scrollP = clamp(p, 0, 1); };
  Viewer.prototype._fitDistance = function (b) {
    // радиус «досягаемости» от цели орбиты: концы лопастей, хвост, нос
    const R = b.reach || Math.max(b.length, b.width || 0) * 0.55;
    const half = Math.tan(this.camera.fov * Math.PI / 360), aspect = this.camera.aspect || 1;
    const t = this._offX(), margin = Math.min(t, 1 - t) / 0.5;   // доступная половина ширины при смещённой цели
    const dH = R / (half * Math.min(aspect, 1.6) * margin);      // по горизонтали (винт, хвост)
    const dV = (b.height * 0.75 + R * 0.4) / half;              // по вертикали (корпус + наклон диска)
    return Math.max(dH, dV) * this._autoFit;
  };
  Viewer.prototype._offX = function () { return this.container.clientWidth < 900 ? 0.5 : this.viewOffsetX; };
  Viewer.prototype.resize = function () {
    const w = this.container.clientWidth, h = this.container.clientHeight; if (!w || !h) return;
    this.renderer.setSize(w, h, false); this.camera.aspect = w / h;
    const t = this._offX();
    if (t !== 0.5) this.camera.setViewOffset(w * 2, h, (1 - t) * w, 0, w, h); else this.camera.clearViewOffset();
    this.camera.updateProjectionMatrix();
    if (this._autoFit && this._bounds) this.orbit.dist = this._fitDistance(this._fitRef || this._bounds);
  };
  Viewer.prototype._bindControls = function () {
    const el = this.renderer.domElement, o = this.orbit, self = this;
    let drag = false, lx = 0, ly = 0;
    el.style.touchAction = 'pan-y'; el.style.cursor = 'grab';
    const down = (x, y) => { drag = true; lx = x; ly = y; self.idleTimer = 0; el.style.cursor = 'grabbing'; };
    const move = (x, y) => { if (!drag) return; o.theta -= (x - lx) * 0.006; o.phi = clamp(o.phi - (y - ly) * 0.004, 0.55, 1.5); lx = x; ly = y; self.idleTimer = 0; };
    el.addEventListener('pointerdown', e => { if (e.pointerType === 'touch') return; down(e.clientX, e.clientY); el.setPointerCapture(e.pointerId); });
    el.addEventListener('pointermove', e => { if (e.pointerType === 'touch') return; move(e.clientX, e.clientY); });
    el.addEventListener('pointerup', () => { drag = false; el.style.cursor = 'grab'; });
    el.addEventListener('pointercancel', () => { drag = false; el.style.cursor = 'grab'; });
    el.addEventListener('touchstart', e => { if (e.touches.length === 1) down(e.touches[0].clientX, e.touches[0].clientY); }, { passive: true });
    el.addEventListener('touchmove', e => { if (e.touches.length === 1 && drag) move(e.touches[0].clientX, e.touches[0].clientY); }, { passive: true });
    el.addEventListener('touchend', () => { drag = false; });
    // колесо — только прокрутка страницы (зум отключён)
  };
  const easeOut = t => 1 - Math.pow(1 - t, 3);
  Viewer.prototype._loop = function () {
    if (!this.running) return;
    requestAnimationFrame(this._loop);
    const dt = Math.min(0.05, this.clock.getDelta());
    if (!this._visible) return;
    this.idleTimer += dt;
    if (this.auto && this.idleTimer > 2.5) this.orbit.theta += this.autoSpeed * dt;
    const o = this.orbit;
    const cx = o.target.x + o.dist * Math.sin(o.phi) * Math.sin(o.theta), cz = o.target.z + o.dist * Math.sin(o.phi) * Math.cos(o.theta), cy = o.target.y + o.dist * Math.cos(o.phi);
    if (this._first) { this.camera.position.set(cx, cy, cz); this._first = false; } else this.camera.position.lerp(new T.Vector3(cx, cy, cz), 0.1);
    this.camera.lookAt(o.target);
    if (this.model) {
      const rate = this.rotorState === 'fast' ? 1 : this.rotorState === 'idle' ? 0.06 : 0;
      (this.model.userData.rotors || []).forEach(r => { const w = r.rpm / 60 * Math.PI * 2 * rate * dt * r.dir; if (r.axis === 'y') r.obj.rotation.y += w; else r.obj.rotation.z += w; });
      const t = this.clock.elapsedTime;
      const rig = this.rig;
      if (this.fly) {
        this.fly.t += dt; const k = easeOut(clamp(this.fly.t / this.fly.dur, 0, 1)), f = this.fly.from;
        rig.position.set(f.x * (1 - k), f.y * (1 - k), f.z * (1 - k)); rig.rotation.set(0, 0, 0);
        rig.rotation.z = f.roll * (1 - k); rig.rotation.x = 0; rig.rotation.order = 'YXZ';
        rig.rotation.x = f.pitch * Math.sin(k * Math.PI);
        if (this.fly.t >= this.fly.dur) { this.fly = null; if (this.opts.rotorState !== 'fast') this.setRotorState(this.opts.rotorState || 'idle'); }
      } else {
        const hover = this._hoverAmp;
        rig.position.set(0, Math.sin(t * 0.9) * 0.08 * hover, 0);
        rig.rotation.z = Math.sin(t * 0.7) * 0.012 * hover;
        rig.rotation.x = 0;
      }
      if (this.scrollP > 0) { const p = this.scrollP; rig.position.y += p * 9; rig.position.x += p * 6; rig.rotation.x -= p * 0.22; rig.rotation.z += p * 0.15; }
    }
    if (this._sceneTick) this._sceneTick(this.clock.elapsedTime);
    this.renderer.render(this.scene, this.camera);
  };
  Viewer.prototype.setVisible = function (v) { this._visible = v; };
  /* Сцена загружена (или не удалась — тогда процедурный пейзаж вместо временной земли) */
  Viewer.prototype.setScene = function (grp) {
    if (this.pad) { this.scene.remove(this.pad); disposeGroup(this.pad); }
    this.pad = grp || makeLandscape({ trees: this.opts.trees });
    this.scene.add(this.pad);
    this._sceneTick = this.pad.userData.tick || null;
  };
  Viewer.prototype.dispose = function () { this.running = false; this._ro.disconnect(); this.renderer.dispose(); };
  function disposeGroup(g) { g.traverse(o => { if (o.geometry) o.geometry.dispose(); if (o.material) (Array.isArray(o.material) ? o.material : [o.material]).forEach(m => { if (m.map) m.map.dispose(); m.dispose(); }); }); }
  function clamp(v, a, b) { return Math.max(a, Math.min(b, v)); }

  const MODELS = {
    as350: { name: 'Eurocopter AS350', build: () => buildAS350(LIVERY.as350), view: { fit: 1.05, ty: 1.5 } },
    mi8amt: { name: 'Ми-8АМТ', build: () => buildMi8(LIVERY.mi8amt), view: { fit: 1.0, ty: 2.5 } },
    mi171: { name: 'Ми-171', build: () => buildMi8(LIVERY.mi171), view: { fit: 1.0, ty: 2.5 } }
  };

  global.Heli3D = { loft, slab, bladeGeometry, buildAS350, buildMi8, LIVERY, MODELS, Viewer, makeEnvironment, makeHelipad, makeLandscape, terrainHeight, MAT, painter, canvasTexture, makeCanvas, disposeGroup };
})(window);
