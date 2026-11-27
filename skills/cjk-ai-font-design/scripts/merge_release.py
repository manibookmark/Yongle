#!/usr/bin/env python3
"""Whitelist-protected CJK font release merger and full-repertoire integrity verifier.

Merges only explicitly approved batches (and targeted override repair batches)
onto a frozen baseline TTF, verifies bit-exact TTF/WOFF2 parity and 24/48/96px
rendering, and emits a before/after horizontal comparison HTML page.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path

from PIL import ImageFont
from fontTools.ttLib import TTFont

from trace_batch import map_codepoint, preserve_dependents


def is_cjk_ideograph(cp: int) -> bool:
    return (0x3400 <= cp <= 0x9FFF) or (0xF900 <= cp <= 0xFAFF) or (0x20000 <= cp <= 0x323AF)


def glyph_signature(font: TTFont, cp: int):
    name = font.getBestCmap().get(cp)
    if name is None:
        return None
    glyf = font["glyf"]
    coords, ends, flags = glyf[name].getCoordinates(glyf)
    return (tuple((int(x), int(y)) for x, y in coords), tuple(ends), bytes(flags))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True, help="Frozen baseline TTF (never modified in-place)")
    parser.add_argument("--approval", type=Path, required=True, help="JSON whitelist specifying approved & override batches")
    parser.add_argument("--out-dir", type=Path, required=True, help="Release output directory")
    parser.add_argument("--family", required=True, help="Output font family name (e.g. MyFont-SCCommon)")
    args = parser.parse_args()

    manifest = json.loads(args.approval.read_text(encoding="utf-8-sig"))
    rejected = set(manifest.get("rejected_batches", []))
    root = args.approval.parent

    # Collect approved glyph sources: char -> Path(ttf)
    sources: dict[str, Path] = {}
    for entry in manifest.get("approved_batches", []):
        name = entry["name"]
        if name in rejected:
            raise ValueError(f"Batch '{name}' is in both approved_batches and rejected_batches")
        ttf = Path(entry["ttf"])
        if not ttf.is_absolute():
            ttf = (root / ttf).resolve()
        for ch in entry["chars"]:
            if ch in sources:
                raise ValueError(f"Duplicate approved char '{ch}' in batch '{name}'")
            sources[ch] = ttf

    # Apply explicit override repair batches (allowed to overwrite earlier approved glyphs)
    for entry in manifest.get("override_batches", []):
        ttf = Path(entry["ttf"])
        if not ttf.is_absolute():
            ttf = (root / ttf).resolve()
        for ch in entry["chars"]:
            sources[ch] = ttf

    if not sources:
        raise ValueError("Approval whitelist contains zero approved glyphs")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    out_ttf = args.out_dir / f"{args.family}.ttf"
    out_woff = args.out_dir / f"{args.family}.woff2"

    with TTFont(args.baseline, checkChecksums=2) as font:
        cmap = font.getBestCmap()
        glyf = font["glyf"]
        hmtx = font["hmtx"]
        order = list(font.getGlyphOrder())
        preserve_dependents(glyf, hmtx, {cmap[ord(c)] for c in sources if ord(c) in cmap})

        by_ttf: dict[Path, list[str]] = {}
        for ch, path in sources.items():
            by_ttf.setdefault(path, []).append(ch)

        for path, chars in by_ttf.items():
            with TTFont(path, checkChecksums=2) as src:
                scmap = src.getBestCmap()
                for ch in chars:
                    cp = ord(ch)
                    if cp not in scmap:
                        raise KeyError(f"Char '{ch}' (U+{cp:04X}) missing in {path}")
                    g = deepcopy(src["glyf"][scmap[cp]])
                    if g.isComposite():
                        raise ValueError(f"Composite glyph not allowed for '{ch}' from {path}")
                    if cp in cmap:
                        key = cmap[cp]
                        adv = hmtx[key][0]
                    else:
                        key = f"uni{cp:04X}" if cp <= 0xFFFF else f"u{cp:X}"
                        if key not in order:
                            order.append(key)
                        map_codepoint(font, cp, key)
                        adv = src["hmtx"][scmap[cp]][0]
                    glyf[key] = g
                    hmtx[key] = (adv, g.xMin)

        font.setGlyphOrder(order)
        for item in list(font["name"].names):
            if item.nameID in {1, 3, 4, 6, 16}:
                font["name"].setName(args.family, item.nameID, item.platformID, item.platEncID, item.langID)
        font.recalcTimestamp = False
        font.save(out_ttf)
        font.flavor = "woff2"
        font.save(out_woff)

    # Full binary & raster integrity verification
    with TTFont(out_ttf, checkChecksums=2) as new, TTFont(out_woff, checkChecksums=2) as web:
        ncmap = new.getBestCmap()
        assert ncmap == web.getBestCmap(), "TTF and WOFF2 cmap mismatch"
        for cp, key in ncmap.items():
            assert glyph_signature(new, cp) == glyph_signature(web, cp), f"Outline mismatch U+{cp:04X}"
            assert new["hmtx"][key] == web["hmtx"][key], f"Metrics mismatch U+{cp:04X}"

    hanzi = [chr(cp) for cp in ncmap if is_cjk_ideograph(cp)]
    for px in (24, 48, 96):
        face = ImageFont.truetype(str(out_ttf), px)
        empty = [c for c in hanzi if not face.getmask(c).getbbox()]
        if empty:
            raise RuntimeError(f"Empty raster glyphs at {px}px: {''.join(empty[:10])}")

    # Emit before/after horizontal comparison HTML
    sample = "".join(sorted(sources, key=ord)[:120])
    html = (
        f'<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>{args.family} Comparison</title>'
        f'<style>@font-face{{font-family:Old;src:url("{args.baseline.as_uri()}")}}'
        f'@font-face{{font-family:New;src:url("{args.family}.woff2")}}'
        f'body{{max-width:1320px;margin:24px auto;padding:0 18px;background:#f4efe6;font:15px/1.6 system-ui}}'
        f'.cols{{display:grid;grid-template-columns:1fr 1fr;gap:18px}}.card{{background:#fffdf8;padding:18px;border:1px solid #dfd4c2;border-radius:8px}}'
        f'.old{{font-family:Old}}.new{{font-family:New}}.t32{{font-size:30px;line-height:1.75;word-break:break-all}}</style>'
        f'<h1>{args.family} Release Comparison ({len(sources)} merged glyphs)</h1>'
        f'<div class="cols"><div class="card"><h2>Baseline</h2><div class="old t32">{sample}</div></div>'
        f'<div class="card"><h2>Release</h2><div class="new t32">{sample}</div></div></div></html>'
    )
    (args.out_dir / f"{args.family}-comparison.html").write_text(html, encoding="utf-8")
    print(f"VERIFIED & BUILT: {out_ttf} & {out_woff} ({len(ncmap)} total codepoints, {len(sources)} merged glyphs)")


if __name__ == "__main__":
    main()
