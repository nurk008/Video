#!/usr/bin/env python3
"""YouTube Long-Form Horizontal Documentary Builder (1920x1080, 16:9, 30fps, KZ ONLY).

"ҚАЗАҚ ХАНДЫҒЫНЫҢ АЛТЫ ҰЛЫ ЖЕҢІСІ: Дала империясы қалай сақталды? (1510–1771)"
30 scenes across 7 chapters/acts using 3 native widescreen modes:
  1) Full-screen 1920x1080 3D-hillshaded tactical maps (WidescreenMapCamera)
  2) Widescreen Split-Dossier (1080x760 crisp cinema frame + 696x760 tactical telemetry)
  3) Chapter Hero Cinema (blurred graded ambient backdrop + framed scene + chapter hero card)

100% Hanafi-compliant (zero close-up faces, zero gore, zero musical instruments: physical SFX + A cappella, -14 LUFS).
Portable path detection: ROOT = Path(__file__).resolve().parent.parent
"""

import asyncio
import json
import math
import os
import re
import subprocess
import sys
import time
import wave
from functools import lru_cache
from pathlib import Path

import edge_tts
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy.ndimage import gaussian_filter, sobel

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "production"))

import sfx as smod

try:
    import imageio_ffmpeg
    FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    FFMPEG = "ffmpeg"

SR = 48000
W, H, FPS = 1920, 1080, 30

FONT_PATH = ROOT / "production" / "fonts" / "Montserrat-Black.ttf"
BUILD = ROOT / "production" / "build_yt_long01"
OUT_DIR = ROOT / "output"
OUT_FILE = "YT_LONG_01_Kazakh_Khanate_16x9_KZ.mp4"

VOICE_MAIN = "kk-KZ-DauletNeural"
VOICE_FALLBACK = "kk-KZ-AigulNeural"
VOICE_RATE = "+8%"
VOICE_PITCH = "-1Hz"

VOICE_FX = (
    "highpass=f=75,"
    "acompressor=threshold=-20dB:ratio=2.8:attack=10:release=140,"
    "equalizer=f=135:t=q:w=1.2:g=3.0,"
    "equalizer=f=3200:t=q:w=1.5:g=1.8"
)

GOLD = (248, 202, 84)
CYAN = (78, 224, 222)
RED = (232, 72, 62)
WHITE = (246, 244, 236)
DARK_BG = (10, 16, 24)

# 7 progress chapters shown in top-right HUD pills
CHAPTER_PILLS = ["ПРОЛОГ", "1510", "1598", "1643", "ЖАРҒЫ", "1730", "1771"]

# Chapter pauses (longer breath at chapter boundaries)
CHAPTER_BREAK_SCENES = {1, 5, 9, 14, 18, 23, 27}

