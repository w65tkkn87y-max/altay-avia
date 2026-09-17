/* ============================================================
   Heli3D — процедурные 3D-модели вертолётов парка «АлтайАвиа»
   Eurocopter AS350 (H125), Ми-8АМТ, Ми-171
   Требует three.js r128 (window.THREE)
   Система координат: X — вперёд (нос), Y — вверх, Z — правый борт
   ============================================================ */
(function (global) {
  'use strict';
  const T = global.THREE;
  if (!T) { console.error('Heli3D: THREE не найден'); return; }

  const DEG = Math.PI / 180;

  /* ---------- Лофт: корпус из последовательных сечений ----------
     station: { x, y, z, w, h, hb, n, nb, u }
       w  — полуширина (по Z), h — полувысота вверх, hb — полувысота вниз
       n  — показатель суперэллипса (2 — эллипс, 3–4 — «прямоугольнее»)
       u  — необязательная координата текстуры вдоль оси
  ------------------------------------------------------------- */
  function loft(stationsIn, opts) {
    opts = opts || {};
    const segs = opts.segs || 40;
    let st = stationsIn.slice().sort((a, b) => a.x - b.x);
    if (opts.caps !== false) {
      const a = st[0], b = st[st.length - 1], eps = 0.004;
      st = [Object.assign({}, a, { x: a.x - eps, w: eps, h: eps, hb: eps, u: 0 }), ...st, Object.assign({}, b, { x: b.x + eps, w: eps, h: eps, hb: eps, u: 1 })];
    }
    const N = st.length;
    const pos = [], uv = [], idx = [];
    const xmin = st[0].x, xmax = st[N - 1].x;
    for (let i = 0; i < N; i++) {
      const s = st[i];
      const n = s.n || 2, nb = s.nb || n;
      const hb = s.hb !== undefined ? s.hb : s.h;
      const uCoord = s.u !== undefined ? s.u : (s.x - xmin) / Math.max(1e-6, xmax - xmin);
      for (let j = 0; j <= segs; j++) {
        const t = j / segs, th = t * Math.PI * 2;
        const c = Math.cos(th), sn = Math.sin(th);
        const hh = sn >= 0 ? s.h : hb;
        const e = sn >= 0 ? n : nb;
        const pz = Math.sign(c) * Math.pow(Math.abs(c), 2 / e) * s.w;
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

  /* Плоская деталь с плановым контуром (киль, стабилизатор): экструзия с фаской */
  function slab(points, thickness, bevel) {
    const sh = new T.Shape();
    points.forEach((p, i) => i ? sh.lineTo(p[0], p[1]) : sh.moveTo(p[0], p[1]));
    sh.closePath();
    const b = bevel !== undefined ? bevel : thickness * 0.35;
    const g = new T.ExtrudeGeometry(sh, {
      depth: Math.max(0.001, thickness - 2 * b), bevelEnabled: true,
      bevelThickness: b, bevelSize: b, bevelSegments: 3, curveSegments: 12
    });
    g.translate(0, 0, -(thickness - 2 * b) / 2);
    return g;
  }

  /* Лопасть: профиль крыла, вытянутый по длине (вдоль +X локально) */
  function bladeGeometry(len, chord, thick, taper) {
    taper = taper === undefined ? 1 : taper;
    const st = [];
    const n = 8;
    for (let i = 0; i <= n; i++) {
      const t = i / n;
      const c = chord * (1 - (1 - taper) * t);
      st.push({ x: t * len, y: 0, z: 0, w: c / 2, h: thick / 2 * (1 - 0.5 * t), hb: thick / 2 * (1 - 0.5 * t) * 0.6, n: 2.6 });
    }
    // закруглить законцовку
    st.push({ x: len + chord * 0.15, y: 0, z: 0, w: c(0.35), h: thick * 0.12, hb: thick * 0.08, n: 2 });
    function c(k) { return chord * taper * k; }
    const g = loft(st, { segs: 16 });
    return g;
  }

  function cyl(r1, r2, h, seg, open) {
    return new T.CylinderGeometry(r1, r2, h, seg || 20, 1, !!open);
  }

  /* ---------- Текстуры-ливреи через canvas ----------
     Развёртка: u — вдоль оси X (0 = xmin, 1 = xmax), v — угол вокруг оси:
     v=0 правый борт, 0.25 верх, 0.5 левый борт, 0.75 низ (низ = 0.75)
  --------------------------------------------------------------- */
  function makeCanvas(w, h) {
    const c = document.createElement('canvas'); c.width = w; c.height = h;
    return c;
  }
  function canvasTexture(c, aniso) {
    const t = new T.CanvasTexture(c);
    t.encoding = T.sRGBEncoding;
    t.anisotropy = aniso || 8;
    t.wrapS = T.RepeatWrapping; t.wrapT = T.RepeatWrapping;
    return t;
  }
  /* Помощник рисования в координатах (u,v)  */
  function painter(ctx, W, H) {
    const P = {
      ctx, W, H,
      X: u => u * W,
      Y: v => (1 - v) * H,
      rect(u0, v0, u1, v1, color) { ctx.fillStyle = color; ctx.fillRect(P.X(u0), P.Y(v1), (u1 - u0) * W, (v1 - v0) * H); },
      rrect(u0, v0, u1, v1, r, color) {
        const x = P.X(u0), y = P.Y(v1), w = (u1 - u0) * W, h = (v1 - v0) * H;
        ctx.fillStyle = color; ctx.beginPath();
        ctx.moveTo(x + r, y); ctx.lineTo(x + w - r, y); ctx.quadraticCurveTo(x + w, y, x + w, y + r);
        ctx.lineTo(x + w, y + h - r); ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
        ctx.lineTo(x + r, y + h); ctx.quadraticCurveTo(x, y + h, x, y + h - r);
        ctx.lineTo(x, y + r); ctx.quadraticCurveTo(x, y, x + r, y); ctx.closePath(); ctx.fill();
      },
      ellipse(u, v, ru, rv, color) { ctx.fillStyle = color; ctx.beginPath(); ctx.ellipse(P.X(u), P.Y(v), ru * W, rv * H, 0, 0, Math.PI * 2); ctx.fill(); },
      poly(pts, color) { ctx.fillStyle = color; ctx.beginPath(); pts.forEach((p, i) => i ? ctx.lineTo(P.X(p[0]), P.Y(p[1])) : ctx.moveTo(P.X(p[0]), P.Y(p[1]))); ctx.closePath(); ctx.fill(); },
      line(pts, color, width) { ctx.strokeStyle = color; ctx.lineWidth = width; ctx.lineCap = 'round'; ctx.beginPath(); pts.forEach((p, i) => i ? ctx.lineTo(P.X(p[0]), P.Y(p[1])) : ctx.moveTo(P.X(p[0]), P.Y(p[1]))); ctx.stroke(); },
      text(str, u, v, size, color, opts) {
        opts = opts || {};
        ctx.save(); ctx.translate(P.X(u), P.Y(v));
        if (opts.flip) ctx.scale(-1, -1); // левый борт: u и v развёрнуты → поворот на 180°
        if (opts.rot) ctx.rotate(opts.rot);
        ctx.fillStyle = color; ctx.font = (opts.weight || '700') + ' ' + size + 'px ' + (opts.font || 'Arial, Helvetica, sans-serif');
        ctx.textAlign = opts.align || 'center'; ctx.textBaseline = 'middle';
        if (opts.stretch) ctx.scale(opts.stretch, 1);
        ctx.fillText(str, 0, 0); ctx.restore();
      },
      /* окно с бликом */
      glass(u0, v0, u1, v1, r) {
        const x = P.X(u0), y = P.Y(v1), w = (u1 - u0) * W, h = (v1 - v0) * H;
        r = r || Math.min(w, h) * 0.2;
        const g = ctx.createLinearGradient(x, y, x + w * 0.4, y + h);
        g.addColorStop(0, '#5e7f9c'); g.addColorStop(0.35, '#1d2c3a'); g.addColorStop(1, '#0d141c');
        P.rrect(u0, v0, u1, v1, r, '#0a0f14');
        ctx.save(); ctx.beginPath();
        const rr = r; ctx.moveTo(x + rr, y); ctx.lineTo(x + w - rr, y); ctx.quadraticCurveTo(x + w, y, x + w, y + rr);
        ctx.lineTo(x + w, y + h - rr); ctx.quadraticCurveTo(x + w, y + h, x + w - rr, y + h);
        ctx.lineTo(x + rr, y + h); ctx.quadraticCurveTo(x, y + h, x, y + h - rr);
        ctx.lineTo(x, y + rr); ctx.quadraticCurveTo(x, y, x + rr, y); ctx.closePath(); ctx.clip();
        ctx.fillStyle = g; ctx.fillRect(x, y, w, h);
        ctx.restore();
        ctx.strokeStyle = 'rgba(20,24,28,0.9)'; ctx.lineWidth = Math.max(2, W * 0.0018);
        ctx.beginPath(); ctx.moveTo(x + rr, y); ctx.lineTo(x + w - rr, y); ctx.quadraticCurveTo(x + w, y, x + w, y + rr);
        ctx.lineTo(x + w, y + h - rr); ctx.quadraticCurveTo(x + w, y + h, x + w - rr, y + h);
        ctx.lineTo(x + rr, y + h); ctx.quadraticCurveTo(x, y + h, x, y + h - rr);
        ctx.lineTo(x, y + rr); ctx.quadraticCurveTo(x, y, x + rr, y); ctx.closePath(); ctx.stroke();
      },
      porthole(u, v, ru, rv) {
        const x = P.X(u), y = P.Y(v);
        const g = ctx.createRadialGradient(x - ru * W * 0.4, y - rv * H * 0.4, 0, x, y, ru * W);
        g.addColorStop(0, '#6d8ea8'); g.addColorStop(0.4, '#1c2a37'); g.addColorStop(1, '#0b1117');
        ctx.fillStyle = '#0a0f14'; ctx.beginPath(); ctx.ellipse(x, y, ru * W * 1.08, rv * H * 1.08, 0, 0, Math.PI * 2); ctx.fill();
        ctx.fillStyle = g; ctx.beginPath(); ctx.ellipse(x, y, ru * W, rv * H, 0, 0, Math.PI * 2); ctx.fill();
        ctx.strokeStyle = 'rgba(200,205,210,0.5)'; ctx.lineWidth = Math.max(1.5, W * 0.0012);
        ctx.beginPath(); ctx.ellipse(x, y, ru * W * 1.12, rv * H * 1.12, 0, 0, Math.PI * 2); ctx.stroke();
      },
      seam(pts, width) { P.line(pts, 'rgba(0,0,0,0.28)', width || Math.max(1.5, W * 0.001)); },
      flagRU(u, v, w, h, mirror) {
        const cols = ['#ffffff', '#1e4fb5', '#d52b1e'];
        for (let i = 0; i < 3; i++) P.rect(u, v - h * (i + 1) / 3, u + w, v - h * i / 3, cols[i]);
      },
      flagAltai(u, v, w, h) { // флаг Республики Алтай: голубой, белая и голубая полосы внизу
        P.rect(u, v - h, u + w, v, '#4aa3df');
        P.rect(u, v - h * 0.82, u + w, v - h * 0.7, '#ffffff');
        P.rect(u, v - h * 0.7, u + w, v - h * 0.62, '#4aa3df');
        P.rect(u, v - h * 0.62, u + w, v - h * 0.5, '#ffffff');
      }
    };
    return P;
  }

  /* ---------- Материалы ---------- */
  function paintMaterial(tex, extra) {
    return new T.MeshPhysicalMaterial(Object.assign({
      map: tex, color: 0xffffff, roughness: 0.38, metalness: 0.0,
      clearcoat: 1.0, clearcoatRoughness: 0.12, envMapIntensity: 1.0
    }, extra || {}));
  }
  const MAT = {
    metal: () => new T.MeshStandardMaterial({ color: 0x9aa0a8, metalness: 0.85, roughness: 0.35 }),
    darkMetal: () => new T.MeshStandardMaterial({ color: 0x3a3d42, metalness: 0.7, roughness: 0.45 }),
    rubber: () => new T.MeshStandardMaterial({ color: 0x17181a, metalness: 0.0, roughness: 0.92 }),
    blade: () => new T.MeshStandardMaterial({ color: 0x1f2226, metalness: 0.2, roughness: 0.55 }),
    bladeOlive: () => new T.MeshStandardMaterial({ color: 0x2e3328, metalness: 0.15, roughness: 0.6 }),
    solid: (c, r, m) => new T.MeshPhysicalMaterial({ color: c, roughness: r === undefined ? 0.4 : r, metalness: m || 0, clearcoat: 0.8, clearcoatRoughness: 0.15 }),
    exhaust: () => new T.MeshStandardMaterial({ color: 0x8c6d3f, metalness: 0.9, roughness: 0.35 }),
    glassDark: () => new T.MeshPhysicalMaterial({ color: 0x0d1720, roughness: 0.05, metalness: 0.1, clearcoat: 1, clearcoatRoughness: 0.03 }),
    light: (c) => new T.MeshStandardMaterial({ color: c, emissive: c, emissiveIntensity: 0.9, roughness: 0.3 }),
    disc: (c) => new T.MeshBasicMaterial({ color: c || 0x222222, transparent: true, opacity: 0.16, side: T.DoubleSide, depthWrite: false })
  };

  function mesh(g, m, shadow) {
    const o = new T.Mesh(g, m);
    o.castShadow = shadow !== false; o.receiveShadow = false;
    return o;
  }

  /* Труба по кривой (полозья, поручни) */
  function tube(points, r, closed, seg) {
    const curve = new T.CatmullRomCurve3(points.map(p => new T.Vector3(p[0], p[1], p[2])), !!closed, 'catmullrom', 0.3);
    return new T.TubeGeometry(curve, seg || 40, r, 10, !!closed);
  }
  function straight(a, b, r, mat, r2) {
    const A = new T.Vector3(a[0], a[1], a[2]), B = new T.Vector3(b[0], b[1], b[2]);
    const len = A.distanceTo(B);
    const g = new T.CylinderGeometry(r2 !== undefined ? r2 : r, r, len, 12);
    const m = mesh(g, mat);
    m.position.copy(A).add(B).multiplyScalar(0.5);
    m.quaternion.setFromUnitVectors(new T.Vector3(0, 1, 0), B.clone().sub(A).normalize());
    return m;
  }

  /* ============================================================
     ЛИВРЕИ
     ============================================================ */
  const LIVERY = {
    as350_navy: {
      base: '#f4f6f8', accent: '#13306b', accent2: '#1b4a9c', reg: 'RA-04062',
      strutColor: 0x13306b, skid: 0x13306b
    },
    as350_red: {
      base: '#c8161d', accent: '#f3efe6', accent2: '#e8b400', reg: 'RA-07544',
      strutColor: 0x2a2a2a, skid: 0x2a2a2a
    },
    mi8amt_blue: { top: '#f5f7f9', mid: '#3b8fd9', low: '#123d9a', reg: 'RA-24187', tank: '#123d9a', gear: 0x2a3a6b, type: 'МИ-8АМТ', windows: 'round' },
    mi171_maroon: { top: '#4a1518', mid: '#4a1518', low: '#3c1013', reg: 'RA-25565', tank: '#9a7a45', stripe: '#c9a45a', gear: 0x2b2b2b, type: 'МИ-171', windows: 'square' }
  };

  /* ============================================================
     EUROCOPTER AS350 B3 (H125) «ÉCUREUIL»
     Длина фюзеляжа 10,93 м, высота 3,34 м, диаметр НВ 10,69 м, РВ 1,86 м
     ============================================================ */
  function buildAS350(liv) {
    liv = liv || LIVERY.as350_navy;
    const G = new T.Group();
    G.name = 'AS350';
    const rotors = [];

    /* --- фюзеляж: сечения от носа (x=+3.45) до перехода в хвостовую балку (x=-2.3) --- */
    const F = [
      { x: 3.45, y: 1.05, w: 0.10, h: 0.10, hb: 0.10, n: 2 },
      { x: 3.30, y: 1.02, w: 0.40, h: 0.26, hb: 0.30, n: 2.2 },
      { x: 3.05, y: 1.05, w: 0.64, h: 0.42, hb: 0.46, n: 2.3 },
      { x: 2.70, y: 1.15, w: 0.82, h: 0.62, hb: 0.58, n: 2.4 },
      { x: 2.30, y: 1.28, w: 0.92, h: 0.80, hb: 0.68, n: 2.5 },
      { x: 1.80, y: 1.36, w: 0.96, h: 0.86, hb: 0.74, n: 2.7 },
      { x: 1.20, y: 1.38, w: 0.97, h: 0.86, hb: 0.76, n: 2.8 },
      { x: 0.50, y: 1.38, w: 0.97, h: 0.86, hb: 0.76, n: 2.8 },
      { x: -0.20, y: 1.40, w: 0.93, h: 0.82, hb: 0.72, n: 2.7 },
      { x: -0.80, y: 1.46, w: 0.80, h: 0.66, hb: 0.60, n: 2.5 },
      { x: -1.40, y: 1.54, w: 0.58, h: 0.46, hb: 0.44, n: 2.3 },
      { x: -1.90, y: 1.60, w: 0.40, h: 0.33, hb: 0.33, n: 2.1 },
      { x: -2.30, y: 1.63, w: 0.31, h: 0.29, hb: 0.29, n: 2 }
    ];
    const fusTex = canvasTexture(paintAS350Fuselage(liv));
    const fus = mesh(loft(F, { segs: 56 }), paintMaterial(fusTex));
    G.add(fus);

    /* --- хвостовая балка x∈[-6.75,-2.3] --- */
    const B = [];
    for (let i = 0; i <= 6; i++) {
      const t = i / 6;
      B.push({ x: -2.3 - t * 4.45, y: 1.63 + t * 0.20, w: 0.31 - t * 0.135, h: 0.29 - t * 0.125, n: 2 });
    }
    const boomTex = canvasTexture(paintAS350Boom(liv));
    const boom = mesh(loft(B, { segs: 32 }), paintMaterial(boomTex));
    G.add(boom);

    /* --- капот двигателя (Arriel 2D) над кабиной --- */
    const E = [
      { x: 1.05, y: 2.22, w: 0.30, h: 0.10, hb: 0.06, n: 2.2 },
      { x: 0.80, y: 2.34, w: 0.42, h: 0.30, hb: 0.14, n: 2.4 },
      { x: 0.40, y: 2.40, w: 0.46, h: 0.36, hb: 0.20, n: 2.5 },
      { x: -0.20, y: 2.42, w: 0.47, h: 0.36, hb: 0.22, n: 2.5 },
      { x: -0.80, y: 2.40, w: 0.44, h: 0.32, hb: 0.20, n: 2.4 },
      { x: -1.30, y: 2.34, w: 0.36, h: 0.24, hb: 0.16, n: 2.3 },
      { x: -1.70, y: 2.26, w: 0.24, h: 0.14, hb: 0.10, n: 2.2 },
      { x: -1.85, y: 2.22, w: 0.05, h: 0.05, hb: 0.04, n: 2 }
    ];
    const cowlTex = canvasTexture(paintAS350Cowl(liv));
    G.add(mesh(loft(E, { segs: 32 }), paintMaterial(cowlTex)));
    /* воздухозаборник (сетка) перед редуктором */
    const intake = mesh(new T.BoxGeometry(0.30, 0.16, 0.5), MAT.darkMetal());
    intake.position.set(0.98, 2.30, 0); G.add(intake);
    /* выхлопная труба */
    const ex = mesh(cyl(0.16, 0.19, 0.55, 20, true), MAT.exhaust());
    ex.material.side = T.DoubleSide;
    ex.rotation.z = Math.PI / 2 + 0.25; ex.position.set(-1.95, 2.28, 0.0);
    G.add(ex);
    const exIn = mesh(cyl(0.13, 0.13, 0.5, 20, true), new T.MeshStandardMaterial({ color: 0x111111, side: T.BackSide, roughness: 1 }));
    exIn.rotation.z = Math.PI / 2 + 0.25; exIn.position.copy(ex.position); G.add(exIn);

    /* --- вал и втулка Starflex, 3 лопасти --- */
    const mast = mesh(cyl(0.09, 0.11, 0.55), MAT.darkMetal()); mast.position.set(0.05, 2.95, 0); G.add(mast);
    const rotor = new T.Group(); rotor.position.set(0.05, 3.22, 0);
    const hubPlate = mesh(cyl(0.34, 0.34, 0.07, 24), MAT.solid(0x2d3136, 0.5, 0.4));
    rotor.add(hubPlate);
    const hubTop = mesh(cyl(0.12, 0.16, 0.22, 20), MAT.darkMetal()); hubTop.position.y = 0.12; rotor.add(hubTop);
    for (let i = 0; i < 3; i++) {
      const arm = new T.Group(); arm.rotation.y = i * Math.PI * 2 / 3;
      const star = mesh(new T.BoxGeometry(0.62, 0.05, 0.16), MAT.solid(0x2d3136, 0.5, 0.4)); star.position.x = 0.36; arm.add(star);
      const grip = mesh(cyl(0.07, 0.06, 0.48, 14), MAT.darkMetal()); grip.rotation.z = Math.PI / 2; grip.position.set(0.72, 0.0, 0); arm.add(grip);
      const pitch = mesh(new T.BoxGeometry(0.22, 0.05, 0.05), MAT.metal()); pitch.position.set(0.55, -0.08, 0.15); arm.add(pitch);
      const bl = mesh(bladeGeometry(4.55, 0.35, 0.06, 0.95), MAT.blade());
      bl.position.set(0.85, 0.0, 0); bl.rotation.z = -0.02; bl.rotation.x = 0.06;
      arm.add(bl);
      rotor.add(arm);
    }
    const disc = mesh(new T.CircleGeometry(5.35, 64), MAT.disc(0x3a3f45), false);
    disc.rotation.x = -Math.PI / 2; disc.position.y = 0.01; disc.visible = false; rotor.add(disc);
    G.add(rotor);
    rotors.push({ obj: rotor, axis: 'y', dir: 1, disc, rpm: 390 });

    /* --- стабилизатор с концевыми шайбами (x≈-4.9) --- */
    const stabG = slab([[0.42, -1.25], [0.42, 1.25], [-0.30, 1.25], [-0.30, -1.25]], 0.09, 0.03);
    const stab = mesh(stabG, MAT.solid(0xf4f6f8, 0.35)); // rotated: shape в XY → нам нужен XZ
    stab.rotation.x = Math.PI / 2; stab.position.set(-4.95, 1.98, 0); G.add(stab);
    [-1, 1].forEach(s => {
      const plate = slab([[0.45, -0.05], [0.25, 0.42], [-0.35, 0.42], [-0.45, -0.30], [0.25, -0.30]], 0.06, 0.02);
      const pm = mesh(plate, MAT.solid(0xf4f6f8, 0.35));
      pm.position.set(-4.95, 2.0, s * 1.25); G.add(pm);
    });

    /* --- киль: верхний стреловидный + нижний (вентральный) --- */
    const finU = slab([[-6.05, 1.75], [-6.55, 3.05], [-7.35, 3.10], [-7.35, 2.55], [-7.05, 1.85]], 0.16, 0.05);
    const finTex = canvasTexture(paintAS350Fin(liv));
    const fin = mesh(finU, paintMaterial(finTex, { color: 0xffffff }));
    fin.position.set(0, 0, 0); G.add(fin);
    const finL = slab([[-6.0, 1.75], [-6.85, 1.75], [-7.20, 0.95], [-6.95, 0.85], [-6.35, 1.20]], 0.14, 0.05);
    G.add(mesh(finL, MAT.solid(new T.Color(liv.accent).getHex(), 0.35)));
    // защитная дуга под килем
    G.add(straight([-7.15, 0.85, 0], [-6.95, 0.72, 0], 0.03, MAT.darkMetal()));

    /* --- рулевой винт (левый борт, 2 лопасти) --- */
    const tgb = mesh(cyl(0.11, 0.09, 0.28, 16), MAT.darkMetal()); tgb.rotation.x = Math.PI / 2; tgb.position.set(-6.85, 2.42, -0.12); G.add(tgb);
    const tr = new T.Group(); tr.position.set(-6.85, 2.42, -0.30);
    const trHub = mesh(cyl(0.06, 0.06, 0.16, 12), MAT.metal()); trHub.rotation.x = Math.PI / 2; tr.add(trHub);
    for (let i = 0; i < 2; i++) {
      const a = new T.Group(); a.rotation.z = i * Math.PI;
      const bl = mesh(bladeGeometry(0.86, 0.19, 0.035, 1), MAT.blade());
      bl.rotation.z = Math.PI / 2; bl.rotation.y = Math.PI / 2; bl.position.set(0, 0.08, 0);
      // выровнять по плоскости XY, ось вращения Z
      bl.rotation.set(0, Math.PI / 2, Math.PI / 2);
      bl.position.set(0, 0.07, 0);
      a.add(bl); tr.add(a);
    }
    const trDisc = mesh(new T.CircleGeometry(0.95, 40), MAT.disc(0x3a3f45), false); trDisc.visible = false; tr.add(trDisc);
    G.add(tr);
    rotors.push({ obj: tr, axis: 'z', dir: -1, disc: trDisc, rpm: 2085 });
    // защитная скоба РВ
    G.add(mesh(tube([[-7.3, 2.42, -0.34], [-7.45, 2.2, -0.34], [-7.4, 1.9, -0.34]], 0.02), MAT.darkMetal()));

    /* --- полозковое шасси --- */
    const skidMat = MAT.solid(liv.skid, 0.4, 0.3);
    [-1, 1].forEach(s => {
      const z = s * 1.12;
      const skid = mesh(tube([[-1.55, 0.06, z], [-0.4, 0.05, z], [1.0, 0.05, z], [2.05, 0.06, z], [2.55, 0.18, z], [2.85, 0.42, z]], 0.045, false, 48), skidMat);
      G.add(skid);
      // ступени
      const step = mesh(new T.BoxGeometry(1.5, 0.03, 0.22), MAT.darkMetal()); step.position.set(0.9, 0.36, z); G.add(step);
      // колёса наземного перемещения (сложены)
      const wheel = mesh(new T.TorusGeometry(0.11, 0.045, 10, 24), MAT.rubber()); wheel.position.set(-0.55, 0.19, z + s * 0.19); G.add(wheel);
    });
    // поперечные дуги
    [1.65, -0.85].forEach(x => {
      const arch = mesh(tube([[x, 0.06, -1.12], [x, 0.50, -0.95], [x, 0.66, -0.35], [x, 0.66, 0.35], [x, 0.50, 0.95], [x, 0.06, 1.12]], 0.05, false, 40), skidMat);
      G.add(arch);
    });

    /* --- носовые детали: ПВД, фары, антенны --- */
    const pitot = straight([3.35, 1.25, 0.28], [3.85, 1.25, 0.28], 0.015, MAT.metal()); G.add(pitot);
    const lamp = mesh(new T.SphereGeometry(0.11, 16, 10, 0, Math.PI * 2, 0, Math.PI / 2), MAT.light(0xfff2c0));
    lamp.rotation.x = Math.PI / 2; lamp.position.set(2.55, 0.62, 0); G.add(lamp);
    const wsps = mesh(new T.BoxGeometry(0.02, 0.32, 0.10), MAT.darkMetal()); wsps.position.set(3.35, 1.42, 0); wsps.rotation.z = 0.2; G.add(wsps);
    const ant1 = mesh(new T.BoxGeometry(0.28, 0.24, 0.02), MAT.darkMetal()); ant1.position.set(-1.5, 0.95, 0); G.add(ant1);
    const ant2 = mesh(new T.BoxGeometry(0.02, 0.22, 0.20), MAT.darkMetal()); ant2.position.set(-3.6, 1.55, 0); G.add(ant2);
    const beacon = mesh(new T.SphereGeometry(0.05, 12, 8), MAT.light(0xff3b30)); beacon.position.set(-3.0, 2.05, 0); G.add(beacon);
    const gps = mesh(new T.BoxGeometry(0.14, 0.03, 0.14), MAT.solid(0xf4f6f8)); gps.position.set(1.7, 2.24, 0.25); G.add(gps);
    // зеркала/поручни на капоте
    [-1, 1].forEach(s => { const rail = mesh(tube([[0.7, 2.28, s * 0.5], [0.0, 2.36, s * 0.55], [-0.7, 2.28, s * 0.5]], 0.012), MAT.metal()); G.add(rail); });

    G.userData.rotors = rotors;
    G.userData.bounds = { length: 12.9, height: 3.4, width: 10.7 };
    G.userData.groundY = 0.0;
    return G;
  }

  /* ---- ливрея AS350: фюзеляж ---- */
  function paintAS350Fuselage(liv) {
    const W = 2048, H = 1024, c = makeCanvas(W, H), ctx = c.getContext('2d');
    const P = painter(ctx, W, H);
    // u: 0 = хвост (x=-2.3), 1 = нос (x=3.45)
    const ux = x => (x + 2.3) / 5.75;
    P.rect(0, 0, 1, 1, liv.base);
    // нижняя тёмная часть: низ (v≈0.75) с плавной границей по бортам
    const vRight = 0.0, vLeft = 0.5, vBot = 0.75;
    // правый борт: тёмная область от v=0.75-0.32 (0.43 — ниже) ... рисуем полосу по низу вокруг оси
    const drawBelly = () => {
      // между v=0.55..0.95 (левый низ->правый низ через 0.75) — с волной от u
      ctx.fillStyle = liv.accent;
      ctx.beginPath();
      const pts = [];
      for (let i = 0; i <= 40; i++) { const u = i / 40; const x = -2.3 + u * 5.75; const rise = x > 1.2 ? 0.0 : (1.2 - x) * 0.045; pts.push([u, 0.54 - rise]); }
      ctx.moveTo(P.X(pts[0][0]), P.Y(pts[0][1]));
      pts.forEach(p => ctx.lineTo(P.X(p[0]), P.Y(p[1])));
      for (let i = 40; i >= 0; i--) { const u = i / 40; const x = -2.3 + u * 5.75; const rise = x > 1.2 ? 0.0 : (1.2 - x) * 0.045; ctx.lineTo(P.X(u), P.Y(0.96 + rise)); }
      ctx.closePath(); ctx.fill();
      // тонкая светлая полоса-разделитель
      P.line(pts, liv.accent2, 10);
      P.line(pts.map(p => [p[0], 1.5 - p[1]]), liv.accent2, 10);
    };
    drawBelly();
    // правая часть v>0.96 переносится на v∈[0,0.04] (wrap): дорисовать
    ctx.fillStyle = liv.accent; ctx.fillRect(0, P.Y(0.04), W, H * 0.04);
    // ---- остекление кабины ----
    // лобовое (оборачивает нос сверху): u∈[ux(2.0), ux(3.35)], v∈[0.10, 0.40]
    const u0 = ux(2.05), u1 = ux(3.38);
    // единое стекло с центральной стойкой
    P.glass(u0, 0.09, u1, 0.41, 40);
    P.line([[u0 + 0.01, 0.25], [u1 - 0.005, 0.25]], '#0b0e11', 14); // центральная стойка
    P.line([[ux(2.7), 0.10], [ux(2.75), 0.40]], '#0b0e11', 10);      // стойка дверей
    // боковые окна кабины экипажа (двери): правый борт v∈[0.0,0.10] и v∈[0.40,0.50] лев.
    P.glass(ux(2.0), 0.02, ux(2.72), 0.115, 30);   // правый передний
    P.glass(ux(2.0), 0.385, ux(2.72), 0.48, 30);   // левый передний
    // окна пассажирского салона (сдвижные двери): u∈[ux(0.55), ux(1.95)]
    P.glass(ux(0.6), 0.015, ux(1.92), 0.13, 34);   // правый борт большое окно
    P.glass(ux(0.6), 0.37, ux(1.92), 0.485, 34);   // левый борт
    // задние малые окна багажника
    P.glass(ux(-0.4), 0.05, ux(0.45), 0.12, 20); P.glass(ux(-0.4), 0.38, ux(0.45), 0.45, 20);
    // швы дверей
    P.seam([[ux(1.95), 0.0], [ux(1.95), 0.12], [ux(0.55), 0.12], [ux(0.55), 0.0]]);
    P.seam([[ux(1.95), 0.5], [ux(1.95), 0.38], [ux(0.55), 0.38], [ux(0.55), 0.5]]);
    P.seam([[ux(2.75), 0.0], [ux(2.75), 0.12], [ux(1.98), 0.12]]);
    P.seam([[ux(2.75), 0.5], [ux(2.75), 0.38], [ux(1.98), 0.38]]);
    // люки багажника снизу
    P.seam([[ux(-1.0), 0.62], [ux(-0.1), 0.62], [ux(-0.1), 0.72], [ux(-1.0), 0.72], [ux(-1.0), 0.62]]);
    // логотип «АлтайАвиа» на бортах
    const logo = (v, flip) => { P.text('АЛТАЙАВИА', ux(0.05), v, 34, liv.accent, { flip, weight: '900', stretch: 1.05 }); };
    logo(0.155, false); logo(0.345, true);
    // флаг РФ на носу и надпись AIRBUS/H125
    P.text('H125', ux(-1.3), 0.19, 26, liv.accent, { weight: '700' });
    P.text('H125', ux(-1.3), 0.31, 26, liv.accent, { weight: '700', flip: true });
    return c;
  }
  function paintAS350Boom(liv) {
    const W = 1024, H = 256, c = makeCanvas(W, H), ctx = c.getContext('2d'); const P = painter(ctx, W, H);
    // u: 0 = хвост (x=-6.75), 1 = у фюзеляжа (x=-2.3)
    P.rect(0, 0, 1, 1, liv.base);
    // нижняя тёмная полоса, поднимающаяся к хвосту
    ctx.fillStyle = liv.accent; ctx.beginPath();
    ctx.moveTo(P.X(0), P.Y(0.46)); ctx.lineTo(P.X(1), P.Y(0.56)); ctx.lineTo(P.X(1), P.Y(0.94)); ctx.lineTo(P.X(0), P.Y(1.04)); ctx.closePath(); ctx.fill();
    P.line([[0, 0.46], [1, 0.56]], liv.accent2, 5); P.line([[0, 1.04], [1, 0.94]], liv.accent2, 5);
    // регистрационный номер по бортам
    P.text(liv.reg, 0.5, 0.15, 58, liv.accent, { weight: '900', stretch: 1.1 });
    P.text(liv.reg, 0.5, 0.34, 58, liv.accent, { weight: '900', stretch: 1.1, flip: true });
    // шов балки
    P.seam([[0.98, 0], [0.98, 1]], 3);
    return c;
  }
  function paintAS350Cowl(liv) {
    const W = 512, H = 256, c = makeCanvas(W, H), ctx = c.getContext('2d'); const P = painter(ctx, W, H);
    P.rect(0, 0, 1, 1, liv.base);
    // вентиляционные жалюзи
    for (let i = 0; i < 6; i++) { P.rect(0.32 + i * 0.05, 0.05, 0.34 + i * 0.05, 0.14, 'rgba(0,0,0,0.35)'); P.rect(0.32 + i * 0.05, 0.36, 0.34 + i * 0.05, 0.45, 'rgba(0,0,0,0.35)'); }
    P.seam([[0.62, 0], [0.62, 1]], 3); P.seam([[0.25, 0], [0.25, 1]], 3);
    return c;
  }
  function paintAS350Fin(liv) {
    const W = 512, H = 512, c = makeCanvas(W, H), ctx = c.getContext('2d'); const P = painter(ctx, W, H);
    P.rect(0, 0, 1, 1, liv.accent);
    // экструзия использует world-UV; просто однотонный
    return c;
  }

  /* ============================================================
     Ми-8АМТ / Ми-171
     Длина фюзеляжа 18,47 м, высота 5,65 м, диаметр НВ 21,29 м, РВ 3,91 м
     ============================================================ */
  function buildMi8(liv) {
    liv = liv || LIVERY.mi8amt_blue;
    const G = new T.Group(); G.name = liv.type;
    const rotors = [];
    /* --- фюзеляж: нос x=+8.35 … корень балки x=-5.2 (вал НВ в x=0) --- */
    const F = [
      { x: 8.40, y: 2.00, w: 0.42, h: 0.34, hb: 0.42, n: 2.4 },
      { x: 8.25, y: 2.02, w: 0.78, h: 0.66, hb: 0.68, n: 2.5 },
      { x: 7.90, y: 2.06, w: 1.04, h: 0.92, hb: 0.88, n: 2.7 },
      { x: 7.30, y: 2.12, w: 1.18, h: 1.05, hb: 1.00, n: 2.9 },
      { x: 6.50, y: 2.15, w: 1.24, h: 1.10, hb: 1.05, n: 3.0 },
      { x: 5.60, y: 2.15, w: 1.26, h: 1.12, hb: 1.08, n: 3.2 },
      { x: 3.00, y: 2.15, w: 1.26, h: 1.12, hb: 1.08, n: 3.2 },
      { x: -1.50, y: 2.15, w: 1.26, h: 1.12, hb: 1.08, n: 3.2 },
      { x: -2.60, y: 2.18, w: 1.22, h: 1.08, hb: 1.02, n: 3.0 },
      { x: -3.40, y: 2.28, w: 1.05, h: 0.96, hb: 0.86, n: 2.7 },
      { x: -4.20, y: 2.45, w: 0.80, h: 0.76, hb: 0.64, n: 2.4 },
      { x: -4.80, y: 2.60, w: 0.62, h: 0.60, hb: 0.52, n: 2.2 },
      { x: -5.20, y: 2.68, w: 0.55, h: 0.54, hb: 0.48, n: 2.1 }
    ];
    const fusTex = canvasTexture(paintMi8Fuselage(liv));
    G.add(mesh(loft(F, { segs: 64 }), paintMaterial(fusTex)));

    /* --- хвостовая балка x∈[-11.0,-5.2] --- */
    const B = [];
    for (let i = 0; i <= 8; i++) { const t = i / 8; B.push({ x: -5.2 - t * 5.8, y: 2.68 + t * 0.34, w: 0.55 - t * 0.27, h: 0.54 - t * 0.26, n: 2 }); }
    const boomTex = canvasTexture(paintMi8Boom(liv));
    G.add(mesh(loft(B, { segs: 36 }), paintMaterial(boomTex)));

    /* --- концевая балка (киль) — изогнутая вверх, с профилем --- */
    // строим как лофт вдоль X с подъёмом центра
    const K = [];
    for (let i = 0; i <= 8; i++) {
      const t = i / 8;
      const x = -11.0 - t * 1.75;
      const y = 3.02 + Math.pow(t, 1.15) * 1.25;
      K.push({ x, y, w: 0.28 - t * 0.12, h: 0.30 + t * 0.55, hb: 0.28 - t * 0.02, n: 2.3 });
    }
    const finTex = canvasTexture(paintMi8Fin(liv));
    G.add(mesh(loft(K, { segs: 32 }), paintMaterial(finTex)));
    // обтекатель хвостового редуктора
    const tgb = mesh(new T.SphereGeometry(0.30, 20, 14), paintMaterial(finTex)); tgb.scale.set(1.5, 1, 1); tgb.position.set(-12.75, 4.58, 0); G.add(tgb);

    /* --- стабилизатор --- */
    [-1, 1].forEach(s => {
      const g = slab([[0.45, 0], [0.32, 1.35], [-0.32, 1.35], [-0.50, 0]], 0.10, 0.03);
      const m = mesh(g, MAT.solid(new T.Color(liv.top).getHex(), 0.35));
      m.rotation.x = s > 0 ? -Math.PI / 2 : Math.PI / 2; m.position.set(-10.3, 3.0, s * 0.3); G.add(m);
    });

    /* --- двигательный отсек: 2 ТВ3-117 с ПЗУ + редуктор --- */
    const deckTex = canvasTexture(paintMi8Deck(liv));
    const deckMat = paintMaterial(deckTex);
    // общий обтекатель (капоты) над кабиной от x=6.2 до x=-3.0
    const D = [
      { x: 6.25, y: 3.32, w: 0.95, h: 0.10, hb: 0.06, n: 3 },
      { x: 5.80, y: 3.40, w: 1.10, h: 0.42, hb: 0.16, n: 3.2 },
      { x: 5.00, y: 3.44, w: 1.14, h: 0.50, hb: 0.20, n: 3.4 },
      { x: 3.20, y: 3.46, w: 1.14, h: 0.54, hb: 0.20, n: 3.4 },
      { x: 1.60, y: 3.50, w: 1.12, h: 0.62, hb: 0.22, n: 3.2 },
      { x: 0.60, y: 3.55, w: 1.02, h: 0.72, hb: 0.24, n: 3.0 },
      { x: -0.40, y: 3.55, w: 0.98, h: 0.72, hb: 0.24, n: 3.0 },
      { x: -1.40, y: 3.48, w: 0.92, h: 0.50, hb: 0.20, n: 2.8 },
      { x: -2.40, y: 3.40, w: 0.80, h: 0.30, hb: 0.14, n: 2.6 },
      { x: -3.10, y: 3.32, w: 0.55, h: 0.10, hb: 0.06, n: 2.4 }
    ];
    G.add(mesh(loft(D, { segs: 48 }), deckMat));
    // воздухозаборники двигателей с ПЗУ (грибовидные обтекатели)
    [-1, 1].forEach(s => {
      const z = s * 0.56;
      const ring = mesh(cyl(0.42, 0.44, 0.35, 28, true), deckMat); ring.material.side = T.DoubleSide; ring.rotation.z = Math.PI / 2; ring.position.set(6.25, 3.62, z); G.add(ring);
      const inner = mesh(cyl(0.40, 0.40, 0.35, 28, true), new T.MeshStandardMaterial({ color: 0x0f1113, side: T.BackSide, roughness: 1 })); inner.rotation.z = Math.PI / 2; inner.position.copy(ring.position); G.add(inner);
      const pzu = mesh(new T.SphereGeometry(0.33, 24, 16), MAT.solid(new T.Color(liv.top).getHex(), 0.35)); pzu.scale.set(1.15, 1, 1); pzu.position.set(6.75, 3.62, z); G.add(pzu);
      const pzuStem = mesh(cyl(0.12, 0.12, 0.4, 14), MAT.darkMetal()); pzuStem.rotation.z = Math.PI / 2; pzuStem.position.set(6.45, 3.62, z); G.add(pzuStem);
      // выхлопные патрубки — вбок-назад
      const exh = mesh(cyl(0.24, 0.27, 0.55, 22, true), MAT.exhaust()); exh.material.side = T.DoubleSide;
      exh.rotation.z = Math.PI / 2; exh.rotation.y = s * 0.55; exh.position.set(2.05, 3.52, s * 1.32); G.add(exh);
      const exhIn = mesh(cyl(0.21, 0.21, 0.5, 22, true), new T.MeshStandardMaterial({ color: 0x0a0a0a, side: T.BackSide, roughness: 1 })); exhIn.rotation.copy(exh.rotation); exhIn.position.copy(exh.position); G.add(exhIn);
    });
    // вентилятор маслорадиатора (за валом) + ВСУ
    const fan = mesh(new T.BoxGeometry(0.9, 0.55, 1.5), deckMat); fan.position.set(-1.1, 4.2, 0); G.add(fan);
    const fanGrill = mesh(new T.BoxGeometry(0.02, 0.4, 1.2), MAT.darkMetal()); fanGrill.position.set(-0.64, 4.2, 0); G.add(fanGrill);
    const apu = mesh(cyl(0.18, 0.18, 0.7, 16), MAT.exhaust()); apu.rotation.z = Math.PI / 2; apu.position.set(-2.9, 3.55, 0.3); G.add(apu);

    /* --- несущий винт: 5 лопастей --- */
    const mast = mesh(cyl(0.16, 0.20, 0.7, 20), MAT.darkMetal()); mast.position.set(0.0, 4.55, 0); G.add(mast);
    const rotor = new T.Group(); rotor.position.set(0, 4.92, 0);
    rotor.add(mesh(cyl(0.42, 0.46, 0.30, 24), MAT.darkMetal()));
    const swash = mesh(cyl(0.52, 0.52, 0.06, 28), MAT.metal()); swash.position.y = -0.28; rotor.add(swash);
    const bladeMat = MAT.bladeOlive();
    const tipMat = MAT.solid(0xf2c230, 0.5);
    for (let i = 0; i < 5; i++) {
      const arm = new T.Group(); arm.rotation.y = i * Math.PI * 2 / 5;
      const grip = mesh(new T.BoxGeometry(0.85, 0.16, 0.22), MAT.darkMetal()); grip.position.x = 0.7; arm.add(grip);
      const damper = mesh(cyl(0.05, 0.05, 0.5, 10), MAT.metal()); damper.rotation.z = Math.PI / 2; damper.rotation.y = 0.6; damper.position.set(0.55, 0.05, 0.28); arm.add(damper);
      const bl = mesh(bladeGeometry(9.35, 0.52, 0.09, 1), bladeMat);
      bl.position.set(1.1, 0.0, 0); bl.rotation.z = -0.045; // провис лопасти
      arm.add(bl);
      const tip = mesh(new T.BoxGeometry(0.5, 0.06, 0.5), tipMat); tip.position.set(10.3, -0.45, 0); arm.add(tip);
      const pl = mesh(new T.BoxGeometry(0.3, 0.04, 0.06), MAT.metal()); pl.position.set(0.9, -0.12, 0.2); arm.add(pl);
      rotor.add(arm);
    }
    const disc = mesh(new T.CircleGeometry(10.65, 72), MAT.disc(0x2f3438), false); disc.rotation.x = -Math.PI / 2; disc.position.y = -0.2; disc.visible = false; rotor.add(disc);
    G.add(rotor);
    rotors.push({ obj: rotor, axis: 'y', dir: 1, disc, rpm: 192 });

    /* --- рулевой винт: 3 лопасти, левый борт --- */
    const tr = new T.Group(); tr.position.set(-12.75, 4.58, -0.42);
    const trHub = mesh(cyl(0.14, 0.14, 0.3, 16), MAT.darkMetal()); trHub.rotation.x = Math.PI / 2; tr.add(trHub);
    for (let i = 0; i < 3; i++) {
      const a = new T.Group(); a.rotation.z = i * Math.PI * 2 / 3;
      const bl = mesh(bladeGeometry(1.75, 0.30, 0.05, 0.9), bladeMat);
      bl.rotation.set(0, Math.PI / 2, Math.PI / 2); bl.position.set(0, 0.15, 0); a.add(bl);
      const tip = mesh(new T.BoxGeometry(0.08, 0.3, 0.3), tipMat); tip.position.set(0, 1.85, 0); a.add(tip);
      tr.add(a);
    }
    const trDisc = mesh(new T.CircleGeometry(1.95, 48), MAT.disc(0x2f3438), false); trDisc.visible = false; tr.add(trDisc);
    G.add(tr);
    rotors.push({ obj: tr, axis: 'z', dir: 1, disc: trDisc, rpm: 1124 });

    /* --- подвесные топливные баки --- */
    const tankColor = new T.Color(liv.tank).getHex();
    const tankMat = MAT.solid(tankColor, 0.32, liv.stripe ? 0.55 : 0.05);
    const makeTank = (x0, x1, z) => {
      const L = x0 - x1, st = [];
      for (let i = 0; i <= 10; i++) {
        const t = i / 10; const x = x0 - t * L;
        const r = 0.45 * Math.sqrt(Math.max(0.02, 1 - Math.pow((t - 0.5) * 2, 6)));
        st.push({ x, y: 1.28, z, w: r, h: r, n: 2 });
      }
      const m = mesh(loft(st, { segs: 28 }), tankMat); G.add(m);
      // кронштейны
      [0.25, 0.75].forEach(k => { const x = x0 - k * L; G.add(straight([x, 1.55, z * 0.8], [x, 1.35, z], 0.04, MAT.darkMetal())); });
    };
    makeTank(4.9, -3.4, 1.62);   // правый — длинный
    makeTank(2.9, -3.4, -1.62);  // левый — короче (за сдвижной дверью)

    /* --- шасси --- */
    const gearMat = MAT.solid(liv.gear, 0.45, 0.2);
    const tyre = (r, w) => mesh(new T.CylinderGeometry(r, r, w, 28), MAT.rubber());
    // носовая стойка — спаренные колёса
    const ns = straight([6.3, 1.05, 0], [6.3, 0.42, 0], 0.07, gearMat); G.add(ns);
    const nsBrace = straight([5.5, 1.1, 0], [6.3, 0.5, 0], 0.035, gearMat); G.add(nsBrace);
    [-1, 1].forEach(s => { const w = tyre(0.30, 0.16); w.rotation.x = Math.PI / 2; w.position.set(6.3, 0.30, s * 0.28); G.add(w); const hub = mesh(cyl(0.12, 0.12, 0.18, 14), MAT.metal()); hub.rotation.x = Math.PI / 2; hub.position.copy(w.position); G.add(hub); });
    G.add(straight([6.3, 0.30, -0.4], [6.3, 0.30, 0.4], 0.05, MAT.darkMetal()));
    // основные стойки — пирамида
    [-1, 1].forEach(s => {
      const wz = s * 2.25, wx = -0.9;
      const w = tyre(0.50, 0.22); w.rotation.x = Math.PI / 2; w.position.set(wx, 0.50, wz); G.add(w);
      const hub = mesh(cyl(0.2, 0.2, 0.26, 16), MAT.metal()); hub.rotation.x = Math.PI / 2; hub.position.copy(w.position); G.add(hub);
      G.add(straight([wx + 0.9, 1.45, s * 1.15], [wx, 0.50, wz - s * 0.16], 0.07, gearMat)); // передний подкос
      G.add(straight([wx - 0.9, 1.45, s * 1.15], [wx, 0.50, wz - s * 0.16], 0.07, gearMat)); // задний подкос
      G.add(straight([wx - 0.2, 2.75, s * 1.28], [wx, 0.55, wz - s * 0.12], 0.075, MAT.metal(), 0.09)); // амортизатор
      G.add(straight([wx, 0.5, wz - s * 0.16], [wx, 0.5, wz + s * 0.02], 0.06, MAT.darkMetal()));
    });
    // хвостовая опора
    G.add(straight([-9.4, 2.6, 0], [-9.9, 1.75, 0], 0.045, gearMat));
    G.add(straight([-8.6, 2.5, 0], [-9.9, 1.75, 0], 0.035, gearMat));
    const tailSkid = mesh(new T.SphereGeometry(0.1, 10, 8), MAT.rubber()); tailSkid.position.set(-9.9, 1.72, 0); G.add(tailSkid);

    /* --- детали: ступеньки, поручни, антенны, ПВД, фары --- */
    const stepMat = MAT.metal();
    // сдвижная дверь слева — трап
    for (let i = 0; i < 3; i++) { const st = mesh(new T.BoxGeometry(0.5, 0.03, 0.2), stepMat); st.position.set(3.35, 1.0 - i * 0.28, -1.5 - i * 0.14); G.add(st); }
    G.add(straight([3.1, 1.15, -1.35], [3.1, 0.2, -1.9], 0.02, stepMat)); G.add(straight([3.6, 1.15, -1.35], [3.6, 0.2, -1.9], 0.02, stepMat));
    // ПВД на носу
    [-1, 1].forEach(s => G.add(straight([7.9, 2.55, s * 0.55], [8.6, 2.6, s * 0.6], 0.02, stepMat)));
    // фары (посадочная и рулёжная)
    const l1 = mesh(new T.SphereGeometry(0.14, 16, 10), MAT.light(0xfff2c0)); l1.position.set(6.9, 1.05, 0); G.add(l1);
    // антенны
    const a1 = mesh(new T.BoxGeometry(0.02, 0.35, 0.35), MAT.darkMetal()); a1.position.set(-6.5, 3.15, 0); G.add(a1);
    const a2 = mesh(new T.BoxGeometry(0.02, 0.3, 0.25), MAT.darkMetal()); a2.position.set(4.5, 0.95, 0.4); G.add(a2);
    const a3 = mesh(new T.BoxGeometry(0.02, 0.3, 0.25), MAT.darkMetal()); a3.position.set(-2.5, 0.95, -0.4); G.add(a3);
    const beacon = mesh(new T.SphereGeometry(0.07, 12, 8), MAT.light(0xff3b30)); beacon.position.set(-8.0, 3.35, 0); G.add(beacon);
    const beacon2 = mesh(new T.SphereGeometry(0.07, 12, 8), MAT.light(0xff3b30)); beacon2.position.set(-3.4, 1.1, 0); G.add(beacon2);
    // доплеровская антенна под балкой
    const dop = mesh(new T.BoxGeometry(0.9, 0.16, 0.5), MAT.solid(new T.Color(liv.low).getHex(), 0.4)); dop.position.set(-6.0, 2.2, 0); G.add(dop);
    // лебёдка над дверью
    const winch = mesh(new T.BoxGeometry(0.35, 0.3, 0.3), MAT.darkMetal()); winch.position.set(3.9, 3.05, -1.35); G.add(winch);

    G.userData.rotors = rotors;
    G.userData.bounds = { length: 25.3, height: 5.65, width: 21.3 };
    G.userData.groundY = 0.0;
    return G;
  }

  /* ---- ливрея Ми-8 ---- */
  function paintMi8Fuselage(liv) {
    const W = 2048, H = 1024, c = makeCanvas(W, H), ctx = c.getContext('2d'); const P = painter(ctx, W, H);
    // u: 0 = x=-5.2 (корень балки), 1 = x=8.35 (нос)
    const ux = x => (x + 5.2) / 13.55;
    P.rect(0, 0, 1, 1, liv.top);
    if (liv.windows === 'round') {
      // синяя ливрея: средняя полоса (v ~0.06..0.18 по бортам) + тёмный низ
      const band = (vTop, vBot, color, flipSide) => {
        // рисуем на одной стороне борта: v0=0.5 (левый) или 0 (правый). Волна поднимается к носу
        ctx.fillStyle = color; ctx.beginPath();
        const pts = [];
        for (let i = 0; i <= 60; i++) { const u = i / 60; const x = -5.2 + u * 13.55; const rise = x > 5.5 ? (x - 5.5) * 0.05 : 0; pts.push([u, vTop + rise]); }
        return pts;
      };
      // левый борт: центр v=0.5; "вверх" — к 0.25, "низ" — к 0.75
      const drawSide = (center, sgn) => {
        // sgn=+1: низ находится при v = center + 0.25 (левый борт: 0.5→0.75). правый: центр 0 -> низ при v=-0.25 → используем wrap: рисуем два раза
        const vv = (off) => center + sgn * off;
        // светло-синяя полоса
        ctx.fillStyle = liv.mid; ctx.beginPath();
        const top = [], bot = [];
        for (let i = 0; i <= 60; i++) { const u = i / 60; const x = -5.2 + u * 13.55; const rise = x > 5.0 ? (x - 5.0) * 0.022 : (x < -2.5 ? (-2.5 - x) * 0.01 : 0); top.push([u, vv(-0.02 - rise)]); bot.push([u, vv(0.09 + rise * 0.5)]); }
        ctx.moveTo(P.X(top[0][0]), P.Y(top[0][1])); top.forEach(p => ctx.lineTo(P.X(p[0]), P.Y(p[1])));
        for (let i = bot.length - 1; i >= 0; i--) ctx.lineTo(P.X(bot[i][0]), P.Y(bot[i][1]));
        ctx.closePath(); ctx.fill();
        // тёмно-синий низ
        ctx.fillStyle = liv.low; ctx.beginPath();
        ctx.moveTo(P.X(bot[0][0]), P.Y(bot[0][1])); bot.forEach(p => ctx.lineTo(P.X(p[0]), P.Y(p[1])));
        ctx.lineTo(P.X(1), P.Y(vv(0.30))); ctx.lineTo(P.X(0), P.Y(vv(0.30))); ctx.closePath(); ctx.fill();
        // белая тонкая полоска между
        P.line(top, '#ffffff', 6);
      };
      drawSide(0.5, 1);   // левый борт (v 0.5 → 0.75 низ)
      drawSide(0.0, -1);  // правый борт (v 0 → -0.25 = wrap 0.75)
      // wrap: часть правого борта ниже v=0 нарисовать на v∈[0.75,1]
      ctx.save(); ctx.translate(0, -H); drawSide(0.0, -1); ctx.restore();
      ctx.save(); ctx.translate(0, H); drawSide(1.0, -1); ctx.restore();
    } else {
      // бордовая ливрея с золотой полосой
      P.rect(0, 0, 1, 1, liv.top);
      P.rect(0, 0.6, 1, 0.9, liv.low);
      P.line([[0, 0.60], [1, 0.60]], liv.stripe, 6); P.line([[0, 0.90], [1, 0.90]], liv.stripe, 6);
      P.line([[ux(-3.0), 0.17], [ux(7.0), 0.17]], liv.stripe, 5); P.line([[ux(-3.0), 0.33], [ux(7.0), 0.33]], liv.stripe, 5);
    }
    /* остекление кабины экипажа: обёртывает нос */
    const gu0 = ux(6.35), gu1 = ux(8.2);
    P.glass(gu0, 0.03, gu1, 0.47, 60);
    // стойки переплёта
    const post = (u, v0, v1) => P.line([[u, v0], [u, v1]], '#0b0e11', 12);
    P.line([[gu0 + 0.005, 0.25], [gu1 - 0.004, 0.25]], '#0b0e11', 11); // центр
    post(ux(7.35), 0.03, 0.47); post(ux(7.8), 0.03, 0.47); post(ux(6.9), 0.03, 0.47);
    P.line([[gu0, 0.13], [gu1, 0.13]], '#0b0e11', 9); P.line([[gu0, 0.37], [gu1, 0.37]], '#0b0e11', 9);
    // сдвижные форточки пилотов
    P.glass(ux(5.5), 0.035, ux(6.3), 0.12, 20); P.glass(ux(5.5), 0.38, ux(6.3), 0.465, 20);
    /* сдвижная дверь левого борта (v ~0.38..0.5) */
    P.seam([[ux(4.2), 0.40], [ux(4.2), 0.59], [ux(2.75), 0.59], [ux(2.75), 0.40], [ux(4.2), 0.40]], 4);
    /* окна салона */
    const xs = liv.windows === 'round' ? [3.55, 1.85, 0.75, -0.35, -1.45] : [3.55, 2.1, 0.9, -0.3, -1.5];
    xs.forEach((x, i) => {
      if (liv.windows === 'round') { P.porthole(ux(x), 0.045, 0.018, 0.045); P.porthole(ux(x), 0.455, 0.018, 0.045); }
      else { P.glass(ux(x - 0.36), 0.015, ux(x + 0.36), 0.085, 18); P.glass(ux(x - 0.36), 0.415, ux(x + 0.36), 0.485, 18); }
    });
    // правая передняя дверь (аварийная) и швы грузовых створок
    P.seam([[ux(4.9), 0.02], [ux(4.9), 0.10], [ux(3.9), 0.10], [ux(3.9), 0.02]], 4);
    P.seam([[ux(-2.5), 0.02], [ux(-2.7), 0.25], [ux(-2.5), 0.48]], 4);
    P.seam([[ux(-3.6), 0.62], [ux(-5.0), 0.75]], 4); P.seam([[ux(-3.6), 0.88], [ux(-5.0), 0.75]], 4);
    /* надписи и флаги */
    const txtColor = liv.windows === 'round' ? liv.low : liv.stripe;
    P.text(liv.type, ux(4.9), 0.155, 30, txtColor, { weight: '700' });
    P.text(liv.type, ux(4.9), 0.345, 30, txtColor, { weight: '700', flip: true });
    P.flagAltai(ux(5.65), 0.19, 0.03, 0.05); P.flagAltai(ux(5.05), 0.31, 0.03, 0.05);
    P.text('АЛТАЙАВИА', ux(0.8), 0.16, 40, txtColor, { weight: '900', stretch: 1.05 });
    P.text('АЛТАЙАВИА', ux(0.8), 0.34, 40, txtColor, { weight: '900', stretch: 1.05, flip: true });
    // швы капотов и панелей
    P.seam([[ux(6.3), 0.16], [ux(6.3), 0.34]], 3);
    for (let i = 0; i < 6; i++) P.seam([[ux(5.0 - i * 1.2), 0.62], [ux(5.0 - i * 1.2), 0.88]], 2);
    return c;
  }
  function paintMi8Boom(liv) {
    const W = 1024, H = 256, c = makeCanvas(W, H), ctx = c.getContext('2d'); const P = painter(ctx, W, H);
    // u: 0 = x=-11 (хвост), 1 = x=-5.2
    const base = liv.windows === 'round' ? liv.top : liv.top;
    P.rect(0, 0, 1, 1, base);
    if (liv.windows === 'round') { P.rect(0, 0.56, 1, 0.94, liv.low); P.line([[0, 0.56], [1, 0.56]], '#ffffff', 4); P.line([[0, 0.94], [1, 0.94]], '#ffffff', 4); }
    else { P.line([[0, 0.17], [1, 0.17]], liv.stripe, 4); P.line([[0, 0.33], [1, 0.33]], liv.stripe, 4); }
    const col = liv.windows === 'round' ? liv.low : liv.stripe;
    P.text(liv.reg, 0.45, 0.14, 54, col, { weight: '900', stretch: 1.1 });
    P.text(liv.reg, 0.45, 0.36, 54, col, { weight: '900', stretch: 1.1, flip: true });
    P.flagRU(0.16, 0.185, 0.05, 0.075); P.flagRU(0.16, 0.395, 0.05, 0.075);
    for (let i = 1; i < 6; i++) P.seam([[i / 6, 0], [i / 6, 1]], 2);
    return c;
  }
  function paintMi8Fin(liv) {
    const W = 512, H = 256, c = makeCanvas(W, H), ctx = c.getContext('2d'); const P = painter(ctx, W, H);
    P.rect(0, 0, 1, 1, liv.top);
    if (liv.windows === 'round') { P.rect(0, 0.58, 1, 0.92, liv.low); }
    else { P.line([[0, 0.2], [1, 0.2]], liv.stripe, 4); P.line([[0, 0.3], [1, 0.3]], liv.stripe, 4); }
    P.seam([[0.5, 0], [0.5, 1]], 2);
    return c;
  }
  function paintMi8Deck(liv) {
    const W = 1024, H = 512, c = makeCanvas(W, H), ctx = c.getContext('2d'); const P = painter(ctx, W, H);
    P.rect(0, 0, 1, 1, liv.top);
    // жалюзи и швы капотов
    for (let i = 0; i < 8; i++) { P.rect(0.55 + i * 0.03, 0.14, 0.565 + i * 0.03, 0.22, 'rgba(0,0,0,0.3)'); P.rect(0.55 + i * 0.03, 0.28, 0.565 + i * 0.03, 0.36, 'rgba(0,0,0,0.3)'); }
    [0.2, 0.42, 0.62, 0.8].forEach(u => P.seam([[u, 0], [u, 1]], 3));
    P.seam([[0, 0.25], [1, 0.25]], 3);
    return c;
  }

  /* ============================================================
     ОКРУЖЕНИЕ: небо/земля для отражений, свет, площадка
     ============================================================ */
  function makeEnvironment(renderer) {
    const pm = new T.PMREMGenerator(renderer);
    const sc = new T.Scene();
    // небо-градиент через vertex colors (ShaderMaterial не кодирует RGBE для PMREM)
    const skyGeo = new T.SphereGeometry(50, 48, 24);
    const top = new T.Color(0x8fbce6), horizon = new T.Color(0xe6ecf1), ground = new T.Color(0x55634f);
    const pa = skyGeo.attributes.position, cols = [];
    const tmp = new T.Color();
    for (let i = 0; i < pa.count; i++) {
      const h = pa.getY(i) / 50;
      if (h > 0) tmp.copy(horizon).lerp(top, Math.pow(h, 0.6)); else tmp.copy(horizon).lerp(ground, Math.pow(-h, 0.5));
      cols.push(tmp.r, tmp.g, tmp.b);
    }
    skyGeo.setAttribute('color', new T.Float32BufferAttribute(cols, 3));
    const skyMat = new T.MeshBasicMaterial({ side: T.BackSide, vertexColors: true });
    sc.add(new T.Mesh(skyGeo, skyMat));
    // «софиты» для бликов
    const addPanel = (x, y, z, w, h, i) => { const m = new T.Mesh(new T.PlaneGeometry(w, h), new T.MeshBasicMaterial({ color: new T.Color().setScalar(i) })); m.position.set(x, y, z); m.lookAt(0, 0, 0); sc.add(m); };
    addPanel(10, 25, 8, 22, 10, 2.6); addPanel(-20, 14, -10, 14, 8, 1.6); addPanel(12, 6, -25, 16, 6, 1.3);
    const tex = pm.fromScene(sc, 0.04).texture;
    pm.dispose();
    return tex;
  }

  function makeHelipad(radius, opts) {
    opts = opts || {};
    const dark = !!opts.dark;
    const g = new T.Group();
    const W = 1024, c = makeCanvas(W, W), ctx = c.getContext('2d');
    // бетонные плиты (днём) / асфальт перрона (тёмная сцена)
    ctx.fillStyle = dark ? '#2b3a55' : '#8d9096'; ctx.fillRect(0, 0, W, W);
    for (let i = 0; i < 4000; i++) { ctx.fillStyle = 'rgba(' + (Math.random() > 0.5 ? '255,255,255' : '0,0,0') + ',' + (Math.random() * 0.06) + ')'; ctx.fillRect(Math.random() * W, Math.random() * W, 2, 2); }
    ctx.strokeStyle = dark ? 'rgba(255,255,255,0.10)' : 'rgba(40,40,45,0.35)'; ctx.lineWidth = 3;
    for (let i = 0; i <= 8; i++) { ctx.beginPath(); ctx.moveTo(i * W / 8, 0); ctx.lineTo(i * W / 8, W); ctx.stroke(); ctx.beginPath(); ctx.moveTo(0, i * W / 8); ctx.lineTo(W, i * W / 8); ctx.stroke(); }
    // жёлтый круг и буква H
    ctx.strokeStyle = '#f0c419'; ctx.lineWidth = 22; ctx.beginPath(); ctx.arc(W / 2, W / 2, W * 0.36, 0, Math.PI * 2); ctx.stroke();
    ctx.lineWidth = 34; ctx.lineCap = 'butt';
    const hx = W / 2, hy = W / 2, hw = W * 0.07, hh = W * 0.11;
    ctx.beginPath(); ctx.moveTo(hx - hw, hy - hh); ctx.lineTo(hx - hw, hy + hh); ctx.moveTo(hx + hw, hy - hh); ctx.lineTo(hx + hw, hy + hh); ctx.moveTo(hx - hw, hy); ctx.lineTo(hx + hw, hy); ctx.stroke();
    const tex = new T.CanvasTexture(c); tex.encoding = T.sRGBEncoding; tex.anisotropy = 8;
    const pad = new T.Mesh(new T.CircleGeometry(radius, 64), new T.MeshStandardMaterial({ map: tex, roughness: 0.95, metalness: 0, envMapIntensity: 0.25 }));
    pad.rotation.x = -Math.PI / 2; pad.receiveShadow = true; g.add(pad);
    // трава (день) / тёмный грунт (ночная сцена)
    const grass = new T.Mesh(new T.CircleGeometry(radius * 6, 64), new T.MeshStandardMaterial({ color: dark ? 0x172742 : 0x5f7f43, roughness: 1, envMapIntensity: 0.2 }));
    grass.rotation.x = -Math.PI / 2; grass.position.y = -0.02; grass.receiveShadow = true; g.add(grass);
    return g;
  }

  /* ============================================================
     VIEWER — интерактивный просмотр модели
     ============================================================ */
  function Viewer(container, opts) {
    opts = opts || {};
    this.container = container;
    this.opts = opts;
    const w = container.clientWidth || 800, h = container.clientHeight || 500;
    const renderer = new T.WebGLRenderer({ antialias: true, alpha: !!opts.transparent, powerPreference: 'high-performance' });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, opts.maxDpr || 2));
    renderer.setSize(w, h);
    renderer.outputEncoding = T.sRGBEncoding;
    renderer.toneMapping = T.ACESFilmicToneMapping;
    renderer.toneMappingExposure = opts.exposure || 1.0;
    renderer.shadowMap.enabled = true; renderer.shadowMap.type = T.PCFSoftShadowMap;
    renderer.physicallyCorrectLights = false;
    container.appendChild(renderer.domElement);
    renderer.domElement.style.display = 'block';
    renderer.domElement.style.width = '100%'; renderer.domElement.style.height = '100%';
    this.renderer = renderer;

    const scene = new T.Scene();
    if (!opts.transparent) scene.background = new T.Color(opts.background || 0xdfe7ee);
    if (opts.fog) scene.fog = new T.Fog(opts.background || 0xdfe7ee, opts.fog[0], opts.fog[1]);
    scene.environment = makeEnvironment(renderer);
    this.scene = scene;

    const camera = new T.PerspectiveCamera(opts.fov || 32, w / h, 0.1, 500);
    this.camera = camera;

    // свет
    const hemi = new T.HemisphereLight(0xdbe9f7, 0x6b7a5c, 0.55); scene.add(hemi);
    const sun = new T.DirectionalLight(0xfff3e0, 1.35);
    sun.position.set(18, 30, 14); sun.castShadow = true;
    sun.shadow.mapSize.set(2048, 2048);
    sun.shadow.camera.near = 1; sun.shadow.camera.far = 120;
    sun.shadow.bias = -0.0004; sun.shadow.normalBias = 0.02;
    scene.add(sun); this.sun = sun;
    const fill = new T.DirectionalLight(0xcfe3ff, 0.35); fill.position.set(-20, 8, -10); scene.add(fill);

    if (opts.helipad !== false) { this.pad = makeHelipad(opts.padRadius || 14, { dark: !!opts.dark }); scene.add(this.pad); }
    if (opts.dark) { scene.fog = new T.Fog(opts.fogColor !== undefined ? opts.fogColor : 0x11244a, 20, 90); this._fog = true; }

    this.model = null; this.rotorState = opts.rotorState || 'idle';
    this.spin = 0; this.orbit = { theta: opts.theta !== undefined ? opts.theta : 0.65, phi: opts.phi !== undefined ? opts.phi : 1.22, dist: 20, target: new T.Vector3(0, 1.5, 0) };
    this.auto = opts.autoRotate !== false; this.autoSpeed = opts.autoSpeed || 0.12;
    this.idleTimer = 0; this.clock = new T.Clock();
    this.running = true; this._first = true;
    this._bindControls();
    const ro = new ResizeObserver(() => this.resize()); ro.observe(container);
    this._ro = ro;
    this._loop = this._loop.bind(this);
    requestAnimationFrame(this._loop);
  }
  Viewer.prototype.setModel = function (model, view) {
    if (this.model) { this.scene.remove(this.model); disposeGroup(this.model); }
    this.model = model; this.scene.add(model);
    const b = model.userData.bounds || { length: 12, height: 3.5 };
    const fit = Math.max(b.length, b.width || 0) * (view && view.fit || 0.95);
    this.orbit.dist = fit; this.orbit.target.set(view && view.tx || 0, (view && view.ty) || b.height * 0.42, 0);
    if (view && view.theta !== undefined) this.orbit.theta = view.theta;
    if (view && view.phi !== undefined) this.orbit.phi = view.phi;
    if (this._fog) { this.scene.fog.near = fit * 1.1; this.scene.fog.far = fit * 4.2; }
    this.sun.shadow.camera.left = -b.length * 0.75; this.sun.shadow.camera.right = b.length * 0.75;
    this.sun.shadow.camera.top = b.length * 0.75; this.sun.shadow.camera.bottom = -b.length * 0.75;
    this.sun.shadow.camera.updateProjectionMatrix();
    this.setRotorState(this.rotorState);
    return this;
  };
  Viewer.prototype.setRotorState = function (s) {
    this.rotorState = s;
    if (!this.model) return;
    (this.model.userData.rotors || []).forEach(r => { r.disc.visible = (s === 'fast'); r.obj.traverse(o => { if (o.isMesh && o !== r.disc) o.material.transparent = (s === 'fast'), o.material.opacity = (s === 'fast') ? 0.35 : 1; }); });
  };
  Viewer.prototype.resize = function () {
    const w = this.container.clientWidth, h = this.container.clientHeight; if (!w || !h) return;
    this.renderer.setSize(w, h, false); this.camera.aspect = w / h; this.camera.updateProjectionMatrix();
  };
  Viewer.prototype._bindControls = function () {
    const el = this.renderer.domElement, o = this.orbit, self = this;
    let drag = false, lx = 0, ly = 0, pinch = 0;
    el.style.touchAction = 'pan-y'; el.style.cursor = 'grab';
    const down = (x, y) => { drag = true; lx = x; ly = y; self.idleTimer = 0; el.style.cursor = 'grabbing'; };
    const move = (x, y) => { if (!drag) return; o.theta -= (x - lx) * 0.006; o.phi = clamp(o.phi - (y - ly) * 0.005, 0.25, 1.52); lx = x; ly = y; self.idleTimer = 0; };
    el.addEventListener('pointerdown', e => { if (e.pointerType === 'touch') return; down(e.clientX, e.clientY); el.setPointerCapture(e.pointerId); });
    el.addEventListener('pointermove', e => { if (e.pointerType === 'touch') return; move(e.clientX, e.clientY); });
    el.addEventListener('pointerup', () => { drag = false; el.style.cursor = 'grab'; });
    el.addEventListener('pointerleave', () => { drag = false; el.style.cursor = 'grab'; });
    el.addEventListener('touchstart', e => { if (e.touches.length === 1) down(e.touches[0].clientX, e.touches[0].clientY); else if (e.touches.length === 2) { drag = false; pinch = Math.hypot(e.touches[0].clientX - e.touches[1].clientX, e.touches[0].clientY - e.touches[1].clientY); } }, { passive: true });
    el.addEventListener('touchmove', e => { if (e.touches.length === 1 && drag) { move(e.touches[0].clientX, e.touches[0].clientY); } else if (e.touches.length === 2) { const d = Math.hypot(e.touches[0].clientX - e.touches[1].clientX, e.touches[0].clientY - e.touches[1].clientY); o.dist = clamp(o.dist * (pinch / d), self._minDist(), self._maxDist()); pinch = d; e.preventDefault && e.cancelable && e.preventDefault(); } }, { passive: false });
    el.addEventListener('touchend', () => { drag = false; });
    el.addEventListener('wheel', e => { if (!self.opts.wheelZoom) return; e.preventDefault(); o.dist = clamp(o.dist * (1 + Math.sign(e.deltaY) * 0.08), self._minDist(), self._maxDist()); self.idleTimer = 0; }, { passive: false });
  };
  Viewer.prototype._minDist = function () { const b = this.model && this.model.userData.bounds; return b ? b.length * 0.35 : 4; };
  Viewer.prototype._maxDist = function () { const b = this.model && this.model.userData.bounds; return b ? b.length * 2.2 : 60; };
  Viewer.prototype._loop = function () {
    if (!this.running) return;
    requestAnimationFrame(this._loop);
    const dt = Math.min(0.05, this.clock.getDelta());
    const vis = this._visible !== false;
    if (!vis) return;
    this.idleTimer += dt;
    if (this.auto && this.idleTimer > 2.5) this.orbit.theta += this.autoSpeed * dt;
    const o = this.orbit;
    const cx = o.target.x + o.dist * Math.sin(o.phi) * Math.sin(o.theta);
    const cz = o.target.z + o.dist * Math.sin(o.phi) * Math.cos(o.theta);
    const cy = o.target.y + o.dist * Math.cos(o.phi);
    if (this._first) { this.camera.position.set(cx, cy, cz); this._first = false; } else this.camera.position.lerp(new T.Vector3(cx, cy, cz), 0.12);
    this.camera.lookAt(o.target);
    if (this.model) {
      const rate = this.rotorState === 'fast' ? 1 : this.rotorState === 'idle' ? 0.06 : 0;
      (this.model.userData.rotors || []).forEach(r => {
        const w = r.rpm / 60 * Math.PI * 2 * rate * dt * r.dir;
        if (r.axis === 'y') r.obj.rotation.y += w; else r.obj.rotation.z += w;
      });
      if (this.opts.hover) { const t = this.clock.elapsedTime; this.model.position.y = Math.sin(t * 0.9) * 0.08; this.model.rotation.z = Math.sin(t * 0.7) * 0.01; }
    }
    this.renderer.render(this.scene, this.camera);
  };
  Viewer.prototype.setVisible = function (v) { this._visible = v; };
  Viewer.prototype.dispose = function () { this.running = false; this._ro.disconnect(); this.renderer.dispose(); };

  function disposeGroup(g) { g.traverse(o => { if (o.geometry) o.geometry.dispose(); if (o.material) { (Array.isArray(o.material) ? o.material : [o.material]).forEach(m => { if (m.map) m.map.dispose(); m.dispose(); }); } }); }
  function clamp(v, a, b) { return Math.max(a, Math.min(b, v)); }

  /* Каталог моделей */
  const MODELS = {
    as350: { name: 'Eurocopter AS350', build: () => buildAS350(LIVERY.as350_navy), view: { fit: 1.05, ty: 1.45, tx: -1.6 } },
    as350_red: { name: 'Eurocopter AS350', build: () => buildAS350(LIVERY.as350_red), view: { fit: 1.05, ty: 1.45, tx: -1.6 } },
    mi8amt: { name: 'Ми-8АМТ', build: () => buildMi8(LIVERY.mi8amt_blue), view: { fit: 1.0, ty: 2.4, tx: -2.1 } },
    mi171: { name: 'Ми-171', build: () => buildMi8(LIVERY.mi171_maroon), view: { fit: 1.0, ty: 2.4, tx: -2.1 } }
  };

  global.Heli3D = { loft, slab, bladeGeometry, buildAS350, buildMi8, LIVERY, MODELS, Viewer, makeEnvironment, makeHelipad, MAT, painter, canvasTexture, makeCanvas, disposeGroup };
})(window);
