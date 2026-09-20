# Survey Method

The foundation. Everything starts here.

## Point kinds (in order)

### 1. Figures → capitals
Character pieces, standees, portraits printed on the board. Each one is a faction's natural seat. Measure the figure's base position.

### 2. Named locations → supply centers
Tiles or spaces that carry a location's name or its distinctive symbol. The symbol-bearing tile IS the canonical marker for that location — not the nearest path point, not the label text position.

### 3. Special spaces → waypoint seeds
Hazard squares, boons, teleports, "lose a turn" spaces, picture/card destinations — anything with a special rule. These are free Schelling points: everyone already coordinates on them.

### 4. Distinct geography → wild/water seeds
Off-path regions with clear visual identity (seas, forests, mountains, swamps).

## Measuring

- **Crop tight** around each candidate and **measure the center**: square center for spaces, figure base for characters.
- Record normalized `(fx, fy)` in 0–1, origin top-left.
- **Verify with an overlay**: plot every measured point on the board image and LOOK at it before committing. A single measurement is a hypothesis; the overlay is the test.
- **Sweep for misses**: after the first pass, do a dedicated search for more points of each kind. There is always one more picture square.

## Provenance

Every seed gets a one-line note: how the position was determined (e.g. "square center, cropped 60px window, verified on overlay"). This is what makes the survey auditable and the headless verify possible.
