# -*- coding: utf-8 -*-
"""Главная страница (v3): страница — это полёт от «Карасука» (375 м) к Белухе (4506 м).
   Герой с живой 3D-сценой и взлётом по прокрутке → бегущая строка направлений → «время в пути» (кабина, иллюминатор)
   → направления (горизонтальная лента) → компания и бортовой журнал → парк в 3D (истинный масштаб) → табло вылетов → услуги."""
import re
from common import *

# направления для ленты: (slug маршрута, картинка, заголовок, подпись, положение кадра)
DEST = [
    ('akkem-ga', 'img/eks/eks23-b-bel1007.jpg', 'Белуха', '4506 м · посадка на озере Аккем', '50% 40%'),
    ('teletskoe-ga', 'img/eks/eks23-b-t00.jpg', 'Телецкое озеро', 'и долина реки Чулышман', '50% 50%'),
    ('urochishche-chokportas', 'img/eks/eks-gornyj-chok-ch-033.jpg', 'Чокпортас', 'каменные останцы урочища', '50% 45%'),
    ('shavlinskie-ga', 'img/eks/eks-gornyj-shav.jpg', 'Шавлинские озёра', 'и Кызыл-Чин — «Марс»', '50% 50%'),
    ('ukok-ga', 'img/eks/eks-gornyj-ukok.jpg', 'Плато Укок', 'граница четырёх стран', '50% 50%'),
    ('karakolskie-ga', 'img/eks/eks-village-karakol.jpg', 'Каракольские озёра', 'каскад из семи озёр', '50% 50%'),
    ('aktru-ga', 'img/eks/eks-village-aktru.jpg', 'Актру', 'центр альпинизма на Алтае', '50% 50%'),
]
# «время в пути»: (slug, картинка в иллюминаторе, время, куда)
LEGS = [
    ('katun-ga-15', 'img/eks/eks-gornyj-katun.jpg', '15', 'минут', 'и под вами долина Катуни'),
    ('karakolskie-ga', 'img/eks/eks-gornyj-karakol1.jpg', '40', 'минут', 'над каскадом Каракольских озёр'),
    ('akkem-ga', 'img/eks/eks23-b-z2.jpg', '2:50', 'часа', 'к подножию Белухи — посадка на озере Аккем'),
]

