"""Configuration file loader registry.

This module provides a registry of config file loaders and convenience
functions for loading config files with automatic format detection.

Thread-safe: All loader registry operations are protected by an internal lock.
"""

import threading
from pathlib import Path
from typing import Any

from rconfig._internal.path_utils import StrOrPath, ensure_path
from rconfig.errors import ConfigFileError
from rconfig.loaders.base import ConfigFileLoader
from rconfig.loaders.position_map import Position, PositionMap
from rconfig.loaders.yaml_loader import YamlConfigLoader
from rconfig.loaders.json_loader import JsonConfigLoader
from rconfig.loaders.toml_loader import TomlConfigLoader

# Registry mapping extension -> loader instance (protected by _loaders_lock)
_extension_to_loader: dict[str, ConfigFileLoader] = {}
_loaders_lock = threading.RLock()


def register_loader(loader: ConfigFileLoader, *extensions: str) -> None:
    """Register a config file loader for specific extensions.

    Thread-safe: protected by internal lock.
    If an extension is already registered, it is silently replaced.
    Extensions are matched case-insensitively.

    :param loader: A ConfigFileLoader instance to register.
    :param extensions: Extensions to register (e.g., ".yaml", ".yml").

    Example::

        class IniConfigLoader(ConfigFileLoader):
            def load(self, path: Path) -> dict[str, Any]:
                import configparser
                parser = configparser.ConfigParser()
                parser.read(path)
                return {s: dict(parser[s]) for s in parser.sections()}

            def load_with_positions(self, path: Path) -> PositionMap:
                return PositionMap(self.load(path))

        register_loader(IniConfigLoader(), ".ini")
    """
    with _loaders_lock:
        for ext in extensions:
            _extension_to_loader[ext.lower()] = loader


def unregister_loader(extension: str) -> None:
    """Unregister a config file loader by extension.

    Thread-safe: protected by internal lock.

    :param extension: The extension to unregister (e.g., ".yaml").
    :raises KeyError: If the extension is not registered.
    """
    with _loaders_lock:
        ext_lower = extension.lower()
        if ext_lower not in _extension_to_loader:
            raise KeyError(f"No loader registered for extension '{extension}'")
        del _extension_to_loader[ext_lower]


def get_loader(path: StrOrPath) -> ConfigFileLoader:
    """Get the appropriate loader for a config file.

    Thread-safe: takes a snapshot of registry before lookup.
    Extensions are matched case-insensitively.

    :param path: Path to the config file. Accepts str, Path, or any os.PathLike.
    :return: A ConfigFileLoader that can handle the file.
    :raises ConfigFileError: If no loader supports the file format.
    """
    path = ensure_path(path)
    ext = path.suffix.lower()

    with _loaders_lock:
        loader = _extension_to_loader.get(ext)
        if loader is not None:
            return loader
        # Take snapshot for error message
        supported = frozenset(_extension_to_loader.keys())

    # Build helpful error message
    supported_str = ", ".join(sorted(supported)) if supported else "none"

    # Check for typos (simple Levenshtein-like suggestion)
    suggestion = _suggest_extension(ext, supported)
    hint = "To support this format, register a custom loader using register_loader()."
    if suggestion:
        raise ConfigFileError(
            path,
            f"unsupported file format '{path.suffix}'. "
            f"Did you mean '{suggestion}'? Supported formats: {supported_str}",
            hint=hint,
        )

    raise ConfigFileError(
        path,
        f"unsupported file format '{path.suffix}'. Supported formats: {supported_str}",
        hint=hint,
    )


def _suggest_extension(ext: str, supported: frozenset[str]) -> str | None:
    """Suggest a similar extension for typos.

    :param ext: The extension that was not found.
    :param supported: Set of supported extensions.
    :return: A suggested extension or None.
    """
    if not supported:
        return None

    # Simple character-based similarity check
    for candidate in supported:
        # Check if extensions differ by only 1-2 characters
        if len(ext) == len(candidate):
            diff = sum(1 for a, b in zip(ext, candidate) if a != b)
            if diff <= 2:
                return candidate
        # Check for transposition (e.g., .ymal vs .yaml)
        if len(ext) == len(candidate) and len(ext) >= 3:
            for i in range(len(ext) - 1):
                swapped = ext[:i] + ext[i + 1] + ext[i] + ext[i + 2 :]
                if swapped == candidate:
                    return candidate

    return None


def supported_loader_extensions() -> frozenset[str]:
    """Return all supported loader extensions.

    Thread-safe: takes a snapshot of registry.

    :return: Frozenset of supported extensions (lowercase).
    """
    with _loaders_lock:
        return frozenset(_extension_to_loader.keys())


def load_config(path: StrOrPath) -> dict[str, Any]:
    """Load a config file with automatic format detection.

    Finds the appropriate loader based on file extension and loads the file.

    :param path: Path to the config file. Accepts str, Path, or any os.PathLike.
    :return: Parsed config as a dictionary.
    :raises ConfigFileError: If format is unsupported or file cannot be loaded.

    Example::

        config = load_config(Path("config.yaml"))
        print(config["_target_"])
    """
    path = ensure_path(path)
    loader = get_loader(path)
    return loader.load(path)


# Default registrations at module load
register_loader(YamlConfigLoader(), ".yaml", ".yml")
register_loader(JsonConfigLoader(), ".json")
register_loader(TomlConfigLoader(), ".toml")


__all__ = [
    "ConfigFileLoader",
    "YamlConfigLoader",
    "JsonConfigLoader",
    "TomlConfigLoader",
    "Position",
    "PositionMap",
    "register_loader",
    "unregister_loader",
    "get_loader",
    "supported_loader_extensions",
    "load_config",
]
