"""Pure FileMap intelligence helpers for V2.5 architecture awareness.

Callers provide path, owner, proof, and test metadata. This module performs no
filesystem IO and returns display-safe records suitable for UI or bridge use.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum


class FileMapFreshnessStatus(Enum):
    FRESH = "fresh"
    STALE = "stale"
    UNKNOWN = "unknown"


class BoundaryAdvisoryStatus(Enum):
    PASS = "pass"
    WARN = "warn"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class FileMapMetadata:
    path: str
    owner: str
    capability: str
    purpose: str = ""
    updated_at_seconds: int | None = None
    max_age_seconds: int | None = None
    proof_refs: tuple[str, ...] = field(default_factory=tuple)
    related_tests: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        _require_non_empty(self.path, "path")
        _require_non_empty(self.owner, "owner")
        _require_non_empty(self.capability, "capability")
        if self.updated_at_seconds is not None and not isinstance(
            self.updated_at_seconds, int
        ):
            raise ValueError("updated_at_seconds must be an integer or None")
        if self.max_age_seconds is not None and (
            not isinstance(self.max_age_seconds, int) or self.max_age_seconds < 0
        ):
            raise ValueError("max_age_seconds must be a non-negative integer or None")

    @property
    def display_path(self) -> str:
        return display_safe_path(self.path)

    def to_display_dict(self) -> dict[str, object]:
        return {
            "path": self.display_path,
            "owner": _display_safe_text(self.owner),
            "capability": _display_safe_text(self.capability),
            "purpose": _display_safe_text(self.purpose),
            "updated_at_seconds": self.updated_at_seconds,
            "max_age_seconds": self.max_age_seconds,
            "proof_refs": tuple(_display_safe_ref(ref) for ref in self.proof_refs),
            "related_tests": tuple(display_safe_path(path) for path in self.related_tests),
        }


@dataclass(frozen=True)
class FileMapFreshnessRecord:
    path: str
    status: FileMapFreshnessStatus
    age_seconds: int | None
    max_age_seconds: int | None
    reason_tags: tuple[str, ...]

    def to_display_dict(self) -> dict[str, object]:
        return {
            "path": display_safe_path(self.path),
            "status": self.status.value,
            "age_seconds": self.age_seconds,
            "max_age_seconds": self.max_age_seconds,
            "reason_tags": tuple(_display_safe_text(tag) for tag in self.reason_tags),
        }


@dataclass(frozen=True)
class CapabilityOwnershipRecord:
    capability: str
    owner: str
    code_paths: tuple[str, ...]
    proof_refs: tuple[str, ...]
    related_tests: tuple[str, ...]

    def to_display_dict(self) -> dict[str, object]:
        return {
            "capability": _display_safe_text(self.capability),
            "owner": _display_safe_text(self.owner),
            "code_paths": tuple(display_safe_path(path) for path in self.code_paths),
            "proof_refs": tuple(_display_safe_ref(ref) for ref in self.proof_refs),
            "related_tests": tuple(display_safe_path(path) for path in self.related_tests),
        }


@dataclass(frozen=True)
class CapabilityNavigationLink:
    capability: str
    owner: str
    code_path: str
    proof_refs: tuple[str, ...]
    related_tests: tuple[str, ...]

    def to_display_dict(self) -> dict[str, object]:
        return {
            "capability": _display_safe_text(self.capability),
            "owner": _display_safe_text(self.owner),
            "code_path": display_safe_path(self.code_path),
            "proof_refs": tuple(_display_safe_ref(ref) for ref in self.proof_refs),
            "related_tests": tuple(display_safe_path(path) for path in self.related_tests),
        }


@dataclass(frozen=True)
class BoundaryAdvisory:
    path: str
    capability: str
    actual_owner: str
    expected_owner: str | None
    status: BoundaryAdvisoryStatus
    reason_tags: tuple[str, ...]
    message: str

    def to_display_dict(self) -> dict[str, object]:
        return {
            "path": display_safe_path(self.path),
            "capability": _display_safe_text(self.capability),
            "actual_owner": _display_safe_text(self.actual_owner),
            "expected_owner": (
                _display_safe_text(self.expected_owner)
                if self.expected_owner is not None
                else None
            ),
            "status": self.status.value,
            "reason_tags": tuple(_display_safe_text(tag) for tag in self.reason_tags),
            "message": _display_safe_text(self.message),
        }


@dataclass(frozen=True)
class RelatedTestHint:
    code_path: str
    related_tests: tuple[str, ...]
    reason_tags: tuple[str, ...]

    def to_display_dict(self) -> dict[str, object]:
        return {
            "code_path": display_safe_path(self.code_path),
            "related_tests": tuple(display_safe_path(path) for path in self.related_tests),
            "reason_tags": tuple(_display_safe_text(tag) for tag in self.reason_tags),
        }


def evaluate_filemap_freshness(
    entries: tuple[FileMapMetadata, ...] | list[FileMapMetadata],
    *,
    now_seconds: int,
) -> tuple[FileMapFreshnessRecord, ...]:
    """Classify FileMap entry freshness from caller-supplied timestamps."""
    if not isinstance(now_seconds, int):
        raise ValueError("now_seconds must be an integer")

    records: list[FileMapFreshnessRecord] = []
    for entry in sorted(entries, key=lambda item: item.display_path):
        if entry.updated_at_seconds is None or entry.max_age_seconds is None:
            records.append(
                FileMapFreshnessRecord(
                    path=entry.path,
                    status=FileMapFreshnessStatus.UNKNOWN,
                    age_seconds=None,
                    max_age_seconds=entry.max_age_seconds,
                    reason_tags=("freshness_metadata_missing",),
                )
            )
            continue

        age_seconds = max(0, now_seconds - entry.updated_at_seconds)
        if age_seconds > entry.max_age_seconds:
            records.append(
                FileMapFreshnessRecord(
                    path=entry.path,
                    status=FileMapFreshnessStatus.STALE,
                    age_seconds=age_seconds,
                    max_age_seconds=entry.max_age_seconds,
                    reason_tags=("filemap_entry_stale",),
                )
            )
        else:
            records.append(
                FileMapFreshnessRecord(
                    path=entry.path,
                    status=FileMapFreshnessStatus.FRESH,
                    age_seconds=age_seconds,
                    max_age_seconds=entry.max_age_seconds,
                    reason_tags=("filemap_entry_fresh",),
                )
            )
    return tuple(records)


def build_capability_ownership_map(
    entries: tuple[FileMapMetadata, ...] | list[FileMapMetadata],
) -> tuple[CapabilityOwnershipRecord, ...]:
    """Group code, proof, and test metadata by capability and owner."""
    grouped: dict[tuple[str, str], list[FileMapMetadata]] = {}
    for entry in entries:
        grouped.setdefault((entry.capability, entry.owner), []).append(entry)

    records: list[CapabilityOwnershipRecord] = []
    for capability, owner in sorted(grouped):
        owned_entries = grouped[(capability, owner)]
        records.append(
            CapabilityOwnershipRecord(
                capability=capability,
                owner=owner,
                code_paths=_sorted_unique(entry.path for entry in owned_entries),
                proof_refs=_sorted_unique(
                    ref for entry in owned_entries for ref in entry.proof_refs
                ),
                related_tests=_sorted_unique(
                    path for entry in owned_entries for path in entry.related_tests
                ),
            )
        )
    return tuple(records)


def build_capability_navigation_links(
    entries: tuple[FileMapMetadata, ...] | list[FileMapMetadata],
) -> tuple[CapabilityNavigationLink, ...]:
    """Return capability-to-code-to-proof links sorted for deterministic display."""
    return tuple(
        CapabilityNavigationLink(
            capability=entry.capability,
            owner=entry.owner,
            code_path=entry.path,
            proof_refs=tuple(_sorted_unique(entry.proof_refs)),
            related_tests=tuple(_sorted_unique(entry.related_tests)),
        )
        for entry in sorted(entries, key=lambda item: (item.capability, item.display_path))
    )


def advise_architecture_boundary(
    entry: FileMapMetadata,
    expected_owners_by_capability: dict[str, str],
) -> BoundaryAdvisory:
    """Warn when an entry's owner does not match the capability boundary owner."""
    expected_owner = expected_owners_by_capability.get(entry.capability)
    if expected_owner is None:
        return BoundaryAdvisory(
            path=entry.path,
            capability=entry.capability,
            actual_owner=entry.owner,
            expected_owner=None,
            status=BoundaryAdvisoryStatus.UNKNOWN,
            reason_tags=("capability_owner_unknown",),
            message="No expected owner is registered for this capability.",
        )

    if _owner_key(entry.owner) != _owner_key(expected_owner):
        return BoundaryAdvisory(
            path=entry.path,
            capability=entry.capability,
            actual_owner=entry.owner,
            expected_owner=expected_owner,
            status=BoundaryAdvisoryStatus.WARN,
            reason_tags=("wrong_capability_owner",),
            message=(
                f"{display_safe_path(entry.path)} is owned by "
                f"{_display_safe_text(entry.owner)}, but "
                f"{_display_safe_text(expected_owner)} owns "
                f"{_display_safe_text(entry.capability)}."
            ),
        )

    return BoundaryAdvisory(
        path=entry.path,
        capability=entry.capability,
        actual_owner=entry.owner,
        expected_owner=expected_owner,
        status=BoundaryAdvisoryStatus.PASS,
        reason_tags=("capability_owner_matches",),
        message="Capability owner matches the registered architecture boundary.",
    )


