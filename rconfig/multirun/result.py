"""MultirunResult dataclass for storing instantiation results.

This module defines the result type returned by multirun iterations,
containing the resolved config, applied overrides, and the instantiated object.
"""

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True, kw_only=True)
class MultirunResult(Generic[T]):
    """Result of a single multirun instantiation.

    Contains the immutable resolved config, the specific overrides applied
    for this run, and the instantiated object (or stored error).

    The `instance` property raises any stored error when accessed, enabling
    try/except error handling patterns.

    :param config: Immutable view of the fully resolved configuration dict.
    :param overrides: The specific overrides applied for this run.

    Example::

        # Pattern 1: Fail fast (let it raise)
        for result in rc.instantiate_multirun(...):
            train(result.instance)  # Raises if this run failed

        # Pattern 2: Handle errors individually with try/except
        for result in rc.instantiate_multirun(...):
            try:
                train(result.instance)
            except InstantiationError as e:
                log_failure(result.overrides, e)
                continue
    """

    config: MappingProxyType[str, Any]
    overrides: MappingProxyType[str, Any]
    _instance: T | None = field(repr=False)
    _error: Exception | None = field(repr=False, default=None)

    @property
    def instance(self) -> T:
        """Access the instantiated object.

        :return: The instantiated object for this run.
        :raises: The stored error if instantiation failed.
        """
        if self._error is not None:
            raise self._error
        return self._instance  # type: ignore[return-value]
