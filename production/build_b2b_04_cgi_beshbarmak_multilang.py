#!/usr/bin/env python3
"""B2B-04 Culinary Science 3D CGI Breakdown Builder (RU / KZ / EN):
'Why Beshbarmak Outlasts Fast Food — 3D Molecular Flavor Breakdown'

Zack D. Films / Animagraffs Food Physics pacing (~34-39s total, 10 dynamic cuts,
85%+ photorealistic 9:16 3D CGI food & biochemistry plates, camera-tracked pointers,
optical laser sweeps, live lipid droplet / gelatin shimmer / steam / CAD-to-CGI morphs,
halal culinary Foley SFX + male a cappella pad, and native RU/KZ/EN narration).

Outputs:
  - output/B2B_04_CGI_Beshbarmak_Shorts_RU.mp4
  - output/B2B_04_CGI_Beshbarmak_Shorts_KZ.mp4
  - output/B2B_04_CGI_Beshbarmak_Shorts_EN.mp4

Usage:
    /Users/market/antigravity/Video/.venv/bin/python3 production/build_b2b_04_cgi_beshbarmak_multilang.py --preview
    /Users/market/antigravity/Video/.venv/bin/python3 production/build_b2b_04_cgi_beshbarmak_multilang.py
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
from scipy import ndimage

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
SUB_Y = 1495

GOLD = (255, 198, 56)
GOLD_BRIGHT = (255, 224, 118)
CYAN = (72, 224, 255)
EMERALD = (74, 222, 138)
CORAL = (255, 92, 92)
AMBER = (255, 166, 62)
WHITE = (248, 250, 255)

VOICE_CFG = {
    "ru": {
        "voice": "ru-RU-DmitryNeural",
        "fallback": "ru-RU-SvetlanaNeural",
        "rate": "+14%",
        "pitch": "-1Hz",
        "out_file": "B2B_04_CGI_Beshbarmak_Shorts_RU.mp4",
    },
    "kz": {
        "voice": "kk-KZ-DauletNeural",
        "fallback": "kk-KZ-AigulNeural",
        "rate": "+14%",
        "pitch": "-1Hz",
        "out_file": "B2B_04_CGI_Beshbarmak_Shorts_KZ.mp4",
    },
    "en": {
        "voice": "en-US-BrianMultilingualNeural",
        "fallback": "en-US-AndrewMultilingualNeural",
        "rate": "+14%",
        "pitch": "-2Hz",
        "out_file": "B2B_04_CGI_Beshbarmak_Shorts_EN.mp4",
    },
}

PAUSE_AFTER = [0.04, 0.05, 0.05, 0.06, 0.05, 0.05, 0.05, 0.05, 0.06, 0.02]

# Camera keyframes per scene: (z0, z1, cx0, cy0, cx1, cy1, shake_amp)
SCENE_CAM = [
    (1.00, 1.12, 0.50, 0.49, 0.50, 0.48, 3.0),   # S01: Floating Astau + laser slice
    (1.00, 1.09, 0.50, 0.48, 0.50, 0.47, 0.0),   # S02: 4-layer Exploded stack
    (1.02, 1.15, 0.48, 0.50, 0.52, 0.50, 2.5),   # S03: Collagen -> Gelatin melt @ 90°C
    (1.00, 1.10, 0.50, 0.49, 0.50, 0.48, 0.0),   # S04: Fat melting point ~30°C vs ~45°C
    (1.02, 1.15, 0.50, 0.49, 0.51, 0.48, 2.0),   # S05: 1mm Porous dough cutaway
    (1.03, 1.15, 0.50, 0.47, 0.50, 0.46, 2.5),   # S06: Boiling 95°C broth onion shock
    (1.00, 1.13, 0.50, 0.48, 0.50, 0.47, 0.0),   # S07: Mineral Sorpa piala cutaway + kazy
    (1.00, 1.12, 0.50, 0.48, 0.50, 0.47, 0.0),   # S08: Macro synergy close-up
    (1.07, 1.00, 0.50, 0.48, 0.50, 0.48, 2.5),   # S09: Optical wipe Exploded -> Astau
    (1.00, 1.07, 0.50, 0.48, 0.50, 0.47, 0.0),   # S10: CAD wireframe -> CGI morph + CTA
]

# Tracked hardware/ingredient coordinates (src_x, src_y, ldx, ldy, color_key, delay_s)
SCENE_ANCHORS = {
    0: [
        (375, 1020, -185, +175, "gold", 0.16),
        (785, 1085, +125, +115, "cyan", 0.36),
    ],
    1: [
        (540, 345, -310, -25, "amber", 0.12),
        (540, 530, +310, -35, "coral", 0.32),
        (540, 745, -310, -15, "gold_bright", 0.52),
        (540, 960, +310, +25, "cyan", 0.72),
    ],
    2: [
        (145, 765, +125, -210, "cyan", 0.15),
        (260, 1110, +160, +160, "amber", 0.42),
        (745, 900, +145, -215, "gold_bright", 0.70),
    ],
    3: [
        (350, 740, -165, -370, "emerald", 0.18),
        (725, 740, +165, -370, "coral", 0.45),
    ],
    4: [
        (315, 965, -135, -230, "gold_bright", 0.15),
        (755, 1020, +145, -235, "amber", 0.45),
    ],
    5: [
        (455, 915, -220, +225, "amber", 0.15),
        (615, 575, +210, -175, "cyan", 0.45),
    ],
    6: [
        (535, 975, +155, +285, "gold_bright", 0.16),
        (770, 625, +165, -205, "coral", 0.45),
    ],
    7: [
        (540, 750, +295, -235, "gold_bright", 0.18),
    ],
}

CONTENT = {
    "ru": {
        "script": [
            "Почему одна тарелка бешбармака работает лучше любого бургера? Режем в 3D.",
            "Здесь сходятся четыре точных слоя: туздык, мясо, тонкое тесто и бульон.",
            "Три часа томления при девяноста градусах превращают жёсткий коллаген в нежный желатин.",
            "Секрет конины — её жир плавится при тридцати градусах, ниже тепла тела. Тяжести ноль.",
            "Ручная жайма толщиной один миллиметр пористая как губка — бульон впитывается с двух сторон.",
            "Кипяток сорпы ошпаривает лук: горечь мгновенно улетучивается, а сладость раскрывает вкус.",
            "Наваристая сорпа с минералами мгновенно согревает и запускает лёгкое усвоение белка.",
            "Жир, аминокислоты и тесто дают ровную энергию на весь день без резкого скачка сахара.",
            "Это не просто старый рецепт — это выверенная веками кулинарная биохимия.",
            "У вас ресторан, доставка или мясной бренд? Покажем ваше блюдо в 3D — пишите «3D» в Дайрект!",
        ],
        "tts_fix": [("3D", "три дэ"), ("«3D»", "три дэ")],
        "badges": [
            "01/10  •  ФИЗИКА БЕШБАРМАКА",
            "02/10  •  4 СЛОЯ В 3D-РАЗРЕЗЕ",
            "03/10  •  РАСПАД КОЛЛАГЕНА",
            "04/10  •  ТЕМПЕРАТУРА +30°C",
            "05/10  •  ПОРИСТАЯ ЖАЙМА 1 ММ",
            "06/10  •  АЛХИМИЯ ТУЗДЫКА",
            "07/10  •  МИНЕРАЛЬНАЯ СОРПА",
            "08/10  •  ЭНЕРГИЯ БЕЗ ТЯЖЕСТИ",
            "09/10  •  СИНЕРГИЯ ВКУСА",
            "10/10  •  3D ДЛЯ РЕСТОРАНОВ И ЕДЫ",
        ],
        "pointers": {
            0: ["МЯСО + КАЗЫ", "ТЕСТО 1 ММ"],
            1: ["ТУЗДЫК +95°C", "КОНИНА + КАЗЫ", "ЖАЙМА 1 ММ", "СОРПА"],
            2: ["КОЛЛАГЕН", "90°C • 3 ЧАСА", "ЖЕЛАТИН"],
            3: ["КОНИНА ~30°C", "ТЯЖЁЛЫЙ ЖИР ~45°C"],
            4: ["ПОРЫ 1 ММ", "ПРОПИТКА x2"],
            5: ["БУЛЬОН +95°C", "ГОРЕЧЬ УХОДИТ"],
            6: ["ЭЛЕКТРОЛИТЫ", "АМИНОКИСЛОТЫ"],
            7: ["БАЛАНС БЖУ + ТЕПЛА"],
        },
        "s8_pill": "ЗАКОН СТЕПИ  •  СЫТОСТЬ БЕЗ ТЯЖЕСТИ",
        "s9_cta": "РЕСТОРАН ИЛИ ДОСТАВКА?  •  ПИШИТЕ «3D» В DIRECT",
    },
    "kz": {
        "script": [
            "Бір табақ бесбармақ кез келген бургерден неге артық тойдырады? 3D-де ашайық.",
            "Мұнда төрт дәл қабат түйіседі: тұздық, ет, жұқа жайма және сорпа.",
            "Тоқсан градуста үш сағат қайнағанда қатты коллаген нәзік желатинге айналады.",
            "Жылқы майы отыз градуста ериді — адам денесінен төмен. Сондықтан ауырлық бермейді.",
            "Бір миллиметр қол жайма губка сияқты — сорпа екі жағынан бірдей сіңеді.",
            "Қайнаған сорпа пияздың ащысын бумен ұшырып, табиғи тәтті дәмін ашады.",
            "Минералды ыстық сорпа ағзаны лезде жылытып, ет ақуызын жеңіл қорытады.",
            "Май, ақуыз бен жайма қантты көтермей, күні бойы тұрақты қуат береді.",
            "Бұл жай ғана тағам емес — ғасырлар бойы шыңдалған асхана ғылымы.",
            "Ресторан не тағам бренді бар ма? Тағамыңызды 3D-де жасаймыз — Дайректке «3D» жазыңыз!",
        ],
        "tts_fix": [("3D-де", "три-дэде"), ("«3D»", "три дэ"), ("3D", "три дэ")],
        "badges": [
            "01/10  •  БЕСБАРМАҚ ФИЗИКАСЫ",
            "02/10  •  3D-РАЗРЕЗ: 4 ҚАБАТ",
            "03/10  •  КОЛЛАГЕН ЫДЫРАУЫ",
            "04/10  •  ЕРУ НҮКТЕСІ +30°C",
            "05/10  •  ҚОЛ ЖАЙМА 1 ММ",
            "06/10  •  ТҰЗДЫҚ АЛХИМИЯСЫ",
            "07/10  •  МИНЕРАЛДЫ СОРПА",
            "08/10  •  АУЫРЛЫҚСЫЗ ҚУАТ",
            "09/10  •  АСХАНА БИОХИМИЯСЫ",
            "10/10  •  РЕСТОРАНДАРҒА 3D-ШОЛУ",
        ],
        "pointers": {
            0: ["ЕТ + ҚАЗЫ", "ҚАМЫР 1 ММ"],
            1: ["ТҰЗДЫҚ +95°C", "ЖЫЛҚЫ ЕТІ + ҚАЗЫ", "ЖАЙМА 1 ММ", "СОРПА"],
            2: ["КОЛЛАГЕН", "90°C • 3 САҒ", "ЖЕЛАТИН"],
            3: ["ЖЫЛҚЫ МАЙЫ ~30°C", "АУЫР МАЙ ~45°C"],
            4: ["1 ММ КЕУЕКТЕР", "ҚОС СІҢІРУ"],
            5: ["СОРПА +95°C", "АЩЫСЫ ҰШАДЫ"],
            6: ["ЭЛЕКТРОЛИТТЕР", "АМИНҚЫШҚЫЛДАР"],
            7: ["АҚУЫЗ + ҚУАТ ТЕҢДІГІ"],
        },
        "s8_pill": "ДАЛА ЗАҢЫ  •  АУЫРЛЫҚСЫЗ ТОЙЫМДЫЛЫҚ",
        "s9_cta": "РЕСТОРАН НЕ ДӘМХАНА МА?  •  DIRECT-КЕ «3D»",
    },
    "en": {
        "script": [
            "Why does one plate of beshbarmak outlast any burger? Let's slice into 3D.",
            "Four engineered layers collide here: caramelized onion, slow meat, thin dough, and broth.",
            "Three hours simmering at ninety degrees unwinds tough collagen straight into silky gelatin.",
            "Horse fat melts around thirty degrees — below body heat, leaving zero heavy grease.",
            "Hand-rolled millimeter dough acts like a sponge, locking rich broth inside every pore.",
            "Boiling broth shocks the onion rings, flashing off sharpness into rich savory sweetness.",
            "Mineral-rich golden sorpa warms the core and primes effortless protein absorption.",
            "Balanced fats, collagen, and thin dough fuel hours of steady energy without crashes.",
            "Not just tradition — centuries of nomadic culinary biochemistry engineered to perfection.",
            "Own a restaurant or food brand? We animate your signature dish in 3D — DM \"3D\" today!",
        ],
        "tts_fix": [("3D", "three-D"), ("\"3D\"", "three D")],
        "badges": [
            "01/10  •  BESHBARMAK PHYSICS",
            "02/10  •  4 ENGINEERED LAYERS",
            "03/10  •  COLLAGEN HYDROLYSIS",
            "04/10  •  30°C MELTING POINT",
            "05/10  •  1MM POROUS DOUGH",
            "06/10  •  95°C ONION INFUSION",
            "07/10  •  MINERAL SORPA BROTH",
            "08/10  •  STEADY FUEL BALANCE",
            "09/10  •  CULINARY BIOCHEMISTRY",
            "10/10  •  3D FOR FOOD BRANDS",
        ],
        "pointers": {
            0: ["MEAT + KAZY", "1MM DOUGH"],
            1: ["ONION GLAZE", "HORSEMEAT + KAZY", "1MM NOODLES", "GOLDEN SORPA"],
            2: ["COLLAGEN", "90°C • 3H", "SILKY GELATIN"],
            3: ["EQUINE LIPID ~30°C", "HEAVY TALLOW ~45°C"],
            4: ["1MM PORES", "BROTH LOCK-IN"],
            5: ["95°C BROTH SHOCK", "HARSHNESS GONE"],
            6: ["ELECTROLYTES", "AMINO ACIDS"],
            7: ["SLOW-BURN ENERGY"],
        },
        "s8_pill": "NOMAD SCIENCE  •  PURE ENERGY, ZERO CRASH",
        "s9_cta": "RESTAURANT OR FOOD BRAND?  •  DM «3D» NOW",
    },
}


def _font_bold(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_BOLD), size)


def verify_all_texts():
    f_bad = _font_bold(23)
    f_ptr = _font_bold(22)
    f_cta = ImageFont.truetype(str(FONT_BLACK), 25)
    tofu_b = bytes(f_bad.getmask("\uffff"))
    tofu_k = bytes(rmod.font(32).getmask("\uffff"))
    d = ImageDraw.Draw(Image.new("RGBA", (10, 10)))

    def check_str(s: str):
        for ch in s:
            if not ch.isspace() and (bytes(f_bad.getmask(ch)) == tofu_b or bytes(rmod.font(32).getmask(ch)) == tofu_k):
                raise ValueError(f"Unsupported font glyph {ch!r} in {s!r}")

    for lang, L in CONTENT.items():
        for b in L["badges"]:
            check_str(b)
            if d.textlength(b, font=f_bad) > W - 140:
                raise ValueError(f"[{lang}] Badge too wide: {b}")
        for si, plist in L["pointers"].items():
            for lbl in plist:
                check_str(lbl)
                if d.textlength(lbl, font=f_ptr) > 360:
                    raise ValueError(f"[{lang}] Pointer label too wide in S{si:02d}: {lbl}")
        check_str(L["s8_pill"])
        if d.textlength(L["s8_pill"], font=f_ptr) > W - 140:
            raise ValueError(f"[{lang}] S8 pill too wide: {L['s8_pill']}")
        check_str(L["s9_cta"])
        if d.textlength(L["s9_cta"], font=f_cta) > W - 120:
            raise ValueError(f"[{lang}] S10 CTA too wide: {L['s9_cta']}")
        for line in L["script"]:
            check_str(line)


# ---------------------------------------------------------------------------
# Pre-Composed CGI Plates, Macro Synergy & Neon CAD Wireframe
# ---------------------------------------------------------------------------

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
    """Load 7 unique food-CGI plates + exploded reframe, CAD wireframe & macro meat/noodle shot."""
    plates: dict[str, Image.Image] = {}
    for i in range(1, 8):
        p = SCENES_DIR / f"scene_{i:02d}.jpg"
        im = Image.open(p).convert("RGB").resize((W, H), Image.Resampling.LANCZOS)
        im = ImageEnhance.Sharpness(im).enhance(1.12)
        plates[f"s{i:02d}"] = im

    # Re-frame s02 (exploded 4-layer stack) into clean y=230..1174 viewport above bottom subtitles
    s2_arr = np.asarray(plates["s02"], dtype=np.float32)
    bg2 = np.array([5.0, 10.0, 14.0], dtype=np.float32)
    plates["exploded"] = _feathered_paste(s2_arr[310:1475, 40:1040], scale=0.81, top_y=230, bg_col=bg2)

    # Shift s05 (test chambers) slightly higher (~70px) so chamber bases clear subtitles cleanly
    s5_arr = np.asarray(plates["s05"], dtype=np.float32)
    bg5 = np.array([6.0, 11.0, 15.0], dtype=np.float32)
    canvas5 = Image.new("RGB", (W, H), tuple(int(c) for c in bg5))
    shift_up = Image.fromarray(s5_arr[70:1820, :].clip(0, 255).astype(np.uint8))
    canvas5.paste(shift_up, (0, 0))
    plates["s05_up"] = canvas5

    # Macro beauty crop of Kazy + Meat + Silky Diamond Dough layers from s02 (for Scene 08)
    plates["s02_macro"] = _feathered_paste(s2_arr[545:1145, 130:950], scale=1.18, top_y=390, bg_col=bg2, fade_start=0.62)

    # Neon-Cyan/Gold 3D CAD Wireframe extracted from `exploded` via Sobel gradient
    arr_ex = np.asarray(plates["exploded"], dtype=np.float32)
    gray = 0.299 * arr_ex[..., 0] + 0.587 * arr_ex[..., 1] + 0.114 * arr_ex[..., 2]
    gx = ndimage.sobel(gray, axis=1)
    gy = ndimage.sobel(gray, axis=0)
    edge = np.hypot(gx, gy)
    edge_n = np.clip((edge - 18.0) / 140.0, 0.0, 1.0) ** 0.72
    glow = ndimage.gaussian_filter(edge_n, sigma=2.2)

    yy_g, xx_g = np.mgrid[0:H, 0:W].astype(np.float32)
    env_g = np.exp(-(((xx_g - W * 0.5) / 360.0) ** 2 + ((yy_g - 705.0) / 480.0) ** 2))
    grid_mask = (((yy_g.astype(int) % 60 == 0) | (xx_g.astype(int) % 60 == 0)).astype(np.float32)) * 0.10 * env_g

    cad = np.empty_like(arr_ex)
    cad[..., 0] = bg2[0] + 22.0 * glow + 65.0 * edge_n + 22.0 * grid_mask
    cad[..., 1] = bg2[1] + 138.0 * glow + 225.0 * edge_n + 100.0 * grid_mask
    cad[..., 2] = bg2[2] + 188.0 * glow + 255.0 * edge_n + 145.0 * grid_mask
    plates["exploded_cad"] = Image.fromarray(cad.clip(0, 255).astype(np.uint8))
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
    if si == 1:  # subtle zero-G culinary float
        y0 = max(0.0, min(H - vh, y0 + math.sin(tau * 3.0) * 5.0 / z))

    frame = im_src.transform((W, H), Image.Transform.EXTENT, (x0, y0, x0 + vw, y0 + vh), Image.Resampling.BICUBIC)
    return frame, x0, y0, z


def map_pt(src_x: float, src_y: float, x0: float, y0: float, z: float) -> tuple[int, int]:
    return int(round((src_x - x0) * z)), int(round((src_y - y0) * z))


# ---------------------------------------------------------------------------
# Live Culinary Physics Overlays (Steam, Lipids, Laser, Broth Drops, CAD Morph)
# ---------------------------------------------------------------------------

def apply_live_fx(frame: Image.Image, plates: dict[str, Image.Image], si: int, u: float, tau: float, t: float,
                  x0: float, y0: float, z: float, lang: str) -> Image.Image:
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)

    # S01: White-hot holographic laser hotspot gliding along Astau cyan slice plane + subtle studio dust
    if si == 0:
        lx_src = 110.0 + ((u * 1.40) % 1.0) * 860.0
        ly_src = 965.0 - 25.0 * ((lx_src - 110.0) / 860.0)
        lx, ly = map_pt(lx_src, ly_src, x0, y0, z)
        d.ellipse([lx - 44, ly - 5, lx + 44, ly + 5], fill=(80, 235, 255, 70))
        d.ellipse([lx - 18, ly - 3, lx + 18, ly + 3], fill=(235, 252, 255, 195))
        b1.draw_particles_studio(ov, t, seed=41, count=14)

    # S02: Sequential cyan/amber halo ring sweeping down the 4 exploded strata
    elif si == 1:
        scan_y = 300.0 + ((tau * 430.0) % 720.0)
        sx, sy = map_pt(540, scan_y, x0, y0, z)
        d.ellipse([sx - 235, sy - 22, sx + 235, sy + 22], outline=(255, 206, 95, 115), width=3)
        b1.draw_particles_studio(ov, t, seed=42, count=14)

    # S03: Thermal line pulse + golden gelatin dissolve bubbles flowing right across collagen slice
    elif si == 2:
        bx, by = map_pt(258, 960, x0, y0, z)
        pulse = 0.65 + 0.35 * math.sin(t * 9.0)
        d.line([(bx, by - 260), (bx, by + 260)], fill=(255, 185, 85, int(110 * pulse)), width=5)
        for k in range(8):
            ph = (t * 0.9 + k * 0.13) % 1.0
            gx, gy = map_pt(275 + ph * 640, 770 + (k % 5) * 95 + math.sin(ph * 6.0 + k) * 14, x0, y0, z)
            al = int(175 * math.sin(ph * math.pi))
            d.ellipse([gx - 5, gy - 5, gx + 5, gy + 5], fill=(255, 220, 120, al))

    # S04: Weightless fluid lipid spheres gliding down the left horsemeat tube (~30°C vs solid block)
    elif si == 3:
        for k in range(6):
            ph = (t * 0.85 + k * 0.16) % 1.0
            fx, fy = map_pt(350 + math.sin(k * 2.1 + ph * 4.0) * 28, 610 + ph * 560, x0, y0, z)
            rad = 6 + (k % 3) * 2
            al = int(205 * math.sin(ph * math.pi))
            d.ellipse([fx - rad, fy - rad, fx + rad, fy + rad], fill=(255, 212, 115, int(al * 0.65)),
                      outline=(255, 245, 200, al), width=2)

    # S05: Golden broth droplets condensing slowly beneath porous 1mm hand-rolled dough edge
    elif si == 4:
        for dx_src, dy_src, ph0 in ((435, 1020, 0.0), (585, 1045, 0.35), (750, 1065, 0.65)):
            ph = (t * 0.95 + ph0) % 1.0
            px, py = map_pt(dx_src, dy_src + ph * 95, x0, y0, z)
            r = int(8 - 3 * ph)
            al = int(200 * (1.0 - ph))
            d.ellipse([px - r, py - r, px + r, py + r], fill=(255, 190, 75, int(al * 0.8)),
                      outline=(255, 236, 165, al), width=2)

    # S06: Aromatic vapor particles escaping upward off 95°C onion shock splash
    elif si == 5:
        for k in range(9):
            ph = (t * 0.9 + k * 0.11) % 1.0
            vx, vy = map_pt(320 + k * 56 + math.sin(k + ph * 5.0) * 22, 820 - ph * 340, x0, y0, z)
            al = int(115 * math.sin(ph * math.pi))
            d.ellipse([vx - 8, vy - 8, vx + 8, vy + 8], fill=(255, 235, 210, int(al * 0.45)))

    # S07: Luminous mineral/electrolyte glints rising through translucent Sorpa piala window
    elif si == 6:
        for k in range(8):
            ph = (t * 0.8 + k * 0.14) % 1.0
            ex, ey = map_pt(405 + (k % 5) * 62, 1130 - ph * 265, x0, y0, z)
            col_e = EMERALD if k % 2 == 0 else GOLD_BRIGHT
            al = int(195 * math.sin(ph * math.pi))
            d.ellipse([ex - 5, ey - 5, ex + 5, ey + 5], fill=(*col_e, al))

    # S08: Savory golden aroma glow gently pulsing across meat + dough macro close-up
    elif si == 7:
        b1.draw_particles_studio(ov, t, seed=48, count=18)

    # S09: Optical cyan-gold reassembly wipe snapping Exploded 4 layers -> Steaming Astau!
    elif si == 8:
        w_u = min(1.0, max(0.0, (u - 0.05) / 0.56))
        e_w = w_u * w_u * (3.0 - 2.0 * w_u)
        split_x = int(round(W * e_w))
        hero_cam, _, _, _ = rigid_cam_crop(plates["s01"], si, u, tau)
        arr_cut = np.asarray(frame, dtype=np.uint8)
        arr_hero = np.asarray(hero_cam, dtype=np.uint8)
        merged = arr_cut.copy()
        if split_x > 0:
            merged[:, :split_x] = arr_hero[:, :split_x]
        frame = Image.fromarray(merged)
        if 0.01 < e_w < 0.99:
            d.rectangle([split_x - 10, 230, split_x + 10, 1250], fill=(255, 206, 95, 165))
            d.line([(split_x, 230), (split_x, 1250)], fill=(255, 255, 255, 245), width=4)

        p_a = min(1.0, max(0.0, (u - 0.28) / 0.20))
        if p_a > 0.02:
            pill = CONTENT[lang]["s8_pill"]
            fp = _font_bold(22)
            tw = d.textlength(pill, font=fp)
            pw = int(tw + 52)
            px0 = (W - pw) // 2
            d.rounded_rectangle([px0, 1276, px0 + pw, 1332], radius=16,
                                fill=(12, 20, 28, int(230 * p_a)), outline=(*GOLD_BRIGHT, int(240 * p_a)), width=2)
            d.text(((W - tw) / 2, 1292), pill, font=fp, fill=(*WHITE, int(252 * p_a)))

    # S10: Neon-Cyan 3D CAD Wireframe morphing live via laser sweep -> Photorealistic CGI Food + Direct CTA!
    elif si == 9:
        cad_cam, _, _, _ = rigid_cam_crop(plates["exploded_cad"], si, u, tau)
        arr_real = np.asarray(frame, dtype=np.uint8)
        arr_cad = np.asarray(cad_cam, dtype=np.uint8)
        sweep_u = min(1.0, u / 0.86)
        e_s = sweep_u * sweep_u * (3.0 - 2.0 * sweep_u)
        beam_y = int(round(220 + 975 * e_s))
        comp = arr_cad.copy()
        if beam_y > 0:
            comp[:min(H, beam_y), :] = arr_real[:min(H, beam_y), :]
        frame = Image.fromarray(comp)

        if 225 < beam_y < 1185:
            d.rectangle([140, beam_y - 8, W - 140, beam_y + 8], fill=(72, 224, 255, 165))
            d.line([(120, beam_y), (W - 120, beam_y)], fill=(255, 255, 255, 240), width=3)

        cta_a = min(1.0, max(0.0, tau / 0.28))
        cta_txt = CONTENT[lang]["s9_cta"]
        f_cta = ImageFont.truetype(str(FONT_BLACK), 25)
        tw = d.textlength(cta_txt, font=f_cta)
        pw = int(tw + 62)
        px0 = (W - pw) // 2
        pulse = 1.0 + 0.015 * math.sin(t * 7.0)
        d.rounded_rectangle([px0, 1246, px0 + pw, 1320], radius=20,
                            fill=(14, 20, 28, int(230 * cta_a)),
                            outline=(*GOLD_BRIGHT, int(245 * cta_a)), width=3)
        d.text(((W - tw) / 2, 1267), cta_txt, font=f_cta, fill=(*GOLD_BRIGHT, int(255 * cta_a * min(1.0, pulse))))

    out_rgba = frame.convert("RGBA")
    out_rgba.alpha_composite(ov)
    return out_rgba


def draw_tracked_pointers(frame_rgba: Image.Image, lang: str, si: int, tau: float,
                          x0: float, y0: float, z: float, t: float):
    anchors = SCENE_ANCHORS.get(si)
    if not anchors:
        return
    labels = CONTENT[lang]["pointers"][si]
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    f_ptr = _font_bold(22)
    cmap = {"coral": CORAL, "cyan": CYAN, "gold": GOLD, "gold_bright": GOLD_BRIGHT, "emerald": EMERALD, "amber": AMBER}

    for (sx_src, sy_src, ldx, ldy, ck, delay), lbl in zip(anchors, labels):
        pop = min(1.0, max(0.0, (tau - delay) / 0.18))
        if pop <= 0.02:
            continue
        pop_e = 1.0 - (1.0 - pop) ** 3
        col = cmap[ck]
        ax, ay = map_pt(sx_src, sy_src, x0, y0, z)
        lx = max(125, min(W - 125, ax + ldx))
        ly = max(168, min(1320, ay + ldy))

        tw = d.textlength(lbl, font=f_ptr)
        pw = int(tw + 32)
        ph = 44
        bx0 = max(36, min(W - 36 - pw, int(lx - pw / 2)))
        by0 = int(ly - ph / 2)
        bx1, by1 = bx0 + pw, by0 + ph

        ecx = bx0 + pw // 2
        ecy = by0 if ay < by0 else (by1 if ay > by1 else by0 + ph // 2)
        mid_x = int(ax + (ecx - ax) * 0.55)
        al_line = int(225 * pop_e)
        d.line([(ax, ay), (mid_x, ecy), (ecx, ecy)], fill=(*col, al_line), width=2)

        pr = 9 + int(2.5 * math.sin(t * 7.5))
        d.ellipse([ax - pr, ay - pr, ax + pr, ay + pr], fill=(*col, int(90 * pop_e)))
        d.ellipse([ax - 5, ay - 5, ax + 5, ay + 5], fill=(*WHITE, int(250 * pop_e)), outline=(*col, al_line), width=2)

        d.rounded_rectangle([bx0, by0, bx1, by1], radius=12,
                            fill=(10, 15, 24, int(218 * pop_e)), outline=(*col, int(235 * pop_e)), width=2)
        d.text((bx0 + 16, by0 + 9), lbl, font=f_ptr, fill=(*WHITE, int(252 * pop_e)))

    frame_rgba.alpha_composite(ov)


def draw_top_badge(frame_rgba: Image.Image, lang: str, si: int, tau: float):
    badge = CONTENT[lang]["badges"][si]
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    f_b = _font_bold(23)
    al = min(1.0, max(0.0, tau / 0.16))
    tw = d.textlength(badge, font=f_b)
    pw = int(tw + 66)
    px0 = (W - pw) // 2
    accent = EMERALD if si == 3 else (GOLD_BRIGHT if si in (1, 6, 9) else CYAN)

    d.rounded_rectangle([px0, 76, px0 + pw, 128], radius=22,
                        fill=(10, 15, 24, int(205 * al)), outline=(*accent, int(195 * al)), width=2)
    d.ellipse([px0 + 18, 95, px0 + 30, 107], fill=(*accent, int(245 * al)))
    d.text((px0 + 42, 88), badge, font=f_b, fill=(*WHITE, int(248 * al)))
    frame_rgba.alpha_composite(ov)


@lru_cache(maxsize=1)
def bottom_scrim_lut() -> np.ndarray:
    y = np.arange(H, dtype=np.float32)[:, None, None]
    fade_y = np.clip((y - 1250.0) / 360.0, 0.0, 1.0)
    return 1.0 - 0.56 * (fade_y ** 1.4)


# ---------------------------------------------------------------------------
# Native Voice TTS + Culinary Physical Foley Audio (100% Halal)
# ---------------------------------------------------------------------------

async def _tts_b2b04_async(lang: str, audio_dir: Path) -> list[tuple[Path, list[dict]]]:
    cfg = VOICE_CFG[lang]
    lines = CONTENT[lang]["script"]
    tts_fix = CONTENT[lang]["tts_fix"]
    manifest_path = audio_dir / "manifest.json"

    lines_hash = hashlib.sha256(
        json.dumps(
            {"voice": cfg["voice"], "fallback": cfg["fallback"], "rate": cfg["rate"], "pitch": cfg["pitch"],
             "lines": lines, "fix": tts_fix},
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
        raise RuntimeError(f"[{lang}] Native Edge TTS synthesis failed on {cfg['voice']} and {cfg['fallback']}.")

    print(f"[B2B-04:{lang.upper()}] Synthesized {len(lines)} lines using native voice: {voice_used}")
    manifest_path.write_text(
        json.dumps({"hash": lines_hash, "voice": voice_used, "items": items_meta}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return results


def synthesize_lang_b2b04(lang: str, build_dir: Path) -> tuple[np.ndarray, list[dict], list[dict], float]:
    lines = CONTENT[lang]["script"]
    raw_items = asyncio.run(_tts_b2b04_async(lang, build_dir))
    segments_audio: list[np.ndarray] = []
    timeline: list[dict] = []
    words_all: list[dict] = []

    cursor = 0.0
    for si, ((mp3_path, bounds), text) in enumerate(zip(raw_items, lines)):
        raw_x = b1._decode_mp3_mono(mp3_path)
        head_pad = 0.025 if si == 0 else 0.030
        tail_pad = 0.035 if si == len(lines) - 1 else 0.050
        seg_x, t0_trim, t1_trim = b1._trim_silence(raw_x, head_pad=head_pad, tail_pad=tail_pad)
        seg_x = b1._voice_fx(seg_x)
        seg_dur = len(seg_x) / SR

        words_seg = b1._align_words(text, bounds, t0_trim, t1_trim, seg_dur, cursor)
        words_all.extend(words_seg)

        timeline.append({"si": si, "t0": cursor, "t1": cursor + seg_dur, "dur": seg_dur})
        segments_audio.append(seg_x)
        cursor += seg_dur

        pause = PAUSE_AFTER[si] if si < len(PAUSE_AFTER) else 0.05
        if pause > 0:
            segments_audio.append(np.zeros(int(round(pause * SR)), dtype=np.float32))
            cursor += pause

    voice_full = np.concatenate(segments_audio).astype(np.float32)
    total_dur = len(voice_full) / SR

    (build_dir / "timeline.json").write_text(json.dumps({"dur": total_dur, "scenes": timeline}, indent=2), encoding="utf-8")
    (build_dir / "words.json").write_text(json.dumps(words_all, ensure_ascii=False, indent=2), encoding="utf-8")
    return voice_full, timeline, words_all, total_dur


def build_food_audio(lang: str, build_dir: Path, voice_mono: np.ndarray, timeline: list[dict], dur: float) -> Path:
    """100% Halal culinary Foley SFX (laser slice, simmer, broth splash, droplet pours, scan) + male a cappella."""
    mix_raw = build_dir / "mix_raw.wav"
    mix_wav = build_dir / "mix_final.wav"
    rng = np.random.default_rng({"ru": 40401, "kz": 40402, "en": 40403}[lang])
    n_samples = len(voice_mono)
    amb = np.zeros((n_samples, 2), dtype=np.float32)

    room = smod.lp(smod.pink(rng, dur + 0.5), 220.0)
    smod.add(amb, smod.st(room[:n_samples], 0.0) * 0.11, 0.0)

    # Subtle male a cappella harmonic pad across 3 acts
    act_defs = [
        (0, 3,  [73.42, 110.0, 146.83], "m", 3, 0.14),
        (3, 7,  [82.41, 123.47, 164.81], "o", 3, 0.15),
        (7, 10, [98.00, 146.83, 196.00], "o", 4, 0.16),
    ]
    for s_lo, s_hi, freqs, vowel, voices, gain in act_defs:
        a0 = timeline[s_lo]["t0"]
        a1 = timeline[s_hi - 1]["t1"]
        pad = smod.reverb(smod.vocal_pad(rng, max(1.0, a1 - a0 + 0.4), freqs, vowel=vowel, voices=voices), wet=0.28, seed=410 + s_lo)
        smod.add(amb, pad * gain, a0)

    for row in timeline:
        si, t0, sd = row["si"], row["t0"], row["dur"]
        if si == 0:
            smod.add(amb, smod.reverb(smod.impact_boom(rng, 0.9), wet=0.20, seed=420) * 0.54, 0.01)
            smod.add(amb, smod.reverb(smod.sword_draw(rng, 0.55), wet=0.16, seed=421) * 0.40, 0.08)
        elif si == 1:
            smod.add(amb, smod.st(smod.whoosh(rng, 0.45), 0.0) * 0.44, t0 + 0.03)
            for k in range(3):
                smod.add(amb, smod.reverb(smod.clasp(rng), wet=0.10, seed=430 + k) * 0.30, t0 + sd * (0.22 + k * 0.22))
        elif si == 2:
            # Gentle boiling broth simmer
            simmer = smod.lp(smod.water(rng, min(2.4, sd * 0.85)), 1600.0)
            smod.add(amb, smod.st(smod.fade(simmer, 0.05, 0.18), -0.1) * 0.32, t0 + 0.04)
        elif si == 3:
            # Soft fluid trickle + UI lock
            smod.add(amb, smod.reverb(smod.clasp(rng), wet=0.12, seed=423) * 0.36, t0 + 0.12)
            smod.add(amb, smod.st(smod.whoosh(rng, 0.36), -0.15) * 0.34, t0 + sd * 0.48)
        elif si == 4:
            # Soft dough tap + gentle liquid soak
            smod.add(amb, smod.reverb(smod.thud(rng), wet=0.14, seed=424) * 0.32, t0 + 0.08)
            smod.add(amb, smod.st(smod.water(rng, min(1.5, sd * 0.6)), 0.12) * 0.24, t0 + 0.22)
        elif si == 5:
            # Hot 95°C broth splash + steam sizzle!
            smod.add(amb, smod.st(smod.water(rng, min(1.8, sd * 0.75)), 0.0) * 0.40, t0 + 0.03)
            smod.add(amb, smod.st(smod.sizzle(rng, min(1.2, sd * 0.55)), 0.15) * 0.30, t0 + 0.08)
        elif si == 6:
            smod.add(amb, smod.reverb(smod.water(rng, min(1.8, sd * 0.7)), wet=0.18, seed=426) * 0.34, t0 + 0.05)
        elif si == 7:
            smod.add(amb, smod.st(smod.whoosh(rng, 0.40), 0.12) * 0.38, t0 + 0.04)
        elif si == 8:
            smod.add(amb, smod.st(smod.whoosh(rng, 0.48), 0.0) * 0.46, t0 + 0.04)
            smod.add(amb, smod.reverb(smod.clasp(rng), wet=0.14, seed=428) * 0.40, t0 + sd * 0.52)
        elif si == 9:
            rlen = min(1.15, sd * 0.45)
            smod.add(amb, smod.st(smod.riser(rng, rlen), 0.0) * 0.36, max(t0, dur - rlen - 0.02))

    rms = smod.frame_rms(voice_mono, win=0.04)
    rms_st = np.interp(np.arange(n_samples), np.arange(len(rms)) * int(SR * 0.04), rms)
    duck = 1.0 - 0.56 * np.clip(rms_st / 0.085, 0.0, 1.0)
    amb *= duck[:, None]

    out = amb * 0.88 + smod.st(voice_mono, 0.0) * 1.00
    out = smod.softclip(out, 0.90)
    smod.write(str(mix_raw), out)
    b1.loudnorm_portable(mix_raw, mix_wav, I=-14.0, TP=-1.5, LRA=11.0)
    return mix_wav


def render_scene_frame(plates: dict[str, Image.Image], lang: str, si: int, u: float, tau: float, t: float,
                       scrim: np.ndarray, vig: np.ndarray) -> Image.Image:
    plate_key_map = {
        0: "s01",
        1: "exploded",
        2: "s04",
        3: "s05_up",
        4: "s03",
        5: "s06",
        6: "s07",
        7: "s02_macro",
        8: "exploded",
        9: "exploded",
    }
    cam_im, x0, y0, z = rigid_cam_crop(plates[plate_key_map[si]], si, u, tau)
    rgba = apply_live_fx(cam_im, plates, si, u, tau, t, x0, y0, z, lang)
    draw_tracked_pointers(rgba, lang, si, tau, x0, y0, z, t)
    draw_top_badge(rgba, lang, si, tau)

    rgb = np.asarray(rgba.convert("RGB"), dtype=np.float32)
    rgb *= scrim
    rgb_v = ((rgb.clip(0, 255).astype(np.uint16) * vig) >> 8).astype(np.uint8)
    return Image.fromarray(rgb_v)


def preview_qa_frames(langs: list[str]):
    plates = load_plates()
    scrim = bottom_scrim_lut()
    vig = rmod.vignette()[..., None]
    qa_dir = PROD / "build_b2b04" / "qa"
    qa_dir.mkdir(parents=True, exist_ok=True)

    sample_subs = {
        "ru": [
            ["РЕЖЕМ", "В", "3D"], ["ЧЕТЫРЕ", "СЛОЯ"], ["НЕЖНЫЙ", "ЖЕЛАТИН"], ["ТЯЖЕСТИ", "НОЛЬ"],
            ["КАК", "ГУБКА"], ["ОШПАРИВАЕТ", "ЛУК"], ["УСВОЕНИЕ", "БЕЛКА"], ["РОВНУЮ", "ЭНЕРГИЮ"],
            ["ПИЩЕВАЯ", "БИОХИМИЯ"], ["ПИШИТЕ", "«3D»"],
        ],
        "kz": [["3D-ДЕ", "АШАЙЫҚ"], ["ТӨРТ", "ҚАБАТ"], ["ЖЕҢІЛ", "ҚОРЫТУ"], ["«3D»", "ЖАЗЫҢЫЗ"]],
        "en": [["SLICE", "INTO", "3D"], ["FOUR", "LAYERS"], ["LIGHT", "LIPIDS"], ["DM", "\"3D\""]],
    }

    for lang in langs:
        scenes_to_check = range(10) if lang == "ru" else (0, 1, 3, 9)
        for idx, si in enumerate(scenes_to_check):
            u = 0.48 if si in (8, 9) else 0.68
            tau = 1.8
            t = si * 3.0 + tau
            frame = render_scene_frame(plates, lang, si, u, tau, t, scrim, vig).convert("RGBA")
            wlist = sample_subs[lang][si if si < len(sample_subs[lang]) else idx % len(sample_subs[lang])]
            words_obj = [{"txt": w, "t0": 0.0, "t1": 1.0} for w in wlist]
            ov = rmod.render_chunk(words_obj, min(1, len(words_obj) - 1))
            frame.paste(ov, (int(W / 2 - ov.width / 2), int(SUB_Y - ov.height / 2)), ov)
            out_p = qa_dir / f"pre_{lang}_s{si:02d}.jpg"
            frame.convert("RGB").save(out_p, "JPEG", quality=92)
            print(f"[B2B-04-PREVIEW] saved {out_p}")


def render_lang_video(lang: str, build_dir: Path, mix_wav: Path, timeline: list[dict],
                      words_all: list[dict], dur: float, out_mp4: Path, plates: dict[str, Image.Image]):
    scrim = bottom_scrim_lut()
    vig = rmod.vignette()[..., None]
    chunks = rmod.chunks_from(words_all, dur)
    chunk_idx = 0
    chunk_cache: dict[tuple[int, int], Image.Image] = {}
    total_frames = int(round(dur * FPS))
    video_silent = build_dir / "video_silent.mp4"

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

            frame_rgb = render_scene_frame(plates, lang, scene_idx, u, tau, t, scrim, vig)
            arr = np.asarray(frame_rgb, dtype=np.float32)

            if scene_idx > 0 and tau < 0.09 and cut_from_rgb is not None:
                alpha = tau / 0.09
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
                print(f"[B2B-04:{lang.upper()}] rendered {fi + 1}/{total_frames} frames ({t:.1f}s/{dur:.1f}s)", flush=True)

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

        print(f"[B2B-04:{lang.upper()}] Synthesizing native narration...")
        voice_mono, timeline, words_all, dur = synthesize_lang_b2b04(lang, build_dir)
        print(f"[B2B-04:{lang.upper()}] Narration ready: {len(timeline)} scenes, {dur:.2f}s, {len(words_all)} words.")

        print(f"[B2B-04:{lang.upper()}] Mixing 3D culinary Foley SFX + a cappella (-14 LUFS)...")
        mix_wav = build_food_audio(lang, build_dir, voice_mono, timeline, dur)

        print(f"[B2B-04:{lang.upper()}] Rendering 1080x1920 @ 30fps -> {out_mp4.name} ...")
        render_lang_video(lang, build_dir, mix_wav, timeline, words_all, dur, out_mp4, plates)
        mb = out_mp4.stat().st_size / (1024 * 1024)
        print(f"[B2B-04:{lang.upper()}] DONE in {time.time() - t_start:.1f}s: {out_mp4} ({mb:.2f} MB, {dur:.2f}s)")


if __name__ == "__main__":
    main()
