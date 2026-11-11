"""High-displacement multi-layer object animation for scenes 17, 18, 19, 20."""
import glob
import math
import subprocess
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter
from scipy.ndimage import gaussian_filter, map_coordinates

ROOT = Path(__file__).resolve().parent
SCENES_DIR = ROOT.parent / "scenes"
VIDEO_DIR = ROOT.parent / "scenes_video"
W, H, FPS = 480, 832, 24
N_FRAMES = 77


def load_rgb(name: str) -> np.ndarray:
    p = sorted(SCENES_DIR.glob(f"{name}_*.jpg"))[0]
    im = Image.open(p).convert("RGB").resize((W, H), Image.LANCZOS)
    return np.asarray(im, dtype=np.float32)


def save_mp4(frames: list[np.ndarray], out_path: Path):
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
        "-i", "-", "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-pix_fmt", "yuv420p", str(out_path),
    ]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for f in frames:
        p.stdin.write(np.clip(f, 0, 255).astype(np.uint8).tobytes())
    p.stdin.close()
    p.wait()


def warp_rgb(img: np.ndarray, dy: np.ndarray, dx: np.ndarray) -> np.ndarray:
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    ny = np.clip(yy - dy, 0, H - 1)
    nx = np.clip(xx - dx, 0, W - 1)
    out = np.empty_like(img)
    for c in range(3):
        out[..., c] = map_coordinates(img[..., c], [ny, nx], order=1, mode="nearest")
    return out


def warp_mask(mask: np.ndarray, dy: np.ndarray, dx: np.ndarray) -> np.ndarray:
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    ny = np.clip(yy - dy, 0, H - 1)
    nx = np.clip(xx - dx, 0, W - 1)
    return map_coordinates(mask, [ny, nx], order=1, mode="constant", cval=0.0)


