# Optimized via Structured-ASIC-Kernel-V4
"""Structured ASIC placement data and environment foundation.

This module implements the Person 1 deliverable: parse a netlist, build the
master-tile fabric, reserve the perimeter, and place fixed pins.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Iterable


VALID_CELL_TYPES = {"T0", "T1", "T2", "T3"}

MASTER_TILE = [
    ["T0", "T1", "T0", "T2", "T0"],
    ["T1", "T0", "T1", "T0", "T1"],
    ["T0", "T2", "T3", "T0", "T2"],
    ["T1", "T0", "T1", "T0", "T0"],
    ["T0", "T0", "T0", "T0", "T0"],
]


class NetlistError(ValueError):
    """Raised when a netlist violates the expected project format."""


@dataclass
class Component:
    """A fixed perimeter pin or a movable design cell."""

    component_id: int
    kind: str
    cell_type: str | None = None
    x: int | None = None
    y: int | None = None

    @property
    def is_pin(self) -> bool:
        return self.kind == "pin"

    @property
    def is_cell(self) -> bool:
        return self.kind == "cell"


@dataclass(frozen=True)
class Net:
    """A net connecting two or more component IDs."""

    net_id: int
    component_ids: tuple[int, ...]


@dataclass
class Site:
    """One coordinate in the full grid."""

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
class Grid:
    """Loaded grid, components, and nets ready for placement logic."""

    num_cells: int
    num_nets: int
    ny: int
    nx: int
    num_fixed_pins: int
    sites: list[list[Site]]
    components: dict[int, Component]
    nets: list[Net]

    @classmethod
    def create_empty(
        cls,
        num_cells: int,
        num_nets: int,
        ny: int,
        nx: int,
        num_fixed_pins: int,
    ) -> "Grid":
        if ny < 3 or nx < 3:
            raise NetlistError("Grid dimensions must leave at least one core site.")

        sites: list[list[Site]] = []
        for y in range(ny):
            row: list[Site] = []
            for x in range(nx):
                is_perimeter = x == 0 or y == 0 or x == nx - 1 or y == ny - 1
                site_type = None
                if not is_perimeter:
                    site_type = MASTER_TILE[(y - 1) % 5][(x - 1) % 5]
                row.append(Site(x=x, y=y, site_type=site_type, is_perimeter=is_perimeter))
            sites.append(row)

        return cls(
            num_cells=num_cells,
            num_nets=num_nets,
            ny=ny,
            nx=nx,
            num_fixed_pins=num_fixed_pins,
            sites=sites,
            components={},
            nets=[],
        )

    def site_at(self, x: int, y: int) -> Site:
        if not (0 <= x < self.nx and 0 <= y < self.ny):
            raise NetlistError(f"Coordinate ({x}, {y}) is outside the grid.")
        return self.sites[y][x]

    def is_perimeter_coord(self, x: int, y: int) -> bool:
        return x == 0 or y == 0 or x == self.nx - 1 or y == self.ny - 1

    def iter_core_sites(self) -> Iterable[Site]:
        for row in self.sites:
            for site in row:
                if not site.is_perimeter:
                    yield site

    def movable_cells(self) -> list[Component]:
        return [component for component in self.components.values() if component.is_cell]

    def fixed_pins(self) -> list[Component]:
        return [component for component in self.components.values() if component.is_pin]

    def core_capacity_by_type(self) -> Counter[str]:
        return Counter(site.site_type for site in self.iter_core_sites() if site.site_type)

    def movable_cells_by_type(self) -> Counter[str]:
        return Counter(
            component.cell_type
            for component in self.components.values()
            if component.is_cell and component.cell_type
        )

    def add_component(self, component: Component) -> None:
        if component.component_id in self.components:
            raise NetlistError(f"Duplicate component ID {component.component_id}.")
        self.components[component.component_id] = component

    def place_fixed_pin(self, component: Component) -> None:
        if component.x is None or component.y is None:
            raise NetlistError(f"Pin {component.component_id} is missing coordinates.")
        if not self.is_perimeter_coord(component.x, component.y):
            raise NetlistError(
                f"Pin {component.component_id} at ({component.x}, {component.y}) is not on the perimeter."
            )

        site = self.site_at(component.x, component.y)
        if site.fixed_pin_id is not None:
            raise NetlistError(
                f"Pin {component.component_id} overlaps pin {site.fixed_pin_id} at ({site.x}, {site.y})."
            )
        site.fixed_pin_id = component.component_id

    def validate_capacity(self) -> None:
        capacity = self.core_capacity_by_type()
        demand = self.movable_cells_by_type()
        for cell_type in sorted(VALID_CELL_TYPES):
            if demand[cell_type] > capacity[cell_type]:
                raise NetlistError(
                    f"Not enough {cell_type} core sites: need {demand[cell_type]}, have {capacity[cell_type]}."
                )

    def render(self) -> str:
        rows: list[str] = []
        for row in self.sites:
            chars: list[str] = []
            for site in row:
                if site.fixed_pin_id is not None:
                    chars.append("P")
                elif site.cell_id is not None:
                    component = self.components[site.cell_id]
                    chars.append(component.cell_type[-1] if component.cell_type else "?")
                elif site.site_type is not None:
                    chars.append(site.site_type[-1])
                else:
                    chars.append(".")
            rows.append("".join(chars))
        return "\n".join(rows)
