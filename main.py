from __future__ import annotations

import argparse
from pathlib import Path
import random
seed = 42
random.seed(seed)
from Placer import netlist_error, parse_netlist, print_summary, valid_cell_types
from initialPlacement import legalize, total_hpwl
from SA import SA_loop


def global_placement(g) -> int:
    """
    Deterministic initial placement: for each movable cell, pick the first empty core site
    of the matching type.
    """
    placed = 0
    # Build a list of all possible (non-perimeter) empty coordinates
    empty_sites: list[tuple[int, int]] = []
    for s in g.iter_core_sites():
        if s.is_empty:
            empty_sites.append((s.x, s.y))

    for cell in g.movable_cells():
        if cell.placement_x is not None and cell.placement_y is not None:
            continue

        if not empty_sites:
            raise netlist_error("No empty core sites left for placement.")

        idx = random.randrange(len(empty_sites))
        x, y = empty_sites.pop(idx)
        g.attach_cell_to_at(cell.component_id, x, y)
        placed += 1

    return placed


def count_placed_cells(g) -> int:
    return sum(1 for c in g.movable_cells() if c.placement_x is not None and c.placement_y is not None)


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Run full placement pipeline: parse -> init -> legalize -> SA.")
    p.add_argument("netlist", type=Path, help="Path to a design_*.txt netlist file.")
    p.add_argument("--cr", type=float, default=0.95, help="Cooling rate (0<CR<1).")
    p.add_argument("--show-grid", action="store_true", help="Render ASCII grid at the end (after SA).")
    p.add_argument("--show-initial-grid", action="store_true", help="Also render grid right after parsing (pins only).")
    return p


def main() -> int:
    args = build_arg_parser().parse_args()

    try:
        g = parse_netlist(args.netlist)
    except netlist_error as exc:
        print(f"Netlist error: {exc}")
        return 1

    # Show what we loaded. By default, don't render grid here (it's pins-only at this stage).
    print_summary(g, args.netlist,1)
    
    # 1) Initial placement (so every movable cell gets placement_x/placement_y)
    newly_placed = global_placement(g)
    print(f"\nInitial placement: placed {newly_placed} previously-unplaced cells.")
    print_summary(g, args.netlist,1)
    
    # 2) Legalize (ensure legal site type + no overlaps)
    legalize(g)
    
    
    placed_after_legalize = count_placed_cells(g)
    total_cells = len(g.movable_cells())
    if placed_after_legalize != total_cells:
        raise netlist_error(f"After legalization, only {placed_after_legalize}/{total_cells} cells are placed.")
    print_summary(g, args.netlist,1)
    
    hpwl_before = total_hpwl(g)
    print(f"HPWL before SA: {hpwl_before}")
    
    # 3) Simulated annealing optimization
    CR = 0.75 #make a loop with all the CRs
    final_cost, accepted, rejected = SA_loop(CR,g)
    hpwl_after = total_hpwl(g)

    print(f"SA stats: accepted={accepted}, rejected={rejected}")
    print(f"HPWL after SA:  {hpwl_after} (SA returned {final_cost})")

    if args.show_grid:
        print("\nFinal grid:")
        print(g.render())
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

