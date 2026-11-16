#!/usr/bin/env python3
"""B2B Client-Magnet Showcase Builder (RU / KZ / EN):
'Why 90% of Business Videos Get Swiped in 2s — and How 3D Motion Wins Clients'

Generates 3 separate vertical 1080x1920 @ 30fps turnkey portfolio Reels/Shorts/TikTok:
  - output/B2B_01_Client_Magnet_Shorts_RU.mp4
  - output/B2B_01_Client_Magnet_Shorts_KZ.mp4
  - output/B2B_01_Client_Magnet_Shorts_EN.mp4

Strict guarantees:
  - 100% custom procedural 3D maps, UI/data motion & isometric blueprints (0 close-up faces)
  - 100% Halal physical SFX + male a cappella vocal pad (0 musical instruments)
  - Strict zero-overlap screen zones:
      * Top HUD: y=64..206
      * Stage (diagrams / 3D maps / CTA): y=245..1090
      * Subtitle corridor (uncluttered): y=1130..1365 (SUB_Y=1250)
      * Lower telemetry card: y=1412..1555
      * Bottom 4-pillar bar: y=1628..1700
  - Portable paths derived from Path(__file__).resolve().parent.parent

Usage:
    /Users/market/antigravity/Video/.venv/bin/python3 production/build_b2b_01_multilang.py --preview
    /Users/market/antigravity/Video/.venv/bin/python3 production/build_b2b_01_multilang.py
    /Users/market/antigravity/Video/.venv/bin/python3 production/build_b2b_01_multilang.py --lang ru kz
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import time
import wave
from functools import lru_cache
from pathlib import Path

import edge_tts
import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import sobel
from scipy.signal import butter, filtfilt

ROOT = Path(__file__).resolve().parent.parent
PROD = Path(__file__).resolve().parent
if str(PROD) not in sys.path:
    sys.path.insert(0, str(PROD))

import anim_ep05 as anim
import render as rmod
import sfx as smod

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
FONT_PATH = PROD / "fonts" / "Montserrat-Black.ttf"
anim.FONT_PATH = FONT_PATH

W, H, FPS = rmod.W, rmod.H, rmod.FPS  # 1080, 1920, 30
SR = smod.SR                          # 48000

_ffmpeg_dir = str(Path(FFMPEG).parent)
if _ffmpeg_dir not in os.environ.get("PATH", ""):
    os.environ["PATH"] = _ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")

# Palette constants
GOLD = (248, 202, 84)
GOLD_BRIGHT = (255, 224, 126)
CYAN = (72, 224, 218)
EMERALD = (64, 216, 140)
CORAL = (238, 86, 76)
WHITE = (244, 247, 252)
MUTED = (165, 178, 196)
BG_CARD = (12, 20, 34)
BG_RED = (34, 15, 19)

VOICE_CFG = {
    "ru": {
        "voice": "ru-RU-DmitryNeural",
        "fallback": "en-US-BrianMultilingualNeural",
        "rate": "+4%",
        "pitch": "-3Hz",
        "out_file": "B2B_01_Client_Magnet_Shorts_RU.mp4",
    },
    "kz": {
        "voice": "kk-KZ-DauletNeural",
        "fallback": "kk-KZ-AigulNeural",
        "rate": "+2%",
        "pitch": "-2Hz",
        "out_file": "B2B_01_Client_Magnet_Shorts_KZ.mp4",
    },
    "en": {
        "voice": "en-US-BrianMultilingualNeural",
        "fallback": "en-US-AndrewMultilingualNeural",
        "rate": "+4%",
        "pitch": "-2Hz",
        "out_file": "B2B_01_Client_Magnet_Shorts_EN.mp4",
    },
}

PAUSE_AFTER = [0.10, 0.12, 0.10, 0.12, 0.10, 0.12, 0.10, 0.12, 0.12, 0.04]

# ---------------------------------------------------------------------------
# Full Localization Table (Voice Script, HUD, All On-Screen Card Labels)
# ---------------------------------------------------------------------------

CONTENT = {
    "ru": {
        "script": [
            "Почему девяносто процентов бизнес-видео в ленте пролистывают уже на второй секунде?",
            "Обычные фото и скучные говорящие головы не держат внимание — клиент уходит к конкуренту, а реклама сливает бюджет.",
            "Посмотрите, как продаёт 3D-продакшн. Для застройщика мы превращаем сухой прайс в живую карту района с маршрутами и инфраструктурой.",
            "Покупатель за пять секунд видит школы, парки, рост стоимости метра и понятные условия рассрочки прямо на экране.",
            "Для товарного бизнеса, маркетплейсов и авто мы делаем динамичный 3D-разбор: главные плюсы, детали и выгода считываются мгновенно.",
            "Зритель досматривает ролик до конца, кликабельность растёт в разы, а стоимость каждой заявки в рекламе заметно падает.",
            "А для экспертов, сервисов и личных брендов такая инфографика в стиле деловых медиа формирует железный авторитет и поток тёплых заявок.",
            "И главное: один готовый видеопроект легко адаптируется сразу на казахский, русский и английский — для Казахстана, СНГ и мировых рынков.",
            "Мы берём всё под ключ: сценарий, 3D-карты, графики, диктора и мощный звук — строго чисто, без лишнего шума, в формате девять на шестнадцать.",
            "Хотите такие же продающие ролики для своего бизнеса? Напишите слово «ВИДЕО» в Дайрект прямо сейчас, иначе вы сами увидите...",
        ],
        "tts_fix": [("3D-", "три-дэ "), ("3D ", "три-дэ ")],
        "pillars": ["1. ПРОБЛЕМА", "2. КЕЙСЫ 3D", "3. ВЫГОДА", "4. ЗАКАЗАТЬ"],
        "banners": [
            ("АУДИТ РЕКЛАМНЫХ РОЛИКОВ", "ПОЧЕМУ СЛИВАЕТСЯ БЮДЖЕТ ЗА 2 СЕКУНДЫ?", 0),
            ("ДИНАМИКА ВНИМАНИЯ 0–30с", "КАК УДЕРЖАТЬ КЛИЕНТА ДО ОФФЕРА", 0),
            ("НИША 1 • НЕДВИЖИМОСТЬ И ЖК", "ЖИВАЯ 3D-КАРТА ЛОКАЦИИ И МАРШРУТОВ", 1),
            ("НИША 1 • ТЕЛЕМЕТРИЯ ОБЪЕКТА", "ШКОЛЫ • РОСТ ЦЕНЫ • РАССРОЧКА 0%", 1),
            ("НИША 2 • KASPI, ТОВАРКА И АВТО", "3D-РАЗБОР ПРОДУКТА ЗА СЕКУНДЫ", 1),
            ("ЭКОНОМИКА РЕКЛАМНОГО ТРАФИКА", "ОТ СТАТИЧНОГО ПОСТА К 3D-ПРОДАКШНУ", 2),
            ("НИША 3 • ЭКСПЕРТЫ, IT И B2B", "ИНФОГРАФИКА В СТИЛЕ ДЕЛОВЫХ МЕДИА", 2),
            ("МУЛЬТИЯЗЫЧНЫЙ ЗАПУСК", "ОДИН ПРОЕКТ — ТРИ ДЕНЕЖНЫХ РЫНКА", 2),
            ("ПРОДАКШН ПОД КЛЮЧ", "ОТ СЦЕНАРИЯ ДО МОНТАЖА 9:16", 3),
            ("ГОТОВЫ К ПОТОКУ ЗАЯВОК?", "НАПИШИТЕ «ВИДЕО» В DIRECT", 3),
        ],
        "s0_before_tag": "ДО • ОБЫЧНЫЙ ПОСТ",
        "s0_before_title": "СВАЙП УЖЕ НА 1.8 СЕКУНДЕ",
        "s0_before_badge": "CTR 0.6%  •  ДЕНЬГИ В МИНУС",
        "s0_mid": "3D РЕДИЗАЙН",
        "s0_after_tag": "ПОСЛЕ • 3D МОУШН-ПРОДАКШН",
        "s0_after_title": "ВИЗУАЛ УДЕРЖИВАЕТ ДО КОНЦА",
        "s0_after_badge": "74% ДОСМОТР  •  ЗАЯВКИ x4.2",
        "s0_low_t": "90% СВАЙП ЗА 2с   vs   74% ДОСМОТР",
        "s0_low_s": "ПЕРВЫЕ 3 СЕКУНДЫ РЕШАЮТ СУДЬБУ РЕКЛАМНОГО БЮДЖЕТА",
        "s1_hdr": "КРИВАЯ УДЕРЖАНИЯ ЗРИТЕЛЯ (0–30с)",
        "s1_bad": "ОБЫЧНЫЙ ПОСТ: 11%",
        "s1_good": "3D МОУШН: 74%",
        "s1_nodes": ["0с ХУК", "3с 3D-КАРТА", "8с ЦИФРЫ", "15с ОФФЕР"],
        "s1_low_t": "РАБОЧИЕ ТРИГГЕРЫ УДЕРЖАНИЯ",
        "s1_low_s": "СМЕНА КАДРА И ГРАФИКА КАЖДЫЕ 2.5–4 СЕКУНДЫ",
        "s2_nodes": {
            "pin": "ЖК PREMIUM", "park": "ПАРК", "school": "ШКОЛА",
            "center": "ЦЕНТР", "highway": "МАГИСТРАЛЬ",
        },
        "s2_rings": ("5 МИН", "10 МИН"),
        "s2_low_t": "АДАПТАЦИЯ ПОД ЛЮБОЙ ЖК И ЛОКАЦИЮ",
        "s2_low_s": "МАРШРУТЫ, ИНФРАСТРУКТУРА И РАДИУС ДОСТУПНОСТИ",
        "s3_floor": "32 ЭТ • 118 М",
        "s3_growth": "+38% РОСТ ЦЕНЫ",
        "s3_pill1": "РАССРОЧКА 0% • 24 МЕС",
        "s3_pill2": "КОНВЕРСИЯ +290%",
        "s3_low_t": "КЛИЕНТ ВИДИТ ВЫГОДУ ЗА 5 СЕКУНД",
        "s3_low_s": "ПЛАНИРОВКА, РОСТ АКТИВА И ЧЕСТНАЯ РАССРОЧКА 0%",
        "s4_title": "3D-ЧЕРТЁЖ ПРОДУКТА / АВТО",
        "s4_quads": [
            "1. 3D-ОБЗОР ДЕТАЛЕЙ",
            "2. ВЫГОДА В ЦИФРАХ",
            "3. ОТСТРОЙКА ОТ КОНКУРЕНТОВ",
            "4. МОМЕНТАЛЬНЫЙ ОФФЕР",
        ],
        "s4_low_t": "KASPI • МАРКЕТПЛЕЙСЫ • АВТО",
        "s4_low_s": "НАГЛЯДНЫЙ РАЗБОР ПРЕИМУЩЕСТВ ВМЕСТО СКУЧНОГО ФОТО",
        "s5_bad_t": "СТАТИЧНОЕ ФОТО",
        "s5_bad_m": "CTR: 0.6%",
        "s5_bad_b": "ДОРОГАЯ ЗАЯВКА  •  БЫСТРЫЙ СВАЙП",
        "s5_good_t": "ДИНАМИЧНЫЙ 3D-РОЛИК",
        "s5_good_m": "CTR: 3.8%  (x6.3)",
        "s5_good_b": "ЗАЯВКА В 3.4х ДЕШЕВЛЕ",
        "s5_low_t": "ВЫШЕ КЛИКАБЕЛЬНОСТЬ — ДЕШЕВЛЕ ЛИД",
        "s5_low_s": "РЕКЛАМНЫЙ АЛГОРИТМ ПРОДВИГАЕТ ВИДЕО С ДОСМОТРОМ",
        "s6_funnel": [
            "1. ОСТРЫЙ ХУК (0–3с)",
            "2. 3D-ИНФОГРАФИКА И КАРТЫ",
            "3. ЭКСПЕРТНОЕ ДОВЕРИЕ (74%)",
            "4. ТЁПЛЫЕ ЗАЯВКИ В DIRECT",
        ],
        "s6_roi": "ВОРОНКА ДОВЕРИЯ • ROI x4.2",
        "s6_low_t": "ЭКСПЕРТЫ • IT / SAAS • БИЗНЕС-РАЗБОРЫ",
        "s6_low_s": "ПОДАЧА В СТИЛЕ VOX ФОРМИРУЕТ АВТОРИТЕТ БРЕНДА",
        "s7_core": "1 ВИДЕОПРОЕКТ  =  3 РЫНКА",
        "s7_cols": [
            ("KZ", "КАЗАХСТАН", "ЛОКАЛЬНЫЙ БИЗНЕС", "НИЗКАЯ КОНКУРЕНЦИЯ"),
            ("RU", "СНГ И БИЗНЕС", "ЖК • ТОВАРКА • IT", "КРУПНЫЕ ЧЕКИ"),
            ("EN", "ДУБАЙ • США", "ГЛОБАЛЬНЫЙ B2B", "$100–$300+ / РОЛИК"),
        ],
        "s7_bot": "ТРОЙНОЙ ОХВАТ ПЛАТЁЖЕСПОСОБНЫХ КЛИЕНТОВ",
        "s7_low_t": "КАЗАХСКИЙ + РУССКИЙ + АНГЛИЙСКИЙ",
        "s7_low_s": "ОТДЕЛЬНЫЕ ЯЗЫКОВЫЕ ВЕРСИИ ПОД КАЖДЫЙ АККАУНТ",
        "s8_checks": [
            ("01 • ПРОДАЮЩИЙ СЦЕНАРИЙ", "ЦЕПКИЙ ХУК 0–3с, СТРУКТУРА И ЯСНЫЙ ОФФЕР"),
            ("02 • 3D-КАРТЫ И ИНФОГРАФИКА", "АНИМАЦИЯ МАРШРУТОВ, ЦИФР И КАРТОЧЕК"),
            ("03 • ОЗВУЧКА И САУНД-ДИЗАЙН", "СТУДИЙНЫЙ ДИКТОР И МОЩНЫЙ SFX БЕЗ МУЗЫКИ"),
            ("04 • ФОРМАТ 9:16 ПОД КЛЮЧ", "ГОТОВО ДЛЯ REELS, YOUTUBE SHORTS И TIKTOK"),
        ],
        "s8_low_t": "ПОЛНЫЙ ПРОДАКШН ПОД КЛЮЧ",
        "s8_low_s": "ЧИСТЫЙ ДЕЛОВОЙ СТАНДАРТ  •  100% ХАЛЯЛЬ-ФОРМАТ",
        "s9_tag": "ЗАКАЗАТЬ ПРОДАЮЩИЙ 3D-РОЛИК",
        "s9_cta": "НАПИШИТЕ «ВИДЕО» В DIRECT",
        "s9_sub": "РАЗБЕРЁМ ПРОДУКТ • ПОКАЖЕМ ПРИМЕРЫ • РАССЧИТАЕМ ЦЕНУ",
        "s9_bot": "ДОСТУПНО СРАЗУ НА RU  •  KZ  •  EN",
        "s9_low_t": "НАЧНИТЕ ПОЛУЧАТЬ ЗАЯВКИ ИЗ REELS",
        "s9_low_s": "ПИШИТЕ «ВИДЕО» В ДИРЕКТ — БЕСШОВНЫЙ ПОВТОР ->",
    },
    "kz": {
        "script": [
            "Неліктен бизнес видеолардың тоқсан пайызы екінші секундта-ақ өткізіліп кетеді?",
            "Жай суреттер мен бірсарынды роликтер назарды ұстамайды — клиент бәсекелеске кетіп, жарнама бюджеті босқа жанып кетеді.",
            "Ал 3D-продакшн қалай сататынын қараңыз. Құрылыс компаниясы үшін құрғақ прайсты бағыттары бар тірі аудан картасына айналдырамыз.",
            "Сатып алушы бес секундта мектепті, саябақты, шаршы метр бағасының өсуін және бөліп төлеу шарттарын экраннан анық көреді.",
            "Тауар бизнесі, маркетплейстер мен авто үшін серпінді 3D-талдау жасаймыз: басты артықшылық пен пайда бір сәтте көрінеді.",
            "Көрермен роликті соңына дейін көреді, жарнамаға басу жиілігі еселеп өсіп, әрбір өтінімнің құны айтарлықтай арзандайды.",
            "Ал сарапшылар, IT-сервистер мен жеке брендтер үшін іскерлік медиа стиліндегі инфографика зор сенім мен жылы өтінімдер әкеледі.",
            "Ең бастысы: бір дайын жоба бірден қазақ, орыс және ағылшын тілдеріне бейімделіп, Қазақстан мен әлем нарығын қамтиды.",
            "Барлығын толық дайындаймыз: сценарий, 3D-карталар, графиктер, диктор және таза дыбыс — артық шусыз, тоғызға он алты форматында.",
            "Бизнесіңізге дәл осындай сататын роликтер керек пе? Дәл қазір Дайректке «ВИДЕО» деп жазыңыз, әйтпесе өзіңіз көресіз...",
        ],
        "tts_fix": [],
        "pillars": ["1. МӘСЕЛЕ", "2. 3D КЕЙС", "3. ПАЙДА", "4. ТАПСЫРЫС"],
        "banners": [
            ("ЖАРНАМА РОЛИКТЕРІНІҢ АУДИТІ", "НЕГЕ БЮДЖЕТ 2 СЕКУНДТА ЖАНЫП КЕТЕДІ?", 0),
            ("КӨРЕРМЕНДІ ҰСТАУ 0–30с", "КЛИЕНТТІ ҰСЫНЫСҚА ДЕЙІН ҰСТАУ ТӘСІЛІ", 0),
            ("1-БАҒЫТ • ТҰРҒЫН ҮЙ КЕШЕНІ", "АУДАН МЕН БАҒЫТТАРДЫҢ 3D-КАРТАСЫ", 1),
            ("1-БАҒЫТ • НЫСАН ТЕЛЕМЕТРИЯСЫ", "МЕКТЕП • БАҒА ӨСІМІ • БӨЛІП ТӨЛЕУ 0%", 1),
            ("2-БАҒЫТ • KASPI, ТАУАР ЖӘНЕ АВТО", "ӨНІМДІ СЕКУНД ІШІНДЕ 3D-ТАЛДАУ", 1),
            ("ТАРГЕТ ЖАРНАМА ЭКОНОМИКАСЫ", "ҚҰРҒАҚ ФОТОДАН 3D-ПРОДАКШНҒА ӨТУ", 2),
            ("3-БАҒЫТ • САРАПШЫ, IT ЖӘНЕ B2B", "ІСКЕРЛІК МЕДИА СТИЛІНДЕГІ ГРАФИКА", 2),
            ("ҮШ ТІЛДІ МАСШТАБТАУ", "БІР ЖОБА — ҮШ ТӨЛЕМ ҚАБІЛЕТТІ НАРЫҚ", 2),
            ("ТОЛЫҚ ҚЫЗМЕТ КЕШЕНІ", "СЦЕНАРИЙДЕН 9:16 ДАЙЫН РОЛИККЕ ДЕЙІН", 3),
            ("ТАПСЫРЫС ПЕН КЛИЕНТ КЕРЕК ПЕ?", "ДАЙРЕКТКЕ «ВИДЕО» ДЕП ЖАЗЫҢЫЗ", 3),
        ],
        "s0_before_tag": "ДЕЙІН • ҚАРАПАЙЫМ ПОСТ",
        "s0_before_title": "1.8 СЕКУНДТА ӨТКІЗІП ЖІБЕРЕДІ",
        "s0_before_badge": "CTR 0.6%  •  БЮДЖЕТ ШЫҒЫНДА",
        "s0_mid": "3D ЖАҢАРТУ",
        "s0_after_tag": "КЕЙІН • 3D МОУШН-ПРОДАКШН",
        "s0_after_title": "КӨРЕРМЕНДІ СОҢЫНА ДЕЙІН ҰСТАЙДЫ",
        "s0_after_badge": "74% ҚАРАЛЫМ  •  ӨТІНІМ x4.2",
        "s0_low_t": "90% 2с ӨТКІЗУ   vs   74% ТОЛЫҚ КӨРУ",
        "s0_low_s": "АЛҒАШҚЫ 3 СЕКУНД ЖАРНАМА ТАҒДЫРЫН ШЕШЕДІ",
        "s1_hdr": "КӨРЕРМЕНДІ ҰСТАУ ҚИСЫҒЫ (0–30с)",
        "s1_bad": "ҚҰРҒАҚ ФОТО: 11%",
        "s1_good": "3D МОУШН: 74%",
        "s1_nodes": ["0с ХУК", "3с 3D-КАРТА", "8с САНДАР", "15с ОФФЕР"],
        "s1_low_t": "НАЗАРДЫ ҰСТАЙТЫН ТРИГГЕРЛЕР",
        "s1_low_s": "ӘР 2.5–4 СЕКУНД САЙЫН ЖАҢА КАДР МЕН ГРАФИКА",
        "s2_nodes": {
            "pin": "ТК PREMIUM", "park": "САЯБАҚ", "school": "МЕКТЕП",
            "center": "ОРТАЛЫҚ", "highway": "ДАҢҒЫЛ",
        },
        "s2_rings": ("5 МИН", "10 МИН"),
        "s2_low_t": "КЕЗ КЕЛГЕН ТК ЖӘНЕ АУДАНҒА",
        "s2_low_s": "МАРШРУТТАР, ИНФРАҚҰРЫЛЫМ ЖӘНЕ ҚАШЫҚТЫҚ РАДИУСЫ",
        "s3_floor": "32 ҚАБАТ • 118 М",
        "s3_growth": "+38% БАҒА ӨСІМІ",
        "s3_pill1": "БӨЛІП ТӨЛЕУ 0% • 24 АЙ",
        "s3_pill2": "КОНВЕРСИЯ +290%",
        "s3_low_t": "КЛИЕНТ ПАЙДАНЫ 5 СЕКУНДТА КӨРЕДІ",
        "s3_low_s": "ЖОСПАРЛАУ, МҮЛІК ӨСІМІ ЖӘНЕ 0% БӨЛІП ТӨЛЕУ",
        "s4_title": "ӨНІМ МЕН АВТОНЫҢ 3D-СЫЗБАСЫ",
        "s4_quads": [
            "1. БӨЛШЕКТЕРГЕ 3D-ШОЛУ",
            "2. НАҚТЫ САНМЕН ПАЙДА",
            "3. БӘСЕКЕЛЕСТЕН АЙЫРМА",
            "4. ЖЫЛДАМ САТУ ОФФЕРІ",
        ],
        "s4_low_t": "KASPI • МАРКЕТПЛЕЙСТЕР • АВТО",
        "s4_low_s": "ҚҰРҒАҚ ФОТО ОРНЫНА АРТЫҚШЫЛЫҚТЫ АНЫҚ КӨРСЕТУ",
        "s5_bad_t": "СТАТИКАЛЫҚ ФОТО",
        "s5_bad_m": "CTR: 0.6%",
        "s5_bad_b": "ҚЫМБАТ ӨТІНІМ  •  ЖЫЛДАМ ӨТКІЗУ",
        "s5_good_t": "СЕРПІНДІ 3D-РОЛИК",
        "s5_good_m": "CTR: 3.8%  (x6.3)",
        "s5_good_b": "ӨТІНІМ 3.4 ЕСЕ АРЗАН",
        "s5_low_t": "КӨП БАСУ — АРЗАН ӨТІНІМ",
        "s5_low_s": "АЛГОРИТМ СОҢЫНА ДЕЙІН КӨРІЛГЕН ВИДЕОНЫ КӨТЕРЕДІ",
        "s6_funnel": [
            "1. ӨТКІР ХУК (0–3с)",
            "2. 3D-ИНФОГРАФИКА ЖӘНЕ КАРТА",
            "3. САРАПШЫҒА СЕНІМ (74%)",
            "4. DIRECT-КЕ ЖЫЛЫ ӨТІНІМ",
        ],
        "s6_roi": "СЕНІМ ВОРОНКАСЫ • ROI x4.2",
        "s6_low_t": "САРАПШЫ • IT / SAAS • БИЗНЕС-ТАЛДАУ",
        "s6_low_s": "VOX СТИЛІ БРЕНД БЕДЕЛІН БІРДЕН КӨТЕРЕДІ",
        "s7_core": "1 БЕЙНЕЖОБА  =  3 НАРЫҚ",
        "s7_cols": [
            ("KZ", "ҚАЗАҚСТАН", "ЖЕРГІЛІКТІ БИЗНЕС", "БӘСЕКЕ ӨТЕ ТӨМЕН"),
            ("RU", "ТМД БИЗНЕСІ", "ТК • ТАУАР • IT", "ІРІ ЧЕКТЕР"),
            ("EN", "ДУБАЙ • АҚШ", "ХАЛЫҚАРАЛЫҚ B2B", "$100–$300+ / РОЛИК"),
        ],
        "s7_bot": "ТӨЛЕМ ҚАБІЛЕТТІ КЛИЕНТТЕРДІ ҮШ ЕСЕ АРТТЫРУ",
        "s7_low_t": "ҚАЗАҚША + ОРЫСША + АҒЫЛШЫНША",
        "s7_low_s": "ӘР АРНАҒА БӨЛЕК ТІЛДІК НҰСҚА ДАЙЫНДАЛАДЫ",
        "s8_checks": [
            ("01 • САТАТЫН СЦЕНАРИЙ", "0–3с ХУК, ҚҰРЫЛЫМ ЖӘНЕ НАҚТЫ ОФФЕР"),
            ("02 • 3D-КАРТА ЖӘНЕ ГРАФИК", "БАҒЫТТАР, ЦИФРЛАР МЕН АНИМАЦИЯ"),
            ("03 • ДАУЫС ПЕН ДЫБЫС", "СТУДИЯЛЫҚ ДИКТОР ЖӘНЕ МУЗЫКАСЫЗ SFX"),
            ("04 • 9:16 ТОЛЫҚ ФОРМАТ", "REELS, YOUTUBE SHORTS ЖӘНЕ TIKTOK-ҚА ДАЙЫН"),
        ],
        "s8_low_t": "ТОЛЫҚ ЦИКЛДІ ПРОДАКШН",
        "s8_low_s": "ІСКЕРЛІК СТАНДАРТ  •  100% ХАЛАЛ ФОРМАТ",
        "s9_tag": "БИЗНЕСКЕ САТАТЫН 3D-РОЛИК ЖАСАТУ",
        "s9_cta": "ДАЙРЕКТКЕ «ВИДЕО» ДЕП ЖАЗЫҢЫЗ",
        "s9_sub": "ӨНІМДІ ТАЛДАЙМЫЗ • МЫСАЛ КӨРСЕТЕМІЗ • БАҒАСЫН АЙТАМЫЗ",
        "s9_bot": "БІРДЕН 3 ТІЛДЕ ДАЙЫН: KZ  •  RU  •  EN",
        "s9_low_t": "REELS АРҚЫЛЫ ӨТІНІМ ҚАБЫЛДАҢЫЗ",
        "s9_low_s": "ДАЙРЕКТКЕ «ВИДЕО» ДЕП ЖАЗЫҢЫЗ ->",
    },
    "en": {
        "script": [
            "Why do ninety percent of business videos get swiped away in two seconds?",
            "Static photos and dull talking heads fail to hold attention — prospects scroll past while your ad budget burns.",
            "Now watch how 3D motion sells. For real estate developers, we turn flat brochures into living district maps and routes.",
            "In five seconds, buyers see schools, parks, rising property value, and clear installment terms right on screen.",
            "For e-commerce, marketplaces, and automotive brands, dynamic 3D breakdowns spotlight key features and real value in seconds.",
            "Viewers watch all the way through, click-through rates climb sharply, and your cost per lead drops significantly.",
            "For founders, SaaS brands, and experts, editorial Vox-style motion graphics build instant authority and warm inbound leads.",
            "Even better: one master production scales seamlessly into Kazakh, Russian, and English across local, CIS, and global markets.",
            "We handle the full pipeline: script, 3D maps, data visuals, studio voiceover, and crisp sound design ready for Reels, Shorts, and TikTok.",
            "Want high-converting motion videos for your business? DM the word \"VIDEO\" right now, otherwise you will keep wondering...",
        ],
        "tts_fix": [],
        "pillars": ["1. PROBLEM", "2. 3D CASES", "3. ROI PROOF", "4. ORDER NOW"],
        "banners": [
            ("BUSINESS VIDEO AUDIT", "WHY 90% OF ADS LOSE ATTENTION IN 2 SECONDS", 0),
            ("RETENTION CURVE 0–30s", "HOW MOTION LOCKS VIEWERS TO THE OFFER", 0),
            ("NICHE 1 • REAL ESTATE 3D", "LIVING DISTRICT MAP & TRANSIT ROUTES", 1),
            ("NICHE 1 • ASSET TELEMETRY", "AMENITIES • +38% GROWTH • 0% INSTALLMENTS", 1),
            ("NICHE 2 • E-COM & AUTOMOTIVE", "3D PRODUCT BREAKDOWNS IN SECONDS", 1),
            ("AD SPEND ECONOMICS", "FROM STATIC FLYERS TO 3D PERFORMANCE", 2),
            ("NICHE 3 • FOUNDERS & SAAS", "EDITORIAL VOX-STYLE B2B FUNNEL", 2),
            ("MULTI-MARKET SCALING", "ONE MASTER PROJECT -> THREE LANGUAGES", 2),
            ("DONE-FOR-YOU PIPELINE", "SCRIPT TO 9:16 FINAL DELIVERY", 3),
            ("READY FOR INBOUND LEADS?", "DM THE WORD \"VIDEO\" TO START", 3),
        ],
        "s0_before_tag": "BEFORE • STATIC POST",
        "s0_before_title": "SWIPED AWAY IN 1.8 SECONDS",
        "s0_before_badge": "CTR 0.6%  •  AD SPEND WASTED",
        "s0_mid": "3D UPGRADE",
        "s0_after_tag": "AFTER • 3D MOTION PRODUCTION",
        "s0_after_title": "HOLDS BUYERS TO THE OFFER",
        "s0_after_badge": "74% RETENTION  •  LEADS x4.2",
        "s0_low_t": "90% 2s DROP   vs   74% COMPLETION",
        "s0_low_s": "THE FIRST 3 SECONDS DECIDE YOUR AD CAMPAIGN ROI",
        "s1_hdr": "AUDIENCE RETENTION CURVE (0–30s)",
        "s1_bad": "STATIC AD: 11%",
        "s1_good": "3D MOTION: 74%",
        "s1_nodes": ["0s HOOK", "3s 3D MAP", "8s DATA", "15s OFFER"],
        "s1_low_t": "PATTERN-INTERRUPT TRIGGERS",
        "s1_low_s": "FRESH VISUAL SHIFT & DATA CUE EVERY 2.5–4 SECONDS",
        "s2_nodes": {
            "pin": "PRIME TOWERS", "park": "CITY PARK", "school": "SCHOOL",
            "center": "DOWNTOWN", "highway": "EXPRESSWAY",
        },
        "s2_rings": ("5 MIN", "10 MIN"),
        "s2_low_t": "CUSTOMIZED FOR ANY DEVELOPMENT",
        "s2_low_s": "TRANSIT ROUTES, LANDMARKS & COMMUTE RADIUS",
        "s3_floor": "32 FL • 118 M",
        "s3_growth": "+38% VALUE GROWTH",
        "s3_pill1": "0% PLAN • 24 MONTHS",
        "s3_pill2": "CONVERSION +290%",
        "s3_low_t": "BUYERS SEE FULL VALUE IN 5 SECONDS",
        "s3_low_s": "FLOOR TELEMETRY, APPRECIATION & CLEAR PAYMENT TERMS",
        "s4_title": "3D PRODUCT / AUTO BLUEPRINT",
        "s4_quads": [
            "1. 3D FEATURE CALLOUTS",
            "2. QUANTIFIED VALUE",
            "3. BRAND DIFFERENTIATION",
            "4. INSTANT DIRECT OFFER",
        ],
        "s4_low_t": "MARKETPLACES • E-COMMERCE • AUTO",
        "s4_low_s": "HIGH-CONTRAST 3D SPECS BEAT STATIC PRODUCT IMAGES",
        "s5_bad_t": "STATIC FLYER AD",
        "s5_bad_m": "CTR: 0.6%",
        "s5_bad_b": "HIGH COST PER LEAD  •  FAST SCROLL",
        "s5_good_t": "DYNAMIC 3D MOTION AD",
        "s5_good_m": "CTR: 3.8%  (x6.3)",
        "s5_good_b": "3.4x LOWER COST PER LEAD",
        "s5_low_t": "HIGHER CTR MEANS CHEAPER LEADS",
        "s5_low_s": "ALGORITHMS BOOST VIDEOS WITH HIGH WATCH TIME",
        "s6_funnel": [
            "1. SHARP HOOK (0–3s)",
            "2. 3D MAPS & DATA GRAPHICS",
            "3. BRAND AUTHORITY (74%)",
            "4. WARM INBOUND DM LEADS",
        ],
        "s6_roi": "AUTHORITY FUNNEL • ROI x4.2",
        "s6_low_t": "FOUNDERS • SAAS • B2B BREAKDOWNS",
        "s6_low_s": "VOX-STYLE VISUALS TURN VIEWERS INTO CLIENTS",
        "s7_core": "1 MASTER PROJECT  =  3 MARKETS",
        "s7_cols": [
            ("KZ", "KAZAKHSTAN", "LOCAL ENTERPRISES", "BLUE OCEAN MARKET"),
            ("RU", "CIS B2B", "DEVELOPERS & E-COM", "HIGH TICKET DEALS"),
            ("EN", "DUBAI • US • EU", "GLOBAL BRANDS", "$100–$300+ / REEL"),
        ],
        "s7_bot": "TRIPLE YOUR REACH TO PAYING CLIENTS",
        "s7_low_t": "ENGLISH + KAZAKH + RUSSIAN",
        "s7_low_s": "DEDICATED LOCALIZED VERSIONS FOR EACH CHANNEL",
        "s8_checks": [
            ("01 • HIGH-RETENTION SCRIPT", "0–3s HOOK, NARRATIVE FLOW & SHARP OFFER"),
            ("02 • 3D MAPS & MOTION CHARTS", "CUSTOM ROUTES, KPI COUNTERS & BLUEPRINTS"),
            ("03 • VOICEOVER & PHYSICAL SFX", "PRO NARRATION & CLEAN CINEMATIC AUDIO"),
            ("04 • 9:16 TURNKEY DELIVERY", "READY FOR REELS, YOUTUBE SHORTS & TIKTOK"),
        ],
        "s8_low_t": "END-TO-END MOTION PRODUCTION",
        "s8_low_s": "BRAND-SAFE EXECUTIVE STYLE  •  100% HALAL FORMAT",
        "s9_tag": "ORDER HIGH-RETENTION 3D REELS",
        "s9_cta": "DM THE WORD \"VIDEO\" NOW",
        "s9_sub": "PRODUCT AUDIT • SAMPLE REELS • CUSTOM QUOTE",
        "s9_bot": "AVAILABLE IN EN  •  RU  •  KZ",
        "s9_low_t": "TURN VIEWS INTO PAID CLIENT ORDERS",
        "s9_low_s": "SEND \"VIDEO\" TO DIRECT — SEAMLESS LOOP ->",
    },
}

URBAN_NODES = {
    "pin":     (540, 560),
    "school":  (245, 395),
    "park":    (835, 390),
    "center":  (245, 760),
    "highway": (835, 760),
}

URBAN_RIVER_PTS = [(60, 495), (275, 470), (490, 505), (725, 465), (1020, 485)]
URBAN_HWY_PTS   = [(85, 815), (340, 775), (595, 760), (855, 765), (1015, 750)]


# ---------------------------------------------------------------------------
# Verification: Safe ASCII/Cyrillic Glyph & Width Check
# ---------------------------------------------------------------------------

def _collect_strings(obj) -> list[str]:
    out = []
    if isinstance(obj, str):
        out.append(obj)
    elif isinstance(obj, (list, tuple)):
        for it in obj:
            out.extend(_collect_strings(it))
    elif isinstance(obj, dict):
        for v in obj.values():
            out.extend(_collect_strings(v))
    return out


def verify_all_texts():
    f_top, f_sub = rmod.font(30), rmod.font(24)
    for lang in ("ru", "kz", "en"):
        d = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
        for top_t, sub_t, _ in CONTENT[lang]["banners"]:
            if d.textlength(top_t, font=f_top) > W - 130:
                raise ValueError(f"[{lang}] Banner too wide: {top_t}")
            if d.textlength(sub_t, font=f_sub) > W - 120:
                raise ValueError(f"[{lang}] Sub callout too wide: {sub_t}")
        # Check pillar labels fit comfortably in 4-slot bar
        f_pil = rmod.font(24)
        slot_w = (W - 104) / 4
        for p in CONTENT[lang]["pillars"]:
            if d.textlength(p, font=f_pil) > slot_w - 18:
                raise ValueError(f"[{lang}] Pillar too wide for slot: {p}")


# ---------------------------------------------------------------------------
# Neural TTS + Alignment + Halal SFX Audio Pipeline
# ---------------------------------------------------------------------------

def _prep_tts_text(text: str, tts_fix: list[tuple[str, str]]) -> str:
    out = text
    for src, dst in tts_fix:
        out = out.replace(src, dst)
    return out


async def _tts_one(text: str, mp3_path: Path, voice: str, rate: str, pitch: str) -> list[dict]:
    comm = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch, boundary="WordBoundary")
    bounds: list[dict] = []
    with open(mp3_path, "wb") as f:
        async for chunk in comm.stream():
            ctype = chunk.get("type")
            if ctype == "audio":
                f.write(chunk["data"])
            elif ctype == "WordBoundary":
                bounds.append({
                    "offset": chunk["offset"] / 10_000_000.0,
                    "duration": chunk["duration"] / 10_000_000.0,
                    "text": chunk["text"],
                })
    return bounds


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

    # Pick one consistent working voice across all scenes in this language.
    voice_used = cfg["voice"]
    results: list[tuple[Path, list[dict]]] = []
    items_meta: list[dict] = []

    for voice_try in (cfg["voice"], cfg["fallback"]):
        results.clear()
        items_meta.clear()
        ok_all = True
        for i, raw_text in enumerate(lines):
            mp3_path = audio_dir / f"seg_{i:02d}.mp3"
            spoken = _prep_tts_text(raw_text, tts_fix)
            bounds = []
            line_ok = False
            for att in range(8):
                try:
                    if mp3_path.exists():
                        mp3_path.unlink()
                    bounds = await _tts_one(spoken, mp3_path, voice_try, cfg["rate"], cfg["pitch"])
                    if mp3_path.exists() and mp3_path.stat().st_size > 1500:
                        line_ok = True
                        break
                except Exception:
                    await asyncio.sleep(0.55 * (att + 1))
            if not line_ok:
                ok_all = False
                break
            results.append((mp3_path, bounds))
            items_meta.append({"bounds": bounds})
        if ok_all:
            voice_used = voice_try
            break

    if len(results) != len(lines):
        raise RuntimeError(f"[{lang}] Edge TTS synthesis failed after retries on both primary and fallback voices.")

    manifest_path.write_text(
        json.dumps({"hash": lines_hash, "voice": voice_used, "items": items_meta}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return results


def _decode_mp3_mono(mp3_path: Path) -> np.ndarray:
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
        wav_tmp = tf.name
    try:
        subprocess.run(
            [FFMPEG, "-y", "-i", str(mp3_path), "-ar", str(SR), "-ac", "1", wav_tmp],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        with wave.open(wav_tmp, "rb") as w:
            raw = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32)
        return raw / 32768.0
    finally:
        if os.path.exists(wav_tmp):
            os.remove(wav_tmp)


def _trim_silence(x: np.ndarray, head_pad: float = 0.04, tail_pad: float = 0.07) -> tuple[np.ndarray, float, float]:
    thr = max(0.008, float(np.max(np.abs(x))) * 0.012)
    idx = np.where(np.abs(x) > thr)[0]
    if len(idx) == 0:
        return x, 0.0, len(x) / SR
    i0 = max(0, int(idx[0]) - int(head_pad * SR))
    i1 = min(len(x), int(idx[-1]) + int(tail_pad * SR))
    seg = x[i0:i1].copy()
    f = min(len(seg) // 4, int(0.014 * SR))
    if f > 0:
        seg[:f] *= np.linspace(0.0, 1.0, f, dtype=np.float32)
        seg[-f:] *= np.linspace(1.0, 0.0, f, dtype=np.float32)
    return seg, i0 / SR, i1 / SR


def _voice_fx(x: np.ndarray) -> np.ndarray:
    if len(x) < 100:
        return x
    nyq = 0.5 * SR
    b_hp, a_hp = butter(2, 75.0 / nyq, btype="high")
    y = filtfilt(b_hp, a_hp, x).astype(np.float32)
    body = smod.bp(y, 120.0, 280.0) * 0.14
    pres = smod.bp(y, 2400.0, 4800.0) * 0.11
    y = y + body + pres
    peak = float(np.max(np.abs(y)))
    if peak > 1e-6:
        y = y / peak * 0.88
    return smod.softclip(y, 0.84)


def _align_words(text: str, bounds: list[dict], trim_t0: float, trim_t1: float, seg_dur: float, t_offset: float) -> list[dict]:
    tokens = text.split()
    out: list[dict] = []
    raw_span = max(0.2, trim_t1 - trim_t0)
    if bounds and len(bounds) >= max(2, int(len(tokens) * 0.65)):
        mapped = []
        bi = 0
        for tok in tokens:
            clean_tok = re.sub(r"[^\wА-Яа-яӘҒҚҢӨҰҮҺІәғқңөұүһі0-9]", "", tok.lower())
            best_b = None
            for k in range(bi, min(len(bounds), bi + 4)):
                btok = re.sub(r"[^\wА-Яа-яӘҒҚҢӨҰҮҺІәғқңөұүһі0-9]", "", bounds[k]["text"].lower())
                if btok and clean_tok and (btok in clean_tok or clean_tok in btok):
                    best_b = bounds[k]
                    bi = k + 1
                    break
            if best_b is not None:
                s = max(0.0, min(seg_dur - 0.05, (best_b["offset"] - trim_t0) * (seg_dur / raw_span)))
                e = max(s + 0.06, min(seg_dur, s + best_b["duration"] * (seg_dur / raw_span)))
                mapped.append((tok, s, e))
            else:
                mapped.append((tok, None, None))
        prev_e = 0.02
        for idx, (tok, s, e) in enumerate(mapped):
            if s is None:
                nxt_s = seg_dur - 0.02
                nxt_cnt = 1
                for j in range(idx + 1, len(mapped)):
                    if mapped[j][1] is not None:
                        nxt_s = mapped[j][1]
                        nxt_cnt = j - idx
                        break
                step = max(0.06, (nxt_s - prev_e) / max(1, nxt_cnt))
                s = prev_e
                e = min(seg_dur, s + step)
            out.append({"w": tok, "t0": t_offset + s, "t1": t_offset + e})
            prev_e = e
        return out

    weights = [max(2, len(re.sub(r"[^0-9A-Za-zА-Яа-яӘҒҚҢӨҰҮҺІәғқңөұүһі]", "", t))) for t in tokens]
    total_w = float(sum(weights)) or 1.0
    speech_start = min(0.04, seg_dur * 0.04)
    speech_span = max(0.2, seg_dur - speech_start - 0.05)
    cur = speech_start
    for tok, w in zip(tokens, weights):
        wd = speech_span * (w / total_w)
        out.append({"w": tok, "t0": t_offset + cur, "t1": t_offset + cur + wd})
        cur += wd
    return out


def synthesize_lang(lang: str, build_dir: Path) -> tuple[np.ndarray, list[dict], list[dict], float]:
    lines = CONTENT[lang]["script"]
    raw_items = asyncio.run(_tts_lang_async(lang, build_dir))
    segments_audio: list[np.ndarray] = []
    timeline: list[dict] = []
    words_all: list[dict] = []

    cursor = 0.0
    for si, ((mp3_path, bounds), text) in enumerate(zip(raw_items, lines)):
        raw_x = _decode_mp3_mono(mp3_path)
        head_pad = 0.03 if si == 0 else 0.04
        tail_pad = 0.04 if si == len(lines) - 1 else 0.07
        seg_x, t0_trim, t1_trim = _trim_silence(raw_x, head_pad=head_pad, tail_pad=tail_pad)
        seg_x = _voice_fx(seg_x)
        seg_dur = len(seg_x) / SR

        words_seg = _align_words(text, bounds, t0_trim, t1_trim, seg_dur, cursor)
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


def loudnorm_portable(src_wav: Path, dst_wav: Path, I: float = -14.0, TP: float = -1.5, LRA: float = 11.0):
    p1 = subprocess.run(
        [FFMPEG, "-y", "-i", str(src_wav), "-af", f"loudnorm=I={I}:TP={TP}:LRA={LRA}:print_format=json", "-f", "null", "-"],
        capture_output=True, text=True, check=True,
    )
    m = re.search(r"\{[\s\S]*?\"input_i\"[\s\S]*?\}", p1.stderr)
    if not m:
        subprocess.run(
            [FFMPEG, "-y", "-i", str(src_wav), "-af", f"loudnorm=I={I}:TP={TP}:LRA={LRA}", "-ar", str(SR), "-ac", "2", str(dst_wav)],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        return
    stats = json.loads(m.group(0))
    af = (
        f"loudnorm=I={I}:TP={TP}:LRA={LRA}:linear=true:"
        f"measured_I={stats['input_i']}:measured_TP={stats['input_tp']}:"
        f"measured_LRA={stats['input_lra']}:measured_thresh={stats['input_thresh']}:"
        f"offset={stats['target_offset']}"
    )
    subprocess.run(
        [FFMPEG, "-y", "-i", str(src_wav), "-af", af, "-ar", str(SR), "-ac", "2", str(dst_wav)],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


def build_b2b_audio(lang: str, build_dir: Path, voice_mono: np.ndarray, timeline: list[dict], dur: float) -> Path:
    mix_raw = build_dir / "mix_raw.wav"
    mix_wav = build_dir / "mix_final.wav"
    rng = np.random.default_rng({"ru": 20261, "kz": 20262, "en": 20263}[lang])
    n_samples = len(voice_mono)
    amb = np.zeros((n_samples, 2), dtype=np.float32)

    # Clean deep studio air room-tone bed (no harsh wind howl)
    room_air = smod.lp(smod.pink(rng, dur + 0.5), 240.0)
    smod.add(amb, smod.st(room_air[:n_samples], 0.0) * 0.14, 0.0)

    # Male a cappella harmonic pad across 3 dynamic acts (zero instruments)
    act_defs = [
        (0, 2,  [73.42, 110.0, 146.83],         "m", 3, 0.16),
        (2, 6,  [82.41, 123.47, 164.81, 246.94], "o", 3, 0.16),
        (6, 10, [98.00, 146.83, 196.00, 293.66], "a", 4, 0.18),
    ]
    for s_lo, s_hi, freqs, vowel, voices, gain in act_defs:
        a0 = timeline[s_lo]["t0"]
        a1 = timeline[s_hi - 1]["t1"]
        pad = smod.vocal_pad(rng, max(1.0, a1 - a0 + 0.5), freqs, vowel=vowel, voices=voices)
        pad_st = smod.reverb(pad, wet=0.28, seed=9100 + s_lo)
        smod.add(amb, pad_st * gain, a0)

    # Crisp physical SFX synced to kinetic UI & transitions
    for row in timeline:
        si, t0, sd = row["si"], row["t0"], row["dur"]
        if si == 0:
            smod.add(amb, smod.reverb(smod.impact_boom(rng, 1.1), wet=0.24, seed=901) * 0.62, 0.02)
            smod.add(amb, smod.st(smod.whoosh(rng, 0.45), 0.15) * 0.45, 0.08)
        elif si == 1:
            smod.add(amb, smod.reverb(smod.clasp(rng), wet=0.16, seed=902) * 0.44, t0 + 0.06)
            smod.add(amb, smod.st(smod.riser(rng, min(1.4, sd * 0.6)), 0.0) * 0.34, t0 + sd * 0.32)
        elif si == 2:
            smod.add(amb, smod.st(smod.whoosh(rng, 0.55), -0.18) * 0.46, t0 + 0.04)
            smod.add(amb, smod.reverb(smod.thud(rng), wet=0.18, seed=903) * 0.40, t0 + sd * 0.45)
        elif si == 3:
            smod.add(amb, smod.reverb(smod.clasp(rng), wet=0.15, seed=904) * 0.42, t0 + 0.10)
            smod.add(amb, smod.st(smod.whoosh(rng, 0.40), 0.20) * 0.36, t0 + sd * 0.55)
        elif si == 4:
            smod.add(amb, smod.reverb(smod.sword_draw(rng, 0.65), wet=0.20, seed=905) * 0.40, t0 + 0.05)
            smod.add(amb, smod.st(smod.whoosh(rng, 0.42), -0.16) * 0.38, t0 + sd * 0.48)
        elif si == 5:
            smod.add(amb, smod.reverb(smod.impact_boom(rng, 1.0), wet=0.24, seed=906) * 0.48, t0 + 0.06)
            smod.add(amb, smod.reverb(smod.clasp(rng), wet=0.15, seed=907) * 0.40, t0 + sd * 0.52)
        elif si == 6:
            smod.add(amb, smod.st(smod.whoosh(rng, 0.48), 0.14) * 0.42, t0 + 0.06)
            smod.add(amb, smod.reverb(smod.clasp(rng), wet=0.16, seed=908) * 0.36, t0 + sd * 0.58)
        elif si == 7:
            for k, frac in enumerate((0.12, 0.38, 0.65)):
                smod.add(amb, smod.reverb(smod.clasp(rng), wet=0.14, seed=910 + k) * 0.38, t0 + sd * frac)
        elif si == 8:
            smod.add(amb, smod.reverb(smod.thud(rng), wet=0.18, seed=920) * 0.42, t0 + 0.08)
            smod.add(amb, smod.st(smod.riser(rng, min(1.3, sd * 0.55)), 0.0) * 0.32, t0 + sd * 0.42)
        elif si == 9:
            smod.add(amb, smod.reverb(smod.impact_boom(rng, 1.1), wet=0.24, seed=930) * 0.46, t0 + 0.05)
            rlen = min(1.35, sd * 0.55)
            smod.add(amb, smod.st(smod.riser(rng, rlen), 0.0) * 0.38, max(t0, dur - rlen - 0.03))

    rms = smod.frame_rms(voice_mono, win=0.05)
    rms_st = np.interp(np.arange(n_samples), np.arange(len(rms)) * int(SR * 0.05), rms)
    duck = 1.0 - 0.54 * np.clip(rms_st / 0.085, 0.0, 1.0)
    amb *= duck[:, None]

    out = amb * 0.88 + smod.st(voice_mono, 0.0) * 1.00
    out = smod.softclip(out, 0.90)
    smod.write(str(mix_raw), out)
    loudnorm_portable(mix_raw, mix_wav, I=-14.0, TP=-1.5, LRA=11.0)
    return mix_wav


# ---------------------------------------------------------------------------
# Procedural Backgrounds, 3D Urban Relief Map & Shared UI Primitives
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def build_studio_backdrop() -> np.ndarray:
    """Deep obsidian-sapphire studio backdrop with radial spotlight Glow."""
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    cx, cy = W * 0.50, 680.0
    dist = np.sqrt(((xx - cx) / 540.0) ** 2 + ((yy - cy) / 620.0) ** 2)
    spot = np.exp(-(dist ** 2) * 0.85)
    vert = 1.0 - np.abs(yy / H - 0.45) * 0.55

    r = 8.0 + 18.0 * spot + 5.0 * vert
    g = 14.0 + 30.0 * spot + 10.0 * vert
    b = 26.0 + 48.0 * spot + 16.0 * vert
    return np.stack([r, g, b], axis=-1).clip(0, 255).astype(np.uint8)


@lru_cache(maxsize=1)
def build_b2b_urban_relief_map() -> Image.Image:
    """2x procedural 3D hillshaded urban + foothill topography for Niche #1 Real Estate."""
    hw, hh = W // 2, H // 2
    elev = anim.fbm_noise(hh, hw, octaves=5, base_scale=95.0, seed=2026)
    yy, xx = np.mgrid[0:hh, 0:hw].astype(np.float32)
    nx, ny = xx / hw, yy / hh

    # Foothills toward upper-right & gentle valley basin in middle city zone
    hills = np.exp(-((nx - 0.82) ** 2 / 0.08 + (ny - 0.24) ** 2 / 0.05)) * 0.72
    park_mound = np.exp(-((nx - 0.76) ** 2 + (ny - 0.21) ** 2) / 0.018) * 0.35
    hmap = np.clip(elev * 0.46 + hills + park_mound, 0.0, 1.35)

    gx = sobel(hmap, axis=1) * 18.0
    gy = sobel(hmap, axis=0) * 18.0
    az, alt = math.radians(315), math.radians(44)
    slope = np.arctan(np.hypot(gx, gy))
    aspect = np.arctan2(-gy, gx)
    shade = np.clip(np.sin(alt) * np.cos(slope) + np.cos(alt) * np.sin(slope) * np.cos(az - aspect), 0.16, 1.0)

    r = 12.0 + 24.0 * shade + 16.0 * np.clip(hmap - 0.48, 0, 1)
    g = 22.0 + 36.0 * shade + 18.0 * np.clip(hmap - 0.48, 0, 1)
    b = 34.0 + 50.0 * shade + 14.0 * np.clip(hmap - 0.48, 0, 1)

    # Subtle urban block avenues in middle district zone (ny in 0.16..0.46)
    urban_mask = (ny > 0.15) & (ny < 0.46) & (nx > 0.10) & (nx < 0.90)
    grid_x = ((xx % 22) < 2) & urban_mask
    grid_y = ((yy % 22) < 2) & urban_mask
    blocks = grid_x | grid_y
    r[blocks] += 10.0
    g[blocks] += 15.0
    b[blocks] += 22.0

    iso = np.abs(np.sin(hmap * 22.0)) < 0.070
    r[iso] += 6.0
    g[iso] += 10.0
    b[iso] += 13.0

    rgb = np.stack([r, g, b], axis=-1).clip(0, 255).astype(np.uint8)
    return Image.fromarray(rgb).resize((W * 2, H * 2), Image.Resampling.BICUBIC)


