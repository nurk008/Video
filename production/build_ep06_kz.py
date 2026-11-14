#!/usr/bin/env python3
"""Episode 6 Builder (KZ ONLY • TURBO RETENTION): 'How Abylai Khan Saved the Steppe'
Engineered to defeat the 3s skip-rate wall and 12s AVD wall:
  - Total runtime ~32-35s, +10% voice cadence, 0.06s tight pauses
  - 3 rapid hook cuts in the first 2.5s + t=0.05s impact boom & clash
  - Pattern interrupt @ ~10s before drop-off point
  - 14 distinct visual cuts (~2.4s avg shot duration) alternating 3D maps & kinetic photoreal
"""

import asyncio
import json
import math
import os
import re
import subprocess
import sys
import time
import wave
from pathlib import Path

import edge_tts
import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path("/Users/market/antigravity/Video")
PROD = ROOT / "production"
SCENES_DIR = ROOT / "scenes_ep06"
BUILD = PROD / "build_ep06"
OUT_DIR = ROOT / "output"
BIN_DIR = PROD / "build_ep02" / "_bin"
OUT_FILE = "EP06_Abylai_Turbo_Shorts_KZ.mp4"

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
VOICE_RATE = "+14%"
VOICE_PITCH = "-1Hz"

VOICE_FX = (
    "highpass=f=75,"
    "equalizer=f=150:t=q:w=1.1:g=2.5,"
    "equalizer=f=320:t=q:w=1.2:g=-1.5,"
    "equalizer=f=3200:t=q:w=1.3:g=2.2,"
    "equalizer=f=6800:t=q:w=1.5:g=-1.8,"
    "acompressor=threshold=-16dB:ratio=2.5:attack=10:release=120:makeup=1.8,"
    "alimiter=limit=-1.2dB:attack=4:release=45"
)

# 12 punchy lines (~82 words -> ~33s at +14%) — ZERO dates in spoken hook
EP06_SCRIPT_KZ = [
    "Екі алып империя қысқанда, Абылай хан даланы қалай сақтады?",
    "Солтүстіктен Ресей бекіністері, шығыстан Цин әскері төнді.",
    "Бір қателік бүкіл Қазақ ордасын жояр еді.",
    "Алдымен Көкшетауда үш жүздің күші бір арнаға тоғысты.",
    "Басты айла — екі алыпты бір-бірімен тең ұстау!",
    "Шығыста Қабанбай мен Бөгенбай жау екпінін тойтарды.",
    "Қазақ атты әскері ауыр жасақтан үш есе шапшаң болды.",
    "Жетісу, Тарбағатай мен Зайсан жайлаулары қайтарылды.",
    "Абылай дипломатиямен соғысты тоқтатып, сауда ашты.",
    "Шекара Жайықтан Алтай тауына дейін бекіді.",
    "Түркістанда ақ киізге көтеріліп, дербес елді нығайтты.",
    "Дала дипломатиясының ұлы жеңісі. Ал мұның сыры,",
]

HUD_META_KZ = {
    "pillars": ["1. ТІРЕК", "2. АЙЛА", "3. СОҚҚЫ", "4. ШЕКАРА"],
    "banners": [
        ("ҚОС ИМПЕРИЯ ҚЫСЫМЫ", "ЕКІ АЛЫП ОРТАСЫНДАҒЫ ҚАЗАҚ ДАЛАСЫ", -1),
        ("ҚОС МАЙДАН ҚАУПІ", "СОЛТҮСТІКТЕН РЕСЕЙ • ШЫҒЫСТАН ЦИН", -1),
        ("ӨМІР НЕМЕСЕ ЖОЙЫЛУ", "БІР ҚАТЕЛІК ОРДАНЫ ЖОЯР ЕДІ", -1),
        ("1-ҚАДАМ • ІШКІ ТІРЕК", "КӨКШЕТАУДА ҮШ ЖҮЗ КҮШІН БІРІКТІРУ", 0),
        ("БАСТЫ АЙЛА • ТЕПЕ-ТЕҢДІК", "ЕКІ АЛЫПТЫ БІР-БІРІМЕН ТЕҢ ҰСТАУ", 1),
        ("3-ҚАДАМ • ШЫҒЫС ҚАРҚЫНЫ", "ҚАБАНБАЙ МЕН БӨГЕНБАЙ ШАБУЫЛЫ", 2),
        ("ДАЛА МАНЕВРІ • ×3 ҚАРҚЫН", "АУЫР ОБОЗДАН ҮШ ЕСЕ ЖЫЛДАМ", 2),
        ("ШЫҒЫС ЖАЙЛАУЛАРЫ ОРАЛДЫ", "ЖЕТІСУ • ТАРБАҒАТАЙ • ЗАЙСАН", 2),
        ("ДИПЛОМАТИЯ ЖЕҢІСІ", "СОҒЫСТЫ ТОҚТАТЫП, САУДА АШУ", 3),
        ("4-ҚАДАМ • БЕРІК ШЕКАРА", "ЕДІЛ–ЖАЙЫҚТАН АЛТАЙҒА ДЕЙІН", 3),
        ("ТҮРКІСТАН • ҮШ ЖҮЗДІҢ ХАНЫ", "АҚ КИІЗГЕ КӨТЕРІЛГЕН ДЕРБЕС ОРДА", -1),
        ("ТҰЙЫҚ ШЕҢБЕР", "ДАЛА ДИПЛОМАТИЯСЫНЫҢ ЕҢ ҰЛЫ ЖЕҢІСІ...", -1),
    ],
}

# Steppe-wide geography in [0..1080, 0..1920] world coordinates (fits comfortably inside y=350..960)
EP06_CITIES = {
    "Сарайшық":   (135, 515),
    "Көкшетау":   (465, 420),
    "Ұлытау":     (375, 645),
    "Түркістан":  (415, 895),
    "Жетісу":     (675, 865),
    "Тарбағатай": (835, 675),
    "Зайсан":     (885, 535),
    "Алтай":      (920, 395),
}

