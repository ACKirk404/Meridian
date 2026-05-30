"""Tests for the Harness Build And Maturity slice (meridian_core/builds.py)."""

from __future__ import annotations

import pytest

from meridian_core.builds import (
    BuildRegistry,
    HarnessBuild,
    HarnessMaturity,
    KNOWN_HARNESSES,
    MeridianBuild,
    make_initial_registry,
)


# ---------------------------------------------------------------------------
# MeridianBuild
# ---------------------------------------------------------------------------


class TestMeridianBuild:
    def test_build_number_exists(self):
        b = MeridianBuild(build_number=1)
        assert b.build_number == 1

    def test_build_number_is_int(self):
        assert isinstance(MeridianBuild(build_number=0).build_number, int)

    def test_build_number_zero_is_valid(self):
        assert MeridianBuild(build_number=0).build_number == 0


# ---------------------------------------------------------------------------
# HarnessBuild
# ---------------------------------------------------------------------------


class TestHarnessBuild:
    def test_has_name(self):
        h = HarnessBuild(name="Beacon", build_number=0, maturity=HarnessMaturity.CONCEPT)
        assert h.name == "Beacon"

    def test_has_build_number(self):
        h = HarnessBuild(name="Relay", build_number=2, maturity=HarnessMaturity.PROTOTYPE)
        assert h.build_number == 2

    def test_has_maturity(self):
        h = HarnessBuild(name="Aegis", build_number=1, maturity=HarnessMaturity.SKELETON)
        assert h.maturity is HarnessMaturity.SKELETON

    def test_build_number_and_maturity_are_independent(self):
        low_build_high_maturity = HarnessBuild("X", build_number=1, maturity=HarnessMaturity.OPERATIONAL)
        high_build_low_maturity = HarnessBuild("Y", build_number=99, maturity=HarnessMaturity.CONCEPT)
        assert low_build_high_maturity.maturity > high_build_low_maturity.maturity
        assert low_build_high_maturity.build_number < high_build_low_maturity.build_number


# ---------------------------------------------------------------------------
# HarnessMaturity ordering
# ---------------------------------------------------------------------------


class TestHarnessMaturityOrdering:
    def test_concept_less_than_skeleton(self):
        assert HarnessMaturity.CONCEPT < HarnessMaturity.SKELETON

    def test_skeleton_less_than_prototype(self):
        assert HarnessMaturity.SKELETON < HarnessMaturity.PROTOTYPE

    def test_prototype_less_than_operational(self):
        assert HarnessMaturity.PROTOTYPE < HarnessMaturity.OPERATIONAL

    def test_operational_less_than_hardened(self):
        assert HarnessMaturity.OPERATIONAL < HarnessMaturity.HARDENED

    def test_hardened_less_than_deprecated(self):
        assert HarnessMaturity.HARDENED < HarnessMaturity.DEPRECATED

    def test_full_ascending_order(self):
        ordered = [
            HarnessMaturity.CONCEPT,
            HarnessMaturity.SKELETON,
            HarnessMaturity.PROTOTYPE,
            HarnessMaturity.OPERATIONAL,
            HarnessMaturity.HARDENED,
            HarnessMaturity.DEPRECATED,
        ]
        for i in range(len(ordered) - 1):
            assert ordered[i] < ordered[i + 1]

    def test_equal_values_compare_equal(self):
        assert HarnessMaturity.OPERATIONAL <= HarnessMaturity.OPERATIONAL
        assert HarnessMaturity.OPERATIONAL >= HarnessMaturity.OPERATIONAL

    def test_gt_and_ge(self):
        assert HarnessMaturity.HARDENED > HarnessMaturity.SKELETON
        assert HarnessMaturity.HARDENED >= HarnessMaturity.HARDENED


# ---------------------------------------------------------------------------
# BuildRegistry
# ---------------------------------------------------------------------------


