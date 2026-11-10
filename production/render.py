"""Step 3 — render the vertical Short (1080×1920, 30 fps) and mux with the final mix.

Ken Burns camera moves per storyboard (zoom / pan / slow rotation), impact shake &
flash, cinematic vignette, and dynamic 1–3-word subtitles with the spoken word in gold.

Usage:  python render.py <ru|kz|en>
Input:  build/<lang>/timeline.json, words.json, mix.wav; ../scenes/*.jpg
Output: ../output/EP01_Ordabasy_Shorts_<LANG>.mp4
"""
import json
import math
import re
import subprocess
import sys
from multiprocessing import Process
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent
SCENES = ROOT.parent / "scenes"
OUTPUT = ROOT.parent / "output"
W, H, FPS = 1080, 1920, 30
FONT = ROOT / "fonts" / "Montserrat-Black.ttf"
SUB_Y, SUB_MAXW = 1240, 940       # subtitle centre (safe zone, slightly below centre)
GOLD, WHITE = (255, 196, 56, 255), (255, 255, 255, 255)
WORKERS = 2


def M(**k):
    return k


# z: zoom, px/py: pan as fraction of free margin (+py = lower part), r: rotation (deg)
MOVES = {
    "scene_01": M(z=(1.0, 1.16), ease="in", shake=True),
    "scene_02": M(z=(1.0, 1.08), py=(0.5, -0.3)),
    "scene_03": M(z=(1.12, 1.12), px=(-0.8, 0.8), ease="lin"),
    "scene_04": M(z=(1.12, 1.12), px=(0.8, -0.6), ease="lin"),
    "scene_04b": M(z=(1.0, 1.1)),
    "scene_05": M(z=(1.0, 1.22), ease="in"),
    "scene_06": M(z=(1.02, 1.12), py=(0.5, 0.0)),
    "scene_07": M(z=(1.14, 1.04), py=(0.8, -0.6)),
    "scene_08": M(z=(1.0, 1.2), ease="in", shake=True),
    "scene_08b": M(z=(1.12, 1.04)),
    "scene_09": M(z=(1.13, 1.13), r=(-2, 2), ease="lin"),
    "scene_09b": M(z=(1.1, 1.16), r=(1, -1)),
    "scene_10": M(z=(1.12, 1.12), px=(-0.8, 0.8), ease="lin"),
    "scene_11": M(z=(1.0, 1.1)),
    "scene_12": M(z=(1.0, 1.1), py=(0.2, 0.0)),
    "scene_13": M(z=(1.12, 1.12), px=(0.7, -0.7), ease="lin"),
    "scene_14": M(z=(1.12, 1.12), px=(-0.9, 0.9), ease="lin"),
    "scene_15": M(z=(1.0, 1.12)),
    "scene_16": M(z=(1.14, 1.14), px=(0.9, -0.9), ease="out"),
    "scene_17": M(z=(1.04, 1.12), shake=True, flash=True),
    "scene_18": M(z=(1.2, 1.2), r=(0, 4), ease="lin"),
    "scene_19": M(z=(1.16, 1.0), ease="out"),
    "scene_20": M(z=(1.0, 1.3), ease="in"),
}


def ease(u, kind):
    if kind == "lin":
        return u
    if kind == "in":
        return u * u
    if kind == "out":
        return 1 - (1 - u) ** 2
    return 0.5 * u + 0.5 * u * u * (3 - 2 * u)   # soft in-out


def segments(tl):
    segs = []
    for sc in tl["scenes"]:
        imgs, t0, t1 = sc["images"], sc["t0"], sc["t1"]
        step = (t1 - t0) / len(imgs)
        for i, name in enumerate(imgs):
            segs.append({"name": name, "t0": t0 + i * step, "t1": t0 + (i + 1) * step})
    return segs


