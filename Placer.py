from __future__ import annotations
from ast import For
from dataclasses import dataclass
from typing import Iterable
from collections import Counter, defaultdict
import argparse
from pathlib import Path

# Data structures andlogic for netlist parsing and grid setup
valid_cell_types = {"T0", "T1", "T2", "T3"}

master_title = [
    ["T0", "T1", "T0", "T2", "T0"],
    ["T1", "T0", "T1", "T0", "T1"],
    ["T0", "T2", "T3", "T0", "T2"],
    ["T1", "T0", "T1", "T0", "T0"],
    ["T0", "T0", "T0", "T0", "T0"],
]


class netlist_error(ValueError):
    '''
    For when a netlist is not valid or does not follow the project rules
    '''


@dataclass
class component:
    component_id: int
    kind: str
    cell_type: str | None = None
    x: int | None = None
    y: int | None = None
    placement_x: int | None = None
    placement_y: int | None = None

    @property
    def is_pin(self) -> bool:
        return self.kind == "pin"

    @property
    def is_cell(self) -> bool:
        return self.kind == "cell"


@dataclass(frozen=True)
class net:
    net_id: int
    component_ids: tuple[int, ...]


@dataclass
class site:
    x: int
    y: int
    site_type: str | None 
    is_perimeter: bool
    fixed_pin_id: int | None = None
    cell_id: int | None = None

    @property
    def is_blocked(self) -> bool:
        return self.is_perimeter

    @property
    def is_empty(self) -> bool:
        return self.fixed_pin_id is None and self.cell_id is None


