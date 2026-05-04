from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable

valid_cell_types = {"T0", "T1", "T2", "T3"}

master_title = [
    ["T0", "T1", "T0", "T2", "T0"],
    ["T1", "T0", "T1", "T0", "T1"],
    ["T0", "T2", "T3", "T0", "T2"],
    ["T1", "T0", "T1", "T0", "T0"],
    ["T0", "T0", "T0", "T0", "T0"],
]

class netlist_editor(ValueError):
    #thats when a netlist is not valid or doesnot have the project rules

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
        
        