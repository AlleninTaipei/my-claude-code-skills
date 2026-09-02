#!/usr/bin/env python3
"""Extract timestamped frames and contact sheets from a local video."""
import argparse, math
from pathlib import Path
import cv2
from PIL import Image, ImageDraw

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("output_dir")
    ap.add_argument("--interval", type=float, default=20.0)
    ap.add_argument("--thumb-width", type=int, default=320)
    args = ap.parse_args()
    src, out = Path(args.video), Path(args.output_dir); out.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(src))
    if not cap.isOpened(): raise SystemExit(f"Cannot open video: {src}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 0
    count = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
    duration = count / fps if fps else 0
    times = [i * args.interval for i in range(math.floor(duration / args.interval) + 1)]
    files = []
    for sec in times:
        cap.set(cv2.CAP_PROP_POS_MSEC, sec * 1000)
        ok, frame = cap.read()
        if not ok: continue
        path = out / f"frame_{sec:08.2f}.jpg"
        cv2.imwrite(str(path), frame); files.append((sec, path))
    cap.release()
    tw, th, lh, cols, rows = args.thumb_width, round(args.thumb_width * 9 / 16), 24, 4, 5
    tiles = []
    for sec, path in files:
        im = Image.open(path).convert("RGB"); im.thumbnail((tw, th))
        tile = Image.new("RGB", (tw, th + lh), "white"); tile.paste(im, (0, 0))
        ImageDraw.Draw(tile).text((7, th + 5), f"{sec:.2f} sec", fill="black"); tiles.append(tile)
    per_page = cols * rows
    for page in range(math.ceil(len(tiles) / per_page)):
        sheet = Image.new("RGB", (tw * cols, (th + lh) * rows), "#dddddd")
        for i, tile in enumerate(tiles[page * per_page:(page + 1) * per_page]):
            sheet.paste(tile, ((i % cols) * tw, (i // cols) * (th + lh)))
        sheet.save(out / f"contact_{page + 1:02d}.jpg", quality=90)
    print(f"duration={duration:.2f}s fps={fps:.3f} frames={len(files)} sheets={math.ceil(len(tiles)/per_page)}")

if __name__ == "__main__": main()