def draw_grid_ambience(ov: Image.Image, t: float, gold_tint: bool = False):
    d = ImageDraw.Draw(ov)
    line_col = (248, 202, 84, 15) if gold_tint else (86, 178, 232, 16)
    for gx in range(60, W, 90):
        d.line([(gx, 220), (gx, 1110)], fill=line_col, width=1)
    for gy in range(240, 1110, 90):
        d.line([(40, gy), (W - 40, gy)], fill=line_col, width=1)
    # Moving horizontal scan sheen in showcase zone
    sy = 250 + ((t * 140.0) % 830.0)
    d.line([(64, sy), (W - 64, sy)], fill=(72, 224, 218, 28), width=2)


def draw_particles_studio(ov: Image.Image, t: float, seed: int = 12, count: int = 20):
    d = ImageDraw.Draw(ov)
    rng = np.random.default_rng(seed)
    xs = rng.uniform(50, W - 50, count)
    ys = rng.uniform(240, 1100, count)
    sp = rng.uniform(18, 52, count)
    rs = rng.uniform(1.8, 3.6, count)
    for k in range(count):
        px = (xs[k] + t * sp[k] * 0.35) % W
        py = 240 + ((ys[k] - t * sp[k] * 0.65 - 240) % 860)
        al = int(42 + 40 * math.sin(t * 2.5 + k))
        col = (*GOLD, al) if k % 3 == 0 else (*CYAN, al)
        d.ellipse([px - rs[k], py - rs[k], px + rs[k], py + rs[k]], fill=col)


