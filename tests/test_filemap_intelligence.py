"""Tests for V2.5 FileMap intelligence helpers."""

from __future__ import annotations

from meridian_core.filemap_intelligence import (
    BoundaryAdvisory,
    BoundaryAdvisoryStatus,
    FileMapFreshnessRecord,
    FileMapFreshnessStatus,
    FileMapMetadata,
    RelatedTestHint,
    advise_architecture_boundary,
    build_capability_navigation_links,
    build_capability_ownership_map,
    evaluate_filemap_freshness,
    infer_related_test_hint,
)


def test_stale_entry_detection_from_supplied_metadata():
    entry = FileMapMetadata(
        path="meridian_core/relay.py",
        owner="Relay",
        capability="Model Routing",
        updated_at_seconds=100,
        max_age_seconds=50,
    )

    records = evaluate_filemap_freshness([entry], now_seconds=175)

    assert records[0].status is FileMapFreshnessStatus.STALE
    assert records[0].age_seconds == 75
    assert records[0].reason_tags == ("filemap_entry_stale",)


def test_boundary_advisory_warns_on_wrong_owner():
    entry = FileMapMetadata(
        path="meridian_core/review_console.py",
        owner="Relay",
        capability="Review Console",
    )

    advisory = advise_architecture_boundary(
        entry,
        {"Review Console": "Aegis"},
    )

    assert advisory.status is BoundaryAdvisoryStatus.WARN
    assert advisory.expected_owner == "Aegis"
    assert advisory.reason_tags == ("wrong_capability_owner",)
    assert "meridian_core/review_console.py" in advisory.message


def test_related_test_hints_include_explicit_and_conventional_matches():
    hint = infer_related_test_hint(
        "meridian_core/filemap_intelligence.py",
        explicit_tests=("tests/test_filemap.py",),
        known_tests=(
            "tests/test_filemap_intelligence.py",
            "tests/test_unrelated.py",
        ),
    )

    assert hint.related_tests == (
        "tests/test_filemap.py",
        "tests/test_filemap_intelligence.py",
    )
    assert "explicit_related_tests" in hint.reason_tags
    assert "conventional_test_match" in hint.reason_tags


def test_navigation_links_connect_capability_code_proof_and_tests():
    entry = FileMapMetadata(
        path="meridian_core/aegis.py",
        owner="Aegis",
        capability="Proof Gates",
        proof_refs=("proof:aegis-gate",),
        related_tests=("tests/test_aegis.py",),
    )

    links = build_capability_navigation_links([entry])
    display = links[0].to_display_dict()

    assert display == {
        "capability": "Proof Gates",
        "owner": "Aegis",
        "code_path": "meridian_core/aegis.py",
        "proof_refs": ("proof:aegis-gate",),
        "related_tests": ("tests/test_aegis.py",),
    }


def test_capability_ownership_map_groups_deterministically():
    entries = [
        FileMapMetadata(
            path="meridian_core/relay.py",
            owner="Relay",
            capability="Model Routing",
            proof_refs=("proof:route",),
            related_tests=("tests/test_relay.py",),
        ),
        FileMapMetadata(
            path="meridian_core/relay_dispatch.py",
            owner="Relay",
            capability="Model Routing",
            proof_refs=("proof:dispatch",),
            related_tests=("tests/test_relay_dispatch.py",),
        ),
    ]

    records = build_capability_ownership_map(entries)

    assert len(records) == 1
    assert records[0].code_paths == (
        "meridian_core/relay.py",
        "meridian_core/relay_dispatch.py",
    )
    assert records[0].proof_refs == ("proof:dispatch", "proof:route")


def test_display_dicts_do_not_leak_local_absolute_paths():
    entry = FileMapMetadata(
        path=r"C:\Users\scott\Code\Meridian\meridian_core\filemap.py",
        owner="FileMap",
        capability="Architecture Memory",
        proof_refs=("provider response: raw output",),
        related_tests=(r"C:\Users\scott\Code\Meridian\tests\test_filemap.py",),
    )

    display = entry.to_display_dict()
    freshness = evaluate_filemap_freshness(
        [entry],
        now_seconds=100,
    )[0].to_display_dict()
    link = build_capability_navigation_links([entry])[0].to_display_dict()

    assert display["path"] == "meridian_core/filemap.py"
    assert display["related_tests"] == ("tests/test_filemap.py",)
    assert display["proof_refs"] == ("[redacted]",)
    assert freshness["path"] == "meridian_core/filemap.py"
    assert link["code_path"] == "meridian_core/filemap.py"
    assert "C:/Users" not in str(display)
    assert r"C:\Users" not in str(display)


def test_non_path_fields_are_sanitized_for_paths_and_secrets():
    entry = FileMapMetadata(
        path="meridian_core/filemap.py",
        owner=r"C:\Users\scott\owner",
        capability="api_key=abcdef1234567890",
        purpose="provider response: raw private output",
        proof_refs=("/home/scott/proof", "token=abcdef1234567890"),
    )

    rendered = str(entry.to_display_dict())
    links = build_capability_navigation_links([entry])[0].to_display_dict()

    assert r"C:\Users" not in rendered
    assert "/home/scott" not in rendered
    assert "abcdef1234567890" not in rendered
    assert "raw private output" not in rendered
    assert entry.to_display_dict()["owner"] == "[redacted]"
    assert entry.to_display_dict()["capability"] == "[redacted]"
    assert links["proof_refs"] == ("[redacted]",)


def test_direct_records_sanitize_messages_and_reason_tags():
    freshness = FileMapFreshnessRecord(
        path="meridian_core/filemap.py",
        status=FileMapFreshnessStatus.STALE,
        age_seconds=100,
        max_age_seconds=10,
        reason_tags=("token=abcdef1234567890",),
    )
    advisory = BoundaryAdvisory(
        path="meridian_core/filemap.py",
        capability="Architecture Memory",
        actual_owner="FileMap",
        expected_owner="Aegis",
        status=BoundaryAdvisoryStatus.WARN,
        reason_tags=("raw transcript: private text",),
        message=r"C:\Users\scott\private-path",
    )
    hint = RelatedTestHint(
        code_path="meridian_core/filemap.py",
        related_tests=("tests/test_filemap.py",),
        reason_tags=("provider response: private output",),
    )

    rendered = str(
        (
            freshness.to_display_dict(),
            advisory.to_display_dict(),
            hint.to_display_dict(),
        )
    )

    assert "abcdef1234567890" not in rendered
    assert "private text" not in rendered
    assert "private output" not in rendered
    assert r"C:\Users" not in rendered
    assert freshness.to_display_dict()["reason_tags"] == ("[redacted]",)
    assert advisory.to_display_dict()["message"] == "[redacted]"
    assert hint.to_display_dict()["reason_tags"] == ("[redacted]",)