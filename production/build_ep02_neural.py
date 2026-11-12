"""Cinematic Tactical Explainer & Neural Voice Builder for Episode 2: Battle of Orbulak (1643).

Features:
1. Uses imageio-ffmpeg static binary automatically if system ffmpeg is not in PATH.
2. Rebuilds all 16 scene clips with strictly rigid camera motion (zero floating/jelly warp).
3. Uses live Neural TTS (edge-tts: ru-RU-DmitryNeural + kk-KZ-DauletNeural) with natural
   pacing, dramatic pauses, and authentic Kazakh terms woven into the Russian track.
4. Renders 1080x1920 30fps vertical video with cinematic tactical HUD overlays (canyon width,
   force ratio counters, animated tactical map & crossfire vectors) explaining HOW and WHY
   600 warriors defeated 50,000.
"""
import asyncio
import json
import math
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import edge_tts
import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy.io import wavfile

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
import make_ep02_clips

VIDEO_DIR = ROOT.parent / "scenes_ep02_video"
OUTPUT = ROOT.parent / "output"
SR = 48000

VOICE_FX = (
    "aresample=48000,highpass=f=65,"
    "equalizer=f=130:t=q:w=1.1:g=2.2,equalizer=f=3100:t=q:w=1.3:g=2.4,"
    "acompressor=threshold=0.14:ratio=2.4:attack=10:release=120:makeup=1.45"
)

