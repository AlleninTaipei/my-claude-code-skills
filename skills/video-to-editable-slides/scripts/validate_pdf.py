#!/usr/bin/env python3
"""Validate PDF integrity, page count, and page dimensions."""
import argparse
import json
from pathlib import Path

from pypdf import PdfReader


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--expected-pages", type=int)
    args = ap.parse_args()
    path = Path(args.pdf)
    if not path.is_file():
        raise SystemExit(f"Missing file: {path}")
    reader = PdfReader(str(path))
    pages = len(reader.pages)
    dimensions = []
    for page in reader.pages:
        box = page.mediabox
        dimensions.append(
            {
                "width_points": float(box.width),
                "height_points": float(box.height),
                "aspect_ratio": round(float(box.width) / float(box.height), 6),
            }
        )
    report = {
        "file": str(path.resolve()),
        "bytes": path.stat().st_size,
        "pages": pages,
        "encrypted": reader.is_encrypted,
        "dimensions": dimensions,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not pages or reader.is_encrypted:
        raise SystemExit(1)
    if args.expected_pages is not None and pages != args.expected_pages:
        raise SystemExit(
            f"Expected {args.expected_pages} pages, found {pages}"
        )


if __name__ == "__main__":
    main()
