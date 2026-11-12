"""Cinematic Tactical Explainer & Neural Voice Builder for Episode 1:
Kurultai at Ordabasy (1726) & Battle of Anyrakai (1729/1730).

Features:
1. Rebuilds all 23 scene clips in scenes_video/ directly from the master high-res stills
   in scenes/ using strictly rigid 2D camera transforms (rigid_cam: zoom, pan, micro-shake)
   plus clean atmospheric overlays (sparks, embers, dust, sun rays) — ZERO floating/jelly warp.
2. Synthesizes live Neural TTS (kk-KZ-DauletNeural for RU/KZ with authentic Kazakh phrases
   woven into the Russian narration; en-US-AndrewMultilingualNeural for EN).
3. Mixes 20-scene steppe & battle SFX + male A cappella choir (zero musical instruments).
4. Renders 1080x1920 30fps vertical video with live Tactical HUD & Strategic Map overlay
   (3 Zhuzes uniting at Ordabasy -> Zhylu mutual aid -> Sabalak's Zhekpe-zhek duel ->
   Tolgama crescent encirclement at Anyrakai).
"""
import asyncio
import json
import math
import os
import re
import subprocess
import sys
from pathlib import Path

import edge_tts
import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw
from scipy.io import wavfile
from scipy.ndimage import gaussian_filter

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

# Ensure ffmpeg is available in PATH via imageio-ffmpeg
FFMPEG_BIN = imageio_ffmpeg.get_ffmpeg_exe()
BIN_DIR = ROOT / "build_ep02" / "_bin"
BIN_DIR.mkdir(parents=True, exist_ok=True)
if not (BIN_DIR / "ffmpeg").exists():
    os.symlink(FFMPEG_BIN, BIN_DIR / "ffmpeg")
os.environ["PATH"] = f"{BIN_DIR}:{os.environ.get('PATH', '')}"

import sfx as smod
import render as rmod

SCENES_DIR = ROOT.parent / "scenes"
VIDEO_DIR = ROOT.parent / "scenes_video"
OUTPUT = ROOT.parent / "output"
SR = 48000
CLIP_W, CLIP_H, CLIP_FPS, CLIP_FRAMES = 540, 960, 24, 84  # 3.5s rigid clips

VOICE_FX = (
    "aresample=48000,highpass=f=65,"
    "equalizer=f=130:t=q:w=1.1:g=2.2,equalizer=f=3100:t=q:w=1.3:g=2.4,"
    "acompressor=threshold=0.14:ratio=2.4:attack=10:release=120:makeup=1.45"
)

VOWELS = set("аеёиоуыэюяәіңғүұқөһaeiouy")


def count_syllables(word: str) -> int:
    return max(1, sum(1 for ch in word.lower() if ch in VOWELS))


