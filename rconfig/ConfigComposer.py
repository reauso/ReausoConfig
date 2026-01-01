"""Config composer for resolving _ref_ references and composing configs.

This module provides functionality for loading config files that reference
other config files via `_ref_`, merging them together with deep merge semantics.
"""

from functools import lru_cache
from pathlib import Path
from typing import Any

from ruamel.yaml.comments import CommentedMap

from .ConfigMerger import deep_merge
from .errors import (
    CircularRefError,
    ConfigFileError,
    RefAtRootError,
    RefInstanceConflictError,
    RefResolutionError,
)
from .loaders import load_config as _load_yaml
from .loaders.yaml_loader import YamlConfigLoader
from .Provenance import Provenance


# Special keys
_REF_KEY = "_ref_"
_INSTANCE_KEY = "_instance_"
_TARGET_KEY = "_target_"

# Shared yaml loader instance for position-aware loading
_yaml_loader = YamlConfigLoader()

# Module-level cache size (0 = unlimited)
_cache_size: int = 0


def set_cache_size(size: int) -> None:
    """Set the LRU cache size for loaded config files.

    :param size: Maximum number of files to cache. 0 means unlimited.
    """
    global _cache_size
    _cache_size = size
    # Clear and recreate cache with new size
    _load_file_cached.cache_clear()


@lru_cache(maxsize=None)
def _load_file_cached(path: str) -> dict[str, Any]:
    """Load a config file with caching.

    :param path: Absolute path to the config file as string.
    :return: Parsed config dictionary.
    :raises ConfigFileError: If file cannot be loaded.
    """
    return _load_yaml(Path(path))


def clear_cache() -> None:
    """Clear the file loading cache."""
    _load_file_cached.cache_clear()


