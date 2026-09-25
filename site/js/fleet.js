/* АлтайАвиа — подключение 3D-сцен (v2): только на главной (герой + парк) и на страницах бортов.
   Модель можно только вращать (зум отключён). Сцена создаётся, когда блок виден; без WebGL — статичный рендер.
   Если есть models/<key>.js (компактная модель, см. build/import/glb2js.py) — загружается она вместо процедурной. */
(function () {
  'use strict';
  const HAS_WEBGL = (function () { try { const c = document.createElement('canvas'); return !!(window.WebGLRenderingContext && (c.getContext('webgl') || c.getContext('experimental-webgl'))); } catch (e) { return false; } })();
  const MOBILE = window.matchMedia('(max-width: 640px)').matches;
  const REDUCED = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const ROOT = document.documentElement.dataset.root || '';
  const FALLBACK = { as350: 'img/3d/as350.png', mi8amt: 'img/3d/mi8amt.png', mi171: 'img/3d/mi171.png' };
  const GLB = {}; // GLB[key] = true, если для модели есть файл models/<key>.js (список — в <html data-models>)
  // эталон для истинного масштаба (data-true-scale="1"): габариты Ми-8 с винтами, м — AS350 в том же кадре почти вдвое меньше
  const REF = { length: 25.37, height: 6.16, width: 20.1, reach: 16.2 };
  function scaleBar(el) {
    const v = el._viewer, bar = el.parentElement && el.parentElement.querySelector('.scale-bar'); if (!v || !bar) return;
    const px = 10 / (2 * v.orbit.dist * Math.tan(v.camera.fov * Math.PI / 360)) * el.clientHeight;   // 10 м на глубине цели орбиты
    bar.style.setProperty('--scale-px', Math.round(px) + 'px');
  }

  function fallback(el, key) {
    el.innerHTML = ''; const d = document.createElement('div'); d.className = 'viewer-fallback';
    const img = document.createElement('img'); img.src = ROOT + (FALLBACK[key] || FALLBACK.as350); img.alt = (window.Heli3D && Heli3D.MODELS[key] ? Heli3D.MODELS[key].name : 'Вертолёт');
    d.appendChild(img); el.appendChild(d);
  }

  function initViewer(el) {
    const key = el.dataset.model || 'as350';
    if (!HAS_WEBGL || !window.Heli3D || !window.THREE) { fallback(el, key); return null; }
    const v = new Heli3D.Viewer(el, {
      transparent: true,
      helipad: el.dataset.helipad === '1',
      rotorState: el.dataset.rotor || 'idle',
      autoRotate: el.dataset.auto !== '0',
      autoSpeed: parseFloat(el.dataset.speed || '0.1'),
      hover: el.dataset.hover === '1',
      theta: el.dataset.theta ? parseFloat(el.dataset.theta) : undefined,
      phi: el.dataset.phi ? parseFloat(el.dataset.phi) : undefined,
      maxDpr: MOBILE ? 1.5 : 2,
      fov: el.dataset.fov ? parseFloat(el.dataset.fov) : 30,
      viewOffsetX: el.dataset.offset ? parseFloat(el.dataset.offset) : 0.5,
      shadowOpacity: el.dataset.helipad === '1' ? 0 : 0.16,
      scene: el.dataset.helipad === '1' ? 'karasuk' : null,              // площадка «Карасук»: рельеф, снимок, ангары
      sceneBase: ROOT + 'scene/', sceneVer: document.documentElement.dataset.v || ''
    });
    v.load = (k) => {
      const M = Heli3D.MODELS[k]; if (!M) return;
      const view = Object.assign({}, M.view, el.dataset.fit ? { fit: el.dataset.fit === 'auto' ? 'auto' : parseFloat(el.dataset.fit) } : {}, el.dataset.ty ? { ty: parseFloat(el.dataset.ty) } : {}, el.dataset.tyRel ? { tyRel: parseFloat(el.dataset.tyRel) } : {}, el.dataset.trueScale === '1' ? { fitRef: REF } : {}, el.dataset.margin ? { margin: parseFloat(el.dataset.margin) } : {});   // data-ty-rel — доля высоты модели; data-true-scale — общий масштаб для всех бортов
      const done = () => { el.dataset.model = k; el.dispatchEvent(new CustomEvent('modelchange', { detail: k })); setTimeout(() => scaleBar(el), 50); };
      if (GLB[k] && v.loadPacked) {
        // компактная модель как обычный <script src> + текстура <img>: без fetch/wasm — работает и в песочнице артефакта
        v.loadPacked(k, ROOT + 'models/' + k + '.js?v=' + (document.documentElement.dataset.v || '1'), ROOT + 'models/', view, err => { if (err) { console.warn('3D:', err.message); v.setModel(M.build(), view); } done(); });
      } else { v.setModel(M.build(), view); done(); }
    };
    v.load(key);
    if ('IntersectionObserver' in window) new IntersectionObserver(es => es.forEach(e => v.setVisible(e.isIntersecting)), { threshold: 0 }).observe(el);
    el._viewer = v;
    window.addEventListener('resize', () => scaleBar(el));
    if (el.dataset.flyin === '1' && !REDUCED) { const go = () => setTimeout(() => v.flyIn(3.4), 150); if (window.AltayUI) AltayUI.onReady(go); else go(); }
    return v;
  }

  /* список внешних моделей задаётся генератором: <html data-models="as350,mi171"> */
  function probeModels(keys, cb) {
    (document.documentElement.dataset.models || '').split(',').forEach(k => { if (k) GLB[k] = true; });
    cb();
  }

  function boot() {
    const els = document.querySelectorAll('.viewer[data-model]');
    if (!els.length) return;
    const keys = Array.from(new Set(Array.from(els).map(e => e.dataset.model)));
    probeModels(keys, () => {
      if ('IntersectionObserver' in window) {
        const io = new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting) { io.unobserve(e.target); initViewer(e.target); } }), { rootMargin: '150px 0px' });
        els.forEach(el => io.observe(el));
      } else els.forEach(initViewer);
    });

    /* Переключатели моделей с «шторкой ангара» */
    document.querySelectorAll('[data-fleet-tab]').forEach(btn => btn.addEventListener('click', () => {
      const target = document.querySelector(btn.dataset.fleetTarget); if (!target) return;
      const k = btn.dataset.fleetTab; if (target.dataset.model === k) return;
      document.querySelectorAll('[data-fleet-target="' + btn.dataset.fleetTarget + '"]').forEach(b => b.setAttribute('aria-selected', b === btn ? 'true' : 'false'));
      const swap = () => { if (target._viewer) target._viewer.load(k); else { target.dataset.model = k; const fb = target.querySelector('.viewer-fallback img'); if (fb) fb.src = ROOT + FALLBACK[k]; } document.querySelectorAll('[data-spec]').forEach(s => { s.hidden = s.dataset.spec !== k; }); };
      const shutter = target.parentElement.querySelector('.shutter');
      if (shutter && !REDUCED) { shutter.classList.remove('is-run'); void shutter.offsetWidth; shutter.classList.add('is-run'); setTimeout(swap, 400); } else swap();
    }));
    document.querySelectorAll('[data-rotor]').forEach(btn => btn.addEventListener('click', () => {
      const target = document.querySelector(btn.dataset.target); if (!target || !target._viewer) return;
      target._viewer.setRotorState(btn.dataset.rotor);
      document.querySelectorAll('[data-rotor][data-target="' + btn.dataset.target + '"]').forEach(b => b.setAttribute('aria-pressed', b === btn ? 'true' : 'false'));
    }));
    document.querySelectorAll('[data-autorotate]').forEach(btn => btn.addEventListener('click', () => {
      const target = document.querySelector(btn.dataset.target); if (!target || !target._viewer) return;
      const v = target._viewer; v.auto = !v.auto; v.idleTimer = 99; btn.setAttribute('aria-pressed', v.auto ? 'true' : 'false');
    }));
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
  window.AltayFleet = { initViewer, HAS_WEBGL };
})();
