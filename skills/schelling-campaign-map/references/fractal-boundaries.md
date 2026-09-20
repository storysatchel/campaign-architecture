# Fractal boundaries (optional mode)

An opt-in alternative to plain finite Voronoi, after Boris the Brave's
["Fractal Jittered Voronoi Partitions"](https://www.boristhebrave.com/2026/08/29/fractal-jittered-voronoi-partitions/)
(2026-08-29). Same seeds, same cells — but the borders come out jagged at
every scale, like coastlines. Good for wilderness frontiers, island chains,
and anywhere a straight Voronoi edge looks too surveyed.

This is a **boundary mode**, not a replacement: the default pipeline stays
plain finite Voronoi. Reach for fractal when the map wants organic borders.

## The idea

Boris starts with jittered sites on a grid, halves the grid spacing at every
layer, and gives each finer site the region of its nearest parent site.
A point's region is found by locating the nearest site at the deepest layer
and tracing parents back up to the root. We use a finite-depth version
(`depth=7` default) and a 5×5-cell search for nearest sites, as the article
describes.

One adaptation: the article's layer 0 is itself a jittered grid. Our layer 0
is **the campaign's seeds** — the surveyed Schelling points — so markers and
labels stay exactly on their authored positions. The base cell size is set
from the seeds' own minimum separation, which guarantees a parent chain can
never drift past the halfway mark to a neighboring seed: **every seed owns
its own location**, and every seed owns raster area. (Verified, not asserted:
`check_seeds_self()` is part of the gate below.)

## Pipeline

```python
from bin.fractal_voronoi import FractalPartition, adjacency_from_grid
from bin.graph_model import derive_layers

# seeds_xy: (N, 2) measured seed positions, extent: (width, height) in map units
fp = FractalPartition(seeds_xy, extent, depth=7, rng_seed=0)

# 1. Rasterize region ownership at render resolution.
grid = fp.rasterize(w_px, h_px)          # (h, w) int array, row 0 = top

# 2. Derive adjacency from the SAME raster you render.
#    A border pair exists where 4-connected pixels differ in ownership.
borders = [(f"n{a}", f"n{b}") for a, b in adjacency_from_grid(grid)]

# 3. Type the pairs into the multiplex graph as usual.
army, fleet = derive_layers(nodes, borders)
```

Rules that keep the map honest:

- **Topology comes from the rendered raster.** Never mix a fractal render
  with a plain-Voronoi adjacency list (or vice versa) — the graph and the
  picture must agree, so derive pairs from the exact grid you draw.
- **Render markers at seeds, never at centroids.** Same rule as the plain
  pipeline; fractal mode doesn't move a single marker.
- **Resolution guidance:** rasterize at the resolution you render. Topology
  is stable across resolutions (the gate checks 200px vs 800px give
  identical pair sets), but the visible wiggle needs enough pixels to read —
  below ~10 px per deepest cell the fractal detail aliases away.

## Tuning

- `depth` (default 7): layers of jitter. Each added layer roughly doubles
  the boundary's fine detail. 5–6 reads as "rough coast", 8+ as "fjords".
  Deeper = slower rasterization (linear in depth).
- `rng_seed` (default 0): changes the jitter, hence the borders — without
  moving any seed. Same seed in, same map out: the partition is fully
  deterministic. Use this to re-roll borders you're unhappy with.

## Verify gate

```bash
python3 bin/fractal_voronoi.py --selftest
```

Must print `SELFTEST OK`. It checks: every seed owns its own location and
some raster area; the raster is deterministic for fixed inputs; a different
`rng_seed` changes boundaries; the boundary mask is non-empty; the adjacency
pair set is identical at 200px and 800px. It also writes
`/tmp/fractal_selftest.png` — look at it. Fractal borders should read as
jagged coastlines; any seed sitting on or near a border is a failure, however
green the numbers are.
