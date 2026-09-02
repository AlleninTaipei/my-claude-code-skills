---
name: knowledge-youtube-to-markdown
description: Convert knowledge-focused YouTube videos or channel batches into source-grounded, readable Markdown notes. Use for YouTube-to-Markdown requests involving captions, transcripts, educational summaries, video indexes, or resumable channel processing. Do not use for slide-deck reconstruction or verbatim transcript-only requests.
---

# Knowledge YouTube to Markdown

Turn educational YouTube content into edited learning notes that remain traceable to the source. Support one video or a resumable channel batch.

## Select the mode

- Single video: produce one Markdown note.
- Channel or playlist: inventory first, apply the user's filters, then process videos individually. Maintain an index and machine-readable status file.
- If the user does not specify a batch size, run a small representative pilot before scaling to the entire channel. State the selected scope.

## Source acquisition

1. Normalize the URL and remove accidental trailing punctuation.
2. Inspect public metadata before downloading media. Collect at least the video ID, title, channel, canonical URL, upload date, duration, chapters, and caption availability.
3. Prefer content sources in this order:
   1. Creator-provided captions.
   2. Original-language automatic captions.
   3. User-provided transcript, audio, or video.
   4. Legally accessible video or audio transcribed locally.
4. Treat downloaded captions and media as temporary analysis material. Do not imply access to the creator's original notes or source files.
5. If the source lacks captions and the media cannot be accessed, mark the item as retryable. Do not infer lesson content from the title, description, thumbnail, or general subject knowledge.

For VTT captions, use `scripts/vtt_to_text.py` when repeated incremental caption cues make the transcript difficult to read.

## Build the note

Read [references/markdown-spec.md](references/markdown-spec.md) before writing deliverables.

Transform the source rather than dumping a transcript:

- Preserve the video's claims, examples, qualifications, and sequence when sequence carries meaning.
- Remove repeated caption fragments, filler, pauses, greetings, and unrelated promotion unless context requires them.
- Separate source-derived content from editorial additions.
- Correct obvious automatic-caption errors only when context makes the correction reliable.
- Preserve examples in their original language. Add translations when they materially improve learning.
- Use timestamps for long videos, distinct chapters, procedures, or claims a reader may want to verify. They are optional for short, single-topic videos.
- Identify uncertainty explicitly. Never silently invent missing wording, examples, statistics, or citations.
- Paraphrase copyrighted content into learning notes. Avoid producing a substitute for the full video or an unnecessarily verbatim transcript unless the user supplies the text or explicitly requests a transcript within applicable limits.

## Batch processing

For a channel or playlist:

1. Inventory entries before processing. Record selection and exclusion reasons.
2. Apply requested filters such as date range, playlist, public visibility, video length, Shorts, livestreams, and caption availability.
3. Use stable filenames containing a date or video ID so reruns do not create duplicates.
4. Process each video independently. A failure must not invalidate completed notes.
5. Create `README.md` as the human-readable index and `batch-status.json` as resumable state.
6. On rerun, skip completed items unless the user requests regeneration. Retry only eligible failures and add new entries.

Recommended states:

- `pending`: selected but not attempted.
- `completed`: note created and verified.
- `retryable`: a temporary source, network, rate-limit, or missing-input problem prevented completion.
- `skipped`: excluded by scope or unsuitable content, with a reason.
- `failed`: a non-temporary processing error requiring review.

Stop repeated automated retries after a small number of identical failures. Preserve the exact reason and tell the user what input or access would unblock the item.

## Verification

Before delivery:

- Confirm every note links to the correct canonical video URL and identifies the video ID.
- Check metadata against the inspected source.
- Confirm examples and claims are supported by captions, transcript, or inspected media.
- Validate that `batch-status.json` parses and that its counts match the indexed items.
- Check all relative links in `README.md` and confirm each `completed` output exists.
- Report completed, retryable, skipped, and failed counts without presenting partial output as a fully completed batch.

Deliver the Markdown files and briefly disclose caption or transcription limitations.
