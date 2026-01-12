"""Dependency analyzer for incremental config composition.

This module provides the DependencyAnalyzer class that analyzes config values
to extract dependency information from interpolations and _instance_ references.
Used for lazy loading and incremental composition.
"""

from __future__ import annotations

import re
from typing import Any

from rconfig._internal.path_utils import (
    build_child_path,
    get_value_at_path,
    parse_path_segments,
    path_exists,
)
from rconfig.interpolation.parser import find_interpolations, has_interpolation


# Special keys
_REF_KEY = "_ref_"
_INSTANCE_KEY = "_instance_"
_TARGET_KEY = "_target_"

# Pattern to extract config path references from interpolation expressions
# Matches: /path.to.key, ./relative.path, path.to.key (not starting with special chars)
_CONFIG_PATH_PATTERN = re.compile(
    r"""
    (?:^|[^a-zA-Z0-9_])  # Start or non-identifier char
    (
        /[a-zA-Z_][a-zA-Z0-9_./\[\]]*  # Absolute path: /model.lr
        |
        \./[a-zA-Z_][a-zA-Z0-9_./\[\]]*  # Relative path: ./local.lr
        |
        (?<![a-zA-Z0-9_:])[a-zA-Z_][a-zA-Z0-9_.]*(?:\[[0-9]+\])?(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*  # Simple path: model.lr
    )
    """,
    re.VERBOSE,
)

# Pattern to detect nested interpolations: ${...${...}...}
_NESTED_INTERPOLATION_PATTERN = re.compile(r"\$\{[^}]*\$\{")


