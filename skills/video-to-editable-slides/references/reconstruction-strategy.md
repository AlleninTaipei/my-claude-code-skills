# Reconstruction Strategy

## Decision Matrix

| Source element | Preferred reconstruction |
|---|---|
| Titles, labels, captions | Native editable text |
| Cards, pills, timelines, process flows | Native shapes and connectors |
| Tables and simple charts with legible values | Native tables/charts |
| Code samples | Editable monospaced text in a code panel |
| Product interfaces or web pages | Cropped screenshot with attribution |
| Photos and bespoke illustrations | Preserve as image when permitted |
| Incremental animation | Merge into the final meaningful composition |
| Narration without meaningful visuals | Create a concise explanatory slide or omit |

## Segmentation Heuristics

- Start with chapters and caption timestamps.
- Sample every 15–30 seconds to discover the overall visual grammar.
- Add samples before and after title changes, major layout changes, long pauses, and chapter boundaries.
- Treat small object additions on a stable canvas as animation states, not separate slides.
- Split a canvas when the main claim, diagram topology, or visual hierarchy changes.
- Prefer 20–40 meaningful slides for a 20-minute explainer, but let information density control the count.

## Content Compression

- Use the narration to recover intent, examples, and transitions.
- Keep only the words necessary to understand the slide without audio.
- Move detailed explanation into speaker notes when the output format supports it.
- Preserve important numbers, named tools, commands, comparisons, and qualifications.
- Mark uncertain OCR or illegible values instead of inventing them.

## Slide Specification JSON

```json
{
  "metadata": {
    "title": "Deck title",
    "source": "https://example.com/video",
    "mode": "professional-remake",
    "theme": {
      "background": "#18181A",
      "foreground": "#F2F0EB",
      "accent": "#F49A19",
      "muted": "#A5A5AA",
      "font": "Microsoft JhengHei"
    }
  },
  "slides": [
    {
      "section": "01 / Context",
      "title": "Slide title",
      "subtitle": "Optional subtitle",
      "layout": "cards",
      "elements": [
        {"type": "card", "heading": "Idea", "body": "Explanation", "accent": "#F49A19"}
      ],
      "source_time": 42.0
    }
  ]
}
```

Supported layouts in the generic builder: `cover`, `bullets`, `cards`, `comparison`, `process`, `quote`, and `image`.

Supported element types: `bullet`, `card`, `step`, `quote`, and `image`. Use `path` for local images and `caption` for attribution.
