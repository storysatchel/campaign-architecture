#!/usr/bin/env python3
"""campaign-matrix: bind quests to supply centers.

Builds the 5x5 quest matrix (5 quests x 5 beats, dealt round-robin onto
supply centers ranked by land-adjacency degree) and a themed 5-room dungeon
per supply center. Reads the typed graph JSON from the schelling-campaign-map
skill, or a plain center/edge list.

Outputs:
  <out>/<name>-matrix.json   quests, bindings, dungeons (matches the map
                             skill's MatrixCellIntersection / FiveRoomDungeon
                             schema, ready to feed back into graph nodes)
  <out>/<name>-matrix.png    matrix table over dungeon table

  python3 bin/matrix.py --graph graph.json --quests "Q1;Q2;Q3;Q4;Q5" --out dir
  python3 bin/matrix.py --centers "A,B,C" --edges "A-B,B-C" --auto --out dir
  python3 bin/matrix.py --verify dir/<name>-matrix.json   (exit nonzero on failure)
"""
import argparse
import hashlib
import json
import os
import re
import sys

BEATS = ["1 Inciting", "2 Complication", "3 Reversal", "4 Crisis", "5 Climax"]
ROOMS = [
    ("room_1_guardian", "Entrance & Guardian"),
    ("room_2_puzzle_or_trap", "Puzzle or Trap"),
    ("room_3_trick_or_climax", "Setback"),
    ("room_4_climax_encounter", "Climax"),
    ("room_5_reward_or_revelation", "Reward & Revelation"),
]


def load_bank(path):
    """Parse references/theme-bank.md into {quests, verbs, themes}."""
    bank = {"quests": [], "verbs": [], "themes": []}
    section = None
    with open(path) as f:
        for line in f:
            line = line.rstrip()
            if line.startswith("## Quest titles"):
                section = "quests"
            elif line.startswith("## Step verbs"):
                section = "verbs"
            elif line.startswith("## Dungeon themes"):
                section = "themes"
            elif line.startswith("- ") and section:
                bank[section].append(line[2:].strip())
            elif section == "verbs" and line and not line.startswith("#"):
                bank[section].append(line.strip())
    if section == "verbs" and len(bank["verbs"]) == 1:
        bank["verbs"] = [v.strip() for v in bank["verbs"][0].split(",")]
    bank["verbs"] = [v for chunk in bank["verbs"]
                     for v in (c.strip() for c in chunk.split(",") if c.strip())]
    return bank


def centers_from_graph(payload):
    """(centers, degree) from a schelling-campaign-map graph JSON."""
    nodes = payload["nodes"]
    centers = [n for n in nodes.values()
               if n.get("is_supply_center") and not n.get("parent_province_id")]
    degree = {n["id"]: 0 for n in centers}
    ids = set(degree)
    for e in payload.get("army_edges", []):
        a, b = e["source_id"], e["target_id"]
        if a in ids and b in ids and a != b:
            degree[a] += 1
            degree[b] += 1
    info = {n["id"]: {"name": n.get("name", n["id"]),
                      "held_by": (n.get("controlling_faction_id")
                                  or n.get("home_power_id") or "Unheld")}
            for n in centers}
    return list(degree), degree, info


def centers_from_lists(names, edges):
    ids = [n.strip() for n in names.split(",") if n.strip()]
    degree = {i: 0 for i in ids}
    for e in (edges or "").split(","):
        e = e.strip()
        if "-" not in e:
            continue
        a, b = (p.strip() for p in e.split("-", 1))
        if a in degree and b in degree and a != b:
            degree[a] += 1
            degree[b] += 1
    info = {i: {"name": i, "held_by": "Unheld"} for i in ids}
    return ids, degree, info


def deal(centers, degree):
    ranked = sorted(centers, key=lambda i: (-degree[i], i))
    steps = [(q, s) for q in range(5) for s in range(5)]
    bindings = {i: [] for i in centers}
    for k, (q, s) in enumerate(steps):
        bindings[ranked[k % len(ranked)]].append((q, s))
    return ranked, bindings


