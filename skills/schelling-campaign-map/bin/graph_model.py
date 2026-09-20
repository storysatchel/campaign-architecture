#!/usr/bin/env python3
"""
Multiplex graph data model for typed campaign maps: G = (V, E_A, E_F, E_C).

Layers:
- E_A (ARMY_LAND): overland movement. Borders between non-sea, non-impassable cells.
- E_F (FLEET_SEA): maritime movement. Borders touching sea cells, routed through
  coast subnodes so fleets can't teleport across landmasses.
- E_C (CONVOY_PORTAL): conditional edges — portals, convoy routes, seasonal
  passes. Carry `conditions` and `is_active`; off until campaign events flip them.

Node taxonomy is two axes:
- space_type: INLAND | COASTAL | SEA | IMPASSABLE (the "Switzerland" pattern:
  impassable nodes block every layer and force choke points)
- campaign_role: SUPPLY | WAYPOINT | WILD (waypoints are neutral, unclaimable)

Coast splitting: a COASTAL node adjacent to two or more disconnected sea
regions is split into subnodes (parent_province_id set, one per contiguous sea
region). The parent keeps ownership, supply-center status, and E_A adjacency;
E_F edges attach to the subnodes.

Derivation: derive_layers() types raw adjacency pairs from cell kinds.
split_coasts() performs the subnode split. to_json()/graph_from_json()
round-trip the whole graph; enums serialize as their string values.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


class SpaceType(Enum):
    INLAND = "inland"
    COASTAL = "coastal"
    SEA = "sea"
    IMPASSABLE = "impassable"  # Switzerland pattern: blocks all layers


class CampaignRole(Enum):
    SUPPLY = "supply"      # claimable, hosts quests/dungeons
    WAYPOINT = "waypoint"  # neutral, unclaimable, never hosts quests
    WILD = "wild"          # unclaimed terrain


class LayerType(Enum):
    ARMY_LAND = "E_A"
    FLEET_SEA = "E_F"
    CONVOY_PORTAL = "E_C"


@dataclass
class Unit:
    unit_id: str
    unit_type: str  # "ARMY" or "FLEET"
    faction_id: str


@dataclass
class MatrixCellIntersection:
    quest_id: int         # 1..5 (parallel quest lines)
    step_number: int      # 1..5 (hook to climax)
    action_verb: str      # e.g. "Disinfect", "Retrieve", "Rescue"
    narrative_summary: str


@dataclass
class FiveRoomDungeon:
    room_1_guardian: str
    room_2_puzzle_or_trap: str
    room_3_trick_or_climax: str
    room_4_climax_encounter: str
    room_5_reward_or_revelation: str


@dataclass
class Node:
    id: str
    name: str
    space_type: SpaceType
    campaign_role: CampaignRole = CampaignRole.WILD

    # Multi-coast geography (Spain -> Spain/North Coast, Spain/South Coast)
    parent_province_id: Optional[str] = None
    coast_variant_ids: List[str] = field(default_factory=list)

    # Geopolitical metadata
    is_supply_center: bool = False
    home_power_id: Optional[str] = None
    controlling_faction_id: Optional[str] = None
    occupying_unit: Optional[Unit] = None

    # Campaign architecture binding
    matrix_cells: List[MatrixCellIntersection] = field(default_factory=list)
    dungeon_template: Optional[FiveRoomDungeon] = None


@dataclass
class Edge:
    source_id: str
    target_id: str
    layer: LayerType
    is_active: bool = True
    traversal_cost: int = 1
    conditions: Optional[str] = None


@dataclass
class DiplomacyMultiplexGraph:
    nodes: Dict[str, Node] = field(default_factory=dict)
    army_edges: List[Edge] = field(default_factory=list)    # E_A
    fleet_edges: List[Edge] = field(default_factory=list)   # E_F
    convoy_edges: List[Edge] = field(default_factory=list)  # E_C (dynamic)

    def neighbors(self, node_id: str, layer: LayerType) -> List[str]:
        """O(1)-ish adjacency lookup on one layer (undirected)."""
        pool = {LayerType.ARMY_LAND: self.army_edges,
                LayerType.FLEET_SEA: self.fleet_edges,
                LayerType.CONVOY_PORTAL: self.convoy_edges}[layer]
        out = []
        for e in pool:
            if not e.is_active:
                continue
            if e.source_id == node_id:
                out.append(e.target_id)
            elif e.target_id == node_id:
                out.append(e.source_id)
        return out


# ---------------------------------------------------------------- derivation

def derive_layers(nodes: Dict[str, Node],
                  borders: List[Tuple[str, str]]) -> Tuple[List[Edge], List[Edge]]:
    """Type raw adjacency pairs into E_A / E_F from endpoint space types.

    - Either endpoint IMPASSABLE -> no edge (Switzerland pattern).
    - Either endpoint SEA -> E_F (fleet layer).
    - Otherwise -> E_A (army/land layer).
    """
    army, fleet = [], []
    for a, b in borders:
        na, nb = nodes[a], nodes[b]
        if na.space_type == SpaceType.IMPASSABLE or nb.space_type == SpaceType.IMPASSABLE:
            continue
        if na.space_type == SpaceType.SEA or nb.space_type == SpaceType.SEA:
            fleet.append(Edge(a, b, LayerType.FLEET_SEA))
        else:
            army.append(Edge(a, b, LayerType.ARMY_LAND))
    return army, fleet


def _contiguous_sea_groups(node_id: str, graph: DiplomacyMultiplexGraph) -> List[List[str]]:
    """Group a coastal node's adjacent seas into contiguous regions (BFS over E_F)."""
    adj_seas = [s for s in graph.neighbors(node_id, LayerType.FLEET_SEA)
                if graph.nodes[s].space_type == SpaceType.SEA]
    seen, groups = set(), []
    for s in adj_seas:
        if s in seen:
            continue
        group, stack = [], [s]
        while stack:
            cur = stack.pop()
            if cur in seen:
                continue
            seen.add(cur)
            group.append(cur)
            stack.extend(t for t in graph.neighbors(cur, LayerType.FLEET_SEA)
                         if graph.nodes[t].space_type == SpaceType.SEA and t not in seen)
        groups.append(group)
    return groups


