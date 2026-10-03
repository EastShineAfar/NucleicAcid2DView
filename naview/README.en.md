# NAView — DNA/RNA secondary structure drawing (GUI + CLI)

[简体中文](README.md) ｜ **English**

A Python implementation of the **NAView** layout algorithm
(Bruccoleri & Heinrich, *CABIOS* 4:167–173, 1988) that draws DNA/RNA secondary
structures as flat diagrams. Comes with a GUI, and a command line for scripting.

- 🖥 **GUI**: preview on the left, settings on the right — type a sequence and a
  dot-bracket structure, hit *Preview*, save as SVG
- 🎨 **Colours you can change**: ring fill and letter colour per base, plus ring
  outline / backbone / base-pair line colours
- 🔠 **Size and line widths**: letter size, ring radius, and the three line
  widths (backbone, pair, ring outline) are all adjustable
- 🔃 **Orientation**: 5′ end at the bottom (default) or top, plus free rotation
  with the letters staying upright
- 📏 **Single-line base pairs**, switchable to double lines
- 💾 **Settings are remembered**: one click saves them for next time
- 📦 **Two ways to run it**: the prebuilt `NAView.exe` on Windows (nothing to
  install), or the pure-stdlib source (cross-platform)
- ✅ **Self-checks included**: 233 algorithm, 61 GUI and 41 settings checks in
  `tests/`

> The GUI itself is in Chinese; drawings and the command line are language-neutral.

---

## 1. Using the GUI

| Environment | How to start |
|---|---|
| Windows (prebuilt exe) | double-click `NAView.exe` (see section 4) |
| Windows (from source) | double-click `启动绘图界面.cmd` (same as `launcher.cmd`) |
| Linux / macOS | `./run-gui.sh` |
| Any platform | `python gui.py` |

This is what it looks like — preview on the left, settings panel on the right
(screenshot of the packaged exe):

![NAView GUI](docs/screenshot-exe.png)

### What you can do

| I want to… | How |
|---|---|
| Draw | fill in the sequence and structure, press **预览 / Preview** (<kbd>Ctrl</kbd>+<kbd>Enter</kbd> or <kbd>F5</kbd>) |
| Change a base's ring or letter colour | click the swatch in the 配色 row for that column |
| Change ring outline / backbone / pair colours | the last three swatches in 配色 |
| **Change letter size / ring radius** | 字号 and 圈径 under 尺寸与线宽 (defaults 6.0 / 6.2) |
| **Change line widths** | 骨架线 / 配对线 / 环描边 under 尺寸与线宽 (default 2.0 each) |
| **Put the 5′ end at the bottom or top** | the 起点在下方 checkbox (on by default) |
| **Rotate the whole figure** | the 旋转 slider; the spin box next to it takes an exact angle (15° steps) |
| **Even out the spacing / avoid overlaps** | keep 自动优化间距 ticked (default) |
| Single ↔ double base-pair lines | the radio buttons under 样式 |
| Backbone only / no letters | untick 显示碱基字母 etc. |
| Zoom / pan | mouse wheel; drag with the left button |
| Fit to window | press 适应窗口 |
| **Keep the current settings** | press 保存为默认 |
| Back to factory values | press 恢复出厂 (changes the form only, writes nothing) |
| Export | press 保存 SVG …, pick a path |

> Colour and size changes apply instantly; you only need to press *Preview* again
> after changing the sequence or the structure.

### What the output looks like

Default rendering of this 60 nt sequence
(`...((....))...(((..((((....)))).))).........................`):

![example output](docs/example-seq60.png)

---

## 2. Settings are remembered

Pressing **保存为默认** writes colours, sizes, line widths, orientation, rotation
and all toggles to:

```
from source:  naview/naview-settings.json        ← next to the program
from the exe: naview-exe/naview-settings.json    ← next to NAView.exe
```

It is read back automatically on the next start.

* Plain JSON — you can edit it in Notepad (UTF-8 with or without a BOM is fine).
* It sits next to the program on purpose: **copy the whole folder (or the exe
  plus that json) to another computer and your settings come along**.
* If the folder is read-only (say `Program Files`), it falls back to
  `~/.naview-settings.json` and the status bar tells you where it went.
* To go back to factory settings: delete the json, or press 恢复出厂 and then
  保存为默认.

> The command line does **not** read this file — it only honours its own flags,
> so scripts never change behaviour because of what you clicked.

---

## 3. Command line

```bash
# sequence + structure
python draw_ss.py --seq GCGCAAAAGCGC --struct "((((....))))" -o hairpin.svg

# structure only (letters left out)
python draw_ss.py --struct "...((....))...(((..((((....)))).)))" -o seq60.svg

# double lines + plain black letters
python draw_ss.py --seq GCGCAAAAGCGC --struct "((((....))))" \
                  --pair-style double --mono -o mono.svg

# bigger letters and rings, 5′ end back at the top
python draw_ss.py --seq GCGCAAAAGCGC --struct "((((....))))" \
                  --font-size 12 --ring-radius 9 --no-flip-y -o big.svg

# line widths
python draw_ss.py --seq GCGCAAAAGCGC --struct "((((....))))" \
                  --backbone-width 0.6 --pair-width 2.5 --ring-width 0.4 -o lines.svg

# rotate 90°; read from a file (FASTA sequence and dot-bracket line), or stdin
python draw_ss.py myinput.txt --rotation 90 -o out.svg
cat myinput.txt | python draw_ss.py - -o out.svg

# coordinates only
python draw_ss.py --struct "((((....))))" --coords
```

