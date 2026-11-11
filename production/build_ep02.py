"""Complete production pipeline for Episode 2: Battle of Orbulak (1643) — 600 vs 50,000.

1. Synthesizes slow, crystal-clear male narration (RU, KZ, EN) with natural pauses.
2. Generates custom Orbulak canyon sound design (trench digging, fuse sizzle, 0.5s silence drop,
   600-musket volley with canyon echo, rockslide avalanche, seismic tremor, 20,000-horse charge,
   and male A cappella choir — strictly zero musical instruments).
3. Ensures all 16 scenes in scenes_ep02_video/ are animated and renders 1080x1920 30fps MP4s.
"""
import json
import math
import os
import re
import subprocess
import sys
from multiprocessing import Process
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy.io import wavfile

import voice as vmod
import sfx as smod
import render as rmod

ROOT = Path(__file__).resolve().parent
DATA = json.loads((ROOT / "narration_shorts_ep02.json").read_text(encoding="utf-8"))
VIDEO_DIR = ROOT.parent / "scenes_ep02_video"
OUTPUT = ROOT.parent / "output"
SR = 48000


def run_voice(lang: str):
    out = ROOT / "build_ep02" / lang
    out.mkdir(parents=True, exist_ok=True)
    voice, sid = vmod.load_voice(lang)
    sr = voice.config.sample_rate

    toks = []
    for si, line in enumerate(DATA[lang]):
        for raw in line.split():
            if not re.search(r"\w", raw):
                if toks:
                    toks[-1]["pause"] = 1
                    toks[-1]["tts"] += " " + raw
                continue
            toks.append({"w": raw, "tts": raw, "scene": si, "pause": 1 if vmod.PAUSE_RE.search(raw) else 0})

    sents = vmod.sentences(toks)
    ns = len(sents)
    L = vmod.TARGET_SCALE.get(lang, 1.06)

    tts_fix = {"en": [("1643", "sixteen forty-three")]}
    cfg = vmod.SynthesisConfig(speaker_id=sid, length_scale=L)
    clips = []
    for s in sents:
        text = " ".join(t["tts"] for t in s)
        for a, b in tts_fix.get(lang, []):
            text = text.replace(a, b)
        a = np.concatenate([c.audio_float_array for c in voice.synthesize(text, syn_config=cfg)])
        clips.append(vmod.trim(a.astype(np.float32), sr))

    gap = vmod.GAP0
    audio, words, T = vmod.assemble(clips, sents, sr, gap, lang)
    print(f"[ep02-{lang}] sentences={ns} length_scale={L:.3f} gap={gap:.3f}s total={T:.2f}s")

    starts = []
    for si in range(len(DATA["scenes"])):
        ws = [w for w in words if w["scene"] == si]
        starts.append(max(0.0, ws[0]["t0"] - 0.08))
    starts[0] = 0.0
    scenes = [
        {
            "id": si + 1,
            "images": DATA["scenes"][si].split("|"),
            "t0": round(starts[si], 3),
            "t1": round(starts[si + 1] if si + 1 < len(starts) else T, 3),
        }
        for si in range(len(starts))
    ]

    wavfile.write(out / "voice_raw.wav", sr, (np.clip(audio, -1, 1) * 32767).astype(np.int16))
    subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(out / "voice_raw.wav"),
         "-af", vmod.VOICE_FX, "-ar", "48000", "-ac", "1", str(out / "voice.wav")],
        check=True,
    )
    subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(out / "voice.wav"),
         "-b:a", "128k", str(out / "voice_raw.mp3")],
        check=True,
    )
    (out / "words.json").write_text(json.dumps(words, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / "timeline.json").write_text(
        json.dumps({"lang": lang, "T": round(T, 3), "length_scale": L, "gap": gap, "scenes": scenes},
                   ensure_ascii=False, indent=1),
        encoding="utf-8",
    )


def musket_shot(rng):
    """Single black-powder matchlock musket crack + canyon echo."""
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
    t = smod.tt(d)
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

    if k == 1:      # Hook: 600 warriors in stone trench, 50,000 marching in gorge
        put(smod.impact_boom(rng, 2.2), 0.0, 0.85, rev=(2.2, 0.35))
        bed(smod.wind, 0.45, howl=0.6)
        bed(smod.march, 0.50)
    elif k == 2:    # 1643 Erdeni Batur invasion army
        bed(smod.herd_far, 0.65)
        bed(smod.wind, 0.35)
        put(smod.vocal_pad(rng, d + 0.6, [55.0, 82.4, 110.0], "o"), 0, 0.35, rev=(2.8, 0.4))
    elif k == 3:    # Salkam Zhangir on cliff
        bed(smod.wind, 0.55, howl=0.7)
        put(smod.jingle(rng, d), 0, 0.35)
    elif k == 4:    # Digging trenches (shantsy) at night
        bed(smod.wind, 0.30)
        for p in np.arange(0.15, d - 0.2, 0.55):
            put(smod.anvil(rng), float(p), 0.55, pan=rng.uniform(-0.4, 0.4), rev=(1.4, 0.25))
        put(rockslide(rng, d), 0, 0.40)
    elif k == 5:    # 300 blocking exit, 300 on cliffs
        bed(smod.wind, 0.40, howl=0.4)
        put(smod.jingle(rng, d), 0, 0.40)
    elif k == 6:    # Enemy column pouring into narrow stone bottleneck
        bed(smod.herd, 0.65)
        put(smod.wheels(rng, d), 0, 0.35)
    elif k == 7:    # Glowing fuse touches black powder + dramatic silence drop at end!
        active_d = max(0.4, d - 0.35)
        put(smod.sizzle(rng, active_d), 0, 0.45)
        put(smod.fire(rng, active_d), 0, 0.40)
    elif k == 8:    # FIRE! Volley of muskets + rockslide avalanche!
        put(smod.impact_boom(rng, 2.0), 0.0, 0.90, rev=(2.4, 0.35))
        put(musket_volley(rng, d, count=32), 0.02, 0.85, rev=(2.2, 0.38))
        put(rockslide(rng, d), 0.10, 0.75, rev=(1.8, 0.3))
    elif k == 9:    # Rotating ranks continuous volley fire
        put(musket_volley(rng, d, count=26), 0.0, 0.75, rev=(2.0, 0.35))
        bed(smod.wind, 0.25)
    elif k == 10:   # Impenetrable stone trap, 10,000 lost
        bed(smod.fire, 0.45)
        bed(smod.wind, 0.35, howl=0.5)
        put(smod.vocal_pad(rng, d + 0.8, [65.4, 98.0, 130.8], "u"), 0, 0.42, rev=(2.8, 0.4))
    elif k == 11:   # Running out of powder on day 2
        bed(smod.wind, 0.45, howl=0.6)
        bed(smod.march, 0.55)
    elif k == 12:   # Stones trembling from seismic roar in the west!
        t = smod.tt(d)
        tremor = smod.norm(smod.lp(smod.brown(rng, d), 95, 4)) * ((t / d) ** 1.3)
        put(tremor, 0, 0.85)
        bed(smod.herd_far, 0.65)
    elif k == 13:   # Zhalantos Bahadur arrives with 20,000 horsemen from Samarkand!
        bed(smod.herd, 0.85)
        put(smod.vocal_pad(rng, d + 1.0, [73.4, 110.0, 146.8, 220.0], "a", voices=5), 0, 0.55, rev=(3.2, 0.4))
    elif k == 14:   # Zhalantos slams into enemy rear
        put(smod.impact_boom(rng, 2.0), 0.0, 0.80, rev=(2.0, 0.3))
        bed(smod.herd, 0.80)
        put(smod.sword_clash(rng), 0.25, 0.70, pan=-0.3, rev=(1.5, 0.25))
        put(smod.sword_clash(rng), min(1.1, d * 0.5), 0.70, pan=0.3, rev=(1.5, 0.25))
    elif k == 15:   # Golden sunset over Orbulak: tactical genius & brotherhood
        bed(smod.wind, 0.40, howl=0.3)
        put(smod.eagle(rng), min(0.8, d * 0.3), 0.48, rev=(2.8, 0.4))
        put(smod.vocal_pad(rng, d + 0.8, [65.4, 98.0, 130.8, 196.0], "o", voices=5), 0, 0.45, rev=(3.2, 0.4))
    elif k == 16:   # Seamless loop riser: cocking matchlock & hissing fuse cut at loop point
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


def render_worker(f0, f1, seg_path, segs, chunks):
    vig = rmod.vignette()[..., None]
    cache = {}
    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "rawvideo",
         "-pix_fmt", "rgb24", "-s", f"{rmod.W}x{rmod.H}", "-r", str(rmod.FPS), "-i", "-",
         "-c:v", "libx264", "-preset", "faster", "-crf", "21", "-maxrate", "5.5M",
         "-bufsize", "11M", "-pix_fmt", "yuv420p", "-g", "60", str(seg_path)],
        stdin=subprocess.PIPE,
    )
    si = ci = 0
    cur_name = None
    cur_frames = None
    for fi in range(f0, f1):
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
            cur_frames = rmod.load_video_frames(vp, min(90, max(8, int(round(seg_dur * rmod.FPS)))))

        idx = min(len(cur_frames) - 1, int(u * len(cur_frames)))
        arr = (cur_frames[idx].astype(np.uint16) * vig) >> 8
        if name in ("scene_08", "scene_14") and tau < 0.35:
            arr = arr + ((255 - arr) * (0.85 * math.exp(-tau / 0.08))).astype(np.uint16)
        im = Image.fromarray(arr.astype(np.uint8))

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
            im.paste(ov, (int(rmod.W / 2 - ov.width / 2), int(rmod.SUB_Y - ov.height / 2)), ov)
        ff.stdin.write(im.tobytes())
    ff.stdin.close()
    ff.wait()


