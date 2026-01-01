"""Composition walker for config files.

This module provides the CompositionWalker class that walks config trees,
resolving _ref_ references and collecting _instance_ markers for later resolution.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

from ruamel.yaml.comments import CommentedMap

from .ConfigMerger import deep_merge
from .errors import (
    CircularRefError,
    ConfigFileError,
    InstanceResolutionError,
    RefAtRootError,
    RefInstanceConflictError,
    RefResolutionError,
)
from .loaders.yaml_loader import YamlConfigLoader
from .Provenance import Provenance


# Special keys
_REF_KEY = "_ref_"
_INSTANCE_KEY = "_instance_"
_TARGET_KEY = "_target_"

# Shared yaml loader instance for position-aware loading
_yaml_loader = YamlConfigLoader()

def set_cache_size(size: int) -> None:
    """Set the LRU cache size for loaded config files.

    :param size: Maximum number of files to cache. 0 means unlimited.
    """
    global _load_file_cached
    maxsize = None if size == 0 else size
    _load_file_cached = lru_cache(maxsize=maxsize)(_load_file_cached.__wrapped__)


@lru_cache(maxsize=None)
def _load_file_cached(path: str) -> CommentedMap:
    """Load a config file with caching and position information.

    :param path: Absolute path to the config file as string.
    :return: CommentedMap with line number information.
    :raises ConfigFileError: If file cannot be loaded.
    """
    return _yaml_loader.load_with_positions(Path(path))


def clear_cache() -> None:
    """Clear the file loading cache."""
    _load_file_cached.cache_clear()


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
    """

    config: dict[str, Any]
    instances: dict[str, InstanceMarker] = field(default_factory=dict)


