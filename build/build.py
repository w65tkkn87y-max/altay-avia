# -*- coding: utf-8 -*-
"""Генератор статического сайта «АлтайАвиа». Запуск: python3 build/build.py"""
import json, os, re, html as H
from common import *

# ширина рендера борта на карточках относительно Ми-8 (по длине с винтами: 12.9 м против 25.4 м)
SCALE_K = {'as350': 0.56, 'mi8amt': 1, 'mi171': 1}
BAND_HELI = {'as350': 'img/gallery/evro-2025/e003.jpg', 'mi8amt': 'img/gallery/mi8amt/01-000.jpg', 'mi171': 'img/gallery/foto24/20250728_142818.jpg'}

EX = json.load(open(os.path.join(DATA, 'excursions.json'), encoding='utf-8'))
POLICY = open(os.path.join(DATA, 'politika_body.html'), encoding='utf-8').read()

def merge_desc(lines):
    """Склеивает фрагменты описания (жирные вставки, разрывы строк) в абзацы."""
    out = []
    for l in lines:
        l = l.strip()
        if not l: continue
        if out and not re.search(r'[.!?…:]["»)]?$', out[-1]):
            sep = '' if l[0] in ',.;:!?' else ' '
            out[-1] = out[-1] + sep + l
        else:
            out.append(l)
    return [re.sub(r'\s+', ' ', o).replace(' - ', ' — ') for o in out]

def esc(s): return H.escape(s, quote=True)

# ---------------------------------------------------------------- Главная
from index_page import build_index as _build_index
def build_index():
    _build_index(EX, esc)

# ---------------------------------------------------------------- Аренда
def build_arenda():
    root = ''
    rows = ''.join(f'''<div class="pass">
  <div class="thumb"><img src="img/3d/{k}-side.png" alt="{HELIS[k]['name']}" loading="lazy" style="--k:{SCALE_K[k]}"></div>
  <div class="name"><b>{HELIS[k]['name']}</b><small>{HELIS[k]['sub']}</small></div>
  <div class="kv pax"><small>Кол-во пассажиров</small><b>{HELIS[k]['pax']}</b></div>
  <div class="kv price"><small>Стоимость, 1 час</small><b>{HELIS[k]['price']}</b></div>
  <a class="btn btn-primary btn-sm" href="zakaz-poleta.html?heli={esc(HELIS[k]['form'])}">заказать</a>
</div>''' for k in HELI_ORDER)
    purposes = [('Бизнес и VIP\nполеты', ICON['brief']), ('Чартерные\nперелеты', ICON['charter']), ('Экскурсии\nи путешествия', ICON['compass']), ('Доставка\nв аэропорт', ICON['airport']), ('Фото и видео\nсъемка', ICON['camera'])]
    purp = ''.join(f'<div class="purpose">{ic}<b>{t}</b></div>' for t, ic in purposes)
    body = band(root, 'Аренда вертолетов', 'slider-arenda.jpg', [(None, 'Аренда')], 'Компания «АлтайАвиа» предлагает в аренду современные вертолеты!') + f'''
<section class="section">
  <div class="wrap">
    <div class="section-head reveal"><div><div class="eyebrow">Тарифы</div><h2>Стоимость аренды вертолетов</h2></div><p>Цена указана за один лётный час. Итоговая стоимость маршрута рассчитывается по общему времени аренды.</p></div>
    <div class="price-head"><span>Модель вертолета</span><span></span><span>Кол-во пассажиров</span><span>Стоимость, 1 час</span><span></span></div>
    <div class="price-list stagger">{rows}</div>
    <p class="prose" style="margin-top:32px;font-size:17px">Сегодня аренда вертолета чаще привлекается для туристических целей, деловых поездок, отдыха или чтобы попасть в непроходимое место. С высоты птичьего полета видна красивая панорама, а также можно сделать неповторимые снимки, которые оставят память на всю жизнь. Заказать вертолет можно на торжественное событие, тогда он сделает праздник запоминающимся и необычным.</p>
  </div>
</section>
<section class="section section-ice">
  <div class="wrap">
    <div class="section-head reveal"><h2>Для чего можно арендовать вертолет?</h2></div>
    <div class="purposes stagger">{purp}</div>
  </div>
</section>
<section class="section">
  <div class="wrap">
    <div class="section-head reveal"><div><h2>Как арендовать вертолет?</h2></div><p>Для того, чтобы арендовать вертолет или заказать индивидуальный маршрут, Вам необходимо выбрать наиболее удобный для вас способ:</p></div>
    <div class="ways">
      <div class="way reveal"><b>По телефону отдела продаж</b><p><a href="{PHONE_HREF}">{PHONE}</a><br>{PHONE_NOTE}</p></div>
      <div class="way reveal"><b>В офисе продаж в Республике Алтай</b><p>Чемальский район, с. Чепош, Посадочная площадка «Карасук»</p></div>
      <div class="way reveal"><b>Отправить заявку на почту</b><p><a href="mailto:brn@altay-avia.ru">brn@altay-avia.ru</a>, <a href="mailto:info@altay-avia.ru">info@altay-avia.ru</a></p></div>
      <div class="way reveal"><b>Заполнить форму обратной связи</b><p>Ниже на этой странице — мы перезвоним и рассчитаем стоимость</p></div>
    </div>
    <div class="order-layout" style="margin-top:40px">
      <div>{order_form(root, 'flight', subject='Заявка на аренду вертолёта')}</div>
      <aside class="order-side reveal reveal-r"><div class="pic"><img src="img/3d/as350.png" alt="Eurocopter AS350" loading="lazy"></div><p class="note">Eurocopter AS350 — самый популярный борт для аренды: 5 пассажиров, посадки на неподготовленные площадки.</p></aside>
    </div>
  </div>
</section>'''
    write('arenda.html', page(root=root, title='Аренда вертолётов в Алтайском крае и Республике Алтай', desc='Стоимость аренды вертолётов Eurocopter AS350, МИ-8АМТ и МИ-171 за лётный час. Бизнес и VIP-полёты, чартеры, экскурсии, доставка в аэропорт, фото- и видеосъёмка.', active='arenda', body=body))

