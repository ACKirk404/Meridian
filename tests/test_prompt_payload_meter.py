import pytest
from meridian_core.prompt_payload_meter import PromptPayloadSnapshot, PayloadStatus


class TestPromptPayloadSnapshot:
    """Test cases for PromptPayloadSnapshot domain helper."""

    def test_create_basic_snapshot(self):
        """Create a basic snapshot with minimal fields."""
        snapshot = PromptPayloadSnapshot(
            raw_prompt_chars=500,
            estimated_tokens=100,
        )
        assert snapshot.raw_prompt_chars == 500
        assert snapshot.estimated_tokens == 100
        assert snapshot.status == PayloadStatus.HEALTHY
        assert snapshot.queue_mode is False

    def test_display_label_under_1k_chars(self):
        """Format display label for small prompts (under 1k chars)."""
        snapshot = PromptPayloadSnapshot(raw_prompt_chars=500, estimated_tokens=100)
        assert snapshot.display_label == "(under 1k)"

    def test_display_label_exact_1k(self):
        """Format display label for exactly 1k characters."""
        snapshot = PromptPayloadSnapshot(raw_prompt_chars=1000, estimated_tokens=250)
        assert snapshot.display_label == "(1k)"

    def test_display_label_over_1k(self):
        """Format display label with decimal precision for larger prompts."""
        snapshot = PromptPayloadSnapshot(raw_prompt_chars=12400, estimated_tokens=3100)
        assert snapshot.display_label == "(12.4k)"

    def test_display_label_large_prompt(self):
        """Format display label for large prompts."""
        snapshot = PromptPayloadSnapshot(raw_prompt_chars=50000, estimated_tokens=12500)
        assert snapshot.display_label == "(50k)"

    def test_budget_percent_calculation(self):
        """Calculate budget as percentage of max budget."""
        snapshot = PromptPayloadSnapshot(
            raw_prompt_chars=5000,
            estimated_tokens=1250,
            budget_tokens=2000,
        )
        assert snapshot.budget_percent == 62.5

    def test_budget_percent_no_budget(self):
        """Return 0 when no budget is set."""
        snapshot = PromptPayloadSnapshot(
            raw_prompt_chars=5000,
            estimated_tokens=1250,
            budget_tokens=None,
        )
        assert snapshot.budget_percent == 0.0

    def test_growth_tokens_calculation(self):
        """Calculate token growth from prior snapshot."""
        snapshot = PromptPayloadSnapshot(
            raw_prompt_chars=5000,
            estimated_tokens=1250,
            prior_estimated_tokens=1000,
        )
        assert snapshot.growth_tokens == 250

    def test_growth_tokens_no_prior(self):
        """Return 0 when no prior snapshot."""
        snapshot = PromptPayloadSnapshot(
            raw_prompt_chars=5000,
            estimated_tokens=1250,
            prior_estimated_tokens=None,
        )
        assert snapshot.growth_tokens == 0

    def test_growth_percent_calculation(self):
        """Calculate growth as percentage of prior."""
        snapshot = PromptPayloadSnapshot(
            raw_prompt_chars=5000,
            estimated_tokens=1250,
            prior_estimated_tokens=1000,
        )
        assert snapshot.growth_percent == 25.0

    def test_growth_percent_no_prior(self):
        """Return 0 when no prior snapshot."""
        snapshot = PromptPayloadSnapshot(
            raw_prompt_chars=5000,
            estimated_tokens=1250,
            prior_estimated_tokens=None,
        )
        assert snapshot.growth_percent == 0.0

    def test_status_healthy_under_budget(self):
        """Status is healthy when well under budget."""
        snapshot = PromptPayloadSnapshot(
            raw_prompt_chars=5000,
            estimated_tokens=500,
            budget_tokens=2000,
        )
        assert snapshot.status == PayloadStatus.HEALTHY

    def test_status_watch_approaching_budget(self):
        """Status is watch when approaching 80% of budget."""
        snapshot = PromptPayloadSnapshot(
            raw_prompt_chars=5000,
            estimated_tokens=1600,
            budget_tokens=2000,
        )
        assert snapshot.status == PayloadStatus.WATCH

    def test_status_degraded_over_budget(self):
        """Status is degraded when exceeding budget."""
        snapshot = PromptPayloadSnapshot(
            raw_prompt_chars=5000,
            estimated_tokens=2100,
            budget_tokens=2000,
        )
        assert snapshot.status == PayloadStatus.DEGRADED

    def test_status_degraded_queue_mode_growth(self):
        """Status is degraded when queue-mode growth is meaningful (>10%)."""
        snapshot = PromptPayloadSnapshot(
            raw_prompt_chars=5000,
            estimated_tokens=1250,
            prior_estimated_tokens=1000,
            queue_mode=True,
        )
        assert snapshot.status == PayloadStatus.DEGRADED

    def test_status_watch_queue_mode_modest_growth(self):
        """Status is watch when queue-mode growth is modest (5-10%)."""
        snapshot = PromptPayloadSnapshot(
            raw_prompt_chars=5000,
            estimated_tokens=1050,
            prior_estimated_tokens=1000,
            queue_mode=True,
        )
        assert snapshot.status == PayloadStatus.WATCH

    def test_status_healthy_queue_mode_minimal_growth(self):
        """Status is healthy when queue-mode growth is minimal (<5%)."""
        snapshot = PromptPayloadSnapshot(
            raw_prompt_chars=5000,
            estimated_tokens=1020,
            prior_estimated_tokens=1000,
            queue_mode=True,
        )
        assert snapshot.status == PayloadStatus.HEALTHY

    def test_immutable_snapshot(self):
        """Snapshot is frozen (immutable)."""
        snapshot = PromptPayloadSnapshot(
            raw_prompt_chars=5000,
            estimated_tokens=1250,
        )
        with pytest.raises(AttributeError):
            snapshot.raw_prompt_chars = 6000

    def test_status_priority_budget_over_queue_growth(self):
        """Budget pressure takes priority over queue-mode growth."""
        snapshot = PromptPayloadSnapshot(
            raw_prompt_chars=5000,
            estimated_tokens=2100,
            budget_tokens=2000,
            prior_estimated_tokens=1000,
            queue_mode=True,
        )
        assert snapshot.status == PayloadStatus.DEGRADED

    def test_complex_scenario_multiple_fields(self):
        """Test realistic scenario with all fields populated."""
        snapshot = PromptPayloadSnapshot(
            raw_prompt_chars=8500,
            estimated_tokens=2125,
            budget_tokens=3000,
            prior_estimated_tokens=1875,
            queue_mode=True,
        )
        assert snapshot.display_label == "(8.5k)"
        assert snapshot.budget_percent == pytest.approx(70.833, rel=0.01)
        assert snapshot.growth_tokens == 250
        assert snapshot.growth_percent == pytest.approx(13.33, rel=0.01)
        assert snapshot.status == PayloadStatus.DEGRADED

    def test_snapshot_with_zero_prior_uses_zero(self):
        """Snapshot with prior_estimated_tokens=0 calculates growth correctly."""
        snapshot = PromptPayloadSnapshot(
            raw_prompt_chars=5000,
            estimated_tokens=500,
            prior_estimated_tokens=0,
        )
        assert snapshot.growth_tokens == 500
        assert snapshot.growth_percent == 0.0


class TestPayloadStatusEnum:
    """Test PayloadStatus enum."""

    def test_status_values(self):
        """Verify expected status values exist."""
        assert PayloadStatus.HEALTHY.value == "healthy"
        assert PayloadStatus.WATCH.value == "watch"
        assert PayloadStatus.DEGRADED.value == "degraded"

    def test_status_count(self):
        """Verify exactly 3 status values."""
        assert len(list(PayloadStatus)) == 3
