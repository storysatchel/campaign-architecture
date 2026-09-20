# Lessons from the Candy Land Build

- Visual grounding returns approximate positions (errors of 30–40 px observed). Always verify with a tight crop and correct by hand.
- The hand-traced track deviated from the printed board by up to 1.4 units. This silently misplaced six waypoint seeds until the squares were measured directly. **Never snap to a traced path.**
- The first survey missed the gumdrop picture square; the sweep caught it. **Sweep every time.**
- When a marker looks "not-quite-there," check the seed position before touching the renderer — it has always been the data, not the drawing.
- Detection proposed wrong candidates twice (landed on a licorice square instead of a gumdrop). **Detection proposes; verification decides.**
- The finite-Voronoi outward normal must use the cloud-center sign rule: `sign(dot(ridge midpoint − cloud center, normal)) × normal`. Midpoint-minus-seed is perpendicular to the normal and silently wrong.