def infer_related_test_hint(
    code_path: str,
    *,
    explicit_tests: tuple[str, ...] | list[str] = (),
    known_tests: tuple[str, ...] | list[str] = (),
) -> RelatedTestHint:
    """Infer likely tests from explicit metadata and caller-supplied test names."""
    display_code_path = display_safe_path(code_path)
    explicit = tuple(display_safe_path(path) for path in explicit_tests)
    known = tuple(display_safe_path(path) for path in known_tests)
    conventional = _conventional_test_path(display_code_path)

    matches: list[str] = list(explicit)
    reason_tags: list[str] = []
    if explicit:
        reason_tags.append("explicit_related_tests")

    if conventional in known and conventional not in matches:
        matches.append(conventional)
        reason_tags.append("conventional_test_match")

    module_stem = _path_stem(display_code_path)
    stem_matches = tuple(
        path for path in known if _path_stem(path).endswith(module_stem)
    )
    for path in stem_matches:
        if path not in matches:
            matches.append(path)
    if stem_matches:
        reason_tags.append("test_stem_match")

    if not matches:
        reason_tags.append("no_related_tests_inferred")

    return RelatedTestHint(
        code_path=code_path,
        related_tests=tuple(sorted(matches)),
        reason_tags=tuple(reason_tags),
    )


