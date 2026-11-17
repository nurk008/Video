#!/usr/bin/env python3
"""B2B-03 Flagship 3D CGI Physical Product Breakdown Builder (RU / KZ / EN):
'4,000₸ Fake vs 90,000₸ Original Wireless Earbuds in 3D Laser Cutaway'

Built in Zack D. Films / Animagraffs / Apple commercial pacing (~32-36s total, 12 rapid cuts,
85%+ photorealistic 9:16 3D CGI visuals, camera-tracked hairline pointers, live optical
wave/laser/water/CAD-to-CGI physics overlays, crisp physical Foley + male a cappella audio,
and native Russian, Kazakh & English voiceovers).

Outputs:
  - output/B2B_03_CGI_Earbuds_Shorts_RU.mp4
  - output/B2B_03_CGI_Earbuds_Shorts_KZ.mp4
  - output/B2B_03_CGI_Earbuds_Shorts_EN.mp4

Usage:
    /Users/market/antigravity/Video/.venv/bin/python3 production/build_b2b_03_cgi_multilang.py --preview
    /Users/market/antigravity/Video/.venv/bin/python3 production/build_b2b_03_cgi_multilang.py
    /Users/market/antigravity/Video/.venv/bin/python3 production/build_b2b_03_cgi_multilang.py --lang ru
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import math
import re
import subprocess
import sys
import time
from functools import lru_cache
from pathlib import Path

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont
from scipy import ndimage, signal

ROOT = Path(__file__).resolve().parent.parent
PROD = Path(__file__).resolve().parent
SCENES_DIR = ROOT / "scenes_b2b03"
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

# Brand & Telemetry Palette
GOLD = (255, 198, 56)
GOLD_BRIGHT = (255, 224, 118)
CYAN = (72, 224, 255)
EMERALD = (74, 222, 138)
CORAL = (255, 92, 92)
AMBER = (255, 166, 62)
WHITE = (248, 250, 255)
OBS_BG = (8, 12, 18)

# Native voices only: RU strictly uses native Russian DmitryNeural / SvetlanaNeural
VOICE_CFG = {
    "ru": {
        "voice": "ru-RU-DmitryNeural",
        "fallback": "ru-RU-SvetlanaNeural",
        "rate": "+14%",
        "pitch": "-1Hz",
        "out_file": "B2B_03_CGI_Earbuds_Shorts_RU.mp4",
    },
    "kz": {
        "voice": "kk-KZ-DauletNeural",
        "fallback": "kk-KZ-AigulNeural",
        "rate": "+14%",
        "pitch": "-1Hz",
        "out_file": "B2B_03_CGI_Earbuds_Shorts_KZ.mp4",
    },
    "en": {
        "voice": "en-US-BrianMultilingualNeural",
        "fallback": "en-US-AndrewMultilingualNeural",
        "rate": "+14%",
        "pitch": "-2Hz",
        "out_file": "B2B_03_CGI_Earbuds_Shorts_EN.mp4",
    },
}

PAUSE_AFTER = [0.04, 0.04, 0.05, 0.05, 0.05, 0.04, 0.04, 0.09, 0.05, 0.04, 0.06, 0.02]

# ---------------------------------------------------------------------------
# Camera Rig per Scene: (z0, z1, cx0, cy0, cx1, cy1, shake_amp)
# ---------------------------------------------------------------------------
SCENE_CAM = [
    (1.00, 1.12, 0.50, 0.48, 0.50, 0.47, 3.0),   # S01: Dual hero + laser beam
    (1.08, 1.00, 0.50, 0.47, 0.50, 0.48, 3.5),   # S02: Split laser cutaway Fake vs Orig
    (1.02, 1.16, 0.49, 0.48, 0.52, 0.49, 2.5),   # S03: Fake knockoff macro
    (1.00, 1.09, 0.50, 0.49, 0.50, 0.48, 0.0),   # S04: 8-layer floating exploded view
    (1.02, 1.17, 0.50, 0.47, 0.50, 0.45, 2.5),   # S05: 11mm Titanium dome + copper coil
    (1.02, 1.15, 0.51, 0.50, 0.47, 0.50, 0.0),   # S06: Outer vent + MEMS noise mic
    (1.00, 1.15, 0.50, 0.46, 0.49, 0.44, 0.0),   # S07: DSP silicon chip
    (1.02, 1.14, 0.50, 0.49, 0.50, 0.49, 3.0),   # S08: Smoked chamber wave collision
    (1.04, 1.13, 0.50, 0.42, 0.50, 0.52, 0.0),   # S09: Steel battery + NTC + arcs
    (1.00, 1.12, 0.50, 0.49, 0.50, 0.47, 0.0),   # S10: IPX4 hydrophobic acoustic mesh
    (1.07, 1.00, 0.50, 0.47, 0.50, 0.48, 2.5),   # S11: Optical laser wipe Cutaway -> Hero
    (1.00, 1.07, 0.50, 0.48, 0.50, 0.47, 0.0),   # S12: CAD wireframe -> CGI morph + CTA
]

# Tracked hardware points (src_x, src_y, label_dx, label_dy, color_key, delay_s)
# Coordinates live in 1080x1920 pre-composed scene plate space.
SCENE_ANCHORS = {
    0: [
        (365, 920, -250, 185, "coral", 0.15),
        (720, 920, +235, 185, "cyan", 0.35),
    ],
    1: [
        (275, 650, -170, -185, "coral", 0.22),
        (705, 680, +210, -185, "cyan", 0.40),
    ],
    2: [
        (320, 740, -210, -175, "coral", 0.12),
        (525, 535, +295, -105, "amber", 0.45),
        (640, 1080, +270, +45, "coral", 0.80),
    ],
    3: [
        (540, 390, -310, -40, "cyan", 0.18),
        (540, 680, +310, -25, "gold", 0.45),
        (540, 945, -310, +30, "emerald", 0.72),
    ],
    4: [
        (540, 725, -315, -175, "cyan", 0.16),
        (540, 1130, +315, +95, "gold", 0.48),
    ],
    5: [
        (355, 895, -215, -215, "coral", 0.14),
        (560, 965, +295, -200, "gold", 0.42),
    ],
    6: [
        (510, 770, +270, -235, "cyan", 0.20),
    ],
    7: [
        (365, 920, -210, -245, "coral", 0.12),
        (705, 920, +210, -245, "cyan", 0.35),
        (540, 955, 0, +285, "gold_bright", 0.75),
    ],
    8: [
        (450, 745, -285, -110, "gold", 0.15),
        (635, 890, +275, -35, "cyan", 0.45),
        (545, 1315, +310, +55, "emerald", 0.78),
    ],
    9: [
        (540, 827, +280, -195, "cyan", 0.20),
    ],
}

# ---------------------------------------------------------------------------
# Trilingual Script, Badges & Hardware Labels
# ---------------------------------------------------------------------------
CONTENT = {
    "ru": {
        "script": [
            "Два одинаковых наушника. Один стоит четыре тысячи, другой — девяносто. В чём подвох?",
            "Режем лазером — и сразу видим разницу.",
            "В дешёвой копии — тонкая плёнка, термоклей и голая фольга вместо защиты.",
            "А вот восемь точных слоёв оригинальной сборки в воздухе.",
            "Титановый драйвер одиннадцать миллиметров с медной катушкой даёт чистый бас без хрипа.",
            "Внешний микрофон ловит шум улицы ещё до уха.",
            "Чип за пять миллисекунд строит зеркальный сигнал.",
            "Волны сталкиваются в камере — и шум исчезает в ноль.",
            "В ножке — стальная батарея в термозащите: восемь часов без перегрева.",
            "А нано-сетка на сопле отталкивает пот и дождь.",
            "Снаружи оба белые — но внутри пропасть качества.",
            "Продаёте товар? Покажем ваш продукт в таком же 3D-разрезе — пишите «3D» в Дайрект!",
        ],
        "tts_fix": [("3D-", "три-дэ "), ("«3D»", "три дэ"), ("3D", "три дэ")],
        "badges": [
            "01/12  •  КОПИЯ vs ОРИГИНАЛ",
            "02/12  •  ЛАЗЕРНЫЙ РАЗРЕЗ",
            "03/12  •  ДЕШЁВАЯ КОПИЯ",
            "04/12  •  8 СЛОЁВ ОРИГИНАЛА",
            "05/12  •  ТИТАН + МЕДЬ",
            "06/12  •  ЗАХВАТ ШУМА",
            "07/12  •  ПРОЦЕССОР ANC",
            "08/12  •  ФИЗИКА -48 дБ",
            "09/12  •  ПИТАНИЕ И ЗАЩИТА",
            "10/12  •  БАРЬЕР IPX4",
            "11/12  •  ИТОГ СРАВНЕНИЯ",
            "12/12  •  3D ДЛЯ ВАШЕГО ТОВАРА",
        ],
        "pointers": {
            0: ["4 000 ₸", "90 000 ₸"],
            1: ["КЛЕЙ + БРАК", "ТИТАН + МЕДЬ"],
            2: ["ПЛЁНКА 6 ММ", "ТЕРМОКЛЕЙ", "ГОЛАЯ ФОЛЬГА"],
            3: ["СЕТКА IPX4", "ТИТАН 11 ММ", "ANC ЧИП"],
            4: ["ТИТАН + КАРБОН", "МЕДНАЯ КАТУШКА"],
            5: ["ШУМ УЛИЦЫ", "MEMS-МИКРОФОН"],
            6: ["DSP ЧИП • 0.005с"],
            7: ["+ ШУМ", "- АНТИВОЛНА", "ТИШИНА • -48 дБ"],
            8: ["СТАЛЬ + КАПТОН", "ТЕРМОДАТЧИК", "8ч БЕЗ НАГРЕВА"],
            9: ["IPX4 • НАНО-СЕТКА"],
        },
        "s10_vs": ("КОПИЯ: ШУМ И БРАК", "ОРИГИНАЛ: -48 дБ • 8ч"),
        "s11_cta": "ВАШ ТОВАР В 3D  •  ПИШИТЕ «3D» В DIRECT",
    },
    "kz": {
        "script": [
            "Сырты бірдей екі құлаққап. Бірі төрт мың, бірі тоқсан мың. Айырмасы неде?",
            "Лазермен кесіп, ішін бірден ашайық.",
            "Арзан көшірмеде — жұқа пленка, ерітілген желім және қорғаныссыз фольга.",
            "Ал түпнұсқа ішінде сегіз дәл инженерлік қабат бар.",
            "Титан драйвері мен мыс орамы бұрмалаусыз таза бас береді.",
            "Сыртқы микрофон көше шуын құлаққа жеткізбей ұстайды.",
            "Чип бес миллисекундта айнадай қарсы толқын жасайды.",
            "Қос толқын соғысып, шу нөлге дейін өшеді.",
            "Сабында — термоқорғаулы болат батарея: сегіз сағат қызусыз жұмыс.",
            "Ал болат тор тер мен жаңбыр тамшысын өткізбейді.",
            "Сырты ұқсас — бірақ ішкі сапасы жер мен көктей.",
            "Тауар сатасыз ба? Өніміңізді дәл осындай 3D-разрезде жасаймыз — Дайректке «3D» деп жазыңыз!",
        ],
        "tts_fix": [("3D-разрезде", "три-дэ разрезде"), ("«3D»", "три дэ"), ("3D", "три дэ")],
        "badges": [
            "01/12  •  КӨШІРМЕ vs ТҮПНҰСҚА",
            "02/12  •  ЛАЗЕРЛІК КЕСІНДІ",
            "03/12  •  АРЗАН КӨШІРМЕ",
            "04/12  •  ТҮПНҰСҚА: 8 ҚАБАТ",
            "05/12  •  ТИТАН + МЫС",
            "06/12  •  ШУДЫ ҰСТАУ",
            "07/12  •  ANC ПРОЦЕССОРЫ",
            "08/12  •  ФИЗИКА -48 дБ",
            "09/12  •  ҚУАТ ЖӘНЕ ҚОРҒАНЫС",
            "10/12  •  IPX4 ҚОРҒАНЫСЫ",
            "11/12  •  НЕГІЗГІ АЙЫРМА",
            "12/12  •  ТАУАРҒА 3D-ШОЛУ",
        ],
        "pointers": {
            0: ["4 000 ₸", "90 000 ₸"],
            1: ["ЖЕЛІМ + БРАК", "ТИТАН + МЫС"],
            2: ["ПЛЕНКА 6 ММ", "ТЕРМОЖЕЛІМ", "БОС ФОЛЬГА"],
            3: ["IPX4 ТОР", "ТИТАН 11 ММ", "ANC ЧИП"],
            4: ["ТИТАН + КАРБОН", "МЫС ОРАМЫ"],
            5: ["КӨШЕ ШУЫ", "MEMS-ДАТЧИК"],
            6: ["DSP ЧИП • 0.005с"],
            7: ["+ ШУ", "- ҚАРСЫ ТОЛҚЫН", "ТЫНЫШТЫҚ • -48 дБ"],
            8: ["БОЛАТ + КАПТОН", "ТЕРМОДАТЧИК", "8 САҒ ҚЫЗУСЫЗ"],
            9: ["IPX4 • НАНО-ТОР"],
        },
        "s10_vs": ("КӨШІРМЕ: ШУ МЕН БРАК", "ТҮПНҰСҚА: -48 дБ • 8 САҒ"),
        "s11_cta": "ӨНІМІҢІЗ 3D-ДЕ  •  DIRECT-КЕ «3D» ЖАЗЫҢЫЗ",
    },
    "en": {
        "script": [
            "Two identical earbuds. One costs ten bucks, the other two hundred. Why?",
            "Slice both open — and the difference is shocking.",
            "Inside the fake: paper-thin film, hot glue blobs, and a sparking foil pouch.",
            "Inside the original: eight precision-engineered floating layers.",
            "An eleven-millimeter titanium dome with copper voice coil delivers crystal bass.",
            "An outer MEMS mic traps street roar before it enters your ear.",
            "In five milliseconds, the DSP chip builds an inverted sound wave.",
            "Both waves collide mid-air — canceling harsh noise into silence.",
            "Inside the stem: a shielded steel battery delivering eight hours, zero overheat.",
            "And a nano-coated steel mesh bounces sweat and rain right off.",
            "Same white shell outside — completely different worlds inside.",
            "Selling physical products? We animate your product in 3D cutaway — DM \"3D\" today!",
        ],
        "tts_fix": [("3D", "three-D"), ("\"3D\"", "three D"), ("MEMS", "mems"), ("DSP", "D S P")],
        "badges": [
            "01/12  •  FAKE vs ORIGINAL",
            "02/12  •  3D LASER CUTAWAY",
            "03/12  •  INSIDE THE KNOCKOFF",
            "04/12  •  8 PRECISION LAYERS",
            "05/12  •  11MM TITANIUM DRIVER",
            "06/12  •  NOISE CAPTURE MIC",
            "07/12  •  5MS DSP PROCESSOR",
            "08/12  •  -48 dB CANCELLATION",
            "09/12  •  SHIELDED POWER STEM",
            "10/12  •  IPX4 NANO MESH",
            "11/12  •  THE REAL GAP",
            "12/12  •  3D FOR YOUR BRAND",
        ],
        "pointers": {
            0: ["$10 FAKE", "$200 ORIGINAL"],
            1: ["GLUE + FOIL", "TITANIUM + COPPER"],
            2: ["6MM FILM", "HOT GLUE", "BARE POUCH"],
            3: ["STEEL MESH", "11MM TITANIUM", "ANC CHIP"],
            4: ["TITANIUM + CARBON", "COPPER COIL"],
            5: ["STREET NOISE", "MEMS MIC"],
            6: ["DSP • 0.005s"],
            7: ["+ NOISE", "- ANTI-WAVE", "SILENCE • -48 dB"],
            8: ["STEEL + KAPTON", "NTC SENSOR", "8H ZERO HEAT"],
            9: ["IPX4 • NANO MESH"],
        },
        "s10_vs": ("FAKE: NOISE + RISK", "ORIGINAL: -48 dB • 8H"),
        "s11_cta": "YOUR PRODUCT IN 3D  •  DM «3D» NOW",
    },
}


# ---------------------------------------------------------------------------
# Verification: Fonts, Glyphs & Bounds
# ---------------------------------------------------------------------------

def _font_bold(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_BOLD), size)


def verify_all_texts():
    f_bad = _font_bold(23)
    f_ptr = _font_bold(22)
    f_cta = ImageFont.truetype(str(FONT_BLACK), 26)
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
            if d.textlength(b, font=f_bad) > W - 160:
                raise ValueError(f"[{lang}] Badge too wide: {b}")
        for si, plist in L["pointers"].items():
            for lbl in plist:
                check_str(lbl)
                if d.textlength(lbl, font=f_ptr) > 360:
                    raise ValueError(f"[{lang}] Pointer label too wide in S{si:02d}: {lbl}")
        for s in L["s10_vs"]:
            check_str(s)
            if d.textlength(s, font=f_ptr) > 430:
                raise ValueError(f"[{lang}] S10 badge too wide: {s}")
        check_str(L["s11_cta"])
        if d.textlength(L["s11_cta"], font=f_cta) > W - 150:
            raise ValueError(f"[{lang}] S12 CTA too wide: {L['s11_cta']}")
        for line in L["script"]:
            check_str(line)


# ---------------------------------------------------------------------------
# Photorealistic 3D CGI Plates & Wireframe Blueprint Pre-Generation
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def load_plates() -> dict[str, Image.Image]:
    """Load and prepare all 9 base 3D CGI plates plus re-framed exploded, CAD wireframe & IPX4 macro plates."""
    plates: dict[str, Image.Image] = {}
    for i in range(1, 10):
        p = SCENES_DIR / f"scene_{i:02d}.jpg"
        im = Image.open(p).convert("RGB").resize((W, H), Image.Resampling.LANCZOS)
        im = ImageEnhance.Sharpness(im).enhance(1.12)
        plates[f"s{i:02d}"] = im

    # Re-frame scene_03 (8-layer exploded view) with seamless elliptical obsidian blend inside y=200..1215
    s3_arr = np.asarray(plates["s03"], dtype=np.float32)
    bg_col = np.array([3.0, 6.0, 12.0], dtype=np.float32)
    crop3 = s3_arr[95:1645, 130:950]  # 820 x 1550
    ch, cw = crop3.shape[:2]
    yy, xx = np.mgrid[0:ch, 0:cw].astype(np.float32)
    dx = (xx - cw * 0.5) / (cw * 0.44)
    dy = (yy - ch * 0.5) / (ch * 0.49)
    rr = np.sqrt(dx * dx + dy * dy)
    t_f = np.clip((rr - 0.72) / 0.26, 0.0, 1.0)
    alpha3 = (0.5 * (1.0 + np.cos(math.pi * t_f)))[..., None]
    # Fade non-object background gently into exact obsidian void
    diff3 = np.linalg.norm(crop3 - bg_col, axis=2, keepdims=True)
    obj_boost = np.clip((diff3 - 42.0) / 35.0, 0.0, 1.0)
    blend3 = np.maximum(alpha3, obj_boost * alpha3)
    feathered = (crop3 * blend3 + bg_col[None, None, :] * (1.0 - blend3)).clip(0, 255).astype(np.uint8)

    scale3 = 0.65
    nw, nh = int(round(cw * scale3)), int(round(ch * scale3))  # ~533 x 1008
    scaled3 = Image.fromarray(feathered).resize((nw, nh), Image.Resampling.LANCZOS)
    canvas3 = Image.new("RGB", (W, H), tuple(int(c) for c in bg_col))
    canvas3.paste(scaled3, ((W - nw) // 2, 200))
    plates["exploded"] = canvas3

    # Neon-Cyan 3D CAD Wireframe extracted from `exploded`, matching exact obsidian bg everywhere
    arr_ex = np.asarray(canvas3, dtype=np.float32)
    gray = 0.299 * arr_ex[..., 0] + 0.587 * arr_ex[..., 1] + 0.114 * arr_ex[..., 2]
    gx = ndimage.sobel(gray, axis=1)
    gy = ndimage.sobel(gray, axis=0)
    edge = np.hypot(gx, gy)
    edge_n = np.clip((edge - 18.0) / 135.0, 0.0, 1.0) ** 0.70
    glow = ndimage.gaussian_filter(edge_n, sigma=2.4)

    yy_g, xx_g = np.mgrid[0:H, 0:W].astype(np.float32)
    env_g = np.exp(-(((xx_g - W * 0.5) / 290.0) ** 2 + ((yy_g - 705.0) / 510.0) ** 2))
    grid_mask = (((yy_g.astype(int) % 60 == 0) | (xx_g.astype(int) % 60 == 0)).astype(np.float32)) * 0.10 * env_g

    cad = np.empty_like(arr_ex)
    cad[..., 0] = bg_col[0] + 20.0 * glow + 60.0 * edge_n + 24.0 * grid_mask
    cad[..., 1] = bg_col[1] + 135.0 * glow + 225.0 * edge_n + 100.0 * grid_mask
    cad[..., 2] = bg_col[2] + 185.0 * glow + 255.0 * edge_n + 145.0 * grid_mask
    plates["exploded_cad"] = Image.fromarray(cad.clip(0, 255).astype(np.uint8))

    # IPX4 Hydrophobic Acoustic Mesh Macro (tight crop omitting bottom white bud bump)
    mesh_crop = s3_arr[105:495, 220:860]  # 640 x 390
    mh, mw = mesh_crop.shape[:2]
    ym, xm = np.mgrid[0:mh, 0:mw].astype(np.float32)
    rm = np.sqrt(((xm - mw * 0.5) / (mw * 0.46)) ** 2 + ((ym - mh * 0.48) / (mh * 0.46)) ** 2)
    tm_f = np.clip((rm - 0.50) / 0.46, 0.0, 1.0)
    m_alpha = (0.5 * (1.0 + np.cos(math.pi * tm_f)))[..., None]
    mesh_f = (mesh_crop * m_alpha + bg_col[None, None, :] * (1.0 - m_alpha)).clip(0, 255).astype(np.uint8)
    m_scale = 1.56
    mw2, mh2 = int(round(mw * m_scale)), int(round(mh * m_scale))  # ~998 x 608
    mesh_big = Image.fromarray(mesh_f).resize((mw2, mh2), Image.Resampling.LANCZOS)
    canvas_m = Image.new("RGB", (W, H), tuple(int(c) for c in bg_col))
    canvas_m.paste(mesh_big, ((W - mw2) // 2, 340))
    plates["mesh_macro"] = canvas_m
    return plates


def rigid_cam_crop(im_src: Image.Image, si: int, u: float, tau: float) -> tuple[Image.Image, float, float, float]:
    """Rigid scale + translation with micro-impact shake on cut; returns (frame_rgb, x0, y0, z)."""
    z0, z1, cx0, cy0, cx1, cy1, sh = SCENE_CAM[si]
    e = u * u * (3.0 - 2.0 * u)
    z = z0 + (z1 - z0) * e
    cx = cx0 + (cx1 - cx0) * e
    cy = cy0 + (cy1 - cy0) * e

    vw = W / z
    vh = H / z
    x0 = max(0.0, min(W - vw, cx * W - vw * 0.5))
    y0 = max(0.0, min(H - vh, cy * H - vh * 0.5))

    if sh > 0.0 and tau < 0.22:
        decay = (1.0 - tau / 0.22) ** 2
        dx = sh * decay * math.sin(tau * 68.0) / z
        dy = sh * decay * math.cos(tau * 54.0) / z
        x0 = max(0.0, min(W - vw, x0 + dx))
        y0 = max(0.0, min(H - vh, y0 + dy))

    if si == 3:  # Gentle magnetic hover float on exploded assembly
        y0 = max(0.0, min(H - vh, y0 + math.sin(tau * 3.1) * 5.0 / z))

    frame = im_src.transform((W, H), Image.Transform.EXTENT, (x0, y0, x0 + vw, y0 + vh), Image.Resampling.BICUBIC)
    return frame, x0, y0, z


def map_pt(src_x: float, src_y: float, x0: float, y0: float, z: float) -> tuple[int, int]:
    return int(round((src_x - x0) * z)), int(round((src_y - y0) * z))


# ---------------------------------------------------------------------------
# Live Photorealistic Optical / Acoustic / Fluid Physics Overlays
# ---------------------------------------------------------------------------

def apply_live_fx(frame: Image.Image, plates: dict[str, Image.Image], si: int, u: float, tau: float, t: float,
                  x0: float, y0: float, z: float, lang: str) -> Image.Image:
    """Layer optical laser beams, acoustic wave interference, water rebounds & CAD-to-CGI morphs."""
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)

    # S01: Traveling white-hot hotspot sliding along exact slanted laser line (796->775) + studio dust
    if si == 0:
        lx_src = 120.0 + ((u * 1.45) % 1.0) * 840.0
        ly_src = 796.0 + (775.0 - 796.0) * ((lx_src - 100.0) / 870.0)
        lx, ly = map_pt(lx_src, ly_src, x0, y0, z)
        d.ellipse([lx - 42, ly - 5, lx + 42, ly + 5], fill=(255, 80, 80, 65))
        d.ellipse([lx - 20, ly - 3, lx + 20, ly + 3], fill=(255, 175, 160, 130))
        d.ellipse([lx - 9, ly - 2, lx + 9, ly + 2], fill=(255, 248, 240, 225))
        b1.draw_particles_studio(ov, t, seed=31, count=14)

    # S02: Crisp vertical laser opening flash + foil sparks
    elif si == 1:
        if tau < 0.24:
            p = 1.0 - tau / 0.24
            vx = int(W * (0.15 + 0.70 * (tau / 0.24)))
            d.rectangle([vx - 8, 280, vx + 8, 1280], fill=(95, 235, 255, int(185 * p)))
            d.line([(vx, 280), (vx, 1280)], fill=(255, 255, 255, int(235 * p)), width=3)
        sx, sy = map_pt(388, 1020, x0, y0, z)
        for k in range(5):
            ang = t * 6.0 + k * 1.25
            r = 8 + ((t * 45 + k * 7) % 28)
            a = int(200 * (1.0 - r / 38.0))
            d.ellipse([sx + math.cos(ang) * r - 3, sy + math.sin(ang) * r - 3,
                       sx + math.cos(ang) * r + 3, sy + math.sin(ang) * r + 3], fill=(255, 175, 65, a))

    # S03: Counterfeit short-circuit ember burst
    elif si == 2:
        sx, sy = map_pt(698, 922, x0, y0, z)
        pulse = 0.6 + 0.4 * math.sin(t * 16.0)
        d.ellipse([sx - 34, sy - 34, sx + 34, sy + 34], fill=(255, 120, 40, int(90 * pulse)))
        for k in range(7):
            ph = (t * 2.4 + k * 0.21) % 1.0
            px = sx + math.sin(k * 2.1) * 44 * ph
            py = sy - 58 * ph + 20 * ph * ph
            a = int(220 * (1.0 - ph))
            d.ellipse([px - 3, py - 3, px + 3, py + 3], fill=(255, 210, 95, a))

    # S04: Cascading holographic highlight ring descending across 8 floating exploded parts
    elif si == 3:
        scan_src_y = 260 + ((tau * 520.0) % 920.0)
        sx, sy = map_pt(540, scan_src_y, x0, y0, z)
        d.ellipse([sx - 165, sy - 16, sx + 165, sy + 16], outline=(78, 224, 255, 110), width=3)
        b1.draw_particles_studio(ov, t, seed=34, count=14)

    # S05: Animated concentric golden acoustic waves rising from vibrating titanium dome
    elif si == 4:
        dx, dy = map_pt(540, 745, x0, y0, z)
        for k in range(4):
            ph = (t * 1.45 + k * 0.25) % 1.0
            rx = int(130 + ph * 225)
            ry = int(34 + ph * 64)
            yy = int(dy - ph * 175)
            a = int(165 * (1.0 - ph) ** 1.3)
            d.ellipse([dx - rx, yy - ry, dx + rx, yy + ry], outline=(255, 206, 95, a), width=4)

    # S06: Chaotic red incoming street-noise wavefront pulsing toward MEMS sensor
    elif si == 5:
        mx, my = map_pt(475, 920, x0, y0, z)
        for k in range(4):
            ph = (t * 1.8 + k * 0.25) % 1.0
            wx = int(mx - (1.0 - ph) * 320)
            rad_y = int(175 - ph * 105)
            a = int(185 * math.sin(ph * math.pi))
            d.arc([wx - 65, my - rad_y, wx + 65, my + rad_y], start=295, end=65, fill=(255, 86, 86, a), width=4)

    # S07: Fast high-frequency cyan telemetry pulses shooting out from DSP silicon die
    elif si == 6:
        cx_p, cy_p = map_pt(510, 770, x0, y0, z)
        for k in range(6):
            ang = k * (math.pi / 3.0) + 0.35
            ph = (t * 3.1 + k * 0.16) % 1.0
            r = 125 + ph * 175
            px = cx_p + math.cos(ang) * r
            py = cy_p + math.sin(ang) * r * 0.68
            a = int(230 * (1.0 - ph))
            d.ellipse([px - 8, py - 8, px + 8, py + 8], fill=(82, 236, 255, a))

    # S08: Real-time red noise sine colliding with inverted cyan anti-wave -> zero at center!
    elif si == 7:
        lx, cy_w = map_pt(235, 938, x0, y0, z)
        cx_w, _ = map_pt(535, 938, x0, y0, z)
        rx, _ = map_pt(810, 938, x0, y0, z)
        pts_r = []
        for x in range(lx, cx_w + 1, 8):
            rel = max(0.0, min(1.0, (x - lx) / max(1, cx_w - lx)))
            amp = 48.0 * (1.0 - 0.90 * (rel ** 2.2))
            y = cy_w + amp * math.sin(rel * 16.0 - t * 14.0)
            pts_r.append((int(x), int(round(y))))
        pts_c = []
        for x in range(cx_w, rx + 1, 8):
            rel = max(0.0, min(1.0, (rx - x) / max(1, rx - cx_w)))
            amp = 48.0 * (1.0 - 0.90 * (rel ** 2.2))
            y = cy_w - amp * math.sin(rel * 16.0 - t * 14.0)
            pts_c.append((int(x), int(round(y))))
        if len(pts_r) >= 2:
            d.line(pts_r, fill=(255, 84, 84, 155), width=3)
        if len(pts_c) >= 2:
            d.line(pts_c, fill=(74, 228, 255, 155), width=3)
        d.line([(cx_w - 38, cy_w), (cx_w + 38, cy_w)], fill=(255, 232, 130, 210), width=3)

    # S09: Electric cyan magnetic charging arcs orbiting gold base contacts
    elif si == 8:
        gx, gy = map_pt(530, 1298, x0, y0, z)
        for k in range(3):
            ph = (t * 2.2 + k * 0.33) % 1.0
            rx = int(115 + ph * 85)
            ry = int(26 + ph * 22)
            a = int(210 * (1.0 - ph))
            d.arc([gx - rx, gy - ry, gx + rx, gy + ry], start=10, end=170, fill=(85, 234, 255, a), width=4)

    # S10: Slow-motion glistening 3D water spheres bouncing off stainless IPX4 mesh!
    elif si == 9:
        mx, my = map_pt(540, 827, x0, y0, z)
        drops = [
            (-160, 0.00, -55, 13), (-85, 0.22, -28, 16), (0, 0.45, +12, 18),
            (+85, 0.15, +35, 15), (+155, 0.62, +58, 12), (-120, 0.78, -42, 14),
            (+45, 0.88, +22, 13), (-40, 0.34, -18, 15),
        ]
        for dx0, ph0, vx_dir, rad in drops:
            ph = (t * 0.85 + ph0) % 1.0
            if ph < 0.48:
                u_d = ph / 0.48
                px = mx + dx0 * (0.7 + 0.3 * u_d)
                py = (my - 300) + 300 * (u_d * u_d)
                sx, sy = rad, rad
            else:
                u_b = (ph - 0.48) / 0.52
                px = mx + dx0 + vx_dir * u_b * 2.2
                py = my - 135 * (4.0 * u_b * (1.0 - u_b))
                squash = 1.0 + 0.35 * max(0.0, 1.0 - u_b * 4.0)
                sx, sy = int(rad * squash), max(6, int(rad / squash))
            a = int(225 * (1.0 - max(0.0, (ph - 0.82) / 0.18)))
            d.ellipse([px - sx, py - sy, px + sx, py + sy],
                      fill=(95, 224, 255, int(105 * a / 255)),
                      outline=(185, 245, 255, int(205 * a / 255)), width=2)
            d.ellipse([px - sx * 0.48, py - sy * 0.48, px - sx * 0.08, py - sy * 0.08],
                      fill=(255, 255, 255, a))

    # S11: Dynamic neon laser reassembly wipe (Cutaway Split -> Gleaming Closed Pair!)
    elif si == 10:
        w_u = min(1.0, max(0.0, (u - 0.06) / 0.58))
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
            d.rectangle([split_x - 10, 260, split_x + 10, 1260], fill=(72, 224, 255, 165))
            d.line([(split_x, 260), (split_x, 1260)], fill=(255, 255, 255, 245), width=4)

        # Compact floating verdict pills (appear smoothly after wipe sweeps across)
        v_a = min(1.0, max(0.0, (u - 0.42) / 0.22))
        if v_a > 0.02:
            bad_lbl, good_lbl = CONTENT[lang]["s10_vs"]
            fp = _font_bold(22)
            for is_bad, bx, lbl, col, bg_c in (
                (True, 290, bad_lbl, CORAL, (38, 14, 16)),
                (False, 790, good_lbl, EMERALD, (12, 34, 24)),
            ):
                tw = d.textlength(lbl, font=fp)
                pw = int(tw + 66)
                x_l, x_r = int(bx - pw // 2), int(bx + pw // 2)
                al_b = int(225 * v_a)
                d.rounded_rectangle([x_l, 1175, x_r, 1230], radius=14,
                                    fill=(*bg_c, al_b), outline=(*col, int(245 * v_a)), width=2)
                ix, iy = x_l + 22, 1202
                if is_bad:
                    d.line([(ix - 7, iy - 7), (ix + 7, iy + 7)], fill=(*col, int(250 * v_a)), width=3)
                    d.line([(ix - 7, iy + 7), (ix + 7, iy - 7)], fill=(*col, int(250 * v_a)), width=3)
                else:
                    b1.draw_vector_check(d, ix, iy, 9, (*col, int(250 * v_a)))
                d.text((x_l + 42, 1188), lbl, font=fp, fill=(*WHITE, int(252 * v_a)))

    # S12: CAD Wireframe-to-Photorealistic CGI Laser Sweep + Compact B2B Offer Pill!
    elif si == 11:
        cad_cam, _, _, _ = rigid_cam_crop(plates["exploded_cad"], si, u, tau)
        arr_real = np.asarray(frame, dtype=np.uint8)
        arr_cad = np.asarray(cad_cam, dtype=np.uint8)
        # Sweep laser cleanly down across u=0.0..0.88 converting cyan CAD wireframe -> real CGI
        sweep_u = min(1.0, u / 0.88)
        e_s = sweep_u * sweep_u * (3.0 - 2.0 * sweep_u)
        beam_y = int(round(205 + 1015 * e_s))
        comp = arr_cad.copy()
        if beam_y > 0:
            comp[:min(H, beam_y), :] = arr_real[:min(H, beam_y), :]
        frame = Image.fromarray(comp)

        if 210 < beam_y < 1215:
            d.rectangle([180, beam_y - 8, W - 180, beam_y + 8], fill=(72, 224, 255, 165))
            d.line([(160, beam_y), (W - 160, beam_y)], fill=(255, 255, 255, 240), width=3)

        # Compact B2B CTA pill nestled cleanly between model bottom (y=1215) & SUB_Y (1495)
        cta_a = min(1.0, max(0.0, tau / 0.30))
        cta_txt = CONTENT[lang]["s11_cta"]
        f_cta = ImageFont.truetype(str(FONT_BLACK), 26)
        tw = d.textlength(cta_txt, font=f_cta)
        pw = int(tw + 64)
        px0 = (W - pw) // 2
        pulse = 1.0 + 0.015 * math.sin(t * 7.0)
        d.rounded_rectangle([px0, 1252, px0 + pw, 1326], radius=20,
                            fill=(14, 20, 30, int(230 * cta_a)),
                            outline=(*GOLD_BRIGHT, int(245 * cta_a)), width=3)
        d.text(((W - tw) / 2, 1272), cta_txt, font=f_cta, fill=(*GOLD_BRIGHT, int(255 * cta_a * min(1.0, pulse))))

    out_rgba = frame.convert("RGBA")
    out_rgba.alpha_composite(ov)
    return out_rgba


# ---------------------------------------------------------------------------
# Camera-Tracked Minimalist Hardware Pointers & Top Glass Capsule HUD
# ---------------------------------------------------------------------------

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
        ly = max(168, min(1330, ay + ldy))

        tw = d.textlength(lbl, font=f_ptr)
        pw = int(tw + 32)
        ph = 44
        # Clamp box strictly inside margins [36, W - 36]
        bx0 = max(36, min(W - 36 - pw, int(lx - pw / 2)))
        by0 = int(ly - ph / 2)
        bx1, by1 = bx0 + pw, by0 + ph

        # Anchor point on box edge nearest the hardware target
        ecx = bx0 + pw // 2
        ecy = by0 if ay < by0 else (by1 if ay > by1 else by0 + ph // 2)
        # Elbow waypoint for crisp engineering CAD leader
        mid_x = int(ax + (ecx - ax) * 0.55)
        al_line = int(225 * pop_e)
        d.line([(ax, ay), (mid_x, ecy), (ecx, ecy)], fill=(*col, al_line), width=2)

        # Glowing target dot on physical 3D component
        pr = 9 + int(2.5 * math.sin(t * 7.5))
        d.ellipse([ax - pr, ay - pr, ax + pr, ay + pr], fill=(*col, int(90 * pop_e)))
        d.ellipse([ax - 5, ay - 5, ax + 5, ay + 5], fill=(*WHITE, int(250 * pop_e)), outline=(*col, al_line), width=2)

        # Sleek dark frosted floating pill
        d.rounded_rectangle([bx0, by0, bx1, by1], radius=12,
                            fill=(10, 15, 24, int(218 * pop_e)), outline=(*col, int(235 * pop_e)), width=2)
        d.text((bx0 + 16, by0 + 9), lbl, font=f_ptr, fill=(*WHITE, int(252 * pop_e)))

    frame_rgba.alpha_composite(ov)


def draw_top_badge(frame_rgba: Image.Image, lang: str, si: int, tau: float):
    """Draw ONE ultra-compact dark frosted topic pill (leaves 90%+ screen clean for 3D CGI)."""
    badge = CONTENT[lang]["badges"][si]
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    f_b = _font_bold(23)
    al = min(1.0, max(0.0, tau / 0.16))
    tw = d.textlength(badge, font=f_b)
    pw = int(tw + 66)
    px0 = (W - pw) // 2
    accent = CORAL if si in (2,) else (GOLD_BRIGHT if si in (4, 11) else CYAN)

    d.rounded_rectangle([px0, 76, px0 + pw, 128], radius=22,
                        fill=(10, 15, 24, int(205 * al)), outline=(*accent, int(195 * al)), width=2)
    d.ellipse([px0 + 18, 95, px0 + 30, 107], fill=(*accent, int(245 * al)))
    d.text((px0 + 42, 88), badge, font=f_b, fill=(*WHITE, int(248 * al)))
    frame_rgba.alpha_composite(ov)


@lru_cache(maxsize=1)
def bottom_scrim_lut() -> np.ndarray:
    """Smooth dark vignette gradient across y=1260..1920 so crisp subtitles always pop over CGI."""
    y = np.arange(H, dtype=np.float32)[:, None, None]
    fade_y = np.clip((y - 1250.0) / 360.0, 0.0, 1.0)
    return 1.0 - 0.56 * (fade_y ** 1.4)


# ---------------------------------------------------------------------------
# Native Voice TTS + Physical Product Foley Mix
# ---------------------------------------------------------------------------

async def _tts_b2b03_async(lang: str, audio_dir: Path) -> list[tuple[Path, list[dict]]]:
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

    print(f"[B2B-03:{lang.upper()}] Synthesized {len(lines)} lines using native voice: {voice_used}")
    manifest_path.write_text(
        json.dumps({"hash": lines_hash, "voice": voice_used, "items": items_meta}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return results


def synthesize_lang_b2b03(lang: str, build_dir: Path) -> tuple[np.ndarray, list[dict], list[dict], float]:
    lines = CONTENT[lang]["script"]
    raw_items = asyncio.run(_tts_b2b03_async(lang, build_dir))
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

        pause = PAUSE_AFTER[si] if si < len(PAUSE_AFTER) else 0.04
        if pause > 0:
            segments_audio.append(np.zeros(int(round(pause * SR)), dtype=np.float32))
            cursor += pause

    voice_full = np.concatenate(segments_audio).astype(np.float32)
    total_dur = len(voice_full) / SR

    (build_dir / "timeline.json").write_text(json.dumps({"dur": total_dur, "scenes": timeline}, indent=2), encoding="utf-8")
    (build_dir / "words.json").write_text(json.dumps(words_all, ensure_ascii=False, indent=2), encoding="utf-8")
    return voice_full, timeline, words_all, total_dur


def _water_blip(rng, freq: float = 950.0) -> np.ndarray:
    """Crisp short water droplet rebound pop on metal mesh (physics-modeled sine chirp)."""
    d = 0.085
    t = smod.tt(d)
    f_sweep = freq * np.exp(t * 9.0)
    return smod.fade(np.sin(2.0 * math.pi * np.cumsum(f_sweep) / SR) * np.exp(-t * 42.0), 0.002, 0.025)


def build_cgi_audio(lang: str, build_dir: Path, voice_mono: np.ndarray, timeline: list[dict], dur: float) -> Path:
    """Halal 3D CGI Foley SFX (laser sweep, sparks, sub pressure, ANC silence drop, droplet pops) + male a cappella pad."""
    mix_raw = build_dir / "mix_raw.wav"
    mix_wav = build_dir / "mix_final.wav"
    rng = np.random.default_rng({"ru": 30301, "kz": 30302, "en": 30303}[lang])
    n_samples = len(voice_mono)
    amb = np.zeros((n_samples, 2), dtype=np.float32)

    # Low studio air floor
    room = smod.lp(smod.pink(rng, dur + 0.5), 210.0)
    smod.add(amb, smod.st(room[:n_samples], 0.0) * 0.11, 0.0)

    # Subtle male a cappella vocal formant pad (dips down at Scene 08 silence drop for dramatic contrast!)
    pad1 = smod.reverb(smod.vocal_pad(rng, max(1.0, timeline[6]["t1"] + 0.3), [73.42, 110.0, 146.83], vowel="m", voices=3), wet=0.26, seed=310)
    smod.add(amb, pad1 * 0.14, 0.0)
    s8_start = timeline[8]["t0"]
    pad2 = smod.reverb(smod.vocal_pad(rng, max(1.0, dur - s8_start + 0.2), [82.41, 123.47, 164.81], vowel="o", voices=4), wet=0.28, seed=311)
    smod.add(amb, pad2 * 0.16, s8_start)

    for row in timeline:
        si, t0, sd = row["si"], row["t0"], row["dur"]
        if si == 0:
            smod.add(amb, smod.reverb(smod.impact_boom(rng, 0.9), wet=0.20, seed=321) * 0.56, 0.01)
            smod.add(amb, smod.st(smod.sizzle(rng, min(1.2, sd * 0.45)), 0.0) * 0.24, 0.10)
        elif si == 1:
            smod.add(amb, smod.reverb(smod.sword_draw(rng, 0.55), wet=0.18, seed=322) * 0.48, t0 + 0.02)
        elif si == 2:
            smod.add(amb, smod.st(smod.sizzle(rng, min(1.1, sd * 0.50)), 0.15) * 0.28, t0 + 0.06)
            smod.add(amb, smod.reverb(smod.thud(rng), wet=0.14, seed=323) * 0.36, t0 + sd * 0.52)
        elif si == 3:
            smod.add(amb, smod.st(smod.whoosh(rng, 0.48), 0.0) * 0.44, t0 + 0.03)
            for k in range(3):
                smod.add(amb, smod.reverb(smod.clasp(rng), wet=0.10, seed=330 + k) * 0.32, t0 + sd * (0.20 + k * 0.22))
        elif si == 4:
            # Physical 52Hz acoustic air-pressure bass pulse from titanium diaphragm
            td = smod.tt(0.55)
            sub_p = smod.fade(np.sin(2.0 * math.pi * 55.0 * td) * np.exp(-td * 4.5), 0.01, 0.15)
            smod.add(amb, smod.st(sub_p, 0.0) * 0.48, t0 + 0.15)
            smod.add(amb, smod.st(smod.whoosh(rng, 0.38), -0.15) * 0.34, t0 + 0.02)
        elif si == 5:
            # Urban low street rumble dying into mic capture
            roar = smod.bp(smod.brown(rng, min(1.8, sd * 0.85)), 90.0, 520.0)
            smod.add(amb, smod.st(smod.fade(roar, 0.04, 0.25), -0.18) * 0.42, t0 + 0.04)
        elif si == 6:
            for k in range(3):
                smod.add(amb, smod.reverb(smod.clasp(rng), wet=0.10, seed=340 + k) * 0.35, t0 + sd * (0.12 + k * 0.18))
        elif si == 7:
            # Dramatic phase-cancel sweep -> near silence right on the beat!
            smod.add(amb, smod.st(smod.whoosh(rng, min(0.7, sd * 0.38)), 0.0) * 0.42, t0 + 0.04)
        elif si == 8:
            smod.add(amb, smod.reverb(smod.clasp(rng), wet=0.14, seed=329) * 0.42, t0 + 0.08)
        elif si == 9:
            for k in range(4):
                smod.add(amb, smod.st(_water_blip(rng, 880.0 + k * 140.0), (k % 2 - 0.5) * 0.4) * 0.45,
                         t0 + sd * (0.14 + k * 0.20))
        elif si == 10:
            smod.add(amb, smod.st(smod.whoosh(rng, 0.45), 0.0) * 0.46, t0 + 0.04)
            smod.add(amb, smod.reverb(smod.clasp(rng), wet=0.14, seed=331) * 0.42, t0 + sd * 0.55)
        elif si == 11:
            rlen = min(1.15, sd * 0.45)
            smod.add(amb, smod.st(smod.riser(rng, rlen), 0.0) * 0.36, max(t0, dur - rlen - 0.02))

    # Sidechain duck behind crisp narration
    rms = smod.frame_rms(voice_mono, win=0.04)
    rms_st = np.interp(np.arange(n_samples), np.arange(len(rms)) * int(SR * 0.04), rms)
    duck = 1.0 - 0.56 * np.clip(rms_st / 0.085, 0.0, 1.0)
    amb *= duck[:, None]

    out = amb * 0.88 + smod.st(voice_mono, 0.0) * 1.00
    out = smod.softclip(out, 0.90)
    smod.write(str(mix_raw), out)
    b1.loudnorm_portable(mix_raw, mix_wav, I=-14.0, TP=-1.5, LRA=11.0)
    return mix_wav


# ---------------------------------------------------------------------------
# Frame Composition & Render Pipeline
# ---------------------------------------------------------------------------

def render_scene_frame(plates: dict[str, Image.Image], lang: str, si: int, u: float, tau: float, t: float,
                       scrim: np.ndarray, vig: np.ndarray) -> Image.Image:
    plate_key_map = {
        0: "s01",
        1: "s02",
        2: "s04",
        3: "exploded",
        4: "s05",
        5: "s06",
        6: "s07",
        7: "s08",
        8: "s09",
        9: "mesh_macro",
        10: "s02",
        11: "exploded",
    }
    cam_im, x0, y0, z = rigid_cam_crop(plates[plate_key_map[si]], si, u, tau)
    rgba = apply_live_fx(cam_im, plates, si, u, tau, t, x0, y0, z, lang)
    draw_tracked_pointers(rgba, lang, si, tau, x0, y0, z, t)
    draw_top_badge(rgba, lang, si, tau)

    # Apply subtle bottom contrast scrim & vignette
    rgb = np.asarray(rgba.convert("RGB"), dtype=np.float32)
    rgb *= scrim
    rgb_v = ((rgb.clip(0, 255).astype(np.uint16) * vig) >> 8).astype(np.uint8)
    return Image.fromarray(rgb_v)


def preview_qa_frames(langs: list[str]):
    plates = load_plates()
    scrim = bottom_scrim_lut()
    vig = rmod.vignette()[..., None]
    qa_dir = PROD / "build_b2b03" / "qa"
    qa_dir.mkdir(parents=True, exist_ok=True)

    sample_subs = {
        "ru": [
            ["ДВА", "НАУШНИКА"], ["РЕЖЕМ", "ЛАЗЕРОМ"], ["ТОНКАЯ", "ПЛЁНКА"], ["ВОСЕМЬ", "СЛОЁВ"],
            ["ЧИСТЫЙ", "БАС"], ["ЛОВИТ", "ШУМ"], ["ПЯТЬ", "МИЛЛИСЕКУНД"], ["ШУМ", "В", "НОЛЬ"],
            ["ВОСЕМЬ", "ЧАСОВ"], ["ОТТАЛКИВАЕТ", "ПОТ"], ["ПРОПАСТЬ", "КАЧЕСТВА"], ["ПИШИТЕ", "«3D»"],
        ],
        "kz": [
            ["ЕКІ", "ҚҰЛАҚҚАП"], ["ЛАЗЕРМЕН", "КЕСІП"], ["ЖҰҚА", "ПЛЕНКА"], ["СЕГІЗ", "ҚАБАТ"],
        ],
        "en": [
            ["TWO", "EARBUDS"], ["SLICE", "BOTH"], ["PAPER-THIN", "FILM"], ["EIGHT", "LAYERS"],
        ],
    }

    for lang in langs:
        scenes_to_check = range(12) if lang == "ru" else (0, 3, 7, 11)
        for si in scenes_to_check:
            u = 0.48 if si == 11 else 0.68
            tau = 1.8
            t = si * 2.5 + tau
            frame = render_scene_frame(plates, lang, si, u, tau, t, scrim, vig).convert("RGBA")
            wlist = sample_subs[lang][si if si < len(sample_subs[lang]) else 0]
            words_obj = [{"txt": w, "t0": 0.0, "t1": 1.0} for w in wlist]
            ov = rmod.render_chunk(words_obj, min(1, len(words_obj) - 1))
            frame.paste(ov, (int(W / 2 - ov.width / 2), int(SUB_Y - ov.height / 2)), ov)
            out_p = qa_dir / f"pre_{lang}_s{si:02d}.jpg"
            frame.convert("RGB").save(out_p, "JPEG", quality=92)
            print(f"[B2B-03-PREVIEW] saved {out_p}")


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

            # Snappy 0.09s whip-dissolve on rapid competitor cuts
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
                print(f"[B2B-03:{lang.upper()}] rendered {fi + 1}/{total_frames} frames ({t:.1f}s/{dur:.1f}s)", flush=True)

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
        build_dir = PROD / "build_b2b03" / lang
        build_dir.mkdir(parents=True, exist_ok=True)
        out_mp4 = out_dir / VOICE_CFG[lang]["out_file"]

        print(f"[B2B-03:{lang.upper()}] Synthesizing native narration...")
        voice_mono, timeline, words_all, dur = synthesize_lang_b2b03(lang, build_dir)
        print(f"[B2B-03:{lang.upper()}] Narration ready: {len(timeline)} scenes, {dur:.2f}s, {len(words_all)} words.")

        print(f"[B2B-03:{lang.upper()}] Mixing 3D physical Foley SFX + a cappella (-14 LUFS)...")
        mix_wav = build_cgi_audio(lang, build_dir, voice_mono, timeline, dur)

        print(f"[B2B-03:{lang.upper()}] Rendering 1080x1920 @ 30fps -> {out_mp4.name} ...")
        render_lang_video(lang, build_dir, mix_wav, timeline, words_all, dur, out_mp4, plates)
        mb = out_mp4.stat().st_size / (1024 * 1024)
        print(f"[B2B-03:{lang.upper()}] DONE in {time.time() - t_start:.1f}s: {out_mp4} ({mb:.2f} MB, {dur:.2f}s)")


if __name__ == "__main__":
    main()
