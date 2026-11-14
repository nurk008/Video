#!/usr/bin/env python3
"""Episode 5 Animation Engine: Camera-Tracked 3D-Hillshaded Campaign Maps,
Kinetic Infographics, Volumetric Fog/Rays, and Arrow-Volley FX for EP05 (KZ).
100% free of pixel-warping jelly artifacts — pure rigid sub-pixel transforms + crisp vectors.
"""

import math
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy.ndimage import gaussian_filter, sobel

W, H = 1080, 1920
FONT_PATH = Path("/Users/market/antigravity/Video/production/fonts/Montserrat-Black.ttf")


@lru_cache(maxsize=32)
def get_font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_PATH), size)


def smoothstep(x: float) -> float:
    x = max(0.0, min(1.0, x))
    return x * x * (3.0 - 2.0 * x)


def ease_out(x: float) -> float:
    x = max(0.0, min(1.0, x))
    return 1.0 - (1.0 - x) ** 3


def fbm_noise(h: int, w: int, octaves: int = 5, base_scale: float = 130.0, seed: int = 1598) -> np.ndarray:
    """Fast multi-octave smooth fractional Brownian motion field in [0, 1]."""
    rng = np.random.default_rng(seed)
    acc = np.zeros((h, w), dtype=np.float32)
    amp = 1.0
    norm_s = 0.0
    for k in range(octaves):
        sig = max(1.5, base_scale / (2.0 ** k))
        gh = max(8, int(h / max(4.0, sig * 0.6)))
        gw = max(8, int(w / max(4.0, sig * 0.6)))
        grid = rng.standard_normal((gh, gw)).astype(np.float32)
        up = np.array(
            Image.fromarray(grid).resize((w, h), Image.Resampling.BICUBIC),
            dtype=np.float32,
        )
        up = gaussian_filter(up, sigma=max(1.0, sig * 0.14))
        acc += amp * up
        norm_s += amp
        amp *= 0.52
    acc /= max(1e-6, norm_s)
    mn, mx = float(acc.min()), float(acc.max())
    return (acc - mn) / max(1e-6, mx - mn)


# Canonical Map World Space: [0..1080, 0..1920] centered cleanly around Syr Darya -> Bukhara corridor
MAP_CITIES = {
    "Сығанақ":   (215, 345),
    "Сауран":    (345, 435),
    "Түркістан": (470, 535),
    "Отырар":    (540, 625),
    "Сайрам":    (745, 650),
    "Ташкент":   (645, 805),
    "Самарқан":  (460, 1020),
    "Бұхара":    (235, 1110),
}

SYR_DARYA_PTS = [
    (980, 770), (835, 745), (705, 760), (565, 705), (485, 595),
    (405, 495), (295, 420), (175, 340), (45, 270),
]

ZERAVSHAN_PTS = [
    (835, 1015), (630, 1005), (460, 1030), (320, 1095), (195, 1185), (75, 1265),
]


