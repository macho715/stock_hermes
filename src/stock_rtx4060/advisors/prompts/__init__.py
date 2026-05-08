"""Versioned Jinja-style prompt templates for the advisor agents.

The Jinja2 dependency is optional — when it is missing we fall back to a
*very* small subset of Jinja that handles ``{{ var }}`` substitution and
``{% for ... in ... %} ... {% endfor %}`` loops.  The fallback is enough
for the templates shipped with this package and lets the unit tests run
on bare-Python environments.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

_PROMPT_DIR = Path(__file__).resolve().parent


def load_prompt(name: str) -> str:
    """Return the raw text of ``name`` (without the ``.md`` suffix)."""
    path = _PROMPT_DIR / f"{name}.md"
    return path.read_text(encoding="utf-8")


def render(template: str, context: dict[str, Any]) -> str:
    """Render ``template`` with ``context``.

    Uses :mod:`jinja2` when available; otherwise a tiny fallback engine
    that supports the constructs used by our prompts.
    """
    try:
        import jinja2  # type: ignore[import-not-found]
    except ImportError:
        return _render_fallback(template, context)
    env = jinja2.Environment(autoescape=False, trim_blocks=False, lstrip_blocks=False)
    tpl = env.from_string(template)
    return tpl.render(**context)


# ---------------------------------------------------------------------------
# Tiny fallback renderer — enough for our shipped templates.
# ---------------------------------------------------------------------------


_VAR_RE = re.compile(r"{{\s*([^{}]+?)\s*}}")
_FOR_RE = re.compile(
    r"{%\s*for\s+(\w+)(?:\s*,\s*(\w+))?\s+in\s+(\w+)(?:\.([a-zA-Z_]+)\(\))?\s*%}(.*?){%\s*endfor\s*%}",
    re.DOTALL,
)
_IF_RE = re.compile(r"{%\s*if\s+([^%]+?)\s*%}(.*?){%\s*endif\s*%}", re.DOTALL)


def _resolve(expr: str, context: dict[str, Any]) -> Any:
    """Resolve a dotted expression like ``item.title`` against ``context``."""
    expr = expr.strip()
    if not expr:
        return ""
    parts = expr.split(".")
    val: Any = context.get(parts[0], "")
    for part in parts[1:]:
        if isinstance(val, dict):
            val = val.get(part, "")
        else:
            val = getattr(val, part, "")
    return val


def _render_fallback(template: str, context: dict[str, Any]) -> str:
    text = template

    def _expand_for(match: re.Match[str]) -> str:
        var = match.group(1)
        var2 = match.group(2)
        iterable_name = match.group(3)
        method = match.group(4)
        body = match.group(5)
        iterable = context.get(iterable_name, [])
        if method == "items" and isinstance(iterable, dict):
            iterable = list(iterable.items())
        elif isinstance(iterable, dict):
            iterable = list(iterable.items())
        out_chunks: list[str] = []
        for item in iterable:
            inner_ctx = dict(context)
            if var2 is not None and isinstance(item, tuple) and len(item) == 2:
                inner_ctx[var] = item[0]
                inner_ctx[var2] = item[1]
            else:
                inner_ctx[var] = item
            out_chunks.append(_render_fallback(body, inner_ctx))
        return "".join(out_chunks)

    # iterate in case nested loops appear
    while _FOR_RE.search(text):
        text = _FOR_RE.sub(_expand_for, text)

    def _expand_if(match: re.Match[str]) -> str:
        cond = match.group(1).strip()
        body = match.group(2)
        truthy = bool(_resolve(cond, context))
        return body if truthy else ""

    while _IF_RE.search(text):
        text = _IF_RE.sub(_expand_if, text)

    def _expand_var(match: re.Match[str]) -> str:
        return str(_resolve(match.group(1), context))

    text = _VAR_RE.sub(_expand_var, text)
    return text


__all__ = ["load_prompt", "render"]
