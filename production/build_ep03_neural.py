#!/usr/bin/env python3
"""Episode 3 Builder: 'Zheti Zhargy' (1680-1715) — RU / KZ / EN
Rigid sub-pixel cinematic camera + neural studio narration + Halal SFX & A cappella.
100% free of jelly warping, close-up faces, or musical instruments.
"""

import asyncio
import math
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import edge_tts
import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path("/Users/market/antigravity/Video")
PROD = ROOT / "production"
SCENES_DIR = ROOT / "scenes_ep03"
BUILD = PROD / "build_ep03"
OUT_DIR = ROOT / "output"
BIN_DIR = PROD / "build_ep02" / "_bin"

if str(PROD) not in sys.path:
    sys.path.insert(0, str(PROD))

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
if BIN_DIR.exists():
    os.environ["PATH"] = f"{BIN_DIR}:{os.environ.get('PATH', '')}"

import render as rmod  # noqa: E402
import sfx as smod     # noqa: E402

W, H, FPS = rmod.W, rmod.H, rmod.FPS  # 1080, 1920, 30
SR = smod.SR                          # 48000

VOICE_CFG = {
    "ru": {"voice": "ru-RU-DmitryNeural", "fallback": "en-US-BrianMultilingualNeural", "rate": "-3%", "pitch": "-4Hz"},
    "kz": {"voice": "kk-KZ-DauletNeural", "fallback": "kk-KZ-AigulNeural", "rate": "-2%", "pitch": "-2Hz"},
    "en": {"voice": "en-US-BrianMultilingualNeural", "fallback": "en-US-AndrewMultilingualNeural", "rate": "-2%", "pitch": "-3Hz"},
}

OUT_FILES = {
    "ru": "EP03_Zheti_Zhargy_Shorts_RU.mp4",
    "kz": "EP03_Zheti_Zhargy_Shorts_KZ.mp4",
    "en": "EP03_Zheti_Zhargy_Shorts_EN.mp4",
}

VOICE_FX = (
    "highpass=f=75,"
    "equalizer=f=150:t=q:w=1.1:g=2.5,"
    "equalizer=f=320:t=q:w=1.2:g=-1.5,"
    "equalizer=f=3200:t=q:w=1.3:g=2.0,"
    "equalizer=f=6800:t=q:w=1.5:g=-1.8,"
    "acompressor=threshold=-16dB:ratio=2.4:attack=12:release=140:makeup=1.5,"
    "alimiter=limit=-1.2dB:attack=4:release=50"
)