# Rigid camera presets for all 23 master scenes of Episode 1 (zero non-uniform warp)
RIGID_CLIP_PRESETS = {
    "scene_01":  {"z0": 1.00, "z1": 1.15, "px0": 0.0,   "px1": 0.0,   "py0": 8.0,  "py1": -8.0, "dust": 0.35, "shake": 0.25},
    "scene_02":  {"z0": 1.02, "z1": 1.12, "px0": -12.0, "px1": 12.0,  "py0": 6.0,  "py1": -6.0, "dust": 0.45},
    "scene_03":  {"z0": 1.04, "z1": 1.16, "px0": -10.0, "px1": 10.0,  "py0": 0.0,  "py1": 0.0,  "sparks": 0.85, "fire": 0.55},
    "scene_04":  {"z0": 1.06, "z1": 1.14, "px0": 14.0,  "px1": -14.0, "py0": 4.0,  "py1": -4.0, "dust": 0.40, "shake": 0.20},
    "scene_04b": {"z0": 1.00, "z1": 1.12, "px0": -8.0,  "px1": 8.0,   "py0": 4.0,  "py1": -4.0, "dust": 0.45},
    "scene_05":  {"z0": 1.00, "z1": 1.18, "px0": 0.0,   "px1": 0.0,   "py0": 6.0,  "py1": -6.0, "sparks": 0.65, "fire": 0.60},
    "scene_06":  {"z0": 1.02, "z1": 1.14, "px0": 0.0,   "px1": 0.0,   "py0": 12.0, "py1": -8.0, "sun": 0.45},
    "scene_07":  {"z0": 1.14, "z1": 1.02, "px0": 0.0,   "px1": 0.0,   "py0": 10.0, "py1": -10.0,"dust": 0.40, "sun": 0.35},
    "scene_08":  {"z0": 1.00, "z1": 1.16, "px0": 0.0,   "px1": 0.0,   "py0": -4.0, "py1": 8.0,  "dust": 0.35, "shake": 0.45},
    "scene_08b": {"z0": 1.12, "z1": 1.02, "px0": -8.0,  "px1": 8.0,   "py0": 4.0,  "py1": -4.0, "dust": 0.30},
    "scene_09":  {"z0": 1.02, "z1": 1.15, "px0": 0.0,   "px1": 0.0,   "py0": 6.0,  "py1": -6.0, "sparks": 0.90, "fire": 0.65, "shake": 0.30},
    "scene_09b": {"z0": 1.04, "z1": 1.14, "px0": 6.0,   "px1": -6.0,  "py0": 8.0,  "py1": -8.0, "sparks": 0.80, "fire": 0.70},
    "scene_10":  {"z0": 1.08, "z1": 1.14, "px0": -18.0, "px1": 18.0,  "py0": 0.0,  "py1": 0.0,  "dust": 0.35, "sun": 0.40},
    "scene_11":  {"z0": 1.00, "z1": 1.12, "px0": -6.0,  "px1": 6.0,   "py0": 4.0,  "py1": -4.0, "sun": 0.25},
    "scene_12":  {"z0": 1.00, "z1": 1.14, "px0": 6.0,   "px1": -6.0,  "py0": 10.0, "py1": -8.0, "dust": 0.30, "sun": 0.35},
    "scene_13":  {"z0": 1.06, "z1": 1.16, "px0": 16.0,  "px1": -16.0, "py0": 4.0,  "py1": -4.0, "dust": 0.55, "shake": 0.25},
    "scene_14":  {"z0": 1.10, "z1": 1.14, "px0": -20.0, "px1": 20.0,  "py0": 0.0,  "py1": 0.0,  "dust": 0.50},
    "scene_15":  {"z0": 1.00, "z1": 1.14, "px0": 0.0,   "px1": 0.0,   "py0": 8.0,  "py1": -8.0, "dust": 0.35},
    "scene_16":  {"z0": 1.02, "z1": 1.18, "px0": 14.0,  "px1": -14.0, "py0": 6.0,  "py1": -8.0, "dust": 0.60, "sun": 0.55, "shake": 0.30},
    "scene_17":  {"z0": 1.02, "z1": 1.16, "px0": 0.0,   "px1": 0.0,   "py0": 4.0,  "py1": -4.0, "sparks": 1.00, "sun": 0.60, "shake": 0.55},
    "scene_18":  {"z0": 1.04, "z1": 1.18, "px0": -10.0, "px1": 10.0,  "py0": 8.0,  "py1": -8.0, "dust": 0.55},
    "scene_19":  {"z0": 1.15, "z1": 1.00, "px0": 0.0,   "px1": 0.0,   "py0": -8.0, "py1": 6.0,  "sun": 0.60},
    "scene_20":  {"z0": 1.00, "z1": 1.22, "px0": -6.0,  "px1": 6.0,   "py0": 6.0,  "py1": -6.0, "sparks": 0.45},
}


def rigid_cam_frame(pil_im: Image.Image, zoom: float, dx: float = 0.0, dy: float = 0.0) -> np.ndarray:
    """Strictly rigid sub-pixel 2D camera crop & resize via Image.EXTENT — zero warping or stepping."""
    z = max(1.0, float(zoom))
    cw = CLIP_W / z
    ch = CLIP_H / z
    x0 = float(np.clip((CLIP_W - cw) * 0.5 + dx, 0.0, max(0.0, CLIP_W - cw)))
    y0 = float(np.clip((CLIP_H - ch) * 0.5 + dy, 0.0, max(0.0, CLIP_H - ch)))
    cropped = pil_im.transform((CLIP_W, CLIP_H), Image.EXTENT, (x0, y0, x0 + cw, y0 + ch), Image.BICUBIC)
    return np.asarray(cropped, dtype=np.float64)