# ---------------------------------------------------------------- Экскурсии
def route_card(it, root):
    dur = it['rows'][0]['dur'] if it['rows'] else ''
    price = it['rows'][0]['price'].replace('р', '₽').replace(' ₽', ' ₽') if it['rows'] else ''
    price = re.sub(r'\s*р\.?$', ' ₽', it['rows'][0]['price']) if it['rows'] else ''
    desc = ' '.join(merge_desc(it['desc']))
    first = re.split(r'(?<=[.!?])\s', desc)[0] if desc else ''
    img = f'<img src="{root}{it["img"]}" alt="{esc(it["title"])}" loading="lazy">' if it['img'] else ''
    keys = sorted({heli_key(r['heli']) for r in it['rows']})
    attrs = f'data-min="{dur_min(dur)}" data-price="{price_int(it["rows"][0]["price"]) if it["rows"] else 0}" data-helis="{" ".join(keys)}"'
    return f'''<a class="route tilt" href="{root}ekskursii/{it['slug']}.html" {attrs} data-cursor="Маршрут">
  <div class="pic">{img}<span class="dur">⏱ {dur}</span></div>
  <div class="txt"><h3>{esc(it['title'])}</h3><p>{esc(first)}</p></div>
  <div class="foot"><span class="from">от <b>{price}</b></span><span class="more">Подробнее →</span></div>
</a>'''

def build_ekskursii():
    root = ''
    n_alt = sum(1 for e in EX if e['cat'] == 'altai'); n_vil = sum(1 for e in EX if e['cat'] == 'village')
    body = band(root, 'Экскурсии на вертолёте', 'video-fon.jpg', [(None, 'Экскурсии')]) + f'''
<section class="section">
  <div class="wrap">
    <div class="dir-grid">
      <a class="dir-card reveal" href="ekskursii/gornyj-altay.html"><img src="img/eks/eks23-b-bel1007.jpg" alt="" loading="lazy"><span class="count">{n_alt} маршрутов</span><div class="body"><h3>Экскурсии по Горному Алтаю</h3><p>Старт с посадочной площадки «Карасук» — Катунь, Белуха, Телецкое озеро, плато Укок и другие маршруты</p></div></a>
      <a class="dir-card reveal" href="ekskursii/altay-village.html"><img src="img/eks/eks23-b-t00.jpg" alt="" loading="lazy"><span class="count">{n_vil} маршрутов</span><div class="body"><h3>Экскурсии с Altay Village</h3><p>Маршруты для гостей курорта Altay Village Телецкое</p></div></a>
    </div>
    <div class="prose reveal" style="margin-top:44px">
      <p>Полет на вертолете — это увлекательный отдых и прекрасный способ получить необычные ощущения и незабываемые эмоции. Любое мероприятие — свидание, день рождения или просто прогулка — станут более удивительными на борту вертолета, движущемуся на высоте птичьего полета. Благодаря большим обзорным окнам вам доступен роскошный вид за бортом. А возможность вертолета регулировать скорость и зависать над объектами, позволяет лучше рассмотреть понравившиеся места.</p>
      <p>Полет на вертолете может стать одним из лучших подарков для тех, кто ценит не вещи, а впечатления. Сказочное воздушное приключение наполнит вас эмоциями и навсегда останется в памяти!</p>
    </div>
  </div>
</section>'''
    write('ekskursii.html', page(root=root, title='Экскурсии на вертолёте по Барнаулу, Горному Алтаю и Белокурихе', desc='Вертолётные экскурсии по Горному Алтаю и с курорта Altay Village: Катунь, Белуха, Телецкое озеро, Каракольские озёра, плато Укок, Белокуриха, Шерегеш.', active='ekskursii', body=body))

    for cat, fname, title, bandimg, sub in [
        ('altai', 'gornyj-altay', 'Экскурсии на вертолёте по Горному Алтаю', 'img/gallery/foto24/20240725_141140.jpg', 'Начало и завершение маршрутов — на посадочной площадке «Карасук», с. Чепош, Чемальский район.'),
        ('village', 'altay-village', 'Экскурсии на вертолёте с Altay Village', 'img/gallery/foto24/20240725_141142.jpg', 'Маршруты для гостей курорта Altay Village Телецкое.')]:
        root = '../'
        items = [e for e in EX if e['cat'] == cat]
        cards = ''.join(route_card(it, root) for it in items)
        body = band(root, title, bandimg, [('ekskursii.html', 'Экскурсии'), (None, title.replace('Экскурсии на вертолёте ', ''))], sub) + f'''
<section class="section"><div class="wrap">
  <div class="section-head reveal"><div><div class="eyebrow">{len(items)} маршрутов</div><h2>Выберите маршрут</h2></div><p>Цена «от» — за полёт на Eurocopter AS350 (до 5 пассажиров). Для групп доступны МИ-8АМТ и МИ-171.</p></div>
  <div class="route-filter" data-filter="#routes" role="group" aria-label="Фильтр маршрутов">
    <div class="rf-group" role="radiogroup" aria-label="Длительность"><small>Время</small>
      <button type="button" data-f-dur="all" aria-pressed="true">Любое</button><button type="button" data-f-dur="0-60" aria-pressed="false">до 1 часа</button><button type="button" data-f-dur="61-180" aria-pressed="false">1–3 часа</button><button type="button" data-f-dur="181-9999" aria-pressed="false">более 3 часов</button></div>
    <div class="rf-group" role="radiogroup" aria-label="Борт"><small>Борт</small>
      <button type="button" data-f-heli="all" aria-pressed="true">Любой</button><button type="button" data-f-heli="as350" aria-pressed="false">AS350</button><button type="button" data-f-heli="mi8amt" aria-pressed="false">МИ-8АМТ</button><button type="button" data-f-heli="mi171" aria-pressed="false">МИ-171</button></div>
    <label class="rf-sort"><small>Сортировка</small><select data-f-sort><option value="">по популярности</option><option value="price">сначала дешевле</option><option value="-price">сначала дороже</option><option value="min">сначала короче</option></select></label>
    <span class="rf-count" aria-live="polite"><b data-f-count>{len(items)}</b> из {len(items)}</span>
  </div>
  <div class="routes stagger" id="routes">{cards}</div>
  <p class="rf-empty" hidden>Нет маршрутов с такими условиями — <button type="button" data-f-reset>сбросить фильтр</button></p>
</div></section>'''
        write(f'ekskursii/{fname}.html', page(root=root, title=title, desc=f'{title}: {len(items)} маршрутов с ценами и продолжительностью полёта на Eurocopter AS350, МИ-8АМТ и МИ-171.', active='ekskursii', body=body))

    # страницы маршрутов
    for it in EX:
        root = '../'
        cat_title = 'Экскурсии по Горному Алтаю' if it['cat'] == 'altai' else 'Экскурсии с Altay Village'
        cat_href = 'ekskursii/gornyj-altay.html' if it['cat'] == 'altai' else 'ekskursii/altay-village.html'
        rows = ''
        heli_keys = []
        for r in it['rows']:
            name = r['heli'].replace(' (Vip салон)', '')
            sub = 'VIP салон' if 'Vip' in r['heli'] else ('Écureuil (H125)' if 'AS350' in r['heli'] else '')
            price = re.sub(r'\s*р\.?$', ' ₽', r['price'])
            key = 'as350' if 'AS350' in name else ('mi8amt' if '8АМТ' in name else 'mi171')
            heli_keys.append(key)
            rows += f'''<div class="row"><div><b>{esc(name)}</b><small>{sub}</small></div><div class="price">{price}</div><div class="meta"><span>{ICON['users']} {r['pax']} пасс.</span><span>{ICON['clock']} {r['dur']}</span></div></div>'''
        desc_html = ''.join(f'<p>{esc(p)}</p>' for p in merge_desc(it['desc']))
        extra = [u for u in it.get('imgs_all', []) if ('/eks' in u) and u != it['img'] and 'passaghir' not in u]
        extra_local = []
        for u in extra:
            loc = 'img/eks/' + u.replace('/images/', '').replace('/', '-')
            if os.path.exists(os.path.join(SITE, loc)) and loc != it['img']: extra_local.append(loc)
        gal = ''
        if extra_local:
            gal = '<div class="photo-strip">' + ''.join(f'<a href="{root}{l}" data-lightbox="route" data-caption="{esc(it["title"])}"><img src="{root}{l}" alt="" loading="lazy"></a>' for l in extra_local) + '</div>'
        hero_img = f'<div class="route-hero"><img src="{root}{it["img"]}" alt="{esc(it["title"])}"></div>' if it['img'] else ''
        body = band(root, it['title'], 'video-fon.jpg', [('ekskursii.html', 'Экскурсии'), (cat_href, cat_title.replace('Экскурсии ', ''))]) + f'''
<section class="section"><div class="wrap route-page">
  <article>
    {hero_img}
    <div class="prose">{desc_html}</div>
    {gal}
    <p class="route-note" style="margin-top:24px">{esc(it['note'])}</p>
    <div style="margin-top:44px">
      <div class="section-head"><div><div class="eyebrow">Индивидуальный маршрут</div><h2>Хотите составить индивидуальный маршрут?</h2></div><p>Для заказа индивидуального полета Вам необходимо выбрать наиболее удобный для вас способ связи:</p></div>
      <div class="ways" style="grid-template-columns:repeat(2,1fr)">
        <div class="way"><b>В офисе продаж в Республике Алтай</b><p>Чемальский район, с. Чепош, Посадочная площадка «Карасук»</p></div>
        <div class="way"><b>По телефону офиса продаж</b><p><a href="{PHONE_HREF}">{PHONE}</a></p></div>
        <div class="way"><b>Отправить заявку на почту</b><p><a href="mailto:info@altay-avia.ru">info@altay-avia.ru</a></p></div>
        <div class="way"><b>Заполнить форму обратной связи</b><p>Оставьте контактные данные и мы свяжемся с Вами</p></div>
      </div>
    </div>
  </article>
  <aside class="route-sticky">
    <div class="tariff">
      <div class="head"><span>Стоимость и время экскурсии*</span><span>{it['rows'][0]['dur'] if it['rows'] else ''}</span></div>
      {rows}
      <div class="cta"><a class="btn btn-primary" href="{root}zakaz-poleta.html?route={esc(it['title'])}">заказать</a><p class="note">* Считается общее время аренды вертолета, т.е. в две стороны.</p></div>
    </div>
    <div id="order">
      <h3 style="font-size:20px">Заказ экскурсии</h3>
      <p class="note">Оставьте контактные данные и мы свяжемся с Вами</p>
      {order_form(root, 'short', route=esc(it['title']), helis=list(dict.fromkeys(heli_keys)) or None, subject='Заказ экскурсии')}
      <p class="note" style="margin-top:10px">Отправляя заявку, Вы даете согласие на обработку персональных данных в соответствии с <a href="{root}politika.html">Условиями</a></p>
    </div>
  </aside>
</div></section>'''
        write(f'ekskursii/{it["slug"]}.html', page(root=root, title=f'{it["title"]} — вертолётная экскурсия | АлтайАвиа', desc=(' '.join(it['desc'])[:155] + '…') if it['desc'] else it['title'], active='ekskursii', body=body))