@dataclass
class grid:
    num_cells: int
    num_nets: int
    ny: int
    nx: int
    num_fixed_pins: int
    sites: list[list[site]]
    components: dict[int, component]
    nets: list[net]

    @classmethod
    def create_empty(cls, num_cells: int, num_nets: int, ny: int, nx: int, num_fixed_pins: int) -> grid:
        if nx < 3 or ny < 3:
            raise netlist_error("Grid dimensions must leave at least one core site")

        sites: list[list[site]] = []
        for y in range(ny):
            row: list[site] = []
            for x in range(nx):
                is_perimeter = x == 0 or y == 0 or x == nx - 1 or y == ny - 1
                site_type = None
                if not is_perimeter:
                    site_type = master_title[(y-1)%5 ][(x-1)%5]
                row.append(site(x=x, y=y, site_type=site_type, is_perimeter=is_perimeter))
            sites.append(row)
        
        return cls(num_cells=num_cells, num_nets=num_nets, ny=ny, nx=nx, num_fixed_pins=num_fixed_pins, sites=sites, components={}, nets=[])

    def site_at(self, x: int, y: int) -> site:
        if not (0 <= x < self.nx and 0 <= y < self.ny):
            raise netlist_error(f"Site at ({x}, {y}) is outside the grids")
        return self.sites[y][x]

    def is_perimeter_coord(self, x: int, y: int) -> bool:
        return x == 0 or y == 0 or x == self.nx - 1 or y == self.ny - 1

    def iter_core_sites(self) -> Iterable[site]:
        for row in self.sites:
            for site in row:
                if not site.is_perimeter:
                    yield site

    def movable_cells(self) -> list[component]:
        return [c for c in self.components.values() if c.is_cell]

    def fixed_pins(self) -> list[component]:
        return [c for c in self.components.values() if c.is_pin]

    def core_capacity_by_type(self) -> Counter[str]:
        return Counter(site.site_type for site in self.iter_core_sites() if site.site_type)

    def movable_cells_by_type(self) -> Counter[str]:
        return Counter(c.cell_type for c in self.components.values() if c.is_cell and c.cell_type)

    def net_at(self, net_id: int) -> net:
        if not (0 <= net_id < len(self.nets)):
            raise netlist_error(f"Unknown net id {net_id}.")

        return self.nets[net_id]

    def add_component(self, component: component) -> None:
        if component.component_id in self.components:
            raise netlist_error(f"Component {component.component_id} already exists")

        self.components[component.component_id] = component

    def validate_capacity(self) -> None:
        capacity = self.core_capacity_by_type()
        demand = self.movable_cells_by_type()

        for cell_type in sorted(valid_cell_types):
            if demand[cell_type] > capacity[cell_type]:
                raise netlist_error(f"Not enough {cell_type} core sites: need {demand[cell_type]}, have {capacity[cell_type]}.")

    def place_fixed_pin(self, component: component) -> None:
        if component.x is None or component.y is None:
            raise netlist_error(f"Pin {component.component_id} is missing coordinates.")

        if not self.is_perimeter_coord(component.x, component.y):
            raise netlist_error(f"Pin {component.component_id} at ({component.x}, {component.y}) is not on the perimeter.")

        site = self.site_at(component.x, component.y)

        if site.fixed_pin_id is not None:
            raise netlist_error(f"Pin {component.component_id} overlaps pin {site.fixed_pin_id} at ({site.x}, {site.y})")

        site.fixed_pin_id = component.component_id

    def attach_cell_to_at(self, cell_id: int, x: int, y: int) -> None:
        component = self.components.get(cell_id)

        if component is None or not component.is_cell:
            raise netlist_error(f"Cell {cell_id} is not a valid cell.")

        if component.cell_type is None:
            raise netlist_error(f"Cell {cell_id} has no cell type.")

        site = self.site_at(x, y)
        if site.is_perimeter:
            raise netlist_error(f"Site at ({x}, {y}) is on the perimeter.")

        if site.fixed_pin_id is not None:
            raise netlist_error(f"Cannot place a cell on pin site ({x}, {y}).")
        
        # if site.site_type != component.cell_type:
        #     raise netlist_error(f"Cell {cell_id} type {component.cell_type} cannot sit on " f"site type {site.site_type} at ({x}, {y}).")

        if site.cell_id is not None and site.cell_id != cell_id:
            raise netlist_error(f"Site ({x}, {y}) already holds cell {site.cell_id}.")
            
        if component.placement_x == x and component.placement_y == y and site.cell_id == cell_id:
            return

        if component.placement_x is not None and component.placement_y is not None:
            old = self.site_at(component.placement_x, component.placement_y)
            if old.cell_id == cell_id:
                old.cell_id = None

        site.cell_id = cell_id
        component.placement_x = x
        component.placement_y = y

    def detach_cell_from(self, cell_id: int) -> None:
        component = self.components.get(cell_id)
        if component is None or not component.is_cell:
            raise netlist_error(f"{cell_id} is not a movable design cell id.")

        if component.placement_x is None or component.placement_y is None:
            return

        old = self.site_at(component.placement_x, component.placement_y)

        if old.cell_id == cell_id:
            old.cell_id = None

        component.placement_x = None
        component.placement_y = None

    def render(self) -> str:
        rows: list[str] = []
        for row in self.sites:
            chars: list[str] = []
            for site in row:
                if site.fixed_pin_id is not None:
                    chars.append('P')
                elif site.cell_id is not None:
                    placed = self.components[site.cell_id]
                    chars.append(placed.cell_type[-1] if placed.cell_type else '?')
                else: 
                    chars.append('.')
            rows.append(''.join(chars))
        return '\n'.join(rows)


# Parsing functions
def strip_inline_comment(line: str) -> str:
    line = line.split("#", 1)[0]
    line = line.split("(", 1)[0]
    return line.strip()

def read_tokens(path: Path) -> list[list[str]]:
    token_lines: list[list[str]] = []

    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        clean_line = strip_inline_comment(raw_line)
        if clean_line:
            token_lines.append(clean_line.split())
        elif raw_line.strip() and not raw_line.lstrip().startswith(("#", "(")):
            raise netlist_error(f"Line {line_number} became empty after comment stripping.")

    return token_lines

def parse_int(token: str, context: str) -> int:
    try:
        return int(token)
    except ValueError as exc:
        raise netlist_error(f"Expected integer for {context}, got {token!r}.") from exc

