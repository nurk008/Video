#!/usr/bin/env python3
"""
B2B-05: 3D CGI Architectural Engineering Breakdown (Real Estate Developers & Public)
«Почему небоскрёб не падает при 8 баллах? (Сейсмозащита и маятник-гаситель в 3D)»

Reuses broadcast voice EQ (`_decode_broadcast_voice_wav`, `_tts_one_clean`) from B2B-04
and core subtitle/audio helpers (`_prep_tts_text`, `_align_words`, `loudnorm_portable`,
`draw_vector_check`) from B2B-01/render/sfx, while introducing 10 visually distinct
lighting worlds (bright alpine daylight, split tremor contrast, macro steel LRB,
subterranean strata, luminous penthouse atrium, amber hydraulic flow, tri-strip stack,
CRISP LIGHT IVORY Vox telemetry chart, golden-hour luxury sunset, and Navy-Gold Developer CTA).

Usage:
    python3 build_b2b_05_seismic_tower_multilang.py --preview
    python3 build_b2b_05_seismic_tower_multilang.py
"""
from __future__ import annotations

import asyncio
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

PROD = Path(__file__).resolve().parent
ROOT = PROD.parent
sys.path.insert(0, str(PROD))

import build_b2b_01_multilang as b1
import build_b2b_04_cgi_beshbarmak_multilang as b4
import render as rmod
import sfx as smod

rmod.FONT = PROD / "fonts" / "Montserrat-Black.ttf"

W, H, FPS = rmod.W, rmod.H, rmod.FPS
SUB_Y = b4.SUB_Y
SR = b4.SR
FFMPEG = b4.FFMPEG

SCENES_DIR = ROOT / "scenes_b2b05"
BUILD_ROOT = PROD / "build_b2b05"
OUT_DIR = ROOT / "output"

PAUSES = [0.07, 0.08, 0.08, 0.08, 0.08, 0.08, 0.08, 0.08, 0.08, 0.04]

VOICES = {
    "ru": ("ru-RU-SvetlanaNeural", "+4%", None),
    "kz": ("kk-KZ-DauletNeural", "+4%", None),
    "en": ("en-US-BrianMultilingualNeural", "+5%", None),
}