def build_rigid_clip_ep01(name: str):
    """Build a rock-solid 24fps MP4 clip from scenes/<name>_*.jpg with zero jelly distortion."""
    VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    out_path = VIDEO_DIR / f"{name}.mp4"
    src_path = sorted(SCENES_DIR.glob(f"{name}_*.jpg"))[0]
    pil_base = Image.open(src_path).convert("RGB").resize((CLIP_W, CLIP_H), Image.LANCZOS)

    cfg = RIGID_CLIP_PRESETS[name]
    seed = sum((i + 1) * ord(ch) for i, ch in enumerate(name))
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:CLIP_H, 0:CLIP_W].astype(np.float64)
    yn, xn = yy / CLIP_H, xx / CLIP_W

    # Embers / sparks particles
    n_sparks = 75
    spx = rng.uniform(0, CLIP_W, n_sparks)
    spy = rng.uniform(0, CLIP_H, n_sparks)
    svx = rng.uniform(-75, 75, n_sparks)
    svy = rng.uniform(-190, -55, n_sparks)

    ff = subprocess.Popen(
        [
            FFMPEG_BIN, "-y", "-hide_banner", "-loglevel", "error",
            "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{CLIP_W}x{CLIP_H}", "-r", str(CLIP_FPS),
            "-i", "-", "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-pix_fmt", "yuv420p", str(out_path),
        ],
        stdin=subprocess.PIPE,
    )

    for fi in range(CLIP_FRAMES):
        u = fi / max(1, CLIP_FRAMES - 1)
        t = fi / CLIP_FPS
        u_sm = 0.5 * (1.0 - math.cos(math.pi * u))

        z = cfg["z0"] + (cfg["z1"] - cfg["z0"]) * u_sm
        dx = cfg["px0"] + (cfg["px1"] - cfg["px0"]) * u_sm
        dy = cfg["py0"] + (cfg["py1"] - cfg["py0"]) * u_sm

        if cfg.get("shake"):
            sh = cfg["shake"] * math.exp(-u * 2.2)
            dx += math.sin(fi * 1.9) * 5.0 * sh
            dy += math.cos(fi * 2.5) * 4.0 * sh

        frame = rigid_cam_frame(pil_base, z, dx, dy)

        # Atmospheric steppe dust haze overlay (subtle 14% additive tint, never warps pixels)
        if cfg.get("dust"):
            haze = (
                0.5
                + 0.3 * np.sin((xn * 3.5 - u * 1.4) * math.pi)
                + 0.2 * np.cos((yn * 4.0 + u * 0.8) * math.pi)
            )
            mask = np.clip((yn - 0.38) / 0.62, 0.0, 1.0)
            frame = frame + (haze * mask)[..., None] * np.array([215.0, 190.0, 150.0]) * (cfg["dust"] * 0.16)

        # Warm firelight flicker overlay
        if cfg.get("fire"):
            flick = 0.65 + 0.35 * math.sin(t * 15.0) * math.cos(t * 9.0)
            glow = np.exp(-((xn - 0.5) ** 2 + (yn - 0.65) ** 2) / 0.22)[..., None]
            frame = frame + glow * np.array([255.0, 125.0, 30.0]) * (cfg["fire"] * 0.22 * flick)

        # Golden dawn / sun flare overlay
        if cfg.get("sun"):
            pulse = 0.8 + 0.2 * math.sin(t * 4.5)
            flare = np.exp(-((xn - 0.5) ** 2 + (yn - 0.25) ** 2) / 0.28)[..., None]
            frame = frame + flare * np.array([255.0, 215.0, 120.0]) * (cfg["sun"] * 0.18 * pulse)

        # Flying sparks / embers overlay
        if cfg.get("sparks"):
            for k in range(n_sparks):
                px = int((spx[k] + svx[k] * t) % CLIP_W)
                py = int((spy[k] + svy[k] * t) % CLIP_H)
                if 2 <= px < CLIP_W - 2 and 2 <= py < CLIP_H - 2:
                    frame[py - 1:py + 2, px - 1:px + 2] = [255.0, 215.0, 95.0]

        ff.stdin.write(np.clip(frame, 0.0, 255.0).astype(np.uint8).tobytes())

    ff.stdin.close()
    ff.wait()
    print(f"[ok-ep01-rigid] {name}.mp4 ({out_path.stat().st_size // 1024} KB)")


def build_all_ep01_clips():
    for name in RIGID_CLIP_PRESETS:
        build_rigid_clip_ep01(name)