# ---------------------------------------------------------------- Площадки
def karasuk_map(root):
    return f'''<div class="map-box" aria-label="Схема расположения площадки «Карасук»">
  <svg viewBox="0 0 600 420" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
    <defs><pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse"><path d="M40 0H0V40" fill="none" stroke="#2E86DE" stroke-opacity=".18"/></pattern></defs>
    <rect width="600" height="420" fill="#0E2244"/><rect width="600" height="420" fill="url(#grid)"/>
    <g fill="none" stroke="#5AA7F0" stroke-opacity=".35"><path d="M-20 300c80-40 140-10 210-60s120-120 220-110 150 60 210 40"/><path d="M-20 340c80-40 140-10 210-60s120-120 220-110 150 60 210 40"/><path d="M-20 260c80-40 140-10 210-60s120-120 220-110 150 60 210 40"/></g>
    <path d="M40 420C120 330 160 300 230 250S330 160 420 120s110-60 180-70" fill="none" stroke="#7FC0FF" stroke-width="7" stroke-linecap="round" opacity=".8"/>
    <text x="300" y="196" fill="#BFE0FF" font-family="Oswald, Arial Narrow, sans-serif" font-size="12" transform="rotate(-38 300 196)">р. Катунь</text>
    <path d="M0 400C150 380 260 330 330 300s160-90 270-80" fill="none" stroke="#F2C230" stroke-width="2" stroke-dasharray="2 8" opacity=".9"/>
    <text x="420" y="240" fill="#F2C230" font-family="Oswald, Arial Narrow, sans-serif" font-size="11" letter-spacing="1">Чуйский тракт</text>
    <g transform="translate(270 262)"><circle r="38" fill="none" stroke="#F2C230" stroke-width="3"/><circle r="52" fill="none" stroke="#F2C230" stroke-opacity=".35" stroke-width="1.5" stroke-dasharray="4 6"/><text y="10" text-anchor="middle" fill="#F2C230" font-family="Unbounded, Arial, sans-serif" font-size="34" font-weight="800">H</text></g>
    <text x="270" y="335" text-anchor="middle" fill="#fff" font-family="Unbounded, Arial, sans-serif" font-size="16" font-weight="700">Площадка «Карасук»</text>
    <text x="270" y="354" text-anchor="middle" fill="#BFE0FF" font-family="Oswald, Arial Narrow, sans-serif" font-size="12">51°33′36″ N · 085°55′03″ E</text>
    <text x="470" y="70" fill="#BFE0FF" font-family="Oswald, Arial Narrow, sans-serif" font-size="12">с. Чепош ↗</text>
    <text x="60" y="60" fill="#BFE0FF" font-family="Oswald, Arial Narrow, sans-serif" font-size="12">Горно-Алтайск ↖ 60 км</text>
    <g transform="translate(540 370)" fill="none" stroke="#fff" stroke-opacity=".7"><circle r="18"/><path d="M0-18v36M-18 0h36"/><path d="M0-18l5 10h-10z" fill="#fff"/></g>
  </svg>
  <div class="map-links"><a href="https://yandex.ru/maps/?pt=85.9175,51.56&z=13&l=map" target="_blank" rel="noopener">Яндекс Карты</a><a href="https://2gis.ru/geo/85.9175,51.56" target="_blank" rel="noopener">2ГИС</a><a href="https://www.google.com/maps?q=51.56,85.9175" target="_blank" rel="noopener">Google Maps</a></div>
</div>'''

