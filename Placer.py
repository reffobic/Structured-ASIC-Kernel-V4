from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable
from collections import Counter, defaultdict

valid_cell_types = {"T0", "T1", "T2", "T3"}

master_title = [
    ["T0", "T1", "T0", "T2", "T0"],
    ["T1", "T0", "T1", "T0", "T1"],
    ["T0", "T2", "T3", "T0", "T2"],
    ["T1", "T0", "T1", "T0", "T0"],
    ["T0", "T0", "T0", "T0", "T0"],
]

class netlist_error(ValueError):
    """thats when a netlist is not valid or doesnot have the project rules"""
    
@dataclass
class component:
    comoponent_id: int
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
            raise netlist_error("grid dimensions must leave at least one core site")

        sites: list[list[site]] = []
        for y in range(ny):
            row: list[site] = []
            for x in range(nx):
                is_perimeter = x == 0 or y == 0 or y == nx - 1 or y == ny - 1
                site_type = None
                if not is_perimeter:
                    site_type = master_title[(y-1)%5 ][(x-1)%5]
                row.append(site(x=x, y=y, site_type=site_type, is_perimeter=is_perimeter))
            sites.append(row)
        
        return cls(num_cells=num_cells, num_nets=num_nets, ny=ny, nx=nx, num_fixed_pins=num_fixed_pins, sites=sites, components={}, nets=[])

    def site_at(self, x: int, y: int) -> site:
        if not (0 <= x < self.nx and 0 <= y < self.ny):
            raise netlist_error(f"site at ({x}, {y}) is outside the grids")
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

    def net_at(self, x: int, y: int) -> net:
        if not (0 <= net_id < len(self.nets)):
            raise netlist_error(f"net at ({x}, {y}) is outside the nets")
        return self.nets[net_id]

    def add_component(self, component: component) -> None:
        if component.component_id in self.components:
            raise netlist_error(f"component {component.component_id} already exists")
        self.components[component.component_id] = component

    def validate_capacity(self) -> None:
        capacity = self.core_capacity_by_type()
        demand = self.movable_cells_by_type()
        for cell_type in sorted(valid_cell_types):
            if demand[cell_type] > capacity[cell_type]:
                raise netlist_error(f"not enough {cell_type} core sites: need {demand[cell_type]}, have {capacity[cell_type]}.")

    def place_fixed_pin(self, component: component) -> None:
        if component.x is None or component.y is None:
            raise netlist_error(f"pin {component.component_id} is missing coordinates.")
        if not self.is_perimeter_coord(component.x, component.y):
            raise netlist_error(f"pin {component.component_id} at ({component.x}, {component.y}) is not on the perimeter.")
        site = self.site_at(component.x, component.y)
        if site.self_at(component.x, component.y).is_blocked:
            if site.fixed_pin_id is not None:
                raise netlist_error(f"pin {component.component_id} overlaps pin {site.fixed_pin_id} at ({site.x}, {site.y})")
        site.fixed_pin_id = component.component_id

    def attach_cell_to_at(self, cell_id: int, x: int, y: int) -> None:
        component = self.components[cell_id]
        if component is None or not component.is_cell:
            raise netlist_error(f"cell {cell_id} is not a valid cell.")
        if component.cell_type is None:
            raise netlist_error(f"cell {cell_id} has no cell type.")

        site = self.site_at(x, y)
        if site.is_perimeter:
            raise netlist_error(f"site at ({x}, {y}) is on the perimeter.")
        if site.fixed_pin_id is not None:
            raise netlist_error(f"Cannot place a cell on pin site ({x}, {y}).")
        if site.site_type != component.cell_type:
            raise netlist_error(f"Cell {cell_id} type {component.cell_type} cannot sit on " f"site type {site.site_type} at ({x}, {y}).")
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

        



