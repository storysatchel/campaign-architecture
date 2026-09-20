# Typed Multiplex Graph

The point-crawl is emitted as **G = (V, E_A, E_F, E_C)**, not a flat adjacency list. Implementation: `bin/graph_model.py`.

## Layers

| Layer | Enum | Meaning | Derived from |
|---|---|---|---|
| E_A | `ARMY_LAND` | Overland movement | Borders between non-sea, non-impassable cells |
| E_F | `FLEET_SEA` | Maritime movement | Borders touching a sea cell, via coast subnodes |
| E_C | `CONVOY_PORTAL` | Conditional fast travel | Authored, not derived: portals, convoy routes, seasonal passes |

E_C edges carry `conditions` (e.g. "Teleportation Circle active") and `is_active`. Off until campaign events flip them. Convoys are one instance of E_C, not the whole concept.

## Node taxonomy (two axes)

- **space_type**: `inland` | `coastal` | `sea` | `impassable`
  - `impassable` is the Switzerland pattern: blocks every layer, forces choke points. Use for mountain ranges, dead-magic zones, elder-dragon territory.
- **campaign_role**: `supply` | `waypoint` | `wild`
  - Waypoints stay neutral and unclaimable (existing invariant, now typed).

A supply center can be coastal; a wild can be impassable. Geography and campaign role are orthogonal.

## Coast splitting

A `coastal` node adjacent to two or more **disconnected** sea regions is split into subnodes — one per contiguous sea region (Spain → Spain/North Coast, Spain/South Coast). The parent keeps ownership, supply-center status, and E_A adjacency; E_F edges attach to the subnodes. This prevents fleets teleporting across landmasses. `split_coasts()` does it mechanically: BFS over E_F groups adjacent seas, splits on 2+ groups.

## Derivation from Voronoi

1. Tessellate seeds → cells with kinds.
2. Map kinds to space types: supply/wild → inland (or coastal if bordering sea); water → sea; designated blockers → impassable.
3. Raw adjacency = shared Voronoi borders.
4. `derive_layers(nodes, borders)` → E_A / E_F. Impassable endpoints produce no edge.
5. `split_coasts(graph)` → subnodes + re-attached E_F.
6. Author E_C edges separately with conditions.

## Campaign binding

Quest content lives on the node, not in a separate file:

- `matrix_cells`: list of `{quest_id, step_number, action_verb, narrative_summary}` — the 5×5 Campaign Matrix intersections hosted at this node.
- `dungeon_template`: the 5-room dungeon (`room_1_guardian` … `room_5_reward_or_revelation`).

Entering a cell exposes its dungeon and triggers its matrix step. Adjacency queries (`graph.neighbors(id, layer)`) validate movement, support ranges, and fast travel per layer.

## Topological invariance

Balance and friction live in the graph (adjacencies, choke points, supply-center density, layer structure), not the drawing. The same G reskins across genres — sugary kingdom, star sector (hyperlanes = edges, nebulae = impassable), planar archipelago — with geopolitics intact.

## JSON

`to_json(graph, title)` emits `graph_metadata` (title, total_nodes, supply_center_count), `nodes`, and the three edge lists. `graph_from_json()` round-trips. Enums serialize as their string values (`"E_A"`, `"coastal"`, …).