def draw_panel(d: ImageDraw.ImageDraw, x0: float, y0: float, x1: float, y1: float,
               pop: float = 1.0, fill_rgb=BG_CARD, out_rgb=GOLD, radius: int = 20,
               fill_alpha: int = 216, width: int = 3):
    d.rounded_rectangle(
        [x0, y0, x1, y1],
        radius=radius,
        fill=(*fill_rgb, int(fill_alpha * pop)),
        outline=(*out_rgb, int(238 * pop)),
        width=width,
    )


def draw_center_text(d: ImageDraw.ImageDraw, text: str, cx: float, y: float, size: int, fill_rgba: tuple):
    f = rmod.font(size)
    tw = d.textlength(text, font=f)
    d.text((cx - tw / 2, y), text, font=f, fill=fill_rgba)


def fit_font_text(d: ImageDraw.ImageDraw, text: str, max_w: float, start_size: int, min_size: int = 16):
    for sz in range(start_size, min_size - 1, -2):
        f = rmod.font(sz)
        if d.textlength(text, font=f) <= max_w:
            return f, d.textlength(text, font=f)
    f = rmod.font(min_size)
    return f, d.textlength(text, font=f)


def draw_vector_check(d: ImageDraw.ImageDraw, cx: float, cy: float, r: float, col: tuple):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(16, 46, 38, 240), outline=col, width=3)
    d.line([(cx - r * 0.42, cy + r * 0.05), (cx - r * 0.08, cy + r * 0.38), (cx + r * 0.45, cy - r * 0.34)],
           fill=col, width=5, joint="curve")


