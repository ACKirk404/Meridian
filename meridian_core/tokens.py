"""
Token counting utility for Relay prompt construction.

Provides a conservative, deterministic approximation of prompt token counts
without vendor-specific tokenizer dependencies. Replace with a model-specific
tokenizer (e.g. tiktoken) when provider integration is ready.
"""

from __future__ import annotations

import math


def count_tokens(text: str) -> int:
    """
    Return a conservative token count approximation for the given text.

    Uses the higher of two estimates:
    - Word count (whitespace-split): accurate for prose
    - ceil(len(text) / 4): accounts for punctuation and code tokens

    Common BPE tokenizers average ~4 characters per token for English.
    This function errs slightly high rather than low to avoid silent
    budget overruns in PromptPacket construction.

    Args:
        text: The string to count tokens for.

    Returns:
        Non-negative integer token estimate. Returns 0 for empty string.

    Raises:
        TypeError: If text is not a str.
    """
    if not isinstance(text, str):
        raise TypeError(
            f"count_tokens expects str, got {type(text).__name__}"
        )
    if not text:
        return 0
    word_count = len(text.split())
    char_estimate = math.ceil(len(text) / 4)
    return max(word_count, char_estimate)