# 30 scenes across 7 chapters (~435 words -> ~195–220s at +8%)
SCENES = [
    # --- PROLOGUE (00:00) ---
    {
        "text": "Зеңбірегі де, тас қамалы да жоқ дала халқы екі жүз алпыс жыл бойы Еуразияның ең алып әскерлерін қалай тоқтатты?",
        "ch_idx": 0, "top": "ПРОЛОГ • ҰЛЫ ДАЛА ҚҰПИЯСЫ", "sub": "ЗЕҢБІРЕКСІЗ ЖӘНЕ ТАС ҚАМАЛСЫЗ 260 ЖЫЛДЫҚ ҚОРҒАНЫС",
        "mode": "cut3", "plates": ["scenes_ep06/cut01a.jpg", "scenes_ep06/cut01b.jpg"],
    },
    {
        "text": "Мұның сыры — кездейсоқ батырлық емес. Қазақ хандығын сақтап қалған алты ұлы стратегиялық жеңіс бар.",
        "ch_idx": 0, "top": "АЛТЫ ҰЛЫ БЕЛЕС (1510–1771)", "sub": "ДАЛА ИМПЕРИЯСЫН САҚТАП ҚАЛҒАН СТРАТЕГИЯЛЫҚ ШЕШІМДЕР",
        "mode": "split", "plate": "scenes_ep05/scene_02.jpg",
        "card_title": "АЛТЫ ҰЛЫ БЕЛЕС", "card_tag": "СТРАТЕГИЯ КАРТАСЫ",
        "bullets": [
            ("1510 • ҰЛЫТАУ", "Қасым ханның қысқы қақпаны"),
            ("1598 • ОҢТҮСТІК", "Түркістан мен Ташкент (200 жыл)"),
            ("1643 • ОРБҰЛАҚ", "600 сарбаз 50 000-ға қарсы (1:83)"),
            ("1680 • ЖЕТІ ЖАРҒЫ", "Үш бидің ортақ дала заңы"),
            ("1730 • АҢЫРАҚАЙ", "Сабалақ пен Толғама қоршауы"),
            ("1771 • АБЫЛАЙ", "Екі алып империя тепе-теңдігі"),
        ],
    },
    # --- CHAPTER 1: 1510 ULYTAU ---
    {
        "text": "Бірінші белес — мың бес жүз оныншы жыл. Қырық градус аязда Ұлытау даласына қарсыластың қалың қолы басып кірді.",
        "ch_idx": 1, "top": "І ТАРАУ • 1510 ҰЛЫТАУ ҚАҚПАНЫ", "sub": "ҚЫРЫҚ ГРАДУС АЯЗ • ҚАСЫМ ХАННЫҢ ТАКТИКАСЫ",
        "mode": "hero", "plate": "scenes_ep04/scene_01.jpg",
        "hero_num": "1510", "hero_title": "ҰЛЫТАУ ҚАҚПАНЫ",
        "hero_sub": "ҚАСЫМ ХАН • ҚЫСҚЫ СТРАТЕГИЯ",
        "hero_stats": [("МАЙДАН ШЕБІ", "ҰЛЫТАУ ТАУЛАРЫ"), ("АУА РАЙЫ", "-40°C ҚЫСҚЫ БҰРҚАСЫН"), ("ТАКТИКА", "ЖАЛҒАН ШЕГІНУ")],
    },
    {
        "text": "Қасым хан мен Мойынсыз Хасан жауды әдейі қар басқан терең аңғарға еліктіріп, таң алдында соққы берді.",
        "ch_idx": 1, "top": "І ТАРАУ • ҰЛЫТАУДАҒЫ ТҮНГІ СОҚҚЫ", "sub": "МОЙЫНСЫЗ ХАСАН ЖАУДЫ АҢҒАРҒА БАҒЫТТАДЫ",
        "mode": "map", "map_id": "ch1_ulytau",
    },
    {
        "text": "Күтпеген түн шабуылында қарсылас шебі талқандалып, Қазақ хандығы Еділ мен Ертіс арасын түгел бақылауға алды.",
        "ch_idx": 1, "top": "І ТАРАУ • АУМАҚТЫҢ КЕҢЕЮІ", "sub": "ЕДІЛДЕН ЕРТІСКЕ ДЕЙІНГІ БАҚЫЛАУ",
        "mode": "split", "plate": "scenes_ep04/scene_11.jpg",
        "card_title": "ТАҢ АЛДЫНДАҒЫ ЖЕҢІС", "card_tag": "1510 • НӘТИЖЕ",
        "bars": [("БАТЫС ШЕБІ: ЕДІЛ – ЖАЙЫҚ", 0.92, GOLD), ("ШЫҒЫС ШЕБІ: ЕРТІС АЛАБЫ", 0.90, CYAN), ("ДАЛА БАҚЫЛАУЫ", 0.96, GOLD)],
        "bullets": [
            ("АМАЛ", "Бөлінген қарсылас шебіне соққы"),
            ("МАҢЫЗЫ", "Оңтүстік пен батыс жолдары ашылды"),
        ],
    },
    {
        "text": "Осы жеңістен кейін Қасым хан халқы миллионнан асқан қуатты мемлекет құрып, дала заңын бекітті.",
        "ch_idx": 1, "top": "І ТАРАУ • ҚАСЫМ ХАННЫҢ ҚАСҚА ЖОЛЫ", "sub": "ХАЛЫҚ САНЫ 1 МЛН+ • МЕМЛЕКЕТТІК ЗАҢ",
        "mode": "split", "plate": "scenes_ep04/scene_08.jpg",
        "card_title": "1 000 000+ ХАЛЫҚ", "card_tag": "ҚАСЫМ ХАН ДӘУІРІ",
        "counter": (1000000, "+", "БІРТҰТАС ДАЛА ХАЛҚЫ"),
        "bullets": [
            ("ЗАҢ ЖҮЙЕСІ", "Қасым ханның қасқа жолы"),
            ("МӘРТЕБЕ", "Еуразияда мойындалған дербес ел"),
        ],
    },
    # --- CHAPTER 2: 1598 TAVEKEL ---
    {
        "text": "Екінші жеңіс — мың бес жүз тоқсан сегізінші жылғы Ұлы Оңтүстік жорығы.",
        "ch_idx": 2, "top": "ІІ ТАРАУ • 1598 ОҢТҮСТІК ЖОРЫҚ", "sub": "ТӘУЕКЕЛ ХАН МЕН ЕР ЕСІМНІҢ НАЙЗАҒАЙ ЖОРЫҒЫ",
        "mode": "hero", "plate": "scenes_ep05/scene_08.jpg",
        "hero_num": "1598", "hero_title": "ҰЛЫ ОҢТҮСТІК ЖОРЫҚ",
        "hero_sub": "ТӘУЕКЕЛ ХАН • ЕР ЕСІМ СҰЛТАН",
        "hero_stats": [("БАСТАЛУЫ", "СЫҒАНАҚ ПЛАЦДАРМЫ"), ("ҚАРҚЫН", "БІР ЖАЗДА 1 200+ ШАҚЫРЫМ"), ("БАҒЫТ", "СЫРДАРИЯ БОЙЫ")],
    },
    {
        "text": "Тәуекел хан мен Ер Есім Сығанақтан найзағайдай жүйткіп, Түркістан мен Ташкентті бірінен соң бірін қайтарды.",
        "ch_idx": 2, "top": "ІІ ТАРАУ • ҚАЛАЛАРДЫҢ ҚАЙТУЫ", "sub": "СЫҒАНАҚ • ТҮРКІСТАН • ТАШКЕНТ • САМАРҚАН",
        "mode": "map", "map_id": "ch2_south",
    },
    {
        "text": "Самарқан қақпасы ашылып, Бұхара түбіндегі шешуші шайқаста дала сарбаздары ерлік көрсетті.",
        "ch_idx": 2, "top": "ІІ ТАРАУ • САМАРҚАН МЕН БҰХАРА", "sub": "ЕР ЕСІМНІҢ БАТЫЛ ЖАСАҒЫ ШЕШУШІ ШАЙҚАСТА",
        "mode": "split", "plate": "scenes_ep05/scene_04.jpg",
        "card_title": "ОҢТҮСТІК СЕРПІЛІС", "card_tag": "1598 • МАЙДАН",
        "bars": [("ТҮРКІСТАН", 1.0, GOLD), ("ТАШКЕНТ", 1.0, GOLD), ("САМАРҚАН", 0.92, CYAN), ("БҰХАРА ҚАҚПАСЫ", 0.85, GOLD)],
        "bullets": [
            ("АЛҒЫ ШЕП", "Сығанақ пен Саураннан шұғыл жорық"),
            ("ТІЗГІН", "Сырдария өткелдерін толық бақылау"),
        ],
    },
    {
        "text": "Нәтижесінде Түркістан мен Ташкент шаһарлары екі ғасыр бойы Қазақ ордасының тірегіне айналды.",
        "ch_idx": 2, "top": "ІІ ТАРАУ • 200 ЖЫЛДЫҚ ТІРЕК", "sub": "ТҮРКІСТАН ОРДА АСТАНАСЫНА АЙНАЛДЫ",
        "mode": "split", "plate": "scenes_ep05/scene_03.jpg",
        "card_title": "200 ЖЫЛДЫҚ ТІРЕК", "card_tag": "1598–1798",
        "counter": (200, " ЖЫЛ", "ТҮРКІСТАН МЕН ТАШКЕНТ ОРДА ҚҰРАМЫНДА"),
        "bullets": [
            ("ЭКОНОМИКА", "Ұлы Жібек жолының сауда торабы"),
            ("САЯСИ ОРТАЛЫҚ", "Түркістан — хан ордасы мен жиын орны"),
        ],
    },
    # --- CHAPTER 3: 1643 ORBULAK ---
    {
        "text": "Үшінші белес — тарихта сирек кездесетін Орбұлақ шайқасы. Алты жүз сарбаз елу мың қолға қарсы тұрды.",
        "ch_idx": 3, "top": "ІІІ ТАРАУ • 1643 ОРБҰЛАҚ ШАЙҚАСЫ", "sub": "600 ҚАЗАҚ САРБАЗЫ 50 000 ҚОЛҒА ҚАРСЫ",
        "mode": "hero", "plate": "scenes_ep02/scene_01.jpg",
        "hero_num": "1643", "hero_title": "ОРБҰЛАҚ ШАТҚАЛЫ",
        "hero_sub": "САЛҚАМ ЖӘҢГІР • 600 vs 50 000",
        "hero_stats": [("ҚАЗАҚ ЖАСАҒЫ", "600 САРБАЗ"), ("ШАБУЫЛДАУШЫ", "50 000 ӘСКЕР"), ("ҚАТЫНАС", "1 : 83 КҮШ ТЕҢСІЗДІГІ")],
    },
    {
        "text": "Салқам Жәңгір шатқалдың тар мойнын таңдап, үш жүз жауынгерді терең оқпандарға жасырды.",
        "ch_idx": 3, "top": "ІІІ ТАРАУ • ТАР ШАТҚАЛ ТАКТИКАСЫ", "sub": "ЕНІ 15–20 МЕТР ТАС ҚЫСАҢ • 300 ЖАУЫНГЕР ОҚПАНДА",
        "mode": "map", "map_id": "ch3_orbulak_trap",
    },
    {
        "text": "Ал биік жартас басынан үш жүз мерген білтелі мылтықпен толассыз қарсы оқ жаудырды.",
        "ch_idx": 3, "top": "ІІІ ТАРАУ • ЕКІ ҚАБАТТЫ ОТ ШЕБІ", "sub": "БИІК ЖАРТАСТАН БІЛТЕЛІ МЫЛТЫҚ ЖАУЫНЫ",
        "mode": "split", "plate": "scenes_ep02/scene_05.jpg",
        "card_title": "300 + 300 СХЕМАСЫ", "card_tag": "ИНЖЕНЕРЛІК ОЙЛАП ТАБУ",
        "bars": [("ТӨМЕНГІ ОҚПАН: 300 ЖАУЫНГЕР", 0.55, GOLD), ("ЖАРТАС МЕРГЕНІ: 300 АТҚЫШ", 0.95, CYAN), ("ШАТҚАЛ ЕНІ (15–20 м)", 0.25, RED)],
        "bullets": [
            ("АУЫСПАЛЫ ШЕП", "Бірінші қатар атса, екіншісі оқтайды"),
            ("ТИІМДІЛІК", "Қалың әскер шатқалда қысылып қалды"),
        ],
    },
    {
        "text": "Дәл шешуші сәтте Самарқаннан жиырма мың қолмен Жалаңтөс Баһадүр жетіп, жаудың тылын талқандады.",
        "ch_idx": 3, "top": "ІІІ ТАРАУ • ЖАЛАҢТӨС БАҺАДҮР СОҚҚЫСЫ", "sub": "САМАРҚАННАН +20 000 САРБАЗ ДӘЛ УАҚЫТЫНДА ЖЕТТІ",
        "mode": "map", "map_id": "ch3_zhalantos",
    },
    {
        "text": "Бір жауынгер сексен үш қарсыласты тоқтатқан бұл ерлік тау шатқалындағы мінсіз қорғаныс үлгісіне айналды.",
        "ch_idx": 3, "top": "ІІІ ТАРАУ • 1 : 83 КҮШ ТЕҢСІЗДІГІ", "sub": "ТАУ ТАКТИКАСЫНЫҢ ӘЛЕМДІК ҮЛГІСІ",
        "mode": "split", "plate": "scenes_ep02/scene_02.jpg",
        "card_title": "1 : 83 ҚАТЫНАС", "card_tag": "ОРБҰЛАҚ ЕРЛІГІ",
        "counter": (83, " ҚАРСЫЛАС", "БІР САРБАЗ ТОҚТАТҚАН КҮШ АРАҚАТЫНАСЫ"),
        "bars": [("ҚАРСЫЛАС АРМИЯСЫ (50 000)", 1.0, RED), ("САЛҚАМ ЖӘҢГІР (600)", 0.08, GOLD), ("ЖАЛАҢТӨС КӨМЕГІ (+20 000)", 0.45, CYAN)],
    },
    # --- CHAPTER 4: ZHETI ZHARGY ---
    {
        "text": "Төртінші жеңіс — қарумен емес, заңмен келген тұрақтылық. Тәуке хан дәуірінде «Жеті Жарғы» қабылданды.",
        "ch_idx": 4, "top": "ІV ТАРАУ • «ЖЕТІ ЖАРҒЫ» ЗАҢЫ", "sub": "ТӘУКЕ ХАН • КҮЛТӨБЕ МЕН ТҮРКІСТАН ЖИЫНЫ",
        "mode": "hero", "plate": "scenes_ep03/scene_06.jpg",
        "hero_num": "ЖЕТІ", "hero_title": "ЖАРҒЫ — ДАЛА ЗАҢЫ",
        "hero_sub": "ТӘУКЕ ХАН • БАЛАНС ЖӘНЕ ТӘРТІП",
        "hero_stats": [("ТІРЕГІ", "7 НЕГІЗГІ ЕРЕЖЕ"), ("АЛҚА", "ҮШ ЖҮЗДІҢ ТӨБЕ БИЛЕРІ"), ("ОРТАЛЫҚ", "ТҮРКІСТАН • КҮЛТӨБЕ")],
    },
    {
        "text": "Төле би, Қазыбек би және Әйтеке би үш жүздің басын қосып, ортақ әділет ережесін орнатты.",
        "ch_idx": 4, "top": "ІV ТАРАУ • ҮШ ЖҮЗДІ БІРІКТІРГЕН ЗАҢ", "sub": "ТӨЛЕ БИ • ҚАЗЫБЕК БИ • ӘЙТЕКЕ БИ",
        "mode": "map", "map_id": "ch4_law",
    },
    {
        "text": "Кімде-кім дау шығарса — билер алқасы қантөгіссіз, әділ бітіммен шешетін мызғымас жүйе құрылды.",
        "ch_idx": 4, "top": "ІV ТАРАУ • БИЛЕР СОТЫ МЕН БІТІМ", "sub": "ДАУЛАРДЫ ҚАНТӨГІССІЗ ШЕШУ ЖҮЙЕСІ",
        "mode": "split", "plate": "scenes_ep06/scene_09.jpg",
        "card_title": "ӘДІЛЕТ ТІЗГІНІ", "card_tag": "ЖЕТІ ЖАРҒЫ",
        "bullets": [
            ("ТӨЛЕ БИ (ҰЛЫ ЖҮЗ)", "Тура билік пен ел іргесі"),
            ("ҚАЗЫБЕК БИ (ОРТА ЖҮЗ)", "Дипломатия мен шешендік"),
            ("ӘЙТЕКЕ БИ (КІШІ ЖҮЗ)", "Ішкі тәртіп пен қорғаныс"),
            ("БАСТЫ ҚАҒИДА", "Жыл сайынғы ортақ Құрылтай"),
        ],
    },
    {
        "text": "Берік заң ішкі тәртіпті нығайтып, бүкіл елді алдағы ең ауыр сынаққа дайындады.",
        "ch_idx": 4, "top": "ІV ТАРАУ • ІШКІ ТҰРАҚТЫЛЫҚ ІРГЕТАСЫ", "sub": "МЫҚТЫ ЗАҢ ҒАНА ЕЛДІ СЫНАҚТАН САҚТАЙДЫ",
        "mode": "split", "plate": "scenes_ep03/scene_11.jpg",
        "card_title": "ТӘРТІП ЖӘНЕ БІРЛІК", "card_tag": "АЛТЫН ҒАСЫР",
        "bars": [("ІШКІ КЕЛІСІМ", 0.96, GOLD), ("ӘДІЛ БИЛІК", 0.94, CYAN), ("ЖОРЫҚҚА ДАЙЫНДЫҚ", 0.90, GOLD)],
        "bullets": [
            ("СҰЛТАНДАР ЕМЕС", "Ортақ ереже бәрінен биік"),
            ("НӘТИЖЕ", "Үш жүз бір арнада топтасты"),
        ],
    },
    # --- CHAPTER 5: 1726-1730 ORDABASY & ANYRAKAI ---
    {
        "text": "Бесінші белес — Ордабасы құрылтайы мен Аңырақай шайқасы. Дала халқының тағдыры шешілген шақ.",
        "ch_idx": 5, "top": "V ТАРАУ • 1726–1730 ОРДАБАСЫ • АҢЫРАҚАЙ", "sub": "ДАЛА ХАЛҚЫНЫҢ ТАҒДЫРЫ ШЕШІЛГЕН СЫНАҚ",
        "mode": "hero", "plate": "scenes/scene_06_1794215174000.jpg",
        "hero_num": "1730", "hero_title": "ОРДАБАСЫ МЕН АҢЫРАҚАЙ",
        "hero_sub": "АБЫЛАЙ • БӨГЕНБАЙ • ҚАБАНБАЙ",
        "hero_stats": [("1726 ЖЫЛ", "ОРДАБАСЫ ҚҰРЫЛТАЙЫ"), ("БАС САРДАР", "ӘБІЛҚАЙЫР ХАН (МЕРИТОКРАТИЯ)"), ("ӘДІСІ", "ТОЛҒАМА ҚАҚПАНЫ")],
    },
    {
        "text": "Ордабасы тауында үш жүз ант беріп, «Жылу» заңымен батыстан оңтүстікке ондаған мың тұлпар жөнелтті.",
        "ch_idx": 5, "top": "V ТАРАУ • «АНТ» ЖӘНЕ «ЖЫЛУ» ЗАҢЫ", "sub": "ҮШ ЖҮЗДІҢ ТҮМЕНДЕРІ ОРДАБАСЫҒА ЖИНАЛДЫ",
        "mode": "map", "map_id": "ch5_ordabasy",
    },
    {
        "text": "Аңырақай даласында он сегіз жасар Сабалақ жекпе-жекте Шарышты құлатып, сарбаздар рухын көтерді.",
        "ch_idx": 5, "top": "V ТАРАУ • 18 ЖАСАР САБАЛАҚ ЖЕКПЕ-ЖЕГІ", "sub": "«АБЫЛАЙЛАП!» ҰРАНДАҒАН ЖАС БАҺАДҮР",
        "mode": "split", "plate": "scenes_ep05/scene_16.jpg",
        "card_title": "ЖЕКПЕ-ЖЕК ШЕШІМІ", "card_tag": "АҢЫРАҚАЙ 1729/1730",
        "bars": [("ЖАУЫНГЕР РУХЫ", 1.0, GOLD), ("ОРТАҚ ҚОЛБАСШЫЛЫҚ", 0.94, CYAN), ("БӨГЕНБАЙ • ҚАБАНБАЙ", 0.97, GOLD)],
        "bullets": [
            ("АБЫЛАЙ ҰРАНЫ", "Жалпы шабуылдың белгісі болды"),
            ("ТӘРТІП", "Лауазым емес — әскери дарын"),
        ],
    },
    {
        "text": "Әбілқайыр, Бөгенбай мен Қабанбай «Толғама» әдісімен жауды Алакөл сор даласына қамап, талқандады.",
        "ch_idx": 5, "top": "V ТАРАУ • «ТОЛҒАМА» ҚОРШАУЫ", "sub": "ХАНТАУ МЕН ИТ-ІШПЕС АЛАКӨЛ АРАСЫНДАҒЫ ҚАҚПАН",
        "mode": "map", "map_id": "ch5_tolgama",
    },
    {
        "text": "Қырық күнге созылған бұл жеңіс шепті қорғап қана қоймай, болашақ ханды тарих сахнасына шығарды.",
        "ch_idx": 5, "top": "V ТАРАУ • 40 КҮНДІК ЖЕҢІС", "sub": "БІРІККЕН ЕЛДІ ЕШБІР КҮШ СЫНДЫРА АЛМАЙДЫ",
        "mode": "split", "plate": "scenes/scene_18_1794250296208.jpg",
        "card_title": "40 КҮНДІК ШАЙҚАС", "card_tag": "1729–1730 • ЖЕҢІС",
        "counter": (40, " КҮН", "АҢЫРАҚАЙ ДАЛАСЫНДАҒЫ ТОЛЫҚ ЖЕҢІС"),
        "bullets": [
            ("ЖАУ ТАКТИКАСЫ", "Ауыр зеңбіректен қол үзді"),
            ("ҚОРЫТЫНДЫ", "Тұтас дала қайта бірікті"),
        ],
    },
    # --- CHAPTER 6: 1771 ABYLAI KHAN ---
    {
        "text": "Алтыншы белес — Түркістанда үш жүздің ақ киізіне көтерілген Абылай ханның теңдессіз дипломатиясы.",
        "ch_idx": 6, "top": "VІ ТАРАУ • 1771 АБЫЛАЙ ХАН СТРАТЕГИЯСЫ", "sub": "ТҮРКІСТАНДА АҚ КИІЗГЕ КӨТЕРІЛГЕН ҮШ ЖҮЗДІҢ ХАНЫ",
        "mode": "split", "plate": "scenes_ep06/scene_05.jpg",
        "card_title": "1771 • ТҮРКІСТАН", "card_tag": "АБЫЛАЙ ХАН ОРДАСЫ",
        "seesaw": True,
        "bullets": [
            ("БАСТЫ АЙЛА", "Екі алып империяны тең ұстау"),
            ("МАҚСАТ", "Дербестік пен бейбіт сауда"),
        ],
    },
    {
        "text": "Солтүстіктен Ресей, шығыстан Цин империясы қысқанда, Абылай хан екі алыпты шеберлікпен тең ұстады.",
        "ch_idx": 6, "top": "VІ ТАРАУ • ҚОС МАЙДАН ТЕПЕ-ТЕҢДІГІ", "sub": "СОЛТҮСТІКТЕ РЕСЕЙ • ШЫҒЫСТА ЦИН • ОРТАДА ҚАЗАҚ ОРДАСЫ",
        "mode": "map", "map_id": "ch6_balance",
    },
    {
        "text": "Қабанбай мен Бөгенбай бастаған шапшаң атты әскер Жетісу, Тарбағатай мен Зайсанды елге қайтарды.",
        "ch_idx": 6, "top": "VІ ТАРАУ • ШЫҒЫС ЖАЙЛАУЛАРЫ ОРАЛДЫ", "sub": "ЖЕТІСУ • ТАРБАҒАТАЙ • ЗАЙСАН ТОЛЫҚ ҚАЙТАРЫЛДЫ",
        "mode": "map", "map_id": "ch6_east",
    },
    {
        "text": "Ақыл мен айла арқасында Қазақ шекарасы Жайықтан Алтай тауларына дейін мызғымастай бекіді.",
        "ch_idx": 6, "top": "VІ ТАРАУ • БЕРІК ШЕКАРА: ЖАЙЫҚ – АЛТАЙ", "sub": "АУЫР ОБОЗДАН ×3 ЖЫЛДАМ МАНЕВР • ДИПЛОМАТИЯ",
        "mode": "hero", "plate": "scenes_ep06/scene_07.jpg",
        "hero_num": "1771", "hero_title": "ЖАЙЫҚТАН АЛТАЙҒА ДЕЙІН",
        "hero_sub": "АБЫЛАЙ ХАН • ДЕРБЕС ШЕКАРА",
        "hero_stats": [("БАТЫС ШЕК", "ЕДІЛ МЕН ЖАЙЫҚ"), ("ШЫҒЫС ШЕК", "ТАРБАҒАТАЙ • ЗАЙСАН • АЛТАЙ"), ("ҚАРҚЫН", "×3 АТТЫ ӘСКЕР ЖЫЛДАМДЫҒЫ")],
    },
    # --- EPILOGUE ---
    {
        "text": "Алты ғасырлық тәжірибе төрт тіректі дәлелдеді: ел бірлігі, әділ заң, өзара жылу және стратегиялық ақыл.",
        "ch_idx": 6, "top": "ҚОРЫТЫНДЫ • ҰЛЫ ДАЛАНЫҢ ТӨРТ ТІРЕГІ", "sub": "БІРЛІК • ӘДІЛ ЗАҢ • ЖЫЛУ • СТРАТЕГИЯЛЫҚ АҚЫЛ",
        "mode": "map", "map_id": "epilogue_border",
    },
    {
        "text": "Келесі үлкен деректі фильмде қай шайқас пен қай тұлғаны талдайық? Пікір жазып, арнаға жазылыңыз!",
        "ch_idx": 6, "top": "КЕЛЕСІ ШЫҒАРЫЛЫМ • АРНАҒА ЖАЗЫЛЫҢЫЗ", "sub": "ПІКІРДЕ КЕЛЕСІ ТАҚЫРЫПТЫ ҰСЫНЫҢЫЗ",
        "mode": "hero", "plate": "scenes_ep06/scene_12.jpg",
        "hero_num": "6/6", "hero_title": "КЕЛЕСІ ДЕРЕКТІ ФИЛЬМ?",
        "hero_sub": "ТАРИХТЫ БІРГЕ ЗЕРТТЕЙІК",
        "hero_stats": [("БІРІНШІ ТІРЕК", "ТЕМІРДЕЙ БІРЛІК"), ("ЕКІНШІ ТІРЕК", "ӘДІЛ «ЖЕТІ ЖАРҒЫ» ЗАҢЫ"), ("ҮШІНШІ ТІРЕК", "ШЫНАЙЫ ЖЫЛУ МЕН АҚЫЛ")],
    },
]