def run_render(lang: str):
    B = ROOT / "build_ep02" / lang
    tl = json.loads((B / "timeline.json").read_text(encoding="utf-8"))
    words = json.loads((B / "words.json").read_text(encoding="utf-8"))
    T = tl["T"]
    segs, chunks = rmod.segments(tl), rmod.chunks_from(words, T)
    F = math.ceil(T * rmod.FPS)
    cuts = [round(F * i / rmod.WORKERS) for i in range(rmod.WORKERS + 1)]
    procs, parts = [], []
    for i in range(rmod.WORKERS):
        p = B / f"seg{i}.mp4"
        parts.append(p)
        procs.append(Process(target=render_worker, args=(cuts[i], cuts[i + 1], p, segs, chunks)))
        procs[-1].start()
    for p in procs:
        p.join()
        assert p.exitcode == 0, "render worker failed"
    (B / "concat.txt").write_text("".join(f"file '{p.name}'\n" for p in parts))
    subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0",
         "-i", str(B / "concat.txt"), "-c", "copy", str(B / "video.mp4")],
        check=True,
    )
    OUTPUT.mkdir(exist_ok=True)
    out = OUTPUT / f"EP02_Orbulak_Shorts_{lang.upper()}.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(B / "video.mp4"),
         "-i", str(B / "mix.wav"), "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac",
         "-b:a", "192k", "-ar", "48000", "-shortest", "-movflags", "+faststart", str(out)],
        check=True,
    )
    print(f"[ep02-{lang}] video ready → {out}")


if __name__ == "__main__":
    langs = sys.argv[1:] if len(sys.argv) > 1 else ["ru", "kz", "en"]
    for l in langs:
        run_voice(l)
        run_sfx(l)
        run_render(l)
