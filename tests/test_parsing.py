"""Baseline-arm reply parsing.

Both cases here are real bugs found in a live run, kept as regressions:

1. `max_tokens: 8` truncated the chat model into returning `content: null`,
   which crashed the parser. The failures were not random — they clustered on
   the hardest items and the most deliberative persona, so the baseline arm
   would have been missing exactly the cases where the model worked hardest.
2. Naive substring matching resolved "3" inside "33" and "1" inside "100",
   which would have silently corrupted the p-beauty contest, where the options
   are the integers 0-100.
"""

from __future__ import annotations

import pytest

from jevbench.client import parse_option

NUMBERS = [str(i) for i in range(101)]


def test_null_content_does_not_crash() -> None:
    assert parse_option(None, ["a", "b"]) is None
    assert parse_option("", ["a", "b"]) is None
    assert parse_option("   \n ", ["a", "b"]) is None


@pytest.mark.parametrize(
    ("reply", "expected"),
    [
        ("33", "33"),
        ("100", "100"),
        ("0", "0"),
        ("1", "1"),
        ("  22  ", "22"),
        ("I would choose 22.", "22"),
        ("My answer: 67", "67"),
    ],
)
def test_numeric_options_resolve_exactly(reply: str, expected: str) -> None:
    assert parse_option(reply, NUMBERS) == expected


def test_numeric_matching_is_not_substring_based() -> None:
    """The specific corruption this guards: '100' must never resolve to '1' or '0'."""
    assert parse_option("100", NUMBERS) == "100"
    assert parse_option("33", NUMBERS) != "3"


def test_out_of_range_number_is_unparsed_rather_than_guessed() -> None:
    assert parse_option("500", NUMBERS) is None


@pytest.mark.parametrize(
    ("reply", "options", "expected"),
    [
        ("$0.05", ["$0.05", "$0.10", "$1.00"], "$0.05"),
        ("cooperate", ["cooperate", "defect"], "cooperate"),
        ("The answer is program_a", ["program_a", "program_b"], "program_a"),
        ("accept", ["accept", "reject"], "accept"),
        ("REJECT", ["accept", "reject"], "reject"),
        ("5 minutes", ["5 minutes", "100 minutes"], "5 minutes"),
    ],
)
def test_label_options_resolve(reply: str, options: list[str], expected: str) -> None:
    assert parse_option(reply, options) == expected


def test_unrelated_reply_is_unparsed() -> None:
    assert parse_option("I cannot answer that.", ["accept", "reject"]) is None


def test_longest_option_wins_over_a_prefix() -> None:
    """'option_a' must not swallow a reply naming 'option_ab'."""
    assert parse_option("option_ab", ["option_a", "option_ab"]) == "option_ab"
