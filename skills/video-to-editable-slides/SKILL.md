---
name: video-to-editable-slides
description: Reconstruct presentation-style videos as structured slide decks in editable PowerPoint and standalone PDF formats. Use when Codex receives a YouTube URL or local video and needs to extract metadata, captions, chapters, representative frames, slide transitions, visual style, and narration; consolidate incremental animation states; decide what to redraw versus preserve as screenshots; create matching 16:9 .pptx and .pdf files; support environments without Microsoft PowerPoint; or validate a reconstructed slide deck.
---

# Video to Editable Slides

Rebuild the information structure and visual language of a presentation-style video as an editable deck. Preserve meaning and attribution; do not claim access to the creator's original source file.

## Workflow

1. Confirm the source is authorized and accessible. Treat downloaded media as temporary analysis material.
2. Inspect metadata, captions, chapters, formats, and duration. Run `scripts/inspect_video.py` for a URL.
3. Obtain the video and captions with an available downloader. Prefer the highest practical resolution and preserve timestamps.
4. Extract representative frames and contact sheets with `scripts/extract_frames.py`. Start with 15–30 second sampling; add denser samples around visual changes.
5. Read `references/reconstruction-strategy.md`. Identify slide families, incremental animation states, screenshots, diagrams, code blocks, and speaker-only sections.
6. Produce a slide specification JSON before generating the deck. Keep one completed idea per slide; merge animation fragments that form one final composition.
7. Build the editable `.pptx` with `scripts/build_pptx.py`. Use native text, shapes, connectors, and tables wherever practical.
8. Build a matching standalone `.pdf` from the same slide specification with `scripts/build_pdf.py`. Do not require Microsoft PowerPoint for PDF creation.
9. Read `references/quality-checklist.md`. Validate the PowerPoint package with `scripts/validate_pptx.py`, validate the PDF with `scripts/validate_pdf.py`, then visually inspect rendered pages when a renderer is available.
10. Deliver both files by default, with a concise reconstruction note: source, slide count, editable elements, screenshot-based elements, and known limitations.

## Reconstruction Modes

- **Faithful:** Match the source layout, palette, typography, and slide rhythm as closely as practical.
- **Professional remake:** Preserve content and sequence while improving density, hierarchy, consistency, and readability. Use this by default when the user does not specify.
- **Outline only:** Produce slide titles, bullets, and speaker notes without attempting visual reconstruction.

## Required Judgment

- Merge progressive animation states instead of creating many nearly empty slides.
- Separate narration from on-slide copy; slides should not become transcript dumps.
- Rebuild text and simple diagrams as editable objects.
- Use screenshots for complex third-party interfaces, photos, or assets that cannot be recreated faithfully and legally.
- Recreate charts only when values are legible or recoverable; otherwise label them as approximate.
- Preserve source attribution and avoid redistributing copyrighted media beyond what is necessary for the user's reconstruction task.

## Slide Specification

Use the JSON schema documented in `references/reconstruction-strategy.md`. At minimum provide `title`, `subtitle`, `section`, `layout`, and `elements` for every slide. Pass the file to:

```powershell
python scripts/build_pptx.py slide-spec.json output.pptx
python scripts/build_pdf.py slide-spec.json output.pdf
```

Both generic builders consume the same JSON and support title slides, bullet slides, cards, comparison layouts, process flows, quotes, and image placements. Extend both builders together when source-specific visuals materially require it.

## PDF Output

- Generate PDF directly from the slide specification with ReportLab. Do not treat PowerPoint automation as the primary PDF path.
- Keep PDF page size at 16:9 so it visually matches the PowerPoint deck.
- Resolve a Unicode-capable system font before drawing Traditional Chinese text. Fail with a clear message if no usable font is available.
- Use LibreOffice or PowerPoint export only as an optional fidelity check when available. The direct PDF builder remains the fallback for environments without either application.
- When the user requests only one format, honor that request. Otherwise, deliver `.pptx` and `.pdf`.

## Dependencies and Fallbacks

- Prefer `yt-dlp` for public video metadata, captions, thumbnails, and media.
- Use OpenCV and Pillow for sampling and contact sheets.
- Use `python-pptx` for editable PowerPoint generation.
- Use ReportLab for standalone PDF generation without PowerPoint.
- If a required dependency is missing, request permission to install it. If the source cannot be downloaded, ask the user to attach the video and caption files.
- If ffmpeg is unavailable, use a video-only stream for frame analysis; audio is unnecessary when captions are present.

## Validation

Run:

```powershell
python scripts/validate_pptx.py output.pptx
python scripts/validate_pdf.py output.pdf
```

Treat package integrity, page count, and dimensions as minimum checks. Confirm that PPTX and PDF page counts match. Prefer visual rendering for final QA; structural validation cannot detect poor line breaks, clipping, or collisions.
