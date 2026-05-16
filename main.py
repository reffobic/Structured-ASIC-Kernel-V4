from __future__ import annotations
import argparse
from pathlib import Path
import random
from Placer import netlist_error, parse_netlist, print_summary
from Placement import global_placement, placement, count_placed_cells
from SA import SA_loop, initial_total_hpwl
import time

# Set a fixed seed for reprodicibility for easier testing 
seed = 42
random.seed(seed)

def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Run full placement pipeline: parse -> init -> legalize -> SA.")
    p.add_argument("netlist", type=Path, help="Path to a design_*.txt netlist file.")
    p.add_argument("--cr", type=float, default=0.95, help="Cooling rate (0<CR<1).")
    p.add_argument("--show-grid", action="store_true", help="Render ASCII grid at the end (after SA).")
    p.add_argument("--show-initial-grid", action="store_true", help="Also render grid right after parsing (pins only).")
    return p


def main():
    # Commandline arguments 
    args = build_arg_parser().parse_args()

    # Parse user's netlist file into our grid data structure
    try:
        g = parse_netlist(args.netlist)
    except netlist_error as exc:
        print(f"Netlist error: {exc}")
        return 1

    # Show loaded netlist (it's pins-only at this stage)
    print_summary(g, args.netlist, 1)
    
    # Placement 
    randomly_placed = global_placement(g)
    print(f"\nGlobalplacement: placed {randomly_placed} previously-unplaced cells.")
    print_summary(g, args.netlist, 1) # logging output 
    
    placement(g)
    legaly_placed = count_placed_cells(g)
    total_cells = len(g.movable_cells())
    if legaly_placed != total_cells:
        raise netlist_error(f"After legalization, only {legaly_placed}/{total_cells} cells are placed.")
    print_summary(g, args.netlist, 1) # logging output

    # check overlap (haya debugging)
    occupied = {}
    for cell in g.movable_cells():
        pos = (cell.placement_x, cell.placement_y)
        if pos in occupied:
            print(f"OVERLAP: cell {cell.component_id} and {occupied[pos]} both at {pos}")
        else:
            occupied[pos] = cell.component_id
    # -------------------------------  

    # Simulated Annealing Loop
    #hpwl_before = initial_total_hpwl(g)
    #print(f"HPWL before SA: {hpwl_before}") # logging output
    
    CR = 0.95 # This setup is for testing and demo, we loop over different CRs below
    start = time.perf_counter() 
    initial_cost, final_cost, accepted, rejected = SA_loop(CR,g)
    hpwl_before = initial_cost
    hpwl_after = final_cost
    elapsed = time.perf_counter() - start
    print(f"SA runtime:     {elapsed:.2f}s")
    print(f"SA stats: accepted={accepted}, rejected={rejected}")
    print(f"HPWL after SA:  {hpwl_before} (SA returned {initial_cost})")
    print(f"HPWL after SA:  {hpwl_after} (SA returned {final_cost})")
    print(f"HPWL change:    {hpwl_after - hpwl_before} ({(hpwl_after - hpwl_before)/hpwl_before:.2%})")
    print_summary(g, args.netlist, 1)

    # # Loop over different CRs 
    # for CR in [0.85, 0.9, 0.95, 0.98]:
    #     # loop 3 times for each CR and get average stats, to account for some randomness in SA
    #     total_final_cost = 0
    #     total_accepted = 0
    #     total_rejected = 0
    #     for _ in range(3):
    #         final_cost, accepted, rejected = SA_loop(CR,g)
    #         hpwl_after = total_hpwl(g)
    #         total_final_cost += final_cost
    #         total_accepted += accepted
    #         total_rejected += rejected
            
    #     print(f"CR={CR}: accepted={total_accepted}, rejected={total_rejected}, HPWL after SA: {hpwl_after} (SA returned {total_final_cost})")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())

