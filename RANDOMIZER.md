# pokeemerald++ Randomizer

A randomizer for this fork. It edits the game's data and rebuilds the ROM, so
it randomizes **every** Pokémon in the project — including the new ones this
fork adds (which tools like Universal Pokémon Randomizer can't touch).

Currently randomizes: **wild encounters, trainer teams, starters**.

---

## Easiest way — make a ROM in your browser (no install)

You only need a (free) GitHub account.

1. **Fork** this repo (top-right **Fork** button).
2. Open the **Actions** tab on your fork. Click **"I understand my workflows, go ahead and enable them."**
3. Pick **"Randomize ROM"** on the left → **Run workflow** → optionally type a seed → **Run workflow**.
4. Wait ~3–5 minutes. Open the finished run → scroll to **Artifacts** → download **`randomized-rom`**.
5. Unzip it → you get `pokeemerald_seed<N>.gba` (play it in mGBA or on a flashcart) and a `.txt` listing the exact settings used.

That's it — a new seed is just **Run workflow** again with a different number.

---

## On your own computer

### One-command new seed
```bash
chmod +x new_seed.sh        # once
./new_seed.sh               # random seed -> roms/pokeemerald_seed<N>.gba
./new_seed.sh 12345         # specific seed (reproducible)
```
Each run restores the original data, randomizes, rebuilds, and saves the ROM
plus a settings record into `roms/`.

### Getting a build environment

**Docker (no toolchain install):**
```bash
docker build -t emerald-randomizer .
docker run --rm -v "$PWD":/project emerald-randomizer ./new_seed.sh
```

**Native (Linux / WSL):**
```bash
sudo apt install build-essential binutils-arm-none-eabi gcc-arm-none-eabi \
                 git libpng-dev pkg-config python3
./new_seed.sh
```

---

## Choosing what gets randomized
```bash
python3 hen_randomizer.py --init-settings   # create hen_settings.json
python3 hen_randomizer.py --show            # view current settings
python3 hen_randomizer.py --list-pool       # see species pool, by generation
```
Edit `hen_settings.json` and set any value to `false` to leave it vanilla.

---

## Files
| File | What it is |
|------|------------|
| `hen_randomizer.py` | The randomizer (edits source data) |
| `new_seed.sh` | One-command launcher |
| `hen_settings.json` | Which categories to randomize |
| `Dockerfile` | Local build environment |
| `.github/workflows/randomize.yml` | Browser-based "Run workflow" build |

## Notes
- Share the **project** (source), not built `.gba` files — source is legal to
  distribute; ROMs contain copyrighted assets.
- Every seed produces a full new `.gba` (the same is true of Universal Pokémon
  Randomizer); there is no "live" randomization. Rebuilds after the first are
  fast because only the data files change.
