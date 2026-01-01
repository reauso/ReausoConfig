"""Configuration validation subsystem.

Validates config dictionaries against registered target classes.
"""

from .Validator import ConfigValidator, ValidationResult

__all__ = ["ConfigValidator", "ValidationResult"]