def make_scene_17():
    """Duel: Left rider and Right rider charge toward each other, clash with explosion of sparks, banner falls."""
    img = load_rgb("scene_17")
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    yn, xn = yy / H, xx / W

    lum = 0.299 * img[..., 0] + 0.587 * img[..., 1] + 0.114 * img[..., 2]
    dark = np.clip((85.0 - lum) / 45.0, 0.0, 1.0) * (yn > 0.30) * (yn < 0.82)

    left_mask = gaussian_filter(dark * (xn < 0.48) * ( 1.0 - (xn > 0.40) * (yn > 0.58) ), sigma=1.5)
    right_mask = gaussian_filter(dark * (xn > 0.52), sigma=1.5)
    banner_mask = gaussian_filter(dark * (xn >= 0.38) * (xn <= 0.53) * (yn >= 0.57) * (yn < 0.83), sigma=1.5)

    # Inpaint golden background behind silhouettes using horizontal background interpolation
    bg = img.copy()
    all_sil = np.clip(left_mask + right_mask + banner_mask, 0, 1)
    for r in range(int(0.30 * H), int(0.84 * H)):
        row_gold = np.percentile(img[r], 85, axis=0)
        bg[r] = bg[r] * (1 - all_sil[r, :, None]) + row_gold[None, :] * all_sil[r, :, None]
    bg = gaussian_filter(bg, sigma=[2.0, 2.0, 0]) * all_sil[..., None] + img * (1 - all_sil[..., None])

    rng = np.random.default_rng(17)
    n_sparks = 160
    ang = rng.uniform(0, 2 * math.pi, n_sparks)
    spd = rng.uniform(60, 320, n_sparks)
    vx, vy = np.cos(ang) * spd, np.sin(ang) * spd - 60

    frames = []
    for i in range(N_FRAMES):
        u = i / (N_FRAMES - 1)
        # Phase 1 (u < 0.28): charge together; Phase 2 (u >= 0.28): clash impact + recoil + continual struggle
        if u < 0.28:
            p = u / 0.28
            ldx = -42.0 * (1 - p)
            ldy = -8.0 * abs(math.sin(p * math.pi * 2))
            rdx = 38.0 * (1 - p)
            rdy = -7.0 * abs(math.cos(p * math.pi * 2))
        else:
            p = (u - 0.28) / 0.72
            ldx = 6.0 * math.sin(p * math.pi * 3) + 10.0 * p
            ldy = -9.0 * abs(math.sin(u * math.pi * 6))
            rdx = -5.0 * math.sin(p * math.pi * 3) - 8.0 * p
            rdy = -8.0 * abs(math.cos(u * math.pi * 6))

        # Saber swing on upper part of left rider
        swing = 18.0 * math.sin(u * math.pi * 4) * np.clip((0.48 - yn) / 0.16, 0, 1)
        l_dx_map = np.full((H, W), ldx, dtype=np.float32) + swing
        l_dy_map = np.full((H, W), ldy, dtype=np.float32) + swing * 0.7

        r_dx_map = np.full((H, W), rdx, dtype=np.float32)
        r_dy_map = np.full((H, W), rdy, dtype=np.float32)

        # Falling enemy banner rotates and drops down into dust after u=0.25
        bp = max(0.0, (u - 0.20) / 0.80)
        b_dx_map = (yy - 0.72 * H) * (0.45 * bp) + 18.0 * bp
        b_dy_map = 55.0 * (bp ** 1.4)

        # Moving dust clouds at bottom
        dust_dx = np.full((H, W), -35.0 * u, dtype=np.float32) * np.clip((yn - 0.65) / 0.25, 0, 1)
        frame = warp_rgb(bg, np.zeros((H, W), dtype=np.float32), dust_dx)

        # Composite falling banner
        bm = warp_mask(banner_mask, b_dy_map, b_dx_map)[..., None]
        bf = warp_rgb(img, b_dy_map, b_dx_map)
        frame = frame * (1 - bm) + bf * bm

        # Composite left and right riders
        lm = warp_mask(left_mask, l_dy_map, l_dx_map)[..., None]
        lf = warp_rgb(img, l_dy_map, l_dx_map)
        frame = frame * (1 - lm) + lf * lm

        rm = warp_mask(right_mask, r_dy_map, r_dx_map)[..., None]
        rf = warp_rgb(img, r_dy_map, r_dx_map)
        frame = frame * (1 - rm) + rf * rm

        # Clash sparks & flash burst at (0.48*W, 0.43*H)
        cx, cy = 0.48 * W, 0.43 * H
        dt = (u - 0.26) if u >= 0.26 else u * 0.4
        if dt > 0:
            flash = math.exp(-dt * 7.0) * 0.55
            dist2 = ((xx - cx) ** 2 + (yy - cy) ** 2) / (160.0 ** 2)
            frame += np.exp(-dist2)[..., None] * np.array([255, 220, 120], dtype=np.float32) * flash
            for k in range(n_sparks):
                sx = int(cx + vx[k] * dt)
                sy = int(cy + vy[k] * dt + 220 * (dt ** 2))
                if 2 <= sx < W - 2 and 2 <= sy < H - 2:
                    frame[sy - 2:sy + 2, sx - 2:sx + 2] = [255, 240, 150]

        frames.append(frame)
    save_mp4(frames, VIDEO_DIR / "scene_17.mp4")
    print("[ok] scene_17.mp4 generated")


