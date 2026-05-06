from __future__ import annotations
import argparse
from pathlib import Path
import random
from Placer import netlist_error, parse_netlist, print_summary
from initialPlacement import legalize, total_hpwl
from SA import SA_loop

# Set a fixed seed for reprodicibility for easier testing 
seed = 42
random.seed(seed)

def global_placement(g):
    """
    Deterministic global placement. For each movable cell, pick a random, empty coordinate on the core area.
    Returns number of placed cells. 
    """

    placed = 0

    # Build a list of all possible (non-perimeter) empty coordinates
    empty_sites: list[tuple[int, int]] = []
    for s in g.iter_core_sites(): # Fetch all core sites to populate empty_sites 
        if s.is_empty:
            empty_sites.append((s.x, s.y))

    for cell in g.movable_cells():
        if cell.placement_x is not None and cell.placement_y is not None: # If the cell already has coordinates
            continue

        if not empty_sites:
            raise netlist_error("No empty core sites left for placement.")

        idx = random.randrange(len(empty_sites))
        x, y = empty_sites.pop(idx)
        g.attach_cell_to_at(cell.component_id, x, y)
        placed += 1

    return placed


def count_placed_cells(g):
    '''
    Helper function to count placed cells, for logging outputs. 
    '''
    return sum(1 for c in g.movable_cells() if c.placement_x is not None and c.placement_y is not None)


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Run full placement pipeline: parse -> init -> legalize -> SA.")
    p.add_argument("netlist", type=Path, help="Path to a design_*.txt netlist file.")
    p.add_argument("--cr", type=float, default=0.95, help="Cooling rate (0<CR<1).")
    p.add_argument("--show-grid", action="store_true", help="Render ASCII grid at the end (after SA).")
    p.add_argument("--show-initial-grid", action="store_true", help="Also render grid right after parsing (pins only).")
    return p


def main():
    args = build_arg_parser().parse_args()

    # Parse user's netlist file into our grid data structure
    try:
        g = parse_netlist(args.netlist)
    except netlist_error as exc:
        print(f"Netlist error: {exc}")
        return 1

    # Show loaded netlist. By default, don't render grid here (it's pins-only at this stage)
    print_summary(g, args.netlist,1)
    
    # 1) Global placement (so every movable cell gets random placement_x/placement_y)
    newly_placed = global_placement(g)
    print(f"\nGlobalplacement: placed {newly_placed} previously-unplaced cells.")
    print_summary(g, args.netlist,1) # logging output 
    
    # 2) Legalize (ensure legal site type + no overlaps)
    legalize(g)
    placed_after_legalize = count_placed_cells(g)
    total_cells = len(g.movable_cells())
    if placed_after_legalize != total_cells:
        raise netlist_error(f"After legalization, only {placed_after_legalize}/{total_cells} cells are placed.")
    print_summary(g, args.netlist,1) # logging output
    
    hpwl_before = total_hpwl(g)
    print(f"HPWL before SA: {hpwl_before}") # logging output
    
    # 3) Simulated annealing optimization (detailed placement)
    CR = 0.75 # still need to add a loop with all the CRs
    final_cost, accepted, rejected = SA_loop(CR,g)
    hpwl_after = total_hpwl(g)
    print(f"SA stats: accepted={accepted}, rejected={rejected}")
    print(f"HPWL after SA:  {hpwl_after} (SA returned {final_cost})")
    print_summary(g, args.netlist,1)

    return 0

if __name__ == "__main__":
    raise SystemExit(main())

