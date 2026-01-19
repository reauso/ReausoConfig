"""Exporter registry for config export.

This module provides a registry of config exporters and convenience
functions for exporting config files with automatic format detection.

Thread-safe: All exporter registry operations are protected by an internal lock.
"""

import threading
from pathlib import Path

from rconfig._internal.path_utils import StrOrPath, ensure_path
from rconfig.errors import ConfigFileError
from rconfig.export.base import Exporter
from rconfig.export.yaml_exporter import YamlExporter
from rconfig.export.json_exporter import JsonExporter
from rconfig.export.toml_exporter import TomlExporter

# Registry mapping extension -> exporter instance (protected by _exporters_lock)
_extension_to_exporter: dict[str, Exporter] = {}
_exporters_lock = threading.RLock()


def register_exporter(exporter: Exporter, *extensions: str) -> None:
    """Register a config exporter for specific extensions.

    Thread-safe: protected by internal lock.
    If an extension is already registered, it is silently replaced.
    Extensions are matched case-insensitively.

    :param exporter: An Exporter instance to register.
    :param extensions: Extensions to register (e.g., ".yaml", ".yml").

    Example::

        class XmlExporter(Exporter):
            def export(self, config: dict[str, Any]) -> str:
                # Custom XML serialization
                ...

        register_exporter(XmlExporter(), ".xml")
    """
    with _exporters_lock:
        for ext in extensions:
            _extension_to_exporter[ext.lower()] = exporter


def unregister_exporter(extension: str) -> None:
    """Unregister a config exporter by extension.

    Thread-safe: protected by internal lock.

    :param extension: The extension to unregister (e.g., ".yaml").
    :raises KeyError: If the extension is not registered.
    """
    with _exporters_lock:
        ext_lower = extension.lower()
        if ext_lower not in _extension_to_exporter:
            raise KeyError(f"No exporter registered for extension '{extension}'")
        del _extension_to_exporter[ext_lower]


def get_exporter(path: StrOrPath) -> Exporter:
    """Get the appropriate exporter for a config file.

    Thread-safe: takes a snapshot of registry before lookup.
    Extensions are matched case-insensitively.

    :param path: Path to the config file. Accepts str, Path, or any os.PathLike.
    :return: An Exporter that can handle the file format.
    :raises ConfigFileError: If no exporter supports the file format.
    """
    path = ensure_path(path)
    ext = path.suffix.lower()

    with _exporters_lock:
        exporter = _extension_to_exporter.get(ext)
        if exporter is not None:
            return exporter
        # Take snapshot for error message
        supported = frozenset(_extension_to_exporter.keys())

    # Build helpful error message
    supported_str = ", ".join(sorted(supported)) if supported else "none"

    # Check for typos (simple Levenshtein-like suggestion)
    suggestion = _suggest_extension(ext, supported)
    if suggestion:
        raise ConfigFileError(
            path,
            f"unsupported export format '{path.suffix}'. "
            f"Did you mean '{suggestion}'? Supported formats: {supported_str}",
        )

    raise ConfigFileError(
        path,
        f"unsupported export format '{path.suffix}'. Supported formats: {supported_str}",
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


def supported_exporter_extensions() -> frozenset[str]:
    """Return all supported exporter extensions.

    Thread-safe: takes a snapshot of registry.

    :return: Frozenset of supported extensions (lowercase).
    """
    with _exporters_lock:
        return frozenset(_extension_to_exporter.keys())


# Default registrations at module load
register_exporter(YamlExporter(), ".yaml", ".yml")
register_exporter(JsonExporter(), ".json")
register_exporter(TomlExporter(), ".toml")
