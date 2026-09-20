#!/usr/bin/env python3
"""
Three sample campaign maps at different strategic densities (N=75, Diplomacy scale):
- diplomacy_like (default): ~45% supply, ~25% sea, ~28% wild, ~1% impassable
- dense:                    ~60% supply
- sparse (frontier):        ~25% supply

Pipeline per sample: Poisson-disc seeds (Bridson) -> kind assignment with
edge-aware heuristics -> Voronoi -> typed multiplex graph (E_A/E_F/E_C via
bin/graph_model.py) -> rendered PNG.

Outputs: diplomacy_like.png, dense.png, sparse.png + a JSON summary each.
"""
import json
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patheffects as patheffects
from scipy.spatial import Voronoi

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "bin"))
from graph_model import (DiplomacyMultiplexGraph, Node, Edge, SpaceType,
                         CampaignRole, LayerType, derive_layers, split_coasts,
                         to_json)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dunmanifestin import build_engine, titleize

# One engine for all three maps: the churn keeps every manifested name unique.
ENG = build_engine(seed=20260919)

OUT = os.path.dirname(os.path.abspath(__file__))
rng = np.random.default_rng(20260919)

# ---------------------------------------------------------------- Poisson-disc (Bridson)

def poisson_disc(r, k=30):
    pts = [rng.random(2)]
    active = [0]
    grid_n = int(np.ceil(np.sqrt(2) / r))
    grid = [[-1] * grid_n for _ in range(grid_n)]
    def cell(p):
        return int(p[0] * grid_n), int(p[1] * grid_n)
    gx, gy = cell(pts[0])
    grid[gy][gx] = 0
    while active:
        i = active[rng.integers(len(active))]
        base = pts[i]
        found = False
        for _ in range(k):
            ang = rng.random() * 2 * np.pi
            rad = r * (1 + rng.random())
            cand = base + rad * np.array([np.cos(ang), np.sin(ang)])
            if not (0 <= cand[0] < 1 and 0 <= cand[1] < 1):
                continue
            cx, cy = cell(cand)
            ok = True
            for yy in range(max(0, cy - 2), min(grid_n, cy + 3)):
                for xx in range(max(0, cx - 2), min(grid_n, cx + 3)):
                    j = grid[yy][xx]
                    if j >= 0 and np.linalg.norm(pts[j] - cand) < r:
                        ok = False
                        break
                if not ok:
                    break
            if ok:
                pts.append(cand)
                grid[cy][cx] = len(pts) - 1
                active.append(len(pts) - 1)
                found = True
        if not found:
            active.remove(i)
    return np.array(pts)


# ---------------------------------------------------------------- Voronoi (finite, clipped)

def finite_voronoi(seeds):
    vor = Voronoi(seeds)
    center = seeds.mean(axis=0)
    polys = []
    for i, reg_idx in enumerate(vor.point_region):
        verts = vor.regions[reg_idx]
        if -1 not in verts:
            poly = [vor.vertices[v] for v in verts]
        else:
            poly = []
            ridge_idx = np.where((vor.ridge_points == i).any(axis=1))[0]
            for j, v in enumerate(verts):
                if v != -1:
                    poly.append(vor.vertices[v])
                else:
                    rp = vor.ridge_points[ridge_idx[0]]
                    a, b = seeds[rp[0]], seeds[rp[1]]
                    mid = (a + b) / 2
                    n = np.array([-(b[1] - a[1]), b[0] - a[0]])
                    n = n / (np.linalg.norm(n) + 1e-12)
                    if np.dot(mid - center, n) < 0:
                        n = -n
                    poly.append(mid + n * 4.0)
            ridge_idx = ridge_idx[1:] if len(ridge_idx) > 1 else ridge_idx
        poly = np.array(poly)
        for axis, val, keep_le in [(0, 0, False), (0, 1, True), (1, 0, False), (1, 1, True)]:
            out = []
            for t in range(len(poly)):
                a, b = poly[t - 1], poly[t]
                ain = (a[axis] <= val) if keep_le else (a[axis] >= val)
                bin_ = (b[axis] <= val) if keep_le else (b[axis] >= val)
                if bin_:
                    if not ain:
                        tt = (val - a[axis]) / (b[axis] - a[axis] + 1e-12)
                        out.append(a + (b - a) * tt)
                    out.append(b)
                elif ain:
                    tt = (val - a[axis]) / (b[axis] - a[axis] + 1e-12)
                    out.append(a + (b - a) * tt)
            poly = np.array(out) if out else np.zeros((0, 2))
            if len(poly) == 0:
                break
        polys.append(poly)
    return polys, vor


def adjacency(vor, n):
    adj = set()
    for a, b in vor.ridge_points:
        if a >= 0 and b >= 0:
            adj.add((min(a, b), max(a, b)))
    return sorted(adj)


# ---------------------------------------------------------------- names via dunmanifestin palettes

