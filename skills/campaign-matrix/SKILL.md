---
name: "campaign-matrix"
description: "Generate the 5x5 quest matrix and 5-room dungeons for a campaign's supply centers: 5 quests x 5 steps dealt round-robin onto centers ranked by land-adjacency degree, one themed 5-room dungeon per center, bound so entering a cell exposes its dungeon and fires its matrix step. Reads the typed graph JSON emitted by the schelling-campaign-map skill."
metadata: { "includeInPrompt": false }
---

# Campaign Matrix

Bind quest content to geography. Given the supply centers of a campaign map (a
typed graph from the schelling-campaign-map skill, or a plain list), produce:

- **The 5×5 quest matrix** — 5 quests × 5 steps, every step bound to a supply
  center. Steps are dealt round-robin onto centers ranked by land-adjacency
  degree, so the best-connected centers recur across quests and become hubs.
- **A 5-room dungeon per supply center** — themed to the center, exposing when
  the party enters its cell.

## The structure

**Quest arc (fixed five beats).** Every quest runs the same arc:

1. Inciting — the hook that pulls the party in.
2. Complication — the plan meets the world.
3. Reversal — what they believed was wrong.
4. Crisis — the point of no return.
5. Climax — the quest resolves (or detonates).

**Step dealing.** Rank supply centers by E_A degree (land adjacency, descending;
ties broken by name for stability). Deal the 25 steps `(q, s)` round-robin onto
the ranking: `centers[k % M]`. A center hosting more than one step is a **hub** —
it recurs across quest lines, which is what makes the campaign feel like one
world instead of five errands. With M centers and 25 steps, hubs are guaranteed
whenever M < 25.

A hub is a **Strategic-Narrative Intersection** (an "Adventure Location"): one
site functioning simultaneously as a military resource on the Diplomacy map
and a reusable narrative stage in the matrix. Mount Doom hosting "Destroy the
Ring" in one quest and "Serve Tea" in another is the shape. Each bound step is
a *reason to be a place and time* — not just a location, but an event at that
location. Aim for on the order of fifteen such intersections per campaign; not
every supply center must host steps.

**The 5-room dungeon (fixed five rooms).** Every supply center gets one,
regardless of whether it hosts a matrix step:

1. Entrance & Guardian — what bars the way in.
2. Puzzle or Trap — what tests wit or caution.
3. Setback — the reversal: the easy path collapses.
4. Climax — the true encounter.
5. Reward & Revelation — the prize and the secret it carries.

Each dungeon is reskinned to a **theme** assigned per center (cycled from a
theme bank, in degree-rank order so the most-visited centers get the strongest
themes first).

**Binding rule.** Entering a supply center's cell exposes its dungeon and fires
its matrix step(s). The dungeon is the *where* of the step — the step's beat
plays out inside (or because of) the dungeon.

## Workflow

### 1. Take the centers

Preferred input: the graph JSON from `bin/graph_model.py`'s `to_json()` in the
schelling-campaign-map skill. Use parent provinces only (`parent_province_id`
empty, `is_supply_center` true) — coast subnodes never host steps or dungeons.

Without a graph: `bin/matrix.py --centers "Name A,Name B,..."` plus optional
`--edges "A-B,B-C,..."` for adjacency. Degree falls back to input order when no
edges are given.

### 2. Name the five quests

Pass `--quests "Q1 title;Q2 title;Q3 title;Q4 title;Q5 title"`. Titles are
authorial — they set the campaign's stakes. (Without them, `--auto` draws from
the fallback bank in `references/theme-bank.md`.)

### 3. Run the generator

    python3 bin/matrix.py --graph <graph.json> \
        --quests "Q1;Q2;Q3;Q4;Q5" \
        --themes references/theme-bank.md \
        --out <dir>

Outputs:

- `<dir>/<name>-matrix.json` — quests, per-center bindings, dungeons. Binding
  objects match the map skill's schema: `quest_id`, `step_number`,
  `action_verb`, `narrative_summary`; dungeons carry `room_1_guardian` through
  `room_5_reward_or_revelation`. Feed the bindings straight back into the
  graph nodes (`matrix_cells`, `dungeon_template`).
- `<dir>/<name>-matrix.png` — the matrix table (quests × steps, cells naming
  center and holder) above the dungeon table (center, held by, theme, steps).
  Pin this next to the campaign map.

### 4. Verify

`bin/matrix.py --verify <dir>/<name>-matrix.json` exits non-zero unless:

- all 25 steps are bound to supply centers;
- every supply center has a dungeon;
- no quest's 5 steps sit on fewer than 3 distinct centers (distribution);
- hub count ≥ 1 when M < 25.

## Operating rules

1. Never bind a step to a waypoint, wild, or coast subnode — supply centers only.
2. The arc beats and room slots are fixed; the *content* of each is where the
   writing happens. Don't invent a sixth beat.
3. Themes come from the bank or the author, in rank order — strongest themes on
   the highest-degree centers.
4. Quest titles are authorial input, not generated filler. Flag `--auto` output
   as provisional.

## Tooling

- `bin/matrix.py` — build + render + verify. See `--help`.
- `references/design.md` — why 5×5, why degree-ranked dealing, the hub argument.
- `references/theme-bank.md` — fallback quest titles and dungeon themes.
