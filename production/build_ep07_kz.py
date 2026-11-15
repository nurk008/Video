#!/usr/bin/env python3
"""Episode 07 Builder (KZ ONLY): Bulanty-Bileuti Battle (1728) — Kalmak Kyrylgan.

Combines EP04's high-retention structure (no dates in hook, bright vista plates
on Scenes 01-03, 4 tactical pillars, seamless loop) with EP05's 6 live
3D hillshaded tactical maps and kinetic infographics.

Usage:
    /Users/market/antigravity/Video/.venv/bin/python3 production/build_ep07_kz.py
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
from pathlib import Path

import edge_tts
import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw
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

W, H, FPS = rmod.W, rmod.H, rmod.FPS
SR = smod.SR

# Prepend bundled ffmpeg dir so downstream libraries see the binary directory if needed.
_ffmpeg_dir = str(Path(FFMPEG).parent)
if _ffmpeg_dir not in os.environ.get("PATH", ""):
    os.environ["PATH"] = _ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")

EP07_SCRIPT_KZ = [
    "Зеңбіректі қалың жау дала жұртын біржола тізе бүктірдім деп ойлады — бірақ Ұлытау етегіндегі бір шайқаста бүкіл әскерінен қалай айырылды?",
    "Мың жеті жүз жиырма сегізінші жыл. Ауыр зеңбірек пен отты қаруға сүйенген басқыншы қол Орталық Қазақстанның жүрегі — Ұлытауға қарай бет алды.",
    "Бес жыл бұрынғы ауыр шегіністен соң, қарсылас далада енді ешкім қарсы тұра алмайды деп нық сенді.",
    "Алайда Ордабасы антынан кейін Әбілқайыр хан бастаған біріккен қазақ қолы жауды дәл Ұлытау етегінде күтіп тұрған еді!",
    "Бірінші әдіс — жасырын топтасу. Қазақ жасақтары ашық жазықта көрінбей, Ұлытаудың тар сайлары мен өзен аңғарларына алдын ала бекінді.",
    "Барлаушылар қарсыластың әр қадамын бақылап, негізгі алпыс мыңдық атты қолды соққы беретін шепке үнсіз жинады.",
    "Екінші әдіс — жер бедерінің қақпаны. Әбілқайыр хан мен батырлар шайқас орны ретінде Бұланты мен Білеуті өзендерінің арасын таңдады.",
    "Жүздеген шақырым жолдан шаршаған жаудың ауыр зеңбіректері мен арбалары өзен өткелдері мен жұмсақ топырақта баяулап, сапы созылып кетті.",
    "Үшінші әдіс — авангардтың найзағай соққысы. Алдыңғы шепте Тайлақ батыр мен Саурық батыр бастаған ұшқыр жасақтар жау керуеніне тұтқиылдан тиді.",
    "Шапшаң атты сарбаздар жаудың алдыңғы тобын негізгі обоздан бөліп тастап, зеңбіректерді бұрып үлгертпей тығырыққа тіреді.",
    "Шешуші сәт Қара-Сиыр жазығында туды. Тәртібі бұзылған басқыншы қол тар аңғарда қоршауға түскенін кеш түсінді.",
    "Төртінші әдіс — қос қанаттан толық қоршау! Бөгенбай мен Қабанбай батырлар бастаған негізгі атты әскер екі бүйірден бір мезетте лап қойды.",
    "Қара-Сиыр даласындағы бірнеше күндік шайқаста басқыншы әскер толық талқандалып, «жеңілмейді» деген аңыз сол жерде күйреді!",
    "Халық бұл тарихи жеңіс орнын «Қалмақ қырылған» деп атады, ал Бұланты шайқасы Аңырақайдағы ұлы жеңіске тікелей жол ашты.",
    "Екі ғасыр бұрын Қасым хан жеңіске жеткен қасиетті Ұлытау даласы тағы да ел бірлігі мен әскери ақылдың қалқанына айналды.",
    "Сөйтіп, темірдей тәртіп, жер сырын білу және ортақ қолбасшылық ең қуатты әскерді де тізе бүктірді, өйткені...",
]

# Photoreal plate files (zero-face, historically authentic) and 3D map scenes.
MAP_SCENES = {3, 5, 7, 9, 11, 13}
STILL_FILES = {
    0: "scene_01.jpg",
    1: "scene_02.jpg",
    2: "scene_03.jpg",
    4: "scene_05.jpg",
    6: "scene_07.jpg",
    8: "scene_09.jpg",
    10: "scene_11.jpg",
    12: "scene_13.jpg",
    14: "scene_15.jpg",
    15: "scene_16.jpg",
}

HUD_META_KZ = {
    "pillars": ["1. ТОПТАСУ", "2. АҢҒАР", "3. АВАНГАРД", "4. ҚОРШАУ"],
    "banners": [
        ("ҰЛЫТАУДАҒЫ ЖҰМБАҚ ШАЙҚАС", "ДАЛА СЫРЫН БІЛМЕГЕН ҚОЛ ҚАЛАЙ КҮЙРЕДІ?", 0),
        ("1728 ЖЫЛ • ОРТАЛЫҚ ҚАЗАҚСТАН", "АУЫР ЗЕҢБІРЕКТІ ҚОЛ ҰЛЫТАУҒА ЖЫЛЖЫДЫ", 0),
        ("БЕС ЖЫЛДАН КЕЙІНГІ СЕНІМ", "ҚАРСЫЛАС ДАЛАНЫ ҚАУҚАРСЫЗ ДЕП ОЙЛАДЫ", 0),
        ("ОРДАБАСЫ АНТЫ • ӘБІЛҚАЙЫР ХАН", "БІРІККЕН ҚОЛ ҰЛЫТАУДА ТОСЫП ТҰРДЫ", 0),
        ("1-ТӘСІЛ • ЖАСЫРЫН ТОПТАСУ", "60 000 САРБАЗ САЙ МЕН АҢҒАРҒА БЕКІНДІ", 0),
        ("БАРЛАУ ЖӘНЕ ШЕП ҚҰРУ", "ҮШ БАҒЫТТАН ҮНСІЗ ЖИНАЛУ", 0),
        ("2-ТӘСІЛ • ЖЕР БЕДЕРІНІҢ ҚАҚПАНЫ", "БҰЛАНТЫ МЕН БІЛЕУТІ ӨЗЕНДЕРІНІҢ АРАСЫ", 1),
        ("ӨТКЕЛДЕР МЕН ОЙПАТТЫ АҢҒАР", "АУЫР ЗЕҢБІРЕКТІ ОБОЗ ЖОЛДА БАЯУЛАДЫ", 1),
        ("3-ТӘСІЛ • АВАНГАРД СОҚҚЫСЫ", "ТАЙЛАҚ ПЕН САУРЫҚ БАТЫРЛАРДЫҢ ШАБУЫЛЫ", 2),
        ("ҚАРА-СИЫР ТҰТҚЫЙЫЛ СОҚҚЫСЫ", "АЛДЫҢҒЫ ШЕПТІ НЕГІЗГІ ОБОЗДАН БӨЛУ", 2),
        ("ҚАРА-СИЫР ЖАЗЫҒЫ • ШЕШУШІ СӘТ", "ТАР АҢҒАРДАҒЫ ҚОРШАУ ШЕҢБЕРІ", 2),
        ("4-ТӘСІЛ • ҚОС ҚАПТАЛДАН ҚОРШАУ", "БӨГЕНБАЙ • ҚАБАНБАЙ ҚОС ҚАНАТЫ", 3),
        ("ЖЕҢІЛМЕЙДІ ДЕГЕН АҢЫЗ КҮЙРЕДІ", "ҚАРА-СИЫР ДАЛАСЫНДАҒЫ ТОЛЫҚ ЖЕҢІС", 3),
        ("«ҚАЛМАҚ ҚЫРЫЛҒАН» • 1728 ЖЫЛ", "БҰЛАНТЫ ЖЕҢІСІ АҢЫРАҚАЙҒА ЖОЛ АШТЫ", 3),
        ("ҰЛЫТАУ • 1510 ЖӘНЕ 1728", "ЕЛ БІРЛІГІ МЕН ӘСКЕРИ АҚЫЛ ҚАЛҚАНЫ", 3),
        ("ЖЕҢІС ФОРМУЛАСЫ", "ТӘРТІП • ЖЕР СЫРЫ • ҚОЛБАСШЫЛЫҚ", 3),
    ],
}

# Pause durations between scenes (tight on hook & seamless end loop).
PAUSE_AFTER = [
    0.16, 0.14, 0.14, 0.16,
    0.14, 0.16, 0.14, 0.16,
    0.14, 0.16, 0.14, 0.16,
    0.18, 0.16, 0.14, 0.04,
]

# Sub-pixel rigid camera choreography for each photoreal scene index.
SCENE_CAM = {
    0:  dict(z0=1.02, z1=1.12, dx0=0.0,  dy0=0.0,   dx1=-16.0, dy1=-14.0),
    1:  dict(z0=1.10, z1=1.02, dx0=0.0,  dy0=-18.0, dx1=0.0,   dy1=14.0),
    2:  dict(z0=1.02, z1=1.12, dx0=-14., dy0=8.0,   dx1=16.0,  dy1=-10.0),
    4:  dict(z0=1.10, z1=1.02, dx0=14.0, dy0=-10.0, dx1=-12.0, dy1=10.0),
    6:  dict(z0=1.03, z1=1.13, dx0=-16., dy0=6.0,   dx1=18.0,  dy1=-8.0),
    8:  dict(z0=1.04, z1=1.16, dx0=-18., dy0=10.0,  dx1=18.0,  dy1=-12.0),
    10: dict(z0=1.11, z1=1.03, dx0=10.0, dy0=-12.0, dx1=-10.0, dy1=12.0),
    12: dict(z0=1.04, z1=1.16, dx0=0.0,  dy0=12.0,  dx1=0.0,   dy1=-18.0),
    14: dict(z0=1.02, z1=1.11, dx0=-12., dy0=14.0,  dx1=10.0,  dy1=-14.0),
    15: dict(z0=1.02, z1=1.10, dx0=0.0,  dy0=10.0,  dx1=0.0,   dy1=-14.0),
}

# Strategic geographical layout in 1080x1920 world coordinates.
EP07_NODES = {
    "Ұлытау":      (360, 415),
    "Бұланты":     (285, 605),
    "Қара-Сиыр":   (485, 575),
    "Білеуті":     (645, 655),
    "Шұбар-Теңіз": (425, 755),
    "Сарысу":      (765, 735),
    "Түркістан":   (360, 865),
    "Ордабасы":    (555, 935),
    "Аңырақай":    (825, 885),
}
EP07_LABEL_SIDE = {
    "Ұлытау":      "above",
    "Бұланты":     "left",
    "Қара-Сиыр":   "above",
    "Білеуті":     "right",
    "Шұбар-Теңіз": "left",
    "Сарысу":      "right",
    "Түркістан":   "left",
    "Ордабасы":    "below",
    "Аңырақай":    "above",
}
BULANTY_PTS = [(220, 465), (305, 555), (365, 645), (415, 750)]
BILEUTI_PTS = [(505, 455), (560, 565), (590, 675), (475, 770)]
SARYSU_PTS  = [(930, 495), (810, 625), (705, 740), (545, 865)]

VOICE_PRIMARY = "kk-KZ-DauletNeural"
VOICE_FALLBACK = "kk-KZ-AigulNeural"
VOICE_RATE = "-2%"
VOICE_PITCH = "-2Hz"


def ensure_dirs() -> tuple[Path, Path, Path, Path]:
    build_dir = PROD / "build_ep07" / "kz"
    qa_dir = PROD / "build_ep07" / "qa"
    scenes_dir = ROOT / "scenes_ep07"
    out_dir = ROOT / "output"
    for d in (build_dir, qa_dir, out_dir):
        d.mkdir(parents=True, exist_ok=True)
    return build_dir, qa_dir, scenes_dir, out_dir


def verify_hud_and_glyphs():
    """Verify Montserrat-Black glyph coverage and banner/pill pixel widths."""
    texts = []
    for t, s, _ in HUD_META_KZ["banners"]:
        texts.extend([t, s])
    texts.extend(HUD_META_KZ["pillars"])
    texts.extend(EP07_NODES.keys())
    texts.extend([
        "«ҚАЛМАҚ ҚЫРЫЛҒАН» • 1728 ЖЫЛ",
        "БҰЛАНТЫ  •  БІЛЕУТІ",
        "ШҰБАР-ТЕҢІЗ",
    ])

    try:
        from fontTools.ttLib import TTFont
        cmap = TTFont(str(FONT_PATH)).getBestCmap()
        missing = sorted({ch for txt in texts + EP07_SCRIPT_KZ for ch in txt if not ch.isspace() and ord(ch) not in cmap})
        if missing:
            raise ValueError(f"Missing glyphs in {FONT_PATH.name}: {missing}")
    except ImportError:
        pass

    probe_img = Image.new("RGBA", (10, 10))
    d = ImageDraw.Draw(probe_img)
    f_top, f_sub = rmod.font(34), rmod.font(28)
    for si, (top_t, sub_t, _) in enumerate(HUD_META_KZ["banners"]):
        if d.textlength(top_t, font=f_top) > W - 150:
            raise ValueError(f"Banner title too wide on scene {si}: {top_t}")
        if d.textlength(sub_t, font=f_sub) > W - 140:
            raise ValueError(f"Sub callout too wide on scene {si}: {sub_t}")


# ---------------------------------------------------------------------------
# Voice Synthesis, Processing & Alignment
# ---------------------------------------------------------------------------

async def _tts_one(text: str, mp3_path: Path, voice: str) -> list[dict]:
    comm = edge_tts.Communicate(text, voice, rate=VOICE_RATE, pitch=VOICE_PITCH)
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


async def _tts_all_async(lines: list[str], audio_dir: Path) -> list[tuple[Path, list[dict]]]:
    manifest_path = audio_dir / "manifest.json"
    lines_hash = hashlib.sha256(
        json.dumps(
            {"voice": VOICE_PRIMARY, "rate": VOICE_RATE, "pitch": VOICE_PITCH, "lines": lines},
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()

    cached_ok = False
    cached_meta: dict = {}
    if manifest_path.exists():
        try:
            cached_meta = json.loads(manifest_path.read_text(encoding="utf-8"))
            if cached_meta.get("hash") == lines_hash and len(cached_meta.get("items", [])) == len(lines):
                cached_ok = all((audio_dir / f"seg_{i:02d}.mp3").exists() for i in range(len(lines)))
        except Exception:
            cached_ok = False

    if cached_ok:
        return [(audio_dir / f"seg_{i:02d}.mp3", cached_meta["items"][i]["bounds"]) for i in range(len(lines))]

    results: list[tuple[Path, list[dict]]] = []
    items_meta = []
    voice_used = VOICE_PRIMARY
    for i, text in enumerate(lines):
        mp3_path = audio_dir / f"seg_{i:02d}.mp3"
        try:
            bounds = await _tts_one(text, mp3_path, voice_used)
        except Exception:
            voice_used = VOICE_FALLBACK
            bounds = await _tts_one(text, mp3_path, voice_used)
        results.append((mp3_path, bounds))
        items_meta.append({"bounds": bounds})

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
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        import wave
        with wave.open(wav_tmp, "rb") as w:
            raw = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32)
        return raw / 32768.0
    finally:
        if os.path.exists(wav_tmp):
            os.remove(wav_tmp)


def _trim_silence(x: np.ndarray, head_pad: float = 0.05, tail_pad: float = 0.08) -> tuple[np.ndarray, float, float]:
    thr = max(0.008, float(np.max(np.abs(x))) * 0.012)
    idx = np.where(np.abs(x) > thr)[0]
    if len(idx) == 0:
        return x, 0.0, len(x) / SR
    i0 = max(0, int(idx[0]) - int(head_pad * SR))
    i1 = min(len(x), int(idx[-1]) + int(tail_pad * SR))
    seg = x[i0:i1].copy()
    f = min(len(seg) // 4, int(0.015 * SR))
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
    # Warm low-mid body + gentle presence clarity without harshness.
    body = smod.bp(y, 120.0, 280.0) * 0.14
    pres = smod.bp(y, 2400.0, 4800.0) * 0.10
    y = y + body + pres
    peak = float(np.max(np.abs(y)))
    if peak > 1e-6:
        y = y / peak * 0.88
    return smod.softclip(y, 0.84)


def _align_words(text: str, bounds: list[dict], trim_t0: float, trim_t1: float, seg_dur: float, t_offset: float) -> list[dict]:
    tokens = text.split()
    out: list[dict] = []
    raw_span = max(0.2, trim_t1 - trim_t0)
    if bounds and len(bounds) >= max(2, int(len(tokens) * 0.55)):
        # Match tokens onto WordBoundary timestamps, clamped into [0, seg_dur].
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
        # Fill any unmatched token gaps via linear interpolation.
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

    # Fallback: character-weighted phoneme alignment across active speech span.
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


def synthesize_ep07(build_dir: Path) -> tuple[np.ndarray, list[dict], list[dict], float]:
    raw_items = asyncio.run(_tts_all_async(EP07_SCRIPT_KZ, build_dir))
    segments_audio: list[np.ndarray] = []
    timeline: list[dict] = []
    words_all: list[dict] = []

    cursor = 0.0
    for si, ((mp3_path, bounds), text) in enumerate(zip(raw_items, EP07_SCRIPT_KZ)):
        raw_x = _decode_mp3_mono(mp3_path)
        head_pad = 0.03 if si == 0 else 0.05
        tail_pad = 0.04 if si == len(EP07_SCRIPT_KZ) - 1 else 0.08
        seg_x, t0_trim, t1_trim = _trim_silence(raw_x, head_pad=head_pad, tail_pad=tail_pad)
        seg_x = _voice_fx(seg_x)
        seg_dur = len(seg_x) / SR

        words_seg = _align_words(text, bounds, t0_trim, t1_trim, seg_dur, cursor)
        words_all.extend(words_seg)

        timeline.append({"si": si, "t0": cursor, "t1": cursor + seg_dur, "dur": seg_dur})
        segments_audio.append(seg_x)
        cursor += seg_dur

        pause = PAUSE_AFTER[si] if si < len(PAUSE_AFTER) else 0.14
        if pause > 0:
            segments_audio.append(np.zeros(int(round(pause * SR)), dtype=np.float32))
            cursor += pause

    voice_full = np.concatenate(segments_audio).astype(np.float32)
    total_dur = len(voice_full) / SR

    (build_dir / "timeline.json").write_text(json.dumps({"dur": total_dur, "scenes": timeline}, indent=2), encoding="utf-8")
    (build_dir / "words.json").write_text(json.dumps(words_all, ensure_ascii=False, indent=2), encoding="utf-8")
    return voice_full, timeline, words_all, total_dur


# ---------------------------------------------------------------------------
# Halal Physical SFX + Male A Cappella Mix + Portable Loudnorm
# ---------------------------------------------------------------------------

def river_splash(rng: np.random.Generator, dur: float = 0.9) -> np.ndarray:
    n = int(SR * dur)
    t = np.linspace(0, dur, n, dtype=np.float32)
    noise = rng.standard_normal(n).astype(np.float32)
    spray = smod.bp(noise, 700, 3200) * np.exp(-t * 3.8)
    rumble = smod.bp(noise, 140, 480) * np.exp(-t * 2.4) * 0.7
    env = np.minimum(1.0, t / 0.03)
    return smod.norm((spray + rumble) * env, 0.72)


def loudnorm_portable(src_wav: Path, dst_wav: Path, I: float = -14.0, TP: float = -1.5, LRA: float = 11.0):
    """Two-pass EBU R128 loudness normalization using the bundled ffmpeg binary."""
    p1 = subprocess.run(
        [
            FFMPEG, "-y", "-i", str(src_wav),
            "-af", f"loudnorm=I={I}:TP={TP}:LRA={LRA}:print_format=json",
            "-f", "null", "-",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    m = re.search(r"\{[\s\S]*?\"input_i\"[\s\S]*?\}", p1.stderr)
    if not m:
        subprocess.run(
            [
                FFMPEG, "-y", "-i", str(src_wav),
                "-af", f"loudnorm=I={I}:TP={TP}:LRA={LRA}",
                "-ar", str(SR), "-ac", "2", str(dst_wav),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
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
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def build_ep07_audio(build_dir: Path, voice_mono: np.ndarray, timeline: list[dict], dur: float) -> Path:
    mix_raw = build_dir / "mix_raw.wav"
    mix_wav = build_dir / "mix_ep07.wav"
    if mix_wav.exists() and mix_wav.stat().st_size > 100_000:
        return mix_wav
    rng = np.random.default_rng(70701)
    n_samples = len(voice_mono)
    amb = np.zeros((n_samples, 2), dtype=np.float32)

    # 1. Continuous Ulutau steppe wind bed.
    wbed = smod.wind(rng, dur + 0.5, howl=0.22)
    smod.add(amb, smod.st(wbed[:n_samples], -0.04) * 0.24, 0.0)

    # 2. Pure male a cappella harmonic progression across 4 acts (zero instruments).
    act_defs = [
        (0, 4,  [73.42, 110.0, 146.83, 220.0],  "o", 3, 0.17),
        (4, 8,  [82.41, 123.47, 164.81, 246.94], "a", 3, 0.16),
        (8, 13, [98.00, 146.83, 196.00, 293.66], "u", 4, 0.19),
        (13, 16,[110.00, 164.81, 220.00, 329.63], "a", 4, 0.20),
    ]
    for s_lo, s_hi, freqs, vowel, voices, gain in act_defs:
        a0 = timeline[s_lo]["t0"]
        a1 = timeline[s_hi - 1]["t1"]
        pad = smod.vocal_pad(rng, max(1.0, a1 - a0 + 0.6), freqs, vowel=vowel, voices=voices)
        pad_st = smod.reverb(pad, wet=0.30, seed=7100 + s_lo)
        smod.add(amb, pad_st * gain, a0)

    # 3. Physical tactical & steppe SFX synced tightly to each scene.
    for row in timeline:
        si, t0, sd = row["si"], row["t0"], row["dur"]
        if si == 0:
            # Immediate 0-1s scroll-stopper sound punch + soaring eagle.
            smod.add(amb, smod.reverb(smod.impact_boom(rng, 1.5), wet=0.30, seed=701) * 0.65, 0.02)
            smod.add(amb, smod.reverb(smod.sword_clash(rng), wet=0.22, seed=702) * 0.50, 0.05)
            smod.add(amb, smod.st(smod.eagle(rng), 0.22) * 0.36, 0.25)
        elif si == 1:
            smod.add(amb, smod.st(smod.herd_far(rng, sd), -0.15) * 0.42, t0)
        elif si == 2:
            smod.add(amb, smod.reverb(smod.thud(rng), wet=0.20, seed=703) * 0.45, t0 + 0.25)
            smod.add(amb, smod.reverb(smod.clasp(rng), wet=0.18, seed=704) * 0.34, t0 + sd * 0.55)
        elif si == 3:
            smod.add(amb, smod.reverb(smod.sword_draw(rng, 0.8), wet=0.24, seed=705) * 0.46, t0 + 0.15)
            smod.add(amb, smod.st(smod.riser(rng, min(1.6, sd * 0.5)), 0.0) * 0.36, t0 + sd * 0.35)
        elif si == 4:
            smod.add(amb, smod.st(smod.herd_far(rng, sd), 0.18) * 0.44, t0)
        elif si == 5:
            smod.add(amb, smod.st(smod.whoosh(rng, 0.55), -0.22) * 0.40, t0 + 0.20)
            smod.add(amb, smod.st(smod.herd(rng, sd * 0.8), 0.10) * 0.36, t0 + sd * 0.15)
        elif si == 6:
            smod.add(amb, smod.st(river_splash(rng, 1.0), -0.15) * 0.50, t0 + 0.25)
            smod.add(amb, smod.reverb(smod.thud(rng), wet=0.22, seed=706) * 0.40, t0 + sd * 0.58)
        elif si == 7:
            smod.add(amb, smod.st(river_splash(rng, 1.1), 0.18) * 0.48, t0 + 0.20)
            smod.add(amb, smod.reverb(smod.thunder(rng, 1.8), wet=0.30, seed=707) * 0.38, t0 + sd * 0.45)
        elif si == 8:
            smod.add(amb, smod.reverb(smod.sword_clash(rng), wet=0.22, seed=708) * 0.52, t0 + 0.08)
            smod.add(amb, smod.st(smod.gallop(rng, sd, horses=14, rate=3.2), 0.0) * 0.54, t0)
            smod.add(amb, smod.st(smod.whoosh(rng, 0.45), 0.25) * 0.42, t0 + sd * 0.45)
        elif si == 9:
            smod.add(amb, smod.st(smod.whoosh(rng, 0.45), -0.25) * 0.44, t0 + 0.15)
            smod.add(amb, smod.reverb(smod.sword_clash(rng), wet=0.22, seed=709) * 0.46, t0 + sd * 0.50)
        elif si == 10:
            smod.add(amb, smod.reverb(smod.sword_draw(rng, 0.85), wet=0.25, seed=710) * 0.48, t0 + 0.12)
            smod.add(amb, smod.reverb(smod.impact_boom(rng, 1.4), wet=0.28, seed=711) * 0.48, t0 + sd * 0.55)
        elif si == 11:
            smod.add(amb, smod.st(smod.gallop(rng, sd, horses=16, rate=3.0), 0.0) * 0.55, t0)
            smod.add(amb, smod.reverb(smod.impact_boom(rng, 1.6), wet=0.30, seed=712) * 0.54, t0 + 0.20)
            smod.add(amb, smod.reverb(smod.thunder(rng, 1.6), wet=0.28, seed=713) * 0.38, t0 + sd * 0.52)
        elif si == 12:
            smod.add(amb, smod.st(smod.gallop(rng, sd * 0.85, horses=12, rate=2.8), 0.12) * 0.48, t0)
            smod.add(amb, smod.reverb(smod.impact_boom(rng, 1.7), wet=0.30, seed=714) * 0.52, t0 + sd * 0.48)
            smod.add(amb, smod.st(smod.eagle(rng), -0.20) * 0.36, t0 + sd * 0.72)
        elif si == 13:
            smod.add(amb, smod.reverb(smod.clasp(rng), wet=0.25, seed=715) * 0.46, t0 + 0.18)
            smod.add(amb, smod.reverb(smod.impact_boom(rng, 1.4), wet=0.28, seed=716) * 0.46, t0 + 0.30)
        elif si == 14:
            smod.add(amb, smod.st(smod.eagle(rng), 0.20) * 0.40, t0 + 0.25)
        elif si == 15:
            rlen = min(1.8, sd * 0.72)
            smod.add(amb, smod.st(smod.riser(rng, rlen), 0.0) * 0.42, max(t0, dur - rlen - 0.04))

    rms = smod.frame_rms(voice_mono, win=0.05)
    rms_st = np.interp(np.arange(n_samples), np.arange(len(rms)) * int(SR * 0.05), rms)
    duck = 1.0 - 0.56 * np.clip(rms_st / 0.085, 0.0, 1.0)
    amb *= duck[:, None]

    out = amb * 0.90 + smod.st(voice_mono, 0.0) * 1.00
    out = smod.softclip(out, 0.90)
    smod.write(str(mix_raw), out)
    loudnorm_portable(mix_raw, mix_wav, I=-14.0, TP=-1.5, LRA=11.0)
    return mix_wav


# ---------------------------------------------------------------------------
# Visuals: Rigid Camera, Atmospheric Dust, Custom Cards & Bulanty 3D Maps
# ---------------------------------------------------------------------------

def rigid_cam_frame(plate_rgba: Image.Image, si: int, u: float, tau: float, shake: bool = False) -> Image.Image:
    cfg = SCENE_CAM[si]
    s = anim.smoothstep(u)
    z = cfg["z0"] + (cfg["z1"] - cfg["z0"]) * s
    dx = cfg["dx0"] + (cfg["dx1"] - cfg["dx0"]) * s
    dy = cfg["dy0"] + (cfg["dy1"] - cfg["dy0"]) * s
    if shake and tau < 0.55:
        decay = (1.0 - tau / 0.55) ** 2
        dx += math.sin(tau * 42.0) * 7.5 * decay
        dy += math.cos(tau * 55.0) * 6.0 * decay

    vw, vh = W / z, H / z
    cx = W * 0.5 - dx
    cy = H * 0.5 - dy
    x0 = max(0.0, min(W - vw, cx - vw * 0.5))
    y0 = max(0.0, min(H - vh, cy - vh * 0.5))
    return plate_rgba.transform((W, H), Image.Transform.EXTENT, (x0, y0, x0 + vw, y0 + vh), Image.Resampling.BICUBIC)


def overlay_particles(ov: Image.Image, t: float, seed: int = 7, warm: bool = True, count: int = 26):
    d = ImageDraw.Draw(ov)
    rng = np.random.default_rng(seed)
    xs = rng.uniform(40, W - 40, count)
    ys = rng.uniform(220, H - 300, count)
    sp = rng.uniform(22, 68, count)
    rs = rng.uniform(1.6, 3.6, count)
    for k in range(count):
        px = (xs[k] + t * sp[k] * 0.55) % W
        py = (ys[k] - t * sp[k] * 0.72) % (H - 360) + 180
        al = int(70 + 60 * math.sin(t * 2.4 + k * 0.9))
        col = (255, 218, 128, al) if warm else (180, 232, 245, al)
        d.ellipse([px - rs[k], py - rs[k], px + rs[k], py + rs[k]], fill=col)


def _draw_card_box(d: ImageDraw.ImageDraw, x0: int, y0: int, cw: int, ch: int, pop: float, fill_rgb=(12, 18, 28), out_rgb=(248, 202, 84)):
    d.rounded_rectangle(
        [x0, y0, x0 + cw, y0 + ch],
        radius=18,
        fill=(*fill_rgb, int(224 * pop)),
        outline=(*out_rgb, int(242 * pop)),
        width=3,
    )


def draw_badge_card(ov: Image.Image, title: str, sub: str, col=(248, 202, 84), tau: float = 0.25, y0: int = 1432):
    d = ImageDraw.Draw(ov)
    pop = anim.ease_out(min(1.0, tau / 0.20))
    cw, ch = 820, 102
    x0 = (W - cw) // 2
    yy = y0 + int(16 * (1.0 - pop))
    _draw_card_box(d, x0, yy, cw, ch, pop, fill_rgb=(12, 16, 24), out_rgb=col)
    f1, f2 = rmod.font(30), rmod.font(21)
    d.text(((W - d.textlength(title, font=f1)) / 2, yy + 14), title, font=f1, fill=(*col, int(252 * pop)))
    d.text(((W - d.textlength(sub, font=f2)) / 2, yy + 58), sub, font=f2, fill=(242, 245, 248, int(242 * pop)))


def draw_mud_drag_card(ov: Image.Image, tau: float, seg_dur: float):
    d = ImageDraw.Draw(ov)
    pop = anim.ease_out(min(1.0, tau / 0.25))
    fill_u = anim.ease_out(min(1.0, max(0.0, (tau - 0.08) / max(0.7, seg_dur * 0.68))))
    cw, ch = 800, 134
    x0, y0 = (W - cw) // 2, 1418 + int(16 * (1.0 - pop))
    _draw_card_box(d, x0, y0, cw, ch, pop, fill_rgb=(22, 14, 14), out_rgb=(235, 92, 76))
    f1, f2 = rmod.font(27), rmod.font(21)
    t1 = "АУЫР ЗЕҢБІРЕК ПЕН ОБОЗ СЫНАҒЫ"
    d.text(((W - d.textlength(t1, font=f1)) / 2, y0 + 13), t1, font=f1, fill=(248, 198, 92, int(250 * pop)))

    bx0, by0, bw, bh = x0 + 44, y0 + 56, cw - 88, 28
    d.rounded_rectangle([bx0, by0, bx0 + bw, by0 + bh], radius=12, fill=(44, 24, 24, int(220 * pop)), outline=(180, 90, 82, int(190 * pop)), width=2)
    pct = max(0.28, 1.0 - 0.72 * fill_u)
    d.rounded_rectangle([bx0 + 3, by0 + 3, bx0 + 3 + int((bw - 6) * pct), by0 + bh - 3], radius=9, fill=(228, 78, 62, int(235 * pop)))
    sub = f"ЖЫЛДАМДЫҚ ТӨМЕНДЕУІ: {int(pct * 100)}%"
    d.text(((W - d.textlength(sub, font=f2)) / 2, y0 + 96), sub, font=f2, fill=(244, 246, 250, int(242 * pop)))


def draw_ep07_speed_card(ov: Image.Image, tau: float, seg_dur: float):
    d = ImageDraw.Draw(ov)
    pop = anim.ease_out(min(1.0, tau / 0.25))
    prog = anim.ease_out(min(1.0, max(0.0, (tau - 0.06) / max(0.7, seg_dur * 0.65))))
    cw, ch = 820, 144
    x0, y0 = (W - cw) // 2, 1410 + int(16 * (1.0 - pop))
    _draw_card_box(d, x0, y0, cw, ch, pop, fill_rgb=(12, 22, 30), out_rgb=(78, 224, 222))
    f1, f2 = rmod.font(24), rmod.font(21)
    hdr = "МАНЁВР ЖЫЛДАМДЫҒЫ • БҰЛАНТЫ-БІЛЕУТІ"
    d.text(((W - d.textlength(hdr, font=f1)) / 2, y0 + 12), hdr, font=f1, fill=(248, 202, 84, int(252 * pop)))

    # Fast Kazakh cavalry bar vs bogged heavy artillery bar.
    bx0, bw = x0 + 295, cw - 330
    d.text((x0 + 28, y0 + 55), "АТТЫ ЖАСАҚ  X3", font=f2, fill=(116, 232, 228, int(248 * pop)))
    d.rounded_rectangle([bx0, y0 + 53, bx0 + bw, y0 + 81], radius=10, fill=(22, 42, 48, 220))
    d.rounded_rectangle([bx0 + 2, y0 + 55, bx0 + 2 + int((bw - 4) * prog * 0.94), y0 + 79], radius=8, fill=(78, 224, 222, int(240 * pop)))

    d.text((x0 + 28, y0 + 98), "АУЫР ЗЕҢБІРЕК X1", font=f2, fill=(242, 128, 116, int(245 * pop)))
    d.rounded_rectangle([bx0, y0 + 96, bx0 + bw, y0 + 124], radius=10, fill=(42, 22, 24, 220))
    d.rounded_rectangle([bx0 + 2, y0 + 98, bx0 + 2 + int((bw - 4) * prog * 0.30), y0 + 122], radius=8, fill=(226, 78, 66, int(235 * pop)))


def draw_dual_hero_card(ov: Image.Image, tau: float):
    d = ImageDraw.Draw(ov)
    pop = anim.ease_out(min(1.0, tau / 0.24))
    y0 = 1425 + int(16 * (1.0 - pop))
    gap = 20
    card_w = 400
    x_left = (W - card_w * 2 - gap) // 2
    for idx, (name, role) in enumerate([("ТАЙЛАҚ БАТЫР", "ОҢТҮСТІК АЛАШ ҚОЛЫ"), ("САУРЫҚ БАТЫР", "ТОСЫН АВАНГАРД СОҚҚЫСЫ")]):
        cx0 = x_left + idx * (card_w + gap)
        _draw_card_box(d, cx0, y0, card_w, 108, pop, fill_rgb=(12, 24, 32), out_rgb=(78, 224, 222))
        f1, f2 = rmod.font(26), rmod.font(18)
        d.text((cx0 + (card_w - d.textlength(name, font=f1)) / 2, y0 + 18), name, font=f1, fill=(248, 202, 84, int(252 * pop)))
        d.text((cx0 + (card_w - d.textlength(role, font=f2)) / 2, y0 + 62), role, font=f2, fill=(130, 232, 230, int(242 * pop)))


def draw_encirclement_gauge_card(ov: Image.Image, tau: float, seg_dur: float):
    d = ImageDraw.Draw(ov)
    pop = anim.ease_out(min(1.0, tau / 0.24))
    prog = anim.ease_out(min(1.0, max(0.0, (tau - 0.05) / max(0.6, seg_dur * 0.70))))
    cw, ch = 800, 128
    x0, y0 = (W - cw) // 2, 1418 + int(16 * (1.0 - pop))
    _draw_card_box(d, x0, y0, cw, ch, pop, fill_rgb=(18, 16, 26), out_rgb=(248, 202, 84))

    f1, f2 = rmod.font(28), rmod.font(20)
    t1 = "ҚАРА-СИЫР ҚАЗАНЫ • ҚОРШАУ ШЕҢБЕРІ"
    d.text(((W - d.textlength(t1, font=f1)) / 2, y0 + 13), t1, font=f1, fill=(248, 202, 84, int(252 * pop)))

    bx0, by0, bw, bh = x0 + 50, y0 + 58, cw - 100, 24
    d.rounded_rectangle([bx0, by0, bx0 + bw, by0 + bh], radius=12, fill=(36, 24, 32, 220))
    fill_half = int((bw // 2 - 4) * prog)
    d.rounded_rectangle([bx0 + 3, by0 + 3, bx0 + 3 + fill_half, by0 + bh - 3], radius=8, fill=(248, 202, 84, int(245 * pop)))
    d.rounded_rectangle([bx0 + bw - 3 - fill_half, by0 + 3, bx0 + bw - 3, by0 + bh - 3], radius=8, fill=(78, 224, 222, int(245 * pop)))
    sub = f"ШЫҒУ ЖОЛДАРЫ ЖАБЫЛДЫ: {int(prog * 100)}%"
    d.text(((W - d.textlength(sub, font=f2)) / 2, y0 + 92), sub, font=f2, fill=(245, 246, 250, int(242 * pop)))


def render_ep07_map_canvas(zoom: float, cx: float, cy: float, t: float) -> tuple[Image.Image, anim.MapCamera]:
    """Crop 2x relief atlas to MapCamera with Bulanty, Bileuti, Sarysu rivers and Shubar-Teniz lake."""
    cam = anim.MapCamera(zoom, cx, cy)
    hi = anim.build_hi_relief_map()
    box_2x = (cam.x0 * 2.0, cam.y0 * 2.0, (cam.x0 + cam.vw) * 2.0, (cam.y0 + cam.vh) * 2.0)
    bg = hi.transform((W, H), Image.Transform.EXTENT, box_2x, Image.Resampling.BICUBIC).convert("RGBA")

    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)

    for gx_w in range(80, W, 140):
        d.line([cam.pt(gx_w, 120), cam.pt(gx_w, 1750)], fill=(210, 175, 102, 22), width=1)
    for gy_w in range(200, 1650, 140):
        d.line([cam.pt(20, gy_w), cam.pt(W - 20, gy_w)], fill=(210, 175, 102, 22), width=1)

    # Shubar-Teniz basin depression polygon.
    lake_w = [(380, 735), (435, 720), (485, 745), (465, 795), (400, 792), (365, 764)]
    lake_s = [cam.pt(px, py) for px, py in lake_w]
    d.polygon(lake_s, fill=(32, 118, 148, 148), outline=(92, 212, 238, 195))

    for wpts, count in ((BULANTY_PTS, 9), (BILEUTI_PTS, 9), (SARYSU_PTS, 10)):
        dense_w = anim.eval_polyline(wpts, 100)
        dense_s = cam.pts(dense_w)
        d.line(dense_s, fill=(24, 105, 138, 130), width=max(9, int(11 * zoom)))
        d.line(dense_s, fill=(76, 198, 228, 192), width=max(4, int(5 * zoom)))
        for k in range(count):
            u0 = (k / count + t * 0.12) % 1.0
            u1 = min(1.0, u0 + 0.04)
            x0, y0, _ = anim.point_along_path(dense_w, u0)
            x1, y1, _ = anim.point_along_path(dense_w, u1)
            alpha = int(165 * math.sin(math.pi * ((t * 1.6 + k * 0.7) % 1.0)) ** 2 + 55)
            d.line([cam.pt(x0, y0), cam.pt(x1, y1)], fill=(205, 250, 255, alpha), width=3)

    bg.alpha_composite(ov)
    return bg, cam


def draw_ep07_nodes(ov: Image.Image, cam: anim.MapCamera, statuses: dict, bursts: dict, capitals: set, t: float):
    for name, wpos in EP07_NODES.items():
        if name not in statuses:
            continue
        anim.draw_fortress_node(
            ov, cam, wpos, name, statuses[name], t,
            pulse_burst=bursts.get(name, 0.0),
            is_capital=(name in capitals),
            label_side=EP07_LABEL_SIDE.get(name, "auto"),
        )


def render_map_scene_frame(si: int, u: float, tau: float, seg_dur: float, t: float) -> Image.Image:
    s = anim.smoothstep(u)
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)

    if si == 3:
        # Map 1: Ordabasy -> Turkistan -> Ulytau strategic march.
        zoom = 1.04 + 0.08 * s
        cx = 510.0 - 30.0 * s
        cy = 955.0 - 35.0 * s
        bg, cam = render_ep07_map_canvas(zoom, cx, cy, t)

        p = anim.ease_out(min(1.0, u / 0.85))
        march_pts = [(555, 935), (445, 895), (360, 865), (355, 650), (360, 475)]
        anim.draw_animated_arrow(ov, cam, march_pts, p, t, col_main=(78, 224, 222), col_glow=(160, 250, 255), width=13)
        enemy_pts = [(940, 600), (765, 735), (645, 655)]
        anim.draw_animated_arrow(ov, cam, enemy_pts, p * 0.9, t, col_main=(232, 72, 62), col_glow=(255, 130, 110), width=11)

        dense_march = anim.eval_polyline(march_pts, 120)
        mx, my, ang = anim.point_along_path(dense_march, min(1.0, p))
        statuses = {"Ордабасы": "kazakh", "Түркістан": "kazakh", "Ұлытау": "kazakh", "Сарысу": "red", "Білеуті": "red"}
        draw_ep07_nodes(ov, cam, statuses, {}, {"Ордабасы", "Ұлытау"}, t)
        anim.draw_army_unit_marker(ov, cam, (mx, my), ang, "ӘБІЛҚАЙЫР • 60 000", col=(248, 202, 84), badge_bg=(14, 38, 48), t=t, label_offset=(115.0, 8.0))
        draw_badge_card(ov, "ОРДАБАСЫДАН ҰЛЫТАУҒА • 60 000 ҚОЛ", "ҮШ ЖҮЗДІҢ БІРІККЕН ЖАСАҒЫ", col=(78, 224, 222), tau=tau, y0=1432)

    elif si == 5:
        # Map 2: Step 1 Hidden Grouping + Recon Radar.
        zoom = 1.18 + 0.14 * s
        bg, cam = render_ep07_map_canvas(zoom, 465.0, 735.0, t)

        anim.draw_recon_radar_map(ov, cam, target_wpos=(645, 655), origin_wpos=(360, 415), t=t, tau=tau)
        p = anim.ease_out(min(1.0, u / 0.85))
        for ctrl in (
            [(360, 415), (315, 500), (285, 605)],
            [(360, 415), (415, 485), (455, 535)],
            [(360, 865), (335, 740), (305, 635)],
        ):
            anim.draw_animated_arrow(ov, cam, ctrl, p, t, col_main=(78, 224, 222), col_glow=(175, 252, 255), width=10, dashed=True)
        anim.draw_animated_arrow(ov, cam, [(765, 735), (645, 655)], min(1.0, u * 0.9), t, col_main=(232, 72, 62), col_glow=(255, 130, 110), width=11)

        statuses = {"Ұлытау": "kazakh", "Бұланты": "kazakh", "Білеуті": "red", "Сарысу": "red", "Қара-Сиыр": "capturing"}
        draw_ep07_nodes(ov, cam, statuses, {}, {"Ұлытау"}, t)
        draw_badge_card(ov, "ЖАСЫРЫН ТОПТАСУ • САЙ-САЛА", "ҚАРСЫЛАС БАЙҚАМАЙТЫН ТАУ ЖӘНЕ ӨЗЕН ШЕБІ", col=(78, 224, 222), tau=tau, y0=1432)

    elif si == 7:
        # Map 3: Step 2 Terrain Trap across Bulanty - Bileuti crossings.
        zoom = 1.36 + 0.10 * s
        bg, cam = render_ep07_map_canvas(zoom, 465.0, 740.0, t)

        p = anim.ease_out(min(1.0, u / 0.88))
        enemy_path = [(765, 735), (645, 655), (565, 610), (485, 575)]
        anim.draw_animated_arrow(ov, cam, enemy_path, p, t, col_main=(232, 72, 62), col_glow=(255, 128, 108), width=13, dashed=True)

        # Pulse warning halos at muddy river crossings.
        for wx, wy in ((575, 630), (360, 615)):
            sx, sy = cam.pt(wx, wy)
            r = 26 + 10 * abs(math.sin(t * 4.5))
            d.ellipse([sx - r, sy - r, sx + r, sy + r], outline=(248, 202, 84, 210), width=3)

        statuses = {"Бұланты": "kazakh", "Білеуті": "red", "Шұбар-Теңіз": "kazakh", "Қара-Сиыр": "capturing", "Сарысу": "red"}
        draw_ep07_nodes(ov, cam, statuses, {"Қара-Сиыр": 0.4 + 0.3 * math.sin(t * 4.0)}, set(), t)
        draw_badge_card(ov, "БҰЛАНТЫ – БІЛЕУТІ ӨТКЕЛДЕРІ", "АУЫР ЗЕҢБІРЕКТЕР ЖҰМСАҚ ТОПЫРАҚТА БАЯУЛАДЫ", col=(248, 202, 84), tau=tau, y0=1432)

    elif si == 9:
        # Map 4: Step 3 Lightning Vanguard Strike by Tailak & Sauryk.
        zoom = 1.44 + 0.08 * s
        bg, cam = render_ep07_map_canvas(zoom, 470.0, 735.0, t)

        p = anim.ease_out(min(1.0, u / 0.72))
        anim.draw_animated_arrow(ov, cam, [(645, 655), (560, 610), (485, 575)], 1.0, t, col_main=(226, 68, 58), col_glow=(255, 118, 96), width=11, dashed=True)
        w1 = [(305, 505), (355, 525), (398, 545)]
        w2 = [(375, 695), (420, 660), (455, 625)]
        anim.draw_animated_arrow(ov, cam, w1, p, t, col_main=(78, 224, 222), col_glow=(200, 252, 255), width=14)
        anim.draw_animated_arrow(ov, cam, w2, p, t, col_main=(248, 202, 84), col_glow=(255, 240, 175), width=14)

        statuses = {"Қара-Сиыр": "capturing", "Бұланты": "kazakh", "Білеуті": "red", "Ұлытау": "kazakh"}
        draw_ep07_nodes(ov, cam, statuses, {"Қара-Сиыр": 0.9 if u > 0.45 else 0.2}, set(), t)

        p1 = anim.point_along_path(anim.eval_polyline(w1, 80), min(1.0, p))
        p2 = anim.point_along_path(anim.eval_polyline(w2, 80), min(1.0, p))
        anim.draw_army_unit_marker(ov, cam, (p1[0], p1[1]), p1[2], "ТАЙЛАҚ", col=(78, 224, 222), badge_bg=(12, 38, 46), t=t, label_offset=(-74.0, -34.0))
        anim.draw_army_unit_marker(ov, cam, (p2[0], p2[1]), p2[2], "САУРЫҚ", col=(248, 202, 84), badge_bg=(32, 28, 12), t=t, label_offset=(-10.0, 38.0))
        draw_badge_card(ov, "ТАЙЛАҚ & САУРЫҚ АВАНГАРД СОҚҚЫСЫ", "ЗЕҢБІРЕКТІ ОБОЗДАН БӨЛІП ТАСТАУ", col=(78, 224, 222), tau=tau, y0=1432)

    elif si == 11:
        # Map 5: Step 4 Dual Flank Encirclement (Bogenbay & Kabanbay).
        zoom = 1.38 + 0.10 * s
        bg, cam = render_ep07_map_canvas(zoom, 465.0, 735.0, t)

        p = anim.ease_out(min(1.0, u / 0.80))
        wing_n = [(320, 455), (385, 480), (435, 520)]
        wing_s = [(420, 710), (505, 675), (535, 625)]
        anim.draw_animated_arrow(ov, cam, wing_n, p, t, col_main=(248, 202, 84), col_glow=(255, 244, 180), width=14)
        anim.draw_animated_arrow(ov, cam, wing_s, p, t, col_main=(78, 224, 222), col_glow=(190, 252, 255), width=14)

        # Closing golden pincer ring around Kara-Siyr.
        ksx, ksy = cam.pt(485, 575)
        r_ring = int(52 - 14 * min(1.0, p))
        d.arc([ksx - r_ring, ksy - r_ring, ksx + r_ring, ksy + r_ring], start=0, end=int(360 * min(1.0, p)), fill=(248, 202, 84, 238), width=5)

        statuses = {"Қара-Сиыр": "red" if u < 0.72 else "capturing", "Бұланты": "kazakh", "Білеуті": "kazakh", "Шұбар-Теңіз": "kazakh", "Ұлытау": "kazakh"}
        draw_ep07_nodes(ov, cam, statuses, {"Қара-Сиыр": 1.0 if u > 0.65 else 0.3}, {"Ұлытау"}, t)

        pn = anim.point_along_path(anim.eval_polyline(wing_n, 80), min(1.0, p))
        ps = anim.point_along_path(anim.eval_polyline(wing_s, 80), min(1.0, p))
        anim.draw_army_unit_marker(ov, cam, (pn[0], pn[1]), pn[2], "БӨГЕНБАЙ", col=(248, 202, 84), badge_bg=(34, 28, 12), t=t, label_offset=(-88.0, -32.0))
        anim.draw_army_unit_marker(ov, cam, (ps[0], ps[1]), ps[2], "ҚАБАНБАЙ", col=(78, 224, 222), badge_bg=(12, 38, 46), t=t, label_offset=(30.0, 44.0))
        draw_badge_card(ov, "ҚОС ҚАНАТТАН ТОЛЫҚ ҚОРШАУ", "БӨГЕНБАЙ + ҚАБАНБАЙ • ҚАРА-СИЫР ҚАЗАНЫ", col=(248, 202, 84), tau=tau, y0=1432)

    else:
        # Map 6 (si == 13): Kalmak Kyrylgan victory seal + Strategic bridge to Anyrakay (1730).
        zoom = 1.28 - 0.20 * s
        cx = 485.0 + 45.0 * s
        cy = 760.0 + 140.0 * s
        bg, cam = render_ep07_map_canvas(zoom, cx, cy, t)

        p = anim.ease_out(min(1.0, u / 0.85))
        any_pts = [(485, 575), (535, 760), (555, 935), (700, 915), (825, 885)]
        anim.draw_animated_arrow(ov, cam, any_pts, p, t, col_main=(248, 202, 84), col_glow=(78, 224, 222), width=14)

        statuses = {"Қара-Сиыр": "kazakh", "Бұланты": "kazakh", "Білеуті": "kazakh", "Ұлытау": "kazakh", "Ордабасы": "kazakh", "Аңырақай": "capturing"}
        draw_ep07_nodes(ov, cam, statuses, {"Қара-Сиыр": 1.0, "Аңырақай": max(0.0, (u - 0.55) * 2.0)}, {"Ұлытау", "Қара-Сиыр"}, t)
        draw_badge_card(ov, "«ҚАЛМАҚ ҚЫРЫЛҒАН» • 1728 ЖЫЛ", "БҰЛАНТЫ  ->  АҢЫРАҚАЙ ҰЛЫ ЖЕҢІСІ (1730)", col=(248, 202, 84), tau=tau, y0=1432)

    overlay_particles(ov, t, seed=300 + si, warm=True, count=22)
    bg.alpha_composite(ov)
    return bg.convert("RGB")


def apply_ep07_kinetic_overlay(plate_rgba: Image.Image, si: int, u: float, tau: float, seg_dur: float, t: float) -> Image.Image:
    base = rigid_cam_frame(plate_rgba, si, u, tau, shake=(si in (0, 8, 12)))

    if si == 0:
        ov = anim.apply_drifting_mist(base, t, col=(252, 222, 165), y_dest=860, speed=62.0)
        anim.draw_arrow_barrage(ov, t, count=30, go_right=True)
        overlay_particles(ov, t, seed=101, warm=True, count=24)
        draw_badge_card(ov, "ҰЛЫТАУ • БҮКІЛ ӘСКЕР ҚАЙДА ЖОҒАЛДЫ?", "ЗЕҢБІРЕКТІ ҚОЛДЫ ЖҰТҚАН БІР ШАЙҚАС", col=(248, 202, 84), tau=max(0.08, tau), y0=1432)
        return ov.convert("RGB")

    elif si == 1:
        ov = anim.apply_drifting_mist(base, t, col=(245, 225, 185), y_dest=840, speed=42.0)
        overlay_particles(ov, t, seed=102, warm=True, count=22)
        draw_badge_card(ov, "1728 ЖЫЛ • ҰЛЫТАУ БАҒЫТЫ", "ОТЫЗ КҮНДІК ЖОРЫҚ ПЕН АУЫР ЗЕҢБІРЕКТЕР", col=(78, 224, 222), tau=tau, y0=1432)
        return ov.convert("RGB")

    elif si == 2:
        ov = anim.apply_drifting_mist(base, t, col=(205, 195, 180), y_dest=850, speed=36.0)
        overlay_particles(ov, t, seed=103, warm=False, count=20)
        draw_mud_drag_card(ov, tau, seg_dur)
        return ov.convert("RGB")

    elif si == 4:
        ov = anim.apply_drifting_mist(base, t, col=(248, 220, 165), y_dest=855, speed=-44.0)
        overlay_particles(ov, t, seed=105, warm=True, count=24)
        anim.draw_kinetic_counter_card(ov, tau, seg_dur, 60000, " САРБАЗ", "ҰЛЫТАУ АҢҒАРЛАРЫНДА ЖАСЫРЫН ТОПТАСУ", y_center=1480)
        return ov.convert("RGB")

    elif si == 6:
        ov = anim.apply_drifting_mist(base, t, col=(200, 232, 240), y_dest=835, speed=58.0)
        overlay_particles(ov, t, seed=107, warm=False, count=22)
        draw_ep07_speed_card(ov, tau, seg_dur)
        return ov.convert("RGB")

    elif si == 8:
        ov = anim.apply_drifting_mist(base, t, col=(250, 212, 145), y_dest=845, speed=74.0)
        anim.draw_arrow_barrage(ov, t, count=36, go_right=True)
        overlay_particles(ov, t, seed=109, warm=True, count=28)
        draw_dual_hero_card(ov, tau)
        return ov.convert("RGB")

    elif si == 10:
        ov = anim.apply_drifting_mist(base, t, col=(220, 200, 170), y_dest=850, speed=-48.0)
        overlay_particles(ov, t, seed=111, warm=True, count=24)
        draw_encirclement_gauge_card(ov, tau, seg_dur)
        return ov.convert("RGB")

    elif si == 12:
        ov = anim.apply_drifting_mist(base, t, col=(252, 208, 138), y_dest=840, speed=78.0)
        anim.draw_arrow_barrage(ov, t, count=38, go_right=True)
        overlay_particles(ov, t, seed=113, warm=True, count=30)
        draw_badge_card(ov, "«ЖЕҢІЛМЕЙДІ» ДЕГЕН АҢЫЗ КҮЙРЕДІ", "ҚАРА-СИЫР ДАЛАСЫ • 1728 ЖЫЛ", col=(248, 202, 84), tau=tau, y0=1432)
        return ov.convert("RGB")

    elif si == 14:
        ov = anim.apply_drifting_mist(base, t, col=(255, 224, 162), y_dest=850, speed=40.0)
        d = ImageDraw.Draw(ov)
        pop = anim.ease_out(min(1.0, tau / 0.35))
        ox, oy = 540, 490
        for k in range(10):
            ang = math.radians(-155 + k * 31 + math.sin(t * 0.9 + k) * 4.0)
            a = int((26 + 12 * math.sin(t * 2.4 + k)) * pop)
            d.polygon(
                [(ox, oy), (ox + math.cos(ang - 0.09) * 1150, oy + math.sin(ang - 0.09) * 1150),
                 (ox + math.cos(ang + 0.09) * 1150, oy + math.sin(ang + 0.09) * 1150)],
                fill=(255, 222, 130, a),
            )
        overlay_particles(ov, t, seed=115, warm=True, count=26)
        draw_badge_card(ov, "ҰЛЫТАУ ДАЛАСЫ • 1510 ЖӘНЕ 1728", "ҚАСЫМ ХАННАН ӘБІЛҚАЙЫРҒА ДЕЙІНГІ ҚАЛҚАН", col=(248, 202, 84), tau=tau, y0=1432)
        return ov.convert("RGB")

    else:
        # Scene 15: Seamless loop transition -> Scene 01.
        ov = anim.apply_drifting_mist(base, t, col=(248, 214, 152), y_dest=840, speed=60.0)
        anim.draw_loop_surge_arrows(ov, tau, t)
        overlay_particles(ov, t, seed=116, warm=True, count=26)
        draw_badge_card(ov, "ҮШ ТАҒАН • БІРІККЕН ЖЕҢІС", "ТӘРТІП  •  ЖЕР СЫРЫ  •  ҚОЛБАСШЫЛЫҚ", col=(78, 224, 222), tau=tau, y0=1432)
        return ov.convert("RGB")


def draw_ep07_hud(frame_pil: Image.Image, si: int, tau: float):
    top_title, sub_callout, active_pillar = HUD_META_KZ["banners"][si]
    pillars = HUD_META_KZ["pillars"]

    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)

    alpha_in = min(1.0, max(0.0, tau / 0.22))
    bx_a = int(round(214 * alpha_in))
    tx_a = int(round(252 * alpha_in))
    gold = (248, 202, 84, tx_a)
    white = (250, 248, 240, tx_a)

    f_top = rmod.font(34)
    f_sub = rmod.font(27)
    f_pil = rmod.font(25)

    d.rounded_rectangle([60, 76, W - 60, 148], radius=22, fill=(10, 16, 24, bx_a), outline=(248, 202, 84, int(232 * alpha_in)), width=2)
    tw = d.textlength(top_title, font=f_top)
    d.text(((W - tw) / 2, 92), top_title, font=f_top, fill=gold)

    cw = d.textlength(sub_callout, font=f_sub)
    pw = min(W - 84, int(cw + 54))
    px0 = (W - pw) // 2
    d.rounded_rectangle([px0, 160, px0 + pw, 216], radius=16, fill=(14, 30, 38, int(206 * alpha_in)), outline=(78, 224, 222, int(210 * alpha_in)), width=2)
    d.text(((W - cw) / 2, 173), sub_callout, font=f_sub, fill=white)

    # Bottom 4-pillar tactical progress strip.
    bar_y0, bar_y1 = 1628, 1700
    d.rounded_rectangle([42, bar_y0, W - 42, bar_y1], radius=18, fill=(10, 16, 24, 212), outline=(145, 168, 184, 110), width=2)
    slot_w = (W - 104) / len(pillars)
    for k, label in enumerate(pillars):
        sx0 = int(52 + k * slot_w)
        sx1 = int(sx0 + slot_w - 8)
        is_active = (k == active_pillar)
        fill_p = (248, 202, 84, 236) if is_active else (24, 34, 46, 170)
        text_p = (16, 20, 26, 255) if is_active else (208, 216, 224, 210)
        d.rounded_rectangle([sx0, bar_y0 + 10, sx1, bar_y1 - 10], radius=12, fill=fill_p)
        lw = d.textlength(label, font=f_pil)
        d.text((sx0 + (sx1 - sx0 - lw) / 2, bar_y0 + 21), label, font=f_pil, fill=text_p)

    frame_pil.alpha_composite(overlay)


# ---------------------------------------------------------------------------
# Main Render Pipeline
# ---------------------------------------------------------------------------

def render_ep07_video(build_dir: Path, scenes_dir: Path, mix_wav: Path, timeline: list[dict], words_all: list[dict], dur: float, out_mp4: Path):
    stills = {}
    for si, fname in STILL_FILES.items():
        p = scenes_dir / fname
        if not p.exists():
            raise FileNotFoundError(f"Missing EP07 plate: {p}")
        stills[si] = Image.open(p).convert("RGBA").resize((W, H), Image.Resampling.LANCZOS)

    vig = rmod.vignette()[..., None]
    chunks = rmod.chunks_from(words_all, dur)
    chunk_idx = 0
    chunk_cache = {}
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

            if scene_idx in MAP_SCENES:
                frame_rgb = render_map_scene_frame(scene_idx, u, tau, sd, t)
            else:
                frame_rgb = apply_ep07_kinetic_overlay(stills[scene_idx], scene_idx, u, tau, sd, t)

            # Crisp 5-frame linear cross-dissolve at scene boundaries.
            arr = np.asarray(frame_rgb, dtype=np.float32)
            if scene_idx > 0 and tau < 0.16 and cut_from_rgb is not None:
                alpha = tau / 0.16
                arr = cut_from_rgb * (1.0 - alpha) + arr * alpha
            prev_frame_rgb = arr

            arr_v = ((arr.clip(0, 255).astype(np.uint16) * vig) >> 8).astype(np.uint8)
            frame_rgba = Image.fromarray(arr_v, "RGB").convert("RGBA")
            draw_ep07_hud(frame_rgba, scene_idx, tau)

            # Subtitle chunk overlay via render.py.
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
                    pop = t - ch["t0"]
                    if pop < 0.09:
                        sc_pop = 0.86 + 0.14 * (1.0 - (1.0 - pop / 0.09) ** 2)
                        ov = ov.resize((max(1, int(ov.width * sc_pop)), max(1, int(ov.height * sc_pop))), Image.Resampling.BILINEAR)
                    frame_rgba.paste(ov, (int(W / 2 - ov.width / 2), int(rmod.SUB_Y - ov.height / 2)), ov)

            proc.stdin.write(frame_rgba.convert("RGB").tobytes())
            if (fi + 1) % 300 == 0 or fi + 1 == total_frames:
                print(f"[EP07] rendered {fi + 1}/{total_frames} frames ({t:.1f}s/{dur:.1f}s)", flush=True)

        proc.stdin.close()
        stderr_out = proc.stderr.read().decode("utf-8", errors="replace") if proc.stderr else ""
        ret = proc.wait()
        if ret != 0:
            raise RuntimeError(f"FFmpeg video encode failed ({ret}): {stderr_out[-1000:]}")
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
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def main():
    print("[EP07] Verifying HUD bounds & Kazakh glyphs...")
    verify_hud_and_glyphs()

    build_dir, _, scenes_dir, out_dir = ensure_dirs()
    out_mp4 = out_dir / "EP07_Bulanty_1728_Shorts_KZ.mp4"

    print("[EP07] Synthesizing Kazakh narration (kk-KZ-DauletNeural)...")
    voice_mono, timeline, words_all, dur = synthesize_ep07(build_dir)
    print(f"[EP07] Narration timeline ready: {len(timeline)} scenes, total {dur:.2f}s, {len(words_all)} words.")

    print("[EP07] Mixing physical SFX + male a cappella (-14 LUFS)...")
    mix_wav = build_ep07_audio(build_dir, voice_mono, timeline, dur)

    print(f"[EP07] Rendering 1080x1920 @ 30fps video -> {out_mp4.name} ...")
    render_ep07_video(build_dir, scenes_dir, mix_wav, timeline, words_all, dur, out_mp4)
    size_mb = out_mp4.stat().st_size / (1024 * 1024)
    print(f"[EP07] DONE: {out_mp4} ({size_mb:.2f} MB, {dur:.2f}s)")


if __name__ == "__main__":
    main()