def make_scene_18():
    """Bird's-eye encirclement: cavalry crescent sweeps forward along the gorge, smoke rises, tactical camera orbit."""
    img = load_rgb("scene_18")
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    yn, xn = yy / H, xx / W

    # Vortex center of the Anyrakai encirclement
    cx, cy = 0.46 * W, 0.51 * H
    rx, ry = xx - cx, yy - cy
    rad = np.sqrt(rx ** 2 + ry ** 2) / (0.32 * W)
    ring_mask = np.exp(-((rad - 0.65) ** 2) / 0.18) * (yn > 0.32) * (yn < 0.72)

    # White smoke / dust plumes rising
    lum = 0.299 * img[..., 0] + 0.587 * img[..., 1] + 0.114 * img[..., 2]
    smoke_mask = np.clip((lum - 145.0) / 60.0, 0, 1) * (yn > 0.15) * (yn < 0.65)

    frames = []
    for i in range(N_FRAMES):
        u = i / (N_FRAMES - 1)
        # Rotational advance of the cavalry ring closing the encirclement + inward squeeze
        theta = 0.28 * u * ring_mask
        squeeze = 0.14 * u * ring_mask
        dx_ring = (-ry * np.sin(theta) - rx * squeeze)
        dy_ring = (rx * np.sin(theta) - ry * squeeze)

        # Rising smoke and drifting clouds
        dy_smoke = -38.0 * u * smoke_mask + 6.0 * np.sin(xx / 18.0 + u * 6.0) * smoke_mask
        dx_smoke = 22.0 * u * smoke_mask

        # Global aerial drone push-in and slight banking
        zoom = 1.0 + 0.14 * u
        bank = 0.05 * u
        g_dx = (xx - W / 2) * (1 - 1 / zoom) - (yy - H / 2) * bank
        g_dy = (yy - H / 2) * (1 - 1 / zoom) + (xx - W / 2) * bank

        frame = warp_rgb(img, g_dy + dy_ring + dy_smoke, g_dx + dx_ring + dx_smoke)
        frames.append(frame)
    save_mp4(frames, VIDEO_DIR / "scene_18.mp4")
    print("[ok] scene_18.mp4 generated")


def make_scene_19():
    """Golden dawn: Eagle flies across the sky flapping wings, banners wave strongly in the wind, sun rays shimmer."""
    img = load_rgb("scene_19")
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    yn, xn = yy / H, xx / W

    # Extract eagle silhouette at (xn ~ 0.60..0.72, yn ~ 0.15..0.22)
    lum = 0.299 * img[..., 0] + 0.587 * img[..., 1] + 0.114 * img[..., 2]
    eagle_box = (xn > 0.56) * (xn < 0.74) * (yn > 0.14) * (yn < 0.22)
    eagle_mask = gaussian_filter(np.clip((130.0 - lum) / 40.0, 0, 1) * eagle_box, sigma=1.0)

    # Inpaint sky behind eagle
    bg = img.copy()
    for r in range(int(0.14 * H), int(0.22 * H)):
        sky_col = np.percentile(img[r, int(0.50 * W):int(0.78 * W)], 85, axis=0)
        bg[r] = bg[r] * (1 - eagle_mask[r, :, None]) + sky_col[None, :] * eagle_mask[r, :, None]

    # Banner cloth mask (blue/white flags on the peak: xn 0.18..0.78, yn 0.22..0.64)
    banner_mask = gaussian_filter(((xn > 0.18) * (xn < 0.78) * (yn > 0.22) * (yn < 0.64)).astype(np.float32), sigma=8.0)
    sky_mask = np.clip((0.55 - yn) / 0.20, 0, 1)

    frames = []
    for i in range(N_FRAMES):
        u = i / (N_FRAMES - 1)
        # 1. Flowing clouds in sky + slow heroic camera push
        zoom = 1.0 + 0.10 * u
        dx = (xx - W / 2) * (1 - 1 / zoom) + 24.0 * u * sky_mask
        dy = (yy - H / 2) * (1 - 1 / zoom)

        # 2. Vigorous cloth wave on the battle standards
        wave_phase = (xx / 22.0) - u * 14.0
        dx += (14.0 * np.sin(wave_phase) + 6.0 * np.cos(yy / 18.0 - u * 10.0)) * banner_mask
        dy += (9.0 * np.cos(wave_phase) + 4.0 * np.sin(xx / 15.0 - u * 12.0)) * banner_mask

        frame = warp_rgb(bg, dy, dx)

        # 3. Eagle flying across the sky from left-center to upper-right with wing beat
        e_dx = -65.0 + 135.0 * u
        e_dy = 22.0 - 48.0 * u + 4.0 * math.sin(u * math.pi * 6)
        wing_flap = 6.0 * math.sin(u * math.pi * 8) * np.abs(xn - 0.65) * 15.0
        ed_x = np.full((H, W), e_dx, dtype=np.float32)
        ed_y = np.full((H, W), e_dy, dtype=np.float32) + wing_flap

        em = warp_mask(eagle_mask, ed_y, ed_x)[..., None]
        ef = warp_rgb(img, ed_y, ed_x)
        frame = frame * (1 - em) + ef * em

        # 4. Pulsing golden sunrise rays around (0.68*W, 0.41*H)
        sx, sy = 0.68 * W, 0.41 * H
        dist2 = ((xx - sx) ** 2 + (yy - sy) ** 2) / (180.0 ** 2)
        glow = (0.10 + 0.08 * math.sin(u * math.pi * 3)) * np.exp(-dist2)
        frame += glow[..., None] * np.array([255, 210, 110], dtype=np.float32)

        frames.append(frame)
    save_mp4(frames, VIDEO_DIR / "scene_19.mp4")
    print("[ok] scene_19.mp4 generated")