def chunks_from(words, T):
    groups, cur = [], []
    for w in words:
        txt = w["w"].replace("—", "").strip()
        if not txt:
            continue
        txt = txt.upper()
        if cur and (len(cur) == 3 or sum(len(x["txt"]) + 1 for x in cur) + len(txt) > 16):
            groups.append(cur)
            cur = []
        cur.append({"txt": txt, "t0": w["t0"], "t1": w["t1"]})
        if re.search(r"[,.!?:;…]+[»\"”]?$", txt):
            groups.append(cur)
            cur = []
    if cur:
        groups.append(cur)
    out = []
    for i, g in enumerate(groups):
        nxt = groups[i + 1][0]["t0"] if i + 1 < len(groups) else T
        end = nxt if nxt - g[-1]["t1"] < 0.6 else g[-1]["t1"] + 0.3
        out.append({"words": g, "t0": g[0]["t0"], "t1": min(end, nxt)})
    return out


_fonts = {}


def font(size):
    if size not in _fonts:
        _fonts[size] = ImageFont.truetype(str(FONT), size)
    return _fonts[size]


def render_chunk(words, active):
    txts = [w["txt"] for w in words]
    for size in range(100, 59, -4):
        f = font(size)
        sp = f.getlength(" ")
        widths = [f.getlength(t) for t in txts]
        if sum(widths) + sp * (len(txts) - 1) <= SUB_MAXW:
            break
    lines = [list(range(len(txts)))]
    if sum(widths) + sp * (len(txts) - 1) > SUB_MAXW and len(txts) > 1:
        k = min(range(1, len(txts)), key=lambda k: max(sum(widths[:k]), sum(widths[k:])))
        lines = [list(range(k)), list(range(k, len(txts)))]
    stroke = max(5, size // 11)
    asc, desc = f.getmetrics()
    lh, pad = asc + desc, 40
    lw = [sum(widths[i] for i in ln) + sp * (len(ln) - 1) for ln in lines]
    iw, ih = int(max(lw) + 2 * pad), int(lh * len(lines) + 2 * pad)
    shadow = Image.new("RGBA", (iw, ih), (0, 0, 0, 0))
    layer = Image.new("RGBA", (iw, ih), (0, 0, 0, 0))
    ds, dl = ImageDraw.Draw(shadow), ImageDraw.Draw(layer)
    for li, ln in enumerate(lines):
        x, y = (iw - lw[li]) / 2, pad + li * lh
        for i in ln:
            ds.text((x + 4, y + 6), txts[i], font=f, fill=(0, 0, 0, 200), stroke_width=stroke, stroke_fill=(0, 0, 0, 200))
            dl.text((x, y), txts[i], font=f, fill=GOLD if i == active else WHITE,
                    stroke_width=stroke, stroke_fill=(0, 0, 0, 255))
            x += widths[i] + sp
    shadow = shadow.filter(ImageFilter.GaussianBlur(9))
    shadow.alpha_composite(layer)
    return shadow


def vignette():
    yy, xx = np.mgrid[0:H, 0:W]
    r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 * 0.9 + ((yy - H / 2) / (H / 2)) ** 2 * 0.75)
    return ((1 - 0.38 * np.clip((r - 0.6) / 0.8, 0, 1) ** 1.6) * 256).astype(np.uint16)


SCENES_VIDEO = ROOT.parent / "scenes_video"


