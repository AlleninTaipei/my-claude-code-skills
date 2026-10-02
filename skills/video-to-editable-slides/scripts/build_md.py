#!/usr/bin/env python3
"""Build a readable Markdown deck from the skill's slide-spec JSON."""
import argparse, json
from pathlib import Path


def esc(value):
    return str(value).replace("\r\n", "\n").strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("output")
    args = ap.parse_args()
    data = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    meta = data.get("metadata", {})
    slides = data.get("slides", [])
    out = []
    out.append(f"# {esc(meta.get('title', 'Reconstructed Deck'))}")
    out.append("")
    if meta.get("source"):
        out.append(f"- Source: {esc(meta['source'])}")
    if meta.get("mode"):
        out.append(f"- Mode: {esc(meta['mode'])}")
    out.append(f"- Slides: {len(slides)}")
    out.append("")

    for idx, spec in enumerate(slides, 1):
        out.append("---")
        out.append("")
        layout = spec.get("layout", "bullets")
        title = esc(spec.get("title", ""))
        subtitle = esc(spec.get("subtitle", ""))
        section = esc(spec.get("section", ""))
        elems = spec.get("elements", [])

        if layout == "cover":
            out.append(f"## {title}")
            out.append("")
            if subtitle:
                out.append(subtitle)
                out.append("")
        else:
            head = f"## {idx:02d}. {title}" if title else f"## {idx:02d}."
            out.append(head)
            out.append("")
            if section:
                out.append(f"`{section}`")
                out.append("")
            if subtitle:
                out.append(subtitle)
                out.append("")

        if layout in ("cards", "comparison", "process"):
            for e in elems:
                heading = esc(e.get("heading", e.get("text", "")))
                body = esc(e.get("body", e.get("caption", "")))
                if heading:
                    out.append(f"### {heading}")
                    out.append("")
                if body:
                    out.append(body)
                    out.append("")
        elif layout == "quote":
            for e in elems:
                quote = esc(e.get("text", e.get("body", "")))
                if quote:
                    out.append(f"> {quote}")
                    out.append("")
        elif layout == "image":
            for e in elems:
                path = esc(e.get("path", ""))
                caption = esc(e.get("caption", ""))
                if path:
                    out.append(f"![{caption or title}]({path})")
                    out.append("")
                if caption:
                    out.append(f"_{caption}_")
                    out.append("")
        elif layout != "cover":
            for e in elems:
                line = esc(e.get("text", e.get("body", "")))
                if line:
                    out.append(f"- {line}")
            if elems:
                out.append("")

        notes = esc(spec.get("notes", ""))
        if notes:
            out.append("Speaker notes:")
            out.append("")
            for line in notes.split("\n"):
                out.append(f"> {line.strip()}" if line.strip() else ">")
            out.append("")
        if spec.get("source_time") is not None:
            out.append(f"<!-- source_time: {spec['source_time']} -->")
            out.append("")

    path = Path(args.output)
    path.write_text("\n".join(out).rstrip() + "\n", encoding="utf-8")
    print(f"saved={path.resolve()} slides={len(slides)}")


if __name__ == "__main__":
    main()
