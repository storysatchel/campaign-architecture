#!/usr/bin/env python3
"""
Minimal Python port of the dunmanifestin palette engine
(https://github.com/gavmor/dunmanifestin), sufficient for place-name
manifestation from https://github.com/gavmor/dunmanifestin-palettes.

Supports: |titled| sections, // comments, N@ repetition, [palette] and
[palette.inflection] references (titleize, capitalize), churn (no repeats).

Palettes are fetched from the palettes repo and cached under ./palettes/.
Two palettes referenced by the fantasy set but never defined there get
curated fallbacks: `word` (evocative nouns) and `animal`.
"""
import os
import random
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "..", "..", "github", "bin"))
from gh_push import api

PALETTE_FILES = [
    "common/placeName.pal",
    "common/regionName.pal",
    "common/color.pal",
    "common/bodyPart.pal",
    "fantasy/namePrefix.pal",
    "fantasy/nameSuffix.pal",
    "fantasy/placeSuffix.pal",
    "fantasy/element.pal",
]

CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "palettes")

FALLBACKS = {
    # `word`: evocative nouns (the fantasy set references [word] but defines no word.pal)
    "word": """ash|thorn|ember|frost|stone|raven|wolf|storm|grim|oak|iron|silver|
        mist|hollow|barrow|cairn|fen|moor|heath|weald|combe|tor|dale|crag|fell|
        wick|holt|shaw|den|ley|stead|gar|mouth|ford|gate|brook|burn|beck|firth|
        ness|holm|ey|shaw|mor|kel|dun|rath|caer|pen|tre|lan|hall|borg|frost|night|
        ember|ashen|hollow|grim|wild|still|red|black|white|gray|pale|wan|dire""",
    # `animal`: the fantasy namePrefix references [animal.titleize]; no animal.pal exists
    "animal": """raven|wolf|fox|owl|bear|hart|boar|stag|wren|hawk|rook|badger|
        otter|weasel|stoat|hare|hound|mare|ram|ewe|swan|crane|heron|thrush|lark""",
}


def titleize(s):
    return " ".join(w[:1].upper() + w[1:] for w in s.split(" "))


def apply_inflections(s, inflections):
    for inf in inflections:
        if inf == "titleize":
            s = titleize(s)
        elif inf == "capitalize":
            s = s[:1].upper() + s[1:] if s else s
    return s


class MissingPalette(Exception):
    pass


class Engine:
    def __init__(self, rng=None):
        self.rng = rng or random.Random()
        self.palettes = {}
        self._used = set()

    def load_text(self, text):
        for chunk in re.split(r"\n(?=\|)", text):
            chunk = chunk.strip()
            if not chunk:
                continue
            lines = chunk.split("\n")
            m = re.match(r"\|(\w+)", lines[0])
            if not m:
                continue
            name = m.group(1)
            phrases = []
            for line in lines[1:]:
                line = re.sub(r"//.*$", "", line).strip()
                if not line or line.startswith("#"):
                    continue
                rm = re.match(r"(\d+)@(.*)$", line)
                if rm:
                    phrases.extend([rm.group(2)] * int(rm.group(1)))
                else:
                    phrases.append(line)
            if phrases:
                self.palettes.setdefault(name, []).extend(phrases)

    def load_fallbacks(self):
        for name, text in FALLBACKS.items():
            words = [w.strip() for w in text.split("|") if w.strip()]
            self.palettes.setdefault(name, []).extend(words)

    def manifest(self, palette_name, phrase=None, _depth=0):
        if _depth > 12:
            raise RuntimeError("palette recursion too deep")
        if palette_name not in self.palettes:
            raise MissingPalette(palette_name)
        phrases = self.palettes[palette_name]
        order = list(range(len(phrases)))
        self.rng.shuffle(order)
        last_err = None
        for idx in order:
            if phrase is not None and phrases[idx] != phrase:
                continue
            try:
                out = self._reify(phrases[idx], _depth)
            except MissingPalette as e:
                last_err = e
                continue
            key = (palette_name, out)
            if key in self._used:
                continue
            self._used.add(key)
            return out
        # everything used or missing: allow a repeat rather than fail
        idx = self.rng.randrange(len(phrases))
        try:
            return self._reify(phrases[idx], _depth)
        except MissingPalette:
            raise last_err or MissingPalette(palette_name)

    def _reify(self, dsl, _depth):
        tokens = re.split(r"[\[\]]", dsl)
        out = []
        for i, tok in enumerate(tokens):
            if i % 2 == 0:
                out.append(tok)
            else:
                parts = tok.split(".")
                name, inflections = parts[0], parts[1:]
                val = self.manifest(name, _depth=_depth + 1)
                out.append(apply_inflections(val, inflections))
        return "".join(out)


def fetch_palettes():
    os.makedirs(CACHE, exist_ok=True)
    texts = {}
    for p in PALETTE_FILES:
        cache_path = os.path.join(CACHE, p.replace("/", "_"))
        if os.path.exists(cache_path):
            with open(cache_path) as f:
                texts[p] = f.read()
        else:
            import base64
            r = api("GET", f"/repos/gavmor/dunmanifestin-palettes/contents/{p}")
            if not r or "content" not in r:
                print(f"could not fetch {p}", file=sys.stderr)
                continue
            texts[p] = base64.b64decode(r["content"]).decode()
            with open(cache_path, "w") as f:
                f.write(texts[p])
    return texts


def build_engine(seed=20260919):
    eng = Engine(random.Random(seed))
    for text in fetch_palettes().values():
        eng.load_text(text)
    eng.load_fallbacks()
    return eng


if __name__ == "__main__":
    eng = build_engine()
    for _ in range(12):
        print(eng.manifest("placeName"))
