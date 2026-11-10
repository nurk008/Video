"""3D Depth-Parallax + Articulated Subject Motion + Particle Physics Animator.

Uses Depth-Anything-V2-Small ONNX to estimate dense 3D scene depth for any scene not yet
in scenes_video/, and synthesizes a 24fps living video clip with:
- Multi-plane 3D depth parallax (foreground silhouettes move independently of background)
- Scene-specific articulated motion (horse gallop/breathing, waving banners, blade clash/draw,
  campfire flicker, river current)
- Real particle physics overlays (rising glowing embers, flying sparks, drifting steppe dust,
  splashing water droplets, golden sun rays)
"""
import math
import subprocess
import sys
import urllib.request
from pathlib import Path

import numpy as np
import onnxruntime as ort
from PIL import Image
from scipy import ndimage

ROOT = Path(__file__).resolve().parent
SCENES_DIR = ROOT.parent / "scenes"
VIDEO_DIR = ROOT.parent / "scenes_video"
VIDEO_DIR.mkdir(exist_ok=True)
DEPTH_MODEL = Path("/tmp/depth_v2.onnx")
DEPTH_URL = "https://huggingface.co/onnx-community/depth-anything-v2-small/resolve/main/onnx/model_quantized.onnx"

# Scene-specific motion & particle presets
SCENE_FX = {
    "scene_08b": {"cam": (0.0, -14.0, 0.08), "wave": "banners", "dust": 0.45},
    "scene_09":  {"cam": (0.0, -8.0, 0.12),  "wave": "clash",   "embers": 0.9, "sparks": 0.7, "fire_glow": 0.55},
    "scene_09b": {"cam": (6.0, -16.0, 0.09), "wave": "fire",    "embers": 1.0, "fire_glow": 0.75},
    "scene_10":  {"cam": (-26.0, 0.0, 0.10), "wave": "gallop",  "water": 0.9,  "dust": 0.35},
    "scene_11":  {"cam": (0.0, -6.0, 0.10),  "wave": "hands",   "glint": 0.6},
    "scene_12":  {"cam": (8.0, -14.0, 0.11), "wave": "rider",   "dust": 0.4},
    "scene_13":  {"cam": (24.0, 6.0, 0.13),  "wave": "gallop",  "dust": 0.75},
    "scene_14":  {"cam": (-22.0, 0.0, 0.08), "wave": "banners", "dust": 0.65},
    "scene_15":  {"cam": (0.0, -12.0, 0.12), "wave": "rider",   "dust": 0.45},
    "scene_16":  {"cam": (22.0, -10.0, 0.16),"wave": "gallop",  "dust": 0.85, "sun_flare": 0.5},
    "scene_17":  {"cam": (0.0, -6.0, 0.12),  "wave": "duel",    "sparks": 1.0, "dust": 0.6, "sun_flare": 0.65},
    "scene_18":  {"cam": (14.0, -14.0, 0.12),"wave": "cavalry", "dust": 0.75},
    "scene_19":  {"cam": (0.0, 12.0, -0.09), "wave": "banners", "sun_flare": 0.55},
    "scene_20":  {"cam": (-10.0, -12.0, 0.14),"wave": "draw",   "glint": 0.9},
}


def get_depth_session():
    if not DEPTH_MODEL.exists():
        urllib.request.urlretrieve(DEPTH_URL, DEPTH_MODEL)
    return ort.InferenceSession(str(DEPTH_MODEL))


