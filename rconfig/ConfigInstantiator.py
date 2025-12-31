"""Configuration instantiation logic.

This module provides instantiation of config dictionaries into actual
Python objects using registered target classes.
"""

from typing import Any

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

        for key, value in config.items():
            if key == TARGET_KEY:
                continue

            field_path = f"{config_path}.{key}" if config_path else key
            kwargs[key] = self._process_value(value, field_path)

        return kwargs

    def _process_value(self, value: Any, config_path: str) -> Any:
        """Process a single value, instantiating if it's a nested config.

        :param value: Value to process.
        :param config_path: Current path for error messages.
        :return: Processed value (instantiated if nested config).
        """
        if self._is_nested_config(value):
            return self.instantiate(value, validate=True, config_path=config_path)

        if isinstance(value, list):
            return [
                self._process_value(item, f"{config_path}[{i}]")
                for i, item in enumerate(value)
            ]

        if isinstance(value, dict):
            return {
                k: self._process_value(v, f"{config_path}.{k}")
                for k, v in value.items()
            }

        return value

    def _is_nested_config(self, value: Any) -> bool:
        """Check if a value is a nested config (dict with _target_)."""
        return isinstance(value, dict) and TARGET_KEY in value
