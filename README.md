# Structured ASIC Simulated-Annealing Placement Tool

A simulated annealing-based placer that minimizes total wire length (HPWL) on a Structured ASIC fabric with a fixed-type site grid and perimeter I/O pins.

---

## Requirements

- Python 3.10+
- No external libraries required (uses only the standard library)

For the GUI viewer (`gui.py`):
- `tkinter` (included in most Python installations; on Linux you may need `sudo apt install python3-tk`)

---

## File Structure

```
.
├── main.py            # Entry point — runs the full pipeline
├── Placer.py          # Data structures (grid, component, site, net) + netlist parser
├── Placement.py       # Global placement + legalization
├── SA.py              # Simulated annealing loop + HPWL helpers
├── gui.py             # Tkinter GUI viewer (optional)
├── design_1_small.txt
├── design_2_medium.txt
├── design_3_large.txt
├── design_4_dense.txt
└── design_5_extreme.txt
```

---

## Setup & Compilation

Python does not require compilation. To get the tool running:

1. Make sure Python 3.10 or higher is installed:
   ```bash
   python --version
   ```

2. Clone or download the repository and navigate into it:
   ```bash
   git clone https://github.com/your-repo/Structured-ASIC-Kernel-V4.git
   cd Structured-ASIC-Kernel-V4
   ```

3. No additional dependencies need to be installed. All modules used (`math`, `random`, `argparse`, `pathlib`, `collections`, `tkinter`) are part of the Python standard library.

4. You are ready to run.

---

## How to Run

### Basic usage

```bash
python main.py <netlist_file>
```

Example:
```bash
python main.py design_1_small.txt
```

This runs the full pipeline (parse → global placement → legalization → SA) with the default cooling rate of CR = 0.95 and prints HPWL before/after SA along with runtime stats.

### Specifying a cooling rate

```bash
python main.py design_2_medium.txt --cr 0.85
```

Valid CR range: any float strictly between 0 and 1.

### Using adaptive non-linear cooling

```bash
python main.py design_2_medium.txt --cr 0.95 --nonlinear
```

Enables the adaptive cooling schedule, which adjusts the cooling rate at each temperature step based on the observed acceptance rate. Generally produces better final wire length than fixed cooling at the same CR.

### Showing the ASCII grid

```bash
python main.py design_1_small.txt --show-grid
```

Prints the full grid to the console after SA completes. Each character represents one site:
- `P`: fixed pin
- `0` / `1` / `2` / `3`: placed design cell of that type
- `.`: empty site

---

## GUI Viewer

```bash
python gui.py
```

Opens a window that lets you load any netlist, set a cooling rate, and press **Run** to execute the full pipeline. The viewer shows the placement grid at four stages:

- **Loaded (pins only)**: after parsing, before any cells are placed
- **After global placement**: cells randomly scattered across the core
- **After legalization**: cells moved to type-legal sites
- **After simulated annealing**: final optimized placement

Use the **Stage** dropdown to switch between snapshots. The status bar shows initial HPWL, final HPWL, and accepted/rejected move counts after SA finishes.

---

## Netlist Format

```
[NumCells] [NumNets] [ny] [nx] [NumFixedPins]
[ID] [X] [Y] P          ← fixed pin (first NumFixedPins lines)
[ID] [Type]             ← movable cell, Type is T0/T1/T2/T3
...
[NumAttached] [ID_1] [ID_2] ... [ID_n]   ← net definitions
...
```

Inline comments starting with `#` or `(` are stripped before parsing.

---

## Cooling Schedule 

| Parameter | Formula |
|-----------|---------|
| Initial temperature | `500 × initial_cost` |
| Final temperature | `(5×10⁻⁵ × initial_cost) / num_nets` |
| Temperature update (fixed) | `T = CR × T` |
| Temperature update (nonlinear) | `T = CR_dynamic × T` where `CR_dynamic` adjusts based on acceptance rate |
| Moves per temperature | `20 × num_cells` |

---

## License

MIT License — Copyright (c) 2026 Mohamed El-Refai, Habiba El-Sayed, Haya Shalaby

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