def load_video_frames(mp4_path: Path, n_out: int):
    """Decode and upscale an AI-animated clip to WxH in native ffmpeg C/SIMD."""
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(mp4_path)],
        capture_output=True, text=True, check=True,
    )
    dur = max(0.5, float(probe.stdout.strip()))
    target_fps = max(12.0, (n_out + 2) / dur)
    vf = (
        f"fps={target_fps:.3f},"
        f"scale={W}:{H}:force_original_aspect_ratio=increase:flags=bicubic,"
        f"crop={W}:{H},unsharp=3:3:0.55:3:3:0.0"
    )
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(mp4_path), "-vf", vf,
         "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        capture_output=True, check=True,
    ).stdout
    frame_bytes = W * H * 3
    n_frames = max(1, len(raw) // frame_bytes)
    return [
        np.frombuffer(raw, dtype=np.uint8, count=frame_bytes, offset=i * frame_bytes).reshape((H, W, 3))
        for i in range(n_frames)
    ]


def worker(f0, f1, seg_path, segs, chunks):
    vig = vignette()[..., None]
    cache = {}
    ff = subprocess.Popen(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "rawvideo",
                           "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                           "-c:v", "libx264", "-preset", "faster", "-crf", "18", "-maxrate", "11M",
                           "-bufsize", "22M", "-pix_fmt", "yuv420p", "-g", "60", str(seg_path)],
                          stdin=subprocess.PIPE)
    si = ci = 0
    cur_name = None
    cur_frames = None
    for fi in range(f0, f1):
        t = fi / FPS
        while si + 1 < len(segs) and t >= segs[si + 1]["t0"]:
            si += 1
        sg = segs[si]
        name = sg["name"]
        mv = MOVES[name]
        tau = t - sg["t0"]
        seg_dur = max(0.1, sg["t1"] - sg["t0"])
        u = min(1.0, max(0.0, tau / seg_dur))

        if name != cur_name:
            cur_name = name
            vp = SCENES_VIDEO / f"{name}.mp4"
            cur_frames = load_video_frames(vp, max(8, int(round(seg_dur * FPS))))

        idx = min(len(cur_frames) - 1, int(u * len(cur_frames)))
        arr = (cur_frames[idx].astype(np.uint16) * vig) >> 8
        if mv.get("flash") and tau < 0.35:
            arr = arr + ((255 - arr) * (0.85 * math.exp(-tau / 0.08))).astype(np.uint16)
        im = Image.fromarray(arr.astype(np.uint8))

        while ci + 1 < len(chunks) and t >= chunks[ci + 1]["t0"]:
            ci += 1
        ch = chunks[ci]
        if ch["t0"] <= t < ch["t1"]:
            act = max(i for i, w in enumerate(ch["words"]) if w["t0"] <= t or i == 0)
            key = (ci, act)
            if key not in cache:
                cache[key] = render_chunk(ch["words"], act)
            ov = cache[key]
            pop = t - ch["t0"]
            if pop < 0.09:   # pop-in
                sc = 0.86 + 0.14 * (1 - (1 - pop / 0.09) ** 2)
                ov = ov.resize((max(1, int(ov.width * sc)), max(1, int(ov.height * sc))), Image.BILINEAR)
            im.paste(ov, (int(W / 2 - ov.width / 2), int(SUB_Y - ov.height / 2)), ov)
        ff.stdin.write(im.tobytes())
    ff.stdin.close()
    ff.wait()


def run(lang):
    B = ROOT / "build" / lang
    tl = json.loads((B / "timeline.json").read_text(encoding="utf-8"))
    words = json.loads((B / "words.json").read_text(encoding="utf-8"))
    T = tl["T"]
    segs, chunks = segments(tl), chunks_from(words, T)
    F = math.ceil(T * FPS)
    cuts = [round(F * i / WORKERS) for i in range(WORKERS + 1)]
    procs, parts = [], []
    for i in range(WORKERS):
        p = B / f"seg{i}.mp4"
        parts.append(p)
        procs.append(Process(target=worker, args=(cuts[i], cuts[i + 1], p, segs, chunks)))
        procs[-1].start()
    for p in procs:
        p.join()
        assert p.exitcode == 0, "render worker failed"
    (B / "concat.txt").write_text("".join(f"file '{p.name}'\n" for p in parts))
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0",
                    "-i", str(B / "concat.txt"), "-c", "copy", str(B / "video.mp4")], check=True)
    OUTPUT.mkdir(exist_ok=True)
    out = OUTPUT / f"EP01_Ordabasy_Shorts_{lang.upper()}.mp4"
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(B / "video.mp4"),
                    "-i", str(B / "mix.wav"), "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac",
                    "-b:a", "192k", "-ar", "48000", "-shortest", "-movflags", "+faststart", str(out)], check=True)
    print(f"[{lang}] video ready → {out}")


if __name__ == "__main__":
    run(sys.argv[1])