def split_coasts(graph: DiplomacyMultiplexGraph) -> DiplomacyMultiplexGraph:
    """Split COASTAL nodes touching 2+ disconnected sea regions into subnodes.

    Returns a new graph. Parent keeps E_A edges, ownership, and supply-center
    status; E_F edges are re-attached to the per-region subnode.
    """
    g = DiplomacyMultiplexGraph(
        nodes=dict(graph.nodes),
        army_edges=list(graph.army_edges),
        fleet_edges=[],
        convoy_edges=list(graph.convoy_edges),
    )
    for nid, node in graph.nodes.items():
        if node.space_type != SpaceType.COASTAL or node.parent_province_id:
            continue
        groups = _contiguous_sea_groups(nid, graph)
        if len(groups) < 2:
            continue
        for i, group in enumerate(groups):
            sub_id = f"{nid}_coast_{i + 1}"
            g.nodes[sub_id] = Node(
                id=sub_id,
                name=f"{node.name} (Coast {i + 1})",
                space_type=SpaceType.COASTAL,
                campaign_role=node.campaign_role,
                parent_province_id=nid,
            )
            node.coast_variant_ids.append(sub_id)
            for sea in group:
                g.fleet_edges.append(Edge(sub_id, sea, LayerType.FLEET_SEA))
    # carry over fleet edges that didn't involve a split parent
    split_parents = {n.parent_province_id for n in g.nodes.values()
                     if n.parent_province_id}
    for e in graph.fleet_edges:
        if e.source_id in split_parents or e.target_id in split_parents:
            continue  # re-attached above
        g.fleet_edges.append(e)
    return g


# ---------------------------------------------------------------- JSON

def _encode(obj):
    if isinstance(obj, Enum):
        return obj.value
    raise TypeError(f"not serializable: {obj!r}")


def to_json(graph: DiplomacyMultiplexGraph, title: str = "") -> str:
    payload = {
        "graph_metadata": {
            "title": title,
            "total_nodes": len(graph.nodes),
            "supply_center_count": sum(1 for n in graph.nodes.values()
                                      if n.is_supply_center and not n.parent_province_id),
        },
        "nodes": {nid: asdict(n) for nid, n in graph.nodes.items()},
        "army_edges": [asdict(e) for e in graph.army_edges],
        "fleet_edges": [asdict(e) for e in graph.fleet_edges],
        "convoy_edges": [asdict(e) for e in graph.convoy_edges],
    }
    return json.dumps(payload, indent=1, default=_encode)


def _node_from(d: dict) -> Node:
    d = dict(d)
    d["space_type"] = SpaceType(d["space_type"])
    d["campaign_role"] = CampaignRole(d.get("campaign_role", "wild"))
    if d.get("occupying_unit"):
        d["occupying_unit"] = Unit(**d["occupying_unit"])
    d["matrix_cells"] = [MatrixCellIntersection(**m) for m in d.get("matrix_cells", [])]
    if d.get("dungeon_template"):
        d["dungeon_template"] = FiveRoomDungeon(**d["dungeon_template"])
    return Node(**d)


def _edge_from(d: dict) -> Edge:
    d = dict(d)
    d["layer"] = LayerType(d["layer"])
    return Edge(**d)


def graph_from_json(text: str) -> DiplomacyMultiplexGraph:
    payload = json.loads(text)
    return DiplomacyMultiplexGraph(
        nodes={nid: _node_from(n) for nid, n in payload["nodes"].items()},
        army_edges=[_edge_from(e) for e in payload.get("army_edges", [])],
        fleet_edges=[_edge_from(e) for e in payload.get("fleet_edges", [])],
        convoy_edges=[_edge_from(e) for e in payload.get("convoy_edges", [])],
    )