# High-retention cinematic tactical explainer script with authentic Kazakh phrases in RU track
TACTICAL_SCRIPT = {
    "voices": {
        "ru": "kk-KZ-DauletNeural",
        "kz": "kk-KZ-DauletNeural",
        "en": "en-US-AndrewMultilingualNeural",
    },
    "scenes": [
        "scene_01", "scene_02", "scene_03", "scene_04",
        "scene_05", "scene_06", "scene_07", "scene_08",
        "scene_09", "scene_10", "scene_11", "scene_12",
        "scene_13", "scene_14", "scene_15", "scene_16",
    ],
    "hud": [
        {"tag": "ОРБҰЛАҚ ШАЙҚАСЫ • 1643", "stat": "600 САРБАЗОВ vs 50 000", "phase": 0},
        {"tag": "ФАКТОР №1: МАСШТАБ УГРОЗЫ", "stat": "ПЕРЕВЕС ВРАГА: 1 к 83", "phase": 0},
        {"tag": "ТАКТИКА САЛҚАМ ЖӘҢГІРА", "stat": "ОТКРЫТАЯ СТЕПЬ = ГИБЕЛЬ", "phase": 0},
        {"tag": "ФАКТОР №2: ОКОПЫ-ШАНЦЫ", "stat": "ФОРТИФИКАЦИЯ ЗА 1 НОЧЬ", "phase": 1},
        {"tag": "ДВУХЪЯРУСНАЯ ЗАСАДА", "stat": "300 В ОКОПАХ + 300 НА СКАЛАХ", "phase": 1},
        {"tag": "КАМЕННОЕ ГОРЛО (15–20 М)", "stat": "50 000 СЖАТЫ В УЗКУЮ КОЛОННУ", "phase": 1},
        {"tag": "ОГНЕВОЙ РУБЕЖ: БІЛТЕЛІ МЫЛТЫҚ", "stat": "ДИСТАНЦИЯ ЗАЛПА: В УПОР", "phase": 2},
        {"tag": "ФАКТОР №3: ОБВАЛ И ЗАЛП", "stat": "АВАНГАРД ОТСЕЧЁН КАМНЕПАДОМ", "phase": 2},
        {"tag": "СМЕННЫЕ ШЕРЕНГИ БЕЗ ПАУЗ", "stat": "1-Й РЯД БЬЁТ • 2-Й ЗАРЯЖАЕТ", "phase": 2},
        {"tag": "КАМЕННЫЙ МЕШОК ОРБУЛАКА", "stat": "ПОТЕРИ ВТОРЖЕНИЯ: -10 000", "phase": 2},
        {"tag": "ДЕНЬ 2: КРИТИЧЕСКИЙ МОМЕНТ", "stat": "БОЕЗАПАС НА ИСХОДЕ", "phase": 3},
        {"tag": "ГУЛ С ЗАПАДА: САМАРКАНД", "stat": "ЗЕМЛЯ ДРОЖИТ ПОД КОПЫТАМИ", "phase": 3},
        {"tag": "ФАКТОР №4: ЖАЛАҢТӨС БАҺАДҮР", "stat": "+20 000 ВСАДНИКОВ БРАТСКОЙ ПОМОЩИ", "phase": 3},
        {"tag": "УДАР В ТЫЛ И РАЗГРОМ", "stat": "КЛЕЩИ: ОКОПЫ + КОННИЦА", "phase": 3},
        {"tag": "ИТОГ: ТАКТИЧЕСКИЙ ГЕНИЙ", "stat": "РЕЛЬЕФ • ШАНЦЫ • ЕДИНСТВО", "phase": 4},
        {"tag": "ОРБҰЛАҚ — МИРОВАЯ ИСТОРИЯ", "stat": "600 ВЫСТОЯЛИ ПРОТИВ 50 000", "phase": 4},
    ],
    "ru": [
        "Как шестьсот казахских сарбазов смогли разгромить армию в пятьдесят тысяч человек? Вот четыре тактических секрета битвы [[kz:Орбұлақ шайқасы]]!",
        "Тысяча шестьсот сорок третий год. Пятидесятитысячное войско Эрдэни-Батура идёт на Великую Степь — [[kz:Ұлы Дала]], рассчитывая смять рубежи числом.",
        "У султана [[kz:Салқам Жәңгір]] всего шестьсот отборных бойцов — [[kz:жаужүрек сарбаздар]]. В открытом поле против пятидесяти тысяч шансов нет.",
        "Секрет первый — окопы-шанцы! За одну ночь в узком ущелье [[kz:Орбұлақ]] воины Жангира вручную вырубают глубокие траншеи и каменные стены.",
        "Секрет второй — двухъярусный капкан: триста бойцов намертво запирают выход из каньона, а триста стрелков — [[kz:мергендер]] — прячутся на отвесных скалах сверху!",
        "Враг втягивается в каменное горло шириной всего пятнадцать метров. Здесь многотысячная конница сжата в узкую колонну и теряет весь свой перевес!",
        "Жангир подпускает колонну вплотную. Тлеющий фитиль ружья — [[kz:білтелі мылтық]] — касается пороха...",
        "Огонь! Со скал обрушиваются тонны валунов, рассекая колонну пополам, а сверху бьёт шквал свинца!",
        "Секрет третий — непрерывный залп! Пока первая шеренга в окопах перезаряжает ружья, вторая встаёт и бьёт в упор без единой секунды паузы!",
        "Каменный капкан сработал идеально: захватчики теряют десять тысяч бойцов, но не могут пройти ни метра вперёд.",
        "На исходе вторых суток порох у шестисот батыров подходит к концу. Враг бросает в прорыв последние силы...",
        "Но вдруг камни на бруствере начинают дрожать от раскатистого гула с запада!",
        "Секрет четвёртый — [[kz:бауырластық серті]], братское единство! Из Самарканда на полном скаку примчался легендарный [[kz:Жалаңтөс Баһадүр]] с двадцатью тысячами всадников!",
        "Стальной клин [[kz:Жалаңтөс Баһадүр]] сходу врезается в тыл зажатой у каньона армии, завершая сокрушительный разгром!",
        "По милости Всевышнего, точный расчёт местности, инженерные шанцы и братское плечо сотворили военное чудо [[kz:Орбұлақ шайқасы]]!",
        "И враг до последней секунды не догадывался, в какую ловушку шагнул, когда...",
    ],
    "kz": [
        "Алты жүз қазақ сарбазы елу мыңдық қалың қолды қалай талқандады? Орбұлақ шайқасындағы жеңістің төрт әскери құпиясы мынадай!",
        "Мың алты жүз қырық үшінші жыл. Эрдэни-Батурдың елу мыңдық әскері Ұлы Дала шебін бір соққымен таптап өтпек болды.",
        "Салқам Жәңгір сұлтанның қолында небәрі алты жүз жаужүрек сарбаз бар еді. Ашық далада сансыз әскерге қарсы тұру мүмкін емес.",
        "Бірінші құпия — әскери инженерия! Бір түннің ішінде сарбаздар Орбұлақ шатқалында терең ор қазып, тастан берік бекініс соқты.",
        "Екінші құпия — қос қабатты торуыл: үш жүз батыр шатқалдың шығар аузын тас бекітті, ал үш жүз мерген құлама жардың үстіне жасырынды!",
        "Жау әскері ені он бес метрлік тар тас қапшыққа кіргенде, сандық басымдығынан толық айырылды!",
        "Жәңгір жауды дәл түбіне дейін жіберді. Білтелі мылтықтың шоғы оқ-дәріге тиді...",
        "Сол сәтте тау шайқалды! Жартастан құлаған ауыр тастар жау легін екіге бөліп, төбеден қорғасын жаңбыры жауды!",
        "Үшінші құпия — үздіксіз залп! Ордағы бірінші қатар мылтығын оқтағанша, екінші қатар тоқтаусыз оқ жаудырды!",
        "Тас қақпаннан өту мүмкін болмады: басқыншылар он мың сарбазынан айырылса да, бір қадам алға баса алмады.",
        "Екінші күннің соңында алты жүз батырдың оқ-дәрісі таусыла бастады. Жау соңғы күшін салды...",
        "Дәл сол сәтте батыс жақтан жер дүниені солқылдатқан қалың аттың дүбірі естілді!",
        "Төртінші құпия — бауырластық серті! Самарқаннан әйгілі Жалаңтөс Баһадүр жиырма мың атты әскерімен көмекке жетті!",
        "Жалаңтөс Баһадүрдің темірдей жұдырығы шатқал аузында тығырыққа тірелген жаудың ту сыртынан соғып, тас-талқанын шығарды!",
        "Жаратқанның қолдауымен, жер бедерін дәл таңдау, тас ор мен бауырластық бірлік әлемдік тарихтағы ұлы жеңіске жеткізді!",
        "Ал басқыншылар соңғы сәтке дейін қандай қақпанға түскенін сезбеді де, өйткені...",
    ],
    "en": [
        "How did six hundred Kazakh warriors defeat a fifty-thousand-strong army? Here are the four tactical secrets of the Battle of Orbulak!",
        "The year is sixteen forty-three. Erdeni Batur leads fifty thousand horsemen into the Great Steppe, expecting an effortless victory.",
        "Sultan Salkam Zhangir commands only six hundred elite warriors. In the open steppe, facing fifty thousand is certain death.",
        "Secret number one — battlefield engineering! Overnight inside the narrow Orbulak gorge, Zhangir's men dig deep fortified stone trenches.",
        "Secret number two — a two-tier ambush: three hundred fighters seal the canyon exit, while three hundred sharpshooters hide high on the sheer cliffs!",
        "As the invading army pours into the fifteen-meter stone bottleneck, their massive numerical advantage completely vanishes!",
        "Zhangir holds his fire until point-blank range. A glowing matchlock fuse touches the black powder...",
        "Fire! Tons of boulders crash down from the cliffs, severing the column in two under a hailstorm of lead!",
        "Secret number three — rotating volleys! While the first trench rank kneels to reload, the second rank fires continuously without a single pause!",
        "The stone trap holds firm: the invaders lose ten thousand men without advancing a single step.",
        "By the end of day two, the six hundred defenders run low on powder. The enemy throws in their final reserves...",
        "Suddenly, the stones underfoot begin to tremble from a thunderous roar in the west!",
        "Secret number four — the code of brotherhood! Legendary commander Zhalantos Bahadur arrives at full gallop from Samarkand with twenty thousand fresh cavalry!",
        "Zhalantos Bahadur's iron wedge slams straight into the rear of the trapped invasion army, shattering their forces completely!",
        "By the grace of the Almighty, terrain mastery, trench warfare, and brotherhood forged a masterpiece of world military history!",
        "And the invaders never realized what trap they had stepped into until the very last second, because...",
    ],
}


