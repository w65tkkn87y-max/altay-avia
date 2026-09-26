/* АлтайАвиа — поведение и анимации страниц (v3 «Небо Алтая»)
   Прелоадер «набор высоты», переход «диск винта», шапка, меню, местное время, высотомер прокрутки,
   взлёт героя, «время в пути» (иллюминатор), горизонтальная лента направлений, бегущая строка, параллакс,
   слова из-под маски, шторки картинок, счётчики, табло split-flap, наклон карточек, магнитные кнопки, курсор,
   лайтбокс, формы, версия для слабовидящих. Всё уважает prefers-reduced-motion. */
(function () {
  'use strict';
  const D = document, W = window, html = D.documentElement;
  html.classList.add('js');
  const REDUCED = W.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const FINE = W.matchMedia('(hover: hover) and (pointer: fine)').matches;
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));

  /* Конфигурация отправки форм: endpoint — URL обработчика (POST JSON). Пока пуст — письмо через mailto. */
  const CONFIG = { formEndpoint: '', mailTo: 'info@altay-avia.ru' };
  const ss = { get: k => { try { return sessionStorage.getItem(k); } catch (e) { return null; } }, set: (k, v) => { try { sessionStorage.setItem(k, v); } catch (e) { } } };

  /* ---------- Прелоадер (первый заход за сессию) и переход «диск винта» ---------- */
  const pre = D.querySelector('.preloader'), warp = D.querySelector('.warp');
  const firstVisit = !ss.get('aa-seen'); ss.set('aa-seen', '1');
  const viaLink = ss.get('aa-nav') === '1'; ss.set('aa-nav', '0');
  let ready = false; const readyQueue = [];
  const onReady = fn => ready ? fn() : readyQueue.push(fn);
  function finishIntro() { if (ready) return; ready = true; html.classList.add('is-ready'); readyQueue.splice(0).forEach(fn => fn()); }
  const warpScale = (x, y) => Math.ceil(2 * Math.hypot(Math.max(x, W.innerWidth - x), Math.max(y, W.innerHeight - y)) / 10) + 2;
  if (pre && firstVisit && !REDUCED) {
    const num = pre.querySelector('[data-pl-num]'), t0 = performance.now(), T = 1700;
    const tick = now => { const k = clamp((now - t0) / T, 0, 1), e = 1 - Math.pow(1 - k, 3); if (num) num.textContent = Math.round(375 * e); if (k < 1) requestAnimationFrame(tick); };
    requestAnimationFrame(tick);
    setTimeout(() => { pre.classList.add('is-done'); setTimeout(finishIntro, 250); }, 1900);
  } else {
    if (pre) pre.classList.add('is-done');
    if (warp && viaLink && !REDUCED) {
      warp.style.setProperty('--x', '50%'); warp.style.setProperty('--y', '50%'); warp.style.setProperty('--s', warpScale(W.innerWidth / 2, W.innerHeight / 2));
      warp.classList.add('is-cover');
      requestAnimationFrame(() => requestAnimationFrame(() => { warp.classList.remove('is-cover'); warp.classList.add('is-out'); setTimeout(finishIntro, 280); }));
    } else finishIntro();
  }
  if (warp && !REDUCED) {
    D.addEventListener('click', e => {
      const a = e.target.closest('a[href]'); if (!a || e.defaultPrevented) return;
      if (e.metaKey || e.ctrlKey || e.shiftKey || e.button > 0 || a.target === '_blank' || a.hasAttribute('download') || a.dataset.lightbox) return;
      const url = new URL(a.href, location.href);
      if (url.origin !== location.origin) return;
      if (!/\.html$/.test(url.pathname) && !/\/$/.test(url.pathname)) return;
      if (url.pathname === location.pathname && url.hash) return;
      e.preventDefault(); ss.set('aa-nav', '1');
      const x = e.clientX || W.innerWidth / 2, y = e.clientY || W.innerHeight / 2;
      warp.classList.remove('is-out', 'is-cover'); warp.style.setProperty('--x', x + 'px'); warp.style.setProperty('--y', y + 'px'); warp.style.setProperty('--s', warpScale(x, y));
      void warp.offsetWidth; warp.classList.add('is-in');
      setTimeout(() => { location.href = url.href; }, 700);
    });
    W.addEventListener('pageshow', e => { if (e.persisted) warp.classList.remove('is-in', 'is-cover'); });
  }

  /* ---------- Шапка: состояние при прокрутке, скрытие вниз / показ вверх, меню ---------- */
  const header = D.querySelector('.site-header'), burger = D.querySelector('.burger');
  const setMenu = open => { if (!header) return; header.classList.toggle('nav-open', open); D.body.classList.toggle('menu-lock', open); if (burger) { burger.setAttribute('aria-expanded', open ? 'true' : 'false'); burger.setAttribute('aria-label', open ? 'Закрыть меню' : 'Открыть меню'); } };
  if (burger) burger.addEventListener('click', () => setMenu(!header.classList.contains('nav-open')));
  D.addEventListener('keydown', e => { if (e.key === 'Escape' && header && header.classList.contains('nav-open')) setMenu(false); });
  D.querySelectorAll('.menu-list a').forEach(a => a.addEventListener('click', () => setMenu(false)));
  const here = location.pathname.replace(/\/index\.html$/, '/');
  D.querySelectorAll('.nav a, .footer-grid a').forEach(a => {
    const path = new URL(a.getAttribute('href') || '', location.href).pathname, sec = a.dataset.section;
    if (path === here || (sec && (here.indexOf('/' + sec + '.html') >= 0 || here.indexOf('/' + sec + '/') >= 0))) a.classList.add('is-active');
  });
  D.querySelectorAll('.nav a span').forEach(s => s.setAttribute('data-t', s.textContent));
  const nav = D.querySelector('.nav');
  if (nav) {
    const glider = D.createElement('span'); glider.className = 'nav-glider'; nav.appendChild(glider);
    const moveTo = a => { if (!a) { glider.style.opacity = '0'; return; } const r = a.getBoundingClientRect(), n = nav.getBoundingClientRect(); glider.style.left = (r.left - n.left) + 'px'; glider.style.width = r.width + 'px'; glider.style.opacity = '1'; };
    const active = nav.querySelector('a.is-active');
    nav.querySelectorAll('a').forEach(a => { a.addEventListener('mouseenter', () => moveTo(a)); a.addEventListener('focus', () => moveTo(a)); });
    nav.addEventListener('mouseleave', () => moveTo(active));
    if (D.fonts && D.fonts.ready) D.fonts.ready.then(() => moveTo(active)); else moveTo(active);
    W.addEventListener('resize', () => moveTo(active));
  }

  /* ---------- Местное время на Алтае (UTC+7) ---------- */
  const clocks = D.querySelectorAll('[data-clock]');
  if (clocks.length) {
    let fmt = null; try { fmt = new Intl.DateTimeFormat('ru-RU', { timeZone: 'Asia/Barnaul', hour: '2-digit', minute: '2-digit' }); } catch (e) { }
    const upd = () => { let s; if (fmt) s = fmt.format(new Date()); else { const d = new Date(Date.now() + 7 * 3600e3); s = String(d.getUTCHours()).padStart(2, '0') + ':' + String(d.getUTCMinutes()).padStart(2, '0'); } clocks.forEach(c => { c.textContent = s; }); };
    upd(); setInterval(upd, 15000);
  }

  /* ---------- Заголовки: посимвольно (обложки) и по словам из-под маски ---------- */
  D.querySelectorAll('.h-split').forEach(el => {
    if (REDUCED) return;
    const text = el.textContent; el.textContent = ''; el.setAttribute('aria-label', text); let i = 0;
    text.split(' ').forEach((word, wi, arr) => {
      const w = D.createElement('span'); w.style.display = 'inline-block'; w.style.maxWidth = '100%'; w.setAttribute('aria-hidden', 'true');
      word.split('').forEach(ch => { const s = D.createElement('span'); s.className = 'ch'; s.textContent = ch; s.style.animationDelay = (250 + i++ * 24) + 'ms'; w.appendChild(s); });
      el.appendChild(w); if (wi < arr.length - 1) el.appendChild(D.createTextNode(' '));
    });
  });
  D.querySelectorAll('.section-head h2, .site-card h2, .gallery-block h2, .prose > h2, .callout h3').forEach(h => { if (!h.querySelector('*')) h.classList.add('split-words'); });
  D.querySelectorAll('.split-words').forEach(el => {
    const text = el.textContent.trim(); el.setAttribute('aria-label', text); el.textContent = '';
    text.split(/\s+/).forEach((word, i, arr) => {
      const o = D.createElement('span'); o.className = 'sw'; o.setAttribute('aria-hidden', 'true'); o.style.setProperty('--i', i);
      const inner = D.createElement('span'); inner.textContent = word; o.appendChild(inner); el.appendChild(o);
      if (i < arr.length - 1) el.appendChild(D.createTextNode(' '));
    });
  });

  /* ---------- Появление при прокрутке, счётчики, табло ---------- */
  const io = 'IntersectionObserver' in W ? new IntersectionObserver(es => es.forEach(e => {
    if (!e.isIntersecting) return; const el = e.target; el.classList.add('is-in'); io.unobserve(el);
    if (el.hasAttribute('data-count')) countUp(el);
    if (el.classList.contains('board')) flapBoard(el);
  }), { rootMargin: '0px 0px -10% 0px', threshold: 0.08 }) : null;
  D.querySelectorAll('.reveal, .stagger, .img-reveal, .split-words, .eyebrow, [data-count], .board').forEach(el => {
    if (!io) { el.classList.add('is-in'); if (el.hasAttribute('data-count')) el.textContent = el.dataset.count + (el.dataset.suffix || ''); return; }
    io.observe(el);
  });
  function countUp(el) {
    const target = parseFloat(el.dataset.count), suffix = el.dataset.suffix || '', dur = 1900, t0 = performance.now();
    const fmt = n => String(Math.round(n)).replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
    const put = n => { el.textContent = fmt(n); if (suffix) { const sm = D.createElement('small'); sm.textContent = suffix.trim(); el.appendChild(sm); } };
    if (REDUCED) { put(target); return; }
    const tick = now => { const k = Math.min(1, (now - t0) / dur), e = 1 - Math.pow(1 - k, 4); put(target * e); if (k < 1) requestAnimationFrame(tick); };
    requestAnimationFrame(tick);
  }
  const ALPHA = ' АБВГДЕЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-.,()…';
  function flapBoard(board) {
    board.querySelectorAll('[data-flap]').forEach((cell, ri) => {
      const text = (cell.dataset.flap || '').toUpperCase(); cell.innerHTML = ''; cell.setAttribute('aria-label', cell.dataset.flap);
      if (W.innerWidth < 640) { cell.classList.add('flap-plain'); cell.textContent = text; if (!REDUCED) cell.animate([{ opacity: 0, transform: 'translateY(8px)' }, { opacity: 1, transform: 'none' }], { duration: 600, delay: ri * 80, fill: 'backwards', easing: 'cubic-bezier(.22,.8,.2,1)' }); return; }   // на телефоне строки короче — без «перекидных» ячеек
      text.split('').forEach((ch, ci) => {
        const c = D.createElement('span'); c.className = 'c' + (ch === ' ' ? ' space' : ''); c.textContent = ch === ' ' ? '' : ch; c.setAttribute('aria-hidden', 'true'); cell.appendChild(c);
        if (REDUCED || ch === ' ') return;
        const target = ALPHA.indexOf(ch); if (target < 0) return; let idx = Math.max(0, target - 6 - Math.floor(Math.random() * 8));
        c.textContent = ALPHA[idx];
        const step = () => { idx++; if (idx > target) { c.textContent = ch; return; } c.textContent = ALPHA[idx]; setTimeout(step, 36); };
        setTimeout(step, 140 + ri * 90 + ci * 14);
      });
    });
  }

  /* ---------- Слоганы героя: смена по кругу с полоской-таймером ---------- */
  const slogWrap = D.querySelector('.slogans'), slogans = slogWrap ? slogWrap.querySelectorAll('li') : [];
  if (slogans.length > 1 && !REDUCED) {
    let i = 0;
    const run = () => { slogWrap.classList.remove('is-run'); void slogWrap.offsetWidth; slogWrap.classList.add('is-run'); };
    onReady(() => { run(); setInterval(() => {
      const cur = slogans[i]; cur.classList.remove('is-live'); cur.classList.add('is-gone'); setTimeout(() => cur.classList.remove('is-gone'), 700);
      i = (i + 1) % slogans.length; slogans[i].classList.add('is-live'); run();
    }, 4200); });
  }

  /* ---------- Прокрутка: высотомер, взлёт героя, параллакс, «время в пути», лента направлений, бегущая строка ---------- */
  const prog = D.querySelector('.scroll-progress i');
  const alt = D.querySelector('.altimeter'), altNum = alt && alt.querySelector('[data-alt]');
  const hero = D.querySelector('[data-hero]'), heroCopy = D.querySelector('.hero-copy'), hudAlt = D.querySelector('[data-hud-alt]'), hudHdg = D.querySelector('[data-hud-hdg]');
  const heroStage = D.querySelector('.hero-stage'); if (heroStage) heroStage.setAttribute('data-cursor', 'Вращать');
  const plx = Array.from(D.querySelectorAll('[data-parallax]')), plxX = Array.from(D.querySelectorAll('[data-parallax-x]'));
  const legs = D.querySelector('[data-legs]'), legItems = legs ? legs.querySelectorAll('.leg') : [], ports = legs ? legs.querySelectorAll('[data-port]') : [];
  const hs = D.querySelector('[data-hscroll]'), htrack = hs && hs.querySelector('[data-htrack]'), hprog = hs && hs.querySelector('[data-hprogress]');
  const useH = hs && htrack && !REDUCED && W.innerWidth > 900;
  if (hs && !useH) hs.classList.add('no-hscroll');
  const mq = D.querySelector('[data-marquee]');
  let lastY = W.scrollY, vel = 0, mqX = 0, legIdx = 0, hidden = false;
  const altOf = p => Math.round(375 + p * (4506 - 375));
  function sizeH() {
    if (!useH) return;
    const extra = Math.max(0, htrack.scrollWidth - W.innerWidth);
    hs.style.height = (W.innerHeight + extra) + 'px'; hs._extra = extra;
  }
  function onScroll() {
    const y = W.scrollY, vh = W.innerHeight, dh = Math.max(1, D.documentElement.scrollHeight - vh), p = clamp(y / dh, 0, 1);
    vel = y - lastY;
    // шапка
    if (header && !header.classList.contains('nav-open')) {
      header.classList.toggle('is-scrolled', y > 40);
      const hide = vel > 4 && y > 500; const show = vel < -4 || y < 300;
      if (hide && !hidden) { header.classList.add('is-hidden'); hidden = true; } else if (show && hidden) { header.classList.remove('is-hidden'); hidden = false; }
    }
    lastY = y;
    // высотомер: страница — полёт с «Карасука» (375 м) к Белухе (4506 м)
    if (prog) prog.style.transform = 'scaleX(' + p.toFixed(4) + ')';
    if (alt) { alt.style.setProperty('--p', p.toFixed(4)); if (altNum) altNum.textContent = altOf(p); alt.classList.toggle('is-on', y > 200); }
    if (hudAlt) hudAlt.textContent = altOf(p);
    // герой: вертолёт набирает высоту и уходит вправо-вверх, текст уплывает
    if (hero) {
      const r = hero.getBoundingClientRect(), k = clamp(-r.top / Math.max(1, r.height * 0.85), 0, 1);
      const v = D.querySelector('.hero-stage .viewer'); if (v && v._viewer) v._viewer.setScroll(k);
      if (heroCopy && !REDUCED) { heroCopy.style.transform = 'translate3d(0,' + (k * -80) + 'px,0)'; heroCopy.style.opacity = String(1 - k * 1.2); }
    }
    if (!REDUCED) {
      plx.forEach(el => { const r = el.getBoundingClientRect(); if (r.bottom < -200 || r.top > vh + 200) return; const f = parseFloat(el.dataset.parallax) || 0.15; el.style.transform = 'translate3d(0,' + ((r.top + r.height / 2 - vh / 2) * -f).toFixed(1) + 'px,0)'; });
      plxX.forEach(el => { const r = el.getBoundingClientRect(); if (r.bottom < 0 || r.top > vh) return; const f = parseFloat(el.dataset.parallaxX) || 0.1; el.style.transform = 'translate3d(' + ((r.top - vh) * f).toFixed(1) + 'px,0,0)'; });
    }
    // «время в пути»: закреплённый экран, три отрезка маршрута
    if (legs && legItems.length) {
      const r = legs.getBoundingClientRect(), span = Math.max(1, r.height - vh), k = clamp(-r.top / span, 0, 1);
      legs.style.setProperty('--p', k.toFixed(4));
      const idx = Math.min(legItems.length - 1, Math.floor(k * legItems.length * 0.999));
      if (idx !== legIdx) { legIdx = idx; legItems.forEach((l, i) => l.classList.toggle('is-on', i === idx)); ports.forEach((im, i) => im.classList.toggle('is-on', i === idx)); }
    }
    // лента направлений
    if (useH && hs._extra !== undefined) {
      const r = hs.getBoundingClientRect(), k = clamp(-r.top / Math.max(1, hs._extra), 0, 1);
      htrack.style.transform = 'translate3d(' + (-k * hs._extra).toFixed(1) + 'px,0,0)';
      if (hprog) hprog.style.setProperty('--hp', k.toFixed(4));
      htrack.style.setProperty('--px', (k * -24).toFixed(1) + 'px');
    }
  }
  let ticking = false;
  W.addEventListener('scroll', () => { if (!ticking) { ticking = true; requestAnimationFrame(() => { ticking = false; onScroll(); }); } }, { passive: true });
  W.addEventListener('resize', () => { sizeH(); onScroll(); });
  W.addEventListener('load', () => { sizeH(); onScroll(); });
  sizeH(); onScroll();
  // бегущая строка и курс по вертолёту — в собственном цикле
  if ((mq || hudHdg) && !REDUCED) {
    let dir = -1, boost = 0;
    const loop = () => {
      if (mq) {
        const half = mq.scrollWidth / 2;
        if (Math.abs(vel) > 1) dir = vel > 0 ? -1 : 1;
        boost += (Math.min(18, Math.abs(vel) * 0.35) - boost) * 0.08; vel *= 0.9;
        mqX += dir * (0.6 + boost);
        if (mqX <= -half) mqX += half; if (mqX > 0) mqX -= half;
        mq.style.transform = 'translate3d(' + mqX.toFixed(1) + 'px,0,0)';
      }
      if (hudHdg) { const v = D.querySelector('#hero-viewer'); if (v && v._viewer) { const deg = ((((-v._viewer.orbit.theta) * 180 / Math.PI) % 360) + 360 + 90) % 360; hudHdg.textContent = String(Math.round(deg)).padStart(3, '0'); } }
      requestAnimationFrame(loop);
    };
    requestAnimationFrame(loop);
  }

  /* ---------- Наклон карточек за курсором ---------- */
  if (!REDUCED && FINE) {
    D.querySelectorAll('.tilt').forEach(card => {
      card.addEventListener('pointermove', e => {
        const r = card.getBoundingClientRect(), x = (e.clientX - r.left) / r.width, y = (e.clientY - r.top) / r.height;
        card.style.transform = 'rotateX(' + ((0.5 - y) * 7) + 'deg) rotateY(' + ((x - 0.5) * 9) + 'deg) translateY(-6px)';
      });
      card.addEventListener('pointerleave', () => { card.style.transform = ''; });
    });
    /* магнитные кнопки + блик под курсором */
    D.querySelectorAll('.btn').forEach(b => b.addEventListener('pointermove', e => { const r = b.getBoundingClientRect(); b.style.setProperty('--bx', (e.clientX - r.left) + 'px'); b.style.setProperty('--by', (e.clientY - r.top) + 'px'); }));
    D.querySelectorAll('.magnetic').forEach(m => {
      m.addEventListener('pointermove', e => { const r = m.getBoundingClientRect(); const dx = e.clientX - (r.left + r.width / 2), dy = e.clientY - (r.top + r.height / 2); m.style.transform = 'translate3d(' + (dx * 0.22).toFixed(1) + 'px,' + (dy * 0.3).toFixed(1) + 'px,0)'; });
      m.addEventListener('pointerleave', () => { m.style.transform = ''; });
    });
    /* курсор: кольцо с подписью над 3D-сценами и карточками */
    const cur = D.querySelector('.cursor'), lab = cur && cur.querySelector('.cursor-label');
    if (cur) {
      let tx = -100, ty = -100, cx = -100, cy = -100;
      D.addEventListener('pointermove', e => { if (e.pointerType !== 'mouse') return; tx = e.clientX; ty = e.clientY; cur.classList.add('is-on');
        const t = e.target.closest && e.target.closest('[data-cursor]');
        if (t) { if (lab.textContent !== t.dataset.cursor) lab.textContent = t.dataset.cursor; cur.classList.add('is-hover'); } else cur.classList.remove('is-hover');
      });
      D.addEventListener('pointerdown', () => cur.classList.add('is-down'));
      D.addEventListener('pointerup', () => cur.classList.remove('is-down'));
      D.addEventListener('mouseleave', () => cur.classList.remove('is-on'));
      const step = () => { cx += (tx - cx) * 0.2; cy += (ty - cy) * 0.2; cur.style.transform = 'translate3d(' + cx.toFixed(1) + 'px,' + cy.toFixed(1) + 'px,0)'; requestAnimationFrame(step); };
      requestAnimationFrame(step);
    }
  }

  /* ---------- «Посадочный талон»: расчёт полёта по тарифам маршрутов ---------- */
  const calc = D.querySelector('[data-calc]');
  if (calc) {
    const J = JSON.parse(calc.querySelector('[data-calc-json]').textContent);
    const fromSel = calc.querySelector('[data-calc-from]'), routeSel = calc.querySelector('[data-calc-route]'), seg = calc.querySelector('[data-calc-helis]');
    const out = { dur: calc.querySelector('[data-calc-dur]'), pax: calc.querySelector('[data-calc-pax]'), price: calc.querySelector('[data-calc-price]') }, link = calc.querySelector('[data-calc-link]');
    const fmt = n => String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
    let heli = 'as350', shown = 0;
    const route = () => J.routes[fromSel.value][+routeSel.value] || J.routes[fromSel.value][0];
    const fillRoutes = () => { routeSel.innerHTML = J.routes[fromSel.value].map((r, i) => '<option value="' + i + '">' + r.t.replace(/</g, '&lt;') + '</option>').join(''); };
    const tween = (from, to) => { if (REDUCED) { out.price.textContent = fmt(to) + ' ₽'; return; } const t0 = performance.now(); const step = now => { const k = Math.min(1, (now - t0) / 650), e = 1 - Math.pow(1 - k, 3); out.price.textContent = fmt(Math.round(from + (to - from) * e)) + ' ₽'; if (k < 1) requestAnimationFrame(step); }; requestAnimationFrame(step); };
    const render = () => {
      const r = route(); if (!r.r.some(x => x.k === heli)) heli = r.r[0].k;
      seg.innerHTML = r.r.map(x => '<button type="button" role="radio" aria-checked="' + (x.k === heli) + '" data-k="' + x.k + '">' + J.helis[x.k].n + '</button>').join('');
      const row = r.r.find(x => x.k === heli);
      out.dur.textContent = row.dur; out.pax.textContent = row.pax;
      tween(shown, row.price); shown = row.price;
      calc.classList.remove('is-tick'); void calc.offsetWidth; calc.classList.add('is-tick');
      if (link) link.href = 'ekskursii/' + r.s + '.html';
    };
    fromSel.addEventListener('change', () => { fillRoutes(); render(); });
    routeSel.addEventListener('change', render);
    seg.addEventListener('click', e => { const b = e.target.closest('button[data-k]'); if (!b) return; heli = b.dataset.k; render(); });
    calc.addEventListener('submit', e => {
      e.preventDefault(); const r = route();
      const q = new URLSearchParams({ route: r.t, heli: J.helis[heli].f, from: fromSel.value === 'village' ? 'Altay Village Телецкое' : 'Площадка «Карасук», с. Чепош' });
      location.href = calc.getAttribute('action') + '?' + q.toString();
    });
    render();
  }

  /* ---------- Фильтр и сортировка маршрутов ---------- */
  D.querySelectorAll('[data-filter]').forEach(bar => {
    const list = D.querySelector(bar.dataset.filter); if (!list) return;
    const cards = Array.from(list.children), order = cards.slice(), cnt = bar.querySelector('[data-f-count]'), empty = list.parentElement.querySelector('.rf-empty');
    const st = { dur: 'all', heli: 'all', sort: '' };
    const apply = () => {
      const first = new Map(cards.map(c => [c, c.getBoundingClientRect()]));
      let n = 0;
      cards.forEach(c => {
        const m = +c.dataset.min, [a, b] = st.dur === 'all' ? [0, 1e9] : st.dur.split('-').map(Number);
        const ok = m >= a && m <= b && (st.heli === 'all' || (' ' + c.dataset.helis + ' ').indexOf(' ' + st.heli + ' ') >= 0);
        c.hidden = !ok; if (ok) n++;
      });
      const key = st.sort.replace('-', ''), dir = st.sort[0] === '-' ? -1 : 1;
      const sorted = key ? cards.slice().sort((x, y) => (+x.dataset[key] - +y.dataset[key]) * dir) : order;
      sorted.forEach(c => list.appendChild(c));
      if (cnt) cnt.textContent = n; if (empty) empty.hidden = n > 0;
      if (REDUCED) return;
      cards.forEach(c => {   // плавная перестановка (FLIP)
        if (c.hidden) return; const a = first.get(c), b = c.getBoundingClientRect();
        if (!a.width) { c.animate([{ opacity: 0, transform: 'scale(.94)' }, { opacity: 1, transform: 'none' }], { duration: 450, easing: 'cubic-bezier(.22,.8,.2,1)' }); return; }
        const dx = a.left - b.left, dy = a.top - b.top; if (!dx && !dy) return;
        c.animate([{ transform: 'translate(' + dx + 'px,' + dy + 'px)' }, { transform: 'none' }], { duration: 550, easing: 'cubic-bezier(.22,.8,.2,1)' });
      });
    };
    const press = (attr, val) => bar.querySelectorAll('[' + attr + ']').forEach(b => b.setAttribute('aria-pressed', b.getAttribute(attr) === val ? 'true' : 'false'));
    bar.addEventListener('click', e => {
      const d = e.target.closest('[data-f-dur]'), h = e.target.closest('[data-f-heli]');
      if (d) { st.dur = d.dataset.fDur; press('data-f-dur', st.dur); apply(); }
      if (h) { st.heli = h.dataset.fHeli; press('data-f-heli', st.heli); apply(); }
    });
    const sel = bar.querySelector('[data-f-sort]'); if (sel) sel.addEventListener('change', () => { st.sort = sel.value; apply(); });
    const reset = empty && empty.querySelector('[data-f-reset]');
    if (reset) reset.addEventListener('click', () => { st.dur = 'all'; st.heli = 'all'; press('data-f-dur', 'all'); press('data-f-heli', 'all'); apply(); });
    list.classList.add('is-in');
  });

  /* ---------- Лайтбокс галереи ---------- */
  const lbLinks = Array.from(D.querySelectorAll('a[data-lightbox]'));
  if (lbLinks.length) {
    const lb = D.createElement('div'); lb.className = 'lightbox'; lb.setAttribute('role', 'dialog'); lb.setAttribute('aria-label', 'Просмотр фотографии');
    lb.innerHTML = '<button class="lb-close" aria-label="Закрыть"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 6l12 12M18 6L6 18"/></svg></button><button class="lb-prev" aria-label="Предыдущая"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 5l-7 7 7 7"/></svg></button><img alt=""><div class="lb-cap"></div><button class="lb-next" aria-label="Следующая"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 5l7 7-7 7"/></svg></button>';
    D.body.appendChild(lb);
    const img = lb.querySelector('img'), cap = lb.querySelector('.lb-cap'); let cur = 0, group = [];
    const show = k => { cur = (k + group.length) % group.length; img.src = group[cur].href; img.alt = group[cur].dataset.caption || ''; cap.textContent = (cur + 1) + ' / ' + group.length + (group[cur].dataset.caption ? ' · ' + group[cur].dataset.caption : ''); img.style.animation = 'none'; void img.offsetWidth; img.style.animation = ''; };
    const open = a => { group = lbLinks.filter(x => x.dataset.lightbox === a.dataset.lightbox); show(group.indexOf(a)); lb.classList.add('is-open'); D.body.style.overflow = 'hidden'; lb.querySelector('.lb-close').focus(); };
    const close = () => { lb.classList.remove('is-open'); D.body.style.overflow = ''; };
    lbLinks.forEach(a => { a.setAttribute('data-cursor', 'Смотреть'); a.addEventListener('click', e => { e.preventDefault(); open(a); }); });
    lb.querySelector('.lb-close').addEventListener('click', close); lb.querySelector('.lb-prev').addEventListener('click', () => show(cur - 1)); lb.querySelector('.lb-next').addEventListener('click', () => show(cur + 1));
    lb.addEventListener('click', e => { if (e.target === lb) close(); });
    D.addEventListener('keydown', e => { if (!lb.classList.contains('is-open')) return; if (e.key === 'Escape') close(); if (e.key === 'ArrowLeft') show(cur - 1); if (e.key === 'ArrowRight') show(cur + 1); });
  }

  /* ---------- Формы заявок ---------- */
  D.querySelectorAll('form[data-form]').forEach(form => {
    const status = form.querySelector('.form-status');
    form.addEventListener('submit', async e => {
      e.preventDefault(); if (!form.reportValidity()) return;
      const data = {}; new FormData(form).forEach((v, k) => { data[k] = v; }); data._form = form.dataset.form; data._page = location.href;
      const btn = form.querySelector('[type=submit]');
      const setStatus = (t, cls) => { if (status) { status.textContent = t; status.className = 'form-status ' + (cls || ''); } };
      if (CONFIG.formEndpoint) {
        btn.disabled = true; setStatus('Отправляем…');
        try { const r = await fetch(CONFIG.formEndpoint, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }); if (!r.ok) throw new Error(r.status); setStatus('Заявка отправлена. Мы свяжемся с вами в ближайшее время.', 'ok'); form.reset(); }
        catch (err) { setStatus('Не удалось отправить заявку. Позвоните нам: 8 800 550 31 31', 'err'); }
        btn.disabled = false;
      } else {
        const subject = (form.dataset.subject || 'Заявка с сайта') + (data.helicopter ? ' — ' + data.helicopter : '');
        const lines = Object.keys(data).filter(k => k[0] !== '_' && data[k]).map(k => { const f = form.querySelector('[name="' + k + '"]'), fl = f && f.closest('.field'), lb = fl && fl.querySelector('label'); return (lb ? lb.textContent.replace('*', '').trim() : k) + ': ' + data[k]; });
        location.href = 'mailto:' + CONFIG.mailTo + '?subject=' + encodeURIComponent(subject) + '&body=' + encodeURIComponent(lines.join('\n'));
        setStatus('Открываем почтовый клиент с готовым письмом…', 'ok');
      }
    });
  });
  const q = new URLSearchParams(location.search);
  if (q.get('heli')) { const sel = D.querySelector('select[name=helicopter]'); if (sel) sel.value = q.get('heli'); }
  if (q.get('route')) { const r = D.querySelector('input[name=route]'); if (r) r.value = q.get('route'); const to = D.querySelector('input[name=to]'); if (to && !to.value) to.value = q.get('route'); }
  if (q.get('from')) { const f = D.querySelector('input[name=from]'); if (f && !f.value) f.value = q.get('from'); }

  /* ---------- Версия для слабовидящих ---------- */
  const A11Y = 'aa-a11y';
  const applyA11y = on => { html.classList.toggle('a11y', on); D.querySelectorAll('.a11y-toggle').forEach(b => b.setAttribute('aria-pressed', on ? 'true' : 'false')); };
  try { applyA11y(localStorage.getItem(A11Y) === '1'); } catch (e) { }
  D.querySelectorAll('.a11y-toggle').forEach(b => b.addEventListener('click', () => { const on = !html.classList.contains('a11y'); applyA11y(on); try { localStorage.setItem(A11Y, on ? '1' : '0'); } catch (e) { } }));
  D.querySelectorAll('[data-year]').forEach(el => { el.textContent = new Date().getFullYear(); });

  W.AltayUI = { onReady, countUp, flapBoard };
})();
