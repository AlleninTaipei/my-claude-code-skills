# md2course — Markdown to Interactive Learning HTML

Convert a Markdown notes or documentation file into a beautiful, self-contained single-page interactive learning course — matching the dark-theme visual style used in the Claude API course series.

## Usage

```
/md2course [file_path]
```

**Arguments:**
- `file_path` — path to the `.md` file (required, via `$ARGUMENTS`)

**Output:** A `.html` file written to the same directory as the input, same base filename.

---

## Instructions for Claude Code

You are converting a markdown file into a polished, self-contained interactive HTML learning course. Read `$ARGUMENTS` as the input file path. Follow every step below exactly.

---

### STEP 1 — Read and analyse the source

Read the markdown file at `$ARGUMENTS`. Identify:
- Title and overall topic
- Major sections (H2 headings → each becomes one `<section>`)
- Sub-concepts within each section (H3 headings → h3 or component inside the section)
- Code examples, comparisons, parameter lists, step-by-step processes, event sequences
- Relationships between concepts (sequential, parallel, hierarchical)
- Whether any concepts are universal across tools vs specific to one provider/tool — flag for scope badges

---

### STEP 2 — Choose a component for each section

For every major section, pick the best interactive component from this vocabulary:

| Content type | Component |
|---|---|
| Step-by-step process (3–6 steps) | Tabbed step navigator |
| A vs B comparison | Side-by-side two-column panel |
| Parameter / field list | `.api-fields` grid of `.field` cards |
| Sequential events or states | `.event-list` with `.event-item` rows |
| Key–value structured data | `.response-box` with `.response-field` rows |
| Important rule or concept tip | `.info-box` with `.tag` label |
| Key takeaway or mental model | `.takeaway` box (green gradient border) |
| Spectrum / range concept | Interactive `<input type="range">` slider |
| Code examples | `<pre class="code-block">` with syntax-highlight spans |
| Pros / cons or tradeoffs | Two-column card grid |
| Multiple named variants | Clickable chip/button selector that swaps content |

Every section must have at least one interactive or visual element — never only paragraphs.

---

### STEP 3 — Generate the complete HTML file

Write a fully self-contained HTML file. No external CSS, fonts, or JavaScript libraries. Everything inline.

