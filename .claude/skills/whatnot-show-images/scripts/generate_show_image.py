#!/usr/bin/env python3
"""
Generate or edit a Whatnot show splash image via Gemini API.

Usage:
  # New image from text prompt
  python3 generate_show_image.py --prompt "FAST GAMES show with coins" --out fast_games_v1.png

  # Edit existing image
  python3 generate_show_image.py --ref fast_games_v4.png --prompt "Change mystery box to Mario block" --out fast_games_v5.png

  # Fast mode (no people, Gemini 2.0 Flash)
  python3 generate_show_image.py --prompt "Silver eagle show" --out silver_show.png --fast
"""

import argparse
import base64
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

OUTPUT_DIR = "/Users/benfife/Desktop/Whatnot Streams"

MODELS = {
    "pro": "gemini-3-pro-image-preview",          # best for people/likeness
    "flash": "gemini-2.0-flash-exp-image-generation",  # fast, no people
}

BASE_REQUIREMENTS = """
Tall portrait image, 11:17 aspect ratio (like 1080x1880px).
No text boxes or banners — all text is part of the design, rendered directly on the background.
Text safe zones: nothing within 150px of top or bottom edge, nothing within 80px of left/right edges.
All text centered horizontally.
"""


def get_api_key():
    result = subprocess.run(["secrets", "get", "google_ai_api_key"], capture_output=True, text=True)
    key = result.stdout.strip()
    if not key:
        key = os.environ.get("GOOGLE_API_KEY", "")
    if not key:
        print("ERROR: Could not get google_ai_api_key from secrets vault")
        sys.exit(1)
    return key


def load_image_b64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def generate(prompt, ref_path=None, out_filename=None, fast=False, open_after=True):
    api_key = get_api_key()
    model = MODELS["flash"] if fast else MODELS["pro"]

    full_prompt = BASE_REQUIREMENTS + "\n\n" + prompt

    parts = [{"text": full_prompt}]
    if ref_path:
        ref_b64 = load_image_b64(ref_path)
        # detect mime type
        mime = "image/png" if ref_path.lower().endswith(".png") else "image/jpeg"
        parts.append({"inline_data": {"mime_type": mime, "data": ref_b64}})

    payload = {
        "contents": [{"parts": parts}],
        "generationConfig": {"responseModalities": ["image", "text"]},
    }

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )

    print(f"Generating with {model}...")
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.read().decode()[:1500]}")
        sys.exit(1)

    for part in data.get("candidates", [{}])[0].get("content", {}).get("parts", []):
        if "inlineData" in part:
            img_data = base64.b64decode(part["inlineData"]["data"])
            out_path = os.path.join(OUTPUT_DIR, out_filename or "show_image.png")
            with open(out_path, "wb") as f:
                f.write(img_data)
            print(f"Saved: {out_path} ({len(img_data):,} bytes)")
            if open_after:
                subprocess.run(["open", "-a", "Google Chrome", out_path])
            return out_path

    print("No image in response:")
    print(json.dumps(data, indent=2)[:2000])
    sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt", required=True, help="Image prompt")
    parser.add_argument("--ref", help="Reference image path (for edits)")
    parser.add_argument("--out", default="show_image.png", help="Output filename")
    parser.add_argument("--fast", action="store_true", help="Use Flash model (faster, no people)")
    parser.add_argument("--no-open", action="store_true", help="Don't open in Chrome")
    args = parser.parse_args()

    generate(
        prompt=args.prompt,
        ref_path=args.ref,
        out_filename=args.out,
        fast=args.fast,
        open_after=not args.no_open,
    )