class DependencyAnalyzer:
    """Analyzes config values to extract dependency information.

    Key principle: Analysis is always ROOTED at a specific path.
    It only walks the subtree under that path, not the entire config.

    This class extracts:
    - Config path references from interpolation expressions (${/path}, ${./path})
    - _instance_ target paths for object sharing
    - Unresolved _ref_ markers that need loading

    Example::

        analyzer = DependencyAnalyzer()

        # Find external dependencies for a subtree
        deps = analyzer.analyze_subtree(config, "model")
        # Returns {"training.lr", "shared.database"} etc.

        # Extract paths from a single interpolation expression
        paths = analyzer.extract_paths_from_expression("/model.lr * 2 + /defaults.scale")
        # Returns {"/model.lr", "/defaults.scale"}
    """

    def analyze_subtree(
        self,
        config: dict[str, Any],
        root_path: str,
    ) -> set[str]:
        """Find all external paths referenced by the subtree at root_path.

        IMPORTANT: Only analyzes the subtree under root_path, not the entire config.
        Returns paths that are OUTSIDE the root_path subtree.

        :param config: The full config dictionary.
        :param root_path: The path to the subtree root (empty string for entire config).
        :return: Set of absolute config paths that the subtree depends on.
        """
        # Get the subtree value
        if root_path:
            try:
                subtree = get_value_at_path(config, root_path)
            except (KeyError, IndexError, TypeError):
                return set()
        else:
            subtree = config

        # Collect all dependencies
        dependencies: set[str] = set()
        self._walk_and_collect(subtree, root_path, dependencies, config)

        # Filter to only external dependencies (outside root_path subtree)
        external_deps: set[str] = set()
        for dep in dependencies:
            if not self._is_descendant_of(dep, root_path):
                external_deps.add(dep)

        return external_deps

    def find_unresolved_refs(
        self,
        config: dict[str, Any],
        root_path: str,
    ) -> dict[str, str]:
        """Find unresolved _ref_ markers in the subtree.

        :param config: The full config dictionary.
        :param root_path: The path to the subtree root.
        :return: Dict mapping config paths to their _ref_ file paths.
        """
        if root_path:
            try:
                subtree = get_value_at_path(config, root_path)
            except (KeyError, IndexError, TypeError):
                return {}
        else:
            subtree = config

        refs: dict[str, str] = {}
        self._find_refs(subtree, root_path, refs)
        return refs

    def extract_paths_from_expression(
        self,
        expression: str,
        current_path: str = "",
    ) -> set[str]:
        """Extract config path references from an interpolation expression.

        Handles absolute paths (/path), relative paths (./path), and simple paths.
        Converts all paths to absolute form.

        :param expression: The interpolation expression (without ${}).
        :param current_path: Current config path for relative resolution.
        :return: Set of absolute config paths referenced.
        """
        paths: set[str] = set()

        # Skip expressions that are clearly not config references
        # Environment variables (env:VAR), app resolvers (app:resolver)
        if expression.startswith("env:") or expression.startswith("app:"):
            return paths

        for match in _CONFIG_PATH_PATTERN.finditer(expression):
            path = match.group(1)
            if not path:
                continue

            # Skip resolver calls like app:uuid or db:lookup
            if ":" in path:
                continue

            # Convert to absolute path
            abs_path = self._to_absolute_path(path, current_path)
            if abs_path:
                paths.add(abs_path)

        return paths

    def has_nested_interpolation(self, expression: str) -> bool:
        """Check if an expression contains nested interpolations.

        Nested interpolations like ${/configs.${./source}.lr} need special
        handling during dependency analysis.

        :param expression: The interpolation expression to check.
        :return: True if nested interpolations are present.
        """
        return bool(_NESTED_INTERPOLATION_PATTERN.search(expression))

    def resolve_nested_interpolation(
        self,
        expression: str,
        config: dict[str, Any],
        current_path: str,
    ) -> set[str]:
        """Resolve nested interpolations to get concrete paths.

        For ${/configs.${./source}.lr}:
        1. Find ${./source} - resolve to concrete value
        2. Substitute to get /configs.production.lr
        3. Return {"/configs.production.lr"}

        :param expression: Expression with potential nested interpolations.
        :param config: Config dictionary for resolving inner values.
        :param current_path: Current path for relative resolution.
        :return: Set of resolved absolute paths.
        :raises ValueError: If inner interpolation cannot be resolved.
        """
        paths: set[str] = set()

        # Find all inner interpolations
        inner_matches = find_interpolations(expression)
        if not inner_matches:
            # No nested interpolations, use regular extraction
            return self.extract_paths_from_expression(expression, current_path)

        # Try to resolve inner interpolations to concrete values
        resolved_expr = expression
        for match in inner_matches:
            inner_expr = match.expression

            # Extract the path from inner expression
            inner_paths = self.extract_paths_from_expression(inner_expr, current_path)
            if len(inner_paths) == 1:
                inner_path = next(iter(inner_paths))
                try:
                    inner_value = get_value_at_path(config, inner_path)
                    if isinstance(inner_value, (str, int, float)):
                        # Replace the inner interpolation with its value
                        resolved_expr = resolved_expr.replace(
                            f"${{{inner_expr}}}", str(inner_value)
                        )
                except (KeyError, IndexError, TypeError):
                    # Can't resolve - add inner path as dependency
                    paths.add(inner_path)
                    continue

        # Extract paths from the (possibly partially) resolved expression
        paths.update(self.extract_paths_from_expression(resolved_expr, current_path))
        return paths

    def _walk_and_collect(
        self,
        value: Any,
        path: str,
        dependencies: set[str],
        full_config: dict[str, Any],
    ) -> None:
        """Walk a value and collect all dependency paths.

        :param value: Current value being walked.
        :param path: Current path in the config tree.
        :param dependencies: Set to accumulate dependencies into.
        :param full_config: Full config for nested interpolation resolution.
        """
        if isinstance(value, str):
            if has_interpolation(value):
                self._collect_from_string(value, path, dependencies, full_config)

        elif isinstance(value, dict):
            # Check for _instance_ reference
            if _INSTANCE_KEY in value:
                instance_path = value[_INSTANCE_KEY]
                if isinstance(instance_path, str):
                    abs_path = self._to_absolute_path(instance_path, path)
                    if abs_path:
                        dependencies.add(abs_path)

            # Check for _ref_ - these need to be loaded before we can analyze deeper
            if _REF_KEY in value:
                ref_path = value[_REF_KEY]
                if isinstance(ref_path, str):
                    # _ref_ is a file path, not a config path dependency
                    # but we mark the config path as having an unresolved ref
                    dependencies.add(f"__ref__:{path}")

            # Recurse into dict values
            for key, val in value.items():
                if key in (_REF_KEY, _INSTANCE_KEY):
                    continue
                child_path = build_child_path(path, key)
                self._walk_and_collect(val, child_path, dependencies, full_config)

        elif isinstance(value, list):
            for i, item in enumerate(value):
                item_path = build_child_path(path, i)
                self._walk_and_collect(item, item_path, dependencies, full_config)

    def _collect_from_string(
        self,
        value: str,
        path: str,
        dependencies: set[str],
        full_config: dict[str, Any],
    ) -> None:
        """Collect dependencies from an interpolation string.

        :param value: String with ${...} patterns.
        :param path: Current config path.
        :param dependencies: Set to accumulate dependencies into.
        :param full_config: Full config for nested interpolation resolution.
        """
        matches = find_interpolations(value)
        for match in matches:
            expr = match.expression

            # Check for nested interpolations
            if self.has_nested_interpolation(f"${{{expr}}}"):
                try:
                    paths = self.resolve_nested_interpolation(expr, full_config, path)
                    dependencies.update(paths)
                except (ValueError, KeyError):
                    # Can't resolve nested - extract what we can
                    paths = self.extract_paths_from_expression(expr, path)
                    dependencies.update(paths)
            else:
                paths = self.extract_paths_from_expression(expr, path)
                dependencies.update(paths)

    def _find_refs(
        self,
        value: Any,
        path: str,
        refs: dict[str, str],
    ) -> None:
        """Find all _ref_ markers in a value tree.

        :param value: Current value being walked.
        :param path: Current path in the config tree.
        :param refs: Dict to accumulate refs into (path -> file_path).
        """
        if isinstance(value, dict):
            if _REF_KEY in value:
                ref_path = value[_REF_KEY]
                if isinstance(ref_path, str):
                    refs[path] = ref_path

            for key, val in value.items():
                if key == _REF_KEY:
                    continue
                child_path = build_child_path(path, key)
                self._find_refs(val, child_path, refs)

        elif isinstance(value, list):
            for i, item in enumerate(value):
                item_path = build_child_path(path, i)
                self._find_refs(item, item_path, refs)

    def _to_absolute_path(self, path: str, current_path: str) -> str | None:
        """Convert a path reference to absolute form.

        :param path: The path reference (may be absolute or relative).
        :param current_path: Current config path for relative resolution.
        :return: Absolute path, or None if invalid.
        """
        if not path:
            return None

        if path.startswith("/"):
            # Absolute path from root
            return path[1:] if len(path) > 1 else ""
        elif path.startswith("./"):
            # Relative path - resolve from current context
            relative_part = path[2:]
            if current_path:
                # Get parent of current path
                segments = parse_path_segments(current_path)
                if segments:
                    # Remove last segment to get parent
                    parent_segments = segments[:-1]
                    parent_path = self._segments_to_path(parent_segments)
                    if parent_path:
                        return f"{parent_path}.{relative_part}"
            return relative_part
        else:
            # Simple path - treat as absolute from root
            return path

    def _segments_to_path(self, segments: list[str | int]) -> str:
        """Convert path segments back to a path string.

        :param segments: List of path segments.
        :return: Path string.
        """
        if not segments:
            return ""

        parts: list[str] = []
        for segment in segments:
            if isinstance(segment, int):
                if parts:
                    parts[-1] = f"{parts[-1]}[{segment}]"
                else:
                    parts.append(f"[{segment}]")
            else:
                parts.append(segment)
        return ".".join(parts)

    def _is_descendant_of(self, path: str, ancestor_path: str) -> bool:
        """Check if a path is a descendant of another path.

        :param path: The path to check.
        :param ancestor_path: The potential ancestor path.
        :return: True if path is a descendant of ancestor_path.
        """
        if not ancestor_path:
            # Everything is a descendant of root
            return True
        if not path:
            return False

        # Path is descendant if it starts with ancestor_path followed by . or [
        if path == ancestor_path:
            return True
        if path.startswith(ancestor_path + "."):
            return True
        if path.startswith(ancestor_path + "["):
            return True
        return False