# High-retention tactical script for Episode 1 with authentic Kazakh phrases in RU track
EP01_SCRIPT = {
    "voices": {
        "ru": "kk-KZ-DauletNeural",
        "kz": "kk-KZ-DauletNeural",
        "en": "en-US-AndrewMultilingualNeural",
    },
    "scenes": [
        "scene_01", "scene_02", "scene_03", "scene_04|scene_04b", "scene_05",
        "scene_06", "scene_07", "scene_08|scene_08b", "scene_09|scene_09b", "scene_10",
        "scene_11", "scene_12", "scene_13", "scene_14", "scene_15",
        "scene_16", "scene_17", "scene_18", "scene_19", "scene_20",
    ],
    "hud": [
        {"tag": "ОРДАБАСЫ ЖӘНЕ АҢЫРАҚАЙ • 1726–1730", "stat": "КАК ЕДИНСТВО СПАСЛО СТЕПЬ", "phase": 0},
        {"tag": "АҚТАБАН ШҰБЫРЫНДЫ • 1723–1726", "stat": "УДАР 40 000 ВТОРЖЕНИЯ", "phase": 0},
        {"tag": "ФАКТОР УГРОЗЫ: АРТИЛЛЕРИЯ", "stat": "ПУШКИ И МОРТИРЫ РЕНАТА", "phase": 0},
        {"tag": "СТАВКА ЗАХВАТЧИКОВ", "stat": "РАЗБИТЬ РОДЫ ПООДИНОЧКЕ", "phase": 0},
        {"tag": "КРИТИЧЕСКИЙ РУБЕЖ • 1726 ГОД", "stat": "РАЗОБЩЁННОСТЬ = ГИБЕЛЬ", "phase": 0},
        {"tag": "СЕКРЕТ №1: ҚҰРЫЛТАЙ ОРДАБАСЫ", "stat": "ТӨЛЕ БИ • ҚАЗЫБЕК БИ • ӘЙТЕКЕ БИ", "phase": 1},
        {"tag": "СБОР ТРЁХ ЖУЗОВ В КУЛАК", "stat": "ҰЛЫ ЖҮЗ • ОРТА ЖҮЗ • КІШІ ЖҮЗ", "phase": 1},
        {"tag": "КОДЕКС ЧЕСТИ СТЕПИ", "stat": "ПРЕКРАЩЕНИЕ ВСЕХ РАСПРЕЙ", "phase": 1},
        {"tag": "ЖЕЛЕЗНАЯ КЛЯТВА «АНТ»", "stat": "3 ЖУЗА — ОДНО ЗНАМЯ", "phase": 1},
        {"tag": "СЕКРЕТ №2: ЗАКОН «ЖЫЛУ»", "stat": "БРАТСКАЯ ПОМОЩЬ ЗАПАДА ЮГУ", "phase": 2},
        {"tag": "ВСЕНАРОДНЫЙ АРСЕНАЛ", "stat": "+ДЕСЯТКИ ТЫСЯЧ КОНЕЙ И САБЕЛЬ", "phase": 2},
        {"tag": "МЕРИТОКРАТИЯ: БАС САРДАР", "stat": "ГЛАВКОМ — ӘБІЛҚАЙЫР ХАН", "phase": 2},
        {"tag": "УДАРНЫЕ ТУМЕНЫ БАТЫРОВ", "stat": "БӨГЕНБАЙ БАТЫР • ҚАБАНБАЙ БАТЫР", "phase": 2},
        {"tag": "АҢЫРАҚАЙ ШАЙҚАСЫ • 1729/1730", "stat": "50 000 ВСАДНИКОВ ЛИЦОМ К ЛИЦУ", "phase": 3},
        {"tag": "СЕКРЕТ №3: ПОЕДИНОК ЖЕКПЕ-ЖЕК", "stat": "ВЫЗОВ НЕПОБЕДИМОГО ШАРЫША", "phase": 3},
        {"tag": "ВЫХОД 18-ЛЕТНЕГО САБАЛАКА", "stat": "БУДУЩИЙ АБЫЛАЙ ХАН", "phase": 3},
        {"tag": "БОЕВОЙ КЛИЧ «АБЫЛАЙ!»", "stat": "ШАРЫШ ПОВЕРЖЕН ЗА СЕКУНДЫ", "phase": 3},
        {"tag": "СЕКРЕТ №4: ТАКТИКА «ТОЛҒАМА»", "stat": "КОЛЬЦО У СОЛОНЧАКОВ АЛАКОЛЯ", "phase": 4},
        {"tag": "40 ДНЕЙ ПОЛНОГО РАЗГРОМА", "stat": "ПО МИЛОСТИ ВСЕВЫШНЕГО — ПОБЕДА", "phase": 4},
        {"tag": "УРОК ОРДАБАСЫ И АНЫРАКАЯ", "stat": "БІРЛІК БАР ЖЕРДЕ — ТІРЛІК БАР", "phase": 4},
    ],
    "ru": [
        "Против их армии со шведскими пушками и ружьями вылетел восемнадцатилетний юноша-сирота Сабалак в простом потёртом тулупе!",
        "Тысяча семьсот двадцать шестой год. Три года назад в годы Великого бедствия — Ақтабан шұбырынды — сорокатысячное войско обрушилось на Великую Степь.",
        "Враг бил наверняка: пленённый шведский офицер Ренат отлил для них тяжёлые пушки и мортиры.",
        "Захватчики были уверены:",
        "разрозненные степные роды обречены на гибель.",
        "Но осенью на священной горе Ордабасы три великих судьи степи — Төле би, Қазыбек би и Әйтеке би —",
        "совершили невозможное! Они собрали все три жуза — Үш жүз — в единый стальной кулак,",
        "навсегда остановив любые внутренние споры",
        "нерушимой клятвой верности — Ант!",
        "Тут же сработал древний степной закон братства — Жылу: западные роды безвозмездно передали",
        "десятки тысяч боевых коней и острых клинков воинам юга!",
        "Верховным главнокомандующим — бас сардаром — избрали Абулхаир-хана не за старшинство титула, а за полководческий гений,",
        "поставив во главе ударных туменов легендарных батыров — Қанжығалы Бөгенбай и Қаракерей Қабанбай!",
        "Весной в урочище Аныракай началось генеральное сражение — Аңырақай шайқасы, где сошлись пятьдесят тысяч всадников.",
        "На смертельный поединок Жекпе-жек перед строем выехал непобедимый военачальник врага — Шарыш.",
        "И тогда навстречу гиганту сорвался никому не известный юноша Сабалак — будущий великий Абылай хан!",
        "С громовым боевым кличем «Абылай!» он в считанные секунды сокрушил Шарыша на глазах обеих армий,",
        "а казахская конница манёвром Толғама заманила врага в солончаки Алаколя и замкнула стальное кольцо!",
        "По милости Всевышнего, этот сорокадневный разгром доказал: единый народ — Бірлік — невозможно сломить ни одной силой в мире,",
        "поэтому захватчики даже не подозревали, что их ждёт, когда...",
    ],
    "kz": [
        "Олардың швед зеңбіректері мен мылтық асынған қалың қолына қарсы жамаулы тон киген он сегіз жасар жетім бозбала құйындай ұшты!",
        "Мың жеті жүз жиырма алтыншы жыл. Үш жыл бұрын қырық мыңдық жоңғар әскері даланы қанға бөктірді.",
        "Тұтқынға түскен швед офицері Ренат",
        "оларға ауыр зеңбіректер құйып берген еді.",
        "Дұшпан «бөлінген рулар енді бас көтере алмайды» деп есептеді.",
        "Бірақ сол күзде Ордабасы тауында даланың үш дана биі — Төле би, Қазыбек би және Әйтеке би —",
        "тарихты күрт өзгертті. Олар үш жүзді бір тудың астына жинап,",
        "барлық алауыздықты тоқтатқан",
        "мызғымас «Ант» қабылдатты!",
        "Сол сәтте даланың «Жылу» заңы іске қосылды: батыстағы ел",
        "оңтүстіктегі бауырларына ондаған мың жүйрік ат пен болат қылышты тегін жөнелтті.",
        "Ал бас сардар етіп Әбілқайыр ханды шені үшін емес, қолбасшылық таланты үшін сайлап,",
        "соққы беруші түмендерді Бөгенбай мен Қабанбай батырларға тапсырды!",
        "Көктемде Аңырақай даласында елу мың сарбаз бетпе-бет келді.",
        "Майдан ортасына жаудың жеңілмейтін нояны Шарыш шыққанда,",
        "оған қарсы ешкім танымайтын Сабалақ есімді жас жігіт — болашақ Абылай хан атылды!",
        "«Абылайлап!» ұран салған ол Шарышты қас-қағым сәтте құлатты,",
        "ал қазақ атты әскері «Толғама» әдісімен жауды Алакөлдің сор даласына қамап, тас-талқан етті!",
        "Жаратқанның қолдауымен, қырық күнге созылған бұл шайқас біріккен елді ешбір күш ала алмайтынын дәлелдеді,",
        "сондықтан басқыншылар өздерін не күтіп тұрғанын сезбеді де, өйткені...",
    ],
    "en": [
        "Against their army of European cannons and muskets charged an eighteen-year-old orphan in a worn sheepskin coat!",
        "The year is seventeen twenty-six. Three years earlier, forty thousand Dzungar invaders had shattered the frontier.",
        "Their secret weapon: heavy cannons and mortars forged by captured Swedish artillery officer Johann Renat.",
        "They were certain",
        "the scattered clans were finished.",
        "But that autumn on Mount Ordabasy, three master statesmen — Tole Bi, Kazybek Bi, and Aiteke Bi —",
        "pulled off the impossible. They forged all three hordes into a single fist,",
        "ending every rivalry",
        "with an unbreakable oath of honor — Ant!",
        "Immediately, the steppe code of Zhylu kicked in: western clans freely sent",
        "tens of thousands of warhorses and steel blades to arm the south.",
        "Breaking royal hierarchy, they elected Abulkhair Khan as supreme commander purely for his tactical genius,",
        "with legendary warriors Bogenbai and Kabanbai leading the strike corps!",
        "At Anyrakai valley, fifty thousand horsemen stood face to face.",
        "When the enemy's undefeated giant, Sharysh, rode out for single combat,",
        "an unknown teenager nicknamed Sabalak — the future Ablai Khan — bolted from the line!",
        "With the thunderous war cry \"Ablai!\", he struck down Sharysh in seconds,",
        "while the Kazakh cavalry sprung the Tolgama crescent trap, pinning the invaders against the salt flats of Alakol!",
        "By the grace of the Almighty, that forty-day triumph proved that a united nation cannot be broken by any force on earth,",
        "which is why the invaders never saw it coming when...",
    ],
}


