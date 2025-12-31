"""Configuration validation logic.

This module provides validation of config dictionaries against registered
target classes in the ConfigStore.
"""

import inspect
from dataclasses import dataclass, field
from inspect import Parameter
from typing import Any, Union, get_args, get_origin, get_type_hints

from rconfig.ConfigStore import ConfigStore, ConfigReference
from rconfig.errors import (
    AmbiguousTargetError,
    MissingFieldError,
    TargetNotFoundError,
    TargetTypeMismatchError,
    TypeInferenceError,
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

            # Check if value is an explicit nested config (has _target_)
            if self._is_nested_config(value):
                # Recursively validate nested config
                nested_result = self.validate(value, field_path)
                errors.extend(nested_result.errors)

                # Also validate that the target class matches the expected type
                if nested_result.valid:
                    errors.extend(
                        self._check_target_type_compatibility(
                            value, expected_type, param_name, field_path
                        )
                    )

            # Check if value could be an implicit nested config (dict without _target_)
            elif self._could_be_implicit_nested(value, expected_type):
                # Try to infer target or report error
                errors.extend(
                    self._validate_implicit_nested(
                        value, expected_type, param_name, field_path
                    )
                )

            else:
                # Validate regular type
                type_error = self._check_type(
                    param_name, value, expected_type, field_path
                )
                if type_error:
                    errors.append(type_error)

        return errors

    def _is_nested_config(self, value: Any) -> bool:
        """Check if a value is a nested config (dict with _target_)."""
        return isinstance(value, dict) and TARGET_KEY in value

    def _is_class_type(self, hint: type) -> bool:
        """Check if a type hint represents a class that could be a config target.

        Excludes primitive types and built-in collection types that cannot
        be config targets.

        :param hint: Type hint to check.
        :return: True if hint is a class type that could be a config target.
        """
        origin = get_origin(hint)

        # If it has an origin, it's a generic (list[X], dict[K, V], Optional[X], etc.)
        if origin is not None:
            return False

        # Check if it's actually a class
        if not isinstance(hint, type):
            return False

        # Exclude primitive types and built-in collections
        excluded_types = (
            int,
            float,
            str,
            bool,
            bytes,
            type(None),
            list,
            dict,
            set,
            frozenset,
            tuple,
        )
        if hint in excluded_types:
            return False

        return True

    def _extract_class_from_hint(self, hint: type) -> type | None:
        """Extract the underlying class type from a type hint.

        Handles Optional[X], Union[X, None], and plain class types.
        Returns None if the hint doesn't represent a single class type.

        :param hint: Type hint to analyze.
        :return: The underlying class type, or None if not applicable.
        """
        origin = get_origin(hint)
        args = get_args(hint)

        # Handle Optional[X] which is Union[X, None]
        if origin is Union:
            non_none_args = [a for a in args if a is not type(None)]
            if len(non_none_args) == 1:
                # It's Optional[X], check if X is a class
                inner = non_none_args[0]
                if self._is_class_type(inner):
                    return inner
            return None

        # Plain class type
        if self._is_class_type(hint):
            return hint

        return None

    def _find_registered_subclasses(self, base_class: type) -> list[str]:
        """Find all registered targets that are subclasses of the given base class.

        :param base_class: Base class to find subclasses of.
        :return: List of target names whose classes are subclasses of base_class.
        """
        subclasses: list[str] = []

        for name, reference in self._store.known_references.items():
            target_class = reference.target_class
            # Check if target_class is a subclass of base_class (including exact match)
            try:
                if issubclass(target_class, base_class):
                    subclasses.append(name)
            except TypeError:
                # issubclass can raise TypeError for some types
                continue

        return subclasses

    def _find_exact_match(self, cls: type) -> str | None:
        """Find a registered target that exactly matches the given class.

        :param cls: Class to find exact match for.
        :return: Target name if exact match found, None otherwise.
        """
        for name, reference in self._store.known_references.items():
            if reference.target_class is cls:
                return name
        return None

    def _is_concrete_type(
        self, cls: type
    ) -> tuple[bool, str | None, list[str]]:
        """Determine if a type is concrete (unambiguously instantiable).

        A type is concrete if:
        1. It is not abstract (no @abstractmethod decorators)
        2. It has exactly one registered target matching it (itself)

        :param cls: Class to check.
        :return: Tuple of (is_concrete, exact_target_name, all_matching_targets)
        """
        # Check if abstract
        if inspect.isabstract(cls):
            matching = self._find_registered_subclasses(cls)
            return (False, None, matching)

        # Find all registered subclasses (including exact matches)
        matching_targets = self._find_registered_subclasses(cls)

        # Check for exact match
        exact_match = self._find_exact_match(cls)

        if exact_match is not None:
            # We have an exact match. Is it the ONLY match?
            if len(matching_targets) == 1 and matching_targets[0] == exact_match:
                # Concrete: exactly one target, it's the exact match
                return (True, exact_match, matching_targets)
            else:
                # Ambiguous: there are subclasses registered too
                return (False, None, matching_targets)
        else:
            # No exact match registered - ambiguous
            return (False, None, matching_targets)

    def _could_be_implicit_nested(
        self, value: Any, expected_type: type | None
    ) -> bool:
        """Check if value could be an implicit nested config (dict without _target_).

        A dict could be an implicit nested config if:
        1. It's a dict without _target_
        2. The expected type is a class type (not list, dict, etc.)
        """
        if not isinstance(value, dict):
            return False
        if TARGET_KEY in value:
            return False  # Already has _target_, not implicit
        if expected_type is None:
            return False

        # Extract the actual class type from the hint (handle Optional, etc.)
        class_type = self._extract_class_from_hint(expected_type)
        return class_type is not None

    def _validate_implicit_nested(
        self,
        value: dict[str, Any],
        expected_type: type,
        field_name: str,
        field_path: str,
    ) -> list[ValidationError]:
        """Validate an implicit nested config (dict without _target_).

        If the type is concrete, infers the target and validates.
        If the type is ambiguous, returns an appropriate error.
        """
        errors: list[ValidationError] = []

        # Extract the class type from the hint
        class_type = self._extract_class_from_hint(expected_type)

        if class_type is None:
            # Should not happen if _could_be_implicit_nested returned True
            return errors

        # Check if the type is concrete (can be inferred)
        is_concrete, inferred_target, matching_targets = self._is_concrete_type(
            class_type
        )

        if is_concrete and inferred_target is not None:
            # Type is concrete - inject the target and validate
            augmented_config = {TARGET_KEY: inferred_target, **value}
            nested_result = self.validate(augmented_config, field_path)

            if not nested_result.valid:
                # Wrap validation errors in TypeInferenceError
                errors.append(
                    TypeInferenceError(
                        field_name,
                        class_type,
                        nested_result.errors,
                        field_path,
                    )
                )
        else:
            # Type is ambiguous - report detailed error
            errors.append(
                AmbiguousTargetError(
                    field_name,
                    class_type,
                    matching_targets,
                    inspect.isabstract(class_type),
                    field_path,
                )
            )

        return errors

    def _check_target_type_compatibility(
        self,
        value: dict[str, Any],
        expected_type: type | None,
        field_name: str,
        field_path: str,
    ) -> list[ValidationError]:
        """Check that an explicit _target_ class is compatible with the expected type.

        :param value: The nested config dict with _target_.
        :param expected_type: Expected type from parent's type hint.
        :param field_name: Name of the field being validated.
        :param field_path: Full path for error messages.
        :return: List of validation errors (empty if valid).
        """
        errors: list[ValidationError] = []

        if expected_type is None:
            return errors

        # Extract the class type from the hint
        class_type = self._extract_class_from_hint(expected_type)

        if class_type is None:
            return errors

        target_name = value[TARGET_KEY]
        if target_name not in self._store.known_references:
            return errors  # Target not found error already handled elsewhere

        target_class = self._store.known_references[target_name].target_class

        # Check if target_class is a subclass of expected type
        try:
            if not issubclass(target_class, class_type):
                errors.append(
                    TargetTypeMismatchError(
                        field_name,
                        target_name,
                        target_class,
                        class_type,
                        field_path,
                    )
                )
        except TypeError:
            # issubclass can raise TypeError for some types
            pass

        return errors

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
            # Explicit nested config - validated recursively
            if isinstance(value, dict) and TARGET_KEY in value:
                return True

            # Implicit nested config (dict without _target_ matching class type)
            if isinstance(value, dict) and self._is_class_type(expected_type):
                return True  # Validated by _validate_implicit_nested

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