# Widescreen Map World Coordinates [0..1920, 0..1080] — all labels cleanly inside y=195..825 above subtitle band
CITIES_169 = {
    "Сарайшық":   (240, 365),
    "Ұлытау":     (645, 420),
    "Көкшетау":   (825, 235),
    "Сығанақ":    (615, 585),
    "Түркістан":  (710, 645),
    "Ордабасы":   (795, 695),
    "Ташкент":    (835, 765),
    "Самарқан":   (685, 815),
    "Бұхара":     (435, 790),
    "Орбұлақ":    (1285, 610),
    "Аңырақай":   (1085, 640),
    "Жетісу":     (1225, 690),
    "Тарбағатай": (1470, 455),
    "Зайсан":     (1565, 345),
    "Алтай":      (1635, 225),
}

LABEL_SIDE_169 = {
    "Сарайшық":   "below",
    "Көкшетау":   "above",
    "Ұлытау":     "left",
    "Сығанақ":    "left",
    "Түркістан":  "left",
    "Ордабасы":   "right",
    "Ташкент":    "right",
    "Самарқан":   "below",
    "Бұхара":     "left",
    "Орбұлақ":    "right",
    "Аңырақай":   "left",
    "Жетісу":     "below",
    "Тарбағатай": "left",
    "Зайсан":     "left",
    "Алтай":      "above",
}

RIVERS_169 = {
    "ЖАЙЫҚ":     [(305, 165), (270, 275), (240, 365), (210, 465)],
    "ЕРТІС":     [(1740, 175), (1550, 330), (1320, 290), (1080, 185)],
    "СЫРДАРИЯ":  [(1080, 740), (885, 725), (710, 645), (555, 560), (415, 490)],
    "ІЛЕ":       [(1440, 705), (1240, 675), (1085, 575)],
    "ЗЕРАВШАН":  [(920, 815), (705, 815), (535, 800), (350, 825)],
}


@lru_cache(maxsize=48)
def get_font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_PATH), size)


def smoothstep(x: float) -> float:
    x = max(0.0, min(1.0, x))
    return x * x * (3.0 - 2.0 * x)


def ease_out(x: float) -> float:
    x = max(0.0, min(1.0, x))
    return 1.0 - (1.0 - x) ** 3


def fbm_noise(h: int, w: int, octaves: int = 5, base_scale: float = 150.0, seed: int = 1771) -> np.ndarray:
    rng = np.random.default_rng(seed)
    acc = np.zeros((h, w), dtype=np.float32)
    amp = 1.0
    norm_s = 0.0
    for k in range(octaves):
        sig = max(1.5, base_scale / (2.0 ** k))
        gh = max(8, int(h / max(4.0, sig * 0.6)))
        gw = max(8, int(w / max(4.0, sig * 0.6)))
        grid = rng.standard_normal((gh, gw)).astype(np.float32)
        up = np.array(Image.fromarray(grid).resize((w, h), Image.Resampling.BICUBIC), dtype=np.float32)
        up = gaussian_filter(up, sigma=max(1.0, sig * 0.14))
        acc += amp * up
        norm_s += amp
        amp *= 0.52
    acc /= max(1e-6, norm_s)
    mn, mx = float(acc.min()), float(acc.max())
    return (acc - mn) / max(1e-6, mx - mn)


def eval_polyline(pts: list[tuple[float, float]], n_samples: int = 120) -> list[tuple[float, float]]:
    p = [pts[0]] + list(pts) + [pts[-1]]
    out = []
    segs = len(pts) - 1
    steps_per = max(4, n_samples // max(1, segs))
    for i in range(segs):
        p0, p1, p2, p3 = p[i], p[i + 1], p[i + 2], p[i + 3]
        for s in range(steps_per):
            t = s / steps_per
            t2, t3 = t * t, t * t * t
            x = 0.5 * ((2 * p1[0]) + (-p0[0] + p2[0]) * t + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2 + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3)
            y = 0.5 * ((2 * p1[1]) + (-p0[1] + p2[1]) * t + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2 + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3)
            out.append((x, y))
    out.append(pts[-1])
    return out


def point_along_path(pts: list[tuple[float, float]], frac: float) -> tuple[float, float, float]:
    frac = max(0.0, min(1.0, frac))
    if len(pts) < 2:
        return pts[0][0], pts[0][1], 0.0
    idx = min(len(pts) - 2, int(frac * (len(pts) - 1)))
    rem = frac * (len(pts) - 1) - idx
    x0, y0 = pts[idx]
    x1, y1 = pts[idx + 1]
    return x0 + (x1 - x0) * rem, y0 + (y1 - y0) * rem, math.atan2(y1 - y0, x1 - x0)


class WidescreenMapCamera:
    def __init__(self, zoom: float, cx: float, cy: float):
        self.zoom = max(1.0, zoom)
        self.vw = W / self.zoom
        self.vh = H / self.zoom
        self.x0 = max(0.0, min(W - self.vw, cx - self.vw * 0.5))
        self.y0 = max(0.0, min(H - self.vh, cy - self.vh * 0.5))

    def to_screen(self, wx: float, wy: float) -> tuple[float, float]:
        return (wx - self.x0) * self.zoom, (wy - self.y0) * self.zoom


_HI_MAP_169 = None


def build_widescreen_relief_map() -> Image.Image:
    """Precompute a 2x (3840x2160) 3D-hillshaded Kazakh Steppe atlas ONCE."""
    global _HI_MAP_169
    if _HI_MAP_169 is not None:
        return _HI_MAP_169
    w0, h0 = 1920, 1080
    elev = fbm_noise(h0, w0, octaves=6, base_scale=175.0, seed=1771)
    ridge = 1.0 - np.abs(fbm_noise(h0, w0, octaves=4, base_scale=120.0, seed=1730) * 2.0 - 1.0)
    hmap = elev * 0.72 + (ridge ** 1.45) * 0.34

    yy, xx = np.mgrid[0:h0, 0:w0].astype(np.float32)
    # Mountain ranges: Ulytau center, Pamir/Alatau southeast, Altai northeast
    altai = np.exp(-(((xx - 1650) / 280.0) ** 2 + ((yy - 250) / 180.0) ** 2))
    alatau = np.exp(-(((xx - 1290) / 260.0) ** 2 + ((yy - 670) / 150.0) ** 2))
    ulytau = np.exp(-(((xx - 645) / 180.0) ** 2 + ((yy - 420) / 120.0) ** 2))
    hmap = hmap + altai * 0.36 + alatau * 0.32 + ulytau * 0.16

    dz_dx = sobel(hmap, axis=1) * 3.1
    dz_dy = sobel(hmap, axis=0) * 3.1
    az = math.radians(315.0)
    alt = math.radians(34.0)
    lx = math.cos(alt) * math.cos(az)
    ly = math.cos(alt) * math.sin(az)
    lz = math.sin(alt)
    shade = np.clip((lz - dz_dx * lx - dz_dy * ly) / np.sqrt(1.0 + dz_dx ** 2 + dz_dy ** 2), 0.14, 1.0)

    rgb = np.zeros((h0, w0, 3), dtype=np.float32)
    lowland = np.clip(1.0 - (hmap / 0.85), 0.0, 1.0)
    rgb[..., 0] = (20 + 28 * hmap + 12 * ridge) * (0.40 + 0.65 * shade)
    rgb[..., 1] = (22 + 24 * hmap + 10 * lowland) * (0.40 + 0.64 * shade)
    rgb[..., 2] = (18 + 18 * lowland) * (0.44 + 0.60 * shade)

    base = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8)).resize((W * 2, H * 2), Image.Resampling.BICUBIC)
    d = ImageDraw.Draw(base)
    # Graticule coordinate grid
    for gx in range(0, W * 2 + 1, 240):
        d.line([(gx, 0), (gx, H * 2)], fill=(48, 62, 74, 110), width=2)
    for gy in range(0, H * 2 + 1, 216):
        d.line([(0, gy), (W * 2, gy)], fill=(48, 62, 74, 110), width=2)

    # Kazakh Steppe Lakes (Aral, Balkhash, Zaisan, Alakol) hints on 2x canvas
    d.ellipse([660, 1020, 820, 1190], fill=(16, 48, 68), outline=(58, 165, 195), width=2)  # Aral
    d.polygon([(1920, 1130), (2180, 1075), (2420, 1090), (2350, 1165), (2050, 1185)], fill=(18, 52, 72))  # Balkhash
    d.ellipse([2680, 990, 2810, 1045], fill=(18, 52, 72))  # Alakol
    d.ellipse([3070, 665, 3195, 715], fill=(18, 52, 72))  # Zaisan

    _HI_MAP_169 = base.convert("RGB")
    return _HI_MAP_169


