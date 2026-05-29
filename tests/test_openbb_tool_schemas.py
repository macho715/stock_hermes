"""Tests for OpenBB tool JSON schemas."""

from __future__ import annotations

import pytest

from stock_rtx4060.advisors.openbb_tools.tool_schemas import (
    ALL_TOOLS,
    GET_COMPANY_NEWS,
    GET_FUNDAMENTAL_METRICS,
    GET_MACRO_INDICATORS,
    GET_PRICE_HISTORY,
    MACRO_TOOLS,
    NEWS_TOOLS,
)

_ALL_DEFS = [GET_PRICE_HISTORY, GET_COMPANY_NEWS, GET_FUNDAMENTAL_METRICS, GET_MACRO_INDICATORS]
_REQUIRED_KEYS = {"name", "description", "input_schema"}


@pytest.mark.parametrize("tool", _ALL_DEFS)
def test_tool_has_required_keys(tool):
    assert _REQUIRED_KEYS.issubset(tool.keys()), f"{tool.get('name')} missing keys"


@pytest.mark.parametrize("tool", _ALL_DEFS)
def test_tool_name_is_nonempty_string(tool):
    assert isinstance(tool["name"], str) and tool["name"]


@pytest.mark.parametrize("tool", _ALL_DEFS)
def test_tool_description_mentions_when_to_use(tool):
    desc = tool["description"].lower()
    assert "use when" in desc or "use " in desc, f"{tool['name']} description should include usage guidance"


@pytest.mark.parametrize("tool", _ALL_DEFS)
def test_input_schema_is_object_type(tool):
    schema = tool["input_schema"]
    assert schema.get("type") == "object"
    assert "properties" in schema


def test_get_price_history_requires_symbol():
    assert "symbol" in GET_PRICE_HISTORY["input_schema"]["required"]


def test_get_company_news_requires_symbol():
    assert "symbol" in GET_COMPANY_NEWS["input_schema"]["required"]


def test_get_fundamental_metrics_requires_symbol():
    assert "symbol" in GET_FUNDAMENTAL_METRICS["input_schema"]["required"]


def test_get_macro_indicators_no_required():
    assert GET_MACRO_INDICATORS["input_schema"].get("required", []) == []


def test_news_tools_contains_news_and_price():
    names = {t["name"] for t in NEWS_TOOLS}
    assert "get_company_news" in names
    assert "get_price_history" in names


def test_macro_tools_contains_macro_and_price():
    names = {t["name"] for t in MACRO_TOOLS}
    assert "get_macro_indicators" in names
    assert "get_price_history" in names


def test_all_tools_has_four_entries():
    assert len(ALL_TOOLS) == 4


def test_all_tool_names_unique():
    names = [t["name"] for t in ALL_TOOLS]
    assert len(names) == len(set(names))


def test_fundamental_metrics_period_enum():
    props = GET_FUNDAMENTAL_METRICS["input_schema"]["properties"]
    assert set(props["period"]["enum"]) == {"annual", "quarter"}


def test_company_news_limit_bounds():
    props = GET_COMPANY_NEWS["input_schema"]["properties"]
    assert props["limit"]["minimum"] == 1
    assert props["limit"]["maximum"] == 15
