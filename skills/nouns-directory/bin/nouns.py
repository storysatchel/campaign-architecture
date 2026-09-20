#!/usr/bin/env python3
"""nouns-directory: the campaign's canonical persons, places, and things.

One JSON store per campaign (<db>/nouns.json). Encounters carry the four
components: sensory details, rewards, risks, hooks. The audit gate fails
hookless encounters and dangling references; `conjunctions` surfaces nouns
reused across quest contexts.

  python3 bin/nouns.py --db <dir> add place "Coco Loft" --desc "..."
  python3 bin/nouns.py --db <dir> encounter "The Night Audit" --at "Coco Loft" \
      --senses "..." --rewards "a;b" --risks "a;b" --hook "text -> Target"
  python3 bin/nouns.py --db <dir> link "Coco Loft" "Q1" --relation stage-of
  python3 bin/nouns.py --db <dir> conjunctions
  python3 bin/nouns.py --db <dir> audit
"""
import argparse
import json
import os
import sys

KINDS = ("person", "place", "thing", "faction", "encounter")


def load(db):
    os.makedirs(db, exist_ok=True)
    path = os.path.join(db, "nouns.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f), path
    return {"nouns": {}, "links": []}, path


def save(store, path):
    with open(path, "w") as f:
        json.dump(store, f, indent=1)


def parse_hook(spec):
    if "->" not in spec:
        sys.exit(f"hook must be 'text -> Target noun': {spec!r}")
    text, target = (p.strip() for p in spec.split("->", 1))
    if not text or not target:
        sys.exit(f"hook needs both text and target: {spec!r}")
    return {"text": text, "target": target}


def cmd_add(args, store):
    if args.kind not in KINDS:
        sys.exit(f"kind must be one of {KINDS}")
    nouns = store["nouns"]
    if args.name in nouns:
        sys.exit(f"noun {args.name!r} already registered (use --aka, not a second entry)")
    nouns[args.name] = {"kind": args.kind, "desc": args.desc or "",
                        "aka": args.aka or []}
    print(f"registered {args.kind} {args.name!r}")


def cmd_encounter(args, store):
    nouns = store["nouns"]
    if args.name in nouns:
        sys.exit(f"noun {args.name!r} already registered")
    if args.at not in nouns:
        sys.exit(f"location {args.at!r} is not a registered noun — add it first")
    nouns[args.name] = {
        "kind": "encounter",
        "desc": args.desc or "",
        "aka": [],
        "at": args.at,
        "senses": args.senses or "",
        "rewards": [r.strip() for r in (args.rewards or "").split(";") if r.strip()],
        "risks": [r.strip() for r in (args.risks or "").split(";") if r.strip()],
        "hooks": [parse_hook(h) for h in args.hook or []],
    }
    print(f"registered encounter {args.name!r} at {args.at!r}")


def cmd_link(args, store):
    for n in (args.a, args.b):
        if n not in store["nouns"] and not n.startswith("Q"):
            print(f"warning: {n!r} is not a registered noun", file=sys.stderr)
    store["links"].append({"a": args.a, "b": args.b,
                           "relation": args.relation or "related"})
    print(f"linked {args.a!r} --[{args.relation}]--> {args.b!r}")


def cmd_conjunctions(args, store):
    contexts = {}
    for l in store["links"]:
        if l["relation"] == "stage-of":
            contexts.setdefault(l["a"], set()).add(l["b"])
    found = False
    for noun, ctxs in sorted(contexts.items(), key=lambda kv: -len(kv[1])):
        if len(ctxs) >= 2:
            found = True
            print(f"{noun}: {', '.join(sorted(ctxs))}")
    if not found:
        print("no conjunctions yet — no noun serves 2+ quest contexts")


def cmd_audit(args, store):
    errors = []
    nouns = store["nouns"]
    for name, n in nouns.items():
        if n["kind"] != "encounter":
            continue
        if not n.get("senses"):
            errors.append(f"encounter {name!r}: no sensory details")
        if not n.get("rewards"):
            errors.append(f"encounter {name!r}: no rewards")
        if not n.get("risks"):
            errors.append(f"encounter {name!r}: no risks")
        if not n.get("hooks"):
            errors.append(f"encounter {name!r}: no hooks — every encounter must hook elsewhere")
        for h in n.get("hooks", []):
            if h["target"] not in nouns:
                errors.append(f"encounter {name!r}: hook target {h['target']!r} is not a registered noun")
        if n.get("at") not in nouns:
            errors.append(f"encounter {name!r}: location {n.get('at')!r} undefined")
    if errors:
        print("FAIL:")
        for e in errors:
            print(" -", e)
        sys.exit(1)
    n_enc = sum(1 for n in nouns.values() if n["kind"] == "encounter")
    print(f"OK: {len(nouns)} nouns, {n_enc} encounters, all hooked and referenced")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=".", help="campaign db dir (holds nouns.json)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("add")
    p.add_argument("kind", help=f"one of {KINDS}")
    p.add_argument("name")
    p.add_argument("--desc", default="")
    p.add_argument("--aka", action="append", default=[])

    p = sub.add_parser("encounter")
    p.add_argument("name")
    p.add_argument("--at", required=True, help="registered place noun")
    p.add_argument("--desc", default="")
    p.add_argument("--senses", default="")
    p.add_argument("--rewards", default="", help="';'-separated")
    p.add_argument("--risks", default="", help="';'-separated")
    p.add_argument("--hook", action="append", default=[],
                   help="'text -> Target noun', repeatable")

    p = sub.add_parser("link")
    p.add_argument("a")
    p.add_argument("b")
    p.add_argument("--relation", default="related")

    sub.add_parser("conjunctions")
    sub.add_parser("audit")
    args = ap.parse_args()

    store, path = load(args.db)
    {"add": cmd_add, "encounter": cmd_encounter, "link": cmd_link,
     "conjunctions": cmd_conjunctions, "audit": cmd_audit}[args.cmd](args, store)
    if args.cmd in ("add", "encounter", "link"):
        save(store, path)


if __name__ == "__main__":
    main()
