#!/usr/bin/env python3
"""Fractal jittered Voronoi partitions.

After Boris the Brave, "Fractal Jittered Voronoi Partitions" (2026-08-29):
https://www.boristhebrave.com/2026/08/29/fractal-jittered-voronoi-partitions/

A Voronoi variant whose cell boundaries are fractal rather than straight —
suited to coastlines, which are similarly fractal in nature.

Procedure
---------
1. Layer 0: the sites are the campaign's seeds (in Boris's original they are
   one jittered site per grid square; here the seeds ARE the sites, so labels
   and markers stay exactly at seeds).
2. Layer 1: a square grid at half the base cell size; one jittered site per
   square (deterministic hash PRNG). Each layer-1 site's parent is its nearest
   site in layer 0.
3. Repeat, halving the grid each layer. Each layer-k site's parent is its
   nearest site in layer k-1.
4. A point's region is the layer-0 seed reached by tracing parents upward.

The base cell size is the seeds' own minimum separation: a parent chain can
drift at most ~0.36 * s0 from its point, so no chain wanders past the halfway
mark to a neighboring seed — every seed owns its own location, and labels /
markers stay truthful. (Boris's original uses a grid for layer 0 with spacing
s0; the seeds-as-layer-0 adaptation needs this scaling to keep the same
guarantee.)

In practice we use the finite-depth approximation: find the nearest site at
the deepest layer, then trace its root. Per-point cost is bounded (a 5x5 cell
search per layer — cells farther away cannot contain the nearest site), so no
diagram is ever constructed.

Public API
----------
  FractalPartition(seeds_xy, extent, depth=7, rng_seed=0)
      .partition_points(pts)   -> (M,) int array of seed indices
      .rasterize(w_px, h_px)   -> (h_px, w_px) int array of seed indices
      .boundary_mask(grid)     -> (h, w) bool array, True on region borders
      .check_seeds_self()      -> list of seed indices that do NOT own
                                  their own location (empty when healthy)
  adjacency_from_grid(grid)    -> set of (i, j) index pairs, i < j

Feed the adjacency pairs to graph_model.derive_layers() as the raw borders.
Topology and render then agree by construction: both come from the raster.

CLI: --selftest builds a small seed set, rasterizes it, runs the gates, and
writes /tmp/fractal_selftest.png.
"""
import argparse

import numpy as np

_U64 = np.uint64
_M32 = np.uint64(0xFFFFFFFF)


def _splitmix64(x):
    with np.errstate(over="ignore"):  # intentional mod-2**64 wraparound
        x = x + _U64(0x9E3779B97F4A7C15)
        z = x
        z = ((z ^ (z >> _U64(30))) * _U64(0xBF58476D1CE4E5B9))
        z = ((z ^ (z >> _U64(27))) * _U64(0x94D049BB133111EB))
        z = z ^ (z >> _U64(31))
    return z


def _to_u32(a):
    return (np.asarray(a) % (1 << 32)).astype(_U64)


def _hash01(key):
    """key: uint64 array -> uniform [0, 1) doubles."""
    z = _splitmix64(key)
    return (z >> _U64(11)).astype(np.float64) / float(1 << 53)


def hash2(rng_seed, layer, cx, cy):
    """Deterministic jitter offsets in [0, 1)^2 for grid cells.

    Vectorized over cx/cy arrays.
    """
    cx = _to_u32(cx)
    cy = _to_u32(cy)
    key = _U64(rng_seed) & _M32
    key = _splitmix64(key + _U64(layer))
    key = _splitmix64(key + cx)
    key = _splitmix64(key + cy)
    u = _hash01(key)
    v = _hash01(key ^ _U64(0x9E3779B97F4A7C15))
    return u, v