class ConfigComposer:
    """Composes config files by resolving _ref_ references.

    The composer loads a config file and recursively resolves any `_ref_`
    references found in the config tree. Referenced files are deep merged
    with any sibling override keys.

    Example::

        composer = ConfigComposer(Path("/project/configs"))
        config = composer.compose(Path("/project/configs/app.yaml"))
    """

    def __init__(self, config_root: Path | None = None) -> None:
        """Initialize the composer.

        :param config_root: Root directory for absolute path resolution.
                           If None, derived from the composed file's parent.
        """
        self._config_root = config_root
        self._loading_stack: list[str] = []
        self._provenance: Provenance | None = None
        self._track_provenance: bool = False

    def compose(self, path: Path) -> dict[str, Any]:
        """Compose a config file by resolving all _ref_ references.

        :param path: Path to the entry-point config file.
        :return: Fully composed config dictionary.
        :raises ConfigFileError: If a file cannot be loaded.
        :raises CircularRefError: If circular references are detected.
        :raises RefAtRootError: If _ref_ is used at root level.
        :raises RefResolutionError: If a _ref_ cannot be resolved.
        """
        path = path.resolve()

        # Set config root to entry file's parent if not specified
        if self._config_root is None:
            self._config_root = path.parent

        # Clear loading stack for fresh composition
        self._loading_stack = []
        self._provenance = None
        self._track_provenance = False

        config = self._load_and_resolve(path)

        # Check for _ref_ at root level in entry file
        if _REF_KEY in config:
            raise RefAtRootError(str(path))

        return config

    def compose_with_provenance(self, path: Path) -> Provenance:
        """Compose a config file and track the origin of each value.

        :param path: Path to the entry-point config file.
        :return: Provenance object with origin information.
        :raises ConfigFileError: If a file cannot be loaded.
        :raises CircularRefError: If circular references are detected.
        :raises RefAtRootError: If _ref_ is used at root level.
        :raises RefResolutionError: If a _ref_ cannot be resolved.

        Example::

            prov = composer.compose_with_provenance(Path("trainer.yaml"))
            print(prov)  # Shows config with file:line annotations
            entry = prov.get("model.layers")  # Get specific origin info
        """
        path = path.resolve()

        # Set config root to entry file's parent if not specified
        if self._config_root is None:
            self._config_root = path.parent

        # Clear loading stack and initialize provenance tracking
        self._loading_stack = []
        self._provenance = Provenance()
        self._track_provenance = True

        config = self._load_and_resolve_with_positions(path)

        # Check for _ref_ at root level in entry file
        if _REF_KEY in config:
            raise RefAtRootError(str(path))

        self._provenance.set_config(config)
        return self._provenance

    def _load_and_resolve_with_positions(
        self, path: Path, parent_config_path: str = ""
    ) -> dict[str, Any]:
        """Load a config file with position info and resolve refs.

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
            config = _yaml_loader.load_with_positions(path)
            resolved = self._resolve_refs_with_positions(
                config, path.parent, parent_config_path, path_str
            )
            return resolved
        finally:
            self._loading_stack.pop()

    def _load_and_resolve(self, path: Path) -> dict[str, Any]:
        """Load a config file and resolve its _ref_ references.

        :param path: Absolute path to the config file.
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
            resolved = self._resolve_refs(config, path.parent, "")
            return resolved
        finally:
            self._loading_stack.pop()

    def _resolve_refs(
        self,
        config: dict[str, Any],
        current_dir: Path,
        config_path: str,
    ) -> dict[str, Any]:
        """Recursively resolve _ref_ references in a config.

        :param config: The config dictionary to process.
        :param current_dir: Directory of the current file (for relative paths).
        :param config_path: Current path in the config tree (for error messages).
        :return: Config with all _ref_ references resolved.
        """
        result = {}

        for key, value in config.items():
            current_path = f"{config_path}.{key}" if config_path else key

            if isinstance(value, dict):
                resolved_value = self._resolve_dict_value(
                    value, current_dir, current_path
                )
                result[key] = resolved_value
            elif isinstance(value, list):
                result[key] = self._resolve_list_value(value, current_dir, current_path)
            else:
                result[key] = value

        return result

    def _resolve_dict_value(
        self,
        value: dict[str, Any],
        current_dir: Path,
        config_path: str,
    ) -> dict[str, Any]:
        """Resolve a dict value, handling _ref_ if present.

        :param value: The dict value to process.
        :param current_dir: Directory of the current file.
        :param config_path: Current path in the config tree.
        :return: Resolved dict value.
        """
        has_ref = _REF_KEY in value
        has_instance = _INSTANCE_KEY in value

        # Check for conflict
        if has_ref and has_instance:
            raise RefInstanceConflictError(config_path)

        if has_ref:
            return self._resolve_ref(value, current_dir, config_path)
        else:
            # No _ref_, just recursively resolve any nested refs
            return self._resolve_refs(value, current_dir, config_path)

    def _resolve_ref(
        self,
        value: dict[str, Any],
        current_dir: Path,
        config_path: str,
    ) -> dict[str, Any]:
        """Resolve a _ref_ reference.

        :param value: Dict containing _ref_ and optional overrides.
        :param current_dir: Directory of the current file.
        :param config_path: Current path in the config tree.
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

        # Load and resolve the referenced file
        try:
            referenced_config = self._load_and_resolve(resolved_path)
        except ConfigFileError as e:
            raise RefResolutionError(ref_path, str(e.reason), config_path) from e

        # Check for _ref_ at root of referenced file
        if _REF_KEY in referenced_config:
            raise RefAtRootError(str(resolved_path))

        # Get overrides (all keys except _ref_)
        overrides = {k: v for k, v in value.items() if k != _REF_KEY}

        # Check for overriding _target_ to null
        if overrides.get(_TARGET_KEY) is None and _TARGET_KEY in overrides:
            raise RefResolutionError(
                ref_path,
                "cannot override _target_ to null",
                config_path,
            )

        # Resolve any refs in the overrides themselves
        if overrides:
            overrides = self._resolve_refs(overrides, current_dir, config_path)

        # Deep merge: referenced config as base, overrides on top
        if overrides:
            return deep_merge(referenced_config, overrides, config_path)
        else:
            return referenced_config

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

    def _resolve_list_value(
        self,
        items: list[Any],
        current_dir: Path,
        config_path: str,
    ) -> list[Any]:
        """Resolve _ref_ references within a list.

        :param items: The list to process.
        :param current_dir: Directory of the current file.
        :param config_path: Current path in the config tree.
        :return: List with all _ref_ references resolved.
        """
        result = []
        for i, item in enumerate(items):
            item_path = f"{config_path}[{i}]"
            if isinstance(item, dict):
                resolved_item = self._resolve_dict_value(item, current_dir, item_path)
                result.append(resolved_item)
            elif isinstance(item, list):
                result.append(self._resolve_list_value(item, current_dir, item_path))
            else:
                result.append(item)
        return result


    def _resolve_refs_with_positions(
        self,
        config: CommentedMap | dict[str, Any],
        current_dir: Path,
        config_path: str,
        file_path: str,
        skip_keys: set[str] | None = None,
        skip_provenance_for: set[str] | None = None,
    ) -> dict[str, Any]:
        """Recursively resolve _ref_ references while tracking provenance.

        :param config: The config dictionary to process.
        :param current_dir: Directory of the current file (for relative paths).
        :param config_path: Current path in the config tree (for provenance).
        :param file_path: Path to the current file.
        :param skip_keys: Keys to skip (e.g., _ref_ when processing overrides).
        :param skip_provenance_for: Keys to skip provenance recording for
                                    (used when provenance was already recorded with override info).
        :return: Config with all _ref_ references resolved.
        """
        result = {}
        skip_keys = skip_keys or set()
        skip_provenance_for = skip_provenance_for or set()

        for key, value in config.items():
            if key in skip_keys:
                continue

            current_path = f"{config_path}.{key}" if config_path else key

            # Get line number from CommentedMap if available
            line = self._get_line_number(config, key)
            should_record_provenance = key not in skip_provenance_for

            if isinstance(value, dict):
                resolved_value = self._resolve_dict_value_with_positions(
                    value, current_dir, current_path, file_path
                )
                result[key] = resolved_value
            elif isinstance(value, list):
                result[key] = self._resolve_list_value_with_positions(
                    value, current_dir, current_path, file_path
                )
                # Record provenance for the list key itself
                if self._provenance is not None and line is not None and should_record_provenance:
                    self._provenance.add(current_path, file=file_path, line=line)
            else:
                result[key] = value
                # Record provenance for scalar values
                if self._provenance is not None and line is not None and should_record_provenance:
                    self._provenance.add(current_path, file=file_path, line=line)

        return result

    def _resolve_dict_value_with_positions(
        self,
        value: CommentedMap | dict[str, Any],
        current_dir: Path,
        config_path: str,
        file_path: str,
    ) -> dict[str, Any]:
        """Resolve a dict value with provenance tracking.

        :param value: The dict value to process.
        :param current_dir: Directory of the current file.
        :param config_path: Current path in the config tree.
        :param file_path: Path to the current file.
        :return: Resolved dict value.
        """
        has_ref = _REF_KEY in value
        has_instance = _INSTANCE_KEY in value

        # Check for conflict
        if has_ref and has_instance:
            raise RefInstanceConflictError(config_path)

        if has_ref:
            return self._resolve_ref_with_positions(
                value, current_dir, config_path, file_path
            )
        else:
            # No _ref_, just recursively resolve any nested refs
            return self._resolve_refs_with_positions(
                value, current_dir, config_path, file_path
            )

    def _resolve_ref_with_positions(
        self,
        value: CommentedMap | dict[str, Any],
        current_dir: Path,
        config_path: str,
        file_path: str,
    ) -> dict[str, Any]:
        """Resolve a _ref_ reference with provenance tracking.

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

        # Load and resolve the referenced file with positions
        # Pass config_path as parent so provenance paths are correctly prefixed
        try:
            referenced_config = self._load_and_resolve_with_positions(
                resolved_path, config_path
            )
        except ConfigFileError as e:
            raise RefResolutionError(ref_path, str(e.reason), config_path) from e

        # Check for _ref_ at root of referenced file
        if _REF_KEY in referenced_config:
            raise RefAtRootError(str(resolved_path))

        # Get overrides (all keys except _ref_)
        # Keep the original value for line number extraction
        override_keys = [k for k in value.keys() if k != _REF_KEY]
        overrides = {k: value[k] for k in override_keys}

        # Check for overriding _target_ to null
        if overrides.get(_TARGET_KEY) is None and _TARGET_KEY in overrides:
            raise RefResolutionError(
                ref_path,
                "cannot override _target_ to null",
                config_path,
            )

        # Track provenance for override keys before resolving
        # (This captures line numbers from the override location)
        if overrides and self._provenance is not None:
            for key in override_keys:
                override_path = f"{config_path}.{key}" if config_path else key
                line = self._get_line_number(value, key)
                if line is not None:
                    # Check if this is overriding something from the referenced file
                    base_entry = self._provenance.get(override_path)
                    overrode = None
                    if base_entry is not None:
                        overrode = f"{base_entry.file}:{base_entry.line}"
                    self._provenance.add(
                        override_path, file=file_path, line=line, overrode=overrode
                    )

        # Resolve any refs in the overrides themselves
        if overrides:
            # Skip provenance recording for scalar overrides (already recorded above with override info)
            scalar_override_keys = {k for k in override_keys if not isinstance(value[k], (dict, list))}
            overrides = self._resolve_refs_with_positions(
                value, current_dir, config_path, file_path,
                skip_keys={_REF_KEY},
                skip_provenance_for=scalar_override_keys,
            )

        # Deep merge: referenced config as base, overrides on top
        if overrides:
            return deep_merge(referenced_config, overrides, config_path)
        else:
            return referenced_config

    def _resolve_list_value_with_positions(
        self,
        items: list[Any],
        current_dir: Path,
        config_path: str,
        file_path: str,
    ) -> list[Any]:
        """Resolve _ref_ references within a list with provenance tracking.

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
                resolved_item = self._resolve_dict_value_with_positions(
                    item, current_dir, item_path, file_path
                )
                result.append(resolved_item)
            elif isinstance(item, list):
                result.append(
                    self._resolve_list_value_with_positions(
                        item, current_dir, item_path, file_path
                    )
                )
            else:
                result.append(item)
                # Track provenance for list items (no line info for individual items)
        return result

    def _get_line_number(
        self, config: CommentedMap | dict[str, Any], key: str
    ) -> int | None:
        """Get the line number for a key in a config.

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

def compose(path: Path) -> dict[str, Any]:
    """Compose a config file by resolving all _ref_ references.

    This is a convenience function that creates a ConfigComposer and
    composes the given file.

    :param path: Path to the entry-point config file.
    :return: Fully composed config dictionary.
    """
    composer = ConfigComposer()
    return composer.compose(path)


def compose_with_provenance(path: Path) -> Provenance:
    """Compose a config file and track the origin of each value.

    This is a convenience function that creates a ConfigComposer and
    composes the given file with provenance tracking.

    :param path: Path to the entry-point config file.
    :return: Provenance object with origin information.
    """
    composer = ConfigComposer()
    return composer.compose_with_provenance(path)
