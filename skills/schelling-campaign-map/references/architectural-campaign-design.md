# Architectural Campaign Design — Procedural Pipeline

Source: the "Architectural Campaign Design" essay. The schelling-campaign-map
skill implements the map half of this procedure (Phases 1–3). Phases 4–5 are
downstream campaign design, recorded here so the map's outputs plug into them.

## Phase 1: Canvas Initialization & Seed Sampling

1. **Define the Canvas**: bounding area (W × H), or load a background basemap.
2. **Determine Node Budget**:
   - Choose total regions N from campaign scope (e.g. N = 25).
   - **60/40 rule**: M ≈ 0.6N supply centers, K ≈ 0.4N non-supply
     (wilderness, water/ocean). N counts **every** cell on the canvas, water
     included — M + K = N must close. (The essay says "land regions" but K
     explicitly includes ocean cells; budget the whole canvas, not land
     alone.)
   - Neutral waypoint cells (hazards, boons, special spaces) come out of the
     non-supply share, never out of M. They are unclaimable neutral ground.
3. **Point Placement**: place N seeds Pi = (xi, yi). Prefer **Poisson-disc
   sampling** (or Lloyd's Relaxation) over raw uniform random — prevents
   clustering, keeps spatial density balanced. (The skill uses Poisson-disc
   with semantic anchoring when there is no source image to survey.)

## Phase 2: Tessellation & Region Generation

1. **Voronoi** from the seeds: perpendicular bisectors between neighboring
   seeds form the polygonal cell boundaries.
2. **Classify**: M cells become supply centers (resource hubs, shrines,
   vaults); K cells become non-supply (oceans, mountains, wilderness) acting
   as natural barriers and strategic buffers.

## Phase 3: Network Graph Extraction (Point Crawl)

1. Cells sharing a border segment get an adjacency link.
2. Seeds are vertices V, shared borders are undirected edges E. Prune
   traversals through impassable water. Result: the point-crawl graph.

## Phase 4: Geopolitical Layering (downstream)

1. Define F competing factions (typically 5–7).
2. **75/25 occupation**: ~75% of regions under faction control at campaign
   launch, ~25% unclaimed borderlands / neutral frontiers.
3. Tag rival-shared borders as military frontlines and high-friction zones.

## Phase 5: Strategic-Narrative Binding (downstream)

1. Overlay the 5×5 campaign matrix (5 quests × 5 steps = 25 cells) onto the M
   supply centers; high-value centers host multiple steps (strategic-narrative
   intersections).
2. Each supply center becomes a 5-room dungeon (Guardian, Puzzle/Trap,
   Climax, …).