class CompositionWalker:
    """Composes config tree, resolving _ref_ and collecting _instance_ markers.

    This class composes config files by walking the tree, loading and merging
    _ref_ files, while collecting _instance_ markers for later resolution by
    InstanceResolver. Provenance (file:line origins) is always tracked.

    Example::

        provenance = Provenance()
        walker = CompositionWalker(config_root, provenance)
        result = walker.compose(Path("app.yaml"))
        # result.config has all _ref_ resolved
        # result.instances has _instance_ markers to resolve
    """

    def __init__(
        self,
        config_root: Path | None,
        provenance: Provenance,
    ) -> None:
        """Initialize the walker.

        :param config_root: Root directory for absolute path resolution.
                           If None, derived from the walked file's parent.
        :param provenance: Provenance tracker to record value origins.
        """
        self._config_root = config_root
        self._provenance = provenance
        self._instances: dict[str, InstanceMarker] = {}
        self._loading_stack: list[str] = []

    def compose(self, path: Path) -> CompositionResult:
        """Compose a config file by resolving _ref_ and collecting _instance_ markers.

        :param path: Path to the config file.
        :return: CompositionResult with merged config and instance markers.
        :raises ConfigFileError: If a file cannot be loaded.
        :raises CircularRefError: If circular references are detected.
        :raises RefAtRootError: If _ref_ is used at root level.
        :raises RefResolutionError: If a _ref_ cannot be resolved.
        """
        path = path.resolve()

        # Set config root to entry file's parent if not specified
        if self._config_root is None:
            self._config_root = path.parent

        config = self._load_and_walk(path)

        # Check for _ref_ at root level in entry file
        if _REF_KEY in config:
            raise RefAtRootError(str(path))

        return CompositionResult(
            config=config,
            instances=self._instances,
        )

    # =========================================================================
    # Core walking algorithm
    # =========================================================================

    def _load_and_walk(
        self,
        path: Path,
        parent_config_path: str = "",
    ) -> dict[str, Any]:
        """Load a config file and walk its tree.

        :param path: Absolute path to the config file.
        :param parent_config_path: Path prefix from parent config (for _ref_).
        :return: Config with all _ref_ references resolved.
        """
        path_str = str(path)

        # Check for circular references
        if path_str in self._loading_stack:
            cycle_start = self._loading_stack.index(path_str)
            chain = self._loading_stack[cycle_start:] + [path_str]
            raise CircularRefError(chain)

        self._loading_stack.append(path_str)

        try:
            config = _load_file_cached(path_str)
            resolved = self._walk_dict(
                config, path.parent, parent_config_path, path_str
            )
            return resolved
        finally:
            self._loading_stack.pop()

    def _walk_dict(
        self,
        config: dict[str, Any],
        current_dir: Path,
        config_path: str,
        file_path: str,
        skip_keys: set[str] | None = None,
        skip_provenance_for: set[str] | None = None,
    ) -> dict[str, Any]:
        """Recursively walk a dict, resolving _ref_ references.

        :param config: The config dictionary to process.
        :param current_dir: Directory of the current file (for relative paths).
        :param config_path: Current path in the config tree.
        :param file_path: Path to the current file.
        :param skip_keys: Keys to skip (e.g., _ref_ when processing overrides).
        :param skip_provenance_for: Keys to skip provenance recording for.
        :return: Config with all _ref_ references resolved.
        """
        result = {}
        skip_keys = skip_keys or set()
        skip_provenance_for = skip_provenance_for or set()

        for key, value in config.items():
            if key in skip_keys:
                continue

            current_path = f"{config_path}.{key}" if config_path else key
            line = self._get_line_number(config, key)
            should_record = key not in skip_provenance_for

            if isinstance(value, dict):
                resolved_value = self._walk_dict_value(
                    value, current_dir, current_path, file_path
                )
                result[key] = resolved_value
            elif isinstance(value, list):
                result[key] = self._walk_list(
                    value, current_dir, current_path, file_path
                )
                # Record provenance for the list key itself
                if line is not None and should_record:
                    self._provenance.add(current_path, file=file_path, line=line)
            else:
                result[key] = value
                # Record provenance for scalar values
                if line is not None and should_record:
                    self._provenance.add(current_path, file=file_path, line=line)

        return result

    def _walk_dict_value(
        self,
        value: dict[str, Any],
        current_dir: Path,
        config_path: str,
        file_path: str,
    ) -> dict[str, Any]:
        """Walk a dict value, handling _ref_ or _instance_ if present.

        :param value: The dict value to process.
        :param current_dir: Directory of the current file.
        :param config_path: Current path in the config tree.
        :param file_path: Path to the current file.
        :return: Resolved dict value (for _instance_, returns marker dict).
        """
        has_ref = _REF_KEY in value
        has_instance = _INSTANCE_KEY in value

        # Check for conflict
        if has_ref and has_instance:
            raise RefInstanceConflictError(config_path)

        if has_ref:
            return self._resolve_ref(value, current_dir, config_path, file_path)
        elif has_instance:
            # Collect _instance_ reference for later resolution
            return self._collect_instance_marker(value, config_path, file_path)
        else:
            # No _ref_ or _instance_, just recursively walk
            return self._walk_dict(value, current_dir, config_path, file_path)

    def _collect_instance_marker(
        self,
        value: dict[str, Any],
        config_path: str,
        file_path: str,
    ) -> dict[str, Any]:
        """Collect an _instance_ marker for later resolution.

        :param value: Dict containing _instance_ key.
        :param config_path: Current path in the config tree.
        :param file_path: Path to the current file.
        :return: A marker dict with the _instance_ key preserved.
        """
        instance_path = value[_INSTANCE_KEY]

        # Validate _instance_ path type
        if instance_path is not None and not isinstance(instance_path, str):
            raise InstanceResolutionError(
                str(instance_path),
                f"_instance_ must be a string or null, got {type(instance_path).__name__}",
                config_path,
            )

        # Get line number for provenance
        line = self._get_line_number(value, _INSTANCE_KEY)

        # Store the marker for later resolution
        self._instances[config_path] = InstanceMarker(
            config_path=config_path,
            instance_path=instance_path,
            file_path=file_path,
            line=line or 0,
        )

        # Return the dict with _instance_ preserved - it will be resolved later
        return {_INSTANCE_KEY: instance_path}

    def _resolve_ref(
        self,
        value: dict[str, Any],
        current_dir: Path,
        config_path: str,
        file_path: str,
    ) -> dict[str, Any]:
        """Resolve a _ref_ reference.

        :param value: Dict containing _ref_ and optional overrides.
        :param current_dir: Directory of the current file.
        :param config_path: Current path in the config tree.
        :param file_path: Path to the current file.
        :return: Merged config from referenced file with overrides.
        """
        ref_path = value[_REF_KEY]

        if not isinstance(ref_path, str):
            raise RefResolutionError(
                str(ref_path),
                f"_ref_ must be a string, got {type(ref_path).__name__}",
                config_path,
            )

        # Resolve the file path
        resolved_path = self._resolve_file_path(ref_path, current_dir, config_path)

        # Load and walk the referenced file
        try:
            referenced_config = self._load_and_walk(resolved_path, config_path)
        except ConfigFileError as e:
            raise RefResolutionError(ref_path, str(e.reason), config_path) from e

        # Check for _ref_ at root of referenced file
        if _REF_KEY in referenced_config:
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
            )

        # Track provenance for overrides
        self._handle_override_provenance(value, override_keys, config_path, file_path)

        # Walk any refs in the overrides themselves
        if overrides:
            # Skip provenance recording for scalar overrides (already recorded with override info)
            scalar_override_keys = {
                k for k in override_keys if not isinstance(value[k], (dict, list))
            }
            overrides = self._walk_dict(
                value,
                current_dir,
                config_path,
                file_path,
                skip_keys={_REF_KEY},
                skip_provenance_for=scalar_override_keys,
            )

        # Deep merge: referenced config as base, overrides on top
        if overrides:
            return deep_merge(referenced_config, overrides, config_path)
        else:
            return referenced_config

    def _handle_override_provenance(
        self,
        value: dict[str, Any],
        override_keys: list[str],
        config_path: str,
        file_path: str,
    ) -> None:
        """Track provenance for override keys with override information.

        :param value: The original dict with _ref_ and overrides.
        :param override_keys: List of keys that are overrides.
        :param config_path: Current path in the config tree.
        :param file_path: Path to the current file.
        """
        for key in override_keys:
            override_path = f"{config_path}.{key}" if config_path else key
            line = self._get_line_number(value, key)
            if line is not None:
                # Check if this is overriding something from the referenced file
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

    def _resolve_file_path(
        self,
        ref_path: str,
        current_dir: Path,
        config_path: str,
    ) -> Path:
        """Resolve a _ref_ file path to an absolute path.

        Path resolution rules:
        - `/path/file.yaml` - Absolute from config root
        - `./file.yaml` - Relative to current file's directory
        - `../file.yaml` - Relative to current file's directory
        - `file.yaml` - Relative to current file's directory

        :param ref_path: The _ref_ path string.
        :param current_dir: Directory of the current file.
        :param config_path: Current path in config (for error messages).
        :return: Resolved absolute path.
        """
        if ref_path.startswith("/"):
            # Absolute from config root
            if self._config_root is None:
                raise RefResolutionError(
                    ref_path,
                    "cannot use absolute path without config root",
                    config_path,
                )
            resolved = self._config_root / ref_path[1:]
        else:
            # Relative to current file's directory
            resolved = current_dir / ref_path

        resolved = resolved.resolve()

        if not resolved.exists():
            raise RefResolutionError(
                ref_path,
                "file not found",
                config_path,
            )

        return resolved

    def _walk_list(
        self,
        items: list[Any],
        current_dir: Path,
        config_path: str,
        file_path: str,
    ) -> list[Any]:
        """Walk _ref_ references within a list.

        :param items: The list to process.
        :param current_dir: Directory of the current file.
        :param config_path: Current path in the config tree.
        :param file_path: Path to the current file.
        :return: List with all _ref_ references resolved.
        """
        result = []
        for i, item in enumerate(items):
            item_path = f"{config_path}[{i}]"
            if isinstance(item, dict):
                resolved_item = self._walk_dict_value(
                    item, current_dir, item_path, file_path
                )
                result.append(resolved_item)
            elif isinstance(item, list):
                result.append(
                    self._walk_list(item, current_dir, item_path, file_path)
                )
            else:
                result.append(item)
        return result

    def _get_line_number(
        self,
        config: CommentedMap | dict[str, Any],
        key: str,
    ) -> int | None:
        """Extract line number from CommentedMap.

        :param config: The config dictionary (may be CommentedMap).
        :param key: The key to get line number for.
        :return: Line number (1-indexed) or None if not available.
        """
        if isinstance(config, CommentedMap) and hasattr(config, "lc"):
            try:
                line, _ = config.lc.key(key)
                return line + 1  # Convert from 0-indexed to 1-indexed
            except (KeyError, TypeError):
                pass
        return None
