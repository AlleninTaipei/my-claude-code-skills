#!/usr/bin/env python3
"""Convert YouTube-style WebVTT captions into deduplicated plain text."""

from __future__ import annotations

import argparse
import html
import re
from pathlib import Path


TIMING_RE = re.compile(r"^\s*\d{2}:\d{2}(?::\d{2})?\.\d{3}\s+-->")
TAG_RE = re.compile(r"<[^>]+>")


def normalize_caption(line: str) -> str:
    line = TAG_RE.sub("", line)
    return " ".join(html.unescape(line).split())


def read_cues(path: Path) -> list[str]:
    cues: list[str] = []
    cue_lines: list[str] = []
    in_cue = False

    def flush() -> None:
        nonlocal cue_lines
        text = normalize_caption(" ".join(cue_lines))
        if text:
            cues.append(text)
        cue_lines = []

    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if TIMING_RE.match(line):
            flush()
            in_cue = True
        elif not line:
            if cue_lines:
                flush()
                in_cue = False
        elif in_cue:
            cue_lines.append(line)
    flush()
    return cues


def deduplicate(cues: list[str]) -> str:
    words: list[str] = []
    for cue in cues:
        current = cue.split()
        max_overlap = min(len(words), len(current))
        overlap = 0
        for size in range(max_overlap, 0, -1):
            if words[-size:] == current[:size]:
                overlap = size
                break
        words.extend(current[overlap:])
    return " ".join(words)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Input .vtt file")
    args = parser.parse_args()
    print(deduplicate(read_cues(args.input)))


if __name__ == "__main__":
    main()
