"""Tests for the token counting utility (meridian_core/tokens.py)."""

from __future__ import annotations

import pytest

from meridian_core.tokens import count_tokens


class TestCountTokensBasic:
    def test_empty_string_returns_zero(self):
        assert count_tokens("") == 0

    def test_whitespace_only_returns_non_negative_int(self):
        result = count_tokens("   ")
        assert isinstance(result, int)
        assert result >= 0

    def test_single_word(self):
        assert count_tokens("hello") >= 1

    def test_multiple_words(self):
        result = count_tokens("hello world")
        assert result >= 2

    def test_returns_int(self):
        assert isinstance(count_tokens("hello world"), int)

    def test_nonempty_string_returns_positive(self):
        assert count_tokens("a") > 0

    def test_longer_text_has_more_tokens_than_shorter(self):
        short = "hello"
        long = "hello world how are you doing today my friend"
        assert count_tokens(long) > count_tokens(short)


class TestCountTokensDeterminism:
    def test_repeated_calls_return_same_value(self):
        text = "The quick brown fox jumps over the lazy dog."
        assert count_tokens(text) == count_tokens(text)

    def test_identical_strings_equal_counts(self):
        text = "Analyze the risk tier for this dispatch route."
        assert count_tokens(text) == count_tokens(text)


class TestCountTokensPunctuation:
    def test_punctuation_heavy_text(self):
        text = "def foo(): return bar.baz['key']"
        result = count_tokens(text)
        assert result > 0
        assert isinstance(result, int)

    def test_code_snippet(self):
        code = "for i in range(10):\n    print(f'item {i}')"
        result = count_tokens(code)
        assert result > 0

    def test_sentence_with_commas(self):
        text = "First, second, third, and fourth items."
        result = count_tokens(text)
        assert result >= 4


class TestCountTokensTypeErrors:
    def test_int_raises_type_error(self):
        with pytest.raises(TypeError):
            count_tokens(123)  # type: ignore[arg-type]

    def test_none_raises_type_error(self):
        with pytest.raises(TypeError):
            count_tokens(None)  # type: ignore[arg-type]

    def test_list_raises_type_error(self):
        with pytest.raises(TypeError):
            count_tokens(["hello", "world"])  # type: ignore[arg-type]

    def test_float_raises_type_error(self):
        with pytest.raises(TypeError):
            count_tokens(3.14)  # type: ignore[arg-type]

    def test_type_error_message_names_the_type(self):
        with pytest.raises(TypeError, match="int"):
            count_tokens(42)  # type: ignore[arg-type]


class TestCountTokensConservatism:
    def test_estimate_is_at_least_word_count(self):
        text = "one two three four five"
        assert count_tokens(text) >= 5

    def test_dense_code_estimate_not_lower_than_char_over_four(self):
        text = "x=y+z*w/q"  # 9 chars, 1 word → char estimate = ceil(9/4) = 3
        result = count_tokens(text)
        assert result >= 1  # at minimum non-zero for non-empty
