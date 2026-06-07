#!/usr/bin/env python3
"""
hen_randomizer.py
=================
Source-level randomizer for pokeemerald-expansion forks.

Reproduces the randomizing parts of the "Hen" UPR ruleset by editing the
decomp's *source data* in place, so it works on a custom fork (new Pokemon
included). After running, rebuild with `make -j$(nproc)`.

Covers (matching the Hen settings):
  * Wild Pokemon  -> Random
  * Trainer Pokemon -> Random (species swapped; moves/ability left to default,
                       which matches "Movesets: Unchanged" and keeps legality)
  * Starters -> Random

Run from your project root, e.g.:
    python3 hen_randomizer.py --seed 12345

Use the SAME --seed to reproduce the same randomization. Commit or back up
your repo first -- this edits files in place.
"""

import argparse
import json
import os
import random
import re
import sys

# Forme markers: an enum entry is an alternate forme (excluded) if its name
# ends with one of these, or contains it followed by '_' (e.g. _MEGA_X).
# Boundary-aware so SPECIES_MEGANIUM is NOT mistaken for a Mega forme.
FORM_MARKERS = (
    "_MEGA", "_PRIMAL", "_ALOLAN", "_GALARIAN", "_HISUIAN", "_PALDEAN",
    "_GIGANTAMAX", "_GMAX", "_TOTEM", "_ETERNAMAX", "_BLOODMOON",
)
# Substrings that mark non-Pokemon sentinel/util entries (excluded).
SENTINEL_BITS = ("_START", "_END", "_COUNT", "_TAG", "NUM_", "_CUSTOM")
HARD_EXCLUDE = {"SPECIES_NONE", "SPECIES_EGG", "NUM_SPECIES"}

ENUM_LINE_RE = re.compile(r"^\s*(SPECIES_[A-Z0-9_]+)\s*(?:=|,)")


def _is_forme(name):
    for m in FORM_MARKERS:
        if name.endswith(m) or (m + "_") in name:
            return True
    return False


def _is_sentinel(name):
    return name in HARD_EXCLUDE or any(b in name for b in SENTINEL_BITS)


def load_species_pool(species_h, max_species=None, verbose=True):
    """Parse include/constants/species.h enum and return base SPECIES_
    identifiers usable as the random pool.

    Strategy that matches the expansion layout: base national-dex species come
    first, then ONE contiguous block of alternate formes (mega/regional/
    cosmetic), then a user 'custom species' region. We collect base species up
    to the first forme, which gates out the whole forme block, then also pick
    up any species inside the SPECIES_CUSTOM_START..SPECIES_CUSTOM_END region
    (where a fork adds its own new Pokemon)."""
    pool = []
    seen = set()
    base_done = False        # flips True once the forme block starts
    in_custom = False
    with open(species_h, encoding="utf-8") as f:
        for line in f:
            m = ENUM_LINE_RE.match(line)
            if not m:
                continue
            name = m.group(1)
            if name in seen:
                continue
            seen.add(name)
            if name.startswith("SPECIES_CUSTOM_START"):
                base_done = True
                in_custom = True
                continue
            if name.startswith("SPECIES_CUSTOM_END"):
                in_custom = False
                continue
            if _is_sentinel(name):
                continue
            if _is_forme(name):
                base_done = True     # reached the forme block; skip it entirely
                continue
            if (not base_done) or in_custom:
                pool.append(name)
    if max_species is not None:
        pool = pool[:max_species]
    if verbose:
        print(f"  species pool: {len(pool)} base species "
              f"({pool[0]} .. {pool[-1]})")
    if len(pool) < 50:
        sys.exit("ERROR: species pool too small -- check species.h path/format.")
    return pool


# --------------------------------------------------------------------------- #
#  Wild Pokemon (wild_encounters.json)
# --------------------------------------------------------------------------- #
def randomize_wild(path, pool, rng):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    count = [0]

    def walk(node):
        if isinstance(node, dict):
            for k, v in node.items():
                if k == "species" and isinstance(v, str) and v.startswith("SPECIES_"):
                    node[k] = rng.choice(pool)
                    count[0] += 1
                else:
                    walk(v)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(data)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    print(f"  wild: randomized {count[0]} encounter slots")


