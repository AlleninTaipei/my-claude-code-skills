# Content Philosophy

> **When to read this:** During Phase 2.5 (writing module briefs) and Phase 3 (writing module HTML). These principles guide every content decision — what to show, how to explain it, and how to test understanding.

These principles are what separate a great course from a generic tutorial. They should guide every content decision:

### Show, Don't Tell — Aggressively Visual
People's eyes glaze over text blocks. The course should feel closer to an infographic than a textbook. Follow these hard rules:

**Text limits:**
- Max **2-3 sentences** per text block. If you're writing a fourth sentence, stop and convert it into a visual instead.
- No text block should ever be wider than the content width AND taller than ~4 lines. If it is, break it up with a visual element.
- Every screen must be **at least 50% visual** (diagrams, code blocks, cards, animations, badges — anything that isn't a paragraph).

**Convert text to visuals:**
- A list of 3+ items → **cards with icons** (pattern cards, feature cards)
- A sequence of steps → **flow diagram with arrows** or **numbered step cards**
- "Component A talks to Component B" → **animated data flow** or **group chat visualization**
- "This file does X, that file does Y" → **visual file tree with annotations** or **icon + one-liner badges**
- Explaining what code does → **code↔English translation block** (not a paragraph *about* the code)
- Comparing two approaches → **side-by-side columns** with visual contrast

**Visual breathing room:**
- Use generous spacing between elements (`--space-8` to `--space-12` between sections)
- Alternate between full-width visuals and narrow text blocks to create rhythm
- Every module should have at least one "hero visual" — a diagram, animation, or interactive element that dominates the screen and teaches the core concept at a glance

### Code ↔ English Translations
Every code snippet gets a side-by-side plain English translation. Left panel: real code from the project with syntax highlighting. Right panel: line-by-line plain English explaining what each line does. This is the single most valuable teaching tool for non-technical learners.

**Critical: No horizontal scrollbars on code.** All code must use `white-space: pre-wrap` so it wraps instead of scrolling. This is a course for non-technical people, not an IDE — readability beats preserving indentation structure.

**Critical: Use original code exactly as-is.** Never modify, simplify, or trim code snippets from the codebase. The learner should be able to open the real file and see the exact same code they learned from — that builds trust. Instead of editing code to make it shorter, *choose* naturally short, punchy snippets (5-10 lines) from the codebase that illustrate the concept well. Every codebase has compact, self-contained moments — find those rather than butchering longer functions.

### One Concept Per Screen
No walls of text. Each screen within a module teaches exactly one idea. If you need more space, add another screen — don't cram.

### Metaphors First, Then Reality
Introduce every new concept with a metaphor from everyday life. Then immediately ground it: "In our code, this looks like..." The metaphor builds intuition; the code grounds it in reality.

**Critical: No recycled metaphors.** Do NOT default to "restaurant" for everything — that's the #1 crutch. Each concept deserves its own metaphor that feels natural to *that specific idea*. A database is a library with a card catalog. Auth is a bouncer checking IDs. An event loop is an air traffic controller. Message passing is a postal system. API rate limiting is a nightclub with a capacity limit. Pick the metaphor that makes the concept click, not the one that's easiest to reach for. If you catch yourself using "restaurant" or "kitchen" more than once in a course, stop and rethink.

### Learn by Tracing
Follow what actually happens when the learner does something they already do every day in the app — trace the data flow end-to-end. "You know that button you click? Here's the journey your data takes after you click it..." This works because the learner has *already experienced the result* — now they're seeing the machinery behind it. It's like watching a behind-the-scenes documentary of a movie you loved.

### Make It Memorable
Use "aha!" callout boxes for universal CS insights. Use humor where natural (not forced). Give components personality — they're "characters" in a story, not abstract boxes on a diagram.

### Glossary Tooltips — No Term Left Behind
Every technical term (API, DOM, callback, middleware, etc.) gets a dashed-underline tooltip on first use in each module. Hover on desktop or tap on mobile to see a 1-2 sentence plain-English definition. The learner should never have to leave the page to Google a term. This is the difference between a course that *says* it's for non-technical people and one that actually *is*.

**Be extremely aggressive with tooltips.** If there is even a 1% chance a non-technical person doesn't know a word, tooltip it. This includes:
- Software names they might not know (Blender, GIMP, Audacity, etc.)
- Everyday developer terms (REPL, JSON, flag, CLI, API, SDK, etc.)
- Programming concepts (function, variable, dictionary, class, module, etc.)
- Infrastructure terms (PATH, pip, namespace, entry point, etc.)
- Acronyms — ALWAYS tooltip acronyms on first use

**The vocabulary IS the learning.** One of the key goals is for learners to acquire the precise technical vocabulary they need to communicate with AI coding agents. Each tooltip should teach the term in a way that helps the learner USE it in their own instructions — e.g., "A **flag** is an option you add to a command to change its behavior — like adding '--json' to get structured data instead of plain text. When talking to AI, you'd say 'add a flag for verbose output.'"

**Cursor:** Use `cursor: pointer` on terms (not `cursor: help`). The question-mark cursor feels clinical — a pointer feels clickable and inviting.

**Tooltip overflow fix:** Translation blocks and other containers with `overflow: hidden` will clip tooltips. To fix this, the tooltip JS must use `position: fixed` and calculate coordinates from `getBoundingClientRect()` instead of relying on CSS `position: absolute` within the container. Append tooltips to `document.body` rather than inside the term element. This ensures tooltips are never clipped by any ancestor's overflow.
