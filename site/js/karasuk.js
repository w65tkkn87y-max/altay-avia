/* АлтайАвиа — 3D-сцена вертолётной площадки «Карасук» (с. Чепош, долина Катуни, Республика Алтай).
   Реальный рельеф (SRTM) и снимок Sentinel-2 cloudless 2016 (EOX, s2maps.eu, CC BY 4.0) ±9 км;
   планировка базы — по спутниковому снимку и фото: ангары, перрон, рулёжки, площадки, полоса сосен вдоль
   Чуйского тракта, посёлок; Катунь — вода с бликами. Данные: scene/karasuk.js (build/terrain/build_karasuk.py).
   Оси: x — восток, z — юг, y — вверх, метры; начало — центр площадки P3 (там стоит вертолёт). */
(function (global) {
  'use strict';
  const T = global.THREE, H = global.Heli3D;
  if (!T || !H) return;
  const MOBILE = global.matchMedia && global.matchMedia('(max-width: 760px)').matches;

  const b64 = str => { const bin = atob(str), u8 = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) u8[i] = bin.charCodeAt(i); return u8.buffer; };
  const lin = hex => new T.Color(hex).convertSRGBToLinear();
  const rng = seed => { let s = seed >>> 0; return () => ((s = (Math.imul(s, 1664525) + 1013904223) >>> 0) / 4294967296); };
  const canvas = (w, h) => { const c = document.createElement('canvas'); c.width = w; c.height = h; return c; };
  const ctex = (c, rep) => { const t = new T.CanvasTexture(c); t.encoding = T.sRGBEncoding; t.anisotropy = 8; if (rep) { t.wrapS = t.wrapT = T.RepeatWrapping; } return t; };

  /* ---------- загрузка данных (общая для всех 3D-блоков страницы) ---------- */
  let dataPromise = null;
  function loadData(base, ver) {
    if (dataPromise) return dataPromise;
    dataPromise = new Promise(res => {
      if (global.AltayScenes && global.AltayScenes.karasuk) return res(global.AltayScenes.karasuk);
      const s = document.createElement('script'); s.src = base + 'karasuk.js' + (ver ? '?v=' + ver : ''); s.async = true;
      s.onload = () => res(global.AltayScenes && global.AltayScenes.karasuk); s.onerror = () => res(null);
      document.head.appendChild(s);
    });
    return dataPromise;
  }
  const texCache = {};
  function loadTex(url, srgb) {
    if (texCache[url]) return texCache[url];
    return (texCache[url] = new Promise(res => {
      const t = new T.TextureLoader().load(url, () => res(t), undefined, () => res(null));
      t.flipY = false; if (srgb) t.encoding = T.sRGBEncoding; t.anisotropy = 8;
    }));
  }

  /* ---------- детальная фактура (трава/хвоя/земля), бесшовная ---------- */
  let detailTex = null;
  function detailTexture() {
    if (detailTex) return detailTex;
    const S = 256, c = canvas(S, S), g = c.getContext('2d'), img = g.createImageData(S, S);
    const r = rng(7);
    const lattice = n => { const a = new Float32Array(n * n); for (let i = 0; i < a.length; i++) a[i] = r(); return a; };
    const L = [lattice(8), lattice(32), lattice(64), lattice(16), lattice(4)];
    const val = (a, n, x, y) => {       // периодический value noise
      const fx = x * n, fy = y * n, x0 = Math.floor(fx), y0 = Math.floor(fy), tx = fx - x0, ty = fy - y0;
      const s = t => t * t * (3 - 2 * t), q = (i, j) => a[((j % n + n) % n) * n + ((i % n + n) % n)];
      const a0 = q(x0, y0) + (q(x0 + 1, y0) - q(x0, y0)) * s(tx), a1 = q(x0, y0 + 1) + (q(x0 + 1, y0 + 1) - q(x0, y0 + 1)) * s(tx);
      return a0 + (a1 - a0) * s(ty);
    };
    for (let y = 0; y < S; y++) for (let x = 0; x < S; x++) {
      const u = x / S, v = y / S, k = (y * S + x) * 4;
      const fine = 0.45 * val(L[2], 64, u, v) + 0.35 * val(L[1], 32, u, v) + 0.2 * r();
      const mid = 0.6 * val(L[3], 16, u, v) + 0.4 * val(L[0], 8, u, v);
      const coarse = 0.7 * val(L[4], 4, u, v) + 0.3 * val(L[0], 8, u, v);
      img.data[k] = fine * 255; img.data[k + 1] = mid * 255; img.data[k + 2] = coarse * 255; img.data[k + 3] = 255;
    }
    g.putImageData(img, 0, 0);
    detailTex = new T.CanvasTexture(c); detailTex.wrapS = detailTex.wrapT = T.RepeatWrapping; detailTex.anisotropy = 8;
    return detailTex;
  }

  /* ---------- трава у площадки: луг (кочки, сухие и тёмные пятна), травинки вблизи и объёмные кустики ---------- */
  const vnoise = (r, n) => {        // периодический value noise на решётке n×n (u, v ∈ [0,1))
    const a = new Float32Array(n * n); for (let i = 0; i < a.length; i++) a[i] = r();
    const q = (i, j) => a[((j % n + n) % n) * n + ((i % n + n) % n)], s = t => t * t * (3 - 2 * t);
    return (u, v) => { const fx = u * n, fy = v * n, x0 = Math.floor(fx), y0 = Math.floor(fy), tx = s(fx - x0), ty = s(fy - y0);
      const a0 = q(x0, y0) + (q(x0 + 1, y0) - q(x0, y0)) * tx, a1 = q(x0, y0 + 1) + (q(x0 + 1, y0 + 1) - q(x0, y0 + 1)) * tx; return a0 + (a1 - a0) * ty; };
  };
  const toLin = c => Math.pow(c / 255, 2.2);
  function meanLinear(c) {          // средний цвет холста в линейном пространстве (для согласования яркости со снимком)
    const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data; let r = 0, g = 0, b = 0; const n = d.length / 4;
    for (let i = 0; i < d.length; i += 16) { r += toLin(d[i]); g += toLin(d[i + 1]); b += toLin(d[i + 2]); }
    return new T.Vector3(r * 4 / n, g * 4 / n, b * 4 / n);
  }
  let meadowTex = null, meadowMean = null;
  function meadowTexture() {        // 14×14 м луга: кочки и куртины 0.1–2 м, сухие (соломенные) пятна, тёмные густые куртины
    if (meadowTex) return meadowTex;
    const S = 512, c = canvas(S, S), g = c.getContext('2d'), img = g.createImageData(S, S), r = rng(53);
    const n1 = vnoise(r, 8), n2 = vnoise(r, 32), n3 = vnoise(r, 96), n4 = vnoise(r, 5), n5 = vnoise(r, 160);
    const dark = [68, 90, 39], mid = [99, 127, 56], light = [128, 150, 78], dry = [160, 152, 94], straw = [180, 169, 112];
    const mix = (a, b, t) => [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t];
    const sm = (e0, e1, x) => { const t = Math.min(1, Math.max(0, (x - e0) / (e1 - e0))); return t * t * (3 - 2 * t); };
    for (let y = 0; y < S; y++) for (let x = 0; x < S; x++) {
      const u = x / S, v = y / S, k = (y * S + x) * 4;
      const t = 0.45 * n2(u, v) + 0.35 * n3(u, v) + 0.2 * n1(u, v);
      let col = t < 0.5 ? mix(dark, mid, sm(0.22, 0.5, t)) : mix(mid, light, sm(0.5, 0.78, t));
      const dz = sm(0.56, 0.74, n4(u, v) + 0.25 * (n2(u, v) - 0.5));                     // сухие пятна
      col = mix(col, mix(dry, straw, n3(u, v)), dz * 0.5);
      const f = 0.9 + 0.2 * n5(u, v) + (r() - 0.5) * 0.08;                                 // кочки у земли и шум травинок
      img.data[k] = col[0] * f; img.data[k + 1] = col[1] * f; img.data[k + 2] = col[2] * f; img.data[k + 3] = 255;
    }
    g.putImageData(img, 0, 0);
    meadowMean = meanLinear(c);
    meadowTex = ctex(c, true); meadowTex.anisotropy = 16;
    return meadowTex;
  }
  let grassTex = null, grassMean = null;
  function grassTexture() {   // 2.4×2.4 м: травинки разных оттенков с тенями между ними, сухие стебли, клевер
    if (grassTex) return grassTex;
    const S = 1024, c = canvas(S, S), g = c.getContext('2d'), r = rng(41);
    g.fillStyle = '#2f421b'; g.fillRect(0, 0, S, S);
    const greens = ['#3f5d24', '#4b6d2a', '#587a30', '#648838', '#6f9140', '#7d9c47', '#86a34e', '#5a7a2c'];
    const dry = ['#9c9460', '#a9a06a', '#8e8a58', '#b3aa73'];
    for (let i = 0; i < 700; i++) { g.fillStyle = 'rgba(20,30,10,' + (0.2 + r() * 0.25) + ')'; g.beginPath(); g.ellipse(r() * S, r() * S, 10 + r() * 40, 8 + r() * 30, r() * 3, 0, 6.3); g.fill(); }
    const blade = (x, y, len, ang, w, col) => { g.strokeStyle = col; g.lineWidth = w; g.beginPath(); g.moveTo(x, y); g.quadraticCurveTo(x + Math.cos(ang) * len * 0.5 + (r() - 0.5) * 4, y + Math.sin(ang) * len * 0.5, x + Math.cos(ang) * len, y + Math.sin(ang) * len); g.stroke(); };
    for (let i = 0; i < 60000; i++) {
      const x = r() * S, y = r() * S, a = r() * Math.PI * 2, len = 6 + r() * 18, isDry = r() < 0.08;
      blade(x, y, len, a, 1 + r() * 1.6, isDry ? dry[Math.floor(r() * dry.length)] : greens[Math.floor(r() * greens.length)]);
      if (x < 24 || y < 24) blade(x + (x < 24 ? S : 0), y + (y < 24 ? S : 0), len, a, 1.2, greens[3]);   // бесшовность у краёв
    }
    for (let i = 0; i < 160; i++) {   // клевер и мелкие листья
      const x = r() * S, y = r() * S; g.fillStyle = r() > 0.5 ? '#5f8a34' : '#6b963c';
      for (let k = 0; k < 3; k++) { const a = k * 2.1 + r(); g.beginPath(); g.ellipse(x + Math.cos(a) * 4, y + Math.sin(a) * 4, 4, 3, a, 0, 6.3); g.fill(); }
    }
    grassMean = meanLinear(c);
    grassTex = ctex(c, true); grassTex.anisotropy = 16;
    return grassTex;
  }
  function grassTufts(d) {
    // кустики травы вокруг большой площадки (не на бетоне): 8 травинок от тёмного основания к светлым кончикам,
    // нормали «вверх» — освещены как земля, поэтому сливаются с лугом и дают объём у самой земли
    const rects = [];
    d.pads.forEach(p => rects.push([p.x - p.s / 2 - 0.3, p.x + p.s / 2 + 0.3, p.z - p.s / 2 - 0.3, p.z + p.s / 2 + 0.3]));
    d.taxiways.forEach(([a, b, w]) => rects.push([Math.min(a[0], b[0]) - w / 2 - 0.2, Math.max(a[0], b[0]) + w / 2 + 0.2, Math.min(a[1], b[1]) - w / 2 - 0.2, Math.max(a[1], b[1]) + w / 2 + 0.2]));
    rects.push([d.apron.x[0] - 1, d.apron.x[1] + 0.5, d.apron.z[0] - 0.5, d.apron.z[1] + 0.5]);
    const onConcrete = (x, z) => rects.some(q => x > q[0] && x < q[1] && z > q[2] && z < q[3]);
    const N = MOBILE ? 9000 : 32000, R = MOBILE ? 28 : 44, r = rng(47), list = [];
    for (let i = 0; i < N * 4 && list.length < N; i++) {
      const a = r() * Math.PI * 2, dd = Math.sqrt(r()) * R, x = Math.cos(a) * dd, z = Math.sin(a) * dd;
      const edge = Math.min(1, Math.max(0, (dd - R * 0.5) / (R * 0.5)));          // к краю реже и мельче — без видимой границы
      if (r() < 1 - edge * edge * (3 - 2 * edge) && !onConcrete(x, z)) list.push([x, z, 1 - 0.45 * edge]);
    }
    const B = 8, pos = new Float32Array(B * 9), nor = new Float32Array(B * 9), col = new Float32Array(B * 9);
    const base = lin(0x3d5523), tips = [lin(0x80994a), lin(0x6f8d3e), lin(0x93a55a), lin(0xa89f63)];
    for (let i = 0; i < B; i++) {
      const a = i / B * Math.PI * 2 + r() * 0.8, lean = 0.45 + r() * 0.55, h = 0.55 + r() * 0.45, w = 0.03 + r() * 0.025;
      const ox = Math.cos(a) * 0.12 * r(), oz = Math.sin(a) * 0.12 * r(), px = -Math.sin(a) * w, pz = Math.cos(a) * w;
      const tip = [ox + Math.cos(a) * lean * h, h, oz + Math.sin(a) * lean * h];
      const v = [[ox - px, 0, oz - pz], [ox + px, 0, oz + pz], tip], tc = tips[Math.floor(r() * tips.length)];
      v.forEach((p, j) => { pos.set(p, i * 9 + j * 3); nor.set([0, 1, 0], i * 9 + j * 3); const c = j < 2 ? base : tc; col.set([c.r, c.g, c.b], i * 9 + j * 3); });
    }
    const geo = new T.BufferGeometry();
    geo.setAttribute('position', new T.BufferAttribute(pos, 3)); geo.setAttribute('normal', new T.BufferAttribute(nor, 3)); geo.setAttribute('color', new T.BufferAttribute(col, 3));
    const mat = new T.MeshStandardMaterial({ vertexColors: true, side: T.DoubleSide, roughness: 0.92, metalness: 0, envMapIntensity: 0.4 });
    // вдали кустики «прорастают» в землю: мельче пикселя они дают только рябь (и тёмное пятно при виде сверху)
    mat.onBeforeCompile = sh => { sh.vertexShader = sh.vertexShader.replace('#include <begin_vertex>', `#include <begin_vertex>
  vec3 tuftPos = (modelMatrix * instanceMatrix * vec4(0.0, 0.0, 0.0, 1.0)).xyz;
  transformed *= 1.0 - smoothstep(50.0, 95.0, distance(tuftPos, cameraPosition));`); };
    const im = new T.InstancedMesh(geo, mat, list.length), mtx = new T.Matrix4(), qq = new T.Quaternion(), up = new T.Vector3(0, 1, 0), c = new T.Color();
    list.forEach(([x, z, k], i) => {
      const sc = (0.14 + r() * 0.2) * k; qq.setFromAxisAngle(up, r() * 6.283);
      mtx.compose(new T.Vector3(x, 0, z), qq, new T.Vector3(sc * (0.8 + r() * 0.5), sc, sc * (0.8 + r() * 0.5))); im.setMatrixAt(i, mtx);
      const b = 0.8 + r() * 0.35; c.setRGB(b, b * (0.97 + r() * 0.06), b * 0.95); im.setColorAt(i, c);
    });
    im.receiveShadow = true; im.name = 'grass';
    return im;
  }

  /* ---------- машины на стоянке ---------- */
  function cars(list) {
    if (!list || !list.length) return new T.Group();
    const parts = [];
    list.forEach(cr => {
      const body = lin(cr.c), glass = lin(0x1b2530), tyre = lin(0x1a1a1c), chrome = lin(0xb9bec4);
      const m = (x, y, z, sx, sy, sz) => M4(0, 0, 0, 1).premultiply(new T.Matrix4().makeRotationY(cr.r)).premultiply(new T.Matrix4().makeTranslation(cr.x, 0, cr.z)).multiply(M4(x, y, z, sx, sy, sz));
      parts.push({ g: new T.BoxGeometry(1, 1, 1), m: m(0, 0.62, 0, 4.45, 0.72, 1.82), c: body });           // кузов
      parts.push({ g: new T.BoxGeometry(1, 1, 1), m: m(-0.25, 1.22, 0, 2.5, 0.52, 1.66), c: glass });      // остекление салона
      parts.push({ g: new T.BoxGeometry(1, 1, 1), m: m(-0.3, 1.5, 0, 2.2, 0.08, 1.6), c: body });          // крыша
      parts.push({ g: new T.BoxGeometry(1, 1, 1), m: m(2.24, 0.62, 0, 0.04, 0.22, 1.5), c: chrome });      // решётка
      [[1.42, 0.86], [1.42, -0.86], [-1.38, 0.86], [-1.38, -0.86]].forEach(([wx, wz]) => {
        const w = new T.CylinderGeometry(0.34, 0.34, 0.24, 14); w.rotateX(Math.PI / 2);
        parts.push({ g: w, m: m(wx, 0.34, wz, 1, 1, 1), c: tyre });
      });
    });
    const mesh = new T.Mesh(merge(parts), new T.MeshStandardMaterial({ vertexColors: true, roughness: 0.35, metalness: 0.4 }));
    mesh.castShadow = true; mesh.receiveShadow = true; mesh.name = 'cars';
    return mesh;
  }

  /* ---------- рельеф ---------- */
  function terrain(d, tex) {
    const N = d.N, R = d.R, A = d.A, hs = new Int16Array(b64(d.h));
    const xs = new Float32Array(N);
    for (let i = 0; i < N; i++) { const u = -1 + 2 * i / (N - 1); xs[i] = R * (A * u + (1 - A) * u * u * u); }
    const pos = new Float32Array(N * N * 3), uv = new Float32Array(N * N * 2);
    for (let j = 0; j < N; j++) for (let i = 0; i < N; i++) {
      const k = j * N + i; pos[k * 3] = xs[i]; pos[k * 3 + 1] = hs[k] / 10; pos[k * 3 + 2] = xs[j];
      uv[k * 2] = (xs[i] + R) / (2 * R); uv[k * 2 + 1] = (xs[j] + R) / (2 * R);
    }
    const idx = new Uint32Array((N - 1) * (N - 1) * 6); let q = 0;
    for (let j = 0; j < N - 1; j++) for (let i = 0; i < N - 1; i++) {
      const a = j * N + i, b = a + 1, c = a + N, e = c + 1;
      idx[q++] = a; idx[q++] = c; idx[q++] = b; idx[q++] = b; idx[q++] = c; idx[q++] = e;
    }
    const g = new T.BufferGeometry();
    g.setAttribute('position', new T.BufferAttribute(pos, 3)); g.setAttribute('uv', new T.BufferAttribute(uv, 2));
    g.setIndex(new T.BufferAttribute(idx, 1)); g.computeVertexNormals(); g.computeBoundingSphere();
    const U = { nearMap: { value: tex.near }, waterMap: { value: tex.water }, detailMap: { value: detailTexture() }, grassMap: { value: grassTexture() }, meadowMap: { value: meadowTexture() }, grassMean: { value: grassMean }, meadowMean: { value: meadowMean },
                uNear: { value: d.near }, uTime: { value: 0 }, uWater: { value: lin(0x5aa39d) }, uWaterDeep: { value: lin(0x2f6f73) } };
    const m = new T.MeshStandardMaterial({ map: tex.sat, roughness: 0.94, metalness: 0, envMapIntensity: 0.55 });
    m.onBeforeCompile = sh => {
      Object.assign(sh.uniforms, U);
      sh.vertexShader = 'varying vec3 vWPos;\n' + sh.vertexShader.replace('#include <begin_vertex>', '#include <begin_vertex>\n  vWPos = (modelMatrix * vec4(transformed, 1.0)).xyz;');
      sh.fragmentShader = 'varying vec3 vWPos;\nuniform sampler2D nearMap, waterMap, detailMap, grassMap, meadowMap;\nuniform vec3 grassMean, meadowMean;\nuniform float uNear, uTime;\nuniform vec3 uWater, uWaterDeep;\nfloat kWat = 0.0;\n' +
        sh.fragmentShader.replace('#include <map_fragment>', `
  vec3 col = mapTexelToLinear(texture2D(map, vUv)).rgb;
  vec2 nUv = (vWPos.xz + uNear) / (2.0 * uNear);
  float fN = smoothstep(0.0, 0.12, min(min(nUv.x, 1.0 - nUv.x), min(nUv.y, 1.0 - nUv.y)));
  if (fN > 0.0) col = mix(col, sRGBToLinear(texture2D(nearMap, clamp(nUv, 0.0, 1.0))).rgb, fN);
  float camD = distance(vWPos, cameraPosition);
  float d1 = texture2D(detailMap, vWPos.xz / 2.6).r, d2 = texture2D(detailMap, vWPos.xz / 23.0).g, d3 = texture2D(detailMap, vWPos.xz / 190.0).b;
  float nearAmt = 1.0 - smoothstep(30.0, 600.0, camD);
  col *= mix(1.0, 0.8 + 0.4 * d1, nearAmt * 0.6) * mix(0.82 + 0.36 * d2, 0.93 + 0.14 * d2, nearAmt) * (0.92 + 0.16 * d3);   // вблизи — без крупных пятен
  float d0 = texture2D(detailMap, vWPos.xz / 0.62).r;                                  // зерно травы у ног
  col *= mix(1.0, 0.8 + 0.4 * d0, 1.0 - smoothstep(4.0, 70.0, camD));
  // полог леса по маске (G): тёмно-зелёные кроны с тенями между ними, светлее на гребнях
  float forest = texture2D(waterMap, vUv).g * (1.0 - fN);
  float crowns = smoothstep(0.3, 0.72, texture2D(detailMap, vWPos.xz / 9.0).g * 0.6 + texture2D(detailMap, vWPos.xz / 3.7).r * 0.4);
  vec3 fcol = mix(vec3(0.008, 0.017, 0.009), vec3(0.026, 0.05, 0.022), crowns) * (0.75 + 0.5 * d3);
  fcol = mix(fcol, col * vec3(0.5, 0.62, 0.45), 0.25);
  col = mix(col, fcol, forest * 0.93);
  // трава вблизи: луг (кочки, сухие и тёмные куртины) × рисунок травинок; оба слоя в двух масштабах с поворотом — без видимого
  // повтора; средняя яркость частично подтянута к снимку, чтобы на границе зоны не было кольца
  float gAmt = (1.0 - smoothstep(40.0, 320.0, camD)) * fN * (1.0 - forest);
  if (gAmt > 0.001) {
    vec2 gpA = vWPos.xz, gpB = vec2(0.8 * gpA.x - 0.6 * gpA.y, 0.6 * gpA.x + 0.8 * gpA.y);
    vec3 meA = sRGBToLinear(texture2D(meadowMap, gpA / 14.0)).rgb;
    vec3 meB = sRGBToLinear(texture2D(meadowMap, gpB / 9.1 + vec2(0.37))).rgb;
    vec3 grA = sRGBToLinear(texture2D(grassMap, gpA / 2.4)).rgb;
    vec3 grB = sRGBToLinear(texture2D(grassMap, gpB / 3.7)).rgb;
    vec3 gTex = mix(meA, meB, 0.42) * mix(vec3(1.0), mix(grA, grB, 0.45) / grassMean, 0.9);
    vec3 lumW = vec3(0.3, 0.59, 0.11);
    vec3 grass = gTex * mix(1.0, dot(col, lumW) / dot(meadowMean, lumW), 0.4);
    col = mix(col, grass, gAmt);
  }
  col *= vec3(0.96, 0.95, 0.9);                                                           // чуть приглушить луга на солнце
  kWat = smoothstep(0.25, 0.75, texture2D(waterMap, vUv).r);
  vec3 wcol = mix(uWater, uWaterDeep, 0.35 + 0.4 * d3) * (0.9 + 0.2 * d2);
  col = mix(col, wcol, kWat * 0.85);
  diffuseColor.rgb *= col;`)
          .replace('#include <roughnessmap_fragment>', '#include <roughnessmap_fragment>\n  roughnessFactor = mix(roughnessFactor, 0.06, kWat);')
          .replace('#include <normal_fragment_maps>', `#include <normal_fragment_maps>
  if (kWat > 0.01) {
    vec2 p = vWPos.xz * 0.35; float t = uTime;
    vec2 gw = vec2(sin(p.x * 1.7 + t * 1.3) + 0.6 * sin(p.y * 2.3 - t * 1.1) + 0.3 * sin((p.x + p.y) * 4.1 + t * 2.1),
                   cos(p.y * 1.9 + t * 1.5) + 0.6 * cos(p.x * 2.7 - t * 0.9) + 0.3 * cos((p.x - p.y) * 3.7 + t * 1.8));
    normal = normalize(normal + (viewMatrix * vec4(gw.x, 0.0, gw.y, 0.0)).xyz * 0.05 * kWat);
  }`);
    };
    const mesh = new T.Mesh(g, m); mesh.receiveShadow = true; mesh.name = 'terrain';
    mesh.userData.tick = t => { U.uTime.value = t; };
    return mesh;
  }

  /* ---------- геометрия: слияние простых частей с цветом вершин ---------- */
  function merge(parts) {
    let n = 0; parts.forEach(p => { n += (p.g.index ? p.g.index.count : p.g.attributes.position.count); });
    const pos = new Float32Array(n * 3), nor = new Float32Array(n * 3), col = new Float32Array(n * 3), uv = new Float32Array(n * 2); let o = 0;
    const v = new T.Vector3(), m3 = new T.Matrix3();
    parts.forEach(p => {
      const g = p.g.index ? p.g.toNonIndexed() : p.g;
      if (p.jitter) {   // неровная «пушистая» крона: смещаем вершины единичной сферы (одинаково для совпадающих вершин)
        const P0 = g.attributes.position, key = (x, y, z) => Math.round(x * 97) + ',' + Math.round(y * 97) + ',' + Math.round(z * 97), off = {};
        for (let i = 0; i < P0.count; i++) { const k = key(P0.getX(i), P0.getY(i), P0.getZ(i)); if (off[k] === undefined) off[k] = 1 + (p.jitter() - 0.5) * 0.55; const f = off[k]; P0.setXYZ(i, P0.getX(i) * f, P0.getY(i) * f, P0.getZ(i) * f); }
      }
      g.applyMatrix4(p.m || new T.Matrix4());
      const ctr = p.radial ? new T.Vector3().setFromMatrixPosition(p.m) : null;
      const P = g.attributes.position, Nn = g.attributes.normal, UV = g.attributes.uv, c = p.c;
      for (let i = 0; i < P.count; i++, o++) {
        pos[o * 3] = P.getX(i); pos[o * 3 + 1] = P.getY(i); pos[o * 3 + 2] = P.getZ(i);
        if (p.up) { nor[o * 3] = 0; nor[o * 3 + 1] = 1; nor[o * 3 + 2] = 0; }
        else if (ctr) { v.set(P.getX(i) - ctr.x, (P.getY(i) - ctr.y) * 1.6 + 0.02, P.getZ(i) - ctr.z).normalize(); nor[o * 3] = v.x; nor[o * 3 + 1] = v.y; nor[o * 3 + 2] = v.z; }   // мягкая «объёмная» крона
        else { nor[o * 3] = Nn.getX(i); nor[o * 3 + 1] = Nn.getY(i); nor[o * 3 + 2] = Nn.getZ(i); }
        const cc = typeof c === 'function' ? c(P.getY(i)) : c;
        col[o * 3] = cc.r; col[o * 3 + 1] = cc.g; col[o * 3 + 2] = cc.b;
        if (UV) { uv[o * 2] = UV.getX(i); uv[o * 2 + 1] = UV.getY(i); }
      }
    });
    const g = new T.BufferGeometry();
    g.setAttribute('position', new T.BufferAttribute(pos, 3)); g.setAttribute('normal', new T.BufferAttribute(nor, 3));
    g.setAttribute('color', new T.BufferAttribute(col, 3)); g.setAttribute('uv', new T.BufferAttribute(uv, 2));
    return g;
  }
  const M4 = (x, y, z, sx, sy, sz, ry) => new T.Matrix4().compose(new T.Vector3(x, y, z), new T.Quaternion().setFromAxisAngle(new T.Vector3(0, 1, 0), ry || 0), new T.Vector3(sx, sy === undefined ? sx : sy, sz === undefined ? sx : sz));

  /* ---------- деревья: вблизи объёмные, вдали — перекрёстные «билборды» ---------- */
  const PINE = 0, SPRUCE = 1, BIRCH = 2;
  function treeGeometries() {
    const r = rng(11);
    const spruceA = lin(0x1d3526), spruceB = lin(0x24402d), birchLeaf = lin(0x5f8a3a), birchLeaf2 = lin(0x719a45);
    // сосна обыкновенная: голый ствол (снизу серо-бурый, выше — рыже-оранжевый), плоская рваная крона наверху
    const bark = y => y < 0.35 ? lin(0x4f4237) : lin(0x74503a);
    const crownC = (lo, hi) => y => lin(lo).lerp(lin(hi), Math.max(0, Math.min(1, (y - 0.55) / 0.42)));   // снизу темнее, сверху светлее
    const pine = [{ g: new T.CylinderGeometry(0.008, 0.018, 0.86, 6, 2), m: M4(0, 0.43, 0, 1), c: bark }];
    for (let i = 0; i < 9; i++) {   // многоярусная неровная крона в верхних ~40%: внизу шире, вверху уже
      const t = i / 8, a = r() * Math.PI * 2, rr = (0.1 - t * 0.07) * (0.4 + r() * 0.6), y = 0.6 + t * 0.34 + (r() - 0.5) * 0.04, s = 0.1 - t * 0.04 + r() * 0.03;
      pine.push({ g: new T.IcosahedronGeometry(1, 0), m: M4(Math.cos(a) * rr, y, Math.sin(a) * rr, s * 1.3, s * 0.55, s * 1.15, r() * 3), c: crownC(i % 2 ? 0x1f3319 : 0x243a1d, i % 2 ? 0x3a5a2c : 0x44662f), radial: true, jitter: r });
    }
    // ель / пихта / кедр: узкий ярусный конус, ветви слегка свисают
    const spruce = [{ g: new T.CylinderGeometry(0.008, 0.018, 0.22, 5), m: M4(0, 0.11, 0, 1), c: lin(0x3f3127) }];
    for (let i = 0; i < 7; i++) {
      const t = i / 7, rad = 0.17 * Math.pow(1 - t, 0.9) + 0.025, h = 0.2 - t * 0.07;
      spruce.push({ g: new T.ConeGeometry(rad, h, 7, 1, true), m: M4(0, 0.08 + t * 0.8 + h / 2, 0, 1, 1, 1, r() * 3), c: i % 2 ? spruceA : spruceB });
    }
    spruce.push({ g: new T.ConeGeometry(0.03, 0.1, 5), m: M4(0, 0.95, 0, 1), c: spruceA });
    // берёза: белый ствол, лёгкая раскидистая крона
    const birch = [{ g: new T.CylinderGeometry(0.009, 0.016, 0.72, 5), m: M4(0, 0.36, 0, 1), c: lin(0xe8e5dc) }];
    for (let i = 0; i < 4; i++) { const a = r() * Math.PI * 2, rr = 0.02 + r() * 0.07, s = 0.09 + r() * 0.05;
      birch.push({ g: new T.IcosahedronGeometry(1, 0), m: M4(Math.cos(a) * rr, 0.58 + r() * 0.32, Math.sin(a) * rr, s, s * 1.2, s, r() * 3), c: i % 2 ? birchLeaf : birchLeaf2, radial: true, jitter: r }); }
    return [merge(pine), merge(spruce), merge(birch)];
  }
  let billboardTex = null;
  function billboardTexture() {
    if (billboardTex) return billboardTex;
    // дальний лес должен читаться сплошным тёмным пологом: плотные кроны, мягкие тени, без светлых просветов
    const W = 1536, Hh = 512, c = canvas(W, Hh), g = c.getContext('2d'), r = rng(3);
    const blob = (x, y, rx, ry, col) => { g.fillStyle = col; g.beginPath(); g.ellipse(x, y, rx, ry, r() * 3, 0, Math.PI * 2); g.fill(); };
    const shade = (base, k) => { const m = base.match(/\w\w/g).map(h => parseInt(h, 16)); return 'rgb(' + m.map(v => Math.round(Math.min(255, v * k))).join(',') + ')'; };
    // сосна (x=256): широкая округлая крона на верхней половине, снизу — тень
    g.fillStyle = '#4a3a2e'; g.fillRect(250, 240, 12, 272);
    blob(256, 150, 170, 120, '#1f331b');
    for (let i = 0; i < 260; i++) { const y = 40 + r() * 210, k = 0.7 + (1 - (y - 40) / 210) * 0.5 + r() * 0.25; blob(256 + (r() - 0.5) * 320, y, 12 + r() * 20, 8 + r() * 12, shade('27401f', k)); }
    // ель / кедр (x=768): плотный конус
    g.fillStyle = '#18291c'; g.beginPath(); g.moveTo(768, 10); g.lineTo(768 - 200, 480); g.lineTo(768 + 200, 480); g.closePath(); g.fill();
    for (let i = 0; i < 16; i++) { const t = i / 16, y = 30 + t * 440, w = 18 + t * 190; g.fillStyle = shade('203826', 0.75 + (1 - t) * 0.35 + r() * 0.2);
      g.beginPath(); g.moveTo(768, y - 34); for (let k = 0; k <= 10; k++) g.lineTo(768 - w + (2 * w) * k / 10, y + 30 + (k % 2 ? -10 : 5)); g.closePath(); g.fill(); }
    g.fillStyle = '#2f261f'; g.fillRect(762, 478, 12, 34);
    // берёза (x=1280): тёмнее и мягче, ствол почти скрыт кроной
    g.fillStyle = '#a9a398'; g.fillRect(1276, 250, 8, 262);
    blob(1280, 170, 175, 135, '#34532a');
    for (let i = 0; i < 220; i++) { const y = 50 + r() * 240; blob(1280 + (r() - 0.5) * 320, y, 12 + r() * 18, 10 + r() * 14, shade('4a7334', 0.7 + (1 - (y - 50) / 240) * 0.45 + r() * 0.2)); }
    billboardTex = new T.CanvasTexture(c); billboardTex.encoding = T.sRGBEncoding; billboardTex.anisotropy = 4;
    return billboardTex;
  }
  function billboardGeometry(kind) {
    const u0 = kind / 3, u1 = (kind + 1) / 3, w = kind === SPRUCE ? 0.55 : kind === PINE ? 0.66 : 0.62;
    const q = (ax) => { const g = new T.PlaneGeometry(w, 1); g.translate(0, 0.5, 0); if (ax) g.rotateY(Math.PI / 2);
      const uv = g.attributes.uv; for (let i = 0; i < uv.count; i++) uv.setX(i, u0 + uv.getX(i) * (u1 - u0)); return g; };
    return merge([{ g: q(0), c: new T.Color(1, 1, 1), up: true }, { g: q(1), c: new T.Color(1, 1, 1), up: true }]);
  }
  function forest(d) {
    const a = new Int16Array(b64(d.trees)), n = a.length / 4, grp = new T.Group(); grp.name = 'forest';
    const NEAR_R = MOBILE ? 220 : 380, FAR_R = MOBILE ? 1000 : 1900;   // дальше — полог леса в шейдере рельефа
    const near = [[], [], []], far = [[], [], []];
    for (let i = 0; i < n; i++) {
      const x = a[i * 4] / 10, z = a[i * 4 + 1] / 10, y = a[i * 4 + 2] / 10, k = (a[i * 4 + 3] >> 12) & 3, h = (a[i * 4 + 3] & 4095) / 10;
      const dist = Math.hypot(x, z);
      if (dist < NEAR_R) near[k].push([x, y, z, h, i]); else if (dist < FAR_R) far[k].push([x, y, z, h, i]);
    }
    const r = rng(5), col = new T.Color(), mtx = new T.Matrix4(), q = new T.Quaternion(), up = new T.Vector3(0, 1, 0);
    const geos = treeGeometries();
    const solid = new T.MeshStandardMaterial({ vertexColors: true, roughness: 0.92, metalness: 0, envMapIntensity: 0.4 });
    near.forEach((list, k) => {
      if (!list.length) return;
      const im = new T.InstancedMesh(geos[k], solid, list.length);
      list.forEach((t, i) => {
        const wf = 0.85 + r() * 0.3; q.setFromAxisAngle(up, r() * 6.283);
        mtx.compose(new T.Vector3(t[0], t[1] - 0.3, t[2]), q, new T.Vector3(t[3] * wf, t[3], t[3] * wf)); im.setMatrixAt(i, mtx);
        const b = 0.82 + r() * 0.3; col.setRGB(b * (0.95 + r() * 0.1), b, b * (0.92 + r() * 0.12)); im.setColorAt(i, col);
      });
      im.castShadow = true; im.receiveShadow = true; im.frustumCulled = false; grp.add(im);
    });
    const bbMat = new T.MeshStandardMaterial({ map: billboardTexture(), alphaTest: 0.5, side: T.DoubleSide, roughness: 0.95, metalness: 0, envMapIntensity: 0.35 });
    far.forEach((list, k) => {
      if (!list.length) return;
      const im = new T.InstancedMesh(billboardGeometry(k), bbMat, list.length);
      list.forEach((t, i) => {
        q.setFromAxisAngle(up, r() * 6.283);
        mtx.compose(new T.Vector3(t[0], t[1] - 0.3, t[2]), q, new T.Vector3(t[3], t[3], t[3])); im.setMatrixAt(i, mtx);
        const b = 0.62 + r() * 0.3; col.setRGB(b * 0.92, b, b * 0.86); im.setColorAt(i, col);
      });
      im.frustumCulled = false; grp.add(im);
    });
    return grp;
  }

  /* ---------- ангары (по фото: белые, синие ворота, синий цоколь и окантовка; северный — тёмный) ---------- */
  const BLUE = '#1f4fb5', BLUE_D = '#173f94';
  function wallCanvas(len, h, o) {
    const ppm = Math.min(24, 2048 / len), W = Math.round(len * ppm), Hh = Math.round(h * ppm), c = canvas(W, Hh), g = c.getContext('2d');
    const dark = o.kind === 'dark';
    g.fillStyle = dark ? '#3d434b' : '#eef1f4'; g.fillRect(0, 0, W, Hh);
    g.fillStyle = dark ? 'rgba(0,0,0,0.18)' : 'rgba(120,130,145,0.16)';                       // рифление профлиста
    for (let x = 0; x < W; x += ppm * 0.25) g.fillRect(x, 0, Math.max(1, ppm * 0.05), Hh);
    g.fillStyle = dark ? 'rgba(255,255,255,0.05)' : 'rgba(90,100,115,0.12)';                  // стыки панелей
    for (let y = Hh - ppm * 1.2; y > 0; y -= ppm * 1.2) g.fillRect(0, y, W, Math.max(1, ppm * 0.03));
    if (!dark) { g.fillStyle = BLUE; g.fillRect(0, Hh - ppm * 1.1, W, ppm * 1.1); g.fillRect(0, 0, W, ppm * 0.28); }   // цоколь и верхняя окантовка
    (o.doors || []).forEach(([f, dw, dh]) => {
      const x0 = (f * len - dw / 2) * ppm, y0 = Hh - dh * ppm, w = dw * ppm, hh = dh * ppm;
      g.fillStyle = BLUE_D; g.fillRect(x0 - ppm * 0.2, y0 - ppm * 0.2, w + ppm * 0.4, hh + ppm * 0.2);   // рама
      g.fillStyle = '#2352c2'; g.fillRect(x0, y0, w, hh);
      g.fillStyle = 'rgba(10,30,90,0.45)'; for (let y = y0 + ppm * 0.5; y < y0 + hh; y += ppm * 0.5) g.fillRect(x0, y, w, Math.max(1, ppm * 0.04));   // секции ворот
      g.fillStyle = '#d7dadd'; g.fillRect(x0 + w / 2 - ppm * 0.3, y0 - ppm * 0.9, ppm * 0.6, ppm * 0.25);        // светильник
    });
    if (o.windows) { g.fillStyle = '#2b3440'; for (let i = 0; i < 3; i++) g.fillRect((len - 3.5 - i * 1.6) * ppm, Hh - 3.6 * ppm, ppm * 1.1, ppm * 1.1); }
    return ctex(c);
  }
  function hangar(hd) {
    const grp = new T.Group(), x0 = hd.x[0], x1 = hd.x[1], z0 = hd.z[0], z1 = hd.z[1], h = hd.h, W = x1 - x0, L = z1 - z0;
    const cx = (x0 + x1) / 2, cz = (z0 + z1) / 2;
    const mk = (len, hh, o) => new T.MeshStandardMaterial({ map: wallCanvas(len, hh, Object.assign({ kind: hd.kind }, o || {})), roughness: 0.6, metalness: 0.05 });
    const wall = (len, hh, mat, x, z, ry) => { const m = new T.Mesh(new T.PlaneGeometry(len, hh), mat); m.position.set(x, hh / 2, z); m.rotation.y = ry; m.castShadow = true; m.receiveShadow = true; grp.add(m); };
    wall(L, h, mk(L, h, { doors: hd.doors, windows: hd.windows }), x1, cz, Math.PI / 2);   // фасад на восток (к перрону)
    wall(L, h, mk(L, h), x0, cz, -Math.PI / 2);
    wall(W, h, mk(W, h), cx, z1, 0);
    wall(W, h, mk(W, h), cx, z0, Math.PI);
    const roof = new T.Mesh(new T.BoxGeometry(W + 0.3, 0.35, L + 0.3), new T.MeshStandardMaterial({ color: lin(hd.kind === 'dark' ? 0x2e333a : 0xd3d7db), roughness: 0.7 }));
    roof.position.set(cx, h + 0.05, cz); roof.castShadow = true; grp.add(roof);
    if (hd.step) {   // ступенчатый аттик фасада (как на фото южного ангара)
      const sw = L * 0.46, sh = 2.2, mat = mk(sw, sh);
      const s = new T.Mesh(new T.BoxGeometry(1.2, sh, sw), [mat, mat, new T.MeshStandardMaterial({ color: lin(0xd3d7db) }), mat, mat, mat]);
      s.position.set(x1 - 0.6, h + sh / 2, cz); s.castShadow = true; grp.add(s);
    }
    return grp;
  }

  /* ---------- перрон, площадки, рулёжки, стоянка ---------- */
  function concreteCanvas(wm, hm, ppm, o) {
    const W = Math.round(wm * ppm), Hh = Math.round(hm * ppm), c = canvas(W, Hh), g = c.getContext('2d'), r = rng(o.seed || 1);
    g.fillStyle = o.base || '#b9b6ae'; g.fillRect(0, 0, W, Hh);
    for (let i = 0; i < W * Hh / 60; i++) { const a = r() * 0.07; g.fillStyle = r() > 0.5 ? 'rgba(255,255,255,' + a + ')' : 'rgba(0,0,0,' + a + ')'; g.fillRect(r() * W, r() * Hh, 1 + r() * 2, 1 + r() * 2); }
    for (let i = 0; i < wm * hm / 30; i++) { g.fillStyle = 'rgba(60,55,45,' + (0.03 + r() * 0.06) + ')'; g.beginPath(); g.ellipse(r() * W, r() * Hh, ppm * (0.5 + r() * 2.5), ppm * (0.4 + r() * 1.6), r() * 3, 0, 6.3); g.fill(); }
    const slab = o.slab || 5; g.strokeStyle = 'rgba(70,70,70,0.35)'; g.lineWidth = Math.max(1, ppm * 0.03);
    for (let x = 0; x <= wm; x += slab) { g.beginPath(); g.moveTo(x * ppm, 0); g.lineTo(x * ppm, Hh); g.stroke(); }
    for (let y = 0; y <= hm; y += slab) { g.beginPath(); g.moveTo(0, y * ppm); g.lineTo(W, y * ppm); g.stroke(); }
    return { c, g, W, Hh };
  }
  function ground(wm, hm, tex, x, z, y, ry) {
    const m = new T.Mesh(new T.PlaneGeometry(wm, hm), new T.MeshStandardMaterial({ map: tex, roughness: 0.9, metalness: 0, polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -2 }));
    m.rotation.x = -Math.PI / 2; m.rotation.z = ry || 0; m.position.set(x, y, z); m.receiveShadow = true; return m;
  }
  const YEL = '#f2c21b';
  function padMesh(p) {
    const ppm = p.kind === 'big' ? 40 : 28, { c, g, W } = concreteCanvas(p.s, p.s, ppm, { seed: 3 + p.s, slab: p.s / 4 });
    g.strokeStyle = YEL; g.lineWidth = 0.42 * ppm; g.beginPath(); g.arc(W / 2, W / 2, p.s * 0.37 * ppm, 0, Math.PI * 2); g.stroke();
    if (p.kind === 'H') {
      g.fillStyle = '#f4f4f0'; const u = p.s * ppm;
      g.fillRect(W / 2 - u * 0.13, W / 2 - u * 0.17, u * 0.05, u * 0.34); g.fillRect(W / 2 + u * 0.08, W / 2 - u * 0.17, u * 0.05, u * 0.34); g.fillRect(W / 2 - u * 0.13, W / 2 - u * 0.025, u * 0.26, u * 0.05);
    } else {
      g.strokeStyle = 'rgba(245,245,240,0.85)'; g.lineWidth = 0.18 * ppm;   // угловые метки
      [[0.08, 0.08, 1, 1], [0.92, 0.08, -1, 1], [0.08, 0.92, 1, -1], [0.92, 0.92, -1, -1]].forEach(([fx, fy, sx, sy]) => { g.beginPath(); g.moveTo(fx * W + sx * 1.6 * ppm, fy * W); g.lineTo(fx * W, fy * W); g.lineTo(fx * W, fy * W + sy * 1.6 * ppm); g.stroke(); });
    }
    return ground(p.s, p.s, ctex(c), p.x, p.z, 0.035);
  }
  function apronMesh(a) {
    const wm = a.x[1] - a.x[0], hm = a.z[1] - a.z[0], ppm = 11, { c, g, W, Hh } = concreteCanvas(wm, hm, ppm, { seed: 9, slab: 6 });
    g.strokeStyle = YEL; g.lineWidth = 0.22 * ppm;
    const cx = (wm * 0.42) * ppm;                                   // осевая линия руления
    g.beginPath(); g.moveTo(cx, 0); g.lineTo(cx, Hh); g.stroke();
    for (let zc = 16; zc < hm - 8; zc += 24) {                     // стоянки вертолётов — жёлтые круги
      g.beginPath(); g.arc(wm * 0.7 * ppm, zc * ppm, 5.6 * ppm, 0, Math.PI * 2); g.stroke();
      g.beginPath(); g.moveTo(cx, zc * ppm); g.lineTo(wm * 0.7 * ppm - 5.6 * ppm, zc * ppm); g.stroke();
    }
    return ground(wm, hm, ctex(c), (a.x[0] + a.x[1]) / 2, (a.z[0] + a.z[1]) / 2, 0.025);
  }
  function taxiway(t) {
    const [p0, p1, w] = t, dx = p1[0] - p0[0], dz = p1[1] - p0[1], L = Math.hypot(dx, dz);
    const { c } = concreteCanvas(w, Math.min(L, 60), 18, { seed: 21, slab: w, base: '#b4b1a8' });
    const tex = ctex(c, true); tex.repeat.set(1, L / Math.min(L, 60));
    const m = ground(w, L, tex, (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2, 0.02, 0);
    m.rotation.z = -Math.atan2(dx, -dz); return m;   // ось полосы — вдоль отрезка
  }
  function parking(p) {
    const wm = p.x[1] - p.x[0], hm = p.z[1] - p.z[0], ppm = 10, { c, g } = concreteCanvas(wm, hm, ppm, { seed: 5, slab: 100, base: '#5c5d5f' });
    g.strokeStyle = 'rgba(240,240,235,0.8)'; g.lineWidth = 0.12 * ppm;
    for (let z = 2; z < hm; z += 2.6) { g.beginPath(); g.moveTo(1 * ppm, z * ppm); g.lineTo(6 * ppm, z * ppm); g.stroke(); g.beginPath(); g.moveTo((wm - 6) * ppm, z * ppm); g.lineTo((wm - 1) * ppm, z * ppm); g.stroke(); }
    return ground(wm, hm, ctex(c), (p.x[0] + p.x[1]) / 2, (p.z[0] + p.z[1]) / 2, 0.02);
  }

  /* ---------- дома посёлка и мелкие постройки (одна геометрия) ---------- */
  function gable() {   // единичная призма: ось X (−0.5…0.5), основание y=0 шириной по Z 1, конёк y=1
    const P = [[-0.5, 0, -0.5], [0.5, 0, -0.5], [0.5, 0, 0.5], [-0.5, 0, 0.5], [-0.5, 1, 0], [0.5, 1, 0]];
    const F = [[0, 1, 5], [0, 5, 4], [3, 4, 5], [3, 5, 2], [0, 4, 3], [1, 2, 5]];   // скаты и фронтоны
    const pos = []; F.forEach(f => f.forEach(i => pos.push(...P[i])));
    const g = new T.BufferGeometry(); g.setAttribute('position', new T.Float32BufferAttribute(pos, 3));
    g.setAttribute('uv', new T.Float32BufferAttribute(new Array(pos.length / 3 * 2).fill(0), 2)); g.computeVertexNormals(); return g;
  }
  function houses(list, small) {
    const parts = [], r = rng(17), walls = ['#efe9df', '#e3d6c3', '#c9a57d', '#b98a5e', '#f2f2ee', '#d8d2c6'].map(lin);
    list.forEach(hh => {
      const wc = walls[Math.floor(r() * walls.length)], roofC = lin(hh.roof);
      parts.push({ g: new T.BoxGeometry(hh.w, hh.h, hh.l), m: M4(hh.x, hh.h / 2, hh.z, 1, 1, 1, hh.r), c: wc });
      // двускатная крыша: конёк вдоль длинной стороны дома
      parts.push({ g: gable(), m: M4(hh.x, hh.h, hh.z, hh.l * 1.06, hh.w * 0.34, hh.w * 1.12, hh.r + Math.PI / 2), c: roofC });
    });
    small.forEach(s => {
      const w = s.x[1] - s.x[0], l = s.z[1] - s.z[0];
      parts.push({ g: new T.BoxGeometry(w, s.h, l), m: M4((s.x[0] + s.x[1]) / 2, s.h / 2, (s.z[0] + s.z[1]) / 2, 1), c: walls[0] });
      parts.push({ g: new T.BoxGeometry(w + 0.4, 0.3, l + 0.4), m: M4((s.x[0] + s.x[1]) / 2, s.h + 0.15, (s.z[0] + s.z[1]) / 2, 1), c: lin(s.roof) });
    });
    const m = new T.Mesh(merge(parts), new T.MeshStandardMaterial({ vertexColors: true, roughness: 0.8, metalness: 0 }));
    m.castShadow = true; m.receiveShadow = true; return m;
  }
  function windsock(p) {
    const g = new T.Group();
    const pole = new T.Mesh(new T.CylinderGeometry(0.06, 0.08, 6, 8), new T.MeshStandardMaterial({ color: lin(0xd9dde1), roughness: 0.4, metalness: 0.5 }));
    pole.position.set(p[0], 3, p[1]); g.add(pole);
    const c = canvas(256, 64), x = c.getContext('2d');
    for (let i = 0; i < 5; i++) { x.fillStyle = i % 2 ? '#f5f5f2' : '#f06a1e'; x.fillRect(i * 51.2, 0, 51.2, 64); }
    const sock = new T.Mesh(new T.CylinderGeometry(0.42, 0.18, 2.6, 16, 1, true), new T.MeshStandardMaterial({ map: ctex(c), side: T.DoubleSide, roughness: 0.8 }));
    sock.rotation.z = Math.PI / 2 - 0.25; sock.rotation.y = 0.6; sock.position.set(p[0] + 1.1, 5.6, p[1] - 0.8); g.add(sock);
    return g;
  }

  /* ---------- сборка сцены ---------- */
  function build(d, tex) {
    const grp = new T.Group(); grp.name = 'Karasuk';
    const terr = terrain(d, tex); grp.add(terr);
    grp.add(apronMesh(d.apron));
    d.taxiways.forEach(t => grp.add(taxiway(t)));
    d.pads.forEach(p => grp.add(padMesh(p)));
    grp.add(parking(d.parking));
    d.hangars.forEach(h => grp.add(hangar(h)));
    grp.add(houses(d.houses || [], d.small));
    grp.add(cars(d.cars));
    grp.add(grassTufts(d));
    grp.add(windsock(d.windsock));
    grp.add(forest(d));
    const sk = sky(); grp.add(sk);
    grp.userData.tick = t => { terr.userData.tick(t); sk.userData.tick(t); };
    return grp;
  }

  /* ---------- небо: градиент под цвет дымки у горизонта и слой кучевых облаков ---------- */
  function sky() {
    const g = new T.Group(); g.name = 'sky';
    const geo = new T.SphereGeometry(12500, 32, 16), pa = geo.attributes.position, cols = [];
    const zen = lin(0x5f9ee0), mid = lin(0x9cc6ee), hor = lin(0xdcebff), c = new T.Color();
    for (let i = 0; i < pa.count; i++) { const h = Math.max(0, pa.getY(i) / 12500); if (h < 0.18) c.copy(hor).lerp(mid, h / 0.18); else c.copy(mid).lerp(zen, Math.min(1, (h - 0.18) / 0.6)); cols.push(c.r, c.g, c.b); }
    geo.setAttribute('color', new T.Float32BufferAttribute(cols, 3));
    const dome = new T.Mesh(geo, new T.MeshBasicMaterial({ vertexColors: true, side: T.BackSide, fog: false, depthWrite: false }));
    dome.renderOrder = -10; g.add(dome);
    // облака: бесшовный шум с альфой на горизонтальном «потолке» 2.6 км
    const S = 512, cv = canvas(S, S), x = cv.getContext('2d'), img = x.createImageData(S, S), r = rng(29);
    const lat = n => { const a = new Float32Array(n * n); for (let i = 0; i < a.length; i++) a[i] = r(); return a; };
    const Ls = [[lat(4), 4], [lat(8), 8], [lat(16), 16], [lat(32), 32]];
    const val = (a, n, u, v) => { const fx = u * n, fy = v * n, x0 = Math.floor(fx), y0 = Math.floor(fy), tx = fx - x0, ty = fy - y0, s = t => t * t * (3 - 2 * t), q = (i, j) => a[((j % n + n) % n) * n + ((i % n + n) % n)];
      const a0 = q(x0, y0) + (q(x0 + 1, y0) - q(x0, y0)) * s(tx), a1 = q(x0, y0 + 1) + (q(x0 + 1, y0 + 1) - q(x0, y0 + 1)) * s(tx); return a0 + (a1 - a0) * s(ty); };
    for (let yy = 0; yy < S; yy++) for (let xx = 0; xx < S; xx++) {
      const u = xx / S, v = yy / S; let n = 0, amp = 1, tot = 0; Ls.forEach(([a, k]) => { n += amp * val(a, k, u, v); tot += amp; amp *= 0.5; }); n /= tot;
      const al = Math.max(0, Math.min(1, (n - 0.52) / 0.2)), k = (yy * S + xx) * 4, sh = 205 + 50 * Math.min(1, (n - 0.5) / 0.3);
      img.data[k] = sh; img.data[k + 1] = sh + 3; img.data[k + 2] = sh + 8; img.data[k + 3] = al * 235;
    }
    x.putImageData(img, 0, 0);
    const t = new T.CanvasTexture(cv); t.wrapS = t.wrapT = T.RepeatWrapping; t.repeat.set(5, 5); t.encoding = T.sRGBEncoding;
    const clouds = new T.Mesh(new T.PlaneGeometry(40000, 40000), new T.MeshBasicMaterial({ map: t, transparent: true, depthWrite: false, fog: true, side: T.DoubleSide }));
    clouds.rotation.x = Math.PI / 2; clouds.position.y = 2600; clouds.renderOrder = -5; g.add(clouds);
    g.userData.tick = tt => { t.offset.set(tt * 0.0012, tt * 0.0005); };
    return g;
  }

  /* временная «земля», пока грузятся данные сцены */
  function placeholder() {
    const g = new T.Group();
    const m = new T.Mesh(new T.CircleGeometry(6000, 48), new T.MeshStandardMaterial({ color: lin(0x6f8f4a), roughness: 1 }));
    m.rotation.x = -Math.PI / 2; m.receiveShadow = true; g.add(m);
    return g;
  }

  function load(viewer, base, ver) {
    loadData(base, ver).then(d => {
      if (!d) { viewer.setScene && viewer.setScene(null); return; }
      const v = ver ? '?v=' + ver : '';
      return Promise.all([loadTex(base + (MOBILE ? d.tex.sat2k : d.tex.sat) + v, true), loadTex(base + d.tex.near + v, false), loadTex(base + d.tex.water + v, false)])
        .then(([sat, near, water]) => { if (!sat || !near || !water) { viewer.setScene(null); return; } viewer.setScene(build(d, { sat, near, water })); });
    }).catch(e => { console.warn('Карасук:', e); viewer.setScene && viewer.setScene(null); });
  }

  H.scenes = H.scenes || {};
  H.scenes.karasuk = { load, placeholder, credit: 'Рельеф: SRTM (AWS Terrain Tiles); снимок: Sentinel-2 cloudless 2016 © EOX, CC BY 4.0' };
})(window);
