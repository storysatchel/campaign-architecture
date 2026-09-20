# campaign-matrix

Bind quest content to campaign geography. Given the supply centers of a
campaign map, generate the **5×5 quest matrix** (5 quests × 5 beats, dealt
round-robin onto centers ranked by land-adjacency degree, so the best-connected
centers recur as hubs) and a themed **5-room dungeon** per supply center.

Entering a center's cell exposes its dungeon and fires its matrix step.

## Use

This is a companion to the
[schelling-campaign-map](https://github.com/gavmor/schelling-campaign-map)
skill — it reads that skill's typed graph JSON (`bin/graph_model.py`'s
`to_json()`), fills each node's `matrix_cells` and `dungeon_template`, and
renders the matrix + dungeon tables.

```bash
python3 bin/matrix.py --graph <graph.json> \
    --quests "The Hollow Crown;The Ashen Compact;The Drowned Ledger;The Ninth Bell;The Salt Rebellion" \
    --out <dir> --name <campaign>
```

No graph? Pass centers and edges directly:

```bash
python3 bin/matrix.py --centers "Crownsgate,Ironford,Millhaven" \
    --edges "Crownsgate-Ironford,Ironford-Millhaven" \
    --auto --out <dir> --name <campaign>
```

`--auto` draws quest titles from the fallback bank (`references/theme-bank.md`) —
flag that output as provisional. Verify any matrix with:

```bash
python3 bin/matrix.py --verify <dir>/<name>-matrix.json
```

## The shape

- **Quest arc:** Inciting → Complication → Reversal → Crisis → Climax.
- **5-room dungeon:** Entrance & Guardian → Puzzle or Trap → Setback → Climax →
  Reward & Revelation. Every supply center gets one, themed in degree-rank order.
- **Binding rule:** entering a supply center's cell exposes its dungeon and
  fires its matrix step(s). Steps never bind to waypoints, wilds, or coast
  subnodes.

See `SKILL.md` for the workflow and `references/design.md` for the rationale.

## Example

`examples/ember-matrix.json` + `examples/ember-matrix.png` — six centers,
synthetic graph, 25 steps dealt, 6 hubs.
