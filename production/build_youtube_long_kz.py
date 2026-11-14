#!/usr/bin/env python3
"""YouTube Long-Form 6-Mode Maximally-Animated Documentary Engine (1920x1080, 16:9, 30fps, KZ ONLY).

Combines best retention & visualization mechanics from Competitor Analysis:
  1) tactical_battle   - topographic contour board, moving regiment blocks, 3-phase stepper, arrows/volleys
  2) strategic_atlas   - 3D-hillshaded Eurasian Steppe atlas, expanding territory zones, campaign arrows
  3) order_of_battle   - head-to-head force comparisons, animated waffle/unit-block grids (1:83), stat bars
  4) system_diagram    - dark blueprint schematic hubs, flowing pulse connectors, seesaw diplomatic scales
  5) timeline_chronicle- interactive 1510..1771 horizontal timeline cursor + dual cinema frames
  6) cinema_montage    - 2-cut subpixel camera + snow/arrows/dust particles + telemetry dossier

100% Hanafi-compliant (zero close-up faces, zero gore, zero musical instruments: physical SFX + A cappella, -14 LUFS).
Portable path detection: ROOT = Path(__file__).resolve().parent.parent
"""

import asyncio
import concurrent.futures
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import time
import wave
from functools import lru_cache
from pathlib import Path

import edge_tts
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy.ndimage import gaussian_filter, sobel

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "production"))

import sfx as smod
from yt_long_scenes_kz import (
    CHAPTER_BREAK_SCENES,
    CHAPTER_PILLS,
    CITIES_169,
    LABEL_SIDE_169,
    RIVERS_169,
    SCENES,
    TIMELINE_ERAS,
)

try:
    import imageio_ffmpeg
    FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    FFMPEG = "ffmpeg"

SR = 48000
W, H, FPS = 1920, 1080, 30

FONT_PATH = ROOT / "production" / "fonts" / "Montserrat-Black.ttf"
BUILD = ROOT / "production" / "build_yt_long01"
OUT_DIR = ROOT / "output"
OUT_FILE = "YT_LONG_01_Kazakh_Khanate_16x9_KZ.mp4"

VOICE_MAIN = "kk-KZ-DauletNeural"
VOICE_FALLBACK = "kk-KZ-AigulNeural"
VOICE_RATE = "+4%"
VOICE_PITCH = "-1Hz"

VOICE_FX = (
    "highpass=f=75,"
    "acompressor=threshold=-20dB:ratio=2.8:attack=10:release=140,"
    "equalizer=f=135:t=q:w=1.2:g=3.0,"
    "equalizer=f=3200:t=q:w=1.5:g=1.8"
)

GOLD = (248, 202, 84)
CYAN = (78, 224, 222)
RED = (232, 72, 62)
WHITE = (246, 244, 236)
DARK_BG = (10, 16, 24)
MUTED = (165, 182, 198)

PALETTE = {"GOLD": GOLD, "CYAN": CYAN, "RED": RED, "WHITE": WHITE}


@lru_cache(maxsize=64)
def get_font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_PATH), size)


def smoothstep(x: float) -> float:
    x = max(0.0, min(1.0, x))
    return x * x * (3.0 - 2.0 * x)


def ease_out(x: float) -> float:
    x = max(0.0, min(1.0, x))
    return 1.0 - (1.0 - x) ** 3


def fbm_noise(h: int, w: int, octaves: int = 5, base_scale: float = 150.0, seed: int = 1771) -> np.ndarray:
    rng = np.random.default_rng(seed)
    acc = np.zeros((h, w), dtype=np.float32)
    amp, norm_s = 1.0, 0.0
    for k in range(octaves):
        sig = max(1.5, base_scale / (2.0 ** k))
        gh = max(8, int(h / max(4.0, sig * 0.6)))
        gw = max(8, int(w / max(4.0, sig * 0.6)))
        grid = rng.standard_normal((gh, gw)).astype(np.float32)
        up = np.array(Image.fromarray(grid).resize((w, h), Image.Resampling.BICUBIC), dtype=np.float32)
        up = gaussian_filter(up, sigma=max(1.0, sig * 0.14))
        acc += amp * up
        norm_s += amp
        amp *= 0.52
    acc /= max(1e-6, norm_s)
    mn, mx = float(acc.min()), float(acc.max())
    return (acc - mn) / max(1e-6, mx - mn)


@lru_cache(maxsize=512)
def eval_polyline(pts_tuple: tuple, n_samples: int = 100) -> tuple:
    pts = list(pts_tuple)
    p = [pts[0]] + pts + [pts[-1]]
    out = []
    segs = max(1, len(pts) - 1)
    steps_per = max(4, n_samples // segs)
    for i in range(segs):
        p0, p1, p2, p3 = p[i], p[i + 1], p[i + 2], p[i + 3]
        for s in range(steps_per):
            t = s / steps_per
            t2, t3 = t * t, t * t * t
            x = 0.5 * ((2 * p1[0]) + (-p0[0] + p2[0]) * t + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2 + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3)
            y = 0.5 * ((2 * p1[1]) + (-p0[1] + p2[1]) * t + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2 + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3)
            out.append((x, y))
    out.append(pts[-1])
    return tuple(out)


def point_along_path(pts, frac: float) -> tuple[float, float, float]:
    frac = max(0.0, min(1.0, frac))
    if len(pts) < 2:
        return pts[0][0], pts[0][1], 0.0
    idx = min(len(pts) - 2, int(frac * (len(pts) - 1)))
    rem = frac * (len(pts) - 1) - idx
    x0, y0 = pts[idx]
    x1, y1 = pts[idx + 1]
    return x0 + (x1 - x0) * rem, y0 + (y1 - y0) * rem, math.atan2(y1 - y0, x1 - x0)


# ---------------------------------------------------------------------------
# CACHED BACKGROUNDS: 3D-HILLSHADED ATLAS + BLUEPRINT GRID + TOPO ARENA
# ---------------------------------------------------------------------------
_HI_MAP_169 = None
_BLUEPRINT_BG = None
_TOPO_BG = None


def build_widescreen_relief_map() -> Image.Image:
    """Build or load cached 3840x2160 3D-hillshaded Kazakh Steppe atlas (rivers/lakes baked in!)."""
    global _HI_MAP_169
    if _HI_MAP_169 is not None:
        return _HI_MAP_169
    cache_p = BUILD / "cache_map_2x.jpg"
    if cache_p.exists() and cache_p.stat().st_size > 200000:
        _HI_MAP_169 = Image.open(cache_p).convert("RGB")
        return _HI_MAP_169

    BUILD.mkdir(parents=True, exist_ok=True)
    w0, h0 = 1920, 1080
    elev = fbm_noise(h0, w0, octaves=6, base_scale=175.0, seed=1771)
    ridge = 1.0 - np.abs(fbm_noise(h0, w0, octaves=4, base_scale=120.0, seed=1730) * 2.0 - 1.0)
    hmap = elev * 0.72 + (ridge ** 1.45) * 0.34

    yy, xx = np.mgrid[0:h0, 0:w0].astype(np.float32)
    altai = np.exp(-(((xx - 1650) / 280.0) ** 2 + ((yy - 250) / 180.0) ** 2))
    alatau = np.exp(-(((xx - 1290) / 260.0) ** 2 + ((yy - 670) / 150.0) ** 2))
    ulytau = np.exp(-(((xx - 645) / 180.0) ** 2 + ((yy - 420) / 120.0) ** 2))
    hmap = hmap + altai * 0.36 + alatau * 0.32 + ulytau * 0.16

    dz_dx, dz_dy = sobel(hmap, axis=1) * 3.1, sobel(hmap, axis=0) * 3.1
    az, alt = math.radians(315.0), math.radians(34.0)
    lx, ly, lz = math.cos(alt) * math.cos(az), math.cos(alt) * math.sin(az), math.sin(alt)
    shade = np.clip((lz - dz_dx * lx - dz_dy * ly) / np.sqrt(1.0 + dz_dx ** 2 + dz_dy ** 2), 0.14, 1.0)

    rgb = np.zeros((h0, w0, 3), dtype=np.float32)
    lowland = np.clip(1.0 - (hmap / 0.85), 0.0, 1.0)
    rgb[..., 0] = (20 + 28 * hmap + 12 * ridge) * (0.40 + 0.65 * shade)
    rgb[..., 1] = (22 + 24 * hmap + 10 * lowland) * (0.40 + 0.64 * shade)
    rgb[..., 2] = (18 + 18 * lowland) * (0.44 + 0.60 * shade)

    base = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8)).resize((W * 2, H * 2), Image.Resampling.BICUBIC).convert("RGB")
    d = ImageDraw.Draw(base, "RGBA")
    for gx in range(0, W * 2 + 1, 240):
        d.line([(gx, 0), (gx, H * 2)], fill=(48, 66, 78, 95), width=2)
    for gy in range(0, H * 2 + 1, 216):
        d.line([(0, gy), (W * 2, gy)], fill=(48, 66, 78, 95), width=2)

    # Baked Caspian/Aral/Balkhash/Alakol/Zaisan waters on 2x canvas
    d.ellipse([660, 1020, 820, 1190], fill=(16, 48, 68, 255), outline=(58, 165, 195, 220), width=3)  # Aral
    d.polygon([(1920, 1130), (2180, 1075), (2420, 1090), (2350, 1165), (2050, 1185)], fill=(18, 52, 72, 255))  # Balkhash
    d.ellipse([2680, 990, 2810, 1045], fill=(18, 52, 72, 255))
    d.ellipse([3070, 665, 3195, 715], fill=(18, 52, 72, 255))

    # Baked stylized rivers (2x scale) + subtle non-colliding river labels
    f_riv = get_font(28)
    for rname, pts in RIVERS_169.items():
        dense = eval_polyline(tuple(pts), 80)
        spts = [(x * 2.0, y * 2.0) for x, y in dense]
        d.line(spts, fill=(46, 152, 198, 72), width=20, joint="curve")
        d.line(spts, fill=(102, 210, 238, 185), width=7, joint="curve")
        l_idx = int(len(spts) * (0.76 if rname == "СЫРДАРИЯ" else (0.30 if rname == "ЖАЙЫҚ" else 0.50)))
        mx, my = spts[min(len(spts) - 1, l_idx)]
        d.text((mx - 48, my - 38), rname, font=f_riv, fill=(128, 226, 248, 200))

    base.save(cache_p, "JPEG", quality=94)
    _HI_MAP_169 = base
    return _HI_MAP_169


def get_blueprint_bg() -> Image.Image:
    global _BLUEPRINT_BG
    if _BLUEPRINT_BG is not None:
        return _BLUEPRINT_BG
    im = Image.new("RGB", (W, H), (9, 15, 23))
    d = ImageDraw.Draw(im, "RGBA")
    for gx in range(0, W + 1, 48):
        col = (34, 60, 78, 70) if gx % 192 == 0 else (24, 42, 56, 36)
        d.line([(gx, 0), (gx, H)], fill=col, width=1)
    for gy in range(0, H + 1, 48):
        col = (34, 60, 78, 70) if gy % 192 == 0 else (24, 42, 56, 36)
        d.line([(0, gy), (W, gy)], fill=col, width=1)
    _BLUEPRINT_BG = im
    return _BLUEPRINT_BG


def get_topo_arena_bg() -> Image.Image:
    global _TOPO_BG
    if _TOPO_BG is not None:
        return _TOPO_BG
    elev = fbm_noise(H, W, octaves=5, base_scale=160.0, seed=1643)
    rgb = np.zeros((H, W, 3), dtype=np.float32)
    rgb[..., 0] = 11 + 18 * elev
    rgb[..., 1] = 16 + 22 * elev
    rgb[..., 2] = 22 + 24 * elev
    im = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8)).convert("RGB")
    d = ImageDraw.Draw(im, "RGBA")
    for gx in range(0, W + 1, 96):
        d.line([(gx, 0), (gx, H)], fill=(50, 72, 90, 45), width=1)
    for gy in range(0, H + 1, 96):
        d.line([(0, gy), (W, gy)], fill=(50, 72, 90, 45), width=1)
    _TOPO_BG = im
    return _TOPO_BG


@lru_cache(maxsize=40)
def load_plate(rel: str) -> Image.Image:
    return Image.open(ROOT / rel).convert("RGB")