def eval_polyline(pts: list[tuple[float, float]], n_samples: int = 120) -> list[tuple[float, float]]:
    p = [pts[0]] + list(pts) + [pts[-1]]
    out = []
    segs = len(pts) - 1
    steps_per = max(4, n_samples // max(1, segs))
    for i in range(segs):
        p0, p1, p2, p3 = p[i], p[i + 1], p[i + 2], p[i + 3]
        for s in range(steps_per):
            t = s / steps_per
            t2, t3 = t * t, t * t * t
            x = 0.5 * (
                (2 * p1[0])
                + (-p0[0] + p2[0]) * t
                + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2
                + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3
            )
            y = 0.5 * (
                (2 * p1[1])
                + (-p0[1] + p2[1]) * t
                + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2
                + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3
            )
            out.append((x, y))
    out.append(pts[-1])
    return out


def point_along_path(pts_dense: list[tuple[float, float]], u: float) -> tuple[float, float, float]:
    u = max(0.0, min(1.0, u))
    fidx = u * (len(pts_dense) - 1)
    i0 = min(len(pts_dense) - 2, max(0, int(fidx)))
    frac = fidx - i0
    x0, y0 = pts_dense[i0]
    x1, y1 = pts_dense[i0 + 1]
    x = x0 + (x1 - x0) * frac
    y = y0 + (y1 - y0) * frac
    return x, y, math.atan2(y1 - y0, x1 - x0)


@lru_cache(maxsize=2)
def build_hi_relief_map() -> Image.Image:
    """High-resolution 2x relief atlas (1080x1920) cached for sharp camera pans & zooms."""
    hw, hh = W // 2, H // 2
    elev = fbm_noise(hh, hw, octaves=5, base_scale=125.0, seed=1598)
    yy, xx = np.mgrid[0:hh, 0:hw].astype(np.float32)
    nx, ny = xx / hw, yy / hh

    ridge1 = np.exp(-((nx - (0.74 - 0.14 * ny)) ** 2) / 0.025) * 0.55
    ridge2 = np.exp(-((ny - 0.44 - 0.24 * (nx - 0.65)) ** 2) / 0.015) * (nx > 0.55) * 0.45
    hmap = np.clip(elev * 0.72 + ridge1 + ridge2, 0.0, 1.35)

    gx = sobel(hmap, axis=1) * 19.0
    gy = sobel(hmap, axis=0) * 19.0
    az, alt = math.radians(315), math.radians(42)
    slope = np.arctan(np.hypot(gx, gy))
    aspect = np.arctan2(-gy, gx)
    shade = np.clip(np.sin(alt) * np.cos(slope) + np.cos(alt) * np.sin(slope) * np.cos(az - aspect), 0.15, 1.0)

    # Rich antique bronze & obsidian war-room palette
    r = 24.0 + 38.0 * shade + 20.0 * np.clip(hmap - 0.55, 0, 1)
    g = 24.0 + 33.0 * shade + 11.0 * np.clip(hmap - 0.55, 0, 1)
    b = 26.0 + 24.0 * shade

    iso = np.abs(np.sin(hmap * 24.0)) < 0.072
    r[iso] += 11.0
    g[iso] += 8.5
    b[iso] += 4.5

    rgb = np.stack([r, g, b], axis=-1).clip(0, 255).astype(np.uint8)
    # Render 2x base so zoomed map regions retain razor detail!
    base = Image.fromarray(rgb).resize((W * 2, H * 2), Image.Resampling.BICUBIC)
    return base


class MapCamera:
    """Maps world coordinates [0..1080, 0..1920] into current zoomed/panned screen pixels."""
    def __init__(self, zoom: float, cx: float, cy: float):
        self.zoom = zoom
        vw = W / zoom
        vh = H / zoom
        self.x0 = max(0.0, min(W - vw, cx - vw * 0.5))
        self.y0 = max(0.0, min(H - vh, cy - vh * 0.5))
        self.vw = vw
        self.vh = vh

    def pt(self, wx: float, wy: float) -> tuple[float, float]:
        return ((wx - self.x0) * self.zoom, (wy - self.y0) * self.zoom)

    def pts(self, wpts: list[tuple[float, float]]) -> list[tuple[float, float]]:
        return [self.pt(x, y) for x, y in wpts]


def render_map_canvas(zoom: float, cx: float, cy: float, t: float) -> tuple[Image.Image, MapCamera]:
    """Crop 2x relief atlas rigidly to MapCamera and draw glowing rivers + cartographic grid."""
    cam = MapCamera(zoom, cx, cy)
    hi = build_hi_relief_map()
    box_2x = (cam.x0 * 2.0, cam.y0 * 2.0, (cam.x0 + cam.vw) * 2.0, (cam.y0 + cam.vh) * 2.0)
    bg = hi.transform((W, H), Image.Transform.EXTENT, box_2x, Image.Resampling.BICUBIC).convert("RGBA")

    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)

    # Cartographic grid in world space
    for gx_w in range(80, W, 140):
        d.line([cam.pt(gx_w, 120), cam.pt(gx_w, 1750)], fill=(210, 175, 102, 22), width=1)
    for gy_w in range(200, 1650, 140):
        d.line([cam.pt(20, gy_w), cam.pt(W - 20, gy_w)], fill=(210, 175, 102, 22), width=1)

    # Rivers + animated glint droplets
    for idx, wpts in enumerate((SYR_DARYA_PTS, ZERAVSHAN_PTS)):
        dense_w = eval_polyline(wpts, 120)
        dense_s = cam.pts(dense_w)
        d.line(dense_s, fill=(24, 105, 138, 130), width=max(10, int(13 * zoom)))
        d.line(dense_s, fill=(76, 198, 228, 190), width=max(4, int(5 * zoom)))
        count = 16 if idx == 0 else 10
        for k in range(count):
            u0 = (k / count + t * 0.085) % 1.0
            u1 = min(1.0, u0 + 0.03)
            x0, y0, _ = point_along_path(dense_w, u0)
            x1, y1, _ = point_along_path(dense_w, u1)
            alpha = int(165 * math.sin(math.pi * ((t * 1.4 + k * 0.7) % 1.0)) ** 2 + 50)
            d.line([cam.pt(x0, y0), cam.pt(x1, y1)], fill=(205, 250, 255, alpha), width=3)

    fr = get_font(22)
    sx, sy = cam.pt(515, 445)
    d.text((sx, sy), "СЫРДАРИЯ", font=fr, fill=(108, 214, 240, 165))
    zx, zy = cam.pt(555, 975)
    d.text((zx, zy), "ЗЕРАВШАН", font=fr, fill=(108, 214, 240, 155))

    bg.alpha_composite(ov)
    return bg, cam


def draw_fortress_node(
    ov: Image.Image,
    cam: MapCamera,
    wpos: tuple[int, int],
    label: str,
    status: str,
    t: float,
    pulse_burst: float = 0.0,
    is_capital: bool = False,
    label_side: str = "auto",
):
    d = ImageDraw.Draw(ov)
    x, y = cam.pt(*wpos)
    if x < -40 or x > W + 40 or y < 220 or y > 1340:
        return

    if status == "kazakh":
        col, ring_c = (248, 202, 84), (78, 224, 222)
    elif status == "capturing":
        col, ring_c = (110, 242, 232), (248, 202, 84)
    else:
        col, ring_c = (226, 76, 66), (255, 130, 110)

    ping_r = 22 + ((t * 28.0) % 26.0)
    ping_a = int(max(0, 135 * (1.0 - ((t * 28.0) % 26.0) / 26.0)))
    if status in ("kazakh", "capturing") or is_capital:
        d.ellipse([x - ping_r, y - ping_r, x + ping_r, y + ping_r], outline=(*ring_c, ping_a), width=3)

    if pulse_burst > 0.01:
        br = 20 + 58 * pulse_burst
        ba = int(230 * (1.0 - pulse_burst))
        d.ellipse([x - br, y - br, x + br, y + br], outline=(255, 228, 120, ba), width=5)

    rad = 21 if is_capital or label in ("Түркістан", "Ташкент", "Самарқан", "Бұхара") else 17
    d.ellipse([x - rad - 4, y - rad - 4, x + rad + 4, y + rad + 4], fill=(12, 16, 22, 225), outline=(*col, 245), width=3)
    d.rectangle([x - 10, y - 4, x + 10, y + 10], fill=(*col, 240))
    d.chord([x - 7, y - 14, x + 7, y + 0], 180, 360, fill=(*ring_c, 255))
    d.rectangle([x - 13, y - 8, x - 9, y + 10], fill=(*col, 240))
    d.rectangle([x + 9, y - 8, x + 13, y + 10], fill=(*col, 240))

    f = get_font(25 if is_capital else 22)
    tw = d.textlength(label, font=f)
    if label_side == "left" or (label_side == "auto" and x > 690):
        lx, ly = x - rad - tw - 24, y - 14
    elif label_side == "below":
        lx, ly = x - tw / 2, y + rad + 10
    elif label_side == "above":
        lx, ly = x - tw / 2, y - rad - 38
    else:
        lx, ly = x + rad + 10, y - 14
    lx = max(16.0, min(W - tw - 20.0, lx))
    d.rounded_rectangle([lx - 8, ly - 4, lx + tw + 10, ly + 30], radius=8, fill=(10, 14, 20, 215), outline=(*col, 150), width=1)
    d.text((lx + 1, ly + 1), label, font=f, fill=(252, 248, 238, 250))