def build(args, bank):
    if args.graph:
        with open(args.graph) as f:
            payload = json.load(f)
        centers, degree, info = centers_from_graph(payload)
    else:
        centers, degree, info = centers_from_lists(args.centers, args.edges)
    if len(centers) < 3:
        sys.exit("need at least 3 supply centers")
    ranked, deal_map = deal(centers, degree)

    if args.auto:
        quests = bank["quests"][:5]
    else:
        quests = [q.strip() for q in args.quests.split(";")]
    if len(quests) != 5 or any(not q for q in quests):
        sys.exit("--quests needs exactly 5 semicolon-separated titles (or --auto)")

    verbs = bank["verbs"] or ["Secure"]
    n_verbs = len(verbs)
    matrix = {"quests": quests, "beats": BEATS, "bindings": {}, "dungeons": {}}
    for ci in ranked:
        cells = []
        for (q, s) in sorted(deal_map[ci]):
            verb = verbs[(q * 5 + s) % n_verbs]
            cells.append({
                "quest_id": q + 1,
                "step_number": s + 1,
                "action_verb": verb,
                "narrative_summary": "",
                "quest_title": quests[q],
                "beat": BEATS[s],
            })
        matrix["bindings"][ci] = {
            "name": info[ci]["name"],
            "held_by": info[ci]["held_by"],
            "hub": len(cells) > 1,
            "cells": cells,
        }
    themes = args.themes or bank["themes"]
    for k, ci in enumerate(ranked):
        theme = themes[k % len(themes)] if themes else "Unthemed vault"
        matrix["dungeons"][ci] = {
            "name": info[ci]["name"],
            "held_by": info[ci]["held_by"],
            "theme": theme,
            "rooms": {key: f"{label} — {theme}" for key, label in ROOMS},
        }
    matrix["hubs"] = [ci for ci in ranked if matrix["bindings"][ci]["hub"]]
    return matrix, ranked


def write_json(matrix, out, name):
    path = os.path.join(out, f"{name}-matrix.json")
    with open(path, "w") as f:
        json.dump(matrix, f, indent=1)
    return path