def build_ploshchadki():
    root = ''
    photos = ['img/gallery/karasuk25/a1.jpg', 'img/gallery/karasuk25/a2.jpg', 'img/gallery/karasuk25/p003.jpg', 'img/gallery/karasuk25/p004.jpg']
    strip = ''.join(f'<a href="{p}" data-lightbox="karasuk" data-caption="Посадочная площадка «Карасук»"><img src="{p}" alt="Посадочная площадка «Карасук»" loading="lazy"></a>' for p in photos)
    body = band(root, 'Посадочные площадки для вертолетов', 'img/gallery/karasuk25/a1.jpg', [(None, 'Площадки')]) + f'''
<section class="section"><div class="wrap">
  <div class="site-card reveal">
    <div class="info">
      <span class="region">Республика Алтай</span>
      <h2>Посадочная площадка «Карасук»</h2>
      <dl class="kv-list">
        <div><dt>Тел.</dt><dd><a href="{PHONE_HREF}">{PHONE}</a></dd></div>
        <div><dt>Сот.</dt><dd><a href="{MOBILE_HREF}">{MOBILE}</a></dd></div>
        <div><dt>Почта</dt><dd><a href="mailto:info@altay-avia.ru">info@altay-avia.ru</a></dd></div>
        <div><dt>Координаты</dt><dd class="coords"><span>51° 33′ 36″ С</span><span>085° 55′ 03″ В</span></dd></div>
      </dl>
    </div>
    {karasuk_map(root)}
  </div>
  <div class="photo-strip reveal">{strip}</div>
  <div class="callout reveal" style="margin-top:40px"><div><h3>Ангарное хранение</h3><p>Компания «АлтайАвиа» предлагает услуги по ангарному хранению вертолетов на нашей посадочной площадке.</p></div><a class="btn btn-primary" href="servis.html">Условия сервиса</a></div>
</div></section>'''
    write('ploshchadki.html', page(root=root, title='Посадочные площадки авиакомпании Алтай Авиа', desc='Посадочная площадка «Карасук» в Республике Алтай: контакты, координаты, ангарное хранение вертолётов.', active='ploshchadki', body=body))

# ---------------------------------------------------------------- Сервис
def build_servis():
    root = ''
    docs = ''.join(f'<a href="img/gallery/servis/{f}" data-lightbox="servis" data-caption="Сертификат авиационно-технической базы"><img src="img/gallery/servis/{f}" alt="Сертификат" loading="lazy"></a>' for f in ['001.jpg', '002.jpg', '004.jpg'])
    extras = [('Базирование, ангарное хранение вертолетов типа Robinson, Eurocopter, Bell, MD, МИ-8', ICON['hangar']),
              ('Установка на стоянку/выпуск и оперативная подготовка воздушных судов до трёх тонн', ICON['heli']),
              ('Заправка ГСМ: авиационный керосин ТС-1; авиационный бензин 100 LL (по предварительному заказу)', ICON['fuel']),
              ('Предпродажная подготовка вертолетов Robinson, Eurocopter AS350, МИ-8', ICON['check']),
              ('Продажа оборудования, расходных материалов для вертолетов', ICON['tag']),
              ('Предполетная подготовка в рамках договора на техническое обслуживание', ICON['wrench'])]
    ex = ''.join(f'<li>{ic}<span>{t}</span></li>' for t, ic in extras)
    body = band(root, 'Сервисное обслуживание вертолетов', 'slider-servis.jpg', [(None, 'Сервис')]) + f'''
<section class="section"><div class="wrap split">
  <div class="prose reveal">
    <div class="eyebrow">Авиационно-техническая база</div>
    <p>Компания «АлтайАвиа» имеет сертифицированную авиационно-техническую базу.</p>
    <p>Инженеры компании проводят работы по всем видам технического обслуживания как своих вертолетов, так и по обращению клиентов: авиакомпаний, корпоративных заказчиков, частных владельцев вертолетов и предоставляет сервисное обслуживание вертолетов типа Robinson R44, Robinson R66, Eurocopter AS350, МИ-8 всех типов.</p>
  </div>
  <div class="reveal"><div class="eyebrow">Сертификаты</div><div class="docs-row">{docs}</div></div>
</div></section>
<section class="section section-ice"><div class="wrap">
  <div class="section-head reveal"><h2>Дополнительные услуги, оказываемые технической службой «АлтайАвиа»:</h2></div>
  <ul class="extra-list stagger">{ex}</ul>
  <p class="prose reveal" style="margin-top:32px">Территория вертодрома огорожена, круглосуточно охраняется и полностью соответствует требованиям к авиационным объектам.</p>
  <div class="callout reveal"><div><h3>Доверьте обслуживание вашего вертолета профессионалам!</h3><p>Позвоните нам или оставьте заявку — рассчитаем стоимость обслуживания и хранения.</p></div><a class="btn btn-primary" href="{PHONE_HREF}">{PHONE}</a></div>
</div></section>'''
    write('servis.html', page(root=root, title='Сервисное обслуживание вертолётов на Алтае', desc='Сертифицированная авиационно-техническая база «АлтайАвиа»: техобслуживание вертолётов Robinson R44/R66, Eurocopter AS350, МИ-8; ангарное хранение, заправка ГСМ, предпродажная подготовка.', active='servis', body=body))

