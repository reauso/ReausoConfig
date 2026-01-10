"""Deprecation information dataclass.

This module provides the DeprecationInfo dataclass that holds information
about a deprecated configuration key, including the pattern, new key,
message, removal version, and policy override.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

DeprecationPolicy = Literal["warn", "error", "ignore"]


@dataclass(frozen=True)
class DeprecationInfo:
    """Information about a deprecated configuration key.

    :param pattern: The registered pattern (exact path or glob pattern).
    :param matched_path: The actual config path that matched the pattern.
                         Set during detection, None for registered patterns.
    :param new_key: The new key path to migrate to (e.g., "model.optimizer.lr").
    :param message: Custom deprecation message for the user.
    :param remove_in: Version in which the key will be removed (e.g., "2.0.0").
    :param policy: Per-deprecation policy override (warn/error/ignore).
                   None means use global policy.

    Example::

        info = DeprecationInfo(
            pattern="learning_rate",
            new_key="model.optimizer.lr",
            message="Use 'model.optimizer.lr' instead",
            remove_in="2.0.0",
        )
    """

    pattern: str
    matched_path: str | None = None
    new_key: str | None = None
    message: str | None = None
    remove_in: str | None = None
    policy: DeprecationPolicy | None = None

    def with_matched_path(self, path: str) -> DeprecationInfo:
        """Create a copy with the matched_path set.

        :param path: The actual config path that matched this pattern.
        :return: A new DeprecationInfo with matched_path set.
        """
        return DeprecationInfo(
            pattern=self.pattern,
            matched_path=path,
            new_key=self.new_key,
            message=self.message,
            remove_in=self.remove_in,
            policy=self.policy,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation.

        :return: Dictionary with non-None fields.
        """
        result: dict[str, Any] = {"pattern": self.pattern}
        if self.matched_path is not None:
            result["matched_path"] = self.matched_path
        if self.new_key is not None:
            result["new_key"] = self.new_key
        if self.message is not None:
            result["message"] = self.message
        if self.remove_in is not None:
            result["remove_in"] = self.remove_in
        if self.policy is not None:
            result["policy"] = self.policy
        return result
