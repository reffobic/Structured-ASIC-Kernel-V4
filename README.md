# Structured ASIC SA Placer

Team project for a simulated-annealing placer on a structured ASIC grid.  
My part was the groundwork: read the netlists, build the fabric (the repeating  
5x5 tile pattern), keep the perimeter for pins only, and load everything into  
a grid object my teammate can plug their placement logic into.

You need Python 3.10+ installed. No extra pip packages for what I have so far.

## How I run it

There is not a separate `main` script yet—I just use Python from the project folder.

Print the board after loading a design:

```bash
python3 -c "from placer import parse_netlist; g = parse_netlist('design_1_small.txt'); print(g.render())"
```

Quick sanity check without dumping the whole grid (counts and that it did not blow up):

```bash
python3 -c "from placer import parse_netlist; g = parse_netlist('design_1_small.txt'); print(g.num_cells, 'cells', g.num_nets, 'nets', g.ny, 'x', g.nx, 'grid')"
```

Swap `design_1_small.txt` for any of the other `design_*.txt` files in the repo.

## What actually gets checked

When you call `parse_netlist`, it walks the file and complains if something is off:  
line counts have to match the header, pins have to sit on the outer ring only,  
cell lines have to be `T0`–`T3`, every net has to point at real component ids,  
and there have to be enough core sites of each type for how many cells of that  
type the design asks for.

If you print `g.render()`, pins show as `P`, core site types as `0`–`3`, and  
empty perimeter slots as `.` (dots).

## For my teammate

If you are doing placement or cost on top of this, import the loader and you get  
a full `Grid` back—sites, components, nets are all wired up:

```python
from placer import parse_netlist

grid = parse_netlist("design_1_small.txt")
# grid.sites, grid.components, grid.nets — go wild
```

That is the handoff from my side.