# Precomputed mist strips for 1920x1080 & 1080x760 panels
@lru_cache(maxsize=6)
def make_mist_tile(tw: int, th: int, seed: int = 88) -> np.ndarray:
    n = fbm_noise(th, tw, octaves=4, base_scale=110.0, seed=seed)
    vfade = np.sin(np.linspace(0.0, math.pi, th, dtype=np.float32))[:, None]
    alpha = np.clip((n - 0.34) * 2.1, 0.0, 1.0) * vfade
    return (alpha * 54.0).astype(np.uint8)


def draw_mist_overlay(ov: Image.Image, t: float, col=(245, 214, 152), y_dest: int = 680, speed: float = 48.0):
    tw, th = W, 240
    strip = make_mist_tile(tw, th, 88)
    shift = int((t * speed) % tw)
    rolled = np.roll(strip, shift, axis=1)
    rgba = np.zeros((th, tw, 4), dtype=np.uint8)
    rgba[..., 0], rgba[..., 1], rgba[..., 2], rgba[..., 3] = col[0], col[1], col[2], rolled
    ov.alpha_composite(Image.fromarray(rgba, mode="RGBA"), dest=(0, y_dest))


def draw_arrow_barrage_wide(ov: Image.Image, t: float, count: int = 44, go_right: bool = True, x0: int = 0, x1: int = W, y0: int = 120, y1: int = 870):
    d = ImageDraw.Draw(ov)
    span_w = max(200, x1 - x0)
    span_h = max(160, y1 - y0)
    for k in range(count):
        seed_f = (k * 0.6180339) % 1.0
        spd = 1.15 + (k % 5) * 0.24
        phase = (t * spd + seed_f) % 1.0
        ax = (x0 - 80 + phase * (span_w + 160)) if go_right else (x1 + 80 - phase * (span_w + 160))
        ay = y0 + ((k * 83) % span_h) + math.sin(phase * math.pi) * (-26.0)
        vx = (48.0 if go_right else -48.0) * spd
        vy = -12.0 * math.cos(phase * math.pi)
        al = 140 + (k % 3) * 32
        d.line([(ax - vx, ay - vy), (ax, ay)], fill=(235, 232, 224, al), width=2)
        d.line([(ax - vx * 0.25, ay - vy * 0.25), (ax, ay)], fill=(255, 216, 118, min(255, al + 45)), width=4)


# ---------------------------------------------------------------------------
# AUDIO SYNTHESIS & ALIGNMENT
# ---------------------------------------------------------------------------
async def _synth_line_async(text: str, voice: str, rate: str, pitch: str, mp3_path: Path):
    comm = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch, boundary="WordBoundary")
    bounds = []
    with open(mp3_path, "wb") as f:
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                bounds.append({"w": chunk["text"], "t0": chunk["offset"] / 1e7, "t1": (chunk["offset"] + chunk["duration"]) / 1e7})
    return bounds


