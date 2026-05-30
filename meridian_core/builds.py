"""
Harness Build And Maturity -- first-class build identity for Meridian.

Tracks:
- Meridian overall build number
- per-harness build number
- per-harness maturity state

Build number and maturity are separate fields. A harness can churn through
many build numbers while staying at low maturity, or reach operational
maturity at a low build number.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class HarnessMaturity(Enum):
    CONCEPT = "Concept"          # named and defined, not implemented
    SKELETON = "Skeleton"        # domain shape exists, limited behavior
    PROTOTYPE = "Prototype"      # works in controlled demo/sample state
    OPERATIONAL = "Operational"  # useful in real workflow with tests/proof
    HARDENED = "Hardened"        # resilient, observable, recoverable, trusted
    DEPRECATED = "Deprecated"    # retained for compatibility, no longer preferred

    def __lt__(self, other: HarnessMaturity) -> bool:
        return _MATURITY_ORDER[self] < _MATURITY_ORDER[other]

    def __le__(self, other: HarnessMaturity) -> bool:
        return _MATURITY_ORDER[self] <= _MATURITY_ORDER[other]

    def __gt__(self, other: HarnessMaturity) -> bool:
        return _MATURITY_ORDER[self] > _MATURITY_ORDER[other]

    def __ge__(self, other: HarnessMaturity) -> bool:
        return _MATURITY_ORDER[self] >= _MATURITY_ORDER[other]


_MATURITY_ORDER: dict[HarnessMaturity, int] = {
    HarnessMaturity.CONCEPT: 0,
    HarnessMaturity.SKELETON: 1,
    HarnessMaturity.PROTOTYPE: 2,
    HarnessMaturity.OPERATIONAL: 3,
    HarnessMaturity.HARDENED: 4,
    HarnessMaturity.DEPRECATED: 5,
}


@dataclass
class HarnessBuild:
    name: str
    build_number: int
    maturity: HarnessMaturity


@dataclass
class MeridianBuild:
    build_number: int


@dataclass
class BuildRegistry:
    meridian: MeridianBuild
    harnesses: dict[str, HarnessBuild] = field(default_factory=dict)

    def get(self, name: str) -> HarnessBuild:
        """Return the HarnessBuild for name. Raises KeyError for unknown harnesses."""
        try:
            return self.harnesses[name]
        except KeyError:
            raise KeyError(f"Unknown harness: {name!r}. Register it before querying.")

    def register(self, harness: HarnessBuild) -> None:
        """Register a new harness build. Raises ValueError if the harness exists."""
        if harness.name in self.harnesses:
            raise ValueError(f"Harness already registered: {harness.name!r}. Use upsert to replace it.")
        self.harnesses[harness.name] = harness

    def upsert(self, harness: HarnessBuild) -> None:
        """Insert or replace harness build metadata intentionally."""
        self.harnesses[harness.name] = harness


# ---------------------------------------------------------------------------
# Known harness names
# ---------------------------------------------------------------------------

KNOWN_HARNESSES: tuple[str, ...] = (
    "Bifrost",
    "Beacon",
    "Echo",
    "Atlas",
    "Vault",
    "Forge",
    "Aegis",
    "Charter",
    "Loom",
    "Compass",
    "Relay",
    "Groot",
    "Lens",
    "Launch",
)


def make_initial_registry() -> BuildRegistry:
    """
    Deterministic sample registry for all known harnesses at current build state.

    All harnesses start at build 0 / Concept unless they have working domain code,
    in which case they are at Skeleton or Prototype.
    """
    registry = BuildRegistry(meridian=MeridianBuild(build_number=1))
    maturity_map: dict[str, tuple[int, HarnessMaturity]] = {
        # (build_number, maturity)
        "Bifrost":  (0, HarnessMaturity.CONCEPT),
        "Beacon":   (0, HarnessMaturity.CONCEPT),
        "Echo":     (0, HarnessMaturity.CONCEPT),
        "Atlas":    (0, HarnessMaturity.CONCEPT),
        "Vault":    (0, HarnessMaturity.CONCEPT),
        "Forge":    (0, HarnessMaturity.CONCEPT),
        "Aegis":    (0, HarnessMaturity.CONCEPT),
        "Charter":  (0, HarnessMaturity.CONCEPT),
        "Loom":     (0, HarnessMaturity.CONCEPT),
        "Compass":  (1, HarnessMaturity.SKELETON),   # objectives + intention domain exists
        "Relay":    (1, HarnessMaturity.SKELETON),   # routing domain exists
        "Groot":    (0, HarnessMaturity.CONCEPT),
        "Lens":     (0, HarnessMaturity.CONCEPT),
        "Launch":   (0, HarnessMaturity.CONCEPT),
    }
    for name, (build_num, maturity) in maturity_map.items():
        registry.register(HarnessBuild(name=name, build_number=build_num, maturity=maturity))
    return registry