VOWELS = set("аеёиоуыэюяәіңғүұқөһaeiouy")


def count_syllables(word: str) -> int:
    return max(1, sum(1 for ch in word.lower() if ch in VOWELS))


async def synth_scene_edge(line: str, voice_name: str, out_dir: Path, si: int):
    clean_text = re.sub(r"\[\[kz:(.*?)\]\]", r"\1", line).strip()
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


async def build_neural_voice_async(lang: str):
    out = ROOT / "build_ep02" / lang
    out.mkdir(parents=True, exist_ok=True)
    voice_name = TACTICAL_SCRIPT["voices"][lang]
    lines = TACTICAL_SCRIPT[lang]

    pieces = []
    all_words = []
    cur_t = 0.0
    gap = 0.22

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
            "images": [TACTICAL_SCRIPT["scenes"][si]],
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
    print(f"[neural-voice-{lang}] {len(lines)} scenes, total={T:.2f}s ({voice_name})")


def draw_tactical_hud(im: Image.Image, scene_idx: int, tau: float, seg_dur: float):
    """Draw cinematic tactical HUD overlay (top callout + mini tactical canyon radar) onto 1080x1920 frame."""
    hud_info = TACTICAL_SCRIPT["hud"][min(scene_idx, len(TACTICAL_SCRIPT["hud"]) - 1)]
    phase = hud_info["phase"]
    u = min(1.0, max(0.0, tau / max(0.1, seg_dur)))

    ov = Image.new("RGBA", (rmod.W, rmod.H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)

    f_tag = rmod.font(30)
    f_stat = rmod.font(38)
    f_map = rmod.font(24)

    # 1. Top Tactical HUD Banner (y = 95..235)
    bx0, by0, bx1, by1 = 64, 92, rmod.W - 64, 232
    d.rounded_rectangle([bx0, by0, bx1, by1], radius=18, fill=(8, 14, 26, 205), outline=(56, 189, 248, 180), width=3)
    # Corner accents
    d.line([(bx0, by0 + 28), (bx0, by0), (bx0 + 28, by0)], fill=(250, 204, 21, 255), width=5)
    d.line([(bx1 - 28, by1), (bx1, by1), (bx1, by1 - 28)], fill=(250, 204, 21, 255), width=5)

    d.text((bx0 + 28, by0 + 18), f"▸ {hud_info['tag']}", font=f_tag, fill=(56, 189, 248, 255))
    d.text((bx0 + 28, by0 + 64), hud_info["stat"], font=f_stat, fill=(250, 204, 21, 255))

    # 2. Tactical Canyon Radar Overlay (bottom-right above subtitles: y = 1420..1690)
    mx0, my0, mx1, my1 = 84, 1430, rmod.W - 84, 1680
    d.rounded_rectangle([mx0, my0, mx1, my1], radius=16, fill=(8, 13, 24, 195), outline=(148, 163, 184, 120), width=2)
    d.text((mx0 + 22, my0 + 12), "ТАКТИЧЕСКАЯ СХЕМА УЩЕЛЬЯ ОРБУЛАК", font=f_map, fill=(148, 163, 184, 230))

    # Serpentine canyon walls inside radar box
    pts_top, pts_bot = [], []
    for x in range(mx0 + 30, mx1 - 30, 14):
        rel = (x - (mx0 + 30)) / max(1, (mx1 - mx0 - 60))
        cy = (my0 + 145) + math.sin(rel * 5.2 - 0.5) * 28
        pts_top.append((x, cy - 28))
        pts_bot.append((x, cy + 28))
    d.line(pts_top, fill=(148, 163, 184, 200), width=4)
    d.line(pts_bot, fill=(148, 163, 184, 200), width=4)

    # Trench barricade on East (right side)
    tx = mx1 - 145
    ty = (my0 + 145) + math.sin(0.84 * 5.2 - 0.5) * 28
    if phase >= 1:
        d.line([(tx, ty - 34), (tx - 10, ty), (tx, ty + 34)], fill=(250, 204, 21, 255), width=7)
        # 300 cliff sharpshooters (cyan dots along ridges)
        for cx in range(mx0 + 260, tx - 20, 45):
            rel = (cx - (mx0 + 30)) / max(1, (mx1 - mx0 - 60))
            ccy = (my0 + 145) + math.sin(rel * 5.2 - 0.5) * 28
            d.ellipse([cx - 6, ccy - 44, cx + 6, ccy - 32], fill=(56, 189, 248, 255))
            d.ellipse([cx - 6, ccy + 32, cx + 6, ccy + 44], fill=(56, 189, 248, 255))
            if phase == 2:
                # Crossfire lines into gorge
                d.line([(cx, ccy - 32), (cx + 8, ccy - 4)], fill=(250, 204, 21, 220), width=3)
                d.line([(cx, ccy + 32), (cx - 8, ccy + 4)], fill=(250, 204, 21, 220), width=3)

    # Invading red column inside canyon
    col_end = int((mx0 + 120) + (tx - mx0 - 150) * (u if scene_idx == 0 else (0.75 if phase >= 3 else 0.92)))
    for cx in range(mx0 + 70, col_end, 26):
        rel = (cx - (mx0 + 30)) / max(1, (mx1 - mx0 - 60))
        ccy = (my0 + 145) + math.sin(rel * 5.2 - 0.5) * 28
        col_fill = (249, 115, 22, 230) if phase >= 2 and cx > mx0 + 240 else (239, 68, 68, 235)
        d.ellipse([cx - 7, ccy - 12, cx + 7, ccy + 2], fill=col_fill)
        d.ellipse([cx - 11, ccy + 2, cx + 3, ccy + 16], fill=col_fill)

    # Phase 3+: Zhalantos Bahadur green cavalry wedge striking from West (left)
    if phase >= 3:
        jx = mx0 + 45 + int(95 * (u if phase == 3 else 1.0))
        jy = my0 + 145
        d.polygon([(jx + 28, jy), (jx - 18, jy - 28), (jx - 6, jy), (jx - 18, jy + 28)], fill=(34, 197, 94, 255))

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


def render_tactical_video(lang: str):
    B = ROOT / "build_ep02" / lang
    tl = json.loads((B / "timeline.json").read_text(encoding="utf-8"))
    words = json.loads((B / "words.json").read_text(encoding="utf-8"))
    T = tl["T"]
    segs, chunks = rmod.segments(tl), rmod.chunks_from(words, T)
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
        if name in ("scene_08", "scene_14") and tau < 0.35:
            arr = arr + ((255 - arr) * (0.85 * math.exp(-tau / 0.08))).astype(np.uint16)
        im = Image.fromarray(arr.astype(np.uint8)).convert("RGBA")

        # Tactical HUD overlay
        draw_tactical_hud(im, si, tau, seg_dur)

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
    out = OUTPUT / f"EP02_Orbulak_Shorts_{lang.upper()}.mp4"
    subprocess.run(
        [
            FFMPEG_BIN, "-y", "-hide_banner", "-loglevel", "error", "-i", str(vid_path),
            "-i", str(B / "mix.wav"), "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac",
            "-b:a", "192k", "-ar", "48000", "-shortest", "-movflags", "+faststart", str(out),
        ],
        check=True,
    )
    print(f"[done] {out} ({out.stat().st_size // (1024 * 1024)} MB)")


def musket_shot(rng):
    d = 1.4
    t = smod.tt(d)
    crack = smod.norm(smod.bp(smod.white(rng, d), 800, 5500)) * smod.expenv(d, 0.018, 0.001)
    punch = smod.norm(smod.lp(smod.white(rng, d), 320)) * smod.expenv(d, 0.08, 0.002)
    boom = np.sin(2 * np.pi * np.cumsum(45 + 90 * np.exp(-t / 0.06)) / SR) * smod.expenv(d, 0.16, 0.002)
    tail = smod.norm(smod.lp(smod.brown(rng, d), 450)) * smod.expenv(d, 0.45, 0.02)
    return smod.norm(crack * 0.9 + punch * 0.8 + boom * 0.7 + tail * 0.5)


def musket_volley(rng, d, count=28):
    out = np.zeros(smod.n_(d) + smod.n_(1.8))
    shots = [musket_shot(rng) for _ in range(8)]
    for i in range(count):
        ti = rng.uniform(0.0, min(0.45, d * 0.4)) if i < count // 2 else rng.uniform(0.0, max(0.2, d - 0.3))
        smod.add(out, shots[rng.integers(len(shots))] * rng.uniform(0.4, 1.0), ti)
    return smod.norm(out[:smod.n_(d) + smod.n_(1.0)])


def rockslide(rng, d):
    rumble = smod.norm(smod.lp(smod.brown(rng, d), 190, 3)) * (0.5 + 0.5 * smod.smooth(rng, d, 7))
    out = rumble * 0.8
    for _ in range(int(14 * d)):
        ti = rng.uniform(0, max(0.1, d - 0.4))
        hd = 0.35
        ht = smod.tt(hd)
        boulder = (
            np.sin(2 * np.pi * np.cumsum(55 + 80 * np.exp(-ht / 0.04)) / SR) * smod.expenv(hd, 0.09)
            + 0.6 * smod.norm(smod.bp(smod.white(rng, hd), 250, 2200)) * smod.expenv(hd, 0.04)
        )
        smod.add(out, boulder * rng.uniform(0.3, 0.9), ti)
    return smod.norm(out)


def ep02_scene_sfx(k, d, rng):
    N = smod.n_(d)
    out = np.zeros((N + smod.n_(3.5), 2))

    def put(x, t0=0.0, g=1.0, pan=0.0, rev=None):
        if t0 >= d:
            return
        s = smod.reverb(x, *rev) if rev else (smod.st(x, pan) if x.ndim == 1 else x)
        i = smod.n_(t0) if t0 > 0 else 0
        m = min(len(s), len(out) - i)
        out[i:i + m] += s[:m] * g

    def bed(fn, g=0.4, **kw):
        a = smod.fade(smod.fit(fn(rng, d, **kw), N), 0.03, 0.12)
        b = smod.fade(smod.fit(fn(rng, d, **kw), N), 0.03, 0.12)
        put(np.stack([0.75 * a + 0.25 * b, 0.25 * a + 0.75 * b], 1), 0.0, g)

    if k == 1:
        put(smod.impact_boom(rng, 2.2), 0.0, 0.85, rev=(2.2, 0.35))
        bed(smod.wind, 0.45, howl=0.6)
        bed(smod.march, 0.50)
    elif k == 2:
        bed(smod.herd_far, 0.65)
        bed(smod.wind, 0.35)
        put(smod.vocal_pad(rng, d + 0.6, [55.0, 82.4, 110.0], "o"), 0, 0.35, rev=(2.8, 0.4))
    elif k == 3:
        bed(smod.wind, 0.55, howl=0.7)
        put(smod.jingle(rng, d), 0, 0.35)
    elif k == 4:
        bed(smod.wind, 0.30)
        for p in np.arange(0.15, d - 0.2, 0.55):
            put(smod.anvil(rng), float(p), 0.55, pan=rng.uniform(-0.4, 0.4), rev=(1.4, 0.25))
        put(rockslide(rng, d), 0, 0.40)
    elif k == 5:
        bed(smod.wind, 0.40, howl=0.4)
        put(smod.jingle(rng, d), 0, 0.40)
    elif k == 6:
        bed(smod.herd, 0.65)
        put(smod.wheels(rng, d), 0, 0.35)
    elif k == 7:
        active_d = max(0.4, d - 0.35)
        put(smod.sizzle(rng, active_d), 0, 0.45)
        put(smod.fire(rng, active_d), 0, 0.40)
    elif k == 8:
        put(smod.impact_boom(rng, 2.0), 0.0, 0.90, rev=(2.4, 0.35))
        put(musket_volley(rng, d, count=32), 0.02, 0.85, rev=(2.2, 0.38))
        put(rockslide(rng, d), 0.10, 0.75, rev=(1.8, 0.3))
    elif k == 9:
        put(musket_volley(rng, d, count=26), 0.0, 0.75, rev=(2.0, 0.35))
        bed(smod.wind, 0.25)
    elif k == 10:
        bed(smod.fire, 0.45)
        bed(smod.wind, 0.35, howl=0.5)
        put(smod.vocal_pad(rng, d + 0.8, [65.4, 98.0, 130.8], "u"), 0, 0.42, rev=(2.8, 0.4))
    elif k == 11:
        bed(smod.wind, 0.45, howl=0.6)
        bed(smod.march, 0.55)
    elif k == 12:
        t = smod.tt(d)
        tremor = smod.norm(smod.lp(smod.brown(rng, d), 95, 4)) * ((t / d) ** 1.3)
        put(tremor, 0, 0.85)
        bed(smod.herd_far, 0.65)
    elif k == 13:
        bed(smod.herd, 0.85)
        put(smod.vocal_pad(rng, d + 1.0, [73.4, 110.0, 146.8, 220.0], "a", voices=5), 0, 0.55, rev=(3.2, 0.4))
    elif k == 14:
        put(smod.impact_boom(rng, 2.0), 0.0, 0.80, rev=(2.0, 0.3))
        bed(smod.herd, 0.80)
        put(smod.sword_clash(rng), 0.25, 0.70, pan=-0.3, rev=(1.5, 0.25))
        put(smod.sword_clash(rng), min(1.1, d * 0.5), 0.70, pan=0.3, rev=(1.5, 0.25))
    elif k == 15:
        bed(smod.wind, 0.40, howl=0.3)
        put(smod.eagle(rng), min(0.8, d * 0.3), 0.48, rev=(2.8, 0.4))
        put(smod.vocal_pad(rng, d + 0.8, [65.4, 98.0, 130.8, 196.0], "o", voices=5), 0, 0.45, rev=(3.2, 0.4))
    elif k == 16:
        put(smod.sword_draw(rng, d), 0, 0.75)
        put(smod.sizzle(rng, d), 0, 0.35)
    return out


def run_sfx(lang: str):
    B = ROOT / "build_ep02" / lang
    tl = json.loads((B / "timeline.json").read_text(encoding="utf-8"))
    T = tl["T"]
    N = smod.n_(T)
    rng = np.random.default_rng(1643)

    sfx = np.zeros((N + smod.n_(4.0), 2))
    for sc in tl["scenes"]:
        s = ep02_scene_sfx(sc["id"], sc["t1"] - sc["t0"], rng)
        i = smod.n_(sc["t0"]) if sc["t0"] > 0 else 0
        m = min(len(s), len(sfx) - i)
        sfx[i:i + m] += s[:m]
    sfx = sfx[:N]

    amb = np.stack([smod.fit(smod.wind(rng, T, 0.3), N), smod.fit(smod.wind(rng, T, 0.3), N)], 1)
    g = np.ones(N)
    s7 = tl["scenes"][6]
    g[smod.n_(max(0, s7["t1"] - 0.4)):smod.n_(s7["t1"])] = 0.08
    sfx += amb * 0.09 * g[:, None]
    smod.write(B / "sfx.wav", smod.norm(sfx, 0.9))

    sr, v = wavfile.read(B / "voice.wav")
    v = smod.fit(v.astype(np.float64) / 32768.0, N)
    vr = smod.frame_rms(v)
    v_level = np.mean(vr[vr > np.max(vr) * 0.05])
    sfx *= (v_level * 0.26) / np.mean(smod.frame_rms(sfx.mean(1)))

    env = smod.lp(np.abs(v), 6, 2)
    env /= np.percentile(env, 95) + 1e-9
    duck = 1 - 0.62 * np.clip(env, 0, 1)
    out = smod.reverb(v, 0.32, 0.025, seed=3)[:N] + sfx * duck[:, None]
    out *= 0.85 / np.percentile(np.abs(out), 99.95)
    smod.write(B / "mix_premaster.wav", smod.softclip(out))
    smod.loudnorm(B / "mix_premaster.wav", B / "mix.wav")
    print(f"[ep02-{lang}] mix ready: {T:.2f}s → {B / 'mix.wav'}")


def main():
    langs = [a for a in sys.argv[1:] if not a.startswith("--")] or ["ru"]
    force_clips = "--rebuild-clips" in sys.argv
    clips_exist = all((VIDEO_DIR / f"scene_{k:02d}.mp4").exists() for k in range(1, 17))
    if force_clips or not clips_exist:
        print("[1/4] Rebuilding rigid scene clips (zero floating/jelly warp)...")
        make_ep02_clips.build_all()
    else:
        print("[1/4] All 16 rigid scene clips already present in scenes_ep02_video/ (skipping clip rebuild).")
    for lang in langs:
        print(f"[2/4] Synthesizing live neural voiceover ({lang})...")
        asyncio.run(build_neural_voice_async(lang))
        print(f"[3/4] Mixing Orbulak canyon SFX + A cappella ({lang})...")
        run_sfx(lang)
        print(f"[4/4] Rendering 1080x1920 tactical explainer video ({lang})...")
        render_tactical_video(lang)


if __name__ == "__main__":
    main()