def make_scene_20():
    """Seamless loop close-up: Hand grips reins and draws gleaming curved steel saber blade out of scabbard."""
    img = load_rgb("scene_20")
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    yn, xn = yy / H, xx / W

    # Diagonal axis of the saber draw (from bottom-left scabbard to upper-right hilt: angle ~ -56 deg)
    # Upper-right region along the blade & hand (hand + hilt + steel blade being drawn out)
    along = (xn - 0.35) * 0.56 - (yn - 0.62) * 0.83
    across = (xn - 0.35) * 0.83 + (yn - 0.62) * 0.56
    hand_blade_mask = gaussian_filter(
        ((along > -0.04) * (yn > 0.28) * (yn < 0.72) * (xn < 0.88)).astype(np.float32),
        sigma=6.0,
    )
    horse_bg_mask = gaussian_filter(((yn < 0.45) * (xn > 0.35)).astype(np.float32), sigma=8.0)

    frames = []
    for i in range(N_FRAMES):
        u = i / (N_FRAMES - 1)
        # Smooth ease-in-out draw of the saber along the scabbard angle (+38 px right, -56 px up)
        draw_u = 0.5 - 0.5 * math.cos(u * math.pi)
        dx = 38.0 * draw_u * hand_blade_mask
        dy = -56.0 * draw_u * hand_blade_mask

        # Horse head in background breathing and shifting
        dx += 14.0 * math.sin(u * math.pi * 2) * horse_bg_mask
        dy += 10.0 * math.cos(u * math.pi * 2) * horse_bg_mask

        # Dramatic push-in toward the gleaming blade for seamless loop into Scene 1
        zoom = 1.0 + 0.18 * (u ** 1.3)
        dx += (xx - 0.52 * W) * (1 - 1 / zoom)
        dy += (yy - 0.54 * H) * (1 - 1 / zoom)

        frame = warp_rgb(img, dy, dx)

        # Specular metallic gleam traveling along the exposed steel blade
        gleam_y = (0.62 - 0.22 * u) * H
        gleam_x = (0.48 + 0.16 * u) * W
        g_dist2 = ((xx - gleam_x) ** 2 + (yy - gleam_y) ** 2) / (42.0 ** 2)
        lum = 0.299 * frame[..., 0] + 0.587 * frame[..., 1] + 0.114 * frame[..., 2]
        steel_mask = np.clip((lum - 110.0) / 60.0, 0, 1) * (yn > 0.42) * (yn < 0.72)
        frame += (np.exp(-g_dist2) * steel_mask)[..., None] * np.array([210, 235, 255], dtype=np.float32) * 0.75

        frames.append(frame)
    save_mp4(frames, VIDEO_DIR / "scene_20.mp4")
    print("[ok] scene_20.mp4 generated")


if __name__ == "__main__":
    make_scene_17()
    make_scene_18()
    make_scene_19()
    make_scene_20()
