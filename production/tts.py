"""Generate neural voice-over (edge-tts) with word-level timings.

Usage: python tts.py <lang> [rate] [pitch]
Outputs: build/<lang>/voice_raw.mp3, build/<lang>/words.json
"""
import asyncio
import json
import sys
from pathlib import Path

import edge_tts

ROOT = Path(__file__).resolve().parent
DATA = json.loads((ROOT / "narration_shorts_ep01.json").read_text(encoding="utf-8"))


async def main(lang: str, rate: str, pitch: str) -> None:
    out = ROOT / "build" / lang
    out.mkdir(parents=True, exist_ok=True)
    text = " ".join(DATA[lang])
    comm = edge_tts.Communicate(text, DATA["voices"][lang], rate=rate, pitch=pitch,
                                boundary="WordBoundary")
    words = []
    with open(out / "voice_raw.mp3", "wb") as f:
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                words.append({
                    "t0": chunk["offset"] / 1e7,
                    "t1": (chunk["offset"] + chunk["duration"]) / 1e7,
                    "w": chunk["text"],
                })
    (out / "words.json").write_text(json.dumps(words, ensure_ascii=False, indent=1), encoding="utf-8")
    print(lang, "words:", len(words), "last end:", round(words[-1]["t1"], 2))


if __name__ == "__main__":
    lang = sys.argv[1]
    rate = sys.argv[2] if len(sys.argv) > 2 else "+0%"
    pitch = sys.argv[3] if len(sys.argv) > 3 else "+0Hz"
    asyncio.run(main(lang, rate, pitch))