# ---------------------------------------------------------------- О компании
def build_about():
    root = ''
    certs = ''.join(f'<a href="img/gallery/sertif2023/{f}" data-lightbox="cert" data-caption="Сертификат эксплуатанта"><img src="img/gallery/sertif2023/{f}" alt="Сертификат" loading="lazy"></a>' for f in ['page-0001.jpg', 'page-0004.jpg', 'page-0006.jpg'])
    cards = ''.join(f'<a class="heli-card tilt" href="vertolety/{k}.html"><div class="pic"><img src="img/3d/{k}-side.png" alt="{HELIS[k]["name"]}" loading="lazy" style="--k:{SCALE_K[k]}"></div><div class="txt"><h3>{HELIS[k]["name"]}</h3><small>{HELIS[k]["sub"]}</small><div class="pax">Кол-во пассажиров: <b>{HELIS[k]["pax"]}</b></div></div></a>' for k in HELI_ORDER)
    body = band(root, 'О компании', 'fon.jpg', [(None, 'О компании')]) + f'''
<section class="section"><div class="wrap">
  <div class="group-banner reveal"><img src="img/misc/pa2025.png" alt="Premier Avia Group"><div><b>С 1 октября 2023 года Авиакомпания АлтайАвиа вошла в состав <a href="{PREMIER}" target="_blank" rel="noopener">PREMIER AVIA GROUP</a>.</b><p>Группа компаний Premier Avia объединяет вертолётных операторов и сервисные базы.</p></div></div>
  <p class="lead reveal" style="margin-top:32px">«АлтайАвиа» – одна из самых крупных вертолетных компаний в Сибири с выгодным расположением к соседним регионам, располагающей сетью посадочных площадок на многих популярных туристических объектах Алтая.</p>
</div></section>
<section class="section section-ice"><div class="wrap">
  <div class="section-head reveal"><h2>Почему стоит выбрать именно нас?</h2></div>
  <ol class="reasons">
    <li class="reveal">Большой парк вертолётов позволяет насладиться полётом с максимальным комфортом.</li>
    <li class="reveal">Уникальные маршруты разработанные нашей компанией, включающие полёты над живописной территорией Республики Алтай, покорят ваше сердце восхитительной красотой алтайской природы.</li>
    <li class="reveal">Профессиональные пилоты гарантируют полную безопасность пассажиров с момента взлёта до приземления.</li>
  </ol>
</div></section>
<section class="section"><div class="wrap split">
  <div>
    <div class="eyebrow">Документы</div>
    <div class="doc-links">
      <a class="doc-link reveal" href="docs/pravila-v-p-26.pdf" target="_blank" rel="noopener">{ICON['pdf']}<span>Правила воздушных перевозок ООО АлтайАвиа<small>PDF</small></span>{ICON['arrow']}</a>
      <a class="doc-link reveal" href="sout.html">{ICON['doc']}<span>Данные по спец.оценке условий труда (СОУТ)<small>Ведомости и перечни мероприятий, 2021–2025</small></span>{ICON['arrow']}</a>
    </div>
  </div>
  <div><div class="eyebrow">Сертификаты</div><div class="docs-row reveal">{certs}</div></div>
</div></section>
<section class="section section-ice"><div class="wrap">
  <div class="section-head reveal"><div><h2>Парк нашей техники:</h2></div><a class="btn btn-outline" href="index.html#park">Осмотреть в 3D</a></div>
  <div class="heli-cards stagger">{cards}</div>
</div></section>'''
    write('o-kompanii.html', page(root=root, title='О авиакомпании Алтай Авиа', desc='«АлтайАвиа» — одна из крупнейших вертолётных компаний Сибири, входит в Premier Avia Group. Парк: Eurocopter AS350, МИ-8АМТ, МИ-171. Правила воздушных перевозок, СОУТ, сертификаты.', active='o-kompanii', body=body))

# ---------------------------------------------------------------- Галерея
def build_gallery():
    root = ''
    blocks = [('МИ-8АМТ (VIP салон)', 'Вместимость до 20 пассажиров', 'mi8amt', ['01-000.jpg', '01-00001.jpg', '01-00002.jpg', '01-0004.jpg']),
              ('МИ-171 (VIP салон)', 'Вместимость до 9 пассажиров', 'mi171-2025', ['0001.jpg', '0002.jpg', '0003.jpg', '0004.jpg']),
              ('Eurocopter AS350', 'Вместимость до 5 пассажиров', 'evro-2025', ['e001.jpg', 'e002.jpg', 'e003.jpg', 'e004.jpg']),
              ('Полёты по Алтаю', 'Маршруты, площадки, ангары', 'foto24', ['20240725_141135.jpg', '20240725_141138.jpg', '20240725_141140.jpg', '20240725_141142.jpg', '20240725_141146.jpg', '20250728_142818.jpg'])]
    html = ''
    for t, s, d, files in blocks:
        imgs = ''.join(f'<a href="img/gallery/{d}/{f}" data-lightbox="{d}" data-caption="{esc(t)}"><img src="img/gallery/{d}/{f}" alt="{esc(t)}" loading="lazy"></a>' for f in files)
        html += f'<div class="gallery-block reveal"><div class="head"><h2>{t}</h2><span>{s}</span></div><div class="gallery-grid">{imgs}</div></div>'
    body = band(root, 'Галерея', 'slider-hranenie.jpg', [(None, 'Галерея')]) + f'<section class="section"><div class="wrap">{html}</div></section>'
    write('galereya.html', page(root=root, title='Галерея авиакомпании Алтай Авиа', desc='Фотографии вертолётов МИ-8АМТ, МИ-171 и Eurocopter AS350 авиакомпании «АлтайАвиа», салоны и вертодром «Карасук».', active='galereya', body=body))

