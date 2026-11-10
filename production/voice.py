"""Step 1 — offline neural voice-over + word timings + scene timeline.

edge-tts (tts.py) is blocked from cloud IPs (HTTP 403), so this script uses local
ONNX neural voices (Piper; ISSAI KazakhTTS for Kazakh) that run fully offline.
Models are downloaded automatically from HuggingFace on first run.

Usage:  python voice.py <ru|kz|en>
Output: production/build/<lang>/voice_raw.wav, voice.wav (48 kHz, processed),
        voice_raw.mp3, words.json, timeline.json
"""
import json
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

import numpy as np
from piper import PiperVoice, SynthesisConfig
from scipy.io import wavfile

ROOT = Path(__file__).resolve().parent
DATA = json.loads((ROOT / "narration_shorts_ep01.json").read_text(encoding="utf-8"))
MODELS = Path(os.environ.get("PIPER_MODELS", "/tmp/piper_models"))
HF = "https://huggingface.co/rhasspy/piper-voices/resolve/main/"
VOICES = {  # lang: (HuggingFace path, speaker id) — all male narrators
    "ru": ("ru/ru_RU/dmitri/medium/ru_RU-dmitri-medium", None),
    "kz": ("kk/kk_KZ/issai/high/kk_KZ-issai-high", 0),  # ISSAI KazakhTTS2, male speaker M2
    "en": ("en/en_US/ryan/high/en_US-ryan-high", None),
}
TTS_FIX = {"en": [("1726", "seventeen twenty-six")]}  # pronunciation only, subtitles keep digits
TARGET = 62.8   # s — Shorts 62–65 s (TikTok Creator Rewards pays only > 60 s)
TAIL = 0.10     # s after the last word: the loop cut point
GAP0 = 0.20     # s pause between sentences (re-fitted)
MAX_SIL = 0.14  # s — longer pauses inside a sentence are squeezed to this
L_MIN = 0.72    # fastest allowed model speed (lower = faster)
MAX_TEMPO = 1.10  # extra pitch-preserving speed-up if still too long
VOICE_FX = ("aresample=48000,highpass=f=70,rubberband=pitch=0.95,"
            "equalizer=f=120:t=q:w=1:g=3,equalizer=f=3000:t=q:w=1.5:g=2,"
            "acompressor=threshold=0.125:ratio=3:attack=5:release=100:makeup=1.5")
END_RE = re.compile(r"[.!?…]+[»\"”]?$")
PAUSE_RE = re.compile(r"[,;:]+[»\"”]?$")


def load_voice(lang):
    path, sid = VOICES[lang]
    MODELS.mkdir(parents=True, exist_ok=True)
    name = Path(path).name
    for suf in (".onnx", ".onnx.json"):
        f = MODELS / (name + suf)
        if not f.exists():
            print("downloading", f.name)
            urllib.request.urlretrieve(HF + path + suf, f)
    return PiperVoice.load(str(MODELS / (name + ".onnx"))), sid


def tokens(lang):
    toks = []
    for si, line in enumerate(DATA[lang]):
        for raw in line.split():
            if not re.search(r"\w", raw):        # standalone dash → pause after previous word
                if toks:
                    toks[-1]["pause"] = 1
                    toks[-1]["tts"] += " " + raw
                continue
            toks.append({"w": raw, "tts": raw, "scene": si, "pause": 1 if PAUSE_RE.search(raw) else 0})
    return toks


def sentences(toks):
    out, cur = [], []
    for t in toks:
        cur.append(t)
        if END_RE.search(t["w"]) and not t["w"].startswith(("«", '"', "“")):
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out


def syllables(w, lang):
    s = w.lower()
    if re.search(r"\d", s):
        return 4
    if lang == "en":
        return max(1, len(re.findall(r"[aeiouy]+", s)))
    return max(1, sum(ch in "аеёиоуыэюяәіөұү" for ch in s))


def trim(a, sr):
    """Cut edge silence and squeeze long pauses inside the sentence to MAX_SIL."""
    k = max(1, int(0.01 * sr))
    env = np.convolve(np.abs(a), np.ones(k) / k, "same")
    loud = env > 0.03 * env.max()
    idx = np.where(loud)[0]
    pad = int(0.03 * sr)
    a, loud = a[max(0, idx[0] - pad): idx[-1] + pad], loud[max(0, idx[0] - pad): idx[-1] + pad]
    d = np.diff(np.concatenate([[1], loud.astype(int), [1]]))
    starts, ends = np.where(d == -1)[0], np.where(d == 1)[0]
    keep, half, pos = [], int(MAX_SIL * sr / 2), 0
    for s, e in zip(starts, ends):
        if s == 0 or e == len(a) or e - s <= 2 * half:
            continue
        keep.append(a[pos:s + half])
        pos = e - half
    keep.append(a[pos:])
    return np.concatenate(keep)


