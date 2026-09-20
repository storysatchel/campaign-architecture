# Headless Survey Verification

The crop-and-look loop needs a human. For an unsupervised harness, replace visual verification with **programmatic color verification**.

## The technique

A seed is correct iff the board underneath it is the right color. Symbols may cover the square's center, so sample a window (45px radius), not a single pixel.

## Usage

```bash
# Find candidate squares by HSV color + shape
python3 bin/survey_auto.py detect --board <image>

# Check every seed sits on its expected square color
python3 bin/survey_auto.py verify --board <image>
```

Pre-render gate:
```bash
python3 bin/survey_auto.py verify --board board.jpg && python3 pipeline.py
```

## How it works

1. **Detect**: converts the board to HSV, applies configurable ranges, finds connected components with area/squareness filters. Emits candidate normalized centers.
2. **Verify**: samples a 45px-radius window around every seed. If the expected-color fraction exceeds 5%, the seed is on its square. Otherwise FAIL.
3. **Fail loudly**: exits non-zero and names the offenders. Never render on a failed verify. Never snap, never guess, never "close enough."

The 5% threshold catches gross misplacements (fraction ~0.00) while tolerating symbol occlusion (fractions 0.08–0.68 observed on good Candy Land seeds).

## Porting to a new board

- Adjust `HSV_RANGES` for the target square colors (sample HSV at known squares).
- Adjust `SQUARE_FRAC_MIN/MAX` for the image resolution.
- Map your survey's `kind` values to color families in `verify()`.
- Run `verify` in CI / before every render. It takes ~1s.

## Honest limits

This verifies **placement of known seeds** — it does not discover new squares, classify symbols, or check completeness. Detection proposes; verification decides. For a new board, the manual survey (`references/method.md`) still finds the points; this script keeps them honest.
