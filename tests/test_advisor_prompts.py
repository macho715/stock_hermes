"""Tests for the advisor prompt loader and the small Jinja fallback."""

from __future__ import annotations

import pytest

from stock_rtx4060.advisors.prompts import _render_fallback, load_prompt, render


def test_load_prompt_returns_text():
    text = load_prompt("news_system")
    assert "JSON" in text
    assert "score" in text


def test_load_prompt_missing_raises():
    with pytest.raises(FileNotFoundError):
        load_prompt("does-not-exist")


def test_render_substitutes_simple_variables():
    out = render("Ticker: {{ ticker }}", {"ticker": "AAPL"})
    assert out.strip() == "Ticker: AAPL"


def test_render_handles_for_loop_over_list():
    template = "{% for item in items %}- {{ item }}\n{% endfor %}"
    out = render(template, {"items": ["a", "b"]})
    assert "- a" in out and "- b" in out


def test_render_handles_for_loop_over_dict_items():
    template = "{% for k, v in factors.items() %}{{ k }}={{ v }}\n{% endfor %}"
    out = render(template, {"factors": {"alpha": 0.1, "beta": 0.2}})
    assert "alpha=0.1" in out
    assert "beta=0.2" in out


def test_render_supports_nested_attribute_access():
    template = "src={{ item.source }} url={{ item.url }}"
    out = render(template, {"item": {"source": "reuters", "url": "http://r"}})
    assert "src=reuters" in out
    assert "url=http://r" in out


def test_render_if_block():
    template = "{% if show %}YES{% endif %}DONE"
    out = render(template, {"show": True})
    assert out == "YESDONE"
    out = render(template, {"show": False})
    assert out == "DONE"


def test_fallback_renderer_handles_news_user_template():
    template = load_prompt("news_user")
    rendered = _render_fallback(
        template,
        {
            "ticker": "AAPL",
            "as_of": "2026-05-08T00:00:00+00:00",
            "headlines": [{"source": "r", "title": "Apple beats", "url": "http://r/1", "summary": "good"}],
        },
    )
    assert "AAPL" in rendered
    assert "Apple beats" in rendered
    assert "http://r/1" in rendered