def synth_all(voice, sid, sents, lang, L):
    sr = voice.config.sample_rate
    cfg = SynthesisConfig(speaker_id=sid, length_scale=L)
    clips = []
    for s in sents:
        text = " ".join(t["tts"] for t in s)
        for a, b in TTS_FIX.get(lang, []):
            text = text.replace(a, b)
        a = np.concatenate([c.audio_float_array for c in voice.synthesize(text, syn_config=cfg)])
        clips.append(trim(a.astype(np.float32), sr))
    return clips


def assemble(clips, sents, sr, gap, lang):
    pieces, words, n = [], [], 0
    for k, (a, s) in enumerate(zip(clips, sents)):
        d = len(a) / sr
        t = n / sr
        w = [syllables(x["w"], lang) + 0.8 * x["pause"] for x in s]
        W, c = sum(w), 0.0
        for x, wi in zip(s, w):
            words.append({"w": x["w"], "scene": x["scene"],
                          "t0": round(t + c / W * d, 3),
                          "t1": round(t + (c + wi - 0.8 * x["pause"]) / W * d, 3)})
            c += wi
        pieces.append(a)
        n += len(a)
        if k < len(clips) - 1:
            g = np.zeros(int(gap * sr), np.float32)
            pieces.append(g)
            n += len(g)
    pieces.append(np.zeros(int(TAIL * sr), np.float32))
    audio = np.concatenate(pieces)
    return audio, words, len(audio) / sr


def run(lang):
    out = ROOT / "build" / lang
    out.mkdir(parents=True, exist_ok=True)
    voice, sid = load_voice(lang)
    sr = voice.config.sample_rate
    sents = sentences(tokens(lang))
    ns = len(sents)

    # pass 1: natural speed → measure; pass 2: re-synthesize with fitted length_scale
    clips = synth_all(voice, sid, sents, lang, 1.0)
    speech = sum(len(c) for c in clips) / sr
    L = float(np.clip((TARGET - TAIL - GAP0 * (ns - 1)) / speech, L_MIN, 1.35))
    clips = synth_all(voice, sid, sents, lang, L)
    speech = sum(len(c) for c in clips) / sr
    gap = float(np.clip((TARGET - TAIL - speech) / max(1, ns - 1), 0.12, 0.6))
    audio, words, T = assemble(clips, sents, sr, gap, lang)
    tempo = float(np.clip(T / TARGET, 1.0, MAX_TEMPO))
    if tempo > 1.0:   # pitch-preserving speed-up; rescale all timings
        T /= tempo
        for w in words:
            w["t0"], w["t1"] = round(w["t0"] / tempo, 3), round(w["t1"] / tempo, 3)
    print(f"[{lang}] sentences={ns} length_scale={L:.3f} gap={gap:.3f}s tempo={tempo:.3f} total={T:.2f}s")

    starts = []
    for si in range(len(DATA["scenes"])):
        ws = [w for w in words if w["scene"] == si]
        starts.append(max(0.0, ws[0]["t0"] - 0.06))
    starts[0] = 0.0
    scenes = [{"id": si + 1, "images": DATA["scenes"][si].split("|"),
               "t0": round(starts[si], 3),
               "t1": round(starts[si + 1] if si + 1 < len(starts) else T, 3)}
              for si in range(len(starts))]

    wavfile.write(out / "voice_raw.wav", sr, (np.clip(audio, -1, 1) * 32767).astype(np.int16))
    fx = VOICE_FX.replace("rubberband=pitch=0.95", f"rubberband=pitch=0.95:tempo={tempo:.4f}")
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(out / "voice_raw.wav"),
                    "-af", fx, "-ar", "48000", "-ac", "1", str(out / "voice.wav")], check=True)
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(out / "voice.wav"),
                    "-b:a", "128k", str(out / "voice_raw.mp3")], check=True)
    (out / "words.json").write_text(json.dumps(words, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / "timeline.json").write_text(json.dumps(
        {"lang": lang, "T": round(T, 3), "length_scale": L, "gap": gap, "scenes": scenes},
        ensure_ascii=False, indent=1), encoding="utf-8")
    for s in scenes:
        print(f"  scene {s['id']:02d}: {s['t0']:6.2f} → {s['t1']:6.2f}  ({s['t1'] - s['t0']:.2f}s)")


if __name__ == "__main__":
    run(sys.argv[1])
