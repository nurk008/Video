#!/usr/bin/env python3
"""B2B-04 Multi-Style Food-Science 3D CGI Breakdown Builder (RU / KZ / EN):
'Why Beshbarmak Outlasts Fast Food — 3D Molecular Flavor Breakdown'

Redesigned for maximum visual diversity across every scene (warm golden hearth Hook,
numbered ribbon strata, animated 90°C thermal microscope reticle + thermometer, bi-color
36.6°C split lab arena, giant 1mm magazine watermark, shutter-flash onion shock, copper
checklist chips, 3-column vertical parallax collage, slam zoom-out, and bronze/gold
Restaurant Commercial Showcase finale) paired with Studio Broadcast Vocal Clarity EQ
and deep-ducked Halal culinary Foley SFX.

Outputs:
  - output/B2B_04_CGI_Beshbarmak_Shorts_RU.mp4
  - output/B2B_04_CGI_Beshbarmak_Shorts_KZ.mp4
  - output/B2B_04_CGI_Beshbarmak_Shorts_EN.mp4
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
from PIL import Image, ImageDraw, ImageEnhance, ImageFont

ROOT = Path(__file__).resolve().parent.parent
PROD = Path(__file__).resolve().parent
SCENES_DIR = ROOT / "scenes_b2b04"
if str(PROD) not in sys.path:
    sys.path.insert(0, str(PROD))

import build_b2b_01_multilang as b1
import render as rmod
import sfx as smod

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
FONT_BLACK = PROD / "fonts" / "Montserrat-Black.ttf"
FONT_BOLD = PROD / "fonts" / "Montserrat-ExtraBold.ttf"
rmod.FONT = FONT_BLACK

W, H, FPS = rmod.W, rmod.H, rmod.FPS
SR = smod.SR
SUB_Y = 1500

GOLD = (255, 198, 56)
GOLD_BRIGHT = (255, 224, 118)
CYAN = (72, 224, 255)
EMERALD = (74, 222, 138)
CORAL = (255, 88, 88)
AMBER = (255, 166, 62)
WHITE = (248, 250, 255)

# Studio broadcast pacing: +4% crisp natural articulation, zero pitch-warp
VOICE_CFG = {
    "ru": {
        "voice": "ru-RU-SvetlanaNeural",
        "fallback": "ru-RU-DmitryNeural",
        "rate": "+4%",
        "pitch": None,
        "out_file": "B2B_04_CGI_Beshbarmak_Shorts_RU.mp4",
    },
    "kz": {
        "voice": "kk-KZ-DauletNeural",
        "fallback": "kk-KZ-AigulNeural",
        "rate": "+4%",
        "pitch": None,
        "out_file": "B2B_04_CGI_Beshbarmak_Shorts_KZ.mp4",
    },
    "en": {
        "voice": "en-US-BrianMultilingualNeural",
        "fallback": "en-US-AndrewMultilingualNeural",
        "rate": "+5%",
        "pitch": None,
        "out_file": "B2B_04_CGI_Beshbarmak_Shorts_EN.mp4",
    },
}

PAUSE_AFTER = [0.08, 0.09, 0.08, 0.09, 0.08, 0.09, 0.08, 0.08, 0.08, 0.04]

SCENE_CAM = [
    (1.04, 1.15, 0.50, 0.49, 0.50, 0.48, 3.0),   # S01: Golden hearth Astau zoom-in
    (1.00, 1.09, 0.50, 0.48, 0.50, 0.47, 0.0),   # S02: 4-layer Exploded Stack + ribbon labels
    (1.02, 1.16, 0.47, 0.50, 0.54, 0.50, 2.0),   # S03: Thermal microscope pan across 90C cut
    (1.00, 1.08, 0.50, 0.49, 0.50, 0.48, 0.0),   # S04: Bi-color split lab @ 36.6C line
    (1.00, 1.22, 0.50, 0.49, 0.50, 0.48, 0.0),   # S05: 1mm giant watermark macro zoom
    (1.20, 1.04, 0.50, 0.47, 0.50, 0.48, 3.5),   # S06: Shutter-flash pullback on 95C splash
    (1.02, 1.13, 0.50, 0.48, 0.50, 0.47, 0.0),   # S07: Copper hearth Sorpa + checklist chips
    (1.00, 1.00, 0.50, 0.50, 0.50, 0.50, 0.0),   # S08: 3-column vertical parallax collage
    (1.30, 1.00, 0.50, 0.49, 0.50, 0.48, 4.0),   # S09: Slam zoom-out back to hero Astau
    (1.00, 1.06, 0.50, 0.50, 0.50, 0.49, 0.0),   # S10: Bronze Restaurant Commercial card
]

CONTENT = {
    "ru": {
        "script": [
            "Почему одна тарелка бешбармака работает лучше любого бургера? Разберём в три-дэ.",
            "В одном блюде сходятся четыре точных слоя: туздык, мясо, тонкое тесто и сорпа.",
            "Три часа томления при девяноста градусах превращают жёсткий коллаген в нежный желатин.",
            "А жир конины плавится уже при тридцати градусах — ниже тепла тела. Никакой тяжести.",
            "Домашняя жайма толщиной в один миллиметр пористая, как губка, и пропитывается с двух сторон.",
            "Кипящая сорпа ошпаривает лук: горечь мгновенно уходит, открывая сладкий аромат туздыка.",
            "Горячая минеральная сорпа сразу согревает организм и помогает легко усвоить белок.",
            "Тонкое тесто, аминокислоты и лёгкие жиры дают ровную энергию без скачка сахара.",
            "Это не просто традиция — это отточенная веками кулинарная биохимия.",
            "У вас ресторан, доставка или мясной бренд? Сделаем 3D-разбор вашего блюда — пишите «3D» в Дайрект!",
        ],
        "tts_fix": [("три-дэ", "три дэ"), ("3D-разбор", "три-дэ разбор"), ("«3D»", "три дэ"), ("3D", "три дэ")],
        "s0_vs": ("БУРГЕР • СПАД 1 ЧАС", "БЕШБАРМАК • +6ч ЭНЕРГИИ"),
        "s0_sub": "ФИЗИКА ВКУСА В 3D",
        "s1_layers": [("01", "ТУЗДЫК +95°C"), ("02", "КОНИНА + КАЗЫ"), ("03", "ЖАЙМА 1 ММ"), ("04", "СОРПА")],
        "s2_hdr": "КОЛЛАГЕН -> ЖЕЛАТИН",
        "s2_gauge": "90°C • 3 ЧАСА",
        "s3_left": "КОНИНА ~30°C",
        "s3_left_s": "ЛЕГКО ТАЕТ В ТЕЛЕ",
        "s3_right": "ОБЫЧНЫЙ ЖИР ~45°C",
        "s3_right_s": "ОСТАЁТСЯ ТВЁРДЫМ",
        "s3_line": "36.6°C ТЕПЛО ТЕЛА",
        "s4_big": "1 ММ",
        "s4_tag": "ДВОЙНАЯ ПРОПИТКА БУЛЬОНОМ",
        "s5_top": "КИПЯТОК +95°C",
        "s5_sub": "ГОРЕЧЬ УХОДИТ -> ВКУС В МЯСО",
        "s6_chips": ["ЭЛЕКТРОЛИТЫ", "АМИНОКИСЛОТЫ", "ЛЁГКОЕ ТЕПЛО"],
        "s7_cols": ["1. ЖАЙМА 1 ММ", "2. ЖЕЛАТИН 90°C", "3. СОРПА + КАЗЫ"],
        "s7_pill": "РОВНАЯ ЭНЕРГИЯ • БЕЗ СКАЧКА САХАРА",
        "s8_title": "КУЛИНАРНАЯ НАУКА СТЕПИ",
        "s9_hdr": "3D-ПРОДАКШН ДЛЯ РЕСТОРАНОВ И ДОСТАВКИ",
        "s9_pts": ["СОЧНЫЕ СЛОИ В 3D", "ОЗВУЧКА RU / KZ / EN", "ГОТОВО ДЛЯ REELS"],
        "s9_cta": "ПИШИТЕ «3D» В DIRECT",
    },
    "kz": {
        "script": [
            "Неге бір табақ бесбармақ кез келген бургерден артық тойдырады? Қазір 3D-де ашамыз.",
            "Мұнда төрт нақты қабат түйіседі: тұздық, жылқы еті, жұқа жайма және ыстық сорпа.",
            "Тоқсан градуста үш сағат қайнағанда қатты коллаген нәзік желатинге айналады.",
            "Ал жылқы майы отыз градуста ериді — адам денесінен төмен. Еш ауырлық жоқ.",
            "Бір миллиметрлік қол жайма губка сияқты, сорпаны екі жағынан бірдей сіңіреді.",
            "Қайнаған сорпа пияздың ащысын ұшырып, тұздықтың тәтті дәмін лезде ашады.",
            "Минералға бай сорпа ағзаны жылытып, ет ақуызын жеңіл қорытуға көмектеседі.",
            "Жайма, аминқышқыл мен жеңіл май күні бойы қантты секіртпей тұрақты қуат береді.",
            "Бұл жай ас емес — ғасырлар бойы шыңдалған тағам биохимиясы.",
            "Ресторан не тағам жеткізу бар ма? Фирмалық асыңызды 3D-де жасаймыз — Дайректке «3D» жазыңыз!",
        ],
        "tts_fix": [("3D-де", "три-дэде"), ("«3D»", "три дэ"), ("3D", "три дэ")],
        "s0_vs": ("БУРГЕР • 1 САҒ ҚУАТ", "БЕСБАРМАҚ • +6 САҒ"),
        "s0_sub": "ДӘМ ФИЗИКАСЫ 3D",
        "s1_layers": [("01", "ТҰЗДЫҚ +95°C"), ("02", "ЖЫЛҚЫ ЕТІ"), ("03", "ЖАЙМА 1 ММ"), ("04", "СОРПА")],
        "s2_hdr": "КОЛЛАГЕН -> ЖЕЛАТИН",
        "s2_gauge": "90°C • 3 САҒ",
        "s3_left": "ЖЫЛҚЫ МАЙЫ ~30°C",
        "s3_left_s": "ДЕНЕДЕ ТЕЗ ЕРИДІ",
        "s3_right": "АУЫР МАЙ ~45°C",
        "s3_right_s": "ҚАТТЫ ҚАЛАДЫ",
        "s3_line": "36.6°C ДЕНЕ ҚЫЗУЫ",
        "s4_big": "1 ММ",
        "s4_tag": "ҚОС ЖАҚТЫ СОРПА СІҢІРУ",
        "s5_top": "ҚАЙНАҒАН СОРПА +95°C",
        "s5_sub": "АЩЫСЫ ҰШАДЫ -> ТӘТТІ ДӘМ",
        "s6_chips": ["ЭЛЕКТРОЛИТТЕР", "АМИНҚЫШҚЫЛДАР", "ЖЕҢІЛ ҚОРЫТУ"],
        "s7_cols": ["1. ЖАЙМА 1 ММ", "2. ЖЕЛАТИН 90°C", "3. СОРПА + ҚАЗЫ"],
        "s7_pill": "ТҰРАҚТЫ ҚУАТ • АУЫРЛЫҚСЫЗ",
        "s8_title": "ДАЛА АСХАНАСЫНЫҢ ҒЫЛЫМЫ",
        "s9_hdr": "РЕСТОРАН МЕН ДӘМХАНАҒА 3D-ШОЛУ",
        "s9_pts": ["ТАҒАМНЫҢ 3D РАЗРЕЗІ", "ҚАЗАҚ • ОРЫС • АҒЫЛШЫН", "REELS-КЕ ДАЙЫН"],
        "s9_cta": "DIRECT-КЕ «3D» ЖАЗЫҢЫЗ",
    },
    "en": {
        "script": [
            "Why does one plate of beshbarmak outlast fast food for hours? Let's break down the 3D physics.",
            "Four exact layers work together here: onion glaze, slow horsemeat, thin dough, and broth.",
            "Three hours simmering at ninety degrees transforms tough collagen straight into silky gelatin.",
            "And horse fat melts near thirty degrees — below human body heat, leaving zero heavy grease.",
            "Hand-rolled millimeter dough works like a sponge, soaking rich broth from both sides.",
            "Boiling sorpa shocks sliced onions, flashing off sharpness to release deep savory sweetness.",
            "Mineral-dense hot broth warms your core and primes effortless protein absorption.",
            "Thin pasta, amino acids, and light lipids deliver steady fuel without sugar crashes.",
            "This isn't just tradition — it's centuries of nomadic culinary biochemistry.",
            "Own a restaurant or food brand? We animate your hero dish in 3D — DM \"3D\" right now!",
        ],
        "tts_fix": [("3D", "three-D"), ("\"3D\"", "three D")],
        "s0_vs": ("BURGER • 1H CRASH", "BESHBARMAK • 6H FUEL"),
        "s0_sub": "FOOD PHYSICS IN 3D",
        "s1_layers": [("01", "ONION GLAZE"), ("02", "MEAT + KAZY"), ("03", "1MM DOUGH"), ("04", "GOLDEN BROTH")],
        "s2_hdr": "COLLAGEN -> GELATIN",
        "s2_gauge": "90°C • 3 HOURS",
        "s3_left": "EQUINE ~30°C",
        "s3_left_s": "MELTS IN THE BODY",
        "s3_right": "TALLOW ~45°C",
        "s3_right_s": "STAYS SOLID / HEAVY",
        "s3_line": "36.6°C BODY WARMTH",
        "s4_big": "1 MM",
        "s4_tag": "DUAL-SIDE BROTH ABSORPTION",
        "s5_top": "BOILING SHOCK +95°C",
        "s5_sub": "HARSHNESS GONE -> SAVORY SWEET",
        "s6_chips": ["ELECTROLYTES", "AMINO ACIDS", "WARM DIGESTION"],
        "s7_cols": ["1. 1MM DOUGH", "2. 90°C GELATIN", "3. SORPA + KAZY"],
        "s7_pill": "STEADY ENERGY • ZERO SUGAR CRASH",
        "s8_title": "NOMADIC CULINARY BIOCHEMISTRY",
        "s9_hdr": "3D MOTION FOR RESTAURANTS & BRANDS",
        "s9_pts": ["3D LAYER BREAKDOWNS", "EN / RU / KZ VOICEOVER", "READY FOR REELS"],
        "s9_cta": "DM «3D» NOW",
    },
}


def _font_bold(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_BOLD), size)


def verify_all_texts():
    f_b = _font_bold(22)
    f_k = rmod.font(32)
    tofu_b = bytes(f_b.getmask("\uffff"))
    tofu_k = bytes(f_k.getmask("\uffff"))
    d = ImageDraw.Draw(Image.new("RGBA", (10, 10)))

    def check_str(s: str):
        for ch in s:
            if not ch.isspace() and (bytes(f_b.getmask(ch)) == tofu_b or bytes(f_k.getmask(ch)) == tofu_k):
                raise ValueError(f"Unsupported font glyph {ch!r} in {s!r}")

    for lang, L in CONTENT.items():
        for k, v in L.items():
            if k == "tts_fix":
                continue
            items = [v] if isinstance(v, str) else list(v)
            for it in items:
                if isinstance(it, tuple):
                    for s in it:
                        check_str(s)
                else:
                    check_str(it)
        if d.textlength(L["s9_hdr"], font=_font_bold(24)) > W - 120:
            raise ValueError(f"[{lang}] s9_hdr too wide")
        if d.textlength(L["s8_title"], font=rmod.font(40)) > W - 100:
            raise ValueError(f"[{lang}] s8_title too wide")


# ---------------------------------------------------------------------------
# Colorized Atmospheric Backdrop Composer (Breaks Dark Void Monotony!)
# ---------------------------------------------------------------------------

def _tint_backdrop(im: Image.Image, mood: str) -> Image.Image:
    """Relight ONLY the dark void studio backdrop behind a photorealistic CGI dish without washing highlights."""
    arr = np.asarray(im, dtype=np.float32)
    lum = np.max(arr, axis=2, keepdims=True)
    # Only dark studio backdrop pixels (lum < 34) receive atmospheric light
    bg_w = np.clip((34.0 - lum) / 26.0, 0.0, 1.0) ** 1.3
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    ny = yy / H
    nx = xx / W

    if mood == "hearth_gold":
        r = 68.0 * np.exp(-((nx - 0.5) ** 2 / 0.28 + (ny - 0.44) ** 2 / 0.14)) + 28.0 * (1.0 - ny)
        g = 34.0 * np.exp(-((nx - 0.5) ** 2 / 0.28 + (ny - 0.44) ** 2 / 0.14)) + 14.0 * (1.0 - ny)
        b = 10.0 * np.exp(-((nx - 0.5) ** 2 / 0.28 + (ny - 0.44) ** 2 / 0.14)) + 6.0 * (1.0 - ny)
    elif mood == "thermal_crimson":
        r = 74.0 * np.exp(-((ny - 0.48) ** 2 / 0.12)) + 20.0
        g = 18.0 * np.exp(-((ny - 0.48) ** 2 / 0.12)) + 8.0
        b = np.full_like(r, 10.0)
    elif mood == "split_lab":
        # Left emerald-cyan light vs right muted crimson warning tint
        is_left = 1.0 - np.clip((nx - 0.49) / 0.02, 0.0, 1.0)
        glow_l = np.exp(-((nx - 0.30) ** 2 / 0.10 + (ny - 0.48) ** 2 / 0.18))
        glow_r = np.exp(-((nx - 0.70) ** 2 / 0.10 + (ny - 0.48) ** 2 / 0.18))
        r = (14.0 * glow_l) * is_left + (68.0 * glow_r) * (1.0 - is_left) + 8.0
        g = (66.0 * glow_l) * is_left + (20.0 * glow_r) * (1.0 - is_left) + 12.0
        b = (56.0 * glow_l) * is_left + (18.0 * glow_r) * (1.0 - is_left) + 14.0
    elif mood == "golden_ivory":
        g0 = np.exp(-((nx - 0.50) ** 2 / 0.32 + (ny - 0.44) ** 2 / 0.16))
        r = 64.0 * g0 + 18.0
        g = 46.0 * g0 + 14.0
        b = 18.0 * g0 + 8.0
    elif mood == "copper_bronze":
        g0 = np.exp(-((nx - 0.50) ** 2 / 0.28 + (ny - 0.48) ** 2 / 0.18))
        r = 66.0 * g0 + 22.0
        g = 28.0 * g0 + 12.0
        b = 14.0 * g0 + 8.0
    else:
        return im

    tint = np.stack([r, g, b], axis=-1)
    # Keep bottom subtitle area dark & rich
    sub_dark = 1.0 - 0.75 * np.clip((ny - 0.66) / 0.16, 0.0, 1.0)
    out = arr + tint * bg_w * sub_dark[..., None]
    return Image.fromarray(out.clip(0, 255).astype(np.uint8))


def _feathered_paste(src_crop: np.ndarray, scale: float, top_y: int, bg_col: np.ndarray,
                     rx_frac: float = 0.45, ry_frac: float = 0.48, fade_start: float = 0.70) -> Image.Image:
    ch, cw = src_crop.shape[:2]
    yy, xx = np.mgrid[0:ch, 0:cw].astype(np.float32)
    rr = np.sqrt(((xx - cw * 0.5) / (cw * rx_frac)) ** 2 + ((yy - ch * 0.5) / (ch * ry_frac)) ** 2)
    tf = np.clip((rr - fade_start) / max(0.05, 0.98 - fade_start), 0.0, 1.0)
    alpha = (0.5 * (1.0 + np.cos(math.pi * tf)))[..., None]
    feathered = (src_crop * alpha + bg_col[None, None, :] * (1.0 - alpha)).clip(0, 255).astype(np.uint8)
    nw, nh = int(round(cw * scale)), int(round(ch * scale))
    scaled = Image.fromarray(feathered).resize((nw, nh), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (W, H), tuple(int(c) for c in bg_col))
    canvas.paste(scaled, ((W - nw) // 2, top_y))
    return canvas


@lru_cache(maxsize=1)
def load_plates() -> dict[str, Image.Image]:
    raw: dict[str, Image.Image] = {}
    for i in range(1, 8):
        im = Image.open(SCENES_DIR / f"scene_{i:02d}.jpg").convert("RGB").resize((W, H), Image.Resampling.LANCZOS)
        raw[f"s{i:02d}"] = ImageEnhance.Sharpness(im).enhance(1.12)

    s2_arr = np.asarray(raw["s02"], dtype=np.float32)
    bg2 = np.array([5.0, 10.0, 14.0], dtype=np.float32)
    exploded = _feathered_paste(s2_arr[310:1475, 40:1040], scale=0.81, top_y=235, bg_col=bg2)

    s5_arr = np.asarray(raw["s05"], dtype=np.float32)
    bg5 = np.array([6.0, 11.0, 15.0], dtype=np.float32)
    canvas5 = Image.new("RGB", (W, H), tuple(int(c) for c in bg5))
    canvas5.paste(Image.fromarray(s5_arr[70:1820, :].clip(0, 255).astype(np.uint8)), (0, 0))

    # Build distinctly lit studio versions so consecutive scenes contrast strongly
    plates = {
        "s01_hearth": _tint_backdrop(raw["s01"], "hearth_gold"),
        "s02_exp": _tint_backdrop(exploded, "copper_bronze"),
        "s04_coll": _tint_backdrop(raw["s04"], "thermal_crimson"),
        "s05_lab": _tint_backdrop(canvas5, "split_lab"),
        "s03_dough": _tint_backdrop(raw["s03"], "golden_ivory"),
        "s06_splash": _tint_backdrop(raw["s06"], "copper_bronze"),
        "s07_sorpa": _tint_backdrop(raw["s07"], "hearth_gold"),
        # Macro strip crops for S08 3-column vertical parallax collage (width ~356 each)
        "strip_dough": raw["s03"].crop((260, 420, 820, 1500)).resize((356, 1360), Image.Resampling.LANCZOS),
        "strip_gel": raw["s04"].crop((180, 560, 900, 1340)).resize((356, 1360), Image.Resampling.LANCZOS),
        "strip_sorpa": raw["s07"].crop((220, 480, 840, 1420)).resize((356, 1360), Image.Resampling.LANCZOS),
    }
    return plates


def rigid_cam_crop(im_src: Image.Image, si: int, u: float, tau: float) -> tuple[Image.Image, float, float, float]:
    z0, z1, cx0, cy0, cx1, cy1, sh = SCENE_CAM[si]
    e = u * u * (3.0 - 2.0 * u)
    z = z0 + (z1 - z0) * e
    cx = cx0 + (cx1 - cx0) * e
    cy = cy0 + (cy1 - cy0) * e

    vw, vh = W / z, H / z
    x0 = max(0.0, min(W - vw, cx * W - vw * 0.5))
    y0 = max(0.0, min(H - vh, cy * H - vh * 0.5))
    if sh > 0.0 and tau < 0.20:
        decay = (1.0 - tau / 0.20) ** 2
        x0 = max(0.0, min(W - vw, x0 + sh * decay * math.sin(tau * 66.0) / z))
        y0 = max(0.0, min(H - vh, y0 + sh * decay * math.cos(tau * 52.0) / z))
    frame = im_src.transform((W, H), Image.Transform.EXTENT, (x0, y0, x0 + vw, y0 + vh), Image.Resampling.BICUBIC)
    return frame, x0, y0, z


def map_pt(src_x: float, src_y: float, x0: float, y0: float, z: float) -> tuple[int, int]:
    return int(round((src_x - x0) * z)), int(round((src_y - y0) * z))


# ---------------------------------------------------------------------------
# 10 Completely Varied Visual Compositions (Zero Formula Repetition!)
# ---------------------------------------------------------------------------

def render_scene_frame(plates: dict[str, Image.Image], lang: str, si: int, u: float, tau: float,
                       sd: float, t: float, progress_frac: float,
                       scrim: np.ndarray, vig: np.ndarray) -> Image.Image:
    L = CONTENT[lang]

    # S01: Golden Hearth Contrast Split Hook (`BURGER 1H CRASH` vs `BESHBARMAK 6H FUEL`)
    if si == 0:
        frame, x0, y0, z = rigid_cam_crop(plates["s01_hearth"], si, u, tau)
        rgba = frame.convert("RGBA")
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)

        pop = min(1.0, tau / 0.22)
        pop_e = 1.0 - (1.0 - pop) ** 3
        bad_t, good_t = L["s0_vs"]
        f_vs = _font_bold(22)
        for is_l, txt, col, bg in (
            (True, bad_t, CORAL, (42, 14, 14)),
            (False, good_t, GOLD_BRIGHT, (32, 24, 10)),
        ):
            tw = d.textlength(txt, font=f_vs)
            pw = min(460, int(tw + 44))
            cx = 280 if is_l else 800
            shift_x = int((1.0 - pop_e) * (-180 if is_l else 180))
            bx0, bx1 = cx - pw // 2 + shift_x, cx + pw // 2 + shift_x
            d.rounded_rectangle([bx0, 128, bx1, 186], radius=16, fill=(*bg, int(230 * pop_e)),
                                outline=(*col, int(245 * pop_e)), width=2)
            d.text((cx + shift_x - tw / 2, 144), txt, font=f_vs, fill=(*WHITE, int(252 * pop_e)))

        f_sub = ImageFont.truetype(str(FONT_BLACK), 34)
        stxt = L["s0_sub"]
        stw = d.textlength(stxt, font=f_sub)
        d.text(((W - stw) / 2, 214), stxt, font=f_sub, fill=(*GOLD_BRIGHT, int(240 * pop_e)))
        b1.draw_particles_studio(ov, t, seed=401, count=14)
        rgba.alpha_composite(ov)

    # S02: Dark Espresso Exploded Layers with Bold Numbered Editorial Ribbons (NO thin wire lines)
    elif si == 1:
        frame, x0, y0, z = rigid_cam_crop(plates["s02_exp"], si, u, tau)
        rgba = frame.convert("RGBA")
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        layer_coords = [(540, 345, -1), (540, 535, +1), (540, 745, -1), (540, 965, +1)]
        layer_cols = [AMBER, CORAL, GOLD_BRIGHT, CYAN]
        f_num = ImageFont.truetype(str(FONT_BLACK), 24)
        f_lbl = _font_bold(23)

        for idx, ((num, lbl), (sx, sy, side), col) in enumerate(zip(L["s1_layers"], layer_coords, layer_cols)):
            loc = min(1.0, max(0.0, (tau - idx * 0.26) / 0.22))
            if loc <= 0.02:
                continue
            loc_e = 1.0 - (1.0 - loc) ** 3
            ax, ay = map_pt(sx, sy, x0, y0, z)
            # Bold horizontal ribbon tab flying in cleanly from flank
            tw_lbl = d.textlength(lbl, font=f_lbl)
            pw = int(tw_lbl + 86)
            if side < 0:
                x_dst = 48
                bx0 = int(x_dst - (1.0 - loc_e) * 260)
            else:
                x_dst = W - 48 - pw
                bx0 = int(x_dst + (1.0 - loc_e) * 260)
            by0 = ay - 26
            d.rounded_rectangle([bx0, by0, bx0 + pw, by0 + 52], radius=14,
                                fill=(18, 14, 12, int(226 * loc_e)), outline=(*col, int(235 * loc_e)), width=2)
            # Solid numbered badge inside left of ribbon
            d.rounded_rectangle([bx0 + 6, by0 + 6, bx0 + 52, by0 + 46], radius=10, fill=(*col, int(245 * loc_e)))
            nw = d.textlength(num, font=f_num)
            d.text((bx0 + 29 - nw / 2, by0 + 11), num, font=f_num, fill=(14, 14, 14, int(255 * loc_e)))
            d.text((bx0 + 66, by0 + 13), lbl, font=f_lbl, fill=(*WHITE, int(252 * loc_e)))
        rgba.alpha_composite(ov)

    # S03: Thermal Furnace Microscope HUD + Animated Thermometer (20C -> 90C) over Collagen Melt
    elif si == 2:
        frame, x0, y0, z = rigid_cam_crop(plates["s04_coll"], si, u, tau)
        rgba = frame.convert("RGBA")
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)

        # Animated circular microscope reticle scanning left->right across collagen unwind
        rx, ry = map_pt(250 + u * 480, 945, x0, y0, z)
        d.ellipse([rx - 145, ry - 145, rx + 145, ry + 145], outline=(255, 200, 90, 210), width=4)
        d.ellipse([rx - 158, ry - 158, rx + 158, ry + 158], outline=(255, 110, 60, 110), width=2)
        d.line([(rx - 175, ry), (rx - 132, ry)], fill=(255, 224, 118, 220), width=3)
        d.line([(rx + 132, ry), (rx + 175, ry)], fill=(255, 224, 118, 220), width=3)

        # Top kinetic header banner cleanly above cut
        f_h = ImageFont.truetype(str(FONT_BLACK), 38)
        ht = L["s2_hdr"]
        htw = d.textlength(ht, font=f_h)
        d.text(((W - htw) / 2, 235), ht, font=f_h, fill=(*GOLD_BRIGHT, 250))

        # Left vertical mercury thermometer gauge rising smoothly up to 90°C
        tx0, ty0, ty1 = 64, 340, 600
        d.rounded_rectangle([tx0, ty0, tx0 + 28, ty1], radius=14, fill=(28, 16, 12, 210), outline=(255, 166, 62, 215), width=2)
        fill_p = min(1.0, 0.25 + 0.72 * u)
        fill_y = int(ty1 - 10 - (ty1 - ty0 - 20) * fill_p)
        d.rounded_rectangle([tx0 + 6, fill_y, tx0 + 22, ty1 - 6], radius=8, fill=(255, 108, 48, 240))
        fg = _font_bold(24)
        d.text((tx0 + 44, fill_y - 14), L["s2_gauge"], font=fg, fill=(*AMBER, 250))
        rgba.alpha_composite(ov)

    # S04: Bi-Color Split Arena with Horizontal 36.6°C Body Warmth Threshold
    elif si == 3:
        frame, x0, y0, z = rigid_cam_crop(plates["s05_lab"], si, u, tau)
        rgba = frame.convert("RGBA")
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)

        # Fluid golden droplets descending inside left horse-fat tube
        for k in range(6):
            ph = (t * 0.9 + k * 0.16) % 1.0
            fx, fy = map_pt(345 + math.sin(k * 2.0 + ph * 4.0) * 24, 590 + ph * 560, x0, y0, z)
            al = int(210 * math.sin(ph * math.pi))
            d.ellipse([fx - 7, fy - 7, fx + 7, fy + 7], fill=(255, 224, 125, al))

        # Horizontal 36.6°C threshold dashed line cutting across both test tubes
        _, ly = map_pt(540, 895, x0, y0, z)
        for xx in range(95, W - 95, 36):
            d.line([(xx, ly), (min(W - 95, xx + 20), ly)], fill=(255, 240, 180, 215), width=3)
        f_th = ImageFont.truetype(str(FONT_BLACK), 24)
        th_txt = L["s3_line"]
        thw = d.textlength(th_txt, font=f_th)
        px_l = int((W - thw) // 2 - 22)
        d.rounded_rectangle([px_l, ly - 24, px_l + int(thw + 44), ly + 22], radius=12,
                            fill=(12, 16, 22, 236), outline=(*GOLD_BRIGHT, 235), width=2)
        d.text(((W - thw) / 2, ly - 15), th_txt, font=f_th, fill=(*GOLD_BRIGHT, 255))

        # Dual bold top headers above left emerald vs right warning tubes
        f_b = ImageFont.truetype(str(FONT_BLACK), 28)
        f_s = _font_bold(21)
        for cx, col, tt, ts in (
            (295, EMERALD, L["s3_left"], L["s3_left_s"]),
            (785, CORAL, L["s3_right"], L["s3_right_s"]),
        ):
            tw = d.textlength(tt, font=f_b)
            sw = d.textlength(ts, font=f_s)
            d.text((cx - tw / 2, 240), tt, font=f_b, fill=(*col, 252))
            d.text((cx - sw / 2, 282), ts, font=f_s, fill=(*WHITE, 235))
        rgba.alpha_composite(ov)

    # S05: Giant Golden Magazine Watermark (`1 MM`) + 2-Sided Porous Broth Absorption on `s03_dough`
    elif si == 4:
        frame, x0, y0, z = rigid_cam_crop(plates["s03_dough"], si, u, tau)
        rgba = frame.convert("RGBA")
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)

        # Giant architectural gold watermark in open upper golden sky
        f_big = ImageFont.truetype(str(FONT_BLACK), 156)
        bw = d.textlength(L["s4_big"], font=f_big)
        d.text(((W - bw) / 2, 225), L["s4_big"], font=f_big, fill=(255, 206, 86, 52))

        f_tg = _font_bold(25)
        tgw = d.textlength(L["s4_tag"], font=f_tg)
        pw = int(tgw + 54)
        px0 = (W - pw) // 2
        d.rounded_rectangle([px0, 395, px0 + pw, 452], radius=16,
                            fill=(22, 16, 10, 215), outline=(*GOLD_BRIGHT, 220), width=2)
        d.text(((W - tgw) / 2, 409), L["s4_tag"], font=f_tg, fill=(*WHITE, 250))

        # Animated golden broth droplets soaking inward onto BOTH top & bottom dough surfaces
        for idx in range(5):
            ph = (t * 1.1 + idx * 0.2) % 1.0
            dx_s = 280 + idx * 130
            ax, ay_top = map_pt(dx_s, 690 + ph * 135, x0, y0, z)
            _, ay_bot = map_pt(dx_s, 1185 - ph * 115, x0, y0, z)
            al = int(220 * math.sin(ph * math.pi))
            d.ellipse([ax - 7, ay_top - 7, ax + 7, ay_top + 7], fill=(255, 200, 80, al))
            d.ellipse([ax - 6, ay_bot - 6, ax + 6, ay_bot + 6], fill=(255, 200, 80, al))
        rgba.alpha_composite(ov)

    # S06: Photographic Shutter Flash Entry + Slow-Mo Pullback on 95C Onion Shock `s06_splash`
    elif si == 5:
        frame, x0, y0, z = rigid_cam_crop(plates["s06_splash"], si, u, tau)
        rgba = frame.convert("RGBA")
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)

        if tau < 0.14:
            fa = int(215 * (1.0 - tau / 0.14) ** 1.5)
            d.rectangle([0, 0, W, H], fill=(255, 245, 225, fa))

        f_top = ImageFont.truetype(str(FONT_BLACK), 38)
        f_sub = _font_bold(24)
        ttw = d.textlength(L["s5_top"], font=f_top)
        tsw = d.textlength(L["s5_sub"], font=f_sub)
        d.text(((W - ttw) / 2, 165), L["s5_top"], font=f_top, fill=(*AMBER, 250))
        d.text(((W - tsw) / 2, 220), L["s5_sub"], font=f_sub, fill=(*WHITE, 238))
        rgba.alpha_composite(ov)

    # S07: Warm Copper Hearth + Stacked Emerald/Gold Checklist Chips over Cutaway Sorpa Piala
    elif si == 6:
        frame, x0, y0, z = rigid_cam_crop(plates["s07_sorpa"], si, u, tau)
        rgba = frame.convert("RGBA")
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)

        for k in range(8):
            ph = (t * 0.8 + k * 0.14) % 1.0
            ex, ey = map_pt(405 + (k % 5) * 62, 1130 - ph * 265, x0, y0, z)
            col_e = EMERALD if k % 2 == 0 else GOLD_BRIGHT
            d.ellipse([ex - 5, ey - 5, ex + 5, ey + 5], fill=(*col_e, int(195 * math.sin(ph * math.pi))))

        # Crisp floating horizontal checklist pills arranged cleanly in upper space y=180..360
        f_c = _font_bold(22)
        for idx, ch_txt in enumerate(L["s6_chips"]):
            pop = min(1.0, max(0.0, (tau - idx * 0.22) / 0.18))
            if pop <= 0.02:
                continue
            pe = 1.0 - (1.0 - pop) ** 3
            tw = d.textlength(ch_txt, font=f_c)
            pw = int(tw + 68)
            x0_c = int(76 + (1.0 - pe) * 140)
            y0_c = 175 + idx * 64
            d.rounded_rectangle([x0_c, y0_c, x0_c + pw, y0_c + 50], radius=14,
                                fill=(22, 16, 12, int(220 * pe)), outline=(*EMERALD, int(235 * pe)), width=2)
            b1.draw_vector_check(d, x0_c + 24, y0_c + 25, 9, (*EMERALD, int(252 * pe)))
            d.text((x0_c + 44, y0_c + 12), ch_txt, font=f_c, fill=(*WHITE, int(252 * pe)))
        rgba.alpha_composite(ov)

    # S08: 3-Column Parallax Vertical Strip Collage (`DOUGH | GELATIN | SORPA+KAZY`) — Huge Visual Break!
    elif si == 7:
        canvas = Image.new("RGB", (W, H), (10, 12, 16))
        strip_keys = ("strip_dough", "strip_gel", "strip_sorpa")
        dirs = (+1.0, -1.0, +1.0)
        xs_dst = (0, 362, 724)
        for sk, dir_y, xd in zip(strip_keys, dirs, xs_dst):
            st_im = plates[sk]  # 356 x 1360
            y_off = int(120 + dir_y * (u - 0.5) * 140)
            crop_s = st_im.crop((0, y_off, 356, y_off + 1040))
            canvas.paste(crop_s, (xd, 195))

        rgba = canvas.convert("RGBA")
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        # Gold architectural strip dividers
        d.rectangle([356, 195, 362, 1235], fill=(*GOLD, 210))
        d.rectangle([718, 195, 724, 1235], fill=(*GOLD, 210))
        d.line([(0, 195), (W, 195)], fill=(*GOLD, 180), width=3)
        d.line([(0, 1235), (W, 1235)], fill=(*GOLD, 180), width=3)

        # Clean column headers at top of each strip
        f_col = _font_bold(20)
        for cx, col_lbl in zip((178, 540, 902), L["s7_cols"]):
            cw = d.textlength(col_lbl, font=f_col)
            d.rounded_rectangle([cx - cw / 2 - 16, 130, cx + cw / 2 + 16, 174], radius=10,
                                fill=(16, 18, 24, 232), outline=(*GOLD, 220), width=2)
            d.text((cx - cw / 2, 140), col_lbl, font=f_col, fill=(*WHITE, 252))

        f_p = _font_bold(23)
        ptw = d.textlength(L["s7_pill"], font=f_p)
        pw = int(ptw + 54)
        px0 = (W - pw) // 2
        d.rounded_rectangle([px0, 1265, px0 + pw, 1322], radius=16,
                            fill=(18, 22, 28, 238), outline=(*GOLD_BRIGHT, 240), width=2)
        d.text(((W - ptw) / 2, 1280), L["s7_pill"], font=f_p, fill=(*GOLD_BRIGHT, 255))
        rgba.alpha_composite(ov)

    # S09: Impact Slam Zoom-Out Snapshot back to Warm Golden Astau (`s01_hearth`)
    elif si == 8:
        frame, _, _, _ = rigid_cam_crop(plates["s01_hearth"], si, u, tau)
        rgba = frame.convert("RGBA")
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        a_t = min(1.0, tau / 0.24)
        f_t = ImageFont.truetype(str(FONT_BLACK), 38)
        tw = d.textlength(L["s8_title"], font=f_t)
        d.text(((W - tw) / 2, 230), L["s8_title"], font=f_t, fill=(*GOLD_BRIGHT, int(250 * a_t)))
        b1.draw_particles_studio(ov, t, seed=409, count=16)
        rgba.alpha_composite(ov)

    # S10: Warm Bronze Commercial Restaurant Showcase Card Finale (ZERO blue CAD clone!)
    else:
        bg_c = Image.new("RGB", (W, H), (14, 10, 7))
        # Subtle warm studio dish preview framed neatly in upper card (y=150..740)
        hero_dish, _, _, _ = rigid_cam_crop(plates["s01_hearth"], si, u, tau)
        dish_crop = hero_dish.crop((80, 480, 1000, 1180)).resize((880, 620), Image.Resampling.LANCZOS).convert("RGBA")
        mask_r = Image.new("L", (880, 620), 0)
        ImageDraw.Draw(mask_r).rounded_rectangle([0, 0, 880, 620], radius=24, fill=255)
        rgba = bg_c.convert("RGBA")
        rgba.paste(dish_crop, (100, 165), mask_r)
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)

        # Warm bronze architectural photo frame around hero dish
        d.rounded_rectangle([98, 163, 982, 787], radius=24, outline=(*GOLD, 215), width=3)
        b1.draw_particles_studio(ov, t, seed=410, count=12)

        # Clean Michelin-bronze Restaurant B2B Offer Card (y=830..1280)
        pop = min(1.0, tau / 0.25)
        pe = 1.0 - (1.0 - pop) ** 3
        d.rounded_rectangle([68, 830, W - 68, 1280], radius=24, fill=(24, 17, 11, int(238 * pe)),
                            outline=(*GOLD_BRIGHT, int(240 * pe)), width=3)
        f_h = _font_bold(24)
        hw = d.textlength(L["s9_hdr"], font=f_h)
        d.text(((W - hw) / 2, 864), L["s9_hdr"], font=f_h, fill=(*CYAN, int(252 * pe)))

        f_pt = _font_bold(22)
        for idx, pt in enumerate(L["s9_pts"]):
            yy = 924 + idx * 58
            b1.draw_vector_check(d, 152, yy + 14, 10, (*EMERALD, int(252 * pe)))
            d.text((180, yy), pt, font=f_pt, fill=(*WHITE, int(250 * pe)))

        pulse = int(4 * math.sin(t * 7.0))
        d.rounded_rectangle([120 - pulse, 1126, W - 120 + pulse, 1234], radius=18,
                            fill=(*GOLD, int(248 * pe)), outline=(*WHITE, int(245 * pe)), width=2)
        f_cta = ImageFont.truetype(str(FONT_BLACK), 34)
        cw = d.textlength(L["s9_cta"], font=f_cta)
        d.text(((W - cw) / 2, 1158), L["s9_cta"], font=f_cta, fill=(16, 12, 8, int(255 * pe)))
        rgba.alpha_composite(ov)

    # Top sleek 4px progress hairline (replaces repetitive 01/10 pill)
    prog_ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dp = ImageDraw.Draw(prog_ov)
    dp.rectangle([0, 0, W, 6], fill=(20, 24, 30, 180))
    dp.rectangle([0, 0, max(4, int(round(W * progress_frac))), 6], fill=(*GOLD_BRIGHT, 245))
    rgba.alpha_composite(prog_ov)

    rgb = np.asarray(rgba.convert("RGB"), dtype=np.float32)
    rgb *= scrim
    rgb_v = ((rgb.clip(0, 255).astype(np.uint16) * vig) >> 8).astype(np.uint8)
    return Image.fromarray(rgb_v)


@lru_cache(maxsize=1)
def bottom_scrim_lut() -> np.ndarray:
    y = np.arange(H, dtype=np.float32)[:, None, None]
    fade_y = np.clip((y - 1280.0) / 340.0, 0.0, 1.0)
    return 1.0 - 0.56 * (fade_y ** 1.4)


# ---------------------------------------------------------------------------
# Studio Broadcast Vocal Mastering + Deep-Ducked Halal SFX Mix
# ---------------------------------------------------------------------------

async def _tts_one_clean(text: str, mp3_path: Path, voice: str, rate: str, pitch: str | None) -> list[dict]:
    kw: dict = {"rate": rate, "boundary": "WordBoundary"}
    if pitch:
        kw["pitch"] = pitch
    comm = b1.edge_tts.Communicate(text, voice, **kw)
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


async def _tts_b2b04_async(lang: str, audio_dir: Path) -> list[tuple[Path, list[dict]]]:
    cfg = VOICE_CFG[lang]
    lines = CONTENT[lang]["script"]
    tts_fix = CONTENT[lang]["tts_fix"]
    manifest_path = audio_dir / "manifest_v2.json"

    lines_hash = hashlib.sha256(
        json.dumps(
            {"v": 2, "voice": cfg["voice"], "fallback": cfg["fallback"], "rate": cfg["rate"],
             "pitch": cfg["pitch"], "lines": lines, "fix": tts_fix},
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()

    if manifest_path.exists():
        try:
            meta = json.loads(manifest_path.read_text(encoding="utf-8"))
            if meta.get("hash") == lines_hash and len(meta.get("items", [])) == len(lines):
                if all((audio_dir / f"v2_seg_{i:02d}.mp3").exists() and (audio_dir / f"v2_seg_{i:02d}.mp3").stat().st_size > 1500 for i in range(len(lines))):
                    return [(audio_dir / f"v2_seg_{i:02d}.mp3", meta["items"][i]["bounds"]) for i in range(len(lines))]
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
            mp3_path = audio_dir / f"v2_seg_{i:02d}.mp3"
            spoken = b1._prep_tts_text(raw_text, tts_fix)
            bounds = []
            line_ok = False
            for att in range(5):
                try:
                    if mp3_path.exists():
                        mp3_path.unlink()
                    bounds = await _tts_one_clean(spoken, mp3_path, voice_try, cfg["rate"], cfg["pitch"])
                    if mp3_path.exists() and mp3_path.stat().st_size > 1500:
                        line_ok = True
                        break
                except Exception:
                    await asyncio.sleep(0.45 * (att + 1))
            if not line_ok:
                ok_all = False
                break
            results.append((mp3_path, bounds))
            items_meta.append({"bounds": bounds})
            await asyncio.sleep(0.12)
        if ok_all:
            voice_used = voice_try
            break

    if len(results) != len(lines):
        raise RuntimeError(f"[{lang}] Edge TTS failed on {cfg['voice']} and {cfg['fallback']}")

    print(f"[B2B-04-v2:{lang.upper()}] Synthesized {len(lines)} clear lines using: {voice_used}")
    manifest_path.write_text(
        json.dumps({"hash": lines_hash, "voice": voice_used, "items": items_meta}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return results


def _decode_broadcast_voice_wav(mp3_path: Path, wav_tmp: Path) -> np.ndarray:
    """FFmpeg broadcast studio vocal chain: clean HPF, anti-boxiness scoop, 3.1kHz crispness, 7.2kHz air & leveling."""
    af = (
        "aresample=48000,"
        "highpass=f=90,"
        "equalizer=f=240:t=q:w=1.4:g=-3.5,"
        "equalizer=f=3100:t=q:w=1.1:g=4.5,"
        "equalizer=f=7200:t=q:w=1.3:g=3.0,"
        "acompressor=threshold=0.085:ratio=3.2:attack=4:release=85:makeup=1.55"
    )
    subprocess.run(
        [FFMPEG, "-y", "-i", str(mp3_path), "-af", af, "-ar", str(SR), "-ac", "1", "-c:a", "pcm_s16le", str(wav_tmp)],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    import wave
    with wave.open(str(wav_tmp), "rb") as w:
        raw = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32)
    return np.clip(raw / 32768.0, -0.95, 0.95)


def synthesize_lang_b2b04(lang: str, build_dir: Path) -> tuple[np.ndarray, list[dict], list[dict], float]:
    lines = CONTENT[lang]["script"]
    raw_items = asyncio.run(_tts_b2b04_async(lang, build_dir))
    segments_audio: list[np.ndarray] = []
    timeline: list[dict] = []
    words_all: list[dict] = []

    cursor = 0.0
    for si, ((mp3_path, bounds), text) in enumerate(zip(raw_items, lines)):
        wav_tmp = build_dir / f"v2_proc_{si:02d}.wav"
        raw_x = _decode_broadcast_voice_wav(mp3_path, wav_tmp)
        seg_x, t0_trim, t1_trim = b1._trim_silence(raw_x, head_pad=0.025, tail_pad=0.045)
        peak = float(np.max(np.abs(seg_x)))
        if peak > 1e-6:
            seg_x = (seg_x / peak * 0.90).astype(np.float32)
        seg_dur = len(seg_x) / SR

        words_seg = b1._align_words(text, bounds, t0_trim, t1_trim, seg_dur, cursor)
        words_all.extend(words_seg)

        timeline.append({"si": si, "t0": cursor, "t1": cursor + seg_dur, "dur": seg_dur})
        segments_audio.append(seg_x)
        cursor += seg_dur

        pause = PAUSE_AFTER[si] if si < len(PAUSE_AFTER) else 0.08
        if pause > 0:
            segments_audio.append(np.zeros(int(round(pause * SR)), dtype=np.float32))
            cursor += pause

    voice_full = np.concatenate(segments_audio).astype(np.float32)
    total_dur = len(voice_full) / SR

    (build_dir / "timeline.json").write_text(json.dumps({"dur": total_dur, "scenes": timeline}, indent=2), encoding="utf-8")
    (build_dir / "words.json").write_text(json.dumps(words_all, ensure_ascii=False, indent=2), encoding="utf-8")
    return voice_full, timeline, words_all, total_dur


def build_food_audio(lang: str, build_dir: Path, voice_mono: np.ndarray, timeline: list[dict], dur: float) -> Path:
    """Crisp Halal culinary SFX deeply ducked behind broadcast-clear narration."""
    mix_raw = build_dir / "mix_raw_v2.wav"
    mix_wav = build_dir / "mix_final_v2.wav"
    rng = np.random.default_rng({"ru": 41401, "kz": 41402, "en": 41403}[lang])
    n_samples = len(voice_mono)
    amb = np.zeros((n_samples, 2), dtype=np.float32)

    room = smod.lp(smod.pink(rng, dur + 0.5), 180.0)
    smod.add(amb, smod.st(room[:n_samples], 0.0) * 0.07, 0.0)

    # Low warm male a cappella pad kept gentle underneath speech
    pad = smod.reverb(smod.vocal_pad(rng, dur + 0.3, [73.42, 110.0, 146.83], vowel="m", voices=3), wet=0.25, seed=415)
    smod.add(amb, pad * 0.10, 0.0)

    for row in timeline:
        si, t0, sd = row["si"], row["t0"], row["dur"]
        if si == 0:
            smod.add(amb, smod.reverb(smod.impact_boom(rng, 0.8), wet=0.18, seed=420) * 0.44, 0.01)
        elif si == 1:
            for k in range(4):
                smod.add(amb, smod.reverb(smod.clasp(rng), wet=0.08, seed=430 + k) * 0.24, t0 + sd * (0.14 + k * 0.20))
        elif si == 2:
            simmer = smod.lp(smod.water(rng, min(1.8, sd * 0.6)), 900.0)
            smod.add(amb, smod.st(smod.fade(simmer, 0.05, 0.15), -0.1) * 0.18, t0 + 0.04)
        elif si == 3:
            smod.add(amb, smod.reverb(smod.clasp(rng), wet=0.10, seed=423) * 0.28, t0 + 0.10)
        elif si == 4:
            smod.add(amb, smod.st(smod.whoosh(rng, 0.35), 0.1) * 0.26, t0 + 0.03)
        elif si == 5:
            # Shutter camera flash snap + soft steam hiss
            smod.add(amb, smod.reverb(smod.clasp(rng), wet=0.08, seed=425) * 0.40, t0 + 0.01)
            smod.add(amb, smod.st(smod.sizzle(rng, min(0.8, sd * 0.35)), 0.15) * 0.16, t0 + 0.08)
        elif si == 6:
            for k in range(3):
                smod.add(amb, smod.reverb(smod.clasp(rng), wet=0.08, seed=440 + k) * 0.26, t0 + sd * (0.12 + k * 0.18))
        elif si == 7:
            smod.add(amb, smod.st(smod.whoosh(rng, 0.40), 0.0) * 0.30, t0 + 0.02)
        elif si == 8:
            smod.add(amb, smod.reverb(smod.impact_boom(rng, 0.8), wet=0.20, seed=428) * 0.42, t0 + 0.01)
        elif si == 9:
            rlen = min(0.9, sd * 0.35)
            smod.add(amb, smod.st(smod.riser(rng, rlen), 0.0) * 0.24, max(t0, dur - rlen - 0.02))

    # Deep aggressive sidechain duck (-16 dB) whenever narrator speaks so voice stays 100% dominant!
    rms = smod.frame_rms(voice_mono, win=0.03)
    rms_st = np.interp(np.arange(n_samples), np.arange(len(rms)) * int(SR * 0.03), rms)
    duck = 1.0 - 0.80 * np.clip(rms_st / 0.065, 0.0, 1.0)
    amb *= duck[:, None]

    out = amb * 0.56 + smod.st(voice_mono, 0.0) * 1.00
    out = smod.softclip(out, 0.92)
    smod.write(str(mix_raw), out)
    b1.loudnorm_portable(mix_raw, mix_wav, I=-14.0, TP=-1.5, LRA=9.0)
    return mix_wav


def preview_qa_frames(langs: list[str]):
    plates = load_plates()
    scrim = bottom_scrim_lut()
    vig = rmod.vignette()[..., None]
    qa_dir = PROD / "build_b2b04" / "qa_v2"
    qa_dir.mkdir(parents=True, exist_ok=True)

    sample_subs = {
        "ru": [
            ["ЛУЧШЕ", "ЛЮБОГО", "БУРГЕРА"], ["ЧЕТЫРЕ", "ТОЧНЫХ", "СЛОЯ"], ["НЕЖНЫЙ", "ЖЕЛАТИН"], ["НИКАКОЙ", "ТЯЖЕСТИ"],
            ["ОДИН", "МИЛЛИМЕТР"], ["ОШПАРИВАЕТ", "ЛУК"], ["УСВОИТЬ", "БЕЛОК"], ["РОВНУЮ", "ЭНЕРГИЮ"],
            ["ПИЩЕВАЯ", "БИОХИМИЯ"], ["ПИШИТЕ", "«3D»"],
        ],
        "kz": [["3D-ДЕ", "АШАМЫЗ"], ["ТӨРТ", "ҚАБАТ"], ["ЕШ", "АУЫРЛЫҚ", "ЖОҚ"], ["«3D»", "ЖАЗЫҢЫЗ"]],
        "en": [["3D", "PHYSICS"], ["FOUR", "LAYERS"], ["ZERO", "GREASE"], ["DM", "\"3D\""]],
    }

    for lang in langs:
        scenes_to_check = range(10) if lang == "ru" else (0, 3, 7, 9)
        for idx, si in enumerate(scenes_to_check):
            u = 0.72
            tau = 2.0
            sd = 3.5
            t = si * 3.5 + tau
            frame = render_scene_frame(plates, lang, si, u, tau, sd, t, (si + u) / 10.0, scrim, vig).convert("RGBA")
            wlist = sample_subs[lang][si if si < len(sample_subs[lang]) else idx % len(sample_subs[lang])]
            words_obj = [{"txt": w, "t0": 0.0, "t1": 1.0} for w in wlist]
            ov = rmod.render_chunk(words_obj, min(1, len(words_obj) - 1))
            frame.paste(ov, (int(W / 2 - ov.width / 2), int(SUB_Y - ov.height / 2)), ov)
            out_p = qa_dir / f"pre_{lang}_s{si:02d}.jpg"
            frame.convert("RGB").save(out_p, "JPEG", quality=92)
            print(f"[B2B-04-v2-PREVIEW] saved {out_p}")


def render_lang_video(lang: str, build_dir: Path, mix_wav: Path, timeline: list[dict],
                      words_all: list[dict], dur: float, out_mp4: Path, plates: dict[str, Image.Image]):
    scrim = bottom_scrim_lut()
    vig = rmod.vignette()[..., None]
    chunks = rmod.chunks_from(words_all, dur)
    chunk_idx = 0
    chunk_cache: dict[tuple[int, int], Image.Image] = {}
    total_frames = int(round(dur * FPS))
    video_silent = build_dir / "video_silent_v2.mp4"

    cmd = [
        FFMPEG, "-y",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-maxrate", "6.5M", "-bufsize", "13.0M",
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

            frame_rgb = render_scene_frame(plates, lang, scene_idx, u, tau, sd, t, min(1.0, t / max(0.1, dur)), scrim, vig)
            arr = np.asarray(frame_rgb, dtype=np.float32)

            # Snappy hard cuts on shock frames (S06 flash, S09 slam) and 0.08s quick blend elsewhere
            if scene_idx > 0 and scene_idx not in (5, 8) and tau < 0.08 and cut_from_rgb is not None:
                alpha = tau / 0.08
                arr = cut_from_rgb * (1.0 - alpha) + arr * alpha
            prev_frame_rgb = arr

            frame_rgba = Image.fromarray(arr.clip(0, 255).astype(np.uint8)).convert("RGBA")

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
                    if pop_s < 0.07:
                        sc_pop = 0.88 + 0.12 * (1.0 - (1.0 - pop_s / 0.07) ** 2)
                        ov = ov.resize((max(1, int(ov.width * sc_pop)), max(1, int(ov.height * sc_pop))), Image.Resampling.BILINEAR)
                    frame_rgba.paste(ov, (int(W / 2 - ov.width / 2), int(SUB_Y - ov.height / 2)), ov)

            proc.stdin.write(frame_rgba.convert("RGB").tobytes())
            if (fi + 1) % 300 == 0 or fi + 1 == total_frames:
                print(f"[B2B-04-v2:{lang.upper()}] rendered {fi + 1}/{total_frames} frames ({t:.1f}s/{dur:.1f}s)", flush=True)

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
    verify_all_texts()
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

    plates = load_plates()
    out_dir = ROOT / "output"
    out_dir.mkdir(parents=True, exist_ok=True)

    for lang in langs:
        t_start = time.time()
        build_dir = PROD / "build_b2b04" / lang
        build_dir.mkdir(parents=True, exist_ok=True)
        out_mp4 = out_dir / VOICE_CFG[lang]["out_file"]

        print(f"[B2B-04-v2:{lang.upper()}] Synthesizing broadcast-clear narration...")
        voice_mono, timeline, words_all, dur = synthesize_lang_b2b04(lang, build_dir)
        print(f"[B2B-04-v2:{lang.upper()}] Narration ready: {len(timeline)} scenes, {dur:.2f}s, {len(words_all)} words.")

        print(f"[B2B-04-v2:{lang.upper()}] Mixing deep-ducked culinary Foley SFX (-14 LUFS)...")
        mix_wav = build_food_audio(lang, build_dir, voice_mono, timeline, dur)

        print(f"[B2B-04-v2:{lang.upper()}] Rendering 1080x1920 @ 30fps -> {out_mp4.name} ...")
        render_lang_video(lang, build_dir, mix_wav, timeline, words_all, dur, out_mp4, plates)
        mb = out_mp4.stat().st_size / (1024 * 1024)
        print(f"[B2B-04-v2:{lang.upper()}] DONE in {time.time() - t_start:.1f}s: {out_mp4} ({mb:.2f} MB, {dur:.2f}s)")


if __name__ == "__main__":
    main()