# ---------------------------------------------------------------- Онлайн-оплата
def build_pay():
    root = ''
    def payform(kind, title, vat):
        return f'''<div class="pay-card reveal"><div class="head"><h2>{title}</h2><small>{vat}</small></div>
<form data-form="pay-{kind}" data-subject="Онлайн-оплата: {title}" novalidate>
  <div class="field"><label for="{kind}-order">Номер договора / счёта <span class="req">*</span></label><input id="{kind}-order" name="order" type="text" required></div>
  <div class="field"><label for="{kind}-name">ФИО плательщика <span class="req">*</span></label><input id="{kind}-name" name="name" type="text" required autocomplete="name"></div>
  <div class="field"><label for="{kind}-phone">Телефон <span class="req">*</span></label><input id="{kind}-phone" name="phone" type="tel" required autocomplete="tel"></div>
  <div class="field"><label for="{kind}-email">Email <span class="req">*</span></label><input id="{kind}-email" name="email" type="email" required autocomplete="email"></div>
  <div class="field"><label for="{kind}-sum">Сумма, ₽ <span class="req">*</span></label><input id="{kind}-sum" name="amount" type="number" min="1" step="1" required inputmode="numeric"></div>
  <label class="check"><input type="checkbox" name="consent" required value="да"><span>Согласен с <a href="#rules">правилами оплаты</a> и обработкой персональных данных в соответствии с <a href="politika.html">Условиями</a></span></label>
  <div class="form-actions"><button class="btn btn-primary" type="submit">Перейти к оплате</button><span class="form-status" role="status" aria-live="polite"></span></div>
  <div class="cards-row"><span>VISA</span><span>MasterCard</span><span>МИР</span></div>
</form></div>'''
    body = band(root, 'Онлайн оплата', 'img/gallery/karasuk25/p003.jpg', [(None, 'On-line оплата')]) + f'''
<section class="section"><div class="wrap">
  <div class="pay-grid">
    {payform('perev', 'Оплата за услугу "Коммерческие воздушные перевозки"', 'НДС — 0%')}
    {payform('rab', 'Оплата за услугу "Авиационные работы"', 'НДС — 20%')}
  </div>
</div></section>
<section class="section section-ice" id="rules"><div class="wrap split">
  <div class="prose reveal">
    <h2>Правила оплаты</h2>
    <p>К оплате принимаются платежные карты: VISA Inc, MasterCard WorldWide. Для оплаты товара банковской картой при оформлении заказа в интернет-магазине выберите способ оплаты: банковской картой.</p>
    <p>При оплате заказа банковской картой, обработка платежа происходит на авторизационной странице банка, где Вам необходимо ввести данные Вашей банковской карты:</p>
    <ul><li>Тип карты,</li><li>Номер карты,</li><li>Срок действия карты (указан на лицевой стороне карты),</li><li>Имя держателя карты (латинскими буквами, точно также как указано на карте),</li><li>CVC2/CVV2 код.</li></ul>
    <p>Если Ваша карта подключена к услуге 3D-Secure, Вы будете автоматически переадресованы на страницу банка, выпустившего карту, для прохождения процедуры аутентификации. Информацию о правилах и методах дополнительной идентификации уточняйте в Банке, выдавшем Вам банковскую карту.</p>
    <p>Безопасность обработки интернет-платежей через платежный шлюз банка гарантирована международным сертификатом безопасности PCI DSS. Передача информации происходит с применением технологии шифрования SSL. Эта информация недоступна посторонним лицам.</p>
    <h3>Советы и рекомендации по необходимым мерам безопасности проведения платежей с использованием банковской карты:</h3>
    <ul>
      <li>Берегите свои пластиковые карты так же, как бережете наличные деньги. Не забывайте их в машине, ресторане, магазине и т.д.</li>
      <li>Никогда не передавайте полный номер своей кредитной карты по телефону каким-либо лицам или компаниям</li>
      <li>Всегда имейте под рукой номер телефона для экстренной связи с банком, выпустившим вашу карту, и в случае ее утраты немедленно свяжитесь с банком</li>
      <li>Вводите реквизиты карты только при совершении покупки. Никогда не указывайте их по каким-то другим причинам.</li>
    </ul>
  </div>
  <div class="prose reveal">
    <h2>Возмещение расходов Заказчиком</h2>
    <p>В случае посадки ВС в аэропорту Заказчик дополнительно возмещает фактические расходы, понесенные авиакомпанией:</p>
    <ul><li>по метео и аэронавигационному обслуживанию,</li><li>аэропортовые сборы,</li><li>расходы за наземное обслуживание экипажа, пассажиров и груза.</li></ul>
    <p>В случае необходимости доставки ГСМ к месту работ (по согласованию с Исполнителем), Заказчик возмещает расходы, понесенные авиакомпанией по доставке ГСМ.</p>
    <p>Данные расходы Заказчик оплачивает авиакомпании на основании универсального передаточного документа после оказания услуг.</p>
    <h2>Возврат авиакомпанией денежных средств Заказчику авиационной услуги</h2>
    <p>В случае, если фактический налет часов оказался меньше, чем оплачено Заказчиком, то авиакомпания возвращает денежные средства путем перечисления на расчетный счет Заказчика по его письменному заявлению в течение 5 банковских дней.</p>
    <p>В случае отмены полета по причине ухудшения метеоусловий либо возникновения иных форс-мажорных обстоятельств, авиакомпания возвращает денежные средства Заказчику на основании его письменного заявления путем перечисления на расчетный счет Заказчика в течение 5 банковских дней.</p>
    <p>В случае отказа Заказчиком от поданной заявки в день вылета оплачивается неустойка в размере 0,1 % от общей цены договора, в том числе НДС.</p>
  </div>
</div></section>
<section class="section"><div class="wrap">
  <div class="section-head reveal"><h2>Реквизиты организации</h2></div>
  <div class="table-wrap reveal"><table class="req-table">
    <tr><th>Название компании</th><td>ООО "АлтайАвиа"</td></tr>
    <tr><th>ИНН/ОГРН</th><td class="mono">0411160184 / 1120411001985</td></tr>
    <tr><th>Телефон</th><td><a href="{PHONE_HREF}">{PHONE}</a></td></tr>
    <tr><th>Режим работы</th><td>пн-вс с 08:00 до 18:00</td></tr>
    <tr><th>Почтовый адрес</th><td>649231, респ Алтай, р-н Чемальский, с Чепош, дом Урочище Карасук</td></tr>
    <tr><th>Физический адрес</th><td>649231, респ Алтай, р-н Чемальский, с Чепош, дом Урочище Карасук</td></tr>
    <tr><th>Юридический адрес</th><td>649231, респ Алтай, р-н Чемальский, с Чепош, дом Урочище Карасук</td></tr>
    <tr><th>e-mail</th><td><a href="mailto:brn@altay-avia.ru">brn@altay-avia.ru</a></td></tr>
  </table></div>
</div></section>'''
    write('onlajn-oplata.html', page(root=root, title='Онлайн оплата услуг авиакомпании Алтай Авиа', desc='Онлайн-оплата услуг ООО «АлтайАвиа»: коммерческие воздушные перевозки и авиационные работы. Правила оплаты, возврат средств, реквизиты организации.', active='onlajn-oplata', body=body))

