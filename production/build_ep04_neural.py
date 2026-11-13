#!/usr/bin/env python3
"""Episode 4 Builder: 'Winter Trap of Ulytau (1510)' — RU / KZ / EN
Rigid sub-pixel cinematic camera + neural studio narration + Halal SFX & A cappella.
100% free of jelly warping, close-up faces, gore, or musical instruments.
"""

import asyncio
import json
import math
import os
import subprocess
import sys
import time
import wave
from pathlib import Path

import edge_tts
import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path("/Users/market/antigravity/Video")
PROD = ROOT / "production"
SCENES_DIR = ROOT / "scenes_ep04"
BUILD = PROD / "build_ep04"
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
    "ru": {"voice": "ru-RU-DmitryNeural", "fallback": "en-US-BrianMultilingualNeural", "rate": "-2%", "pitch": "-4Hz"},
    "kz": {"voice": "kk-KZ-DauletNeural", "fallback": "kk-KZ-AigulNeural", "rate": "-2%", "pitch": "-2Hz"},
    "en": {"voice": "en-US-BrianMultilingualNeural", "fallback": "en-US-AndrewMultilingualNeural", "rate": "-2%", "pitch": "-3Hz"},
}

OUT_FILES = {
    "ru": "EP04_Ulytau_1510_Shorts_RU.mp4",
    "kz": "EP04_Ulytau_1510_Shorts_KZ.mp4",
    "en": "EP04_Ulytau_1510_Shorts_EN.mp4",
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

# 16 Scenes matching ulytau_1510_viral_script.md
EP04_SCRIPT = {
    "ru": [
        "Он захватил богатейшие города Средней Азии и считался непобедимым — но потерял всё за одну ледяную зиму в Казахской степи!",
        "Январь тысяча пятьсот десятого года. Повелитель Самарканда и Бухары Мухаммед Шейбани вводит торговую блокаду и бросает огромную армию на север.",
        "За его спиной — тяжёлая конница в латах, обозы с оружием и самоуверенный план: за пару недель сломить степь внезапным зимним рейдом.",
        "Казалось, открытый бой неизбежен. Но Касым-хан применил ледяную стратегию, перед которой любая броня оказалась бесполезной!",
        "Приём первый — «холодная пустота». Вместо лобового удара Касым-хан увёл все аулы, табуны и запасы вглубь неприступных предгорий Улытау.",
        "Враг продвигался милю за милей по пустой белой пустыне — ни добычи, ни укрытия от ледяного ветра, ни сена для боевых коней.",
        "Приём второй — удар голодом и морозом. Пока тяжёлые скакуны противника слабели в глубоких сугробах, войско ханства экономило каждую силу.",
        "Выносливые степные кони добывали траву прямо из-под снега, а летучие дозоры видели каждый шаг замерзающей армии.",
        "Приём третий — ночные удары по тылам. Лучший полководец Касыма — батыр Мойынсыз Хасан — выдвинулся вперёд во главе отборного авангарда.",
        "Стремительные отряды громили передовые заставы и отрезали обозы с провизией, исчезая в метели прежде, чем враг успевал построиться.",
        "Решающий миг наступил на рассвете в предгорьях Улытау. Измотанный холодом авангард потерял бдительность в заснеженном лагере.",
        "Приём четвёртый — молниеносный удар свежего клинка! Свежая конница Мойынсыз Хасана обрушилась на лагерь одновременно с нескольких направлений.",
        "Противник не выдержал натиска и отступил на юг, оставив обозы и захваченные рубежи. Миф о непобедимости завоевателя рухнул в снегах Улытау!",
        "Эта победа открыла золотой век Касым-хана: он объединил земли от Сырдарьи до берегов Яика и утвердил великий закон «Каска жолы»!",
        "Население степной державы выросло до одного миллиона человек, а триста тысяч конных защитников надёжно берегли покой от Алтая до Урала.",
        "Так холодный расчёт, единство и знание родной земли сокрушили армию, перед которой трепетали царства — ведь...",
    ],
    "kz": [
        "Орталық Азияның ең бай қалаларын бағындырған жеңілмейтін билеуші бір-ақ қыста Ұлы Далада бүкіл әскерінен қалай айырылды?",
        "Мың бес жүз оныншы жылдың қаңтары. Самарқан мен Бұхара билеушісі Мұхаммед Шайбани сауда жолын жауып, солтүстікке қалың қол аттандырды.",
        "Оның қолында сауыт киген ауыр атты әскер, мол қару-жарақ пен «қақаған қыста дала жұртын тез бағындырамын» деген нық сенім болды.",
        "Ашық шайқас болмай қоймайтындай көрінді. Бірақ Қасым хан ешқандай сауыт төтеп бере алмайтын ақылды айла қолданды!",
        "Бірінші әдіс — «бос дала» тактикасы. Қасым хан бетпе-бет соғыспай, бүкіл ауыл мен мал-мүлікті қарлы Ұлытау қойнауына алып кетті.",
        "Қалың қол айдалада шақырымдап ілгері басты: не азық жоқ, не ықтасын жоқ, не соғыс аттарына берер бір уыс шөп табылмады.",
        "Екінші әдіс — аяз бен аштық соққысы. Жаудың ауыр аттары қалың қарда әлсіреген сайын, қазақ жасағы қуатын үнемдеп, күш жинай берді.",
        "Жергілікті қазанаттар қар астынан тебіндеп азық тапса, жылдам шолғыншылар жау әскерінің әр қадамын қалт жібермей бақылап отырды.",
        "Үшінші әдіс — тыл мен шепке түнгі соққы. Қасымның даңқты сардары Мойынсыз Хасан батыр таңдаулы жасақты бастап, алға шықты.",
        "Ұшқыр жасақтар жаудың алдыңғы қарауылы мен азық артқан керуендерін талқандап, дұшпан сап түзегенше боран ішінде ізім-ғайым жоғалатын.",
        "Шешуші сәт Ұлытау етегінде, таң қылаң бере туды. Аяз бен аштықтан қалжыраған жау қолы қарлы қоста сақтығын жоғалтты.",
        "Төртінші әдіс — тың күштің найзағай соққысы! Мойынсыз Хасанның сайыпқыран атты әскері жау қосынына бірнеше бағыттан лап қойды.",
        "Қарсылас тегеурінге шыдамай, бүкіл жүгін тастап оңтүстікке шегінді. Жеңілмейтін билеушінің даңқы Ұлытау қарында күйреді!",
        "Бұл жеңіс Қасым ханның алтын дәуірін ашты: шекара Сырдариядан Жайыққа дейін жетіп, «Қасым ханның қасқа жолы» заңы бекіді!",
        "Ел халқы бір миллионға жетіп, Алтай мен Жайық арасын үш жүз мың таңдаулы атты жасақ сенімді қорғап тұрды.",
        "Сөйтіп, суық ақыл, ауызбіршілік пен туған жердің сырын терең білу талай патшалықты тітіркенткен әскерді жеңді, өйткені...",
    ],
    "en": [
        "He conquered the richest cities of Central Asia and never lost a siege—yet a single freezing winter in the Kazakh Steppe shattered his empire!",
        "January 1510. Ruler of Samarkand and Bukhara, Muhammad Shaybani, seals the trade cities and launches a massive winter offensive northward.",
        "Behind him ride armored shock cavalry and supply wagons—convinced a lightning mid-winter strike will catch the nomads completely off guard.",
        "A pitched battle seemed inevitable. Instead, Kasym Khan unleashed a winter strategy that turned heavy armor into a fatal trap!",
        "Tactic one — empty winter lands. Refusing a reckless frontal clash, Kasym Khan quietly withdrew every clan, herd, and storehouse deep into the Ulytau foothills.",
        "Mile after mile, the invading column trudged through white emptiness—no plunder, no shelter from razor winds, and zero fodder for warhorses.",
        "Tactic two — attrition by frost and famine. As enemy chargers weakened in waist-deep drifts, Kazakh detachments preserved their horses in sheltered valleys.",
        "Hardy steppe horses dug frozen grass straight through snowpack, while silent scouts tracked every freezing step of the overstretched column.",
        "Tactic three — surgical night raids. Kasym's master commander, Batyr Moyinsyz Khasan, pushed forward with a handpicked mobile vanguard.",
        "Swift horse squads shattered forward outposts and supply wagons, vanishing into the blizzard long before armored ranks could form up.",
        "The decisive hour struck at dawn in the Ulytau foothills. Frozen and starving, the forward camp dropped its guard inside a snowbound hollow.",
        "Tactic four — thunderbolt counterstrike! Moyinsyz Khasan's fresh cavalry crashed down from frozen ridges across multiple flanks at once.",
        "Unable to hold formation, the invading host retreated south in ruin, abandoning wagons and frontier claims. An empire's invincibility died in the snows!",
        "That triumph unlocked Kasym Khan's golden age: borders stretched from Syr Darya to the Ural river, anchored by his Bright Path code—Qaska Zholy!",
        "Contemporary chroniclers counted one million citizens and three hundred thousand horsemen guarding peace from the Altai to the Urals.",
        "And so, disciplined strategy, unity, and mastery of their own winter terrain broke an army kingdoms feared—because...",
    ],
}

# Rigid sub-pixel Ken Burns specs: (z0, z1, x0, y0, x1, y1, particle_mode, dissolve_in)
SCENE_CAM = [
    (1.00, 1.13, 0.50, 0.45, 0.50, 0.56, "blizzard", False),  # 01 Scout overlooking winter column
    (1.00, 1.13, 0.47, 0.50, 0.54, 0.48, "snow_sun", True),   # 02 Syr Darya dawn winter citadel
    (1.02, 1.13, 0.49, 0.56, 0.51, 0.46, "blizzard", True),   # 03 Iron stirrup & armored cavalry
    (1.05, 1.15, 0.46, 0.56, 0.54, 0.44, "embers",   True),   # 04 Top-down map & bronze pointer
    (1.00, 1.12, 0.54, 0.51, 0.46, 0.49, "snow_sun", True),   # 05 Empty snow-drifted winter camp
    (1.01, 1.13, 0.50, 0.54, 0.50, 0.46, "blizzard", True),   # 06 Column trudging waist-deep snow
    (1.02, 1.12, 0.48, 0.53, 0.52, 0.48, "blizzard", True),   # 07 Frost-dusted glove & horse mane
    (1.00, 1.13, 0.48, 0.52, 0.53, 0.47, "snow_sun", True),   # 08 Three steppe scouts from behind
    (1.02, 1.13, 0.50, 0.44, 0.50, 0.56, "stars",    True),   # 09 Moonlit valley campfires below
    (1.00, 1.14, 0.47, 0.53, 0.53, 0.48, "blizzard", True),   # 10 Lone scout riding into blizzard
    (1.02, 1.14, 0.49, 0.55, 0.51, 0.46, "snow_sun", True),   # 11 Pre-dawn hand on saber hilt
    (1.01, 1.15, 0.53, 0.54, 0.47, 0.46, "blizzard", True),   # 12 Crescent multi-flank pincer
    (1.12, 1.00, 0.50, 0.46, 0.50, 0.53, "blizzard", True),   # 13 Commander gesturing victory pull-out
    (1.03, 1.13, 0.46, 0.48, 0.53, 0.53, "embers",   True),   # 14 Imperial Qaska Zholy scroll & seal
    (1.00, 1.12, 0.46, 0.52, 0.54, 0.48, "snow_sun", True),   # 15 Peaceful steppe herds to horizon
    (1.12, 1.00, 0.50, 0.56, 0.50, 0.47, "blizzard", True),   # 16 Cliff ridge trail -> seamless loop
]

HUD_META = {
    "ru": {
        "banners": [
            ("1510 • ЗИМНИЙ КАПКАН УЛЫТАУ", "ОДНА ЗИМА СЛОМИЛА НЕПОБЕДИМУЮ АРМИЮ", -1),
            ("ЯНВАРЬ 1510 • ВТОРЖЕНИЕ", "ШЕЙБАНИ: БЛОКАДА + ПОХОД НА СЕВЕР", -1),
            ("СТАВКА НА БЛИЦКРИГ", "ТЯЖЁЛАЯ ЛАТНАЯ КОННИЦА И ОБОЗЫ", -1),
            ("СТРАТЕГИЯ КАСЫМ-ХАНА", "ПОЧЕМУ БРОНЯ СТАЛА ЛОВУШКОЙ?", -1),
            ("ПРИЁМ №1 • ХОЛОДНАЯ ПУСТОТА", "УВОД АУЛОВ И ТАБУНОВ ВГЛУБЬ УЛЫТАУ", 0),
            ("ПРИЁМ №1 • БЕЗ ДОБЫЧИ", "ЛЕДЯНАЯ ПУСТЫНЯ: НИ СЕНА, НИ УКРЫТИЯ", 0),
            ("ПРИЁМ №2 • ГОЛОД И МОРОЗ", "ТЯЖЁЛЫЕ КОНИ ГИБЛИ В СУГРОБАХ", 1),
            ("ПРИЁМ №2 • ТЕБЕНЁВКА", "СТЕПНЫЕ КОНИ ДОБЫВАЛИ КОРМ ИЗ-ПОД СНЕГА", 1),
            ("ПРИЁМ №3 • НОЧНЫЕ НАЛЁТЫ", "АВАНГАРД БАТЫРА МОЙЫНСЫЗ ХАСАНА", 2),
            ("ПРИЁМ №3 • ОХОТА НА ОБОЗЫ", "УДАР ПО ЗАСТАВАМ И ОТХОД В МЕТЕЛЬ", 2),
            ("РАССВЕТ В УЛЫТАУ", "ИЗМОТАННЫЙ ВРАГ ПОТЕРЯЛ БДИТЕЛЬНОСТЬ", 3),
            ("ПРИЁМ №4 • УДАР КЛИНКА", "АТАКА СВЕЖЕЙ КОННИЦЫ С ФЛАНГОВ", 3),
            ("КРАХ ЗАВОЕВАТЕЛЯ", "ОТСТУПЛЕНИЕ НА ЮГ • ПОТЕРЯ РУБЕЖЕЙ", -1),
            ("ЗОЛОТОЙ ВЕК КАСЫМ-ХАНА", "ГРАНИЦЫ ДО ЯИКА • ЗАКОН «КАСКА ЖОЛЫ»", -1),
            ("1511–1521 • МОЩЬ ХАНСТВА", "1 МЛН ЖИТЕЛЕЙ • ДО 300 000 ВСАДНИКОВ", -1),
            ("БЕСШОВНАЯ ПЕТЛЯ", "КАК СТЕПЬ ПОБЕДИЛА БЕЗ ГЕНЕРАЛЬНОГО БОЯ...", -1),
        ],
        "pillars": ["1. ПУСТОТА", "2. МОРОЗ", "3. НАЛЁТЫ", "4. УДАР"],
    },
    "kz": {
        "banners": [
            ("1510 • ҰЛЫТАУ ҚЫСҚЫ ҚАҚПАНЫ", "БІР ҚЫСТА ЖЕҢІЛМЕЙТІН ӘСКЕР КҮЙРЕДІ", -1),
            ("1510 ЖЫЛ • ҚАҢТАР ШАБУЫЛЫ", "ШАЙБАНИ: САУДА ЖАБЫҚ • СОЛТҮСТІК", -1),
            ("АУЫР ҚОЛДЫҢ ЕСЕБІ", "САУЫТТЫ АТТЫ ӘСКЕР МЕН ҚАЛЫҢ ОБОЗ", -1),
            ("ҚАСЫМ ХАННЫҢ АЙЛАСЫ", "АУЫР САУЫТ ҚАЛАЙ ЖАУҒА ТҰСАУ БОЛДЫ?", -1),
            ("1-ӘДІС • «БОС ДАЛА»", "АУЫЛ МЕН МАЛДЫ ҰЛЫТАУ ҚОЙНАУЫНА ӘКЕТУ", 0),
            ("1-ӘДІС • АҚ ТҮТЕК БОРАН", "ШӨП ЖОҚ • ЫҚТАСЫН ЖОҚ • ҚҰР ДАЛА", 0),
            ("2-ӘДІС • АЯЗ БЕН АШТЫҚ", "АУЫР АТТАР ҚАРДА ӘЛСІРЕЙ БЕРДІ", 1),
            ("2-ӘДІС • ҚАЗАНАТ ТӨЗІМІ", "ҚАР АСТЫНАН ТЕБІНДЕП КҮШ САҚТАУ", 1),
            ("3-ӘДІС • ТҮНГІ ШАБУЫЛ", "МОЙЫНСЫЗ ХАСАН БАТЫРДЫҢ ЖАСАҒЫ", 2),
            ("3-ӘДІС • КЕРУЕНДІ ҚИРАТУ", "ҚАРАУЫЛДЫ БҰЗЫП, БОРАНҒА СІҢІП КЕТУ", 2),
            ("ҰЛЫТАУ ЕТЕГІ • ТАҢ АЛДЫ", "ҚАЛЖЫРАҒАН ҚОЛ САҚТЫҒЫН ЖОҒАЛТТЫ", 3),
            ("4-ӘДІС • НАЙЗАҒАЙ СОҚҚЫ", "ТЫҢ АТТЫ ӘСКЕР БІРНЕШЕ ТҰСТАН ШАПТЫ", 3),
            ("ЖОРЫҚТЫҢ КҮЙРЕУІ", "ОҢТҮСТІККЕ ШЕГІНУ • ЖҮК ПЕН ТУ ТАСТАУ", -1),
            ("ҚАСЫМ ХАННЫҢ АЛТЫН ДӘУІРІ", "ЖАЙЫҚҚА ДЕЙІН • «ҚАСҚА ЖОЛЫ» ЗАҢЫ", -1),
            ("1511–1521 • ҰЛЫ ДЕРЖАВА", "1 МЛН ХАЛЫҚ • 300 МЫҢ АТТЫ ӘСКЕР", -1),
            ("ТҰЙЫҚ ШЕҢБЕР", "ҚАҺАРЛЫ ҚОЛДЫ ЖЕҢГЕН ДАЛА ДАНАЛЫҒЫ...", -1),
        ],
        "pillars": ["1. БОС ДАЛА", "2. АЯЗ", "3. ШАБУЫЛ", "4. СОҚҚЫ"],
    },
    "en": {
        "banners": [
            ("1510 • THE ULYTAU WINTER TRAP", "ONE WINTER SHATTERED AN UNBEATEN HOST", -1),
            ("JANUARY 1510 • NORTHERN PUSH", "SHAYBANI: TRADE EMBARGO + MASSIVE RAID", -1),
            ("HEAVY SHOCK GAMBIT", "ARMORED CAVALRY BUILT FOR A KNOCKOUT", -1),
            ("KASYM KHAN'S COUNTER", "TURNING HEAVY ARMOR INTO A WINTER CURSE", -1),
            ("TACTIC #1 • EMPTY LANDS", "EVACUATING CLANS & HERDS TO ULYTAU PEAKS", 0),
            ("TACTIC #1 • FROZEN VOID", "ZERO PLUNDER • ZERO SHELTER • ZERO FODDER", 0),
            ("TACTIC #2 • FROST ATTRITION", "HEAVY WARHORSES STALLED IN DEEP DRIFTS", 1),
            ("TACTIC #2 • STEPPE ENDURANCE", "NATIVE HORSES GRAZED UNDER THE SNOWPACK", 1),
            ("TACTIC #3 • NIGHT RAIDS", "BATYR MOYINSYZ KHASAN'S VANGUARD", 2),
            ("TACTIC #3 • SUPPLY STRIKES", "SMASH OUTPOSTS & VANISH INTO BLIZZARDS", 2),
            ("DAWN AT ULYTAU BASIN", "STARVING CAMP DROPS ITS WINTER GUARD", 3),
            ("TACTIC #4 • FLASH STRIKE", "MULTI-FLANK CAVALRY SURPRISE CHARGE", 3),
            ("MYTH BROKEN IN SNOW", "HOST RETREATS SOUTH • INVINCIBILITY GONE", -1),
            ("KASYM'S GOLDEN AGE", "BORDERS TO URAL • QASKA ZHOLY STATUTES", -1),
            ("1511–1521 • STEPPE SUPERPOWER", "1M CITIZENS • 300,000 MOUNTED DEFENDERS", -1),
            ("SEAMLESS LOOP", "HOW WINTER STRATEGY BROKE AN EMPIRE...", -1),
        ],
        "pillars": ["1. EMPTINESS", "2. FROST", "3. RAIDS", "4. STRIKE"],
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

    lines = EP04_SCRIPT[lang]
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
    smod.write(str(voice_wav), smod.norm(full_voice, 0.92))
    return voice_wav, timeline, words_all, len(full_voice) / SR


def snow_march(rng, dur: float, steps: int = 12):
    """Crisp crunch of boots/hooves packing deep frozen snow (100% physical SFX)."""
    n = smod.n_(dur)
    out = np.zeros(n, dtype=np.float64)
    for k in range(steps):
        t0 = rng.uniform(0.05, max(0.2, dur - 0.25))
        i0 = int(t0 * SR)
        cd = rng.uniform(0.09, 0.16)
        cn = min(int(cd * SR), n - i0)
        if cn > 20:
            crunch = smod.bp(smod.white(rng, cd), 750, 4200)[:cn] * smod.expenv(cd, 0.032, 0.008)[:cn]
            thump = smod.lp(smod.brown(rng, cd), 260)[:cn] * smod.expenv(cd, 0.045, 0.004)[:cn]
            out[i0:i0 + cn] += (crunch * 0.72 + thump * 0.45) * rng.uniform(0.55, 1.0)
    return smod.norm(out, 0.7)


def run_ep04_sfx(lang: str, voice_wav: Path, timeline: list, dur: float):
    ldir = BUILD / lang
    mix_raw = ldir / "mix_raw.wav"
    mix_wav = ldir / "mix.wav"

    v = smod.bp(read_wav_mono(voice_wav).astype(np.float64), 80, 11500)
    N = int(round(dur * SR))
    amb = np.zeros((N, 2), dtype=np.float64)
    rng = np.random.default_rng(1510 + sum(ord(c) for c in lang))

    # Bed: bitter winter gale sweeping the high steppe
    bed = smod.wind(rng, dur, howl=0.28) * 0.34
    amb += smod.st(bed, 0.0)

    # Pure human male A cappella choir pads (strictly ZERO musical instruments)
    A2, D3, E3, F3, G3, A3, C4, D4, E4 = 110.00, 146.83, 164.81, 174.61, 196.00, 220.00, 261.63, 293.66, 329.63
    t_s = lambda si: timeline[si]["t0"]

    # Act I — Blizzard Omen & Invasion (01-04)
    t_a0, t_a1 = t_s(0), timeline[3]["t1"]
    smod.add(amb, smod.reverb(smod.vocal_pad(rng, t_a1 - t_a0, (D3, F3, A3, C4), "o", 4), wet=0.45, seed=11) * 0.40, t_a0)

    # Act II — Cold Emptiness & Frost Attrition (05-08)
    t_b0, t_b1 = t_s(4), timeline[7]["t1"]
    smod.add(amb, smod.reverb(smod.vocal_pad(rng, t_b1 - t_b0, (A2, D3, E3, A3), "u", 3), wet=0.44, seed=22) * 0.36, t_b0)

    # Act III — Surgical Night Raids & Pre-dawn Suspense (09-11)
    t_c0, t_c1 = t_s(8), timeline[10]["t1"]
    smod.add(amb, smod.reverb(smod.vocal_pad(rng, t_c1 - t_c0, (D3, F3, G3, C4), "u", 4), wet=0.44, seed=33) * 0.40, t_c0)

    # Act IV — Dawn Strike & Kasym's Golden Age (12-16)
    t_d0 = t_s(11)
    smod.add(amb, smod.reverb(smod.vocal_pad(rng, dur - t_d0, (D3, F3, A3, D4, E4), "a", 5), wet=0.48, seed=44) * 0.46, t_d0)

    # Scene-accurate 100% physical SFX cues
    for si, seg in enumerate(timeline):
        t0 = seg["t0"]
        sd = seg["t1"] - seg["t0"]
        if si == 0:
            smod.add(amb, smod.reverb(smod.wind(rng, sd, howl=0.42), wet=0.3, seed=201) * 0.36, t0)
            smod.add(amb, smod.st(smod.eagle(rng), 0.25) * 0.32, t0 + max(0.6, sd - 2.3))
        elif si == 1:
            smod.add(amb, smod.st(smod.lp(smod.herd_far(rng, sd), 1050), -0.15) * 0.42, t0)
        elif si == 2:
            smod.add(amb, smod.st(snow_march(rng, sd, max(6, int(sd * 2.2))), 0.1) * 0.42, t0)
            smod.add(amb, smod.reverb(smod.jingle(rng, min(2.2, sd), density=30), wet=0.2, seed=203) * 0.28, t0 + 0.3)
        elif si == 3:
            smod.add(amb, smod.st(smod.fire(rng, sd), 0.2) * 0.30, t0)
            smod.add(amb, smod.reverb(smod.clasp(rng), wet=0.25, seed=204) * 0.48, t0 + 0.35)
        elif si == 4:
            smod.add(amb, smod.reverb(smod.wind(rng, sd, howl=0.38), wet=0.35, seed=205) * 0.40, t0)
        elif si == 5:
            smod.add(amb, smod.st(smod.lp(smod.gallop(rng, sd, horses=10, rate=1.15), 880), 0.0) * 0.36, t0)
            smod.add(amb, smod.st(smod.wind(rng, sd, howl=0.34), -0.2) * 0.32, t0)
        elif si == 6:
            smod.add(amb, smod.st(snow_march(rng, sd, max(5, int(sd * 1.6))), -0.1) * 0.40, t0)
            smod.add(amb, smod.reverb(smod.clasp(rng), wet=0.22, seed=207) * 0.42, t0 + 0.45)
        elif si == 7:
            smod.add(amb, smod.st(smod.wind(rng, sd, howl=0.20), 0.15) * 0.28, t0)
            smod.add(amb, smod.st(smod.herd_far(rng, sd), -0.2) * 0.35, t0)
        elif si == 8:
            smod.add(amb, smod.st(smod.fire(rng, sd), -0.2) * 0.26, t0)
            smod.add(amb, smod.st(smod.lp(smod.gallop(rng, sd, horses=6, rate=2.1), 1250), 0.25) * 0.34, t0 + 0.2)
        elif si == 9:
            smod.add(amb, smod.st(smod.whoosh(rng, 0.9), 0.15) * 0.50, t0 + 0.15)
            smod.add(amb, smod.reverb(smod.sword_clash(rng), wet=0.28, seed=210) * 0.46, t0 + 0.45)
            smod.add(amb, smod.st(smod.thud(rng), -0.2) * 0.44, t0 + 0.70)
        elif si == 10:
            smod.add(amb, smod.reverb(smod.sword_draw(rng, min(3.2, sd)), wet=0.25, seed=211) * 0.52, t0 + max(0.1, sd - min(3.2, sd)))
            smod.add(amb, smod.st(smod.riser(rng, min(2.4, sd)), 0.0) * 0.42, t0 + max(0.1, sd - min(2.4, sd)))
        elif si == 11:
            smod.add(amb, smod.reverb(smod.impact_boom(rng, 2.4), wet=0.35, seed=212) * 0.65, t0)
            smod.add(amb, smod.st(smod.herd(rng, sd), 0.0) * 0.54, t0 + 0.1)
        elif si == 12:
            smod.add(amb, smod.st(smod.thunder(rng, min(4.0, sd)), -0.1) * 0.46, t0)
            smod.add(amb, smod.st(smod.wind(rng, sd, howl=0.30), 0.2) * 0.32, t0)
        elif si == 13:
            smod.add(amb, smod.st(smod.fire(rng, sd), 0.15) * 0.25, t0)
            smod.add(amb, smod.reverb(smod.thud(rng), wet=0.25, seed=214) * 0.45, t0 + 0.45)
        elif si == 14:
            smod.add(amb, smod.st(smod.eagle(rng), -0.25) * 0.38, t0 + 0.35)
            smod.add(amb, smod.st(smod.herd_far(rng, sd), 0.1) * 0.40, t0)
        elif si == 15:
            smod.add(amb, smod.st(smod.wind(rng, sd, howl=0.32), 0.0) * 0.34, t0)
            smod.add(amb, smod.st(smod.riser(rng, min(2.5, sd * 0.65)), 0.0) * 0.40, max(t0, dur - min(2.5, sd * 0.65)))

    rms = smod.frame_rms(v, win=0.05)
    rms_st = np.interp(np.arange(N), np.arange(len(rms)) * int(SR * 0.05), rms)
    duck = 1.0 - 0.56 * np.clip(rms_st / 0.085, 0.0, 1.0)
    amb *= duck[:, None]

    out = amb * 0.90 + smod.st(v, 0.0) * 1.00
    out = smod.softclip(out, 0.90)
    smod.write(str(mix_raw), out)
    smod.loudnorm(str(mix_raw), str(mix_wav), I=-14, TP=-1.5, LRA=11)
    return mix_wav


PARTICLES_CACHE = {}


def make_particle_LUT(mode: str, n_pts: int = 85, seed: int = 42):
    rng = np.random.default_rng(seed)
    xs = rng.uniform(0.02, 0.98, n_pts)
    ys = rng.uniform(0.03, 0.95, n_pts)
    if mode == "blizzard":
        vx = rng.uniform(0.085, 0.175, n_pts)
        vy = rng.uniform(0.038, 0.095, n_pts)
        rad = rng.uniform(1.6, 3.6, n_pts)
    elif mode == "snow_sun":
        vx = rng.uniform(0.015, 0.055, n_pts)
        vy = rng.uniform(0.014, 0.038, n_pts)
        rad = rng.uniform(1.5, 3.3, n_pts)
    elif mode == "stars":
        vx = rng.uniform(-0.002, 0.002, n_pts)
        vy = rng.uniform(-0.002, 0.002, n_pts)
        rad = rng.uniform(1.4, 2.8, n_pts)
    else:  # embers
        vx = rng.uniform(-0.018, 0.028, n_pts)
        vy = rng.uniform(-0.048, -0.014, n_pts)
        rad = rng.uniform(1.6, 3.6, n_pts)
    alpha = rng.uniform(0.24, 0.72, n_pts)
    phase = rng.uniform(0.0, 2 * math.pi, n_pts)
    return xs, ys, vx, vy, rad, alpha, phase


def overlay_particles(arr: np.ndarray, mode: str, t_global: float, si: int):
    key = (mode, si)
    if key not in PARTICLES_CACHE:
        n_pts = 85 if mode == "blizzard" else (48 if mode == "stars" else 68)
        PARTICLES_CACHE[key] = make_particle_LUT(mode, n_pts=n_pts, seed=900 + si * 17)
    xs, ys, vx, vy, rad, alpha, phase = PARTICLES_CACHE[key]

    if mode == "embers":
        color = np.array([255.0, 148.0, 44.0], dtype=np.float32)
    elif mode == "blizzard":
        color = np.array([232.0, 244.0, 255.0], dtype=np.float32)
    elif mode == "stars":
        color = np.array([242.0, 245.0, 255.0], dtype=np.float32)
    else:  # snow_sun
        color = np.array([246.0, 238.0, 222.0], dtype=np.float32)

    pxs = ((xs + vx * t_global) % 1.0) * W
    if mode == "stars":
        pys = ys * H * 0.48
    else:
        pys = ((ys + vy * t_global) % 1.0) * H

    twinkle = 0.58 + 0.42 * np.sin(2.6 * t_global + phase)
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


def draw_ep04_hud(frame_pil: Image.Image, lang: str, si: int, tau: float):
    """Crisp icy steel-gold HUD banner + 4-Tactic Winter Campaign Tracker."""
    meta = HUD_META[lang]
    top_title, sub_callout, active_pillar = meta["banners"][si]
    pillars = meta["pillars"]

    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)

    alpha_in = min(1.0, max(0.0, tau / 0.35))
    bx_a = int(round(204 * alpha_in))
    tx_a = int(round(248 * alpha_in))
    gold = (242, 200, 108, tx_a)
    white = (248, 250, 255, tx_a)

    f_top = rmod.font(34)
    f_sub = rmod.font(29)
    f_pil = rmod.font(26)

    # Top Obsidian-Frost Glass Banner (y = 76..148)
    d.rounded_rectangle([64, 76, W - 64, 148], radius=22, fill=(10, 16, 26, bx_a), outline=(235, 198, 112, int(215 * alpha_in)), width=2)
    tw = d.textlength(top_title, font=f_top)
    d.text(((W - tw) / 2, 92), top_title, font=f_top, fill=gold)

    # Sub-callout Frost-Steel Pill (y = 160..216)
    cw = d.textlength(sub_callout, font=f_sub)
    pw = min(W - 88, int(cw + 56))
    px0 = (W - pw) // 2
    d.rounded_rectangle([px0, 160, px0 + pw, 216], radius=16, fill=(14, 28, 44, int(198 * alpha_in)), outline=(122, 204, 246, int(195 * alpha_in)), width=2)
    d.text(((W - cw) / 2, 171), sub_callout, font=f_sub, fill=white)

    # Bottom 4-Tactic Tracker Bar (y = 1628..1700)
    bar_y0, bar_y1 = 1628, 1700
    d.rounded_rectangle([54, bar_y0, W - 54, bar_y1], radius=20, fill=(10, 16, 26, 200), outline=(122, 204, 246, 130), width=2)

    slot_w = (W - 128) // 4
    for idx, label in enumerate(pillars):
        sx0 = 64 + idx * slot_w + 4
        sx1 = sx0 + slot_w - 8
        is_active = (idx == active_pillar)
        fill_c = (232, 182, 72, 232) if is_active else (20, 30, 44, 178)
        out_c = (255, 234, 158, 255) if is_active else (96, 128, 156, 150)
        txt_c = (14, 16, 22, 255) if is_active else (210, 220, 232, 222)
        d.rounded_rectangle([sx0, bar_y0 + 10, sx1, bar_y1 - 10], radius=12, fill=fill_c, outline=out_c, width=2)
        lw = d.textlength(label, font=f_pil)
        d.text((sx0 + (sx1 - sx0 - lw) / 2, bar_y0 + 20), label, font=f_pil, fill=txt_c)

    frame_rgba = frame_pil.convert("RGBA")
    frame_rgba.alpha_composite(overlay)
    return frame_rgba.convert("RGB")


def rigid_cam_frame(im_src: Image.Image, si: int, u: float) -> Image.Image:
    """Strictly rigid linear scale + translation via EXTENT float box (ZERO warping)."""
    z0, z1, cx0, cy0, cx1, cy1, _, _ = SCENE_CAM[si]
    e = u * u * (3.0 - 2.0 * u)
    z = z0 + (z1 - z0) * e
    cx = cx0 + (cx1 - cx0) * e
    cy = cy0 + (cy1 - cy0) * e

    vw = W / z
    vh = H / z
    x0 = max(0.0, min(W - vw, cx * W - vw * 0.5))
    y0 = max(0.0, min(H - vh, cy * H - vh * 0.5))
    return im_src.transform((W, H), Image.Transform.EXTENT, (x0, y0, x0 + vw, y0 + vh), Image.Resampling.BICUBIC)


def build_lang(lang: str, voice_only: bool = False):
    print(f"\n=== Building EP04 [{lang.upper()}] ===", flush=True)
    voice_wav, timeline, words_all, dur = build_voice_and_timeline(lang)
    print(f"  [{lang}] Voice synthesized: {dur:.2f}s across {len(timeline)} scenes, {len(words_all)} words", flush=True)

    mix_wav = run_ep04_sfx(lang, voice_wav, timeline, dur)
    print(f"  [{lang}] Sound design & -14 LUFS mastering ready: {mix_wav}", flush=True)
    if voice_only:
        return None

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

        if si > 0 and SCENE_CAM[si][7]:
            frames_into = int(round(tau * FPS))
            if frames_into < dissolve_frames:
                prev_pil = rigid_cam_frame(stills[si - 1], si - 1, 1.0)
                alpha_mix = (frames_into + 1) / (dissolve_frames + 1)
                frame_pil = Image.blend(prev_pil, frame_pil, alpha_mix)

        arr = np.asarray(frame_pil, dtype=np.uint8).copy()
        arr = overlay_particles(arr, SCENE_CAM[si][6], t, si)
        arr = ((arr.astype(np.uint16) * vign[..., None]) >> 8).clip(0, 255).astype(np.uint8)
        frame_pil = Image.fromarray(arr)

        frame_pil = draw_ep04_hud(frame_pil, lang, si, tau)

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
