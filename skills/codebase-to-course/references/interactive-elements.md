# Interactive Elements Reference

Implementation patterns for every interactive element type used in courses. Pick the elements that best serve each module's teaching goal.

> **Architecture note:** All CSS and JavaScript for these elements live in `references/styles.css` and `references/main.js`, which are copied verbatim into every course directory. When writing module HTML files, use only the HTML patterns below — do **not** inline `<style>` or `<script>` tags for these elements. The engines in `main.js` auto-initialize on page load by scanning for the relevant class names and `data-*` attributes described here.

## Table of Contents
1. [Code ↔ English Translation Blocks](#code--english-translation-blocks)
2. [Group Chat Animation](#group-chat-animation)
3. [Message Flow / Data Flow Animation](#message-flow--data-flow-animation)
4. [Interactive Architecture Diagram](#interactive-architecture-diagram)
5. [Layer Toggle Demo](#layer-toggle-demo)
6. [Callout Boxes](#callout-boxes)
7. [Pattern/Feature Cards](#patternfeature-cards)
8. [Flow Diagrams](#flow-diagrams)
9. [Permission/Config Badges](#permissionconfig-badges)
10. [Glossary Tooltips](#glossary-tooltips)
11. [Visual File Tree](#visual-file-tree)
12. [Icon-Label Rows](#icon-label-rows)
13. [Numbered Step Cards](#numbered-step-cards)

---

## Code ↔ English Translation Blocks

The most important teaching element. Shows real code from the project on the left and a plain English translation on the right, line by line.

**HTML:**
```html
<div class="translation-block animate-in">
  <div class="translation-code">
    <span class="translation-label">CODE</span>
    <pre><code>
<span class="code-line"><span class="code-keyword">const</span> response = <span class="code-keyword">await</span> <span class="code-function">fetch</span>(url, {</span>
<span class="code-line">  <span class="code-property">method</span>: <span class="code-string">'POST'</span>,</span>
<span class="code-line">  <span class="code-property">headers</span>: { <span class="code-string">'Authorization'</span>: apiKey }</span>
<span class="code-line">});</span>
    </code></pre>
  </div>
  <div class="translation-english">
    <span class="translation-label">PLAIN ENGLISH</span>
    <div class="translation-lines">
      <p class="tl">Send a request to the URL and wait for a response...</p>
      <p class="tl">We're sending data (POST), not just asking for it (GET)...</p>
      <p class="tl">Include our API key so the server knows who we are...</p>
      <p class="tl">End of the request setup.</p>
    </div>
  </div>
</div>
```

**CSS:**
```css
.translation-block {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0;
  border-radius: var(--radius-md);
  overflow: hidden;
  box-shadow: var(--shadow-md);
  margin: var(--space-8) 0;
}
.translation-code {
  background: var(--color-bg-code);
  color: #CDD6F4;
  padding: var(--space-6);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  line-height: 1.7;
  position: relative;
  overflow-x: hidden;  /* NO horizontal scrollbar — ever */
}
.translation-code pre,
.translation-code code {
  white-space: pre-wrap;       /* wrap long lines instead of scrolling */
  word-break: break-word;      /* break mid-word if needed */
  overflow-x: hidden;
}
.translation-english {
  background: var(--color-surface-warm);
  padding: var(--space-6);
  font-size: var(--text-sm);
  line-height: 1.7;
  border-left: 3px solid var(--color-accent);
}
.translation-label {
  position: absolute;
  top: var(--space-2);
  right: var(--space-3);
  font-size: var(--text-xs);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  opacity: 0.5;
}
.translation-english .translation-label {
  color: var(--color-text-muted);
}
/* Responsive: stack vertically on mobile */
@media (max-width: 768px) {
  .translation-block { grid-template-columns: 1fr; }
  .translation-english { border-left: none; border-top: 3px solid var(--color-accent); }
}
```

**Rules:**
- Each English line should correspond to 1-2 code lines
- Use conversational language, not technical jargon
- Highlight the "why" not just the "what" — e.g., "Include our API key so the server knows who we are" not "Set the Authorization header"

---

## Group Chat Animation

iMessage/WeChat-style chat showing components "talking" to each other. Messages appear one by one with typing indicators.

**Wiring:** `main.js` auto-initializes every `.chat-window` on page load. Give each chat window a unique `id`. Control buttons need these classes: `.chat-next-btn`, `.chat-all-btn`, `.chat-reset-btn`. The typing indicator avatar element should have `id="{chatWindowId}-typing-avatar"` or simply be the first `.chat-avatar` inside `.chat-typing`.

**HTML:**
```html
<div class="chat-window" id="chat-module2">
  <div class="chat-messages">
    <div class="chat-message" data-msg="0" data-sender="actor-a" style="display:none">
      <div class="chat-avatar" style="background: var(--color-actor-1)">A</div>
      <div class="chat-bubble">
        <span class="chat-sender" style="color: var(--color-actor-1)">Actor A</span>
        <p>Hey Background, I need the data for this item.</p>
      </div>
    </div>
    <!-- more messages... -->
  </div>

  <div class="chat-typing" id="chat-typing" style="display:none">
    <div class="chat-avatar" id="typing-avatar">?</div>
    <div class="chat-typing-dots">
      <span class="typing-dot"></span>
      <span class="typing-dot"></span>
      <span class="typing-dot"></span>
    </div>
  </div>

  <div class="chat-controls">
    <button class="btn chat-next-btn">Next Message</button>
    <button class="btn chat-all-btn">Play All</button>
    <button class="btn chat-reset-btn">Replay</button>
    <span class="chat-progress"></span>
  </div>
</div>
```

**CSS for typing dots:**
```css
.typing-dot {
  width: 8px; height: 8px; border-radius: 50%;
  background: var(--color-text-muted);
  animation: typingBounce 1.4s infinite;
}
.typing-dot:nth-child(2) { animation-delay: 0.2s; }
.typing-dot:nth-child(3) { animation-delay: 0.4s; }
@keyframes typingBounce {
  0%, 60%, 100% { transform: translateY(0); }
  30% { transform: translateY(-6px); }
}
```

---

## Message Flow / Data Flow Animation

Step-by-step visualization of data moving between components. User clicks "Next Step" to advance.

**Wiring:** `main.js` auto-initializes every `.flow-animation` on page load. Pass steps as JSON in `data-steps`. Each step object: `{ highlight: "flow-actor-id", label: "description", packet: true, from: "actor-id-suffix", to: "actor-id-suffix" }`. Actor element IDs must be `flow-actor-1`, `flow-actor-2`, etc. Control buttons need classes `.flow-next-btn` and `.flow-reset-btn`.

> **⚠️ Single quotes in step labels will break parsing.** The `data-steps` attribute is delimited by single quotes (`data-steps='[...]'`), so any single quote inside a label (e.g. `"the user's request"`) will terminate the attribute early and cause `JSON.parse` to fail silently — the entire animation will stop working. Either avoid apostrophes in labels, replace them with `&apos;`, or rewrite the attribute using double-quote delimiters with escaped inner quotes (`data-steps="[{\"label\":\"...\"}]"`).

**HTML:**
```html
<div class="flow-animation" data-steps='[
  {"highlight":"flow-actor-1","label":"User clicks the button"},
  {"highlight":"flow-actor-1","label":"Frontend sends request","packet":true,"from":"actor-1","to":"actor-2"},
  {"highlight":"flow-actor-2","label":"Backend calls the database","packet":true,"from":"actor-2","to":"actor-3"}
]'>
  <div class="flow-actors">
    <div class="flow-actor" id="flow-actor-1">
      <div class="flow-actor-icon">A</div>
      <span>Actor 1</span>
    </div>
    <div class="flow-actor" id="flow-actor-2">
      <div class="flow-actor-icon">B</div>
      <span>Actor 2</span>
    </div>
    <div class="flow-actor" id="flow-actor-3">
      <div class="flow-actor-icon">C</div>
      <span>Actor 3</span>
    </div>
  </div>

  <div class="flow-packet" id="flow-packet"></div>

  <div class="flow-step-label" id="flow-label">Click "Next Step" to begin</div>

  <div class="flow-controls">
    <button class="btn flow-next-btn">Next Step</button>
    <button class="btn flow-reset-btn">Restart</button>
    <span class="flow-progress"></span>
  </div>
</div>
```

**CSS for active actor glow:**
```css
.flow-actor.active {
  box-shadow: 0 0 0 3px var(--color-accent), 0 0 20px rgba(217, 79, 48, 0.2);
  transform: scale(1.05);
  transition: all var(--duration-normal) var(--ease-out);
}
```

---

## Interactive Architecture Diagram

Full-system diagram where hovering/clicking a component shows a description tooltip.

**HTML:**
```html
<div class="arch-diagram">
  <div class="arch-zone arch-zone-browser">
    <h4 class="arch-zone-label">Browser</h4>
    <div class="arch-component" data-desc="Injects UI into the web page, reads DOM, captures user actions"
         onclick="showArchDesc(this)">
      <div class="arch-icon">📄</div>
      <span>Component A</span>
    </div>
    <!-- more components -->
  </div>
  <div class="arch-zone arch-zone-external">
    <h4 class="arch-zone-label">External Services</h4>
    <!-- API cards -->
  </div>
  <div class="arch-description" id="arch-desc">Click any component to learn what it does</div>
</div>
```

---

## Layer Toggle Demo

Shows how different layers (e.g., HTML/CSS/JS, or data/logic/UI) build on each other. Three tabs switch between views.

**HTML:**
```html
<div class="layer-demo">
  <div class="layer-tabs">
    <button class="layer-tab active" onclick="showLayer('html')">HTML</button>
    <button class="layer-tab" onclick="showLayer('css')">+ CSS</button>
    <button class="layer-tab" onclick="showLayer('js')">+ JS</button>
  </div>
  <div class="layer-viewport">
    <div class="layer" id="layer-html" style="display:block">
      <!-- Raw unstyled version -->
    </div>
    <div class="layer" id="layer-css" style="display:none">
      <!-- Styled version -->
    </div>
    <div class="layer" id="layer-js" style="display:none">
      <!-- Interactive version -->
    </div>
  </div>
  <p class="layer-description" id="layer-desc">This is the raw HTML...</p>
</div>
```

---

## Callout Boxes

"Aha!" moments — universal CS insights. Max 2 per module.

```html
<div class="callout callout-accent">
  <div class="callout-icon">💡</div>
  <div class="callout-content">
    <strong class="callout-title">Key Insight</strong>
    <p>This pattern — splitting responsibilities into focused roles — is one of the most important ideas in software engineering. Engineers call it "separation of concerns."</p>
  </div>
</div>
```

**Variants:**
- `callout-accent`: vermillion left border, light accent background (for CS insights)
- `callout-info`: teal left border, light info background (for "good to know")
- `callout-warning`: red left border, light error background (for common mistakes)

---

## Pattern/Feature Cards

Grid of cards highlighting engineering patterns, tech stack components, or key concepts.

```html
<div class="pattern-cards">
  <div class="pattern-card" style="border-top: 3px solid var(--color-actor-1)">
    <div class="pattern-icon" style="background: var(--color-actor-1)">🔄</div>
    <h4 class="pattern-title">Caching</h4>
    <p class="pattern-desc">Store results to avoid redundant work — like keeping leftovers instead of cooking a new meal every time.</p>
  </div>
  <!-- more cards -->
</div>
```

```css
.pattern-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: var(--space-4);
}
.pattern-card {
  background: var(--color-surface);
  border-radius: var(--radius-md);
  padding: var(--space-6);
  box-shadow: var(--shadow-sm);
  transition: transform var(--duration-normal) var(--ease-out), box-shadow var(--duration-normal);
}
.pattern-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-md);
}
```

---

## Flow Diagrams

**Horizontal flow (desktop):**
```html
<div class="flow-steps">
  <div class="flow-step">
    <div class="flow-step-num">1</div>
    <p>User clicks button</p>
  </div>
  <div class="flow-arrow">→</div>
  <div class="flow-step">
    <div class="flow-step-num">2</div>
    <p>Component A detects click</p>
  </div>
  <div class="flow-arrow">→</div>
  <!-- more steps -->
</div>
```

Arrows rotate to `↓` on mobile via CSS transform.

---

## Permission/Config Badges

For annotating config files, permissions, or settings:

```html
<div class="badge-list">
  <div class="badge-item">
    <code class="badge-code">storage</code>
    <span class="badge-desc">Save data between sessions (like browser bookmarks)</span>
  </div>
  <div class="badge-item">
    <code class="badge-code">activeTab</code>
    <span class="badge-desc">Access the currently open tab (only when the user clicks)</span>
  </div>
</div>
```

```css
.badge-item {
  display: flex; align-items: center; gap: var(--space-4);
  padding: var(--space-3) var(--space-4);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
  transition: border-color var(--duration-fast);
}
.badge-item:hover { border-color: var(--color-accent-muted); }
.badge-code {
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  background: var(--color-bg-code);
  color: #CBA6F7;
  padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-sm);
  white-space: nowrap;
}
```

---

## Glossary Tooltips

The most important accessibility feature for non-technical learners. Any technical term in the course text should be wrapped in a tooltip that shows a plain-English definition on hover (desktop) or tap (mobile). The learner never has to leave the page or Google anything.

**HTML — mark up terms inline:**
```html
<p>The extension uses a
  <span class="term" data-definition="A service worker is a background script that runs independently of the web page — like a behind-the-scenes assistant that's always on, even when you're not looking at the page.">service worker</span>
  to handle API calls.
</p>
```

**CSS:**
```css
.term {
  border-bottom: 1.5px dashed var(--color-accent-muted);
  cursor: pointer;    /* NOT cursor: help — pointer feels clickable and inviting */
  position: relative;
}
.term:hover, .term.active {
  border-bottom-color: var(--color-accent);
  color: var(--color-accent);
}

/* The tooltip bubble — uses position: fixed and is appended to document.body
   via JS so it is NEVER clipped by ancestor overflow: hidden containers
   (like translation blocks). See JS section below for positioning logic. */
.term-tooltip {
  position: fixed;        /* CRITICAL: fixed, not absolute — prevents clipping */
  background: var(--color-bg-code);
  color: #CDD6F4;
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
  font-family: var(--font-body);
  line-height: var(--leading-normal);
  width: max(200px, min(320px, 80vw));
  box-shadow: var(--shadow-lg);
  pointer-events: none;
  opacity: 0;
  transition: opacity var(--duration-fast);
  z-index: 10000;        /* Above everything, including nav */
}
/* Arrow pointing down */
.term-tooltip::after {
  content: '';
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  border: 6px solid transparent;
  border-top-color: var(--color-bg-code);
}
.term-tooltip.visible {
  opacity: 1;
}

/* If tooltip goes off-screen top, flip to below */
.term-tooltip.flip {
  bottom: auto;
  top: calc(100% + 8px);
}
.term-tooltip.flip::after {
  top: auto;
  bottom: 100%;
  border-top-color: transparent;
  border-bottom-color: var(--color-bg-code);
}
```

**JS — position: fixed tooltips appended to body (never clipped by overflow):**
```javascript
// Tooltip container — appended to body so it's never clipped
let activeTooltip = null;

function positionTooltip(term, tip) {
  const rect = term.getBoundingClientRect();
  const tipWidth = 300; // approximate
  let left = rect.left + rect.width / 2 - tipWidth / 2;
  // Clamp to viewport
  left = Math.max(8, Math.min(left, window.innerWidth - tipWidth - 8));

  // Try above first
  let top = rect.top - 8;
  tip.style.left = left + 'px';

  // Position above by default, flip below if no room
  document.body.appendChild(tip);
  const tipHeight = tip.offsetHeight;
  if (rect.top - tipHeight - 8 < 0) {
    // Flip below
    tip.style.top = (rect.bottom + 8) + 'px';
    tip.classList.add('flip');
  } else {
    tip.style.top = (rect.top - tipHeight - 8) + 'px';
    tip.classList.remove('flip');
  }
}

document.querySelectorAll('.term').forEach(term => {
  const tip = document.createElement('span');
  tip.className = 'term-tooltip';
  tip.textContent = term.dataset.definition;

  // Hover for desktop
  term.addEventListener('mouseenter', () => {
    if (activeTooltip && activeTooltip !== tip) {
      activeTooltip.classList.remove('visible');
      activeTooltip.remove();
    }
    positionTooltip(term, tip);
    requestAnimationFrame(() => tip.classList.add('visible'));
    activeTooltip = tip;
  });

  term.addEventListener('mouseleave', () => {
    tip.classList.remove('visible');
    setTimeout(() => { if (!tip.classList.contains('visible')) tip.remove(); }, 150);
    activeTooltip = null;
  });

  // Tap for mobile
  term.addEventListener('click', (e) => {
    e.stopPropagation();
    if (activeTooltip && activeTooltip !== tip) {
      activeTooltip.classList.remove('visible');
      activeTooltip.remove();
    }
    if (tip.classList.contains('visible')) {
      tip.classList.remove('visible');
      tip.remove();
      activeTooltip = null;
    } else {
      positionTooltip(term, tip);
      requestAnimationFrame(() => tip.classList.add('visible'));
      activeTooltip = tip;
    }
  });
});

// Close tooltips when clicking elsewhere
document.addEventListener('click', () => {
  if (activeTooltip) {
    activeTooltip.classList.remove('visible');
    activeTooltip.remove();
    activeTooltip = null;
  }
});
```

**Rules:**
- Mark up EVERY technical term on first use in each module (API, DOM, callback, async, endpoint, middleware, etc.)
- Keep definitions to 1-2 sentences max, in everyday language
- Use a metaphor in the definition when it helps — e.g., "A **callback** is like leaving your phone number at a restaurant so they can call you when your table is ready"
- Don't mark the same term twice within the same screen — only on first appearance per module
- The dashed underline should be subtle enough not to distract but visible enough that curious learners discover it

---

## Visual File Tree

Use instead of paragraphs listing "this folder does X, that folder does Y." Much easier to scan.

```html
<div class="file-tree">
  <div class="ft-folder open">
    <span class="ft-name">app/</span>
    <span class="ft-desc">Pages and API routes</span>
    <div class="ft-children">
      <div class="ft-folder">
        <span class="ft-name">api/</span>
        <span class="ft-desc">Backend endpoints the frontend calls</span>
      </div>
      <div class="ft-file">
        <span class="ft-name">layout.tsx</span>
        <span class="ft-desc">The shell that wraps every page</span>
      </div>
    </div>
  </div>
  <div class="ft-folder">
    <span class="ft-name">components/</span>
    <span class="ft-desc">Reusable UI building blocks</span>
  </div>
  <div class="ft-folder">
    <span class="ft-name">lib/</span>
    <span class="ft-desc">Shared logic and utilities</span>
  </div>
</div>
```

```css
.file-tree { font-family: var(--font-mono); font-size: var(--text-sm); }
.ft-folder, .ft-file {
  padding: var(--space-2) var(--space-3);
  border-left: 2px solid var(--color-border-light);
  margin-left: var(--space-4);
}
.ft-folder > .ft-name { color: var(--color-accent); font-weight: 600; }
.ft-folder > .ft-name::before { content: '📁 '; }
.ft-file > .ft-name::before { content: '📄 '; }
.ft-desc {
  color: var(--color-text-secondary);
  font-family: var(--font-body);
  margin-left: var(--space-2);
  font-size: var(--text-xs);
}
.ft-children { margin-left: var(--space-4); }
```

---

## Icon-Label Rows

For listing components, features, or concepts visually. Replaces bullet-point paragraphs.

```html
<div class="icon-rows">
  <div class="icon-row">
    <div class="icon-circle" style="background: var(--color-actor-1)">🖥️</div>
    <div>
      <strong>Frontend (Next.js)</strong>
      <p>What the user sees and interacts with</p>
    </div>
  </div>
  <div class="icon-row">
    <div class="icon-circle" style="background: var(--color-actor-2)">⚡</div>
    <div>
      <strong>API Routes</strong>
      <p>Backend logic that runs on the server</p>
    </div>
  </div>
  <div class="icon-row">
    <div class="icon-circle" style="background: var(--color-actor-3)">🗄️</div>
    <div>
      <strong>Database (Supabase)</strong>
      <p>Where all the data is stored permanently</p>
    </div>
  </div>
</div>
```

```css
.icon-rows { display: flex; flex-direction: column; gap: var(--space-4); }
.icon-row {
  display: flex; align-items: center; gap: var(--space-4);
  padding: var(--space-4);
  background: var(--color-surface);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
}
.icon-row p { margin: 0; color: var(--color-text-secondary); font-size: var(--text-sm); }
.icon-circle {
  width: 48px; height: 48px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 1.25rem; flex-shrink: 0;
}
```

---

## Numbered Step Cards

For sequences that would otherwise be a numbered paragraph list. Visual, scannable, and each step stands alone.

```html
<div class="step-cards">
  <div class="step-card">
    <div class="step-num">1</div>
    <div class="step-body">
      <strong>User pastes a YouTube URL</strong>
      <p>The frontend captures the URL and extracts the video ID</p>
    </div>
  </div>
  <div class="step-card">
    <div class="step-num">2</div>
    <div class="step-body">
      <strong>API fetches the transcript</strong>
      <p>A server-side route calls an external service to get the video's text</p>
    </div>
  </div>
  <div class="step-card">
    <div class="step-num">3</div>
    <div class="step-body">
      <strong>AI analyzes the content</strong>
      <p>The transcript is sent to an AI model that extracts key moments</p>
    </div>
  </div>
</div>
```

```css
.step-cards { display: flex; flex-direction: column; gap: var(--space-3); }
.step-card {
  display: flex; align-items: flex-start; gap: var(--space-4);
  padding: var(--space-4) var(--space-5);
  background: var(--color-surface);
  border-radius: var(--radius-md);
  border-left: 3px solid var(--color-accent);
  box-shadow: var(--shadow-sm);
}
.step-num {
  width: 32px; height: 32px; border-radius: 50%;
  background: var(--color-accent);
  color: white; font-weight: 700;
  display: flex; align-items: center; justify-content: center;
  font-family: var(--font-display);
  flex-shrink: 0;
}
.step-body p { margin: var(--space-1) 0 0; color: var(--color-text-secondary); font-size: var(--text-sm); }
```
