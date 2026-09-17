# -*- coding: utf-8 -*-
"""Главная страница (v2): герой с прилётом 3D-модели, бортовой журнал, парк, табло вылетов, услуги."""
import re
from common import *

def build_index(EX, esc):
    root = ''
    slog = [('Аренда вертолетов', 'по городам Сибири'), ('Уникальные', 'экскурсионные маршруты'), ('Сервисное', 'обслуживание вертолетов'), ('Услуги по', 'ангарному хранению')]
    slog_html = ''.join(f'<li{" class=is-live" if i == 0 else ""}><span class="idx">0{i+1}</span><div><strong>{a}</strong><span>{b}</span></div></li>' for i, (a, b) in enumerate(slog))
    tabs = ''.join(f'<button class="fleet-tab" role="tab" aria-selected="{"true" if k=="as350" else "false"}" data-fleet-tab="{k}" data-fleet-target="#fleet-viewer"><span><b>{HELIS[k]["name"]}</b><small>{HELIS[k]["sub"]}</small></span><span class="pax"><b>{HELIS[k]["pax"]}</b>пасс.</span></button>' for k in HELI_ORDER)
    specs = ''.join(f'<div class="spec-card" data-spec="{k}"{"" if k=="as350" else " hidden"}><h3>{HELIS[k]["name"]}</h3><div class="reg">Борт {HELIS[k]["reg"]} · {HELIS[k]["sub"]}</div><dl class="spec-list">' + ''.join(f'<div><dt>{a}</dt><dd>{b}</dd></div>' for a, b in HELIS[k]['specs']) + f'</dl><a class="btn btn-primary btn-sm" href="zakaz-poleta.html?heli={esc(HELIS[k]["form"])}">Заказать полёт</a></div>' for k in HELI_ORDER)
    services = [
        ('arenda.html', 'Аренда', 'Доставим Вас быстро\nи комфортно в любую\nточку региона', ICON['heli']),
        ('ekskursii.html', 'Экскурсии', 'Проведем незабываемые\nэкскурсии на высоте\nптичьего полета', ICON['tour']),
        ('ploshchadki.html', 'Площадки', 'Предлагаем услуги\nангарного\nхранения', ICON['hangar']),
        ('servis.html', 'Сервис', 'Проводим работы по всем\nвидам технического\nобслуживания', ICON['wrench']),
    ]
    serv_html = ''.join(f'<a class="service tilt" href="{h}"><span class="sheen"></span><div class="ico">{ic}</div><div><h3>{t}</h3><p>{d}</p></div><span class="more">Подробнее {ICON["arrow"]}</span></a>' for h, t, d, ic in services)
    board_rows = ''
    for it in [e for e in EX if e['cat'] == 'altai'][:8]:
        r0 = it['rows'][0]
        price = re.sub(r'\s*р\.?$', '', r0['price'])
        t = it['title']
        if len(t) > 38: t = t[:38].rsplit(' ', 1)[0] + '…'
        board_rows += f'<a class="board-row" href="ekskursii/{it["slug"]}.html"><span class="flap" data-flap="{esc(t)}"></span><span class="num">{r0["dur"]}</span><span class="num">от <b>{price} ₽</b></span><span class="status">Доступно</span></a>'
    hero = f'''
<section class="hero">
  <div class="clouds" aria-hidden="true"><span class="cloud c1"></span><span class="cloud c2"></span><span class="cloud c3"></span><span class="cloud c4"></span></div>
  <svg class="flightpath" viewBox="0 0 1400 700" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
    <path class="route" d="M520 690C640 560 700 470 840 420S1040 330 1120 230 1260 120 1460 110"/>
    <path class="trace" d="M520 690C640 560 700 470 840 420S1040 330 1120 230 1260 120 1460 110"/>
    <circle class="wp" cx="600" cy="596" r="5"/><text class="wp-l" x="614" y="588">Карасук</text>
    <circle class="wp" cx="840" cy="420" r="5"/><text class="wp-l" x="854" y="412">Чемал</text>
    <circle class="wp" cx="1120" cy="230" r="5"/><text class="wp-l" x="1134" y="222">Белуха 4506 м</text>
    <circle class="wp" cx="1340" cy="116" r="5"/><text class="wp-l" x="1354" y="108">Телецкое</text>
  </svg>
  <div class="hero-stage">
    <div class="viewer" id="hero-viewer" data-model="mi171" data-helipad="1" data-rotor="fast" data-hover="1" data-auto="1" data-speed="0.1" data-theta="1.05" data-phi="1.5" data-fit="auto" data-ty="8" data-fov="30" data-offset="0.66" data-flyin="1" aria-label="3D-модель вертолёта МИ-171 на площадке «Карасук» — вращайте мышью"></div>
    <div class="hero-hud"><div class="hint">{ICON['drag']} потяните, чтобы осмотреть</div><div class="tag">Борт {HELIS['mi171']['reg']}<b>МИ-171 · VIP салон</b></div></div>
  </div>
  <div class="hero-grid">
    <div class="hero-copy">
      <div class="hero-kicker"><i></i>Коммерческий авиаперевозчик · Республика Алтай</div>
      <ul class="slogans">{slog_html}</ul>
      <div class="hero-actions">
        <a class="btn btn-primary" href="zakaz-poleta.html">Заказать полет</a>
        <a class="btn btn-outline" href="ekskursii.html">Экскурсионные маршруты</a>
      </div>
      <p class="hero-note">Отправляя заявку, Вы даете согласие на обработку персональных данных в соответствии с <a href="politika.html">Условиями</a></p>
    </div>
  </div>
</section>'''
    body = hero + f'''
<section class="section">
  <div class="wrap cert-grid">
    <div class="cert-text reveal reveal-l">
      <div class="eyebrow">О компании</div>
      <h2>Сертифицированный коммерческий авиаперевозчик на Алтае</h2>
      <p>Компания «АлтайАвиа» осуществляет коммерческие воздушные перевозки. Мы — одна из самых крупных частных авиакомпаний в Сибири с выгодным расположением к соседним регионам и сетью посадочных площадок во многих популярных туристических объектах Алтая и Сибири.</p>
      <div class="hero-actions" style="margin-top:18px"><a class="btn btn-outline" href="o-kompanii.html">Подробнее о компании</a><a class="btn btn-outline" href="galereya.html">Галерея</a></div>
    </div>
    <div class="fact-board reveal reveal-r">
      <div class="board-title"><span>Бортовой журнал</span><span>KARASUK · 51°33′N 085°55′E</span></div>
      <ul>
        <li><b data-count="3">0</b><span>типа вертолётов в парке: Eurocopter AS350, МИ-8АМТ и МИ-171 с VIP-салонами</span></li>
        <li><b data-count="20">0</b><span>пассажиров — вместимость самого крупного борта</span></li>
        <li><b data-count="30">0</b><span>экскурсионных маршрутов по Горному Алтаю, Телецкому озеру, Белокурихе и Шерегешу</span></li>
        <li><b data-count="4506" data-suffix=" м">0</b><span>высота Белухи — самой высокой точки наших маршрутов</span></li>
      </ul>
    </div>
  </div>
</section>

<section class="section section-sky" id="park">
  <div class="wrap">
    <div class="section-head reveal"><div><div class="eyebrow">3D-осмотр</div><h2>Парк нашей техники:</h2></div><p>Модели построены по заводским размерам бортов авиакомпании. Вращайте сцену мышью или пальцем, включайте винты.</p></div>
    <div class="runway"></div>
    <div class="fleet">
      <div class="fleet-stage reveal">
        <div class="viewer" id="fleet-viewer" data-model="as350" data-helipad="1" data-rotor="idle" data-auto="1" data-speed="0.1" data-theta="0.7" data-phi="1.45" data-fit="auto" data-ty="3.5" data-fov="30" aria-label="3D-модель вертолёта"></div>
        <div class="shutter" aria-hidden="true"></div>
        <div class="stage-hud"><span class="chip">Live 3D</span><span class="chip">масштаб 1:1</span></div>
        <div class="stage-controls">
          <button type="button" data-rotor="stop" data-target="#fleet-viewer" title="Винты остановлены" aria-label="Остановить винты">{ICON['pause']}</button>
          <button type="button" data-rotor="idle" data-target="#fleet-viewer" title="Малый газ" aria-pressed="true" aria-label="Медленное вращение винтов">{ICON['rotor']}</button>
          <button type="button" data-rotor="fast" data-target="#fleet-viewer" title="Взлётный режим" aria-label="Быстрое вращение винтов">{ICON['plane']}</button>
          <button type="button" data-autorotate data-target="#fleet-viewer" title="Авто-облёт камерой" aria-pressed="true" aria-label="Автоматический облёт камерой">{ICON['rotate']}</button>
        </div>
      </div>
      <div class="fleet-side reveal reveal-r">
        <div class="fleet-tabs" role="tablist" aria-label="Выбор вертолёта">{tabs}</div>
        {specs}
      </div>
    </div>
  </div>
</section>

<section class="section">
  <div class="wrap">
    <div class="section-head reveal"><div><div class="eyebrow">Табло вылетов</div><h2>Экскурсионные маршруты</h2></div><p>Цена «от» — за полёт на Eurocopter AS350. Старт с посадочной площадки «Карасук».</p></div>
    <div class="board reveal">
      <div class="board-head"><span>Маршрут</span><span>Время</span><span>Стоимость</span><span>Статус</span></div>
      {board_rows}
      <div class="board-foot"><span>Все 30 маршрутов, включая экскурсии с курорта Altay Village</span><a href="ekskursii.html">Смотреть все маршруты →</a></div>
    </div>
  </div>
</section>

<section class="section section-sky">
  <div class="wrap">
    <div class="section-head reveal"><div><div class="eyebrow">Направления</div><h2>Наши услуги</h2></div></div>
    <div class="services stagger">{serv_html}</div>
  </div>
</section>
'''
    write('index.html', page(root=root, title='Авиакомпания АлтайАвиа | официальный сайт', desc='Аренда вертолётов по городам Сибири, уникальные экскурсионные маршруты по Горному Алтаю, сервисное обслуживание и ангарное хранение вертолётов. Посадочная площадка «Карасук», Республика Алтай.', active='', body=body, scripts_3d=True, models=('mi171', 'mi8amt')))