# ==============================================================================
#  10-SCENE SCRIPT (RU / KZ / EN) WITH PHONETIC `tts_fix` FOR CRISP ARTICULATION
# ==============================================================================
LANGS = {
    "ru": {
        "out_name": "B2B_05_CGI_SeismicTower_Shorts_RU.mp4",
        "pause_end": 0.14,
        "tts_fix": [
            ("8 баллов", "восемь баллов"),
            ("3D", "три дэ"),
            ("70%", "семидесяти процентов"),
            ("30 метров", "тридцати метров"),
            ("700 тонн", "семьсот тонн"),
            ("35 этаже", "тридцать пятом этаже"),
        ],
        "hook": "8 БАЛЛОВ • ПОЧЕМУ НЕ ПАДАЕТ?",
        "split_top": "БЕЗ ИЗОЛЯЦИИ   |   НА ОПОРАХ LRB",
        "split_l": "ЖЁСТКИЙ БЕТОН",
        "split_r": "СЕЙСМОЗАЩИТА",
        "lrb_tag": "СВИНЦОВО-РЕЗИНОВЫЕ ОПОРЫ",
        "lrb_span": "<- СДВИГ 35 СМ ->",
        "pile_badge": "БУРОНАБИВНЫЕ СВАИ • -30 М В ПОРОДУ",
        "tmd_wm": "700 Т",
        "tmd_sub": "МАЯТНИК В ПРОТИВОФАЗЕ • -40%",
        "hydro_tag": "КИНЕТИКА -> ТЕПЛО",
        "hydro_val": "ГИДРОДЕМПФЕР",
        "stack_title": "4 УРОВНЯ СЕЙСМОЗАЩИТЫ",
        "stack_labels": ["СВАИ 30 М", "ОПОРЫ LRB", "МАЯТНИК 700 Т"],
        "chart_kicker": "ИНЖЕНЕРНАЯ ТЕЛЕМЕТРИЯ • ВЕРХНИЕ ЭТАЖИ",
        "chart_title": "Амплитуда раскачки при 8 баллах",
        "chart_bad": "БЕЗ ЗАЩИТЫ: +/- 1.4 М",
        "chart_good": "С ЗАЩИТОЙ: +/- 0.2 М",
        "chart_stat": "В 7 РАЗ ТИШЕ",
        "calm_pill": "СПОКОЙСТВИЕ НА 35 ЭТАЖЕ",
        "cta_title": "3D ДЛЯ ЗАСТРОЙЩИКОВ",
        "cta_items": [
            "ДЛЯ ТАРГЕТА И REELS ЖК",
            "ПОКАЗ КОНСТРУКТИВА В 3D",
            "РОСТ ДОВЕРИЯ И ПРОДАЖ",
        ],
        "cta_btn": "ПИШИТЕ «3D» В DIRECT",
        "scenes": [
            {"scene": 1, "text": "Землетрясение в 8 баллов. Обычный дом треснет. Этот небоскрёб — просто качнётся. Как это работает?"},
            {"scene": 2, "text": "Если залить фундамент намертво, вся сила толчка пойдёт по стенам. Здание разорвёт собственная инерция."},
            {"scene": 3, "text": "Секрет под землёй. Весь дом стоит на свинцово-резиновых опорах. Они смещаются вбок и гасят до 70% удара."},
            {"scene": 4, "text": "Под опорами — глубокие сваи. Они уходят на 30 метров в плотную породу, рассеивая ударную волну."},
            {"scene": 5, "text": "А на самой вершине висит стальной шар весом в 700 тонн. Он качается в противофазе и останавливает крен."},
            {"scene": 6, "text": "Вокруг шара — мощные гидроцилиндры. Масло под давлением гасит энергию раскачки, превращая её в тепло."},
            {"scene": 7, "text": "Сваи, опоры, маятник и демпферы работают как один организм. Ни один болт не принимает удар в одиночку."},
            {"scene": 8, "text": "Посмотрите на график: без защиты крышу швыряет на полтора метра. С ней — амплитуда падает почти в семь раз."},
            {"scene": 9, "text": "Когда инженерная физика скрыта внутри бетона — вы спокойно пьёте чай на 35 этаже."},
            {"scene": 10, "text": "Строите жилые комплексы и продаёте надёжность? Покажите скрытую инженерию в 3D. Пишите 3D в Директ!"},
        ],
    },
    "kz": {
        "out_name": "B2B_05_CGI_SeismicTower_Shorts_KZ.mp4",
        "pause_end": 0.14,
        "tts_fix": [
            ("8 балдық", "сегіз балдық"),
            ("70%", "жетпіс пайызын"),
            ("30 метр", "отыз метр"),
            ("700 тонна", "жеті жүз тонна"),
            ("35-қабатта", "отыз бесінші қабатта"),
            ("3D", "три дэ"),
        ],
        "hook": "8 БАЛЛ • НЕГЕ ҚҰЛАМАЙДЫ?",
        "split_top": "ҚАТТЫ ІРГЕТАС   |   LRB ТІРЕКТЕРІ",
        "split_l": "ЖАРЫЛУ ҚАУПІ",
        "split_r": "СЕЙСМОҚОРҒАУ",
        "lrb_tag": "ҚОРҒАСЫН-РЕЗЕҢКЕ ТІРЕК",
        "lrb_span": "<- 35 СМ ЖЫЛЖУ ->",
        "pile_badge": "ТЕРЕҢ ҚАДАЛАР • -30 М ЖЫНЫСҚА",
        "tmd_wm": "700 Т",
        "tmd_sub": "ҚАРСЫ ТЕРБЕЛІС • -40% КРЕН",
        "hydro_tag": "КИНЕТИКА -> ЖЫЛУ",
        "hydro_val": "ГИДРОДЕМПФЕР",
        "stack_title": "4 ДЕҢГЕЙЛІ ҚОРҒАНЫС",
        "stack_labels": ["ҚАДА 30 М", "LRB ТІРЕК", "МАЯТНИК 700 Т"],
        "chart_kicker": "ИНЖЕНЕРЛІК ДЕРЕК • ЖОҒАРҒЫ ҚАБАТ",
        "chart_title": "8 балл кезіндегі шайқалу амплитудасы",
        "chart_bad": "ҚОРҒАУСЫЗ: +/- 1.4 М",
        "chart_good": "ҚОРҒАНЫСПЕН: +/- 0.2 М",
        "chart_stat": "7 ЕСЕ ТЫНЫШ",
        "calm_pill": "35-ҚАБАТТА ТОЛЫҚ ТЫНЫШТЫҚ",
        "cta_title": "ҚҰРЫЛЫС КОМПАНИЯЛАРЫНА 3D",
        "cta_items": [
            "REELS ПЕН ТАРГЕТКЕ ДАЙЫН",
            "КОНСТРУКТИВТІ 3D КӨРСЕТУ",
            "САТЫП АЛУШЫ СЕНІМІН ӨСІРУ",
        ],
        "cta_btn": "DIRECT-КЕ «3D» ЖАЗЫҢЫЗ",
        "scenes": [
            {"scene": 1, "text": "8 балдық зілзала. Қарапайым үй жарылады. Ал мына зәулім ғимарат тек тербеледі. Қалайша?"},
            {"scene": 2, "text": "Егер іргетасты қатырып құйса, соққы күші тікелей қабырғаға өтеді. Ғимарат өз салмағынан қирайды."},
            {"scene": 3, "text": "Құпия — жер астында. Үй қорғасын-резеңке тіректерде тұр. Олар бүйірге жылжып, соққының 70% өшіреді."},
            {"scene": 4, "text": "Тіректердің астында — терең қадалар. Олар тығыз жынысқа 30 метр кіріп, соққы толқынын таратады."},
            {"scene": 5, "text": "Ал ең төбесінде салмағы 700 тонна болат шар ілулі тұр. Ол қарсы бағытта тербеліп, ғимаратты теңестіреді."},
            {"scene": 6, "text": "Шар айналасында қуатты гидроцилиндрлер орнатылған. Қысымды май тербеліс күшін лезде жылуға айналдырады."},
            {"scene": 7, "text": "Қадалар, тіректер, маятник және демпферлер бір жүйедей жұмыс істейді. Бүкіл салмақ тең бөлінеді."},
            {"scene": 8, "text": "Графикке қараңыз: қорғаныссыз шатыр бір жарым метрге шайқалады. Қорғаныспен тербеліс жеті есеге кемиді."},
            {"scene": 9, "text": "Инженерлік физика бетон ішінде жасырылса — 35-қабатта да жайлы тыныштық сақталады."},
            {"scene": 10, "text": "Тұрғын үй кешенін салып, сенімділік сатасыз ба? Жасырын инженерияны 3D-да көрсетіңіз. Директке 3D жазыңыз!"},
        ],
    },
    "en": {
        "out_name": "B2B_05_CGI_SeismicTower_Shorts_EN.mp4",
        "pause_end": 0.14,
        "tts_fix": [
            ("30m", "thirty meters"),
            ("35th", "thirty-fifth"),
            ("3D", "three D"),
            ("DM 3D", "D M three D"),
        ],
        "hook": "MAGNITUDE 8 • WHY IT STANDS?",
        "split_top": "RIGID ANCHOR   |   BASE ISOLATED",
        "split_l": "SHEAR FRACTURE",
        "split_r": "ISOLATED CORE",
        "lrb_tag": "LEAD-RUBBER BASE ISOLATOR",
        "lrb_span": "<- 35 CM LATERAL SHEAR ->",
        "pile_badge": "DEEP BEDROCK PILES • -30 M DEPTH",
        "tmd_wm": "700 T",
        "tmd_sub": "COUNTER-PHASE PENDULUM • -40%",
        "hydro_tag": "KINETIC -> THERMAL",
        "hydro_val": "VISCOUS DAMPER",
        "stack_title": "4-LAYER SEISMIC SPINE",
        "stack_labels": ["30M PILES", "LRB PADS", "700T SPHERE"],
        "chart_kicker": "STRUCTURAL TELEMETRY • TOP FLOOR SWAY",
        "chart_title": "Lateral Drift at Magnitude 8.0",
        "chart_bad": "UNBRACED: +/- 1.4 M",
        "chart_good": "ISOLATED: +/- 0.2 M",
        "chart_stat": "7X CALMER ROOF",
        "calm_pill": "STILLNESS ON THE 35TH FLOOR",
        "cta_title": "3D CGI FOR DEVELOPERS",
        "cta_items": [
            "REELS & AD CREATIVES",
            "HIDDEN SAFETY IN 3D",
            "BUILD BUYER TRUST FAST",
        ],
        "cta_btn": "DM «3D» TO LAUNCH",
        "scenes": [
            {"scene": 1, "text": "A magnitude eight quake hits. Normal buildings crack. This skyscraper barely sways. Here is how."},
            {"scene": 2, "text": "Anchor concrete rigid to bedrock, and shockwaves shoot straight up the walls. Inertia tears it apart."},
            {"scene": 3, "text": "The secret hides below. Towers sit on lead-rubber bearings that shear sideways, cutting seventy percent of quake force."},
            {"scene": 4, "text": "Beneath those pads stand deep concrete piles anchored 30m into solid bedrock to scatter the wave."},
            {"scene": 5, "text": "High inside the crown hangs a seven-hundred-ton golden pendulum. It swings in reverse to cancel roof sway."},
            {"scene": 6, "text": "Giant hydraulic pistons surround the sphere, forcing thick fluid through valves to turn violence into heat."},
            {"scene": 7, "text": "Piles, isolators, pendulum, and dampers act as one living spine. No single joint carries the shock alone."},
            {"scene": 8, "text": "Look at the data: unbraced roofs whip over a meter wide. Seismic engineering cuts that sway nearly sevenfold."},
            {"scene": 9, "text": "When structural physics hides inside the concrete, the 35th floor stays remarkably still."},
            {"scene": 10, "text": "Building residential towers where trust sells? Turn hidden engineering into 3D CGI. DM 3D to launch!"},
        ],
    },
}


