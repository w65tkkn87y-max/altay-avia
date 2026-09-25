# -*- coding: utf-8 -*-
"""Общие фрагменты: шапка, подвал, иконки, обёртка страницы."""
import json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, 'site')
DATA = os.path.join(ROOT, 'data')

PHONE = '8 800 550 31 31'
PHONE_HREF = 'tel:88005503131'
PHONE_NOTE = 'звонок по России бесплатно'
MOBILE = '+7 913 210 0333'
MOBILE_HREF = 'tel:+79132100333'
VK = 'https://vk.com/club211344178'
PREMIER = 'https://premieravia.ru/about_us/#group-company'
SITE_NAME = 'АлтайАвиа'
import time
BUILD_V = time.strftime('%Y%m%d%H%M')   # версия сборки для сброса кэша css/js

NAV = [
    ('arenda.html', 'Аренда', 'arenda'),
    ('ekskursii.html', 'Экскурсии', 'ekskursii'),
    ('ploshchadki.html', 'Площадки', 'ploshchadki'),
    ('servis.html', 'Сервис', 'servis'),
    ('o-kompanii.html', 'О компании', 'o-kompanii'),
    ('galereya.html', 'Галерея', 'galereya'),
    ('onlajn-oplata.html', 'On-line оплата', 'onlajn-oplata'),
    ('kontakty.html', 'Контакты', 'kontakty'),
]
FOOTER_COL1 = [('index.html', 'Главная'), ('o-kompanii.html', 'О компании'), ('galereya.html', 'Галерея'), ('kontakty.html', 'Контакты')]
FOOTER_COL2 = [('arenda.html', 'Аренда'), ('ekskursii.html', 'Экскурсии'), ('ploshchadki.html', 'Площадки'), ('servis.html', 'Сервис'), ('onlajn-oplata.html', 'On-line оплата')]

HELIS = {
    'as350': {'name': 'Eurocopter AS350', 'sub': 'Écureuil (H125)', 'pax': 5, 'price': '275 000 р.', 'reg': 'RA-04062', 'form': 'Eurocopter AS350',
              'specs': [('Пассажиров', '5'), ('Крейсерская скорость', '245 км/ч'), ('Максимальная скорость', '287 км/ч'), ('Дальность', '630 км')],
              'about': 'Лёгкий одномоторный вертолёт с панорамным остеклением — идеален для экскурсий, фото- и видеосъёмки, посадок на высокогорные площадки.'},
    'mi8amt': {'name': 'МИ-8АМТ', 'sub': 'VIP салон', 'pax': 20, 'price': '470 000 р.', 'reg': 'RA-24187', 'form': 'МИ-8АМТ (VIP салон)',
               'specs': [('Пассажиров', '20'), ('Крейсерская скорость', '230 км/ч'), ('Максимальная скорость', '250 км/ч'), ('Дальность', '610 км')],
               'about': 'Средний двухдвигательный вертолёт с просторным салоном — для больших групп, чартерных перелётов и дальних маршрутов по Алтаю и Сибири.'},
    'mi171': {'name': 'МИ-171', 'sub': 'VIP салон', 'pax': 9, 'price': '495 000 р.', 'reg': 'RA-25565', 'form': 'МИ-171 (VIP салон)',
              'specs': [('Пассажиров', '9'), ('Крейсерская скорость', '230 км/ч'), ('Максимальная скорость', '250 км/ч'), ('Дальность', '610 км')],
              'about': 'Вертолёт бизнес-класса на базе Ми-8: VIP-салон на 9 пассажиров, повышенный комфорт и всепогодность для деловых и туристических перелётов.'},
}
HELI_ORDER = ['as350', 'mi8amt', 'mi171']

