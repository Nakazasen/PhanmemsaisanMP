"""Business-phase adapter for the allocation compatibility façade.

The calculation rules remain owned by ``AllocationEngine`` during the staged
migration; this coordinator makes the three operational phases explicit and
keeps transaction ownership in one place.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class AllocationPhaseOwner(Protocol):
    conn: object

    def _map_direct_costs(self) -> dict[str, int]: ...
    def _process_allocation_rules(self) -> None: ...
    def _process_bus_headcount_drivers(self) -> None: ...


@dataclass(frozen=True)
class AllocationPhaseResult:
    """Evidence returned after all allocation phases complete successfully."""

    direct_cost_mapping: dict[str, int]


class AllocationPhaseCoordinator:
    """Run allocation phases in their required business order."""

    def run(self, owner: AllocationPhaseOwner) -> AllocationPhaseResult:
        direct_cost_mapping = owner._map_direct_costs()
        owner._process_allocation_rules()
        owner._process_bus_headcount_drivers()
        owner.conn.commit()
        return AllocationPhaseResult(direct_cost_mapping=direct_cost_mapping)
