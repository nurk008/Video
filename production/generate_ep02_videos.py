"""Generate all 16 AI video clips for Episode 2 (Battle of Orbulak, 1643) using LTX-Video-Distilled."""
import glob
import os
import shutil
import time
from pathlib import Path

os.environ["NO_PROXY"] = "localhost,127.0.0.1"
os.environ["no_proxy"] = "localhost,127.0.0.1"

from gradio_client import Client, handle_file

ROOT = Path(__file__).resolve().parent
ART_DIR = Path("/home/antigravity/.gemini/jetski/brain/v1/default/jetski_remote_agents_3p/16f769ab-eb10-4cfb-a67c-08a242cb4814")
SCENES_DIR = ROOT.parent / "scenes_ep02"
VIDEO_DIR = ROOT.parent / "scenes_ep02_video"
SCENES_DIR.mkdir(exist_ok=True)
VIDEO_DIR.mkdir(exist_ok=True)

# Copy already generated 8k base images if present
for k, pat in [("scene_01", "ep02_scene_01_*.jpg"), ("scene_02", "ep02_scene_02_*.jpg"), ("scene_05", "ep02_scene_05_*.jpg")]:
    m = sorted(ART_DIR.glob(pat))
    if m and not (SCENES_DIR / f"{k}.jpg").exists():
        shutil.copy(m[-1], SCENES_DIR / f"{k}.jpg")

# Copy already generated scene_03 video if present in /tmp/gradio
tmp_s3 = Path("/tmp/gradio/c607acd7dc5aead5597ed109a2379e4622c6119cc1cb3e675911e4bfcea3cc24/output_62021.mp4")
if tmp_s3.exists() and not (VIDEO_DIR / "scene_03.mp4").exists():
    shutil.copy(tmp_s3, VIDEO_DIR / "scene_03.mp4")
    print("[ok-cached] scene_03.mp4 copied")

PROMPTS = {
    "scene_01": "Over-the-shoulder POV from behind silhouetted 17th-century Kazakh warriors crouching in a fortified stone trench high on a narrow mountain canyon ledge, long iron barrels of matchlock muskets resting on grey rocks pointing down into the deep gorge below where a massive dark column of horsemen is marching in, wind and dust moving, no visible faces",
    "scene_02": "Epic wide aerial view of the Dzungarian Alatau mountain foothills at dawn, a colossal dark army of fifty thousand horsemen with iron lances and dark banners advancing forward across the dusty valley toward a narrow mountain pass, thick dust clouds billowing, slow aerial push forward",
    "scene_03": "Heroic low-angle back view of a lone Kazakh commander in steel helmet and chainmail armor standing on the edge of a high jagged cliff at dusk, wind blowing his cloak, looking down at the winding narrow canyon below, dramatic golden and blue sky, no visible face",
    "scene_04": "Cinematic night scene under cold moonlight inside a narrow rocky mountain gorge: dark silhouettes of warriors seen from behind digging deep defensive trenches and stacking heavy grey boulders into stone walls, bright sparks flying as iron pickaxes strike stone, torches flickering in the mist, no faces visible",
    "scene_05": "Dramatic low-angle shot looking up from the dark floor of a narrow vertical stone canyon toward the sheer rocky cliffs high above: rows of dark silhouetted warriors with long matchlock muskets aiming down from both cliff edges against a stormy moving sky, stone barricade blocking the canyon ahead",
    "scene_06": "High-angle bird's-eye view looking straight down into a narrow winding stone gorge: thousands of dark armored horsemen riding packed tightly together into the narrow canyon bottleneck between sheer vertical rock walls, thick dust rising under hooves, dynamic top-down camera movement",
    "scene_07": "Extreme macro close-up of a warrior hand in a weathered leather gauntlet pulling the iron trigger lever of an antique matchlock musket: a bright orange glowing cord fuse hissing and spitting fiery sparks into the black gunpowder pan, dark smoky background, no face",
    "scene_08": "Explosive cinematic action shot inside a narrow mountain canyon: bright orange muzzle flashes and thick white gunpowder smoke erupting from high cliff ledges while massive grey boulders crash and tumble down into the smoky gorge below, dynamic camera shake, no faces or gore",
    "scene_09": "Back-view silhouette of a line of 17th-century musketeers inside a deep stone trench firing a synchronized volley of matchlock muskets into thick white smoke, bright orange flames and sparks shooting from the long iron barrels, second rank reloading behind them, no visible faces",
    "scene_10": "Wide atmospheric shot of a narrow rocky mountain canyon filled with drifting white gunpowder smoke and glowing embers, broken wooden lances and fallen dark banners scattered on the stones in front of an unbroken stone trench wall, slow tracking camera movement",
    "scene_11": "Close-up of rough warrior hands in a dark stone trench turning an empty leather gunpowder horn upside down as the last grains of black powder fall onto cold grey stone, dark figures advancing through thick smoke in the distant background, tense mood, no faces",
    "scene_12": "Extreme close-up of small grey pebbles and dust resting on the flat stone parapet of a mountain trench suddenly vibrating, jumping, and trembling violently as a massive seismic rumble approaches from the horizon, dramatic low-angle focus",
    "scene_13": "Epic low-angle shot of twenty thousand heavily armored cavalrymen in gleaming chainmail and steel helmets charging at full gallop over a sunlit mountain ridge, tall battle banners streaming in the wind, massive clouds of golden dust rising under hooves, strictly silhouette and back-lit",
    "scene_14": "High-altitude aerial view of the mountain canyon entrance: a massive wedge of armored cavalry charging at full speed and slamming into the rear of the dark army trapped outside the gorge, huge clouds of dust sweeping across the battlefield",
    "scene_15": "Majestic golden sunset over the rocky cliffs of Orbulak canyon: two armored commanders on warhorses seen strictly from behind standing side by side on the high mountain peak overlooking the vast peaceful steppe bathed in golden light, banners waving in the wind, eagle soaring",
    "scene_16": "Extreme close-up in dim pre-battle canyon light: a warrior hand in a leather gauntlet smoothly resting the long iron barrel of a matchlock musket onto a rough grey stone trench parapet and cocking the glowing fuse lever, metallic gleam, camera pushing in",
}


