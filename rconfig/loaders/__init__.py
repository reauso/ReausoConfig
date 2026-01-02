"""Configuration file loader registry.

This module provides a registry of config file loaders and convenience
functions for loading config files with automatic format detection.

Thread-safe: All loader registry operations are protected by an internal lock.
"""

import threading
from pathlib import Path
from typing import Any

from rconfig.errors import ConfigFileError
from rconfig.loaders.base import ConfigFileLoader
from rconfig.loaders.yaml_loader import YamlConfigLoader

# Registry of available loaders (protected by _loaders_lock)
_loaders: list[ConfigFileLoader] = [YamlConfigLoader()]
_loaders_lock = threading.RLock()


def register_loader(loader: ConfigFileLoader) -> None:
    """Register a custom config file loader.

    Thread-safe: protected by internal lock.
    Registered loaders are checked in order when loading a config file.
    Later registered loaders take priority over earlier ones.

    :param loader: A ConfigFileLoader instance to register.

    Example::

        class TomlConfigLoader(ConfigFileLoader):
            def load(self, path: Path) -> dict[str, Any]:
                import tomllib
                with open(path, 'rb') as f:
                    return tomllib.load(f)

            def supports(self, path: Path) -> bool:
                return path.suffix == '.toml'

        register_loader(TomlConfigLoader())
    """
    with _loaders_lock:
        _loaders.insert(0, loader)


def unregister_loader(loader: ConfigFileLoader) -> None:
    """Unregister a previously registered config file loader.

    Thread-safe: protected by internal lock.

    :param loader: The loader instance to remove.
    :raises ValueError: If the loader is not registered.
    """
    with _loaders_lock:
        _loaders.remove(loader)


def get_loader(path: Path) -> ConfigFileLoader:
    """Get the appropriate loader for a config file.

    Thread-safe: takes a snapshot of loaders before iteration.
    Checks registered loaders in order and returns the first one
    that supports the given file path.

    :param path: Path to the config file.
    :return: A ConfigFileLoader that can handle the file.
    :raises ConfigFileError: If no loader supports the file format.
    """
    # Take snapshot under lock, then iterate outside lock
    with _loaders_lock:
        loaders_snapshot = list(_loaders)

    for loader in loaders_snapshot:
        if loader.supports(path):
            return loader

    # Build error message (using snapshot)
    supported = set()
    for loader in loaders_snapshot:
        if hasattr(loader, "_SUPPORTED_EXTENSIONS"):
            supported.update(loader._SUPPORTED_EXTENSIONS)

    supported_str = ", ".join(sorted(supported)) if supported else "none"
    raise ConfigFileError(
        path,
        f"unsupported file format '{path.suffix}'. Supported formats: {supported_str}",
    )


def load_config(path: Path) -> dict[str, Any]:
    """Load a config file with automatic format detection.

    Finds the appropriate loader based on file extension and loads the file.

    :param path: Path to the config file.
    :return: Parsed config as a dictionary.
    :raises ConfigFileError: If format is unsupported or file cannot be loaded.

    Example::

        config = load_config(Path("config.yaml"))
        print(config["_target_"])
    """
    loader = get_loader(path)
    return loader.load(path)


__all__ = [
    "ConfigFileLoader",
    "YamlConfigLoader",
    "register_loader",
    "unregister_loader",
    "get_loader",
    "load_config",
]
