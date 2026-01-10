"""Resolver registry for custom interpolation resolvers.

This module provides the ResolverRegistry class for registering and invoking
custom resolver functions that can be called from interpolation expressions
using the syntax: ${app:resolver_name(args)}.
"""

from __future__ import annotations

import inspect
import threading
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Callable

from rconfig._internal import Singleton
from rconfig.errors import ResolverExecutionError, UnknownResolverError


@dataclass(frozen=True)
class ResolverReference:
    """Immutable reference to a registered resolver.

    :param path: Colon-joined resolver path (e.g., "uuid", "db:lookup").
    :param func: The resolver function.
    :param needs_config: True if the function has a `_config_` parameter.
    :param signature: The function's signature for argument validation.
    """

    path: str
    func: Callable[..., Any]
    needs_config: bool
    signature: inspect.Signature


@Singleton
class ResolverRegistry:
    """Thread-safe registry for custom resolvers.

    Follows the same pattern as ConfigStore for API consistency.
    Resolvers are stored with colon-joined path keys (e.g., "db:lookup").

    Example::

        registry = ResolverRegistry()

        # Register a simple resolver
        registry.register("uuid", func=lambda: str(uuid.uuid4()))

        # Register a namespaced resolver
        registry.register("db", "lookup", func=my_lookup_fn)

        # Check if resolver exists
        if "db:lookup" in registry:
            value = registry.resolve("db:lookup", ["users"], {"id": 42}, config)

        # Get all registered resolvers
        for path, ref in registry.known_resolvers.items():
            print(f"{path}: {ref.func.__name__}")
    """

    def __init__(self) -> None:
        """Initialize an empty resolver registry."""
        self._known_resolvers: dict[str, ResolverReference] = {}
        self._lock = threading.RLock()

    @property
    def known_resolvers(self) -> MappingProxyType[str, ResolverReference]:
        """Read-only view of all registered resolvers.

        :return: Mapping from resolver path to ResolverReference.
        """
        return MappingProxyType(self._known_resolvers)

    def __contains__(self, path: str) -> bool:
        """Check if a resolver is registered using 'in' keyword.

        Thread-safe: protected by internal lock.

        :param path: Colon-joined resolver path (e.g., "uuid", "db:lookup").
        :return: True if the resolver is registered.

        Example::

            if "db:lookup" in registry:
                ...
        """
        with self._lock:
            return path in self._known_resolvers

    def register(self, *path: str, func: Callable[..., Any]) -> None:
        """Register a resolver under a path.

        :param path: One or more path components (e.g., "uuid" or "db", "lookup").
                     Also accepts colon or dot-delimited strings: "db:lookup" or "db.lookup".
        :param func: The resolver function to register.
        :raises ValueError: If path is empty or func is not callable.

        Examples::

            register("uuid", func=my_uuid)              # ${app:uuid}
            register("db", "lookup", func=my_lookup)    # ${app:db:lookup}
            register("db:lookup", func=my_lookup)       # ${app:db:lookup} (alternative)
            register("db.lookup", func=my_lookup)       # ${app:db:lookup} (alternative)
        """
        if not path:
            raise ValueError("Resolver path cannot be empty")
        if not callable(func):
            raise ValueError(f"Resolver must be callable, got {type(func).__name__}")

        # Normalize path: handle single string with delimiters
        normalized_path: tuple[str, ...]
        if len(path) == 1:
            single = path[0]
            if ":" in single:
                normalized_path = tuple(single.split(":"))
            elif "." in single:
                normalized_path = tuple(single.split("."))
            else:
                normalized_path = path
        else:
            normalized_path = path

        key = ":".join(normalized_path)
        sig = inspect.signature(func)
        needs_config = "_config_" in sig.parameters

        ref = ResolverReference(
            path=key,
            func=func,
            needs_config=needs_config,
            signature=sig,
        )

        with self._lock:
            self._known_resolvers[key] = ref

    def unregister(self, *path: str) -> None:
        """Unregister a resolver by path.

        :param path: One or more path components (e.g., "uuid" or "db", "lookup").
                     Also accepts colon or dot-delimited strings: "db:lookup" or "db.lookup".
        :raises KeyError: If the resolver is not registered.
        """
        # Normalize path: handle single string with delimiters
        normalized_path: tuple[str, ...]
        if len(path) == 1:
            single = path[0]
            if ":" in single:
                normalized_path = tuple(single.split(":"))
            elif "." in single:
                normalized_path = tuple(single.split("."))
            else:
                normalized_path = path
        else:
            normalized_path = path

        key = ":".join(normalized_path)
        with self._lock:
            if key not in self._known_resolvers:
                raise KeyError(f"Resolver '{key}' is not registered")
            del self._known_resolvers[key]

    def clear(self) -> None:
        """Clear all registered resolvers.

        Thread-safe: protected by internal lock.
        This is primarily intended for testing purposes to reset the registry
        between test cases.
        """
        with self._lock:
            self._known_resolvers.clear()

    def resolve(
        self,
        path: str,
        args: list[Any],
        kwargs: dict[str, Any],
        config: dict[str, Any] | None,
    ) -> Any:
        """Invoke a resolver by its colon-joined path.

        :param path: Colon-joined resolver path (e.g., "uuid", "db:lookup").
        :param args: Positional arguments to pass to the resolver.
        :param kwargs: Keyword arguments to pass to the resolver.
        :param config: The config dictionary (passed as read-only if resolver needs it).
        :return: The value returned by the resolver function.
        :raises UnknownResolverError: If the resolver is not registered.
        :raises ResolverExecutionError: If the resolver function raises an exception.
        """
        ref = self._known_resolvers.get(path)
        if ref is None:
            available = list(self._known_resolvers.keys())
            raise UnknownResolverError(path, available)

        # Prepare arguments
        call_kwargs = dict(kwargs)
        if ref.needs_config:
            # Pass config as read-only MappingProxyType
            call_kwargs["_config_"] = (
                MappingProxyType(config) if config is not None else MappingProxyType({})
            )

        # Call the resolver
        try:
            return ref.func(*args, **call_kwargs)
        except Exception as e:
            raise ResolverExecutionError(path, e) from e