# --- Иконки (inline SVG, stroke=currentColor) ---
ICON = {
    'heli': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M3 5h14M10 5v3"/><path d="M6 12.5c0-2 1.6-3.5 3.6-3.5h3.2c2.3 0 4.2 1.4 5 3.4l.4 1.1H21"/><path d="M6 12.5V15a2 2 0 0 0 2 2h9l1-3.5H6z"/><path d="M6 19h8M8 17v2M13 17v2"/><path d="M11 9v3.5"/></svg>',
    'tour': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M3 19l5.5-9 3.5 5 2.5-3.5L21 19H3z"/><circle cx="17" cy="6" r="2"/><path d="M8 10l2-3"/></svg>',
    'hangar': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M3 20V10.5L12 4l9 6.5V20"/><path d="M7 20v-7h10v7"/><path d="M7 16h10"/><path d="M3 20h18"/></svg>',
    'wrench': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M14.5 6.5a4 4 0 0 0 5 5L11 20a2.1 2.1 0 0 1-3-3l8.5-8.5"/><path d="M14.5 6.5L17 4l3 3-2.5 2.5"/></svg>',
    'arrow': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M13 6l6 6-6 6"/></svg>',
    'clock': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>',
    'users': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><circle cx="9" cy="8" r="3.2"/><path d="M3.5 19a5.5 5.5 0 0 1 11 0"/><circle cx="17" cy="9" r="2.4"/><path d="M15.5 19h5a4.5 4.5 0 0 0-3-4.2"/></svg>',
    'pdf': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5"/><path d="M8.5 17v-5h1.6a1.5 1.5 0 0 1 0 3H8.5M13 12h1.4a1.6 1.6 0 0 1 1.6 1.6v1.8a1.6 1.6 0 0 1-1.6 1.6H13z"/></svg>',
    'doc': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5M9 13h6M9 17h6"/></svg>',
    'vk': '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12.8 17.6c-5.9 0-9.3-4-9.4-10.8h3c.1 5 2.3 7 4 7.5V6.8h2.8v4.3c1.7-.2 3.5-2.1 4.1-4.3h2.8c-.5 2.6-2.4 4.6-3.8 5.4 1.4.6 3.6 2.3 4.4 5.4h-3.1c-.6-2-2.2-3.6-4.4-3.8v3.8h-.4z"/></svg>',
    'tg': '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M20.7 4.3L2.9 11.2c-1 .4-1 1 .1 1.3l4.5 1.4 1.7 5.3c.2.6.4.8 1 .8.5 0 .8-.2 1.2-.6l2.4-2.3 4.7 3.5c.9.5 1.5.2 1.7-.8l3-14.3c.3-1.2-.4-1.7-1.5-1.2zM8 13.6l9.6-6c.5-.3.9-.1.5.2l-8 7.2-.3 3.3-1.8-4.7z"/></svg>',
    'pin': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M12 21s6-5.7 6-11a6 6 0 0 0-12 0c0 5.3 6 11 6 11z"/><circle cx="12" cy="10" r="2.2"/></svg>',
    'phone': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M5 4h4l2 5-2.5 1.5a11 11 0 0 0 5 5L15 13l5 2v4a2 2 0 0 1-2 2A16 16 0 0 1 3 6a2 2 0 0 1 2-2z"/></svg>',
    'mail': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 7l9 6 9-6"/></svg>',
    'form': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><rect x="4" y="3" width="16" height="18" rx="2"/><path d="M8 8h8M8 12h8M8 16h5"/></svg>',
    'brief': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"><rect x="3" y="7" width="18" height="13" rx="2"/><path d="M9 7V5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2M3 12h18"/></svg>',
    'charter': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12h4l3-6h2l-1.5 6H16l1.5-2H20l-1.5 4L20 18h-2.5L16 16h-5.5L12 22h-2l-3-6H3z"/></svg>',
    'camera': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"><path d="M4 8h3l2-3h6l2 3h3v11H4z"/><circle cx="12" cy="13" r="3.2"/></svg>',
    'airport': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M3 20h18M6 20V9l6-5 6 5v11"/><path d="M10 20v-5h4v5M9 11h2M13 11h2"/></svg>',
    'compass': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M15.5 8.5l-2 5-5 2 2-5z"/></svg>',
    'check': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12.5l4.5 4.5L19 7"/></svg>',
    'fuel': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"><path d="M5 21V5a2 2 0 0 1 2-2h5a2 2 0 0 1 2 2v16M5 21h9M7 7h5v4H7z"/><path d="M14 9h2l2 2v6a1.5 1.5 0 0 0 3 0v-7l-2-2"/></svg>',
    'tag': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12V4h8l10 10-8 8z"/><circle cx="7.5" cy="8.5" r="1.5"/></svg>',
    'plane': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M2 16l20-8-6 9-4-3-3 4-1-5z"/></svg>',
    'eye': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6S2 12 2 12z"/><circle cx="12" cy="12" r="3"/></svg>',
    'rotate': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M20 12a8 8 0 1 1-3-6.2"/><path d="M20 4v5h-5"/></svg>',
    'rotor': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><circle cx="12" cy="12" r="1.8"/><path d="M12 10.2V3M12 13.8V21M10.2 12H3M13.8 12H21"/></svg>',
    'pause': '<svg viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="5" width="4" height="14" rx="1"/><rect x="14" y="5" width="4" height="14" rx="1"/></svg>',
    'drag': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 12h16M7 9l-3 3 3 3M17 9l3 3-3 3"/></svg>',
}

