"""Incremental composition for config files.

This module provides the IncrementalComposer class that composes config files
incrementally, loading only the files needed to reach and resolve a given path.
This is the unified algorithm for both full and partial composition.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

from rconfig._internal.path_utils import (
    build_child_path,
    get_value_at_path,
    parse_path_segments,
    path_exists,
)
from rconfig.errors import (
    CircularRefError,
    ConfigFileError,
    InstanceResolutionError,
    InvalidInnerPathError,
    RefAtRootError,
    RefInstanceConflictError,
    RefResolutionError,
)
from rconfig.loaders import get_loader
from rconfig.loaders.position_map import PositionMap

from .DependencyAnalyzer import DependencyAnalyzer
from .file_path_resolver import FilePathResolver
from .Merger import deep_merge
from rconfig.provenance import NullProvenanceBuilder, ProvenanceBuilder


# Special keys
_REF_KEY = "_ref_"
_INSTANCE_KEY = "_instance_"
_TARGET_KEY = "_target_"

# Cache management lock
_cache_lock = threading.Lock()


def _load_file_impl(path: str) -> PositionMap:
    """Load a config file with position information.

    This is the actual implementation, wrapped by the cached version.

    :param path: Absolute path to the config file as string.
    :return: PositionMap with line and column information.
    :raises ConfigFileError: If file cannot be loaded.
    """
    path_obj = Path(path)
    loader = get_loader(path_obj)
    return loader.load_with_positions(path_obj)


# Initialize the cached function
_load_file_cached = lru_cache(maxsize=None)(_load_file_impl)


def _load_file_impl_no_positions(path: str) -> dict[str, Any]:
    """Load a config file without position information (faster).

    Used when provenance tracking is disabled to skip PositionMap creation.

    :param path: Absolute path to the config file as string.
    :return: Plain dict without position tracking.
    :raises ConfigFileError: If file cannot be loaded.
    """
    path_obj = Path(path)
    loader = get_loader(path_obj)
    return loader.load(path_obj)


# Initialize the cached function for no-positions loading
_load_file_cached_no_positions = lru_cache(maxsize=None)(_load_file_impl_no_positions)


def set_cache_size(size: int) -> None:
    """Set the LRU cache size for loaded config files.

    Thread-safe: protected by internal lock.

    :param size: Maximum number of files to cache. 0 means unlimited.
    """
    global _load_file_cached, _load_file_cached_no_positions
    with _cache_lock:
        maxsize = None if size == 0 else size
        _load_file_cached = lru_cache(maxsize=maxsize)(_load_file_impl)
        _load_file_cached_no_positions = lru_cache(maxsize=maxsize)(
            _load_file_impl_no_positions
        )


def clear_cache() -> None:
    """Clear the file loading cache.

    Thread-safe: protected by internal lock.
    """
    with _cache_lock:
        _load_file_cached.cache_clear()
        _load_file_cached_no_positions.cache_clear()


@dataclass
class BlockingRef:
    """A _ref_ that blocks access to a target path.

    :param config_path: Path in the config tree where the _ref_ is.
    :param file_path: The file path the _ref_ points to.
    :param inline_overrides: Any keys alongside _ref_ that act as overrides.
    """

    config_path: str
    file_path: str
    inline_overrides: dict[str, Any] = field(default_factory=dict)


@dataclass
class InstanceMarker:
    """An _instance_ marker collected during tree walk.

    :param config_path: Path in the config tree (e.g., "service.db").
    :param instance_path: Target path (e.g., "/shared.database") or None for null.
    :param file_path: Path to the file containing the marker.
    :param line: Line number in the source file (1-indexed).
    """

    config_path: str
    instance_path: str | None
    file_path: str
    line: int


@dataclass
class CompositionResult:
    """Result of composing a config tree.

    :param config: Fully merged config (all _ref_ resolved).
    :param instances: _instance_ markers by config path.
    :param loaded_files: Set of file paths that were loaded.
    :param dependency_closure: Set of config paths in the dependency closure.
    """

    config: dict[str, Any]
    instances: dict[str, InstanceMarker] = field(default_factory=dict)
    loaded_files: set[Path] = field(default_factory=set)
    dependency_closure: set[str] = field(default_factory=set)


class IncrementalComposer:
    """Composes config files incrementally, loading only what's needed.

    This class implements the unified incremental composition algorithm that:
    1. Loads only the files needed to reach the target inner_path
    2. Analyzes dependencies to find required external paths
    3. Loads additional files only for paths in the dependency closure

    When inner_path is empty/None, the algorithm naturally loads all files
    (same as full composition).

    Example::

        composer = IncrementalComposer(config_root, provenance)

        # Partial composition - only loads files needed for "model"
        result = composer.compose(Path("trainer.yaml"), inner_path="model")

        # Full composition - loads all files (inner_path="" or None)
        result = composer.compose(Path("trainer.yaml"))
    """

    def __init__(
        self,
        config_root: Path | None,
        provenance: ProvenanceBuilder,
    ) -> None:
        """Initialize the composer.

        :param config_root: Root directory for absolute path resolution.
                           If None, derived from the composed file's parent.
        :param provenance: ProvenanceBuilder to record value origins.
        """
        self._config_root = config_root
        self._provenance = provenance
        self._track_provenance = not isinstance(provenance, NullProvenanceBuilder)
        self._instances: dict[str, InstanceMarker] = {}
        self._loading_stack: list[str] = []
        self._ref_graph: dict[str, list[str]] = {}
        self._loaded_files: set[Path] = set()
        self._analyzer = DependencyAnalyzer()
        self._inner_path: str = ""
        self._dependency_closure: set[str] = set()

    def compose(
        self,
        path: Path,
        inner_path: str | None = None,
    ) -> CompositionResult:
        """Compose a config file, loading only what's needed for inner_path.

        This is the unified algorithm that works for both full and partial
        composition. When inner_path is None or empty, all files are loaded.

        :param path: Path to the entry-point config file.
        :param inner_path: Optional path to the target subtree. If None or "",
                          composes the entire config (loads all files).
        :return: CompositionResult with merged config and instance markers.
        :raises ConfigFileError: If a file cannot be loaded.
        :raises CircularRefError: If circular references are detected.
        :raises RefAtRootError: If _ref_ is used at root level.
        :raises RefResolutionError: If a _ref_ cannot be resolved.
        :raises InvalidInnerPathError: If inner_path doesn't exist.
        """
        path = path.resolve()
        inner_path = inner_path or ""

        # Set config root to entry file's parent if not specified
        if self._config_root is None:
            self._config_root = path.parent

        self._file_resolver = FilePathResolver(self._config_root)

        # Store inner_path for selective ref resolution
        self._inner_path = inner_path

        # Step 1: Load root file only (no _ref_ resolution yet)
        config = self._load_raw_file(path)
        self._loaded_files.add(path)

        # Check for _ref_ at root level in entry file
        if _REF_KEY in config:
            raise RefAtRootError(str(path))

        # Step 2: Follow inner_path, loading refs as needed
        if inner_path:
            config = self._ensure_path_reachable(config, inner_path, path)

        # Step 3: Dependency analysis rooted at inner_path
        dependencies = self._analyzer.analyze_subtree(config, inner_path)

        # Step 4: Load files for external dependencies
        config, all_deps = self._load_dependencies(config, dependencies, path)

        # Store the dependency closure for selective resolution
        self._dependency_closure = all_deps

        # Now resolve all remaining _ref_ markers in the relevant subtree
        # When inner_path is set, only resolve refs within inner_path and dependencies
        config = self._resolve_all_refs(config, path.parent, "", str(path))

        return CompositionResult(
            config=config,
            instances=self._instances,
            loaded_files=self._loaded_files,
            dependency_closure=all_deps,
        )

    @property
    def ref_graph(self) -> dict[str, list[str]]:
        """Get the graph of _ref_ relationships.

        Returns a mapping of source file path -> list of referenced file paths.
        """
        return self._ref_graph

    def _load_raw_file(self, path: Path) -> PositionMap | dict[str, Any]:
        """Load a config file without resolving _ref_.

        :param path: Absolute path to the config file.
        :return: Raw config dict (may contain _ref_ markers). Returns PositionMap
                 when provenance tracking is enabled, plain dict otherwise.
        """
        path_str = str(path)
        if self._track_provenance:
            return _load_file_cached(path_str)
        return _load_file_cached_no_positions(path_str)

    def _ensure_path_reachable(
        self,
        config: dict[str, Any],
        target_path: str,
        root_file: Path,
    ) -> dict[str, Any]:
        """Ensure a target path is reachable by loading blocking refs.

        :param config: Current config dict.
        :param target_path: The path we need to reach.
        :param root_file: The root config file (for error messages).
        :return: Updated config with necessary refs resolved.
        :raises InvalidInnerPathError: If path cannot be reached.
        """
        max_iterations = 100  # Prevent infinite loops
        iterations = 0

        while not path_exists(config, target_path):
            iterations += 1
            if iterations > max_iterations:
                raise InvalidInnerPathError(
                    target_path, "maximum ref resolution depth exceeded"
                )

            # Find which _ref_ blocks the path
            blocking_ref = self._find_blocking_ref(config, target_path)
            if blocking_ref is None:
                raise InvalidInnerPathError(
                    target_path, f"path not found in config from {root_file}"
                )

            # Load and merge that specific ref
            config = self._resolve_single_ref(
                config,
                blocking_ref,
                root_file.parent,
            )

        return config

    def _find_blocking_ref(
        self,
        config: dict[str, Any],
        target_path: str,
    ) -> BlockingRef | None:
        """Find the _ref_ that blocks access to target_path.

        Walks toward the target path and returns the first _ref_ encountered.

        :param config: The config dictionary.
        :param target_path: The path we're trying to reach.
        :return: BlockingRef if found, None if path should exist or is unreachable.
        """
        segments = parse_path_segments(target_path)
        if not segments:
            return None

        current = config
        current_path = ""

        for i, segment in enumerate(segments):
            if isinstance(segment, int):
                # List index - can't have a _ref_ here
                if not isinstance(current, list):
                    return None
                if segment >= len(current):
                    return None
                current = current[segment]
                current_path = build_child_path(current_path, segment)
            else:
                # Dict key
                if not isinstance(current, dict):
                    return None

                if segment not in current:
                    # Key doesn't exist - path is invalid
                    return None

                value = current[segment]
                next_path = build_child_path(current_path, segment)

                # Check if this is a _ref_ that needs resolution
                if isinstance(value, dict) and _REF_KEY in value:
                    ref_path = value[_REF_KEY]
                    if isinstance(ref_path, str):
                        # Collect inline overrides (keys other than _ref_)
                        overrides = {k: v for k, v in value.items() if k != _REF_KEY}
                        return BlockingRef(
                            config_path=next_path,
                            file_path=ref_path,
                            inline_overrides=overrides,
                        )

                current = value
                current_path = next_path

        return None

    def _resolve_single_ref(
        self,
        config: dict[str, Any],
        blocking_ref: BlockingRef,
        current_dir: Path,
    ) -> dict[str, Any]:
        """Resolve a single _ref_ and merge it into the config.

        This method recursively resolves nested refs inside the loaded file.

        :param config: The current config dictionary.
        :param blocking_ref: The blocking ref to resolve.
        :param current_dir: Directory of the current file.
        :return: Config with the ref resolved.
        """
        # Resolve the file path
        resolved_path = self._file_resolver.resolve(
            blocking_ref.file_path,
            current_dir,
            blocking_ref.config_path,
        )

        # Load the referenced file
        ref_config = self._load_raw_file(resolved_path)
        self._loaded_files.add(resolved_path)

        # Track ref graph
        resolved_str = str(resolved_path)
        parent_file_str = str(current_dir.resolve())
        if parent_file_str not in self._ref_graph:
            self._ref_graph[parent_file_str] = []
        if resolved_str not in self._ref_graph[parent_file_str]:
            self._ref_graph[parent_file_str].append(resolved_str)

        # Check for _ref_ at root of referenced file
        if _REF_KEY in ref_config:
            raise RefAtRootError(str(resolved_path))

        # Apply inline overrides
        if blocking_ref.inline_overrides:
            ref_config = deep_merge(
                dict(ref_config), blocking_ref.inline_overrides, blocking_ref.config_path
            )

        # Recursively resolve any nested _ref_ markers in the loaded file
        # This is critical for partial composition to work with nested refs
        resolved_ref_config = self._resolve_nested_refs_simple(
            ref_config, resolved_path.parent, blocking_ref.config_path
        )

        # Insert the resolved config at the blocking ref's path
        return self._set_value_at_path(config, blocking_ref.config_path, resolved_ref_config)

    def _resolve_nested_refs_simple(
        self,
        config: dict[str, Any] | PositionMap,
        current_dir: Path,
        config_path: str,
    ) -> dict[str, Any]:
        """Recursively resolve _ref_ markers in a config without full provenance tracking.

        This is a simplified version used during incremental loading to resolve
        nested refs that block the target path.

        :param config: Config dict to process.
        :param current_dir: Directory of current file.
        :param config_path: Current path in config tree.
        :return: Config with refs resolved.
        """
        result: dict[str, Any] = {}

        for key, value in config.items():
            current_path = build_child_path(config_path, key)

            if isinstance(value, dict):
                # Check for _ref_
                if _REF_KEY in value:
                    ref_path = value[_REF_KEY]
                    if isinstance(ref_path, str):
                        # Resolve this ref
                        resolved_path = self._file_resolver.resolve(
                            ref_path, current_dir, current_path
                        )
                        ref_config = self._load_raw_file(resolved_path)
                        self._loaded_files.add(resolved_path)

                        # Track in ref graph
                        resolved_str = str(resolved_path)
                        parent_str = str(current_dir.resolve())
                        if parent_str not in self._ref_graph:
                            self._ref_graph[parent_str] = []
                        if resolved_str not in self._ref_graph[parent_str]:
                            self._ref_graph[parent_str].append(resolved_str)

                        # Check for root ref
                        if _REF_KEY in ref_config:
                            raise RefAtRootError(str(resolved_path))

                        # Get overrides
                        overrides = {k: v for k, v in value.items() if k != _REF_KEY}

                        # Recursively resolve
                        resolved_value = self._resolve_nested_refs_simple(
                            ref_config, resolved_path.parent, current_path
                        )

                        # Apply overrides
                        if overrides:
                            resolved_overrides = self._resolve_nested_refs_simple(
                                overrides, current_dir, current_path
                            )
                            resolved_value = deep_merge(
                                resolved_value, resolved_overrides, current_path
                            )

                        result[key] = resolved_value
                    else:
                        result[key] = dict(value)
                else:
                    # Regular dict - recurse
                    result[key] = self._resolve_nested_refs_simple(
                        value, current_dir, current_path
                    )
            elif isinstance(value, list):
                result[key] = self._resolve_list_refs_simple(
                    value, current_dir, current_path
                )
            else:
                result[key] = value

        return result

    def _resolve_list_refs_simple(
        self,
        items: list[Any],
        current_dir: Path,
        config_path: str,
    ) -> list[Any]:
        """Resolve _ref_ markers in a list.

        :param items: List to process.
        :param current_dir: Directory of current file.
        :param config_path: Current path in config tree.
        :return: List with refs resolved.
        """
        result = []
        for i, item in enumerate(items):
            item_path = build_child_path(config_path, i)
            if isinstance(item, dict):
                result.append(self._resolve_nested_refs_simple(item, current_dir, item_path))
            elif isinstance(item, list):
                result.append(self._resolve_list_refs_simple(item, current_dir, item_path))
            else:
                result.append(item)
        return result

    def _load_dependencies(
        self,
        config: dict[str, Any],
        dependencies: set[str],
        root_file: Path,
    ) -> tuple[dict[str, Any], set[str]]:
        """Load files needed to satisfy dependencies.

        :param config: Current config dict.
        :param dependencies: Initial set of dependencies.
        :param root_file: The root config file.
        :return: Tuple of (updated config, complete dependency closure).
        """
        all_deps = set(dependencies)
        pending = list(dependencies)
        visited_deps: set[str] = set()

        while pending:
            dep_path = pending.pop()
            if dep_path in visited_deps:
                continue
            visited_deps.add(dep_path)

            # Skip special markers
            if dep_path.startswith("__ref__:"):
                continue

            # Check if we can reach this dependency
            if not path_exists(config, dep_path):
                blocking_ref = self._find_blocking_ref(config, dep_path)
                if blocking_ref is not None:
                    config = self._resolve_single_ref(
                        config, blocking_ref, root_file.parent
                    )

            # Analyze dependencies of this dependency (transitive closure)
            if path_exists(config, dep_path):
                new_deps = self._analyzer.analyze_subtree(config, dep_path)
                for new_dep in new_deps:
                    if new_dep not in all_deps:
                        all_deps.add(new_dep)
                        pending.append(new_dep)

        return config, all_deps

    def _resolve_all_refs(
        self,
        config: PositionMap | dict[str, Any],
        current_dir: Path,
        config_path: str,
        file_path: str,
    ) -> dict[str, Any]:
        """Recursively resolve all remaining _ref_ markers.

        :param config: Config dict to process (may be PositionMap for line info).
        :param current_dir: Directory of current file.
        :param config_path: Current path in config tree.
        :param file_path: Path to current file.
        :return: Config with all refs resolved.
        """
        result: dict[str, Any] = {}

        for key, value in config.items():
            current_path = build_child_path(config_path, key)
            line = self._get_line_number(config, key)

            if isinstance(value, dict):
                resolved_value = self._resolve_dict_value(
                    value, current_dir, current_path, file_path
                )
                result[key] = resolved_value

                # Record provenance for dict with _target_
                if (
                    isinstance(resolved_value, dict)
                    and _TARGET_KEY in resolved_value
                    and line is not None
                ):
                    target_name = resolved_value.get(_TARGET_KEY)
                    if isinstance(target_name, str):
                        self._provenance.add(
                            current_path,
                            file=file_path,
                            line=line,
                            target_name=target_name,
                        )
            elif isinstance(value, list):
                result[key] = self._resolve_list(
                    value, current_dir, current_path, file_path
                )
                if line is not None:
                    self._provenance.add(current_path, file=file_path, line=line)
            else:
                result[key] = value
                if line is not None:
                    self._provenance.add(current_path, file=file_path, line=line)

        # Record root level _target_ if present
        if config_path == "" and _TARGET_KEY in result:
            target_name = result.get(_TARGET_KEY)
            if isinstance(target_name, str):
                line = self._get_line_number(config, _TARGET_KEY) or 1
                self._provenance.add("", file=file_path, line=line, target_name=target_name)

        return result

    def _should_resolve_path(self, config_path: str) -> bool:
        """Check if a config path should be resolved based on inner_path.

        When inner_path is set, we only resolve paths that are:
        1. Within the inner_path subtree (descendants)
        2. Ancestors leading to inner_path
        3. In the dependency closure

        :param config_path: The config path to check.
        :return: True if the path should be resolved.
        """
        # If no inner_path, resolve everything
        if not self._inner_path:
            return True

        # Check if path is in or leads to inner_path subtree
        # path is ancestor if inner_path starts with path
        # path is descendant if path starts with inner_path
        if not config_path:
            # Root level - always process to reach inner_path
            return True

        inner_path_with_dot = self._inner_path + "."
        config_path_with_dot = config_path + "."

        # Path is ancestor of inner_path
        if inner_path_with_dot.startswith(config_path_with_dot):
            return True

        # Path is descendant of inner_path
        if config_path_with_dot.startswith(inner_path_with_dot):
            return True

        # Path equals inner_path
        if config_path == self._inner_path:
            return True

        # Path is in dependency closure
        if config_path in self._dependency_closure:
            return True

        # Check if any dependency is a descendant of this path
        for dep in self._dependency_closure:
            dep_with_dot = dep + "."
            if dep_with_dot.startswith(config_path_with_dot):
                return True

        return False

    def _resolve_dict_value(
        self,
        value: dict[str, Any],
        current_dir: Path,
        config_path: str,
        file_path: str,
    ) -> dict[str, Any]:
        """Resolve a dict value, handling _ref_ or _instance_ if present.

        :param value: The dict value to process.
        :param current_dir: Directory of current file.
        :param config_path: Current path in config tree.
        :param file_path: Path to current file.
        :return: Resolved dict value.
        """
        has_ref = _REF_KEY in value
        has_instance = _INSTANCE_KEY in value

        # Check for conflict
        if has_ref and has_instance:
            raise RefInstanceConflictError(config_path)

        if has_ref:
            # Check if we should resolve this ref based on inner_path
            if not self._should_resolve_path(config_path):
                # Skip this ref - return the raw dict (keep _ref_ marker)
                return dict(value)
            return self._resolve_ref(value, current_dir, config_path, file_path)
        elif has_instance:
            # Only collect instance markers in the relevant scope
            if not self._should_resolve_path(config_path):
                return dict(value)
            return self._collect_instance_marker(value, config_path, file_path)
        else:
            return self._resolve_all_refs(value, current_dir, config_path, file_path)

    def _resolve_ref(
        self,
        value: dict[str, Any],
        current_dir: Path,
        config_path: str,
        file_path: str,
    ) -> dict[str, Any]:
        """Resolve a _ref_ reference.

        :param value: Dict containing _ref_ and optional overrides.
        :param current_dir: Directory of current file.
        :param config_path: Current path in config tree.
        :param file_path: Path to current file.
        :return: Merged config from referenced file with overrides.
        """
        ref_path = value[_REF_KEY]

        if not isinstance(ref_path, str):
            raise RefResolutionError(
                str(ref_path),
                f"_ref_ must be a string, got {type(ref_path).__name__}",
                config_path,
                hint="Use a string file path like './config.yaml' or '/path/to/config.yaml'.",
            )

        # Resolve the file path
        resolved_path = self._file_resolver.resolve(ref_path, current_dir, config_path)

        # Track the ref relationship
        resolved_path_str = str(resolved_path)
        if file_path not in self._ref_graph:
            self._ref_graph[file_path] = []
        if resolved_path_str not in self._ref_graph[file_path]:
            self._ref_graph[file_path].append(resolved_path_str)

        # Check for circular references
        if resolved_path_str in self._loading_stack:
            cycle_start = self._loading_stack.index(resolved_path_str)
            chain = self._loading_stack[cycle_start:] + [resolved_path_str]
            raise CircularRefError(chain)

        self._loading_stack.append(resolved_path_str)
        self._loaded_files.add(resolved_path)

        try:
            # Load and walk the referenced file
            try:
                ref_config = _load_file_cached(resolved_path_str)
                resolved_config = self._resolve_all_refs(
                    ref_config, resolved_path.parent, config_path, resolved_path_str
                )
            except ConfigFileError as e:
                raise RefResolutionError(ref_path, str(e.reason), config_path) from e

            # Check for _ref_ at root of referenced file
            if _REF_KEY in resolved_config:
                raise RefAtRootError(str(resolved_path))

            # Get overrides (all keys except _ref_)
            override_keys = [k for k in value.keys() if k != _REF_KEY]
            overrides = {k: value[k] for k in override_keys}

            # Check for overriding _target_ to null
            if overrides.get(_TARGET_KEY) is None and _TARGET_KEY in overrides:
                raise RefResolutionError(
                    ref_path,
                    "cannot override _target_ to null",
                    config_path,
                    hint="Remove the _target_ override or set it to a valid target name.",
                )

            # Track provenance for overrides
            self._handle_override_provenance(value, override_keys, config_path, file_path)

            # Walk any refs in the overrides themselves
            if overrides:
                scalar_override_keys = {
                    k for k in override_keys if not isinstance(value[k], (dict, list))
                }
                overrides = self._resolve_all_refs(
                    {k: v for k, v in value.items() if k != _REF_KEY},
                    current_dir,
                    config_path,
                    file_path,
                )

            # Deep merge
            if overrides:
                return deep_merge(resolved_config, overrides, config_path)
            return resolved_config

        finally:
            self._loading_stack.pop()

    def _collect_instance_marker(
        self,
        value: dict[str, Any],
        config_path: str,
        file_path: str,
    ) -> dict[str, Any]:
        """Collect an _instance_ marker for later resolution.

        :param value: Dict containing _instance_ key.
        :param config_path: Current path in config tree.
        :param file_path: Path to current file.
        :return: A marker dict with the _instance_ key preserved.
        """
        instance_path = value[_INSTANCE_KEY]

        if instance_path is not None and not isinstance(instance_path, str):
            raise InstanceResolutionError(
                str(instance_path),
                f"_instance_ must be a string or null, got {type(instance_path).__name__}",
                config_path,
                hint="Use a string path like 'database.connection' to reference another config path.",
            )

        line = self._get_line_number(value, _INSTANCE_KEY)

        self._instances[config_path] = InstanceMarker(
            config_path=config_path,
            instance_path=instance_path,
            file_path=file_path,
            line=line or 0,
        )

        return {_INSTANCE_KEY: instance_path}

    def _resolve_list(
        self,
        items: list[Any],
        current_dir: Path,
        config_path: str,
        file_path: str,
    ) -> list[Any]:
        """Resolve all _ref_ references in a list.

        :param items: The list to process.
        :param current_dir: Directory of current file.
        :param config_path: Current path in config tree.
        :param file_path: Path to current file.
        :return: List with all refs resolved.
        """
        result = []
        for i, item in enumerate(items):
            item_path = build_child_path(config_path, i)
            if isinstance(item, dict):
                resolved_item = self._resolve_dict_value(
                    item, current_dir, item_path, file_path
                )
                result.append(resolved_item)
            elif isinstance(item, list):
                result.append(
                    self._resolve_list(item, current_dir, item_path, file_path)
                )
            else:
                result.append(item)
        return result

    def _handle_override_provenance(
        self,
        value: dict[str, Any],
        override_keys: list[str],
        config_path: str,
        file_path: str,
    ) -> None:
        """Track provenance for override keys.

        :param value: The original dict with _ref_ and overrides.
        :param override_keys: List of keys that are overrides.
        :param config_path: Current path in config tree.
        :param file_path: Path to current file.
        """
        for key in override_keys:
            override_path = build_child_path(config_path, key)
            line = self._get_line_number(value, key)
            if line is not None:
                base_entry = self._provenance.get(override_path)
                if base_entry is not None:
                    self._provenance.add(
                        override_path,
                        file=file_path,
                        line=line,
                        overrode=f"{base_entry.file}:{base_entry.line}",
                    )
                else:
                    self._provenance.add(override_path, file=file_path, line=line)

    def _set_value_at_path(
        self,
        config: dict[str, Any],
        path: str,
        value: Any,
    ) -> dict[str, Any]:
        """Set a value at a config path, creating a new dict.

        :param config: The config dictionary.
        :param path: The path to set.
        :param value: The value to set.
        :return: New config with value set.
        """
        if not path:
            if isinstance(value, dict):
                return {**config, **value}
            return config

        segments = parse_path_segments(path)
        if not segments:
            return config

        # Deep copy and set
        result = dict(config)
        current = result

        for segment in segments[:-1]:
            if isinstance(segment, int):
                # Can't create list indices
                return result
            if segment not in current:
                current[segment] = {}
            elif not isinstance(current[segment], dict):
                return result
            # Make a copy to avoid mutating original
            current[segment] = dict(current[segment])
            current = current[segment]

        final_segment = segments[-1]
        if isinstance(final_segment, int):
            return result
        current[final_segment] = value
        return result

    def _get_line_number(
        self,
        config: PositionMap | dict[str, Any],
        key: str,
    ) -> int | None:
        """Extract line number from PositionMap.

        :param config: The config dictionary (may be PositionMap).
        :param key: The key to get line number for.
        :return: Line number (1-indexed) or None if not available.
        """
        if isinstance(config, PositionMap):
            return config.get_line(key)
        return None
