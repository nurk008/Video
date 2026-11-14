#!/usr/bin/env python3
"""Episode 5 Builder (KZ ONLY): '1598 Great Southern Campaign — Tavekel Khan & Esim Sultan'
Maximum legitimate visual animation:
  - 6 camera-tracked 3D-hillshaded topographical tactical map sequences
  - 10 rigid multi-plane photoreal scenes with drifting mist, kinetic infographics,
    arrow barrages, stability fracture meters, pincer diagrams, & sunrise rays
  - Zero jelly warping, zero close-up faces, zero gore, zero musical instruments (-14 LUFS)
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
SCENES_DIR = ROOT / "scenes_ep05"
BUILD = PROD / "build_ep05"
OUT_DIR = ROOT / "output"
BIN_DIR = PROD / "build_ep02" / "_bin"
OUT_FILE = "EP05_Tavekel_1598_Shorts_KZ.mp4"

if str(PROD) not in sys.path:
    sys.path.insert(0, str(PROD))

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
if BIN_DIR.exists():
    os.environ["PATH"] = f"{BIN_DIR}:{os.environ.get('PATH', '')}"

import render as rmod      # noqa: E402
import sfx as smod         # noqa: E402
import anim_ep05 as anim   # noqa: E402

W, H, FPS = rmod.W, rmod.H, rmod.FPS  # 1080, 1920, 30
SR = smod.SR                          # 48000

VOICE_MAIN = "kk-KZ-DauletNeural"
VOICE_FALLBACK = "kk-KZ-AigulNeural"
VOICE_RATE = "-2%"
VOICE_PITCH = "-2Hz"

VOICE_FX = (
    "highpass=f=75,"
    "equalizer=f=150:t=q:w=1.1:g=2.5,"
    "equalizer=f=320:t=q:w=1.2:g=-1.5,"
    "equalizer=f=3200:t=q:w=1.3:g=2.0,"
    "equalizer=f=6800:t=q:w=1.5:g=-1.8,"
    "acompressor=threshold=-16dB:ratio=2.4:attack=12:release=140:makeup=1.5,"
    "alimiter=limit=-1.2dB:attack=4:release=50"
)

# 16 Scenes — numbers spelled in natural Kazakh words for crystal-clear DauletNeural diction
EP05_SCRIPT_KZ = [
    "Мың бес жүз тоқсан сегізінші жылы Тәуекел хан бүкіл Сырдария бойын түбегейлі өзгерткен жорық бастады.",
    "Оның туы астына бір жұдырықтай біріккен жүз мыңға жуық қазақ жауынгері жиналды.",
    "Ол кезде Түркістан, Сайрам мен Ташкент сияқты ірі шаһарлар Бұхара хандығының қолында болатын.",
    "Тәуекел бұл қалаларды ұзақ қоршаумен емес, далалық шапшаң маневр арқылы алуды көздеді.",
    "Бірінші тәсіл — берік плацдарм. Сол жағалаудағы Сығанақ пен Сауран азық-түлік және жасақ қоймасына айналды.",
    "Екінші тәсіл — дәл сәтті күту. Мың бес жүз тоқсан сегізінші жылы Бұхара хандығында билік дағдарысы ушықты.",
    "Тақ таласы шекара қорғанысын әлсіретті. Тәуекел ханның шолғыншылары осы сәтті қалт жібермеді.",
    "Үшінші тәсіл — домино соққысы. Қазақ қолы қарсылас есін жиғанша үздіксіз алға басты.",
    "Алдымен Түркістан мен Отырар алынып, Сайрам арқылы Ташкент шаһары да қазақ қолына өтті.",
    "Ташкент пен Самарқан арасындағы ашық далада Бұхараның көмекші қолы қапталдаудан ойсырай жеңілді.",
    "Төртінші тәсіл — қос қанат. Самарқан берілген соң, қол екі стратегиялық топқа бөлінді.",
    "Есім сұлтан жиырма мың сарбазбен Самарқанды бекітті, ал Тәуекел негізгі сексен мың қолмен Бұхараны қоршады.",
    "Бұхара түбіндегі ауыр шайқаста Тәуекел хан жараланып, Ташкентте дүниеден өтті. Билік інісі Есім ханға көшті.",
    "Бірақ біртұтас әскер ыдырамады. Ер Есім жасасқан бейбіт келісім Түркістан, Сайрам мен Ташкентті екі жүз жылға бекітті.",
    "Түркістан қаласы Қазақ хандығының саяси ордасына айналып, Орталық Азиядағы тепе-теңдікті нығайтты.",
    "Бұл жорық қазақ тарихындағы ең нәтижелі науқан болды. Ал мұндай жеңістің бастауы...",
]

HUD_META_KZ = {
    "pillars": ["1. ПЛАЦДАРМ", "2. ДӘЛ СӘТ", "3. ДОМИНО", "4. ҚОС ҚАНАТ"],
    "banners": [
        ("1598 • ОҢТҮСТІККЕ ҰЛЫ ЖОРЫҚ", "БІР ЖОРЫҚ ЕКІ ҒАСЫРҒА ШЕКАРА БЕКІТТІ", -1),
        ("БІРІККЕН ҚАЗАҚ ҚОСЫНЫ", "СЕРПІНДІ ДАЛА ЖОРЫҒЫНЫҢ АЛДЫНДА", -1),
        ("1598 ЖЫЛҒА ДЕЙІНГІ ЖАҒДАЙ", "ОҢТҮСТІК ШАҺАРЛАР БҰХАРА ҚОЛЫНДА", -1),
        ("ТӘУЕКЕЛДІҢ ЖАҢА ЕСЕБІ", "ҰЗАҚ ҚОРШАУ ЕМЕС — ШАПШАҢ ҚОЗҒАЛЫС", 0),
        ("1-ТӘСІЛ • БЕРІК ПЛАЦДАРМ", "СЫҒАНАҚ ПЕН САУРАН — НЕГІЗГІ ТІРЕК", 0),
        ("2-ТӘСІЛ • ДӘЛ СӘТТІ КҮТУ", "БҰХАРА ХАНДЫҒЫНДАҒЫ ІШКІ ДАҒДАРЫС", 1),
        ("2-ТӘСІЛ • БАРЛАУ ЖӘНЕ УАҚЫТ", "ІШКІ ТАҚ ТАЛАСЫ ШЕКАРАНЫ ӘЛСІРЕТТІ", 1),
        ("3-ТӘСІЛ • ДОМИНО СОҚҚЫСЫ", "ҚАРСЫЛАС ЕС ЖИҒАНША ҚАМАЛ АЛУ", 2),
        ("3-ТӘСІЛ • СЫР БОЙЫН БОСАТУ", "ТҮРКІСТАН, ОТЫРАР, САЙРАМ ЖӘНЕ ТАШКЕНТ", 2),
        ("ШЕШУШІ ДАЛА ШАЙҚАСЫ", "ТАШКЕНТ ПЕН САМАРҚАН АРАСЫНДАҒЫ ЖЕҢІС", 2),
        ("4-ТӘСІЛ • ҚОС ҚАНАТ", "САМАРҚАН БЕРІЛГЕН СОҢ ЕКІ БАҒЫТҚА БӨЛІНУ", 3),
        ("4-ТӘСІЛ • ҚЫСЫМ ЖӘНЕ ТЫЛ", "ЕСІМ — САМАРҚАНДА, ТӘУЕКЕЛ — БҰХАРА ТҮБІНДЕ", 3),
        ("АУЫР СЫН • ХАН АМАНАТЫ", "ЖАРАЛАНУ ЖӘНЕ БИЛІКТІҢ БЕРІК ЖАЛҒАСУЫ", -1),
        ("ТАРИХИ КЕЛІСІМ НӘТИЖЕСІ", "ТҮРКІСТАН, САЙРАМ, ТАШКЕНТ 200 ЖЫЛҒА БЕКІДІ", -1),
        ("ТҮРКІСТАН — ОРТАЛЫҚ ОРДА", "ХАНДЫҚТЫҢ САЯСИ ОШАҒЫ МЕН ТЕПЕ-ТЕҢДІК", -1),
        ("ТҰЙЫҚ ШЕҢБЕР", "ҚАЗАҚ ТАРИХЫНДАҒЫ ЕҢ НӘТИЖЕЛІ ЖОРЫҚ...", -1),
    ],
}

# Maps scenic backdrop slots (0-based): True = full animated 3D map, False = photoreal plate
MAP_SCENES = {0, 4, 6, 8, 10, 13}

# Camera parameters for photoreal scenes: (z0, z1, cx0, cy0, cx1, cy1, particle_mode, dissolve_in)
PHOTO_CAM = {
    1:  (1.00, 1.12, 0.50, 0.48, 0.52, 0.44, "dust",   True),
    2:  (1.03, 1.12, 0.50, 0.46, 0.50, 0.50, "embers", True),
    3:  (1.03, 1.14, 0.48, 0.48, 0.54, 0.46, "dust",   True),
    5:  (1.02, 1.12, 0.50, 0.48, 0.48, 0.46, "embers", True),
    7:  (1.02, 1.15, 0.50, 0.45, 0.50, 0.49, "dust",   True),
    9:  (1.00, 1.11, 0.50, 0.46, 0.50, 0.44, "sparks", True),
    11: (1.03, 1.12, 0.50, 0.45, 0.49, 0.49, "embers", True),
    12: (1.00, 1.09, 0.50, 0.48, 0.50, 0.45, "embers", True),
    14: (1.02, 1.10, 0.50, 0.48, 0.50, 0.44, "dust",   True),
    15: (1.00, 1.12, 0.50, 0.50, 0.50, 0.45, "sparks", True),
}

CITY_LABEL_SIDE = {
    "Сығанақ":   "above",
    "Сауран":    "left",
    "Түркістан": "left",
    "Отырар":    "left",
    "Сайрам":    "above",
    "Ташкент":   "right",
    "Самарқан":  "left",
    "Бұхара":    "right",
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


def synth_line_with_retry(text: str, mp3_path: Path, wav_path: Path):
    bounds_path = wav_path.with_suffix(".json")
    if wav_path.exists() and wav_path.stat().st_size > 4000:
        if bounds_path.exists():
            return json.loads(bounds_path.read_text(encoding="utf-8"))
        return []

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
            time.sleep(0.6 * (attempt + 1))
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


def build_voice_and_timeline():
    ldir = BUILD / "kz"
    ldir.mkdir(parents=True, exist_ok=True)
    voice_wav = ldir / "voice.wav"

    clips = []
    timeline = []
    words_all = []
    t_cursor = 0.0

    for si, text in enumerate(EP05_SCRIPT_KZ):
        mp3_p = ldir / f"line_{si:02d}.mp3"
        wav_p = ldir / f"line_{si:02d}.wav"
        bounds = synth_line_with_retry(text, mp3_p, wav_p)
        raw = read_wav_mono(wav_p)
        spoken = trim_silence(raw)
        speech_dur = len(spoken) / SR
        pause_after = 0.14 if si == len(EP05_SCRIPT_KZ) - 1 else 0.28
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


def river_splash(rng, dur: float):
    """Natural rushing water + thundering cavalry hooves across Syr Darya shallow ford."""
    water = smod.bp(smod.brown(rng, dur) * 0.7 + smod.white(rng, dur) * 0.3, 280, 3200)
    mod = 0.75 + 0.25 * np.sin(2.0 * np.pi * 1.8 * smod.tt(dur))
    return smod.norm(water * mod, 0.65)


def run_ep05_sfx(voice_wav: Path, timeline: list, dur: float):
    ldir = BUILD / "kz"
    mix_raw = ldir / "mix_raw.wav"
    mix_wav = ldir / "mix.wav"
    if mix_wav.exists() and mix_wav.stat().st_size > 1_000_000:
        return mix_wav

    v = smod.bp(read_wav_mono(voice_wav).astype(np.float64), 80, 11500)
    N = int(round(dur * SR))
    amb = np.zeros((N, 2), dtype=np.float64)
    rng = np.random.default_rng(1598)

    # Warm Silk Road open-steppe breeze bed (zero musical instruments)
    bed = smod.wind(rng, dur, howl=0.18) * 0.30
    amb += smod.st(bed, 0.0)

    # Pure human male A cappella choir pads across 4 campaign acts
    A2, D3, E3, F3, G3, A3, C4, D4, E4 = 110.00, 146.83, 164.81, 174.61, 196.00, 220.00, 261.63, 293.66, 329.63
    t_s = lambda si: timeline[si]["t0"]

    # Act I — Southern Mobilization & Springboard (01-05)
    t0_a, t1_a = t_s(0), timeline[4]["t1"]
    smod.add(amb, smod.reverb(smod.vocal_pad(rng, t1_a - t0_a, (D3, F3, A3, D4), "o", 4), wet=0.45, seed=101) * 0.38, t0_a)

    # Act II — Timing Crisis & Recon Radar (06-07)
    t0_b, t1_b = t_s(5), timeline[6]["t1"]
    smod.add(amb, smod.reverb(smod.vocal_pad(rng, t1_b - t0_b, (A2, D3, E3, A3), "u", 3), wet=0.44, seed=102) * 0.36, t0_b)

    # Act III — Domino Blitz & Twin-Wing Siege (08-12)
    t0_c, t1_c = t_s(7), timeline[11]["t1"]
    smod.add(amb, smod.reverb(smod.vocal_pad(rng, t1_c - t0_c, (D3, F3, G3, C4), "a", 4), wet=0.46, seed=103) * 0.42, t0_c)

    # Act IV — Esim Khan Succession & 200-Year Peace (13-16)
    t0_d = t_s(12)
    smod.add(amb, smod.reverb(smod.vocal_pad(rng, dur - t0_d, (D3, F3, A3, D4, E4), "a", 5), wet=0.48, seed=104) * 0.44, t0_d)

    # Bespoke physical SFX matched to each scene
    for si, seg in enumerate(timeline):
        t0 = seg["t0"]
        sd = seg["t1"] - seg["t0"]
        if si == 0:
            smod.add(amb, smod.st(smod.eagle(rng), 0.25) * 0.34, t0 + 0.5)
            smod.add(amb, smod.st(smod.herd_far(rng, sd), -0.15) * 0.36, t0)
        elif si == 1:
            smod.add(amb, smod.st(smod.whoosh(rng, 0.8), 0.2) * 0.44, t0 + 0.3)
            smod.add(amb, smod.st(smod.whoosh(rng, 0.7), -0.2) * 0.40, t0 + 1.2)
            smod.add(amb, smod.st(smod.herd(rng, sd), 0.0) * 0.44, t0)
        elif si == 2:
            smod.add(amb, smod.reverb(smod.clasp(rng), wet=0.25, seed=303) * 0.42, t0 + 0.4)
            smod.add(amb, smod.st(smod.wind(rng, sd, howl=0.28), 0.1) * 0.30, t0)
        elif si == 3:
            smod.add(amb, smod.st(river_splash(rng, sd), 0.1) * 0.38, t0)
            smod.add(amb, smod.st(smod.gallop(rng, sd, horses=10, rate=2.2), -0.1) * 0.44, t0)
        elif si == 4:
            smod.add(amb, smod.reverb(smod.jingle(rng, min(2.4, sd), density=26), wet=0.22, seed=305) * 0.30, t0 + 0.4)
            smod.add(amb, smod.st(smod.thud(rng), 0.0) * 0.42, t0 + 0.1)
        elif si == 5:
            smod.add(amb, smod.st(smod.fire(rng, sd), 0.15) * 0.26, t0)
            smod.add(amb, smod.reverb(smod.thud(rng), wet=0.30, seed=306) * 0.48, t0 + 1.6)
        elif si == 6:
            smod.add(amb, smod.st(smod.wind(rng, sd, howl=0.22), -0.15) * 0.30, t0)
            smod.add(amb, smod.reverb(smod.clasp(rng), wet=0.25, seed=307) * 0.38, t0 + 0.6)
        elif si == 7:
            smod.add(amb, smod.st(smod.herd(rng, sd), 0.0) * 0.50, t0)
            smod.add(amb, smod.st(smod.whoosh(rng, 0.75), 0.2) * 0.45, t0 + 0.8)
        elif si == 8:
            # 4 rapid domino pulses synchronized with city flips
            for step in (0.12, 0.34, 0.56, 0.78):
                smod.add(amb, smod.reverb(smod.thud(rng), wet=0.22, seed=309 + int(step * 100)) * 0.44, t0 + sd * step)
        elif si == 9:
            smod.add(amb, smod.reverb(smod.sword_clash(rng), wet=0.28, seed=310) * 0.50, t0 + 0.45)
            smod.add(amb, smod.st(smod.whoosh(rng, 0.8), -0.2) * 0.46, t0 + 0.15)
            smod.add(amb, smod.st(smod.herd(rng, sd), 0.0) * 0.48, t0)
        elif si == 10:
            smod.add(amb, smod.reverb(smod.impact_boom(rng, 2.2), wet=0.34, seed=311) * 0.56, t0 + 0.1)
            smod.add(amb, smod.st(smod.herd_far(rng, sd), 0.15) * 0.38, t0)
        elif si == 11:
            smod.add(amb, smod.reverb(smod.sword_draw(rng, min(2.8, sd)), wet=0.26, seed=312) * 0.46, t0 + 0.4)
            smod.add(amb, smod.st(smod.thunder(rng, min(3.5, sd)), -0.1) * 0.42, t0)
        elif si == 12:
            smod.add(amb, smod.st(smod.fire(rng, sd), 0.0) * 0.30, t0)
            smod.add(amb, smod.reverb(smod.thud(rng), wet=0.35, seed=313) * 0.42, t0 + 1.8)
        elif si == 13:
            smod.add(amb, smod.reverb(smod.impact_boom(rng, 2.5), wet=0.36, seed=314) * 0.54, t0 + 0.25)
            smod.add(amb, smod.st(smod.eagle(rng), -0.2) * 0.36, t0 + max(0.8, sd - 2.4))
        elif si == 14:
            smod.add(amb, smod.st(smod.eagle(rng), 0.2) * 0.38, t0 + 0.4)
            smod.add(amb, smod.st(smod.herd_far(rng, sd), 0.0) * 0.34, t0)
        elif si == 15:
            smod.add(amb, smod.st(smod.wind(rng, sd, howl=0.26), 0.0) * 0.32, t0)
            smod.add(amb, smod.st(smod.riser(rng, min(2.4, sd * 0.65)), 0.0) * 0.42, max(t0, dur - min(2.4, sd * 0.65)))

    rms = smod.frame_rms(v, win=0.05)
    rms_st = np.interp(np.arange(N), np.arange(len(rms)) * int(SR * 0.05), rms)
    duck = 1.0 - 0.58 * np.clip(rms_st / 0.085, 0.0, 1.0)
    amb *= duck[:, None]

    out = amb * 0.90 + smod.st(v, 0.0) * 1.00
    out = smod.softclip(out, 0.90)
    smod.write(str(mix_raw), out)
    smod.loudnorm(str(mix_raw), str(mix_wav), I=-14, TP=-1.5, LRA=11)
    return mix_wav


PARTICLES_CACHE = {}


def make_particle_LUT(mode: str, n_pts: int = 85, seed: int = 1598):
    key = (mode, n_pts, seed)
    if key in PARTICLES_CACHE:
        return PARTICLES_CACHE[key]
    rng = np.random.default_rng(seed)
    xs = rng.uniform(0.0, 1.0, n_pts).astype(np.float32)
    ys = rng.uniform(0.0, 1.0, n_pts).astype(np.float32)
    phase = rng.uniform(0.0, 2.0 * math.pi, n_pts).astype(np.float32)
    if mode == "sparks":
        vx = rng.uniform(-0.07, 0.07, n_pts).astype(np.float32)
        vy = -rng.uniform(0.09, 0.24, n_pts).astype(np.float32)
        rad = rng.uniform(1.8, 3.8, n_pts).astype(np.float32)
        alpha = rng.uniform(0.55, 0.98, n_pts).astype(np.float32)
        col = np.array([255, 198, 92], dtype=np.float32)
    elif mode == "embers":
        vx = rng.uniform(-0.03, 0.04, n_pts).astype(np.float32)
        vy = -rng.uniform(0.04, 0.14, n_pts).astype(np.float32)
        rad = rng.uniform(1.8, 4.0, n_pts).astype(np.float32)
        alpha = rng.uniform(0.45, 0.90, n_pts).astype(np.float32)
        col = np.array([255, 152, 68], dtype=np.float32)
    else:  # dust / golden steppe wind motes
        vx = rng.uniform(0.03, 0.10, n_pts).astype(np.float32)
        vy = rng.uniform(-0.02, 0.03, n_pts).astype(np.float32)
        rad = rng.uniform(1.5, 3.6, n_pts).astype(np.float32)
        alpha = rng.uniform(0.28, 0.68, n_pts).astype(np.float32)
        col = np.array([250, 224, 168], dtype=np.float32)
    PARTICLES_CACHE[key] = (xs, ys, vx, vy, phase, rad, alpha, col)
    return PARTICLES_CACHE[key]


def overlay_particles(arr: np.ndarray, mode: str, t_global: float, si: int):
    xs, ys, vx, vy, phase, rad, alpha, color = make_particle_LUT(mode, 92, 1500 + si * 19)
    pxs = ((xs + vx * t_global + 0.015 * np.sin(1.7 * t_global + phase)) % 1.0) * W
    pys = ((ys + vy * t_global) % 1.0) * H
    twinkle = 0.58 + 0.42 * np.sin(2.8 * t_global + phase)
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


def rigid_cam_frame(im_src: Image.Image, si: int, u: float, tau: float) -> Image.Image:
    z0, z1, cx0, cy0, cx1, cy1, _, _ = PHOTO_CAM[si]
    e = u * u * (3.0 - 2.0 * u)
    z = z0 + (z1 - z0) * e
    cx = cx0 + (cx1 - cx0) * e
    cy = cy0 + (cy1 - cy0) * e

    # Subtle physical camera micro-rumble during heavy cavalry clash/charges
    dx_px, dy_px = 0.0, 0.0
    if si == 9 and 0.30 <= tau <= 0.80:
        decay = math.exp(-7.0 * (tau - 0.30))
        dx_px = 9.0 * decay * math.sin(tau * 58.0)
        dy_px = 7.0 * decay * math.cos(tau * 47.0)
    elif si in (1, 7):
        dx_px = 3.0 * math.sin(tau * 22.0)
        dy_px = 2.0 * math.cos(tau * 17.0)

    vw = W / z
    vh = H / z
    x0 = max(0.0, min(W - vw, cx * W - vw * 0.5 + dx_px / z))
    y0 = max(0.0, min(H - vh, cy * H - vh * 0.5 + dy_px / z))
    return im_src.transform((W, H), Image.Transform.EXTENT, (x0, y0, x0 + vw, y0 + vh), Image.Resampling.BICUBIC)


def draw_cities_subset(ov: Image.Image, cam: anim.MapCamera, statuses: dict, bursts: dict, capitals: set, t: float):
    for name, wpos in anim.MAP_CITIES.items():
        if name not in statuses:
            continue
        anim.draw_fortress_node(
            ov, cam, wpos, name, statuses[name], t,
            pulse_burst=bursts.get(name, 0.0),
            is_capital=(name in capitals),
            label_side=CITY_LABEL_SIDE.get(name, "auto"),
        )


def render_map_scene_frame(si: int, u: float, tau: float, seg_dur: float, t: float) -> Image.Image:
    e = anim.smoothstep(u)
    MC = anim.MAP_CITIES

    if si == 0:
        # Map 1 (HOOK): Smooth regional campaign dive + south spearheads
        bg, cam = anim.render_map_canvas(1.04 + 0.14 * e, 470 + 20 * e, 755 + 35 * e, t)
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        prog1 = anim.ease_out(min(1.0, u / 0.65))
        prog2 = anim.ease_out(max(0.0, min(1.0, (u - 0.20) / 0.75)))
        route = [MC["Сығанақ"], MC["Сауран"], MC["Түркістан"], MC["Отырар"], MC["Ташкент"], MC["Самарқан"]]
        anim.draw_animated_arrow(ov, cam, route, prog1, t, width=13)
        route2 = [MC["Самарқан"], (350, 1105), MC["Бұхара"]]
        anim.draw_animated_arrow(ov, cam, route2, prog2, t, col_main=(78, 224, 222), col_glow=(248, 202, 84), width=11)

        dense = anim.eval_polyline(route, 100)
        ux, uy, ang = anim.point_along_path(dense, min(0.96, prog1 * 0.94))
        anim.draw_army_unit_marker(ov, cam, (ux, uy), ang, "100 000 ҚОЛ", t=t, label_offset=(75, -35))

        statuses = {
            "Сығанақ": "kazakh", "Сауран": "kazakh",
            "Түркістан": "red", "Отырар": "red", "Сайрам": "red",
            "Ташкент": "red", "Самарқан": "red", "Бұхара": "red",
        }
        draw_cities_subset(ov, cam, statuses, {}, {"Сығанақ", "Түркістан", "Ташкент", "Бұхара"}, t)
        bg.alpha_composite(ov)
        return bg.convert("RGB")

    elif si == 4:
        # Map 2 (1. ПЛАЦДАРМ): Northern Logistics Sygnak -> Sauran Springboard
        bg, cam = anim.render_map_canvas(1.48 + 0.12 * e, 415 + 25 * e, 515 + 20 * e, t)
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        sup_prog = anim.ease_out(min(1.0, u / 0.55))
        adv_prog = anim.ease_out(max(0.0, min(1.0, (u - 0.18) / 0.72)))
        # Supply chain Sygnak -> Sauran
        anim.draw_animated_arrow(ov, cam, [MC["Сығанақ"], (285, 395), MC["Сауран"]], sup_prog, t, col_main=(248, 202, 84), col_glow=(250, 210, 115), width=9, dashed=True)
        # Vanguard spearheads staging toward Turkestan
        anim.draw_animated_arrow(ov, cam, [MC["Сауран"], (420, 480), (455, 515)], adv_prog, t, width=13)
        # Twin battalion markers cleanly offset away from Sygnak/Sauran labels
        anim.draw_army_unit_marker(ov, cam, (305, 378), 0.58, "ҚОРЫҚ ҚОЙМА", t=t, label_offset=(92, -32))
        anim.draw_army_unit_marker(ov, cam, (410, 485), 0.62, "АВАНГАРД", col=(78, 224, 222), t=t, label_offset=(84, -18))

        statuses = {
            "Сығанақ": "kazakh", "Сауран": "kazakh",
            "Түркістан": "red", "Отырар": "red", "Сайрам": "red", "Ташкент": "red",
        }
        draw_cities_subset(ov, cam, statuses, {}, {"Сығанақ", "Сауран", "Түркістан"}, t)
        bg.alpha_composite(ov)
        return bg.convert("RGB")

    elif si == 6:
        # Map 3 (2. ДӘЛ СӘТ): Strategic Timing Recon Radar over Bukhara Crisis
        bg, cam = anim.render_map_canvas(1.24, 465 - 25 * e, 855 + 35 * e, t)
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        anim.draw_recon_radar_map(ov, cam, target_wpos=MC["Бұхара"], origin_wpos=MC["Сауран"], t=t, tau=tau)

        scout_prog = anim.ease_out(min(1.0, u / 0.78))
        anim.draw_animated_arrow(ov, cam, [MC["Сауран"], (435, 650), MC["Ташкент"]], scout_prog, t, col_glow=(78, 224, 222), width=7, dashed=True)
        anim.draw_animated_arrow(ov, cam, [MC["Ташкент"], (530, 920), MC["Самарқан"], MC["Бұхара"]], scout_prog, t, col_glow=(250, 210, 110), width=7, dashed=True)

        statuses = {
            "Сауран": "kazakh",
            "Түркістан": "red", "Отырар": "red", "Сайрам": "red",
            "Ташкент": "red", "Самарқан": "red", "Бұхара": "red",
        }
        draw_cities_subset(ov, cam, statuses, {}, {"Бұхара", "Самарқан", "Ташкент"}, t)
        bg.alpha_composite(ov)
        return bg.convert("RGB")

    elif si == 8:
        # Map 4 (3. ДОМИНО): Sequential 4-City Capture (Turkestan -> Otyrar -> Sairam -> Tashkent)
        bg, cam = anim.render_map_canvas(1.36, 505 + 30 * e, 635 + 45 * e, t)
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        sweep_pts = [MC["Сауран"], MC["Түркістан"], MC["Отырар"], MC["Сайрам"], MC["Ташкент"]]
        prog = anim.ease_out(min(1.0, u / 0.88))
        anim.draw_animated_arrow(ov, cam, sweep_pts, prog, t, width=14)

        dense = anim.eval_polyline(sweep_pts, 120)
        ux, uy, ang = anim.point_along_path(dense, min(0.96, prog * 0.96))
        anim.draw_army_unit_marker(ov, cam, (ux, uy), ang, "ДОМИНО СОҚҚЫСЫ", t=t, label_offset=(82, -26))

        thresholds = [("Түркістан", 0.14), ("Отырар", 0.36), ("Сайрам", 0.58), ("Ташкент", 0.78)]
        statuses = {"Сығанақ": "kazakh", "Сауран": "kazakh", "Самарқан": "red"}
        bursts = {}
        flipped = 0
        for cname, thr in thresholds:
            if u < thr - 0.05:
                statuses[cname] = "red"
            elif u < thr + 0.10:
                statuses[cname] = "capturing"
                bursts[cname] = (u - (thr - 0.05)) / 0.15
                flipped += 1
            else:
                statuses[cname] = "kazakh"
                flipped += 1

        draw_cities_subset(ov, cam, statuses, bursts, {"Түркістан", "Ташкент"}, t)
        anim.draw_domino_cities_counter(ov, flipped, 4, y_center=1215)
        bg.alpha_composite(ov)
        return bg.convert("RGB")

    elif si == 10:
        # Map 5 (4. ҚОС ҚАНАТ): Twin-Wing Split from Samarkand (Esim 20k hold + Tavekel 80k Bukhara)
        bg, cam = anim.render_map_canvas(1.36 + 0.08 * e, 435 - 30 * e, 965 + 45 * e, t)
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        p_sam = anim.ease_out(min(1.0, u / 0.45))
        p_buk = anim.ease_out(max(0.0, min(1.0, (u - 0.18) / 0.75)))

        # Tashkent -> Samarkand liberated path
        anim.draw_animated_arrow(ov, cam, [MC["Ташкент"], (550, 910), MC["Самарқан"]], p_sam, t, col_main=(78, 224, 222), col_glow=(248, 202, 84), width=12)
        # Main golden 80k wing surging west along Zeravshan -> Bukhara
        buk_route = [MC["Самарқан"], (350, 1085), (275, 1135), MC["Бұхара"]]
        anim.draw_animated_arrow(ov, cam, buk_route, p_buk, t, col_main=(248, 202, 84), col_glow=(255, 226, 130), width=15)

        dense_b = anim.eval_polyline(buk_route, 90)
        bx, by, bang = anim.point_along_path(dense_b, min(0.92, p_buk * 0.90))
        anim.draw_army_unit_marker(ov, cam, MC["Самарқан"], 1.5, "ЕСІМ • 20 000", col=(78, 224, 222), t=t, label_offset=(82, 18))
        anim.draw_army_unit_marker(ov, cam, (bx, by), bang, "ТӘУЕКЕЛ • 80 000", col=(248, 202, 84), t=t, label_offset=(18, -56))

        statuses = {
            "Ташкент": "kazakh",
            "Самарқан": "capturing" if u < 0.35 else "kazakh",
            "Бұхара": "red",
        }
        bursts = {"Самарқан": u / 0.35} if u < 0.35 else {}
        draw_cities_subset(ov, cam, statuses, bursts, {"Ташкент", "Самарқан", "Бұхара"}, t)
        bg.alpha_composite(ov)
        return bg.convert("RGB")

    else:
        # Map 6 (si == 13, PAYOFF): 200-Year Peace Treaty Border Map (Turkestan, Sairam, Tashkent Fixed)
        bg, cam = anim.render_map_canvas(1.16 - 0.04 * e, 505, 615, t)
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))

        statuses = {
            "Сығанақ": "kazakh", "Сауран": "kazakh", "Түркістан": "kazakh",
            "Отырар": "kazakh", "Сайрам": "kazakh", "Ташкент": "kazakh",
            "Самарқан": "red", "Бұхара": "red",
        }
        anim.draw_200yr_peace_overlay(ov, cam, tau, seg_dur, t, part="shield")
        draw_cities_subset(ov, cam, statuses, {}, {"Түркістан", "Ташкент", "Самарқан", "Бұхара"}, t)
        anim.draw_200yr_peace_overlay(ov, cam, tau, seg_dur, t, part="card")
        bg.alpha_composite(ov)
        return bg.convert("RGB")


def apply_photoreal_kinetic_overlay(frame_rgb: Image.Image, si: int, tau: float, seg_dur: float, t: float) -> Image.Image:
    """Apply bespoke drifting volumetric mist + crisp animated kinetic graphics per photoreal scene."""
    if si == 1:
        # 100 000 Kazakh Host + Arrow Barrage + Counter
        ov = anim.apply_drifting_mist(frame_rgb, t, col=(245, 208, 138), y_dest=860, speed=52.0)
        anim.draw_arrow_barrage(ov, t, count=36, go_right=True)
        anim.draw_kinetic_counter_card(ov, tau, seg_dur, 100000, "САРБАЗ", "БІРІККЕН ҚАЗАҚ ҚОСЫНЫ • 1598", y_center=1155)
        return ov.convert("RGB")
    elif si == 2:
        # Bukhara Fortress Defense Barrier over Citadel
        ov = anim.apply_drifting_mist(frame_rgb, t, col=(215, 165, 130), y_dest=820, speed=-38.0)
        anim.draw_fortress_shield_card(ov, tau, seg_dur, t, y_center=1155)
        return ov.convert("RGB")
    elif si == 3:
        # Speed Comparison x3 vs x1 + water rush streaks
        ov = anim.apply_drifting_mist(frame_rgb, t, col=(175, 224, 228), y_dest=850, speed=60.0)
        anim.draw_arrow_barrage(ov, t, count=22, go_right=True)
        anim.draw_speed_comparison_card(ov, tau, seg_dur, y_center=1150)
        return ov.convert("RGB")
    elif si == 5:
        # 1598 Bukhara Dynasty Crisis Meter dropping 92% -> 34%
        ov = anim.apply_drifting_mist(frame_rgb, t, col=(235, 175, 120), y_dest=860, speed=32.0)
        anim.draw_empire_fracture_card(ov, tau, seg_dur, t, y_center=1155)
        return ov.convert("RGB")
    elif si == 7:
        # Unstoppable Domino Tempo Wave + Cavalry Barrage
        ov = anim.apply_drifting_mist(frame_rgb, t, col=(246, 208, 146), y_dest=830, speed=66.0)
        anim.draw_arrow_barrage(ov, t, count=42, go_right=False)
        anim.draw_tempo_wave_card(ov, tau, seg_dur, t, y_center=1155)
        return ov.convert("RGB")
    elif si == 9:
        # Open-Plain Pincer Battle Envelopment Inset
        ov = anim.apply_drifting_mist(frame_rgb, t, col=(240, 190, 125), y_dest=880, speed=-48.0)
        anim.draw_arrow_barrage(ov, t, count=28, go_right=True)
        anim.draw_battle_pincer_inset(ov, tau, seg_dur, t)
        return ov.convert("RGB")
    elif si == 11:
        # Twin-Wing Siege Ring + Dual Commander Crest Cards
        ov = anim.apply_drifting_mist(frame_rgb, t, col=(160, 212, 225), y_dest=840, speed=40.0)
        anim.draw_siege_ring_gauge(ov, tau, seg_dur, t, center=(540, 620))
        anim.draw_dual_crest_card(ov, tau, y_center=1175)
        return ov.convert("RGB")
    elif si == 12:
        # Solemn Succession Continuity Card (Tavekel -> Esim Khan)
        ov = anim.apply_drifting_mist(frame_rgb, t, col=(220, 172, 128), y_dest=890, speed=30.0)
        anim.draw_succession_banner(ov, tau, seg_dur, t, y_center=1150)
        return ov.convert("RGB")
    elif si == 14:
        # Turkestan Dawn Rays + Crest
        ov = anim.apply_drifting_mist(frame_rgb, t, col=(250, 222, 165), y_dest=860, speed=42.0)
        anim.draw_dawn_rays_crest(ov, tau, t, origin=(540, 560))
        return ov.convert("RGB")
    else:
        # si == 15: Loop Surge Chevrons
        ov = anim.apply_drifting_mist(frame_rgb, t, col=(248, 214, 150), y_dest=840, speed=58.0)
        anim.draw_loop_surge_arrows(ov, tau, t)
        return ov.convert("RGB")


def draw_ep05_hud(frame_pil: Image.Image, si: int, tau: float):
    """Crisp Silk-Road Gold & Turquoise Glass HUD + 4-Tactic Tracker Bar."""
    top_title, sub_callout, active_pillar = HUD_META_KZ["banners"][si]
    pillars = HUD_META_KZ["pillars"]

    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)

    alpha_in = min(1.0, max(0.0, tau / 0.35))
    bx_a = int(round(208 * alpha_in))
    tx_a = int(round(250 * alpha_in))
    gold = (248, 202, 84, tx_a)
    white = (250, 248, 240, tx_a)

    f_top = rmod.font(34)
    f_sub = rmod.font(28)
    f_pil = rmod.font(25)

    # Top Glass Banner (y = 76..148)
    d.rounded_rectangle([60, 76, W - 60, 148], radius=22, fill=(10, 16, 24, bx_a), outline=(248, 202, 84, int(225 * alpha_in)), width=2)
    tw = d.textlength(top_title, font=f_top)
    d.text(((W - tw) / 2, 92), top_title, font=f_top, fill=gold)

    # Sub-callout Turquoise Pill (y = 160..216)
    cw = d.textlength(sub_callout, font=f_sub)
    pw = min(W - 84, int(cw + 54))
    px0 = (W - pw) // 2
    d.rounded_rectangle([px0, 160, px0 + pw, 216], radius=16, fill=(14, 30, 38, int(202 * alpha_in)), outline=(78, 224, 222, int(205 * alpha_in)), width=2)
    d.text(((W - cw) / 2, 172), sub_callout, font=f_sub, fill=white)

    # Bottom 4-Tactic Tracker Bar (y = 1628..1700)
    bar_y0, bar_y1 = 1628, 1700
    d.rounded_rectangle([54, bar_y0, W - 54, bar_y1], radius=20, fill=(10, 16, 24, 204), outline=(78, 224, 222, 138), width=2)

    slot_w = (W - 128) // 4
    for idx, label in enumerate(pillars):
        sx0 = 64 + idx * slot_w + 4
        sx1 = sx0 + slot_w - 8
        is_active = (idx == active_pillar)
        fill_c = (248, 202, 84, 236) if is_active else (18, 28, 38, 182)
        out_c = (255, 238, 165, 255) if is_active else (88, 135, 148, 155)
        txt_c = (12, 14, 20, 255) if is_active else (216, 228, 236, 228)
        d.rounded_rectangle([sx0, bar_y0 + 10, sx1, bar_y1 - 10], radius=12, fill=fill_c, outline=out_c, width=2)
        lw = d.textlength(label, font=f_pil)
        d.text((sx0 + (sx1 - sx0 - lw) / 2, bar_y0 + 21), label, font=f_pil, fill=txt_c)

    frame_rgba = frame_pil.convert("RGBA")
    frame_rgba.alpha_composite(overlay)
    return frame_rgba.convert("RGB")


def render_raw_scene_frame(si: int, u: float, tau: float, seg_dur: float, t: float, stills: dict) -> Image.Image:
    if si in MAP_SCENES:
        return render_map_scene_frame(si, u, tau, seg_dur, t)
    base = rigid_cam_frame(stills[si], si, u, tau)
    return apply_photoreal_kinetic_overlay(base, si, tau, seg_dur, t)


def check_hud_widths():
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    f_top, f_sub, f_pil = rmod.font(34), rmod.font(28), rmod.font(25)
    max_t = max(d.textlength(b[0], font=f_top) for b in HUD_META_KZ["banners"])
    max_s = max(d.textlength(b[1], font=f_sub) for b in HUD_META_KZ["banners"])
    max_p = max(d.textlength(p, font=f_pil) for p in HUD_META_KZ["pillars"])
    print(f"[HUD CHECK] max_top={max_t:.0f}px (lim 920), max_sub={max_s:.0f}px (lim 960), max_pil={max_p:.0f}px (lim 220)")
    assert max_t <= 920, f"Top banner too wide: {max_t}"
    assert max_s <= 960, f"Sub callout too wide: {max_s}"
    assert max_p <= 220, f"Pillar label too wide: {max_p}"


def build_ep05(voice_only: bool = False):
    print(f"\n=== BUILDING EP05 [KZ ONLY] (voice_only={voice_only}) ===", flush=True)
    check_hud_widths()
    t_start = time.time()
    voice_wav, timeline, words_all, dur = build_voice_and_timeline()
    mix_wav = run_ep05_sfx(voice_wav, timeline, dur)

    ldir = BUILD / "kz"
    (ldir / "timeline.json").write_text(json.dumps(timeline, ensure_ascii=False, indent=2), encoding="utf-8")
    (ldir / "words.json").write_text(json.dumps(words_all, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  Voice + Mix ready: {dur:.2f}s (16 scenes, {len(words_all)} words)", flush=True)
    if voice_only:
        return None

    stills = {}
    for si in range(16):
        if si not in MAP_SCENES:
            stills[si] = Image.open(SCENES_DIR / f"scene_{si + 1:02d}.jpg").convert("RGB")

    # Warm the 2x 3D topographical relief cache once before frame loop
    anim.build_hi_relief_map()

    chunks = rmod.chunks_from(words_all, dur)
    vign = rmod.vignette()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_mp4 = OUT_DIR / OUT_FILE
    tmp_vid = ldir / "video_silent.mp4"

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

        frame_pil = render_raw_scene_frame(si, u, tau, seg_dur, t, stills)

        if si > 0:
            frames_into = int(round(tau * FPS))
            if frames_into < dissolve_frames:
                prev_seg = timeline[si - 1]
                prev_sd = max(0.05, prev_seg["t1"] - prev_seg["t0"])
                prev_pil = render_raw_scene_frame(si - 1, 1.0, prev_sd, prev_sd, prev_seg["t1"], stills)
                alpha_mix = (frames_into + 1) / (dissolve_frames + 1)
                frame_pil = Image.blend(prev_pil, frame_pil, alpha_mix)

        arr = np.asarray(frame_pil, dtype=np.uint8).copy()
        pmode = "dust" if si in MAP_SCENES else PHOTO_CAM[si][6]
        if si not in MAP_SCENES:
            arr = overlay_particles(arr, pmode, t, si)
        arr = ((arr.astype(np.uint16) * vign[..., None]) >> 8).clip(0, 255).astype(np.uint8)
        frame_pil = Image.fromarray(arr)

        frame_pil = draw_ep05_hud(frame_pil, si, tau)

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
            print(f"  [KZ] Frame {fi}/{total_frames} ({t:.1f}s/{dur:.1f}s)", flush=True)

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
    print(f"  DONE [KZ]: {out_mp4} ({dur:.1f}s, {sz_mb:.1f} MB) in {time.time() - t_start:.1f}s", flush=True)
    return out_mp4


if __name__ == "__main__":
    v_only = "--voice-only" in sys.argv[1:]
    build_ep05(voice_only=v_only)
