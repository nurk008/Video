"""Animate static scene images into living AI video clips using LTX-Video-Distilled & Wan 2.2 I2V.

Saves real AI-animated clips to ../scenes_video/<scene_name>.mp4.
"""
import os
import shutil
import sys
import time
from pathlib import Path

os.environ["NO_PROXY"] = "localhost,127.0.0.1"
os.environ["no_proxy"] = "localhost,127.0.0.1"

from gradio_client import Client, handle_file

ROOT = Path(__file__).resolve().parent
SCENES_DIR = ROOT.parent / "scenes"
VIDEO_DIR = ROOT.parent / "scenes_video"
VIDEO_DIR.mkdir(exist_ok=True)

PROMPTS = {
    "scene_01": "Lone young rider in weathered sheepskin coat on a breathing warhorse seen from behind, wind blowing horse mane and fur coat, dust drifting across the valley toward a distant army wall of spears and bronze cannons, dramatic camera push forward, strictly no visible faces",
    "scene_02": "Wide aerial shot of the vast steppe at dusk, thick columns of black smoke rising and billowing into a stormy sky, thousands of dark cavalry silhouettes advancing across the horizon, slow aerial push forward",
    "scene_03": "Close-up of glowing molten bronze actively pouring into a cannon mold inside a dark smoky foundry, bright sparks flying in the air, silhouetted hands holding iron tongs, slow tracking camera movement",
    "scene_04": "Low-angle close-up of heavy 18th-century bronze cannon wheels turning and rolling forward through deep mud and dry steppe grass, rows of iron boots marching in dark silhouette behind, low tracking shot",
    "scene_04b": "Dark silhouetted ranks of marching soldiers carrying matchlock muskets and spears advancing forward through thick battle smoke and dust, banners flapping in the wind, no faces visible",
    "scene_05": "Close-up of an ancient parchment map of the Kazakh Steppe on a dark stone table, glowing red embers and orange flames actively burning and curling along the map edge, smoke rising, top-down zoom in",
    "scene_06": "Three elders in tall traditional fur hats and long robes standing shoulder to shoulder seen from behind on the rocky cliff of Mount Ordabasy at sunrise, wind moving their robes, thousands of horsemen and waving banners moving in the valley below, heroic low-angle push in",
    "scene_07": "Epic wide aerial shot of Mount Ordabasy between two rivers, three massive cavalry columns with tall colorful banners riding and converging from three directions toward the mountain peak, dust rising under hooves",
    "scene_08": "Close-up of a heavy wooden staff with iron rings striking down firmly against a flat mountain stone, dust and small pebbles jumping from the impact, warrior boots standing united in a circle",
    "scene_08b": "Circle of steppe warriors seen from behind and in dark silhouette around the mountain rock, raising their spears and sabers high in unison, wind blowing dust and banners, no visible faces",
    "scene_09": "Extreme close-up of three curved steel saber blades clashing and crossing together over a blazing campfire, warrior hands in leather gauntlets gripping the hilts tightly, dancing firelight and sparks reflecting on the steel",
    "scene_09b": "Blazing steppe campfire at night with bright orange flames leaping and glowing embers rising into the dark sky while silhouetted warriors stand united around the fire from behind",
    "scene_10": "Cinematic wide shot of a vast herd of thousands of warhorses galloping at full speed across a shallow sunlit river, water splashing high in golden light, dynamic parallel tracking shot",
    "scene_11": "Close-up of rough warrior hands passing bundles of steel spears, curved sabers, and braided leather horse reins to another warrior's hands, firm brotherhood grip, no faces visible",
    "scene_12": "Low-angle back view of a commander in gleaming chainmail and steel helmet sitting on a white stallion on a ridge, raising and pointing his curved saber toward the eastern mountains as the horse shifts beneath him",
    "scene_13": "Two heavily armored horsemen in dark silhouette riding side by side at the head of a charging cavalry wedge galloping fast across dusty terrain, tall battle banners streaming in the wind behind them",
    "scene_14": "Extreme wide panoramic shot of the Anyrakai valley between mountains and salt lake, two colossal armies of horsemen advancing toward each other across white salt sand, wind blowing dust clouds between the lines",
    "scene_15": "Low-angle shot of a massive armored enemy horseman in dark heavy lamellar armor on a warhorse in the center of the dusty field, seen in dark shadow silhouette, horse breathing and stepping heavily, holding a heavy iron lance",
    "scene_16": "Back-view shot of a young rider in a simple sheepskin coat spurring his horse into an explosive gallop straight toward the blinding golden sun, kicking up a cloud of white dust",
    "scene_17": "Dramatic stark black-and-gold silhouette against a blinding golden sun: two horsemen colliding at full gallop, a brilliant burst of glowing sparks flying as a curved saber shatters the heavy iron lance, enemy banner falling into dust",
    "scene_18": "High-altitude tactical bird's-eye view of the Anyrakai gorge: two massive crescent-shaped cavalry wings galloping and sweeping forward from behind the hills to encircle the enemy army in a cloud of dust",
    "scene_19": "Majestic wide shot of the Kazakh steppe at golden dawn after battle, tall battle standards planted on the mountain peak waving proudly in the wind, golden eagles soaring across the sky",
    "scene_20": "Extreme close-up of a rough hand in a sheepskin sleeve tightening its grip on braided leather reins and smoothly drawing a curved steel saber blade from its leather scabbard, metallic gleam in dim pre-battle light",
}