# ==============================================================================
#  FONT GLYPH VERIFICATION (PREVENT MISSING TOFU BOXES)
# ==============================================================================
def verify_all_texts():
    f_black = ImageFont.truetype(str(rmod.FONT), 48)
    f_bold = b4._font_bold(48)
    notdef_black = bytes(f_black.getmask("\uffff"))
    notdef_bold = bytes(f_bold.getmask("\uffff"))
    bad = []
    for lang, cfg in LANGS.items():
        fields = [
            cfg["hook"], cfg["split_top"], cfg["split_l"], cfg["split_r"],
            cfg["lrb_tag"], cfg["lrb_span"], cfg["pile_badge"], cfg["tmd_wm"],
            cfg["tmd_sub"], cfg["hydro_tag"], cfg["hydro_val"], cfg["stack_title"],
            *cfg["stack_labels"], cfg["chart_kicker"], cfg["chart_title"],
            cfg["chart_bad"], cfg["chart_good"], cfg["chart_stat"],
            cfg["calm_pill"], cfg["cta_title"], *cfg["cta_items"], cfg["cta_btn"],
            *(s["text"] for s in cfg["scenes"]),
        ]
        for txt in fields:
            for ch in txt:
                if ord(ch) <= 32:
                    continue
                if bytes(f_black.getmask(ch)) == notdef_black or bytes(f_bold.getmask(ch)) == notdef_bold:
                    bad.append((lang, ch, hex(ord(ch)), txt[:40]))
    if bad:
        raise RuntimeError(f"Unsupported glyph(s) detected: {bad}")
    print("✓ All RU/KZ/EN strings verified glyph-safe in Montserrat-Black & ExtraBold.")


def _compact_with_shifts(trimmed: np.ndarray, bounds: list[dict], t0_trim: float,
                         max_gap: float = 0.22, keep_gap: float = 0.12) -> tuple[np.ndarray, list[dict]]:
    if len(bounds) < 2:
        return trimmed, [dict(b) for b in bounds]
    adj = [dict(b) for b in bounds]
    cuts: list[tuple[int, int]] = []
    removed_s = 0.0
    for i in range(len(bounds) - 1):
        end_s = (bounds[i]["offset"] + bounds[i]["duration"]) - t0_trim
        start_nxt = bounds[i + 1]["offset"] - t0_trim
        gap = start_nxt - end_s
        if gap > max_gap:
            cut_s = gap - keep_gap
            s0 = int((end_s + keep_gap * 0.55) * SR)
            s1 = s0 + int(cut_s * SR)
            if 0 <= s0 < s1 < len(trimmed) - int(0.05 * SR):
                seg = trimmed[s0:s1]
                if float(np.sqrt(np.mean(seg ** 2))) < 0.018:
                    cuts.append((s0, s1))
                    removed_s += (s1 - s0) / SR
        adj[i + 1]["offset"] = bounds[i + 1]["offset"] - removed_s

    if not cuts:
        return trimmed, adj

    pieces = []
    pos = 0
    fade_n = int(0.008 * SR)
    for s0, s1 in cuts:
        if s0 > pos:
            part = trimmed[pos:s0].copy()
            if len(part) > fade_n:
                part[-fade_n:] *= np.linspace(1.0, 0.0, fade_n, dtype=np.float32)
            pieces.append(part)
        pos = s1
    if pos < len(trimmed):
        tail = trimmed[pos:].copy()
        if len(tail) > fade_n:
            tail[:fade_n] *= np.linspace(0.0, 1.0, fade_n, dtype=np.float32)
        pieces.append(tail)
    return np.concatenate(pieces), adj


