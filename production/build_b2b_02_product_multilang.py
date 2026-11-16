#!/usr/bin/env python3
"""B2B-02 Physical Product 3D Cutaway Builder (RU / KZ / EN):
'How 2mm of Vacuum Inside a Steel Thermos Keeps Water +95°C for 24 Hours at -35°C'

Combines Animagraffs/Zack D. Films 3D engineering cross-section visuals with EP04's
winning retention structure (bright sunlit winter hook with zero self-promo at start,
continuous physical animations, 24h data curve, 10s buyer checklist, and a native
marketplace-seller CTA + seamless loop in the closing seconds).

Outputs:
  - output/B2B_02_Product_3D_Shorts_RU.mp4
  - output/B2B_02_Product_3D_Shorts_KZ.mp4
  - output/B2B_02_Product_3D_Shorts_EN.mp4

Usage:
    /Users/market/antigravity/Video/.venv/bin/python3 production/build_b2b_02_product_multilang.py --preview
    /Users/market/antigravity/Video/.venv/bin/python3 production/build_b2b_02_product_multilang.py
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import math
import subprocess
import sys
import time
from functools import lru_cache
from pathlib import Path

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
PROD = Path(__file__).resolve().parent
if str(PROD) not in sys.path:
    sys.path.insert(0, str(PROD))

import anim_ep05 as anim
import build_b2b_01_multilang as b1
import render as rmod
import sfx as smod

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
FONT_PATH = PROD / "fonts" / "Montserrat-Black.ttf"
anim.FONT_PATH = FONT_PATH

W, H, FPS = rmod.W, rmod.H, rmod.FPS
SR = smod.SR

# Palette constants
GOLD = b1.GOLD
GOLD_BRIGHT = b1.GOLD_BRIGHT
CYAN = b1.CYAN
EMERALD = b1.EMERALD
CORAL = b1.CORAL
WHITE = b1.WHITE
MUTED = b1.MUTED
BG_CARD = b1.BG_CARD
COPPER = (224, 134, 82)
COPPER_LIGHT = (255, 184, 132)
AMBER_HOT = (255, 148, 42)
ICE_BLUE = (132, 226, 255)
STEEL_EDGE = (176, 198, 222)

VOICE_CFG = {
    "ru": {
        "voice": "en-US-BrianMultilingualNeural",
        "fallback": "en-US-AndrewMultilingualNeural",
        "rate": "+4%",
        "pitch": "-2Hz",
        "out_file": "B2B_02_Product_3D_Shorts_RU.mp4",
    },
    "kz": {
        "voice": "kk-KZ-DauletNeural",
        "fallback": "kk-KZ-AigulNeural",
        "rate": "+2%",
        "pitch": "-2Hz",
        "out_file": "B2B_02_Product_3D_Shorts_KZ.mp4",
    },
    "en": {
        "voice": "en-US-BrianMultilingualNeural",
        "fallback": "en-US-AndrewMultilingualNeural",
        "rate": "+4%",
        "pitch": "-2Hz",
        "out_file": "B2B_02_Product_3D_Shorts_EN.mp4",
    },
}

PAUSE_AFTER = [0.08, 0.10, 0.10, 0.10, 0.12, 0.10, 0.10, 0.12, 0.10, 0.04]

# ---------------------------------------------------------------------------
# Trilingual Content Table (Script, HUD, All Cutaway & Telemetry Callouts)
# ---------------------------------------------------------------------------

CONTENT = {
    "ru": {
        "script": [
            "Как два миллиметра пустоты внутри стального термоса держат кипяток целые сутки даже в тридцатипятиградусный мороз?",
            "Если заглянуть в тепловизор, дешёвая колба светится красным снаружи и быстро остывает — а качественный вакуумный корпус остаётся ледяным.",
            "Весь секрет спрятан в четырёх инженерных слоях — давайте разберём каждый из них в разрезе.",
            "Первый слой — двойная пищевая сталь триста четыре. Хром и никель в сплаве защищают стенки от ржавчины и запахов годами.",
            "Второй слой — глубокий вакуум между колбами. Когда воздух полностью откачан, молекулам просто нечем передавать тепло наружу.",
            "Но тепло всё равно уходит лучами, поэтому третий слой — тончайшее медное напыление, которое как зеркало отражает тепло обратно.",
            "И четвёртый барьер — глубокая пробка с двойными силиконовыми кольцами. Она намертво запирает выход пара через горловину.",
            "В результате вместо ледяной воды через три часа качественный термос сохраняет почти восемьдесят градусов даже через сутки.",
            "Запомните три быстрые проверки при покупке: холодная стенка с кипятком внутри, клеймо триста четыре на дне и плотная двойная резьба.",
            "Продаёте свой товар? Покажем любой продукт в таком же наглядном 3D-разрезе — пишите слово «ОБЗОР» в Дайрект, чтобы клиент сразу понял...",
        ],
        "tts_fix": [("3D-", "три-дэ "), ("3D ", "три-дэ ")],
        "pillars": ["1. ЗАГАДКА", "2. 4 СЛОЯ", "3. ТЕСТ 24Ч", "4. ПРОВЕРКА"],
        "banners": [
            ("ФИЗИКА ВЕЩЕЙ • 3D-РАЗРЕЗ", "КАК 2 ММ ПУСТОТЫ ДЕРЖАТ +95°C В МОРОЗ?", 0),
            ("ТЕСТ ТЕПЛОВИЗОРОМ FLIR", "ДЕШЁВАЯ КОЛБА  vs  ВАКУУМНЫЙ КОРПУС", 0),
            ("ВЗРЫВ-СХЕМА ТЕРМОСА", "ЧЕТЫРЕ ЗАЩИТНЫХ БАРЬЕРА КОРПУСА", 1),
            ("СЛОЙ 1 • ПИЩЕВАЯ СТАЛЬ 304", "ДВОЙНАЯ СТЕНКА 0.8 + 0.8 ММ БЕЗ РЖАВЧИНЫ", 1),
            ("СЛОЙ 2 • МОЛЕКУЛЫ ВАКУУМА", "ВОЗДУХ ОТКАЧАН — ТЕПЛО НЕ ПРОХОДИТ", 1),
            ("СЛОЙ 3 • МЕДНЫЙ ЭКРАН", "НАПЫЛЕНИЕ 0.02 ММ ОТРАЖАЕТ ИК-ЛУЧИ", 1),
            ("СЛОЙ 4 • ГЕРМЕТИЧНЫЙ КЛАПАН", "ДВА СИЛИКОНОВЫХ КОЛЬЦА ПРОТИВ ПАРА", 1),
            ("ДУЭЛЬ ОСТЫВАНИЯ 0–24 ЧАСА", "ПОЧЕМУ ВОДА НЕ ОСТЫВАЕТ СУТКИ", 2),
            ("ЧЕК-ЛИСТ ПОКУПКИ ЗА 10 СЕК", "КАК ОТЛИЧИТЬ КАЧЕСТВО НА МАРКЕТПЛЕЙСЕ", 3),
            ("3D-ВИЗУАЛ ДЛЯ ВАШЕГО ТОВАРА", "ПОКАЖЕМ ПРЕИМУЩЕСТВА ЗА 3 СЕКУНДЫ", 3),
        ],
        "s0_cold": "-35°C СНАРУЖИ",
        "s0_hot": "+95°C КИПЯТОК",
        "s0_gap": "ВАКУУМ ВСЕГО 2 ММ",
        "s0_low_t": "ПЕРЕПАД ТЕМПЕРАТУР 130°C",
        "s0_low_s": "ТОНКАЯ СТЕНКА ПРОТИВ СУРОВОГО МОРОЗА",
        "s1_bad_t": "ДЕШЁВАЯ КОЛБА",
        "s1_bad_s": "+68°C СНАРУЖИ • ГРЕЕТ УЛИЦУ",
        "s1_good_t": "ВАКУУМНЫЙ ТЕРМОС",
        "s1_good_s": "+18°C СНАРУЖИ • ТЕПЛО ЗАПЕРТО",
        "s1_low_t": "ТЕПЛОВИЗОР СРАЗУ ВЫДАЁТ ПОДДЕЛКУ",
        "s1_low_s": "ХОЛОДНЫЙ КОРПУС = НЕТ УТЕЧКИ ЭНЕРГИИ",
        "s2_layers": [
            ("1. СТАЛЬ AISI 304", "ВНЕШНЯЯ И ВНУТРЕННЯЯ КОЛБА"),
            ("2. ВАКУУМ 2 ММ", "ГЛУБОКАЯ ОТКАЧКА ВОЗДУХА"),
            ("3. МЕДЬ 0.02 ММ", "ЗЕРКАЛО ОТ ИК-ИЗЛУЧЕНИЯ"),
            ("4. ДВОЙНОЙ КЛАПАН", "2 КОЛЬЦА ПИЩЕВОГО СИЛИКОНА"),
        ],
        "s2_low_t": "4 УРОВНЯ ЗАЩИТЫ ОТ ХОЛОДА",
        "s2_low_s": "КАЖДЫЙ СЛОЙ БЛОКИРУЕТ СВОЙ ВИД ПОТЕРИ ТЕПЛА",
        "s3_top": "ПИЩЕВАЯ СТАЛЬ AISI 304 (18/8)",
        "s3_chem": "Cr 18%  •  Ni 8%  •  0.8 ММ + 0.8 ММ",
        "s3_bad": "ДЕШЁВАЯ СТАЛЬ 201 -> РЖАВЧИНА И ЗАПАХ",
        "s3_low_t": "НУЛЕВОЕ ОКИСЛЕНИЕ И ЧИСТЫЙ ВКУС",
        "s3_low_s": "ЗАЩИТНАЯ ОКСИДНАЯ ПЛЁНКА НЕ ПУСКАЕТ КОРРОЗИЮ",
        "s4_bad_t": "ОБЫЧНЫЙ ЗАЗОР: ЕСТЬ ВОЗДУХ",
        "s4_bad_s": "МОЛЕКУЛЫ ПЕРЕНОСЯТ ТЕПЛО НАРУЖУ",
        "s4_good_t": "ВАКУУМ 2 ММ: 0 МОЛЕКУЛ ВОЗДУХА",
        "s4_good_s": "-85% ТЕПЛОПРОВОДНОСТИ • ТЕПЛО ЗАПЕРТО",
        "s4_low_t": "ПУСТОТА — ЛУЧШИЙ ТЕПЛОИЗОЛЯТОР",
        "s4_low_s": "НЕТ ЧАСТИЦ — НЕТ ПЕРЕДАЧИ ТЕПЛА ОТ СТЕНКИ К СТЕНКЕ",
        "s5_hot": "ЯДРО +95°C",
        "s5_copper": "МЕДЬ 0.02 ММ",
        "s5_rays": "95% ИК-ЛУЧЕЙ ВОЗВРАЩАЕТСЯ ВНУТРЬ",
        "s5_vac": "ВАКУУМ + ХОЛОДНАЯ СТЕНКА",
        "s5_low_t": "МЕДНОЕ ТЕПЛОВОЕ ЗЕРКАЛО",
        "s5_low_s": "ВОЗВРАЩАЕТ ИНФРАКРАСНЫЕ ЛУЧИ ОБРАТНО В КИПЯТОК",
        "s6_title": "ГЕРМЕТИЧНАЯ ПРОБКА + 2 КОЛЬЦА",
        "s6_seal": "ДВОЙНОЙ СИЛИКОН",
        "s6_lock": "ПОТЕРИ ПАРА: 0%",
        "s6_low_t": "КОНВЕКЦИЯ ПОЛНОСТЬЮ ПЕРЕКРЫТА",
        "s6_low_s": "ОСНОВНОЙ ТЕПЛОУДАР ВСЕГДА ИДЁТ ЧЕРЕЗ ГОРЛОВИНУ",
        "s7_hdr": "ТЕМПЕРАТУРА ВОДЫ ЗА 24 ЧАСА",
        "s7_bad": "ОБЫЧНАЯ КОЛБА: +22°C ЗА 3ч",
        "s7_good": "ВАКУУМ + МЕДЬ: +78°C ЧЕРЕЗ 24ч",
        "s7_low_t": "ГОРЯЧИЙ ЧАЙ ДАЖЕ НА СЛЕДУЮЩИЙ ДЕНЬ",
        "s7_low_s": "РАЗНИЦА В 56°C БЛАГОДАРЯ 4 ИНЖЕНЕРНЫМ СЛОЯМ",
        "s8_checks": [
            ("01 • ХОЛОДНАЯ СТЕНКА СНАРУЖИ", "С КИПЯТКОМ ВНУТРИ КОРПУС НЕ ДОЛЖЕН ГРЕТЬСЯ"),
            ("02 • ШТАМП 304 / 18-8 НА ДНЕ", "НАСТОЯЩАЯ ПИЩЕВАЯ НЕРЖАВЕЮЩАЯ СТАЛЬ"),
            ("03 • ПЛОТНАЯ ПРОБКА С 2 КОЛЬЦАМИ", "ГЛУБОКИЙ КЛАПАН БЕЗ ЛЮФТА РЕЗЬБЫ"),
        ],
        "s8_low_t": "ТРИ ПРОВЕРКИ ЗА 10 СЕКУНД",
        "s8_low_s": "СОХРАНИ ЧТОБЫ НЕ КУПИТЬ ПОДДЕЛКУ",
        "s9_sku": "3D-ОБЗОР ТОВАРА • KASPI / WB / OZON",
        "s9_tag": "ПРОДАЁТЕ ФИЗИЧЕСКИЙ ТОВАР?",
        "s9_cta": "ПИШИТЕ «ОБЗОР» В DIRECT",
        "s9_sub": "ПОКАЖЕМ ВАШ ПРОДУКТ В РАЗРЕЗЕ • НА RU И KZ",
        "s9_low_t": "ПОКУПАТЕЛЬ ВИДИТ ЦЕННОСТЬ ЗА 3 СЕКУНДЫ",
        "s9_low_s": "ПОВТОР РАЗБОРА -> НАЧАЛО ВИДЕО",
    },
    "kz": {
        "script": [
            "Болат термостың ішіндегі екі-ақ миллиметр бос кеңістік отыз бес градус аязда қайнаған суды тәулік бойы қалай суытпай ұстайды?",
            "Тепловизормен қарасақ, арзан термос сыртынан қып-қызыл болып жылуын тез жоғалтады — ал нағыз вакуумды корпус салқын күйінде қалады.",
            "Бүкіл құпия төрт инженерлік қабатта жатыр — қазір әрқайсысын бөлшектеп көрейік.",
            "Бірінші қабат — үш жүз төртінші тағамдық болат. Құрамындағы хром мен никель қабырғаны тот пен бөгде иістен жылдар бойы қорғайды.",
            "Екінші қабат — қос қабырға арасындағы терең вакуум. Ауа толық сорылғандықтан, жылуды сыртқа таситын молекула қалмайды.",
            "Бірақ жылу сәулемен де тарайды, сондықтан үшінші қабат — айна сияқты инфрақызыл сәулені ішке қайтаратын жұқа мыс жабыны.",
            "Төртінші тосқауыл — қос силикон сақиналы терең қақпақ. Ол бу мен қызудың мойын арқылы сыртқа шығуын мүлде бұғаттайды.",
            "Нәтижесінде үш сағатта мұздап қалудың орнына, сапалы термос жиырма төрт сағаттан соң да сексен градусқа жуық қызуын сақтайды.",
            "Сатып аларда үш белгіні тексеріңіз: ішінде қайнаған су тұрса да сырты салқын болуы, түбіндегі үш жүз төрт мөрі және тығыз қос сақина.",
            "Тауар сатасыз ба? Кез келген өнімді дәл осындай 3D-бөлшектеп көрсетеміз — Дайректке «ШОЛУ» деп жазыңыз, сонда сатып алушы бірден көреді...",
        ],
        "tts_fix": [],
        "pillars": ["1. ЖҰМБАҚ", "2. 4 ҚАБАТ", "3. 24 САҒАТ", "4. ТЕКСЕРУ"],
        "banners": [
            ("ЗАТТАР ФИЗИКАСЫ • 3D-ТАЛДАУ", "2 ММ БОС КЕҢІСТІК +95°C ҚАЛАЙ САҚТАЙДЫ?", 0),
            ("FLIR ТЕПЛОВИЗОР СЫНАҒЫ", "АРЗАН КОЛБА  vs  ВАКУУМДЫ КОРПУС", 0),
            ("ТЕРМОСТЫҢ 3D ҚҰРЫЛЫМЫ", "ЖЫЛУДЫ САҚТАЙТЫН ТӨРТ ҚАБАТ", 1),
            ("1-ҚАБАТ • 304 ТАҒАМДЫҚ БОЛАТ", "ТОТ БАСПАЙТЫН 0.8 + 0.8 ММ ҚОС ҚАБЫРҒА", 1),
            ("2-ҚАБАТ • ВАКУУМ МОЛЕКУЛАСЫ", "АУА ТОЛЫҚ СОРУЛЫ — ЖЫЛУ ӨТПЕЙДІ", 1),
            ("3-ҚАБАТ • МЫС ЖЫЛУ АЙНАСЫ", "0.02 ММ ҚАБАТ ИК-СӘУЛЕНІ ҚАЙТАРАДЫ", 1),
            ("4-ҚАБАТ • БІТЕУ ҚАҚПАҚ ПЕН САҚИНА", "ҚОС СИЛИКОН БУДЫ СЫРТҚА ШЫҒАРМАЙДЫ", 1),
            ("24 САҒАТТЫҚ СЫНАҚ КЕСТЕСІ", "НЕГЕ ШАЙ ТӘУЛІК БОЙЫ СУЫМАЙДЫ", 2),
            ("10 СЕКУНДТЫҚ САТЫП АЛУ ТЕСТІ", "МАРКЕТПЛЕЙСТЕ САПАНЫ ТЕЗ АНЫҚТАУ", 3),
            ("ТАУАРЫҢЫЗҒА 3D-ШОЛУ ЖАСАУ", "АРТЫҚШЫЛЫҒЫН 3 СЕКУНДТА КӨРСЕТЕМІЗ", 3),
        ],
        "s0_cold": "-35°C АЯЗ",
        "s0_hot": "+95°C ҚАЙНАҒАН СУ",
        "s0_gap": "ВАКУУМ ТЕК 2 ММ",
        "s0_low_t": "ТЕМПЕРАТУРА АЙЫРМАСЫ 130°C",
        "s0_low_s": "ЖҰҚА ҚАБЫРҒА АЯЗҒА ҚАЛАЙ ТӨТЕП БЕРЕДІ",
        "s1_bad_t": "АРЗАН КОЛБА",
        "s1_bad_s": "+68°C СЫРТЫ • ЖЫЛУ ТАРАП ЖАТЫР",
        "s1_good_t": "ВАКУУМДЫ ТЕРМОС",
        "s1_good_s": "+18°C СЫРТЫ • ҚЫЗУ ІШТЕ САҚТАЛУДА",
        "s1_low_t": "ТЕПЛОВИЗОР ЖАСАНДЫ ӨНІМДІ БІРДЕН АШАДЫ",
        "s1_low_s": "САЛҚЫН КОРПУС = ЖЫЛУ ШЫҒЫНЫ ЖОҚ",
        "s2_layers": [
            ("1. БОЛАТ AISI 304", "СЫРТҚЫ ЖӘНЕ ІШКІ ҚАБЫРҒА"),
            ("2. ВАКУУМ 2 ММ", "АУАСЫ ТОЛЫҚ СОРЫЛҒАН ҚУЫС"),
            ("3. МЫС 0.02 ММ", "ИНФРАҚЫЗЫЛ ЖЫЛУ АЙНАСЫ"),
            ("4. ҚОС ҚАҚПАҚ", "2 ҚАБАТ ТАҒАМДЫҚ СИЛИКОН"),
        ],
        "s2_low_t": "СУЫҚТАН ҚОРҒАЙТЫН 4 ТОСҚАУЫЛ",
        "s2_low_s": "ӘР ҚАБАТ ЖЫЛУ ЖОҒАЛУДЫҢ БІР ЖОЛЫН ЖАБАДЫ",
        "s3_top": "ТАҒАМДЫҚ БОЛАТ AISI 304 (18/8)",
        "s3_chem": "Cr 18%  •  Ni 8%  •  0.8 ММ + 0.8 ММ",
        "s3_bad": "АРЗАН БОЛАТ 201 -> ТОТ ЖӘНЕ ИІС",
        "s3_low_t": "ТАЗА ДӘМ ЖӘНЕ НӨЛ ҚЫШҚЫЛДАНУ",
        "s3_low_s": "ҚОРҒАНЫС ҚАБЫҒЫ ТЕМІРДІ ТОТТАН САҚТАЙДЫ",
        "s4_bad_t": "ҚАРАПАЙЫМ ҚУЫС: АУА БАР",
        "s4_bad_s": "МОЛЕКУЛАЛАР ЖЫЛУДЫ СЫРТҚА ТАСИДЫ",
        "s4_good_t": "ВАКУУМ 2 ММ: 0 АУА МОЛЕКУЛАСЫ",
        "s4_good_s": "-85% ЖЫЛУ ЖОҒАЛУЫ • ҚЫЗУ САҚТАЛДЫ",
        "s4_low_t": "БОС КЕҢІСТІК — ЕҢ ҮЗДІК ОҚШАУЛАҒЫШ",
        "s4_low_s": "МОЛЕКУЛА ЖОҚ БОЛСА, ЖЫЛУ СЫРТҚА ӨТЕ АЛМАЙДЫ",
        "s5_hot": "ОРТАСЫ +95°C",
        "s5_copper": "МЫС 0.02 ММ",
        "s5_rays": "ИК-СӘУЛЕНІҢ 95% ІШКЕ ҚАЙТАДЫ",
        "s5_vac": "ВАКУУМ + САЛҚЫН ҚАБЫРҒА",
        "s5_low_t": "МЫС ЖЫЛУ АЙНАСЫ",
        "s5_low_s": "ИНФРАҚЫЗЫЛ СӘУЛЕНІ ҚАЙТАДАН СУҒА БАҒЫТТАЙДЫ",
        "s6_title": "ТЕРЕҢ ҚАҚПАҚ + 2 САҚИНА",
        "s6_seal": "ҚОС СИЛИКОН",
        "s6_lock": "БУ ШЫҒЫНЫ: 0%",
        "s6_low_t": "МОЙЫН АРҚЫЛЫ ШЫҒЫН ТОЛЫҚ ЖАБЫҚ",
        "s6_low_s": "НЕГІЗГІ ЖЫЛУ ЖОҒАЛУЫ ҚАҚПАҚ ТҰСЫНАН БОЛАДЫ",
        "s7_hdr": "24 САҒАТТАҒЫ СУ ТЕМПЕРАТУРАСЫ",
        "s7_bad": "АРЗАН КОЛБА: 3 САҒАТТА +22°C",
        "s7_good": "ВАКУУМ + МЫС: 24 САҒАТТА +78°C",
        "s7_low_t": "ЕРТЕҢГЕ ДЕЙІН ЫСТЫҚ ШАЙ САҚТАЛАДЫ",
        "s7_low_s": "4 ҚАБАТ АРҚАСЫНДА 56°C АРТЫҚШЫЛЫҚ",
        "s8_checks": [
            ("01 • СЫРТҚЫ ҚАБЫРҒАСЫ САЛҚЫН", "ІШІНДЕ ҚАЙНАҒАН СУ ТҰРСА ДА ҚЫЗБАУЫ ТИІС"),
            ("02 • ТҮБІНДЕ 304 / 18-8 МӨРІ БАР", "НАҒЫЗ ТАҒАМДЫҚ ТОТ БАСПАЙТЫН БОЛАТ"),
            ("03 • ҚОС САҚИНАЛЫ ТЫҒЫЗ ҚАҚПАҚ", "БОС ОЙНАМАЙТЫН ТЕРЕҢ БҰРАНДА"),
        ],
        "s8_low_t": "10 СЕКУНДТА 3 ТЕКСЕРУ",
        "s8_low_s": "ЖАСАНДЫ ТЕРМОС АЛМАУ ҮШІН САҚТАП АЛЫҢЫЗ",
        "s9_sku": "3D ТАУАР ШОЛУЫ • KASPI / МАРКЕТПЛЕЙС",
        "s9_tag": "ФИЗИКАЛЫҚ ТАУАР САТАСЫЗ БА?",
        "s9_cta": "ДАЙРЕКТКЕ «ШОЛУ» ДЕП ЖАЗЫҢЫЗ",
        "s9_sub": "ӨНІМІҢІЗДІ 3D-БӨЛШЕКТЕП КӨРСЕТЕМІЗ • KZ / RU",
        "s9_low_t": "САТЫП АЛУШЫ САПАНЫ 3 СЕКУНДТА КӨРЕДІ",
        "s9_low_s": "ҚАЙТА ҚАРАУ -> БАСЫНА ӨТУ",
    },
    "en": {
        "script": [
            "How can two millimeters of empty space inside a steel thermos keep boiling water hot for a full day at minus thirty-five degrees?",
            "Under a thermal camera, a cheap flask glows bright red outside and leaks heat fast — while a true vacuum shell stays ice-cold.",
            "The entire secret hides inside four engineered layers — let's pull each one apart in a cutaway.",
            "Layer one is double food-grade three-oh-four steel. Chromium and nickel lock out rust, corrosion, and metallic taste for years.",
            "Layer two is a deep vacuum gap. Once the air is pumped out, there are simply no gas molecules left to carry heat across.",
            "Heat still travels as infrared waves, so layer three is a microscopic copper lining that bounces radiant energy straight back in.",
            "And barrier four is a deep insulated stopper with dual silicone gaskets, sealing convective steam escape right at the neck.",
            "As a result, instead of going cold in three hours, a copper-lined vacuum flask still holds nearly eighty degrees a full day later.",
            "Remember three ten-second buyer checks: a cold outer wall with boiling water inside, a three-oh-four base stamp, and dual gaskets.",
            "Selling a physical product? We break down your SKU in full 3D cutaway — DM \"REVIEW\" right now, so buyers instantly see...",
        ],
        "tts_fix": [],
        "pillars": ["1. PARADOX", "2. 4 LAYERS", "3. 24H TEST", "4. CHECKLIST"],
        "banners": [
            ("PRODUCT PHYSICS • 3D CUTAWAY", "HOW 2 MM OF VOID HOLDS +95°C FOR 24H?", 0),
            ("FLIR THERMAL CAMERA TEST", "CHEAP FLASK  vs  TRUE VACUUM SHELL", 0),
            ("4-LAYER EXPLODED CUTAWAY", "FOUR BARRIERS BLOCKING HEAT LOSS", 1),
            ("LAYER 1 • AISI 304 STEEL", "DOUBLE 0.8 + 0.8 MM RUST-PROOF SHELL", 1),
            ("LAYER 2 • VACUUM MOLECULES", "AIR PUMPED OUT — ZERO CONDUCTION", 1),
            ("LAYER 3 • COPPER SHIELD", "0.02 MM MIRROR BOUNCES IR WAVES", 1),
            ("LAYER 4 • HERMETIC VALVE", "DUAL SILICONE GASKETS LOCK STEAM IN", 1),
            ("24-HOUR COOLING DUEL", "WHY BOILING WATER LASTS ALL DAY", 2),
            ("10-SECOND BUYER CHECKLIST", "HOW TO SPOT QUALITY BEFORE BUYING", 3),
            ("3D BREAKDOWNS FOR YOUR BRAND", "SHOW REAL VALUE IN 3 SECONDS FLAT", 3),
        ],
        "s0_cold": "-35°C OUTSIDE",
        "s0_hot": "+95°C BOILING",
        "s0_gap": "ONLY 2 MM VACUUM",
        "s0_low_t": "130°C TEMPERATURE DIFFERENTIAL",
        "s0_low_s": "A PAPER-THIN GAP AGAINST ARCTIC FREEZE",
        "s1_bad_t": "CHEAP FLASK",
        "s1_bad_s": "+68°C SHELL • HEAT ESCAPING",
        "s1_good_t": "VACUUM THERMOS",
        "s1_good_s": "+18°C SHELL • HEAT LOCKED IN",
        "s1_low_t": "THERMAL CAMERA EXPOSES FAKES",
        "s1_low_s": "ICE-COLD OUTER WALL = ZERO ENERGY LEAK",
        "s2_layers": [
            ("1. AISI 304 STEEL", "OUTER & INNER WALL SHIELD"),
            ("2. 2 MM VACUUM", "DEEP EVACUATED THERMAL GAP"),
            ("3. 0.02 MM COPPER", "INFRARED RADIATION MIRROR"),
            ("4. DUAL SEAL CAP", "TWIN FOOD-GRADE SILICONE RINGS"),
        ],
        "s2_low_t": "4 ENGINEERED THERMAL BARRIERS",
        "s2_low_s": "EACH LAYER STOPS A SPECIFIC MODE OF HEAT LOSS",
        "s3_top": "FOOD-GRADE AISI 304 (18/8) STEEL",
        "s3_chem": "Cr 18%  •  Ni 8%  •  0.8 MM + 0.8 MM",
        "s3_bad": "CHEAP STEEL 201 -> RUST & METALLIC TASTE",
        "s3_low_t": "ZERO OXIDATION & PURE TASTE",
        "s3_low_s": "PASSIVE OXIDE FILM BLOCKS CORROSION FOR YEARS",
        "s4_bad_t": "ORDINARY GAP: FILLED WITH AIR",
        "s4_bad_s": "MOLECULES CARRY HEAT STRAIGHT OUT",
        "s4_good_t": "2 MM VACUUM: 0 AIR MOLECULES",
        "s4_good_s": "-85% CONDUCTION • HEAT TRAPPED",
        "s4_low_t": "EMPTY SPACE BEATS ANY INSULATION",
        "s4_low_s": "NO GAS PARTICLES MEANS NO HEAT BRIDGE",
        "s5_hot": "+95°C CORE",
        "s5_copper": "0.02 MM COPPER",
        "s5_rays": "95% INFRARED RAYS BOUNCED BACK",
        "s5_vac": "VACUUM + COOL SHELL",
        "s5_low_t": "MICROSCOPIC COPPER IR MIRROR",
        "s5_low_s": "REFLECTS RADIANT HEAT STRAIGHT INTO THE LIQUID",
        "s6_title": "DEEP STOPPER + DUAL GASKETS",
        "s6_seal": "TWIN SILICONE",
        "s6_lock": "STEAM LEAK: 0%",
        "s6_low_t": "NECK CONVECTION SEALED SHUT",
        "s6_low_s": "MOST CHEAP FLASKS LOSE HEAT THROUGH THE CAP",
        "s7_hdr": "24-HOUR WATER TEMPERATURE CURVE",
        "s7_bad": "ORDINARY FLASK: +22°C IN 3H",
        "s7_good": "VACUUM + COPPER: +78°C AT 24H",
        "s7_low_t": "PIPING HOT EVEN THE NEXT MORNING",
        "s7_low_s": "56°C ADVANTAGE DELIVERED BY 4 THERMAL LAYERS",
        "s8_checks": [
            ("01 • COOL OUTER SHELL TEST", "OUTSIDE MUST STAY COOL WITH BOILING WATER"),
            ("02 • 304 / 18-8 BASE STAMP", "TRUE CORROSION-PROOF FOOD-GRADE ALLOY"),
            ("03 • TIGHT DUAL-GASKET CAP", "DEEP THREADS WITH ZERO WOBBLE OR LEAK"),
        ],
        "s8_low_t": "THREE 10-SECOND BUYER CHECKS",
        "s8_low_s": "SAVE THIS BEFORE BUYING YOUR NEXT FLASK",
        "s9_sku": "3D PRODUCT CUTAWAY • AMAZON / SHOPIFY",
        "s9_tag": "SELLING A PHYSICAL PRODUCT?",
        "s9_cta": "DM THE WORD \"REVIEW\" NOW",
        "s9_sub": "WE TURN YOUR SKU INTO A 3D BREAKDOWN • EN / RU / KZ",
        "s9_low_t": "CUSTOMERS SEE VALUE IN 3 SECONDS",
        "s9_low_s": "SEAMLESS REPLAY -> SCENE 01",
    },
}


# ---------------------------------------------------------------------------
# Voice Synthesis & Engineering Physical SFX Audio Mix
# ---------------------------------------------------------------------------

async def _tts_lang_async(lang: str, audio_dir: Path) -> list[tuple[Path, list[dict]]]:
    cfg = VOICE_CFG[lang]
    lines = CONTENT[lang]["script"]
    tts_fix = CONTENT[lang]["tts_fix"]
    manifest_path = audio_dir / "manifest.json"

    lines_hash = hashlib.sha256(
        json.dumps(
            {"voice": cfg["voice"], "rate": cfg["rate"], "pitch": cfg["pitch"], "lines": lines, "fix": tts_fix},
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()

    if manifest_path.exists():
        try:
            meta = json.loads(manifest_path.read_text(encoding="utf-8"))
            if meta.get("hash") == lines_hash and len(meta.get("items", [])) == len(lines):
                if all((audio_dir / f"seg_{i:02d}.mp3").exists() and (audio_dir / f"seg_{i:02d}.mp3").stat().st_size > 1500 for i in range(len(lines))):
                    return [(audio_dir / f"seg_{i:02d}.mp3", meta["items"][i]["bounds"]) for i in range(len(lines))]
        except Exception:
            pass

    voice_used = cfg["voice"]
    results: list[tuple[Path, list[dict]]] = []
    items_meta: list[dict] = []

    for voice_try in (cfg["voice"], cfg["fallback"]):
        results.clear()
        items_meta.clear()
        ok_all = True
        for i, raw_text in enumerate(lines):
            mp3_path = audio_dir / f"seg_{i:02d}.mp3"
            spoken = b1._prep_tts_text(raw_text, tts_fix)
            bounds = []
            line_ok = False
            for att in range(6):
                try:
                    if mp3_path.exists():
                        mp3_path.unlink()
                    bounds = await b1._tts_one(spoken, mp3_path, voice_try, cfg["rate"], cfg["pitch"])
                    if mp3_path.exists() and mp3_path.stat().st_size > 1500:
                        line_ok = True
                        break
                except Exception:
                    await asyncio.sleep(0.5 * (att + 1))
            if not line_ok:
                ok_all = False
                break
            results.append((mp3_path, bounds))
            items_meta.append({"bounds": bounds})
        if ok_all:
            voice_used = voice_try
            break

    if len(results) != len(lines):
        raise RuntimeError(f"[{lang}] Edge TTS failed after retries on both primary and fallback voices.")

    manifest_path.write_text(
        json.dumps({"hash": lines_hash, "voice": voice_used, "items": items_meta}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return results


def synthesize_lang(lang: str, build_dir: Path) -> tuple[np.ndarray, list[dict], list[dict], float]:
    lines = CONTENT[lang]["script"]
    raw_items = asyncio.run(_tts_lang_async(lang, build_dir))
    segments_audio: list[np.ndarray] = []
    timeline: list[dict] = []
    words_all: list[dict] = []

    cursor = 0.0
    for si, ((mp3_path, bounds), text) in enumerate(zip(raw_items, lines)):
        raw_x = b1._decode_mp3_mono(mp3_path)
        seg_x, t0_trim, t1_trim = b1._trim_silence(raw_x, head_pad=(0.03 if si == 0 else 0.04), tail_pad=(0.04 if si == len(lines) - 1 else 0.07))
        seg_x = b1._voice_fx(seg_x)
        seg_dur = len(seg_x) / SR

        words_seg = b1._align_words(text, bounds, t0_trim, t1_trim, seg_dur, cursor)
        words_all.extend(words_seg)

        timeline.append({"si": si, "t0": cursor, "t1": cursor + seg_dur, "dur": seg_dur})
        segments_audio.append(seg_x)
        cursor += seg_dur

        pause = PAUSE_AFTER[si] if si < len(PAUSE_AFTER) else 0.10
        if pause > 0:
            segments_audio.append(np.zeros(int(round(pause * SR)), dtype=np.float32))
            cursor += pause

    voice_full = np.concatenate(segments_audio).astype(np.float32)
    total_dur = len(voice_full) / SR

    (build_dir / "timeline.json").write_text(json.dumps({"dur": total_dur, "scenes": timeline}, indent=2), encoding="utf-8")
    (build_dir / "words.json").write_text(json.dumps(words_all, ensure_ascii=False, indent=2), encoding="utf-8")
    return voice_full, timeline, words_all, total_dur


def build_product_audio(lang: str, build_dir: Path, voice_mono: np.ndarray, timeline: list[dict], dur: float) -> Path:
    mix_raw = build_dir / "mix_raw.wav"
    mix_wav = build_dir / "mix_final.wav"
    rng = np.random.default_rng({"ru": 30401, "kz": 30402, "en": 30403}[lang])
    n_samples = len(voice_mono)
    amb = np.zeros((n_samples, 2), dtype=np.float32)

    # Subtle frosty studio atmosphere bed (zero instruments)
    room = smod.lp(smod.pink(rng, dur + 0.5), 260.0)
    smod.add(amb, smod.st(room[:n_samples], 0.0) * 0.14, 0.0)

    # Male a cappella vocal pad across 3 acts
    act_defs = [
        (0, 2,  [73.42, 110.0, 146.83],          "o", 3, 0.15),
        (2, 7,  [82.41, 123.47, 164.81, 246.94], "m", 3, 0.15),
        (7, 10, [98.00, 146.83, 196.00, 293.66], "a", 4, 0.17),
    ]
    for s_lo, s_hi, freqs, vowel, voices, gain in act_defs:
        a0 = timeline[s_lo]["t0"]
        a1 = timeline[s_hi - 1]["t1"]
        pad = smod.vocal_pad(rng, max(1.0, a1 - a0 + 0.5), freqs, vowel=vowel, voices=voices)
        pad_st = smod.reverb(pad, wet=0.28, seed=9400 + s_lo)
        smod.add(amb, pad_st * gain, a0)

    # Physical thermos SFX: ice wind, steam sizzle, steel chime, vacuum suction, cap gaskets
    for row in timeline:
        si, t0, sd = row["si"], row["t0"], row["dur"]
        if si == 0:
            smod.add(amb, smod.reverb(smod.impact_boom(rng, 1.0), wet=0.22, seed=951) * 0.58, 0.02)
            smod.add(amb, smod.st(smod.sizzle(rng, min(1.4, sd * 0.45)), 0.12) * 0.32, 0.18)
            smod.add(amb, smod.st(smod.wind(rng, sd, howl=0.25), -0.15) * 0.24, t0)
        elif si == 1:
            smod.add(amb, smod.st(smod.whoosh(rng, 0.45), -0.18) * 0.42, t0 + 0.05)
            smod.add(amb, smod.reverb(smod.clasp(rng), wet=0.14, seed=952) * 0.40, t0 + sd * 0.55)
        elif si == 2:
            smod.add(amb, smod.st(smod.whoosh(rng, 0.42), 0.15) * 0.40, t0 + 0.04)
            for k in range(4):
                smod.add(amb, smod.reverb(smod.clasp(rng), wet=0.12, seed=960 + k) * 0.34, t0 + sd * (0.14 + k * 0.18))
        elif si == 3:
            smod.add(amb, smod.reverb(smod.sword_draw(rng, 0.65), wet=0.22, seed=953) * 0.40, t0 + 0.06)
            smod.add(amb, smod.reverb(smod.thud(rng), wet=0.18, seed=954) * 0.38, t0 + sd * 0.45)
        elif si == 4:
            # Air suction whoosh dropping into silent vacuum contrast
            smod.add(amb, smod.st(smod.riser(rng, min(1.3, sd * 0.45)), 0.0) * 0.36, t0 + 0.05)
        elif si == 5:
            smod.add(amb, smod.st(smod.sizzle(rng, 0.75), 0.0) * 0.24, t0 + 0.15)
            smod.add(amb, smod.st(smod.whoosh(rng, 0.40), 0.18) * 0.38, t0 + sd * 0.45)
        elif si == 6:
            smod.add(amb, smod.st(smod.water(rng, min(1.8, sd * 0.5)), -0.10) * 0.26, t0 + 0.08)
            smod.add(amb, smod.reverb(smod.clasp(rng), wet=0.14, seed=955) * 0.44, t0 + sd * 0.38)
            smod.add(amb, smod.reverb(smod.clasp(rng), wet=0.14, seed=956) * 0.44, t0 + sd * 0.62)
        elif si == 7:
            smod.add(amb, smod.reverb(smod.clasp(rng), wet=0.15, seed=957) * 0.38, t0 + 0.08)
            smod.add(amb, smod.st(smod.riser(rng, min(1.5, sd * 0.5)), 0.0) * 0.34, t0 + sd * 0.42)
        elif si == 8:
            for k, frac in enumerate((0.12, 0.42, 0.72)):
                smod.add(amb, smod.reverb(smod.clasp(rng), wet=0.14, seed=970 + k) * 0.42, t0 + sd * frac)
        elif si == 9:
            smod.add(amb, smod.reverb(smod.impact_boom(rng, 1.0), wet=0.22, seed=958) * 0.46, t0 + 0.05)
            rlen = min(1.30, sd * 0.55)
            smod.add(amb, smod.st(smod.riser(rng, rlen), 0.0) * 0.38, max(t0, dur - rlen - 0.03))

    rms = smod.frame_rms(voice_mono, win=0.05)
    rms_st = np.interp(np.arange(n_samples), np.arange(len(rms)) * int(SR * 0.05), rms)
    duck = 1.0 - 0.54 * np.clip(rms_st / 0.085, 0.0, 1.0)
    amb *= duck[:, None]

    out = amb * 0.88 + smod.st(voice_mono, 0.0) * 1.00
    out = smod.softclip(out, 0.90)
    smod.write(str(mix_raw), out)
    b1.loudnorm_portable(mix_raw, mix_wav, I=-14.0, TP=-1.5, LRA=11.0)
    return mix_wav


# ---------------------------------------------------------------------------
# Procedural 3D Thermos Shading, Frost Vista Backdrop & Engineering Visuals
# ---------------------------------------------------------------------------

@lru_cache(maxsize=24)
def make_cyl_patch(w: int, h: int, kind: str) -> Image.Image:
    """Create a 3D cylindrical shaded metallic/thermal surface patch (fast cached RGB)."""
    x = np.linspace(-1.0, 1.0, max(2, w), dtype=np.float32)[None, :]
    # Asymmetric studio cylindrical lighting: specular highlight around x = -0.32
    diff = np.clip(0.55 + 0.45 * np.cos((x + 0.30) * 1.65), 0.14, 1.0)
    spec = np.exp(-((x + 0.34) ** 2) / 0.022) * 0.88 + np.exp(-((x - 0.52) ** 2) / 0.045) * 0.30
    edge_dark = 1.0 - 0.55 * (np.abs(x) ** 2.6)

    if kind == "steel":
        r = (58.0 * diff + 165.0 * spec) * edge_dark + 16.0
        g = (70.0 * diff + 178.0 * spec) * edge_dark + 22.0
        b = (88.0 * diff + 195.0 * spec) * edge_dark + 30.0
    elif kind == "copper":
        r = (185.0 * diff + 170.0 * spec) * edge_dark + 28.0
        g = (96.0 * diff + 115.0 * spec) * edge_dark + 14.0
        b = (48.0 * diff + 75.0 * spec) * edge_dark + 8.0
    elif kind == "hot":
        r = (210.0 * diff + 110.0 * spec) * edge_dark + 32.0
        g = (88.0 * diff + 115.0 * spec) * edge_dark + 12.0
        b = (18.0 * diff + 45.0 * spec) * edge_dark + 6.0
    elif kind == "flir_hot":
        # Vertical + cylindrical thermal leak map (bright orange/yellow/red outside)
        r = 215.0 * diff + 75.0 * spec
        g = 64.0 * diff + 130.0 * spec
        b = 18.0 * diff + 22.0 * spec
    elif kind == "flir_cold":
        r = 14.0 * diff + 36.0 * spec
        g = 78.0 * diff + 125.0 * spec
        b = 158.0 * diff + 100.0 * spec
    else:  # cap_dark
        r = (28.0 * diff + 75.0 * spec) * edge_dark + 12.0
        g = (36.0 * diff + 88.0 * spec) * edge_dark + 16.0
        b = (48.0 * diff + 106.0 * spec) * edge_dark + 22.0

    rgb = np.stack([np.broadcast_to(r, (h, w)), np.broadcast_to(g, (h, w)), np.broadcast_to(b, (h, w))], axis=-1)
    return Image.fromarray(rgb.clip(0, 255).astype(np.uint8)).convert("RGBA")


@lru_cache(maxsize=1)
def build_winter_hook_backdrop() -> np.ndarray:
    """EP04-inspired bright sunlit alpine winter backdrop in top/mid, fading dark below for sharp subs."""
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    ny = yy / H
    nx = xx / W

    # Crisp icy cerulean sky & sunlit clouds fading smoothly toward lower UI darkness
    sky_bright = np.clip(1.0 - ny / 0.56, 0.0, 1.0)
    sun_glow = np.exp(-(((nx - 0.50) / 0.42) ** 2 + ((ny - 0.28) / 0.22) ** 2))

    # Distant snow mountain ridge silhouette around ny = 0.44..0.58
    ridge_y = 0.46 - 0.06 * np.cos((nx - 0.22) * 8.5) - 0.04 * np.sin(nx * 14.0)
    is_mtn = ny > ridge_y
    dark_band = np.clip((ny - 0.56) / 0.14, 0.0, 1.0)

    r = (95.0 + 110.0 * sky_bright + 42.0 * sun_glow) * (1.0 - 0.88 * dark_band) + 10.0 * dark_band
    g = (145.0 + 82.0 * sky_bright + 34.0 * sun_glow) * (1.0 - 0.86 * dark_band) + 18.0 * dark_band
    b = (195.0 + 52.0 * sky_bright + 22.0 * sun_glow) * (1.0 - 0.80 * dark_band) + 32.0 * dark_band

    # Sunlit snowy mountain slopes above dark subtitle zone
    mtn_blend = is_mtn * (1.0 - dark_band)
    slope_light = 0.72 + 0.28 * np.sin(nx * 18.0 + ny * 9.0)
    r = r * (1.0 - mtn_blend * 0.55) + (195.0 * slope_light) * (mtn_blend * 0.55)
    g = g * (1.0 - mtn_blend * 0.48) + (218.0 * slope_light) * (mtn_blend * 0.48)
    b = b * (1.0 - mtn_blend * 0.40) + (240.0 * slope_light) * (mtn_blend * 0.40)

    return np.stack([r, g, b], axis=-1).clip(0, 255).astype(np.uint8)


def draw_thermos_cylinder(ov: Image.Image, cx: int, y_top: int, w: int, h: int,
                          body_kind: str = "steel", cap_lift: float = 0.0, cutaway_frac: float = 0.0,
                          t: float = 0.0, copper_trim: bool = False):
    """Draw a sleek volumetric 3D stainless thermos with optional X-ray cutaway core directly on ov."""
    x0 = cx - w // 2
    neck_h = int(h * 0.07)
    cap_h = int(h * 0.14)
    body_y = y_top + cap_h + neck_h
    body_h = h - cap_h - neck_h

    # Metallic body on ov (so it renders brightly above any panel background)
    body_patch = make_cyl_patch(w, body_h, body_kind)
    ov.paste(body_patch, (x0, body_y), body_patch)

    # Shoulder & threaded neck
    nw = int(w * 0.64)
    nx0 = cx - nw // 2
    neck_patch = make_cyl_patch(nw, neck_h + 18, "steel")
    ov.paste(neck_patch, (nx0, body_y - neck_h), neck_patch)

    # Floating / seated insulated screw cap
    cw = int(w * 0.72)
    cx0 = cx - cw // 2
    cy0 = int(y_top - cap_lift)
    cap_patch = make_cyl_patch(cw, cap_h, "cap_dark")
    ov.paste(cap_patch, (cx0, cy0), cap_patch)

    # Optional luminous X-ray cutaway showing vacuum gap, copper sheath & boiling +95°C core
    if cutaway_frac > 0.02:
        cw_in = int(w * 0.74)
        ch_full = int((body_h - 44) * min(1.0, cutaway_frac))
        ix0 = cx - cw_in // 2
        iy0 = body_y + 22
        if copper_trim:
            cp = make_cyl_patch(cw_in + 16, ch_full + 14, "copper")
            ov.paste(cp, (ix0 - 8, iy0 - 7), cp)
        core = make_cyl_patch(cw_in, max(8, ch_full), "hot")
        ov.paste(core, (ix0, iy0), core)

    d = ImageDraw.Draw(ov)
    d.rounded_rectangle([x0, body_y, x0 + w, body_y + body_h], radius=16, outline=(*STEEL_EDGE, 210), width=3)
    d.rectangle([nx0, body_y - neck_h, nx0 + nw, body_y], outline=(*STEEL_EDGE, 180), width=2)
    d.rounded_rectangle([cx0, cy0, cx0 + cw, cy0 + cap_h], radius=12, outline=(*CYAN, 200), width=2)
    if cap_lift > 10.0:
        for oy in (body_y - int(neck_h * 0.72), body_y - int(neck_h * 0.35)):
            d.rounded_rectangle([nx0 - 3, oy, nx0 + nw + 3, oy + 7], radius=3, fill=(*EMERALD, 235))

    if cutaway_frac > 0.02:
        cw_in = int(w * 0.74)
        ch_full = int((body_h - 44) * min(1.0, cutaway_frac))
        ix0 = cx - cw_in // 2
        iy0 = body_y + 22
        rng = np.random.default_rng(777)
        bxs = rng.uniform(ix0 + 18, ix0 + cw_in - 18, 12)
        bys = rng.uniform(0, max(20, ch_full), 12)
        for k in range(12):
            by = iy0 + ch_full - ((bys[k] + t * (55 + k * 5)) % max(18, ch_full - 12)) - 6
            r_b = 4 + (k % 3) * 2
            d.ellipse([bxs[k] - r_b, by - r_b, bxs[k] + r_b, by + r_b], outline=(255, 240, 175, 195), width=2)
        d.rounded_rectangle([ix0 - 10, iy0 - 8, ix0 + cw_in + 10, iy0 + ch_full + 8], radius=14, outline=(*GOLD_BRIGHT, 235), width=3)


def draw_steam_wisps(d: ImageDraw.ImageDraw, cx: float, y_base: float, t: float, col=(255, 255, 255)):
    for k in range(4):
        phase = (t * 0.75 + k * 0.25) % 1.0
        yy = y_base - phase * 68.0
        xx = cx + math.sin(phase * 6.0 + k * 1.4) * 20.0
        al = int(170 * math.sin(math.pi * phase))
        rw = 12 + phase * 20
        d.ellipse([xx - rw, yy - rw * 0.55, xx + rw, yy + rw * 0.55], fill=(*col, al))


def draw_snowflakes(ov: Image.Image, t: float, count: int = 34):
    d = ImageDraw.Draw(ov)
    rng = np.random.default_rng(2027)
    xs = rng.uniform(30, W - 30, count)
    ys = rng.uniform(40, 1080, count)
    sp = rng.uniform(45, 115, count)
    rs = rng.uniform(2.0, 5.2, count)
    for k in range(count):
        px = (xs[k] + math.sin(t * 1.5 + k) * 24.0) % W
        py = (ys[k] + t * sp[k]) % 1060
        al = int(135 + 90 * math.sin(t * 2.2 + k))
        d.ellipse([px - rs[k], py - rs[k], px + rs[k], py + rs[k]], fill=(255, 255, 255, al))


def render_scene_frame(lang: str, si: int, u: float, tau: float, seg_dur: float, t: float) -> Image.Image:
    L = CONTENT[lang]
    pop = anim.ease_out(min(1.0, tau / 0.24))
    fill_u = anim.ease_out(min(1.0, max(0.0, (tau - 0.04) / max(0.55, seg_dur * 0.72))))

    if si == 0:
        bg = Image.fromarray(build_winter_hook_backdrop()).convert("RGBA")
    else:
        bg = Image.fromarray(b1.build_studio_backdrop()).convert("RGBA")

    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)

    if si != 0:
        b1.draw_grid_ambience(ov, t, gold_tint=(si in (5, 7, 9)))

    # -----------------------------------------------------------------------
    # SCENE 0: Bright Winter Hook (-35°C Frost Outside vs +95°C Boiling X-Ray)
    # -----------------------------------------------------------------------
    if si == 0:
        draw_snowflakes(ov, t, count=36)
        cut_frac = anim.ease_out(min(1.0, max(0.25, fill_u * 1.15)))
        draw_thermos_cylinder(ov, cx=540, y_top=300, w=276, h=750, body_kind="steel",
                              cap_lift=0.0, cutaway_frac=cut_frac, t=t, copper_trim=True)
        draw_steam_wisps(d, 540, 294, t, col=(255, 255, 255))

        # Left icy badge (-35°C), Right hot core badge (+95°C) + Vacuum gap badge
        b1.draw_panel(d, 54, 435, 366, 526, pop=pop, fill_rgb=(12, 34, 58), out_rgb=ICE_BLUE, radius=16)
        f_cl, t_cl = b1.fit_font_text(d, L["s0_cold"], 285, 26, 18)
        d.text((210 - t_cl / 2, 466), L["s0_cold"], font=f_cl, fill=(*ICE_BLUE, 255))
        d.line([(366, 480), (402, 505)], fill=(*ICE_BLUE, 225), width=3)

        b1.draw_panel(d, 714, 520, 1026, 610, pop=pop, fill_rgb=(46, 22, 10), out_rgb=AMBER_HOT, radius=16)
        f_ht, t_ht = b1.fit_font_text(d, L["s0_hot"], 285, 26, 18)
        d.text((870 - t_ht / 2, 550), L["s0_hot"], font=f_ht, fill=(*GOLD_BRIGHT, 255))
        d.line([(714, 565), (620, 610)], fill=(*GOLD_BRIGHT, 235), width=3)

        b1.draw_panel(d, 704, 770, 1026, 860, pop=pop, fill_rgb=(14, 24, 38), out_rgb=GOLD, radius=16)
        f_gp, t_gp = b1.fit_font_text(d, L["s0_gap"], 292, 24, 17)
        d.text((865 - t_gp / 2, 801), L["s0_gap"], font=f_gp, fill=(*GOLD, 255))
        d.line([(704, 815), (656, 815)], fill=(*GOLD, 235), width=3)

        b1.draw_lower_card(ov, L["s0_low_t"], L["s0_low_s"], GOLD, tau, prog=fill_u)

    # -----------------------------------------------------------------------
    # SCENE 1: FLIR Thermal Camera Comparison (Cheap Red Leak vs Cold Vacuum)
    # -----------------------------------------------------------------------
    elif si == 1:
        b1.draw_panel(d, 64, 246, 1016, 1062, pop=pop, fill_rgb=(10, 14, 24), out_rgb=CYAN, radius=24)
        # Thermal camera viewfinder corners & badge
        d.text((92, 268), "FLIR IR // +15..+95°C", font=rmod.font(20), fill=(*CYAN, 220))
        d.ellipse([936, 272, 954, 290], fill=(*CORAL, int(140 + 110 * abs(math.sin(t * 5.0)))))
        d.text((882, 268), "REC", font=rmod.font(20), fill=(*CORAL, 240))

        # Left bad thermos (hot glowing exterior losing heat!)
        draw_thermos_cylinder(ov, cx=310, y_top=375, w=205, h=555, body_kind="flir_hot", cutaway_frac=0.0, t=t)
        # Escaping red thermal waves outward on both sides of bad thermos
        for wy_off in (520, 640, 760):
            drift = (t * 48.0) % 44.0
            d.line([(185 - drift, wy_off), (150 - drift, wy_off)], fill=(*CORAL, 215), width=4)
            d.line([(435 + drift, wy_off), (470 + drift, wy_off)], fill=(*CORAL, 215), width=4)

        b1.draw_panel(d, 106, 305, 514, 366, pop=pop, fill_rgb=b1.BG_RED, out_rgb=CORAL, radius=14)
        f_b1, tb1 = b1.fit_font_text(d, L["s1_bad_t"], 380, 24, 17)
        d.text((310 - tb1 / 2, 322), L["s1_bad_t"], font=f_b1, fill=(255, 155, 142, 255))
        b1.draw_panel(d, 86, 952, 534, 1024, pop=pop, fill_rgb=b1.BG_RED, out_rgb=CORAL, radius=14)
        f_b2, tb2 = b1.fit_font_text(d, L["s1_bad_s"], 420, 20, 15)
        d.text((310 - tb2 / 2, 976), L["s1_bad_s"], font=f_b2, fill=(*WHITE, 248))

        # Right good thermos (cold icy outer body keeping heat trapped inside)
        draw_thermos_cylinder(ov, cx=770, y_top=375, w=205, h=555, body_kind="flir_cold", cutaway_frac=0.68, t=t)
        b1.draw_panel(d, 566, 305, 974, 366, pop=pop, fill_rgb=(12, 36, 44), out_rgb=CYAN, radius=14)
        f_g1, tg1 = b1.fit_font_text(d, L["s1_good_t"], 380, 24, 17)
        d.text((770 - tg1 / 2, 322), L["s1_good_t"], font=f_g1, fill=(*CYAN, 255))
        b1.draw_panel(d, 546, 952, 994, 1024, pop=pop, fill_rgb=(12, 36, 44), out_rgb=EMERALD, radius=14)
        f_g2, tg2 = b1.fit_font_text(d, L["s1_good_s"], 420, 20, 15)
        d.text((770 - tg2 / 2, 976), L["s1_good_s"], font=f_g2, fill=(*EMERALD, 255))

        # Sweeping vertical thermal scan laser line
        scan_x = 100 + ((t * 280.0) % 880.0)
        d.line([(scan_x, 305), (scan_x, 945)], fill=(*GOLD_BRIGHT, 165), width=3)

        b1.draw_lower_card(ov, L["s1_low_t"], L["s1_low_s"], CYAN, tau, prog=fill_u)

    # -----------------------------------------------------------------------
    # SCENE 2: Exploded 3D 4-Layer Cutaway (Left Thermos + Right Clean Callouts)
    # -----------------------------------------------------------------------
    elif si == 2:
        lift = 54.0 * anim.ease_out(min(1.0, fill_u * 1.15))
        draw_thermos_cylinder(ov, cx=278, y_top=325, w=248, h=700, body_kind="steel",
                              cap_lift=lift, cutaway_frac=0.88, t=t, copper_trim=True)

        anchors_y = (615, 725, 830, 355)
        targets_x = (398, 378, 355, 358)
        layer_cols = (STEEL_EDGE, CYAN, COPPER_LIGHT, EMERALD)
        for idx, ((ltitle, lsub), ay, ax, col) in enumerate(zip(L["s2_layers"], anchors_y, targets_x, layer_cols)):
            lu = anim.ease_out(min(1.0, max(0.0, fill_u * 1.4 - idx * 0.14)))
            cy = 278 + idx * 195
            ch = 160
            cx0, cx1 = 500, 1014
            if lu > 0.05:
                d.line([(ax, ay), (465, ay), (cx0, cy + ch // 2)], fill=(*col, int(225 * lu)), width=3)
                d.ellipse([ax - 7, ay - 7, ax + 7, ay + 7], fill=(*col, int(255 * lu)))
                b1.draw_panel(d, cx0, cy, cx1, cy + ch, pop=lu, fill_rgb=BG_CARD, out_rgb=col, radius=18)
                ft1, _ = b1.fit_font_text(d, ltitle, 470, 27, 19)
                ft2, _ = b1.fit_font_text(d, lsub, 470, 20, 14)
                d.text((cx0 + 24, cy + 36), ltitle, font=ft1, fill=(*col, int(255 * lu)))
                d.text((cx0 + 24, cy + 92), lsub, font=ft2, fill=(*WHITE, int(238 * lu)))

        b1.draw_lower_card(ov, L["s2_low_t"], L["s2_low_s"], GOLD, tau, prog=fill_u)

    # -----------------------------------------------------------------------
    # SCENE 3: Layer 1 — AISI 304 (18/8) Atomic Shield vs Cheap Steel 201
    # -----------------------------------------------------------------------
    elif si == 3:
        b1.draw_panel(d, 68, 250, 1012, 765, pop=pop, fill_rgb=BG_CARD, out_rgb=CYAN, radius=24)
        f_st, tst = b1.fit_font_text(d, L["s3_top"], 880, 29, 20)
        d.text(((W - tst) / 2, 278), L["s3_top"], font=f_st, fill=(*CYAN, 255))

        # Macro double stainless wall slabs directly on ov above panel background
        w_steel_1 = make_cyl_patch(760, 74, "steel")
        w_steel_2 = make_cyl_patch(760, 74, "steel")
        ov.paste(w_steel_1, (160, 355), w_steel_1)
        ov.paste(w_steel_2, (160, 525), w_steel_2)
        d = ImageDraw.Draw(ov)
        d.rounded_rectangle([160, 355, 920, 429], radius=10, outline=(*STEEL_EDGE, 230), width=3)
        d.rounded_rectangle([160, 525, 920, 599], radius=10, outline=(*STEEL_EDGE, 230), width=3)

        # Glowing Cr/Ni protective lattice nodes along inner wall surface
        for kx in range(195, 900, 65):
            col_n = GOLD_BRIGHT if ((kx // 65) % 2 == 0) else CYAN
            d.ellipse([kx - 9, 553, kx + 9, 571], fill=(*col_n, 240), outline=(12, 20, 34, 255), width=2)

        f_ch, tch = b1.fit_font_text(d, L["s3_chem"], 840, 30, 20)
        d.text(((W - tch) / 2, 660), L["s3_chem"], font=f_ch, fill=(*GOLD_BRIGHT, 255))

        # Bottom contrast card: Cheap Steel 201 corrosion warning (y=792..1040)
        b1.draw_panel(d, 68, 792, 1012, 1042, pop=pop, fill_rgb=b1.BG_RED, out_rgb=CORAL, radius=22)
        b1.draw_vector_cross(d, 138, 916, 28, (*CORAL, 250))
        f_b3, _ = b1.fit_font_text(d, L["s3_bad"], 790, 28, 18)
        d.text((196, 898), L["s3_bad"], font=f_b3, fill=(255, 165, 152, 255))

        b1.draw_lower_card(ov, L["s3_low_t"], L["s3_low_s"], CYAN, tau, prog=fill_u)

    # -----------------------------------------------------------------------
    # SCENE 4: Layer 2 — Molecular Air Conduction vs Deep Vacuum Gap
    # -----------------------------------------------------------------------
    elif si == 4:
        # Top chamber: Filled with bouncing air molecules transferring heat (y=252..626)
        b1.draw_panel(d, 68, 252, 1012, 626, pop=pop, fill_rgb=b1.BG_RED, out_rgb=CORAL, radius=22)
        f_4a, t4a = b1.fit_font_text(d, L["s4_bad_t"], 860, 26, 18)
        d.text(((W - t4a) / 2, 274), L["s4_bad_t"], font=f_4a, fill=(*CORAL, 255))
        # Left hot wall (+95) and Right cold wall (-35)
        d.rounded_rectangle([104, 326, 148, 536], radius=8, fill=(*AMBER_HOT, 235))
        d.rounded_rectangle([932, 326, 976, 536], radius=8, fill=(*ICE_BLUE, 235))
        # Animated gas molecules carrying heat across
        rng = np.random.default_rng(402)
        mxs = rng.uniform(175, 905, 18)
        mys = rng.uniform(345, 515, 18)
        for k in range(18):
            mx = 175 + ((mxs[k] - 175 + t * (95 + k * 9)) % 730)
            my = mys[k] + math.sin(t * 6.0 + k) * 16.0
            d.ellipse([mx - 9, my - 9, mx + 9, my + 9], fill=(*GOLD_BRIGHT, 225))
            d.line([(mx + 10, my), (mx + 26, my)], fill=(*CORAL, 190), width=3)
        f_4b, t4b = b1.fit_font_text(d, L["s4_bad_s"], 860, 24, 16)
        d.text(((W - t4b) / 2, 566), L["s4_bad_s"], font=f_4b, fill=(*WHITE, 245))

        # Bottom chamber: Deep vacuum 2mm (0 molecules — heat blocked!) (y=654..1052)
        b1.draw_panel(d, 68, 654, 1012, 1052, pop=pop, fill_rgb=(10, 28, 36), out_rgb=EMERALD, radius=22)
        f_4c, t4c = b1.fit_font_text(d, L["s4_good_t"], 860, 26, 18)
        d.text(((W - t4c) / 2, 678), L["s4_good_t"], font=f_4c, fill=(*EMERALD, 255))
        d.rounded_rectangle([104, 732, 148, 950], radius=8, fill=(*AMBER_HOT, 235))
        d.rounded_rectangle([932, 732, 976, 950], radius=8, fill=(*ICE_BLUE, 235))
        # Blocked heat barrier glow near hot wall
        for wy in range(752, 940, 38):
            bounce_x = 166 + 40 * abs(math.sin(t * 4.0 + wy * 0.1))
            d.line([(152, wy), (bounce_x, wy)], fill=(*GOLD_BRIGHT, 230), width=4)
            d.ellipse([bounce_x - 5, wy - 5, bounce_x + 5, wy + 5], fill=(*GOLD_BRIGHT, 255))
        d.text((405, 822), "0.001 Pa  VACUUM", font=rmod.font(26), fill=(*CYAN, 170))
        f_4d, t4d = b1.fit_font_text(d, L["s4_good_s"], 860, 24, 16)
        d.text(((W - t4d) / 2, 988), L["s4_good_s"], font=f_4d, fill=(*GOLD_BRIGHT, 255))

        b1.draw_lower_card(ov, L["s4_low_t"], L["s4_low_s"], EMERALD, tau, prog=fill_u)

    # -----------------------------------------------------------------------
    # SCENE 5: Layer 3 — 0.02mm Copper Shield Reflecting Infrared Radiation
    # -----------------------------------------------------------------------
    elif si == 5:
        b1.draw_panel(d, 68, 250, 1012, 1055, pop=pop, fill_rgb=(12, 18, 30), out_rgb=COPPER_LIGHT, radius=24)

        # Left boiling zone (x=96..495) on ov so it glows brightly above panel background
        hot_bg = make_cyl_patch(390, 560, "hot")
        ov.paste(hot_bg, (96, 330), hot_bg)

        # Center 0.02mm Copper Mirror vertical ribbon (x=495..565)
        cop_bg = make_cyl_patch(70, 560, "copper")
        ov.paste(cop_bg, (495, 330), cop_bg)

        # Cool vacuum + exterior right zone (x=585..980)
        vac_bg = make_cyl_patch(395, 560, "flir_cold")
        ov.paste(vac_bg, (585, 330), vac_bg)

        d = ImageDraw.Draw(ov)
        f_5h, _ = b1.fit_font_text(d, L["s5_hot"], 360, 26, 18)
        d.text((130, 350), L["s5_hot"], font=f_5h, fill=(*WHITE, 255))
        d.rectangle([495, 330, 565, 890], outline=(*COPPER_LIGHT, 255), width=3)
        f_5v, _ = b1.fit_font_text(d, L["s5_vac"], 360, 24, 17)
        d.text((610, 350), L["s5_vac"], font=f_5v, fill=(*ICE_BLUE, 250))

        # Animated infrared chevron rays bouncing off copper mirror at x=495 back left!
        for k, ry_center in enumerate((455, 565, 675, 785)):
            phase = (t * 1.1 + k * 0.25) % 1.0
            rx_hit = 492
            d.line([(160, ry_center - 32), (rx_hit, ry_center), (160, ry_center + 32)], fill=(*GOLD_BRIGHT, 195), width=4)
            # Traveling light dot along reflection V-path
            if phase < 0.5:
                p_in = phase * 2.0
                dx_dot = 160 + (rx_hit - 160) * p_in
                dy_dot = (ry_center - 32) + 32 * p_in
            else:
                p_out = (phase - 0.5) * 2.0
                dx_dot = rx_hit - (rx_hit - 160) * p_out
                dy_dot = ry_center + 32 * p_out
            d.ellipse([dx_dot - 10, dy_dot - 10, dx_dot + 10, dy_dot + 10], fill=(*WHITE, 255))

        # Copper badge + Bottom result ribbon inside card
        b1.draw_panel(d, 382, 272, 682, 324, pop=pop, fill_rgb=(42, 22, 14), out_rgb=COPPER_LIGHT, radius=12)
        f_5c, t5c = b1.fit_font_text(d, L["s5_copper"], 275, 22, 16)
        d.text((532 - t5c / 2, 286), L["s5_copper"], font=f_5c, fill=(*COPPER_LIGHT, 255))

        b1.draw_panel(d, 108, 922, 972, 1020, pop=pop, fill_rgb=(36, 24, 14), out_rgb=GOLD, radius=16)
        f_5r, t5r = b1.fit_font_text(d, L["s5_rays"], 820, 28, 18)
        d.text(((W - t5r) / 2, 955), L["s5_rays"], font=f_5r, fill=(*GOLD_BRIGHT, 255))

        b1.draw_lower_card(ov, L["s5_low_t"], L["s5_low_s"], COPPER_LIGHT, tau, prog=fill_u)

    # -----------------------------------------------------------------------
    # SCENE 6: Layer 4 — Hermetic Stopper + Dual Silicone Rings Blocking Steam
    # -----------------------------------------------------------------------
    elif si == 6:
        b1.draw_panel(d, 68, 250, 1012, 1055, pop=pop, fill_rgb=BG_CARD, out_rgb=EMERALD, radius=24)
        f_6t, t6t = b1.fit_font_text(d, L["s6_title"], 880, 29, 20)
        d.text(((W - t6t) / 2, 278), L["s6_title"], font=f_6t, fill=(*GOLD, 255))

        # Close-up stainless neck walls & trapped warm interior pasted onto ov above panel
        n_l = make_cyl_patch(52, 400, "steel")
        n_r = make_cyl_patch(52, 400, "steel")
        ov.paste(n_l, (280, 540), n_l)
        ov.paste(n_r, (748, 540), n_r)
        seat_u = anim.ease_out(min(1.0, fill_u * 1.35))
        cap_y = int(350 + 135 * seat_u)
        hot_chamber = make_cyl_patch(400, max(40, 915 - (cap_y + 195)), "hot")
        ov.paste(hot_chamber, (340, cap_y + 195), hot_chamber)
        stopper = make_cyl_patch(390, 200, "cap_dark")
        ov.paste(stopper, (345, cap_y), stopper)
        d = ImageDraw.Draw(ov)
        d.rounded_rectangle([345, cap_y, 735, cap_y + 200], radius=18, outline=(*CYAN, 235), width=3)

        # Dual glowing emerald silicone O-ring gaskets on both sides of stopper!
        for oy_off in (110, 158):
            d.rounded_rectangle([332, cap_y + oy_off, 748, cap_y + oy_off + 20], radius=10, fill=(*EMERALD, 250))

        # Rising hot steam molecules trapped BELOW stopper bouncing back downward
        for k in range(5):
            phase = (t * 1.3 + k * 0.2) % 1.0
            sx_p = 385 + k * 78
            top_lim = cap_y + 216
            sy_p = 880 - abs(math.sin(phase * math.pi)) * max(40, 880 - top_lim)
            d.ellipse([sx_p - 10, sy_p - 10, sx_p + 10, sy_p + 10], fill=(*AMBER_HOT, 220))
            d.line([(sx_p, sy_p + 12), (sx_p, sy_p + 34)], fill=(*GOLD_BRIGHT, 180), width=3)

        # Clear seal & 0% loss pills
        b1.draw_panel(d, 748, 555, 988, 635, pop=pop, fill_rgb=(14, 38, 34), out_rgb=EMERALD, radius=14)
        f_6s, t6s = b1.fit_font_text(d, L["s6_seal"], 215, 22, 16)
        d.text((868 - t6s / 2, 582), L["s6_seal"], font=f_6s, fill=(*EMERALD, 255))

        b1.draw_panel(d, 220, 935, 860, 1020, pop=pop, fill_rgb=(16, 42, 34), out_rgb=GOLD, radius=16)
        f_6k, t6k = b1.fit_font_text(d, L["s6_lock"], 580, 32, 20)
        d.text(((W - t6k) / 2, 960), L["s6_lock"], font=f_6k, fill=(*GOLD_BRIGHT, 255))

        b1.draw_lower_card(ov, L["s6_low_t"], L["s6_low_s"], EMERALD, tau, prog=fill_u)

    # -----------------------------------------------------------------------
    # SCENE 7: 24-Hour Cooling Curve Duel (+22°C vs +78°C)
    # -----------------------------------------------------------------------
    elif si == 7:
        px0, py0, px1, py1 = 68, 252, 1012, 1052
        b1.draw_panel(d, px0, py0, px1, py1, pop=pop, fill_rgb=BG_CARD, out_rgb=GOLD, radius=24)
        f_7h, t7h = b1.fit_font_text(d, L["s7_hdr"], 880, 29, 20)
        d.text(((W - t7h) / 2, py0 + 28), L["s7_hdr"], font=f_7h, fill=(*GOLD, 255))

        gx0, gy0, gx1, gy1 = px0 + 102, py0 + 108, px1 - 48, py1 - 154
        gw, gh = gx1 - gx0, gy1 - gy0
        for temp in (0, 25, 50, 75, 100):
            yy = gy1 - gh * (temp / 100.0)
            d.line([(gx0, yy), (gx1, yy)], fill=(70, 92, 118, 95), width=2)
            d.text((px0 + 18, yy - 13), f"{temp}°C", font=rmod.font(20), fill=(*MUTED, 215))
        d.line([(gx0, gy0), (gx0, gy1), (gx1, gy1)], fill=(150, 175, 205, 195), width=3)

        h_unit = "h" if lang == "en" else "ч"
        if lang == "kz":
            h_unit = " сағ"
        for ux, hr in ((0.0, 0), (0.33, 8), (0.66, 16), (1.0, 24)):
            xx_t = gx0 + gw * ux
            hlbl = f"{hr}{h_unit}"
            hw = d.textlength(hlbl, font=rmod.font(18))
            d.text((max(gx0, min(gx1 - hw, xx_t - hw / 2)), gy1 + 10), hlbl, font=rmod.font(18), fill=(*MUTED, 215))

        n_samp = 48
        max_i = max(2, int(n_samp * fill_u))
        # Cheap flask drops to +22°C early
        bad_pts = [(gx0 + gw * (k / n_samp), gy1 - gh * (0.22 + 0.73 * math.exp(-(k / n_samp) * 8.0))) for k in range(n_samp + 1)]
        # Vacuum + copper flask smoothly holds +78°C at 24h!
        good_pts = [(gx0 + gw * (k / n_samp), gy1 - gh * (0.95 - 0.17 * ((k / n_samp) ** 0.85))) for k in range(n_samp + 1)]
        d.line(bad_pts[:max_i], fill=(*CORAL, 240), width=7, joint="curve")
        d.line(good_pts[:max_i], fill=(*EMERALD, 250), width=9, joint="curve")

        # Glowing dot at the tip of the winning curve
        tx, ty = good_pts[min(n_samp, max_i - 1)]
        d.ellipse([tx - 12, ty - 12, tx + 12, ty + 12], fill=(*GOLD_BRIGHT, 255), outline=(12, 20, 34, 255), width=3)

        ly = py1 - 102
        b1.draw_panel(d, px0 + 36, ly, px0 + 450, ly + 68, pop=pop, fill_rgb=b1.BG_RED, out_rgb=CORAL, radius=14)
        f_l1, tl1 = b1.fit_font_text(d, L["s7_bad"], 390, 22, 16)
        d.text((px0 + 36 + (414 - tl1) / 2, ly + 21), L["s7_bad"], font=f_l1, fill=(255, 152, 140, 255))

        b1.draw_panel(d, px1 - 450, ly, px1 - 36, ly + 68, pop=pop, fill_rgb=(14, 38, 34), out_rgb=EMERALD, radius=14)
        f_l2, tl2 = b1.fit_font_text(d, L["s7_good"], 390, 22, 16)
        d.text((px1 - 450 + (414 - tl2) / 2, ly + 21), L["s7_good"], font=f_l2, fill=(*EMERALD, 255))

        b1.draw_lower_card(ov, L["s7_low_t"], L["s7_low_s"], GOLD, tau, prog=fill_u)

    # -----------------------------------------------------------------------
    # SCENE 8: 3 Ten-Second Buyer Checklist Cards
    # -----------------------------------------------------------------------
    elif si == 8:
        cols_8 = (CYAN, GOLD, EMERALD)
        for idx, ((t8, s8), ccol) in enumerate(zip(L["s8_checks"], cols_8)):
            cu = anim.ease_out(min(1.0, max(0.0, fill_u * 1.4 - idx * 0.16)))
            ry = 276 + idx * 258
            rh = 220
            b1.draw_panel(d, 74, ry, 1006, ry + rh, pop=cu, fill_rgb=BG_CARD, out_rgb=ccol, radius=22)
            b1.draw_vector_check(d, 154, ry + rh // 2, 36, (*ccol, int(252 * cu)))
            f_8t, _ = b1.fit_font_text(d, t8, 760, 31, 20)
            f_8s, _ = b1.fit_font_text(d, s8, 760, 23, 16)
            d.text((218, ry + 56), t8, font=f_8t, fill=(*ccol, int(255 * cu)))
            d.text((218, ry + 122), s8, font=f_8s, fill=(*WHITE, int(242 * cu)))

        b1.draw_lower_card(ov, L["s8_low_t"], L["s8_low_s"], EMERALD, tau, prog=fill_u)

    # -----------------------------------------------------------------------
    # SCENE 9: Marketplace Seller Showcase + Native Offer + Seamless Loop
    # -----------------------------------------------------------------------
    else:
        # Marketplace showcase window (y=252..680) displaying mini 3D thermos cutaway
        b1.draw_panel(d, 72, 252, 1008, 678, pop=pop, fill_rgb=(12, 22, 36), out_rgb=CYAN, radius=24)
        f_sku, tsku = b1.fit_font_text(d, L["s9_sku"], 880, 27, 19)
        d.text(((W - tsku) / 2, 276), L["s9_sku"], font=f_sku, fill=(*CYAN, 255))
        draw_thermos_cylinder(ov, cx=260, y_top=332, w=125, h=320, body_kind="steel",
                              cap_lift=14.0, cutaway_frac=0.82, t=t, copper_trim=True)
        d = ImageDraw.Draw(ov)
        # Highlight checkmark bullets on right side of product card
        for idx, (lbl_p, _) in enumerate(L["s2_layers"][:3]):
            yy_p = 365 + idx * 88
            b1.draw_vector_check(d, 465, yy_p + 18, 18, (*GOLD_BRIGHT, 245))
            fp, _ = b1.fit_font_text(d, lbl_p, 480, 26, 18)
            d.text((502, yy_p + 2), lbl_p, font=fp, fill=(*WHITE, 248))

        # Massive native B2B CTA Card (y=708..1055)
        pulse_p = int(5 * math.sin(t * 5.2))
        cx0, cy0, cx1, cy1 = 68 - pulse_p, 708, 1012 + pulse_p, 1055
        b1.draw_panel(d, cx0, cy0, cx1, cy1, pop=pop, fill_rgb=(24, 22, 12), out_rgb=GOLD_BRIGHT, radius=24, width=4)
        f_tg, ttg = b1.fit_font_text(d, L["s9_tag"], 860, 28, 19)
        d.text(((W - ttg) / 2, cy0 + 34), L["s9_tag"], font=f_tg, fill=(*CYAN, 255))

        b1.draw_panel(d, cx0 + 42, cy0 + 96, cx1 - 42, cy0 + 232, pop=pop, fill_rgb=GOLD, out_rgb=WHITE, radius=18)
        f_ct, tct = b1.fit_font_text(d, L["s9_cta"], (cx1 - cx0) - 120, 40, 22)
        d.text(((W - tct) / 2, cy0 + 138), L["s9_cta"], font=f_ct, fill=(14, 18, 26, 255))

        f_sb, tsb = b1.fit_font_text(d, L["s9_sub"], (cx1 - cx0) - 80, 23, 15)
        d.text(((W - tsb) / 2, cy0 + 274), L["s9_sub"], font=f_sb, fill=(*WHITE, 248))

        b1.draw_lower_card(ov, L["s9_low_t"], L["s9_low_s"], GOLD_BRIGHT, tau, prog=fill_u)

    if si != 0:
        b1.draw_particles_studio(ov, t, seed=400 + si, count=16)

    bg.alpha_composite(ov)
    return bg.convert("RGB")


def draw_hud(frame_pil: Image.Image, lang: str, si: int, tau: float):
    L = CONTENT[lang]
    top_title, sub_callout, active_pillar = L["banners"][si]
    pillars = L["pillars"]

    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)

    alpha_in = min(1.0, max(0.0, tau / 0.20))
    bx_a = int(round(224 * alpha_in))
    tx_a = int(round(252 * alpha_in))

    f_top, tw = b1.fit_font_text(d, top_title, W - 140, 30, 20)
    f_sub, cw = b1.fit_font_text(d, sub_callout, W - 140, 24, 17)
    f_pil = rmod.font(24)

    d.rounded_rectangle([54, 68, W - 54, 138], radius=20, fill=(10, 16, 28, bx_a), outline=(*GOLD, int(235 * alpha_in)), width=2)
    d.text(((W - tw) / 2, 85), top_title, font=f_top, fill=(*GOLD, tx_a))

    pw = min(W - 84, int(cw + 54))
    px0 = (W - pw) // 2
    d.rounded_rectangle([px0, 150, px0 + pw, 206], radius=15, fill=(12, 28, 38, int(218 * alpha_in)), outline=(*CYAN, int(215 * alpha_in)), width=2)
    d.text(((W - cw) / 2, 164), sub_callout, font=f_sub, fill=(*WHITE, tx_a))

    bar_y0, bar_y1 = 1628, 1700
    d.rounded_rectangle([42, bar_y0, W - 42, bar_y1], radius=18, fill=(10, 16, 26, 222), outline=(145, 168, 184, 110), width=2)
    slot_w = (W - 104) / len(pillars)
    for k, label in enumerate(pillars):
        sx0 = int(52 + k * slot_w)
        sx1 = int(sx0 + slot_w - 8)
        is_active = (k == active_pillar)
        fill_p = (*GOLD, 240) if is_active else (22, 32, 48, 182)
        text_p = (14, 18, 26, 255) if is_active else (208, 218, 228, 215)
        d.rounded_rectangle([sx0, bar_y0 + 10, sx1, bar_y1 - 10], radius=12, fill=fill_p)
        lw = d.textlength(label, font=f_pil)
        d.text((sx0 + (sx1 - sx0 - lw) / 2, bar_y0 + 22), label, font=f_pil, fill=text_p)

    frame_pil.alpha_composite(overlay)


def compose_single_frame(lang: str, si: int, u: float, tau: float, sd: float, t: float,
                         vig: np.ndarray, sub_words: list[str] | None = None) -> Image.Image:
    frame_rgb = render_scene_frame(lang, si, u, tau, sd, t)
    arr = np.asarray(frame_rgb, dtype=np.uint16)
    arr_v = ((arr * vig) >> 8).astype(np.uint8)
    frame_rgba = Image.fromarray(arr_v).convert("RGBA")
    draw_hud(frame_rgba, lang, si, tau)
    if sub_words:
        words_obj = [{"txt": w, "t0": 0.0, "t1": 1.0} for w in sub_words]
        ov = rmod.render_chunk(words_obj, min(1, len(words_obj) - 1))
        frame_rgba.paste(ov, (int(W / 2 - ov.width / 2), int(rmod.SUB_Y - ov.height / 2)), ov)
    return frame_rgba


def preview_qa_frames(langs: list[str]):
    qa_dir = PROD / "build_b2b02" / "qa"
    qa_dir.mkdir(parents=True, exist_ok=True)
    vig = rmod.vignette()[..., None]
    cases = [
        ("ru", 0, 0.72, 2.8, 4.5, 2.8, ["держат", "кипяток", "целые", "сутки"]),
        ("ru", 1, 0.76, 3.4, 5.0, 7.6, ["светится", "красным", "снаружи"]),
        ("ru", 2, 0.80, 3.6, 5.2, 12.8, ["в", "четырёх", "инженерных", "слоях"]),
        ("ru", 3, 0.78, 3.6, 5.2, 18.0, ["двойная", "пищевая", "сталь"]),
        ("ru", 4, 0.78, 3.6, 5.2, 23.2, ["молекулам", "просто", "нечем"]),
        ("ru", 5, 0.78, 3.6, 5.2, 28.4, ["тончайшее", "медное", "напыление"]),
        ("ru", 6, 0.80, 3.6, 5.2, 33.6, ["двойными", "силиконовыми", "кольцами"]),
        ("ru", 7, 0.82, 3.8, 5.2, 39.0, ["восемьдесят", "градусов", "через"]),
        ("ru", 8, 0.82, 3.8, 5.2, 44.2, ["три", "быстрые", "проверки"]),
        ("ru", 9, 0.78, 3.4, 4.8, 49.0, ["слово", "«ОБЗОР»", "в", "Дайрект"]),
        ("kz", 0, 0.72, 2.8, 4.5, 2.8, ["қайнаған", "суды", "тәулік", "бойы"]),
        ("kz", 2, 0.80, 3.6, 5.2, 12.8, ["төрт", "инженерлік", "қабатта"]),
        ("en", 5, 0.78, 3.6, 5.2, 28.4, ["microscopic", "copper", "lining"]),
        ("en", 9, 0.78, 3.4, 4.8, 49.0, ["DM", "\"REVIEW\"", "right", "now"]),
    ]
    for lang, si, u, tau, sd, t, words in cases:
        if lang not in langs:
            continue
        im = compose_single_frame(lang, si, u, tau, sd, t, vig, sub_words=words)
        out_p = qa_dir / f"pre_{lang}_s{si:02d}.jpg"
        im.convert("RGB").save(out_p, "JPEG", quality=92)
        print(f"[B2B-02-PREVIEW] saved {out_p}")


def render_lang_video(lang: str, build_dir: Path, mix_wav: Path, timeline: list[dict], words_all: list[dict], dur: float, out_mp4: Path):
    vig = rmod.vignette()[..., None]
    chunks = rmod.chunks_from(words_all, dur)
    chunk_idx = 0
    chunk_cache: dict[tuple[int, int], Image.Image] = {}
    total_frames = int(round(dur * FPS))
    video_silent = build_dir / "video_silent.mp4"

    cmd = [
        FFMPEG, "-y",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-maxrate", "5.8M", "-bufsize", "11.6M",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(video_silent),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    if proc.stdin is None:
        raise RuntimeError("Failed to open ffmpeg stdin pipe")

    scene_idx = 0
    prev_scene_idx = 0
    n_scenes = len(timeline)
    prev_frame_rgb: np.ndarray | None = None
    cut_from_rgb: np.ndarray | None = None

    try:
        for fi in range(total_frames):
            t = fi / FPS
            while scene_idx < n_scenes - 1 and t >= timeline[scene_idx]["t1"] + (PAUSE_AFTER[scene_idx] if scene_idx < len(PAUSE_AFTER) else 0.0):
                scene_idx += 1
            if scene_idx != prev_scene_idx:
                cut_from_rgb = prev_frame_rgb
                prev_scene_idx = scene_idx

            sc = timeline[scene_idx]
            sd = max(0.1, sc["dur"])
            tau = max(0.0, t - sc["t0"])
            u = min(1.0, tau / sd)

            frame_rgb = render_scene_frame(lang, scene_idx, u, tau, sd, t)
            arr = np.asarray(frame_rgb, dtype=np.float32)
            if scene_idx > 0 and tau < 0.14 and cut_from_rgb is not None:
                alpha = tau / 0.14
                arr = cut_from_rgb * (1.0 - alpha) + arr * alpha
            prev_frame_rgb = arr

            arr_v = ((arr.clip(0, 255).astype(np.uint16) * vig) >> 8).astype(np.uint8)
            frame_rgba = Image.fromarray(arr_v).convert("RGBA")
            draw_hud(frame_rgba, lang, scene_idx, tau)

            while chunk_idx < len(chunks) - 1 and t >= chunks[chunk_idx + 1]["t0"]:
                chunk_idx += 1
            if chunk_idx < len(chunks):
                ch = chunks[chunk_idx]
                if ch["t0"] <= t < ch["t1"]:
                    act = max(i for i, w in enumerate(ch["words"]) if w["t0"] <= t or i == 0)
                    ck = (chunk_idx, act)
                    sub_img = chunk_cache.get(ck)
                    if sub_img is None:
                        sub_img = rmod.render_chunk(ch["words"], act)
                        if len(chunk_cache) > 64:
                            chunk_cache.clear()
                        chunk_cache[ck] = sub_img
                    ov = sub_img
                    pop_s = t - ch["t0"]
                    if pop_s < 0.08:
                        sc_pop = 0.88 + 0.12 * (1.0 - (1.0 - pop_s / 0.08) ** 2)
                        ov = ov.resize((max(1, int(ov.width * sc_pop)), max(1, int(ov.height * sc_pop))), Image.Resampling.BILINEAR)
                    frame_rgba.paste(ov, (int(W / 2 - ov.width / 2), int(rmod.SUB_Y - ov.height / 2)), ov)

            proc.stdin.write(frame_rgba.convert("RGB").tobytes())
            if (fi + 1) % 300 == 0 or fi + 1 == total_frames:
                print(f"[B2B-02:{lang.upper()}] rendered {fi + 1}/{total_frames} frames ({t:.1f}s/{dur:.1f}s)", flush=True)

        proc.stdin.close()
        stderr_out = proc.stderr.read().decode("utf-8", errors="replace") if proc.stderr else ""
        ret = proc.wait()
        if ret != 0:
            raise RuntimeError(f"FFmpeg encode failed ({ret}): {stderr_out[-1000:]}")
    finally:
        if proc.poll() is None:
            proc.kill()

    subprocess.run(
        [
            FFMPEG, "-y",
            "-i", str(video_silent),
            "-i", str(mix_wav),
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
            "-shortest", "-movflags", "+faststart", str(out_mp4),
        ],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


def main():
    args = sys.argv[1:]
    langs = ["ru", "kz", "en"]
    if "--lang" in args:
        idx = args.index("--lang")
        langs = [a for a in args[idx + 1:] if not a.startswith("--") and a in VOICE_CFG]
        if not langs:
            raise ValueError("No valid languages passed after --lang")

    if "--preview" in args:
        preview_qa_frames(langs)
        return

    out_dir = ROOT / "output"
    out_dir.mkdir(parents=True, exist_ok=True)

    for lang in langs:
        t_start = time.time()
        build_dir = PROD / "build_b2b02" / lang
        build_dir.mkdir(parents=True, exist_ok=True)
        out_mp4 = out_dir / VOICE_CFG[lang]["out_file"]

        print(f"[B2B-02:{lang.upper()}] Synthesizing narration...")
        voice_mono, timeline, words_all, dur = synthesize_lang(lang, build_dir)
        print(f"[B2B-02:{lang.upper()}] Narration ready: {len(timeline)} scenes, {dur:.2f}s, {len(words_all)} words.")

        print(f"[B2B-02:{lang.upper()}] Mixing physical product SFX + a cappella (-14 LUFS)...")
        mix_wav = build_product_audio(lang, build_dir, voice_mono, timeline, dur)

        print(f"[B2B-02:{lang.upper()}] Rendering 1080x1920 @ 30fps -> {out_mp4.name} ...")
        render_lang_video(lang, build_dir, mix_wav, timeline, words_all, dur, out_mp4)
        mb = out_mp4.stat().st_size / (1024 * 1024)
        print(f"[B2B-02:{lang.upper()}] DONE in {time.time() - t_start:.1f}s: {out_mp4} ({mb:.2f} MB, {dur:.2f}s)")


if __name__ == "__main__":
    main()