@lru_cache(maxsize=40)
def load_ambient_wide(rel: str) -> Image.Image:
    src = load_plate(rel)
    sw, sh = src.size
    crop_h = int(sw * H / W)
    cy = int(sh * 0.45)
    y0 = max(0, min(sh - crop_h, cy - crop_h // 2))
    wide = src.crop((0, y0, sw, y0 + crop_h)).resize((W, H), Image.Resampling.BILINEAR)
    wide = wide.filter(ImageFilter.GaussianBlur(16))
    arr = (np.asarray(wide, dtype=np.float32) * 0.32).astype(np.uint8)
    return Image.fromarray(arr)


def crop_rigid_viewport(src: Image.Image, tw: int, th: int, u: float, tau: float, z0: float = 1.02, z1: float = 1.12, cy_focus: float = 0.45, shake: bool = False) -> Image.Image:
    sw, sh = src.size
    e = smoothstep(u)
    z = z0 + (z1 - z0) * e
    dx_px, dy_px = 0.0, 0.0
    if shake and tau <= 0.42:
        dec = math.exp(-7.5 * tau)
        dx_px = 8.0 * dec * math.sin(tau * 60.0)
        dy_px = 5.0 * dec * math.cos(tau * 48.0)
    vw = sw / z
    vh = vw * (th / tw)
    if vh > sh:
        vh = sh / z
        vw = vh * (tw / th)
    cx = sw * (0.49 + 0.02 * e) + dx_px
    cy = sh * (cy_focus - 0.03 * e) + dy_px
    x0 = max(0.0, min(sw - vw, cx - vw * 0.5))
    y0 = max(0.0, min(sh - vh, cy - vh * 0.5))
    return src.transform((tw, th), Image.Transform.EXTENT, (x0, y0, x0 + vw, y0 + vh), Image.Resampling.BILINEAR)


# ---------------------------------------------------------------------------
# FAST REUSABLE PRIMITIVES (DRAW DIRECTLY VIA ImageDraw(im, "RGBA"))
# ---------------------------------------------------------------------------
class WidescreenMapCamera:
    def __init__(self, zoom: float, cx: float, cy: float):
        self.zoom = max(1.0, zoom)
        self.vw, self.vh = W / self.zoom, H / self.zoom
        self.x0 = max(0.0, min(W - self.vw, cx - self.vw * 0.5))
        self.y0 = max(0.0, min(H - self.vh, cy - self.vh * 0.5))

    def to_screen(self, wx: float, wy: float) -> tuple[float, float]:
        return (wx - self.x0) * self.zoom, (wy - self.y0) * self.zoom


def draw_city_node(d: ImageDraw.ImageDraw, cam: WidescreenMapCamera, name: str, status: str, burst_u: float, t: float, emphasis: bool = False):
    wx, wy = CITIES_169[name]
    sx, sy = cam.to_screen(wx, wy)
    if not (-60 <= sx <= W + 60 and 95 <= sy <= H - 170):
        return
    if status == "red":
        c_fill, c_ring = RED, (255, 130, 110)
    elif status == "capturing":
        c_fill, c_ring = CYAN, (180, 255, 255)
    elif status == "neutral":
        c_fill, c_ring = (140, 152, 165), (195, 208, 220)
    else:
        c_fill, c_ring = GOLD, (110, 232, 230)

    r = 19 if emphasis else 13
    if 0.0 < burst_u < 1.0:
        br = int(r + 62 * ease_out(burst_u))
        ba = int(225 * (1.0 - burst_u))
        d.ellipse([sx - br, sy - br, sx + br, sy + br], outline=(248, 202, 84, ba), width=4)

    ro = int((r + 8) * (1.0 + 0.13 * math.sin(t * 4.5 + wx * 0.02)))
    d.ellipse([sx - ro, sy - ro, sx + ro, sy + ro], outline=(*c_ring, 135), width=2)
    d.ellipse([sx - r - 3, sy - r - 3, sx + r + 3, sy + r + 3], fill=(12, 18, 28, 235), outline=(*c_ring, 245), width=2)
    fw = int(r * 0.56)
    d.rectangle([sx - fw, sy - fw + 3, sx + fw, sy + fw - 1], fill=(*c_fill, 245))
    d.pieslice([sx - fw, sy - r + 2, sx + fw, sy - fw + 8], 180, 360, fill=(*c_fill, 245))

    f_lbl = get_font(21 if emphasis else 18)
    tw = d.textlength(name, font=f_lbl)
    side = LABEL_SIDE_169.get(name, "below")
    if side == "above":
        tx, ty = sx - tw * 0.5, sy - r - 31
    elif side == "left":
        tx, ty = sx - r - 14 - tw, sy - 11
    elif side == "right":
        tx, ty = sx + r + 14, sy - 11
    else:
        tx, ty = sx - tw * 0.5, sy + r + 9
    d.rounded_rectangle([tx - 7, ty - 2, tx + tw + 7, ty + 24], radius=6, fill=(10, 16, 24, 215), outline=(*c_ring, 145), width=1)
    d.text((tx, ty), name, font=f_lbl, fill=(252, 248, 236, 252))


def draw_arrow_map(d: ImageDraw.ImageDraw, cam: WidescreenMapCamera, pts_world: list, progress: float, t: float, col_main=GOLD, col_glow=CYAN, width: int = 10):
    if progress <= 0.02:
        return
    dense = eval_polyline(tuple(pts_world), 96)
    n_show = max(2, int(len(dense) * min(1.0, progress)))
    pts = [cam.to_screen(x, y) for x, y in dense[:n_show]]
    d.line(pts, fill=(*col_glow, 72), width=width + 10, joint="curve")
    d.line(pts, fill=(*col_main, 238), width=width, joint="curve")
    for m in range(3):
        frac = ((t * 0.85 + m * 0.33) % 1.0) * min(0.95, progress)
        if frac > 0.05:
            px, py, _ = point_along_path(dense, frac)
            sx, sy = cam.to_screen(px, py)
            d.ellipse([sx - 4, sy - 4, sx + 4, sy + 4], fill=(255, 252, 240, 235))
    hx, hy = pts[-1]
    px0, py0 = pts[max(0, len(pts) - 4)]
    ang = math.atan2(hy - py0, hx - px0)
    sz = width * 1.85 + 5
    d.polygon([
        (hx + math.cos(ang) * 6, hy + math.sin(ang) * 6),
        (hx - math.cos(ang - 0.55) * sz, hy - math.sin(ang - 0.55) * sz),
        (hx - math.cos(ang + 0.55) * sz, hy - math.sin(ang + 0.55) * sz),
    ], fill=(*col_main, 255))


def draw_unit_badge_map(d: ImageDraw.ImageDraw, cam: WidescreenMapCamera, wx: float, wy: float, label: str, t: float, col=GOLD, off=(0, -48)):
    sx, sy = cam.to_screen(wx, wy)
    if not (-60 <= sx <= W + 60 and 95 <= sy <= H - 170):
        return
    by = sy + math.sin(t * 6.0) * 3.0
    d.polygon([(sx - 18, by + 10), (sx, by - 14), (sx + 18, by + 10), (sx + 11, by + 15), (sx - 11, by + 15)], fill=(*col, 245), outline=(12, 16, 22, 255))
    f = get_font(18)
    tw = d.textlength(label, font=f)
    lx, ly = sx + off[0] - tw * 0.5, by + off[1]
    d.rounded_rectangle([lx - 10, ly - 4, lx + tw + 10, ly + 25], radius=8, fill=(10, 16, 24, 225), outline=(*col, 235), width=2)
    d.text((lx, ly), label, font=f, fill=(*col, 255))


def draw_map_callout(d: ImageDraw.ImageDraw, title: str, sub: str, col=GOLD, x: int = 48, y: int = 770, w: int = 660):
    d.rounded_rectangle([x, y, x + w, y + 96], radius=16, fill=(10, 16, 24, 232), outline=(*col, 235), width=2)
    d.text((x + 22, y + 15), title, font=get_font(24), fill=(*col, 255))
    d.text((x + 22, y + 53), sub, font=get_font(18), fill=(238, 240, 244, 240))


def draw_seesaw_scale(d: ImageDraw.ImageDraw, tau: float, t: float, x0: int, y0: int, w: int, h: int, title: str = "ТЕПЕ-ТЕҢДІК АЙЛАСЫ • ҚОС ИМПЕРИЯ АРАСЫНДА"):
    d.rounded_rectangle([x0, y0, x0 + w, y0 + h], radius=18, fill=(10, 16, 24, 235), outline=(*GOLD, 235), width=3)
    fh = get_font(18)
    d.text((x0 + (w - d.textlength(title, font=fh)) / 2, y0 + 14), title, font=fh, fill=(*CYAN, 250))
    tilt = 0.08 * math.sin(t * 2.4) * math.exp(-tau * 0.20)
    bx, by = x0 + w // 2, y0 + int(h * 0.66)
    bw = int(w * 0.34)
    xL, yL = bx - math.cos(tilt) * bw, by - math.sin(tilt) * bw
    xR, yR = bx + math.cos(tilt) * bw, by + math.sin(tilt) * bw
    d.polygon([(bx, by + 6), (bx - 16, by + 32), (bx + 16, by + 32)], fill=(*CYAN, 240))
    d.line([(xL, yL), (xR, yR)], fill=(*GOLD, 250), width=6)
    fl = get_font(18)
    for px, py, txt, c_out, c_txt in [(xL, yL - 30, "РЕСЕЙ", RED, WHITE), (bx, by - 36, "ҚАЗАҚ ОРДАСЫ", GOLD, GOLD), (xR, yR - 30, "ЦИН", RED, WHITE)]:
        tw = d.textlength(txt, font=fl) + 22
        d.rounded_rectangle([px - tw / 2, py - 12, px + tw / 2, py + 15], radius=10, fill=(16, 24, 34, 235), outline=(*c_out, 235), width=2)
        d.text((px - d.textlength(txt, font=fl) / 2, py - 9), txt, font=fl, fill=(*c_txt, 255))


def draw_dossier_right(d: ImageDraw.ImageDraw, sc: dict, tau: float, t: float, x0: int = 1264, y0: int = 114, w: int = 608, h: int = 782):
    pop = ease_out(min(1.0, tau / 0.28))
    d.rounded_rectangle([x0, y0, x0 + w, y0 + h], radius=22, fill=(10, 16, 24, int(234 * pop)), outline=(*GOLD, int(230 * pop)), width=3)
    tag = sc.get("card_tag", "ТАКТИКАЛЫҚ ТАЛДАУ")
    ft = get_font(18)
    tw = d.textlength(tag, font=ft) + 32
    d.rounded_rectangle([x0 + 26, y0 + 22, x0 + 26 + tw, y0 + 54], radius=10, fill=(18, 38, 48, 235), outline=(*CYAN, 220), width=2)
    d.text((x0 + 42, y0 + 27), tag, font=ft, fill=(*CYAN, 255))

    d.text((x0 + 26, y0 + 70), sc.get("card_title", sc["top"][:26]), font=get_font(29), fill=(*GOLD, 255))
    d.line([(x0 + 26, y0 + 114), (x0 + w - 26, y0 + 114)], fill=(78, 224, 222, 130), width=2)
    cur_y = y0 + 134

    if "counter" in sc:
        target_num, suf, desc = sc["counter"]
        prog = ease_out(min(1.0, tau / 1.1))
        val = int(round(target_num * prog))
        txt_num = f"{val:,}{suf}".replace(",", " ")
        d.text((x0 + 28, cur_y), txt_num, font=get_font(50), fill=(*GOLD, 255))
        d.text((x0 + 28, cur_y + 62), desc, font=get_font(17), fill=(238, 244, 248, 238))
        cur_y += 116

    if "bars" in sc:
        fb = get_font(19)
        bw = w - 56
        for idx, (lbl, frac, cname) in enumerate(sc["bars"]):
            col = PALETTE.get(cname, GOLD) if isinstance(cname, str) else cname
            af = frac * ease_out(min(1.0, max(0.0, (tau - 0.08 * idx) / 0.55)))
            d.text((x0 + 28, cur_y), lbl, font=fb, fill=(246, 244, 236, 245))
            by = cur_y + 28
            d.rounded_rectangle([x0 + 28, by, x0 + 28 + bw, by + 22], radius=8, fill=(22, 32, 44, 235), outline=(90, 120, 135, 160), width=1)
            d.rounded_rectangle([x0 + 28, by, x0 + 28 + max(14, int(bw * af)), by + 22], radius=8, fill=(*col, 240))
            cur_y += 68

    if "bullets" in sc:
        fk, fv = get_font(18), get_font(19)
        for idx, (k_txt, v_txt) in enumerate(sc["bullets"]):
            bp = ease_out(min(1.0, max(0.0, (tau - 0.06 * idx) / 0.30)))
            if bp <= 0.05:
                continue
            d.rounded_rectangle([x0 + 26, cur_y, x0 + w - 26, cur_y + 74], radius=12, fill=(16, 24, 34, int(222 * bp)), outline=(78, 224, 222, int(145 * bp)), width=1)
            d.text((x0 + 42, cur_y + 10), k_txt, font=fk, fill=(*CYAN, int(250 * bp)))
            d.text((x0 + 42, cur_y + 39), v_txt, font=fv, fill=(*WHITE, int(248 * bp)))
            cur_y += 86

    # Clean bottom telemetry footer if panel has open lower room
    if cur_y <= y0 + h - 104:
        fy = y0 + h - 82
        d.line([(x0 + 26, fy - 14), (x0 + w - 26, fy - 14)], fill=(78, 224, 222, 95), width=1)
        ch_lbl = CHAPTER_PILLS[sc["ch_idx"]]
        d.text((x0 + 28, fy), f"БӨЛІМ {sc['ch_idx'] + 1} / {len(CHAPTER_PILLS)}  •  {ch_lbl} ДӘУІРІ", font=get_font(17), fill=(*CYAN, 235))
        pct = min(1.0, (sc["ch_idx"] + 0.25 + 0.70 * ease_out(min(1.0, tau / 3.0))) / len(CHAPTER_PILLS))
        pbw = w - 56
        d.rounded_rectangle([x0 + 28, fy + 32, x0 + 28 + pbw, fy + 44], radius=6, fill=(22, 34, 48, 230))
        d.rounded_rectangle([x0 + 28, fy + 32, x0 + 28 + max(18, int(pbw * pct)), fy + 44], radius=6, fill=(*GOLD, 240))


# ---------------------------------------------------------------------------
# MODE 1: TACTICAL BATTLE (REGIMENT BLOCKS, ARROWS, TRENCHES, 3 PHASES)
# ---------------------------------------------------------------------------
def draw_regiment_block(d: ImageDraw.ImageDraw, cx: float, cy: float, bw: float, bh: float, label: str, col: tuple, kind: str = "cav", rot_deg: float = 0.0):
    ang = math.radians(rot_deg)
    ca, sa = math.cos(ang), math.sin(ang)
    hw, hh = bw * 0.5, bh * 0.5
    corners = []
    for dx, dy in [(-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)]:
        corners.append((cx + dx * ca - dy * sa, cy + dx * sa + dy * ca))
    d.polygon(corners, fill=(*col, 225), outline=(255, 250, 236, 245))
    # NATO tactical diagonal inside unit block
    if kind == "cav":
        d.line([corners[0], corners[2]], fill=(12, 16, 24, 220), width=3)
    elif kind == "inf":
        d.line([corners[0], corners[2]], fill=(12, 16, 24, 220), width=3)
        d.line([corners[1], corners[3]], fill=(12, 16, 24, 220), width=3)
    else:
        d.ellipse([cx - 8, cy - 8, cx + 8, cy + 8], fill=(12, 16, 24, 235))
    if label:
        fl = get_font(16)
        tw = d.textlength(label, font=fl)
        lx, ly = cx - tw * 0.5, cy + hh + 6
        d.rounded_rectangle([lx - 6, ly - 1, lx + tw + 6, ly + 21], radius=5, fill=(10, 16, 24, 225))
        d.text((lx, ly), label, font=fl, fill=(*WHITE, 250))


def draw_battle_arrow(d: ImageDraw.ImageDraw, pts: list, prog: float, col: tuple, width: int = 8):
    if prog <= 0.03:
        return
    dense = eval_polyline(tuple(pts), 60)
    n = max(2, int(len(dense) * min(1.0, prog)))
    sub = dense[:n]
    d.line(sub, fill=(*col, 235), width=width, joint="curve")
    hx, hy = sub[-1]
    px0, py0 = sub[max(0, len(sub) - 3)]
    ang = math.atan2(hy - py0, hx - px0)
    sz = width * 1.9 + 4
    d.polygon([
        (hx + math.cos(ang) * 5, hy + math.sin(ang) * 5),
        (hx - math.cos(ang - 0.55) * sz, hy - math.sin(ang - 0.55) * sz),
        (hx - math.cos(ang + 0.55) * sz, hy - math.sin(ang + 0.55) * sz),
    ], fill=(*col, 255))


def render_tactical_battle(sc: dict, u: float, tau: float, t: float) -> Image.Image:
    im = get_topo_arena_bg().copy()
    d = ImageDraw.Draw(im, "RGBA")
    bx0, by0, bx1, by1 = 48, 114, 1236, 896
    d.rounded_rectangle([bx0, by0, bx1, by1], radius=22, fill=(12, 19, 28, 185), outline=(*CYAN, 180), width=3)

    bid = sc["battle_id"]
    p = ease_out(min(1.0, u / 0.85))
    sub_phase = 0 if u < 0.34 else (1 if u < 0.68 else 2)

    # Top battle map legend pill
    d.rounded_rectangle([bx0 + 22, by0 + 18, bx0 + 540, by0 + 58], radius=10, fill=(10, 16, 24, 225), outline=(*GOLD, 160), width=1)
    d.text((bx0 + 36, by0 + 27), "АЛТЫН = ҚАЗАҚ ҚОЛЫ   |   ҚЫЗЫЛ = ҚАРСЫЛАС", font=get_font(17), fill=(*WHITE, 245))

    if bid.startswith("ulytau"):
        # Snowy gorge walls top/bottom
        d.polygon([(bx0 + 40, by0 + 110), (bx1 - 60, by0 + 110), (bx1 - 60, by0 + 245), (bx0 + 40, by0 + 200)], fill=(45, 62, 82, 125))
        d.polygon([(bx0 + 40, by1 - 210), (bx1 - 60, by1 - 245), (bx1 - 60, by1 - 95), (bx0 + 40, by1 - 95)], fill=(45, 62, 82, 125))
        d.text((bx0 + 480, by0 + 145), "ҚАР БАСҚАН ҰЛЫТАУ АҢҒАРЫ (-40°C)", font=get_font(20), fill=(*CYAN, 220))
        if bid in {"ulytau_p0", "ulytau_p1"}:
            draw_battle_arrow(d, [(280, 480), (540, 480), (880, 480)], p, RED, 10)
            draw_battle_arrow(d, [(660, 480), (860, 440), (1050, 430)], p, GOLD, 8)
            draw_regiment_block(d, 260 + 280 * p, 480, 96, 48, "ҚАРСЫЛАС КОЛОННАСЫ", RED, "cav")
            draw_regiment_block(d, 640 + 340 * p, 455, 76, 38, "БАРЛАУ (ЖАЛҒАН ШЕГІНУ)", GOLD, "cav")
        else:
            draw_regiment_block(d, 580, 485, 110, 50, "ҚОРШАЛҒАН ҚОЛ", RED, "cav")
            # Double flank encirclement blocks descending from ridge
            draw_battle_arrow(d, [(320, 260), (490, 355), (560, 430)], p, GOLD, 9)
            draw_battle_arrow(d, [(820, 720), (680, 610), (600, 540)], p, GOLD, 9)
            draw_regiment_block(d, 320 + 210 * p, 260 + 150 * p, 78, 38, "ҚАСЫМ ХАН ҚАПТАЛЫ", GOLD, "cav", 25)
            draw_regiment_block(d, 820 - 190 * p, 720 - 150 * p, 78, 38, "МОЙЫНСЫЗ ХАСАН", GOLD, "cav", -30)
            if bid in {"ulytau_p3"}:
                pulse_r = int(28 + 38 * ((t * 2.2) % 1.0))
                d.ellipse([580 - pulse_r, 485 - pulse_r, 580 + pulse_r, 485 + pulse_r], outline=(*CYAN, 200), width=4)

    elif bid.startswith("orbulak") or bid == "preview_traps":
        # Narrow 15-20m canyon walls top/bottom with stepped elevation ridges
        n_wall = [(bx0 + 30, by0 + 92), (bx1 - 30, by0 + 92), (bx1 - 30, by0 + 318), (bx0 + 790, by0 + 334), (bx0 + 470, by0 + 334), (bx0 + 30, by0 + 252)]
        s_wall = [(bx0 + 30, by1 - 242), (bx0 + 470, by1 - 308), (bx0 + 790, by1 - 308), (bx1 - 30, by1 - 292), (bx1 - 30, by1 - 86), (bx0 + 30, by1 - 86)]
        d.polygon(n_wall, fill=(44, 52, 64, 235), outline=(92, 112, 134, 210))
        d.polygon(s_wall, fill=(44, 52, 64, 235), outline=(92, 112, 134, 210))
        d.line([(bx0 + 40, by0 + 215), (bx0 + 475, by0 + 292), (bx1 - 40, by0 + 282)], fill=(76, 94, 114, 165), width=2)
        d.line([(bx0 + 40, by1 - 205), (bx0 + 475, by1 - 268), (bx1 - 40, by1 - 255)], fill=(76, 94, 114, 165), width=2)
        d.text((bx0 + 495, by0 + 132), "БИІК ЖАРТАС (300 БІЛТЕЛІ МЫЛТЫҚ)", font=get_font(20), fill=(*CYAN, 245))
        # Caliper dimension line across narrow 15-20m pass
        d.line([(595, 444), (595, 588)], fill=(*GOLD, 210), width=2)
        d.text((bx0 + 475, by1 - 205), "ТАР ӨТКЕЛ ЕНІ: 15–20 МЕТР", font=get_font(20), fill=(*GOLD, 245))
        # Marksmen icons perched along upper cliff edge
        for mx in range(510, 790, 56):
            d.polygon([(mx - 10, 424), (mx, 408), (mx + 10, 424)], fill=(*CYAN, 240))
        # Earth trenches across narrow throat
        d.line([(650, 445), (650, 565)], fill=(*GOLD, 255), width=12)
        d.line([(690, 450), (690, 560)], fill=(*CYAN, 220), width=6)
        draw_regiment_block(d, 745, 505, 62, 74, "ОҚПАН: 300", GOLD, "inf")
        # 50 000 invader blocks jammed at canyon mouth
        for row in range(3):
            col_x = 240 + row * 115 - (30 * p if bid == "orbulak_p3" else 0)
            draw_regiment_block(d, col_x, 455 + row * 48, 88, 36, "ЖАУ ЛЕГІ" if row == 1 else "", RED, "cav")
        draw_battle_arrow(d, [(220, 505), (460, 505), (620, 505)], p * 0.75, RED, 11)
        # Cliffside sniper crossfire tracers from cliff edge down to pass
        for k in range(5):
            sx, sy = 515 + k * 56, 426
            tx, ty = 355 + k * 52, 505
            frac = (t * 2.5 + k * 0.22) % 1.0
            lx, ly = sx + (tx - sx) * frac, sy + (ty - sy) * frac
            d.line([(sx, sy), (lx, ly)], fill=(255, 225, 110, 225), width=3)
            d.ellipse([lx - 4, ly - 4, lx + 4, ly + 4], fill=(*CYAN, 255))
        if bid == "orbulak_p3":
            draw_battle_arrow(d, [(140, 250), (140, 420), (200, 485)], p, GOLD, 12)
            draw_regiment_block(d, 155, 390 + 60 * p, 92, 42, "ЖАЛАҢТӨС (+20 000)", CYAN, "cav")

    elif bid.startswith("anyrakai") or bid == "bulanty_1728":
        # Anyrakai crescent Tolgama vs Alakol white salt pan + Khantau ridge
        d.ellipse([780, 230, 1180, 420], fill=(215, 228, 235, 65), outline=(*CYAN, 175), width=2)
        d.text((845, 295), "ИТ-ІШПЕС АЛАКӨЛ (ТҰЗДЫ СОР)", font=get_font(18), fill=(*CYAN, 240))
        d.polygon([(350, 720), (880, 670), (1120, 745), (300, 770)], fill=(56, 62, 70, 180))
        d.text((545, 732), "ХАНТАУ ТАУЛАРЫ", font=get_font(18), fill=(*GOLD, 220))
        draw_regiment_block(d, 690 + (160 * p if "p3" in bid else 0), 495 - (100 * p if "p3" in bid else 0), 112, 52, "ЖАУ ЗЕҢБІРЕГІ", RED, "art")
        # Crescent pincer wings
        draw_battle_arrow(d, [(250, 510), (470, 510), (590, 500)], p, GOLD, 9)
        draw_battle_arrow(d, [(320, 390), (560, 315), (840, 360)], p, CYAN, 10)
        draw_battle_arrow(d, [(330, 625), (590, 635), (870, 580)], p, CYAN, 10)
        draw_regiment_block(d, 280 + 220 * p, 495, 76, 36, "ОРТАЛЫҚ", GOLD, "inf")
        draw_regiment_block(d, 380 + 360 * p, 330, 80, 36, "БӨГЕНБАЙ", CYAN, "cav", 12)
        draw_regiment_block(d, 390 + 380 * p, 620, 80, 36, "ҚАБАНБАЙ", GOLD, "cav", -12)

    elif bid.startswith("south") or bid in {"ordabasy_command", "east_campaign_prep", "east_cavalry"}:
        # Maneuver / city capture tactical corridor
        draw_battle_arrow(d, [(200, 520), (490, 440), (760, 480), (1050, 460)], p, GOLD, 11)
        draw_battle_arrow(d, [(240, 620), (540, 600), (880, 560)], p, CYAN, 9)
        for idx, (cx, cy, nm) in enumerate([(440, 470, "ШЕП 1"), (740, 485, "ШЕП 2"), (1020, 465, "МАҚСАТ")]):
            st = GOLD if p > idx * 0.30 else RED
            d.ellipse([cx - 28, cy - 28, cx + 28, cy + 28], fill=(14, 22, 32, 240), outline=(*st, 240), width=4)
            d.text((cx - 28, cy + 36), nm, font=get_font(17), fill=(*st, 250))
        px = 230 + 680 * p
        draw_regiment_block(d, px, 475, 96, 44, "ШАПШАҢ АТТЫ ҚОЛ", GOLD, "cav")
        draw_regiment_block(d, 250 + 520 * p, 600, 84, 38, "ҚАПТАЛ ЖАСАҒЫ", CYAN, "cav")

    # Bottom 3-phase animated progress bar inside Tactical Arena
    ph_w = (bx1 - bx0 - 80) // 3
    for i, pname in enumerate(["ФАЗА 1: БАРЛАУ ЖӘНЕ ТАРТУ", "ФАЗА 2: ҚЫСАҢ МЕН ҚЫСЫМ", "ФАЗА 3: ШЕШУШІ СОҚҚЫ"]):
        px0 = bx0 + 24 + i * (ph_w + 16)
        act = (i <= sub_phase)
        d.rounded_rectangle([px0, by1 - 68, px0 + ph_w, by1 - 18], radius=12, fill=(*GOLD, 235) if act else (18, 28, 40, 220), outline=(*CYAN, 200) if act else (70, 95, 115, 160), width=2)
        fp = get_font(16)
        tw = d.textlength(pname, font=fp)
        d.text((px0 + (ph_w - tw) / 2, by1 - 53), pname, font=fp, fill=(10, 14, 20, 255) if act else (*MUTED, 230))

    # Drifting snow/sparks on top
    if "ulytau" in bid:
        for k in range(32):
            sx = bx0 + ((k * 73 + int(t * 240)) % (bx1 - bx0 - 20))
            sy = by0 + ((k * 59 + int(t * 75)) % (by1 - by0 - 90))
            d.ellipse([sx, sy, sx + 4, sy + 4], fill=(225, 240, 255, 165))

    draw_dossier_right(d, sc, tau, t, x0=1264, y0=114, w=608, h=782)
    return im


# ---------------------------------------------------------------------------
# MODE 2: STRATEGIC ATLAS (3D HILLSHADED MAP, TERRITORY ZONES, VECTORS)
# ---------------------------------------------------------------------------
def render_strategic_atlas(sc: dict, u: float, tau: float, t: float) -> Image.Image:
    mid = sc["map_id"]
    e = smoothstep(u)
    p = ease_out(min(1.0, u / 0.85))
    C = CITIES_169

    # Camera trajectories per map_id
    cams = {
        "prologue_wide":    (1.04, 1.08, 950, 520, 960, 520),
        "to_1510":          (1.06, 1.40, 920, 500, 645, 455),
        "ch1_embargo":      (1.36, 1.44, 620, 610, 635, 510),
        "ch1_expansion":    (1.22, 1.06, 650, 460, 940, 480),
        "to_1598":          (1.18, 1.42, 660, 480, 690, 665),
        "ch2_prep":         (1.34, 1.44, 680, 630, 700, 660),
        "ch2_cascade":      (1.40, 1.48, 650, 640, 680, 685),
        "ch2_bukhara":      (1.42, 1.38, 690, 690, 620, 740),
        "ch2_200years":     (1.32, 1.40, 720, 675, 760, 665),
        "to_1643":          (1.20, 1.48, 860, 640, 1265, 615),
        "ch3_locate":       (1.52, 1.62, 1275, 610, 1285, 610),
        "ch3_time_buy":     (1.50, 1.56, 1280, 610, 1285, 610),
        "ch3_zhalantos_long":(1.30, 1.18, 1100, 660, 960, 675),
        "to_1680":          (1.24, 1.44, 880, 630, 720, 645),
        "ch4_law_spread":   (1.14, 1.08, 760, 610, 880, 520),
        "to_1726":          (1.16, 1.34, 860, 530, 795, 670),
        "ch5_jylu_route":   (1.16, 1.24, 720, 520, 820, 560),
        "ch5_liberation":   (1.26, 1.12, 1080, 620, 920, 540),
        "to_1771":          (1.10, 1.12, 860, 540, 940, 480),
        "ch6_squeeze":      (1.06, 1.08, 960, 510, 960, 520),
        "ch6_speed_120":    (1.20, 1.36, 980, 500, 1340, 450),
        "ch6_wave1":        (1.34, 1.44, 1180, 610, 1260, 650),
        "ch6_wave2":        (1.34, 1.42, 1350, 520, 1490, 390),
        "to_summary":       (1.26, 1.04, 1280, 460, 960, 520),
        "epilogue_border":  (1.04, 1.04, 960, 520, 960, 520),
    }
    z0, z1, cx0, cy0, cx1, cy1 = cams.get(mid, (1.10, 1.15, 960, 520, 960, 520))
    cam = WidescreenMapCamera(z0 + (z1 - z0) * e, cx0 + (cx1 - cx0) * e, cy0 + (cy1 - cy0) * e)
    hi = build_widescreen_relief_map()
    box_2x = (cam.x0 * 2.0, cam.y0 * 2.0, (cam.x0 + cam.vw) * 2.0, (cam.y0 + cam.vh) * 2.0)
    bg = hi.transform((W, H), Image.Transform.EXTENT, box_2x, Image.Resampling.BILINEAR).convert("RGB")
    d = ImageDraw.Draw(bg, "RGBA")

    if mid in {"prologue_wide", "epilogue_border", "ch1_expansion"}:
        poly_w = [C["Сарайшық"], C["Көкшетау"], C["Алтай"], C["Зайсан"], C["Тарбағатай"], C["Жетісу"], C["Ташкент"], C["Түркістан"], C["Сарайшық"]]
        s_poly = [cam.to_screen(x, y) for x, y in poly_w]
        if mid != "prologue_wide":
            d.polygon(s_poly[:-1], fill=(*GOLD, int(36 * p)))
        dense = eval_polyline(tuple(poly_w), 150)
        nd = max(3, int(len(dense) * min(1.0, u / 0.72)))
        pts = [cam.to_screen(x, y) for x, y in dense[:nd]]
        d.line(pts, fill=(*CYAN, 115), width=16, joint="curve")
        d.line(pts, fill=(*GOLD, 242), width=6, joint="curve")
        for cn in ("Сарайшық", "Ұлытау", "Көкшетау", "Түркістан", "Ташкент", "Жетісу", "Тарбағатай", "Зайсан", "Алтай"):
            draw_city_node(d, cam, cn, "kazakh", 0.0, t, emphasis=(cn in {"Көкшетау", "Түркістан", "Ұлытау"}))
        if mid == "prologue_wide":
            draw_map_callout(d, "АШЫҚ ДАЛА • 2 700 000 ШАРШЫ ШАҚЫРЫМ", "ТАС ҚАМАЛСЫЗ 260 ЖЫЛДЫҚ ҚОРҒАНЫС ШЕБІ", col=GOLD)
        elif mid == "ch1_expansion":
            draw_arrow_map(d, cam, [C["Ұлытау"], C["Сарайшық"]], p, t, width=10)
            draw_arrow_map(d, cam, [C["Ұлытау"], C["Көкшетау"], C["Алтай"]], p, t, width=10)
            draw_map_callout(d, "1511–1521 • ЕДІЛДЕН ЕРТІСКЕ КЕҢЕЮ", "ҚАСЫМ ХАН ТҰСЫНДА ХАЛЫҚ САНЫ 1 МИЛЛИОННАН АСТЫ", col=GOLD)
        else:
            draw_map_callout(d, "ТҰТАС ҚАЗАҚ ОРДАСЫ • ЖАЙЫҚ – АЛТАЙ", "АЛТЫ ҰЛЫ ЖЕҢІСПЕН БЕКІГЕН МИЛЛИОН ШАҚЫРЫМ ДАЛА", col=GOLD, w=740)

    elif mid in {"to_1510", "ch1_embargo"}:
        draw_arrow_map(d, cam, [C["Бұхара"], C["Сығанақ"], (640, 445)], p, t, col_main=RED, col_glow=(255, 130, 110), width=11)
        for cn in ("Сарайшық", "Көкшетау", "Ұлытау", "Сығанақ", "Түркістан", "Бұхара"):
            draw_city_node(d, cam, cn, "red" if cn == "Бұхара" else "kazakh", 0.0, t, emphasis=(cn == "Ұлытау"))
        draw_map_callout(d, "1510 • ҰЛЫТАУ БАҒЫТЫНДАҒЫ ҚЫСҚЫ ҚЫСЫМ", "ОҢТҮСТІК САУДА ШЕКТЕЛІП, ОРТАЛЫҚҚА ЖОРЫҚ БАСТАЛДЫ", col=RED)

    elif mid in {"to_1598", "ch2_prep", "ch2_cascade", "ch2_bukhara", "ch2_200years"}:
        route = [C["Сығанақ"], C["Түркістан"], C["Ташкент"], C["Самарқан"], C["Бұхара"]]
        draw_arrow_map(d, cam, route, p, t, width=11)
        px, py, _ = point_along_path(eval_polyline(tuple(route), 80), min(0.95, p * 0.94))
        draw_unit_badge_map(d, cam, px, py, "ТӘУЕКЕЛ • ЕР ЕСІМ (100 000)", t)
        for idx, cn in enumerate(["Сығанақ", "Түркістан", "Ташкент", "Самарқан", "Бұхара"]):
            thr = idx * 0.19
            st = "kazakh" if (mid == "ch2_200years" or u >= thr + 0.1) else ("capturing" if u >= thr else "red")
            draw_city_node(d, cam, cn, st, max(0.0, (u - thr) / 0.15) if st == "capturing" else 0.0, t, emphasis=(cn in {"Түркістан", "Ташкент"}))
        ttl = "1598–1798 • 200 ЖЫЛДЫҚ ҚОРҒАН БЕЛДЕУІ" if mid == "ch2_200years" else "1598 • ОҢТҮСТІК БЛИЦКРИГ ЖОРЫҒЫ"
        draw_map_callout(d, ttl, "СЫҒАНАҚ – ТҮРКІСТАН – ТАШКЕНТ – САМАРҚАН – БҰХАРА", col=GOLD, x=1180, w=688)

    elif mid in {"to_1643", "ch3_locate", "ch3_time_buy", "ch3_zhalantos_long"}:
        ox, oy = C["Орбұлақ"]
        draw_arrow_map(d, cam, [(1530, 520), (1410, 565), (ox + 32, oy - 10)], min(1.0, p * 1.1), t, col_main=RED, col_glow=(255, 130, 110), width=12)
        if mid == "ch3_zhalantos_long":
            fl = [C["Самарқан"], C["Ташкент"], C["Жетісу"], C["Орбұлақ"]]
            draw_arrow_map(d, cam, fl, p, t, width=12)
            px, py, _ = point_along_path(eval_polyline(tuple(fl), 80), min(0.95, p * 0.94))
            draw_unit_badge_map(d, cam, px, py, "ЖАЛАҢТӨС (+20 000 АТТЫ ӘСКЕР)", t, col=CYAN)
            for cn in ("Самарқан", "Ташкент", "Жетісу", "Орбұлақ"):
                draw_city_node(d, cam, cn, "kazakh", 0.0, t, emphasis=(cn in {"Самарқан", "Орбұлақ"}))
            draw_map_callout(d, "1643 • САМАРҚАННАН ЖЕДЕЛ КӨМЕК", "ЖАЛАҢТӨС БАҺАДҮР 20 000 ҚОЛМЕН ЖЕТІП, ТЫЛДАН СОҚҚЫ БЕРДІ", col=GOLD, x=1160, w=710)
        else:
            sx, sy = cam.to_screen(ox, oy)
            for rr in (48, 86):
                d.arc([sx - rr, sy - rr, sx + rr, sy + rr], 290, 90, fill=(*CYAN, 230), width=5)
            draw_city_node(d, cam, "Орбұлақ", "capturing", (t * 0.8) % 1.0, t, emphasis=True)
            draw_city_node(d, cam, "Жетісу", "kazakh", 0.0, t)
            draw_unit_badge_map(d, cam, ox, oy, "600 САРБАЗ • УАҚЫТ ҰТУ", t, col=CYAN)
            draw_map_callout(d, "1643 • ОРБҰЛАҚ ШАТҚАЛЫ", "50 000 ҚОЛ ТАР АСУДА ОДАҚТАС ЖЕТКЕНШЕ БӨГЕЛДІ", col=CYAN)

    elif mid in {"to_1680", "ch4_law_spread"}:
        sx, sy = cam.to_screen(*C["Түркістан"])
        for ri in range(3):
            rp = ((t * 0.45 + ri * 0.33) % 1.0)
            rr = int(50 + rp * 440)
            d.ellipse([sx - rr, sy - rr, sx + rr, sy + rr], outline=(*GOLD, int(205 * (1.0 - rp))), width=4)
        for src in (C["Сарайшық"], C["Көкшетау"], C["Жетісу"]):
            draw_arrow_map(d, cam, [C["Түркістан"], src], p, t, col_main=CYAN, col_glow=GOLD, width=8)
        for cn in ("Сарайшық", "Ұлытау", "Көкшетау", "Түркістан", "Жетісу"):
            draw_city_node(d, cam, cn, "kazakh", 0.0, t, emphasis=(cn == "Түркістан"))
        draw_map_callout(d, "~1680 • ТҮРКІСТАННАН БҮКІЛ ДАЛАҒА", "«ЖЕТІ ЖАРҒЫ» ҮШ ЖҮЗДІҢ ОРТАҚ ҚҰҚЫҚ ЖҮЙЕСІНЕ АЙНАЛДЫ", col=GOLD, x=1160, w=710)

    elif mid in {"to_1726", "ch5_jylu_route", "ch5_liberation"}:
        target = C["Аңырақай"] if mid == "ch5_liberation" else C["Ордабасы"]
        srcs = [C["Сарайшық"], C["Ұлытау"], C["Көкшетау"], C["Жетісу"]]
        for src in srcs:
            pts = [target, src] if mid == "ch5_liberation" else [src, target]
            draw_arrow_map(d, cam, pts, p, t, col_main=GOLD if mid != "ch5_jylu_route" else CYAN, width=10)
        for cn in ("Сарайшық", "Ұлытау", "Бұланты", "Көкшетау", "Түркістан", "Ордабасы", "Аңырақай", "Жетісу"):
            draw_city_node(d, cam, cn, "capturing" if cn in {"Ордабасы", "Аңырақай"} else "kazakh", 0.0, t, emphasis=(cn in {"Ордабасы", "Аңырақай"}))
        ttl = "1726–1730 • «ЖЫЛУ» ТҰЛПАР КОНВЕЙЕРІ (2 000 КМ)" if mid == "ch5_jylu_route" else "1726–1730 • БІРТҰТАС АЗАТТЫҚ ЖЕҢІСІ"
        draw_map_callout(d, ttl, "БАТЫС ПЕН СОЛТҮСТІКТЕН ОҢТҮСТІК МАЙДАНҒА ҮЗДІКСІЗ ҚОЛДАУ", col=GOLD)

    else:
        # Chapter 6: 1771 Abylai squeeze + Eastern rapid sweep
        if mid in {"ch6_squeeze", "to_1771", "to_summary"}:
            draw_arrow_map(d, cam, [(480, 145), (670, 210), (790, 235)], p, t, col_main=RED, col_glow=(255, 130, 110), width=11)
            draw_arrow_map(d, cam, [(1120, 145), (960, 200), (855, 235)], p, t, col_main=RED, col_glow=(255, 130, 110), width=11)
            draw_arrow_map(d, cam, [(1850, 420), (1680, 435), (1500, 455)], p, t, col_main=RED, col_glow=(255, 130, 110), width=11)
            for cn in ("Сарайшық", "Көкшетау", "Ұлытау", "Түркістан", "Жетісу", "Тарбағатай", "Зайсан", "Алтай"):
                draw_city_node(d, cam, cn, "red" if cn in {"Тарбағатай", "Зайсан", "Алтай"} else "kazakh", 0.0, t, emphasis=(cn in {"Көкшетау", "Түркістан"}))
            draw_map_callout(d, "1771 • ЕКІ ИМПЕРИЯ АРАСЫНДАҒЫ ТЕПЕ-ТЕҢДІК", "СОЛТҮСТІК РЕСЕЙ БЕКІНІСІ • ШЫҒЫС ЦИН ҚЫСЫМЫ", col=RED)
            draw_seesaw_scale(d, tau, t, x0=1210, y0=710, w=660, h=156)
        else:
            east = [C["Көкшетау"], C["Аңырақай"], C["Жетісу"], C["Тарбағатай"], C["Зайсан"], C["Алтай"]]
            draw_arrow_map(d, cam, east, p, t, width=12)
            px, py, _ = point_along_path(eval_polyline(tuple(east), 80), min(0.95, p * 0.94))
            draw_unit_badge_map(d, cam, px, py, "ҚАБАНБАЙ • БӨГЕНБАЙ (120 км/тәу)", t)
            for idx, cn in enumerate(["Жетісу", "Тарбағатай", "Зайсан", "Алтай"]):
                thr = 0.14 + idx * 0.20
                st = "kazakh" if (u >= thr + 0.1 or mid == "ch6_wave2") else ("capturing" if u >= thr else "red")
                draw_city_node(d, cam, cn, st, 0.0, t, emphasis=(cn in {"Жетісу", "Тарбағатай", "Зайсан"}))
            draw_city_node(d, cam, "Көкшетау", "kazakh", 0.0, t)
            draw_map_callout(d, "ШЫҒЫС ЖАЙЛАУЛАРЫ ОРАЛДЫ (×3 ЖЫЛДАМДЫҚ)", "ЖЕТІСУ • ІЛЕ • ТАРБАҒАТАЙ • ЗАЙСАН • АЛТАЙ", col=GOLD, x=1160, w=710)

    return bg


# ---------------------------------------------------------------------------
# MODE 3: ORDER OF BATTLE (HEAD-TO-HEAD DUELS & WAFFLE UNIT GRIDS)
# ---------------------------------------------------------------------------
def render_order_of_battle(sc: dict, u: float, tau: float, t: float) -> Image.Image:
    im = get_blueprint_bg().copy()
    d = ImageDraw.Draw(im, "RGBA")
    pop = ease_out(min(1.0, tau / 0.28))

    # Left panel: Forces Duel & Animated Waffle Block Matrix
    lx0, ly0, lw, lh = 48, 114, 1188, 782
    d.rounded_rectangle([lx0, ly0, lx0 + lw, ly0 + lh], radius=22, fill=(11, 18, 28, int(235 * pop)), outline=(*CYAN, 195), width=3)

    # Left vs Right Score Header Boxes
    mid_x = lx0 + lw // 2
    d.rounded_rectangle([lx0 + 28, ly0 + 24, mid_x - 36, ly0 + 160], radius=16, fill=(22, 34, 48, 235), outline=(*GOLD, 240), width=3)
    d.text((lx0 + 52, ly0 + 40), sc["left_title"], font=get_font(22), fill=(*CYAN, 250))
    d.text((lx0 + 52, ly0 + 78), sc["left_num"], font=get_font(44), fill=(*GOLD, 255))

    # VS pill
    d.ellipse([mid_x - 28, ly0 + 62, mid_x + 28, ly0 + 118], fill=(16, 24, 34, 255), outline=(*WHITE, 230), width=2)
    d.text((mid_x - 16, ly0 + 78), "VS", font=get_font(22), fill=(*WHITE, 255))

    d.rounded_rectangle([mid_x + 36, ly0 + 24, lx0 + lw - 28, ly0 + 160], radius=16, fill=(36, 18, 22, 235), outline=(*RED, 240), width=3)
    d.text((mid_x + 60, ly0 + 40), sc["right_title"], font=get_font(22), fill=(255, 165, 155, 250))
    d.text((mid_x + 60, ly0 + 78), sc["right_num"], font=get_font(44), fill=(*RED, 255))

    cur_y = ly0 + 190
    if "waffle" in sc:
        n_kaz, n_foe, wdesc = sc["waffle"]
        d.text((lx0 + 32, cur_y), wdesc, font=get_font(20), fill=(*WHITE, 245))
        cur_y += 42
        cols, sz, gap = 17, 46, 12
        tot_blocks = n_kaz + n_foe
        n_lit = max(1, int(tot_blocks * ease_out(min(1.0, tau / 1.35))))
        for bi in range(tot_blocks):
            r_idx, c_idx = bi // cols, bi % cols
            bx, by = lx0 + 32 + c_idx * (sz + gap), cur_y + r_idx * (sz + gap)
            is_kaz = (bi < n_kaz)
            if bi < n_lit:
                fc = (*GOLD, 245) if is_kaz else (*RED, 230)
                oc = (*CYAN, 255) if is_kaz else (255, 130, 120, 220)
            else:
                fc, oc = (24, 34, 46, 140), (60, 80, 95, 120)
            d.rounded_rectangle([bx, by, bx + sz, by + sz], radius=8, fill=fc, outline=oc, width=2)
        d.text((lx0 + 32, cur_y + 210), "АНЫҚТАМА: 1 ЖЕҢІЛ САРБАЗ РЕЛЬЕФ ПЕН ОҚПАН АРҚЫЛЫ 83 ЖАУДЫ ТОҚТАТТЫ", font=get_font(19), fill=(*CYAN, 245))

    if "bars" in sc:
        fb = get_font(22)
        bw = lw - 68
        for idx, (lbl, frac, cname) in enumerate(sc["bars"]):
            col = PALETTE.get(cname, GOLD)
            af = frac * ease_out(min(1.0, max(0.0, (tau - 0.12 * idx) / 0.60)))
            d.text((lx0 + 32, cur_y), lbl, font=fb, fill=(*WHITE, 250))
            by = cur_y + 34
            d.rounded_rectangle([lx0 + 32, by, lx0 + 32 + bw, by + 34], radius=10, fill=(20, 30, 44, 240), outline=(90, 120, 140, 175), width=2)
            d.rounded_rectangle([lx0 + 32, by, lx0 + 32 + max(20, int(bw * af)), by + 34], radius=10, fill=(*col, 245))
            pct_txt = f"{int(round(af * 100))}%"
            d.text((lx0 + 44, by + 6), pct_txt, font=get_font(18), fill=(12, 16, 22, 255) if af > 0.25 else (*WHITE, 245))
            cur_y += 96
        if cur_y <= ly0 + lh - 120:
            by_f = ly0 + lh - 122
            d.rounded_rectangle([lx0 + 32, by_f, lx0 + lw - 32, ly0 + lh - 26], radius=14, fill=(16, 26, 38, 245), outline=(*GOLD, 165), width=2)
            d.text((lx0 + 54, by_f + 16), "ТАКТИКАЛЫҚ АРТЫҚШЫЛЫҚ ҚОРЫТЫНДЫСЫ", font=get_font(18), fill=(*CYAN, 245))
            d.text((lx0 + 54, by_f + 48), sc["sub"], font=get_font(20), fill=(*GOLD, 252))

    # Right panel: Photo preview + analytical takeaway card
    rx0, rw = 1264, 608
    vp = crop_rigid_viewport(load_plate(sc["plate"]), rw, 440, u, tau, cy_focus=0.44)
    im.paste(vp, (rx0, 114))
    d = ImageDraw.Draw(im, "RGBA")
    d.rounded_rectangle([rx0, 114, rx0 + rw, 554], radius=18, outline=(*GOLD, 225), width=3)

    d.rounded_rectangle([rx0, 574, rx0 + rw, 896], radius=20, fill=(10, 16, 24, 236), outline=(*CYAN, 220), width=3)
    d.text((rx0 + 26, 594), sc.get("card_tag", "АНАЛИТИКА"), font=get_font(18), fill=(*CYAN, 250))
    d.text((rx0 + 26, 626), sc["card_title"], font=get_font(29), fill=(*GOLD, 255))
    if "counter" in sc:
        tnum, suf, desc = sc["counter"]
        val = int(round(tnum * ease_out(min(1.0, tau / 1.0))))
        d.text((rx0 + 26, 684), f"{val}{suf}", font=get_font(56), fill=(*WHITE, 255))
        d.text((rx0 + 26, 756), desc, font=get_font(18), fill=(*MUTED, 240))
    else:
        d.text((rx0 + 26, 692), "ОРДА СТРАТЕГИЯСЫ:", font=get_font(20), fill=(*WHITE, 245))
        d.text((rx0 + 26, 728), "ЖЫЛДАМДЫҚ + РЕЛЬЕФ + БІРЛІК", font=get_font(24), fill=(*GOLD, 250))
        d.text((rx0 + 26, 772), "КҮШ ТЕҢСІЗДІГІН ТҮБЕГЕЙЛІ ӨЗГЕРТТІ", font=get_font(19), fill=(*CYAN, 235))
    return im


# ---------------------------------------------------------------------------
# MODE 4: SYSTEM DIAGRAM (FLOWCHARTS, 7 PILLARS, SEESAW GEOPOLITICS)
# ---------------------------------------------------------------------------
DIAGRAM_CONFIGS = {
    "four_pillars": {
        "hub": ("ДАЛА", "4 ТІРЕГІ"),
        "nodes": [
            ("1. ЖЕР ЖӘНЕ КЛИМАТ", "Аяз, тар шатқал, шөл"),
            ("2. ШАПШАҢ ЛОГИСТИКА", "Қос атты легі (×3 қарқын)"),
            ("3. ОРТАҚ ЗАҢ", "Құрылтай мен билер соты"),
            ("4. ДИПЛОМАТИЯ", "Қос империя тепе-теңдігі"),
        ],
    },
    "kaska_zhol": {
        "hub": ("ҚАСЫМ ХАН", "ҚАСҚА ЖОЛЫ"),
        "nodes": [
            ("1. МҮЛІК ЗАҢЫ", "Жер, мал мен мұра тәртібі"),
            ("2. ҚЫЛМЫС ЗАҢЫ", "Қоғамдық тәртіп пен жаза"),
            ("3. ӘСКЕРИ ЖАРАҚ", "Жұмылдыру мен шекара қорғау"),
            ("4. ЕЛШІЛІК ЖОЛЫ", "Мемлекеттік хат алмасу"),
            ("5. ЖҰРТШЫЛЫҚ", "Хандық пен халық бірлігі"),
        ],
    },
    "south_value": {
        "hub": ("СЫР БОЙЫ", "ТІРЕК ҚАЛАЛАРЫ"),
        "nodes": [
            ("ЖЫЛЫ ҚЫСТАУ", "Малды қыстан аман шығару"),
            ("ҚАРУ ҰСТАХАНАСЫ", "Болат пен оқ-дәрі өндірісі"),
            ("ЖІБЕК ЖОЛЫ", "Тұрақты сауда табысы"),
            ("ХАН ОРДАСЫ", "Түркістан — саяси орталық"),
        ],
    },
    "city_steppe_loop": {
        "hub": ("ҚАЛА + ДАЛА", "ТҰТАС ЖҮЙЕ"),
        "nodes": [
            ("КӨШПЕЛІ МАЛ", "Жеткілікті ет пен ат қоры"),
            ("ҚАЛА ҚОЛӨНЕРІ", "Қару, мата және зергерлік"),
            ("САУДА КЕРУЕНІ", "Кіріс және дипломатия"),
            ("БЕРІК ШЕКАРА", "Қорғаныс шебі 200 жыл"),
        ],
    },
    "three_bis": {
        "hub": ("ТӘУКЕ ХАН", "КҮЛТӨБЕ КЕҢЕСІ"),
        "nodes": [
            ("ТӨЛЕ БИ (ҰЛЫ ЖҮЗ)", "Тура билік пен ел іргесі"),
            ("ҚАЗЫБЕК БИ (ОРТА ЖҮЗ)", "Дипломатия мен шешендік"),
            ("ӘЙТЕКЕ БИ (КІШІ ЖҮЗ)", "Тәртіп пен батыс қорғанысы"),
        ],
    },
    "jeti_zhargy": {
        "hub": ("ЖЕТІ ЖАРҒЫ", "ДАЛА ЗАҢЫ"),
        "nodes": [
            ("1. ЖЕР-ЖАЙЫЛЫМ", "Қыстау-жайлау нақты бөлінді"),
            ("2. ОТАН ҚОРҒАУ", "Қауіпте жаппай жасаққа шығу"),
            ("3. ЕЛШІЛІК ЗАҢЫ", "Елші өмірі — қол сұғылмас"),
            ("4. БИЛЕР СОТЫ", "Қанды кексіз әділ бітім"),
            ("5-6. ҚАЗЫНА & ҚОРҒАУ", "Салық пен отбасы кепілдігі"),
            ("7. ЖЫЛДЫҚ ҚҰРЫЛТАЙ", "Күзгі жалпыұлттық шешім"),
        ],
    },
    "ordabasy_staff": {
        "hub": ("ӘБІЛҚАЙЫР", "БАС САРДАР"),
        "nodes": [
            ("ҚАНЖЫҒАЛЫ БӨГЕНБАЙ", "Тәжірибелі қолбасшы • Оң қанат"),
            ("ҚАРАКЕРЕЙ ҚАБАНБАЙ", "Екпінді шабуыл • Сол қанат"),
            ("РАЙЫМБЕК БАТЫР", "Оңтүстік-шығыс қорғанысы"),
            ("МАЛАЙСАРЫ БАТЫР", "Барлау мен авангард шебі"),
        ],
    },
    "jylu_network": {
        "hub": ("ЖЫЛУ ЗАҢЫ", "2 000 КМ ЖЕЛІ"),
        "nodes": [
            ("БАТЫС ӨҢІР", "Он мыңдаған төзімді тұлпар"),
            ("ОРТАЛЫҚ & СОЛТҮСТІК", "Ер-тұрман, азық, темір қару"),
            ("ТҮРКІСТАН ШТАБЫ", "Жинау және бөлу бекеті"),
            ("АҢЫРАҚАЙ МАЙДАНЫ", "Үздіксіз ауысым аттары"),
        ],
    },
    "abylai_seesaw": {
        "hub": ("АБЫЛАЙ ХАН", "ТЕПЕ-ТЕҢДІК"),
        "nodes": [
            ("СОЛТҮСТІК: РЕСЕЙ", "Шекара саудасы & хат алмасу"),
            ("ШЫҒЫС: ЦИН", "Шығыс жайлауларға еркін жол"),
            ("ТҮРКІСТАН ОРДАСЫ", "Оңтүстік рухани & саяси тірек"),
            ("КӨКШЕТАУ ОРДАСЫ", "Солтүстік дипломатиялық орталық"),
        ],
    },
    "abylai_state": {
        "hub": ("1771 ОРДА", "ИНФРАҚҰРЫЛЫМ"),
        "nodes": [
            ("САУДА КЕРУЕНІ", "Бұхара, Омбы, Құлжа бағыттары"),
            ("МЕТАЛЛ & ҚОЛӨНЕР", "Қару мен ауыл шаруашылығы"),
            ("ДИПЛОМАТИЯ", "Кәсіби елшілік хаттамасы"),
            ("ТҰТАС ШЕКАРА", "Жайық пен Ертістен Алтайға"),
        ],
    },
}


def render_system_diagram(sc: dict, u: float, tau: float, t: float) -> Image.Image:
    im = get_blueprint_bg().copy()
    d = ImageDraw.Draw(im, "RGBA")
    cfg = DIAGRAM_CONFIGS[sc["diag_id"]]
    act_idx = sc.get("active_node", -1)
    nodes = cfg["nodes"]
    n_cnt = len(nodes)

    cx, cy = W // 2, 504
    if sc["diag_id"] == "abylai_seesaw":
        cy = 355

    # Compute node coordinates radially cleanly inside y=145..865
    coords = []
    if n_cnt == 3:
        pos_list = [(W // 2, 220), (420, 725), (1500, 725)]
    elif n_cnt == 4:
        if sc["diag_id"] == "abylai_seesaw":
            pos_list = [(400, 225), (1520, 225), (400, 505), (1520, 505)]
        else:
            pos_list = [(420, 295), (1500, 295), (420, 705), (1500, 705)]
    elif n_cnt == 5:
        pos_list = [(W // 2, 200), (1520, 385), (1440, 745), (480, 745), (400, 385)]
    else:
        pos_list = [(390, 240), (1530, 240), (350, 504), (1570, 504), (390, 768), (1530, 768)]

    for idx, (nx, ny) in enumerate(pos_list[:n_cnt]):
        coords.append((nx, ny))
        is_act = (act_idx == -1 and tau > idx * 0.14) or (idx == act_idx)
        lcol = GOLD if idx == act_idx else (CYAN if is_act else (85, 110, 128))
        lwid = 6 if idx == act_idx else 3
        d.line([(cx, cy), (nx, ny)], fill=(*lcol, 210 if is_act else 110), width=lwid)
        # Moving energy pulse packet along connector
        if is_act:
            pf = (t * 0.85 + idx * 0.22) % 1.0
            px, py = cx + (nx - cx) * pf, cy + (ny - cy) * pf
            d.ellipse([px - 7, py - 7, px + 7, py + 7], fill=(*GOLD, 250))

    # Draw outer nodes
    fn_k, fn_v = get_font(22), get_font(19)
    bw, bh = 540, 112
    for idx, ((nx, ny), (nk, nv)) in enumerate(zip(coords, nodes)):
        is_hl = (idx == act_idx)
        lit = (act_idx == -1 and tau >= idx * 0.14) or is_hl
        pop = ease_out(min(1.0, max(0.0, (tau - idx * 0.08) / 0.30)))
        fc = (22, 34, 48, 252) if is_hl else ((13, 22, 33, 250) if lit else (14, 18, 26, 245))
        oc = (*GOLD, 255) if is_hl else ((*CYAN, 215) if lit else (75, 95, 112, 185))
        rx0, ry0 = nx - bw // 2, ny - bh // 2
        d.rounded_rectangle([rx0, ry0, rx0 + bw, ry0 + bh], radius=16, fill=fc, outline=oc, width=3 if is_hl else 2)
        d.text((rx0 + 24, ry0 + 18), nk, font=fn_k, fill=(*GOLD, 255) if is_hl else (*CYAN, 250))
        d.text((rx0 + 24, ry0 + 58), nv, font=fn_v, fill=(*WHITE, 250) if lit else (*MUTED, 210))

    # Central glowing Hub
    pulse = 1.0 + 0.06 * math.sin(t * 4.0)
    hr = int(124 * pulse)
    d.ellipse([cx - hr - 12, cy - hr - 12, cx + hr + 12, cy + hr + 12], outline=(*CYAN, 110), width=3)
    d.ellipse([cx - hr, cy - hr, cx + hr, cy + hr], fill=(12, 22, 34, 248), outline=(*GOLD, 250), width=4)
    h1, h2 = cfg["hub"]
    fh1, fh2 = get_font(28), get_font(20)
    d.text((cx - d.textlength(h1, font=fh1) / 2, cy - 30), h1, font=fh1, fill=(*GOLD, 255))
    d.text((cx - d.textlength(h2, font=fh2) / 2, cy + 12), h2, font=fh2, fill=(*CYAN, 245))

    if sc["diag_id"] == "abylai_seesaw":
        draw_seesaw_scale(d, tau, t, x0=560, y0=695, w=800, h=172)
    return im


# ---------------------------------------------------------------------------
# MODE 5: TIMELINE CHRONICLE (1510..1771 SCRUBBER + DUAL CINEMA PLATES)
# ---------------------------------------------------------------------------
def render_timeline_chronicle(sc: dict, u: float, tau: float, t: float) -> Image.Image:
    im = get_blueprint_bg().copy()
    d = ImageDraw.Draw(im, "RGBA")

    # Top chronological track bar (y: 120..290)
    tx0, ty0, tx1, ty1 = 48, 116, W - 48, 294
    d.rounded_rectangle([tx0, ty0, tx1, ty1], radius=20, fill=(10, 16, 24, 232), outline=(*CYAN, 185), width=2)
    line_y = 198
    sx0, sx1 = tx0 + 110, tx1 - 110
    d.line([(sx0, line_y), (sx1, line_y)], fill=(70, 95, 115, 220), width=6)

    i0, i1 = sc["era_idx"], sc["era_to"]
    cur_era = i0 + (i1 - i0) * smoothstep(min(1.0, u / 0.80))
    step_x = (sx1 - sx0) / (len(TIMELINE_ERAS) - 1)
    cur_x = sx0 + cur_era * step_x
    d.line([(sx0, line_y), (cur_x, line_y)], fill=(*GOLD, 248), width=8)

    f_yr, f_nm = get_font(22), get_font(16)
    for ei, (yr, nm, _) in enumerate(TIMELINE_ERAS):
        ex = sx0 + ei * step_x
        past = (ei <= cur_era + 0.05)
        is_tgt = (ei == i1)
        r = 16 if is_tgt else 11
        fc = (*GOLD, 255) if is_tgt else ((*CYAN, 240) if past else (24, 34, 46, 240))
        d.ellipse([ex - r, line_y - r, ex + r, line_y + r], fill=fc, outline=(*WHITE, 235), width=2)
        d.text((ex - d.textlength(yr, font=f_yr) / 2, line_y - 50), yr, font=f_yr, fill=(*GOLD, 255) if is_tgt else (*WHITE, 230))
        d.text((ex - d.textlength(nm, font=f_nm) / 2, line_y + 26), nm, font=f_nm, fill=(*CYAN, 245) if past else (*MUTED, 195))

    # Sweeping golden cursor ring
    d.ellipse([cur_x - 21, line_y - 21, cur_x + 21, line_y + 21], outline=(*GOLD, 220), width=3)

    # Lower Dual Cinema Viewports + Synthesis Dossier (y: 316..896)
    vh = 580
    vp1 = crop_rigid_viewport(load_plate(sc["plates"][0]), 592, vh, u, tau, cy_focus=0.44)
    vp2 = crop_rigid_viewport(load_plate(sc["plates"][1]), 592, vh, u, tau, cy_focus=0.45)
    im.paste(vp1, (48, 316))
    im.paste(vp2, (660, 316))
    d = ImageDraw.Draw(im, "RGBA")
    d.rounded_rectangle([48, 316, 640, 896], radius=16, outline=(*CYAN, 220), width=3)
    d.rounded_rectangle([660, 316, 1252, 896], radius=16, outline=(*GOLD, 220), width=3)

    draw_dossier_right(d, sc, tau, t, x0=1274, y0=316, w=598, h=580)
    return im


# ---------------------------------------------------------------------------
# MODE 6: CINEMA MONTAGE (2-CUT SUBPIXEL CAMERA + WEATHER + DOSSIER)
# ---------------------------------------------------------------------------
def render_cinema_montage(sc: dict, u: float, tau: float, seg_dur: float, t: float) -> Image.Image:
    pls = sc["plates"]
    cut_idx = 0 if (u < 0.50 or len(pls) < 2) else 1
    su = (u / 0.50) if cut_idx == 0 else ((u - 0.50) / 0.50)
    stau = tau if cut_idx == 0 else max(0.0, tau - seg_dur * 0.50)
    pl = pls[cut_idx]

    im = load_ambient_wide(pl).copy()
    vp = crop_rigid_viewport(load_plate(pl), 1184, 782, su, stau, cy_focus=0.45, shake=(sc.get("weather") == "arrows" and cut_idx == 0))
    im.paste(vp, (48, 114))
    d = ImageDraw.Draw(im, "RGBA")
    oc = GOLD if cut_idx == 0 else CYAN
    d.rounded_rectangle([48, 114, 1232, 896], radius=20, outline=(*oc, 235), width=4)

    wtype = sc.get("weather", "dust")
    if wtype == "snow":
        for k in range(38):
            sx = 56 + ((k * 71 + int(t * 260)) % 1160)
            sy = 122 + ((k * 53 + int(t * 95)) % 760)
            d.ellipse([sx, sy, sx + 5, sy + 5], fill=(235, 245, 255, 190))
    elif wtype == "arrows":
        for k in range(26):
            ph = (t * (1.2 + (k % 4) * 0.25) + k * 0.618) % 1.0
            ax = 60 + ph * 1140
            ay = 160 + ((k * 79) % 660) - math.sin(ph * math.pi) * 28.0
            d.line([(ax - 44, ay + 10), (ax, ay)], fill=(255, 224, 130, 195), width=3)
    else:
        for k in range(24):
            sx = 60 + ((k * 97 + int(t * 70)) % 1150)
            sy = 160 + ((k * 67 + int(t * 25)) % 680)
            d.ellipse([sx, sy, sx + 4, sy + 4], fill=(248, 212, 120, 145))

    draw_dossier_right(d, sc, tau, t, x0=1264, y0=114, w=608, h=782)
    return im


def render_scene_frame(sc: dict, u: float, tau: float, seg_dur: float, t: float) -> Image.Image:
    mode = sc["mode"]
    if mode == "tactical_battle":
        return render_tactical_battle(sc, u, tau, t)
    if mode == "strategic_atlas":
        return render_strategic_atlas(sc, u, tau, t)
    if mode == "order_of_battle":
        return render_order_of_battle(sc, u, tau, t)
    if mode == "system_diagram":
        return render_system_diagram(sc, u, tau, t)
    if mode == "timeline_chronicle":
        return render_timeline_chronicle(sc, u, tau, t)
    return render_cinema_montage(sc, u, tau, seg_dur, t)


# ---------------------------------------------------------------------------
# CACHED HUD & KARAOKE SUBTITLES
# ---------------------------------------------------------------------------
_HUD_CACHE = {}


def get_hud_top_strip(si: int, step_a: int) -> Image.Image:
    key = (si, step_a)
    if key in _HUD_CACHE:
        return _HUD_CACHE[key]
    sc = SCENES[si]
    alpha_in = step_a / 5.0
    strip = Image.new("RGBA", (W, 106), (0, 0, 0, 0))
    d = ImageDraw.Draw(strip)

    bx_a, tx_a = int(round(225 * alpha_in)), int(round(252 * alpha_in))
    d.rounded_rectangle([48, 14, 1216, 94], radius=18, fill=(10, 16, 24, bx_a), outline=(*GOLD, int(230 * alpha_in)), width=2)
    d.text((72, 22), sc["top"], font=get_font(25), fill=(*GOLD, tx_a))
    d.text((72, 58), sc["sub"], font=get_font(17), fill=(*CYAN, tx_a))

    px0, px1 = 1236, W - 48
    d.rounded_rectangle([px0, 20, px1, 88], radius=16, fill=(10, 16, 24, 215), outline=(*CYAN, 155), width=2)
    slot_w = (px1 - px0 - 16) // len(CHAPTER_PILLS)
    fp = get_font(13)
    for idx, lbl in enumerate(CHAPTER_PILLS):
        sx0 = px0 + 8 + idx * slot_w + 2
        sx1 = sx0 + slot_w - 4
        is_act = (idx == sc["ch_idx"])
        fc = (*GOLD, 245) if is_act else (20, 30, 42, 195)
        oc = (255, 242, 180, 255) if is_act else (85, 130, 145, 150)
        tc = (12, 14, 20, 255) if is_act else (218, 228, 236, 230)
        d.rounded_rectangle([sx0, 28, sx1, 80], radius=9, fill=fc, outline=oc, width=2)
        d.text((sx0 + (sx1 - sx0 - d.textlength(lbl, font=fp)) / 2, 46), lbl, font=fp, fill=tc)

    if len(_HUD_CACHE) < 400:
        _HUD_CACHE[key] = strip
    return strip


def build_chunks_169(words: list, T: float) -> list:
    groups, cur = [], []
    for w in words:
        txt = w["w"].replace("—", "").strip()
        if not txt:
            continue
        txt = txt.upper()
        if cur and (len(cur) == 4 or sum(len(x["txt"]) + 1 for x in cur) + len(txt) > 34):
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
        end = nxt if nxt - g[-1]["t1"] < 0.55 else g[-1]["t1"] + 0.25
        out.append({"words": g, "t0": g[0]["t0"], "t1": min(end, nxt)})
    return out


_SUB_CACHE = {}


def render_sub_169(ci: int, words: list, active: int) -> Image.Image:
    key = (ci, active)
    if key in _SUB_CACHE:
        return _SUB_CACHE[key]
    txts = [w["txt"] for w in words]
    maxw = 1520
    f, sp, widths = get_font(52), 14.0, []
    for size in range(60, 42, -4):
        f = get_font(size)
        sp = f.getlength(" ")
        widths = [f.getlength(t) for t in txts]
        if sum(widths) + sp * (len(txts) - 1) <= maxw:
            break
    lines = [list(range(len(txts)))]
    if sum(widths) + sp * (len(txts) - 1) > maxw and len(txts) > 1:
        k = min(range(1, len(txts)), key=lambda idx: max(sum(widths[:idx]), sum(widths[idx:])))
        lines = [list(range(k)), list(range(k, len(txts)))]

    stroke = max(4, f.size // 12)
    asc, desc = f.getmetrics()
    lh, pad = asc + desc, 18
    lw = [sum(widths[i] for i in ln) + sp * (len(ln) - 1) for ln in lines]
    iw, ih = int(max(lw) + 2 * pad), int(lh * len(lines) + 2 * pad)
    shadow = Image.new("RGBA", (iw, ih), (0, 0, 0, 0))
    layer = Image.new("RGBA", (iw, ih), (0, 0, 0, 0))
    ds, dl = ImageDraw.Draw(shadow), ImageDraw.Draw(layer)
    for li, ln in enumerate(lines):
        x, y = (iw - lw[li]) / 2, pad + li * lh
        for i in ln:
            ds.text((x + 3, y + 5), txts[i], font=f, fill=(0, 0, 0, 210), stroke_width=stroke, stroke_fill=(0, 0, 0, 210))
            dl.text((x, y), txts[i], font=f, fill=(255, 198, 58, 255) if i == active else (255, 255, 255, 255), stroke_width=stroke, stroke_fill=(0, 0, 0, 255))
            x += widths[i] + sp
    shadow = shadow.filter(ImageFilter.GaussianBlur(6))
    shadow.alpha_composite(layer)
    if len(_SUB_CACHE) < 1200:
        _SUB_CACHE[key] = shadow
    return shadow


# ---------------------------------------------------------------------------
# VOICE SYNTHESIS & PHYSICAL + A CAPPELLA AUDIO MIX
# ---------------------------------------------------------------------------
async def _synth_line_async(text: str, voice: str, rate: str, pitch: str, mp3_path: Path):
    comm = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch, boundary="WordBoundary")
    bounds = []
    with open(mp3_path, "wb") as f:
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                bounds.append({"w": chunk["text"], "t0": chunk["offset"] / 1e7, "t1": (chunk["offset"] + chunk["duration"]) / 1e7})
    return bounds


def synth_line_with_retry(text: str, mp3_path: Path, wav_path: Path):
    txt_hash = hashlib.sha1(f"{text}|{VOICE_MAIN}|{VOICE_RATE}|{VOICE_PITCH}".encode("utf-8")).hexdigest()[:12]
    meta_path = wav_path.with_suffix(".json")
    if wav_path.exists() and wav_path.stat().st_size > 4000 and meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if isinstance(meta, dict) and meta.get("hash") == txt_hash:
            return meta["bounds"]

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
    meta_path.write_text(json.dumps({"hash": txt_hash, "bounds": bounds}, ensure_ascii=False), encoding="utf-8")
    return bounds


def read_wav_mono(path: Path) -> np.ndarray:
    with wave.open(str(path), "rb") as wf:
        raw = wf.readframes(wf.getnframes())
    return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0


def trim_silence(x: np.ndarray, pad_s: float = 0.03, thresh: float = 0.010) -> np.ndarray:
    idx = np.where(np.abs(x) > thresh)[0]
    if len(idx) == 0:
        return x
    i0, i1 = max(0, int(idx[0]) - int(pad_s * SR)), min(len(x), int(idx[-1]) + int(0.05 * SR))
    out = x[i0:i1].copy()
    fi, fo = min(int(0.012 * SR), len(out) // 4), min(int(0.018 * SR), len(out) // 4)
    if fi > 0:
        out[:fi] *= np.linspace(0.0, 1.0, fi)
    if fo > 0:
        out[-fo:] *= np.linspace(1.0, 0.0, fo)
    return out


def align_words(text: str, raw_bounds: list, seg_start: float, speech_dur: float, scene_num: int):
    display_words = text.split()
    if raw_bounds and abs(len(raw_bounds) - len(display_words)) <= 2 and raw_bounds[-1]["t1"] > 0.2:
        b0, b1 = raw_bounds[0]["t0"], max(raw_bounds[0]["t0"] + 0.1, raw_bounds[-1]["t1"])
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
    weights = [max(1.1, sum(1 for c in w if c in vowels) + len(w) * 0.16 + (1.4 if w[-1] in ".!?" else (0.7 if w[-1] in ",;—–:" else 0.0))) for w in display_words]
    tot, t_cur, out = sum(weights), seg_start, []
    for w, wt in zip(display_words, weights):
        dur_w = speech_dur * (wt / tot)
        out.append({"w": w, "scene": scene_num, "t0": round(t_cur, 3), "t1": round(t_cur + dur_w, 3)})
        t_cur += dur_w
    return out


def looped_vocal_pad(rng, target_dur: float, notes: tuple, vowel: str, seed: int) -> np.ndarray:
    """Fast crossfaded loop of rich male A cappella choir (zero instruments)."""
    unit_d = min(22.0, target_dur)
    pad = smod.reverb(smod.vocal_pad(rng, unit_d, notes, vowel, 4), wet=0.40, seed=seed)
    n_tot = int(round(target_dur * SR))
    if len(pad) >= n_tot:
        return pad[:n_tot]
    out = np.zeros((n_tot, 2), dtype=np.float64)
    xf = int(1.5 * SR)
    step = max(SR, len(pad) - xf)
    pos = 0
    while pos < n_tot:
        rem = min(len(pad), n_tot - pos)
        blk = pad[:rem].copy()
        if pos > 0:
            fade_n = min(xf, rem)
            blk[:fade_n] *= np.linspace(0.0, 1.0, fade_n)[:, None]
        if pos + rem < n_tot:
            fade_n = min(xf, rem)
            blk[-fade_n:] *= np.linspace(1.0, 0.0, fade_n)[:, None]
        out[pos:pos + rem] += blk
        pos += step
    return out


def build_voice_and_timeline():
    ldir = BUILD / "kz"
    ldir.mkdir(parents=True, exist_ok=True)
    voice_wav = ldir / "voice.wav"

    clips, timeline, words_all = [], [], []
    t_cursor = 0.0
    for si, sc in enumerate(SCENES):
        text = sc["text"]
        bounds = synth_line_with_retry(text, ldir / f"line_{si:03d}.mp3", ldir / f"line_{si:03d}.wav")
        spoken = trim_silence(read_wav_mono(ldir / f"line_{si:03d}.wav"))
        speech_dur = len(spoken) / SR
        pause_after = 0.55 if si == len(SCENES) - 1 else (0.38 if si in CHAPTER_BREAK_SCENES else 0.14)
        seg_dur = speech_dur + pause_after
        clips.append(spoken)
        clips.append(np.zeros(int(round(pause_after * SR)), dtype=np.float32))
        timeline.append({"scene": si + 1, "ch_idx": sc["ch_idx"], "mode": sc["mode"], "title": sc["top"], "t0": round(t_cursor, 4), "t1": round(t_cursor + seg_dur, 4), "speech_dur": round(speech_dur, 4), "text": text})
        words_all.extend(align_words(text, bounds, t_cursor, speech_dur, si + 1))
        t_cursor += seg_dur
        if (si + 1) % 25 == 0 or si == len(SCENES) - 1:
            print(f"  [TTS] Synthesized {si + 1}/{len(SCENES)} scenes ({t_cursor:.1f}s)...", flush=True)

    full_voice = np.concatenate(clips)
    smod.write(str(voice_wav), smod.norm(full_voice, 0.94))
    return voice_wav, timeline, words_all, len(full_voice) / SR


def run_yt_sfx(voice_wav: Path, timeline: list, dur: float) -> Path:
    ldir = BUILD / "kz"
    mix_raw, mix_wav = ldir / "mix_raw.wav", ldir / "mix.wav"
    if mix_wav.exists() and mix_wav.stat().st_size > 500000:
        return mix_wav

    v = smod.bp(read_wav_mono(voice_wav).astype(np.float64), 80, 11500)
    N = int(round(dur * SR))
    amb = np.zeros((N, 2), dtype=np.float64)
    rng = np.random.default_rng(177102)

    # Tiled natural steppe wind bed (zero instruments)
    w_unit = smod.wind(rng, 25.0, howl=0.20) * 0.24
    pos = 0
    while pos < N:
        rem = min(len(w_unit), N - pos)
        amb[pos:pos + rem] += smod.st(w_unit[:rem], 0.0)
        pos += len(w_unit)

    # 8-chapter male A cappella choir progressions
    ch_starts = []
    for ch in range(8):
        ch_starts.append(next(seg["t0"] for seg in timeline if seg["ch_idx"] == ch))
    ch_starts.append(dur)
    D3, E3, F3, G3, A3, Bb3, C4, D4, E4 = 146.83, 164.81, 174.61, 196.00, 220.00, 233.08, 261.63, 293.66, 329.63
    ch_chords = [
        ((D3, F3, A3, D4), "o", 0.32),
        ((D3, F3, Bb3, D4), "u", 0.34),
        ((E3, G3, A3, D4), "o", 0.34),
        ((D3, F3, A3, C4), "u", 0.36),
        ((F3, A3, C4, D4), "o", 0.32),
        ((D3, F3, G3, D4, E4), "a", 0.38),
        ((D3, E3, A3, D4), "o", 0.34),
        ((D3, F3, A3, D4, E4), "a", 0.36),
    ]
    for ci, ((chord, vow, amp), t_a, t_b) in enumerate(zip(ch_chords, ch_starts[:-1], ch_starts[1:])):
        cdur = max(1.5, t_b - t_a)
        smod.add(amb, looped_vocal_pad(rng, cdur, chord, vow, 800 + ci) * amp, t_a)

    # Physical scene-matched SFX
    boom_s = smod.reverb(smod.impact_boom(rng, 1.5), wet=0.28, seed=901) * 0.52
    clasp_s = smod.reverb(smod.clasp(rng), wet=0.20, seed=902) * 0.38
    clash_s = smod.reverb(smod.sword_clash(rng), wet=0.22, seed=903) * 0.44
    whoosh_s = smod.st(smod.whoosh(rng, 0.42), 0.15) * 0.38
    gallop_s = smod.st(smod.gallop_fast(rng, 3.8), -0.1) * 0.34
    herd_s = smod.st(smod.herd_far(rng, 4.0), 0.1) * 0.35

    prev_ch = -1
    for si, seg in enumerate(timeline):
        t0, sd, mode, ch = seg["t0"], seg["t1"] - seg["t0"], seg["mode"], seg["ch_idx"]
        if ch != prev_ch:
            smod.add(amb, boom_s, t0)
            prev_ch = ch
        if si == 0:
            smod.add(amb, clash_s, 0.08)
            smod.add(amb, whoosh_s, sd * 0.48)
        elif mode == "tactical_battle":
            smod.add(amb, clash_s if (si % 2 == 0) else gallop_s, t0 + 0.15)
        elif mode == "strategic_atlas":
            smod.add(amb, whoosh_s, t0 + 0.05)
            if ch in {2, 5, 6}:
                smod.add(amb, herd_s, t0 + 0.30)
        elif mode in {"order_of_battle", "system_diagram"}:
            smod.add(amb, clasp_s, t0 + 0.12)
        elif mode == "cinema_montage":
            smod.add(amb, gallop_s if ch in {1, 2, 5} else smod.st(smod.eagle(rng), 0.2) * 0.34, t0 + 0.2)

    rms = smod.frame_rms(v, win=0.05)
    rms_st = np.interp(np.arange(N), np.arange(len(rms)) * int(SR * 0.05), rms)
    amb *= (1.0 - 0.56 * np.clip(rms_st / 0.085, 0.0, 1.0))[:, None]

    out = smod.softclip(amb * 0.88 + smod.st(v, 0.0), 0.90)
    smod.write(str(mix_raw), out)
    r = subprocess.run([FFMPEG, "-hide_banner", "-i", str(mix_raw), "-af", "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"], capture_output=True, text=True)
    js = json.loads(r.stderr[r.stderr.rindex("{"):r.stderr.rindex("}") + 1])
    af = f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={js['input_i']}:measured_TP={js['input_tp']}:measured_LRA={js['input_lra']}:measured_thresh={js['input_thresh']}:offset={js['target_offset']}:linear=true"
    subprocess.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", str(mix_raw), "-af", af, "-ar", "48000", str(mix_wav)], check=True)
    return mix_wav


# ---------------------------------------------------------------------------
# PARALLEL CHUNK VIDEO ENCODER WORKER
# ---------------------------------------------------------------------------
def encode_chunk_worker(args: tuple) -> tuple[int, str]:
    c_idx, f0, f1, timeline_path, words_path, dur, seg_path_str = args
    build_widescreen_relief_map()
    timeline = json.loads(Path(timeline_path).read_text(encoding="utf-8"))
    words_all = json.loads(Path(words_path).read_text(encoding="utf-8"))
    chunks = build_chunks_169(words_all, dur)

    cmd_enc = [
        FFMPEG, "-y",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
        "-i", "-",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
        "-maxrate", "760k", "-bufsize", "1520k",
        "-pix_fmt", "yuv420p", "-g", "30", "-keyint_min", "30",
        str(seg_path_str),
    ]
    proc = subprocess.Popen(cmd_enc, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    t0_chunk = f0 / FPS
    si = 0
    while si < len(SCENES) - 1 and t0_chunk >= timeline[si]["t1"]:
        si += 1
    ci = 0
    while ci < len(chunks) and t0_chunk >= chunks[ci]["t1"] + 0.06:
        ci += 1

    dissolve_frames = 4
    for fi in range(f0, f1):
        t = fi / FPS
        while si < len(SCENES) - 1 and t >= timeline[si]["t1"]:
            si += 1
        seg = timeline[si]
        seg_dur = max(0.05, seg["t1"] - seg["t0"])
        tau = max(0.0, t - seg["t0"])
        u = min(1.0, tau / seg_dur)

        frame_pil = render_scene_frame(SCENES[si], u, tau, seg_dur, t)
        if si > 0:
            frames_into = int(round(tau * FPS))
            if frames_into < dissolve_frames:
                prev_seg = timeline[si - 1]
                prev_sd = max(0.05, prev_seg["t1"] - prev_seg["t0"])
                prev_pil = render_scene_frame(SCENES[si - 1], 1.0, prev_sd, prev_sd, prev_seg["t1"])
                frame_pil = Image.blend(prev_pil, frame_pil, (frames_into + 1) / (dissolve_frames + 1))

        step_a = min(5, int(round(min(1.0, tau / 0.20) * 5)))
        hud_strip = get_hud_top_strip(si, step_a)
        frame_pil.paste(hud_strip, (0, 0), hud_strip)

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
                sub_im = render_sub_169(ci, ws, act)
                frame_pil.paste(sub_im, ((W - sub_im.width) // 2, 982 - sub_im.height // 2), sub_im)

        proc.stdin.write(frame_pil.tobytes())

    proc.stdin.close()
    ret = proc.wait()
    if ret != 0:
        raise RuntimeError(f"FFmpeg chunk {c_idx} failed with exit code {ret}")
    return c_idx, seg_path_str


# ---------------------------------------------------------------------------
# VALIDATORS (GLYPHS, WIDTHS, ASSETS)
# ---------------------------------------------------------------------------
def check_hud_and_glyphs():
    max_t = max(get_font(25).getlength(s["top"]) for s in SCENES)
    max_s = max(get_font(17).getlength(s["sub"]) for s in SCENES)
    max_p = max(get_font(13).getlength(p) for p in CHAPTER_PILLS)
    print(f"[HUD 16:9 CHECK] max_top={max_t:.0f}px (lim 1120), max_sub={max_s:.0f}px (lim 1120), max_pil={max_p:.0f}px (lim 72)")
    assert max_t <= 1120, f"Top banner too wide: {max_t}"
    assert max_s <= 1120, f"Sub banner too wide: {max_s}"
    assert max_p <= 72, f"Pill too wide: {max_p}"

    for si, s in enumerate(SCENES):
        if "card_title" in s:
            assert get_font(29).getlength(s["card_title"]) <= 556, f"Card title too wide at {si}: {s['card_title']}"
        for k, v in s.get("bullets", []):
            assert get_font(18).getlength(k) <= 536, f"Bullet key wide at {si}: {k}"
            assert get_font(19).getlength(v) <= 536, f"Bullet val wide at {si}: {v}"
        if "plate" in s:
            assert (ROOT / s["plate"]).exists(), f"Missing plate at {si}: {s['plate']}"
        for pl in s.get("plates", []):
            assert (ROOT / pl).exists(), f"Missing plate at {si}: {pl}"

    f = get_font(40)
    ref = f.getmask("\ufffe")
    bad = set()
    for pyf in (Path(__file__), ROOT / "production" / "yt_long_scenes_kz.py"):
        for st in re.findall(r'"([^"\\]*(?:\\.[^"\\]*)*)"', pyf.read_text(encoding="utf-8")):
            for ch in st:
                if ord(ch) > 32 and bytes(f.getmask(ch)) == bytes(ref) and f.getmask(ch).size == ref.size:
                    bad.add(ch)
    assert not bad, f"Missing font glyphs: {bad}"


def write_smoke_modes():
    """Render 1 QA frame from each of the 6 animated modes into qa/ for visual inspection."""
    qa_dir = BUILD / "qa"
    qa_dir.mkdir(parents=True, exist_ok=True)
    picks = {}
    for si, sc in enumerate(SCENES):
        if sc["mode"] not in picks:
            picks[sc["mode"]] = si
    build_widescreen_relief_map()
    for mode, si in picks.items():
        sc = SCENES[si]
        im = render_scene_frame(sc, 0.58, 2.2, 6.0, si * 6.0 + 2.2)
        hud = get_hud_top_strip(si, 5)
        im.paste(hud, (0, 0), hud)
        out_p = qa_dir / f"smoke_{mode}.png"
        im.save(out_p)
        print(f"  [SMOKE] Saved {out_p} (scene {si + 1}: {sc['top']})", flush=True)


def build_youtube_long(voice_only: bool = False, smoke_only: bool = False):
    print(f"\n=== BUILDING YOUTUBE LONG 16:9 [KZ ONLY • {len(SCENES)} SCENES] ===", flush=True)
    check_hud_and_glyphs()
    if smoke_only:
        write_smoke_modes()
        return None

    t_start = time.time()
    voice_wav, timeline, words_all, dur = build_voice_and_timeline()
    assert dur >= 600.0, f"Video duration {dur:.1f}s is under 10 minutes (600s)!"
    mix_wav = run_yt_sfx(voice_wav, timeline, dur)

    ldir = BUILD / "kz"
    tpath, wpath = ldir / "timeline.json", ldir / "words.json"
    tpath.write_text(json.dumps(timeline, ensure_ascii=False, indent=2), encoding="utf-8")
    wpath.write_text(json.dumps(words_all, ensure_ascii=False, indent=2), encoding="utf-8")
    wc = sum(len(s["text"].split()) for s in SCENES)
    print(f"  Voice + Mix ready: {dur:.2f}s ({dur / 60:.2f} min, {len(SCENES)} scenes / 8 chapters, {wc} words)", flush=True)
    if voice_only:
        write_smoke_modes()
        return None

    build_widescreen_relief_map()
    total_frames = int(round(dur * FPS))
    # Split into GOP-aligned chunks (multiples of 30 frames = exact integer seconds) across 4 workers
    n_chunks = 16
    raw_step = ((total_frames + n_chunks - 1) // n_chunks + FPS - 1) // FPS * FPS
    jobs, seg_paths = [], []
    f0, c_idx = 0, 0
    while f0 < total_frames:
        f1 = min(total_frames, f0 + raw_step)
        sp = ldir / f"seg_{c_idx:02d}.mp4"
        seg_paths.append(sp)
        jobs.append((c_idx, f0, f1, str(tpath), str(wpath), dur, str(sp)))
        f0 = f1
        c_idx += 1

    print(f"  Encoding {total_frames} frames across {len(jobs)} segments with 4 parallel workers...", flush=True)
    with concurrent.futures.ProcessPoolExecutor(max_workers=4) as ex:
        futs = [ex.submit(encode_chunk_worker, job) for job in jobs]
        done_cnt = 0
        for fut in concurrent.futures.as_completed(futs):
            ci_done, _ = fut.result()
            done_cnt += 1
            print(f"  [CHUNK {done_cnt}/{len(jobs)}] seg_{ci_done:02d} done ({time.time() - t_start:.1f}s)", flush=True)

    concat_txt = ldir / "concat.txt"
    concat_txt.write_text("".join(f"file '{sp.name}'\n" for sp in seg_paths), encoding="utf-8")
    tmp_vid = ldir / "video_silent.mp4"
    subprocess.run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", str(concat_txt), "-c", "copy", str(tmp_vid)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_mp4 = OUT_DIR / OUT_FILE
    subprocess.run(
        [
            FFMPEG, "-y", "-i", str(tmp_vid), "-i", str(mix_wav),
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart",
            str(out_mp4),
        ],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    sz_mb = out_mp4.stat().st_size / (1024 * 1024)
    print(f"  DONE [YT 16:9 KZ]: {out_mp4} ({dur:.1f}s / {dur / 60:.2f} min, {sz_mb:.1f} MB) in {time.time() - t_start:.1f}s", flush=True)
    return out_mp4


if __name__ == "__main__":
    v_only = "--voice-only" in sys.argv[1:]
    s_only = "--smoke-only" in sys.argv[1:]
    build_youtube_long(voice_only=v_only, smoke_only=s_only)
