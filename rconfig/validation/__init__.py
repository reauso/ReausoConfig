"""Configuration validation subsystem.

Validates config dictionaries against registered target classes.
"""

from .Validator import ConfigValidator, ValidationResult
from .required import (
    RequiredMarker,
    find_required_markers,
    is_required_marker,
    extract_required_type,
)

__all__ = [
    "ConfigValidator",
    "ValidationResult",
    "RequiredMarker",
    "find_required_markers",
    "is_required_marker",
    "extract_required_type",
]
