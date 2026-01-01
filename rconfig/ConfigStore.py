"""Store and inspect configuration class references.

This module provides :class:`ConfigReference`, a dataclass capturing the
constructor parameters of a target class, and :class:`ConfigStore`, a singleton
registry for such references.  References can be registered and later
unregistered from the store.
"""

import inspect
from collections import OrderedDict
from dataclasses import dataclass, field
from inspect import Parameter
from types import MappingProxyType
from typing import Any

from .util import Singleton


@dataclass(kw_only=True, frozen=True)
class ConfigReference:
    """Immutable reference to a configuration class.

    The ``decisive_init_parameters`` attribute exposes the parameters required
    to instantiate the referenced class.
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

        init_signature = inspect.signature(self.target_class.__init__, follow_wrapped=True)
        init_parameters = OrderedDict({key: value for key, value in init_signature.parameters.items() if key != 'self'})

        object.__setattr__(self, "decisive_init_parameters", MappingProxyType(init_parameters))

    def _validate_target_has_init_method(self) -> None:
        """Ensure the target class defines an ``__init__`` method."""
        if not hasattr(self.target_class, '__init__'):
            message = (f"The class '{self.target_class.__module__}.{self.target_class.__qualname__}' "
                       f"has no '__init__' method.")
            raise AttributeError(message)


@Singleton
class ConfigStore:
    """Registry for :class:`ConfigReference` objects.

    References can be registered via :meth:`register` and unregistered again
    using :meth:`unregister`.
    """

    def __init__(self) -> None:
        """Initialize the store."""
        self._known_references: dict[str, ConfigReference] = {}

    def register(
            self,
            name: str,
            target: type[Any],
    ) -> None:
        """Register a target class under a unique name.

        :param name: Identifier for the target class.
        :param target: Class to register.
        """
        reference = ConfigReference(
            name=name,
            target_class=target,
        )
        self._known_references[reference.name] = reference

    def unregister(self, name: str) -> None:
        """Unregister a previously registered configuration reference.

        :param name: Identifier of the reference to unregister.
        :raises KeyError: If no reference with that name exists.
        """
        del self._known_references[name]

    def clear(self) -> None:
        """Clear all registered references.

        This is primarily intended for testing purposes to reset the store
        between test cases.
        """
        self._known_references.clear()

    @property
    def known_references(self) -> MappingProxyType[str, ConfigReference]:
        """Read-only mapping of all registered configuration references."""
        return MappingProxyType(self._known_references)
