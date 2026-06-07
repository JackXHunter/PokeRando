#!/usr/bin/env bash
# new_seed.sh -- generate a fresh randomized pokeemerald ROM with a new seed.
#
# Usage:
#   ./new_seed.sh            # random seed
#   ./new_seed.sh 12345      # specific seed (reproducible)
#
# Each run restores the original Pokemon data, randomizes with the seed,
# rebuilds, and saves the ROM + a settings record into ./roms/.
set -euo pipefail
cd "$(dirname "$0")"                 # run from the project root (where this lives)

# A 30-bit random seed if none was given on the command line.
SEED="${1:-$(( (RANDOM << 15) | RANDOM ))}"

DATA=(src/data/wild_encounters.json src/data/trainers.party src/starter_choose.c)
PRISTINE=.hen_pristine

echo
echo "[1/3] Preparing data (seed ${SEED})..."

# Capture the ORIGINAL (un-randomized) data once, then restore it each run.
if [ ! -d "$PRISTINE" ]; then
    echo "      saving a one-time pristine snapshot (from git HEAD)..."
    for f in "${DATA[@]}"; do
        mkdir -p "$PRISTINE/$(dirname "$f")"
        if ! git show "HEAD:$f" > "$PRISTINE/$f" 2>/dev/null; then
            echo "ERROR: could not read original '$f' from git HEAD."
            echo "Commit the original (un-randomized) data first, or put pristine"
            echo "copies into $PRISTINE/ yourself, then re-run."
            rm -rf "$PRISTINE"
            exit 1
        fi
    done
fi
for f in "${DATA[@]}"; do cp "$PRISTINE/$f" "$f"; done

echo "[2/3] Randomizing..."
mkdir -p roms
MANIFEST="roms/pokeemerald_seed${SEED}.txt"
python3 hen_randomizer.py --seed "$SEED" --manifest "$MANIFEST"

echo "[3/3] Building the ROM -- compiler output follows."
echo "      (First build is slow; new seeds only recompile a few files.)"
echo "----------------------------------------------------------------"
BUILD_START=$SECONDS
make -j"$(nproc)"
BUILD_TIME=$(( SECONDS - BUILD_START ))
echo "----------------------------------------------------------------"
echo "      build finished in ${BUILD_TIME}s."

cp pokeemerald.gba "roms/pokeemerald_seed${SEED}.gba"

echo
echo "=================================================="
echo " New randomized game ready:"
echo "   ROM      : roms/pokeemerald_seed${SEED}.gba"
echo "   Settings : roms/pokeemerald_seed${SEED}.txt"
echo "   Seed     : ${SEED}   (reuse to reproduce this exact game)"
echo "=================================================="