async def synth_scene_edge(line: str, voice_name: str, out_dir: Path, si: int):
    clean_text = line.strip()
    seg_mp3 = out_dir / f"sc_{si:02d}_neural.mp3"
    seg_wav = out_dir / f"sc_{si:02d}_neural.wav"

    fallback_voices = [voice_name, "en-US-AndrewMultilingualNeural", "en-US-BrianMultilingualNeural"]
    for attempt, v_try in enumerate(fallback_voices):
        try:
            comm = edge_tts.Communicate(clean_text, v_try)
            await comm.save(str(seg_mp3))
            if seg_mp3.exists() and seg_mp3.stat().st_size > 200:
                break
        except Exception:
            if attempt == len(fallback_voices) - 1:
                raise
            await asyncio.sleep(0.4)

    subprocess.run(
        [FFMPEG_BIN, "-y", "-hide_banner", "-loglevel", "error", "-i", str(seg_mp3),
         "-ar", str(SR), "-ac", "1", str(seg_wav)],
        check=True,
    )
    _, pcm = wavfile.read(seg_wav)
    arr = pcm.astype(np.float32) / 32768.0
    env = np.abs(arr)
    nz = np.where(env > 0.015)[0]
    if len(nz) > 0:
        i0 = max(0, nz[0] - int(0.025 * SR))
        i1 = min(len(arr), nz[-1] + int(0.04 * SR))
        arr = arr[i0:i1]

    seg_dur = len(arr) / SR
    toks = [t for t in clean_text.split() if t not in ("—", "-", "–")]
    weights = [count_syllables(t) + (0.35 if t.endswith((",", ".", "!", "?", ":", "…")) else 0.0) for t in toks]
    total_w = sum(weights) or 1.0
    w_cur = 0.0
    sc_words = []
    for tok, w_val in zip(toks, weights):
        w_dur = seg_dur * (w_val / total_w)
        sc_words.append({
            "w": tok,
            "t0": w_cur,
            "t1": w_cur + w_dur * 0.94,
        })
        w_cur += w_dur

    return arr, sc_words


