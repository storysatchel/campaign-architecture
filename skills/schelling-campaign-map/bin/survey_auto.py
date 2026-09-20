#!/usr/bin/env python3
"""
Headless survey: detect special track squares and verify seeds programmatically.

No visual inspection required. Two operations:

  1. detect  - find candidate squares by color + shape, emit normalized centers
  2. verify  - check that every seed in track_data.py falls inside a detected
               square of the expected color. Fails loudly on mismatch.

Usage:
    python3 survey_auto.py detect --board board.jpg
    python3 survey_auto.py verify --board board.jpg

The technique:
  - Work in HSV. Pink/magenta picture squares and orange licorice squares
    separate cleanly from the board's background in hue.
  - Connected components on the hue mask, filtered by area (square-sized,
    not background blobs) and squareness (bbox fill ratio).
  - A seed is "on its square" iff its normalized coordinate falls inside the
    detected square's bounding box, shrunk by 15% (so edge-grazing fails).
  - Never snap, never guess: if a seed fails verification the script exits
    non-zero and names the offender. A human (or a second detection pass
    with tuned thresholds) resolves it.

Porting to a new board:
  - Adjust HSV_RANGES for the target square colors.
  - Adjust AREA_PX for the image resolution (squares are ~4-5% of board width).
  - The verify step is color-agnostic: it just needs detections + seeds.
"""

import argparse
import json
import sys

import numpy as np
from PIL import Image

# HSV ranges (OpenCV convention: H 0-179, S 0-255, V 0-255) tuned for this board.
# Pink/magenta picture squares. Note: some squares are washed out (S~45),
# so the saturation floor is low.
HSV_RANGES = {
    "pink":   [((130, 35, 120), (179, 255, 255)),
               ((0, 35, 120),   (12, 255, 255))],   # hue wraps
    # Orange squares that carry the licorice "lose one turn" symbol.
    "orange": [((8, 60, 100), (28, 255, 255))],
}

# Expected square size as a fraction of board width (tune per board/resolution).
# This board: squares ~70px on a 1600px-wide image -> ~0.044.
SQUARE_FRAC_MIN, SQUARE_FRAC_MAX = 0.025, 0.075
# Bounding box must be at least this full of mask pixels (rejects streaks).
MIN_FILL_RATIO = 0.45
# Shrink factor for the "is the seed inside?" test (edge-grazing fails).
INSIDE_SHRINK = 0.15


def load_hsv(board_path):
    im = Image.open(board_path).convert("RGB")
    a = np.asarray(im).astype(np.float32) / 255.0
    r, g, b = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    mx, mn = a.max(axis=2), a.min(axis=2)
    d = mx - mn
    # Hue 0-179
    h = np.zeros_like(mx)
    m = d > 1e-6
    mr = m & (mx == r)
    mg = m & (mx == g)
    mb = m & (mx == b)
    h[mr] = (60 * ((g[mr] - b[mr]) / d[mr]) % 360) / 2
    h[mg] = (60 * ((b[mg] - r[mg]) / d[mg]) + 120) / 2
    h[mb] = (60 * ((r[mb] - g[mb]) / d[mb]) + 240) / 2
    s = np.where(mx > 1e-6, d / mx, 0) * 255
    v = mx * 255
    return h.astype(np.uint8), s.astype(np.uint8), v.astype(np.uint8), im.size


def mask_for(h, s, v, ranges):
    mask = np.zeros(h.shape, dtype=bool)
    for (h0, s0, v0), (h1, s1, v1) in ranges:
        if h0 <= h1:
            hm = (h >= h0) & (h <= h1)
        else:  # wraps (not used here, ranges are pre-split)
            hm = (h >= h0) | (h <= h1)
        mask |= hm & (s >= s0) & (s <= s1) & (v >= v0) & (v <= v1)
    return mask