def draw_vector_cross(d: ImageDraw.ImageDraw, cx: float, cy: float, r: float, col: tuple):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(46, 18, 22, 235), outline=col, width=3)
    k = r * 0.40
    d.line([(cx - k, cy - k), (cx + k, cy + k)], fill=col, width=5)
    d.line([(cx - k, cy + k), (cx + k, cy - k)], fill=col, width=5)


def draw_lower_card(ov: Image.Image, title: str, sub: str, col: tuple, tau: float, prog: float | None = None):
    """Unified lower telemetry card inside y=1412..1555 (strictly below SUB_Y=1250)."""
    d = ImageDraw.Draw(ov)
    pop = anim.ease_out(min(1.0, tau / 0.22))
    cw, ch = 880, 126
    x0 = (W - cw) // 2
    y0 = 1418 + int(16 * (1.0 - pop))
    draw_panel(d, x0, y0, x0 + cw, y0 + ch, pop=pop, fill_rgb=BG_CARD, out_rgb=col, radius=18)

    f1, tw1 = fit_font_text(d, title, cw - 52, 27, 18)
    d.text((x0 + (cw - tw1) / 2, y0 + 16), title, font=f1, fill=(*col, int(250 * pop)))

    if prog is not None:
        bx0, by0, bw, bh = x0 + 48, y0 + 54, cw - 96, 18
        d.rounded_rectangle([bx0, by0, bx0 + bw, by0 + bh], radius=9, fill=(26, 36, 52, 230))
        d.rounded_rectangle([bx0 + 2, by0 + 2, bx0 + 2 + int((bw - 4) * max(0.03, prog)), by0 + bh - 2],
                            radius=7, fill=(*col, int(238 * pop)))
        f2, tw2 = fit_font_text(d, sub, cw - 52, 20, 15)
        d.text((x0 + (cw - tw2) / 2, y0 + 84), sub, font=f2, fill=(*WHITE, int(238 * pop)))
    else:
        f2, tw2 = fit_font_text(d, sub, cw - 52, 22, 16)
        d.text((x0 + (cw - tw2) / 2, y0 + 64), sub, font=f2, fill=(*WHITE, int(240 * pop)))