# 16 Scenes matching zheti_zhargy_viral_script.md
EP03_SCRIPT = {
    "ru": [
        "Ни одной тюрьмы, ни одного детского дома и почти нулевая преступность на земле размером с пол-Европы! Как работал забытый кодекс Великой Степи?",
        "Конец семнадцатого века. Пока в мире возводили каменные казематы, в Казахской степи действовал совершенно иной порядок.",
        "На холме Культобе мудрый Тауке-хан и три великих бия — Толе би, Казыбек би и Айтеке би — утвердили знаменитый свод «Жеты Жаргы».",
        "Семь великих уложений превратили кочевую страну без единой крепостной стены в общество редкой справедливости и взаимного доверия.",
        "Секрет первый — народный суд биев! Судьёй становился не богач и не чиновник по блату, а человек безупречной честности и глубоких знаний.",
        "Приговор выносили открыто перед всем народом, поэтому главный контроль в степи держала не решётка, а живая совесть и сила слова.",
        "Секрет второй — закон «Кун». Чтобы остановить вековую кровную месть между родами, виновный искупал вину тяжёлым возмещением и примирением.",
        "Семья пострадавшего получала реальную опору и защиту, а оба рода расходились с миром — без многолетних распрей и новых жертв.",
        "Секрет третий — «Асар» и «Жылу»! Если в семье погибал кормилец или случалась беда, весь род собирался вместе на рассвете.",
        "За один день людям бесплатно ставили новую юрту и отдавали скот на прокорм — поэтому в степи не бросали ни вдов, ни сирот, ни стариков.",
        "Секрет четвёртый — священный закон гостеприимства «Конакасы». Любой уставший путник ночью имел законное право на тёплый кров и еду бесплатно.",
        "В огромной степи без постоялых дворов никто не замерзал в дороге, ведь каждый дом встречал странника как дорогого гостя.",
        "И даже над самим ханом стояла совесть народа — бесстрашные мудрецы жырау, имевшие право говорить правителю любую правду в лицо.",
        "Опора на исламскую этику милосердия, чистую совесть и братское плечо превратила степной закон в удивительную цивилизацию порядка.",
        "По милости Всевышнего, предки доказали всему миру: крепче любой каменной темницы страну хранят справедливость и единство!",
        "И каждый раз, глядя на эти забытые ржавые цепи в высокой траве, понимаешь, почему в Великой Степи...",
    ],
    "kz": [
        "Бүкіл Еуропаның жартысындай ұлан-ғайыр далада бірде-бір түрме де, жетімдер үйі де болмаған! Ұлы Даланың бұл заңы қалай жұмыс істеді?",
        "Он жетінші ғасырдың соңы. Әлемде тас зындандар мен түрмелер салынып жатқанда, Қазақ даласында мүлде бөлек жүйе өмір сүрді.",
        "Күлтөбе басында дана Тәуке хан мен үш ұлы би — Төле би, Қазыбек би және Әйтеке би — тарихи «Жеті Жарғы» заңдар жинағын бекітті.",
        "Жеті тараудан тұрған бұл Ұлы Заң бірде-бір түрмесіз-ақ елді әділдік пен өзара сенімнің биігіне көтерді.",
        "Бірінші құпия — Билер соты! Би болу үшін байлық емес, халық мойындаған мінсіз ар-ождан, шешендік пен терең білім жеткілікті еді.",
        "Билік бүкіл жұрттың алдында ашық айтылатын. Сондықтан елді темір тор емес, сөз құдіреті мен ар-намыс тәртіпке салды.",
        "Екінші құпия — Құн заңы! Ғасырларға созылатын қанды кекті тоқтату үшін айыпты тарап ауыр құн төлеп, ел алдында татуласатын.",
        "Жәбір көрген отбасы нақты қолдау мен өтемақы алып, екі жақ жаңа қантөгіссіз, тату-тәтті тарасатын.",
        "Үшінші құпия — Асар мен Жылу! Бір отбасы асыраушысынан айырылса не жұтқа ұшыраса, бүкіл ауыл таң атпастан көмекке жиналатын.",
        "Жұрт бір күнде тегін киіз үй тігіп, сауын мал бөліп беретін. Сондықтан далада жетім де, жесір де, қарт та қараусыз қалмаған.",
        "Төртінші құпия — Құдайы қонақ дәстүрі! Түн ішінде келген кез келген жолаушы еш ақысыз жылы орын мен ыстық асқа заңды түрде құқылы еді.",
        "Қонақүйсіз ұлы далада ешбір жолаушы далада қалмаған, себебі әр шаңырақ жолаушыны Құдайы қонақ деп төріне оздырған.",
        "Тіпті ханның өзінен биік халық ар-ожданы тұрды: дана жыраулар билеушіге бүкіл шындықты тайсалмай бетіне айта алатын.",
        "Исламдағы мейірім мен әділдік қағидаларына сүйенген бұл жүйе дала өмірін ғажайып өркениет пен тәртіп үлгісіне айналдырды.",
        "Жаратқанның қолдауымен бабаларымыз бүкіл әлемге дәлелдеді: елді тас қамалдан гөрі әділдік пен бірлік мықты сақтайды!",
        "Сондықтан шөп басқан мына тот басқан кісендерге қарап, Ұлы Далада неге...",
    ],
    "en": [
        "Zero stone prisons, zero orphanages, and remarkably low crime across a landmass half the size of Europe! How did this forgotten steppe legal code work?",
        "The late seventeenth century. While stone dungeons multiplied across the Old World, a completely different social order governed the Kazakh Steppe.",
        "Atop Kultobe hill, wise Tauke Khan and the three master judges — Tole Bi, Kazybek Bi, and Aiteke Bi — forged the historic code of Zheti Zhargy.",
        "Seven foundational statutes transformed a vast nomadic realm without prison walls into a society of fierce honor and trust.",
        "Secret number one — the People's Court of Biys! Judges were never bought or appointed by wealth; people chose only minds famed for integrity and wisdom.",
        "Trials took place in full view of the community — so what kept the peace across the plains was not iron bars, but public conscience and honor.",
        "Secret number two — the law of Qun! To halt endless blood feuds before they began, offenses were settled through heavy restitution and public reconciliation.",
        "The injured family gained real economic protection, and rival clans parted in lasting peace without cycles of revenge.",
        "Secret number three — Asar and Zhylu! Whenever a household lost its breadwinner or was struck by disaster, the entire clan gathered at dawn.",
        "In a single day they raised a new yurt and gifted livestock freely — so no orphan, widow, or elder was ever abandoned to a shelter.",
        "Secret number four — the sacred law of Qonaqasy! Any weary stranger riding in at night held an unbreakable legal right to warm shelter and food.",
        "Across endless grasslands with zero roadside inns, no traveler perished in the cold, because every threshold welcomed strangers with honor.",
        "Even the Khan answered to public conscience — fearless steppe sage-orators, the Zhyrau, held the sacred right to speak hard truth straight to the ruler.",
        "Grounded in Islamic ethics of mercy, accountability, and kinship, Steppe law forged a civilization of quiet strength and dignity.",
        "By the grace of the Almighty, our ancestors proved to history: justice and unity guard a nation stronger than any fortress wall!",
        "And every time you look at those forgotten rusted chains in the tall steppe grass, you realize why on the Great Steppe...",
    ],
}

# Rigid sub-pixel Ken Burns specs: (z0, z1, x0, y0, x1, y1, particle_mode, dissolve_in)
SCENE_CAM = [
    (1.00, 1.12, 0.50, 0.53, 0.51, 0.48, "dust_gold", False),  # 01 Open gate onto dawn steppe
    (1.00, 1.13, 0.50, 0.47, 0.50, 0.53, "dust_gold", True),   # 02 Turkestan panorama
    (1.01, 1.12, 0.50, 0.55, 0.50, 0.48, "dust_gold", True),   # 03 Tauke Khan & 3 Biys
    (1.05, 1.15, 0.46, 0.44, 0.53, 0.55, "embers",    True),   # 04 Illuminated scroll & lamp
    (1.00, 1.12, 0.47, 0.53, 0.52, 0.49, "dust_gold", True),   # 05 Elder hands, staff & scales
    (1.02, 1.12, 0.50, 0.57, 0.50, 0.47, "embers",    True),   # 06 Circle of Biys
    (1.00, 1.11, 0.49, 0.52, 0.51, 0.48, "embers",    True),   # 07 Hands clasped over fire
    (1.06, 1.14, 0.45, 0.55, 0.55, 0.49, "dust_gold", True),   # 08 Saryarka valley & herd
    (1.02, 1.14, 0.50, 0.56, 0.50, 0.44, "dust_gold", True),   # 09 Raising shanyrak (Asar)
    (1.00, 1.13, 0.48, 0.55, 0.53, 0.49, "snow",      True),   # 10 Riders bringing livestock
    (1.03, 1.12, 0.50, 0.44, 0.50, 0.55, "stars",     True),   # 11 Night traveler & open yurt
    (1.03, 1.13, 0.45, 0.48, 0.53, 0.53, "embers",    True),   # 12 Pouring kumys & baursaks
    (1.00, 1.12, 0.50, 0.46, 0.50, 0.53, "dust_gold", True),   # 13 Carved staff & council
    (1.12, 1.00, 0.50, 0.47, 0.50, 0.51, "dust_gold", True),   # 14 Yasawi portal pull-back
    (1.01, 1.13, 0.48, 0.56, 0.53, 0.43, "dust_gold", True),   # 15 Steppe banners & eagle
    (1.10, 1.00, 0.50, 0.62, 0.50, 0.49, "dust_gold", True),   # 16 Rusted chains -> loop
]