def logo(root):
    return f'<a class="brand" href="{root}index.html" aria-label="АлтайАвиа — на главную"><img class="keep" src="{root}img/misc/logo-big-25.png" alt="АлтайАвиа" width="213" height="70"></a>'

HEAD_FONTS = '<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Unbounded:wght@400;500;600;700;800&family=Golos+Text:wght@400;500;600;700&family=Oswald:wght@300;400;500;600&display=swap">'

ICON['spark'] = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2l1.6 6.9L20 10.5l-6.4 1.6L12 19l-1.6-6.9L4 10.5l6.4-1.6z"/></svg>'
ICON['arrow-ur'] = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M7 17L17 7M9 7h8v8"/></svg>'

def header(root, active=''):
    items = ''.join('<li><a href="%s%s" data-section="%s"%s><span>%s</span></a></li>' % (root, h, sec, ' class="is-active"' if sec == active else '', t) for h, t, sec in NAV)
    mitems = ''.join('<li style="--i:%d"><a href="%s%s"><small>0%d</small><span>%s</span></a></li>' % (i, root, h, i + 1, t) for i, (h, t, sec) in enumerate(NAV))
    return f'''<header class="site-header">
  <div class="topbar"><div class="wrap">
    <span class="tb-item"><i class="tb-dot"></i>Посадочная площадка «Карасук» · 51°33′36″ N 85°55′03″ E</span>
    <span class="tb-item tb-clock">На Алтае сейчас <b data-clock>--:--</b></span>
    <a class="tb-group" href="{PREMIER}" target="_blank" rel="noopener"><span>Входим в группу компаний Premier Avia</span><img src="{root}img/misc/pa2025.png" alt="Premier Avia Group" width="42" height="30" loading="lazy"></a>
  </div></div>
  <div class="mainbar"><div class="wrap">
    {logo(root)}
    <nav class="nav-wrap" aria-label="Основное меню"><ul class="nav">{items}</ul></nav>
    <div class="phone-block"><a href="{PHONE_HREF}">{PHONE}</a><small>{PHONE_NOTE}</small></div>
    <a class="phone-round" href="{PHONE_HREF}" aria-label="Позвонить: {PHONE}">{ICON['phone']}</a>
    <a class="btn btn-primary btn-sm head-cta magnetic" href="{root}zakaz-poleta.html"><span>Заказать полёт</span>{ICON['arrow']}</a>
    <button class="burger" aria-label="Открыть меню" aria-expanded="false"><span></span></button>
  </div></div>
  <div class="menu-panel">
    <div class="wrap">
      <ul class="menu-list">{mitems}</ul>
      <div class="menu-foot"><a class="menu-phone" href="{PHONE_HREF}">{PHONE}</a><small>{PHONE_NOTE}</small><a class="btn btn-primary" href="{root}zakaz-poleta.html">Заказать полёт</a></div>
    </div>
  </div>
</header>'''

