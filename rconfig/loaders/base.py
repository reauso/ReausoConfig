"""Abstract base class for configuration file loaders.

This module defines the interface that all config file loaders must implement,
enabling support for multiple config file formats (YAML, JSON, TOML, etc.).
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class ConfigFileLoader(ABC):
    """Abstract base class for config file loaders.

    Subclass this to add support for new config file formats.
    Implementations must handle file reading and parsing, converting
    the file contents to a Python dictionary.

    Example::

        class JsonConfigLoader(ConfigFileLoader):
            def load(self, path: Path) -> dict[str, Any]:
                import json
                with open(path) as f:
                    return json.load(f)

            def supports(self, path: Path) -> bool:
                return path.suffix.lower() == '.json'
    """

    @abstractmethod
    def load(self, path: Path) -> dict[str, Any]:
        """Load a config file and return its contents as a dictionary.

        :param path: Path to the config file.
        :return: Parsed config as a dictionary.
        :raises ConfigFileError: If the file cannot be read or parsed.
        """

    @abstractmethod
    def supports(self, path: Path) -> bool:
        """Check if this loader supports the given file.

        Typically checks the file extension to determine compatibility.

        :param path: Path to check.
        :return: True if this loader can handle the file.
        """
