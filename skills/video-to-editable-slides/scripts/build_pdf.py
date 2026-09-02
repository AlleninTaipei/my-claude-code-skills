#!/usr/bin/env python3
"""Build a standalone 16:9 PDF deck from the skill's slide-spec JSON."""
import argparse
import json
import os
from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph

PAGE_W, PAGE_H = 960.0, 540.0


def find_font(explicit=None):
    candidates = [
        explicit,
        os.environ.get("SLIDES_FONT"),
        r"C:\Windows\Fonts\msjh.ttc",
        r"C:\Windows\Fonts\msjh.ttf",
        r"C:\Windows\Fonts\mingliu.ttc",
        r"C:\Windows\Fonts\arialuni.ttf",
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return Path(candidate)
    raise SystemExit(
        "No Unicode-capable font found. Pass --font PATH or set SLIDES_FONT."
    )


def register_font(path):
    try:
        pdfmetrics.registerFont(TTFont("SlidesFont", str(path), subfontIndex=0))
    except TypeError:
        pdfmetrics.registerFont(TTFont("SlidesFont", str(path)))
    return "SlidesFont"


def safe(text):
    return (
        str(text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\n", "<br/>")
    )


def draw_text(c, value, x, y, w, h, font, size, color, bold=False, align=TA_LEFT):
    style = ParagraphStyle(
        "slide",
        fontName=font,
        fontSize=size,
        leading=size * 1.28,
        textColor=HexColor(color),
        alignment=align,
    )
    markup = safe(value)
    if bold:
        markup = f"<b>{markup}</b>"
    para = Paragraph(markup, style)
    pw, ph = para.wrap(w, h)
    para.drawOn(c, x, y + h - ph)


def draw_card(c, element, x, y, w, h, theme, font):
    accent = element.get("accent", theme["accent"])
    c.setFillColor(HexColor("#232327"))
    c.setStrokeColor(HexColor(accent))
    c.setLineWidth(1.2)
    c.roundRect(x, y, w, h, 10, fill=1, stroke=1)
    draw_text(
        c,
        element.get("heading", element.get("text", "")),
        x + 12,
        y + h - 47,
        w - 24,
        32,
        font,
        15,
        accent,
        True,
    )
    draw_text(
        c,
        element.get("body", element.get("caption", "")),
        x + 12,
        y + 15,
        w - 24,
        h - 64,
        font,
        11,
        theme["foreground"],
    )


def draw_process_arrow(c, x, y, gap, color):
    c.setFillColor(HexColor(color))
    pad = 3.0
    x0, x1 = x + pad, x + gap - pad
    if x1 <= x0:
        return
    shaft_end = x0 + (x1 - x0) * 0.55
    c.rect(x0, y - 1.5, shaft_end - x0, 3.0, fill=1, stroke=0)
    p = c.beginPath()
    p.moveTo(shaft_end, y - 7)
    p.lineTo(x1, y)
    p.lineTo(shaft_end, y + 7)
    p.close()
    c.drawPath(p, fill=1, stroke=0)


def draw_slide(c, spec, meta, theme, font, number):
    c.setFillColor(HexColor(theme["background"]))
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    c.setFillColor(HexColor(theme["accent"]))
    c.rect(0, PAGE_H - 4, PAGE_W, 4, fill=1, stroke=0)

    layout = spec.get("layout", "bullets")
    title = spec.get("title", "")
    subtitle = spec.get("subtitle", "")
    elements = spec.get("elements", [])

    if layout == "cover":
        draw_text(c, title, 58, 300, 840, 100, font, 34, theme["foreground"], True)
        draw_text(c, subtitle, 60, 235, 780, 50, font, 18, theme["muted"])
        draw_text(c, meta.get("source", ""), 60, 28, 840, 22, font, 8, theme["muted"])
        return

    draw_text(c, spec.get("section", ""), 32, 498, 360, 20, font, 8, theme["accent"], True)
    draw_text(c, f"{number:02d}", 850, 498, 70, 20, font, 8, theme["muted"], align=TA_RIGHT)
    draw_text(c, title, 54, 426, 850, 58, font, 24, theme["foreground"], True)
    if subtitle:
        draw_text(c, subtitle, 55, 394, 825, 28, font, 11, theme["muted"])

    if layout in ("cards", "comparison", "process"):
        count = max(1, len(elements))
        gap, left, total = 18.0, 54.0, 852.0
        width = (total - gap * (count - 1)) / count
        card_y, card_h = 120, 235
        for i, element in enumerate(elements):
            cx = left + i * (width + gap)
            draw_card(c, element, cx, card_y, width, card_h, theme, font)
            if layout == "process" and i < count - 1:
                draw_process_arrow(c, cx + width, card_y + card_h / 2, gap, theme["accent"])
    elif layout == "quote":
        quote = elements[0].get("text", "") if elements else ""
        draw_text(c, quote, 80, 185, 800, 170, font, 25, theme["accent"], True, TA_CENTER)
    elif layout == "image":
        element = elements[0] if elements else {}
        path = Path(element.get("path", ""))
        if path.is_file():
            c.drawImage(ImageReader(str(path)), 72, 80, 816, 300, preserveAspectRatio=True, anchor="c")
        if element.get("caption"):
            draw_text(c, element["caption"], 72, 42, 816, 20, font, 8, theme["muted"], align=TA_CENTER)
    else:
        lines = [
            e.get("text", e.get("body", ""))
            for e in elements
            if e.get("text") or e.get("body")
        ]
        bullet_text = "<br/><br/>".join(f"• {safe(line)}" for line in lines)
        style = ParagraphStyle(
            "bullets",
            fontName=font,
            fontSize=18,
            leading=25,
            textColor=HexColor(theme["foreground"]),
        )
        para = Paragraph(bullet_text, style)
        _, ph = para.wrap(800, 315)
        para.drawOn(c, 72, 365 - ph)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("output")
    ap.add_argument("--font")
    args = ap.parse_args()

    data = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    meta = data.get("metadata", {})
    theme = {
        "background": "#18181A",
        "foreground": "#F2F0EB",
        "accent": "#F49A19",
        "muted": "#A5A5AA",
        "font": "Microsoft JhengHei",
    }
    theme.update(meta.get("theme", {}))
    font_path = find_font(args.font)
    font = register_font(font_path)

    output = Path(args.output)
    pdf = canvas.Canvas(str(output), pagesize=(PAGE_W, PAGE_H), pageCompression=1)
    pdf.setTitle(meta.get("title", ""))
    pdf.setSubject(f"Source: {meta.get('source', '')}")
    for number, spec in enumerate(data.get("slides", []), 1):
        draw_slide(pdf, spec, meta, theme, font, number)
        pdf.showPage()
    pdf.save()
    print(f"saved={output.resolve()} pages={len(data.get('slides', []))} font={font_path}")


if __name__ == "__main__":
    main()