RIDGE = ('<svg class="ridge" viewBox="0 0 1600 200" preserveAspectRatio="none" aria-hidden="true">'
         '<path d="M0 200V132l92-38 70 30 96-66 64 42 58-24 120-72 82 60 66-22 104 76 58-30 92 44 112-96 76 50 60-18 118 78 70-36 88 40 94-58 80 38V200z" fill="currentColor" opacity=".3"/>'
         '<path d="M0 200V156l120-30 84 26 110-48 90 40 76-16 128 52 104-60 88 44 96-28 120 50 92-34 116 40 92-30 104 30 90-18 90 26V200z" fill="currentColor" opacity=".55"/>'
         '<path d="M0 200v-22l180-14 140 12 160-20 150 18 170-16 160 18 170-14 150 12 130-10 90 8v36z" fill="currentColor"/></svg>')

def footer(root):
    c1 = ''.join('<li><a href="%s%s">%s</a></li>' % (root, h, t) for h, t in FOOTER_COL1)
    c2 = ''.join('<li><a href="%s%s">%s</a></li>' % (root, h, t) for h, t in FOOTER_COL2)
    return f'''<section class="takeoff" aria-label="Заказ полёта">
  <div class="takeoff-bg" data-parallax="0.16"><img src="{root}img/hero/slider-kara.jpg" alt="" loading="lazy"></div>
  <div class="wrap takeoff-inner">
    <div class="eyebrow eyebrow-light">Готовы к взлёту</div>
    <h2 class="takeoff-title split-words">Ваш полёт над Алтаем начинается здесь</h2>
    <p class="takeoff-lead">Позвоните или оставьте заявку — подберём борт и маршрут, рассчитаем стоимость полёта.</p>
    <div class="takeoff-actions">
      <a class="btn btn-light btn-lg magnetic" href="{root}zakaz-poleta.html"><span>Заказать полёт</span>{ICON['arrow']}</a>
      <a class="takeoff-phone" href="{PHONE_HREF}"><small>{PHONE_NOTE}</small>{PHONE}</a>
    </div>
  </div>
  <div class="takeoff-hud" aria-hidden="true"><span>KARASUK</span><span>ELEV 375 M</span><span>51°33′N 085°55′E</span></div>
</section>
<footer class="site-footer">
  {RIDGE}
  <div class="wrap">
    <div class="footer-grid">
      <div class="footer-brand"><img class="keep" src="{root}img/misc/logo-big-25.png" alt="АлтайАвиа" width="213" height="70" loading="lazy"><p>Сертифицированный коммерческий авиаперевозчик. Посадочная площадка «Карасук», Республика Алтай.</p></div>
      <div><h4>Компания</h4><ul>{c1}</ul></div>
      <div><h4>Услуги</h4><ul>{c2}</ul></div>
      <div class="footer-contact"><h4>Связаться</h4><a class="tel" href="{PHONE_HREF}">{PHONE}</a><small>{PHONE_NOTE}</small><a class="vk" href="{VK}" target="_blank" rel="noopener">{ICON['vk']}Подписывайтесь на нас в ВКонтакте</a></div>
    </div>
    <div class="footer-mega" aria-hidden="true"><span data-parallax-x="0.12">АлтайАвиа · небо Алтая · АлтайАвиа · небо Алтая</span></div>
    <div class="footer-bottom">
      <div class="legal"><a href="{root}sout.html">СОУТ</a><a href="{root}politika.html">Политика конфиденциальности</a><span>Официальный сайт «АлтайАвиа» <span data-year>2026</span> год</span>{model_credits()}</div>
      <button class="a11y-toggle" type="button" aria-pressed="false">{ICON['eye']}Версия для слабовидящих</button>
    </div>
  </div>
</footer>'''

def available_models():
    """Ключи моделей, для которых есть компактный файл site/models/<key>.js (см. build/import/glb2js.py)."""
    d = os.path.join(SITE, 'models')
    return ','.join(sorted(f[:-3] for f in os.listdir(d) if f.endswith('.js'))) if os.path.isdir(d) else ''

