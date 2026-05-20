from __future__ import annotations
import argparse
from pathlib import Path
import random
import time
from Placer import netlist_error, parse_netlist, print_summary
from Placement import global_placement, placement, count_placed_cells
from SA import SA_loop

seed = 42
random.seed(seed)


def parse_cr(value: str) -> float:
    cr = float(value)
    if not 0 < cr < 1:
        raise argparse.ArgumentTypeError("Cooling rate must be between 0 and 1.")
    return cr


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Run full placement pipeline: parse -> init -> SA.")
    p.add_argument("netlist",       type=Path,     help="Path to a design_*.txt netlist file.")
    p.add_argument("--cr",          type=parse_cr, default=0.95, help="Cooling rate (0<CR<1). Default: 0.95")
    p.add_argument("--nonlinear",   action="store_true",         help="Use adaptive non-linear cooling schedule.")
    p.add_argument("--show-grid",   action="store_true",         help="Render ASCII grid after SA.")
    return p


def main():
    args = build_arg_parser().parse_args()

    try:
        g = parse_netlist(args.netlist)
    except netlist_error as exc:
        print(f"Netlist error: {exc}")
        return 1

    print_summary(g, args.netlist, 1)

    randomly_placed = global_placement(g)
    print(f"\nGlobal placement: placed {randomly_placed} cells.")

    placement(g)
    legally_placed = count_placed_cells(g)
    total_cells    = len(g.movable_cells())
    if legally_placed != total_cells:
        raise netlist_error(f"After legalization, only {legally_placed}/{total_cells} cells placed.")

    # overlap check
    occupied = {}
    for cell in g.movable_cells():
        pos = (cell.placement_x, cell.placement_y)
        if pos in occupied:
            print(f"OVERLAP: cell {cell.component_id} and {occupied[pos]} both at {pos}")
        else:
            occupied[pos] = cell.component_id

    print(f"\nRunning SA  CR={args.cr}  nonlinear={args.nonlinear}")
    start = time.perf_counter()
    initial_cost, final_cost, accepted, rejected = SA_loop(args.cr, g, nonlinear=args.nonlinear)
    elapsed = time.perf_counter() - start

    print(f"SA runtime:  {elapsed:.2f}s")
    print(f"SA stats:    accepted={accepted}, rejected={rejected}")
    print(f"HPWL before: {initial_cost}")
    print(f"HPWL after:  {final_cost}")
    print(f"Improvement: {initial_cost - final_cost} ({(initial_cost - final_cost)/initial_cost:.2%})")

    print_summary(g, args.netlist, 1)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
