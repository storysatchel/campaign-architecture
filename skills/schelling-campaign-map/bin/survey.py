#!/usr/bin/env python3
"""Schelling-point survey helper.

Implements the measure-and-verify loop from the schelling-campaign-map skill:
crop tight around a candidate point, measure its center, then overlay ALL
points on the board image and look before committing.

Usage:
    python3 survey.py crop BOARD FX FY --size 200 --out /tmp/crop.png
    python3 survey.py overlay BOARD --point "Name,fx,fy,color" ... --out /tmp/check.png
    python3 survey.py verify BOARD DATA.py   # overlay every point in a survey module
"""

import argparse
import importlib.util
import sys

import numpy as np
from PIL import Image


def load_board(path):
    im = Image.open(path).convert("RGB")
    return im, np.array(im)


def crop(board_path, fx, fy, size=200, out="/tmp/survey_crop.png"):
    """Crop a size×size px box around normalized point (fx, fy)."""
    im, _ = load_board(board_path)
    w, h = im.size
    cx, cy = fx * w, fy * h
    box = (int(cx - size // 2), int(cy - size // 2),
           int(cx + size // 2), int(cy + size // 2))
    c = im.crop(box)
    scale = max(1, 400 // size)
    c.resize((c.width * scale, c.height * scale), Image.LANCZOS).save(out)
    print(f"crop {out}: center board-px ({cx:.0f},{cy:.0f})")


def overlay(board_path, points, out="/tmp/survey_overlay.png"):
    """Plot (name, fx, fy, color) points on the board for visual verification."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    im, _ = load_board(board_path)
    w, h = im.size
    fig, ax = plt.subplots(figsize=(16, 16 * h / w))
    ax.imshow(im, extent=[0, 1, 0, 1], origin="upper")
    for name, fx, fy, color in points:
        ax.plot(fx, fy, "o", ms=10, mfc=color, mec="black", mew=1.5)
        ax.text(fx, fy - 0.018, name, ha="center", va="top", fontsize=7,
                color="white", weight="bold",
                bbox=dict(fc="black", ec="none", alpha=0.7, pad=1.5))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    fig.savefig(out, dpi=110, bbox_inches="tight")
    print(f"overlay {out}: {len(points)} points — LOOK at it before committing")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("crop", help="crop around a normalized point")
    c.add_argument("board")
    c.add_argument("fx", type=float)
    c.add_argument("fy", type=float)
    c.add_argument("--size", type=int, default=200)
    c.add_argument("--out", default="/tmp/survey_crop.png")

    o = sub.add_parser("overlay", help="plot points on the board")
    o.add_argument("board")
    o.add_argument("--point", action="append", default=[],
                   help='"Name,fx,fy,color" (repeatable)')
    o.add_argument("--out", default="/tmp/survey_overlay.png")

    args = ap.parse_args()
    if args.cmd == "crop":
        crop(args.board, args.fx, args.fy, args.size, args.out)
    elif args.cmd == "overlay":
        pts = []
        for p in args.point:
            name, fx, fy, color = p.split(",")
            pts.append((name, float(fx), float(fy), color))
        overlay(args.board, pts, args.out)


if __name__ == "__main__":
    main()
