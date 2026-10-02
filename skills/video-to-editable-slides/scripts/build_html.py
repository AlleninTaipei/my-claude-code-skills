#!/usr/bin/env python3
"""Build a self-contained 16:9 HTML deck from the skill's slide-spec JSON."""
import argparse, base64, html, json, mimetypes
from pathlib import Path

THEME = {
    "background": "#18181A",
    "foreground": "#F2F0EB",
    "accent": "#F49A19",
    "muted": "#A5A5AA",
    "font": "Microsoft JhengHei",
    "surface": "#232327",
}

CSS = """
:root {
  --bg: %(background)s; --fg: %(foreground)s; --accent: %(accent)s;
  --muted: %(muted)s; --surface: %(surface)s;
  --font: "%(font)s", "Noto Sans TC", system-ui, sans-serif;
}
* { box-sizing: border-box; }
body { margin: 0; background: #0d0d0f; color: var(--fg); font-family: var(--font); }
.deck { display: flex; flex-direction: column; align-items: center; gap: 24px; padding: 24px 16px 64px; }
.slide {
  position: relative; width: min(1280px, 100%%); aspect-ratio: 16 / 9;
  background: var(--bg); border-top: 4px solid var(--accent); border-radius: 6px;
  padding: 44px 56px; overflow: hidden; display: flex; flex-direction: column;
  box-shadow: 0 8px 28px rgba(0,0,0,.45);
}
.kicker { font-size: .78rem; letter-spacing: .12em; text-transform: uppercase; color: var(--accent); }
.page-no { position: absolute; top: 28px; right: 40px; font-size: .78rem; color: var(--muted); }
h1 { font-size: 2.9rem; margin: .4em 0 .2em; line-height: 1.15; }
h2 { font-size: 1.95rem; margin: .25em 0 .15em; line-height: 1.2; }
.subtitle { color: var(--muted); font-size: 1rem; margin: 0 0 .6em; }
.body { flex: 1; min-height: 0; overflow: hidden; }
ul { margin: .4em 0; padding-left: 1.2em; font-size: 1.25rem; line-height: 1.7; }
.cards { display: grid; grid-auto-flow: column; grid-auto-columns: 1fr; gap: 18px; height: 100%%; align-items: stretch; }
.card { background: var(--surface); border: 1px solid var(--accent); border-radius: 10px; padding: 18px 20px; }
.card h3 { margin: 0 0 .5em; font-size: 1.05rem; color: var(--accent); }
.card p { margin: 0; font-size: .92rem; line-height: 1.6; color: var(--fg); }
.process .card { position: relative; }
.process .card:not(:last-child)::after {
  content: "\\2192"; position: absolute; right: -16px; top: 50%%; transform: translateY(-50%%);
  color: var(--accent); font-size: 1.4rem;
}
blockquote { margin: 0; font-size: 1.9rem; line-height: 1.5; color: var(--accent); text-align: center;
  display: flex; align-items: center; justify-content: center; height: 100%%; }
figure { margin: 0; height: 100%%; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 10px; }
figure img { max-width: 100%%; max-height: 88%%; object-fit: contain; border-radius: 4px; }
figcaption { font-size: .8rem; color: var(--muted); }
.notes { width: min(1280px, 100%%); font-size: .88rem; color: var(--muted); line-height: 1.6;
  border-left: 3px solid var(--surface); padding: 2px 0 2px 14px; margin: -12px 0 4px; }
.meta { color: var(--muted); font-size: .8rem; margin-top: auto; }
@media print {
  body { background: var(--bg); }
  .deck { gap: 0; padding: 0; }
  .slide { width: 100%%; border-radius: 0; box-shadow: none; page-break-after: always; }
  .notes { display: none; }
}
"""


def esc(value):
    return html.escape(str(value).strip())


def embed_image(path):
    p = Path(path)
    if not p.is_file():
        return None
    mime = mimetypes.guess_type(p.name)[0] or "image/png"
    return f"data:{mime};base64,{base64.b64encode(p.read_bytes()).decode('ascii')}"


def render_slide(idx, spec, meta):
    layout = spec.get("layout", "bullets")
    title = esc(spec.get("title", ""))
    subtitle = esc(spec.get("subtitle", ""))
    section = esc(spec.get("section", ""))
    elems = spec.get("elements", [])
    out = ['<section class="slide">']

    if layout == "cover":
        out.append(f"<h1>{title}</h1>")
        if subtitle:
            out.append(f'<p class="subtitle">{subtitle}</p>')
        if meta.get("source"):
            out.append(f'<p class="meta">{esc(meta["source"])}</p>')
        out.append("</section>")
        return "\n".join(out)

    out.append(f'<span class="page-no">{idx:02d}</span>')
    if section:
        out.append(f'<span class="kicker">{section}</span>')
    if title:
        out.append(f"<h2>{title}</h2>")
    if subtitle:
        out.append(f'<p class="subtitle">{subtitle}</p>')
    out.append('<div class="body">')

    if layout in ("cards", "comparison", "process"):
        out.append(f'<div class="cards {layout}">')
        for e in elems:
            heading = esc(e.get("heading", e.get("text", "")))
            body = esc(e.get("body", e.get("caption", "")))
            accent = e.get("accent")
            style = f' style="border-color:{esc(accent)}"' if accent else ""
            head_style = f' style="color:{esc(accent)}"' if accent else ""
            out.append(f'<div class="card"{style}>')
            if heading:
                out.append(f"<h3{head_style}>{heading}</h3>")
            if body:
                out.append(f"<p>{body}</p>")
            out.append("</div>")
        out.append("</div>")
    elif layout == "quote":
        quote = esc(elems[0].get("text", elems[0].get("body", ""))) if elems else ""
        out.append(f"<blockquote>{quote}</blockquote>")
    elif layout == "image":
        e = elems[0] if elems else {}
        src = embed_image(e.get("path", "")) if e.get("path") else None
        out.append("<figure>")
        if src:
            out.append(f'<img src="{src}" alt="{esc(e.get("caption", title))}">')
        else:
            out.append(f'<figcaption>Missing image: {esc(e.get("path", ""))}</figcaption>')
        if e.get("caption"):
            out.append(f"<figcaption>{esc(e['caption'])}</figcaption>")
        out.append("</figure>")
    else:
        out.append("<ul>")
        for e in elems:
            line = esc(e.get("text", e.get("body", "")))
            if line:
                out.append(f"<li>{line}</li>")
        out.append("</ul>")

    out.append("</div>")
    out.append("</section>")
    notes = esc(spec.get("notes", ""))
    if notes:
        out.append(f'<div class="notes">{notes}</div>')
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("output")
    args = ap.parse_args()
    data = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    meta = data.get("metadata", {})
    theme = dict(THEME)
    theme.update({k: v for k, v in meta.get("theme", {}).items() if v})
    slides = data.get("slides", [])
    body = "\n".join(render_slide(i, s, meta) for i, s in enumerate(slides, 1))
    doc = f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(meta.get('title', 'Reconstructed Deck'))}</title>
<style>{CSS % theme}</style>
</head>
<body>
<main class="deck">
{body}
</main>
</body>
</html>
"""
    path = Path(args.output)
    path.write_text(doc, encoding="utf-8")
    print(f"saved={path.resolve()} slides={len(slides)}")


if __name__ == "__main__":
    main()