def draw_animated_arrow(
    ov: Image.Image,
    cam: MapCamera,
    w_ctrl_pts: list[tuple[float, float]],
    progress: float,
    t: float,
    col_main=(248, 202, 84),
    col_glow=(78, 224, 222),
    width: int = 12,
    dashed: bool = False,
):
    if progress <= 0.02:
        return
    dense_s = cam.pts(eval_polyline(w_ctrl_pts, 115))
    max_i = max(2, int(progress * (len(dense_s) - 1)))
    pts = dense_s[: max_i + 1]
    d = ImageDraw.Draw(ov)

    if dashed:
        for i in range(0, len(pts) - 3, 5):
            d.line([pts[i], pts[min(i + 2, len(pts) - 1)]], fill=(*col_glow, 195), width=max(4, width // 2))
    else:
        d.line(pts, fill=(*col_glow, 95), width=width + 12, joint="curve")
        d.line(pts, fill=(*col_main, 238), width=width, joint="curve")
        for k in range(3):
            pu = ((t * 0.65 + k / 3.0) % 1.0) * progress
            px, py, _ = point_along_path(dense_s, pu)
            d.ellipse([px - 5, py - 5, px + 5, py + 5], fill=(255, 252, 230, 230))

    tip_x, tip_y = pts[-1]
    prev_x, prev_y = pts[max(0, len(pts) - 4)]
    ang = math.atan2(tip_y - prev_y, tip_x - prev_x)
    alen, aw = width * 2.3, width * 1.4
    p1 = (tip_x + math.cos(ang) * 6, tip_y + math.sin(ang) * 6)
    p2 = (tip_x - math.cos(ang) * alen + math.sin(ang) * aw, tip_y - math.sin(ang) * alen - math.cos(ang) * aw)
    p3 = (tip_x - math.cos(ang) * alen * 0.65, tip_y - math.sin(ang) * alen * 0.65)
    p4 = (tip_x - math.cos(ang) * alen - math.sin(ang) * aw, tip_y - math.sin(ang) * alen + math.cos(ang) * aw)
    d.polygon([p1, p2, p3, p4], fill=(*col_main, 255))


def draw_army_unit_marker(
    ov: Image.Image,
    cam: MapCamera,
    wpos: tuple[float, float],
    ang: float,
    title: str,
    col=(248, 202, 84),
    badge_bg=(16, 44, 52),
    t: float = 0.0,
    label_offset: tuple[float, float] = (0.0, 28.0),
):
    d = ImageDraw.Draw(ov)
    cx, cy = cam.pt(*wpos)
    ca, sa = math.cos(ang), math.sin(ang)
    rx, ry = -sa, ca
    rw, rh = 26, 16
    corners = [
        (cx + ca * rw + rx * rh, cy + sa * rw + ry * rh),
        (cx + ca * (rw + 10), cy + sa * (rw + 10)),
        (cx + ca * rw - rx * rh, cy + sa * rw - ry * rh),
        (cx - ca * rw - rx * rh, cy - sa * rw - ry * rh),
        (cx - ca * (rw - 6), cy - sa * (rw - 6)),
        (cx - ca * rw + rx * rh, cy - sa * rw + ry * rh),
    ]
    d.polygon(corners, fill=(*badge_bg, 240), outline=(*col, 255), width=3)

    px0, py0 = cx - ca * (rw * 0.7), cy - sa * (rw * 0.7)
    d.line([(px0, py0), (px0, py0 - 25)], fill=(235, 225, 205, 245), width=2)
    wave = math.sin(t * 9.0 + cx * 0.05) * 4.0
    d.polygon([(px0, py0 - 25), (px0 - 20, py0 - 21 + wave), (px0 - 15, py0 - 15 + wave), (px0, py0 - 13)], fill=(*col, 240))

    if title:
        f = get_font(20)
        tw = d.textlength(title, font=f)
        lx, ly = cx + label_offset[0], cy + label_offset[1]
        lx = max(tw / 2 + 18.0, min(W - tw / 2 - 18.0, lx))
        d.rounded_rectangle([lx - tw / 2 - 9, ly - 4, lx + tw / 2 + 9, ly + 26], radius=7, fill=(10, 14, 20, 225), outline=(*col, 175), width=2)
        d.text((lx - tw / 2, ly), title, font=f, fill=(252, 248, 238, 255))


# ─────────────────────── KINETIC FX, MIST & INFOGRAPHICS OVER PHOTOREAL ───────────────────────

@lru_cache(maxsize=4)
def make_mist_strip(seed: int = 88) -> np.ndarray:
    """Seamless 2160x520 volumetric battlefield mist/smoke strip."""
    n = fbm_noise(260, W * 2, octaves=4, base_scale=95.0, seed=seed)
    n = np.clip((n - 0.36) * 2.1, 0.0, 1.0)
    vert_env = np.sin(np.linspace(0, math.pi, 260))[:, None] ** 1.3
    return (n * vert_env * 88.0).clip(0, 255).astype(np.uint8)


def apply_drifting_mist(frame: Image.Image, t: float, col=(245, 214, 152), y_dest: int = 880, speed: float = 42.0):
    strip = make_mist_strip(88)
    shift = int((t * speed) % (W * 2))
    sl = np.roll(strip, -shift, axis=1)[:, :W]
    rgba = np.zeros((260, W, 4), dtype=np.uint8)
    rgba[:, :, :3] = col
    rgba[:, :, 3] = sl
    im_mist = Image.fromarray(rgba).resize((W, 520), Image.Resampling.BILINEAR)
    ov = frame.convert("RGBA")
    ov.alpha_composite(im_mist, dest=(0, y_dest))
    return ov


def draw_arrow_barrage(ov: Image.Image, t: float, count: int = 38, go_right: bool = True):
    """Sleek razor-sharp animated parabolic arrow volley streaks."""
    rng = np.random.default_rng(7005)
    d = ImageDraw.Draw(ov)
    for _ in range(count):
        period = rng.uniform(0.95, 1.55)
        phase = ((t + rng.uniform(0, period)) % period) / period
        y_base = rng.uniform(460, 1080)
        arc_h = rng.uniform(130, 280)
        x0 = -70 if go_right else W + 70
        x1 = W + 90 if go_right else -90
        x = x0 + (x1 - x0) * phase
        y = y_base - 4.0 * arc_h * phase * (1.0 - phase)
        dx = x1 - x0
        dy = -4.0 * arc_h * (1.0 - 2.0 * phase)
        nm = max(1.0, math.hypot(dx, dy))
        ux, uy = dx / nm, dy / nm
        d.line([(x - ux * 115, y - uy * 115), (x - ux * 42, y - uy * 42)], fill=(255, 218, 128, 75), width=2)
        d.line([(x - ux * 42, y - uy * 42), (x, y)], fill=(255, 240, 185, 235), width=3)
        d.polygon([(x + ux * 6, y + uy * 6), (x - uy * 3 - ux * 7, y + ux * 3 - uy * 7), (x + uy * 3 - ux * 7, y - ux * 3 - uy * 7)], fill=(255, 248, 220, 250))


def draw_kinetic_counter_card(ov: Image.Image, tau: float, seg_dur: float, target_num: int, suffix: str, sub: str, y_center: int = 1160):
    """Animated kinetic counter card springing smoothly in + rolling count up."""
    d = ImageDraw.Draw(ov)
    pop = ease_out(min(1.0, tau / 0.45))
    val_u = ease_out(min(1.0, max(0.0, (tau - 0.1) / min(1.8, seg_dur * 0.55))))
    cur_val = int(round(target_num * val_u))
    num_str = f"{cur_val:,}".replace(",", " ") + f" {suffix}"

    card_w = int(680 * (0.88 + 0.12 * pop))
    card_h = 114
    x0 = (W - card_w) // 2
    y0 = y_center - card_h // 2 + int(28 * (1.0 - pop))
    a_fill = int(208 * pop)
    a_tx = int(250 * pop)

    d.rounded_rectangle([x0, y0, x0 + card_w, y0 + card_h], radius=20, fill=(12, 18, 26, a_fill), outline=(248, 202, 84, a_tx), width=3)
    f_big = get_font(44)
    f_sm = get_font(22)
    nw = d.textlength(num_str, font=f_big)
    sw = d.textlength(sub, font=f_sm)
    d.text(((W - nw) / 2, y0 + 16), num_str, font=f_big, fill=(248, 202, 84, a_tx))
    d.text(((W - sw) / 2, y0 + 72), sub, font=f_sm, fill=(116, 224, 228, a_tx))


def draw_speed_comparison_card(ov: Image.Image, tau: float, seg_dur: float, y_center: int = 1125):
    """Animated bar comparison showing nomadic twin-horse speed advantage (2-3x)."""
    d = ImageDraw.Draw(ov)
    pop = ease_out(min(1.0, tau / 0.4))
    bar_u = ease_out(min(1.0, max(0.0, (tau - 0.25) / min(2.0, seg_dur * 0.55))))
    x0, y0, cw, ch = 120, y_center - 82, W - 240, 164
    d.rounded_rectangle([x0, y0, x0 + cw, y0 + ch], radius=18, fill=(10, 16, 24, int(212 * pop)), outline=(78, 224, 222, int(210 * pop)), width=2)

    f_lbl = get_font(23)
    # Row 1: Kazakh twin-horse column (3x bar)
    d.text((x0 + 26, y0 + 18), "ҚАЗАҚ ҚОС АТТЫ ҚОСЫНЫ (×3 ЖЫЛДАМДЫҚ)", font=f_lbl, fill=(248, 202, 84, int(250 * pop)))
    bw1 = int((cw - 52) * 0.96 * bar_u)
    d.rounded_rectangle([x0 + 26, y0 + 50, x0 + 26 + bw1, y0 + 76], radius=10, fill=(248, 202, 84, int(235 * pop)))

    # Row 2: Heavy siege/supply caravan (1x bar)
    d.text((x0 + 26, y0 + 92), "АУЫР ҚАМАЛ ЖӘНЕ ОБОЗ ЖАСАҒЫ (×1)", font=f_lbl, fill=(210, 218, 226, int(225 * pop)))
    bw2 = int((cw - 52) * 0.32 * bar_u)
    d.rounded_rectangle([x0 + 26, y0 + 124, x0 + 26 + bw2, y0 + 148], radius=10, fill=(224, 78, 66, int(215 * pop)))


def draw_scout_radar_overlay(ov: Image.Image, t: float, origin=(540, 740)):
    """Pulsing recon beacon arcs scanning southward from mountain lookouts."""
    d = ImageDraw.Draw(ov)
    ox, oy = origin
    for k in range(3):
        prog = (t * 0.45 + k / 3.0) % 1.0
        r = 30 + prog * 460
        alpha = int(175 * (1.0 - prog))
        d.arc([ox - r, oy - r, ox + r, oy + r], 35, 145, fill=(78, 224, 222, alpha), width=4)
    # Bright beacon center dot
    pr = 9 + 4 * math.sin(t * 7.0)
    d.ellipse([ox - pr, oy - pr, ox + pr, oy + pr], fill=(248, 202, 84, 235))


def draw_battle_pincer_inset(ov: Image.Image, tau: float, seg_dur: float, t: float):
    """Animated mini-diagram showing Open-Plain Flank Envelopment between Tashkent & Samarkand."""
    d = ImageDraw.Draw(ov)
    pop = ease_out(min(1.0, tau / 0.35))
    prog = ease_out(min(1.0, max(0.0, (tau - 0.15) / max(1.0, seg_dur * 0.60))))
    mx0, my0, mw, mh = 135, 1085, W - 270, 215
    d.rounded_rectangle([mx0, my0, mx0 + mw, my0 + mh], radius=18, fill=(10, 16, 24, int(214 * pop)), outline=(248, 202, 84, int(215 * pop)), width=2)
    ft = get_font(21)
    d.text((mx0 + 22, my0 + 14), "ТАШКЕНТ – САМАРҚАН АРАСЫ • ҚАПТАЛДАУ", font=ft, fill=(248, 202, 84, int(245 * pop)))

    # Red opposing center block getting compressed
    cx, cy = mx0 + mw // 2, my0 + 132
    squeeze = int(28 * prog)
    d.rounded_rectangle([cx - 88 + squeeze, cy - 22, cx + 88 - squeeze, cy + 22], radius=8, fill=(220, 68, 58, int(225 * pop)), outline=(255, 160, 140, 230), width=2)
    # Two curved turquoise-gold pincer wings wrapping around red center
    for side in (-1, 1):
        pts = eval_polyline([(cx + side * 225, cy + 56), (cx + side * 255, cy - 8), (cx + side * 125, cy - 58), (cx + side * 32, cy - 34)], 50)
        sub = pts[: max(2, int(prog * (len(pts) - 1)))]
        d.line(sub, fill=(78, 224, 222, 235), width=8, joint="curve")
        tip, prev = sub[-1], sub[max(0, len(sub) - 3)]
        ang = math.atan2(tip[1] - prev[1], tip[0] - prev[0])
        ah, aw = 18, 10
        d.polygon([
            (tip[0] + math.cos(ang) * 5, tip[1] + math.sin(ang) * 5),
            (tip[0] - math.cos(ang) * ah + math.sin(ang) * aw, tip[1] - math.sin(ang) * ah - math.cos(ang) * aw),
            (tip[0] - math.cos(ang) * ah - math.sin(ang) * aw, tip[1] - math.sin(ang) * ah + math.cos(ang) * aw),
        ], fill=(248, 202, 84, 252))


def draw_dual_crest_card(ov: Image.Image, tau: float, y_center: int = 1175):
    """Animated twin-commander showcase sliding left & right cleanly."""
    d = ImageDraw.Draw(ov)
    pop = ease_out(min(1.0, tau / 0.45))
    slide = int(120 * (1.0 - pop))
    bw, bh = 430, 108
    # Left Card: Тәуекел хан
    lx0 = 80 - slide
    d.rounded_rectangle([lx0, y_center - bh // 2, lx0 + bw, y_center + bh // 2], radius=18, fill=(14, 20, 28, int(222 * pop)), outline=(248, 202, 84, int(235 * pop)), width=3)
    # Right Card: Есім сұлтан
    rx0 = W - 80 - bw + slide
    d.rounded_rectangle([rx0, y_center - bh // 2, rx0 + bw, y_center + bh // 2], radius=18, fill=(14, 28, 36, int(222 * pop)), outline=(78, 224, 222, int(235 * pop)), width=3)

    f1, f2 = get_font(27), get_font(20)
    for bx, name, role, col in [
        (lx0, "ТӘУЕКЕЛ ХАН", "80 000 • БҰХАРА БАҒЫТЫ", (248, 202, 84)),
        (rx0, "ЕСІМ СҰЛТАН", "20 000 • САМАРҚАН ҚАЛҚАНЫ", (78, 224, 222)),
    ]:
        nw = d.textlength(name, font=f1)
        rw = d.textlength(role, font=f2)
        d.text((bx + (bw - nw) / 2, y_center - 32), name, font=f1, fill=(*col, int(250 * pop)))
        d.text((bx + (bw - rw) / 2, y_center + 10), role, font=f2, fill=(242, 245, 250, int(240 * pop)))


def draw_fortress_shield_card(ov: Image.Image, tau: float, seg_dur: float, t: float, y_center: int = 1155):
    """Scene 03: Pulsing crimson fortress barrier & patrolling sentinel dots."""
    d = ImageDraw.Draw(ov)
    pop = ease_out(min(1.0, tau / 0.4))
    prog = ease_out(min(1.0, max(0.0, (tau - 0.1) / max(1.0, seg_dur * 0.65))))
    x0, y0, cw, ch = 120, y_center - 74, W - 240, 148
    d.rounded_rectangle([x0, y0, x0 + cw, y0 + ch], radius=18, fill=(20, 12, 16, int(215 * pop)), outline=(232, 82, 70, int(230 * pop)), width=3)

    ft = get_font(23)
    title = "БҰХАРА ҚОРҒАНЫС ШЕБІ (1598 ЖЫЛҒА ДЕЙІН)"
    tw = d.textlength(title, font=ft)
    d.text(((W - tw) / 2, y0 + 18), title, font=ft, fill=(255, 168, 152, int(245 * pop)))

    # 3 Crimson Fortress Nodes linked by animated defensive laser wall
    cities = [("ТҮРКІСТАН", x0 + 135), ("САЙРАМ", W // 2), ("ТАШКЕНТ", x0 + cw - 135)]
    line_y = y0 + 82
    full_w = cities[-1][1] - cities[0][1]
    d.line([(cities[0][1], line_y), (cities[0][1] + full_w * prog, line_y)], fill=(235, 78, 66, int(225 * pop)), width=6)
    # Patrolling crimson sentinel dot moving across barrier
    patrol_x = cities[0][1] + full_w * (0.5 + 0.5 * math.sin(t * 2.4))
    d.ellipse([patrol_x - 7, line_y - 7, patrol_x + 7, line_y + 7], fill=(255, 224, 180, int(240 * pop)))

    fc = get_font(21)
    pulse = 1.0 + 0.14 * math.sin(t * 5.0)
    for cname, cx in cities:
        r = 16 * pulse
        d.ellipse([cx - r, line_y - r, cx + r, line_y + r], fill=(40, 16, 18, 240), outline=(242, 92, 78, 245), width=3)
        cw_t = d.textlength(cname, font=fc)
        d.text((cx - cw_t / 2, line_y + 24), cname, font=fc, fill=(246, 232, 228, int(245 * pop)))


def draw_empire_fracture_card(ov: Image.Image, tau: float, seg_dur: float, t: float, y_center: int = 1155):
    """Scene 06: Animated Bukhara dynasty crisis stability meter dropping from 100% -> 35%."""
    d = ImageDraw.Draw(ov)
    pop = ease_out(min(1.0, tau / 0.4))
    drop = ease_out(min(1.0, max(0.0, (tau - 0.15) / max(1.2, seg_dur * 0.65))))
    x0, y0, cw, ch = 125, y_center - 74, W - 250, 148
    d.rounded_rectangle([x0, y0, x0 + cw, y0 + ch], radius=18, fill=(14, 16, 24, int(218 * pop)), outline=(235, 92, 74, int(220 * pop)), width=2)

    ft = get_font(23)
    d.text((x0 + 28, y0 + 18), "БҰХАРА ХАНДЫҒЫ • БИЛІК ДАҒДАРЫСЫ (1598)", font=ft, fill=(255, 178, 130, int(245 * pop)))

    # Stability bar cracking from 92% down to 34%
    bar_x, bar_y, bar_w, bar_h = x0 + 28, y0 + 62, cw - 56, 32
    d.rounded_rectangle([bar_x, bar_y, bar_x + bar_w, bar_y + bar_h], radius=10, fill=(32, 36, 46, 220))
    frac = 0.92 - 0.58 * drop
    fill_w = max(40, int(bar_w * frac))
    col = (240, 140, 62) if frac > 0.55 else (228, 68, 58)
    d.rounded_rectangle([bar_x, bar_y, bar_x + fill_w, bar_y + bar_h], radius=10, fill=(*col, int(235 * pop)))
    # Jagged seismic crack lines cutting across the bar
    for k in range(3):
        kx = bar_x + int(bar_w * (0.42 + k * 0.21))
        jitter = math.sin(t * 14.0 + k) * 3.0 * drop
        d.line([(kx - 6, bar_y - 6), (kx + 5 + jitter, bar_y + 14), (kx - 4, bar_y + bar_h + 6)], fill=(12, 14, 20, int(230 * drop)), width=4)

    fs = get_font(21)
    pct = int(round(frac * 100))
    d.text((bar_x, y0 + 106), f"ШЕКАРА БАҚЫЛАУЫ: {pct}%  •  ОРТАЛЫҚ ТІРЕК ШАЙҚАЛДЫ", font=fs, fill=(242, 238, 228, int(240 * pop)))


def draw_recon_radar_map(ov: Image.Image, cam: MapCamera, target_wpos=(225, 1170), origin_wpos=(475, 530), t: float = 0.0, tau: float = 0.0):
    """Scene 07: Spinning 360 recon radar sweep & target lock pulses over Bukhara / Samarkand."""
    d = ImageDraw.Draw(ov)
    tx, ty = cam.pt(*target_wpos)
    ox, oy = cam.pt(*origin_wpos)

    # Expanding sonar waves centered on Bukhara political crisis
    for k in range(3):
        prog = (t * 0.52 + k / 3.0) % 1.0
        r = 35 + prog * 235
        a = int(190 * (1.0 - prog))
        d.ellipse([tx - r, ty - r, tx + r, ty + r], outline=(235, 94, 78, a), width=3)

    # Rotating turquoise radar arc sweeping from northern watchpoint
    ang_deg = (t * 95.0) % 360.0
    for rad in (160, 280, 410):
        d.arc([ox - rad, oy - rad, ox + rad, oy + rad], ang_deg - 28, ang_deg + 28, fill=(78, 224, 222, 130), width=4)

    # Target Crosshair box around Bukhara
    lock_u = ease_out(min(1.0, tau / 0.55))
    bx = 72 + 24 * (1.0 - lock_u)
    for sx in (-1, 1):
        for sy in (-1, 1):
            cx, cy = tx + sx * bx, ty + sy * bx
            d.line([(cx, cy), (cx - sx * 18, cy)], fill=(248, 202, 84, int(235 * lock_u)), width=4)
            d.line([(cx, cy), (cx, cy - sy * 18)], fill=(248, 202, 84, int(235 * lock_u)), width=4)


def draw_tempo_wave_card(ov: Image.Image, tau: float, seg_dur: float, t: float, y_center: int = 1155):
    """Scene 08: Animated 3-stage lightning breakthrough card (САЙРАМ -> ТҮРКІСТАН -> ТАШКЕНТ)."""
    d = ImageDraw.Draw(ov)
    pop = ease_out(min(1.0, tau / 0.4))
    prog = ease_out(min(1.0, max(0.0, (tau - 0.1) / max(1.0, seg_dur * 0.7))))
    x0, y0, cw, ch = 120, y_center - 72, W - 240, 144
    d.rounded_rectangle([x0, y0, x0 + cw, y0 + ch], radius=18, fill=(10, 18, 26, int(218 * pop)), outline=(78, 224, 222, int(225 * pop)), width=2)

    ft = get_font(22)
    d.text((x0 + 26, y0 + 16), "ДАМЫЛСЫЗ ШАБУЫЛ ҚАРҚЫНЫ • ҚАМАЛ БҰЗУ", font=ft, fill=(78, 224, 222, int(245 * pop)))

    stages = [("ТҮРКІСТАН", 0.2), ("ОТЫРАР", 0.48), ("САЙРАМ", 0.74), ("ТАШКЕНТ", 0.98)]
    ly = y0 + 78
    sx0, sx1 = x0 + 95, x0 + cw - 95
    d.line([(sx0, ly), (sx1, ly)], fill=(50, 62, 74, 200), width=6)
    d.line([(sx0, ly), (sx0 + (sx1 - sx0) * prog, ly)], fill=(248, 202, 84, 240), width=7)

    fc = get_font(20)
    for idx, (lbl, thr) in enumerate(stages):
        px = sx0 + (sx1 - sx0) * (idx / 3.0)
        done = prog >= thr - 0.08
        col = (248, 202, 84) if done else (110, 125, 140)
        rad = 14 if done else 10
        d.ellipse([px - rad, ly - rad, px + rad, ly + rad], fill=(14, 22, 30, 240), outline=(*col, 250), width=4 if done else 2)
        tw = d.textlength(lbl, font=fc)
        d.text((px - tw / 2, ly + 22), lbl, font=fc, fill=(250, 246, 236, 245 if done else 140))


def draw_domino_cities_counter(ov: Image.Image, n_flipped: int, total: int = 4, y_center: int = 1205):
    """Scene 09 Map Overlay: Live ticking liberation counter synchronized with city captures."""
    d = ImageDraw.Draw(ov)
    cw, ch = 560, 88
    x0, y0 = (W - cw) // 2, y_center - ch // 2
    d.rounded_rectangle([x0, y0, x0 + cw, y0 + ch], radius=16, fill=(10, 16, 24, 222), outline=(248, 202, 84, 235), width=3)
    f1 = get_font(29)
    txt = f"АЗАТ ЕТІЛГЕН ҚАЛАЛАР: {n_flipped} / {total}"
    tw = d.textlength(txt, font=f1)
    d.text(((W - tw) / 2, y0 + 26), txt, font=f1, fill=(248, 202, 84, 252))


def draw_siege_ring_gauge(ov: Image.Image, tau: float, seg_dur: float, t: float, center=(540, 620)):
    """Scene 12: Closing golden-turquoise siege ring perimeter over Bukhara horizon."""
    d = ImageDraw.Draw(ov)
    cx, cy = center
    prog = ease_out(min(1.0, max(0.0, tau / max(1.0, seg_dur * 0.72))))
    rot = t * 28.0
    for rad, span, col, w in [
        (260, int(310 * prog), (248, 202, 84), 6),
        (215, int(265 * prog), (78, 224, 222), 4),
    ]:
        d.arc([cx - rad, cy - rad, cx + rad, cy + rad], rot, rot + span, fill=(*col, 165), width=w)
    # Inward converging ticks
    for k in range(8):
        ang = math.radians(k * 45.0 + rot * 0.4)
        r_out = 300 - 30 * prog
        r_in = 272 - 30 * prog
        d.line([(cx + math.cos(ang) * r_out, cy + math.sin(ang) * r_out), (cx + math.cos(ang) * r_in, cy + math.sin(ang) * r_in)], fill=(255, 225, 130, 180), width=4)


def draw_succession_banner(ov: Image.Image, tau: float, seg_dur: float, t: float, y_center: int = 1150):
    """Scene 13: Dignified unbroken continuity card (ТӘУЕКЕЛ ХАН -> ЕР ЕСІМ ХАН)."""
    d = ImageDraw.Draw(ov)
    pop = ease_out(min(1.0, tau / 0.45))
    prog = ease_out(min(1.0, max(0.0, (tau - 0.25) / max(1.0, seg_dur * 0.55))))
    x0, y0, cw, ch = 100, y_center - 74, W - 200, 148
    d.rounded_rectangle([x0, y0, x0 + cw, y0 + ch], radius=18, fill=(14, 18, 26, int(222 * pop)), outline=(248, 202, 84, int(225 * pop)), width=2)

    ft = get_font(22)
    head = "БИЛІК САБАҚТАСТЫҒЫ • БІРТҰТАС ҚОЛ"
    hw = d.textlength(head, font=ft)
    d.text(((W - hw) / 2, y0 + 18), head, font=ft, fill=(118, 226, 228, int(245 * pop)))

    f_nm = get_font(30)
    left_s, right_s = "ТӘУЕКЕЛ ХАН", "ЕР ЕСІМ ХАН"
    d.text((x0 + 48, y0 + 68), left_s, font=f_nm, fill=(248, 202, 84, int(245 * pop)))
    rw = d.textlength(right_s, font=f_nm)
    d.text((x0 + cw - 48 - rw, y0 + 68), right_s, font=f_nm, fill=(78, 224, 222, int(245 * pop)))

    # Animated bridge arrow moving from left name to right name
    ax0 = x0 + 315
    ax1 = x0 + cw - 305
    ay = y0 + 84
    d.line([(ax0, ay), (ax0 + (ax1 - ax0) * prog, ay)], fill=(255, 232, 150, int(245 * pop)), width=6)
    tip_x = ax0 + (ax1 - ax0) * prog
    d.polygon([(tip_x + 12, ay), (tip_x - 6, ay - 9), (tip_x - 6, ay + 9)], fill=(255, 232, 150, int(250 * pop)))


def draw_200yr_peace_overlay(ov: Image.Image, cam: MapCamera, tau: float, seg_dur: float, t: float, part: str = "both"):
    """Scene 14 Map Overlay: Golden-Turquoise Southern Border Shield & 1598->1798 Rolling Timeline."""
    d = ImageDraw.Draw(ov)
    if part in ("both", "shield"):
        shield_wpts = [
            (200, 345), (360, 425), (490, 520), (600, 610), (775, 645),
            (670, 825), (555, 800), (455, 580), (225, 420), (200, 345),
        ]
        dense_w = eval_polyline(shield_wpts, 120)
        dense_s = cam.pts(dense_w)
        prog = ease_out(min(1.0, max(0.0, tau / max(1.0, seg_dur * 0.65))))
        sub = dense_s[: max(3, int(prog * (len(dense_s) - 1)))]
        if len(sub) >= 3:
            d.line(sub, fill=(78, 224, 222, 120), width=18, joint="curve")
            d.line(sub, fill=(248, 202, 84, 235), width=6, joint="curve")

    if part in ("both", "card"):
        # Timeline Seal Card cleanly slotted between Tashkent and Samarkand
        pop = ease_out(min(1.0, tau / 0.45))
        yr_u = ease_out(min(1.0, max(0.0, (tau - 0.15) / max(1.2, seg_dur * 0.65))))
        yr_cur = int(round(1598 + 200 * yr_u))
        cw, ch = 740, 106
        x0, y0 = (W - cw) // 2, 965
        d.rounded_rectangle([x0, y0, x0 + cw, y0 + ch], radius=18, fill=(10, 18, 26, int(230 * pop)), outline=(248, 202, 84, int(240 * pop)), width=3)
        f_big = get_font(35)
        f_sm = get_font(21)
        head = f"1598 – {yr_cur} • 200 ЖЫЛДЫҚ БЕКІНІС"
        hw = d.textlength(head, font=f_big)
        sub_t = "ТҮРКІСТАН • САЙРАМ • ТАШКЕНТ ҚАЗАҚ ХАНДЫҒЫНДА"
        sw = d.textlength(sub_t, font=f_sm)
        d.text(((W - hw) / 2, y0 + 14), head, font=f_big, fill=(248, 202, 84, int(252 * pop)))
        d.text(((W - sw) / 2, y0 + 65), sub_t, font=f_sm, fill=(116, 228, 228, int(245 * pop)))


def draw_dawn_rays_crest(ov: Image.Image, tau: float, t: float, origin=(540, 620)):
    """Scene 15: Volumetric golden sunrise beams + Turkestan Capital Crest."""
    d = ImageDraw.Draw(ov)
    ox, oy = origin
    pop = ease_out(min(1.0, tau / 0.5))
    for k in range(12):
        ang = math.radians(-160 + k * 28 + math.sin(t * 0.7 + k) * 4.5)
        w_ang = 0.085
        r_far = 1150
        p1 = (ox, oy)
        p2 = (ox + math.cos(ang - w_ang) * r_far, oy + math.sin(ang - w_ang) * r_far)
        p3 = (ox + math.cos(ang + w_ang) * r_far, oy + math.sin(ang + w_ang) * r_far)
        a = int((26 + 14 * math.sin(t * 2.2 + k)) * pop)
        d.polygon([p1, p2, p3], fill=(255, 222, 130, a))

    # Crest card at y=1110
    cw, ch = 680, 98
    x0, y0 = (W - cw) // 2, 1110
    d.rounded_rectangle([x0, y0, x0 + cw, y0 + ch], radius=18, fill=(14, 18, 26, int(218 * pop)), outline=(248, 202, 84, int(240 * pop)), width=3)
    f1, f2 = get_font(31), get_font(21)
    t1 = "ТҮРКІСТАН — ХАН ОРДАСЫ"
    t2 = "ОРТАЛЫҚ АЗИЯ ТҰРАҚТЫЛЫҒЫНЫҢ ТІРЕГІ"
    d.text(((W - d.textlength(t1, font=f1)) / 2, y0 + 14), t1, font=f1, fill=(248, 202, 84, int(252 * pop)))
    d.text(((W - d.textlength(t2, font=f2)) / 2, y0 + 58), t2, font=f2, fill=(116, 224, 228, int(245 * pop)))


def draw_loop_surge_arrows(ov: Image.Image, tau: float, t: float):
    """Scene 16 Seamless Loop Bridge: Rising golden chevron waves feeding back into Scene 01."""
    d = ImageDraw.Draw(ov)
    for idx in range(5):
        phase = ((t * 0.9 + idx * 0.2) % 1.0)
        y = 1220 - phase * 620
        a = int(190 * math.sin(math.pi * phase))
        cx = 540
        hw = 180 + idx * 14
        pts = [(cx - hw, y + 36), (cx, y), (cx + hw, y + 36)]
        d.line(pts, fill=(248, 202, 84, a), width=7, joint="curve")
    pop = ease_out(min(1.0, tau / 0.4))
    cw, ch = 760, 88
    x0, y0 = (W - cw) // 2, 1150
    d.rounded_rectangle([x0, y0, x0 + cw, y0 + ch], radius=16, fill=(12, 18, 26, int(222 * pop)), outline=(78, 224, 222, int(235 * pop)), width=2)
    f1 = get_font(25)
    txt = "БІРЛІК ПЕН ЖЫЛДАМДЫҚ • 200 ЖЫЛДЫҚ БЕКІНІС"
    d.text(((W - d.textlength(txt, font=f1)) / 2, y0 + 28), txt, font=f1, fill=(250, 246, 236, int(250 * pop)))