| Flag | Meaning |
|---|---|
| `-o FILE` | output SVG (stdout if omitted) |
| `--pair-style single\|double` | one or two lines per base pair (default `single`) |
| `--font-size N` | letter size in figure pixels (default 6.0) |
| `--ring-radius N` | base ring radius in figure pixels (default 6.2) |
| `--backbone-width N` | backbone line width in figure pixels (default 2.0) |
| `--pair-width N` | base-pair line width (default 2.0) |
| `--ring-width N` | ring outline width (default 2.0) |
| `--flip-y` / `--no-flip-y` | 5′ end at the bottom (default) / top |
| `--rotation DEG` | rotate the whole figure (default 0; letters stay upright) |
| `--even-loops` / `--no-even-loops` | force / forbid evening out the loop angles (default: pick the better one) |
| `--reference` | turn off all spacing post-processing (raw NAView layout) |
| `--mono` | grey rings, black letters |
| `--title TEXT` | figure title |
| `--base-distance N` | pixels per NAView unit, default 20 |
| `--no-bases` / `--no-pairs` / `--no-backbone` | leave out that element |
| `--open` | open the result when done |
| `--coords` | print a coordinate table (`index x y partner`) |

---

## 4. Copying it to another computer

### 4.1 Prebuilt exe (nothing to install)

Take `NAView.exe` (about 13 MB, 64-bit Windows) from the
**[`naview-exe/`](../naview-exe) folder**, copy it anywhere and double-click it.
Settings are stored in `naview-settings.json` **next to the exe**, so take the
two together and colours, sizes, line widths and rotation come along.

* A one-file exe unpacks itself on every start: **the first launch takes 1–3 s**.
* 64-bit Windows only. For macOS / Linux use the source version below.

**About the “Windows protected your PC” (SmartScreen) prompt**: this program has
no code-signing certificate, so Windows may warn you the first time. Click
**More info** → **Run anyway**; it will not ask again.

> Would buying a certificate remove it? **Basically no.** Microsoft's own docs
> state that a valid OV/EV certificate **still** warns on first download (it just
> shows the publisher name), and reputation accumulates per file hash /
> certificate; **EV certificates no longer bypass SmartScreen**, and a
> self-signed certificate behaves exactly like no signature at all. The only way
> to avoid the prompt entirely is to ship through the Microsoft Store.
> See [SmartScreen reputation (Microsoft Learn)](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/smartscreen-reputation).

Optional integrity check:

```powershell
Get-FileHash .\NAView.exe -Algorithm SHA256
# this build should be 96F062085FD33D0097ED16DC24C36EA73C61920809B30A283FE3763030C5FE85
```

**Rebuilding the exe** (needs Python + PyInstaller):

```powershell
pip install pyinstaller
python -m PyInstaller --noconfirm --clean --onefile --windowed `
    --name NAView --icon naview\appicon.ico --add-data "naview\appicon.ico;." `
    --distpath naview-exe --workpath exe-build --specpath exe-build naview\gui.py
```

### 4.2 Source version (needs Python, works everywhere)

Copy the whole `naview` folder — there are **no third-party dependencies**. You
need Python 3.8+ with tkinter:

| Platform | Notes |
|---|---|
| **Windows** | install from [python.org](https://www.python.org/downloads/) — `tcl/tk and IDLE` is ticked by default. Then double-click `启动绘图界面.cmd`. |
| **macOS** | the python.org installer ships tkinter. |
| **Ubuntu/Debian** | one extra package: `sudo apt install python3-tk` |

If Python is missing, the launcher shows a clear message with a download link
instead of failing silently.

---

## 5. Using it from Python (optional)

```python
import sys
sys.path.insert(0, 'naview')          # path to the naview folder

from naview import parse_dot_bracket, naview_layout
from render_svg import render_svg

layout = naview_layout(parse_dot_bracket('((((....))))'))
layout.xs, layout.ys                  # per-base coordinates, in NAView units
layout.warnings                       # algorithm warnings

svg = render_svg(layout, 'GCGCAAAAGCGC',
                 font_size=6.0, ring_radius=6.2,   # figure pixels
                 backbone_width=2.0, pair_width=2.0, ring_width=2.0,
                 flip_y=True,                      # True: 5′ end at the bottom
                 rotation=0.0)                     # rotate the whole figure
open('out.svg', 'w', encoding='utf-8').write(svg)
```

---

## 6. Files

```
naview/
├── gui.py              tkinter GUI (standard library only)
├── naview.py           layout: dot-bracket parsing + NAView
├── render_svg.py       drawing primitives + SVG export
├── draw_ss.py          command-line entry point
├── settings.py         settings persistence (naview-settings.json)
├── appicon.ico         program icon
├── docs/               screenshots used by this README
├── 启动绘图界面.cmd / launcher.cmd / run-gui.sh    launchers
├── tests/              self-checks (233 algorithm / 61 GUI / 41 settings)
└── README.md / README.en.md
```

---

## 7. Known limitations

- **No pseudoknots**: NAView needs a tree; crossing pairs such as `([)]` are
  rejected with an explanation.
- **It draws, it does not fold**: compute the structure with NUPACK / ViennaRNA /
  mfold and paste it in.
- **Only the NAView layout** is implemented, and the geometry differs from
  VARNA's `naview` mode — it is not pixel-identical.
- Export is SVG only. For PNG, convert the SVG (open it in a browser and
  screenshot, or use `cairosvg`).

---

## 8. Credits and licence

The algorithm is from R.E. Bruccoleri & G. Heinrich, *Computer Applications in
the Biosciences* **4**(1):167–173, 1988.

The reference implementation is `naview.c` (Copyright © 1988 Robert E.
Bruccoleri, copying permitted for non-commercial use); this project is a Python
rewrite based on it and contains no code from GPL projects such as VARNA.
