"""Target registry for configuration classes.

This module provides :class:`TargetEntry`, a dataclass capturing the
constructor parameters of a target class, and :class:`TargetRegistry`, a singleton
registry for such entries. Entries can be registered and later
unregistered from the registry.

Thread-safe: All operations on TargetRegistry are protected by an internal lock.
"""

import inspect
import threading
from collections import OrderedDict
from dataclasses import dataclass, field
from inspect import Parameter
from types import MappingProxyType
from typing import Any

from rconfig._internal import Singleton


@dataclass(kw_only=True, frozen=True)
class TargetEntry:
    """Immutable entry for a registered target class.

    The ``decisive_init_parameters`` attribute exposes the parameters required
    to instantiate the target class.
    """

    name: str
    target_class: type[Any]
    decisive_init_parameters: MappingProxyType[str, Parameter] = field(init=False, repr=True, compare=False)

    def __post_init__(self) -> None:
        """Populate ``decisive_init_parameters`` after initialization."""
        self._determine_decisive_init_parameters()

    def _determine_decisive_init_parameters(self) -> None:
        """Inspect the target class and cache its constructor parameters."""
        self._validate_target_has_init_method()
        self._validate_target_is_not_abstract()

        init_signature = inspect.signature(self.target_class.__init__, follow_wrapped=True)
        init_parameters = OrderedDict({key: value for key, value in init_signature.parameters.items() if key != 'self'})

        object.__setattr__(self, "decisive_init_parameters", MappingProxyType(init_parameters))

    def _validate_target_has_init_method(self) -> None:
        """Ensure the target class defines an ``__init__`` method."""
        if not hasattr(self.target_class, '__init__'):
            message = (f"The class '{self.target_class.__module__}.{self.target_class.__qualname__}' "
                       f"has no '__init__' method.")
            raise AttributeError(message)

    def _validate_target_is_not_abstract(self) -> None:
        """Ensure the target class is not abstract."""
        if inspect.isabstract(self.target_class):
            message = (f"The class '{self.target_class.__module__}.{self.target_class.__qualname__}' "
                       f"is abstract and cannot be registered as a target.")
            raise TypeError(message)


@Singleton
class TargetRegistry:
    """Thread-safe registry for :class:`TargetEntry` objects.

    Entries can be registered via :meth:`register` and unregistered again
    using :meth:`unregister`. All operations are protected by an internal lock.
    """

    def __init__(self) -> None:
        """Initialize the registry."""
        self._known_targets: dict[str, TargetEntry] = {}
        self._lock = threading.RLock()

    def register(
            self,
            name: str,
            target: type[Any],
    ) -> None:
        """Register a target class under a unique name.

        Thread-safe: protected by internal lock.

        :param name: Identifier for the target class.
        :param target: Class to register.
        """
        # Create TargetEntry outside lock (inspect.signature may be slow)
        entry = TargetEntry(
            name=name,
            target_class=target,
        )
        with self._lock:
            self._known_targets[entry.name] = entry

    def unregister(self, name: str) -> None:
        """Unregister a previously registered target entry.

        Thread-safe: protected by internal lock.

        :param name: Identifier of the entry to unregister.
        :raises KeyError: If no entry with that name exists.
        """
        with self._lock:
            del self._known_targets[name]

    def clear(self) -> None:
        """Clear all registered entries.

        Thread-safe: protected by internal lock.
        This is primarily intended for testing purposes to reset the registry
        between test cases.
        """
        with self._lock:
            self._known_targets.clear()

    def __contains__(self, name: str) -> bool:
        """Check if an entry is registered using 'in' keyword.

        Thread-safe: protected by internal lock.

        :param name: Identifier of the entry to check.
        :return: True if the entry is registered.

        Example::

            if "model" in registry:
                ...
        """
        with self._lock:
            return name in self._known_targets

    @property
    def known_targets(self) -> MappingProxyType[str, TargetEntry]:
        """Read-only view of all registered target entries.

        Returns a live view - changes made after this call ARE reflected.
        Individual read operations are thread-safe, but iteration during
        concurrent mutation may raise RuntimeError.
        """
        return MappingProxyType(self._known_targets)
