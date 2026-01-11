"""YAML configuration file loader.

This module provides YAML file loading support using ruamel.yaml.
"""

from pathlib import Path
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap
from ruamel.yaml.error import YAMLError

from rconfig.errors import ConfigFileError
from rconfig.loaders.base import ConfigFileLoader
from rconfig.loaders.position_map import PositionMap


class YamlConfigLoader(ConfigFileLoader):
    """YAML config file loader using ruamel.yaml.

    Supports files with ``.yaml`` and ``.yml`` extensions.
    Register with: ``register_loader(YamlConfigLoader(), ".yaml", ".yml")``
    """

    def __init__(self) -> None:
        """Initialize the YAML loader."""
        self._yaml = YAML()
        self._yaml.preserve_quotes = True

    def load(self, path: Path) -> dict[str, Any]:
        """Load a YAML config file.

        :param path: Path to the YAML file.
        :return: Parsed YAML content as a dictionary.
        :raises ConfigFileError: If file not found or contains invalid YAML.
        """
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = self._yaml.load(f)
        except FileNotFoundError:
            raise ConfigFileError(
                path,
                "file not found",
                hint="Check that the file path is correct and the file exists.",
            )
        except PermissionError:
            raise ConfigFileError(
                path,
                "permission denied",
                hint="Check file permissions or run with appropriate access rights.",
            )
        except YAMLError as e:
            raise ConfigFileError(
                path,
                f"invalid YAML syntax: {e}",
                hint="Check the file for syntax errors at the indicated location.",
            )
        except Exception as e:
            raise ConfigFileError(path, str(e))

        if content is None:
            return {}

        if not isinstance(content, dict):
            raise ConfigFileError(
                path,
                f"expected a mapping at root level, got {type(content).__name__}",
                hint="Ensure the root of the file is a YAML mapping (key: value pairs).",
            )

        return dict(content)

    def load_with_positions(self, path: Path) -> PositionMap:
        """Load a YAML config file preserving line position information.

        This method returns a PositionMap which includes line and column
        information for each key.

        :param path: Path to the YAML file.
        :return: PositionMap with position information.
        :raises ConfigFileError: If file not found or contains invalid YAML.

        Example::

            config = loader.load_with_positions(Path("config.yaml"))
            pos = config.get_position("_target_")  # Position(line=1, column=1)
        """
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = self._yaml.load(f)
        except FileNotFoundError:
            raise ConfigFileError(
                path,
                "file not found",
                hint="Check that the file path is correct and the file exists.",
            )
        except PermissionError:
            raise ConfigFileError(
                path,
                "permission denied",
                hint="Check file permissions or run with appropriate access rights.",
            )
        except YAMLError as e:
            raise ConfigFileError(
                path,
                f"invalid YAML syntax: {e}",
                hint="Check the file for syntax errors at the indicated location.",
            )
        except Exception as e:
            raise ConfigFileError(path, str(e))

        if content is None:
            return PositionMap()

        if not isinstance(content, dict):
            raise ConfigFileError(
                path,
                f"expected a mapping at root level, got {type(content).__name__}",
                hint="Ensure the root of the file is a YAML mapping (key: value pairs).",
            )

        return self._commented_map_to_position_map(content)

    def _commented_map_to_position_map(
        self,
        commented_map: CommentedMap,
    ) -> PositionMap:
        """Convert CommentedMap to PositionMap with positions.

        :param commented_map: The ruamel.yaml CommentedMap.
        :return: PositionMap with data and positions.
        """
        result = PositionMap(dict(commented_map))

        for key in commented_map:
            # Extract position from CommentedMap's lc attribute
            if hasattr(commented_map, "lc"):
                try:
                    line, col = commented_map.lc.key(key)
                    # Convert from 0-indexed to 1-indexed
                    result.set_position(key, line + 1, col + 1)
                except (KeyError, TypeError):
                    pass

            # Recursively process nested dicts
            value = commented_map[key]
            if isinstance(value, CommentedMap):
                nested = self._commented_map_to_position_map(value)
                result[key] = nested

        return result
