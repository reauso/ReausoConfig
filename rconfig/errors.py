"""Custom exceptions for ReausoConfig.

This module defines the exception hierarchy used throughout the library
for configuration loading, validation, and instantiation errors.
"""

from pathlib import Path
from typing import Any


class ConfigError(Exception):
    """Base exception for all ReausoConfig errors."""


class ConfigFileError(ConfigError):
    """Raised when a config file cannot be read or parsed.

    :param path: Path to the problematic config file.
    :param reason: Description of what went wrong.
    """

    def __init__(self, path: Path, reason: str) -> None:
        self.path = path
        self.reason = reason
        super().__init__(f"Failed to load config file '{path}': {reason}")


class TargetNotFoundError(ConfigError):
    """Raised when a _target_ identifier is not registered in ConfigStore.

    :param target: The unregistered target identifier.
    :param available: List of currently registered target names.
    :param config_path: Path in config where error occurred (e.g., "model.encoder").
    """

    def __init__(
        self,
        target: str,
        available: list[str],
        config_path: str = "",
    ) -> None:
        self.target = target
        self.available = available
        self.config_path = config_path

        location = f" at '{config_path}'" if config_path else ""
        available_str = ", ".join(f"'{name}'" for name in available) if available else "(none)"
        super().__init__(
            f"Target '{target}'{location} is not registered. "
            f"Available targets: {available_str}"
        )


class ValidationError(ConfigError):
    """Base exception for validation errors.

    :param config_path: Path in config where error occurred (e.g., "model.encoder").
    """

    def __init__(self, message: str, config_path: str = "") -> None:
        self.config_path = config_path
        super().__init__(message)


class MissingFieldError(ValidationError):
    """Raised when a required field is missing from the config.

    :param field: Name of the missing field.
    :param target: Target class name that requires this field.
    :param config_path: Path in config where error occurred.
    """

    def __init__(self, field: str, target: str, config_path: str = "") -> None:
        self.field = field
        self.target = target

        location = f" at '{config_path}'" if config_path else ""
        super().__init__(
            f"Missing required field '{field}' for target '{target}'{location}",
            config_path,
        )


class TypeMismatchError(ValidationError):
    """Raised when a field value has an incompatible type.

    :param field: Name of the field with wrong type.
    :param expected: Expected type or type description.
    :param actual: Actual type of the provided value.
    :param config_path: Path in config where error occurred.
    """

    def __init__(
        self,
        field: str,
        expected: type | str,
        actual: type,
        config_path: str = "",
    ) -> None:
        self.field = field
        self.expected = expected
        self.actual = actual

        expected_name = expected if isinstance(expected, str) else expected.__name__
        location = f" at '{config_path}'" if config_path else ""
        super().__init__(
            f"Type mismatch for field '{field}'{location}: "
            f"expected {expected_name}, got {actual.__name__}",
            config_path,
        )


class InstantiationError(ConfigError):
    """Raised when object instantiation fails.

    :param target: Target class name that failed to instantiate.
    :param reason: Description of what went wrong.
    :param config_path: Path in config where error occurred.
    """

    def __init__(self, target: str, reason: str, config_path: str = "") -> None:
        self.target = target
        self.reason = reason
        self.config_path = config_path

        location = f" at '{config_path}'" if config_path else ""
        super().__init__(
            f"Failed to instantiate target '{target}'{location}: {reason}"
        )