HUD_META = {
    "ru": {
        "banners": [
            ("1680–1715 • ТАЙНА ВЕЛИКОЙ СТЕПИ", "ТЮРЕМ: 0  •  СИРОТСКИХ ДОМОВ: 0", -1),
            ("СТЕПНАЯ ЦИВИЛИЗАЦИЯ", "АЛЬТЕРНАТИВА КАЗЕМАТАМ", -1),
            ("СОВЕТ В КУЛЬТОБЕ", "ТАУКЕ-ХАН  +  ТОЛЕ • КАЗЫБЕК • АЙТЕКЕ БИ", -1),
            ("СВОД «ЖЕТЫ ЖАРГЫ»", "7 ОСНОВОПОЛАГАЮЩИХ УЛОЖЕНИЙ", -1),
            ("СЕКРЕТ №1 • СУД БИЕВ", "ВЛАСТЬ СОВЕСТИ ВМЕСТО ЧИНОВ И ВЗЯТОК", 0),
            ("СЕКРЕТ №1 • ГЛАСНОСТЬ", "ОТКРЫТЫЙ СУД ПЕРЕД ВСЕМ АУЛОМ", 0),
            ("СЕКРЕТ №2 • ЗАКОН «КУН»", "КРОВНАЯ МЕСТЬ ✕  ->  ПРИМИРЕНИЕ", 1),
            ("СЕКРЕТ №2 • ЗАЩИТА СЕМЬИ", "ОПОРА ВМЕСТО БЕСКОНЕЧНОЙ ВРАЖДЫ", 1),
            ("СЕКРЕТ №3 • «АСАР» И «ЖЫЛУ»", "НА РАССВЕТЕ — ВСЕМ РОДОМ НА ПОМОЩЬ", 2),
            ("СЕКРЕТ №3 • СОЦИАЛЬНЫЙ ЩИТ", "НОВАЯ ЮРТА И СКОТ — БЕЗ ПРИЮТОВ", 2),
            ("СЕКРЕТ №4 • «КОНАКАСЫ»", "ЗАКОННОЕ ПРАВО ПУТНИКА НА КРОВ", 3),
            ("СЕКРЕТ №4 • ТЕПЛО СТЕПИ", "КАЖДЫЙ ОЧАГ — ОПОРА В ДОРОГЕ", 3),
            ("СОВЕСТЬ ВЫШЕ ВЛАСТИ", "ЖЫРАУ ГОВОРИЛ ПРАВДУ САМОМУ ХАНУ", -1),
            ("ДУХОВНЫЙ ФУНДАМЕНТ", "ИСЛАМСКАЯ ЭТИКА МИЛОСЕРДИЯ И ЧЕСТИ", -1),
            ("ПО МИЛОСТИ ВСЕВЫШНЕГО", "СПРАВЕДЛИВОСТЬ КРЕПЧЕ КАМЕННЫХ СТЕН", -1),
            ("БЕСШОВНАЯ ПЕТЛЯ", "ЗАБЫТЫЕ ЦЕПИ ВЕЛИКОЙ СТЕПИ...", -1),
        ],
        "pillars": ["1. БИИ", "2. КУН", "3. АСАР", "4. КОНАКАСЫ"],
    },
    "kz": {
        "banners": [
            ("1680–1715 • ҰЛЫ ДАЛА ҚҰПИЯСЫ", "ТҮРМЕ: 0  •  ЖЕТІМДЕР ҮЙІ: 0", -1),
            ("ДАЛА ӨРКЕНИЕТІ", "ТАС ЗЫНДАНСЫЗ ТӘРТІП ЖҮЙЕСІ", -1),
            ("КҮЛТӨБЕ КЕҢЕСІ", "ТӘУКЕ ХАН  +  ТӨЛЕ • ҚАЗЫБЕК • ӘЙТЕКЕ БИ", -1),
            ("«ЖЕТІ ЖАРҒЫ» ЖИНАҒЫ", "ӘДІЛДІК ПЕН СЕНІМНІҢ ЖЕТІ ТАРАУЫ", -1),
            ("1-ҚҰПИЯ • БИЛЕР СОТЫ", "БАЙЛЫҚ ЕМЕС — АР-ОЖДАН МЕН БІЛІМ", 0),
            ("1-ҚҰПИЯ • АШЫҚ БИЛІК", "ТЕМІР ТОР ЕМЕС — ХАЛЫҚ АЛДЫНДАҒЫ АР", 0),
            ("2-ҚҰПИЯ • ҚҰН ЗАҢЫ", "ҚАНДЫ КЕК ✕  ->  ӨТЕМАҚЫ ЖӘНЕ БІТІМ", 1),
            ("2-ҚҰПИЯ • ОТБАСЫ ҚОРҒАНЫ", "ҚОЛДАУ МЕН ТАТУЛЫҚ КЕПІЛІ", 1),
            ("3-ҚҰПИЯ • АСАР МЕН ЖЫЛУ", "ТАҢ АТПАСТАН БҮКІЛ АУЫЛ КӨМЕККЕ", 2),
            ("3-ҚҰПИЯ • ЕЛ ҚАМҚОРЛЫҒЫ", "БІР КҮНДЕ КИІЗ ҮЙ МЕН САУЫН МАЛ", 2),
            ("4-ҚҰПИЯ • ҚҰДАЙЫ ҚОНАҚ", "ЖОЛАУШЫНЫҢ ЖЫЛЫ ОРЫНҒА ЗАҢДЫ ҚҰҚЫ", 3),
            ("4-ҚҰПИЯ • ДАЛА МЕЙІРІМІ", "ӘР ШАҢЫРАҚ — ҚОНАҚҚА АШЫҚ ТӨР", 3),
            ("ХАННАН БИІК АР-ОЖДАН", "ЖЫРАУ ХАНҒА АШЫҚ ШЫНДЫҚ АЙТҚАН", -1),
            ("РУХАНИ ТІРЕК", "ИСЛАМ МЕЙІРІМІ МЕН ӘДІЛДІК НЕГІЗІ", -1),
            ("ЖАРАТҚАННЫҢ ҚОЛДАУЫМЕН", "ӘДІЛДІК ПЕН БІРЛІК — БАСТЫ ҚОРҒАН", -1),
            ("ТҰЙЫҚ ШЕҢБЕР", "ҰЛЫ ДАЛАНЫҢ ТОТ БАСҚАН КІСЕНДЕРІ...", -1),
        ],
        "pillars": ["1. БИЛЕР", "2. ҚҰН", "3. АСАР", "4. ҚОНАҚ"],
    },
    "en": {
        "banners": [
            ("1680–1715 • STEPPE SECRET", "PRISONS: 0  •  ORPHANAGES: 0", -1),
            ("NOMADIC ORDER", "AN ALTERNATIVE TO STONE DUNGEONS", -1),
            ("COUNCIL AT KULTOBE", "TAUKE KHAN + TOLE • KAZYBEK • AITEKE BI", -1),
            ("CODE OF ZHETI ZHARGY", "SEVEN PILLARS OF HONOR & TRUST", -1),
            ("SECRET #1 • COURT OF BIYS", "INTEGRITY & WISDOM OVER WEALTH", 0),
            ("SECRET #1 • OPEN JUSTICE", "PUBLIC CONSCIENCE INSTEAD OF BARS", 0),
            ("SECRET #2 • LAW OF QUN", "BLOOD FEUD ✕  ->  RESTITUTION & PEACE", 1),
            ("SECRET #2 • FAMILY SHIELD", "PROTECTION WITHOUT ENDLESS REVENGE", 1),
            ("SECRET #3 • ASAR & ZHYLU", "ENTIRE CLAN GATHERS AT DAWN", 2),
            ("SECRET #3 • SOCIAL SAFETY", "FREE YURT & HERD — ZERO SHELTERS", 2),
            ("SECRET #4 • QONAQASY", "SACRED LEGAL RIGHT TO WARM SHELTER", 3),
            ("SECRET #4 • OPEN HEARTHS", "EVERY THRESHOLD WELCOMED TRAVELERS", 3),
            ("ABOVE THE KHAN", "ZHYRAU SPOKE HARD TRUTH TO POWER", -1),
            ("SPIRITUAL ETHOS", "ISLAMIC MERCY & ACCOUNTABILITY", -1),
            ("BY THE ALMIGHTY'S GRACE", "JUSTICE STRONGER THAN FORTRESS WALLS", -1),
            ("SEAMLESS LOOP", "RUSTED CHAINS IN THE STEPPE GRASS...", -1),
        ],
        "pillars": ["1. BIYS", "2. QUN", "3. ASAR", "4. QONAQASY"],
    },
}


