/* АлтайАвиа — поведение и анимации страниц (v2)
   Прелоадер «раскрутка винта», шторка переходов, бегунок меню, слоганы, трасса полёта,
   счётчики, табло вылетов (split-flap), наклон карточек, галерея, формы, версия для слабовидящих */
(function () {
  'use strict';
  const D = document, W = window, html = D.documentElement;
  html.classList.add('js');
  const REDUCED = W.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* Конфигурация отправки форм: endpoint — URL обработчика (POST JSON). Пока пуст — письмо через mailto. */
  const CONFIG = { formEndpoint: '', mailTo: 'info@altay-avia.ru' };

  const ss = { get: k => { try { return sessionStorage.getItem(k); } catch (e) { return null; } }, set: (k, v) => { try { sessionStorage.setItem(k, v); } catch (e) { } } };

  /* ---------- Прелоадер (только при первом заходе за сессию) и шторка ---------- */
  const pre = D.querySelector('.preloader'), curtain = D.querySelector('.curtain');
  const firstVisit = !ss.get('aa-seen'); ss.set('aa-seen', '1');
  const viaLink = ss.get('aa-nav') === '1'; ss.set('aa-nav', '0');
  let ready = false; const readyQueue = [];
  const onReady = fn => ready ? fn() : readyQueue.push(fn);
  function finishIntro() { ready = true; readyQueue.splice(0).forEach(fn => fn()); html.classList.add('is-ready'); }
  if (pre && firstVisit && !REDUCED) {
    setTimeout(() => { pre.classList.add('is-done'); finishIntro(); }, 1900);
  } else {
    if (pre) pre.classList.add('is-done');
    if (curtain && viaLink && !REDUCED) {
      curtain.classList.add('is-in');
      requestAnimationFrame(() => requestAnimationFrame(() => { curtain.classList.remove('is-in'); curtain.classList.add('is-out'); setTimeout(finishIntro, 350); }));
    } else finishIntro();
  }
  /* переход по внутренним ссылкам: шторка → навигация */
  if (curtain && !REDUCED) {
    D.addEventListener('click', e => {
      const a = e.target.closest('a[href]'); if (!a) return;
      if (e.metaKey || e.ctrlKey || e.shiftKey || a.target === '_blank' || a.hasAttribute('download') || a.dataset.lightbox) return;
      const url = new URL(a.href, location.href);
      if (url.origin !== location.origin) return;
      if (!/\.html$/.test(url.pathname) && !/\/$/.test(url.pathname)) return;
      if (url.pathname === location.pathname && url.hash) return;
      e.preventDefault(); ss.set('aa-nav', '1');
      curtain.classList.remove('is-out'); curtain.classList.add('is-in');
      setTimeout(() => { location.href = url.href; }, 620);
    });
    W.addEventListener('pageshow', e => { if (e.persisted) { curtain.classList.remove('is-in'); } });
  }

  /* ---------- Шапка: бургер, компактный режим, бегунок меню ---------- */
  const header = D.querySelector('.site-header'), burger = D.querySelector('.burger');
  if (burger && header) burger.addEventListener('click', () => { const open = header.classList.toggle('nav-open'); burger.setAttribute('aria-expanded', open ? 'true' : 'false'); });
  if (header) { let last = false; const onScroll = () => { const c = W.scrollY > 80; if (c !== last) { header.classList.toggle('is-compact', c); last = c; } }; W.addEventListener('scroll', onScroll, { passive: true }); onScroll(); }
  const here = location.pathname.replace(/\/index\.html$/, '/');
  D.querySelectorAll('.nav a, .footer-grid a').forEach(a => {
    const path = new URL(a.getAttribute('href') || '', location.href).pathname, sec = a.dataset.section;
    if (path === here || (sec && (here.indexOf('/' + sec + '.html') >= 0 || here.indexOf('/' + sec + '/') >= 0))) a.classList.add('is-active');
  });
  const nav = D.querySelector('.nav');
  if (nav) {
    const glider = D.createElement('span'); glider.className = 'nav-glider'; nav.appendChild(glider);
    const moveTo = a => { if (!a) { glider.style.opacity = '0'; return; } const r = a.getBoundingClientRect(), n = nav.getBoundingClientRect(); glider.style.left = (r.left - n.left + 13) + 'px'; glider.style.width = (r.width - 26) + 'px'; glider.style.opacity = '1'; };
    const active = nav.querySelector('a.is-active');
    nav.querySelectorAll('a').forEach(a => { a.addEventListener('mouseenter', () => moveTo(a)); a.addEventListener('focus', () => moveTo(a)); });
    nav.addEventListener('mouseleave', () => moveTo(active));
    if (D.fonts && D.fonts.ready) D.fonts.ready.then(() => moveTo(active)); else moveTo(active);
    W.addEventListener('resize', () => moveTo(active));
  }

  /* ---------- Заголовки: посимвольный вылет ---------- */
  D.querySelectorAll('.h-split').forEach(el => {
    if (REDUCED) return;
    const text = el.textContent; el.textContent = ''; el.setAttribute('aria-label', text); let i = 0; const words = text.split(' ');
    words.forEach((word, wi) => {
      const w = D.createElement('span'); w.style.whiteSpace = 'nowrap'; w.setAttribute('aria-hidden', 'true');
      word.split('').forEach(ch => { const s = D.createElement('span'); s.className = 'ch'; s.textContent = ch; s.style.animationDelay = (i++ * 22) + 'ms'; w.appendChild(s); });
      el.appendChild(w); if (wi < words.length - 1) el.appendChild(D.createTextNode(' '));
    });
  });

  /* ---------- Главный экран: слоганы, трасса полёта, параллакс, связь 3D со скроллом ---------- */
  const slogans = D.querySelectorAll('.slogans li');
  if (slogans.length) {
    slogans.forEach(li => { const s = li.querySelector('strong'); if (s && !s.querySelector('.w')) { const words = s.textContent.trim().split(/\s+/); s.innerHTML = words.map((w, i) => '<span class="w" style="animation-delay:' + (i * 90) + 'ms">' + w + '</span>').join(' '); } });
    if (!REDUCED) { let i = 0; onReady(() => setInterval(() => { slogans[i].classList.remove('is-live'); i = (i + 1) % slogans.length; slogans[i].classList.add('is-live'); }, 3800)); }
  }
  const fp = D.querySelector('.flightpath'); if (fp) onReady(() => fp.classList.add('is-on'));
  const hero = D.querySelector('.hero'), heroCopy = D.querySelector('.hero-copy');
  if (hero && !REDUCED) {
    const onScroll = () => {
      const r = hero.getBoundingClientRect(); const p = Math.min(1, Math.max(0, -r.top / Math.max(1, r.height * 0.9)));
      const v = D.querySelector('.hero-stage .viewer'); if (v && v._viewer) v._viewer.setScroll(p);
      if (heroCopy) heroCopy.style.transform = 'translateY(' + (p * 60) + 'px)';
      hero.style.setProperty('--p', p);
    };
    W.addEventListener('scroll', onScroll, { passive: true });
    hero.addEventListener('pointermove', e => { if (!heroCopy) return; const r = hero.getBoundingClientRect(); const x = (e.clientX - r.left) / r.width - .5, y = (e.clientY - r.top) / r.height - .5; D.querySelectorAll('.cloud').forEach((c, i) => { c.style.marginLeft = (x * (10 + i * 6)) + 'px'; c.style.marginTop = (y * (6 + i * 4)) + 'px'; }); });
  }

  /* ---------- Появление при прокрутке, «взлётная полоса», счётчики ---------- */
  const io = 'IntersectionObserver' in W ? new IntersectionObserver(es => es.forEach(e => {
    if (!e.isIntersecting) return; const el = e.target; el.classList.add('is-in'); io.unobserve(el);
    if (el.hasAttribute('data-count')) countUp(el);
    if (el.classList.contains('board')) flapBoard(el);
  }), { rootMargin: '0px 0px -8% 0px', threshold: 0.05 }) : null;
  D.querySelectorAll('.reveal, .stagger, .runway, [data-count], .board').forEach(el => {
    if (!io) { el.classList.add('is-in'); if (el.hasAttribute('data-count')) el.textContent = el.dataset.count; return; }
    const r = el.getBoundingClientRect();
    if (r.top < W.innerHeight * 0.9 && !el.hasAttribute('data-count') && !el.classList.contains('board')) el.classList.add('is-in'); else io.observe(el);
  });
  function countUp(el) {
    const target = parseFloat(el.dataset.count), suffix = el.dataset.suffix || '', dur = 1600, t0 = performance.now();
    const fmt = n => String(Math.round(n)).replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
    if (REDUCED) { el.textContent = fmt(target) + suffix; return; }
    const tick = now => { const k = Math.min(1, (now - t0) / dur), e = 1 - Math.pow(1 - k, 3); el.textContent = fmt(target * e) + suffix; if (k < 1) requestAnimationFrame(tick); };
    requestAnimationFrame(tick);
  }

  /* ---------- Табло вылетов: буквы «перелистываются» до нужного значения ---------- */
  const ALPHA = ' АБВГДЕЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-.,()…';
  function flapBoard(board) {
    board.querySelectorAll('[data-flap]').forEach((cell, ri) => {
      const text = (cell.dataset.flap || '').toUpperCase(); cell.innerHTML = '';
      text.split('').forEach((ch, ci) => {
        const c = D.createElement('span'); c.className = 'c' + (ch === ' ' ? ' space' : ''); c.textContent = ch === ' ' ? '' : ch; cell.appendChild(c);
        if (REDUCED || ch === ' ') return;
        const target = ALPHA.indexOf(ch); let idx = Math.max(0, target - 6 - Math.floor(Math.random() * 8)); if (target < 0) return;
        c.textContent = ALPHA[idx];
        const step = () => { idx++; if (idx > target) { c.textContent = ch; return; } c.textContent = ALPHA[idx]; setTimeout(step, 38); };
        setTimeout(step, 120 + ri * 90 + ci * 14);
      });
    });
  }

  /* ---------- Наклон карточек за курсором + блик ---------- */
  if (!REDUCED && W.matchMedia('(hover:hover)').matches) {
    D.querySelectorAll('.tilt').forEach(card => {
      card.addEventListener('pointermove', e => {
        const r = card.getBoundingClientRect(), x = (e.clientX - r.left) / r.width, y = (e.clientY - r.top) / r.height;
        card.style.transform = 'rotateX(' + ((0.5 - y) * 8) + 'deg) rotateY(' + ((x - 0.5) * 10) + 'deg) translateY(-4px)';
        card.style.setProperty('--mx', (x * 100) + '%'); card.style.setProperty('--my', (y * 100) + '%');
      });
      card.addEventListener('pointerleave', () => { card.style.transform = ''; });
    });
  }

  /* ---------- Лайтбокс галереи ---------- */
  const lbLinks = Array.from(D.querySelectorAll('a[data-lightbox]'));
  if (lbLinks.length) {
    const lb = D.createElement('div'); lb.className = 'lightbox'; lb.setAttribute('role', 'dialog'); lb.setAttribute('aria-label', 'Просмотр фотографии');
    lb.innerHTML = '<button class="lb-close" aria-label="Закрыть"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 6l12 12M18 6L6 18"/></svg></button><button class="lb-prev" aria-label="Предыдущая"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 5l-7 7 7 7"/></svg></button><img alt=""><div class="lb-cap"></div><button class="lb-next" aria-label="Следующая"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 5l7 7-7 7"/></svg></button>';
    D.body.appendChild(lb);
    const img = lb.querySelector('img'), cap = lb.querySelector('.lb-cap'); let cur = 0, group = [];
    const show = k => { cur = (k + group.length) % group.length; img.src = group[cur].href; img.alt = group[cur].dataset.caption || ''; cap.textContent = (cur + 1) + ' / ' + group.length + (group[cur].dataset.caption ? ' · ' + group[cur].dataset.caption : ''); };
    const open = a => { group = lbLinks.filter(x => x.dataset.lightbox === a.dataset.lightbox); show(group.indexOf(a)); lb.classList.add('is-open'); D.body.style.overflow = 'hidden'; lb.querySelector('.lb-close').focus(); };
    const close = () => { lb.classList.remove('is-open'); D.body.style.overflow = ''; };
    lbLinks.forEach(a => a.addEventListener('click', e => { e.preventDefault(); open(a); }));
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
        const lines = Object.keys(data).filter(k => k[0] !== '_' && data[k]).map(k => (form.querySelector('[name="' + k + '"]')?.closest('.field')?.querySelector('label')?.textContent.replace('*', '').trim() || k) + ': ' + data[k]);
        location.href = 'mailto:' + CONFIG.mailTo + '?subject=' + encodeURIComponent(subject) + '&body=' + encodeURIComponent(lines.join('\n'));
        setStatus('Открываем почтовый клиент с готовым письмом…', 'ok');
      }
    });
  });
  const q = new URLSearchParams(location.search);
  if (q.get('heli')) { const sel = D.querySelector('select[name=helicopter]'); if (sel) sel.value = q.get('heli'); }
  if (q.get('route')) { const r = D.querySelector('input[name=route]'); if (r) r.value = q.get('route'); }

  /* ---------- Версия для слабовидящих ---------- */
  const A11Y = 'aa-a11y';
  const applyA11y = on => { html.classList.toggle('a11y', on); D.querySelectorAll('.a11y-toggle').forEach(b => b.setAttribute('aria-pressed', on ? 'true' : 'false')); };
  try { applyA11y(localStorage.getItem(A11Y) === '1'); } catch (e) { }
  D.querySelectorAll('.a11y-toggle').forEach(b => b.addEventListener('click', () => { const on = !html.classList.contains('a11y'); applyA11y(on); try { localStorage.setItem(A11Y, on ? '1' : '0'); } catch (e) { } }));
  D.querySelectorAll('[data-year]').forEach(el => { el.textContent = new Date().getFullYear(); });

  W.AltayUI = { onReady, countUp, flapBoard };
})();
