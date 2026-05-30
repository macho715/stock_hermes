"""RD-Agent integration: discover & validate new factors automatically.

This package exposes a small API surface intentionally — heavy lifting is
delegated to the optional ``rdagent`` package (https://github.com/microsoft/RD-Agent).
"""

from .runner import run_factor_mining
from .settings import STOCK1901_CONFIG_PATH, load_stock1901_config
from .validator import ValidationResult, validate_discovered_factor

__all__ = [
    "run_factor_mining",
    "load_stock1901_config",
    "STOCK1901_CONFIG_PATH",
    "validate_discovered_factor",
    "ValidationResult",
]
