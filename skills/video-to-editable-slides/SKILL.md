---
name: video-to-editable-slides
description: Reconstruct presentation-style videos as structured slide decks. Produces editable Markdown and a self-contained HTML deck by default, and editable PowerPoint plus standalone PDF on request. Use when Codex receives a YouTube URL or local video and needs to extract metadata, captions, chapters, representative frames, slide transitions, visual style, and narration; consolidate incremental animation states; decide what to redraw versus preserve as screenshots; create .md, .html, .pptx, or .pdf slide decks; support environments without Microsoft PowerPoint; or validate a reconstructed slide deck.
---

# Video to Editable Slides

Rebuild the information structure and visual language of a presentation-style video as an editable deck. Preserve meaning and attribution; do not claim access to the creator's original source file.

## Default Output

- Default deliverables are `deck.md` and `deck.html`, both generated from one slide specification JSON.
- Generate `.pptx` and `.pdf` only when the user asks for them, by name or by intent, for example "also give me PowerPoint", "I need a PDF", "output all formats", or "I have to edit it in Office".
- When the user names a subset, honor exactly that subset.
- Keep the slide specification JSON alongside the outputs so any format can be regenerated without reanalyzing the video.

## Workflow

1. Confirm the source is authorized and accessible. Treat downloaded media as temporary analysis material.
2. Inspect metadata, captions, chapters, formats, and duration. Run `scripts/inspect_video.py` for a URL.
3. Obtain the video and captions with an available downloader. Prefer the highest practical resolution and preserve timestamps.
4. Extract representative frames and contact sheets with `scripts/extract_frames.py`. Start with 15–30 second sampling; add denser samples around visual changes.
5. Read `references/reconstruction-strategy.md`. Identify slide families, incremental animation states, screenshots, diagrams, code blocks, and speaker-only sections.
6. Produce a slide specification JSON before generating any deck. Keep one completed idea per slide; merge animation fragments that form one final composition.
7. Build the Markdown deck with `scripts/build_md.py` and the self-contained HTML deck with `scripts/build_html.py`. These two are the default deliverables.
8. Build `.pptx` with `scripts/build_pptx.py` and `.pdf` with `scripts/build_pdf.py` only when the user requested those formats.
9. Read `references/quality-checklist.md`. Validate every format you produced: check the Markdown headings and slide count, open the HTML in a renderer when one is available, then run `scripts/validate_pptx.py` and `scripts/validate_pdf.py` for the optional binary formats.
10. Deliver the produced files with a concise reconstruction note: source, slide count, formats generated, editable elements, screenshot-based elements, and known limitations. Mention that `.pptx` and `.pdf` are available on request when they were not generated.

## Reconstruction Modes

- **Faithful:** Match the source layout, palette, typography, and slide rhythm as closely as practical.
- **Professional remake:** Preserve content and sequence while improving density, hierarchy, consistency, and readability. Use this by default when the user does not specify.
- **Outline only:** Produce slide titles, bullets, and speaker notes without attempting visual reconstruction. The Markdown output alone satisfies this mode.

## Required Judgment

- Merge progressive animation states instead of creating many nearly empty slides.
- Separate narration from on-slide copy; slides should not become transcript dumps.
- Rebuild text and simple diagrams as editable objects.
- Use screenshots for complex third-party interfaces, photos, or assets that cannot be recreated faithfully and legally.
- Recreate charts only when values are legible or recoverable; otherwise label them as approximate.
- Preserve source attribution and avoid redistributing copyrighted media beyond what is necessary for the user's reconstruction task.

## Slide Specification

Use the JSON schema documented in `references/reconstruction-strategy.md`. At minimum provide `title`, `subtitle`, `section`, `layout`, and `elements` for every slide. Add `notes` for speaker notes; the Markdown and HTML builders render them. Pass the same file to every builder:

```powershell
python scripts/build_md.py slide-spec.json deck.md
python scripts/build_html.py slide-spec.json deck.html
python scripts/build_pptx.py slide-spec.json deck.pptx    # on request
python scripts/build_pdf.py slide-spec.json deck.pdf      # on request
```

All four builders consume the same JSON and support title slides, bullet slides, cards, comparison layouts, process flows, quotes, and image placements. Extend the builders together when source-specific visuals materially require it.

## Markdown and HTML Output

- Markdown is the editing surface: one `---` separated section per slide, headings for titles, lists for bullets, blockquotes for quotes and speaker notes.
- HTML is the viewing surface: a single self-contained file with 16:9 slide sections, inline CSS, and base64 embedded images. It needs no network access and no build step.
- The HTML print stylesheet paginates one slide per page, so a browser "print to PDF" covers casual PDF needs without the ReportLab path.
- Neither builder requires third-party packages, so the default path works in a bare Python environment.

## PPTX and PDF Output

- Generate these only when requested. Treat them as export targets of the same specification, not as the primary artifacts.
- Generate PDF directly from the slide specification with ReportLab. Do not treat PowerPoint automation as the primary PDF path.
- Keep PPTX slide size and PDF page size at 16:9 so all formats match.
- Resolve a Unicode-capable system font before drawing Traditional Chinese text. Fail with a clear message if no usable font is available.
- Use LibreOffice or PowerPoint export only as an optional fidelity check when available.

## Dependencies and Fallbacks

- Prefer `yt-dlp` for public video metadata, captions, thumbnails, and media.
- Use OpenCV and Pillow for sampling and contact sheets.
- The Markdown and HTML builders use the standard library only.
- Use `python-pptx` for editable PowerPoint generation and ReportLab for standalone PDF generation. Install these only when those formats are requested.
- If a required dependency is missing, request permission to install it. If the source cannot be downloaded, ask the user to attach the video and caption files.
- If ffmpeg is unavailable, use a video-only stream for frame analysis; audio is unnecessary when captions are present.

## Validation

Every builder prints `slides=N`. Confirm that count matches across the formats you produced.

```powershell
python scripts/validate_pptx.py deck.pptx
python scripts/validate_pdf.py deck.pdf --expected-pages N
```

For the default formats, confirm the Markdown slide separators and heading count, open the HTML deck in a browser, and check the last slide for clipping. Treat package integrity, page count, and dimensions as minimum checks for the optional formats. Prefer visual rendering for final QA; structural validation cannot detect poor line breaks, clipping, or collisions.
