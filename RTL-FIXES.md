# RTL Fixes for Hermes WebUI

This file documents all RTL-related fixes applied to the project.
Keep this as a reference for future maintenance.

## Final Fix (commit `85519611`) — `text-align` inline style via `renderMd()`

**Date**: 2026-06-12

**Problem**: Arabic text was left-aligned (LTR) in chat messages and tool cards.

**Root cause**: The CSS direction computed property used by `text-align:start` is affected by complex inheritance chains and BIDI specs. Every previous approach failed:

| Approach | Why it failed |
|----------|--------------|
| `dir="auto"` on `.msg-body` | Evaluated once at DOM insertion. During streaming, the element is empty — direction defaults to rtl inherited from `<html>`. Never re-evaluates. |
| `unicode-bidi: plaintext` CSS | Does NOT change CSS `direction` computed property (used by `text-align:start`). Only affects internal BIDI reordering. |
| `dir="rtl"`/`dir="ltr"` on `<p>` | Works for static content, but `text-align:start` still uses `direction` from CSS DOM cascade, not HTML dir attribute. Confusing spec interaction. |
| `_resolveAutoDir()` JS | Fragile timing — runs after DOM insertion but may miss elements swapped by `_preservedLiveTurn` pattern. |
| `requestAnimationFrame` | Race with `_preservedLiveTurn` swap and other DOM mutations. |

**Solution**: In `renderMd()` (`static/ui.js`, line ~3902), inspect each paragraph for Arabic Unicode characters and set an **inline `style` attribute**:

```javascript
// Before:
return `<p>${content}</p>`;

// After:
var hasArabic = /[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]/
  .test(content.replace(/<[^>]+>/g, ''));
if (hasArabic) {
  return '<p style="text-align:right">' + content + '</p>';
}
return '<p style="text-align:left">' + content + '</p>';
```

**Why inline style?** Inline styles have the highest CSS specificity (short of `!important`) and are NOT affected by:
- DOM inheritance chains
- `_preservedLiveTurn` segment swaps (the style travels with the HTML)
- Re-renders via `renderMessages()`
- Stream completion
- CSS direction computed property

**Result**: Arabic paragraphs → `text-align:right` ✅, English paragraphs → `text-align:left` ✅.

---

## Previous Attempt 1 — Remove CSS `direction` from tool cards

Removed `direction:ltr !important` from `.tool-call-group-summary` and `.tool-call-group-body .tool-call-group-summary` CSS blocks. These were overriding `dir="auto"` on tool card children with CSS `!important`.

**Files**: `static/style.css` (lines 5601-5607, 5740-5744)

---

## Previous Attempt 2 — Add `dir="auto"` to `.msg-body`

Added `dir="auto"` attribute to `.msg-body` in `renderMessages()` for both user (line ~8388) and assistant (line ~8450) message paths. Removed duplicate CSS block. Added `unicode-bidi:plaintext` fallback.

---

## Previous Attempt 3 — Add `dir="auto"` to `<p>` in `renderMd()`

Modified `renderMd()` to produce `<p dir="auto">...</p>` instead of bare `<p>`. Added `_resolveAutoDir()` JS calls. This failed because `dir="auto"` is evaluated once and `text-align:start` uses CSS direction, not HTML dir.

---

## Tool Cards still need `dir="auto"`

Tool cards (`.tool-card-detail`, `.tool-card-result`, `.tool-card-name`, `.tool-card-preview`) use `dir="auto"` HTML attribute set in their templates. These work for short labels. If Arabic tool card details appear LTR, verify:

1. CSS `.chat-content-rtl .tool-call-group-summary` does NOT have `direction:ltr !important` ✅
2. CSS `.chat-content-rtl .tool-call-group-body .tool-call-group-summary` does NOT have `direction:ltr !important` ✅
3. The element has `dir="auto"` in its HTML template

---

## CSS Classes with special RTL handling

| CSS Class | Purpose |
|-----------|---------|
| `.chat-content-rtl` | Root RTL container. Sets `direction:rtl`. |
| `.chat-content-rtl .msg-row` | Inherits direction from parent. |
| `.chat-content-rtl .msg-body` | `text-align:start` — okay because children have explicit inline style. |
| `.chat-content-rtl .msg-body > p, li, pre, h1-6, blockquote` | `unicode-bidi:plaintext` for BIDI ordering. Inline style from renderMd handles alignment. |
| `.chat-content-rtl .agent-activity-status-icon, .agent-activity-status-copy` | `unicode-bidi: plaintext; text-align: start` |
| `.chat-content-rtl .tool-call-group-label, .tool-call-group-duration` | `direction:ltr !important` — intentional (always English labels). |
| `.chat-content-rtl .msg-row[data-role="user"]` | `margin-left: auto` — floats right. |
| `.chat-content-rtl .msg-row[data-role="assistant"]` | `margin-right: auto` — floats left. |

---

## Unicode Arabic Blocks Used for Detection

```
\u0600-\u06FF  — Arabic
\u0750-\u077F  — Arabic Supplement
\u08A0-\u08FF  — Arabic Extended-A
\uFB50-\uFDFF  — Arabic Presentation Forms-A
\uFE70-\uFEFF  — Arabic Presentation Forms-B
```
