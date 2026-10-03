# NAView — DNA/RNA secondary structure drawing

[简体中文](README.md) ｜ **English**

A Python implementation of the **NAView** layout algorithm (Bruccoleri &
Heinrich, *CABIOS* 4:167–173, 1988) that draws DNA/RNA secondary structures as
flat diagrams. It comes with a GUI and a command line, plus a **portable
Windows exe** that needs nothing installed on the target machine.

![NAView GUI](naview-exe/screenshot.png)

---

## Quick start

| I want to | Go to |
|---|---|
| **Just draw something, without installing Python** | download [`naview-exe/NAView.exe`](naview-exe/NAView.exe) (about 13 MB, 64-bit Windows) and double-click it. Details in [naview-exe/README.en.md](naview-exe/README.en.md) |
| **Read the source / use the command line / run on macOS or Linux** | the [`naview/`](naview) folder → details in [naview/README.en.md](naview/README.en.md) |

On first run the exe may trigger “Windows protected your PC” — click
**More info** → **Run anyway**. (Every unsigned application does this; buying a
code-signing certificate does not remove it either — see the exe notes.)

---

## What is in this repository

| Folder | Contents | Docs |
|---|---|---|
| [`naview/`](naview) | **Source**: GUI + command line + layout algorithm, standard library only, no third-party dependencies | [中文](naview/README.md) ｜ [English](naview/README.en.md) |
| [`naview-exe/`](naview-exe) | the prebuilt **`NAView.exe`** (portable, 64-bit Windows) | [中文](naview-exe/README.md) ｜ [English](naview-exe/README.en.md) |

---

## Features

- 🖥 **GUI**: preview on the left, settings on the right — type a sequence and a
  dot-bracket structure, press *Preview*, save as SVG
- 🎨 **Colours you can change**: ring fill and letter colour per base, plus ring
  outline / backbone / base-pair line colours
- 🔠 **Size and line widths**: letter size, ring radius, and three independent
  line widths (backbone, base pair, ring outline)
- 🔃 **Orientation**: 5′ end at the bottom (default) or top, plus free rotation
  with the letters staying upright
- 📏 **Single-line base pairs**, switchable to double lines
- 💾 **Settings are remembered**: one click saves them next to the program, so
  they travel with the folder (or with the exe)
- 📦 **Two ways to run it**: the portable exe (Windows) or the pure-stdlib
  source (cross-platform, Python 3.8+ with tkinter)
- ✅ **Self-checks included**: 233 algorithm, 61 GUI and 41 settings checks

---

## What the output looks like

Default rendering of this 60 nt sequence
(`...((....))...(((..((((....)))).))).........................`):

![example output](naview/docs/example-seq60.png)

---

## Requirements

| | |
|---|---|
| **exe build** | Windows 10 / 11, 64-bit. Nothing to install, works offline |
| **source build** | Python 3.8+ with tkinter (the official Windows installer ticks `tcl/tk and IDLE`; on Ubuntu run `sudo apt install python3-tk`) |
| **export** | SVG vector graphics (scales cleanly, opens in Illustrator / Inkscape / Word) |

---

## Known limitations

- **It draws, it does not fold**: compute the structure with NUPACK / ViennaRNA /
  mfold and paste it in.
- **No pseudoknots**: crossing pairs such as `([)]` are rejected with an explanation.
- **Only the NAView layout** is implemented, and the geometry differs from VARNA's
  `naview` mode — not pixel-identical.
- SVG export only; convert it to PNG separately (open in a browser, or use `cairosvg`).

---

## Credits and licence

The layout algorithm is from R.E. Bruccoleri & G. Heinrich, *Computer
Applications in the Biosciences* **4**(1):167–173, 1988.

The reference implementation is `naview.c` (Copyright © 1988 Robert E.
Bruccoleri, copying permitted for non-commercial use); this project is a Python
rewrite based on it and contains no code from GPL projects such as VARNA.
