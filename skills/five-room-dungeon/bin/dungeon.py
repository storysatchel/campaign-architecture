#!/usr/bin/env python3
"""five-room-dungeon: build the modular adventure block.

Generates a five-room dungeon brief from a theme, optionally bound to a
campaign-matrix cell. Rooms are the fixed shape; deployment order at the
table is free (beads on a string).

  python3 bin/dungeon.py --theme "..." --name slug --out dir
  python3 bin/dungeon.py --from-matrix matrix.json --center <id> --out dir
  python3 bin/dungeon.py --verify slug-dungeon.json
"""
import argparse
import json
import os
import sys

ROOMS = [
    ("room_1_guardian", "Entrance & Guardian",
     "States the dungeon's terms: what it costs to enter, and what bars the way.",
     "AUTHOR: who or what guards the threshold, and what does it want?"),
    ("room_2_puzzle_or_trap", "Puzzle or Trap",
     "The place itself resists. Tests wit or caution, not force.",
     "AUTHOR: the mechanism, what triggers it, what it costs to misread."),
    ("room_3_trick_or_climax", "Setback",
     "The reversal: the easy path collapses, the map was wrong, the ally falters. "
     "Must reverse something — never a second guardian.",
     "AUTHOR: what breaks, what false assumption does it punish?"),
    ("room_4_climax_encounter", "Climax",
     "The true encounter, the location's focal point. Force, not wit.",
     "AUTHOR: the opposition, what winning costs, what losing costs."),
    ("room_5_reward_or_revelation", "Reward & Revelation",
     "The prize AND the secret it carries. The revelation must hook elsewhere — "
     "a reward with no hook is a dead end.",
     "AUTHOR: the reward, the revelation, and at least one outbound hook."),
]

BEAT_ROOM = {1: 1, 2: 2, 3: 3, 4: 4, 5: 4}  # which room carries a beat's weight


def brief(name, theme, binding):
    dungeon = {"name": name, "theme": theme, "binding": binding, "rooms": {}}
    for key, label, purpose, author in ROOMS:
        dungeon["rooms"][key] = {
            "label": label,
            "purpose": purpose,
            "seed": f"{label} — {theme}.",
            "challenge": author,
            "twist": "",
            "hooks": [],
        }
    if binding:
        step = binding.get("step_number")
        room_key = [k for k, _, _, _ in ROOMS][BEAT_ROOM.get(step, 1) - 1]
        dungeon["rooms"][room_key]["challenge"] += (
            f" This room carries the matrix beat "
            f"Q{binding['quest_id']}.{step} ({binding['beat']}, "
            f"{binding['action_verb']}: {binding['quest_title']}).")
    return dungeon


def to_markdown(d):
    L = [f"# {d['name']} — {d['theme']}", ""]
    if d["binding"]:
        b = d["binding"]
        L += [f"*Matrix binding: Q{b['quest_id']}.{b['step_number']} — "
              f"{b['quest_title']} ({b['beat']}, {b['action_verb']})*", ""]
    for key, label, _, _ in ROOMS:
        r = d["rooms"][key]
        L += [f"## Room {label}", "",
              f"**Purpose.** {r['purpose']}", "",
              f"**Seed.** {r['seed']}", "",
              f"**Challenge.** {r['challenge']}", ""]
        if r["twist"]:
            L += [f"**Twist.** {r['twist']}", ""]
        hooks = ", ".join(r["hooks"]) if r["hooks"] else "AUTHOR: hooks that lead elsewhere"
        L += [f"**Hooks.** {hooks}", ""]
    return "\n".join(L)


def verify(d):
    errors = []
    rooms = d.get("rooms", {})
    if [k for k, _, _, _ in ROOMS] != list(rooms):
        errors.append("rooms must be exactly the five slots in order")
        return errors
    for key, label, _, _ in ROOMS:
        r = rooms[key]
        if not r.get("purpose"):
            errors.append(f"{label}: no purpose")
        if not r.get("challenge"):
            errors.append(f"{label}: no challenge")
    r3 = rooms["room_3_trick_or_climax"]
    text = (r3.get("challenge", "") + r3.get("twist", "")).lower()
    if not any(w in text for w in ("collaps", "wrong", "break", "falter", "revers", "false", "cost", "trap")):
        errors.append("room 3 (Setback): no reversal language — must reverse something")
    r5 = rooms["room_5_reward_or_revelation"]
    if not r5.get("hooks"):
        errors.append("room 5 (Reward & Revelation): no outbound hooks")
    return errors


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--theme", default="")
    ap.add_argument("--from-matrix", default="")
    ap.add_argument("--center", default="")
    ap.add_argument("--name", default="")
    ap.add_argument("--out", default=".")
    ap.add_argument("--verify", default="")
    args = ap.parse_args()

    if args.verify:
        with open(args.verify) as f:
            d = json.load(f)
        errors = verify(d)
        if errors:
            print("FAIL:")
            for e in errors:
                print(" -", e)
            sys.exit(1)
        print(f"OK: {d['name']} — five rooms, setback reverses, room 5 hooks out")
        return

    binding = None
    theme = args.theme
    if args.from_matrix:
        with open(args.from_matrix) as f:
            m = json.load(f)
        if args.center not in m["bindings"]:
            sys.exit(f"center {args.center!r} not in matrix")
        b = m["bindings"][args.center]
        theme = m["dungeons"][args.center]["theme"]
        cell = b["cells"][0] if b["cells"] else None
        if cell:
            binding = {"quest_id": cell["quest_id"], "step_number": cell["step_number"],
                       "beat": cell["beat"], "action_verb": cell["action_verb"],
                       "quest_title": cell["quest_title"]}
    if not theme:
        sys.exit("need --theme or --from-matrix")
    name = args.name or "".join(c if c.isalnum() else "-" for c in theme.lower())[:40].strip("-")
    d = brief(name, theme, binding)
    os.makedirs(args.out, exist_ok=True)
    jp = os.path.join(args.out, f"{name}-dungeon.json")
    mp = os.path.join(args.out, f"{name}-dungeon.md")
    with open(jp, "w") as f:
        json.dump(d, f, indent=1)
    with open(mp, "w") as f:
        f.write(to_markdown(d))
    print(f"wrote {jp}\nwrote {mp}")
    print("note: Challenge/Twist/Hooks marked AUTHOR are yours to write; "
          "--verify checks structure, not prose")


if __name__ == "__main__":
    main()