def animate_one(name: str, force: bool = False) -> bool:
    out_path = VIDEO_DIR / f"{name}.mp4"
    if not force and out_path.exists() and out_path.stat().st_size > 50_000:
        print(f"[skip] {name}.mp4 already exists ({out_path.stat().st_size // 1024} KB)")
        return True

    img_path = next(SCENES_DIR.glob(f"{name}_*.jpg"))
    prompt = PROMPTS[name]
    hf_token = os.environ.get("HF_TOKEN")
    tokens = [hf_token, None] if hf_token else [None]

    for tok in tokens:
        # 1. DeepRat LTX-Video-ZeroGPU-Optimized (low GPU duration reservation ~15s)
        try:
            t0 = time.time()
            client = Client("DeepRat/LTX-Video-ZeroGPU-Optimized", token=tok, verbose=False)
            res = client.predict(
                prompt=prompt,
                negative_prompt="worst quality, inconsistent motion, blurry, jittery, distorted, static",
                input_image_filepath=handle_file(str(img_path)),
                input_video_filepath=None,
                height_ui=768,
                width_ui=448,
                mode="image-to-video",
                duration_ui=2.5,
                ui_frames_to_use=9,
                seed_ui=42,
                randomize_seed=True,
                ui_guidance_scale=1.0,
                improve_texture_flag=False,
                slow_motion_flag=False,
                api_name="/image_to_video",
            )
            vid_file = res[0]["video"] if isinstance(res[0], dict) else res[0]
            shutil.copy(vid_file, out_path)
            print(f"[ok-deeprat] {name} in {time.time() - t0:.1f}s -> {out_path.stat().st_size // 1024} KB", flush=True)
            return True
        except Exception as e:
            print(f"[warn-deeprat] {name}: {str(e).splitlines()[0][:140]}", flush=True)

        # 2. Upsampler/ltx-video (20s GPU reservation)
        try:
            t0 = time.time()
            client = Client("Upsampler/ltx-video", token=tok, verbose=False)
            res = client.predict(
                input_image=handle_file(str(img_path)),
                prompt=prompt,
                duration=2.5,
                enhance_prompt=False,
                seed=42,
                randomize_seed=True,
                height=768,
                width=448,
                api_name="/generate_video",
            )
            vid_file = res[0]["video"] if isinstance(res[0], dict) else res[0]
            shutil.copy(vid_file, out_path)
            print(f"[ok-upsampler] {name} in {time.time() - t0:.1f}s -> {out_path.stat().st_size // 1024} KB", flush=True)
            return True
        except Exception as e:
            print(f"[warn-upsampler] {name}: {str(e).splitlines()[0][:140]}", flush=True)

        # 3. Lightricks/ltx-video-distilled
        try:
            t0 = time.time()
            client = Client("Lightricks/ltx-video-distilled", token=tok, verbose=False)
            res = client.predict(
                prompt=prompt,
                negative_prompt="worst quality, inconsistent motion, blurry, jittery, distorted, static",
                input_image_filepath=handle_file(str(img_path)),
                input_video_filepath=None,
                height_ui=768,
                width_ui=448,
                mode="image-to-video",
                duration_ui=2.6,
                ui_frames_to_use=9,
                seed_ui=42,
                randomize_seed=True,
                ui_guidance_scale=1.0,
                improve_texture_flag=True,
                api_name="/image_to_video",
            )
            vid_file = res[0]["video"] if isinstance(res[0], dict) else res[0]
            shutil.copy(vid_file, out_path)
            print(f"[ok-ltx] {name} in {time.time() - t0:.1f}s -> {out_path.stat().st_size // 1024} KB", flush=True)
            return True
        except Exception as e:
            print(f"[warn-ltx] {name}: {str(e).splitlines()[0][:140]}", flush=True)

    return False


if __name__ == "__main__":
    force = "--force" in sys.argv
    args = [a for a in sys.argv[1:] if a != "--force"]
    targets = args if args else list(PROMPTS.keys())
    ok = 0
    for name in targets:
        if animate_one(name, force=force):
            ok += 1
    print(f"Done: {ok}/{len(targets)} scenes animated in {VIDEO_DIR}")
