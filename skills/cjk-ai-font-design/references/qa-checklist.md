# 4-Gate CJK Font QA Checklist

A CJK font cannot be validated by automated metrics alone, nor by single-glyph zooming alone. Every batch and release must pass all four gates.

---

## Gate 1: Raw Sheet Visual Gate (Before Tracing)
- [ ] Pure white background, pure black strokes, clean 4×4 spacing with visible whitespace gutters between every row and column.
- [ ] Exact 16-character order matches the planned row list (no swapped cells, no duplicated characters).
- [ ] Every character preserves the style master's brush rhythm (no drift into modern digital KaiTi/Songti).
- [ ] Any character with missing strokes, extra strokes, merged counters, or traditional/simplified mixups is immediately listed in `--skip` (never traced into the batch font).

## Gate 2: Optical Weight & Scale Gate (Per Batch)
- [ ] Vectorized with `--keep-sheet-scale` so sparse glyphs (`一、二、小、口`) keep natural size proportions instead of inflating to the full em box.
- [ ] Batch median main stroke width stays within **±12%** of the style master's median (measured via distance transform in `scripts/audit_glyphs.py`).
- [ ] No contour self-intersections, zero empty outlines, and `advanceWidth` preserved consistently (`1000` for full-width Hanzi).

## Gate 3: Structural Typo Gate (Against Standard Reference Font)
- [ ] Run `scripts/audit_glyphs.py` comparing every newly added glyph against a standard reference font (`simkai.ttf`, Noto Serif CJK, etc.).
- [ ] Inspect the generated `[Standard Gray | New Black]` contact sheets at ≥60px, paying special attention to:
  - **Enclosed hole mismatches (`h:cand/ref`)**: catches missing inner bars in `目/直/真/算/置/矗`, missing inner box in `禀`, or missing strokes inside `凿/兜`.
  - **Missing dots / lookalike radicals**: catches `孵(卵→卯)`, `搀(毚→免)`, `啄/琢(豖→豕)`, `粱(米→木)`, `福/神/禅(礻→衤)`, `姊(右→市)`.
  - **Component placement errors**: catches complex characters like `赣` (`章` left, `攵` top-right, `贝` bottom-right).
- [ ] All flagged typos are routed to Dual-Reference Repair (`--make-structure-ref`) and merged via `override_batches`.

## Gate 4: Real Body-Text Horizontal & Vertical Rendering Gate (Release)
- [ ] Open the merged TTF/WOFF2 in `templates/specimen.html` and the before/after comparison page.
- [ ] Inspect mixed paragraphs containing **both** previously approved glyphs and newly added glyphs at **20px, 28px, 36px, and 64px**.
- [ ] Check four visual criteria in continuous reading:
  1. **Grey-value uniformity**: no newly added characters popping out as dark blotches or faint holes.
  2. **Baseline & optical center**: no characters jumping up/down or leaning off-axis.
  3. **Counter openness**: complex characters remain legible at 20–24px without plugging into black blobs.
  4. **Binary integrity**: `cmap` matches `repertoire.txt`, `TTF == WOFF2` outlines & metrics, all characters render non-empty at `24 / 48 / 96 px`.
