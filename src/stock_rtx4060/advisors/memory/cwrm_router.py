"""CWRM — Context-Aware Workflow for Reasoning.

Decides whether the DevilsAdvocate should take the *shallow* (summary)
or *deep* (full chain) path based on the disagreement between the
news_sentiment and macro_regime advisors.

No LLM call is made — routing is purely arithmetic so latency is < 1 ms.

Environment variables
---------------------
CWRM_DEEP_THRESHOLD : float, default 0.5
    |news.score - macro.score| > threshold AND conf_product > CWRM_CONF_MIN
    → deep path
CWRM_CONF_MIN : float, default 0.3
    Both advisors must have at least this confidence-product before deep
    path is triggered (prevents noisy-but-uncertain signals from always
    routing deep).
"""
from __future__ import annotations

import os
from dataclasses import dataclass

_DEEP_THRESHOLD: float = float(os.environ.get("CWRM_DEEP_THRESHOLD", "0.5"))
_CONF_MIN: float = float(os.environ.get("CWRM_CONF_MIN", "0.3"))


@dataclass(frozen=True)
class RoutingDecision:
    path: str          # "shallow" | "deep"
    disagreement: float
    conf_product: float
    deep_threshold: float
    conf_min: float


class CWRMRouter:
    """Stateless routing calculator.

    Parameters
    ----------
    deep_threshold:
        Override for CWRM_DEEP_THRESHOLD env var.
    conf_min:
        Override for CWRM_CONF_MIN env var.
    """

    def __init__(
        self,
        deep_threshold: float = _DEEP_THRESHOLD,
        conf_min: float = _CONF_MIN,
    ) -> None:
        self.deep_threshold = deep_threshold
        self.conf_min = conf_min

    def route(self, news_score: float, news_conf: float, macro_score: float, macro_conf: float) -> RoutingDecision:
        """Determine the routing path from two advisor outputs.

        Parameters
        ----------
        news_score, news_conf:
            Score and confidence from the news_sentiment advisor.
        macro_score, macro_conf:
            Score and confidence from the macro_regime advisor.

        Returns
        -------
        RoutingDecision
            ``.path`` is ``"deep"`` when both conditions are satisfied:
            * ``|news_score - macro_score| > deep_threshold``
            * ``news_conf * macro_conf > conf_min``
        """
        disagreement = abs(float(news_score) - float(macro_score))
        conf_product = float(news_conf) * float(macro_conf)
        is_deep = disagreement > self.deep_threshold and conf_product > self.conf_min
        return RoutingDecision(
            path="deep" if is_deep else "shallow",
            disagreement=round(disagreement, 4),
            conf_product=round(conf_product, 4),
            deep_threshold=self.deep_threshold,
            conf_min=self.conf_min,
        )


__all__ = ["CWRMRouter", "RoutingDecision"]