def synth_line_with_retry(text: str, mp3_path: Path, wav_path: Path):
    bounds_path = wav_path.with_suffix(".json")
    if wav_path.exists() and wav_path.stat().st_size > 4000 and bounds_path.exists():
        return json.loads(bounds_path.read_text(encoding="utf-8"))

    bounds = []
    last_err = None
    for voice in (VOICE_MAIN, VOICE_FALLBACK):
        for attempt in range(4):
            try:
                if mp3_path.exists():
                    mp3_path.unlink()
                bounds = asyncio.run(_synth_line_async(text, voice, VOICE_RATE, VOICE_PITCH, mp3_path))
                if mp3_path.exists() and mp3_path.stat().st_size > 2000:
                    last_err = None
                    break
            except Exception as e:
                last_err = e
            time.sleep(0.5 * (attempt + 1))
        if last_err is None and mp3_path.exists() and mp3_path.stat().st_size > 2000:
            break
    if last_err is not None or not mp3_path.exists() or mp3_path.stat().st_size <= 2000:
        raise RuntimeError(f"KZ TTS failed: {last_err}")

    subprocess.run(
        [FFMPEG, "-y", "-i", str(mp3_path), "-af", VOICE_FX, "-ar", str(SR), "-ac", "1", "-c:a", "pcm_s16le", str(wav_path)],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    bounds_path.write_text(json.dumps(bounds, ensure_ascii=False), encoding="utf-8")
    return bounds


def read_wav_mono(path: Path) -> np.ndarray:
    with wave.open(str(path), "rb") as wf:
        raw = wf.readframes(wf.getnframes())
    return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0


def trim_silence(x: np.ndarray, pad_s: float = 0.03, thresh: float = 0.010) -> np.ndarray:
    idx = np.where(np.abs(x) > thresh)[0]
    if len(idx) == 0:
        return x
    pad = int(pad_s * SR)
    i0 = max(0, int(idx[0]) - pad)
    i1 = min(len(x), int(idx[-1]) + int(0.05 * SR))
    out = x[i0:i1].copy()
    fi = min(int(0.012 * SR), len(out) // 4)
    fo = min(int(0.018 * SR), len(out) // 4)
    if fi > 0:
        out[:fi] *= np.linspace(0.0, 1.0, fi)
    if fo > 0:
        out[-fo:] *= np.linspace(1.0, 0.0, fo)
    return out


def align_words(text: str, raw_bounds: list, seg_start: float, speech_dur: float, scene_num: int):
    display_words = text.split()
    if raw_bounds and abs(len(raw_bounds) - len(display_words)) <= 2 and raw_bounds[-1]["t1"] > 0.2:
        b0 = raw_bounds[0]["t0"]
        b1 = max(b0 + 0.1, raw_bounds[-1]["t1"])
        scale = speech_dur / (b1 - b0)
        out = []
        for idx, w in enumerate(display_words):
            bi = min(idx, len(raw_bounds) - 1)
            wt0 = seg_start + (raw_bounds[bi]["t0"] - b0) * scale
            wt1 = seg_start + (raw_bounds[bi]["t1"] - b0) * scale
            if out and wt0 < out[-1]["t1"]:
                wt0 = out[-1]["t1"]
            wt1 = max(wt0 + 0.07, wt1)
            out.append({"w": w, "scene": scene_num, "t0": round(wt0, 3), "t1": round(wt1, 3)})
        return out

    vowels = set("аеёиоуыэюяәіңғүұқөһАЕЁИОУЫЭЮЯӘІҢҒҮҰҚӨҺaeiouyAEIOUY")
    weights = []
    for w in display_words:
        v = sum(1 for c in w if c in vowels)
        p = 1.4 if w[-1] in ".!?" else (0.7 if w[-1] in ",;—–:" else 0.0)
        weights.append(max(1.1, v * 1.0 + len(w) * 0.16 + p))
    tot = sum(weights)
    t_cur = seg_start
    out = []
    for w, wt in zip(display_words, weights):
        dur_w = speech_dur * (wt / tot)
        out.append({"w": w, "scene": scene_num, "t0": round(t_cur, 3), "t1": round(t_cur + dur_w, 3)})
        t_cur += dur_w
    return out


def build_voice_and_timeline():
    ldir = BUILD / "kz"
    ldir.mkdir(parents=True, exist_ok=True)
    voice_wav = ldir / "voice.wav"

    clips = []
    timeline = []
    words_all = []
    t_cursor = 0.0

    for si, sc in enumerate(SCENES):
        text = sc["text"]
        mp3_p = ldir / f"line_{si:02d}.mp3"
        wav_p = ldir / f"line_{si:02d}.wav"
        bounds = synth_line_with_retry(text, mp3_p, wav_p)
        raw = read_wav_mono(wav_p)
        spoken = trim_silence(raw)
        speech_dur = len(spoken) / SR
        pause_after = 0.35 if si == len(SCENES) - 1 else (0.24 if si in CHAPTER_BREAK_SCENES else 0.10)
        seg_dur = speech_dur + pause_after

        clips.append(spoken)
        clips.append(np.zeros(int(round(pause_after * SR)), dtype=np.float32))
        timeline.append({
            "scene": si + 1,
            "ch_idx": sc["ch_idx"],
            "title": sc["top"],
            "t0": round(t_cursor, 4),
            "t1": round(t_cursor + seg_dur, 4),
            "speech_dur": round(speech_dur, 4),
            "text": text,
        })
        words_all.extend(align_words(text, bounds, t_cursor, speech_dur, si + 1))
        t_cursor += seg_dur

    full_voice = np.concatenate(clips)
    smod.write(str(voice_wav), smod.norm(full_voice, 0.94))
    return voice_wav, timeline, words_all, len(full_voice) / SR


def run_yt_sfx(voice_wav: Path, timeline: list, dur: float) -> Path:
    ldir = BUILD / "kz"
    mix_raw = ldir / "mix_raw.wav"
    mix_wav = ldir / "mix.wav"
    if mix_wav.exists() and mix_wav.stat().st_size > 100000:
        return mix_wav

    v = smod.bp(read_wav_mono(voice_wav).astype(np.float64), 80, 11500)
    N = int(round(dur * SR))
    amb = np.zeros((N, 2), dtype=np.float64)
    rng = np.random.default_rng(177101)

    # Natural wind bed across the documentary (zero musical instruments)
    bed = smod.wind(rng, dur, howl=0.22) * 0.25
    amb += smod.st(bed, 0.0)

    # 7-chapter shifting male A cappella vocal choir progressions (halal, atmospheric)
    D3, E3, F3, G3, A3, Bb3, C4, D4, E4 = 146.83, 164.81, 174.61, 196.00, 220.00, 233.08, 261.63, 293.66, 329.63
    chap_starts = [0.0, timeline[2]["t0"], timeline[6]["t0"], timeline[10]["t0"], timeline[15]["t0"], timeline[19]["t0"], timeline[24]["t0"], dur]
    chap_chords = [
        ((D3, F3, A3, D4), "o", 0.34),
        ((D3, F3, Bb3, D4), "u", 0.34),
        ((E3, G3, A3, D4), "o", 0.36),
        ((D3, F3, A3, C4), "u", 0.38),
        ((F3, A3, C4, D4), "o", 0.34),
        ((D3, F3, G3, D4, E4), "a", 0.40),
        ((D3, F3, A3, D4, E4), "a", 0.38),
    ]
    for ci, ((chord, vow, amp), t_a, t_b) in enumerate(zip(chap_chords, chap_starts[:-1], chap_starts[1:])):
        cdur = max(1.0, t_b - t_a)
        smod.add(amb, smod.reverb(smod.vocal_pad(rng, cdur, chord, vow, 4), wet=0.42, seed=800 + ci) * amp, t_a)

    # Scene-matched physical SFX
    for si, seg in enumerate(timeline):
        t0, sd = seg["t0"], seg["t1"] - seg["t0"]
        if si == 0:
            smod.add(amb, smod.reverb(smod.impact_boom(rng, 1.8), wet=0.28, seed=901) * 0.68, 0.02)
            smod.add(amb, smod.reverb(smod.sword_clash(rng), wet=0.22, seed=902) * 0.50, 0.06)
            smod.add(amb, smod.st(smod.whoosh(rng, 0.45), -0.25) * 0.44, sd * 0.35)
            smod.add(amb, smod.st(smod.whoosh(rng, 0.45), 0.25) * 0.44, sd * 0.70)
        elif si in {2, 6, 10, 15, 19, 24}:
            # Chapter transition boom
            smod.add(amb, smod.reverb(smod.impact_boom(rng, 1.6), wet=0.30, seed=910 + si) * 0.56, t0)
        if si in {3, 4}:
            smod.add(amb, smod.st(smod.gallop_fast(rng, min(4.0, sd)), -0.1) * 0.36, t0 + 0.3)
        elif si in {7, 8, 26, 27}:
            smod.add(amb, smod.st(smod.herd_far(rng, min(4.5, sd)), 0.15) * 0.38, t0 + 0.2)
        elif si in {11, 12, 13}:
            smod.add(amb, smod.reverb(smod.clasp(rng), wet=0.22, seed=930 + si) * 0.42, t0 + 0.3)
            if si == 13:
                smod.add(amb, smod.st(smod.gallop(rng, min(4.0, sd), horses=12, rate=2.5), 0.0) * 0.45, t0 + 0.4)
        elif si in {17, 18, 25}:
            smod.add(amb, smod.reverb(smod.clasp(rng), wet=0.25, seed=950 + si) * 0.38, t0 + 0.25)
        elif si in {20, 21, 22}:
            if si == 21:
                smod.add(amb, smod.reverb(smod.sword_clash(rng), wet=0.25, seed=961) * 0.48, t0 + 0.5)
            if si == 22:
                smod.add(amb, smod.st(smod.herd(rng, min(4.5, sd)), 0.0) * 0.42, t0 + 0.2)
        elif si in {28, 29}:
            smod.add(amb, smod.st(smod.eagle(rng), 0.22) * 0.38, t0 + 0.3)
            if si == 29:
                smod.add(amb, smod.st(smod.riser(rng, min(2.0, sd * 0.5)), 0.0) * 0.36, max(t0, dur - 2.2))

    rms = smod.frame_rms(v, win=0.05)
    rms_st = np.interp(np.arange(N), np.arange(len(rms)) * int(SR * 0.05), rms)
    duck = 1.0 - 0.56 * np.clip(rms_st / 0.085, 0.0, 1.0)
    amb *= duck[:, None]

    out = amb * 0.88 + smod.st(v, 0.0) * 1.00
    out = smod.softclip(out, 0.90)
    smod.write(str(mix_raw), out)
    r = subprocess.run([FFMPEG, "-hide_banner", "-i", str(mix_raw), "-af", "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"], capture_output=True, text=True)
    js = json.loads(r.stderr[r.stderr.rindex("{"):r.stderr.rindex("}") + 1])
    af = f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={js['input_i']}:measured_TP={js['input_tp']}:measured_LRA={js['input_lra']}:measured_thresh={js['input_thresh']}:offset={js['target_offset']}:linear=true"
    subprocess.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", str(mix_raw), "-af", af, "-ar", "48000", str(mix_wav)], check=True)
    return mix_wav


# ---------------------------------------------------------------------------
# WIDESCREEN MAP & GRAPHIC ELEMENTS (1920x1080)
# ---------------------------------------------------------------------------
def draw_city_node_169(ov: Image.Image, cam: WidescreenMapCamera, name: str, status: str, burst_u: float, t: float, emphasis: bool = False):
    wx, wy = CITIES_169[name]
    sx, sy = cam.to_screen(wx, wy)
    if not (-60 <= sx <= W + 60 and 95 <= sy <= H - 150):
        return
    d = ImageDraw.Draw(ov)

    if status == "red":
        c_fill, c_ring = RED, (255, 130, 110)
    elif status == "capturing":
        c_fill, c_ring = CYAN, (180, 255, 255)
    elif status == "neutral":
        c_fill, c_ring = (140, 152, 165), (195, 208, 220)
    else:
        c_fill, c_ring = GOLD, (110, 232, 230)

    r = 20 if emphasis else 14
    if burst_u > 0.0 and burst_u < 1.0:
        br = int(r + 65 * ease_out(burst_u))
        ba = int(230 * (1.0 - burst_u))
        d.ellipse([sx - br, sy - br, sx + br, sy + br], outline=(248, 202, 84, ba), width=4)

    pulse = 1.0 + 0.14 * math.sin(t * 4.5 + wx * 0.02)
    ro = int((r + 9) * pulse)
    d.ellipse([sx - ro, sy - ro, sx + ro, sy + ro], outline=(*c_ring[:3], 130), width=2)
    d.ellipse([sx - r - 3, sy - r - 3, sx + r + 3, sy + r + 3], fill=(12, 18, 28, 235), outline=(*c_ring[:3], 245), width=2)
    # Fortress silhouette inside node
    fw = int(r * 0.56)
    d.rectangle([sx - fw, sy - fw + 3, sx + fw, sy + fw - 1], fill=(*c_fill[:3], 245))
    d.pieslice([sx - fw, sy - r + 2, sx + fw, sy - fw + 8], 180, 360, fill=(*c_fill[:3], 245))

    f_lbl = get_font(22 if emphasis else 19)
    tw = d.textlength(name, font=f_lbl)
    side = LABEL_SIDE_169.get(name, "below")
    if side == "above":
        tx, ty = sx - tw * 0.5, sy - r - 32
    elif side == "left":
        tx, ty = sx - r - 14 - tw, sy - 11
    elif side == "right":
        tx, ty = sx + r + 14, sy - 11
    else:
        tx, ty = sx - tw * 0.5, sy + r + 10
    d.rounded_rectangle([tx - 7, ty - 2, tx + tw + 7, ty + 25], radius=6, fill=(10, 16, 24, 215), outline=(*c_ring[:3], 140), width=1)
    d.text((tx, ty), name, font=f_lbl, fill=(252, 248, 236, 252))


def draw_arrow_169(ov: Image.Image, cam: WidescreenMapCamera, pts_world: list, progress: float, t: float, col_main=GOLD, col_glow=CYAN, width: int = 10):
    if progress <= 0.02:
        return
    dense = eval_polyline(pts_world, 120)
    n_show = max(2, int(len(dense) * min(1.0, progress)))
    pts = [cam.to_screen(x, y) for x, y in dense[:n_show]]
    d = ImageDraw.Draw(ov)
    d.line(pts, fill=(*col_glow[:3], 75), width=width + 10, joint="curve")
    d.line(pts, fill=(*col_main[:3], 240), width=width, joint="curve")
    # Moving pulse ticks
    for m in range(3):
        frac = ((t * 0.8 + m * 0.33) % 1.0) * min(0.95, progress)
        if frac > 0.05:
            px, py, _ = point_along_path(dense, frac)
            sx, sy = cam.to_screen(px, py)
            d.ellipse([sx - 4, sy - 4, sx + 4, sy + 4], fill=(255, 252, 240, 235))
    hx, hy = pts[-1]
    px0, py0 = pts[max(0, len(pts) - 4)]
    ang = math.atan2(hy - py0, hx - px0)
    sz = width * 1.9 + 5
    d.polygon([
        (hx + math.cos(ang) * 6, hy + math.sin(ang) * 6),
        (hx - math.cos(ang - 0.55) * sz, hy - math.sin(ang - 0.55) * sz),
        (hx - math.cos(ang + 0.55) * sz, hy - math.sin(ang + 0.55) * sz),
    ], fill=(*col_main[:3], 255))


def draw_unit_badge_169(ov: Image.Image, cam: WidescreenMapCamera, wx: float, wy: float, label: str, t: float, col=GOLD, off=(0, -48)):
    sx, sy = cam.to_screen(wx, wy)
    if not (-60 <= sx <= W + 60 and 95 <= sy <= H - 150):
        return
    d = ImageDraw.Draw(ov)
    bob = math.sin(t * 6.0) * 3.0
    by = sy + bob
    d.polygon([(sx - 18, by + 10), (sx, by - 14), (sx + 18, by + 10), (sx + 11, by + 15), (sx - 11, by + 15)], fill=(*col[:3], 245), outline=(12, 16, 22, 255))
    f = get_font(19)
    tw = d.textlength(label, font=f)
    lx, ly = sx + off[0] - tw * 0.5, by + off[1]
    d.rounded_rectangle([lx - 10, ly - 4, lx + tw + 10, ly + 26], radius=8, fill=(10, 16, 24, 225), outline=(*col[:3], 235), width=2)
    d.text((lx, ly), label, font=f, fill=(*col[:3], 255))


def render_widescreen_map_base(zoom: float, cx: float, cy: float, t: float, tint=None) -> tuple[Image.Image, WidescreenMapCamera]:
    cam = WidescreenMapCamera(zoom, cx, cy)
    hi = build_widescreen_relief_map()
    box_2x = (cam.x0 * 2.0, cam.y0 * 2.0, (cam.x0 + cam.vw) * 2.0, (cam.y0 + cam.vh) * 2.0)
    bg = hi.transform((W, H), Image.Transform.EXTENT, box_2x, Image.Resampling.BILINEAR).convert("RGBA")
    if tint is not None:
        bg.alpha_composite(Image.new("RGBA", (W, H), tint))
    d = ImageDraw.Draw(bg)
    f_riv = get_font(16)
    for rname, pts in RIVERS_169.items():
        dense = eval_polyline(pts, 70)
        spts = [cam.to_screen(x, y) for x, y in dense]
        d.line(spts, fill=(46, 152, 198, 72), width=11, joint="curve")
        d.line(spts, fill=(102, 210, 238, 185), width=4, joint="curve")
        mx, my = spts[len(spts) // 2]
        if 80 < mx < W - 120 and 120 < my < 850:
            d.text((mx - 28, my - 22), rname, font=f_riv, fill=(128, 226, 248, 195))
    return bg, cam


def draw_map_badge_card(ov: Image.Image, title: str, sub: str, col=GOLD, x: int = 56, y: int = 755, w: int = 620):
    d = ImageDraw.Draw(ov)
    d.rounded_rectangle([x, y, x + w, y + 96], radius=16, fill=(10, 16, 24, 228), outline=(*col[:3], 235), width=2)
    f1, f2 = get_font(25), get_font(18)
    d.text((x + 22, y + 16), title, font=f1, fill=(*col[:3], 255))
    d.text((x + 22, y + 54), sub, font=f2, fill=(238, 240, 244, 240))


def draw_seesaw_inset(ov: Image.Image, tau: float, t: float, x0: int = 1220, y0: int = 700, w: int = 640, h: int = 152):
    d = ImageDraw.Draw(ov)
    d.rounded_rectangle([x0, y0, x0 + w, y0 + h], radius=18, fill=(10, 16, 24, 232), outline=(*GOLD, 235), width=3)
    fh = get_font(19)
    hdr = "ТЕПЕ-ТЕҢДІК АЙЛАСЫ • ҚОС ИМПЕРИЯ АРАСЫНДА"
    d.text((x0 + (w - d.textlength(hdr, font=fh)) / 2, y0 + 14), hdr, font=fh, fill=(*CYAN, 250))
    tilt = 0.08 * math.sin(t * 2.5) * math.exp(-tau * 0.25)
    bx, by = x0 + w // 2, y0 + 98
    bw = 215
    xL, yL = bx - math.cos(tilt) * bw, by - math.sin(tilt) * bw
    xR, yR = bx + math.cos(tilt) * bw, by + math.sin(tilt) * bw
    d.polygon([(bx, by + 6), (bx - 16, by + 34), (bx + 16, by + 34)], fill=(*CYAN, 240))
    d.line([(xL, yL), (xR, yR)], fill=(*GOLD, 250), width=6)
    fl = get_font(19)
    for px, py, txt, c_out, c_txt in [(xL, yL - 30, "РЕСЕЙ", RED, WHITE), (bx, by - 36, "ҚАЗАҚ ОРДАСЫ", GOLD, GOLD), (xR, yR - 30, "ЦИН", RED, WHITE)]:
        tw = d.textlength(txt, font=fl) + 22
        d.rounded_rectangle([px - tw / 2, py - 12, px + tw / 2, py + 15], radius=10, fill=(16, 24, 34, 235), outline=(*c_out, 235), width=2)
        d.text((px - d.textlength(txt, font=fl) / 2, py - 9), txt, font=fl, fill=(*c_txt, 255))


def render_map_scene(sc: dict, u: float, tau: float, seg_dur: float, t: float) -> Image.Image:
    mid = sc["map_id"]
    e = smoothstep(u)
    p = ease_out(min(1.0, u / 0.85))
    C = CITIES_169

    if mid == "ch1_ulytau":
        bg, cam = render_widescreen_map_base(1.38 + 0.08 * e, 635, 480, t, tint=(24, 38, 60, 48))
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        # Red invader push into winter trap + gold Kazakh encirclement at dawn
        draw_arrow_169(ov, cam, [C["Бұхара"], C["Сығанақ"], (640, 455)], p, t, col_main=RED, col_glow=(255, 130, 110), width=11)
        draw_arrow_169(ov, cam, [C["Сарайшық"], (460, 395), C["Ұлытау"]], p, t, col_main=GOLD, col_glow=CYAN, width=10)
        draw_arrow_169(ov, cam, [C["Көкшетау"], (730, 330), C["Ұлытау"]], p, t, col_main=GOLD, col_glow=CYAN, width=10)
        for cname in ("Сарайшық", "Көкшетау", "Ұлытау", "Сығанақ", "Бұхара"):
            draw_city_node_169(ov, cam, cname, "red" if cname == "Бұхара" else "kazakh", min(1.0, u * 1.4) if cname == "Ұлытау" else 0.0, t, emphasis=(cname == "Ұлытау"))
        draw_unit_badge_169(ov, cam, C["Ұлытау"][0], C["Ұлытау"][1], "ҚАСЫМ ХАН • ТАҢҒЫ СОҚҚЫ", t, off=(0, -52))
        draw_map_badge_card(ov, "1510 • ҰЛЫТАУ ҚАҚПАНЫ", "ЖАУДЫ ҚАР БАСҚАН АҢҒАРҒА ТҮСІРДІ", col=CYAN)
        bg.alpha_composite(ov)
        return bg.convert("RGB")

    elif mid == "ch2_south":
        bg, cam = render_widescreen_map_base(1.42 + 0.06 * e, 660, 665, t)
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        route = [C["Сығанақ"], C["Түркістан"], C["Ташкент"], C["Самарқан"], C["Бұхара"]]
        draw_arrow_169(ov, cam, route, p, t, col_main=GOLD, col_glow=CYAN, width=11)
        px, py, _ = point_along_path(eval_polyline(route, 80), min(0.95, p * 0.94))
        draw_unit_badge_169(ov, cam, px, py, "ТӘУЕКЕЛ • ЕР ЕСІМ", t, off=(0, -50))
        for idx, cname in enumerate(["Сығанақ", "Түркістан", "Ташкент", "Самарқан", "Бұхара"]):
            thr = idx * 0.19
            st = "kazakh" if u >= thr + 0.1 else ("capturing" if u >= thr else "red")
            bu = max(0.0, (u - thr) / 0.16) if st == "capturing" else 0.0
            draw_city_node_169(ov, cam, cname, st, bu, t, emphasis=(cname in {"Түркістан", "Ташкент"}))
        draw_map_badge_card(ov, "1598 • ОҢТҮСТІК ЖОРЫҚ МАРШРУТЫ", "СЫҒАНАҚ – ТҮРКІСТАН – ТАШКЕНТ – САМАРҚАН", col=GOLD, x=1220, y=755, w=640)
        bg.alpha_composite(ov)
        return bg.convert("RGB")

    elif mid == "ch3_orbulak_trap":
        bg, cam = render_widescreen_map_base(1.55 + 0.08 * e, 1270, 610, t)
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ox, oy = C["Орбұлақ"]
        # Red invader column pushing against narrow Orbulak chokepoint
        draw_arrow_169(ov, cam, [(1530, 520), (1410, 565), (ox + 35, oy - 12)], p, t, col_main=RED, col_glow=(255, 130, 110), width=13)
        # Flashing defense arc
        sx, sy = cam.to_screen(ox, oy)
        d = ImageDraw.Draw(ov)
        for rr in (48, 86):
            d.arc([sx - rr, sy - rr, sx + rr, sy + rr], 290, 90, fill=(*CYAN, 230), width=5)
        draw_city_node_169(ov, cam, "Орбұлақ", "capturing", 0.5 + 0.4 * math.sin(t * 6), t, emphasis=True)
        for cn in ("Жетісу", "Тарбағатай"):
            draw_city_node_169(ov, cam, cn, "kazakh" if cn == "Жетісу" else "red", 0.0, t)
        draw_unit_badge_169(ov, cam, ox, oy, "600 САРБАЗ • ТАР ШАТҚАЛ (15–20 м)", t, col=CYAN, off=(-20, -60))
        draw_map_badge_card(ov, "ИНЖЕНЕРЛІК ОҚПАН + БИІК МЕРГЕНДЕР", "50 000 ҚОЛ ШАТҚАЛДА БӨГЕЛДІ", col=CYAN)
        bg.alpha_composite(ov)
        return bg.convert("RGB")

    elif mid == "ch3_zhalantos":
        bg, cam = render_widescreen_map_base(1.30 + 0.05 * e, 980, 680, t)
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        flank = [C["Самарқан"], C["Ташкент"], C["Жетісу"], C["Орбұлақ"]]
        draw_arrow_169(ov, cam, flank, p, t, col_main=GOLD, col_glow=CYAN, width=12)
        px, py, _ = point_along_path(eval_polyline(flank, 90), min(0.95, p * 0.94))
        draw_unit_badge_169(ov, cam, px, py, "ЖАЛАҢТӨС БАҺАДҮР (+20 000)", t, col=GOLD, off=(0, -54))
        for cn in ("Самарқан", "Ташкент", "Жетісу", "Орбұлақ"):
            draw_city_node_169(ov, cam, cn, "kazakh", 0.0, t, emphasis=(cn in {"Самарқан", "Орбұлақ"}))
        draw_map_badge_card(ov, "ШЕШУШІ СӘТТЕГІ ТЫЛ СОҚҚЫСЫ", "САМАРҚАННАН 20 000 АТТЫ ӘСКЕР КӨМЕККЕ КЕЛДІ", col=GOLD, x=1200, y=755, w=660)
        bg.alpha_composite(ov)
        return bg.convert("RGB")

    elif mid == "ch4_law":
        bg, cam = render_widescreen_map_base(1.16 + 0.04 * e, 880, 520, t)
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        sx, sy = cam.to_screen(*C["Түркістан"])
        d = ImageDraw.Draw(ov)
        for ring_i in range(3):
            rp = ((t * 0.42 + ring_i * 0.33) % 1.0)
            rr = int(55 + rp * 480)
            al = int(210 * (1.0 - rp))
            d.ellipse([sx - rr, sy - rr, sx + rr, sy + rr], outline=(*GOLD, al), width=4)
        for src, lbl in [(C["Сарайшық"], "КІШІ ЖҮЗ • ӘЙТЕКЕ БИ"), (C["Көкшетау"], "ОРТА ЖҮЗ • ҚАЗЫБЕК БИ"), (C["Жетісу"], "ҰЛЫ ЖҮЗ • ТӨЛЕ БИ")]:
            draw_arrow_169(ov, cam, [src, C["Түркістан"]], p, t, col_main=CYAN, col_glow=GOLD, width=8)
            draw_unit_badge_169(ov, cam, (src[0] + C["Түркістан"][0]) / 2, (src[1] + C["Түркістан"][1]) / 2, lbl, t, col=CYAN, off=(0, -34))
        for cn in ("Сарайшық", "Көкшетау", "Ұлытау", "Түркістан", "Жетісу"):
            draw_city_node_169(ov, cam, cn, "kazakh", 0.0, t, emphasis=(cn == "Түркістан"))
        draw_map_badge_card(ov, "«ЖЕТІ ЖАРҒЫ» • ТҮРКІСТАН ОРТАЛЫҒЫ", "ҮШ ЖҮЗДІҢ ТӨБЕ БИЛЕРІ ОРНАТҚАН ОРТАҚ ЗАҢ", col=GOLD, x=1220, y=755, w=640)
        bg.alpha_composite(ov)
        return bg.convert("RGB")

    elif mid == "ch5_ordabasy":
        bg, cam = render_widescreen_map_base(1.24 + 0.06 * e, 810, 550, t)
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        for src in (C["Сарайшық"], C["Ұлытау"], C["Көкшетау"], C["Жетісу"]):
            draw_arrow_169(ov, cam, [src, C["Ордабасы"]], p, t, col_main=GOLD, col_glow=CYAN, width=11)
        for cn in ("Сарайшық", "Ұлытау", "Көкшетау", "Түркістан", "Ордабасы", "Жетісу"):
            draw_city_node_169(ov, cam, cn, "capturing" if cn == "Ордабасы" else "kazakh", min(1.0, u * 1.4) if cn == "Ордабасы" else 0.0, t, emphasis=(cn == "Ордабасы"))
        draw_unit_badge_169(ov, cam, C["Ордабасы"][0], C["Ордабасы"][1], "ҮШ ЖҮЗ БІРЛІГІ • АНТ ЖӘНЕ ЖЫЛУ", t, col=GOLD, off=(20, 48))
        draw_map_badge_card(ov, "1726 • ОРДАБАСЫ ҚҰРЫЛТАЙЫ", "БАТЫСТАН ОҢТҮСТІККЕ ОНДАҒАН МЫҢ ТҰЛПАР ЖӨНЕЛТІЛДІ", col=GOLD)
        bg.alpha_composite(ov)
        return bg.convert("RGB")

    elif mid == "ch5_tolgama":
        bg, cam = render_widescreen_map_base(1.48 + 0.06 * e, 1180, 610, t)
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        # Tolgama Pincer crescent trap
        draw_arrow_169(ov, cam, [C["Ордабасы"], (960, 635), C["Аңырақай"]], p, t, col_main=GOLD, col_glow=CYAN, width=10)
        draw_arrow_169(ov, cam, [(995, 535), (1120, 505), (1210, 575)], p, t, col_main=CYAN, col_glow=GOLD, width=11)
        draw_arrow_169(ov, cam, [(1020, 720), (1150, 745), (1220, 675)], p, t, col_main=CYAN, col_glow=GOLD, width=11)
        draw_city_node_169(ov, cam, "Аңырақай", "capturing", (t * 0.9) % 1.0, t, emphasis=True)
        draw_city_node_169(ov, cam, "Жетісу", "kazakh", 0.0, t)
        draw_unit_badge_169(ov, cam, 1130, 595, "ТОЛҒАМА ҚОРШАУЫ • 40 КҮН", t, col=GOLD, off=(0, -54))
        draw_map_badge_card(ov, "ӘБІЛҚАЙЫР • БӨГЕНБАЙ • ҚАБАНБАЙ", "ЖАУДЫ ИТ-ІШПЕС АЛАКӨЛ СОР ДАЛАСЫНА ҚАМАДЫ", col=CYAN)
        bg.alpha_composite(ov)
        return bg.convert("RGB")

    elif mid == "ch6_balance":
        bg, cam = render_widescreen_map_base(1.06 + 0.04 * e, 960, 530, t)
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw_arrow_169(ov, cam, [(480, 145), (670, 210), (790, 235)], p, t, col_main=RED, col_glow=(255, 130, 110), width=11)
        draw_arrow_169(ov, cam, [(1120, 145), (960, 200), (855, 235)], p, t, col_main=RED, col_glow=(255, 130, 110), width=11)
        draw_arrow_169(ov, cam, [(1850, 420), (1680, 435), (1500, 455)], p, t, col_main=RED, col_glow=(255, 130, 110), width=12)
        draw_arrow_169(ov, cam, [(1840, 640), (1640, 625), (1320, 610)], p, t, col_main=RED, col_glow=(255, 130, 110), width=12)
        for cn in ("Сарайшық", "Көкшетау", "Ұлытау", "Түркістан", "Жетісу", "Тарбағатай", "Зайсан", "Алтай"):
            draw_city_node_169(ov, cam, cn, "red" if cn in {"Зайсан", "Тарбағатай", "Алтай"} else "kazakh", 0.0, t, emphasis=(cn in {"Көкшетау", "Түркістан"}))
        draw_map_badge_card(ov, "ЕКІ АЛЫП ИМПЕРИЯ ҚЫСЫМЫ", "СОЛТҮСТІК РЕСЕЙ • ШЫҒЫС ЦИН ӘСКЕРІ", col=RED)
        draw_seesaw_inset(ov, tau, t)
        bg.alpha_composite(ov)
        return bg.convert("RGB")

    elif mid == "ch6_east":
        bg, cam = render_widescreen_map_base(1.36 + 0.06 * e, 1380, 460, t)
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        east_path = [C["Көкшетау"], C["Аңырақай"], C["Жетісу"], C["Тарбағатай"], C["Зайсан"], C["Алтай"]]
        draw_arrow_169(ov, cam, east_path, p, t, col_main=GOLD, col_glow=CYAN, width=12)
        px, py, _ = point_along_path(eval_polyline(east_path, 90), min(0.95, p * 0.94))
        draw_unit_badge_169(ov, cam, px, py, "ҚАБАНБАЙ • БӨГЕНБАЙ (×3 ҚАРҚЫН)", t, off=(0, -52))
        flipped = 0
        for idx, cn in enumerate(["Жетісу", "Тарбағатай", "Зайсан", "Алтай"]):
            thr = 0.15 + idx * 0.20
            st = "kazakh" if u >= thr + 0.1 else ("capturing" if u >= thr else "red")
            if st in {"kazakh", "capturing"}:
                flipped += 1
            draw_city_node_169(ov, cam, cn, st, max(0.0, (u - thr) / 0.15) if st == "capturing" else 0.0, t, emphasis=(cn in {"Жетісу", "Тарбағатай", "Зайсан"}))
        draw_city_node_169(ov, cam, "Көкшетау", "kazakh", 0.0, t)
        draw_map_badge_card(ov, f"ШЫҒЫС ЖАЙЛАУЛАРЫ ОРАЛДЫ: {min(3, flipped)} / 3", "ЖЕТІСУ • ТАРБАҒАТАЙ • ЗАЙСАН", col=GOLD, x=1220, y=755, w=640)
        bg.alpha_composite(ov)
        return bg.convert("RGB")

    else:
        # epilogue_border: Full Golden-Turquoise Border Shield across Kazakhstan
        bg, cam = render_widescreen_map_base(1.04, 960, 520, t)
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        border_pts = [
            C["Сарайшық"], C["Көкшетау"], C["Алтай"], C["Зайсан"],
            C["Тарбағатай"], C["Жетісу"], C["Ташкент"], C["Түркістан"], C["Сарайшық"],
        ]
        dense = eval_polyline(border_pts, 180)
        n_draw = max(3, int(len(dense) * min(1.0, u / 0.72)))
        spts = [cam.to_screen(x, y) for x, y in dense[:n_draw]]
        d = ImageDraw.Draw(ov)
        d.line(spts, fill=(*CYAN, 120), width=18, joint="curve")
        d.line(spts, fill=(*GOLD, 245), width=6, joint="curve")
        for cn in ("Сарайшық", "Ұлытау", "Көкшетау", "Түркістан", "Ташкент", "Жетісу", "Тарбағатай", "Зайсан", "Алтай"):
            draw_city_node_169(ov, cam, cn, "kazakh", 0.0, t, emphasis=(cn in {"Көкшетау", "Түркістан", "Алтай"}))
        draw_map_badge_card(ov, "ТҰТАС ҚАЗАҚ ОРДАСЫ • 4 МЫЗҒЫМАС ТІРЕК", "БІРЛІК • ӘДІЛ ЗАҢ • ЖЫЛУ • СТРАТЕГИЯЛЫҚ АҚЫЛ", col=GOLD, x=56, y=755, w=760)
        bg.alpha_composite(ov)
        return bg.convert("RGB")


# ---------------------------------------------------------------------------
# RIGID SUBPIXEL CAMERA & WIDESCREEN CINEMA / DOSSIER CARDS
# ---------------------------------------------------------------------------
@lru_cache(maxsize=32)
def load_plate(rel: str) -> Image.Image:
    return Image.open(ROOT / rel).convert("RGB")


@lru_cache(maxsize=32)
def load_ambient_wide(rel: str) -> Image.Image:
    """Precompute darkened, softly blurred 1920x1080 widescreen ambient backdrop ONCE."""
    src = load_plate(rel)
    sw, sh = src.size
    crop_h = int(sw * H / W)
    cy = int(sh * 0.45)
    y0 = max(0, min(sh - crop_h, cy - crop_h // 2))
    wide = src.crop((0, y0, sw, y0 + crop_h)).resize((W, H), Image.Resampling.BILINEAR)
    wide = wide.filter(ImageFilter.GaussianBlur(18))
    arr = (np.asarray(wide, dtype=np.float32) * 0.34).astype(np.uint8)
    return Image.fromarray(arr)


def crop_rigid_viewport(src: Image.Image, target_w: int, target_h: int, u: float, tau: float, z0: float = 1.02, z1: float = 1.12, cy_focus: float = 0.46, shake: bool = False) -> Image.Image:
    """Zero-jelly rigid camera pan/zoom fitted proportionally into target_w x target_h (no chopping!)."""
    sw, sh = src.size
    e = smoothstep(u)
    z = z0 + (z1 - z0) * e
    dx_px, dy_px = 0.0, 0.0
    if shake and tau <= 0.42:
        dec = math.exp(-7.5 * tau)
        dx_px = 9.0 * dec * math.sin(tau * 60.0)
        dy_px = 6.0 * dec * math.cos(tau * 48.0)

    # Fit viewport aspect ratio inside source width so maximum vertical body/scenery shows cleanly!
    vw = sw / z
    vh = vw * (target_h / target_w)
    if vh > sh:
        vh = sh / z
        vw = vh * (target_w / target_h)
    cx = sw * (0.49 + 0.02 * e) + dx_px
    cy = sh * (cy_focus - 0.03 * e) + dy_px
    x0 = max(0.0, min(sw - vw, cx - vw * 0.5))
    y0 = max(0.0, min(sh - vh, cy - vh * 0.5))
    return src.transform((target_w, target_h), Image.Transform.EXTENT, (x0, y0, x0 + vw, y0 + vh), Image.Resampling.BILINEAR)


def draw_dossier_panel(ov: Image.Image, sc: dict, u: float, tau: float, t: float, x0: int = 1168, y0: int = 116, w: int = 696, h: int = 758):
    d = ImageDraw.Draw(ov)
    pop = ease_out(min(1.0, tau / 0.30))
    d.rounded_rectangle([x0, y0, x0 + w, y0 + h], radius=22, fill=(10, 16, 24, int(232 * pop)), outline=(*GOLD, int(235 * pop)), width=3)

    f_tag = get_font(19)
    tag = sc.get("card_tag", "ТАКТИКАЛЫҚ ДОСЬЕ")
    tw = d.textlength(tag, font=f_tag) + 34
    d.rounded_rectangle([x0 + 28, y0 + 24, x0 + 28 + tw, y0 + 58], radius=10, fill=(18, 38, 48, 235), outline=(*CYAN, 220), width=2)
    d.text((x0 + 45, y0 + 30), tag, font=f_tag, fill=(*CYAN, 255))

    f_title = get_font(31)
    d.text((x0 + 28, y0 + 76), sc["card_title"], font=f_title, fill=(*GOLD, 255))
    d.line([(x0 + 28, y0 + 122), (x0 + w - 28, y0 + 122)], fill=(78, 224, 222, 130), width=2)

    cur_y = y0 + 146

    if "counter" in sc:
        target_num, suf, desc = sc["counter"]
        prog = ease_out(min(1.0, tau / 1.15))
        val = int(round(target_num * prog))
        txt_num = f"{val:,}{suf}".replace(",", " ")
        fn = get_font(54)
        d.text((x0 + 32, cur_y), txt_num, font=fn, fill=(*GOLD, 255))
        fd = get_font(20)
        d.text((x0 + 32, cur_y + 68), desc, font=fd, fill=(238, 244, 248, 238))
        cur_y += 126

    if sc.get("seesaw"):
        draw_seesaw_inset(ov, tau, t, x0=x0 + 24, y0=cur_y, w=w - 48, h=154)
        cur_y += 182

    if "bars" in sc:
        fb = get_font(21)
        bw = w - 64
        for idx, (lbl, frac, col) in enumerate(sc["bars"]):
            anim_f = frac * ease_out(min(1.0, max(0.0, (tau - 0.10 * idx) / 0.65)))
            d.text((x0 + 32, cur_y), lbl, font=fb, fill=(246, 244, 236, 245))
            by = cur_y + 32
            d.rounded_rectangle([x0 + 32, by, x0 + 32 + bw, by + 26], radius=9, fill=(22, 32, 44, 235), outline=(90, 120, 135, 160), width=1)
            fw = max(16, int(bw * anim_f))
            d.rounded_rectangle([x0 + 32, by, x0 + 32 + fw, by + 26], radius=9, fill=(*col, 240))
            cur_y += 78

    if "bullets" in sc:
        fk = get_font(20)
        fv = get_font(21)
        for idx, (k_txt, v_txt) in enumerate(sc["bullets"]):
            bpop = ease_out(min(1.0, max(0.0, (tau - 0.08 * idx) / 0.35)))
            if bpop <= 0.05:
                continue
            d.rounded_rectangle([x0 + 28, cur_y, x0 + w - 28, cur_y + 72], radius=12, fill=(16, 24, 34, int(218 * bpop)), outline=(78, 224, 222, int(135 * bpop)), width=1)
            d.text((x0 + 44, cur_y + 10), k_txt, font=fk, fill=(*CYAN, int(250 * bpop)))
            d.text((x0 + 44, cur_y + 38), v_txt, font=fv, fill=(*WHITE, int(248 * bpop)))
            cur_y += 84


def draw_hero_panel(ov: Image.Image, sc: dict, tau: float, x0: int = 1020, y0: int = 116, w: int = 844, h: int = 758):
    d = ImageDraw.Draw(ov)
    pop = ease_out(min(1.0, tau / 0.32))
    d.rounded_rectangle([x0, y0, x0 + w, y0 + h], radius=24, fill=(10, 16, 24, int(226 * pop)), outline=(*GOLD, int(235 * pop)), width=3)

    f_num = get_font(124)
    d.text((x0 + 42, y0 + 24), sc["hero_num"], font=f_num, fill=(*GOLD, int(245 * pop)))
    f_tit = get_font(40)
    d.text((x0 + 42, y0 + 166), sc["hero_title"], font=f_tit, fill=(*WHITE, int(252 * pop)))
    f_sub = get_font(23)
    d.text((x0 + 42, y0 + 220), sc["hero_sub"], font=f_sub, fill=(*CYAN, int(248 * pop)))
    d.line([(x0 + 42, y0 + 266), (x0 + w - 42, y0 + 266)], fill=(248, 202, 84, 150), width=2)

    cur_y = y0 + 298
    fk, fv = get_font(20), get_font(25)
    for idx, (sk, sv) in enumerate(sc["hero_stats"]):
        spop = ease_out(min(1.0, max(0.0, (tau - 0.12 * idx) / 0.35)))
        d.rounded_rectangle([x0 + 42, cur_y, x0 + w - 42, cur_y + 112], radius=16, fill=(16, 26, 38, int(228 * spop)), outline=(78, 224, 222, int(175 * spop)), width=2)
        d.text((x0 + 66, cur_y + 18), sk, font=fk, fill=(*CYAN, int(245 * spop)))
        d.text((x0 + 66, cur_y + 52), sv, font=fv, fill=(*WHITE, int(252 * spop)))
        cur_y += 134


def render_scene_frame(sc: dict, u: float, tau: float, seg_dur: float, t: float) -> Image.Image:
    mode = sc["mode"]

    if mode == "cut3":
        # Cold Open: 3 snappy cuts across first sentence!
        if u < 0.35:
            su = u / 0.35
            bg = load_ambient_wide(sc["plates"][0]).copy()
            vp = crop_rigid_viewport(load_plate(sc["plates"][0]), 1240, 758, su, tau, z0=1.02, z1=1.14, cy_focus=0.49, shake=True)
            bg.paste(vp, (340, 116))
            ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            d = ImageDraw.Draw(ov)
            d.rounded_rectangle([340, 116, 1580, 874], radius=18, outline=(*GOLD, 240), width=4)
            draw_arrow_barrage_wide(ov, t, count=36, go_right=True)
            draw_map_badge_card(ov, "ЗЕҢБІРЕКСІЗ • ТАС ҚАМАЛСЫЗ", "ДАЛА ХАЛҚЫ 260 ЖЫЛ ҚАЛАЙ ТӨТЕП БЕРДІ?", col=GOLD, x=620, y=760, w=680)
            out = bg.convert("RGBA")
            out.alpha_composite(ov)
            return out.convert("RGB")
        elif u < 0.70:
            su = (u - 0.35) / 0.35
            bg = load_ambient_wide(sc["plates"][1]).copy()
            vp = crop_rigid_viewport(load_plate(sc["plates"][1]), 1240, 758, su, max(0.0, tau - seg_dur * 0.35), z0=1.02, z1=1.14, cy_focus=0.45)
            bg.paste(vp, (340, 116))
            ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            d = ImageDraw.Draw(ov)
            d.rounded_rectangle([340, 116, 1580, 874], radius=18, outline=(*CYAN, 240), width=4)
            draw_mist_overlay(ov, t, y_dest=660)
            draw_map_badge_card(ov, "ЕУРАЗИЯНЫҢ АЛЫП ӘСКЕРЛЕРІНЕ ҚАРСЫ", "6 СТРАТЕГИЯЛЫҚ ЖЕҢІС ТАРИХЫ", col=CYAN, x=620, y=760, w=680)
            out = bg.convert("RGBA")
            out.alpha_composite(ov)
            return out.convert("RGB")
        else:
            su = (u - 0.70) / 0.30
            bg, cam = render_widescreen_map_base(1.06 + 0.08 * smoothstep(su), 960, 520, t)
            ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            p = ease_out(min(1.0, su / 0.8))
            C = CITIES_169
            draw_arrow_169(ov, cam, [C["Ұлытау"], C["Түркістан"], C["Орбұлақ"], C["Алтай"]], p, t, width=12)
            for cn in ("Сарайшық", "Ұлытау", "Көкшетау", "Түркістан", "Орбұлақ", "Аңырақай", "Алтай"):
                draw_city_node_169(ov, cam, cn, "kazakh", 0.0, t, emphasis=(cn in {"Ұлытау", "Түркістан", "Орбұлақ"}))
            draw_map_badge_card(ov, "АЛТЫ ҰЛЫ БЕЛЕС (1510–1771)", "БАТЫСТАН ШЫҒЫСҚА ДЕЙІНГІ ТАРИХ", col=GOLD)
            bg.alpha_composite(ov)
            return bg.convert("RGB")

    if mode == "map":
        return render_map_scene(sc, u, tau, seg_dur, t)

    bg = load_ambient_wide(sc["plate"]).copy()
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))

    if mode == "split":
        vp = crop_rigid_viewport(load_plate(sc["plate"]), 1080, 758, u, tau, cy_focus=0.45)
        bg.paste(vp, (56, 116))
        d = ImageDraw.Draw(ov)
        d.rounded_rectangle([56, 116, 1136, 874], radius=18, outline=(*CYAN, 215), width=3)
        draw_dossier_panel(ov, sc, u, tau, t)
    else:
        # hero / panorama mode: left 930x758 cinema frame + right 844x758 chapter hero card + ambient mist/rays
        vp = crop_rigid_viewport(load_plate(sc["plate"]), 930, 758, u, tau, cy_focus=0.44)
        bg.paste(vp, (56, 116))
        d = ImageDraw.Draw(ov)
        d.rounded_rectangle([56, 116, 986, 874], radius=18, outline=(*GOLD, 225), width=3)
        draw_mist_overlay(ov, t, y_dest=670)
        if sc["ch_idx"] in {3, 5}:
            draw_arrow_barrage_wide(ov, t, count=24, x0=56, x1=986, y0=126, y1=860)
        draw_hero_panel(ov, sc, tau)

    out = bg.convert("RGBA")
    out.alpha_composite(ov)
    return out.convert("RGB")


# ---------------------------------------------------------------------------
# HUD TOP BAR (CACHED BY SCENE + ALPHA STEP FOR HIGH RENDER SPEED)
# ---------------------------------------------------------------------------
_HUD_CACHE = {}


def get_hud_top_strip(si: int, step_a: int) -> Image.Image:
    key = (si, step_a)
    if key in _HUD_CACHE:
        return _HUD_CACHE[key]
    sc = SCENES[si]
    alpha_in = step_a / 5.0
    strip = Image.new("RGBA", (W, 108), (0, 0, 0, 0))
    d = ImageDraw.Draw(strip)

    # Left title + subtitle banner
    bx_a = int(round(220 * alpha_in))
    tx_a = int(round(252 * alpha_in))
    d.rounded_rectangle([56, 16, 1210, 96], radius=18, fill=(10, 16, 24, bx_a), outline=(*GOLD, int(230 * alpha_in)), width=2)
    f_top, f_sub = get_font(27), get_font(18)
    d.text((80, 24), sc["top"], font=f_top, fill=(*GOLD, tx_a))
    d.text((80, 62), sc["sub"], font=f_sub, fill=(*CYAN, tx_a))

    # Right 7-chapter progress bar
    px0, px1 = 1234, W - 56
    d.rounded_rectangle([px0, 22, px1, 90], radius=16, fill=(10, 16, 24, 212), outline=(*CYAN, 155), width=2)
    slot_w = (px1 - px0 - 20) // len(CHAPTER_PILLS)
    f_pil = get_font(15)
    for idx, lbl in enumerate(CHAPTER_PILLS):
        sx0 = px0 + 10 + idx * slot_w + 3
        sx1 = sx0 + slot_w - 6
        is_act = (idx == sc["ch_idx"])
        fc = (*GOLD, 242) if is_act else (20, 30, 42, 190)
        oc = (255, 242, 180, 255) if is_act else (85, 130, 145, 150)
        tc = (12, 14, 20, 255) if is_act else (218, 228, 236, 230)
        d.rounded_rectangle([sx0, 30, sx1, 82], radius=10, fill=fc, outline=oc, width=2)
        lw = d.textlength(lbl, font=f_pil)
        d.text((sx0 + (sx1 - sx0 - lw) / 2, 46), lbl, font=f_pil, fill=tc)

    if len(_HUD_CACHE) < 256:
        _HUD_CACHE[key] = strip
    return strip


# ---------------------------------------------------------------------------
# WIDESCREEN SUBTITLE CHUNKS (CACHED FOR 30+ FPS RENDER SPEED)
# ---------------------------------------------------------------------------
def build_chunks_169(words: list, T: float) -> list:
    groups, cur = [], []
    for w in words:
        txt = w["w"].replace("—", "").strip()
        if not txt:
            continue
        txt = txt.upper()
        if cur and (len(cur) == 4 or sum(len(x["txt"]) + 1 for x in cur) + len(txt) > 34):
            groups.append(cur)
            cur = []
        cur.append({"txt": txt, "t0": w["t0"], "t1": w["t1"]})
        if re.search(r"[,.!?:;…]+[»\"”]?$", txt):
            groups.append(cur)
            cur = []
    if cur:
        groups.append(cur)
    out = []
    for i, g in enumerate(groups):
        nxt = groups[i + 1][0]["t0"] if i + 1 < len(groups) else T
        end = nxt if nxt - g[-1]["t1"] < 0.55 else g[-1]["t1"] + 0.25
        out.append({"words": g, "t0": g[0]["t0"], "t1": min(end, nxt)})
    return out


_SUB_CACHE = {}


def render_sub_169(ci: int, words: list, active: int) -> Image.Image:
    key = (ci, active)
    if key in _SUB_CACHE:
        return _SUB_CACHE[key]
    txts = [w["txt"] for w in words]
    maxw = 1520
    f, sp, widths = get_font(52), 14.0, []
    for size in range(62, 42, -4):
        f = get_font(size)
        sp = f.getlength(" ")
        widths = [f.getlength(t) for t in txts]
        if sum(widths) + sp * (len(txts) - 1) <= maxw:
            break
    lines = [list(range(len(txts)))]
    if sum(widths) + sp * (len(txts) - 1) > maxw and len(txts) > 1:
        k = min(range(1, len(txts)), key=lambda idx: max(sum(widths[:idx]), sum(widths[idx:])))
        lines = [list(range(k)), list(range(k, len(txts)))]

    stroke = max(4, f.size // 12)
    asc, desc = f.getmetrics()
    lh, pad = asc + desc, 20
    lw = [sum(widths[i] for i in ln) + sp * (len(ln) - 1) for ln in lines]
    iw, ih = int(max(lw) + 2 * pad), int(lh * len(lines) + 2 * pad)
    shadow = Image.new("RGBA", (iw, ih), (0, 0, 0, 0))
    layer = Image.new("RGBA", (iw, ih), (0, 0, 0, 0))
    ds, dl = ImageDraw.Draw(shadow), ImageDraw.Draw(layer)
    for li, ln in enumerate(lines):
        x, y = (iw - lw[li]) / 2, pad + li * lh
        for i in ln:
            ds.text((x + 3, y + 5), txts[i], font=f, fill=(0, 0, 0, 210), stroke_width=stroke, stroke_fill=(0, 0, 0, 210))
            dl.text((x, y), txts[i], font=f, fill=(255, 198, 58, 255) if i == active else (255, 255, 255, 255), stroke_width=stroke, stroke_fill=(0, 0, 0, 255))
            x += widths[i] + sp
    shadow = shadow.filter(ImageFilter.GaussianBlur(7))
    shadow.alpha_composite(layer)
    if len(_SUB_CACHE) < 1024:
        _SUB_CACHE[key] = shadow
    return shadow


def check_hud_and_glyphs():
    f_top, f_sub, f_pil = get_font(27), get_font(18), get_font(15)
    max_t = max(f_top.getlength(s["top"]) for s in SCENES)
    max_s = max(f_sub.getlength(s["sub"]) for s in SCENES)
    max_p = max(f_pil.getlength(p) for p in CHAPTER_PILLS)
    print(f"[HUD 16:9 CHECK] max_top={max_t:.0f}px (lim 1110), max_sub={max_s:.0f}px (lim 1110), max_pil={max_p:.0f}px (lim 82)")
    assert max_t <= 1110, f"Top banner too wide: {max_t}"
    assert max_s <= 1110, f"Sub banner too wide: {max_s}"
    assert max_p <= 82, f"Pill label too wide: {max_p}"

    # Check bullet / hero / counter text widths
    f_b = get_font(21)
    for idx, s in enumerate(SCENES):
        if "card_title" in s:
            assert get_font(31).getlength(s["card_title"]) <= 640, f"Card title too wide at scene {idx}"
        for k, v in s.get("bullets", []):
            assert f_b.getlength(v) <= 630, f"Bullet too wide at scene {idx}: {v}"
        if "hero_title" in s:
            assert get_font(40).getlength(s["hero_title"]) <= 760, f"Hero title too wide at scene {idx}"

    f = get_font(40)
    ref = f.getmask("\ufffe")
    strs = re.findall(r'"([^"\\]*(?:\\.[^"\\]*)*)"', Path(__file__).read_text(encoding="utf-8"))
    bad = [ch for st in strs for ch in st if ord(ch) > 32 and bytes(f.getmask(ch)) == bytes(ref) and f.getmask(ch).size == ref.size]
    assert not bad, f"Missing glyphs: {set(bad)}"


# ---------------------------------------------------------------------------
# MAIN BUILD PIPELINE
# ---------------------------------------------------------------------------
def build_youtube_long(voice_only: bool = False):
    print(f"\n=== BUILDING YOUTUBE LONG 16:9 [KZ ONLY] (voice_only={voice_only}) ===", flush=True)
    check_hud_and_glyphs()
    t_start = time.time()

    voice_wav, timeline, words_all, dur = build_voice_and_timeline()
    mix_wav = run_yt_sfx(voice_wav, timeline, dur)

    ldir = BUILD / "kz"
    (ldir / "timeline.json").write_text(json.dumps(timeline, ensure_ascii=False, indent=2), encoding="utf-8")
    (ldir / "words.json").write_text(json.dumps(words_all, ensure_ascii=False, indent=2), encoding="utf-8")
    word_count = sum(len(s["text"].split()) for s in SCENES)
    print(f"  Voice + Mix ready: {dur:.2f}s ({len(SCENES)} scenes / 7 chapters, {word_count} words)", flush=True)
    if voice_only:
        return None

    build_widescreen_relief_map()
    chunks = build_chunks_169(words_all, dur)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_mp4 = OUT_DIR / OUT_FILE
    tmp_vid = ldir / "video_silent.mp4"

    cmd_enc = [
        FFMPEG, "-y",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
        "-i", "-",
        "-c:v", "libx264", "-preset", "fast", "-crf", "21",
        "-maxrate", "2500k", "-bufsize", "5000k",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        str(tmp_vid),
    ]
    proc = subprocess.Popen(cmd_enc, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    total_frames = int(round(dur * FPS))
    dissolve_frames = 5  # Crisp 0.16s chapter/scene transitions
    ci = 0
    si = 0

    for fi in range(total_frames):
        t = fi / FPS
        while si < len(SCENES) - 1 and t >= timeline[si]["t1"]:
            si += 1
        seg = timeline[si]
        seg_dur = max(0.05, seg["t1"] - seg["t0"])
        tau = max(0.0, t - seg["t0"])
        u = min(1.0, tau / seg_dur)

        frame_pil = render_scene_frame(SCENES[si], u, tau, seg_dur, t)

        if si > 0:
            frames_into = int(round(tau * FPS))
            if frames_into < dissolve_frames:
                prev_seg = timeline[si - 1]
                prev_sd = max(0.05, prev_seg["t1"] - prev_seg["t0"])
                prev_pil = render_scene_frame(SCENES[si - 1], 1.0, prev_sd, prev_sd, prev_seg["t1"])
                frame_pil = Image.blend(prev_pil, frame_pil, (frames_into + 1) / (dissolve_frames + 1))

        # Paste cached top HUD strip directly via mask
        step_a = min(5, int(round(min(1.0, tau / 0.22) * 5)))
        hud_strip = get_hud_top_strip(si, step_a)
        frame_pil.paste(hud_strip, (0, 0), hud_strip)

        # Paste cached word-by-word subtitle chunk in lower safe band (y ≈ 975)
        while ci < len(chunks) and t >= chunks[ci]["t1"] + 0.06:
            ci += 1
        if ci < len(chunks):
            ch = chunks[ci]
            if t >= ch["t0"] - 0.10 and t <= ch["t1"] + 0.10:
                ws = ch["words"]
                act = len(ws) - 1
                for wi, wd in enumerate(ws):
                    if t <= wd["t1"]:
                        act = wi
                        break
                sub_im = render_sub_169(ci, ws, act)
                sx = (W - sub_im.width) // 2
                sy = 975 - sub_im.height // 2
                frame_pil.paste(sub_im, (sx, sy), sub_im)

        proc.stdin.write(frame_pil.tobytes())
        if fi % (FPS * 15) == 0:
            print(f"  [YT 16:9 KZ] Frame {fi}/{total_frames} ({t:.1f}s/{dur:.1f}s)", flush=True)

    proc.stdin.close()
    ret = proc.wait()
    if ret != 0:
        raise RuntimeError(f"FFmpeg encode failed with code {ret}")

    subprocess.run(
        [
            FFMPEG, "-y",
            "-i", str(tmp_vid), "-i", str(mix_wav),
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart",
            str(out_mp4),
        ],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    sz_mb = out_mp4.stat().st_size / (1024 * 1024)
    print(f"  DONE [YT 16:9 KZ]: {out_mp4} ({dur:.1f}s, {sz_mb:.1f} MB) in {time.time() - t_start:.1f}s", flush=True)
    return out_mp4


if __name__ == "__main__":
    v_only = "--voice-only" in sys.argv[1:]
    build_youtube_long(voice_only=v_only)
