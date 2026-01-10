"""Path matching with glob-style pattern support.

This module provides the PathMatcher class for matching configuration paths
against patterns with glob-style wildcards:
- Exact match: "model.lr" matches only "model.lr"
- Single wildcard (*): "*.lr" matches "model.lr", "optimizer.lr" (one level)
- Double wildcard (**): "**.lr" matches "model.lr", "a.b.c.lr" (any depth)
"""

from __future__ import annotations

from functools import lru_cache
from typing import Iterable


class PathMatcher:
    """Matches config paths against patterns with glob support.

    Patterns are matched against full config paths from the root.
    No relative path matching is supported.

    Example::

        matcher = PathMatcher()

        # Exact match
        matcher.matches("model.lr", "model.lr")  # True
        matcher.matches("model.lr", "other.lr")  # False

        # Single wildcard - matches one level
        matcher.matches("*.lr", "model.lr")  # True
        matcher.matches("*.lr", "a.b.lr")    # False (two levels)

        # Double wildcard - matches any depth
        matcher.matches("**.lr", "model.lr")  # True
        matcher.matches("**.lr", "a.b.c.lr")  # True
    """

    def matches(self, pattern: str, path: str) -> bool:
        """Check if a path matches a pattern.

        :param pattern: The pattern to match against. Supports:
            - Exact paths: "model.lr"
            - Single wildcard (*): matches exactly one path segment
            - Double wildcard (**): matches zero or more path segments
        :param path: The config path to check.
        :return: True if the path matches the pattern.

        Examples::

            matches("model.lr", "model.lr")      # True - exact match
            matches("*.lr", "model.lr")          # True - * matches "model"
            matches("*.lr", "a.b.lr")            # False - * only matches one segment
            matches("**.lr", "model.lr")         # True - ** matches "model"
            matches("**.lr", "a.b.c.lr")         # True - ** matches "a.b.c"
            matches("model.**.lr", "model.a.lr") # True - ** in middle
            matches("model.*", "model.lr")       # True - * at end
        """
        return self._match_segments(
            pattern.split(".") if pattern else [],
            path.split(".") if path else [],
        )

    def _match_segments(
        self,
        pattern_parts: list[str],
        path_parts: list[str],
    ) -> bool:
        """Recursively match pattern segments against path segments.

        :param pattern_parts: Remaining pattern segments to match.
        :param path_parts: Remaining path segments to match against.
        :return: True if the pattern matches the path.
        """
        # Base cases
        if not pattern_parts and not path_parts:
            return True
        if not pattern_parts:
            return False

        first_pattern = pattern_parts[0]
        rest_pattern = pattern_parts[1:]

        # Handle ** (matches zero or more segments)
        if first_pattern == "**":
            # Try matching zero segments (skip **)
            if self._match_segments(rest_pattern, path_parts):
                return True
            # Try matching one or more segments (consume one path segment)
            if path_parts and self._match_segments(pattern_parts, path_parts[1:]):
                return True
            return False

        # Handle * (matches exactly one segment)
        if first_pattern == "*":
            if not path_parts:
                return False
            # * must match a non-empty segment
            if not path_parts[0]:
                return False
            return self._match_segments(rest_pattern, path_parts[1:])

        # Handle literal match
        if not path_parts:
            return False
        if first_pattern != path_parts[0]:
            return False
        return self._match_segments(rest_pattern, path_parts[1:])

    def find_match(self, path: str, patterns: Iterable[str]) -> str | None:
        """Find the first pattern that matches a path.

        :param path: The config path to check.
        :param patterns: An iterable of patterns to check against.
        :return: The first matching pattern, or None if no match.

        Example::

            patterns = ["model.lr", "*.dropout", "**.hidden_size"]
            find_match("encoder.dropout", patterns)  # "*.dropout"
        """
        for pattern in patterns:
            if self.matches(pattern, path):
                return pattern
        return None


# Module-level singleton for convenience
_matcher = PathMatcher()


def matches(pattern: str, path: str) -> bool:
    """Check if a path matches a pattern using the module-level matcher.

    :param pattern: The pattern to match against.
    :param path: The config path to check.
    :return: True if the path matches the pattern.
    """
    return _matcher.matches(pattern, path)


def find_match(path: str, patterns: Iterable[str]) -> str | None:
    """Find the first pattern that matches a path using the module-level matcher.

    :param path: The config path to check.
    :param patterns: An iterable of patterns to check against.
    :return: The first matching pattern, or None if no match.
    """
    return _matcher.find_match(path, patterns)