def predict_depth(sess, img: Image.Image) -> np.ndarray:
    w, h = img.size
    tw, th = (w // 14) * 14, (h // 14) * 14
    arr = np.asarray(img.resize((tw, th), Image.BILINEAR), dtype=np.float32) / 255.0
    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
    inp = ((arr - mean) / std).transpose(2, 0, 1)[None, ...]
    pred = sess.run(None, {"pixel_values": inp})[0][0]
    d_img = Image.fromarray(pred).resize((w, h), Image.BILINEAR)
    d = np.asarray(d_img, dtype=np.float32)
    d = ndimage.gaussian_filter(d, sigma=3.5)
    d = (d - d.min()) / (d.max() - d.min() + 1e-6)
    return d  # 0.0 = far background, 1.0 = closest foreground


def make_particles(rng, count, w, h, kind="embers"):
    px = rng.uniform(0, w, count)
    py = rng.uniform(0, h, count)
    vx = rng.uniform(-90, 90, count) if kind != "sparks" else rng.normal(0, 260, count)
    vy = rng.uniform(-220, -80, count) if kind == "embers" else (
        rng.uniform(-260, 180, count) if kind == "sparks" else rng.uniform(-160, -40, count)
    )
    if kind == "sparks":
        px = w * 0.48 + rng.normal(0, 28, count)
        py = h * 0.45 + rng.normal(0, 28, count)
    sz = rng.uniform(1.8, 5.2, count)
    bright = rng.uniform(0.5, 1.0, count)
    return {"x": px, "y": py, "vx": vx, "vy": vy, "sz": sz, "b": bright}


def render_scene_clip(sess, name: str, fps: int = 24, duration: float = 3.2):
    out_path = VIDEO_DIR / f"{name}.mp4"
    if out_path.exists() and out_path.stat().st_size > 50_000:
        print(f"[skip] {name}.mp4 exists")
        return

    img_path = next(SCENES_DIR.glob(f"{name}_*.jpg"))
    img = Image.open(img_path).convert("RGB")
    w, h = img.size
    base = np.asarray(img, dtype=np.float32)
    depth = predict_depth(sess, img)
    fx = SCENE_FX.get(name, {"cam": (0.0, -10.0, 0.10), "wave": "banners", "dust": 0.4})

    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    n_frames = int(round(fps * duration))
    rng = np.random.default_rng(abs(hash(name)) % 100000)

    # Pre-generate smooth volumetric dust clouds (multi-octave filtered noise)
    dust_tex = ndimage.gaussian_filter(rng.standard_normal((h, w * 2)).astype(np.float32), sigma=28.0)
    dust_tex = (dust_tex - dust_tex.min()) / (dust_tex.max() - dust_tex.min() + 1e-6)

    embers = make_particles(rng, 85, w, h, "embers") if fx.get("embers") else None
    sparks = make_particles(rng, 110, w, h, "sparks") if fx.get("sparks") else None
    drops = make_particles(rng, 120, w, h, "water") if fx.get("water") else None

    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
         "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r", str(fps), "-i", "-",
         "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p", str(out_path)],
        stdin=subprocess.PIPE,
    )

    dx_cam, dy_cam, dz_cam = fx["cam"]
    wave_mode = fx.get("wave", "banners")

    for fi in range(n_frames):
        t = fi / fps
        u = fi / max(1, n_frames - 1)
        # Smooth ease curve
        u_smooth = 0.5 * u + 0.5 * (1 - math.cos(math.pi * u))

        # 1. 3D Depth-Map Parallax + Camera Push
        # Foreground moves up to 2.4x faster than background; slight overscan avoids border clamp
        scale = 1.04 + dz_cam * u_smooth * (0.45 + 0.85 * depth)
        par_x = dx_cam * (u_smooth - 0.5) * (0.25 + 1.35 * depth)
        par_y = dy_cam * (u_smooth - 0.5) * (0.25 + 1.35 * depth)

        # 2. Articulated Subject Deformation per scene type
        art_x = np.zeros_like(depth)
        art_y = np.zeros_like(depth)

        if wave_mode == "gallop":
            # Rhythmic cavalry gallop bobbing + forward surge on foreground horses/riders
            bob = math.sin(2 * math.pi * 2.6 * t) * 7.5 * (depth ** 1.5)
            surge = np.sin(yy / 42.0 - 9.0 * t) * 3.2 * (depth ** 1.3)
            art_y += bob
            art_x += surge
        elif wave_mode == "rider":
            # Breathing warhorse + subtle torso/cape sway + wind ripple
            breath = math.sin(2 * math.pi * 0.9 * t) * 5.0 * (depth ** 1.6)
            wind_w = np.sin(xx / 28.0 + yy / 45.0 - 7.5 * t) * 3.5 * (depth ** 1.2)
            art_y += breath
            art_x += wind_w
        elif wave_mode == "banners":
            # Cloth banner rippling in wind + slow atmospheric motion
            cloth = np.sin(xx / 22.0 - 10.0 * t + yy / 60.0) * 4.5 * np.clip(1.2 - yy / (h * 0.85), 0.2, 1.0)
            art_x += cloth * (0.4 + 0.6 * depth)
            art_y += np.cos(xx / 30.0 - 8.0 * t) * 2.2 * depth
        elif wave_mode == "clash":
            # Crossed blades pressing together and vibrating from impact
            sign_x = np.sign(xx - w * 0.5)
            press = -sign_x * 12.0 * u_smooth * (depth ** 1.4)
            vib = math.sin(t * 48.0) * math.exp(-t * 1.2) * 4.0 * depth
            art_x += press + vib
        elif wave_mode == "fire":
            # Heat shimmer rising above campfire + warrior silhouettes breathing
            heat = np.sin(yy / 16.0 - 14.0 * t + xx / 25.0) * 4.2 * (1.0 - depth * 0.5)
            art_x += heat
            art_y += math.sin(2 * math.pi * 0.8 * t) * 3.5 * depth
        elif wave_mode == "hands":
            # Hands passing weapons toward center
            sign_x = np.sign(xx - w * 0.5)
            art_x += -sign_x * 14.0 * u_smooth * (depth ** 1.3)
            art_y += math.sin(2 * math.pi * 1.1 * t) * 3.0 * depth
        elif wave_mode == "duel":
            # Two riders colliding inward at high speed + impact shock
            sign_x = np.sign(xx - w * 0.5)
            lunge = -sign_x * 22.0 * (u ** 0.7) * (depth ** 1.3)
            shock = math.sin(t * 55.0) * math.exp(-abs(t - 0.35) * 6.0) * 7.0
            art_x += lunge + shock
            art_y += math.sin(2 * math.pi * 2.8 * t) * 6.0 * depth
        elif wave_mode == "cavalry":
            # Crescent wings sweeping inward to encircle
            dx_c = (xx - w * 0.5) / (w * 0.5)
            dy_c = (yy - h * 0.55) / (h * 0.5)
            art_x += -dx_c * 18.0 * u_smooth * (0.4 + 0.6 * depth)
            art_y += dy_c * 12.0 * u_smooth * (0.4 + 0.6 * depth)
        elif wave_mode == "draw":
            # Hand drawing curved saber upward-right from scabbard
            fg = np.clip((depth - 0.45) / 0.55, 0.0, 1.0)
            upper_half = np.clip(1.0 - (yy - h * 0.25) / (h * 0.55), 0.0, 1.0)
            pull = fg * upper_half * u_smooth
            art_x += 16.0 * pull
            art_y += -22.0 * pull

        sx = (xx - w * 0.5) / scale + w * 0.5 - par_x - art_x
        sy = (yy - h * 0.5) / scale + h * 0.5 - par_y - art_y

        # Fast bilinear warp
        x0 = np.clip(np.floor(sx).astype(np.int32), 0, w - 2)
        y0 = np.clip(np.floor(sy).astype(np.int32), 0, h - 2)
        wx = (np.clip(sx, 0, w - 1.001) - x0)[..., None]
        wy = (np.clip(sy, 0, h - 1.001) - y0)[..., None]
        frame = (
            base[y0, x0] * (1 - wx) * (1 - wy)
            + base[y0, x0 + 1] * wx * (1 - wy)
            + base[y0 + 1, x0] * (1 - wx) * wy
            + base[y0 + 1, x0 + 1] * wx * wy
        )

        # 3. Dynamic Lighting & Atmospheric Overlays
        if fx.get("fire_glow"):
            flicker = 1.0 + fx["fire_glow"] * (0.14 * math.sin(19 * t) + 0.09 * math.cos(31 * t))
            glow_mask = np.clip((yy / h - 0.25) / 0.75, 0.0, 1.0)[..., None]
            frame[..., 0] = frame[..., 0] * (1 + (flicker - 1) * 1.3 * glow_mask[..., 0])
            frame[..., 1] = frame[..., 1] * (1 + (flicker - 1) * 0.7 * glow_mask[..., 0])

        if fx.get("sun_flare"):
            pulse = 1.0 + 0.16 * math.sin(5.5 * t) * fx["sun_flare"]
            sun_mask = np.exp(-(((xx - w * 0.5) / (w * 0.45)) ** 2 + ((yy - h * 0.28) / (h * 0.28)) ** 2))[..., None]
            frame += sun_mask * np.array([48.0, 34.0, 12.0], dtype=np.float32) * pulse

        if fx.get("glint"):
            # Moving specular metallic gleam across steel blade
            band_pos = (0.25 + 0.55 * u_smooth) * h
            band = np.exp(-(((yy + 0.6 * (xx - w * 0.5)) - band_pos) / 38.0) ** 2) * (depth > 0.5)
            frame += band[..., None] * np.array([95.0, 105.0, 120.0], dtype=np.float32) * fx["glint"]

        if fx.get("dust"):
            shift = int((u * w * 0.45)) % w
            d_layer = dust_tex[:, shift:shift + w]
            mid_mask = ((1.0 - depth * 0.65) * np.clip((yy / h - 0.15) / 0.7, 0.1, 1.0))[..., None]
            frame = frame * (1 - 0.22 * fx["dust"] * d_layer[..., None] * mid_mask) + (
                np.array([215.0, 185.0, 140.0], dtype=np.float32) * (0.26 * fx["dust"] * d_layer[..., None] * mid_mask)
            )

        # 4. Particle Systems (Embers / Sparks / Water Spray)
        for pset, col, grav in [
            (embers, (255.0, 140.0, 35.0), -15.0),
            (sparks, (255.0, 220.0, 95.0), 340.0),
            (drops,  (235.0, 240.0, 250.0), 220.0),
        ]:
            if pset is None:
                continue
            px = (pset["x"] + pset["vx"] * t + 18.0 * np.sin(4.0 * t + pset["b"] * 6.0)) % w
            py = (pset["y"] + pset["vy"] * t + 0.5 * grav * (t ** 2)) % h
            for xi, yi, szi, bi in zip(px.astype(int), py.astype(int), pset["sz"], pset["b"]):
                r = max(1, int(szi))
                y1, y2 = max(0, yi - r), min(h, yi + r + 1)
                x1, x2 = max(0, xi - r), min(w, xi + r + 1)
                frame[y1:y2, x1:x2, 0] = np.minimum(255.0, frame[y1:y2, x1:x2, 0] + col[0] * bi * 0.75)
                frame[y1:y2, x1:x2, 1] = np.minimum(255.0, frame[y1:y2, x1:x2, 1] + col[1] * bi * 0.75)
                frame[y1:y2, x1:x2, 2] = np.minimum(255.0, frame[y1:y2, x1:x2, 2] + col[2] * bi * 0.75)

        ff.stdin.write(np.clip(frame, 0, 255).astype(np.uint8).tobytes())

    ff.stdin.close()
    ff.wait()
    print(f"[3d-animated] {name}.mp4 -> {out_path.stat().st_size // 1024} KB", flush=True)


if __name__ == "__main__":
    sess = get_depth_session()
    targets = sys.argv[1:] if len(sys.argv) > 1 else list(SCENE_FX.keys())
    for name in targets:
        render_scene_clip(sess, name)