EP06_LABEL_SIDE = {
    "Сарайшық":   "below",
    "Көкшетау":   "above",
    "Ұлытау":     "left",
    "Түркістан":  "left",
    "Жетісу":     "below",
    "Тарбағатай": "left",
    "Зайсан":     "left",
    "Алтай":      "above",
}

ERTIS_PTS = [(970, 310), (855, 455), (710, 415), (555, 315)]
SYRDARYA_EP06_PTS = [(650, 945), (495, 920), (355, 835), (215, 760)]
ILI_PTS = [(850, 885), (735, 860), (635, 785)]

MAP_SCENES = {1, 3, 5, 7, 9}

PHOTO_CAM = {
    "cut01a": (1.03, 1.16, 0.50, 0.48, 0.50, 0.45),
    "cut01b": (1.02, 1.14, 0.48, 0.48, 0.53, 0.45),
    2:        (1.03, 1.16, 0.49, 0.47, 0.52, 0.44),
    4:        (1.02, 1.15, 0.50, 0.48, 0.50, 0.44),
    6:        (1.02, 1.16, 0.50, 0.49, 0.50, 0.43),
    8:        (1.03, 1.15, 0.50, 0.48, 0.48, 0.45),
    10:       (1.02, 1.14, 0.50, 0.49, 0.50, 0.44),
    11:       (1.02, 1.16, 0.50, 0.50, 0.50, 0.44),
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
            time.sleep(0.5 * (attempt + 1))
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


def trim_silence(x: np.ndarray, pad_s: float = 0.03, thresh: float = 0.010) -> np.ndarray:
    idx = np.where(np.abs(x) > thresh)[0]
    if len(idx) == 0:
        return x
    pad = int(pad_s * SR)
    i0 = max(0, int(idx[0]) - pad)
    i1 = min(len(x), int(idx[-1]) + int(0.05 * SR))
    out = x[i0:i1].copy()
    fi = min(int(0.012 * SR), len(out) // 4)
    fo = min(int(0.018 * SR), len(out) // 4)
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
            wt1 = max(wt0 + 0.07, wt1)
            out.append({"w": w, "scene": scene_num, "t0": round(wt0, 3), "t1": round(wt1, 3)})
        return out

    vowels = set("аеёиоуыэюяәіңғүұқөһАЕЁИОУЫЭЮЯӘІҢҒҮҰҚӨҺaeiouyAEIOUY")
    weights = []
    for w in display_words:
        v = sum(1 for c in w if c in vowels)
        p = 1.4 if w[-1] in ".!?" else (0.7 if w[-1] in ",;—–:" else 0.0)
        weights.append(max(1.1, v * 1.0 + len(w) * 0.16 + p))
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

    for si, text in enumerate(EP06_SCRIPT_KZ):
        mp3_p = ldir / f"line_{si:02d}.mp3"
        wav_p = ldir / f"line_{si:02d}.wav"
        bounds = synth_line_with_retry(text, mp3_p, wav_p)
        raw = read_wav_mono(wav_p)
        spoken = trim_silence(raw)
        speech_dur = len(spoken) / SR
        pause_after = 0.10 if si == len(EP06_SCRIPT_KZ) - 1 else 0.06
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
    smod.write(str(voice_wav), smod.norm(full_voice, 0.94))
    return voice_wav, timeline, words_all, len(full_voice) / SR


def run_ep06_sfx(voice_wav: Path, timeline: list, dur: float):
    ldir = BUILD / "kz"
    mix_raw = ldir / "mix_raw.wav"
    mix_wav = ldir / "mix.wav"

    v = smod.bp(read_wav_mono(voice_wav).astype(np.float64), 80, 11500)
    N = int(round(dur * SR))
    amb = np.zeros((N, 2), dtype=np.float64)
    rng = np.random.default_rng(1771)

    # Atmospheric steppe gale bed (zero instruments)
    bed = smod.wind(rng, dur, howl=0.22) * 0.28
    amb += smod.st(bed, 0.0)

    # Intense A cappella male choir pads
    A2, D3, E3, F3, G3, A3, C4, D4, E4 = 110.00, 146.83, 164.81, 174.61, 196.00, 220.00, 261.63, 293.66, 329.63
    t_s = lambda si: timeline[si]["t0"]

    t0_b, t0_c = t_s(4), t_s(8)
    smod.add(amb, smod.reverb(smod.vocal_pad(rng, t0_b, (D3, F3, A3, D4), "o", 4), wet=0.40, seed=601) * 0.36, 0.0)
    smod.add(amb, smod.reverb(smod.vocal_pad(rng, t0_c - t0_b, (D3, F3, G3, C4), "u", 4), wet=0.42, seed=602) * 0.38, t0_b)
    smod.add(amb, smod.reverb(smod.vocal_pad(rng, dur - t0_c, (D3, F3, A3, D4, E4), "a", 5), wet=0.45, seed=603) * 0.42, t0_c)

    # High-retention audio punches matched to cuts
    for si, seg in enumerate(timeline):
        t0 = seg["t0"]
        sd = seg["t1"] - seg["t0"]
        if si == 0:
            # 0.05s instant scroll-stopper impact + sword clash + sub-cut whooshes
            smod.add(amb, smod.reverb(smod.impact_boom(rng, 1.6), wet=0.28, seed=701) * 0.72, 0.02)
            smod.add(amb, smod.reverb(smod.sword_clash(rng), wet=0.24, seed=702) * 0.56, 0.05)
            smod.add(amb, smod.st(smod.whoosh(rng, 0.45), -0.25) * 0.46, sd * 0.33)
            smod.add(amb, smod.st(smod.whoosh(rng, 0.45), 0.25) * 0.48, sd * 0.66)
        elif si == 1:
            smod.add(amb, smod.st(smod.herd_far(rng, sd), -0.15) * 0.40, t0)
        elif si == 2:
            smod.add(amb, smod.st(smod.thunder(rng, min(2.4, sd)), 0.0) * 0.46, t0)
        elif si == 3:
            smod.add(amb, smod.reverb(smod.clasp(rng), wet=0.22, seed=704) * 0.46, t0 + 0.12)
        elif si == 4:
            # 10s Pattern Interrupt punch
            smod.add(amb, smod.reverb(smod.impact_boom(rng, 1.4), wet=0.28, seed=705) * 0.62, t0)
            smod.add(amb, smod.reverb(smod.clasp(rng), wet=0.20, seed=706) * 0.48, t0 + 0.35)
        elif si == 5:
            smod.add(amb, smod.st(smod.herd(rng, sd), 0.1) * 0.48, t0)
            smod.add(amb, smod.st(smod.whoosh(rng, 0.55), -0.2) * 0.44, t0 + 0.4)
        elif si == 6:
            smod.add(amb, smod.st(smod.gallop(rng, sd, horses=10, rate=2.4), 0.0) * 0.48, t0)
            smod.add(amb, smod.st(smod.whoosh(rng, 0.5), 0.25) * 0.42, t0 + 0.6)
        elif si == 7:
            for st_u in (0.14, 0.44, 0.72):
                smod.add(amb, smod.reverb(smod.thud(rng), wet=0.20, seed=708 + int(st_u * 100)) * 0.48, t0 + sd * st_u)
        elif si == 8:
            smod.add(amb, smod.reverb(smod.clasp(rng), wet=0.24, seed=709) * 0.42, t0 + 0.25)
        elif si == 9:
            smod.add(amb, smod.reverb(smod.impact_boom(rng, 1.8), wet=0.32, seed=710) * 0.52, t0 + 0.1)
        elif si == 10:
            smod.add(amb, smod.st(smod.eagle(rng), 0.2) * 0.40, t0 + 0.25)
        elif si == 11:
            smod.add(amb, smod.st(smod.riser(rng, min(1.8, sd * 0.75)), 0.0) * 0.45, max(t0, dur - min(1.8, sd * 0.75)))

    rms = smod.frame_rms(v, win=0.05)
    rms_st = np.interp(np.arange(N), np.arange(len(rms)) * int(SR * 0.05), rms)
    duck = 1.0 - 0.56 * np.clip(rms_st / 0.085, 0.0, 1.0)
    amb *= duck[:, None]

    out = amb * 0.92 + smod.st(v, 0.0) * 1.00
    out = smod.softclip(out, 0.90)
    smod.write(str(mix_raw), out)
    smod.loudnorm(str(mix_raw), str(mix_wav), I=-14, TP=-1.5, LRA=11)
    return mix_wav


def render_steppe_map_canvas(zoom: float, cx: float, cy: float, t: float) -> tuple[Image.Image, anim.MapCamera]:
    """Crop 2x relief atlas to MapCamera with Kazakhstan steppe rivers (Ertis, Syr Darya, Ili)."""
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

    for wpts, count in ((ERTIS_PTS, 12), (SYRDARYA_EP06_PTS, 10), (ILI_PTS, 7)):
        dense_w = anim.eval_polyline(wpts, 100)
        dense_s = cam.pts(dense_w)
        d.line(dense_s, fill=(24, 105, 138, 130), width=max(9, int(11 * zoom)))
        d.line(dense_s, fill=(76, 198, 228, 190), width=max(4, int(5 * zoom)))
        for k in range(count):
            u0 = (k / count + t * 0.11) % 1.0
            u1 = min(1.0, u0 + 0.04)
            x0, y0, _ = anim.point_along_path(dense_w, u0)
            x1, y1, _ = anim.point_along_path(dense_w, u1)
            alpha = int(165 * math.sin(math.pi * ((t * 1.6 + k * 0.7) % 1.0)) ** 2 + 55)
            d.line([cam.pt(x0, y0), cam.pt(x1, y1)], fill=(205, 250, 255, alpha), width=3)

    fr = anim.get_font(20)
    d.text(cam.pt(710, 355), "ЕРТІС", font=fr, fill=(108, 214, 240, 165))
    d.text(cam.pt(245, 795), "СЫРДАРИЯ", font=fr, fill=(108, 214, 240, 160))
    d.text(cam.pt(730, 810), "ІЛЕ", font=fr, fill=(108, 214, 240, 155))

    bg.alpha_composite(ov)
    return bg, cam


def draw_steppe_cities(ov: Image.Image, cam: anim.MapCamera, statuses: dict, bursts: dict, capitals: set, t: float):
    for name, wpos in EP06_CITIES.items():
        if name not in statuses:
            continue
        anim.draw_fortress_node(
            ov, cam, wpos, name, statuses[name], t,
            pulse_burst=bursts.get(name, 0.0),
            is_capital=(name in capitals),
            label_side=EP06_LABEL_SIDE.get(name, "auto"),
        )


def draw_hook_flash_badge(ov: Image.Image, title: str, sub: str, col=(248, 202, 84), tau: float = 0.2):
    d = ImageDraw.Draw(ov)
    pop = anim.ease_out(min(1.0, tau / 0.16))
    cw, ch = 780, 96
    x0, y0 = (W - cw) // 2, 1140 + int(18 * (1.0 - pop))
    d.rounded_rectangle([x0, y0, x0 + cw, y0 + ch], radius=16, fill=(12, 16, 24, int(226 * pop)), outline=(*col, int(245 * pop)), width=3)
    f1, f2 = anim.get_font(33), anim.get_font(21)
    d.text(((W - d.textlength(title, font=f1)) / 2, y0 + 13), title, font=f1, fill=(*col, int(252 * pop)))
    d.text(((W - d.textlength(sub, font=f2)) / 2, y0 + 57), sub, font=f2, fill=(244, 246, 250, int(240 * pop)))


def draw_threat_meter_card(ov: Image.Image, tau: float, seg_dur: float, t: float):
    d = ImageDraw.Draw(ov)
    pop = anim.ease_out(min(1.0, tau / 0.25))
    fill_u = anim.ease_out(min(1.0, max(0.0, (tau - 0.05) / max(0.6, seg_dur * 0.65))))
    x0, y0, cw, ch = 120, 1080, W - 240, 146
    d.rounded_rectangle([x0, y0, x0 + cw, y0 + ch], radius=18, fill=(24, 12, 14, int(224 * pop)), outline=(235, 82, 70, int(240 * pop)), width=3)
    ft = anim.get_font(23)
    pct = int(round(45 + 50 * fill_u))
    d.text((x0 + 26, y0 + 18), f"ҚОС МАЙДАН ҚАУПІ: {pct}% • ШЕШУШІ СӘТ", font=ft, fill=(255, 180, 155, int(248 * pop)))

    bx, by, bw, bh = x0 + 26, y0 + 62, cw - 52, 32
    d.rounded_rectangle([bx, by, bx + bw, by + bh], radius=10, fill=(40, 24, 28, 220))
    d.rounded_rectangle([bx, by, bx + max(40, int(bw * (pct / 100.0))), by + bh], radius=10, fill=(235, 76, 62, int(238 * pop)))

    fs = anim.get_font(20)
    d.text((bx, y0 + 106), "СОЛТҮСТІК ШЕП + ШЫҒЫС ҚЫСЫМЫ БІР СӘТТЕ", font=fs, fill=(244, 232, 228, int(235 * pop)))


def draw_balance_seesaw_card(ov: Image.Image, tau: float, seg_dur: float, t: float):
    d = ImageDraw.Draw(ov)
    pop = anim.ease_out(min(1.0, tau / 0.22))
    settle = anim.ease_out(min(1.0, max(0.0, tau / max(0.6, seg_dur * 0.7))))
    x0, y0, cw, ch = 100, 1080, W - 200, 154
    d.rounded_rectangle([x0, y0, x0 + cw, y0 + ch], radius=18, fill=(10, 18, 26, int(226 * pop)), outline=(248, 202, 84, int(240 * pop)), width=3)

    ft = anim.get_font(22)
    head = "СТРАТЕГИЯЛЫҚ АЙЛА • ЕКІ ИМПЕРИЯ ТЕПЕ-ТЕҢДІГІ"
    d.text(((W - d.textlength(head, font=ft)) / 2, y0 + 16), head, font=ft, fill=(78, 224, 222, int(248 * pop)))

    # Animated balancing beam settling from tilted to level
    cx, cy = W // 2, y0 + 96
    tilt = math.radians(11.0 * (1.0 - settle) * math.cos(t * 7.0))
    half = 275
    dx, dy = math.cos(tilt) * half, math.sin(tilt) * half
    d.line([(cx - dx, cy - dy), (cx + dx, cy + dy)], fill=(248, 202, 84, int(245 * pop)), width=7)
    d.polygon([(cx, cy + 4), (cx - 18, cy + 32), (cx + 18, cy + 32)], fill=(78, 224, 222, int(245 * pop)))

    f_end = anim.get_font(22)
    f_mid = anim.get_font(21)
    d.rounded_rectangle([cx - dx - 68, cy - dy - 38, cx - dx + 68, cy - dy - 8], radius=8, fill=(28, 36, 48, 240), outline=(235, 92, 78, 240), width=2)
    rw = d.textlength("РЕСЕЙ", font=f_end)
    d.text((cx - dx - rw / 2, cy - dy - 35), "РЕСЕЙ", font=f_end, fill=(252, 232, 228, 250))

    d.rounded_rectangle([cx + dx - 58, cy + dy - 38, cx + dx + 58, cy + dy - 8], radius=8, fill=(28, 36, 48, 240), outline=(235, 92, 78, 240), width=2)
    qw = d.textlength("ЦИН", font=f_end)
    d.text((cx + dx - qw / 2, cy + dy - 35), "ЦИН", font=f_end, fill=(252, 232, 228, 250))

    ow = d.textlength("ҚАЗАҚ ОРДАСЫ", font=f_mid)
    d.text((cx - ow / 2, cy - 38), "ҚАЗАҚ ОРДАСЫ", font=f_mid, fill=(248, 202, 84, int(252 * pop)))


def draw_recovered_counter(ov: Image.Image, n_flipped: int, total: int = 3):
    d = ImageDraw.Draw(ov)
    cw, ch = 580, 86
    x0, y0 = (W - cw) // 2, 1180
    d.rounded_rectangle([x0, y0, x0 + cw, y0 + ch], radius=16, fill=(10, 16, 24, 224), outline=(248, 202, 84, 240), width=3)
    f1 = anim.get_font(28)
    txt = f"ҚАЙТАРЫЛҒАН ШЕКАРА: {n_flipped} / {total}"
    d.text(((W - d.textlength(txt, font=f1)) / 2, y0 + 25), txt, font=f1, fill=(248, 202, 84, 252))


def draw_diplomacy_shield_card(ov: Image.Image, tau: float, seg_dur: float):
    d = ImageDraw.Draw(ov)
    pop = anim.ease_out(min(1.0, tau / 0.25))
    prog = anim.ease_out(min(1.0, max(0.0, tau / max(0.6, seg_dur * 0.65))))
    cw, ch = 780, 118
    x0, y0 = (W - cw) // 2, 1105
    d.rounded_rectangle([x0, y0, x0 + cw, y0 + ch], radius=18, fill=(12, 22, 30, int(226 * pop)), outline=(78, 224, 222, int(240 * pop)), width=3)
    f1, f2 = anim.get_font(29), anim.get_font(21)
    t1 = "БЕЙБІТ КЕЛІСІМ ЖӘНЕ ЕРКІН САУДА"
    t2 = "АБЫЛАЙ ДИПЛОМАТИЯСЫ • ЕЛ ҚАУІПСІЗДІГІ"
    d.text(((W - d.textlength(t1, font=f1)) / 2, y0 + 18), t1, font=f1, fill=(248, 202, 84, int(252 * pop)))
    d.line([(x0 + 80, y0 + 60), (x0 + 80 + (cw - 160) * prog, y0 + 60)], fill=(78, 224, 222, int(220 * pop)), width=4)
    d.text(((W - d.textlength(t2, font=f2)) / 2, y0 + 74), t2, font=f2, fill=(240, 246, 250, int(242 * pop)))


def draw_steppe_border_shield(ov: Image.Image, cam: anim.MapCamera, tau: float, seg_dur: float, part: str = "both"):
    d = ImageDraw.Draw(ov)
    if part in ("both", "shield"):
        C = EP06_CITIES
        ring = [C["Сарайшық"], C["Көкшетау"], C["Алтай"], C["Зайсан"], C["Тарбағатай"], C["Жетісу"], C["Түркістан"], C["Сарайшық"]]
        dense_w = anim.eval_polyline(ring, 140)
        dense_s = cam.pts(dense_w)
        prog = anim.ease_out(min(1.0, max(0.0, tau / max(0.8, seg_dur * 0.72))))
        sub = dense_s[: max(3, int(prog * (len(dense_s) - 1)))]
        if len(sub) >= 3:
            d.line(sub, fill=(78, 224, 222, 120), width=18, joint="curve")
            d.line(sub, fill=(248, 202, 84, 238), width=6, joint="curve")

    if part in ("both", "card"):
        pop = anim.ease_out(min(1.0, tau / 0.25))
        cw, ch = 760, 98
        x0, y0 = (W - cw) // 2, 1130
        d.rounded_rectangle([x0, y0, x0 + cw, y0 + ch], radius=18, fill=(10, 18, 26, int(228 * pop)), outline=(248, 202, 84, int(242 * pop)), width=3)
        f1, f2 = anim.get_font(31), anim.get_font(20)
        t1 = "ЕДІЛДЕН АЛТАЙҒА ДЕЙІН • БЕРІК ШЕКАРА"
        t2 = "ТҰТАС ҚАЗАҚ ХАНДЫҒЫНЫҢ АУМАҒЫ"
        d.text(((W - d.textlength(t1, font=f1)) / 2, y0 + 16), t1, font=f1, fill=(248, 202, 84, int(252 * pop)))
        d.text(((W - d.textlength(t2, font=f2)) / 2, y0 + 60), t2, font=f2, fill=(116, 228, 228, int(245 * pop)))


def rigid_cam_key(im_src: Image.Image, cam_key, u: float, tau: float, shake: bool = False) -> Image.Image:
    z0, z1, cx0, cy0, cx1, cy1 = PHOTO_CAM[cam_key]
    e = u * u * (3.0 - 2.0 * u)
    z = z0 + (z1 - z0) * e
    cx = cx0 + (cx1 - cx0) * e
    cy = cy0 + (cy1 - cy0) * e

    dx_px, dy_px = 0.0, 0.0
    if shake and tau <= 0.45:
        dec = math.exp(-7.5 * tau)
        dx_px = 10.0 * dec * math.sin(tau * 62.0)
        dy_px = 7.0 * dec * math.cos(tau * 50.0)

    vw = W / z
    vh = H / z
    x0 = max(0.0, min(W - vw, cx * W - vw * 0.5 + dx_px / z))
    y0 = max(0.0, min(H - vh, cy * H - vh * 0.5 + dy_px / z))
    return im_src.transform((W, H), Image.Transform.EXTENT, (x0, y0, x0 + vw, y0 + vh), Image.Resampling.BICUBIC)


def render_map_scene_frame(si: int, u: float, tau: float, seg_dur: float, t: float) -> Image.Image:
    e = anim.smoothstep(u)
    C = EP06_CITIES

    if si == 1:
        # Map 1 (Double-front pressure from Russia N & Qing E)
        bg, cam = render_steppe_map_canvas(1.06 + 0.06 * e, 530, 650, t)
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        p = anim.ease_out(min(1.0, u / 0.85))
        # Red arrows pressing in from North & East
        anim.draw_animated_arrow(ov, cam, [(260, 250), (360, 345), (440, 415)], p, t, col_main=(232, 72, 62), col_glow=(255, 130, 110), width=12)
        anim.draw_animated_arrow(ov, cam, [(680, 240), (585, 330), (495, 410)], p, t, col_main=(232, 72, 62), col_glow=(255, 130, 110), width=12)
        anim.draw_animated_arrow(ov, cam, [(1020, 520), (925, 550), (775, 655)], p, t, col_main=(232, 72, 62), col_glow=(255, 130, 110), width=14)
        anim.draw_animated_arrow(ov, cam, [(1010, 760), (885, 745), (725, 835)], p, t, col_main=(232, 72, 62), col_glow=(255, 130, 110), width=13)

        statuses = {
            "Көкшетау": "kazakh", "Ұлытау": "kazakh", "Түркістан": "kazakh", "Сарайшық": "kazakh",
            "Жетісу": "red", "Тарбағатай": "red", "Зайсан": "red", "Алтай": "red",
        }
        draw_steppe_cities(ov, cam, statuses, {}, {"Көкшетау", "Түркістан"}, t)
        draw_hook_flash_badge(ov, "РЕСЕЙ ШЕБІ  +  ЦИН ШАБУЫЛЫ", "ЕКІ ЖАҚТЫ ҚОРШАУ ҚАУПІ", col=(240, 95, 82), tau=tau)
        bg.alpha_composite(ov)
        return bg.convert("RGB")

    elif si == 3:
        # Map 2 (1. ТІРЕК: Uniting 3 Zhuzes at Kokshetau + Recon Radar)
        bg, cam = render_steppe_map_canvas(1.22 + 0.08 * e, 470, 625, t)
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        anim.draw_recon_radar_map(ov, cam, target_wpos=C["Көкшетау"], origin_wpos=C["Көкшетау"], t=t, tau=tau)
        p = anim.ease_out(min(1.0, u / 0.85))
        for start in (C["Сарайшық"], C["Ұлытау"], C["Түркістан"]):
            anim.draw_animated_arrow(ov, cam, [start, ((start[0] + 465) // 2, (start[1] + 420) // 2), C["Көкшетау"]], p, t, col_main=(248, 202, 84), col_glow=(78, 224, 222), width=11)

        anim.draw_army_unit_marker(ov, cam, C["Көкшетау"], -0.4, "ҮШ ЖҮЗ БІРЛІГІ", col=(248, 202, 84), t=t, label_offset=(125, -18))
        statuses = {"Сарайшық": "kazakh", "Ұлытау": "kazakh", "Түркістан": "kazakh", "Көкшетау": "capturing"}
        draw_steppe_cities(ov, cam, statuses, {"Көкшетау": min(1.0, u * 1.4)}, {"Көкшетау", "Түркістан"}, t)
        bg.alpha_composite(ov)
        return bg.convert("RGB")

    elif si == 5:
        # Map 3 (3. СОҚҚЫ: Lightning Eastern Counter-Offensive — Kabanbai & Bogenbai)
        bg, cam = render_steppe_map_canvas(1.18 + 0.08 * e, 635 + 30 * e, 615, t)
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        p = anim.ease_out(min(1.0, u / 0.85))
        r1 = [C["Көкшетау"], (690, 445), C["Зайсан"]]
        r2 = [C["Ұлытау"], (620, 675), C["Тарбағатай"]]
        r3 = [C["Түркістан"], C["Жетісу"]]
        anim.draw_animated_arrow(ov, cam, r1, p, t, width=13)
        anim.draw_animated_arrow(ov, cam, r2, p, t, width=13)
        anim.draw_animated_arrow(ov, cam, r3, p, t, col_main=(78, 224, 222), col_glow=(248, 202, 84), width=11)

        d1 = anim.eval_polyline(r1, 80)
        px1, py1, ang1 = anim.point_along_path(d1, min(0.95, p * 0.94))
        anim.draw_army_unit_marker(ov, cam, (px1, py1), ang1, "ҚАБАНБАЙ • БӨГЕНБАЙ", t=t, label_offset=(0, -56))

        statuses = {
            "Көкшетау": "kazakh", "Ұлытау": "kazakh", "Түркістан": "kazakh",
            "Жетісу": "red", "Тарбағатай": "red", "Зайсан": "red", "Алтай": "red",
        }
        draw_steppe_cities(ov, cam, statuses, {}, {"Көкшетау"}, t)
        bg.alpha_composite(ov)
        return bg.convert("RGB")

    elif si == 7:
        # Map 4 (ЖЕР ҚАЙТАРУ: Sequential Eastern Flip 1/3 -> 3/3)
        bg, cam = render_steppe_map_canvas(1.22, 685 + 20 * e, 645, t)
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        thresholds = [("Жетісу", 0.16), ("Тарбағатай", 0.44), ("Зайсан", 0.72)]
        statuses = {"Көкшетау": "kazakh", "Түркістан": "kazakh", "Ұлытау": "kazakh", "Алтай": "kazakh"}
        bursts = {}
        flipped = 0
        for cname, thr in thresholds:
            if u < thr - 0.05:
                statuses[cname] = "red"
            elif u < thr + 0.14:
                statuses[cname] = "capturing"
                bursts[cname] = (u - (thr - 0.05)) / 0.19
                flipped += 1
            else:
                statuses[cname] = "kazakh"
                flipped += 1

        p = anim.ease_out(min(1.0, u / 0.88))
        anim.draw_animated_arrow(ov, cam, [C["Жетісу"], C["Тарбағатай"], C["Зайсан"], C["Алтай"]], p, t, width=13)
        draw_steppe_cities(ov, cam, statuses, bursts, {"Тарбағатай", "Зайсан"}, t)
        draw_recovered_counter(ov, flipped, 3)
        bg.alpha_composite(ov)
        return bg.convert("RGB")

    else:
        # Map 5 (si == 9, 4. ШЕКАРА): Full Kazakh Steppe Golden-Turquoise Border Shield
        bg, cam = render_steppe_map_canvas(1.06 - 0.04 * e, 540, 650, t)
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw_steppe_border_shield(ov, cam, tau, seg_dur, part="shield")
        statuses = {name: "kazakh" for name in EP06_CITIES}
        draw_steppe_cities(ov, cam, statuses, {}, {"Көкшетау", "Түркістан", "Алтай"}, t)
        draw_steppe_border_shield(ov, cam, tau, seg_dur, part="card")
        bg.alpha_composite(ov)
        return bg.convert("RGB")


def render_raw_scene_frame(si: int, u: float, tau: float, seg_dur: float, t: float, stills: dict) -> Image.Image:
    if si == 0:
        # 3-CUT RAPID HOOK IN FIRST 2.8 SECONDS!
        if u < 0.34:
            sub_u = u / 0.34
            sub_tau = tau
            base = rigid_cam_key(stills["cut01a"], "cut01a", sub_u, sub_tau, shake=True)
            ov = anim.apply_drifting_mist(base, t, col=(250, 200, 120), y_dest=860, speed=75.0)
            anim.draw_arrow_barrage(ov, t, count=36, go_right=True)
            draw_hook_flash_badge(ov, "ҚОС ИМПЕРИЯ ҚЫСЫМЫ!", "ОРДАНЫ САҚТАУ ЖОЛЫ ҚАНДАЙ?", col=(248, 202, 84), tau=sub_tau)
            return ov.convert("RGB")
        elif u < 0.68:
            sub_u = (u - 0.34) / 0.34
            sub_tau = tau - seg_dur * 0.34
            base = rigid_cam_key(stills["cut01b"], "cut01b", sub_u, max(0.0, sub_tau), shake=False)
            ov = anim.apply_drifting_mist(base, t, col=(240, 212, 160), y_dest=850, speed=-65.0)
            draw_hook_flash_badge(ov, "АБЫЛАЙ ХАН СТРАТЕГИЯСЫ", "ЕКІ АЛЫПҚА ҚАРСЫ ДАЛА АҚЫЛЫ", col=(78, 224, 222), tau=max(0.0, sub_tau))
            return ov.convert("RGB")
        else:
            sub_u = (u - 0.68) / 0.32
            bg, cam = render_steppe_map_canvas(1.06 + 0.10 * anim.smoothstep(sub_u), 540, 640, t)
            ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            p = anim.ease_out(min(1.0, sub_u / 0.85))
            anim.draw_animated_arrow(ov, cam, [(280, 250), (455, 415)], p, t, col_main=(232, 72, 62), col_glow=(255, 130, 110), width=14)
            anim.draw_animated_arrow(ov, cam, [(1020, 520), (830, 670)], p, t, col_main=(232, 72, 62), col_glow=(255, 130, 110), width=14)
            statuses = {"Көкшетау": "kazakh", "Түркістан": "kazakh", "Зайсан": "red", "Тарбағатай": "red"}
            draw_steppe_cities(ov, cam, statuses, {}, {"Көкшетау"}, t)
            draw_hook_flash_badge(ov, "СОЛТҮСТІК + ШЫҒЫС МАЙДАН", "АЛАПАТ ҚЫСЫМ АСТЫНДА", col=(240, 95, 82), tau=max(0.0, tau - seg_dur * 0.68))
            bg.alpha_composite(ov)
            return bg.convert("RGB")

    if si in MAP_SCENES:
        return render_map_scene_frame(si, u, tau, seg_dur, t)

    base = rigid_cam_key(stills[si], si, u, tau, shake=(si == 4))
    if si == 2:
        ov = anim.apply_drifting_mist(base, t, col=(210, 165, 145), y_dest=830, speed=55.0)
        draw_threat_meter_card(ov, tau, seg_dur, t)
        return ov.convert("RGB")
    elif si == 4:
        ov = anim.apply_drifting_mist(base, t, col=(248, 214, 150), y_dest=850, speed=-48.0)
        draw_balance_seesaw_card(ov, tau, seg_dur, t)
        return ov.convert("RGB")
    elif si == 6:
        ov = anim.apply_drifting_mist(base, t, col=(245, 212, 152), y_dest=830, speed=72.0)
        anim.draw_arrow_barrage(ov, t, count=36, go_right=True)
        anim.draw_speed_comparison_card(ov, tau, seg_dur, y_center=1150)
        return ov.convert("RGB")
    elif si == 8:
        ov = anim.apply_drifting_mist(base, t, col=(220, 190, 140), y_dest=860, speed=40.0)
        draw_diplomacy_shield_card(ov, tau, seg_dur)
        return ov.convert("RGB")
    elif si == 10:
        ov = anim.apply_drifting_mist(base, t, col=(250, 224, 165), y_dest=850, speed=46.0)
        # Draw sunrise beams and custom Abylai/Turkestan seal
        d = ImageDraw.Draw(ov)
        pop = anim.ease_out(min(1.0, tau / 0.35))
        ox, oy = 540, 520
        for k in range(10):
            ang = math.radians(-155 + k * 31 + math.sin(t * 0.9 + k) * 4.0)
            r_far = 1150
            a = int((26 + 14 * math.sin(t * 2.5 + k)) * pop)
            d.polygon([(ox, oy), (ox + math.cos(ang - 0.09) * r_far, oy + math.sin(ang - 0.09) * r_far), (ox + math.cos(ang + 0.09) * r_far, oy + math.sin(ang + 0.09) * r_far)], fill=(255, 222, 130, a))
        cw, ch = 760, 96
        x0, y0 = (W - cw) // 2, 1115
        d.rounded_rectangle([x0, y0, x0 + cw, y0 + ch], radius=18, fill=(14, 18, 26, int(222 * pop)), outline=(248, 202, 84, int(242 * pop)), width=3)
        f1, f2 = anim.get_font(30), anim.get_font(20)
        t1 = "1771 • ТҮРКІСТАН — АБЫЛАЙ ХАН ОРДАСЫ"
        t2 = "ҮШ ЖҮЗДІҢ АҚ КИІЗГЕ КӨТЕРГЕН ХАНЫ"
        d.text(((W - d.textlength(t1, font=f1)) / 2, y0 + 15), t1, font=f1, fill=(248, 202, 84, int(252 * pop)))
        d.text(((W - d.textlength(t2, font=f2)) / 2, y0 + 58), t2, font=f2, fill=(116, 228, 228, int(245 * pop)))
        return ov.convert("RGB")
    else:
        ov = anim.apply_drifting_mist(base, t, col=(248, 214, 150), y_dest=840, speed=62.0)
        anim.draw_loop_surge_arrows(ov, tau, t)
        return ov.convert("RGB")


def draw_ep06_hud(frame_pil: Image.Image, si: int, tau: float):
    top_title, sub_callout, active_pillar = HUD_META_KZ["banners"][si]
    pillars = HUD_META_KZ["pillars"]

    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)

    alpha_in = min(1.0, max(0.0, tau / 0.22))
    bx_a = int(round(212 * alpha_in))
    tx_a = int(round(252 * alpha_in))
    gold = (248, 202, 84, tx_a)
    white = (250, 248, 240, tx_a)

    f_top = rmod.font(34)
    f_sub = rmod.font(28)
    f_pil = rmod.font(25)

    d.rounded_rectangle([60, 76, W - 60, 148], radius=22, fill=(10, 16, 24, bx_a), outline=(248, 202, 84, int(230 * alpha_in)), width=2)
    tw = d.textlength(top_title, font=f_top)
    d.text(((W - tw) / 2, 92), top_title, font=f_top, fill=gold)

    cw = d.textlength(sub_callout, font=f_sub)
    pw = min(W - 84, int(cw + 54))
    px0 = (W - pw) // 2
    d.rounded_rectangle([px0, 160, px0 + pw, 216], radius=16, fill=(14, 30, 38, int(204 * alpha_in)), outline=(78, 224, 222, int(208 * alpha_in)), width=2)
    d.text(((W - cw) / 2, 172), sub_callout, font=f_sub, fill=white)

    bar_y0, bar_y1 = 1628, 1700
    d.rounded_rectangle([54, bar_y0, W - 54, bar_y1], radius=20, fill=(10, 16, 24, 206), outline=(78, 224, 222, 142), width=2)

    slot_w = (W - 128) // 4
    for idx, label in enumerate(pillars):
        sx0 = 64 + idx * slot_w + 4
        sx1 = sx0 + slot_w - 8
        is_active = (idx == active_pillar)
        fill_c = (248, 202, 84, 238) if is_active else (18, 28, 38, 184)
        out_c = (255, 238, 165, 255) if is_active else (88, 135, 148, 155)
        txt_c = (12, 14, 20, 255) if is_active else (216, 228, 236, 228)
        d.rounded_rectangle([sx0, bar_y0 + 10, sx1, bar_y1 - 10], radius=12, fill=fill_c, outline=out_c, width=2)
        lw = d.textlength(label, font=f_pil)
        d.text((sx0 + (sx1 - sx0 - lw) / 2, bar_y0 + 21), label, font=f_pil, fill=txt_c)

    frame_rgba = frame_pil.convert("RGBA")
    frame_rgba.alpha_composite(overlay)
    return frame_rgba.convert("RGB")


def check_hud_and_glyphs():
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

    f = ImageFont.truetype("/Users/market/antigravity/Video/production/fonts/Montserrat-Black.ttf", 40)
    ref = f.getmask("\ufffe")
    strs = re.findall(r'"([^"\\]*(?:\\.[^"\\]*)*)"', Path(__file__).read_text(encoding="utf-8"))
    bad = [ch for s in strs for ch in s if ord(ch) > 32 and bytes(f.getmask(ch)) == bytes(ref) and f.getmask(ch).size == ref.size]
    assert not bad, f"Missing glyphs in build_ep06_kz.py: {set(bad)}"


def build_ep06(voice_only: bool = False):
    print(f"\n=== BUILDING EP06 [KZ ONLY • TURBO RETENTION] (voice_only={voice_only}) ===", flush=True)
    check_hud_and_glyphs()
    t_start = time.time()
    voice_wav, timeline, words_all, dur = build_voice_and_timeline()
    mix_wav = run_ep06_sfx(voice_wav, timeline, dur)

    ldir = BUILD / "kz"
    (ldir / "timeline.json").write_text(json.dumps(timeline, ensure_ascii=False, indent=2), encoding="utf-8")
    (ldir / "words.json").write_text(json.dumps(words_all, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  Voice + Mix ready: {dur:.2f}s (12 scenes / 14 visual cuts, {len(words_all)} words)", flush=True)
    if voice_only:
        return None

    stills = {
        "cut01a": Image.open(SCENES_DIR / "cut01a.jpg").convert("RGB"),
        "cut01b": Image.open(SCENES_DIR / "cut01b.jpg").convert("RGB"),
        2:  Image.open(SCENES_DIR / "scene_03.jpg").convert("RGB"),
        4:  Image.open(SCENES_DIR / "scene_05.jpg").convert("RGB"),
        6:  Image.open(SCENES_DIR / "scene_07.jpg").convert("RGB"),
        8:  Image.open(SCENES_DIR / "scene_09.jpg").convert("RGB"),
        10: Image.open(SCENES_DIR / "scene_11.jpg").convert("RGB"),
        11: Image.open(SCENES_DIR / "scene_12.jpg").convert("RGB"),
    }

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
    dissolve_frames = 3  # Snappy 0.10s crossfades for turbo retention!
    ci = 0
    si = 0

    for fi in range(total_frames):
        t = fi / FPS
        while si < 11 and t >= timeline[si]["t1"]:
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
        arr = ((arr.astype(np.uint16) * vign[..., None]) >> 8).clip(0, 255).astype(np.uint8)
        frame_pil = Image.fromarray(arr)
        frame_pil = draw_ep06_hud(frame_pil, si, tau)

        while ci < len(chunks) and t >= chunks[ci]["t1"] + 0.06:
            ci += 1
        if ci < len(chunks):
            ch = chunks[ci]
            if t >= ch["t0"] - 0.10 and t <= ch["t1"] + 0.10:
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
        if fi % (FPS * 5) == 0:
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
    build_ep06(voice_only=v_only)