MODEL_CREDITS = {  # атрибуция внешних 3D-моделей (лицензии CC BY и GPL требуют указать авторов)
    'as350': '3D-модель AS350 — на основе «Eurocopter AS350 Squirrel» (FlightGear UK, github.com/FGMEMBERS/AS350), GPL-2.0',
    'mi8amt': '3D-модели Ми-8АМТ и Ми-171 — на основе «Mil Mi-8AMTSh» (42manako, Sketchfab), CC BY 4.0',
    'mi171': '',
}
SCENE_CREDIT = 'Площадка «Карасук»: рельеф SRTM (AWS Terrain Tiles), снимок Sentinel-2 cloudless 2016 © EOX (s2maps.eu), CC BY 4.0'
def model_credits():
    used = [MODEL_CREDITS[k] for k in available_models().split(',') if MODEL_CREDITS.get(k)]
    if os.path.isfile(os.path.join(SITE, 'scene', 'karasuk.js')): used.append(SCENE_CREDIT)
    return ''.join(f'<span>{c}</span>' for c in used)

def page(*, root, title, desc, active, body, scripts_3d=False, extra_head='', canonical='', models=(), body_class=''):
    three = ''
    if scripts_3d:
        three = (f'<script src="{root}js/vendor/three.min.js"></script>'
                 f'<script src="{root}js/heli3d.js?v={BUILD_V}" defer></script><script src="{root}js/karasuk.js?v={BUILD_V}" defer></script>'
                 f'<script src="{root}js/fleet.js?v={BUILD_V}" defer></script>')
    intro = ('<div class="preloader" aria-hidden="true"><div class="pl-inner">'
             '<div class="pl-rotor"><svg viewBox="0 0 120 120"><g fill="none" stroke="currentColor" stroke-width="4" stroke-linecap="round"><path d="M60 60V8"/><path d="M60 60l45 26"/><path d="M60 60L15 86"/></g><circle cx="60" cy="60" r="7" fill="currentColor"/></svg></div>'
             '<div class="pl-alt"><span class="pl-num" data-pl-num>0</span><small>м — набор высоты</small></div>'
             '<div class="pl-bar"><i></i></div><div class="pl-text">АлтайАвиа · Карасук</div></div></div>'
             '<div class="warp" aria-hidden="true"><div class="warp-disc"></div><div class="warp-mark"><svg viewBox="0 0 120 120"><g fill="none" stroke="currentColor" stroke-width="5" stroke-linecap="round"><path d="M60 60V10"/><path d="M60 60l43 25"/><path d="M60 60L17 85"/></g><circle cx="60" cy="60" r="8" fill="currentColor"/></svg></div></div>'
             '<aside class="altimeter" aria-hidden="true"><div class="alt-read"><small>ВЫС</small><b data-alt>375</b><small>м</small></div>'
             '<div class="alt-scale"><i class="alt-fill"></i><i class="alt-cursor"></i></div>'
             '<div class="alt-marks"><span>4506</span><span>3000</span><span>1500</span><span>375</span></div></aside>'
             '<div class="cursor" aria-hidden="true"><span class="cursor-label"></span></div>')
    return f'''<!DOCTYPE html>
<html lang="ru" data-root="{root}" data-models="{available_models()}" data-v="{BUILD_V}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#F4F8FE">
<title>{title}</title>
<meta name="description" content="{desc}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:type" content="website">
<meta property="og:image" content="{root}img/3d/mi171.png">
<link rel="icon" href="{root}favicon.svg" type="image/svg+xml">
{HEAD_FONTS}
<link rel="stylesheet" href="{root}css/main.css?v={BUILD_V}">
{extra_head}
</head>
<body class="{body_class}">
{intro}
{header(root, active)}
<main>
{body}
</main>
{footer(root)}
<script src="{root}js/main.js?v={BUILD_V}" defer></script>
{three}
</body>
</html>'''

