#!/usr/bin/env python3
"""Slice a 4x4 CJK reference sheet, vectorize with vtracer, and build TTF/WOFF2 + HTML preview.

Uses proportional `keep_sheet_scale` so sparse glyphs (一, 二, 小, 口) retain
their natural optical scale instead of inflating to the full em box.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from pathlib import Path
import re
from statistics import median
from tempfile import TemporaryDirectory
from xml.etree import ElementTree

import numpy as np
from PIL import Image, ImageFont
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.svgLib.path import parse_path
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._c_m_a_p import CmapSubtable
import vtracer


def map_codepoint(font: TTFont, cp: int, gname: str) -> None:
    """Safely map BMP or SMP (>0xFFFF) codepoints without breaking format-4 subtables."""
    cmap_table = font["cmap"]
    if cp > 0xFFFF:
        has_f12 = any(sub.format == 12 and sub.isUnicode() for sub in cmap_table.tables)
        if not has_f12:
            base_map = dict(font.getBestCmap())
            for pid, eid in ((0, 4), (3, 10)):
                sub = CmapSubtable.newSubtable(12)
                sub.platformID = pid
                sub.platEncID = eid
                sub.language = 0
                sub.cmap = dict(base_map)
                cmap_table.tables.append(sub)
    for sub in cmap_table.tables:
        if not sub.isUnicode():
            continue
        if cp <= 0xFFFF or sub.format in (12, 13):
            sub.cmap[cp] = gname


def whitespace_edges(occupied: np.ndarray, fractions: list[float]) -> list[int]:
    extent = len(occupied)
    edges = [0]
    radius = max(12, round(extent / (len(fractions) + 1) * 0.31))
    for left, frac, right in zip([0.0] + fractions, fractions, fractions[1:] + [1.0]):
        guess = round(frac * extent)
        lo = max(edges[-1] + 8, guess - radius, round((left + frac) / 2 * extent))
        hi = min(extent - 8, guess + radius, round((right + frac) / 2 * extent))
        slots = [p for p in range(lo, hi + 1) if not occupied[max(0, p - 2) : p + 3].any()]
        if not slots:
            raise ValueError(f"No safe whitespace cut near pixel {guess} (range {lo}..{hi})")
        edges.append(min(slots, key=lambda p: abs(guess - p)))
    return edges + [extent]


def slice_sheet(image_path: Path, rows: list[str], threshold: int = 128) -> dict[str, Image.Image]:
    cols = len(rows[0])
    if not all(len(r) == cols for r in rows):
        raise ValueError("All rows must have the same number of characters")
    with Image.open(image_path) as img:
        mask = img.convert("L").point(lambda v: 255 if v < threshold else 0)
    y_edges = whitespace_edges(np.asarray(mask).any(axis=1), [i / len(rows) for i in range(1, len(rows))])
    cells: dict[str, Image.Image] = {}
    for r_idx, row_str in enumerate(rows):
        strip = mask.crop((0, y_edges[r_idx], mask.width, y_edges[r_idx + 1]))
        x_edges = whitespace_edges(np.asarray(strip).any(axis=0), [i / cols for i in range(1, cols)])
        for c_idx, ch in enumerate(row_str):
            cell = strip.crop((x_edges[c_idx], 0, x_edges[c_idx + 1], strip.height))
            bbox = cell.getbbox()
            if not bbox:
                raise ValueError(f"Empty cell for character '{ch}' at row {r_idx+1} col {c_idx+1}")
            cells[ch] = cell.crop(bbox)
    return cells


def vectorize_glyph(ink: Image.Image, sheet_scale: float | None = None, target_w: int = 875, target_h: int = 814, center_y: int = 380, advance: int = 1000):
    padded = Image.new("RGBA", (ink.width + 8, ink.height + 8), "white")
    padded.paste((0, 0, 0, 255), (4, 4, 4 + ink.width, 4 + ink.height), ink)
    svg = vtracer.convert_pixels_to_svg(
        list(padded.get_flattened_data()),
        padded.size,
        colormode="binary",
        mode="spline",
        filter_speckle=2,
        corner_threshold=55,
        length_threshold=3.8,
        splice_threshold=38,
        path_precision=4,
    )
    if sheet_scale is not None:
        sx = sy = sheet_scale
    else:
        sx = target_w / ink.width
        sy = target_h / ink.height
        sx = min(sx, sy * 1.07)
        sy = min(sy, sx * 1.07)

    pen = TTGlyphPen(None)
    quad = Cu2QuPen(pen, max_err=0.65)
    center_x = advance / 2
    for path in ElementTree.fromstring(svg).iter("{http://www.w3.org/2000/svg}path"):
        transform = path.get("transform", "translate(0,0)")
        m = re.fullmatch(r"translate\(([-.\d]+),\s*([-.\d]+)\)", transform)
        if not m:
            raise ValueError(f"Unsupported SVG transform: {transform}")
        tx, ty = map(float, m.groups())
        mapped = TransformPen(
            quad,
            (
                sx, 0, 0, -sy,
                center_x - (ink.width * sx / 2) + (tx - 4) * sx,
                center_y + (ink.height * sy / 2) - (ty - 4) * sy,
            ),
        )
        parse_path(path.attrib["d"], mapped)
    glyph = pen.glyph()
    glyph.recalcBounds(None)
    if glyph.numberOfContours <= 0:
        raise ValueError("Vectorization produced zero contours")
    return glyph, advance


def create_seed_font(path: Path, family: str) -> None:
    builder = FontBuilder(1000, isTTF=True)
    glyphs = {name: TTGlyphPen(None).glyph() for name in (".notdef", "space")}
    builder.setupGlyphOrder(list(glyphs))
    builder.setupCharacterMap({0x20: "space"})
    builder.setupGlyf(glyphs)
    builder.setupHorizontalMetrics({".notdef": (1000, 0), "space": (500, 0)})
    builder.setupHorizontalHeader(ascent=900, descent=-180)
    builder.setupNameTable({"familyName": family, "styleName": "Regular"})
    builder.setupOS2(sTypoAscender=900, sTypoDescender=-180, usWinAscent=900, usWinDescent=180)
    builder.setupPost()
    builder.save(path)


def preserve_dependents(glyf, hmtx, target_names: set[str]) -> None:
    """Keep existing composite glyphs intact when replacing a component glyph."""
    referenced = {
        part.glyphName
        for name in glyf.keys()
        if glyf[name].isComposite()
        for part in glyf[name].components
    }
    aliases: dict[str, str] = {}
    for name in sorted(target_names & referenced):
        alias = f"{name}.orig"
        while alias in glyf:
            alias += "_"
        aliases[name] = alias
        glyf[alias] = deepcopy(glyf[name])
        hmtx[alias] = hmtx[name]
    if aliases:
        for name in glyf.keys():
            g = glyf[name]
            if g.isComposite():
                for part in g.components:
                    part.glyphName = aliases.get(part.glyphName, part.glyphName)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", type=Path, required=True, help="Input 4x4 PNG/JPG reference sheet")
    parser.add_argument("--rows", required=True, help="Comma-separated row strings, e.g. '家步行水,复天于而,片下从不,之君其直'")
    parser.add_argument("--skip", default="", help="Characters to exclude from tracing (e.g. held typos or pad chars)")
    parser.add_argument("--baseline", type=Path, help="Optional baseline TTF to update; creates standalone seed TTF if omitted")
    parser.add_argument("--out-dir", type=Path, required=True, help="Output directory for TTF, WOFF2, and HTML proof")
    parser.add_argument("--family", required=True, help="Font family / output stem name")
    parser.add_argument("--keep-sheet-scale", action="store_true", help="Use one uniform scale across the whole sheet (recommended)")
    parser.add_argument("--target-height", type=int, default=814, help="Reference em height for sheet median glyph")
    args = parser.parse_args()

    rows = [r.strip() for r in args.rows.split(",") if r.strip()]
    skip_set = set(args.skip)
    cells = slice_sheet(args.image, rows)

    sheet_scale: float | None = None
    if args.keep_sheet_scale:
        heights = [im.height for im in cells.values()]
        widths = [im.width for im in cells.values()]
        sheet_scale = min(args.target_height / median(heights), 875 / median(widths))

    args.out_dir.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=args.out_dir) as tmp:
        tmp_path = Path(tmp)
        base_ttf = args.baseline
        if base_ttf is None:
            base_ttf = tmp_path / "seed.ttf"
            create_seed_font(base_ttf, args.family)

        with TTFont(base_ttf) as font:
            cmap = font.getBestCmap()
            glyf = font["glyf"]
            hmtx = font["hmtx"]
            order = list(font.getGlyphOrder())

            active = [c for r in rows for c in r if c not in skip_set]
            existing_targets = {cmap[ord(c)] for c in active if ord(c) in cmap}
            preserve_dependents(glyf, hmtx, existing_targets)

            for ch in active:
                glyph, adv = vectorize_glyph(cells[ch], sheet_scale=sheet_scale)
                cp = ord(ch)
                if cp in cmap:
                    gname = cmap[cp]
                else:
                    gname = f"uni{cp:04X}" if cp <= 0xFFFF else f"u{cp:X}"
                    if gname not in order:
                        order.append(gname)
                    map_codepoint(font, cp, gname)
                glyf[gname] = glyph
                hmtx[gname] = (adv, glyph.xMin)
                print(f"  {ch} (U+{cp:04X}): bounds=({glyph.xMin},{glyph.yMin},{glyph.xMax},{glyph.yMax}) contours={glyph.numberOfContours}")

            font.setGlyphOrder(order)
            for item in list(font["name"].names):
                if item.nameID in {1, 3, 4, 6, 16}:
                    font["name"].setName(args.family, item.nameID, item.platformID, item.platEncID, item.langID)

            out_ttf = args.out_dir / f"{args.family}.ttf"
            out_woff = args.out_dir / f"{args.family}.woff2"
            font.save(out_ttf)
            font.flavor = "woff2"
            font.save(out_woff)

        # Verify non-empty rasterization at 32/64/96px
        for px in (32, 64, 96):
            face = ImageFont.truetype(str(out_ttf), px)
            for ch in active:
                if not face.getmask(ch).getbbox():
                    raise RuntimeError(f"Glyph '{ch}' rendered empty at {px}px")

    # Emit standalone HTML proof
    spans = "".join(f'<span class="{"held" if c in skip_set else ""}">{c}</span>' for r in rows for c in r)
    rel_img = args.image.name if args.image.parent.resolve() == args.out_dir.resolve() else args.image.as_uri()
    html = (
        f'<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>{args.family}</title>'
        f'<style>@font-face{{font-family:F;src:url("{args.family}.woff2")}}'
        f'body{{font:15px/1.6 system-ui,sans-serif;background:#f7f4ee;padding:24px;color:#221c16}}'
        f'.grid{{display:grid;grid-template-columns:repeat({len(rows[0])},110px);gap:10px;background:#fff;padding:16px;width:fit-content;border:1px solid #dfd4c2}}'
        f'.grid span{{font:78px/1.2 F;text-align:center}}.held{{opacity:.28}}</style>'
        f'<h1>{args.family} ({len(active)}/{sum(len(r) for r in rows)} traced)</h1>'
        f'<div class="grid">{spans}</div>'
        f'<p><img src="{rel_img}" width="460" style="border:1px solid #dfd4c2"></p></html>'
    )
    (args.out_dir / f"{args.family}-preview.html").write_text(html, encoding="utf-8")
    print(f"Done: {out_ttf}, {out_woff}")


if __name__ == "__main__":
    main()
