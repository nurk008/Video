"""Build all 16 animated video clips for Episode 2 (Battle of Orbulak 1643) in scenes_ep02_video/.

Uses strictly rigid camera motion (push-in, pan, tilt, impact shake) + atmospheric/particle overlays
(muzzle flashes, gunsmoke, sparks, rockslide) without non-uniform sine-wave pixel warping, eliminating
any 'floating/jelly' distortion on rocks, cliffs, and silhouettes.
"""
import math
import subprocess
from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent
EP1_VID = ROOT.parent / "scenes_video"
EP2_IMG = ROOT.parent / "scenes_ep02"
EP2_VID = ROOT.parent / "scenes_ep02_video"
EP2_VID.mkdir(exist_ok=True)
W, H, FPS = 480, 832, 24
N = 77


def read_mp4(path: Path, n_frames: int = N) -> list[np.ndarray]:
    raw = subprocess.check_output([
        "ffmpeg", "-v", "error", "-i", str(path),
        "-vf", f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-"
    ])
    fb = W * H * 3
    m = max(1, len(raw) // fb)
    src = [np.frombuffer(raw, dtype=np.uint8, count=fb, offset=i * fb).reshape((H, W, 3)).astype(np.float32) for i in range(m)]
    return [src[min(m - 1, int(i * m / n_frames))].copy() for i in range(n_frames)]


def read_jpg(path: Path) -> np.ndarray:
    im = Image.open(path).convert("RGB").resize((W, H), Image.LANCZOS)
    return np.asarray(im, dtype=np.float32)


def write_mp4(frames: list[np.ndarray], out_path: Path):
    p = subprocess.Popen([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
        "-i", "-", "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-pix_fmt", "yuv420p", str(out_path)
    ], stdin=subprocess.PIPE)
    for f in frames:
        p.stdin.write(np.clip(f, 0, 255).astype(np.uint8).tobytes())
    p.stdin.close()
    p.wait()
    print(f"[ok] {out_path.name} ({out_path.stat().st_size // 1024} KB)")


def rigid_cam(img: np.ndarray, zoom: float = 1.0, pan_x: float = 0.0, pan_y: float = 0.0, cx: float = 0.5, cy: float = 0.5) -> np.ndarray:
    """Apply a strictly rigid uniform zoom + pan crop (zero non-uniform warping or jelly distortion)."""
    z = max(1.0, float(zoom))
    cw, ch = W / z, H / z
    x0 = np.clip(cx * W - cw / 2.0 + pan_x, 0.0, W - cw)
    y0 = np.clip(cy * H - ch / 2.0 + pan_y, 0.0, H - ch)
    pil_im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    cropped = pil_im.transform((W, H), Image.EXTENT, (x0, y0, x0 + cw, y0 + ch), Image.BICUBIC)
    return np.asarray(cropped, dtype=np.float32)


def build_all():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    yn, xn = yy / H, xx / W
    rng = np.random.default_rng(1643)

    # 1. scene_01: 600 warriors in stone trench aiming matchlocks down into serpentine canyon
    img1 = read_jpg(EP2_IMG / "scene_01.jpg")
    frames = []
    for i in range(N):
        u = i / (N - 1)
        u_ease = 0.5 - 0.5 * math.cos(u * math.pi)
        f = rigid_cam(img1, zoom=1.02 + 0.12 * u_ease, pan_x=-8.0 * u_ease, pan_y=6.0 * u_ease, cx=0.45, cy=0.48)
        frames.append(f)
    write_mp4(frames, EP2_VID / "scene_01.mp4")

    # 2. scene_02: 50,000 invasion army advancing through dust in Dzungarian Alatau
    img2 = read_jpg(EP2_IMG / "scene_02.jpg")
    frames = []
    for i in range(N):
        u = i / (N - 1)
        u_ease = 0.5 - 0.5 * math.cos(u * math.pi)
        f = rigid_cam(img2, zoom=1.04 + 0.14 * u_ease, pan_x=10.0 * u_ease, pan_y=-12.0 * u_ease, cx=0.50, cy=0.44)
        frames.append(f)
    write_mp4(frames, EP2_VID / "scene_02.mp4")

    # 3. scene_03: Already generated via LTX-Video-Distilled
    assert (EP2_VID / "scene_03.mp4").exists(), "scene_03.mp4 missing"

    # 4. scene_04: Night trench building & pickaxe sparks on canyon stone
    s08 = read_mp4(EP1_VID / "scene_08.mp4")
    s03 = read_mp4(EP1_VID / "scene_03.mp4")
    frames = []
    for i in range(N):
        base = s08[i] if i < N // 2 else s03[i]
        lum = 0.299 * base[..., 0] + 0.587 * base[..., 1] + 0.114 * base[..., 2]
        spark = np.clip((base[..., 0] - 160.0) / 80.0, 0, 1)[..., None]
        night = np.stack([lum * 0.48, lum * 0.65, lum * 0.95], axis=-1)
        f = night * (1 - spark) + base * 1.25 * spark
        frames.append(f)
    write_mp4(frames, EP2_VID / "scene_04.mp4")

    # 5. scene_05: 300 sharpshooters on sheer cliffs + stone barricade blocking canyon
    img5 = read_jpg(EP2_IMG / "scene_05.jpg")
    frames = []
    for i in range(N):
        u = i / (N - 1)
        u_ease = 0.5 - 0.5 * math.cos(u * math.pi)
        f = rigid_cam(img5, zoom=1.06 + 0.12 * u_ease, pan_x=0.0, pan_y=-18.0 * u_ease, cx=0.50, cy=0.45)
        frames.append(f)
    write_mp4(frames, EP2_VID / "scene_05.mp4")

    # 6. scene_06: Invading column pouring into narrow canyon bottleneck
    s04b = read_mp4(EP1_VID / "scene_04b.mp4")
    canyon_walls = np.clip(np.abs(xn - 0.5) * 2.5 - 0.65, 0, 1)[..., None]
    frames = [s04b[i] * (1 - 0.75 * canyon_walls) for i in range(N)]
    write_mp4(frames, EP2_VID / "scene_06.mp4")

    # 7. scene_07: Glowing matchlock fuse touching black powder pan
    s20 = read_mp4(EP1_VID / "scene_20.mp4")
    frames = []
    for i in range(N):
        u = i / (N - 1)
        f = s20[i] * 0.75
        fx = (0.36 + 0.18 * u) * W
        fy = (0.38 + 0.14 * u) * H
        dist2 = ((xx - fx) ** 2 + (yy - fy) ** 2) / ((18.0 + 25.0 * (u > 0.75)) ** 2)
        glow = np.exp(-dist2)[..., None] * np.array([255, 165, 45], dtype=np.float32) * (1.2 + 0.6 * math.sin(i * 1.7))
        f += glow
        for _ in range(35):
            ang = rng.uniform(0, 6.28)
            rad = rng.uniform(2, 48 * (0.5 + u))
            sx, sy = int(fx + math.cos(ang) * rad), int(fy + math.sin(ang) * rad)
            if 2 <= sx < W - 2 and 2 <= sy < H - 2:
                f[sy - 2:sy + 2, sx - 2:sx + 2] = [255, 230, 120]
        frames.append(f)
    write_mp4(frames, EP2_VID / "scene_07.mp4")

    # 8. scene_08: FIRE! Hundreds of muzzle flashes from cliffs + falling boulders rockslide!
    n_boulders = 28
    bx0 = rng.uniform(0.22 * W, 0.78 * W, n_boulders)
    by0 = rng.uniform(-0.25 * H, 0.35 * H, n_boulders)
    bvy = rng.uniform(260, 480, n_boulders)
    bvx = rng.uniform(-45, 45, n_boulders)
    brad = rng.integers(8, 22, n_boulders)
    muzzle_pts = [(0.26, 0.16), (0.31, 0.24), (0.36, 0.31), (0.72, 0.18), (0.68, 0.26), (0.64, 0.33)]
    frames = []
    for i in range(N):
        u = i / (N - 1)
        shk_x = 7.0 * math.sin(i * 2.3) * math.exp(-u * 1.5)
        shk_y = 7.0 * math.cos(i * 2.9) * math.exp(-u * 1.5)
        f = rigid_cam(img5, zoom=1.08 + 0.06 * u, pan_x=shk_x, pan_y=shk_y)
        for mi, (mx, my) in enumerate(muzzle_pts):
            pulse = max(0.0, math.sin(u * 18.0 + mi * 1.9))
            cx, cy = mx * W, my * H
            d2 = ((xx - cx) ** 2 + (yy - cy) ** 2) / (34.0 ** 2)
            f += np.exp(-d2)[..., None] * np.array([255, 180, 60], np.float32) * (1.3 * pulse)
            sx = cx + (0.5 - mx) * 110.0 * u
            sy = cy + 45.0 * u
            sd2 = ((xx - sx) ** 2 + (yy - sy) ** 2) / ((55.0 + 70.0 * u) ** 2)
            smoke = np.exp(-sd2)[..., None] * 0.55 * min(1.0, u * 2.5)
            f = f * (1 - smoke) + np.array([215, 220, 225], np.float32) * smoke
        for b in range(n_boulders):
            bx = int(bx0[b] + bvx[b] * u)
            by = int((by0[b] + bvy[b] * u + 240 * (u ** 2)) % (0.88 * H))
            r = brad[b]
            if r < bx < W - r and r < by < H - r:
                sub_y, sub_x = np.ogrid[-r:r, -r:r]
                bm = (sub_x ** 2 + sub_y ** 2 <= r ** 2)
                f[by - r:by + r, bx - r:bx + r][bm] = [48, 50, 54]
        frames.append(f)
    write_mp4(frames, EP2_VID / "scene_08.mp4")

    # 9. scene_09: Rotating ranks firing volleys from stone trenches (rigid recoil kick, no rubber warp)
    frames = []
    for i in range(N):
        u = i / (N - 1)
        recoil = 5.0 * max(0.0, math.sin(u * math.pi * 5))
        f = rigid_cam(img1, zoom=1.08 + 0.08 * u, pan_x=recoil, pan_y=recoil * 0.6)
        for bi, (bx, by) in enumerate([(0.33 * W, 0.48 * H), (0.56 * W, 0.46 * H)]):
            burst = max(0.0, math.sin(u * math.pi * 5 + bi * 1.5)) ** 2
            d2 = ((xx - bx) ** 2 + (yy - by) ** 2) / (52.0 ** 2)
            f += np.exp(-d2)[..., None] * np.array([255, 190, 75], np.float32) * (1.5 * burst)
            sd2 = ((xx - (bx - 40 * u)) ** 2 + (yy - (by - 30 * u)) ** 2) / (95.0 ** 2)
            sm = np.exp(-sd2)[..., None] * 0.45
            f = f * (1 - sm) + np.array([210, 215, 220], np.float32) * sm
        frames.append(f)
    write_mp4(frames, EP2_VID / "scene_09.mp4")

    # 10. scene_10: Impenetrable stone trap, smoky canyon (clean cut instead of double-exposure ghost blend)
    s08b = read_mp4(EP1_VID / "scene_08b.mp4")
    s09b = read_mp4(EP1_VID / "scene_09b.mp4")
    frames = [s08b[i] if i < N // 2 else s09b[i] for i in range(N)]
    write_mp4(frames, EP2_VID / "scene_10.mp4")

    # 11. scene_11: Day 2 running out of powder
    s11 = read_mp4(EP1_VID / "scene_11.mp4")
    s15 = read_mp4(EP1_VID / "scene_15.mp4")
    frames = [s11[i] if i < N // 2 else s15[i] for i in range(N)]
    write_mp4(frames, EP2_VID / "scene_11.mp4")

    # 12. scene_12: Stones on trench parapet trembling violently from seismic roar in the west!
    stone_crop = np.asarray(
        Image.open(EP2_IMG / "scene_01.jpg").convert("RGB").crop((180, 420, 720, 1380)).resize((W, H), Image.LANCZOS),
        dtype=np.float32,
    )
    n_peb = 45
    px0 = rng.uniform(40, W - 40, n_peb)
    py0 = rng.uniform(0.30 * H, 0.85 * H, n_peb)
    prad = rng.integers(4, 11, n_peb)
    frames = []
    for i in range(N):
        u = i / (N - 1)
        amp = (u ** 1.2) * 8.0
        shk_x = amp * math.sin(i * 3.1)
        shk_y = amp * math.cos(i * 3.7)
        f = rigid_cam(stone_crop, zoom=1.08, pan_x=shk_x, pan_y=shk_y)
        for p in range(n_peb):
            jump = abs(math.sin(u * 24.0 + p * 0.7)) * (28.0 * u)
            px, py = int(px0[p] - shk_x), int(py0[p] - jump)
            r = prad[p]
            if r < px < W - r and r < py < H - r:
                f[py - r:py + r, px - r:px + r] = [135, 138, 142]
        frames.append(f)
    write_mp4(frames, EP2_VID / "scene_12.mp4")

    # 13. scene_13: Zhalantos Bahadur arriving at full gallop with 20,000 horsemen
    s13 = read_mp4(EP1_VID / "scene_13.mp4")
    s10 = read_mp4(EP1_VID / "scene_10.mp4")
    frames = [s13[i] if i < N // 2 else s10[i] for i in range(N)]
    write_mp4(frames, EP2_VID / "scene_13.mp4")

    # 14. scene_14: Zhalantos's iron fist slamming into enemy rear
    s16 = read_mp4(EP1_VID / "scene_16.mp4")
    s14 = read_mp4(EP1_VID / "scene_14.mp4")
    frames = [s16[i] if i < N // 2 else s14[i] for i in range(N)]
    write_mp4(frames, EP2_VID / "scene_14.mp4")

    # 15. scene_15: Golden sunset over Orbulak cliffs, brotherhood & soaring eagle
    s06 = read_mp4(EP1_VID / "scene_06.mp4")
    s19 = read_mp4(EP1_VID / "scene_19.mp4")
    frames = [s06[i] if i < N // 2 else s19[i] for i in range(N)]
    write_mp4(frames, EP2_VID / "scene_15.mp4")

    # 16. scene_16: Seamless loop close-up — cocking the matchlock musket on the stone trench parapet
    musket_crop = np.asarray(
        Image.open(EP2_IMG / "scene_01.jpg").convert("RGB").crop((140, 460, 680, 1420)).resize((W, H), Image.LANCZOS),
        dtype=np.float32,
    )
    frames = []
    for i in range(N):
        u = i / (N - 1)
        zoom = 1.02 + 0.20 * (u ** 1.4)
        f = rigid_cam(musket_crop, zoom=zoom, cx=0.48, cy=0.52)
        fx, fy = (0.58 - 0.04 * u) * W, (0.68 - 0.05 * u) * H
        d2 = ((xx - fx) ** 2 + (yy - fy) ** 2) / ((16.0 + 28.0 * u) ** 2)
        f += np.exp(-d2)[..., None] * np.array([255, 175, 50], np.float32) * (0.8 + 1.1 * u)
        frames.append(f)
    write_mp4(frames, EP2_VID / "scene_16.mp4")


if __name__ == "__main__":
    build_all()
