"""Configuration instantiation logic.

This module provides instantiation of config dictionaries into actual
Python objects using registered target classes.
"""

import inspect
from typing import Any, Union, get_args, get_origin, get_type_hints

from rconfig.ConfigStore import ConfigStore
from rconfig.ConfigValidator import ConfigValidator, TARGET_KEY
from rconfig.errors import InstantiationError


class ConfigInstantiator:
    """Instantiates Python objects from validated config dictionaries.

    Handles recursive instantiation of nested configs and validates
    configs before instantiation.
    """

    def __init__(self, store: ConfigStore, validator: ConfigValidator) -> None:
        """Initialize the instantiator.

        :param store: ConfigStore containing registered target classes.
        :param validator: ConfigValidator for validating configs before instantiation.
        """
        self._store = store
        self._validator = validator

    def instantiate(
        self,
        config: dict[str, Any],
        validate: bool = True,
        config_path: str = "",
    ) -> Any:
        """Create an object from a config dictionary.

        :param config: Config dict with _target_ key.
        :param validate: Whether to validate before instantiation.
        :param config_path: Current path for error messages.
        :return: Instantiated object.
        :raises ValidationError: If config is invalid (when validate=True).
        :raises InstantiationError: If instantiation fails.
        """
        if validate:
            result = self._validator.validate(config, config_path)
            if not result.valid:
                # Raise the first error
                raise result.errors[0]

        target_name = config[TARGET_KEY]
        reference = self._store.known_references[target_name]

        # Process arguments, instantiating nested configs
        kwargs = self._process_arguments(config, config_path)

        try:
            return reference.target_class(**kwargs)
        except Exception as e:
            raise InstantiationError(target_name, str(e), config_path)

    def _process_arguments(
        self,
        config: dict[str, Any],
        config_path: str,
    ) -> dict[str, Any]:
        """Process config arguments, recursively instantiating nested configs.

        :param config: Config dict to process.
        :param config_path: Current path for error messages.
        :return: Dictionary of processed arguments.
        """
        kwargs: dict[str, Any] = {}

        # Get type hints for inferring nested config types
        target_name = config[TARGET_KEY]
        reference = self._store.known_references[target_name]

        try:
            type_hints = get_type_hints(reference.target_class)
        except Exception:
            type_hints = {}

        for key, value in config.items():
            if key == TARGET_KEY:
                continue

            field_path = f"{config_path}.{key}" if config_path else key
            expected_type = type_hints.get(key)
            kwargs[key] = self._process_value(value, field_path, expected_type)

        return kwargs

    def _process_value(
        self,
        value: Any,
        config_path: str,
        expected_type: type | None = None,
    ) -> Any:
        """Process a single value, instantiating if it's a nested config.

        :param value: Value to process.
        :param config_path: Current path for error messages.
        :param expected_type: Expected type from parent's type hint.
        :return: Processed value (instantiated if nested config).
        """
        # Explicit nested config with _target_
        if self._is_nested_config(value):
            return self.instantiate(value, validate=True, config_path=config_path)

        # Implicit nested config - dict without _target_ where type can be inferred
        if self._could_be_implicit_nested(value, expected_type):
            augmented = self._augment_with_inferred_target(value, expected_type)
            if augmented is not None:
                return self.instantiate(augmented, validate=True, config_path=config_path)

        if isinstance(value, list):
            return [
                self._process_value(item, f"{config_path}[{i}]", None)
                for i, item in enumerate(value)
            ]

        if isinstance(value, dict):
            return {
                k: self._process_value(v, f"{config_path}.{k}", None)
                for k, v in value.items()
            }

        return value

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
        """
        origin = get_origin(hint)
        args = get_args(hint)

        # Handle Optional[X] which is Union[X, None]
        if origin is Union:
            non_none_args = [a for a in args if a is not type(None)]
            if len(non_none_args) == 1:
                inner = non_none_args[0]
                if self._is_class_type(inner):
                    return inner
            return None

        if self._is_class_type(hint):
            return hint

        return None

    def _could_be_implicit_nested(
        self,
        value: Any,
        expected_type: type | None,
    ) -> bool:
        """Check if value could be an implicit nested config."""
        if not isinstance(value, dict):
            return False
        if TARGET_KEY in value:
            return False
        if expected_type is None:
            return False

        class_type = self._extract_class_from_hint(expected_type)
        return class_type is not None

    def _find_exact_match(self, cls: type) -> str | None:
        """Find a registered target that exactly matches the given class."""
        for name, reference in self._store.known_references.items():
            if reference.target_class is cls:
                return name
        return None

    def _find_registered_subclasses(self, base_class: type) -> list[str]:
        """Find all registered targets that are subclasses of the given base class."""
        subclasses: list[str] = []
        for name, reference in self._store.known_references.items():
            try:
                if issubclass(reference.target_class, base_class):
                    subclasses.append(name)
            except TypeError:
                continue
        return subclasses

    def _is_concrete_type(self, cls: type) -> tuple[bool, str | None]:
        """Determine if a type is concrete (unambiguously instantiable).

        :return: Tuple of (is_concrete, inferred_target_name)
        """
        if inspect.isabstract(cls):
            return (False, None)

        matching_targets = self._find_registered_subclasses(cls)
        exact_match = self._find_exact_match(cls)

        if exact_match is not None:
            if len(matching_targets) == 1 and matching_targets[0] == exact_match:
                return (True, exact_match)

        return (False, None)

    def _augment_with_inferred_target(
        self,
        value: dict[str, Any],
        expected_type: type,
    ) -> dict[str, Any] | None:
        """Add inferred _target_ to a dict if the type is concrete.

        :return: Augmented config if inference succeeds, None otherwise.
        """
        class_type = self._extract_class_from_hint(expected_type)

        if class_type is None:
            return None

        is_concrete, inferred_target = self._is_concrete_type(class_type)

        if is_concrete and inferred_target is not None:
            return {TARGET_KEY: inferred_target, **value}

        return None
