"""Unit tests for STLProtocol — Sentiment-To-Logic proposition extraction."""
from __future__ import annotations

import pytest

from stock_rtx4060.advisors.memory.stl_protocol import STLProtocol


@pytest.fixture()
def stl():
    return STLProtocol()


def test_extract_valid_proposition_from_plain_text(stl):
    rationale = "IF VIX>25 THEN bearish WITH 0.7 due to risk aversion."
    result = stl.extract(rationale)
    assert result == "IF VIX>25 THEN bearish WITH 0.7"


def test_extract_from_embedded_json(stl):
    rationale = 'Summary: {"proposition": "IF earnings > Q3 THEN bullish WITH 0.8"}'
    result = stl.extract(rationale)
    assert result == "IF earnings > Q3 THEN bullish WITH 0.8"


def test_extract_fallback_on_no_proposition(stl):
    """Rationale without IF-THEN-WITH → empty string, no exception."""
    result = stl.extract("positive earnings surprise, market broadly optimistic")
    assert result == ""


def test_extract_empty_string(stl):
    assert stl.extract("") == ""


def test_extract_none_like_empty(stl):
    assert stl.extract("   ") == ""


def test_validate_correct_format(stl):
    assert stl.validate("IF VIX>25 THEN bearish WITH 0.7") is True


def test_validate_incorrect_format(stl):
    assert stl.validate("bullish because earnings beat") is False


def test_extract_case_insensitive(stl):
    rationale = "if vix>25 then bearish with 0.7"
    result = stl.extract(rationale)
    assert "bearish" in result.lower()


def test_extract_from_json_key_alias(stl):
    rationale = '{"logical_proposition": "IF rates>5 THEN bearish WITH 0.6"}'
    result = stl.extract(rationale)
    assert result == "IF rates>5 THEN bearish WITH 0.6"
