# Markdown deliverable specification

Use plain GitHub-flavored Markdown. Keep the hierarchy useful when rendered and readable as source text.

## Single-video note

Start with one H1 title. Follow it with a compact source block containing:

- Linked video title and channel.
- Canonical YouTube URL.
- Upload date and duration when available.
- Video ID.
- Content basis, such as creator captions, automatic captions, local transcription, or user-provided material.

Choose sections based on the source rather than filling a rigid template. A knowledge note commonly contains:

1. A short summary.
2. Main concepts organized by topic or chapter.
3. Source examples, formulas, commands, or quotations when useful.
4. Comparisons, procedures, or tables when they improve comprehension.
5. A concise review or practical takeaway.
6. Source and confidence limitations.

Do not add empty sections. Do not turn every sentence into a bullet. Prefer paragraphs for explanation and lists for genuinely parallel items.

## Source distinction

Make these categories distinguishable when more than one appears:

- Video content: faithful paraphrase or clearly attributed short excerpt.
- Translation: identify it as a translation when ambiguity is possible.
- Editorial explanation: label additions such as "補充說明" or "編者整理".
- Uncertainty: state what could not be verified and why.

Do not call editorial examples "影片例句". Reserve that label for wording supported by the transcript or inspected media.

## Timestamps

Use `MM:SS` for videos under one hour and `HH:MM:SS` otherwise. A timestamp may link directly to the source:

```markdown
[03:18](https://www.youtube.com/watch?v=VIDEO_ID&t=198s)
```

Avoid timestamping every sentence. Prefer section starts, demonstrations, definitions, and claims that benefit from verification.

## Channel index

The batch `README.md` should identify the channel, batch scope, update date, filters, and progress. Use a table with at least:

| Date | Video | Duration | Status | Note or reason |
| --- | --- | ---: | --- | --- |

Link completed items with relative paths. Show concise reasons for retryable, skipped, or failed items.

## Batch status

Use valid UTF-8 JSON. Include channel identity, scope, update time, aggregate counts, and one object per video. Each video object should contain:

```json
{
  "id": "VIDEO_ID",
  "title": "Source title",
  "upload_date": "YYYY-MM-DD",
  "duration_seconds": 123,
  "status": "completed",
  "source": "creator_captions",
  "output": "videos/example.md"
}
```

For non-completed items, replace `source` and `output` when appropriate and include a stable, concise `reason` value. Aggregate counts must equal the number of video records.

## Filename guidance

Prefer portable lowercase filenames using ASCII words where practical:

```text
videos/YYYY-MM-DD-topic-VIDEO_ID.md
```

Retaining the video ID prevents collisions and makes reconciliation reliable. Avoid characters invalid on Windows, including `<`, `>`, `:`, `"`, `/`, `\`, `|`, `?`, and `*`.
