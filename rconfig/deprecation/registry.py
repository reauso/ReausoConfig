"""Deprecation registry for managing deprecated configuration keys.

This module provides the DeprecationRegistry singleton for registering
deprecated keys, managing global deprecation policy, and handling
deprecation warnings.
"""

from __future__ import annotations

import threading
from types import MappingProxyType
from typing import TYPE_CHECKING, Callable

from rconfig._internal import Singleton
from rconfig.deprecation.handler import (
    DefaultDeprecationHandler,
    DeprecationHandler,
    FunctionDeprecationHandler,
)
from rconfig.deprecation.info import DeprecationInfo, DeprecationPolicy
from rconfig.deprecation.matcher import PathMatcher

if TYPE_CHECKING:
    pass


@Singleton
class DeprecationRegistry:
    """Thread-safe registry for deprecated configuration keys.

    Follows the same pattern as ResolverRegistry for API consistency.
    Deprecations are stored by their pattern (exact path or glob).

    Example::

        registry = DeprecationRegistry()

        # Register a deprecation
        registry.register(
            old_key="learning_rate",
            new_key="model.optimizer.lr",
            remove_in="2.0.0"
        )

        # Register with glob pattern
        registry.register("**.dropout", message="Dropout configured elsewhere")

        # Check if a path matches any deprecation
        info = registry.find_match("model.dropout")
        if info:
            print(f"Deprecated: {info.pattern}")

        # Set global policy
        registry.set_policy("error")

        # Get effective policy for a deprecation
        policy = registry.effective_policy(info)
    """

    def __init__(self) -> None:
        """Initialize an empty deprecation registry."""
        self._deprecations: dict[str, DeprecationInfo] = {}
        self._global_policy: DeprecationPolicy = "warn"
        self._handler: DeprecationHandler = DefaultDeprecationHandler()
        self._matcher = PathMatcher()
        self._lock = threading.RLock()

    @property
    def known_deprecations(self) -> MappingProxyType[str, DeprecationInfo]:
        """Read-only view of all registered deprecations.

        :return: Mapping from pattern to DeprecationInfo.
        """
        return MappingProxyType(self._deprecations)

    @property
    def global_policy(self) -> DeprecationPolicy:
        """Current global deprecation policy.

        :return: The global policy ("warn", "error", or "ignore").
        """
        return self._global_policy

    @property
    def handler(self) -> DeprecationHandler:
        """Current deprecation warning handler.

        :return: The handler instance used for "warn" policy.
        """
        return self._handler

    def register(
        self,
        old_key: str,
        *,
        new_key: str | None = None,
        message: str | None = None,
        remove_in: str | None = None,
        policy: DeprecationPolicy | None = None,
    ) -> None:
        """Register a deprecated key.

        :param old_key: The deprecated key pattern. Supports exact paths and
                        glob patterns (* for single level, ** for any depth).
        :param new_key: The new key path to migrate to.
        :param message: Custom deprecation message.
        :param remove_in: Version in which the key will be removed.
        :param policy: Per-deprecation policy override.

        Examples::

            # Exact path
            register("learning_rate", new_key="model.optimizer.lr")

            # Single wildcard
            register("*.lr", message="Use full path")

            # Double wildcard
            register("**.dropout", message="Dropout configured elsewhere")
        """
        info = DeprecationInfo(
            pattern=old_key,
            new_key=new_key,
            message=message,
            remove_in=remove_in,
            policy=policy,
        )

        with self._lock:
            self._deprecations[old_key] = info

    def unregister(self, old_key: str) -> None:
        """Unregister a deprecated key.

        :param old_key: The pattern to unregister.
        :raises KeyError: If the pattern is not registered.
        """
        with self._lock:
            if old_key not in self._deprecations:
                raise KeyError(f"Key '{old_key}' is not registered as deprecated")
            del self._deprecations[old_key]

    def is_deprecated(self, key: str) -> bool:
        """Check if a key pattern is registered as deprecated.

        This checks for an exact pattern match, not glob matching.
        Use find_match() to check if a path matches any pattern.

        :param key: The pattern to check.
        :return: True if the pattern is registered.
        """
        with self._lock:
            return key in self._deprecations

    def get(self, key: str) -> DeprecationInfo | None:
        """Get deprecation info for an exact pattern.

        This looks up by exact pattern, not by glob matching.
        Use find_match() to find a pattern that matches a path.

        :param key: The pattern to look up.
        :return: The DeprecationInfo, or None if not registered.
        """
        return self._deprecations.get(key)

    def find_match(self, path: str) -> DeprecationInfo | None:
        """Find a deprecation pattern that matches a config path.

        This uses glob matching to find patterns that match the path.
        Exact matches are checked first, then glob patterns.

        :param path: The config path to check.
        :return: The DeprecationInfo for the matching pattern, or None.
        """
        with self._lock:
            # Check exact match first (faster)
            if path in self._deprecations:
                return self._deprecations[path]

            # Check glob patterns
            patterns = self._deprecations.keys()
            matched_pattern = self._matcher.find_match(path, patterns)
            if matched_pattern:
                return self._deprecations[matched_pattern]

            return None

    def set_policy(self, policy: DeprecationPolicy) -> None:
        """Set the global deprecation policy.

        :param policy: The policy to set ("warn", "error", or "ignore").
        """
        with self._lock:
            self._global_policy = policy

    def set_handler(self, handler: DeprecationHandler) -> None:
        """Set the deprecation warning handler.

        :param handler: The handler to use for "warn" policy.
        """
        with self._lock:
            self._handler = handler

    def set_handler_func(
        self,
        func: Callable[[DeprecationInfo, str, str, int], None],
    ) -> None:
        """Set the deprecation warning handler from a function.

        :param func: A function with signature (info, path, file, line) -> None.
        """
        with self._lock:
            self._handler = FunctionDeprecationHandler(func)

    def effective_policy(self, info: DeprecationInfo) -> DeprecationPolicy:
        """Get the effective policy for a deprecation.

        Returns the per-deprecation policy if set, otherwise the global policy.

        :param info: The deprecation info.
        :return: The effective policy.
        """
        if info.policy is not None:
            return info.policy
        return self._global_policy

    def clear(self) -> None:
        """Clear all registered deprecations.

        Thread-safe: protected by internal lock.
        This is primarily intended for testing purposes to reset the registry
        between test cases. Also resets the handler to default.
        """
        with self._lock:
            self._deprecations.clear()
            self._global_policy = "warn"
            self._handler = DefaultDeprecationHandler()


def get_deprecation_registry() -> DeprecationRegistry:
    """Get the global deprecation registry instance.

    :return: The DeprecationRegistry singleton.
    """
    return DeprecationRegistry()