# ---------------------------------------------------------------------------
# 10 Procedural Commercial & Analytic Scenes (si = 0..9, y=245..1090)
# ---------------------------------------------------------------------------

def render_scene_frame(lang: str, si: int, u: float, tau: float, seg_dur: float, t: float) -> Image.Image:
    L = CONTENT[lang]
    pop = anim.ease_out(min(1.0, tau / 0.25))
    fill_u = anim.ease_out(min(1.0, max(0.0, (tau - 0.04) / max(0.55, seg_dur * 0.72))))

    # Scene 2 uses live camera-tracked 3D urban relief map; others use lit obsidian-sapphire studio
    if si == 2:
        cam = anim.MapCamera(1.04 + 0.14 * anim.smoothstep(u), 540.0, 560.0 - 15.0 * anim.smoothstep(u))
        hi = build_b2b_urban_relief_map()
        box_2x = (cam.x0 * 2.0, cam.y0 * 2.0, (cam.x0 + cam.vw) * 2.0, (cam.y0 + cam.vh) * 2.0)
        bg = hi.transform((W, H), Image.Transform.EXTENT, box_2x, Image.Resampling.BICUBIC).convert("RGBA")
        # Clean dark band behind subtitle zone (y=1120..1380) so white/gold subs stay ultra sharp
        band = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        bd = ImageDraw.Draw(band)
        bd.rectangle([0, 1110, W, 1405], fill=(8, 14, 24, 185))
        bg.alpha_composite(band)
    else:
        bg = Image.fromarray(build_studio_backdrop()).convert("RGBA")

    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)

    if si != 2:
        draw_grid_ambience(ov, t, gold_tint=(si in (3, 7, 9)))

    # -----------------------------------------------------------------------
    # SCENE 0: Hook Split Duel — Before (Static 1.8s Swipe) vs After (3D Motion)
    # -----------------------------------------------------------------------
    if si == 0:
        jitter_x = int(math.sin(t * 28.0) * 4.0) if tau < 0.7 else 0
        # BEFORE card (y=248..548)
        bx0, by0, bx1, by1 = 78 + jitter_x, 250, 1002 + jitter_x, 548
        draw_panel(d, bx0, by0, bx1, by1, pop=pop, fill_rgb=BG_RED, out_rgb=CORAL, radius=22)
        draw_vector_cross(d, bx0 + 52, by0 + 52, 22, (*CORAL, 240))
        d.text((bx0 + 90, by0 + 36), L["s0_before_tag"], font=rmod.font(24), fill=(*CORAL, 245))
        f_bt, _ = fit_font_text(d, L["s0_before_title"], 840, 32, 22)
        d.text((bx0 + 38, by0 + 96), L["s0_before_title"], font=f_bt, fill=(*WHITE, 230))
        # Collapsing progress gauge (drains fast like a swipe away)
        swipe_u = min(1.0, max(0.0, tau / 1.4))
        rem_w = max(28, int((840 - 80) * (1.0 - 0.86 * swipe_u)))
        d.rounded_rectangle([bx0 + 38, by0 + 158, bx1 - 38, by0 + 190], radius=10, fill=(58, 24, 28, 220))
        d.rounded_rectangle([bx0 + 42, by0 + 162, bx0 + 42 + rem_w, by0 + 186], radius=8, fill=(*CORAL, 235))
        d.rounded_rectangle([bx0 + 38, by0 + 214, bx1 - 38, by0 + 272], radius=12, fill=(56, 20, 24, 230), outline=(*CORAL, 160), width=2)
        f_bb, tw_bb = fit_font_text(d, L["s0_before_badge"], 820, 26, 18)
        d.text(((W - tw_bb) / 2, by0 + 228), L["s0_before_badge"], font=f_bb, fill=(255, 148, 138, 250))

        # Divider VS / 3D Upgrade Pill (y=568..630)
        pulse = 1.0 + 0.08 * math.sin(t * 7.0)
        mw = int(310 * pulse)
        draw_panel(d, 540 - mw // 2, 566, 540 + mw // 2, 628, pop=pop, fill_rgb=(28, 24, 14), out_rgb=GOLD, radius=18)
        f_mid, tw_mid = fit_font_text(d, L["s0_mid"], mw - 24, 25, 18)
        d.text((540 - tw_mid / 2, 581), L["s0_mid"], font=f_mid, fill=(*GOLD_BRIGHT, 255))

        # AFTER card (y=648..1068)
        ax0, ay0, ax1, ay1 = 78, 648, 1002, 1068
        draw_panel(d, ax0, ay0, ax1, ay1, pop=pop, fill_rgb=(12, 30, 38), out_rgb=EMERALD, radius=22)
        draw_vector_check(d, ax0 + 52, ay0 + 52, 22, (*EMERALD, 250))
        d.text((ax0 + 90, ay0 + 36), L["s0_after_tag"], font=rmod.font(24), fill=(*EMERALD, 250))
        f_at, _ = fit_font_text(d, L["s0_after_title"], 840, 32, 22)
        d.text((ax0 + 38, ay0 + 96), L["s0_after_title"], font=f_at, fill=(*WHITE, 255))
        # Ascending animated bars inside AFTER card (strictly below ay0 + 148)
        bar_base = ay0 + 304
        for k in range(6):
            bx = ax0 + 62 + k * 76
            bh = int((36 + k * 19) * anim.ease_out(min(1.0, max(0.0, fill_u * 1.4 - k * 0.08))))
            col_b = GOLD if k >= 4 else EMERALD
            d.rounded_rectangle([bx, bar_base - bh, bx + 48, bar_base], radius=8, fill=(*col_b, 235))
        # Mini 3D ascending arrow beside bars
        pts_up = [(ax0 + 540, ay0 + 286), (ax0 + 660, ay0 + 244), (ax0 + 765, ay0 + 204), (ax0 + 865, ay0 + 162)]
        end_idx = max(2, int(len(pts_up) * fill_u + 1))
        d.line(pts_up[:end_idx], fill=(*GOLD_BRIGHT, 245), width=8)
        lx, ly = pts_up[min(len(pts_up) - 1, end_idx - 1)]
        d.ellipse([lx - 10, ly - 10, lx + 10, ly + 10], fill=(*GOLD_BRIGHT, 255))
        # Green-Gold result pill
        d.rounded_rectangle([ax0 + 38, ay0 + 322, ax1 - 38, ay0 + 392], radius=14, fill=(18, 46, 36, 235), outline=(*GOLD, 210), width=2)
        f_ab, tw_ab = fit_font_text(d, L["s0_after_badge"], 820, 29, 20)
        d.text(((W - tw_ab) / 2, ay0 + 340), L["s0_after_badge"], font=f_ab, fill=(*GOLD_BRIGHT, 255))

        draw_lower_card(ov, L["s0_low_t"], L["s0_low_s"], GOLD, tau, prog=fill_u)

    # -----------------------------------------------------------------------
    # SCENE 1: Audience Retention Curve Duel (0-30s)
    # -----------------------------------------------------------------------
    elif si == 1:
        px0, py0, px1, py1 = 68, 252, 1012, 1052
        draw_panel(d, px0, py0, px1, py1, pop=pop, fill_rgb=BG_CARD, out_rgb=CYAN, radius=24)
        f_ch, tw_ch = fit_font_text(d, L["s1_hdr"], 880, 29, 20)
        d.text(((W - tw_ch) / 2, py0 + 28), L["s1_hdr"], font=f_ch, fill=(*GOLD, 250))

        # Plot box
        gx0, gy0, gx1, gy1 = px0 + 92, py0 + 108, px1 - 46, py1 - 150
        gw, gh = gx1 - gx0, gy1 - gy0
        for pct in (0, 25, 50, 75, 100):
            yy = gy1 - gh * (pct / 100.0)
            d.line([(gx0, yy), (gx1, yy)], fill=(70, 92, 118, 95), width=2)
            d.text((px0 + 20, yy - 13), f"{pct}%", font=rmod.font(20), fill=(*MUTED, 210))
        d.line([(gx0, gy0), (gx0, gy1), (gx1, gy1)], fill=(150, 175, 205, 195), width=3)
        sec_unit = "s" if lang == "en" else "с"
        for tx_u, sec_v in ((0.0, 0), (0.33, 10), (0.66, 20), (1.0, 30)):
            xx_t = gx0 + gw * tx_u
            slbl = f"{sec_v}{sec_unit}"
            sw = d.textlength(slbl, font=rmod.font(18))
            d.text((max(gx0, min(gx1 - sw, xx_t - sw / 2)), gy1 + 10), slbl, font=rmod.font(18), fill=(*MUTED, 210))

        # Bad collapsing curve (drops to 11% around 2s-5s)
        bad_pts = []
        n_samp = 48
        max_i = max(2, int(n_samp * fill_u))
        for k in range(n_samp + 1):
            u_x = k / n_samp
            val = 0.11 + 0.89 * math.exp(-u_x * 9.5)
            bad_pts.append((gx0 + gw * u_x, gy1 - gh * val))
        d.line(bad_pts[:max_i], fill=(*CORAL, 240), width=7, joint="curve")

        # Good 3D curve (holds at 74%)
        good_pts = []
        for k in range(n_samp + 1):
            u_x = k / n_samp
            val = 0.74 + 0.26 * math.exp(-u_x * 5.2) + 0.025 * math.sin(u_x * 16.0)
            val = min(1.0, max(0.72, val))
            good_pts.append((gx0 + gw * u_x, gy1 - gh * val))
        d.line(good_pts[:max_i], fill=(*EMERALD, 245), width=9, joint="curve")

        # Highlight trigger milestones on green curve
        trigger_fracs = (0.04, 0.22, 0.48, 0.78)
        for tf, tlbl in zip(trigger_fracs, L["s1_nodes"]):
            if fill_u >= tf:
                idx = min(n_samp, int(tf * n_samp))
                tx, ty = good_pts[idx]
                d.ellipse([tx - 12, ty - 12, tx + 12, ty + 12], fill=(*GOLD_BRIGHT, 255), outline=(12, 20, 34, 255), width=3)
                # Label box cleanly placed above curve
                f_n = rmod.font(18)
                nw = d.textlength(tlbl, font=f_n)
                bx = max(gx0 + 18, min(gx1 - nw - 18, tx - nw / 2 - 8))
                by = ty - 54
                d.rounded_rectangle([bx, by, bx + nw + 16, by + 34], radius=9, fill=(14, 34, 42, 235), outline=(*GOLD, 210), width=2)
                d.text((bx + 8, by + 6), tlbl, font=f_n, fill=(*GOLD_BRIGHT, 255))

        # Legend pills inside bottom of chart panel (y=935..1020)
        ly = py1 - 102
        draw_panel(d, px0 + 44, ly, px0 + 440, ly + 68, pop=pop, fill_rgb=BG_RED, out_rgb=CORAL, radius=14)
        f_l1, tw_l1 = fit_font_text(d, L["s1_bad"], 370, 24, 17)
        d.text((px0 + 44 + (396 - tw_l1) / 2, ly + 20), L["s1_bad"], font=f_l1, fill=(255, 148, 138, 252))

        draw_panel(d, px1 - 440, ly, px1 - 44, ly + 68, pop=pop, fill_rgb=(14, 38, 34), out_rgb=EMERALD, radius=14)
        f_l2, tw_l2 = fit_font_text(d, L["s1_good"], 370, 24, 17)
        d.text((px1 - 440 + (396 - tw_l2) / 2, ly + 20), L["s1_good"], font=f_l2, fill=(*EMERALD, 255))

        draw_lower_card(ov, L["s1_low_t"], L["s1_low_s"], CYAN, tau, prog=fill_u)

    # -----------------------------------------------------------------------
    # SCENE 2: Niche #1 Real Estate — Live 3D District Map & Routes
    # -----------------------------------------------------------------------
    elif si == 2:
        # Subtle map coordinate lines
        for gx_w in range(100, W, 160):
            d.line([cam.pt(gx_w, 220), cam.pt(gx_w, 1080)], fill=(120, 200, 240, 26), width=1)
        for gy_w in range(240, 1080, 140):
            d.line([cam.pt(40, gy_w), cam.pt(W - 40, gy_w)], fill=(120, 200, 240, 26), width=1)

        # Animated canal/river and highway corridor
        for pts_w, c_glow, c_core, w_core in (
            (URBAN_RIVER_PTS, (24, 108, 146, 130), (80, 212, 244, 210), 6),
            (URBAN_HWY_PTS,   (110, 88, 36, 130),  (248, 202, 84, 195), 7),
        ):
            dense_w = anim.eval_polyline(pts_w, 90)
            dense_s = cam.pts(dense_w)
            d.line(dense_s, fill=c_glow, width=14)
            d.line(dense_s, fill=c_core, width=w_core)

        # Concentric 5 MIN / 10 MIN distance radar rings around central residential pin
        px_c, py_c = cam.pt(*URBAN_NODES["pin"])
        for rad_w, ring_lbl, col_r in ((148, L["s2_rings"][0], CYAN), (275, L["s2_rings"][1], GOLD)):
            rs = rad_w * cam.zoom * anim.ease_out(min(1.0, fill_u * 1.25))
            d.ellipse([px_c - rs, py_c - rs, px_c + rs, py_c + rs], outline=(*col_r, 175), width=3)
            rl_w = d.textlength(ring_lbl, font=rmod.font(20))
            d.rounded_rectangle([px_c - rl_w / 2 - 10, py_c - rs - 16, px_c + rl_w / 2 + 10, py_c - rs + 14],
                                radius=8, fill=(10, 22, 34, 230), outline=(*col_r, 200), width=2)
            d.text((px_c - rl_w / 2, py_c - rs - 12), ring_lbl, font=rmod.font(20), fill=(*col_r, 250))

        # Animated routes from ЖК PREMIUM pin outward to 4 landmarks
        p_route = anim.ease_out(min(1.0, u / 0.78))
        for dst_k, mid_pt, col_a in (
            ("school",  (385, 455), CYAN),
            ("park",    (695, 450), EMERALD),
            ("center",  (385, 675), GOLD),
            ("highway", (695, 670), GOLD_BRIGHT),
        ):
            route = [URBAN_NODES["pin"], mid_pt, URBAN_NODES[dst_k]]
            anim.draw_animated_arrow(ov, cam, route, p_route, t, col_main=col_a, col_glow=(255, 248, 210), width=10)

        # Draw crisp labeled pins
        for key, wpos in URBAN_NODES.items():
            sx, sy = cam.pt(*wpos)
            lbl = L["s2_nodes"][key]
            is_main = (key == "pin")
            col_n = GOLD if is_main else (EMERALD if key == "park" else CYAN)
            r_dot = 18 if is_main else 12
            if is_main:
                pulse_r = r_dot + 12 + 8 * abs(math.sin(t * 4.5))
                d.ellipse([sx - pulse_r, sy - pulse_r, sx + pulse_r, sy + pulse_r], outline=(*GOLD, 180), width=3)
            d.ellipse([sx - r_dot, sy - r_dot, sx + r_dot, sy + r_dot], fill=(*col_n, 255), outline=(10, 16, 26, 255), width=4)
            f_n = rmod.font(26 if is_main else 22)
            nw = d.textlength(lbl, font=f_n)
            ly_off = -56 if key in ("pin", "school", "park") else 26
            bx0 = max(36, min(W - nw - 56, sx - nw / 2 - 14))
            d.rounded_rectangle([bx0, sy + ly_off, bx0 + nw + 28, sy + ly_off + 38],
                                radius=10, fill=(10, 20, 32, 238), outline=(*col_n, 230), width=2)
            d.text((bx0 + 14, sy + ly_off + 6), lbl, font=f_n, fill=(*WHITE, 255))

        draw_lower_card(ov, L["s2_low_t"], L["s2_low_s"], GOLD, tau, prog=fill_u)

    # -----------------------------------------------------------------------
    # SCENE 3: Real Estate Asset Telemetry — 3D Wireframe Towers + 0% Plan
    # -----------------------------------------------------------------------
    elif si == 3:
        draw_panel(d, 72, 250, 560, 840, pop=pop, fill_rgb=BG_CARD, out_rgb=CYAN, radius=22)
        draw_panel(d, 580, 250, 1008, 840, pop=pop, fill_rgb=BG_CARD, out_rgb=GOLD, radius=22)

        # Left card: 3 rising 3D wireframe towers
        base_y = 780
        d.line([(106, base_y), (528, base_y)], fill=(*CYAN, 180), width=3)
        towers = [
            (132, 110, 250, 0.00, CYAN),
            (256, 130, 415, 0.14, GOLD),
            (398, 102, 320, 0.28, EMERALD),
        ]
        for tx, tw_b, full_h, delay, tcol in towers:
            tu = anim.ease_out(min(1.0, max(0.0, (fill_u - delay) / max(0.25, 1.0 - delay))))
            cur_h = max(12, int(full_h * tu))
            ty = base_y - cur_h
            # Front glass face + side perspective depth face
            d.rectangle([tx, ty, tx + tw_b, base_y], fill=(16, 36, 56, 225), outline=(*tcol, 240), width=3)
            d.polygon(
                [(tx + tw_b, ty), (tx + tw_b + 24, ty + 16), (tx + tw_b + 24, base_y), (tx + tw_b, base_y)],
                fill=(10, 24, 38, 220), outline=(*tcol, 190),
            )
            # Lit window bands
            for wy in range(ty + 18, base_y - 16, 24):
                lit = ((wy // 24 + tx) % 3) != 0
                w_col = (*GOLD_BRIGHT, 190) if lit else (56, 98, 128, 120)
                d.rectangle([tx + 12, wy, tx + tw_b - 12, wy + 10], fill=w_col)
        # Architectural height label
        f_fl, tw_fl = fit_font_text(d, L["s3_floor"], 420, 24, 18)
        d.text((72 + (488 - tw_fl) / 2, 796), L["s3_floor"], font=f_fl, fill=(*CYAN, 250))

        # Right card: 4-bar rising value telemetry
        g_base = 740
        vals = [0.32, 0.50, 0.72, 0.96]
        yrs = ["2023", "2024", "2025", "2026"]
        for idx, (vf, yr) in enumerate(zip(vals, yrs)):
            bx = 620 + idx * 92
            bu = anim.ease_out(min(1.0, max(0.0, fill_u * 1.35 - idx * 0.14)))
            bh = max(12, int(355 * vf * bu))
            bcol = GOLD_BRIGHT if idx == 3 else EMERALD
            d.rounded_rectangle([bx, g_base - bh, bx + 58, g_base], radius=8, fill=(*bcol, 232))
            yw = d.textlength(yr, font=rmod.font(20))
            d.text((bx + 29 - yw / 2, g_base + 12), yr, font=rmod.font(20), fill=(*MUTED, 235))
        f_gr, tw_gr = fit_font_text(d, L["s3_growth"], 390, 28, 19)
        d.text((580 + (428 - tw_gr) / 2, 286), L["s3_growth"], font=f_gr, fill=(*GOLD_BRIGHT, 255))

        # Bottom twin pills inside stage (y=865..1035)
        draw_panel(d, 72, 868, 528, 1020, pop=pop, fill_rgb=(14, 34, 30), out_rgb=EMERALD, radius=18)
        f_p1, tw_p1 = fit_font_text(d, L["s3_pill1"], 420, 28, 18)
        d.text((72 + (456 - tw_p1) / 2, 926), L["s3_pill1"], font=f_p1, fill=(*EMERALD, 255))

        draw_panel(d, 552, 868, 1008, 1020, pop=pop, fill_rgb=(28, 24, 12), out_rgb=GOLD, radius=18)
        f_p2, tw_p2 = fit_font_text(d, L["s3_pill2"], 420, 28, 18)
        d.text((552 + (456 - tw_p2) / 2, 926), L["s3_pill2"], font=f_p2, fill=(*GOLD_BRIGHT, 255))

        draw_lower_card(ov, L["s3_low_t"], L["s3_low_s"], GOLD, tau, prog=fill_u)

    # -----------------------------------------------------------------------
    # SCENE 4: Niche #2 Kaspi / E-Commerce / Auto — Isometric 3D Blueprint
    # -----------------------------------------------------------------------
    elif si == 4:
        draw_panel(d, 68, 250, 1012, 1055, pop=pop, fill_rgb=(10, 18, 30), out_rgb=CYAN, radius=24)
        f_bt, tw_bt = fit_font_text(d, L["s4_title"], 860, 28, 20)
        d.text(((W - tw_bt) / 2, 276), L["s4_title"], font=f_bt, fill=(*GOLD, 250))

        # Center rotating isometric 3D chamfered tech/auto prism
        cx, cy = 540, 650
        rot = t * 0.65
        rx, ry = 185.0, 95.0
        # Outer reticle circle
        d.ellipse([cx - 210, cy - 175, cx + 210, cy + 175], outline=(72, 224, 218, 85), width=2)
        d.ellipse([cx - 145, cy - 120, cx + 145, cy + 120], outline=(248, 202, 84, 95), width=2)

        top_pts = []
        bot_pts = []
        for k in range(6):
            ang = rot + k * math.pi / 3.0
            px = cx + math.cos(ang) * rx
            py = cy - 46 + math.sin(ang) * ry
            top_pts.append((px, py))
            bot_pts.append((px, py + 92))
        d.polygon(bot_pts, fill=(16, 40, 62, 180), outline=(*CYAN, 200))
        d.polygon(top_pts, fill=(24, 56, 86, 220), outline=(*GOLD_BRIGHT, 240))
        for p_top, p_bot in zip(top_pts, bot_pts):
            d.line([p_top, p_bot], fill=(*CYAN, 230), width=3)
        # Scan beam across 3D prism
        scan_y = cy - 125 + ((t * 150.0) % 250.0)
        d.line([(cx - 205, scan_y), (cx + 205, scan_y)], fill=(*GOLD_BRIGHT, 205), width=4)

        # 4 Quadrant Callout Cards pinned around centerpiece (strictly inside panel)
        quads = [
            (94,  345, (425, 575), CYAN),
            (556, 345, (655, 575), GOLD),
            (94,  880, (425, 730), EMERALD),
            (556, 880, (655, 730), GOLD_BRIGHT),
        ]
        for idx, ((qx, qy, anchor, qcol), qtext) in enumerate(zip(quads, L["s4_quads"])):
            qu = anim.ease_out(min(1.0, max(0.0, fill_u * 1.4 - idx * 0.14)))
            qw, qh = 430, 96
            q_anchor_x = qx + qw // 2
            q_anchor_y = qy + qh if idx < 2 else qy
            if qu > 0.05:
                d.line([(q_anchor_x, q_anchor_y), anchor], fill=(*qcol, int(205 * qu)), width=3)
                d.ellipse([anchor[0] - 8, anchor[1] - 8, anchor[0] + 8, anchor[1] + 8], fill=(*qcol, int(255 * qu)))
                draw_panel(d, qx, qy, qx + qw, qy + qh, pop=qu, fill_rgb=BG_CARD, out_rgb=qcol, radius=16)
                f_q, tw_q = fit_font_text(d, qtext, qw - 28, 22, 15)
                d.text((qx + (qw - tw_q) / 2, qy + 34), qtext, font=f_q, fill=(*WHITE, int(252 * qu)))

        draw_lower_card(ov, L["s4_low_t"], L["s4_low_s"], CYAN, tau, prog=fill_u)

    # -----------------------------------------------------------------------
    # SCENE 5: Ad Economics Duel — Static CTR 0.6% vs 3D Motion CTR 3.8%
    # -----------------------------------------------------------------------
    elif si == 5:
        # Top Static Card (y=260..615)
        draw_panel(d, 78, 260, 1002, 615, pop=pop, fill_rgb=BG_RED, out_rgb=CORAL, radius=22)
        d.text((120, 290), L["s5_bad_t"], font=rmod.font(28), fill=(*CORAL, 245))
        d.text((120, 342), L["s5_bad_m"], font=rmod.font(46), fill=(*WHITE, 235))
        d.rounded_rectangle([120, 422, 960, 466], radius=12, fill=(56, 22, 26, 230))
        bad_w = int(832 * (0.14 * min(1.0, fill_u * 1.6)))
        d.rounded_rectangle([124, 426, 124 + max(16, bad_w), 462], radius=10, fill=(*CORAL, 235))
        draw_panel(d, 120, 496, 960, 582, pop=pop, fill_rgb=(54, 20, 24), out_rgb=CORAL, radius=14)
        f_sb, tw_sb = fit_font_text(d, L["s5_bad_b"], 800, 26, 18)
        d.text(((W - tw_sb) / 2, 524), L["s5_bad_b"], font=f_sb, fill=(255, 152, 140, 250))

        # Bottom Dynamic 3D Card (y=655..1060)
        draw_panel(d, 78, 655, 1002, 1060, pop=pop, fill_rgb=(12, 32, 36), out_rgb=EMERALD, radius=22)
        d.text((120, 686), L["s5_good_t"], font=rmod.font(28), fill=(*EMERALD, 250))
        d.text((120, 738), L["s5_good_m"], font=rmod.font(48), fill=(*GOLD_BRIGHT, 255))
        d.rounded_rectangle([120, 822, 960, 868], radius=12, fill=(20, 48, 42, 230))
        good_w = int(832 * (0.90 * fill_u))
        d.rounded_rectangle([124, 826, 124 + max(18, good_w), 864], radius=10, fill=(*EMERALD, 245))
        draw_panel(d, 120, 902, 960, 1020, pop=pop, fill_rgb=(20, 46, 34), out_rgb=GOLD, radius=16)
        f_sg, tw_sg = fit_font_text(d, L["s5_good_b"], 800, 32, 20)
        d.text(((W - tw_sg) / 2, 942), L["s5_good_b"], font=f_sg, fill=(*GOLD_BRIGHT, 255))

        draw_lower_card(ov, L["s5_low_t"], L["s5_low_s"], EMERALD, tau, prog=fill_u)

    # -----------------------------------------------------------------------
    # SCENE 6: Niche #3 Vox Editorial B2B Funnel + Exponential ROI Curve
    # -----------------------------------------------------------------------
    elif si == 6:
        widths = (880, 750, 625, 505)
        cols_f = (CYAN, (92, 206, 232), EMERALD, GOLD)
        for idx, (fw, fcol, flbl) in enumerate(zip(widths, cols_f, L["s6_funnel"])):
            fu = anim.ease_out(min(1.0, max(0.0, fill_u * 1.4 - idx * 0.14)))
            fy = 264 + idx * 124
            fh = 96
            fx0 = (W - fw) // 2
            draw_panel(d, fx0, fy, fx0 + fw, fy + fh, pop=fu, fill_rgb=BG_CARD, out_rgb=fcol, radius=16)
            ftx, ftw = fit_font_text(d, flbl, fw - 36, 27, 18)
            d.text((540 - ftw / 2, fy + 31), flbl, font=ftx, fill=(*(GOLD_BRIGHT if idx == 3 else WHITE), int(252 * fu)))
            if idx < 3:
                d.line([(526, fy + fh + 6), (540, fy + fh + 20), (554, fy + fh + 6)], fill=(*GOLD, int(220 * fu)), width=4)

        # Exponential curve card below funnel (y=776..1055)
        draw_panel(d, 78, 776, 1002, 1055, pop=pop, fill_rgb=(12, 26, 36), out_rgb=GOLD, radius=20)
        f_r, tw_r = fit_font_text(d, L["s6_roi"], 860, 29, 20)
        d.text(((W - tw_r) / 2, 796), L["s6_roi"], font=f_r, fill=(*GOLD_BRIGHT, 255))
        pts_e = []
        for k in range(36):
            ux = k / 35.0
            px = 130 + ux * 820
            py = 1020 - (ux ** 1.85) * 168
            pts_e.append((px, py))
        cnt_e = max(2, int(len(pts_e) * fill_u))
        d.line(pts_e[:cnt_e], fill=(*EMERALD, 250), width=8, joint="curve")
        ex, ey = pts_e[min(len(pts_e) - 1, cnt_e - 1)]
        d.ellipse([ex - 11, ey - 11, ex + 11, ey + 11], fill=(*GOLD_BRIGHT, 255))

        draw_lower_card(ov, L["s6_low_t"], L["s6_low_s"], GOLD, tau, prog=fill_u)

    # -----------------------------------------------------------------------
    # SCENE 7: 3-Language Market Scaling Matrix (KZ • RU • EN)
    # -----------------------------------------------------------------------
    elif si == 7:
        draw_panel(d, 120, 262, 960, 366, pop=pop, fill_rgb=(26, 22, 12), out_rgb=GOLD, radius=20)
        f_cr, tw_cr = fit_font_text(d, L["s7_core"], 800, 32, 22)
        d.text(((W - tw_cr) / 2, 296), L["s7_core"], font=f_cr, fill=(*GOLD_BRIGHT, 255))

        col_w, gap = 286, 24
        x_start = (W - col_w * 3 - gap * 2) // 2
        col_colors = (CYAN, GOLD, EMERALD)
        for idx, ((code, market, sub1, sub2), ccol) in enumerate(zip(L["s7_cols"], col_colors)):
            cu = anim.ease_out(min(1.0, max(0.0, fill_u * 1.4 - idx * 0.14)))
            cx0 = x_start + idx * (col_w + gap)
            mid_x = cx0 + col_w // 2
            # Branching conduit line from core
            d.line([(540, 366), (540, 412), (mid_x, 412), (mid_x, 466)], fill=(*ccol, int(215 * cu)), width=4)
            draw_panel(d, cx0, 466, cx0 + col_w, 916, pop=cu, fill_rgb=BG_CARD, out_rgb=ccol, radius=20)
            # Language pill tag at top of column
            draw_panel(d, mid_x - 62, 492, mid_x + 62, 562, pop=cu, fill_rgb=(20, 34, 50), out_rgb=ccol, radius=14)
            f_cd = rmod.font(36)
            cdw = d.textlength(code, font=f_cd)
            d.text((mid_x - cdw / 2, 504), code, font=f_cd, fill=(*ccol, 255))

            f_mk, t_mk = fit_font_text(d, market, col_w - 28, 26, 17)
            d.text((mid_x - t_mk / 2, 608), market, font=f_mk, fill=(*WHITE, 255))
            d.line([(cx0 + 26, 668), (cx0 + col_w - 26, 668)], fill=(*ccol, 110), width=2)
            f_s1, t_s1 = fit_font_text(d, sub1, col_w - 24, 21, 15)
            d.text((mid_x - t_s1 / 2, 704), sub1, font=f_s1, fill=(*MUTED, 240))
            draw_panel(d, cx0 + 18, 784, cx0 + col_w - 18, 882, pop=cu, fill_rgb=(16, 30, 44), out_rgb=ccol, radius=14)
            f_s2, t_s2 = fit_font_text(d, sub2, col_w - 52, 20, 14)
            d.text((mid_x - t_s2 / 2, 820), sub2, font=f_s2, fill=(*ccol, 255))

        draw_panel(d, 78, 944, 1002, 1044, pop=pop, fill_rgb=(14, 34, 30), out_rgb=EMERALD, radius=18)
        f_b7, tw_b7 = fit_font_text(d, L["s7_bot"], 880, 27, 18)
        d.text(((W - tw_b7) / 2, 978), L["s7_bot"], font=f_b7, fill=(*EMERALD, 255))

        draw_lower_card(ov, L["s7_low_t"], L["s7_low_s"], GOLD, tau, prog=fill_u)

    # -----------------------------------------------------------------------
    # SCENE 8: Turnkey Deliverables Checklist
    # -----------------------------------------------------------------------
    elif si == 8:
        cols_c = (GOLD, CYAN, EMERALD, GOLD_BRIGHT)
        for idx, ((title_c, sub_c), ccol) in enumerate(zip(L["s8_checks"], cols_c)):
            cu = anim.ease_out(min(1.0, max(0.0, fill_u * 1.45 - idx * 0.14)))
            ry = 268 + idx * 194
            rh = 166
            draw_panel(d, 74, ry, 1006, ry + rh, pop=cu, fill_rgb=BG_CARD, out_rgb=ccol, radius=20)
            draw_vector_check(d, 148, ry + rh // 2, 32, (*ccol, int(252 * cu)))
            ft1, _ = fit_font_text(d, title_c, 770, 30, 20)
            ft2, _ = fit_font_text(d, sub_c, 770, 22, 15)
            d.text((208, ry + 36), title_c, font=ft1, fill=(*ccol, int(255 * cu)))
            d.text((208, ry + 94), sub_c, font=ft2, fill=(*WHITE, int(238 * cu)))

        draw_lower_card(ov, L["s8_low_t"], L["s8_low_s"], EMERALD, tau, prog=fill_u)

    # -----------------------------------------------------------------------
    # SCENE 9: Direct CTA Offer + Rising Seamless Loop Chevrons
    # -----------------------------------------------------------------------
    else:
        # Rising golden chevrons strictly in upper stage (y=260..470) pointing smoothly into CTA / Loop
        for idx in range(4):
            phase = (t * 0.95 + idx * 0.25) % 1.0
            cy_ch = 470 - phase * 200
            al = int(190 * math.sin(math.pi * phase))
            hw = 155 + idx * 24
            d.line([(540 - hw, cy_ch + 28), (540, cy_ch), (540 + hw, cy_ch + 28)], fill=(*GOLD, al), width=7, joint="curve")

        # Massive pulsing gold CTA card (y=505..875)
        pulse_pad = int(6 * math.sin(t * 5.2))
        cx0, cy0, cx1, cy1 = 68 - pulse_pad, 505, 1012 + pulse_pad, 875
        draw_panel(d, cx0, cy0, cx1, cy1, pop=pop, fill_rgb=(24, 22, 12), out_rgb=GOLD_BRIGHT, radius=26, width=4)

        f_tag, tw_tag = fit_font_text(d, L["s9_tag"], 860, 28, 19)
        d.text(((W - tw_tag) / 2, cy0 + 40), L["s9_tag"], font=f_tag, fill=(*CYAN, 250))

        # Inner bright button highlighting the exact keyword DM action
        draw_panel(d, cx0 + 46, cy0 + 104, cx1 - 46, cy0 + 244, pop=pop, fill_rgb=(248, 202, 84), out_rgb=WHITE, radius=20)
        f_cta, tw_cta = fit_font_text(d, L["s9_cta"], (cx1 - cx0) - 130, 44, 24)
        d.text(((W - tw_cta) / 2, cy0 + 148), L["s9_cta"], font=f_cta, fill=(14, 18, 26, 255))

        f_sub, tw_sub = fit_font_text(d, L["s9_sub"], (cx1 - cx0) - 80, 23, 15)
        d.text(((W - tw_sub) / 2, cy0 + 288), L["s9_sub"], font=f_sub, fill=(*WHITE, 248))

        draw_panel(d, 110, 916, 970, 1020, pop=pop, fill_rgb=(12, 28, 36), out_rgb=EMERALD, radius=18)
        f_bot, tw_bot = fit_font_text(d, L["s9_bot"], 800, 28, 19)
        d.text(((W - tw_bot) / 2, 950), L["s9_bot"], font=f_bot, fill=(*EMERALD, 255))

        draw_lower_card(ov, L["s9_low_t"], L["s9_low_s"], GOLD_BRIGHT, tau, prog=fill_u)

    draw_particles_studio(ov, t, seed=300 + si, count=18)
    bg.alpha_composite(ov)
    return bg.convert("RGB")


def draw_hud(frame_pil: Image.Image, lang: str, si: int, tau: float):
    L = CONTENT[lang]
    top_title, sub_callout, active_pillar = L["banners"][si]
    pillars = L["pillars"]

    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)

    alpha_in = min(1.0, max(0.0, tau / 0.20))
    bx_a = int(round(220 * alpha_in))
    tx_a = int(round(252 * alpha_in))

    f_top = rmod.font(30)
    f_sub = rmod.font(24)
    f_pil = rmod.font(24)

    d.rounded_rectangle([54, 68, W - 54, 138], radius=20, fill=(10, 16, 28, bx_a), outline=(*GOLD, int(235 * alpha_in)), width=2)
    tw = d.textlength(top_title, font=f_top)
    d.text(((W - tw) / 2, 85), top_title, font=f_top, fill=(*GOLD, tx_a))

    cw = d.textlength(sub_callout, font=f_sub)
    pw = min(W - 84, int(cw + 54))
    px0 = (W - pw) // 2
    d.rounded_rectangle([px0, 150, px0 + pw, 206], radius=15, fill=(12, 28, 38, int(212 * alpha_in)), outline=(*CYAN, int(215 * alpha_in)), width=2)
    d.text(((W - cw) / 2, 164), sub_callout, font=f_sub, fill=(*WHITE, tx_a))

    bar_y0, bar_y1 = 1628, 1700
    d.rounded_rectangle([42, bar_y0, W - 42, bar_y1], radius=18, fill=(10, 16, 26, 218), outline=(145, 168, 184, 110), width=2)
    slot_w = (W - 104) / len(pillars)
    for k, label in enumerate(pillars):
        sx0 = int(52 + k * slot_w)
        sx1 = int(sx0 + slot_w - 8)
        is_active = (k == active_pillar)
        fill_p = (*GOLD, 240) if is_active else (22, 32, 48, 180)
        text_p = (14, 18, 26, 255) if is_active else (208, 218, 228, 215)
        d.rounded_rectangle([sx0, bar_y0 + 10, sx1, bar_y1 - 10], radius=12, fill=fill_p)
        lw = d.textlength(label, font=f_pil)
        d.text((sx0 + (sx1 - sx0 - lw) / 2, bar_y0 + 22), label, font=f_pil, fill=text_p)

    frame_pil.alpha_composite(overlay)


def compose_single_frame(
    lang: str, si: int, u: float, tau: float, sd: float, t: float,
    vig: np.ndarray, sub_words: list[str] | None = None,
) -> Image.Image:
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
    verify_all_texts()
    qa_dir = PROD / "build_b2b01" / "qa"
    qa_dir.mkdir(parents=True, exist_ok=True)
    vig = rmod.vignette()[..., None]
    cases = [
        ("ru", 0, 0.72, 3.2, 4.6, 3.2, ["бизнес-видео", "пролистывают", "за", "секунду?"]),
        ("ru", 1, 0.78, 3.6, 5.2, 8.6, ["реклама", "сливает", "бюджет"]),
        ("ru", 2, 0.78, 3.8, 5.4, 14.0, ["живую", "карту", "района"]),
        ("ru", 3, 0.78, 3.8, 5.4, 19.5, ["рассрочки", "прямо", "на", "экране"]),
        ("ru", 4, 0.78, 3.8, 5.4, 24.8, ["главные", "плюсы", "мгновенно"]),
        ("ru", 5, 0.78, 3.8, 5.4, 30.2, ["стоимость", "заявки", "падает"]),
        ("ru", 6, 0.78, 3.8, 5.4, 35.6, ["поток", "тёплых", "заявок"]),
        ("ru", 7, 0.78, 3.8, 5.4, 41.0, ["казахский,", "русский", "и", "английский"]),
        ("ru", 8, 0.82, 4.0, 5.4, 46.5, ["сценарий,", "3D-карты,", "графики"]),
        ("ru", 9, 0.76, 3.4, 4.8, 51.0, ["слово", "«ВИДЕО»", "в", "Дайрект"]),
        ("kz", 2, 0.78, 3.8, 5.4, 14.0, ["тірі", "аудан", "картасына"]),
        ("kz", 9, 0.76, 3.4, 4.8, 51.0, ["Дайректке", "«ВИДЕО»", "деп"]),
        ("en", 4, 0.78, 3.8, 5.4, 24.8, ["spotlight", "key", "features"]),
        ("en", 9, 0.76, 3.4, 4.8, 51.0, ["the", "word", "\"VIDEO\""]),
    ]
    for lang, si, u, tau, sd, t, words in cases:
        if lang not in langs:
            continue
        im = compose_single_frame(lang, si, u, tau, sd, t, vig, sub_words=words)
        out_p = qa_dir / f"pre_{lang}_s{si:02d}.jpg"
        im.convert("RGB").save(out_p, "JPEG", quality=92)
        print(f"[B2B-01-PREVIEW] saved {out_p}")


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
                print(f"[B2B-01:{lang.upper()}] rendered {fi + 1}/{total_frames} frames ({t:.1f}s/{dur:.1f}s)", flush=True)

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

    verify_all_texts()
    out_dir = ROOT / "output"
    out_dir.mkdir(parents=True, exist_ok=True)

    for lang in langs:
        t_start = time.time()
        build_dir = PROD / "build_b2b01" / lang
        build_dir.mkdir(parents=True, exist_ok=True)
        out_mp4 = out_dir / VOICE_CFG[lang]["out_file"]

        print(f"[B2B-01:{lang.upper()}] Synthesizing narration...")
        voice_mono, timeline, words_all, dur = synthesize_lang(lang, build_dir)
        print(f"[B2B-01:{lang.upper()}] Narration ready: {len(timeline)} scenes, {dur:.2f}s, {len(words_all)} words.")

        print(f"[B2B-01:{lang.upper()}] Mixing studio Halal SFX + a cappella (-14 LUFS)...")
        mix_wav = build_b2b_audio(lang, build_dir, voice_mono, timeline, dur)

        print(f"[B2B-01:{lang.upper()}] Rendering 1080x1920 @ 30fps -> {out_mp4.name} ...")
        render_lang_video(lang, build_dir, mix_wav, timeline, words_all, dur, out_mp4)
        mb = out_mp4.stat().st_size / (1024 * 1024)
        print(f"[B2B-01:{lang.upper()}] DONE in {time.time() - t_start:.1f}s: {out_mp4} ({mb:.2f} MB, {dur:.2f}s)")


if __name__ == "__main__":
    main()
