"""Deprecation warnings for configuration keys.

This module provides tools for marking configuration keys as deprecated
while maintaining backwards compatibility. Deprecated keys are tracked
in the provenance system, providing a single source of truth.

Example::

    import rconfig as rc

    # Register a deprecation
    rc.deprecate(
        old_key="learning_rate",
        new_key="model.optimizer.lr",
        message="Use 'model.optimizer.lr' instead",
        remove_in="2.0.0"
    )

    # Set global policy
    rc.set_deprecation_policy("warn")  # or "error" or "ignore"

    # Custom warning handler
    @rc.deprecation_handler
    def my_handler(info, path, file, line):
        print(f"Deprecated: {path}")
"""

from rconfig.deprecation.detector import (
    auto_map_deprecated_values,
    check_deprecation,
    handle_deprecated_marker,
    has_deprecated_marker,
)
from rconfig.deprecation.handler import (
    DefaultDeprecationHandler,
    DeprecationHandler,
    FunctionDeprecationHandler,
    RconfigDeprecationWarning,
)
from rconfig.deprecation.info import DeprecationInfo, DeprecationPolicy
from rconfig.deprecation.matcher import PathMatcher, find_match, matches
from rconfig.deprecation.registry import DeprecationRegistry, get_deprecation_registry

__all__ = [
    # Info
    "DeprecationInfo",
    "DeprecationPolicy",
    # Handler
    "DeprecationHandler",
    "DefaultDeprecationHandler",
    "FunctionDeprecationHandler",
    "RconfigDeprecationWarning",
    # Matcher
    "PathMatcher",
    "matches",
    "find_match",
    # Registry
    "DeprecationRegistry",
    "get_deprecation_registry",
    # Detector
    "check_deprecation",
    "handle_deprecated_marker",
    "has_deprecated_marker",
    "auto_map_deprecated_values",
]
