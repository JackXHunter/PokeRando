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


# National Dex generation ranges (inclusive), for verifying pool coverage.
GEN_BOUNDS = [
    ("Gen 1", 1, 151), ("Gen 2", 152, 251), ("Gen 3", 252, 386),
    ("Gen 4", 387, 493), ("Gen 5", 494, 649), ("Gen 6", 650, 721),
    ("Gen 7", 722, 809), ("Gen 8", 810, 905), ("Gen 9", 906, 1025),
]


def parse_species_numbers(species_h):
    """Return {SPECIES_NAME: dex_number} by tracking enum values
    (explicit '= N' or auto-increment)."""
    nums = {}
    val = -1
    with open(species_h, encoding="utf-8") as f:
        for line in f:
            m = re.match(r"^\s*(SPECIES_[A-Z0-9_]+)\s*(?:=\s*([0-9]+))?\s*,", line)
            if not m:
                continue
            if m.group(2) is not None:
                val = int(m.group(2))
            else:
                val += 1
            nums.setdefault(m.group(1), val)
    return nums


def list_pool_by_generation(species_h, max_species=None):
    pool = load_species_pool(species_h, max_species, verbose=False)
    nums = parse_species_numbers(species_h)
    print(f"Species pool: {len(pool)} eligible base species\n")
    buckets = {name: 0 for name, _, _ in GEN_BOUNDS}
    other = 0
    for sp in pool:
        n = nums.get(sp)
        placed = False
        if n is not None:
            for name, lo, hi in GEN_BOUNDS:
                if lo <= n <= hi:
                    buckets[name] += 1
                    placed = True
                    break
        if not placed:
            other += 1
    for name, lo, hi in GEN_BOUNDS:
        bar = "#" * (buckets[name] // 5)
        print(f"  {name}  (#{lo}-{hi}): {buckets[name]:4}  {bar}")
    if other:
        print(f"  Custom/other        : {other:4}  (fork additions / unranged)")


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
def randomize_starters(path, pool, rng, unique=True):
    with open(path, encoding="utf-8") as f:
        text = f.read()
    m = re.search(r"(sStarterMon\s*\[[^\]]*\]\s*=\s*\{)(.*?)(\};)", text, re.DOTALL)
    if not m:
        print("  starters: sStarterMon[] not found -- skipped (tell me the format)")
        return
    head, body, tail = m.group(1), m.group(2), m.group(3)
    n = len(re.findall(r"SPECIES_|STARTER", body)) or 3
    if unique:
        picks = rng.sample(pool, min(n, len(pool)))
    else:
        picks = [rng.choice(pool) for _ in range(n)]
    new_body = "\n    " + ",\n    ".join(picks) + ",\n"
    text = text[:m.start()] + head + new_body + tail + text[m.end():]
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"  starters: set to {', '.join(picks)}")


# --------------------------------------------------------------------------- #
#  Settings
# --------------------------------------------------------------------------- #
DEFAULT_SETTINGS = {
    "randomize_wild": True,
    "randomize_trainers": True,
    "randomize_starters": True,
    "unique_starters": True,
}
SETTINGS_HELP = {
    "randomize_wild": "Randomize wild Pokemon encounters",
    "randomize_trainers": "Randomize trainer (foe) Pokemon",
    "randomize_starters": "Randomize the three starter Pokemon",
    "unique_starters": "Force the starters to be three different species",
}


def load_settings(path):
    settings = dict(DEFAULT_SETTINGS)
    if path and os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            user = json.load(f)
        for k in DEFAULT_SETTINGS:
            if k in user:
                settings[k] = user[k]
    return settings


def write_default_settings(path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(DEFAULT_SETTINGS, f, indent=2)
        f.write("\n")
    print(f"Wrote default settings to {path}")


# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser(description="Hen-style source randomizer for pokeemerald-expansion")
    ap.add_argument("--seed", type=int, default=None,
                    help="seed for reproducible runs (random if omitted)")
    ap.add_argument("--root", default=".", help="project root (default: current dir)")
    ap.add_argument("--settings", default=None,
                    help="path to settings JSON (default: <root>/hen_settings.json)")
    ap.add_argument("--show", action="store_true",
                    help="print the resolved settings and the seed, then exit")
    ap.add_argument("--list-pool", action="store_true",
                    help="print the species pool broken down by generation, then exit")
    ap.add_argument("--init-settings", action="store_true",
                    help="write a default hen_settings.json you can edit, then exit")
    ap.add_argument("--manifest", default=None,
                    help="write a JSON record of seed+settings used (for sharing/viewing)")
    ap.add_argument("--max-species", type=int, default=None, help="cap pool to first N (debug)")
    args = ap.parse_args()

    root = args.root
    settings_path = args.settings or os.path.join(root, "hen_settings.json")

    if args.init_settings:
        write_default_settings(settings_path)
        return

    if args.list_pool:
        list_pool_by_generation(os.path.join(root, "include/constants/species.h"),
                                args.max_species)
        return

    settings = load_settings(settings_path)
    seed = args.seed if args.seed is not None else random.randrange(1, 2**31 - 1)

    if args.show:
        src = settings_path if os.path.isfile(settings_path) else "built-in defaults"
        print(f"Randomization settings (from {src}):")
        for k in DEFAULT_SETTINGS:
            print(f"  {k:20} = {str(settings[k]):5}   # {SETTINGS_HELP[k]}")
        print(f"  {'seed (this run)':20} = {seed}")
        return

    rng = random.Random(seed)
    species_h = os.path.join(root, "include/constants/species.h")
    wild_json = os.path.join(root, "src/data/wild_encounters.json")
    trainers  = os.path.join(root, "src/data/trainers.party")
    starters  = os.path.join(root, "src/starter_choose.c")

    if not os.path.isfile(species_h):
        sys.exit(f"ERROR: {species_h} not found -- run from project root or pass --root")

    print(f"Seed: {seed}")
    pool = load_species_pool(species_h, args.max_species)

    did = []
    if settings["randomize_wild"] and os.path.isfile(wild_json):
        randomize_wild(wild_json, pool, rng); did.append("wild")
    if settings["randomize_trainers"] and os.path.isfile(trainers):
        randomize_trainers(trainers, pool, rng); did.append("trainers")
    if settings["randomize_starters"] and os.path.isfile(starters):
        randomize_starters(starters, pool, rng, settings["unique_starters"]); did.append("starters")

    if args.manifest:
        with open(args.manifest, "w", encoding="utf-8") as f:
            json.dump({"seed": seed, "randomized": did,
                       "species_pool_size": len(pool), "settings": settings},
                      f, indent=2)
            f.write("\n")
        print(f"  manifest: {args.manifest}")

    print("Done. Now rebuild:  make -j$(nproc)")


if __name__ == "__main__":
    main()