# --------------------------------------------------------------------------- #
#  Trainers (trainers.party)
# --------------------------------------------------------------------------- #
# Lines that are Pokemon-stat fields (kept). Anything else on the first line of
# a mon block is the species line.
MON_FIELD_RE = re.compile(
    r"^(Level|IVs|EVs|Ability|Nature|Happiness|Friendship|Ball|Shiny|"
    r"Dynamax Level|Tera Type|Gigantamax|Status|Nickname)\s*:",
    re.IGNORECASE,
)
GENDER_RE = re.compile(r"\((M|F)\)")
ITEM_RE = re.compile(r"@.*$")


def _new_species_line(old_line, new_species):
    """Build a replacement species line keeping gender + held item."""
    item = ""
    m = ITEM_RE.search(old_line)
    if m:
        item = " " + m.group(0).strip()
    gender = ""
    g = GENDER_RE.search(old_line.split("@")[0])
    if g:
        gender = " " + g.group(0)
    return f"{new_species}{gender}{item}"


def randomize_trainers(path, pool, rng):
    with open(path, encoding="utf-8") as f:
        raw = f.read()
    blocks = re.split(r"\n\s*\n", raw)
    mon_count = 0
    seen_header = False          # everything before first "===" is preamble
    out_blocks = []
    for block in blocks:
        lines = block.split("\n")
        first = lines[0].lstrip("﻿").strip()
        if first.startswith("==="):
            seen_header = True
            out_blocks.append(block)          # trainer header + metadata: keep
            continue
        if not seen_header or first == "":
            out_blocks.append(block)          # file comment / preamble: keep
            continue
        # A Pokemon entry inside a trainer. lines[0] is the species line.
        new_lines = [_new_species_line(lines[0], rng.choice(pool))]
        for ln in lines[1:]:
            s = ln.strip()
            if s.startswith("- "):
                continue                       # drop explicit moves -> defaults
            if s.lower().startswith(("ability:", "nature:", "gigantamax")):
                continue                       # drop -> legal defaults for new mon
            new_lines.append(ln)
        out_blocks.append("\n".join(new_lines))
        mon_count += 1
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n\n".join(out_blocks))
    print(f"  trainers: randomized {mon_count} trainer Pokemon")


# --------------------------------------------------------------------------- #
#  Starters (src/starter_choose.c)
# --------------------------------------------------------------------------- #
def randomize_starters(path, pool, rng):
    with open(path, encoding="utf-8") as f:
        text = f.read()
    m = re.search(r"(sStarterMon\s*\[[^\]]*\]\s*=\s*\{)(.*?)(\};)", text, re.DOTALL)
    if not m:
        print("  starters: sStarterMon[] not found -- skipped (tell me the format)")
        return
    head, body, tail = m.group(1), m.group(2), m.group(3)
    n = len(re.findall(r"SPECIES_|STARTER", body)) or 3
    picks = rng.sample(pool, min(n, len(pool)))   # unique starters
    new_body = "\n    " + ",\n    ".join(picks) + ",\n"
    text = text[:m.start()] + head + new_body + tail + text[m.end():]
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"  starters: set to {', '.join(picks)}")


# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser(description="Hen-style source randomizer for pokeemerald-expansion")
    ap.add_argument("--seed", type=int, default=None, help="seed for reproducible runs")
    ap.add_argument("--root", default=".", help="project root (default: current dir)")
    ap.add_argument("--max-species", type=int, default=None,
                    help="cap species pool to first N (debug)")
    ap.add_argument("--skip", default="", help="comma list: wild,trainers,starters")
    args = ap.parse_args()

    rng = random.Random(args.seed)
    skip = {s.strip() for s in args.skip.split(",") if s.strip()}
    root = args.root

    species_h = os.path.join(root, "include/constants/species.h")
    wild_json = os.path.join(root, "src/data/wild_encounters.json")
    trainers  = os.path.join(root, "src/data/trainers.party")
    starters  = os.path.join(root, "src/starter_choose.c")

    if not os.path.isfile(species_h):
        sys.exit(f"ERROR: {species_h} not found -- run from project root or pass --root")

    print(f"Seed: {args.seed}")
    pool = load_species_pool(species_h, args.max_species)

    if "wild" not in skip and os.path.isfile(wild_json):
        randomize_wild(wild_json, pool, rng)
    if "trainers" not in skip and os.path.isfile(trainers):
        randomize_trainers(trainers, pool, rng)
    if "starters" not in skip and os.path.isfile(starters):
        randomize_starters(starters, pool, rng)

    print("Done. Now rebuild:  make -j$(nproc)")


if __name__ == "__main__":
    main()