def parse_netlist(path: str | Path) -> grid:
    input_path = Path(path)
    token_lines = read_tokens(input_path)

    if not token_lines:
        raise netlist_error(f"{input_path} is empty.")

    header = token_lines[0]

    if len(header) != 5:
        raise netlist_error("Header must contain: NumCells NumNets ny nx NumFixedPins.")

    num_cells   = parse_int(header[0], "NumCells")
    num_nets    = parse_int(header[1], "NumNets")
    ny          = parse_int(header[2], "ny")
    nx          = parse_int(header[3], "nx")
    num_fixed_pins = parse_int(header[4], "NumFixedPins")

    if num_cells < 0 or num_nets < 0 or num_fixed_pins < 0:
        raise netlist_error("Header counts cannot be negative.")

    if num_fixed_pins > num_cells:
        raise netlist_error("NumFixedPins cannot exceed NumCells.")

    expected_lines = 1 + num_cells + num_nets

    if len(token_lines) != expected_lines:
        raise netlist_error(f"Expected {expected_lines} non-empty data lines, found {len(token_lines)}.")

    g = grid.create_empty(num_cells, num_nets, ny, nx, num_fixed_pins)

    for index, tokens in enumerate(token_lines[1 : 1 + num_cells]):
        if index < num_fixed_pins:
            if len(tokens) != 4 or tokens[3] != "P":
                raise netlist_error(f"Fixed pin line {index + 2} must be: ID X Y P.")
            cid = parse_int(tokens[0], "pin ID")
            x   = parse_int(tokens[1], f"pin {cid} x")
            y   = parse_int(tokens[2], f"pin {cid} y")
            comp = component(component_id=cid, kind="pin", x=x, y=y)
            g.add_component(comp)
            g.place_fixed_pin(comp)

        else:
            if len(tokens) != 2:
                raise netlist_error(f"Movable cell line {index + 2} must be: ID Type.")

            cid = parse_int(tokens[0], "cell ID")
            cell_type = tokens[1]

            if cell_type not in valid_cell_types:
                raise netlist_error(f"Cell {cid} has invalid type {cell_type!r}; expected T0, T1, T2, or T3.")

            g.add_component(component(component_id=cid, kind="cell", cell_type=cell_type))

    for net_id, tokens in enumerate(token_lines[1 + num_cells:]):
        if not tokens:
            raise netlist_error(f"Net line {net_id + 2 + num_cells} is empty.")

        num_attached = parse_int(tokens[0], f"net {net_id} attachment count")
        attached_ids = tuple(parse_int(t, f"net {net_id} component ID") for t in tokens[1:])

        if num_attached != len(attached_ids):
            raise netlist_error(f"Net {net_id} declares {num_attached} attachments but lists {len(attached_ids)} IDs.")

        if num_attached < 1:
            raise netlist_error(f"Net {net_id} must attach at least one component.")

        missing = [cid for cid in attached_ids if cid not in g.components]

        if missing:
            raise netlist_error(f"Net {net_id} references unknown component IDs: {missing}.")

        g.nets.append(net(net_id=net_id, component_ids=attached_ids))

    g.validate_capacity()
    return g

def format_counter(counter: Counter[str], keys: Iterable[str]) -> str:
    return ", ".join(f"{key}: {counter[key]}" for key in keys)


# I/O functions
def print_summary(g: grid, source: Path, show_grid: bool) -> None:
    print(f"Loaded: {source}")
    print(f"Header: components={g.num_cells}, nets={g.num_nets}, "f"grid={g.ny}x{g.nx}, fixed_pins={g.num_fixed_pins}")
    print(f"Movable cells by type: {format_counter(g.movable_cells_by_type(), sorted(valid_cell_types))}")
    print(f"Core capacity by type: {format_counter(g.core_capacity_by_type(), sorted(valid_cell_types))}")
    print(f"Pins placed on perimeter: {len(g.fixed_pins())}")
    print(f"Nets loaded: {len(g.nets)}")
    if show_grid:
        print("\nGrid:")
        print(g.render())

def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Load a Structured ASIC netlist and print summary.")
    parser.add_argument("netlist", type=Path, help="Path to a netlist text file.")
    parser.add_argument("--no-grid", action="store_true", help="Skip ASCII grid output.")
    return parser


# For unit testing
# def main() -> int:
#     parser = build_arg_parser()
#     args = parser.parse_args()
#     try:
#         g = parse_netlist(args.netlist)
#     except netlist_error as exc:
#         parser.exit(status=1, message=f"Netlist error: {exc}\n")
#     print_summary(g, args.netlist, show_grid=not args.no_grid)
#     return 0

# if __name__ == "__main__":
#     raise SystemExit(main())