# ==============================================================================
#  VOICE + FOLEY AUDIO PIPELINE (BROADCAST EQ + DEEP SIDECHAIN DUCKING)
# ==============================================================================
def synthesize_lang_audio(lang: str) -> tuple[Path, list[dict], list[dict], float]:
    cfg = LANGS[lang]
    voice_name, rate, pitch = VOICES[lang]
    bdir = BUILD_ROOT / lang
    tdir = bdir / "tts"
    bdir.mkdir(parents=True, exist_ok=True)
    tdir.mkdir(parents=True, exist_ok=True)

    segments = []
    words_all = []
    cursor = 0.0
    print(f"\n[{lang.upper()}] Synthesizing {voice_name} ({rate}) + Broadcast EQ...")

    for idx, sc in enumerate(cfg["scenes"]):
        mp3_path = tdir / f"s{idx:02d}.mp3"
        b_path = tdir / f"s{idx:02d}_bounds.json"
        wav_tmp = tdir / f"s{idx:02d}_eq.wav"
        raw_text = sc["text"]
        spoken = b1._prep_tts_text(raw_text, cfg["tts_fix"])

        if mp3_path.exists() and mp3_path.stat().st_size > 1000 and b_path.exists():
            bounds = json.loads(b_path.read_text(encoding="utf-8"))
        else:
            bounds = asyncio.run(b4._tts_one_clean(spoken, mp3_path, voice_name, rate, pitch))
            b_path.write_text(json.dumps(bounds, ensure_ascii=False), encoding="utf-8")
        wav_x = b4._decode_broadcast_voice_wav(mp3_path, wav_tmp)
        trimmed, t0_t, t1_t = b1._trim_silence(wav_x, head_pad=0.025, tail_pad=0.045)
        trimmed, bounds_adj = _compact_with_shifts(trimmed, bounds, t0_t, max_gap=0.22, keep_gap=0.11)
        t1_t = t0_t + len(trimmed) / SR
        seg_dur = len(trimmed) / SR

        ws = b1._align_words(raw_text, bounds_adj, t0_t, t1_t, seg_dur, cursor)
        words_all.extend(ws)

        segments.append({
            "idx": idx,
            "scene": sc["scene"],
            "t0": round(cursor, 4),
            "t1": round(cursor + seg_dur, 4),
            "dur": round(seg_dur, 4),
            "wav": str(tdir / f"s{idx:02d}_trim.npy"),
        })
        np.save(tdir / f"s{idx:02d}_trim.npy", trimmed)

        pause = PAUSES[idx] if idx < len(PAUSES) else 0.05
        cursor += seg_dur + pause

    total_dur = round(cursor + cfg["pause_end"], 3)
    N = int(total_dur * SR)

    voice_buf = np.zeros((N, 2), dtype=np.float32)
    for seg in segments:
        x = np.load(seg["wav"])
        s0 = int(seg["t0"] * SR)
        m = min(len(x), N - s0)
        if m > 0:
            voice_buf[s0:s0 + m, 0] += x[:m]
            voice_buf[s0:s0 + m, 1] += x[:m]

    # Ambient sub-room depth + halal engineering Foley SFX
    rng = np.random.default_rng(5005 + {"ru": 1, "kz": 2, "en": 3}[lang])
    pad = smod.vocal_pad(rng, total_dur, notes=(55.0, 82.41, 110.0), vowel="o", voices=4)
    pad = smod.lp(pad, 310.0, o=2)
    amb = np.column_stack([pad, pad]) * 0.020

    sfx_buf = np.zeros((N, 2), dtype=np.float32)

    def place(mono_or_st, t0: float, gain: float = 0.25, pan: float = 0.0):
        arr = mono_or_st if mono_or_st.ndim == 2 else smod.st(mono_or_st, pan)
        s0 = int(max(0.0, t0) * SR)
        m = min(len(arr), N - s0)
        if m > 0:
            sfx_buf[s0:s0 + m] += arr[:m] * gain

    t_of = lambda k: segments[k]["t0"]
    # S01: Tectonic rumble & fault strike
    place(smod.thunder(rng, min(3.4, segments[0]["dur"] + 0.4)), t_of(0), gain=0.28)
    place(smod.impact_boom(rng, 1.5), t_of(0) + 0.04, gain=0.34)
    # S02: Brittle fracture crack + split whoosh
    place(smod.whoosh(rng, 0.55), t_of(1), gain=0.18, pan=-0.3)
    place(smod.clasp(rng), t_of(1) + 0.45, gain=0.30, pan=-0.35)
    # S03: Rubber-steel lateral shear slide
    slide = smod.lp(smod.sword_draw(rng, 0.85), 1400.0, o=2)
    place(slide, t_of(2) + 0.05, gain=0.22)
    # S04: Deep subterranean pile resonance
    place(smod.impact_boom(rng, 1.8), t_of(3) + 0.04, gain=0.30)
    place(smod.thud(rng), t_of(3) + 0.55, gain=0.22)
    # S05: 700-ton pendulum heavy air sweep
    pend = smod.lp(smod.whoosh(rng, 1.15), 950.0, o=2)
    place(pend, t_of(4) + 0.05, gain=0.28)
    # S06: Flash click + pressurized hydraulic oil flow
    place(smod.clasp(rng), t_of(5), gain=0.24)
    oil = smod.bp(smod.water(rng, min(2.4, segments[5]["dur"])), 850.0, 3200.0, o=2)
    place(oil, t_of(5) + 0.08, gain=0.22)
    # S07: Three clean mechanical lock snaps
    place(smod.clasp(rng), t_of(6) + 0.08, gain=0.22, pan=-0.35)
    place(smod.clasp(rng), t_of(6) + 0.44, gain=0.22, pan=0.0)
    place(smod.clasp(rng), t_of(6) + 0.80, gain=0.24, pan=0.35)
    # S08: Editorial chart sweep + telemetry pulse
    place(smod.whoosh(rng, 0.50), t_of(7), gain=0.18)
    place(smod.clasp(rng), t_of(7) + 0.30, gain=0.18, pan=0.2)
    # S09: High-altitude calm alpine breeze
    breeze = smod.bp(rng.standard_normal(int(segments[8]["dur"] * SR)), 280.0, 1050.0, o=2)
    env_b = np.sin(np.linspace(0, np.pi, len(breeze), dtype=np.float32))
    place(breeze * env_b * 0.25, t_of(8), gain=0.16)
    # S10: Clean authoritative CTA transition + riser loop tail
    place(smod.impact_boom(rng, 1.4), t_of(9), gain=0.26)
    place(smod.riser(rng, min(1.2, segments[9]["dur"])), max(0.0, total_dur - 1.35), gain=0.14)

    # Strong sidechain ducking envelope (-15 dB under active voice)
    mono_v = np.abs(voice_buf[:, 0])
    win = int(0.055 * SR)
    kernel = np.ones(win, dtype=np.float32) / win
    env_v = np.convolve(mono_v, kernel, mode="same")
    env_norm = np.clip(env_v / (np.percentile(env_v, 95) + 1e-6), 0.0, 1.0)
    duck = 1.0 - 0.82 * env_norm

    mix_raw = voice_buf * 1.15 + (amb * 0.56 + sfx_buf * 0.36) * duck[:, None]
    mix_raw = smod.softclip(mix_raw, th=0.86)

    raw_wav = bdir / "mix_raw.wav"
    out_wav = bdir / "mix_final.wav"
    smod.write(raw_wav, mix_raw)
    b1.loudnorm_portable(raw_wav, out_wav, I=-14.0, TP=-1.5, LRA=9.0)

    (bdir / "timeline.json").write_text(json.dumps(segments, ensure_ascii=False, indent=2), encoding="utf-8")
    (bdir / "words.json").write_text(json.dumps(words_all, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[{lang.upper()}] Final mix ready: {total_dur:.2f}s | {len(words_all)} words")
    return out_wav, segments, words_all, total_dur


# ==============================================================================
#  PLATE LOADING + DIVERSE VISUAL WORLD HELPERS
# ==============================================================================
def _load_scene_plate(n: int) -> Image.Image:
    im = Image.open(SCENES_DIR / f"scene_{n:02d}.jpg").convert("RGB")
    if im.size != (W, H):
        im = im.resize((W, H), Image.Resampling.LANCZOS)
    return im


def _prepare_s03_shifted(plate03: Image.Image) -> Image.Image:
    """Shift scene_03 slightly upward edge-to-edge so bottom concrete clears SUB_Y=1500 cleanly."""
    bg = Image.new("RGB", (W, H), (10, 15, 23))
    nh = int(H * 0.96)
    scaled = plate03.resize((W, nh), Image.Resampling.LANCZOS)
    bg.paste(scaled, (0, -86))
    arr = np.asarray(bg, dtype=np.float32)
    y_idx = np.arange(H, dtype=np.float32)[:, None]
    fade = np.clip((y_idx - 1270.0) / 160.0, 0.0, 1.0)
    dark = np.array([10.0, 15.0, 23.0], dtype=np.float32)
    arr = arr * (1.0 - fade[..., None]) + dark * fade[..., None]
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def _zoom_crop(img: Image.Image, z: float, cx: float = 0.5, cy: float = 0.5, dx: int = 0, dy: int = 0) -> Image.Image:
    if abs(z - 1.0) < 1e-4 and dx == 0 and dy == 0:
        return img.copy()
    cw, ch = W / z, H / z
    x0 = max(0.0, min(W - cw, W * cx - cw * 0.5 + dx))
    y0 = max(0.0, min(H - ch, H * cy - ch * 0.5 + dy))
    return img.crop((x0, y0, x0 + cw, y0 + ch)).resize((W, H), Image.Resampling.BILINEAR)


def _rounded_rect(d: ImageDraw.ImageDraw, box, r: int, fill=None, outline=None, width: int = 2):
    d.rounded_rectangle(box, radius=r, fill=fill, outline=outline, width=width)


def _fit_box(d: ImageDraw.ImageDraw, text: str, max_w: float, size: int, min_size: int = 22):
    f, tw = b1.fit_font_text(d, text, max_w, size, min_size=min_size)
    bx0, by0, bx1, by1 = d.textbbox((0, 0), text, font=f)
    return f, bx1 - bx0, by1 - by0, bx0, by0


def _draw_pill(ov: Image.Image, text: str, cx: int, cy: int, size: int = 34,
               bg=(16, 26, 40, 220), fg=(255, 255, 255, 255),
               border=(110, 210, 255, 190), pad_x: int = 34, pad_y: int = 16,
               max_w: int = 940):
    d = ImageDraw.Draw(ov, "RGBA")
    f, tw, th, bx0, by0 = _fit_box(d, text, max_w - pad_x * 2, size, min_size=20)
    x0, y0 = int(cx - tw / 2 - pad_x), int(cy - th / 2 - pad_y)
    x1, y1 = int(cx + tw / 2 + pad_x), int(cy + th / 2 + pad_y)
    _rounded_rect(d, (x0, y0, x1, y1), r=(y1 - y0) // 2, fill=bg, outline=border, width=3)
    d.text((cx - tw / 2 - bx0, cy - th / 2 - by0), text, font=f, fill=fg)


def _apply_bottom_scrim(frame: Image.Image, scrim_lut: np.ndarray, strength: float = 0.88) -> Image.Image:
    arr = np.asarray(frame, dtype=np.float32)
    mult = 1.0 - (1.0 - scrim_lut) * strength
    arr *= mult
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def _ease_out(x: float) -> float:
    x = max(0.0, min(1.0, x))
    return 1.0 - (1.0 - x) ** 3


def _draw_crisp_ivory_chart(cfg: dict, lt: float, sdur: float) -> Image.Image:
    """Scene 08 signature anti-sameness frame: CRISP LIGHT IVORY editorial graph + slate sub-dock."""
    p = min(1.0, lt / max(0.4, sdur))
    reveal = _ease_out(min(1.0, lt / 0.85))
    pulse = 0.5 + 0.5 * math.sin(lt * 4.2)

    img = Image.new("RGB", (W, H), (245, 243, 238))  # Crisp Warm Ivory #F5F3EE
    d = ImageDraw.Draw(img, "RGBA")

    # Subtle architectural drafting grid on the bright ivory paper
    for gx in range(60, W, 90):
        d.line([(gx, 60), (gx, 1380)], fill=(224, 219, 209, 255), width=1)
    for gy in range(90, 1380, 90):
        d.line([(40, gy), (W - 40, gy)], fill=(224, 219, 209, 255), width=1)

    # Top kicker badge & bold dark editorial headline
    _draw_pill(
        img, cfg["chart_kicker"], W // 2, 148, size=27,
        bg=(23, 34, 51, 255), fg=(245, 220, 150, 255),
        border=(23, 34, 51, 255), pad_x=28, pad_y=12, max_w=920,
    )
    f_title, tw, th, bx0, by0 = _fit_box(d, cfg["chart_title"], 920, 48, min_size=28)
    d.text(((W - tw) // 2 - bx0, 224 - by0), cfg["chart_title"], font=f_title, fill=(22, 32, 46, 255))

    # Pure White elevated telemetry card
    cx0, cy0, cx1, cy1 = 68, 330, W - 68, 1315
    _rounded_rect(d, (cx0 + 6, cy0 + 10, cx1 + 6, cy1 + 10), r=34, fill=(212, 207, 196, 160))
    _rounded_rect(d, (cx0, cy0, cx1, cy1), r=34, fill=(255, 255, 255, 255), outline=(218, 214, 204, 255), width=3)

    # Top-right stat badge ("7X CALMER ROOF")
    if lt > 0.45:
        _draw_pill(
            img, cfg["chart_stat"], cx1 - 195, cy0 + 62, size=28,
            bg=(12, 139, 110, 255), fg=(255, 255, 255, 255),
            border=(12, 139, 110, 255), pad_x=24, pad_y=11, max_w=360,
        )

    # Upper panel: Unbraced violent sway (+/- 1.4m Crimson)
    ux0, ux1 = cx0 + 48, cx1 - 48
    uy_mid = 615
    d.line([(ux0, uy_mid), (ux1, uy_mid)], fill=(215, 215, 220, 255), width=2)
    f_lbl = b4._font_bold(30)
    d.text((ux0, cy0 + 46), cfg["chart_bad"], font=f_lbl, fill=(208, 45, 48, 255))

    pts_bad = []
    n_pts = 150
    draw_limit = int(n_pts * reveal)
    for i in range(max(2, draw_limit)):
        u = i / (n_pts - 1)
        x = ux0 + u * (ux1 - ux0)
        amp = 138.0 * (0.45 + 0.55 * math.sin(u * math.pi * 0.9))
        y = uy_mid + math.sin(u * 38.0 + lt * 5.0) * amp + math.cos(u * 19.0) * 28.0
        pts_bad.append((x, y))
    d.line(pts_bad, fill=(216, 48, 52, 255), width=8)
    d.ellipse((pts_bad[-1][0] - 11, pts_bad[-1][1] - 11, pts_bad[-1][0] + 11, pts_bad[-1][1] + 11),
              fill=(216, 48, 52, 255))

    # Divider line inside chart card
    d.line([(ux0, 815), (ux1, 815)], fill=(228, 226, 220, 255), width=3)

    # Lower panel: Base-Isolated + TMD calm wave (+/- 0.2m Emerald Teal)
    ly_mid = 1045
    d.line([(ux0, ly_mid), (ux1, ly_mid)], fill=(215, 215, 220, 255), width=2)
    d.text((ux0, 855), cfg["chart_good"], font=f_lbl, fill=(10, 128, 98, 255))

    pts_good = []
    for i in range(max(2, draw_limit)):
        u = i / (n_pts - 1)
        x = ux0 + u * (ux1 - ux0)
        env = math.exp(-u * 2.1)
        y = ly_mid + math.sin(u * 24.0 + lt * 3.0) * (26.0 * env + 5.0)
        pts_good.append((x, y))
    d.line(pts_good, fill=(12, 145, 112, 255), width=8)
    ex, ey = pts_good[-1]
    r_dot = int(10 + 4 * pulse)
    d.ellipse((ex - r_dot, ey - r_dot, ex + r_dot, ey + r_dot), fill=(12, 145, 112, 255))

    # Clean architectural Midnight Slate dock at bottom (y=1395..1920) so subtitles are 100% legible!
    d.rectangle((0, 1395, W, H), fill=(16, 24, 36, 255))
    d.line([(0, 1395), (W, 1395)], fill=(226, 182, 85, 255), width=5)
    return img


def _draw_cta_card(cfg: dict, lt: float, sdur: float, tower_thumb: Image.Image) -> Image.Image:
    """Scene 10: Architectural Navy-Slate & Ice-Gold B2B Developer Showcase Card."""
    p = min(1.0, lt / max(0.4, sdur))
    img = Image.new("RGB", (W, H), (14, 21, 32))
    d = ImageDraw.Draw(img, "RGBA")

    # Subtle architectural gradient wash from warm navy (#182538) to slate (#0C131D)
    y_norm = np.linspace(0.0, 1.0, H, dtype=np.float32)[:, None]
    grad = np.zeros((H, W, 3), dtype=np.float32)
    grad[..., 0] = 24.0 * (1.0 - y_norm) + 10.0 * y_norm
    grad[..., 1] = 36.0 * (1.0 - y_norm) + 15.0 * y_norm
    grad[..., 2] = 56.0 * (1.0 - y_norm) + 24.0 * y_norm
    img = Image.fromarray(grad.astype(np.uint8))
    d = ImageDraw.Draw(img, "RGBA")

    # Rounded preview window of golden-hour luxury towers at the top (y=120..580)
    card_w, card_h = 840, 440
    cx0, cy0 = (W - card_w) // 2, 125
    thumb = tower_thumb.crop((60, 250, W - 60, 1210)).resize((card_w, card_h), Image.Resampling.LANCZOS)
    mask = Image.new("L", (card_w, card_h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, card_w, card_h), radius=34, fill=255)
    img.paste(thumb, (cx0, cy0), mask)
    _rounded_rect(d, (cx0, cy0, cx0 + card_w, cy0 + card_h), r=34, outline=(245, 200, 108, 220), width=4)

    # Headline
    f_h, tw, _, bx0, by0 = _fit_box(d, cfg["cta_title"], 900, 46, min_size=28)
    d.text(((W - tw) // 2 - bx0, 620 - by0), cfg["cta_title"], font=f_h, fill=(246, 210, 130, 255))

    # 3 staggered vector checkmark pills
    for i, item in enumerate(cfg["cta_items"]):
        if lt < i * 0.22:
            continue
        alpha = int(255 * _ease_out(min(1.0, (lt - i * 0.22) / 0.25)))
        by = 735 + i * 116
        bx0_c, bx1_c = 120, W - 120
        _rounded_rect(d, (bx0_c, by, bx1_c, by + 92), r=24,
                      fill=(24, 36, 54, min(230, alpha)),
                      outline=(86, 190, 230, min(140, alpha)), width=2)
        b1.draw_vector_check(d, bx0_c + 52, by + 46, 20, (56, 232, 168, alpha))
        f_it, _, th_it, bx0_i, by0_i = _fit_box(d, item, 640, 31, min_size=22)
        d.text((bx0_c + 96 - bx0_i, by + 46 - th_it // 2 - by0_i), item, font=f_it, fill=(255, 255, 255, alpha))

    # Pulsing luminous Ice-Gold Developer CTA Pill (sits above SUB_Y=1500 cleanly!)
    pulse = 0.5 + 0.5 * math.sin(lt * 6.5)
    btn_bg = (242, int(192 + 24 * pulse), 86, 255)
    _draw_pill(
        img, cfg["cta_btn"], W // 2, 1215, size=44,
        bg=btn_bg, fg=(16, 23, 34, 255), border=(255, 240, 195, 255),
        pad_x=52, pad_y=26, max_w=920,
    )
    return img


# ==============================================================================
#  PER-FRAME RENDERER ACROSS ALL 10 DIVERSE WORLDS
# ==============================================================================
def make_frame_renderer(lang: str, plates: dict[int, Image.Image], segments: list[dict],
                        words_all: list[dict], dur: float, is_preview: bool = False):
    cfg = LANGS[lang]
    scrim = b4.bottom_scrim_lut()
    vig_f = (rmod.vignette().astype(np.float32) / 256.0)[..., None]
    chunks = rmod.chunks_from(words_all, dur)
    # Bridge tiny inter-sentence gaps (<0.38s) so subtitles stay continuous without blinking
    for ci in range(len(chunks) - 1):
        if chunks[ci + 1]["t0"] - chunks[ci]["t1"] < 0.38:
            chunks[ci]["t1"] = chunks[ci + 1]["t0"]
    plate03_clean = _prepare_s03_shifted(plates[3])

    def _find_seg(t: float) -> dict:
        for seg in segments:
            if seg["t0"] <= t <= seg["t1"] + 0.12:
                return seg
        return segments[-1]

    def _chunk_at(t: float):
        for ch in chunks:
            if ch["t0"] <= t <= ch["t1"]:
                return ch
        return None

    def render_at(t: float) -> Image.Image:
        seg = _find_seg(t)
        idx = seg["idx"]
        lt = max(0.0, t - seg["t0"])
        sdur = max(0.3, seg["dur"])
        p = min(1.0, lt / sdur)

        # ---- S01: Alpine Daylight Quake Hook ----
        if idx == 0:
            jitter_amp = 10.0 * max(0.0, 1.0 - lt / 1.15)
            dx = int(jitter_amp * math.sin(lt * 52.0))
            dy = int(jitter_amp * 0.6 * math.cos(lt * 43.0))
            frame = _zoom_crop(plates[1], 1.02 + 0.08 * p, 0.5, 0.48, dx=dx, dy=dy)
            _draw_pill(frame, cfg["hook"], W // 2, 175, size=36,
                       bg=(15, 24, 38, 225), fg=(255, 214, 110, 255),
                       border=(255, 170, 75, 220), max_w=940)
            frame = _apply_bottom_scrim(frame, scrim, 0.72)

        # ---- S02: Rigid vs Base-Isolated Split ----
        elif idx == 1:
            dx = int(5 * math.sin(lt * 40.0)) if lt < 1.8 else 0
            frame = _zoom_crop(plates[2], 1.01 + 0.05 * p, 0.5, 0.48, dx=dx // 2, dy=0)
            ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            d = ImageDraw.Draw(ov, "RGBA")
            # Animated vertical divider gleam + left fracture / right check badges
            d.line([(W // 2, 220), (W // 2, 1360)], fill=(120, 210, 255, 110), width=3)
            _draw_pill(ov, cfg["split_l"], 275, 315, size=27,
                       bg=(125, 24, 30, 225), fg=(255, 235, 235, 255),
                       border=(255, 95, 95, 230), pad_x=24, pad_y=12, max_w=430)
            _draw_pill(ov, cfg["split_r"], 805, 315, size=27,
                       bg=(12, 86, 66, 225), fg=(225, 255, 244, 255),
                       border=(72, 235, 170, 230), pad_x=24, pad_y=12, max_w=430)
            # Highlight right base-isolation chamber with subtle emerald focus bracket
            rp = (lt * 1.1) % 1.0
            rad_iso = int(85 + rp * 55)
            al_iso = int(190 * (1.0 - rp))
            d.ellipse((778 - rad_iso, 1385 - rad_iso // 2, 778 + rad_iso, 1385 + rad_iso // 2),
                      outline=(72, 240, 178, al_iso), width=4)
            frame = Image.alpha_composite(frame.convert("RGBA"), ov).convert("RGB")
            _draw_pill(frame, cfg["split_top"], W // 2, 168, size=28,
                       bg=(12, 18, 28, 220), fg=(220, 235, 250, 255),
                       border=(110, 200, 255, 180), max_w=930)
            frame = _apply_bottom_scrim(frame, scrim, 0.85)

        # ---- S03: Macro LRB Base Isolator + Shear Dimension Ruler ----
        elif idx == 2:
            shear_x = int(14 * math.sin(p * math.tau * 1.4))
            frame = _zoom_crop(plate03_clean, 1.02 + 0.06 * p, 0.5, 0.45, dx=shear_x, dy=0)
            ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            d = ImageDraw.Draw(ov, "RGBA")
            # Blueprint ruler dimension line beneath isolator at y=1320
            ry = 1320
            d.line([(210 + shear_x, ry), (870 + shear_x, ry)], fill=(86, 228, 255, 220), width=4)
            d.line([(210 + shear_x, ry - 18), (210 + shear_x, ry + 18)], fill=(86, 228, 255, 220), width=4)
            d.line([(870 + shear_x, ry - 18), (870 + shear_x, ry + 18)], fill=(86, 228, 255, 220), width=4)
            _draw_pill(ov, cfg["lrb_span"], 540 + shear_x, ry - 48, size=27,
                       bg=(10, 24, 38, 225), fg=(120, 242, 255, 255),
                       border=(86, 228, 255, 220), pad_x=24, pad_y=10, max_w=540)
            b1.draw_particles_studio(ov, t, seed=31, count=14)
            frame = Image.alpha_composite(frame.convert("RGBA"), ov).convert("RGB")
            _draw_pill(frame, cfg["lrb_tag"], W // 2, 168, size=32,
                       bg=(14, 22, 34, 220), fg=(255, 255, 255, 255),
                       border=(86, 228, 255, 200), max_w=920)
            frame = _apply_bottom_scrim(frame, scrim, 0.85)

        # ---- S04: Subterranean Piles Geological Cutaway ----
        elif idx == 3:
            frame = _zoom_crop(plates[4], 1.02 + 0.08 * p, 0.5, 0.54)
            ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            d = ImageDraw.Draw(ov, "RGBA")
            # Accurate depth scale along left edge aligned to ground surface (485) & pile tips (1185)
            d.line([(68, 485), (68, 1185)], fill=(96, 232, 255, 200), width=4)
            f_dep = b4._font_bold(24)
            for tag, yy in [("0M", 485), ("-15M", 835), ("-30M", 1185)]:
                d.line([(56, yy), (92, yy)], fill=(96, 232, 255, 230), width=3)
                d.text((102, yy - 13), tag, font=f_dep, fill=(175, 248, 255, 240))
            frame = Image.alpha_composite(frame.convert("RGBA"), ov).convert("RGB")
            _draw_pill(frame, cfg["pile_badge"], W // 2, 168, size=31,
                       bg=(14, 24, 38, 225), fg=(145, 248, 225, 255),
                       border=(82, 235, 205, 210), max_w=930)
            frame = _apply_bottom_scrim(frame, scrim, 0.84)

        # ---- S05: Bright Atrium 700T Golden Tuned Mass Damper ----
        elif idx == 4:
            sway_dx = int(18 * math.sin(p * math.tau * 1.1))
            frame = _zoom_crop(plates[5], 1.04 + 0.07 * p, 0.5, 0.48, dx=sway_dx // 2, dy=0)
            ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            d = ImageDraw.Draw(ov, "RGBA")
            # Giant transparent editorial watermark "700 Т" across upper glass atrium
            f_wm, wtw, _, bx0_w, _ = _fit_box(d, cfg["tmd_wm"], 860, 210, min_size=130)
            d.text(((W - wtw) // 2 + sway_dx // 3 - bx0_w, 215), cfg["tmd_wm"], font=f_wm, fill=(255, 226, 150, 54))
            # Counter-phase pendulum arc gauge cleanly below deck beam (y=1315)
            ax, ay, ar = W // 2, 1315, 115
            d.arc((ax - ar, ay - ar, ax + ar, ay + ar), start=25, end=155, fill=(255, 215, 120, 220), width=5)
            ang = math.radians(90 - 42 * math.sin(p * math.tau * 1.1))
            nx, ny = ax + int(ar * math.cos(ang)), ay + int(ar * math.sin(ang))
            d.line([(ax, ay), (nx, ny)], fill=(255, 215, 120, 140), width=3)
            d.ellipse((nx - 11, ny - 11, nx + 11, ny + 11), fill=(255, 210, 96, 255))
            b1.draw_particles_studio(ov, t, seed=55, count=16)
            frame = Image.alpha_composite(frame.convert("RGBA"), ov).convert("RGB")
            _draw_pill(frame, cfg["tmd_sub"], W // 2, 168, size=31,
                       bg=(16, 28, 44, 225), fg=(255, 224, 130, 255),
                       border=(255, 200, 95, 210), max_w=930)
            frame = _apply_bottom_scrim(frame, scrim, 0.82)

        # ---- S06: Hydraulic Viscous Piston Macro + Camera Flash Entry ----
        elif idx == 5:
            frame = _zoom_crop(plates[6], 1.03 + 0.09 * p, 0.52, 0.46)
            # Crisp 0.16s camera flash cut on entry
            if lt < 0.16:
                f_alpha = (1.0 - lt / 0.16) * 0.62
                arr = np.asarray(frame, dtype=np.float32)
                arr = arr * (1.0 - f_alpha) + np.array([225.0, 245.0, 255.0]) * f_alpha
                frame = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
            ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            d = ImageDraw.Draw(ov, "RGBA")
            # Laminar glowing amber oil particles streaming diagonally through piston
            for k in range(10):
                u = (lt * 0.9 + k * 0.10) % 1.0
                px = int(760 - u * 440 + math.sin(k * 2.3) * 28)
                py = int(420 + u * 540 + math.cos(k * 1.9) * 22)
                al = int(210 * math.sin(u * math.pi))
                d.ellipse((px - 7, py - 7, px + 7, py + 7), fill=(255, 198, 92, al))
            _draw_pill(ov, cfg["hydro_tag"], 540, 1295, size=30,
                       bg=(22, 18, 12, 225), fg=(255, 206, 108, 255),
                       border=(255, 175, 68, 220), pad_x=28, pad_y=12, max_w=640)
            frame = Image.alpha_composite(frame.convert("RGBA"), ov).convert("RGB")
            _draw_pill(frame, cfg["hydro_val"], W // 2, 168, size=34,
                       bg=(14, 22, 34, 220), fg=(120, 232, 255, 255),
                       border=(86, 210, 255, 210), max_w=900)
            frame = _apply_bottom_scrim(frame, scrim, 0.86)

        # ---- S07: 3-Strip Architectural Cross-Section Stack ----
        elif idx == 6:
            frame = Image.new("RGB", (W, H), (18, 29, 44))
            d = ImageDraw.Draw(frame, "RGBA")
            # Fine blueprint hairlines
            for gx in range(45, W, 90):
                d.line([(gx, 0), (gx, H)], fill=(34, 52, 76, 255), width=1)
            for gy in range(90, 1450, 90):
                d.line([(0, gy), (W, gy)], fill=(34, 52, 76, 255), width=1)
            strips = [
                (plates[4], (180, 320, 900, 1400), cfg["stack_labels"][0], 0.00),
                (plate03_clean, (150, 310, 930, 1340), cfg["stack_labels"][1], 0.36),
                (plates[5], (180, 260, 900, 1260), cfg["stack_labels"][2], 0.72),
            ]
            col_w, col_h = 304, 935
            gap = 24
            start_x = (W - (col_w * 3 + gap * 2)) // 2
            top_y = 275
            for k, (src_p, crop_box, lbl, t_on) in enumerate(strips):
                slide_p = _ease_out(min(1.0, max(0.0, (lt - t_on) / 0.35)))
                if slide_p <= 0.01:
                    continue
                bx = start_x + k * (col_w + gap)
                by = top_y + int((1.0 - slide_p) * 180)
                patch = src_p.crop(crop_box).resize((col_w, col_h), Image.Resampling.LANCZOS)
                msk = Image.new("L", (col_w, col_h), 0)
                ImageDraw.Draw(msk).rounded_rectangle((0, 0, col_w, col_h), radius=28, fill=255)
                frame.paste(patch, (bx, by), msk)
                active_col = (255, 206, 98, 240) if lt >= t_on + 0.1 else (105, 205, 245, 180)
                _rounded_rect(d, (bx, by, bx + col_w, by + col_h), r=28, outline=active_col, width=4)
                _draw_pill(frame, lbl, bx + col_w // 2, by + col_h - 54, size=24,
                           bg=(14, 22, 34, 235), fg=(255, 255, 255, 255),
                           border=active_col, pad_x=16, pad_y=10, max_w=col_w - 22)
            _draw_pill(frame, cfg["stack_title"], W // 2, 168, size=34,
                       bg=(14, 22, 34, 235), fg=(255, 218, 125, 255),
                       border=(255, 200, 95, 210), max_w=920)
            frame = _apply_bottom_scrim(frame, scrim, 0.82)

        # ---- S08: Crisp Light Ivory Editorial Sway Telemetry Chart ----
        elif idx == 7:
            frame = _draw_crisp_ivory_chart(cfg, lt, sdur)

        # ---- S09: Warm Golden-Hour Calm Panorama ----
        elif idx == 8:
            z = 1.09 - 0.08 * p
            frame = _zoom_crop(plates[7], z, 0.5, 0.48)
            _draw_pill(frame, cfg["calm_pill"], W // 2, 168, size=32,
                       bg=(24, 22, 20, 210), fg=(255, 226, 155, 255),
                       border=(245, 198, 112, 210), max_w=920)
            frame = _apply_bottom_scrim(frame, scrim, 0.78)

        # ---- S10: Architectural Developer Showcase & CTA ----
        else:
            frame = _draw_cta_card(cfg, lt, sdur, plates[7])

        # Apply subtle vignette on CGI scenes (keep light chart S08 & CTA S10 crisp) + karaoke subtitles
        if idx not in (7, 9):
            arr = np.asarray(frame, dtype=np.float32) * (1.0 - (1.0 - vig_f) * 0.60)
            frame = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
        ch = _chunk_at(t)
        if ch:
            act = max(0, sum(1 for w in ch["words"] if t >= w["t0"] - 0.01) - 1)
            sub_im = rmod.render_chunk(ch["words"], act)
            frame_rgba = frame.convert("RGBA")
            frame_rgba.alpha_composite(sub_im, ((W - sub_im.width) // 2, SUB_Y))
            return frame_rgba.convert("RGB")
        return frame

    return render_at


# ==============================================================================
#  PREVIEW QA & FULL MP4 RENDERER
# ==============================================================================
def run_preview():
    qa_dir = BUILD_ROOT / "qa"
    qa_dir.mkdir(parents=True, exist_ok=True)
    plates = {i: _load_scene_plate(i) for i in range(1, 8)}

    # Synthetic preview timing (~4s each) across RU, plus key spotlight scenes for KZ/EN
    for lang, idxs in [("ru", list(range(10))), ("kz", [0, 2, 6, 7, 9]), ("en", [0, 7, 9])]:
        cfg = LANGS[lang]
        fake_segs = []
        fake_words = []
        cur = 0.0
        for idx in idxs:
            sdur = 3.2
            txt = cfg["scenes"][idx]["text"]
            ws = txt.split()
            dt = sdur / max(1, len(ws))
            for k, w in enumerate(ws):
                fake_words.append({"w": w, "t0": cur + k * dt, "t1": cur + (k + 1) * dt})
            fake_segs.append({"idx": idx, "scene": idx + 1, "t0": cur, "t1": cur + sdur, "dur": sdur})
            cur += sdur + 0.08
        render_at = make_frame_renderer(lang, plates, fake_segs, fake_words, cur, is_preview=True)
        for seg in fake_segs:
            t_mid = seg["t0"] + 1.45
            out_p = qa_dir / f"pre_{lang}_s{seg['idx']:02d}.jpg"
            render_at(t_mid).save(out_p, quality=92)
            print(f"Saved preview frame: {out_p.name}")


def render_lang_video(lang: str, plates: dict[int, Image.Image]):
    cfg = LANGS[lang]
    bdir = BUILD_ROOT / lang
    wav_path, segments, words_all, dur = synthesize_lang_audio(lang)
    render_at = make_frame_renderer(lang, plates, segments, words_all, dur)

    silent_mp4 = bdir / "video_silent.mp4"
    final_mp4 = OUT_DIR / cfg["out_name"]
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    total_frames = int(math.ceil(dur * FPS))
    cmd_v = [
        FFMPEG, "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-c:v", "libx264", "-preset", "medium", "-crf", "17",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(silent_mp4),
    ]
    print(f"[{lang.upper()}] Rendering {total_frames} frames ({dur:.2f}s @ {FPS}fps)...")
    proc = subprocess.Popen(cmd_v, stdin=subprocess.PIPE)
    assert proc.stdin is not None
    try:
        for fi in range(total_frames):
            proc.stdin.write(render_at(fi / FPS).tobytes())
            if fi % 150 == 0 and fi > 0:
                print(f"  [{lang.upper()}] frame {fi}/{total_frames}")
    finally:
        proc.stdin.close()
        ret = proc.wait()
        if ret != 0:
            raise RuntimeError(f"FFmpeg silent render failed ({ret}) for {lang}")

    cmd_mux = [
        FFMPEG, "-y",
        "-i", str(silent_mp4), "-i", str(wav_path),
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-shortest", "-movflags", "+faststart", str(final_mp4),
    ]
    subprocess.run(cmd_mux, check=True)
    mb = final_mp4.stat().st_size / (1024 * 1024)
    print(f"✓ Built {final_mp4.name} ({dur:.2f}s, {mb:.2f} MB)")


def main():
    verify_all_texts()
    if "--preview" in sys.argv:
        run_preview()
        return
    plates = {i: _load_scene_plate(i) for i in range(1, 8)}
    target_langs = [a for a in sys.argv[1:] if a in VOICES] or ["ru", "kz", "en"]
    for lang in target_langs:
        render_lang_video(lang, plates)


if __name__ == "__main__":
    main()
