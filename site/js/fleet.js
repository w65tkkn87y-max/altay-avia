/* АлтайАвиа — подключение 3D-сцен (v3): главная (герой + парк) и страницы бортов.
   Модель можно только вращать (зум отключён). Сцена создаётся, когда блок виден; без WebGL — статичный рендер.
   Смена борта в «Парке»: текущий взлетает и уходит из кадра, новый заходит и садится на площадку. Остальные борта
   догружаются заранее (на компьютере — в простое, на телефоне — когда посетитель задержался у сцены), построенные
   модели кэшируются — повторное переключение мгновенное. На телефонах — облегчённые текстуры 2048 px. */
(function () {
  'use strict';
  const HAS_WEBGL = (function () { try { const c = document.createElement('canvas'); return !!(window.WebGLRenderingContext && (c.getContext('webgl') || c.getContext('experimental-webgl'))); } catch (e) { return false; } })();
  const MOBILE = window.matchMedia('(max-width: 640px)').matches;
  const SMALL = window.matchMedia('(max-width: 820px), (pointer: coarse)').matches;
  const REDUCED = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const CONN = navigator.connection || {};
  const SAVE = !!CONN.saveData || /(^|-)2g$/.test(CONN.effectiveType || '');
  const ROOT = document.documentElement.dataset.root || '';
  const VER = document.documentElement.dataset.v || '1';
  const FALLBACK = { as350: 'img/3d/as350.png', mi8amt: 'img/3d/mi8amt.png', mi171: 'img/3d/mi171.png' };
  const GLB = {};   // GLB[key] = true, если для модели есть файл models/<key>.js (список — в <html data-models>)
  (document.documentElement.dataset.models || '').split(',').forEach(k => { if (k) GLB[k] = true; });
  // эталон для истинного масштаба (data-true-scale="1"): габариты Ми-8 с винтами, м — AS350 в том же кадре почти вдвое меньше
  const REF = { length: 25.37, height: 6.16, width: 20.1, reach: 16.2 };
  const modelUrl = k => ROOT + 'models/' + k + '.js?v=' + VER;
  const idle = window.requestIdleCallback || (fn => setTimeout(fn, 600));

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
  function viewFor(el, k) {
    const M = Heli3D.MODELS[k], d = el.dataset;
    return Object.assign({}, M.view, d.fit ? { fit: d.fit === 'auto' ? 'auto' : parseFloat(d.fit) } : {}, d.ty ? { ty: parseFloat(d.ty) } : {},
      d.tyRel ? { tyRel: parseFloat(d.tyRel) } : {}, d.trueScale === '1' ? { fitRef: REF } : {}, d.margin ? { margin: parseFloat(d.margin) } : {},
      d.trueScale === '1' && MOBILE ? { margin: 0.8 } : {});   // на телефоне кадр плотнее — борт крупнее
  }
  function stageOf(el) { return el.closest('.fleet-stage, .hero-stage') || el.parentElement; }
  function setLoading(el, on) {
    const st = stageOf(el); if (!st) return;
    let l = st.querySelector('.stage-loader');
    if (!l && on) { l = document.createElement('div'); l.className = 'stage-loader'; l.setAttribute('role', 'status'); l.innerHTML = '<i></i><span>Борт заходит на посадку…</span>'; st.appendChild(l); }
    st.classList.toggle('is-loading', !!on);
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
      maxDpr: MOBILE ? 1.5 : SMALL ? 1.75 : 2,
      lowTex: SMALL || SAVE,
      fov: el.dataset.fov ? parseFloat(el.dataset.fov) : 30,
      viewOffsetX: el.dataset.offset ? parseFloat(el.dataset.offset) : 0.5,
      shadowOpacity: el.dataset.helipad === '1' ? 0 : 0.16,
      scene: el.dataset.helipad === '1' ? 'karasuk' : null,              // площадка «Карасук»: рельеф, снимок, ангары
      sceneBase: ROOT + 'scene/', sceneVer: VER
    });
    const announce = k => { el.dataset.model = k; el.dispatchEvent(new CustomEvent('modelchange', { detail: k })); setTimeout(() => scaleBar(el), 50); };
    const getModel = k => cb => {
      if (GLB[k] && v.getPacked) v.getPacked(k, modelUrl(k), ROOT + 'models/', (err, m) => { if (err) { console.warn('3D:', err.message); cb(null, Heli3D.MODELS[k].build()); } else cb(null, m); });
      else cb(null, Heli3D.MODELS[k].build());
    };
    /* первый показ — сразу; смена — с анимацией взлёта/посадки */
    v.load = (k, animate) => {
      if (!Heli3D.MODELS[k]) return;
      if (animate && v.model && !REDUCED) {
        announce(k);
        v.swapTo(getModel(k), viewFor(el, k), () => { setLoading(el, false); scaleBar(el); }, on => setLoading(el, on));
      } else getModel(k)((err, m) => { v.setModel(m, viewFor(el, k)); announce(k); if (!v._primed) { v._primed = true; prefetchOthers(el, v, k); } });
    };
    v.load(key);
    if ('IntersectionObserver' in window) new IntersectionObserver(es => es.forEach(e => v.setVisible(e.isIntersecting)), { threshold: 0 }).observe(el);
    el._viewer = v;
    window.addEventListener('resize', () => scaleBar(el));
    if (el.dataset.flyin === '1' && !REDUCED) { const go = () => setTimeout(() => v.flyIn(3.4), 150); if (window.AltayUI) AltayUI.onReady(go); else go(); }
    return v;
  }

  /* Упреждающая загрузка остальных бортов для сцены с вкладками */
  function prefetchOthers(el, v, first) {
    if (!el.id) return;
    const tabs = Array.from(document.querySelectorAll('[data-fleet-target="#' + el.id + '"]'));
    if (!tabs.length || SAVE) return;
    const keys = tabs.map(t => t.dataset.fleetTab).filter(k => k !== first && GLB[k]);
    const run = () => {
      const next = keys.shift(); if (!next) return;
      v.getPacked(next, modelUrl(next), ROOT + 'models/', (err, m) => { if (!err) idle(() => { v.warm(m); idle(run); }); else run(); });
    };
    if (!SMALL) { idle(run); return; }
    // телефон: только если посетитель задержался у сцены (2 с в кадре) или коснулся вкладки
    let timer = null, started = false;
    const start = () => { if (started) return; started = true; clearTimeout(timer); run(); };
    if ('IntersectionObserver' in window) new IntersectionObserver(es => es.forEach(e => { clearTimeout(timer); if (e.isIntersecting) timer = setTimeout(start, 2000); }), { threshold: 0.5 }).observe(el);
    tabs.forEach(t => { t.addEventListener('pointerdown', start, { once: true }); t.addEventListener('focus', start, { once: true }); });
  }

  function boot() {
    const els = document.querySelectorAll('.viewer[data-model]');
    if (!els.length) return;
    if ('IntersectionObserver' in window) {
      const io = new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting) { io.unobserve(e.target); initViewer(e.target); } }), { rootMargin: '300px 0px' });
      els.forEach(el => io.observe(el));
    } else els.forEach(initViewer);

    /* Вкладки бортов: характеристики меняются сразу, 3D — взлёт текущего и посадка выбранного */
    document.querySelectorAll('[data-fleet-tab]').forEach(btn => btn.addEventListener('click', () => {
      const target = document.querySelector(btn.dataset.fleetTarget); if (!target) return;
      const k = btn.dataset.fleetTab; if (target.dataset.model === k) return;
      document.querySelectorAll('[data-fleet-target="' + btn.dataset.fleetTarget + '"]').forEach(b => b.setAttribute('aria-selected', b === btn ? 'true' : 'false'));
      document.querySelectorAll('[data-spec]').forEach(s => { s.hidden = s.dataset.spec !== k; });
      if (target._viewer) target._viewer.load(k, true);
      else { target.dataset.model = k; const fb = target.querySelector('.viewer-fallback img'); if (fb) fb.src = ROOT + FALLBACK[k]; }
    }));
    document.querySelectorAll('[data-rotor]').forEach(btn => btn.addEventListener('click', () => {
      const target = document.querySelector(btn.dataset.target); if (!target || !target._viewer) return;
      const v = target._viewer;
      if (v.swap) v.swap.prevRotor = btn.dataset.rotor; else v.setRotorState(btn.dataset.rotor);   // во время смены борта — применится после посадки
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