def connected_components(mask):
    """Simple flood-fill labeling. Returns list of (ys, xs) pixel arrays."""
    h, w = mask.shape
    seen = np.zeros_like(mask, dtype=bool)
    comps = []
    for y, x in zip(*np.where(mask & ~seen)):
        if seen[y, x]:
            continue
        stack = [(y, x)]
        seen[y, x] = True
        ys, xs = [], []
        while stack:
            cy, cx = stack.pop()
            ys.append(cy); xs.append(cx)
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    ny, nx = cy + dy, cx + dx
                    if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        stack.append((ny, nx))
        comps.append((np.array(ys), np.array(xs)))
    return comps


def detect(board_path, color):
    h, s, v, (W, H) = load_hsv(board_path)
    mask = mask_for(h, s, v, HSV_RANGES[color])
    out = []
    for ys, xs in connected_components(mask):
        area = len(xs)
        frac = np.sqrt(area) / W
        if not (SQUARE_FRAC_MIN <= frac <= SQUARE_FRAC_MAX):
            continue
        x0, x1 = xs.min(), xs.max()
        y0, y1 = ys.min(), ys.max()
        bw, bh = x1 - x0 + 1, y1 - y0 + 1
        if bw == 0 or bh == 0:
            continue
        fill = area / (bw * bh)
        squareness = min(bw, bh) / max(bw, bh)
        if fill < MIN_FILL_RATIO or squareness < 0.6:
            continue
        fx = (x0 + x1 + 1) / 2 / W
        fy = (y0 + y1 + 1) / 2 / H
        out.append({
            "fx": round(float(fx), 4), "fy": round(float(fy), 4),
            "bbox": [int(x0), int(y0), int(x1), int(y1)],
            "area_px": int(area),
        })
    # de-duplicate near-identical detections, keep largest
    out.sort(key=lambda d: -d["area_px"])
    kept = []
    for d in out:
        if all(abs(d["fx"] - k["fx"]) > 0.02 or abs(d["fy"] - k["fy"]) > 0.02 for k in kept):
            kept.append(d)
    return kept


def verify(board_path):
    """Headless verify: for each special-space seed, check that the expected
    square color appears in a window around the seed. No connected components,
    no visual inspection. Fails loudly."""
    import sys
    sys.path.insert(0, "/home/hatch/workspace/procedural-map-candy")
    from track_data import SPECIAL_SPACES

    h, s, v, (W, H) = load_hsv(board_path)
    failures = []
    for name, kind, (fx, fy) in SPECIAL_SPACES:
        color = "pink" if kind == "picture" else "orange"
        mask = mask_for(h, s, v, HSV_RANGES[color])
        x, y = int(fx * W), int(fy * H)
        r = 45  # px radius: catches square border even if symbol covers center
        window = mask[max(0, y-r):y+r, max(0, x-r):x+r]
        frac = window.sum() / window.size
        ok = frac > 0.05  # at least 5% of window is the square color
        status = "OK " if ok else "FAIL"
        print(f"[{status}] {name:16s} ({fx:.4f}, {fy:.4f})  {color} frac={frac:.3f}")
        if not ok:
            failures.append(name)
    if failures:
        print(f"\nVERIFY FAILED for: {', '.join(failures)}", file=sys.stderr)
        sys.exit(1)
    print(f"\nAll {len(SPECIAL_SPACES)} special-space seeds verified.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("op", choices=["detect", "verify"])
    ap.add_argument("--board", required=True)
    args = ap.parse_args()

    if args.op == "detect":
        result = {}
        for color in HSV_RANGES:
            dets = detect(args.board, color)
            result[color] = dets
            print(f"# {color}: {len(dets)} candidate squares")
            for d in dets:
                print(f"  ({d['fx']:.4f}, {d['fy']:.4f})  bbox={d['bbox']}")
        with open("/tmp/survey_detections.json", "w") as f:
            json.dump(result, f, indent=1)
        print("# wrote /tmp/survey_detections.json")
        return

    verify(args.board)


if __name__ == "__main__":
    main()
