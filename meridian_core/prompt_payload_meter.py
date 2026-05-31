from dataclasses import dataclass
from enum import Enum
from typing import Optional


class PayloadStatus(Enum):
    """Status of prompt payload relative to budget and growth constraints."""
    HEALTHY = "healthy"
    WATCH = "watch"
    DEGRADED = "degraded"


@dataclass(frozen=True)
class PromptPayloadSnapshot:
    """Frozen snapshot of prompt payload metrics for Relay dispatch visibility.

    Provides deterministic, cheap status and metrics computation without API calls,
    filesystem access, or model invocation. Designed for per-dispatch payload visibility
    in the style of Polaris prompt-size meters.
    """

    raw_prompt_chars: int
    estimated_tokens: int
    budget_tokens: Optional[int] = None
    prior_estimated_tokens: Optional[int] = None
    queue_mode: bool = False

    @property
    def display_label(self) -> str:
        """Polaris-style display label for prompt size visibility.

        Returns:
            - "(under 1k)" for prompts < 1000 chars
            - "(Nk)" for round thousands (1k, 2k, etc)
            - "(N.Mk)" for values with one decimal place
        """
        chars = self.raw_prompt_chars
        if chars < 1000:
            return "(under 1k)"
        elif chars % 1000 == 0:
            return f"({chars // 1000}k)"
        else:
            return f"({chars / 1000:.1f}k)"

    @property
    def budget_percent(self) -> float:
        """Estimated tokens as percentage of budget tokens.

        Returns:
            Percentage (0-100+) or 0 if no budget set.
        """
        if self.budget_tokens is None:
            return 0.0
        return (self.estimated_tokens / self.budget_tokens) * 100

    @property
    def growth_tokens(self) -> int:
        """Absolute token growth from prior snapshot.

        Returns:
            Token difference, or 0 if no prior snapshot.
        """
        if self.prior_estimated_tokens is None:
            return 0
        return self.estimated_tokens - self.prior_estimated_tokens

    @property
    def growth_percent(self) -> float:
        """Token growth as percentage of prior tokens.

        Returns:
            Percentage growth, or 0 if no prior snapshot or prior is 0.
        """
        if self.prior_estimated_tokens is None or self.prior_estimated_tokens == 0:
            return 0.0
        return (self.growth_tokens / self.prior_estimated_tokens) * 100

    @property
    def status(self) -> PayloadStatus:
        """Deterministic status based on budget and queue-mode growth constraints.

        Logic:
        - DEGRADED: exceeds budget OR (queue_mode AND growth > 10%)
        - WATCH: at 80%+ of budget OR (queue_mode AND growth 5-10%)
        - HEALTHY: otherwise
        """
        # Budget pressure takes priority
        if self.budget_tokens is not None:
            if self.estimated_tokens > self.budget_tokens:
                return PayloadStatus.DEGRADED
            if self.budget_percent >= 80:
                return PayloadStatus.WATCH

        # Queue-mode growth constraints
        if self.queue_mode and self.prior_estimated_tokens is not None:
            if self.growth_percent > 10:
                return PayloadStatus.DEGRADED
            if self.growth_percent >= 5:
                return PayloadStatus.WATCH

        return PayloadStatus.HEALTHY
