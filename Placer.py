from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable
from collections import defaultdict

valid_cell_types = {"T0", "T1", "T2", "T3"}

master_title = [
    ["T0", "T1", "T0", "T2", "T0"],
    ["T1", "T0", "T1", "T0", "T1"],
    ["T0", "T2", "T3", "T0", "T2"],
    ["T1", "T0", "T1", "T0", "T0"],
    ["T0", "T0", "T0", "T0", "T0"],
]

class netlist_editor(ValueError):
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
            raise netlist_editor("grid dimensions must leave at least one core site")

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
            raise netlist_editor(f"site at ({x}, {y}) is outside the grids")
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
            raise netlist_editor(f"net at ({x}, {y}) is outside the nets")
        return self.nets[net_id]

    def add_component(self, component: component) -> None:
        if component.component_id in self.components:
            raise netlist_editor(f"component {component.component_id} already exists")
        self.components[component.component_id] = component

    def validate_capacity(self) -> None:
        capacity = self.core_capacity_by_type()
        demand = self.movable_cells_by_type()
        for cell_type in sorted(VALID_CELL_TYPES):
            if demand[cell_type] > capacity[cell_type]:
                raise netlist_editor(f"not enough {cell_type} core sites: need {demand[cell_type]}, have {capacity[cell_type]}.")

    

            
