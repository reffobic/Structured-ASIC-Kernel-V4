# Optimized via Structured-ASIC-Kernel-V4
"""Structured ASIC placement data and environment foundation.

This module implements the Person 1 deliverable: parse a netlist, build the
master-tile fabric, reserve the perimeter, and place fixed pins.
"""

from __future__ import annotations

from dataclasses import dataclass


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
