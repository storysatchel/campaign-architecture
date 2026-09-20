---
name: "nouns-directory"
description: "The campaign's canonical store of persons, places, and things, plus the encounter design formula. One source of truth for every noun; encounters carry sensory detail, rewards and risks, and mandatory outbound hooks. The audit gate fails encounters with no hooks and surfaces conjunctions — nouns reused across quest contexts, where plotlines collide."
metadata: { "includeInPrompt": false }
---

# Nouns Directory

The atomic layer of campaign architecture. Everything the campaign names —
every person, place, thing, faction, and encounter — lives here, once,
canonically. When the matrix reuses a location across two quests, the reuse
is visible here as two contexts on one noun. Those intersections are the
"conjunctions of Destiny": the places where plotlines collide and players
must choose.

## The encounter formula

Every encounter is built from the same four components:

1. **Sensory details** — sights, sounds, smells. Ground the scene.
2. **Rewards** — treasure, information, leverage. What the scene offers.
3. **Risks** — monsters or opponents, plus a trap or terrain feature. What the
   scene threatens. Environmental risk counts; a scene with only combat is
   half-built.
4. **Hooks (mandatory)** — plot or adventure hooks that lead elsewhere. Every
   encounter must have at least one, and critical information must be
   **repeated** across encounters — the party walks through a dense jungle of
   hooks and repeated clues, so nothing vital is missable. A hook names its
   target noun; a hook to nowhere is a dead end.

## Workflow

All state lives in `<db>/nouns.json` (one file per campaign).

### 1. Register nouns

    python3 bin/nouns.py --db <dir> add place "Coco Loft" --desc "Rooftop garden above the market"
    python3 bin/nouns.py --db <dir> add person "The Tallyman" --desc "Counts debts, collects in kind"

Kinds: `person`, `place`, `thing`, `faction`, `encounter`.

### 2. Build encounters

    python3 bin/nouns.py --db <dir> encounter "The Night Audit" --at "Coco Loft" \
        --senses "Rain on canvas, charcoal smoke, the Tallyman's abacus clicking" \
        --rewards "The drowned ledger; the Tallyman's favor" \
        --risks "The Tallyman's collectors; the rotten deck edge" \
        --hook "The ledger names a debtor in Q3 -> The Salt Rebellion" \
        --hook "A collector drops a token of the Ashen Compact -> The Ashen Compact"

`--hook` is repeatable and takes the form `"text -> Target noun"`.

### 3. Record reuse

When a noun serves two quest contexts, link it:

    python3 bin/nouns.py --db <dir> link "Coco Loft" "Q1" --relation stage-of
    python3 bin/nouns.py --db <dir> link "Coco Loft" "Q3" --relation stage-of

### 4. Audit (the gate)

    python3 bin/nouns.py --db <dir> audit

Exits non-zero unless: every encounter has senses, at least one reward, at
least one risk, and at least one hook; every hook target names a registered
noun; no noun is referenced but undefined.

### 5. Find conjunctions

    python3 bin/nouns.py --db <dir> conjunctions

Lists nouns bound to two or more quest contexts — the collision points. These
are where the campaign's plotlines intersect; prep them hardest.

## Operating rules

1. One canonical name per noun. Aliases go in `--aka`, never as second entries.
2. No encounter without a hook. No hook without a target. No target that
   isn't a registered noun.
3. Repeat critical clues across at least two encounters — the audit can't
   check this, so the author must.
4. The directory is written before the matrix is dealt, and read while the
   matrix is written: deal steps onto places that already exist here.
