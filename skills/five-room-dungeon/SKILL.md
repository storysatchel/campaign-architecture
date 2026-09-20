---
name: "five-room-dungeon"
description: "Build a five-room dungeon: the modular adventure block of the campaign-architecture suite. Fixed five-room shape (Entrance & Guardian, Puzzle or Trap, Setback, Climax, Reward & Revelation) reskinned to a theme, prepared as beads on a string — deploy in any order at the table. Binds to a campaign-matrix cell when given one."
metadata: { "includeInPrompt": false }
---

# Five-Room Dungeon

The modular unit of campaign architecture. One dungeon fleshes out one
matrix cell (or stands alone as a single-site adventure). The shape is fixed;
the deployment is not.

## The five rooms

1. **Entrance & Guardian** — the threshold and what bars it. States the
   dungeon's terms: what it costs to enter.
2. **Puzzle or Trap** — tests wit or caution. No guardian here; the place
   itself resists.
3. **Setback** — the reversal. The easy path collapses, the map was wrong,
   the ally falters. The room most dungeons skip, and the one that earns the
   climax.
4. **Climax** — the true encounter, the location's focal point. Force, not wit.
5. **Reward & Revelation** — the prize *and* the secret it carries. The reward
   must hook elsewhere (see the nouns-directory skill's encounter formula) or
   the dungeon is a dead end.

## The string-of-beads rule

Prepare the rooms as beads on a string, then ball it up and knot it at the
table: players may hit the rooms in any order, skip one, or trigger two at
once. So no room may assume another was visited. Each room states its own
stakes; cross-room continuity lives in the hooks, not in a sequence.

## Workflow

### 1. Take the theme (and the binding, if any)

A dungeon needs a theme — one line, a promise of content ("Cistern of mirrored
water, reflections arrive late"). If it serves a matrix step, take the binding
too: quest, step, beat, action verb. The beat tells you which room carries the
weight (a Climax-beat step lives in room 4; a Reversal-beat step wants room 3).

### 2. Generate the brief

    python3 bin/dungeon.py --theme "Cistern of mirrored water" --name cistern --out <dir>

    # bound to a matrix cell:
    python3 bin/dungeon.py --from-matrix <dir>/<name>-matrix.json --center <center-id> \
        --out <dir>

Outputs `<name>-dungeon.md` (the brief: five rooms, each with Purpose /
Challenge / Twist / Hooks, theme-derived scaffolding plus author slots) and
`<name>-dungeon.json` (the structured version, same schema the matrix skill
emits for `dungeon_template`).

### 3. Verify

`python3 bin/dungeon.py --verify <name>-dungeon.json` exits non-zero unless
all five slots are present, each has a purpose and a challenge, room 3 is a
genuine setback (not a second guardian), and room 5 carries at least one
outbound hook.

## Operating rules

1. The five slots are fixed and in this order on the page; the *play* order is
   free. Never write "after room 2" — write what the room is.
2. Room 3 must reverse something — a collapsed path, a false assumption, a
   cost. If it reads like another fight, it's wrong.
3. Room 5's revelation must point outside the dungeon. A reward with no hook
   is a dead end; the matrix starves.
4. Reskin freely, never reorder, never add a sixth room. If the site needs
   more, it needs a second dungeon.