def band(root, title, image, crumbs, sub='', pos='center'):
    """Обложка внутренней страницы: фото во всю ширину с параллаксом, крошки, заголовок посимвольно, приборная строка."""
    cr = ''.join('<li>%s</li>' % (('<a href="%s%s">%s</a>' % (root, h, t)) if h else t) for h, t in crumbs)
    subhtml = f'<p class="lead">{sub}</p>' if sub else ''
    src = image if '/' in image else 'img/hero/' + image
    return f'''<section class="page-band">
  <div class="bg" data-parallax="0.3"><img src="{root}{src}" alt="" style="object-position:{pos}"></div>
  <div class="wrap band-inner"><nav class="crumbs" aria-label="Вы здесь"><ul><li><a href="{root}index.html">Главная</a></li>{cr}</ul></nav><h1><span class="h-split">{title}</span></h1>{subhtml}</div>
  <div class="band-hud" aria-hidden="true"><span>51°33′N · 085°55′E</span><span class="band-line"></span><span>АлтайАвиа</span></div>
</section>'''

def write(path, html):
    full = os.path.join(SITE, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, 'w', encoding='utf-8') as f:
        f.write(html)
    return full

def order_form(root, kind='flight', route='', helis=None, subject='Заявка на полёт'):
    """Форма заявки: kind = flight (полная) | short (контакты) """
    opts = ''.join('<option value="%s">%s</option>' % (HELIS[k]['form'], HELIS[k]['form']) for k in (helis or HELI_ORDER))
    routef = f'<input type="hidden" name="route" value="{route}">' if route else ''
    consent = f'<label class="check"><input type="checkbox" name="consent" required value="да"><span>Согласен на обработку персональных данных в соответствии с <a href="{root}politika.html">Условиями</a> <span class="req">*</span></span></label>'
    if kind == 'flight':
        fields = f'''<div class="form-grid">
  <div class="field"><label for="f-date">Дата вылета:</label><input id="f-date" type="date" name="date"></div>
  <div class="field"><label for="f-time">Время вылета:</label><input id="f-time" type="time" name="time"></div>
  <div class="field"><label for="f-from">Откуда: <span class="req">*</span></label><input id="f-from" type="text" name="from" required placeholder="Площадка «Карасук», с. Чепош"></div>
  <div class="field"><label for="f-to">Куда: <span class="req">*</span></label><input id="f-to" type="text" name="to" required placeholder="Телецкое озеро"></div>
  <div class="field full"><label for="f-name">ФИО <span class="req">*</span></label><input id="f-name" type="text" name="name" required autocomplete="name"></div>
  <div class="field"><label for="f-phone">Телефон: <span class="req">*</span></label><input id="f-phone" type="tel" name="phone" required autocomplete="tel" placeholder="+7"></div>
  <div class="field"><label for="f-email">Email <span class="req">*</span></label><input id="f-email" type="email" name="email" required autocomplete="email"></div>
  <div class="field full"><label for="f-heli">Выберите модель вертолета:</label><select id="f-heli" name="helicopter"><option value="">-</option>{opts}</select></div>
  <div class="field full"><label for="f-msg">Комментарий</label><textarea id="f-msg" name="message" placeholder="Количество пассажиров, пожелания к маршруту"></textarea></div>
  <div class="full">{consent}</div>
</div>'''
    else:
        fields = f'''<div class="form-grid">
  <div class="field"><label for="s-name">Ваше имя <span class="req">*</span></label><input id="s-name" type="text" name="name" required autocomplete="name"></div>
  <div class="field"><label for="s-phone">Телефон <span class="req">*</span></label><input id="s-phone" type="tel" name="phone" required autocomplete="tel" placeholder="+7"></div>
  <div class="field"><label for="s-email">Email</label><input id="s-email" type="email" name="email" autocomplete="email"></div>
  <div class="field"><label for="s-heli">Модель вертолета</label><select id="s-heli" name="helicopter"><option value="">-</option>{opts}</select></div>
  <div class="field full"><label for="s-msg">Комментарий</label><textarea id="s-msg" name="message" placeholder="Дата, количество пассажиров, пожелания"></textarea></div>
  <div class="full">{consent}</div>
</div>'''
    return f'''<form class="form-card" data-form="{kind}" data-subject="{subject}" novalidate>
{routef}{fields}
<div class="form-actions"><button class="btn btn-primary" type="submit">Отправить</button><span class="form-status" role="status" aria-live="polite"></span></div>
</form>'''