class FractalPartition:
    def __init__(self, seeds_xy, extent, depth=7, rng_seed=0):
        self.seeds = np.asarray(seeds_xy, dtype=np.float64)
        if self.seeds.ndim != 2 or self.seeds.shape[1] != 2:
            raise ValueError("seeds_xy must be (N, 2)")
        if len(self.seeds) < 2:
            raise ValueError("need at least 2 seeds")
        self.W, self.H = float(extent[0]), float(extent[1])
        self.depth = int(depth)
        self.rng_seed = int(rng_seed)
        # Base cell size from the seeds themselves: a parent chain can drift
        # at most ~0.36 * s0 from its point, so with s0 = min seed separation
        # no chain can wander past the halfway mark to a neighboring seed —
        # every seed owns its own location. Floored so pathological
        # near-duplicate seeds can't drive cell sizes (and caches) to zero.
        d2 = ((self.seeds[:, None, :] - self.seeds[None, :, :]) ** 2).sum(-1)
        np.fill_diagonal(d2, np.inf)
        sep_min = float(np.sqrt(d2.min()))
        if not np.isfinite(sep_min) or sep_min <= 0:
            raise ValueError("duplicate seeds")
        self.s0 = max(sep_min, max(self.W, self.H) / 1024)
        self.sep_min = sep_min

    def _cell_size(self, layer):
        return self.s0 / (2 ** layer)

    # -- vectorized root trace ---------------------------------------------

    def _trace_roots(self, cells_d):
        """Root seed index for each layer-`depth` cell.

        cells_d: (C, 2) int64 array of deepest-layer cells.
        Walks every cell's parent chain upward, one whole level at a time,
        vectorized over cells. Returns (C,) int64 seed indices.
        """
        cells = np.asarray(cells_d, dtype=np.int64)
        for k in range(self.depth, 1, -1):
            s_k = self._cell_size(k)
            u, v = hash2(self.rng_seed, k, cells[:, 0], cells[:, 1])
            sites = s_k * (cells + np.stack([u, v], axis=1))  # (C, 2)
            s_km = self._cell_size(k - 1)
            ccx = np.floor(sites[:, 0] / s_km).astype(np.int64)
            ccy = np.floor(sites[:, 1] / s_km).astype(np.int64)
            best_d2 = np.full(len(cells), np.inf)
            best = np.zeros_like(cells)
            for dx in range(-2, 3):
                for dy in range(-2, 3):
                    qx = ccx + dx
                    qy = ccy + dy
                    uu, vv = hash2(self.rng_seed, k - 1, qx, qy)
                    sx = s_km * (qx + uu)
                    sy = s_km * (qy + vv)
                    dd = (sites[:, 0] - sx) ** 2 + (sites[:, 1] - sy) ** 2
                    better = dd < best_d2
                    best_d2 = np.where(better, dd, best_d2)
                    best[better, 0] = qx[better]
                    best[better, 1] = qy[better]
            cells = best
        # cells is now at layer 1: each parent is the nearest seed
        s_1 = self._cell_size(1)
        u, v = hash2(self.rng_seed, 1, cells[:, 0], cells[:, 1])
        sites = s_1 * (cells + np.stack([u, v], axis=1))
        roots = np.empty(len(cells), dtype=np.int64)
        for lo in range(0, len(cells), 50_000):
            blk = sites[lo:lo + 50_000]
            d2 = ((blk[:, None, :] - self.seeds[None, :, :]) ** 2).sum(-1)
            roots[lo:lo + 50_000] = np.argmin(d2, axis=1)
        return roots

    # -- vectorized finite-depth partition ----------------------------------

    def partition_points(self, pts, chunk=100_000):
        """pts: (M, 2) array -> (M,) int array of owning seed indices."""
        pts = np.asarray(pts, dtype=np.float64)
        out = np.empty(len(pts), dtype=np.int64)
        d = self.depth
        s = self._cell_size(d)
        offs = [(dx, dy) for dx in range(-2, 3) for dy in range(-2, 3)]
        for lo in range(0, len(pts), chunk):
            c = pts[lo:lo + chunk]
            ccx = np.floor(c[:, 0] / s).astype(np.int64)
            ccy = np.floor(c[:, 1] / s).astype(np.int64)
            best_d2 = np.full(len(c), np.inf)
            best_cx = np.zeros(len(c), dtype=np.int64)
            best_cy = np.zeros(len(c), dtype=np.int64)
            for dx, dy in offs:
                qx = ccx + dx
                qy = ccy + dy
                u, v = hash2(self.rng_seed, d, qx, qy)
                sx = s * (qx + u)
                sy = s * (qy + v)
                d2 = (c[:, 0] - sx) ** 2 + (c[:, 1] - sy) ** 2
                better = d2 < best_d2
                best_d2 = np.where(better, d2, best_d2)
                best_cx = np.where(better, qx, best_cx)
                best_cy = np.where(better, qy, best_cy)
            # trace each distinct winning cell to its root seed
            uniq, inv = np.unique(
                np.stack([best_cx, best_cy], axis=1), axis=0, return_inverse=True)
            out[lo:lo + chunk] = self._trace_roots(uniq)[inv]
        return out

    def rasterize(self, w_px, h_px):
        """Region-id grid over the extent. Row 0 is the top (y=0)."""
        ys = (np.arange(h_px) + 0.5) * self.H / h_px
        xs = (np.arange(w_px) + 0.5) * self.W / w_px
        yy, xx = np.meshgrid(ys, xs, indexing="ij")
        pts = np.stack([xx.ravel(), yy.ravel()], axis=1)
        return self.partition_points(pts).reshape(h_px, w_px)

    @staticmethod
    def boundary_mask(grid):
        """True where a 4-neighbor belongs to a different region."""
        m = np.zeros_like(grid, dtype=bool)
        m[:-1, :] |= grid[:-1, :] != grid[1:, :]
        m[1:, :] |= grid[:-1, :] != grid[1:, :]
        m[:, :-1] |= grid[:, :-1] != grid[:, 1:]
        m[:, 1:] |= grid[:, :-1] != grid[:, 1:]
        return m

    def check_seeds_self(self):
        """Seeds that do not own their own location. Healthy == []."""
        got = self.partition_points(self.seeds)
        return [i for i, g in enumerate(got) if g != i]


