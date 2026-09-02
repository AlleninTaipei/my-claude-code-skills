# Quality Checklist

## Content

- Confirm chapter order and central argument against captions.
- Preserve proper nouns, commands, numbers, and qualifications.
- Remove caption repetition and speech fillers.
- Do not present inferred or approximate content as exact.
- Include the source URL in deck metadata or the final slide.

## Reconstruction

- Merge incremental animations into complete ideas.
- Keep one primary claim per slide.
- Rebuild text and simple diagrams as editable objects.
- Identify screenshot-based or approximate elements in the handoff.
- Avoid copying large amounts of copyrighted text or imagery unnecessarily.

## Layout

- Use 16:9 unless the source or user requests another ratio.
- Keep titles, body text, and footers inside safe margins.
- Maintain consistent typography, palette, spacing, and card geometry.
- Avoid transcript-sized paragraphs; target short bullets and concise labels.
- Check contrast, line breaks, clipping, overlaps, and connector alignment.

## Technical

- Open the file with `python-pptx` after saving.
- Test ZIP package integrity.
- Confirm slide count and dimensions.
- Generate a standalone PDF from the same slide specification without requiring Microsoft PowerPoint.
- Confirm PDF page count matches the PowerPoint slide count.
- Confirm the PDF uses a 16:9 page size and embeds or references a Unicode-capable font.
- Check missing image targets and external relationships.
- Render to images or PDF when a compatible renderer is available.
- Retain source media separately from the final deck so temporary assets can be removed safely.