class TestBuildRegistry:
    def _registry(self) -> BuildRegistry:
        r = BuildRegistry(meridian=MeridianBuild(build_number=1))
        r.register(HarnessBuild("Beacon", build_number=0, maturity=HarnessMaturity.CONCEPT))
        r.register(HarnessBuild("Relay", build_number=1, maturity=HarnessMaturity.SKELETON))
        return r

    def test_get_known_harness(self):
        r = self._registry()
        h = r.get("Beacon")
        assert h.name == "Beacon"

    def test_get_returns_correct_build_number(self):
        r = self._registry()
        assert r.get("Relay").build_number == 1

    def test_get_returns_correct_maturity(self):
        r = self._registry()
        assert r.get("Relay").maturity is HarnessMaturity.SKELETON

    def test_get_unknown_harness_raises_key_error(self):
        r = self._registry()
        with pytest.raises(KeyError, match="Unknown harness"):
            r.get("Nonexistent")

    def test_register_adds_harness(self):
        r = BuildRegistry(meridian=MeridianBuild(build_number=0))
        r.register(HarnessBuild("Aegis", build_number=0, maturity=HarnessMaturity.CONCEPT))
        assert r.get("Aegis").name == "Aegis"

    def test_register_duplicate_raises_value_error(self):
        r = self._registry()
        with pytest.raises(ValueError, match="already registered"):
            r.register(HarnessBuild("Beacon", build_number=3, maturity=HarnessMaturity.OPERATIONAL))

    def test_upsert_overwrites_existing(self):
        r = self._registry()
        r.upsert(HarnessBuild("Beacon", build_number=3, maturity=HarnessMaturity.OPERATIONAL))
        assert r.get("Beacon").build_number == 3
        assert r.get("Beacon").maturity is HarnessMaturity.OPERATIONAL

    def test_meridian_build_number_accessible(self):
        r = self._registry()
        assert r.meridian.build_number == 1


# ---------------------------------------------------------------------------
# Known harness list
# ---------------------------------------------------------------------------


class TestKnownHarnesses:
    def test_known_harnesses_is_non_empty(self):
        assert len(KNOWN_HARNESSES) > 0

    def test_all_expected_names_present(self):
        expected = {
            "Bifrost", "Beacon", "Echo", "Atlas", "Vault", "Forge",
            "Aegis", "Charter", "Loom", "Compass", "Relay", "Groot",
            "Lens", "Launch",
        }
        assert expected == set(KNOWN_HARNESSES)

    def test_no_duplicates(self):
        assert len(KNOWN_HARNESSES) == len(set(KNOWN_HARNESSES))


# ---------------------------------------------------------------------------
# Initial registry (deterministic sample)
# ---------------------------------------------------------------------------


class TestInitialRegistry:
    def test_meridian_build_number_is_positive(self):
        assert make_initial_registry().meridian.build_number >= 1

    def test_all_known_harnesses_registered(self):
        r = make_initial_registry()
        for name in KNOWN_HARNESSES:
            h = r.get(name)
            assert h.name == name

    def test_each_harness_has_valid_maturity(self):
        r = make_initial_registry()
        for name in KNOWN_HARNESSES:
            assert isinstance(r.get(name).maturity, HarnessMaturity)

    def test_each_harness_has_non_negative_build_number(self):
        r = make_initial_registry()
        for name in KNOWN_HARNESSES:
            assert r.get(name).build_number >= 0

    def test_output_is_deterministic(self):
        r1 = make_initial_registry()
        r2 = make_initial_registry()
        assert r1.meridian.build_number == r2.meridian.build_number
        for name in KNOWN_HARNESSES:
            assert r1.get(name).build_number == r2.get(name).build_number
            assert r1.get(name).maturity == r2.get(name).maturity

    def test_unknown_harness_still_raises(self):
        r = make_initial_registry()
        with pytest.raises(KeyError):
            r.get("Bogus")

    def test_compass_is_at_least_skeleton(self):
        r = make_initial_registry()
        assert r.get("Compass").maturity >= HarnessMaturity.SKELETON

    def test_relay_is_at_least_skeleton(self):
        r = make_initial_registry()
        assert r.get("Relay").maturity >= HarnessMaturity.SKELETON