# ---------------------------------------------------------------- Контакты
def build_contacts():
    root = ''
    body = band(root, 'Контакты', 'img/gallery/karasuk25/a2.jpg', [(None, 'Контакты')]) + f'''
<section class="section"><div class="wrap">
  <div class="site-card reveal">
    <div class="info">
      <span class="region">Посадочная площадка «Карасук»</span>
      <h2>Как с нами связаться</h2>
      <p style="margin:0;color:var(--muted)">649231, Республика Алтай, Муниципальный Чемальский р-он, Чепошское Сельское Поселение, с. Чепош, Территория урочище Карасук, д. 1</p>
      <dl class="kv-list">
        <div><dt>Тел.</dt><dd><a href="{PHONE_HREF}">{PHONE}</a> <small style="color:var(--muted);font-weight:400">— {PHONE_NOTE}</small></dd></div>
        <div><dt>Сот.</dt><dd><a href="{MOBILE_HREF}">{MOBILE}</a></dd></div>
        <div><dt>Почта</dt><dd><a href="mailto:info@altay-avia.ru">info@altay-avia.ru</a> <small style="color:var(--muted);font-weight:400">— прием заказов на полеты</small></dd></div>
        <div><dt>Почта</dt><dd><a href="mailto:office@altay-avia.ru">office@altay-avia.ru</a> <small style="color:var(--muted);font-weight:400">— прием корреспонденции</small></dd></div>
        <div><dt>Координаты</dt><dd class="coords"><span>51° 33′ 36″ С</span><span>085° 55′ 03″ В</span></dd></div>
      </dl>
      <div class="social-row"><a href="{VK}" target="_blank" rel="noopener">{ICON['vk']}Мы ВКонтакте</a><a href="https://t.me/altay_avia" target="_blank" rel="noopener">{ICON['tg']}Мы в Telegram</a></div>
    </div>
    {karasuk_map(root)}
  </div>
  <div class="order-layout" style="margin-top:48px">
    <div><div class="section-head"><div><div class="eyebrow">Напишите нам</div><h2>Заявка на полёт</h2></div></div>{order_form(root, 'short', subject='Обращение со страницы Контакты')}</div>
    <aside class="order-side reveal reveal-r"><div class="pic" style="padding:0"><img src="img/gallery/karasuk25/a1.jpg" alt="Вертодром «Карасук»" loading="lazy" style="object-fit:cover;animation:none"></div><p class="note">Режим работы: пн-вс с 08:00 до 18:00.</p></aside>
  </div>
</div></section>'''
    write('kontakty.html', page(root=root, title='Контакты авиакомпании Алтай Авиа', desc='Контакты ООО «АлтайАвиа»: посадочная площадка «Карасук», с. Чепош, Чемальский район, Республика Алтай. Телефон 8 800 550 31 31, info@altay-avia.ru.', active='kontakty', body=body))

# ---------------------------------------------------------------- Заказ полёта
def build_order():
    root = ''
    body = band(root, 'Заказ полета', 'img/gallery/mi8amt/01-000.jpg', [(None, 'Заказ полета')], 'Заполните заявку — мы перезвоним, уточним детали и рассчитаем стоимость.') + f'''
<section class="section"><div class="wrap order-layout">
  <div>{order_form(root, 'flight', subject='Заказ полёта')}</div>
  <aside class="order-side reveal reveal-r">
    <div class="pic"><img src="img/3d/as350.png" alt="Eurocopter AS350" loading="lazy"></div>
    <div class="heli-cards" style="grid-template-columns:1fr;gap:10px"><a class="heli-card" href="vertolety/as350.html" style="grid-template-rows:auto"><div class="txt" style="display:flex;justify-content:space-between;align-items:center;gap:12px"><span><h3 style="font-size:16px;margin:0">{HELIS['as350']['name']}</h3><small>{HELIS['as350']['sub']}</small></span><span class="pax" style="margin:0"><b>{HELIS['as350']['pax']}</b> пасс.</span></div></a><a class="heli-card" href="vertolety/mi8amt.html" style="grid-template-rows:auto"><div class="txt" style="display:flex;justify-content:space-between;align-items:center;gap:12px"><span><h3 style="font-size:16px;margin:0">{HELIS['mi8amt']['name']}</h3><small>{HELIS['mi8amt']['sub']}</small></span><span class="pax" style="margin:0"><b>{HELIS['mi8amt']['pax']}</b> пасс.</span></div></a><a class="heli-card" href="vertolety/mi171.html" style="grid-template-rows:auto"><div class="txt" style="display:flex;justify-content:space-between;align-items:center;gap:12px"><span><h3 style="font-size:16px;margin:0">{HELIS['mi171']['name']}</h3><small>{HELIS['mi171']['sub']}</small></span><span class="pax" style="margin:0"><b>{HELIS['mi171']['pax']}</b> пасс.</span></div></a></div>
    <p class="note">Или позвоните: <a href="{PHONE_HREF}"><b>{PHONE}</b></a> — {PHONE_NOTE}</p>
  </aside>
</div></section>'''
    write('zakaz-poleta.html', page(root=root, title='Заказ полета — АлтайАвиа', desc='Заявка на полёт: выберите дату, маршрут и модель вертолёта — Eurocopter AS350, МИ-8АМТ или МИ-171.', active='', body=body))

# ---------------------------------------------------------------- Политика, СОУТ
def build_policy():
    root = ''
    heads = re.findall(r'<h2 id="(p\d+)">(.*?)</h2>', POLICY)
    toc = '<ol class="toc">' + ''.join(f'<li><a href="#{i}">{t.split(". ",1)[1].capitalize()}</a></li>' for i, t in heads) + '</ol>'
    body = band(root, 'Политика конфиденциальности', 'fon.jpg', [(None, 'Политика конфиденциальности')], 'Политика по обработке персональных данных ООО «АлтайАвиа»') + f'''
<section class="section"><div class="wrap doc">
  <div class="eyebrow">Содержание</div>{toc}
  {POLICY.replace('<p>Обновлено:', '<p class="updated">Обновлено:')}
</div></section>'''
    write('politika.html', page(root=root, title='Политика конфиденциальности персональных данных', desc='Политика по обработке персональных данных ООО «АлтайАвиа»: какие данные собираются, как используются и кому передаются.', active='', body=body))

def build_sout():
    root = ''
    years = [('2025', [('merop-2025-1.pdf', 'Перечень рекомендуемых мероприятий по улучшению условий труда от 30.09.2025'), ('vedom-2025-1.pdf', 'Сводная ведомость результатов проведения специальной оценки условий труда от 30.09.2025'), ('merop-2025.pdf', 'Перечень рекомендуемых мероприятий по улучшению условий труда от 14.01.2025'), ('vedom-2025.pdf', 'Сводная ведомость результатов проведения специальной оценки условий труда от 14.01.2025')]),
             ('2023', [('merop-2023.pdf', 'Перечень рекомендуемых мероприятий по улучшению условий труда от 20.09.2023'), ('vedom-2023.pdf', 'Сводная ведомость результатов проведения специальной оценки условий труда от 20.09.2023')]),
             ('2022', [('merop-2022.pdf', 'Перечень рекомендуемых мероприятий по улучшению условий труда от 17.10.2022'), ('vedom-2022.pdf', 'Сводная ведомость результатов проведения специальной оценки условий труда от 17.10.2022'), ('merop-2022-04.pdf', 'Перечень рекомендуемых мероприятий по улучшению условий труда от 05.04.2022'), ('vedom-2022-04.pdf', 'Сводная ведомость результатов проведения специальной оценки условий труда от 05.04.2022')]),
             ('2021', [('merop-2021.pdf', 'Перечень рекомендуемых мероприятий по улучшению условий труда от 19.10.2021'), ('vedom-2021.pdf', 'Сводная ведомость результатов проведения специальной оценки условий труда от 19.10.2021')])]
    html = ''
    for y, docs in years:
        html += f'<div class="sout-year reveal"><h2>{y} год</h2><div class="sout-list">' + ''.join(f'<a href="docs/sout/{f}" target="_blank" rel="noopener">{ICON["pdf"]}<span>{t}</span><span class="pdf">PDF</span></a>' for f, t in docs) + '</div></div>'
    body = band(root, 'Специальная оценка условий труда', 'img/gallery/karasuk25/p004.jpg', [(None, 'СОУТ')]) + f'<section class="section"><div class="wrap doc">{html}</div></section>'
    write('sout.html', page(root=root, title='СОУТ — специальная оценка условий труда | АлтайАвиа', desc='Сводные ведомости результатов специальной оценки условий труда и перечни рекомендуемых мероприятий ООО «АлтайАвиа», 2021–2025.', active='', body=body))

