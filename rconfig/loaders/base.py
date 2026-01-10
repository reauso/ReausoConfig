"""Abstract base class for configuration file loaders.

This module defines the interface that all config file loaders must implement,
enabling support for multiple config file formats (YAML, JSON, TOML, etc.).
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from rconfig.loaders.position_map import PositionMap


class ConfigFileLoader(ABC):
    """Abstract base class for config file loaders.

    Subclass this to add support for new config file formats.
    Implementations must handle file reading and parsing, converting
    the file contents to a Python dictionary.

    To register a custom loader, use the register_loader function::

        from rconfig.loaders import register_loader

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

    @abstractmethod
    def load(self, path: Path) -> dict[str, Any]:
        """Load a config file and return its contents as a dictionary.

        :param path: Path to the config file.
        :return: Parsed config as a dictionary.
        :raises ConfigFileError: If the file cannot be read or parsed.
        """

    @abstractmethod
    def load_with_positions(self, path: Path) -> PositionMap:
        """Load a config file preserving line and column position information.

        This method returns a PositionMap which provides position lookup
        for each key via the ``get_position()`` method.

        :param path: Path to the config file.
        :return: PositionMap with position information.
        :raises ConfigFileError: If the file cannot be read or parsed.

        Example::

            config = loader.load_with_positions(Path("config.json"))
            pos = config.get_position("_target_")  # Position(line=1, column=3)
        """