async def _synth_line_async(text: str, voice: str, rate: str, pitch: str, mp3_path: Path):
    comm = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch, boundary="WordBoundary")
    bounds = []
    with open(mp3_path, "wb") as f:
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                bounds.append({
                    "w": chunk["text"],
                    "t0": chunk["offset"] / 1e7,
                    "t1": (chunk["offset"] + chunk["duration"]) / 1e7,
                })
    return bounds


def synth_line_with_retry(text: str, lang: str, mp3_path: Path, wav_path: Path):
    import json
    bounds_path = wav_path.with_suffix(".json")
    if wav_path.exists() and wav_path.stat().st_size > 4000:
        if bounds_path.exists():
            return json.loads(bounds_path.read_text(encoding="utf-8"))
        return []

    cfg = VOICE_CFG[lang]
    voices_to_try = [cfg["voice"], cfg["fallback"]]
    bounds = []
    last_err = None
    for voice in voices_to_try:
        for attempt in range(4):
            try:
                if mp3_path.exists():
                    mp3_path.unlink()
                bounds = asyncio.run(_synth_line_async(text, voice, cfg["rate"], cfg["pitch"], mp3_path))
                if mp3_path.exists() and mp3_path.stat().st_size > 2000:
                    last_err = None
                    break
            except Exception as e:
                last_err = e
            time.sleep(0.6 * (attempt + 1))
        if last_err is None and mp3_path.exists() and mp3_path.stat().st_size > 2000:
            break
    if last_err is not None or not mp3_path.exists() or mp3_path.stat().st_size <= 2000:
        raise RuntimeError(f"TTS failed for [{lang}]: {last_err}")

    subprocess.run(
        [FFMPEG, "-y", "-i", str(mp3_path), "-af", VOICE_FX, "-ar", str(SR), "-ac", "1", "-c:a", "pcm_s16le", str(wav_path)],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    bounds_path.write_text(json.dumps(bounds, ensure_ascii=False), encoding="utf-8")
    return bounds


def read_wav_mono(path: Path) -> np.ndarray:
    import wave
    with wave.open(str(path), "rb") as wf:
        raw = wf.readframes(wf.getnframes())
    return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0


def trim_silence(x: np.ndarray, pad_s: float = 0.06, thresh: float = 0.008) -> np.ndarray:
    idx = np.where(np.abs(x) > thresh)[0]
    if len(idx) == 0:
        return x
    pad = int(pad_s * SR)
    i0 = max(0, int(idx[0]) - pad)
    i1 = min(len(x), int(idx[-1]) + int(0.10 * SR))
    out = x[i0:i1].copy()
    fi = min(int(0.015 * SR), len(out) // 4)
    fo = min(int(0.025 * SR), len(out) // 4)
    if fi > 0:
        out[:fi] *= np.linspace(0.0, 1.0, fi)
    if fo > 0:
        out[-fo:] *= np.linspace(1.0, 0.0, fo)
    return out


def align_words(text: str, raw_bounds: list, seg_start: float, speech_dur: float, scene_num: int):
    display_words = text.split()
    if raw_bounds and abs(len(raw_bounds) - len(display_words)) <= 2 and raw_bounds[-1]["t1"] > 0.2:
        # Map boundaries smoothly onto exact trimmed speech span
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
            wt1 = max(wt0 + 0.08, wt1)
            out.append({"w": w, "scene": scene_num, "t0": round(wt0, 3), "t1": round(wt1, 3)})
        return out

    # Syllable-weighted exact synchronization fallback
    vowels = set("аеёиоуыэюяәіңғүұқөһАЕЁИОУЫЭЮЯӘІҢҒҮҰҚӨҺaeiouyAEIOUY")
    weights = []
    for w in display_words:
        v = sum(1 for c in w if c in vowels)
        p = 1.6 if w[-1] in ".!?" else (0.9 if w[-1] in ",;—–:" else 0.0)
        weights.append(max(1.2, v * 1.0 + len(w) * 0.18 + p))
    tot = sum(weights)
    t_cur = seg_start
    out = []
    for w, wt in zip(display_words, weights):
        dur_w = speech_dur * (wt / tot)
        out.append({"w": w, "scene": scene_num, "t0": round(t_cur, 3), "t1": round(t_cur + dur_w, 3)})
        t_cur += dur_w
    return out


def build_voice_and_timeline(lang: str):
    ldir = BUILD / lang
    ldir.mkdir(parents=True, exist_ok=True)
    voice_wav = ldir / "voice.wav"

    lines = EP03_SCRIPT[lang]
    clips = []
    timeline = []
    words_all = []
    t_cursor = 0.0

    for si, text in enumerate(lines):
        mp3_p = ldir / f"line_{si:02d}.mp3"
        wav_p = ldir / f"line_{si:02d}.wav"
        bounds = synth_line_with_retry(text, lang, mp3_p, wav_p)
        raw = read_wav_mono(wav_p)
        spoken = trim_silence(raw)
        speech_dur = len(spoken) / SR
        pause_after = 0.14 if si == len(lines) - 1 else 0.30
        seg_dur = speech_dur + pause_after

        clips.append(spoken)
        clips.append(np.zeros(int(round(pause_after * SR)), dtype=np.float32))

        timeline.append({
            "scene": si + 1,
            "t0": round(t_cursor, 4),
            "t1": round(t_cursor + seg_dur, 4),
            "speech_dur": round(speech_dur, 4),
            "text": text,
        })
        words_all.extend(align_words(text, bounds, t_cursor, speech_dur, si + 1))
        t_cursor += seg_dur

    full_voice = np.concatenate(clips)
    # Write lossless PCM 16-bit WAV
    smod.write(str(voice_wav), smod.norm(full_voice, 0.92))
    return voice_wav, timeline, words_all, len(full_voice) / SR


def kumys_pour(rng, dur: float):
    """Synthesize liquid pouring + gentle splash inside wooden bowl (100% physical SFX)."""
    n = smod.n_(dur)
    t = smod.tt(dur)
    # Bubble resonant drops + aerated stream noise
    base = smod.bp(smod.white(rng, dur), 450, 2400)
    # Rising pitch resonance as bowl fills
    f0 = 320.0 + 480.0 * (t / max(0.1, dur)) ** 1.3
    bubbles = np.zeros(n, dtype=np.float64)
    for k in range(int(dur * 24)):
        tb = rng.uniform(0.05, max(0.1, dur - 0.15))
        ib = int(tb * SR)
        bd = rng.uniform(0.025, 0.06)
        bn = min(int(bd * SR), n - ib)
        if bn > 10:
            bt = np.arange(bn) / SR
            bf = f0[ib] * rng.uniform(0.85, 1.35)
            chirp = np.sin(2 * np.pi * (bf * bt + 650.0 * bt * bt)) * np.exp(-bt / (bd * 0.4))
            bubbles[ib:ib + bn] += chirp * rng.uniform(0.25, 0.65)
    env = np.sin(np.pi * np.clip(t / max(0.1, dur), 0, 1)) ** 0.6
    return smod.norm((base * 0.45 + bubbles * 0.75) * env, 0.65)


def chain_drop(rng, dur: float = 2.0):
    """Dull heavy iron chain links settling onto dirt (non-musical metal clank)."""
    out = np.zeros(smod.n_(dur), dtype=np.float64)
    clinks = smod.jingle(rng, 0.55, density=45) * 0.6
    th = smod.thud(rng) * 0.7
    smod.add(out, clinks, 0.05)
    smod.add(out, th, 0.22)
    return smod.norm(smod.bp(out, 180, 4200), 0.7)


def run_ep03_sfx(lang: str, voice_wav: Path, timeline: list, dur: float):
    ldir = BUILD / lang
    mix_raw = ldir / "mix_raw.wav"
    mix_wav = ldir / "mix.wav"

    v = smod.bp(read_wav_mono(voice_wav).astype(np.float64), 80, 11500)
    N = int(round(dur * SR))
    out = np.zeros((N, 2), dtype=np.float64)
    amb = np.zeros((N, 2), dtype=np.float64)
    rng = np.random.default_rng(707 + sum(ord(c) for c in lang))

    # Bed: vast peaceful Kazakh steppe dawn breeze
    bed = smod.wind(rng, dur, howl=0.14) * 0.30
    amb += smod.st(bed, 0.0)

    # Pure human male A cappella choir pads (strictly ZERO instruments)
    D3, F3, A3, C4, D4, E4, G3 = 146.83, 174.61, 220.00, 261.63, 293.66, 329.63, 196.00
    t_s = lambda si: timeline[si]["t0"]

    # Intro awe pad (01-04) — reverb takes mono and returns stereo (N_out, 2)
    t_a0, t_a1 = t_s(0), timeline[3]["t1"]
    smod.add(amb, smod.reverb(smod.vocal_pad(rng, t_a1 - t_a0, (D3, A3, D4, E4), "o", 4), wet=0.45, seed=11) * 0.38, t_a0)

    # Wise contemplation pad across Biys/Qun (05-08)
    t_b0, t_b1 = t_s(4), timeline[7]["t1"]
    smod.add(amb, smod.reverb(smod.vocal_pad(rng, t_b1 - t_b0, (G3, D3, A3, C4), "u", 3), wet=0.42, seed=22) * 0.34, t_b0)

    # Dawn fellowship Asar & Qonaqasy (09-12)
    t_c0, t_c1 = t_s(8), timeline[11]["t1"]
    smod.add(amb, smod.reverb(smod.vocal_pad(rng, t_c1 - t_c0, (F3, C4, D4, A3), "a", 4), wet=0.45, seed=33) * 0.36, t_c0)

    # Grand finale Zhyrau + Ethics + Glory (13-16)
    t_d0, t_d1 = t_s(12), dur
    smod.add(amb, smod.reverb(smod.vocal_pad(rng, t_d1 - t_d0, (D3, F3, A3, D4), "a", 5), wet=0.48, seed=44) * 0.44, t_d0)

    # Scene-accurate 100% physical SFX cues
    for si, seg in enumerate(timeline):
        t0 = seg["t0"]
        sd = seg["t1"] - seg["t0"]
        if si == 0:
            smod.add(amb, smod.reverb(chain_drop(rng, 2.0), wet=0.25, seed=101) * 0.55, t0 + 0.1)
            smod.add(amb, smod.st(smod.eagle(rng), 0.25) * 0.28, t0 + max(0.5, sd - 2.2))
        elif si == 1:
            smod.add(amb, smod.st(smod.wind(rng, sd, howl=0.25), -0.1) * 0.28, t0)
        elif si == 2:
            smod.add(amb, smod.reverb(smod.staff(rng), wet=0.30, seed=103) * 0.45, t0 + 0.15)
        elif si == 3:
            smod.add(amb, smod.st(smod.fire(rng, sd), 0.2) * 0.25, t0)
        elif si == 4:
            smod.add(amb, smod.reverb(smod.staff(rng), wet=0.25, seed=105) * 0.52, t0 + 0.2)
        elif si == 5:
            smod.add(amb, smod.st(smod.fire(rng, sd), 0.0) * 0.32, t0)
        elif si == 6:
            smod.add(amb, smod.reverb(smod.clasp(rng), wet=0.2, seed=107) * 0.55, t0 + 0.4)
            smod.add(amb, smod.st(smod.fire(rng, sd), -0.15) * 0.42, t0)
        elif si == 7:
            smod.add(amb, smod.st(smod.herd_far(rng, sd), 0.15) * 0.40, t0)
            smod.add(amb, smod.st(smod.water(rng, sd), -0.25) * 0.28, t0)
        elif si == 8:
            smod.add(amb, smod.st(smod.thud(rng), 0.0) * 0.48, t0 + 0.25)
            smod.add(amb, smod.st(smod.staff(rng), 0.15) * 0.35, t0 + max(0.4, sd * 0.5))
        elif si == 9:
            smod.add(amb, smod.st(smod.herd_far(rng, sd), -0.1) * 0.36, t0)
            smod.add(amb, smod.st(smod.wind(rng, sd, howl=0.18), 0.15) * 0.30, t0)
        elif si == 10:
            smod.add(amb, smod.st(smod.wind(rng, sd, howl=0.22), 0.0) * 0.34, t0)
            smod.add(amb, smod.st(smod.herd_far(rng, min(2.5, sd)), 0.25) * 0.32, t0 + 0.1)
        elif si == 11:
            smod.add(amb, smod.st(kumys_pour(rng, min(3.2, sd * 0.7)), 0.05) * 0.62, t0 + 0.35)
            smod.add(amb, smod.st(smod.fire(rng, sd), 0.30) * 0.25, t0)
        elif si == 12:
            smod.add(amb, smod.reverb(smod.staff(rng), wet=0.35, seed=113) * 0.58, t0 + 0.12)
        elif si == 13:
            smod.add(amb, smod.reverb(smod.wind(rng, sd, howl=0.10), wet=0.40, seed=114) * 0.28, t0)
        elif si == 14:
            smod.add(amb, smod.st(smod.eagle(rng), -0.20) * 0.38, t0 + 0.35)
            smod.add(amb, smod.st(smod.wind(rng, sd, howl=0.15), 0.10) * 0.32, t0)
        elif si == 15:
            smod.add(amb, smod.reverb(chain_drop(rng, min(2.0, sd)), wet=0.25, seed=116) * 0.48, t0 + 0.25)

    # Smart ducking under narrator speech (frame_rms window is 50ms)
    rms = smod.frame_rms(v, win=0.05)
    rms_st = np.interp(np.arange(N), np.arange(len(rms)) * int(SR * 0.05), rms)
    duck = 1.0 - 0.54 * np.clip(rms_st / 0.09, 0.0, 1.0)
    amb *= duck[:, None]

    out = amb + smod.st(v, 0.0) * 0.96
    out = smod.softclip(out, 0.90)
    smod.write(str(mix_raw), out)
    smod.loudnorm(str(mix_raw), str(mix_wav), I=-14, TP=-1.5, LRA=11)
    return mix_wav


def make_particle_LUT(mode: str, n_pts: int = 75, seed: int = 42):
    rng = np.random.default_rng(seed)
    xs = rng.uniform(0.03, 0.97, n_pts)
    ys = rng.uniform(0.05, 0.92, n_pts)
    vx = rng.uniform(-0.015, 0.025, n_pts)
    vy = rng.uniform(-0.045, -0.012, n_pts) if mode != "snow" else rng.uniform(0.015, 0.040, n_pts)
    rad = rng.uniform(1.6, 3.8, n_pts)
    alpha = rng.uniform(0.22, 0.72, n_pts)
    phase = rng.uniform(0.0, 2 * math.pi, n_pts)
    return xs, ys, vx, vy, rad, alpha, phase


PARTICLES_CACHE = {}


def overlay_particles(arr: np.ndarray, mode: str, t_global: float, si: int):
    key = (mode, si)
    if key not in PARTICLES_CACHE:
        PARTICLES_CACHE[key] = make_particle_LUT(mode, n_pts=65 if mode != "stars" else 45, seed=500 + si * 13)
    xs, ys, vx, vy, rad, alpha, phase = PARTICLES_CACHE[key]

    if mode == "embers":
        color = np.array([255.0, 145.0, 42.0], dtype=np.float32)
    elif mode == "snow":
        color = np.array([220.0, 235.0, 255.0], dtype=np.float32)
    elif mode == "stars":
        color = np.array([245.0, 240.0, 220.0], dtype=np.float32)
    else:
        color = np.array([255.0, 222.0, 148.0], dtype=np.float32)

    pxs = ((xs + vx * t_global) % 1.0) * W
    if mode == "stars":
        pys = ys * H * 0.55
    else:
        pys = ((ys + vy * t_global) % 1.0) * H

    twinkle = 0.55 + 0.45 * np.sin(2.5 * t_global + phase)
    eff = alpha * twinkle

    for i in range(len(pxs)):
        cx = int(pxs[i])
        cy = int(pys[i])
        r = int(round(rad[i]))
        if cx < r + 2 or cx >= W - r - 2 or cy < r + 2 or cy >= H - r - 2:
            continue
        x0, x1 = cx - r, cx + r + 1
        y0, y1 = cy - r, cy + r + 1
        yy, xx = np.ogrid[y0:y1, x0:x1]
        d2 = ((xx - cx) ** 2 + (yy - cy) ** 2) / max(1.0, float(r * r))
        mask = np.clip(1.0 - d2, 0.0, 1.0) ** 1.6
        patch = arr[y0:y1, x0:x1].astype(np.float32) + (color[None, None, :] * (eff[i] * mask[..., None]))
        arr[y0:y1, x0:x1] = np.clip(patch, 0, 255).astype(np.uint8)
    return arr


def draw_ep03_hud(frame_pil: Image.Image, lang: str, si: int, tau: float):
    """Crisp translucent tactical HUD banner + 4-Pillar Steppe Law tracker."""
    meta = HUD_META[lang]
    top_title, sub_callout, active_pillar = meta["banners"][si]
    pillars = meta["pillars"]

    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)

    # Fade in smoothly at start of scene
    alpha_in = min(1.0, max(0.0, tau / 0.35))
    bx_a = int(round(200 * alpha_in))
    tx_a = int(round(248 * alpha_in))
    gold = (244, 198, 92, tx_a)
    white = (250, 248, 244, tx_a)
    turq = (78, 214, 212, tx_a)

    f_top = rmod.font(34)
    f_sub = rmod.font(29)
    f_pil = rmod.font(26)

    # Top Glass Banner (y = 78..148)
    d.rounded_rectangle([64, 76, W - 64, 148], radius=22, fill=(14, 18, 24, bx_a), outline=(244, 198, 92, int(210 * alpha_in)), width=2)
    tw = d.textlength(top_title, font=f_top)
    d.text(((W - tw) / 2, 92), top_title, font=f_top, fill=gold)

    # Sub-callout Stat Pill (y = 160..216)
    cw = d.textlength(sub_callout, font=f_sub)
    pw = min(W - 88, int(cw + 56))
    px0 = (W - pw) // 2
    d.rounded_rectangle([px0, 160, px0 + pw, 216], radius=16, fill=(18, 36, 40, int(195 * alpha_in)), outline=(78, 214, 212, int(190 * alpha_in)), width=2)
    d.text(((W - cw) / 2, 171), sub_callout, font=f_sub, fill=white)

    # Bottom 4-Pillar Steppe Law Tracker Bar (y = 1630..1705, safely below captions and above Shorts UI)
    bar_y0, bar_y1 = 1628, 1700
    d.rounded_rectangle([54, bar_y0, W - 54, bar_y1], radius=20, fill=(12, 16, 22, 195), outline=(244, 198, 92, 120), width=2)

    slot_w = (W - 128) // 4
    for idx, label in enumerate(pillars):
        sx0 = 64 + idx * slot_w + 4
        sx1 = sx0 + slot_w - 8
        is_active = (idx == active_pillar)
        fill_c = (212, 152, 46, 225) if is_active else (28, 34, 44, 170)
        out_c = (255, 226, 138, 255) if is_active else (90, 102, 118, 150)
        txt_c = (15, 16, 20, 255) if is_active else (205, 210, 218, 220)
        d.rounded_rectangle([sx0, bar_y0 + 10, sx1, bar_y1 - 10], radius=12, fill=fill_c, outline=out_c, width=2)
        lw = d.textlength(label, font=f_pil)
        d.text((sx0 + (sx1 - sx0 - lw) / 2, bar_y0 + 20), label, font=f_pil, fill=txt_c)

    frame_rgba = frame_pil.convert("RGBA")
    frame_rgba.alpha_composite(overlay)
    return frame_rgba.convert("RGB")


def rigid_cam_frame(im_src: Image.Image, si: int, u: float) -> Image.Image:
    """Strictly rigid linear scale + translation via EXTENT float box (ZERO warping)."""
    z0, z1, cx0, cy0, cx1, cy1, _, _ = SCENE_CAM[si]
    e = u * u * (3.0 - 2.0 * u)  # Smoothstep ease
    z = z0 + (z1 - z0) * e
    cx = cx0 + (cx1 - cx0) * e
    cy = cy0 + (cy1 - cy0) * e

    vw = W / z
    vh = H / z
    x0 = max(0.0, min(W - vw, cx * W - vw * 0.5))
    y0 = max(0.0, min(H - vh, cy * H - vh * 0.5))
    return im_src.transform((W, H), Image.Transform.EXTENT, (x0, y0, x0 + vw, y0 + vh), Image.Resampling.BICUBIC)


def build_lang(lang: str, voice_only: bool = False):
    print(f"\n=== Building EP03 [{lang.upper()}] ===", flush=True)
    voice_wav, timeline, words_all, dur = build_voice_and_timeline(lang)
    print(f"  [{lang}] Voice synthesized: {dur:.2f}s across {len(timeline)} scenes, {len(words_all)} words", flush=True)

    mix_wav = run_ep03_sfx(lang, voice_wav, timeline, dur)
    print(f"  [{lang}] Sound design & -14 LUFS mastering ready: {mix_wav}", flush=True)
    if voice_only:
        return None

    # Preload crisp 1080x1920 stills
    stills = [Image.open(SCENES_DIR / f"scene_{i + 1:02d}.jpg").convert("RGB") for i in range(16)]
    chunks = rmod.chunks_from(words_all, dur)
    vign = rmod.vignette()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_mp4 = OUT_DIR / OUT_FILES[lang]
    tmp_vid = BUILD / lang / "video_silent.mp4"

    cmd_enc = [
        FFMPEG, "-y",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
        "-i", "-",
        "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        str(tmp_vid),
    ]
    proc = subprocess.Popen(cmd_enc, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    total_frames = int(round(dur * FPS))
    dissolve_frames = 6
    ci = 0
    si = 0

    for fi in range(total_frames):
        t = fi / FPS
        while si < 15 and t >= timeline[si]["t1"]:
            si += 1
        seg = timeline[si]
        seg_dur = max(0.05, seg["t1"] - seg["t0"])
        tau = max(0.0, t - seg["t0"])
        u = min(1.0, tau / seg_dur)

        frame_pil = rigid_cam_frame(stills[si], si, u)

        # Clean 6-frame rigid cross-dissolve across scene cut (no spatial warp)
        if si > 0 and SCENE_CAM[si][7]:
            frames_into = int(round(tau * FPS))
            if frames_into < dissolve_frames:
                prev_seg = timeline[si - 1]
                prev_u = 1.0
                prev_pil = rigid_cam_frame(stills[si - 1], si - 1, prev_u)
                alpha_mix = (frames_into + 1) / (dissolve_frames + 1)
                frame_pil = Image.blend(prev_pil, frame_pil, alpha_mix)

        # Additive particles before HUD & text
        arr = np.asarray(frame_pil, dtype=np.uint8).copy()
        arr = overlay_particles(arr, SCENE_CAM[si][6], t, si)

        # Cinematic vignette (precomputed uint16 LUT)
        arr = ((arr.astype(np.uint16) * vign[..., None]) >> 8).clip(0, 255).astype(np.uint8)
        frame_pil = Image.fromarray(arr, mode="RGB")

        # Tactical HUD overlay
        frame_pil = draw_ep03_hud(frame_pil, lang, si, tau)

        # Karaoke synchronized subtitles at clean y = 1350..1580 band
        while ci < len(chunks) and t >= chunks[ci]["t1"] + 0.08:
            ci += 1
        if ci < len(chunks):
            ch = chunks[ci]
            if t >= ch["t0"] - 0.12 and t <= ch["t1"] + 0.12:
                ws = ch["words"]
                act = len(ws) - 1
                for wi, wd in enumerate(ws):
                    if t <= wd["t1"]:
                        act = wi
                        break
                sub_im = rmod.render_chunk(ws, act)
                sx = (W - sub_im.width) // 2
                sy = 1435 - sub_im.height // 2
                frame_rgba = frame_pil.convert("RGBA")
                frame_rgba.alpha_composite(sub_im, dest=(sx, sy))
                frame_pil = frame_rgba.convert("RGB")

        proc.stdin.write(frame_pil.tobytes())
        if fi % (FPS * 10) == 0:
            print(f"  [{lang}] Rendered frame {fi}/{total_frames} ({t:.1f}s/{dur:.1f}s)", flush=True)

    proc.stdin.close()
    ret = proc.wait()
    if ret != 0:
        raise RuntimeError(f"FFmpeg video encode failed with exit code {ret}")

    # Mux clean -14 LUFS audio
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
    print(f"  DONE [{lang.upper()}]: {out_mp4} ({dur:.1f}s, {sz_mb:.1f} MB)", flush=True)
    return out_mp4


if __name__ == "__main__":
    args = sys.argv[1:]
    voice_only = False
    if "--voice-only" in args:
        voice_only = True
        args.remove("--voice-only")
    langs = [a.lower() for a in args] if args else ["ru", "kz", "en"]
    for lg in langs:
        build_lang(lg, voice_only=voice_only)
