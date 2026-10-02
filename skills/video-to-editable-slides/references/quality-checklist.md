# Quality Checklist

## Content

- Confirm chapter order and central argument against captions.
- Preserve proper nouns, commands, numbers, and qualifications.
- Remove caption repetition and speech fillers.
- Do not present inferred or approximate content as exact.
- Include the source URL in deck metadata, the Markdown header, or the cover slide.

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

## Technical: Default Formats

- Confirm the Markdown deck has one `---` separated section per slide and no empty slide bodies.
- Confirm speaker notes landed in the Markdown blockquotes rather than the on-slide copy.
- Open the HTML deck in a browser and check the first, a middle, and the last slide for clipping or overflow.
- Confirm every image in the HTML deck embedded as a data URI; a `Missing image` caption means the path was wrong.
- Confirm the `slides=N` count printed by each builder matches.
- Keep the slide specification JSON with the outputs so any format can be regenerated.

## Technical: Optional Formats

- Produce `.pptx` and `.pdf` only when the user requested them.
- Open the file with `python-pptx` after saving and test ZIP package integrity.
- Confirm slide count and dimensions.
- Generate the PDF from the same slide specification without requiring Microsoft PowerPoint.
- Confirm PDF page count matches the Markdown and HTML slide count.
- Confirm the PDF uses a 16:9 page size and embeds or references a Unicode-capable font.
- Check missing image targets and external relationships.
- Render to images or PDF when a compatible renderer is available.
- Retain source media separately from the final deck so temporary assets can be removed safely.