async def build_neural_voice_ep01_async(lang: str):
    out = ROOT / "build" / lang
    out.mkdir(parents=True, exist_ok=True)
    voice_name = EP01_SCRIPT["voices"][lang]
    lines = EP01_SCRIPT[lang]

    pieces = []
    all_words = []
    cur_t = 0.0
    gap = 0.20

    for si, line in enumerate(lines):
        arr, sc_words = await synth_scene_edge(line, voice_name, out, si)
        dur = len(arr) / SR
        for w in sc_words:
            all_words.append({
                "w": w["w"],
                "scene": si,
                "t0": round(cur_t + w["t0"], 3),
                "t1": round(cur_t + min(dur, w["t1"]), 3),
            })

        pieces.append(arr)
        cur_t += dur
        if si < len(lines) - 1:
            g_len = int(gap * SR)
            pieces.append(np.zeros(g_len, dtype=np.float32))
            cur_t += gap

    pieces.append(np.zeros(int(0.15 * SR), dtype=np.float32))
    full_audio = np.concatenate(pieces)
    T = len(full_audio) / SR

    starts = []
    for si in range(len(lines)):
        ws = [w for w in all_words if w["scene"] == si]
        starts.append(max(0.0, ws[0]["t0"] - 0.06) if ws else (si * T / len(lines)))
    starts[0] = 0.0
    scenes = [
        {
            "id": si + 1,
            "images": EP01_SCRIPT["scenes"][si].split("|"),
            "t0": round(starts[si], 3),
            "t1": round(starts[si + 1] if si + 1 < len(starts) else T, 3),
        }
        for si in range(len(starts))
    ]

    wavfile.write(out / "voice_raw.wav", SR, (np.clip(full_audio, -1, 1) * 32767).astype(np.int16))
    subprocess.run(
        [FFMPEG_BIN, "-y", "-hide_banner", "-loglevel", "error", "-i", str(out / "voice_raw.wav"),
         "-af", VOICE_FX, "-ar", "48000", "-ac", "1", str(out / "voice.wav")],
        check=True,
    )
    (out / "words.json").write_text(json.dumps(all_words, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / "timeline.json").write_text(
        json.dumps({"lang": lang, "T": round(T, 3), "scenes": scenes}, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    print(f"[ep01-neural-voice-{lang}] {len(lines)} scenes, total={T:.2f}s ({voice_name})")


def draw_ep01_tactical_hud(im: Image.Image, scene_idx: int, tau: float, seg_dur: float):
    """Draw cinematic tactical HUD overlay for Ordabasy (1726) & Anyrakai (1729/1730)."""
    hud_info = EP01_SCRIPT["hud"][min(scene_idx, len(EP01_SCRIPT["hud"]) - 1)]
    phase = hud_info["phase"]
    u = min(1.0, max(0.0, tau / max(0.1, seg_dur)))

    ov = Image.new("RGBA", (rmod.W, rmod.H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)

    f_tag = rmod.font(30)
    f_stat = rmod.font(38)
    f_map = rmod.font(24)

    # 1. Top Tactical HUD Banner (y = 92..232)
    bx0, by0, bx1, by1 = 64, 92, rmod.W - 64, 232
    d.rounded_rectangle([bx0, by0, bx1, by1], radius=18, fill=(8, 14, 26, 205), outline=(56, 189, 248, 180), width=3)
    d.line([(bx0, by0 + 28), (bx0, by0), (bx0 + 28, by0)], fill=(250, 204, 21, 255), width=5)
    d.line([(bx1 - 28, by1), (bx1, by1), (bx1, by1 - 28)], fill=(250, 204, 21, 255), width=5)

    d.text((bx0 + 28, by0 + 18), f"▸ {hud_info['tag']}", font=f_tag, fill=(56, 189, 248, 255))
    d.text((bx0 + 28, by0 + 64), hud_info["stat"], font=f_stat, fill=(250, 204, 21, 255))

    # 2. Bottom Tactical Map Overlay (y = 1430..1680)
    mx0, my0, mx1, my1 = 84, 1430, rmod.W - 84, 1680
    d.rounded_rectangle([mx0, my0, mx1, my1], radius=16, fill=(8, 13, 24, 195), outline=(148, 163, 184, 120), width=2)

    cx, cy = (mx0 + mx1) // 2, my0 + 145
    if phase <= 2:
        d.text((mx0 + 22, my0 + 12), "СТРАТЕГИЧЕСКАЯ СХЕМА: КУРУЛТАЙ В ОРДАБАСЫ (1726)", font=f_map, fill=(148, 163, 184, 230))
        # Central Ordabasy Peak
        d.polygon([(cx, cy - 38), (cx - 42, cy + 28), (cx + 42, cy + 28)], fill=(250, 204, 21, 220), outline=(255, 255, 255, 220))
        # Three Zhuz columns converging from West, North, South-East
        vecs = [
            (mx0 + 90, cy - 25, cx - 55, cy - 5, (56, 189, 248, 255)),
            (cx, my0 + 52, cx, cy - 46, (34, 197, 94, 255)),
            (mx1 - 90, cy + 25, cx + 55, cy + 5, (250, 204, 21, 255)),
        ]
        prog = 0.35 if phase == 0 else (0.85 if phase == 1 else 1.0)
        for x_s, y_s, x_e, y_e, col in vecs:
            xm = int(x_s + (x_e - x_s) * prog)
            ym = int(y_s + (y_e - y_s) * prog)
            d.line([(x_s, y_s), (xm, ym)], fill=col, width=6)
            d.ellipse([xm - 9, ym - 9, xm + 9, ym + 9], fill=col)
    else:
        d.text((mx0 + 22, my0 + 12), "ТАКТИКА «ТОЛҒАМА»: КОЛЬЦО У ОЗЕРА АЛАКОЛЬ (1729)", font=f_map, fill=(148, 163, 184, 230))
        # Salt lake Alakol on East (right side)
        d.rounded_rectangle([mx1 - 150, my0 + 60, mx1 - 36, my1 - 24], radius=22, fill=(14, 116, 144, 180), outline=(56, 189, 248, 220), width=2)
        # Invading red force pinned in center-right
        for rx in range(cx - 10, mx1 - 190, 32):
            for ry in (cy - 18, cy + 16):
                d.ellipse([rx - 9, ry - 9, rx + 9, ry + 9], fill=(239, 68, 68, 235))
        # Kazakh Tolgama crescent wings sweeping around top & bottom to close the ring
        arc_top = [(mx0 + 110 + i * 48, int(cy - 52 - 18 * math.sin(i * 0.45))) for i in range(12)]
        arc_bot = [(mx0 + 110 + i * 48, int(cy + 52 + 18 * math.sin(i * 0.45))) for i in range(12)]
        d.line(arc_top, fill=(34, 197, 94, 255), width=6)
        d.line(arc_bot, fill=(34, 197, 94, 255), width=6)
        # Zhekpe-zhek duel star in center
        d.ellipse([cx - 48, cy - 16, cx - 16, cy + 16], fill=(250, 204, 21, 255))

    im.alpha_composite(ov)


def load_video_frames_local(mp4_path: Path, n_out: int):
    raw = subprocess.run(
        [
            FFMPEG_BIN, "-v", "error", "-i", str(mp4_path),
            "-vf", f"scale={rmod.W}:{rmod.H}:force_original_aspect_ratio=increase:flags=bicubic,crop={rmod.W}:{rmod.H}",
            "-f", "rawvideo", "-pix_fmt", "rgb24", "-",
        ],
        capture_output=True,
        check=True,
    ).stdout
    fb = rmod.W * rmod.H * 3
    m = max(1, len(raw) // fb)
    src = [
        np.frombuffer(raw, dtype=np.uint8, count=fb, offset=i * fb).reshape((rmod.H, rmod.W, 3))
        for i in range(m)
    ]
    return [src[min(m - 1, int(i * m / max(1, n_out)))] for i in range(max(1, n_out))]


def segs_with_scene_idx(tl):
    segs = []
    for si, sc in enumerate(tl["scenes"]):
        imgs, t0, t1 = sc["images"], sc["t0"], sc["t1"]
        step = (t1 - t0) / len(imgs)
        for i, name in enumerate(imgs):
            segs.append({
                "name": name,
                "scene_idx": si,
                "t0": t0 + i * step,
                "t1": t0 + (i + 1) * step,
            })
    return segs


def render_ep01_tactical_video(lang: str):
    B = ROOT / "build" / lang
    tl = json.loads((B / "timeline.json").read_text(encoding="utf-8"))
    words = json.loads((B / "words.json").read_text(encoding="utf-8"))
    T = tl["T"]
    segs = segs_with_scene_idx(tl)
    chunks = rmod.chunks_from(words, T)
    F = math.ceil(T * rmod.FPS)

    vig = rmod.vignette()[..., None]
    cache = {}
    vid_path = B / "video.mp4"
    ff = subprocess.Popen(
        [
            FFMPEG_BIN, "-y", "-hide_banner", "-loglevel", "error", "-f", "rawvideo",
            "-pix_fmt", "rgb24", "-s", f"{rmod.W}x{rmod.H}", "-r", str(rmod.FPS), "-i", "-",
            "-c:v", "libx264", "-preset", "faster", "-crf", "20", "-maxrate", "6M",
            "-bufsize", "12M", "-pix_fmt", "yuv420p", "-g", "60", str(vid_path),
        ],
        stdin=subprocess.PIPE,
    )

    si = ci = 0
    cur_name = None
    cur_frames = None
    for fi in range(F):
        t = fi / rmod.FPS
        while si + 1 < len(segs) and t >= segs[si + 1]["t0"]:
            si += 1
        sg = segs[si]
        name = sg["name"]
        tau = t - sg["t0"]
        seg_dur = max(0.1, sg["t1"] - sg["t0"])
        u = min(1.0, max(0.0, tau / seg_dur))

        if name != cur_name:
            cur_name = name
            vp = VIDEO_DIR / f"{name}.mp4"
            cur_frames = load_video_frames_local(vp, min(90, max(8, int(round(seg_dur * rmod.FPS)))))

        idx = min(len(cur_frames) - 1, int(u * len(cur_frames)))
        arr = (cur_frames[idx].astype(np.uint16) * vig) >> 8
        if name in ("scene_08", "scene_17") and tau < 0.32:
            arr = arr + ((255 - arr) * (0.80 * math.exp(-tau / 0.08))).astype(np.uint16)
        im = Image.fromarray(arr.astype(np.uint8)).convert("RGBA")

        # Tactical HUD overlay
        draw_ep01_tactical_hud(im, sg["scene_idx"], tau, seg_dur)

        # Dynamic word-by-word subtitles
        while ci + 1 < len(chunks) and t >= chunks[ci + 1]["t0"]:
            ci += 1
        ch = chunks[ci]
        if ch["t0"] <= t < ch["t1"]:
            act = max(i for i, w in enumerate(ch["words"]) if w["t0"] <= t or i == 0)
            key = (ci, act)
            if key not in cache:
                cache[key] = rmod.render_chunk(ch["words"], act)
            ov = cache[key]
            pop = t - ch["t0"]
            if pop < 0.09:
                sc = 0.86 + 0.14 * (1 - (1 - pop / 0.09) ** 2)
                ov = ov.resize((max(1, int(ov.width * sc)), max(1, int(ov.height * sc))), Image.BILINEAR)
            im.paste(ov, (int(rmod.W / 2 - ov.width / 2), int(1180 - ov.height / 2)), ov)

        ff.stdin.write(im.convert("RGB").tobytes())

    ff.stdin.close()
    ff.wait()

    OUTPUT.mkdir(exist_ok=True)
    out = OUTPUT / f"EP01_Ordabasy_Shorts_{lang.upper()}.mp4"
    subprocess.run(
        [
            FFMPEG_BIN, "-y", "-hide_banner", "-loglevel", "error", "-i", str(vid_path),
            "-i", str(B / "mix.wav"), "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac",
            "-b:a", "192k", "-ar", "48000", "-shortest", "-movflags", "+faststart", str(out),
        ],
        check=True,
    )
    print(f"[done] {out} ({out.stat().st_size // (1024 * 1024)} MB)")


def main():
    langs = [a for a in sys.argv[1:] if not a.startswith("--")] or ["ru", "kz", "en"]
    force_voice = "--rebuild-voice" in sys.argv
    print("[1/4] Rebuilding all 23 Episode 1 scene clips with rigid camera motion (zero floating/jelly warp)...")
    build_all_ep01_clips()
    for lang in langs:
        B = ROOT / "build" / lang
        if force_voice or not (B / "mix.wav").exists():
            print(f"[2/4] Synthesizing live neural voiceover for Episode 1 ({lang})...")
            asyncio.run(build_neural_voice_ep01_async(lang))
            print(f"[3/4] Mixing Ordabasy & Anyrakai SFX + A cappella ({lang})...")
            smod.run(lang)
        else:
            print(f"[2-3/4] Reusing neural voiceover & SFX mix for Episode 1 ({lang}) -> {B / 'mix.wav'}")
        print(f"[4/4] Rendering 1080x1920 tactical explainer video for Episode 1 ({lang})...")
        render_ep01_tactical_video(lang)


if __name__ == "__main__":
    main()