def _curated(template_options, tries=30, min_len=6):
    """Manifest from placeName with a chosen template; the palettes' bare
    [word] template is too terse for a supply center, so prefer compounds.
    (This curation is the documented workflow: keep promises, drop filler.)
    Final labels are title-cased for the map; the engine itself is case-neutral."""
    for _ in range(tries):
        tmpl = ENG.rng.choice(template_options)
        n = ENG.manifest("placeName", phrase=tmpl)
        if len(n) >= min_len and n.replace("-", "").replace(" ", "").isalpha():
            return titleize(n)
    return titleize(ENG.manifest("placeName"))


def supply_name():
    return _curated(["[namePrefix][placeSuffix]", "[word][placeSuffix]"])


def wild_name():
    return titleize(_curated(["[word][placeSuffix]", "[namePrefix][placeSuffix]",
                     "[word]-[word]"], min_len=5))


def sea_name():
    w = titleize(ENG.manifest("word"))
    kind = ENG.rng.choice(["Sea", "Deep", "Reach", "Expanse"])
    return f"the {w} {kind}"


def impassable_name():
    return f"the {titleize(ENG.manifest('word'))} Spine"


# ---------------------------------------------------------------- build one sample

def build_sample(key, ratios, title):
    seeds = poisson_disc(r=0.095)
    N = len(seeds)
    # counts from density ratios, corrected to sum to N
    counts = {k: max(1, round(v * N)) for k, v in ratios.items()}
    diff = N - sum(counts.values())
    counts["wild"] += diff  # wild absorbs rounding
    n_supply, n_sea = counts["supply"], counts["sea"]
    n_wild, n_waypoint = counts["wild"], counts["waypoint"]
    n_impassable = counts["impassable"]

    polys, vor = finite_voronoi(seeds)
    adj = adjacency(vor, N)
    nbrs = {i: set() for i in range(N)}
    for a, b in adj:
        nbrs[a].add(b)
        nbrs[b].add(a)

    edge_cell = [any([p[:, 0].min() <= 1e-9, p[:, 0].max() >= 1 - 1e-9,
                      p[:, 1].min() <= 1e-9, p[:, 1].max() >= 1 - 1e-9])
                 for p in polys]
    outer_third = [np.linalg.norm(s - 0.5) > 1 / 3 for s in seeds]

    kind = ["wild"] * N
    # impassable: most central cell
    imp = int(np.argmin([np.linalg.norm(s - 0.5) for s in seeds]))
    kind[imp] = "impassable"
    # seas: spread around the edge cells
    edge_ids = [i for i in range(N) if edge_cell[i] and kind[i] == "wild"]
    rng.shuffle(edge_ids)
    seas = edge_ids[:n_sea]
    for i in seas:
        kind[i] = "sea"
    # supply: mix of interior + guaranteed edge presence (interesting-edges rule)
    remaining = [i for i in range(N) if kind[i] == "wild"]
    edge_supply = [i for i in remaining if outer_third[i]][:3]
    rest = [i for i in remaining if i not in edge_supply]
    rng.shuffle(rest)
    supply_ids = edge_supply + rest[:n_supply - len(edge_supply)]
    for i in supply_ids:
        kind[i] = "supply"
    # waypoints: wild cells adjacent to supply (buffers)
    remaining = [i for i in range(N) if kind[i] == "wild"]
    buf = [i for i in remaining if any(n in supply_ids for n in nbrs[i])]
    rng.shuffle(buf)
    for i in buf[:n_waypoint]:
        kind[i] = "waypoint"

    # space types (coastal = supply/wild/waypoint adjacent to sea)
    sea_set = {i for i in range(N) if kind[i] == "sea"}
    space = []
    for i in range(N):
        if kind[i] == "sea":
            space.append(SpaceType.SEA)
        elif kind[i] == "impassable":
            space.append(SpaceType.IMPASSABLE)
        elif any(n in sea_set for n in nbrs[i]):
            space.append(SpaceType.COASTAL)
        else:
            space.append(SpaceType.INLAND)
    role = {"supply": CampaignRole.SUPPLY, "waypoint": CampaignRole.WAYPOINT,
            "sea": CampaignRole.WILD, "wild": CampaignRole.WILD,
            "impassable": CampaignRole.WILD}[kind[i]] if False else None
    role_of = {"supply": CampaignRole.SUPPLY, "waypoint": CampaignRole.WAYPOINT,
               "sea": CampaignRole.WILD, "wild": CampaignRole.WILD,
               "impassable": CampaignRole.WILD}

    nodes = {}
    wi = 0
    for i in range(N):
        if kind[i] == "supply":
            nm = supply_name()
        elif kind[i] == "sea":
            nm = sea_name()
        elif kind[i] == "impassable":
            nm = impassable_name()
        elif kind[i] == "waypoint":
            nm = f"waypoint-{wi + 1}"; wi += 1
        else:
            nm = wild_name()
        nodes[f"n{i}"] = Node(
            id=f"n{i}", name=nm, space_type=space[i],
            campaign_role=role_of[kind[i]],
            is_supply_center=(kind[i] == "supply"),
        )

    g = DiplomacyMultiplexGraph(nodes=nodes)
    idb = [(f"n{a}", f"n{b}") for a, b in adj]
    g.army_edges, g.fleet_edges = derive_layers(nodes, idb)
    # a couple of sample E_C portals between far supply centers
    sup = [f"n{i}" for i in supply_ids]
    if len(sup) >= 4:
        g.convoy_edges.append(Edge(sup[0], sup[-1], LayerType.CONVOY_PORTAL,
                                   is_active=False,
                                   conditions="Ley-line conduit (dormant)"))
        g.convoy_edges.append(Edge(sup[1], sup[-2], LayerType.CONVOY_PORTAL,
                                   is_active=True, traversal_cost=0,
                                   conditions="Allied naval convoy"))
    g = split_coasts(g)

    # ---- render
    COLORS = {SpaceType.INLAND: "#7cb342", SpaceType.COASTAL: "#aed581",
              SpaceType.SEA: "#3a7bd5", SpaceType.IMPASSABLE: "#616161"}
    fig = plt.figure(figsize=(10, 10), dpi=120)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    for i, poly in enumerate(polys):
        if len(poly) < 3:
            continue
        nid = f"n{i}"
        node = g.nodes[nid]
        c = "#ffd75e" if node.is_supply_center else COLORS[node.space_type]
        ec = "#1a3a6b" if node.space_type == SpaceType.SEA else "#333333"
        ax.fill(poly[:, 0], poly[:, 1], facecolor=c, edgecolor=ec,
                linewidth=0.7, zorder=2)
    halo = dict(path_effects=[patheffects.withStroke(linewidth=2.5, foreground="white")])
    for i in range(N):
        nid = f"n{i}"
        node = g.nodes[nid]
        sx, sy = seeds[i]
        if node.is_supply_center:
            ax.plot(sx, sy, marker="*", color="#b8860b", markersize=9,
                    markeredgecolor="white", markeredgewidth=0.7, zorder=5)
            ax.text(sx, sy + 0.018, node.name, ha="center", va="bottom",
                    fontsize=5.5, weight="bold", color="#5a3d00", zorder=6, **halo)
        elif node.space_type == SpaceType.SEA:
            ax.text(sx, sy, node.name, ha="center", va="center", fontsize=6,
                    style="italic", color="white", zorder=6, **halo)
        elif node.space_type == SpaceType.IMPASSABLE:
            ax.text(sx, sy, node.name, ha="center", va="center", fontsize=7,
                    weight="bold", color="white", zorder=6, **halo)
        elif node.campaign_role == CampaignRole.WAYPOINT:
            ax.plot(sx, sy, marker="D", color="#6a1b9a", markersize=6,
                    markeredgecolor="white", markeredgewidth=0.7, zorder=5)
    ax.set_title(f"{title}\nN={N}  supply={n_supply}  sea={n_sea}  "
                 f"wild={n_wild}  waypoints={n_waypoint}  impassable={n_impassable}  |  "
                 f"E_A={len(g.army_edges)}  E_F={len(g.fleet_edges)}  E_C={len(g.convoy_edges)}",
                 fontsize=10, pad=12)
    out_png = os.path.join(OUT, f"{key}.png")
    fig.savefig(out_png, dpi=120, bbox_inches="tight", pad_inches=0.1)
    plt.close(fig)

    summary = {"key": key, "title": title, "N": N,
               "supply": n_supply, "sea": n_sea, "wild": n_wild,
               "waypoints": n_waypoint, "impassable": n_impassable,
               "E_A": len(g.army_edges), "E_F": len(g.fleet_edges),
               "E_C": len(g.convoy_edges),
               "coast_subnodes": sum(1 for n in g.nodes.values() if n.parent_province_id)}
    with open(os.path.join(OUT, f"{key}.json"), "w") as f:
        json.dump(summary, f, indent=1)
    print(f"{key}: N={N} E_A={summary['E_A']} E_F={summary['E_F']} "
          f"E_C={summary['E_C']} subnodes={summary['coast_subnodes']} -> {out_png}")
    return summary


if __name__ == "__main__":
    build_sample("diplomacy_like",
                 {"supply": 0.45, "sea": 0.25, "wild": 0.24,
                  "waypoint": 0.04, "impassable": 0.013},
                 "Diplomacy-like (default) — d≈0.45")
    build_sample("dense",
                 {"supply": 0.60, "sea": 0.16, "wild": 0.19,
                  "waypoint": 0.04, "impassable": 0.013},
                 "Dense — d≈0.60")
    build_sample("sparse",
                 {"supply": 0.25, "sea": 0.27, "wild": 0.40,
                  "waypoint": 0.07, "impassable": 0.013},
                 "Sparse frontier — d≈0.25")
