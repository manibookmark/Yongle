#!/usr/bin/env python3
"""Audit CJK candidate font glyphs against a standard reference font.

Capabilities:
1. Structural typo detection (enclosed hole count + dilated ink mismatch)
   with side-by-side contact sheets ([Standard Gray | Candidate Black]).
2. Stroke-width weight distribution monitoring via Euclidean distance transform.
3. Structure-strip generator (--make-structure-ref) for dual-reference repair.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
import statistics

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage


def load_chars(chars_arg: str | None, chars_file: Path | None) -> list[str]:
    raw = chars_arg or ""
    if chars_file:
        raw += "\n" + chars_file.read_text(encoding="utf-8-sig")
    out, seen = [], set()
    for line in raw.splitlines():
        tok = line.strip()
        if not tok or tok.startswith("#"):
            continue
        if tok.upper().startswith("U+"):
            c = chr(int(tok[2:], 16))
            if c not in seen and 0x3400 <= ord(c) <= 0x9FFF:
                seen.add(c); out.append(c)
        else:
            for c in tok:
                if c not in seen and 0x3400 <= ord(c) <= 0x9FFF:
                    seen.add(c); out.append(c)
    return out


def analyze_glyph(font: ImageFont.FreeTypeFont, ch: str, px: int = 128):
    img = Image.new("L", (px * 2, px * 2), 255)
    ImageDraw.Draw(img).text((px // 2, px // 2), ch, fill=0, font=font)
    arr = np.asarray(img) < 128
    ys, xs = np.where(arr)
    if len(xs) == 0:
        return np.zeros((96, 96), dtype=bool), 0, 0, 0.0

    # Stroke width estimate in 1000-em units using distance transform on full-res bitmap
    dt = ndimage.distance_transform_edt(arr)
    # Local ridge proxy: top 60% of foreground distance pixels * 2
    vals = dt[arr]
    stroke_w = float(np.percentile(vals, 75) * 2.0 * (1000.0 / px)) if len(vals) else 0.0

    crop = Image.fromarray((arr[ys.min() : ys.max() + 1, xs.min() : xs.max() + 1] * 255).astype(np.uint8))
    crop.thumbnail((88, 88), Image.Resampling.BILINEAR)
    canvas = Image.new("L", (96, 96), 0)
    canvas.paste(crop, ((96 - crop.width) // 2, (96 - crop.height) // 2))
    bw = np.asarray(canvas) > 96

    lbl, n_fg = ndimage.label(bw)
    fg_sizes = ndimage.sum(bw, lbl, range(1, n_fg + 1)) if n_fg else []
    comps = int(np.sum(np.asarray(fg_sizes) >= 6)) if n_fg else 0

    inv = ~bw
    blbl, n_bg = ndimage.label(inv)
    border = set(blbl[0, :]) | set(blbl[-1, :]) | set(blbl[:, 0]) | set(blbl[:, -1])
    holes = sum(1 for lid in range(1, n_bg + 1) if lid not in border and int(np.sum(blbl == lid)) >= 8)
    return bw, comps, holes, stroke_w


def make_structure_ref(chars: str, ref_font: Path, out_path: Path) -> None:
    chars = "".join(c for c in chars if 0x3400 <= ord(c) <= 0x9FFF)
    if not chars:
        raise ValueError("No valid CJK characters given for --make-structure-ref")
    step = 160
    im = Image.new("RGB", (len(chars) * step + 40, 210), (255, 255, 255))
    dr = ImageDraw.Draw(im)
    font = ImageFont.truetype(str(ref_font), 140)
    for i, c in enumerate(chars):
        dr.text((20 + i * step, 26), c, fill=(0, 0, 0), font=font)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    im.save(out_path)
    print(f"Saved standard structure reference strip ({len(chars)} chars) -> {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--font", type=Path, help="Candidate TTF/OTF to audit")
    parser.add_argument("--ref-font", type=Path, required=True, help="Standard reference font (e.g. simkai.ttf)")
    parser.add_argument("--chars", help="Inline characters to audit")
    parser.add_argument("--chars-file", type=Path, help="File listing characters (plain text or U+XXXX)")
    parser.add_argument("--out-dir", type=Path, required=True, help="Output directory for CSV & contact sheets")
    parser.add_argument("--top-n", type=int, default=160, help="Number of highest-suspicion glyphs to render")
    parser.add_argument("--make-structure-ref", help="Generate a crisp standard-font reference strip for dual-ref repair")
    args = parser.parse_args()

    if args.make_structure_ref:
        make_structure_ref(args.make_structure_ref, args.ref_font, args.out_dir / "structure_ref.png")
        return

    if not args.font:
        parser.error("--font is required unless --make-structure-ref is used")

    chars = load_chars(args.chars, args.chars_file)
    if not chars:
        raise ValueError("No characters to audit; pass --chars or --chars-file")

    f_cand = ImageFont.truetype(str(args.font), 128)
    f_ref = ImageFont.truetype(str(args.ref_font), 128)

    rows = []
    widths = []
    for ch in chars:
        a, fa, ha, sw = analyze_glyph(f_cand, ch)
        b, fb, hb, _ = analyze_glyph(f_ref, ch)
        a_d = ndimage.binary_dilation(a, iterations=2)
        b_d = ndimage.binary_dilation(b, iterations=2)
        miss = float(np.logical_and(b, ~a_d).sum() / max(1, b.sum()))
        extra = float(np.logical_and(a, ~b_d).sum() / max(1, a.sum()))
        score = (miss + extra) * 2.0 + abs(ha - hb) * 0.35 + max(0, abs(fa - fb) - 1) * 0.12
        rows.append((score, miss, extra, ha, hb, fa, fb, round(sw, 1), ch))
        if sw > 0:
            widths.append(sw)

    rows.sort(reverse=True)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = args.out_dir / "typo_audit.csv"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["字", "码位", "疑错分", "漏墨率", "多墨率", "候选孔洞", "标准孔洞", "候选连通数", "标准连通数", "估算笔宽"])
        for s, m, e, ha, hb, fa, fb, sw, ch in rows:
            w.writerow([ch, f"U+{ord(ch):04X}", f"{s:.3f}", f"{m:.3f}", f"{e:.3f}", ha, hb, fa, fb, sw])

    print(f"Audited {len(rows)} glyphs -> {csv_path}")
    if widths:
        print(f"Estimated stroke width median={statistics.median(widths):.1f} (p10={np.percentile(widths,10):.1f}, p90={np.percentile(widths,90):.1f})")

    # Render side-by-side contact sheets for top suspicious glyphs (80 per page, 62px glyphs)
    fk = ImageFont.truetype(str(args.ref_font), 62)
    fv = ImageFont.truetype(str(args.font), 62)
    try:
        ui = ImageFont.truetype("msyh.ttc", 18)
        sm = ImageFont.truetype("msyh.ttc", 12)
    except OSError:
        ui = sm = ImageFont.load_default()

    top = rows[: min(args.top_n, len(rows))]
    per_page = 80
    for p_idx in range(0, len(top), per_page):
        chunk = top[p_idx : p_idx + per_page]
        cols, cw, ch_h = 8, 176, 108
        rn = (len(chunk) + cols - 1) // cols
        im = Image.new("RGB", (cols * cw + 32, rn * ch_h + 56), (250, 248, 242))
        dr = ImageDraw.Draw(im)
        dr.text((16, 14), f"Suspect Audit #{p_idx+1}-{p_idx+len(chunk)} (Gray=Ref, Black=Candidate, h=holes)", fill=(30, 25, 20), font=ui)
        for i, (s, _, _, ha, hb, _, _, sw, ch) in enumerate(chunk):
            rr, cc = divmod(i, cols)
            x, y = 16 + cc * cw, 48 + rr * ch_h
            dr.rectangle([x, y, x + cw - 6, y + ch_h - 6], fill=(255, 255, 255), outline=(210, 200, 190))
            dr.text((x + 8, y + 6), ch, fill=(135, 135, 135), font=fk)
            dr.text((x + 86, y + 6), ch, fill=(10, 10, 10), font=fv)
            dr.text((x + 8, y + 78), f"h:{ha}/{hb} s:{s:.2f} w:{sw:.0f}", fill=(160, 40, 30) if ha != hb else (85, 80, 75), font=sm)
        out_img = args.out_dir / f"suspect_page_{p_idx // per_page + 1}.png"
        im.save(out_img)
        print("Saved:", out_img)


if __name__ == "__main__":
    main()
