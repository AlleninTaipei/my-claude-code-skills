#!/usr/bin/env python3
"""Inspect a public video URL with yt-dlp and emit compact JSON."""
import argparse, json, subprocess, sys

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("-o", "--output")
    args = ap.parse_args()
    cmd = [sys.executable, "-m", "yt_dlp", "--dump-single-json", "--skip-download", "--no-warnings", args.url]
    try:
        raw = subprocess.check_output(cmd, text=True, encoding="utf-8")
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        raise SystemExit(f"yt-dlp inspection failed: {exc}")
    data = json.loads(raw)
    compact = {k: data.get(k) for k in (
        "id", "title", "description", "channel", "uploader", "duration",
        "duration_string", "upload_date", "webpage_url", "chapters", "thumbnail"
    )}
    compact["subtitles"] = sorted((data.get("subtitles") or {}).keys())
    compact["automatic_captions"] = sorted((data.get("automatic_captions") or {}).keys())
    compact["max_resolution"] = max(
        ((f.get("width") or 0, f.get("height") or 0) for f in data.get("formats", [])),
        default=(0, 0), key=lambda pair: pair[0] * pair[1]
    )
    text = json.dumps(compact, ensure_ascii=False, indent=2)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh: fh.write(text + "\n")
    else:
        print(text)

if __name__ == "__main__": main()