def display_safe_path(path: str) -> str:
    """Return a relative-looking path without leaking local absolute prefixes."""
    clean = str(path).strip().replace("\\", "/")
    parts = tuple(part for part in clean.split("/") if part)
    roots = ("meridian_core", "tests", "docs", "bifrost", "scripts", "electron")

    lowered_parts = tuple(part.lower() for part in parts)
    for root in roots:
        if root.lower() in lowered_parts:
            index = lowered_parts.index(root.lower())
            return _display_safe_path_candidate("/".join(parts[index:]))

    if len(parts) > 1 and (":" in parts[0] or clean.startswith("/")):
        return _display_safe_path_candidate(parts[-1])
    if _looks_like_unsafe_text(clean):
        return "[redacted]"
    return clean


def _conventional_test_path(code_path: str) -> str:
    stem = _path_stem(code_path)
    return f"tests/test_{stem}.py"


def _path_stem(path: str) -> str:
    name = display_safe_path(path).rstrip("/").split("/")[-1]
    if "." in name:
        return name.rsplit(".", 1)[0]
    return name


def _owner_key(owner: str) -> str:
    return " ".join(owner.strip().casefold().split())


def _sorted_unique(values: object) -> tuple[str, ...]:
    return tuple(sorted({_display_safe_text(str(value)) for value in values}))


def _display_safe_ref(value: str) -> str:
    clean = _display_safe_text(value)
    if _looks_like_unsafe_text(clean):
        return "[redacted]"
    return clean


def _display_safe_path_candidate(value: str) -> str:
    if _looks_like_unsafe_text(value):
        return "[redacted]"
    return value


def _display_safe_text(value: str | None) -> str:
    if value is None:
        return ""
    clean = str(value).strip()
    if _looks_like_unsafe_text(clean):
        return "[redacted]"
    return clean


def _looks_like_unsafe_text(value: str) -> bool:
    return bool(
        re.search(
            r"(?is)(?:"
            r"[A-Z]:\\|\\\\[^\\\s]+\\[^\\\s]+\\|/(?:Users|home|var|tmp|mnt|Volumes)/|"
            r"\b(?:raw|full|complete)\s+prompt\s*:|"
            r"\b(?:raw|full|complete)\s+transcript\s*:|"
            r"\b(?:provider|model)\s+(?:response|output)\s*:|"
            r"\b(?:api[_-]?key|secret|token|password|credential)\s*[:=]\s*\S{8,}|"
            r"sk-(?:proj-)?[A-Za-z0-9_-]{16,}|"
            r"gh[pousr]_[A-Za-z0-9_]{20,}"
            r")",
            value,
        )
    )


def _require_non_empty(value: str, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must not be empty")