# ---------------------------------------------------------------- Страницы вертолётов
def build_helis():
    gal = {'as350': ('evro-2025', ['e001.jpg', 'e002.jpg', 'e003.jpg', 'e004.jpg']), 'mi8amt': ('mi8amt', ['01-000.jpg', '01-00001.jpg', '01-00002.jpg', '01-0004.jpg']), 'mi171': ('mi171-2025', ['0001.jpg', '0002.jpg', '0003.jpg', '0004.jpg'])}
    for k in HELI_ORDER:
        root = '../'
        h = HELIS[k]
        d, files = gal[k]
        photos = ''.join(f'<a href="{root}img/gallery/{d}/{f}" data-lightbox="{k}" data-caption="{esc(h["name"])}"><img src="{root}img/gallery/{d}/{f}" alt="{esc(h["name"])}" loading="lazy"></a>' for f in files)
        specs = ''.join(f'<div><dt>{a}</dt><dd>{b}</dd></div>' for a, b in h['specs'])
        routes = [e for e in EX if any(('AS350' in r['heli']) if k == 'as350' else (('8АМТ' in r['heli']) if k == 'mi8amt' else ('171' in r['heli'])) for r in e['rows'])]
        rl = ''.join(f'<li><a href="{root}ekskursii/{e["slug"]}.html">{esc(e["title"])}</a></li>' for e in routes[:10])
        body = band(root, h['name'], BAND_HELI[k], [('o-kompanii.html', 'О компании'), (None, h['name'])], h['sub']) + f'''
<section class="section section-sky"><div class="wrap">
  <div class="fleet">
    <div class="fleet-stage" data-cursor="Вращать">
      <div class="viewer" id="heli-viewer" data-model="{k}" data-helipad="1" data-rotor="idle" data-auto="1" data-theta="0.7" data-phi="1.42" data-fit="auto" data-ty-rel="0.5" data-true-scale="1" data-fov="30" aria-label="3D-модель {esc(h['name'])}"></div>
      <div class="stage-hud"><span class="chip">Live 3D</span><span class="chip">борт {h['reg']}</span><span class="chip">масштаб 1:1</span></div>
      <div class="scale-bar" aria-hidden="true"><i></i><span>10 м</span></div>
      <div class="stage-controls">
        <button type="button" data-rotor="stop" data-target="#heli-viewer" aria-label="Остановить винты">{ICON['pause']}</button>
        <button type="button" data-rotor="idle" data-target="#heli-viewer" aria-pressed="true" aria-label="Медленное вращение винтов">{ICON['rotor']}</button>
        <button type="button" data-rotor="fast" data-target="#heli-viewer" aria-label="Быстрое вращение винтов">{ICON['plane']}</button>
        <button type="button" data-autorotate data-target="#heli-viewer" aria-pressed="true" aria-label="Автоматический облёт камерой">{ICON['rotate']}</button>
      </div>
    </div>
    <div class="fleet-side"><div class="spec-card"><h3>{h['name']}</h3><div class="reg">БОРТ {h['reg']} · {h['sub'].upper()}</div><p style="color:var(--ink-2);font-size:14.5px">{h['about']}</p><dl class="spec-list">{specs}</dl><a class="btn btn-primary" href="{root}zakaz-poleta.html?heli={esc(h['form'])}">Заказать полёт · {h['price']}/час</a></div></div>
  </div>
</div></section>
<section class="section"><div class="wrap split">
  <div><div class="eyebrow">Фото</div><div class="gallery-grid" style="grid-template-columns:repeat(2,1fr)">{photos}</div></div>
  <div><div class="eyebrow">Маршруты на этом борту</div><ul class="prose" style="padding-left:1.2em">{rl}</ul><a class="btn btn-outline" href="{root}ekskursii.html">Все экскурсии</a></div>
</div></section>'''
        write(f'vertolety/{k}.html', page(root=root, title=f'{h["name"]} — {h["sub"]} | АлтайАвиа', desc=f'{h["name"]}: {h["about"]} Аренда — {h["price"]} за лётный час.', active='o-kompanii', body=body, scripts_3d=True, models=(k,) if k != 'as350' else ()))

# ---------------------------------------------------------------- favicon, robots
def build_misc():
    fav = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="14" fill="#0B1D3A"/><path d="M8 48l16-24 8 11 5-6 8 11 5-8 10 16z" fill="#5AA7F0"/><path d="M12 14h40" stroke="#F2C230" stroke-width="3" stroke-linecap="round"/><path d="M32 14v6" stroke="#F2C230" stroke-width="3" stroke-linecap="round"/></svg>'
    write('favicon.svg', fav)
    pages = ['index.html', 'arenda.html', 'ekskursii.html', 'ekskursii/gornyj-altay.html', 'ekskursii/altay-village.html'] + [f'ekskursii/{e["slug"]}.html' for e in EX] + ['ploshchadki.html', 'servis.html', 'o-kompanii.html', 'galereya.html', 'onlajn-oplata.html', 'kontakty.html', 'zakaz-poleta.html', 'politika.html', 'sout.html'] + [f'vertolety/{k}.html' for k in HELI_ORDER]
    write('sitemap.xml', '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + ''.join(f'<url><loc>https://www.altay-avia.ru/{p}</loc></url>' for p in pages) + '</urlset>')
    write('robots.txt', 'User-agent: *\nAllow: /\nSitemap: https://www.altay-avia.ru/sitemap.xml\n')

if __name__ == '__main__':
    build_index(); build_arenda(); build_ekskursii(); build_ploshchadki(); build_servis(); build_about(); build_gallery(); build_pay(); build_contacts(); build_order(); build_policy(); build_sout(); build_helis(); build_misc()
    n = sum(len([f for f in fs if f.endswith('.html')]) for _, _, fs in os.walk(SITE))
    print('built', n, 'html pages')
