"""Configuration validation logic.

This module provides validation of config dictionaries against registered
target classes in the ConfigStore.
"""

from dataclasses import dataclass, field
from inspect import Parameter
from typing import Any, Union, get_args, get_origin, get_type_hints

from rconfig.ConfigStore import ConfigStore, ConfigReference
from rconfig.errors import (
    MissingFieldError,
    TargetNotFoundError,
    TypeMismatchError,
    ValidationError,
)


# Sentinel for _target_ key
TARGET_KEY = "_target_"


@dataclass
class ValidationResult:
    """Result of config validation.

    :param valid: True if validation passed with no errors.
    :param errors: List of validation errors found.
    """

    valid: bool
    errors: list[ValidationError] = field(default_factory=list)


class ConfigValidator:
    """Validates config dictionaries against registered target classes.

    Performs validation including:
    - Target existence in ConfigStore
    - Required field presence
    - Type compatibility
    - Recursive validation of nested configs
    """

    def __init__(self, store: ConfigStore) -> None:
        """Initialize the validator.

        :param store: ConfigStore containing registered target classes.
        """
        self._store = store

    def validate(self, config: dict[str, Any], config_path: str = "") -> ValidationResult:
        """Validate a config dictionary against its target class.

        :param config: Config dict that should contain a _target_ key.
        :param config_path: Current path for error messages (e.g., "model.encoder").
        :return: ValidationResult with any errors found.
        """
        errors: list[ValidationError] = []

        # Check _target_ exists in config
        if TARGET_KEY not in config:
            errors.append(
                MissingFieldError(TARGET_KEY, "(root)", config_path)
            )
            return ValidationResult(valid=False, errors=errors)

        target_name = config[TARGET_KEY]

        # Check target is registered
        target_error = self._validate_target_exists(target_name, config_path)
        if target_error:
            errors.append(target_error)
            return ValidationResult(valid=False, errors=errors)

        reference = self._store.known_references[target_name]

        # Validate required fields
        missing_errors = self._validate_required_fields(config, reference, config_path)
        errors.extend(missing_errors)

        # Validate types
        type_errors = self._validate_types(config, reference, config_path)
        errors.extend(type_errors)

        return ValidationResult(valid=len(errors) == 0, errors=errors)

    def _validate_target_exists(
        self, target: str, config_path: str
    ) -> TargetNotFoundError | None:
        """Check if target is registered in the ConfigStore."""
        if target not in self._store.known_references:
            available = list(self._store.known_references.keys())
            return TargetNotFoundError(target, available, config_path)
        return None

    def _validate_required_fields(
        self,
        config: dict[str, Any],
        reference: ConfigReference,
        config_path: str,
    ) -> list[MissingFieldError]:
        """Check that all required fields are present in config."""
        errors: list[MissingFieldError] = []

        for param_name, param in reference.decisive_init_parameters.items():
            # Skip if has default value
            if param.default is not Parameter.empty:
                continue
            # Skip if has default factory (VAR_KEYWORD, VAR_POSITIONAL)
            if param.kind in (Parameter.VAR_KEYWORD, Parameter.VAR_POSITIONAL):
                continue

            if param_name not in config:
                errors.append(
                    MissingFieldError(param_name, reference.name, config_path)
                )

        return errors

    def _validate_types(
        self,
        config: dict[str, Any],
        reference: ConfigReference,
        config_path: str,
    ) -> list[ValidationError]:
        """Validate that config values match expected types."""
        errors: list[ValidationError] = []

        try:
            type_hints = get_type_hints(reference.target_class)
        except Exception:
            # If we can't get type hints, skip type validation
            return errors

        for param_name, param in reference.decisive_init_parameters.items():
            if param_name not in config:
                continue

            value = config[param_name]
            expected_type = type_hints.get(param_name)

            if expected_type is None:
                continue

            field_path = f"{config_path}.{param_name}" if config_path else param_name

            # Check if value is a nested config
            if self._is_nested_config(value):
                # Recursively validate nested config
                nested_result = self.validate(value, field_path)
                errors.extend(nested_result.errors)
            else:
                # Validate type
                type_error = self._check_type(
                    param_name, value, expected_type, field_path
                )
                if type_error:
                    errors.append(type_error)

        return errors

    def _is_nested_config(self, value: Any) -> bool:
        """Check if a value is a nested config (dict with _target_)."""
        return isinstance(value, dict) and TARGET_KEY in value

    def _check_type(
        self,
        field_name: str,
        value: Any,
        expected_type: type,
        config_path: str,
    ) -> TypeMismatchError | None:
        """Check if value matches expected type."""
        if self._type_matches(value, expected_type):
            return None

        return TypeMismatchError(
            field_name,
            self._type_repr(expected_type),
            type(value),
            config_path,
        )

    def _type_matches(self, value: Any, expected_type: type) -> bool:
        """Check if a value matches an expected type."""
        origin = get_origin(expected_type)
        args = get_args(expected_type)

        # Handle None
        if value is None:
            if origin is Union and type(None) in args:
                return True
            return expected_type is type(None)

        # Handle Union (including Optional which is Union[T, None])
        if origin is Union:
            return any(self._type_matches(value, arg) for arg in args)

        # Handle list
        if origin is list:
            if not isinstance(value, list):
                return False
            if not args:
                return True
            return all(self._type_matches(item, args[0]) for item in value)

        # Handle dict
        if origin is dict:
            if not isinstance(value, dict):
                return False
            if not args:
                return True
            key_type, value_type = args
            return all(
                self._type_matches(k, key_type) and self._type_matches(v, value_type)
                for k, v in value.items()
            )

        # Handle basic types
        if origin is None:
            # For nested configs, we check the _target_ matches
            if isinstance(value, dict) and TARGET_KEY in value:
                return True  # Will be validated recursively

            # Direct type check
            return isinstance(value, expected_type)

        return False

    def _type_repr(self, t: type) -> str:
        """Get a readable string representation of a type."""
        origin = get_origin(t)
        args = get_args(t)

        if origin is Union:
            if type(None) in args:
                non_none = [a for a in args if a is not type(None)]
                if len(non_none) == 1:
                    return f"{self._type_repr(non_none[0])} | None"
            return " | ".join(self._type_repr(a) for a in args)

        if origin is list:
            if args:
                return f"list[{self._type_repr(args[0])}]"
            return "list"

        if origin is dict:
            if args:
                return f"dict[{self._type_repr(args[0])}, {self._type_repr(args[1])}]"
            return "dict"

        if hasattr(t, "__name__"):
            return t.__name__

        return str(t)