def build_index(EX, esc):
    root = ''
    by_slug = {e['slug']: e for e in EX}
    price_of = lambda e: re.sub(r'\s*р\.?$', '', e['rows'][0]['price']).strip() if e['rows'] else ''

    slog = [('Аренда вертолетов', 'по городам Сибири'), ('Уникальные', 'экскурсионные маршруты'), ('Сервисное', 'обслуживание вертолетов'), ('Услуги по', 'ангарному хранению')]
    slog_html = ''.join(f'<li{" class=is-live" if i == 0 else ""}><span class="idx">0{i+1}<i>/04</i></span><p><strong>{a}</strong> {b}</p></li>' for i, (a, b) in enumerate(slog))

    # ---------------- герой
    hero = f'''
<section class="hero" data-hero>
  <div class="hero-stage">
    <div class="viewer" id="hero-viewer" data-model="mi171" data-helipad="1" data-rotor="fast" data-hover="1" data-auto="1" data-speed="0.08" data-theta="1.05" data-phi="1.49" data-fit="auto" data-margin="0.72" data-ty="4.6" data-fov="30" data-offset="0.7" data-flyin="1" aria-label="3D-модель вертолёта МИ-171 на площадке «Карасук» — вращайте мышью"></div>
  </div>
  <div class="hero-veil" aria-hidden="true"></div>
  <div class="wrap hero-inner">
    <div class="hero-copy">
      <div class="hero-kicker"><i></i>Коммерческий авиаперевозчик · Республика Алтай</div>
      <h1 class="hero-title"><span class="ht-line"><span class="ht-big">Алтай</span></span><span class="ht-line"><span class="ht-sub">с высоты птичьего полёта</span></span></h1>
      <ul class="slogans" aria-label="Наши услуги">{slog_html}</ul>
      <div class="hero-actions">
        <a class="btn btn-primary btn-lg magnetic" href="zakaz-poleta.html"><span>Заказать полет</span>{ICON['arrow']}</a>
        <a class="btn btn-ghost btn-lg" href="ekskursii.html"><span>Экскурсионные маршруты</span></a>
      </div>
      <p class="hero-note">Отправляя заявку, Вы даете согласие на обработку персональных данных в соответствии с <a href="politika.html">Условиями</a></p>
    </div>
  </div>
  <div class="hud" aria-hidden="true">
    <div class="hud-cell"><small>ВЫС</small><b data-hud-alt>375</b><em>м</em></div>
    <div class="hud-cell"><small>КУРС</small><b data-hud-hdg>051</b><em>°</em></div>
    <div class="hud-cell"><small>БОРТ</small><b>RA-25565</b><em>МИ-171</em></div>
    <div class="hud-hint">{ICON['drag']}<span>потяните, чтобы осмотреть</span></div>
  </div>
  <a class="scroll-cue" href="#legs" aria-label="Листайте вниз"><span>Листайте — взлетаем</span><i></i></a>
</section>'''

    # ---------------- бегущая строка
    names = ['Белуха 4506 м', 'Телецкое озеро', 'Плато Укок', 'Каракольские озёра', 'Шавлинские озёра', 'Актру', 'Чулышман', 'Долина Катуни', 'Белокуриха', 'Шерегеш']
    run = ''.join(f'<span>{n}</span><i>{ICON["spark"]}</i>' for n in names)
    marquee = f'<div class="marquee" aria-hidden="true"><div class="marquee-track" data-marquee>{run}{run}</div></div>'

    # ---------------- время в пути (кабина + иллюминатор)
    legs_html = ''
    ports = ''
    for i, (slug, img, t, unit, where) in enumerate(LEGS):
        e = by_slug[slug]
        legs_html += f'''<a class="leg{' is-on' if i == 0 else ''}" href="ekskursii/{slug}.html" data-leg="{i}">
      <span class="leg-time"><b>{t}</b><em>{unit}</em></span><span class="leg-where">{where}</span><span class="leg-price">{esc(e['title'])} · от {price_of(e)} ₽</span></a>'''
        ports += f'<img src="{img}" alt="" data-port="{i}"{" class=is-on" if i == 0 else ""} loading="lazy">'
    legs = f'''
<section class="legs" id="legs" data-legs>
  <div class="legs-sticky">
    <div class="legs-bg"><img src="img/hero/video-fon.jpg" alt="Вид из кабины вертолёта на горы Алтая" loading="lazy"></div>
    <div class="legs-shade"></div>
    <div class="wrap legs-inner">
      <div class="legs-copy">
        <div class="eyebrow eyebrow-light">Время в пути</div>
        <h2 class="legs-title">Горный Алтай ближе, чем кажется</h2>
        <div class="legs-list">{legs_html}</div>
        <p class="legs-note">Цены — за полёт на Eurocopter AS350, старт с площадки «Карасук». Считается общее время аренды.</p>
      </div>
      <div class="porthole" aria-hidden="true"><div class="porthole-glass">{ports}</div><div class="porthole-rim"></div><div class="porthole-bolts"></div></div>
    </div>
    <div class="legs-progress" aria-hidden="true"><i></i></div>
  </div>
</section>'''

    # ---------------- направления (горизонтальная лента)
    cards = ''
    for i, (slug, img, t, sub, pos) in enumerate(DEST):
        e = by_slug[slug]
        dur = e['rows'][0]['dur'] if e['rows'] else ''
        cards += f'''<a class="dest" href="ekskursii/{slug}.html" data-cursor="Маршрут">
      <div class="dest-pic"><img src="{img}" alt="{esc(t)}" loading="lazy" style="object-position:{pos}"></div>
      <span class="dest-num">0{i+1}</span>
      <div class="dest-body"><h3>{t}</h3><p>{sub}</p><div class="dest-meta"><span>{ICON['clock']}{dur}</span><span>от <b>{price_of(e)} ₽</b></span></div></div>
      <span class="dest-go">{ICON['arrow-ur']}</span>
    </a>'''
    dests = f'''
<section class="dests" data-hscroll>
  <div class="dests-sticky">
    <div class="wrap dests-head">
      <div><div class="eyebrow">Экскурсионные маршруты</div><h2 class="split-words">Куда полетим?</h2></div>
      <p>Тридцать маршрутов по Горному Алтаю — от получасового облёта Катуни до ледников Белухи. Прокрутите ленту.</p>
    </div>
    <div class="dests-track" data-htrack>{cards}
      <a class="dest dest-all" href="ekskursii.html"><span class="dest-all-in"><b>30</b><span>маршрутов<br>по Алтаю и Сибири</span><em>Смотреть все {ICON['arrow']}</em></span></a>
    </div>
    <div class="wrap dests-bar"><div class="dests-progress"><i data-hprogress></i></div><span class="dests-hint">{ICON['drag']} листайте</span></div>
  </div>
</section>'''

    # ---------------- компания и бортовой журнал
    about = f'''
<section class="section about">
  <div class="wrap about-grid">
    <div class="about-copy">
      <div class="eyebrow">О компании</div>
      <h2 class="split-words">Сертифицированный коммерческий авиаперевозчик на Алтае</h2>
      <p class="lead reveal">Компания «АлтайАвиа» осуществляет коммерческие воздушные перевозки. Мы — одна из самых крупных частных авиакомпаний в Сибири с выгодным расположением к соседним регионам и сетью посадочных площадок во многих популярных туристических объектах Алтая и Сибири.</p>
      <div class="hero-actions reveal"><a class="btn btn-outline" href="o-kompanii.html"><span>Подробнее о компании</span>{ICON['arrow']}</a><a class="btn btn-ghost" href="galereya.html"><span>Галерея</span></a></div>
    </div>
    <div class="about-media">
      <figure class="img-reveal about-main" data-parallax="-0.06"><img src="img/gallery/karasuk25/a1.jpg" alt="Вертодром «Карасук» с высоты" loading="lazy"></figure>
      <figure class="img-reveal about-sub" data-parallax="0.1"><img src="img/gallery/foto24/20240725_141140.jpg" alt="Вертолёт АлтайАвиа у горного озера" loading="lazy"></figure>
      <div class="about-badge"><b>51°33′</b><span>N · Карасук</span></div>
    </div>
  </div>
  <div class="wrap">
    <div class="logbook">
      <div class="logbook-head"><span>Бортовой журнал</span><span>KARASUK · 51°33′N 085°55′E</span></div>
      <ul class="logbook-list stagger">
        <li><b data-count="3">0</b><span>типа вертолётов в парке: Eurocopter AS350, МИ-8АМТ и МИ-171 с VIP-салонами</span></li>
        <li><b data-count="20">0</b><span>пассажиров — вместимость самого крупного борта</span></li>
        <li><b data-count="30">0</b><span>экскурсионных маршрутов по Горному Алтаю, Телецкому озеру, Белокурихе и Шерегешу</span></li>
        <li><b data-count="4506" data-suffix=" м">0</b><span>высота Белухи — самой высокой точки наших маршрутов</span></li>
      </ul>
    </div>
  </div>
</section>'''

    # ---------------- парк (3D, истинный масштаб)
    tabs = ''.join(f'<button class="fleet-tab" role="tab" aria-selected="{"true" if k=="mi171" else "false"}" data-fleet-tab="{k}" data-fleet-target="#fleet-viewer"><b>{HELIS[k]["name"]}</b><small>{HELIS[k]["sub"]} · {HELIS[k]["pax"]} пасс.</small></button>' for k in HELI_ORDER)
    specs = ''.join(f'<div class="spec-card" data-spec="{k}"{"" if k=="mi171" else " hidden"}><div class="reg">Борт {HELIS[k]["reg"]}</div><h3>{HELIS[k]["name"]}</h3><p class="spec-about">{HELIS[k]["about"]}</p><dl class="spec-list">' + ''.join(f'<div><dt>{a}</dt><dd>{b}</dd></div>' for a, b in HELIS[k]['specs']) + f'</dl><a class="btn btn-primary btn-block" href="zakaz-poleta.html?heli={esc(HELIS[k]["form"])}"><span>Заказать полёт · {HELIS[k]["price"]}/час</span>{ICON["arrow"]}</a></div>' for k in HELI_ORDER)
    fleet = f'''
<section class="section fleet-sec" id="park">
  <div class="wrap">
    <div class="section-head"><div><div class="eyebrow">3D-осмотр · масштаб 1:1</div><h2 class="split-words">Парк нашей техники</h2></div><p class="reveal">Все борта показаны в одном масштабе: МИ-8АМТ и МИ-171 почти вдвое больше Eurocopter AS350. Вращайте сцену мышью или пальцем, включайте винты.</p></div>
  </div>
  <div class="wrap-wide">
    <div class="fleet-stage img-reveal" data-cursor="Вращать">
      <div class="viewer" id="fleet-viewer" data-model="mi171" data-helipad="1" data-rotor="idle" data-auto="1" data-speed="0.1" data-theta="0.7" data-phi="1.42" data-fit="auto" data-ty-rel="0.5" data-true-scale="1" data-fov="30" data-offset="0.4" aria-label="3D-модель вертолёта"></div>
      <div class="shutter" aria-hidden="true"></div>
      <div class="fleet-tabs" role="tablist" aria-label="Выбор вертолёта">{tabs}</div>
      <div class="fleet-panel">{specs}</div>
      <div class="stage-controls">
        <button type="button" data-rotor="stop" data-target="#fleet-viewer" title="Винты остановлены" aria-label="Остановить винты">{ICON['pause']}</button>
        <button type="button" data-rotor="idle" data-target="#fleet-viewer" title="Малый газ" aria-pressed="true" aria-label="Медленное вращение винтов">{ICON['rotor']}</button>
        <button type="button" data-rotor="fast" data-target="#fleet-viewer" title="Взлётный режим" aria-label="Быстрое вращение винтов">{ICON['plane']}</button>
        <button type="button" data-autorotate data-target="#fleet-viewer" title="Авто-облёт камерой" aria-pressed="true" aria-label="Автоматический облёт камерой">{ICON['rotate']}</button>
      </div>
      <div class="scale-bar" aria-hidden="true"><i></i><span>10 м</span></div>
    </div>
  </div>
</section>'''

    # ---------------- табло вылетов
    board_rows = ''
    for it in [e for e in EX if e['cat'] == 'altai'][:8]:
        r0 = it['rows'][0]
        t = it['title']
        if len(t) > 38: t = t[:38].rsplit(' ', 1)[0] + '…'
        board_rows += f'<a class="board-row" href="ekskursii/{it["slug"]}.html"><span class="flap" data-flap="{esc(t)}"></span><span class="num">{r0["dur"]}</span><span class="num">от <b>{price_of(it)} ₽</b></span><span class="status"><i></i>Доступно</span></a>'
    board = f'''
<section class="section board-sec">
  <div class="wrap">
    <div class="section-head"><div><div class="eyebrow">Табло вылетов</div><h2 class="split-words">Экскурсионные маршруты</h2></div><p class="reveal">Цена «от» — за полёт на Eurocopter AS350. Старт с посадочной площадки «Карасук».</p></div>
    <div class="board reveal">
      <div class="board-top"><span>Вылеты · Карасук</span><span class="board-clock"><i></i>Местное время <b data-clock>--:--</b></span></div>
      <div class="board-head"><span>Маршрут</span><span>Время</span><span>Стоимость</span><span>Статус</span></div>
      {board_rows}
      <div class="board-foot"><span>Все 30 маршрутов, включая экскурсии с курорта Altay Village</span><a href="ekskursii.html">Смотреть все маршруты →</a></div>
    </div>
  </div>
</section>'''

    # ---------------- услуги
    services = [
        ('arenda.html', 'Аренда', 'Доставим Вас быстро и комфортно в любую точку региона', 'img/gallery/foto24/20240725_141135.jpg'),
        ('ekskursii.html', 'Экскурсии', 'Проведем незабываемые экскурсии на высоте птичьего полета', 'img/eks/eks-gornyj-chok-ch-011.jpg'),
        ('ploshchadki.html', 'Площадки', 'Предлагаем услуги ангарного хранения', 'img/gallery/karasuk25/p003.jpg'),
        ('servis.html', 'Сервис', 'Проводим работы по всем видам технического обслуживания', 'img/hero/slider-servis.jpg'),
    ]
    serv_html = ''.join(f'<a class="service tilt" href="{h}" data-cursor="Открыть"><div class="service-pic"><img src="{img}" alt="" loading="lazy"></div><span class="service-num">0{i+1}</span><div class="service-body"><h3>{t}</h3><p>{d}</p><span class="more">Подробнее {ICON["arrow"]}</span></div></a>' for i, (h, t, d, img) in enumerate(services))
    serv = f'''
<section class="section services-sec">
  <div class="wrap">
    <div class="section-head"><div><div class="eyebrow">Направления</div><h2 class="split-words">Наши услуги</h2></div></div>
    <div class="services stagger">{serv_html}</div>
  </div>
</section>'''

    body = hero + marquee + legs + dests + about + fleet + board + serv
    write('index.html', page(root=root, title='Авиакомпания АлтайАвиа | официальный сайт', desc='Аренда вертолётов по городам Сибири, уникальные экскурсионные маршруты по Горному Алтаю, сервисное обслуживание и ангарное хранение вертолётов. Посадочная площадка «Карасук», Республика Алтай.', active='', body=body, scripts_3d=True, models=('mi171', 'mi8amt'), body_class='is-home'))
