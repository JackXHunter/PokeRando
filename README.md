# PokeRando — a randomized pokeemerald++

Generate your own **randomized** version of this Pokémon game. It shuffles
**wild Pokémon, trainer teams, and starters** — including the extra Pokémon this
fork adds — and builds a `.gba` you can play in an emulator or on a flashcart.

There are **two ways** to make a randomized ROM. Pick whichever suits you:

| Way | Best for | Install needed |
|-----|----------|----------------|
| **A. GitHub Actions** | Anyone — works in the browser | Nothing (just a GitHub account) |
| **B. Double-click `.bat`** | Windows users who want it local | WSL, one-time setup |

---

## Option A — Make a ROM in your browser (no install)

1. **Fork** this repo — click **Fork** (top-right of the GitHub page).
2. On your fork, open the **Actions** tab. If prompted, click
   **"I understand my workflows, go ahead and enable them."**
3. In the left list, click **Randomize ROM** → **Run workflow**.
   - Leave the seed blank for a random game, or type a number to get a specific,
     repeatable one.
   - Click the green **Run workflow** button.
4. Wait ~3–5 minutes. Click the finished run, scroll down to **Artifacts**, and
   download **`randomized-rom`**.
5. Unzip it. Inside is your `pokeemerald_seed<NUMBER>.gba` (the game) and a
   `.txt` file listing the settings that were used.

To make another seed, just **Run workflow** again. That's it.

---

## Option B — Double-click launcher on Windows

This builds the ROM on your own PC. It needs **WSL** (Windows Subsystem for
Linux) set up once. After that, it's double-click-and-go.

### Step 1 — Install WSL (one time)

1. Click **Start**, type **PowerShell**, right-click it and choose
   **Run as administrator**.
2. In the blue window, paste this and press Enter:
   ```powershell
   wsl --install
   ```
3. **Restart your PC** when it asks.
4. After restarting, an **Ubuntu** window opens automatically and asks you to
   create a **username** and **password**. Type any you like.
   *(The password stays invisible as you type — that's normal. Press Enter.)*

### Step 2 — Install the build tools (one time)

In that **Ubuntu** window, paste this single line and press Enter (type your
password if asked):

```bash
sudo apt update && sudo apt install -y build-essential binutils-arm-none-eabi gcc-arm-none-eabi git libpng-dev pkg-config python3
```

Let it finish. You only ever do Steps 1–2 once.

### Step 3 — Make a ROM

1. Download/clone this project to a folder on your PC.
2. **Double-click `randomize.bat`.**
   - For a specific seed, open a Command Prompt in the folder and run
     `randomize.bat 12345`.
3. After a few minutes, your ROM appears in the **`roms`** folder as
   `pokeemerald_seed<NUMBER>.gba`.

Open that `.gba` in an emulator like [mGBA](https://mgba.io/), or copy it to a
flashcart to play on real hardware.

---

## Changing what gets randomized

Open **`hen_settings.json`** in any text editor and set a value to `false` to
leave that part untouched:

```json
{
  "randomize_wild": true,
  "randomize_trainers": true,
  "randomize_starters": true,
  "unique_starters": true
}
```

Handy commands (run in WSL/terminal from the project folder):

```bash
python3 hen_randomizer.py --show        # view current settings
python3 hen_randomizer.py --list-pool   # see which Pokémon/generations are included
```

---

## Seeds

- The **seed** is the number that decides the randomization. The **same seed
  always makes the same game** — great for sharing a run with a friend or
  racing the same layout.
- Each ROM is saved with its seed in the filename, and a matching `.txt` records
  the exact settings used.

---

## Troubleshooting

- **`randomize.bat` flashes and closes / "command not found":** WSL isn't set up
  yet — do Steps 1–2 above.
- **`bad interpreter` error:** the launcher auto-fixes this, but if you hit it,
  run `sed -i 's/\r$//' new_seed.sh` once in WSL.
- **Build fails on the GitHub Action:** open the failed run and copy the error;
  it's usually a missing build dependency that's quick to add.

---

## Notes

- Every seed produces a full new `.gba` — there's no "live" randomization (the
  same is true of other randomizers).
- Please share the **project** (this repo), not finished `.gba` files: the source
  is fine to distribute, but ROMs contain copyrighted game assets.
