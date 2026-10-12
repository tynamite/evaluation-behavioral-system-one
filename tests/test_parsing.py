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


def test_reads_past_a_reasoning_trace() -> None:
    """A 64-token cap still truncated numeric items where the model reasons first.

    The cap is now generous, so replies arrive with the working shown. The answer
    is the last option named, not the first: a model restates the problem's
    numbers before committing to one.
    """
    assert parse_option("Two-thirds of 50 is 33, so I choose 22.", NUMBERS) == "22"
    assert parse_option("The average might be 50. I pick 33", NUMBERS) == "33"
    assert (
        parse_option("Not program_a. I choose program_b.", ["program_a", "program_b"])
        == "program_b"
    )
    assert parse_option("Reject rather than accept? No - reject.", ["accept", "reject"]) == "reject"


def test_an_option_at_the_end_of_a_sentence_still_matches() -> None:
    """Excluding a trailing '.' outright silently dropped sentence-final answers."""
    assert parse_option("I would accept.", ["accept", "reject"]) == "accept"
    assert parse_option("cooperate.", ["cooperate", "defect"]) == "cooperate"


def test_a_decimal_does_not_match_its_integer_prefix() -> None:
    assert parse_option("33.5", NUMBERS) is None


# Replies seen in the committed chat runs that an earlier parser misread.


def test_echoed_option_line_takes_the_leading_key() -> None:
    dollars = [f"${i}" for i in range(11)]
    # The label after the colon names other amounts; the key before it is the answer.
    assert parse_option("$1: Offer $1, keep $9", dollars) == "$1"
    assert parse_option("$0: Contribute $0, keep $10", dollars) == "$0"
    assert parse_option("pressure: pressure", ["pressure", "volume"]) == "pressure"


def test_true_false_needs_a_bare_answer() -> None:
    tf = ["true", "false"]
    assert parse_option("**True**", tf) == "true"
    assert parse_option("false.", tf) == "false"
    # Declining the format is not an answer of "false".
    assert parse_option("I can't answer that with true or false. Roughly 85%.", tf) is None
    assert parse_option('I can\'t answer with only "true" or "false".', tf) is None


def test_percentage_band_matches_without_its_percent_sign() -> None:
    bands = ["0-35%", "35-45%", "45-55%", "55-65%"]
    assert parse_option("45-55", bands) == "45-55%"
    assert parse_option("35-45%", bands) == "35-45%"
    assert parse_option("B", bands) is None