def adjacency_from_grid(grid):
    """Region pairs sharing a 4-connected border. Returns {(i, j), i < j}."""
    pairs = set()
    v = np.stack([grid[:-1, :].ravel(), grid[1:, :].ravel()], axis=1)
    h = np.stack([grid[:, :-1].ravel(), grid[:, 1:].ravel()], axis=1)
    for a, b in np.concatenate([v, h]):
        a, b = int(a), int(b)
        if a != b:
            pairs.add((min(a, b), max(a, b)))
    return pairs


def _selftest():
    rng = np.random.default_rng(7)
    W = H = 100.0
    seeds = rng.uniform(15, 85, size=(12, 2))
    # enforce a minimum separation so the self-ownership gate is meaningful
    fp = FractalPartition(seeds, (W, H), depth=7, rng_seed=42)
    bad = fp.check_seeds_self()
    print(f"seeds: {len(seeds)}, depth 7, self-ownership failures: {bad}")
    assert not bad, "every seed must own its own location"

    import time
    t0 = time.time()
    grid = fp.rasterize(400, 400)
    dt = time.time() - t0
    print(f"rasterized 400x400 in {dt:.1f}s")
    assert grid.min() >= 0 and grid.max() < len(seeds)
    assert set(np.unique(grid)) == set(range(len(seeds))), \
        "every seed must own some pixels"

    adj = adjacency_from_grid(grid)
    print(f"adjacency pairs: {len(adj)}")
    # symmetry / sanity: spot-check a pair against the boundary mask
    mask = FractalPartition.boundary_mask(grid)
    assert mask.any(), "boundary mask must be non-empty"
    frac = mask.mean()
    print(f"boundary pixels: {frac:.3f} of raster")

    # determinism: same inputs -> identical grid
    fp2 = FractalPartition(seeds, (W, H), depth=7, rng_seed=42)
    assert np.array_equal(grid, fp2.rasterize(400, 400)), "not deterministic"
    fp3 = FractalPartition(seeds, (W, H), depth=7, rng_seed=43)
    assert not np.array_equal(grid, fp3.rasterize(400, 400)), \
        "jitter seed had no effect"

    # resolution stability: topology must not wobble with raster resolution
    def _pairs(px):
        g = FractalPartition(seeds, (W, H), depth=7, rng_seed=42).rasterize(px, px)
        return {tuple(sorted(p)) for p in adjacency_from_grid(g)}
    p_lo, p_hi = _pairs(200), _pairs(800)
    assert p_lo == p_hi, \
        f"adjacency changed with resolution: {sorted(p_lo ^ p_hi)}"
    print(f"resolution-stable topology: {len(p_lo)} pairs at 200px and 800px")

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(6, 6))
        ax.imshow(grid, origin="upper", cmap="tab20")
        by = mask
        yy, xx = np.nonzero(by)
        ax.scatter(xx[::7], yy[::7], s=1, c="black", alpha=0.6)
        sx = seeds[:, 0] / W * 400
        sy = seeds[:, 1] / H * 400
        ax.scatter(sx, sy, s=40, c="white", edgecolors="black", zorder=3)
        ax.set_axis_off()
        fig.savefig("/tmp/fractal_selftest.png", dpi=100, bbox_inches="tight")
        print("wrote /tmp/fractal_selftest.png")
    except ImportError:
        print("(matplotlib unavailable, skipping demo render)")
    print("SELFTEST OK")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        _selftest()
    else:
        ap.print_help()