#### Document shell

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>COURSE_TITLE</title>
  <style>
    /* ── Reset & base (Light mode — default) ── */
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
           background: #f0f4f8; color: #1a202c; line-height: 1.7; }

    /* ── Header ── */
    header { background: linear-gradient(135deg, #dbeafe 0%, #f0f4f8 100%);
             border-bottom: 1px solid #bfdbfe; padding: 48px 24px 40px; text-align: center; }
    header h1 { font-size: 2.2rem; font-weight: 700; color: #1e3a5f; }
    header p  { margin-top: 10px; color: #4a5568; font-size: 1.05rem;
                max-width: 600px; margin-inline: auto; }

    /* ── Layout ── */
    main    { max-width: 860px; margin: 0 auto; padding: 48px 24px 80px; }
    section { margin-bottom: 52px; }
    h2 { font-size: 1.4rem; font-weight: 600; color: #1e40af;
         border-left: 4px solid #3b82f6; padding-left: 14px; margin-bottom: 20px; }
    h3 { font-size: 1.05rem; font-weight: 600; color: #1a202c; margin: 20px 0 8px; }
    p  { color: #4a5568; margin-bottom: 12px; }

    /* ── Code blocks ── */
    .code-block { background: #f8fafc; border: 1px solid #cbd5e0; border-radius: 8px;
      padding: 16px 18px; font-family: monospace; font-size: 0.82rem; color: #1a202c;
      overflow-x: auto; margin-top: 14px; line-height: 1.7; white-space: pre; }
    .kw  { color: #7c3aed; }
    .fn  { color: #16a34a; }
    .str { color: #d97706; }
    .cmt { color: #94a3b8; font-style: italic; }
    .key { color: #2563eb; }

    /* ── Info box ── */
    .info-box { background: #dbeafe; border: 1px solid #93c5fd; border-radius: 10px;
      padding: 16px 20px; margin-top: 14px; }
    .info-box .tag { display: inline-block; background: #3b82f6; color: #fff;
      font-size: 0.72rem; font-weight: 700; padding: 2px 8px; border-radius: 4px;
      margin-bottom: 10px; letter-spacing: 0.05em; }
    .info-box p { color: #1e3a5f; font-size: 0.88rem; margin: 0; }

    /* ── Takeaway ── */
    .takeaway { background: linear-gradient(135deg, #dcfce7, #f0fdf4);
      border: 1px solid #4ade80; border-radius: 10px; padding: 20px 24px; margin-top: 16px; }
    .takeaway p { color: #166534; font-size: 0.9rem; margin: 0; }

    /* ── Field cards ── */
    .api-fields { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 16px; }
    .field { background: #fff; border: 1px solid #cbd5e0; border-radius: 8px; padding: 14px 16px; }
    .field .name { font-family: monospace; font-size: 0.85rem; color: #16a34a; font-weight: 600; }
    .field .desc { font-size: 0.82rem; color: #4a5568; margin-top: 4px; }

    /* ── Event list ── */
    .event-list { margin-top: 14px; display: flex; flex-direction: column; gap: 6px; }
    .event-item { background: #fff; border: 1px solid #cbd5e0; border-radius: 6px;
      padding: 9px 14px; display: flex; gap: 14px; align-items: baseline; }
    .event-name { font-family: monospace; font-size: 0.82rem; color: #16a34a;
      min-width: 160px; flex-shrink: 0; }
    .event-desc { font-size: 0.82rem; color: #4a5568; }

    /* ── Response / data box ── */
    .response-box { background: #fff; border: 1px solid #cbd5e0; border-radius: 10px;
      padding: 20px; margin-top: 16px; }
    .response-field { display: flex; gap: 16px; padding: 8px 0; border-bottom: 1px solid #e2e8f0; }
    .response-field:last-child { border-bottom: none; }
    .rf-key { font-family: monospace; font-size: 0.82rem; color: #d97706; width: 130px; flex-shrink: 0; }
    .rf-val { font-size: 0.85rem; color: #374151; }

    /* ── Scope badges ── */
    .scope-badge { display: inline-block; font-size: 0.58rem; font-weight: 700;
      letter-spacing: 0.07em; text-transform: uppercase; padding: 2px 8px;
      border-radius: 4px; vertical-align: middle; margin-left: 10px;
      position: relative; top: -2px; }
    .scope-universal { background: #dcfce7; color: #166534; border: 1px solid #4ade80; }
    .scope-api       { background: #fef3c7; color: #92400e; border: 1px solid #fcd34d; }
    .scope-specific  { background: #ede9fe; color: #6d28d9; border: 1px solid #a78bfa; }
    .scope-legend { display: flex; gap: 10px; flex-wrap: wrap; align-items: center;
      background: #e2e8f0; border: 1px solid #cbd5e0; border-radius: 8px;
      padding: 10px 18px; margin-bottom: 36px; }
    .scope-legend-label { font-size: 0.72rem; color: #4a5568; font-weight: 700; }
    .scope-legend-item  { display: flex; align-items: center; gap: 6px; font-size: 0.72rem; color: #374151; }

    /* ── Tabs ── */
    .stage-tabs { display: flex; gap: 6px; margin-bottom: 20px; flex-wrap: wrap; }
    .stage-tab  { padding: 7px 16px; border-radius: 20px; font-size: 0.82rem; font-weight: 600;
      cursor: pointer; border: 1px solid #cbd5e0; background: #e2e8f0; color: #4a5568; transition: all 0.2s; }
    .stage-tab.active { background: #2563eb; border-color: #3b82f6; color: #fff; }
    .stage-tab.done   { background: #166534; border-color: #4ade80; color: #dcfce7; }
    .step-indicator { color: #6b7280; font-size: 0.82rem; margin-top: 10px; display: block; }

    /* ── Panels ── */
    .demo-panel { display: none; }
    .demo-panel.visible { display: block; animation: fadeIn 0.3s ease; }
    @keyframes fadeIn { from { opacity:0; transform:translateY(6px) } to { opacity:1; transform:none } }

    /* ── Two-column layout ── */
    .two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-top: 16px; }
    .col-card { background: #fff; border: 1px solid #cbd5e0; border-radius: 10px; padding: 16px 18px; }
    .col-card-title { font-size: 0.75rem; font-weight: 700; letter-spacing: 0.07em;
      text-transform: uppercase; color: #6b7280; margin-bottom: 10px; }
    .col-card p { font-size: 0.83rem; color: #4a5568; margin-bottom: 6px; }
    .col-card p:last-child { margin-bottom: 0; }

    /* ── Chip selector ── */
    .chip-row { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 16px; align-items: center; }
    .chip-label { font-size: 0.75rem; color: #6b7280; }
    .chip { padding: 5px 14px; border-radius: 20px; font-size: 0.78rem; font-weight: 600;
      cursor: pointer; border: 1px solid #cbd5e0; background: #e2e8f0; color: #4a5568; transition: all 0.2s; }
    .chip.active { background: #dcfce7; border-color: #4ade80; color: #166534; }

    /* ── Responsive ── */
    @media (max-width: 640px) {
      .api-fields, .two-col { grid-template-columns: 1fr; }
    }

    /* ── Theme toggle button ── */
    #themeToggle { position: fixed; top: 16px; right: 16px; z-index: 9999;
      padding: 7px 14px; border-radius: 20px; font-size: 0.78rem; font-weight: 700;
      cursor: pointer; border: 1px solid #cbd5e0; background: #fff; color: #1a202c;
      transition: all 0.25s; box-shadow: 0 2px 8px rgba(0,0,0,0.12); letter-spacing: 0.03em; }
    #themeToggle:hover { border-color: #2563eb; color: #2563eb; }

    /* ── Dark mode overrides ── */
    body.dark { background: #0f1117; color: #e2e8f0; }
    body.dark header { background: linear-gradient(135deg, #1a1f2e 0%, #0f1117 100%); border-bottom-color: #2d3748; }
    body.dark header h1 { color: #f7fafc; }
    body.dark header p  { color: #a0aec0; }
    body.dark h2 { color: #90cdf4; border-left-color: #4299e1; }
    body.dark h3 { color: #e2e8f0; }
    body.dark p  { color: #a0aec0; }
    body.dark .code-block { background: #0d1117; border-color: #2d3748; color: #e2e8f0; }
    body.dark .kw  { color: #9f7aea; }
    body.dark .fn  { color: #68d391; }
    body.dark .str { color: #f6ad55; }
    body.dark .cmt { color: #4a5568; }
    body.dark .key { color: #63b3ed; }
    body.dark .info-box { background: #1a202c; border-color: #2a4a6a; }
    body.dark .info-box .tag { background: #2a4a6a; color: #90cdf4; }
    body.dark .info-box p { color: #a0aec0; }
    body.dark .takeaway { background: linear-gradient(135deg, #1a2a1a, #1a202c); border-color: #276749; }
    body.dark .takeaway p { color: #c6f6d5; }
    body.dark .field { background: #1a202c; border-color: #2d3748; }
    body.dark .field .name { color: #68d391; }
    body.dark .field .desc { color: #718096; }
    body.dark .event-item { background: #1a202c; border-color: #2d3748; }
    body.dark .event-name { color: #68d391; }
    body.dark .event-desc { color: #718096; }
    body.dark .response-box { background: #1a202c; border-color: #2d3748; }
    body.dark .response-field { border-bottom-color: #2d3748; }
    body.dark .rf-key { color: #f6ad55; }
    body.dark .rf-val { color: #a0aec0; }
    body.dark .scope-universal { background: #1a3a28; color: #68d391; border-color: #276749; }
    body.dark .scope-api       { background: #3a2a10; color: #f6ad55; border-color: #7a5a20; }
    body.dark .scope-specific  { background: #2d1f4a; color: #b794f4; border-color: #553c8b; }
    body.dark .scope-legend { background: #1a202c; border-color: #2d3748; }
    body.dark .scope-legend-label { color: #4a5568; }
    body.dark .scope-legend-item  { color: #718096; }
    body.dark .step-indicator { color: #718096; }
    body.dark .stage-tab { background: #1a202c; border-color: #2d3748; color: #718096; }
    body.dark .stage-tab.active { background: #2b6cb0; border-color: #4299e1; color: #fff; }
    body.dark .stage-tab.done   { background: #276749; border-color: #48bb78; color: #c6f6d5; }
    body.dark .col-card { background: #1a202c; border-color: #2d3748; }
    body.dark .col-card-title { color: #4a5568; }
    body.dark .col-card p { color: #a0aec0; }
    body.dark .chip { background: #1a202c; border-color: #2d3748; color: #718096; }
    body.dark .chip.active { background: #1c3a2a; border-color: #38a169; color: #68d391; }
    body.dark #themeToggle { background: #1a202c; color: #e2e8f0; border-color: #4a5568; box-shadow: 0 2px 8px rgba(0,0,0,0.4); }
    body.dark #themeToggle:hover { border-color: #90cdf4; color: #90cdf4; }

    /* ── Additional component CSS goes here as needed ── */
  </style>
</head>
<body>

<button id="themeToggle" onclick="toggleTheme()">🌙 暗色模式</button>

<header>
  <h1>COURSE_TITLE</h1>
  <p>COURSE_SUBTITLE</p>
</header>

<main>
  <!-- Scope legend (only if content has universal vs specific concepts) -->
  <!-- Sections go here -->
</main>

<script>
  /* ── Theme toggle ── */
  function toggleTheme() {
    const isDark = document.body.classList.toggle('dark');
    document.getElementById('themeToggle').textContent = isDark ? '☀ 亮色模式' : '🌙 暗色模式';
  }

  /* All other JavaScript goes here — one single block */
</script>
</body>
</html>
```

#### Syntax highlighting in code blocks

Always use these span classes inside `<pre class="code-block">` to colour code. Never leave code unstyled.

| Span class | Colour | Use for |
|---|---|---|
| `.kw` | purple `#9f7aea` | keywords: `def`, `class`, `import`, `if`, `return`, `async`, `await` |
| `.fn` | green `#68d391` | function/method names being called or defined |
| `.str` | orange `#f6ad55` | string literals and dictionary/object keys |
| `.cmt` | grey `#4a5568` italic | comments |
| `.key` | blue `#63b3ed` | variable names, parameter names |

#### JavaScript pattern for tab/step navigator

Use this exact pattern for any step-through component. Give each instance a unique prefix (e.g. `tu`, `lc`, `mcp`) to avoid name collisions.

```javascript
let XStep = 0;
const X_MAX = N - 1;  // N = number of panels

function xGoTo(n) {
  XStep = Math.max(0, Math.min(X_MAX, n));
  document.querySelectorAll('.x-panel').forEach((el, i) =>
    el.classList.toggle('visible', i === XStep));
  document.querySelectorAll('.x-tab').forEach((t, i) => {
    t.classList.remove('active', 'done');
    if (i === XStep)     t.classList.add('active');
    else if (i < XStep)  t.classList.add('done');
  });
  document.getElementById('xIndicator').textContent =
    `Step ${XStep + 1} of ${X_MAX + 1}`;
}

xGoTo(0);
```

HTML structure to match:
```html
<div class="stage-tabs">
  <div class="x-tab stage-tab active" onclick="xGoTo(0)">1 · First Step</div>
  <div class="x-tab stage-tab" onclick="xGoTo(1)">2 · Second Step</div>
  <!-- ... -->
</div>

<div class="x-panel demo-panel visible" id="x-p0">...</div>
<div class="x-panel demo-panel" id="x-p1">...</div>

<span class="step-indicator" id="xIndicator">Step 1 of N</span>
```

---

### STEP 4 — Quality rules (non-negotiable)

1. **Every section needs a visual/interactive element** — no section is only text + code block
2. **All code must be syntax-highlighted** using the span classes above
3. **Single `<script>` block** at the bottom — no inline `onclick` that calls undefined functions
4. **Responsive** — all two-column grids collapse to one column at ≤ 640px via media query
5. **Self-contained** — zero external resources; all CSS and JS inline
6. **Scope badges** — add `UNIVERSAL` / `API-SPECIFIC` / `TOOL-SPECIFIC` badges to h2s only when the content meaningfully distinguishes concept generality; include a legend div at the top of `<main>` if badges are used
7. **No lorem ipsum** — every word must come from the source markdown or be a genuine explanation
8. **Section count** — one `<section>` per H2 heading in the markdown; H3s become `<h3>` or component labels inside the section
9. **Light / Dark toggle** — default style is **light mode** (`body` base = light); always include the fixed-position `#themeToggle` button (top-right, text `🌙 暗色模式`) and the full `body.dark` CSS override block as shown in the document shell above; `toggleTheme()` toggles the `dark` class on `<body>` and must be the first function in the `<script>` block

---

### STEP 5 — Write the output file

- Output path: same directory as the input `.md` file, same base filename, `.html` extension
- Write the complete HTML using the Write tool
- After writing, report to the user:
  - Output file path
  - Number of sections created
  - Which component was chosen for each section
  - Any markdown content that could not be visualised interactively (list it so the user can decide)