def render(matrix, ranked, out, name):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    quests, beats = matrix["quests"], matrix["beats"]
    m = len(ranked)
    # Vertical budget in inches: title, matrix table, label, dungeon table, margin.
    mtx_h = 5 * 0.34 + 0.35
    dun_h = m * 0.27 + 0.35
    H = 1.0 + mtx_h + 0.55 + dun_h + 0.45
    fig = plt.figure(figsize=(13, H))

    def y_top(inches_from_top):
        return 1.0 - inches_from_top / H

    fig.suptitle(f"Quest Matrix & 5-Room Dungeons — {name}", fontsize=14,
                 weight="bold", y=y_top(0.35))
    fig.text(0.5, y_top(0.72),
             "Every step is bound to a supply center — entering its cell fires the step. "
             "Hubs (★) recur across quests.",
             ha="center", fontsize=10)

    # Matrix table: quests x beats
    ax1 = fig.add_axes([0.14, y_top(1.0 + mtx_h), 0.82, mtx_h / H])
    ax1.axis("off")
    cell_text = []
    for q in range(5):
        row = []
        for s in range(5):
            ci = ranked[(q * 5 + s) % m]
            b = matrix["bindings"][ci]
            row.append(b["name"] + (" ★" if b["hub"] else ""))
        cell_text.append(row)
    tab = ax1.table(cellText=cell_text,
                    rowLabels=[f"Q{q+1} · {t}" for q, t in enumerate(quests)],
                    colLabels=beats, loc="center", cellLoc="center")
    tab.auto_set_font_size(False)
    tab.set_fontsize(8)
    tab.scale(1, 1.8)

    # Dungeon table
    fig.text(0.5, y_top(1.0 + mtx_h + 0.32),
             "Supply-center dungeons — every center is a 5-room dungeon",
             ha="center", fontsize=10)
    ax2 = fig.add_axes([0.04, 0.45 / H, 0.92, dun_h / H])
    ax2.axis("off")
    drows = []
    for ci in ranked:
        b = matrix["bindings"][ci]
        d = matrix["dungeons"][ci]
        chips = ", ".join(f"Q{c['quest_id']}.{c['step_number']}"
                          for c in b["cells"]) or "—"
        drows.append([d["name"], d["held_by"], d["theme"], chips])
    tab2 = ax2.table(cellText=drows,
                     colLabels=["Center", "Held by", "Dungeon theme", "Matrix steps"],
                     colWidths=[0.22, 0.18, 0.40, 0.20],
                     loc="center", cellLoc="left")
    tab2.auto_set_font_size(False)
    tab2.set_fontsize(7.5)
    tab2.scale(1, 1.35)
    path = os.path.join(out, f"{name}-matrix.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def verify(matrix):
    errors = []
    bound = [(c["quest_id"], c["step_number"])
             for b in matrix["bindings"].values() for c in b["cells"]]
    if sorted(bound) != sorted((q + 1, s + 1) for q in range(5) for s in range(5)):
        errors.append("not all 25 steps bound exactly once")
    for ci, d in matrix["dungeons"].items():
        if set(d["rooms"]) != {key for key, _ in ROOMS}:
            errors.append(f"dungeon {ci}: rooms incomplete")
    if set(matrix["dungeons"]) != set(matrix["bindings"]):
        errors.append("center/dungeon sets differ")
    per_quest = {}
    for b in matrix["bindings"].values():
        for c in b["cells"]:
            per_quest.setdefault(c["quest_id"], set()).add(
                next(ci for ci, bb in matrix["bindings"].items()
                     if c in bb["cells"]))
    for q, centers in per_quest.items():
        if len(centers) < 3:
            errors.append(f"quest {q}: steps on only {len(centers)} centers")
    m = len(matrix["bindings"])
    if m < 25 and not matrix.get("hubs"):
        errors.append("no hubs formed though M < 25")
    return errors


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--graph", help="typed graph JSON from schelling-campaign-map")
    ap.add_argument("--centers", help='comma-separated center names (no graph)')
    ap.add_argument("--edges", default="", help='"A-B,B-C" adjacency (no graph)')
    ap.add_argument("--quests", default="", help='"Q1;Q2;Q3;Q4;Q5" titles')
    ap.add_argument("--auto", action="store_true", help="titles from theme bank")
    ap.add_argument("--themes", default="",
                    help="file with one dungeon theme per line")
    ap.add_argument("--bank", default=os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..",
        "references", "theme-bank.md"))
    ap.add_argument("--out", default=".")
    ap.add_argument("--name", default="campaign")
    ap.add_argument("--verify", help="verify a matrix JSON and exit")
    args = ap.parse_args()

    if args.verify:
        with open(args.verify) as f:
            matrix = json.load(f)
        errors = verify(matrix)
        if errors:
            print("FAIL:")
            for e in errors:
                print(" -", e)
            sys.exit(1)
        print(f"OK: {len(matrix['bindings'])} centers, "
              f"{len(matrix['hubs'])} hubs, 25 steps bound")
        return

    if not args.graph and not args.centers:
        sys.exit("need --graph or --centers")
    bank = load_bank(args.bank) if os.path.exists(args.bank) else \
        {"quests": [], "verbs": ["Secure"], "themes": []}
    themes = []
    if args.themes:
        with open(args.themes) as f:
            themes = [l.strip() for l in f if l.strip()]
    elif bank["themes"]:
        themes = bank["themes"]
    args.themes = themes

    matrix, ranked = build(args, bank)
    os.makedirs(args.out, exist_ok=True)
    jp = write_json(matrix, args.out, args.name)
    pp = render(matrix, ranked, args.out, args.name)
    errors = verify(matrix)
    print(f"wrote {jp}\nwrote {pp}")
    print(f"{len(ranked)} centers, {len(matrix['hubs'])} hubs")
    if errors:
        print("VERIFY FAIL:")
        for e in errors:
            print(" -", e)
        sys.exit(1)
    print("verify: OK")


if __name__ == "__main__":
    main()