def generate_one(name: str) -> bool:
    out_path = VIDEO_DIR / f"{name}.mp4"
    if out_path.exists() and out_path.stat().st_size > 50_000:
        print(f"[skip] {name}.mp4 already exists ({out_path.stat().st_size // 1024} KB)")
        return True

    img_file = SCENES_DIR / f"{name}.jpg"
    has_img = img_file.exists()
    prompt = PROMPTS[name]
    hf_token = os.environ.get("HF_TOKEN")
    tokens = [None, hf_token] if hf_token else [None]

    for tok in tokens:
        try:
            t0 = time.time()
            c = Client("Lightricks/ltx-video-distilled", token=tok, verbose=False)
            res = c.predict(
                prompt=prompt,
                negative_prompt="worst quality, inconsistent motion, blurry, jittery, distorted, close-up face, portrait",
                input_image_filepath=handle_file(str(img_file)) if has_img else None,
                input_video_filepath=None,
                height_ui=768,
                width_ui=448,
                mode="image-to-video" if has_img else "text-to-video",
                duration_ui=2.6,
                ui_frames_to_use=9,
                seed_ui=42,
                randomize_seed=True,
                ui_guidance_scale=1.0,
                improve_texture_flag=False,
                api_name="/image_to_video" if has_img else "/text_to_video",
            )
            vid_file = res[0]["video"] if isinstance(res[0], dict) else res[0]
            shutil.copy(vid_file, out_path)
            print(f"[ok-ltx] {name} ({'i2v' if has_img else 't2v'}, tok={bool(tok)}) in {time.time() - t0:.1f}s -> {out_path.stat().st_size // 1024} KB", flush=True)
            return True
        except Exception as e:
            print(f"[warn-ltx] {name} (tok={bool(tok)}): {str(e).splitlines()[0][:140]}", flush=True)
    return False


if __name__ == "__main__":
    ok = 0
    for name in PROMPTS:
        if generate_one(name):
            ok += 1
    print(f"Done: {ok}/{len(PROMPTS)} scenes ready in {VIDEO_DIR}")
