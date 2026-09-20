# Campaign Architecture

The full suite: four skills that build a TTRPG campaign from geopolitics
down to atomic encounters, each layer feeding the next. The design is
documented in [the Candyland monograph](docs/monograph-candyland-framework.md).

## The layers

| # | Skill | Scale | What it produces |
|---|-------|-------|------------------|
| 1 | `skills/schelling-campaign-map` | macro | The Diplomacy Map: a Voronoi point-crawl of regions, supply centers, and faction claims, with a typed movement graph G=(V, E_A, E_F, E_C) |
| 2 | `skills/campaign-matrix` | meso | The Campaign Matrix: 5 quests × 5 beats dealt round-robin onto supply centers ranked by land-adjacency degree, so the best-connected centers recur as hubs |
| 3 | `skills/five-room-dungeon` | site | The Five-Room Dungeon: each matrix cell fleshed out as Entrance & Guardian → Puzzle or Trap → Setback → Climax → Reward & Revelation |
| 4 | `skills/nouns-directory` | atomic | The Nouns Directory: every canonical person, place, and thing, plus the encounter formula — sensory detail, rewards & risks, and mandatory outbound hooks |

## The Strategic-Narrative Intersection

The three middle layers meet at one concept: the **Strategic-Narrative
Intersection** (an "Adventure Location") — a single site that is simultaneously
a military resource on the Diplomacy map, a reusable narrative stage in the
Campaign Matrix, and a five-room dungeon on the inside. The where, the when,
and the walk-through.

- The map skill makes it a supply center: strategically valuable, contested.
- The matrix skill makes it a hub: several cells, each a *reason to be a place
  and time* — an event at that location, not just the location.
- The dungeon skill makes it explorable: five rooms with a spent state, because
  at a hub the party comes back.
- The nouns skill finds them: any noun serving two or more quest contexts is
  an intersection of Destiny and matter — prep those hardest.

Aim for on the order of fifteen per campaign. See
[the guide](docs/strategic-narrative-intersection.md).

## The pipeline

```
map graph ──▶ matrix (quests bound to centers)
                  │
                  ▼
        dungeon per center (five-room-dungeon)
                  │
                  ▼
        nouns directory (canonical names, encounters, hooks)
                  │
                  ▼
        conjunctions: nouns serving 2+ quest contexts
```

Each skill is usable standalone, but they share contracts:

- The map skill emits the typed graph JSON; the matrix skill reads it and
  writes `matrix_cells` / `dungeon_template` bindings back onto the nodes.
- The dungeon skill reads a matrix JSON (`--from-matrix`) and generates the
  dungeon for one center, pre-bound to its quest step.
- The nouns skill is the single source of truth for names: deal matrix steps
  onto places registered there, and every encounter must carry at least one
  hook to a registered noun.

Every skill ships an executable verification gate (`--verify` / `audit`).
Detection proposes; verification decides.

## Layout

```
campaign-architecture/
  README.md
  docs/
    monograph-candyland-framework.md       # the design document
    strategic-narrative-intersection.md    # the unifying concept
  skills/
    schelling-campaign-map/
    campaign-matrix/
    five-room-dungeon/
    nouns-directory/
  bin/sync-from-live.sh                   # re-sync skills/ from live skill dirs
```

## Development

The skills are developed in their live directories (`~/workspace/skills/<name>`)
and synced here with `bin/sync-from-live.sh` before release. The skills are
also published individually; this repo is the integrated suite.
