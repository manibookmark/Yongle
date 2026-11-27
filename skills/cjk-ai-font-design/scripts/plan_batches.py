#!/usr/bin/env python3
"""Plan density-balanced 4x4 (16-glyph) batches for CJK AI font generation.

Interleaves medium/dense characters with sparse characters (2+2 per row) so
image models maintain steady calligraphic weight instead of drifting on
all-sparse sheets.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont


def load_repertoire(path: Path) -> list[str]:
    """Read characters from either a U+XXXX list (one per line) or plain UTF-8 text."""
    text = path.read_text(encoding="utf-8-sig")
    chars: list[str] = []
    seen: set[str] = set()
    for line in text.splitlines():
        token = line.strip()
        if not token or token.startswith("#"):
            continue
        if token.upper().startswith("U+"):
            ch = chr(int(token[2:], 16))
            if ch not in seen and 0x3400 <= ord(ch) <= 0x9FFF:
                seen.add(ch)
                chars.append(ch)
        else:
            for ch in token:
                if ch not in seen and 0x3400 <= ord(ch) <= 0x9FFF:
                    seen.add(ch)
                    chars.append(ch)
    return chars


def ink_density(font: ImageFont.FreeTypeFont, ch: str) -> float:
    img = Image.new("L", (128, 128), 255)
    ImageDraw.Draw(img).text((16, 16), ch, fill=0, font=font)
    arr = np.asarray(img) < 128
    return float(arr.mean())


def load_excluded(path: Path | None) -> set[str]:
    if not path or not path.is_file():
        return set()
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    excluded: set[str] = set()
    for item in data.get("approved_custom_batches", []):
        excluded.update(item.get("approved_chars", ""))
    for item in data.get("completed_chars", []):
        excluded.update(item)
    return excluded


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repertoire", type=Path, required=True, help="U+XXXX per line or plain text Hanzi list")
    parser.add_argument("--ref-font", type=Path, required=True, help="Reference TTF/TTC used to estimate ink density")
    parser.add_argument("--exclude-file", type=Path, help="Optional plain text file of characters to skip")
    parser.add_argument("--exclude-json", type=Path, help="Optional approved_batches.json to skip already done chars")
    parser.add_argument("--pad-chars", default="人膏日旧羽目肇大同哥十誓骨小国警", help="Master chars to pad final partial batch to 16")
    parser.add_argument("--start-batch", type=int, default=1, help="Starting batch number")
    parser.add_argument("--out", type=Path, required=True, help="Output JSON batch plan path")
    args = parser.parse_args()

    chars = load_repertoire(args.repertoire)
    excluded = load_excluded(args.exclude_json)
    if args.exclude_file and args.exclude_file.is_file():
        excluded.update(load_repertoire(args.exclude_file))

    todo = [c for c in chars if c not in excluded]
    if not todo:
        print("No remaining characters to plan.")
        args.out.write_text("{}", encoding="utf-8")
        return

    font = ImageFont.truetype(str(args.ref_font), 96)
    scored = sorted(todo, key=lambda c: ink_density(font, c))

    # Pad to a multiple of 16 so every board is a full 4x4 grid (padded chars go in skip during tracing)
    rem = len(scored) % 16
    pad_used: list[str] = []
    if rem:
        need = 16 - rem
        for c in args.pad_chars:
            if c not in set(scored) and c not in pad_used:
                pad_used.append(c)
                if len(pad_used) == need:
                    break
        scored.extend(pad_used)

    n_batches = len(scored) // 16
    half = len(scored) // 2
    sparse_pool = scored[:half]
    dense_pool = scored[half:]

    plan: dict[str, dict] = {}
    for i in range(n_batches):
        s = sparse_pool[i * 8 : (i + 1) * 8]
        d = dense_pool[i * 8 : (i + 1) * 8]
        rows = [d[r * 2] + s[r * 2] + d[r * 2 + 1] + s[r * 2 + 1] for r in range(4)]
        skip_pad = "".join(c for c in "".join(rows) if c in pad_used)
        entry: dict = {"rows": rows}
        if skip_pad:
            entry["pad_skip"] = skip_pad
        plan[str(args.start_batch + i)] = entry

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Planned {len(todo)} target chars (+ {len(pad_used)} pad chars) into {n_batches} full 4x4 batches -> {args.out}")


if __name__ == "__main__":
    main()
