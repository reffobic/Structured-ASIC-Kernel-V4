from Placer import grid, parse_netlist, netlist_error, build_arg_parser, print_summary
from initialPlacement import legalize
from SA import SA_loop

def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()
    try:
        g = parse_netlist(args.netlist)
    except netlist_error as exc:
        parser.exit(status=1, message=f"Netlist error: {exc}\n")
    print("Initial placement:")
    print_summary(g, args.netlist, show_grid=not args.no_grid)
    print("\nLegalizing placement...")
    legalize(g)
    print_summary(g, args.netlist, show_grid=not args.no_grid)
    #CR = 0.95

    return 0

if __name__ == "__main__":
    raise SystemExit(main())