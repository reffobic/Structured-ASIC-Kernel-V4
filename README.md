# Structured ASIC SA Placer

This repository currently contains the Person 1 foundation for the placement
project: netlist parsing, fabric generation, perimeter blocking, and fixed-pin
placement.

## Requirements

- Python 3.10 or newer

No third-party packages are required for the Person 1 parser/fabric demo.

## Run

Parse a design and print the loaded grid:

```bash
python3 placer.py design_1_small.txt
```

Print only the validation summary:

```bash
python3 placer.py design_1_small.txt --no-grid
```

## What The Demo Checks

The loader validates that:

- The header count matches the number of component and net lines.
- Fixed pins are placed only on the one-cell perimeter.
- Movable cells use valid types: `T0`, `T1`, `T2`, or `T3`.
- Every net references known component IDs.
- The generated core has enough legal sites for each cell type.

The console grid uses:

- `P` for fixed pins.
- `0`, `1`, `2`, and `3` for legal core site types.
- `.` for empty perimeter locations.

## Team Handoff

Person 2 can import `parse_netlist` from `placer.py` and receive a fully loaded
`Grid` object:

```python
from placer import parse_netlist

grid = parse_netlist("design_1_small.txt")
```

The `Grid` object owns the generated sites, all `Component` objects, and all
`Net` connectivity data.
