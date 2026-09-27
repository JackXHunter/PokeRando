#!/usr/bin/env bash
# new_seed.sh -- generate a fresh randomized pokeemerald ROM with a new seed.
#
# Usage:
#   ./new_seed.sh            # random seed
#   ./new_seed.sh 12345      # specific seed (reproducible)
#
# Works whether the project was cloned with git OR downloaded as a ZIP.
# The 3 source data files are randomized only DURING the build and restored to
# their original state afterward, so your repo stays clean.
set -euo pipefail
cd "$(dirname "$0")"                 # run from the project root (where this lives)

# A 30-bit random seed if none was given on the command line.
SEED="${1:-$(( (RANDOM << 15) | RANDOM ))}"

DATA=(src/data/wild_encounters.json src/data/trainers.party src/starter_choose.c)
PRISTINE=.hen_pristine

# pokeemerald-expansion stamps a version from git history; ZIP downloads have
# none and the build would stop. This tells it to continue anyway.
touch .histignore 2>/dev/null || true

echo
echo "[1/3] Preparing data (seed ${SEED})..."

# Capture the ORIGINAL (un-randomized) data once. Prefer git (pristine even if
# the working copy is already randomized); if there is no git history (ZIP
# download), fall back to the current files -- pristine on a fresh download.
if [ ! -d "$PRISTINE" ]; then
    echo "      saving a one-time pristine snapshot of the Pokemon data..."
    for f in "${DATA[@]}"; do
        mkdir -p "$PRISTINE/$(dirname "$f")"
        if git rev-parse --git-dir >/dev/null 2>&1 \
           && git show "HEAD:$f" > "$PRISTINE/$f" 2>/dev/null; then
            :                                   # got pristine copy from git
        else
            cp "$f" "$PRISTINE/$f"              # no git: use current (fresh) file
        fi
    done
fi

restore_pristine() { for f in "${DATA[@]}"; do cp "$PRISTINE/$f" "$f" 2>/dev/null || true; done; }

# Always leave the working tree clean when we exit (success OR failure), so the
# randomized data never shows up as uncommitted changes in git.
trap restore_pristine EXIT

restore_pristine                     # start from pristine data

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
# (trap restores the source data to pristine here, on exit)

echo
echo "=================================================="
echo " New randomized game ready:"
echo "   ROM      : roms/pokeemerald_seed${SEED}.gba"
echo "   Settings : roms/pokeemerald_seed${SEED}.txt"
echo "   Seed     : ${SEED}   (reuse to reproduce this exact game)"
echo "=================================================="
