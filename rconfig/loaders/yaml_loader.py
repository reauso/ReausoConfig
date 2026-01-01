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


class YamlConfigLoader(ConfigFileLoader):
    """YAML config file loader using ruamel.yaml.

    Supports files with ``.yaml`` and ``.yml`` extensions.
    """

    _SUPPORTED_EXTENSIONS = (".yaml", ".yml")

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
            raise ConfigFileError(path, "file not found")
        except PermissionError:
            raise ConfigFileError(path, "permission denied")
        except YAMLError as e:
            raise ConfigFileError(path, f"invalid YAML syntax: {e}")
        except Exception as e:
            raise ConfigFileError(path, str(e))

        if content is None:
            return {}

        if not isinstance(content, dict):
            raise ConfigFileError(
                path,
                f"expected a mapping at root level, got {type(content).__name__}"
            )

        return dict(content)

    def load_with_positions(self, path: Path) -> CommentedMap:
        """Load a YAML config file preserving line position information.

        This method returns the raw ruamel.yaml CommentedMap which includes
        line and column information for each key via the `.lc` attribute.

        :param path: Path to the YAML file.
        :return: CommentedMap with position information.
        :raises ConfigFileError: If file not found or contains invalid YAML.

        Example::

            config = loader.load_with_positions(Path("config.yaml"))
            line, col = config.lc.key("_target_")  # 0-indexed
        """
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = self._yaml.load(f)
        except FileNotFoundError:
            raise ConfigFileError(path, "file not found")
        except PermissionError:
            raise ConfigFileError(path, "permission denied")
        except YAMLError as e:
            raise ConfigFileError(path, f"invalid YAML syntax: {e}")
        except Exception as e:
            raise ConfigFileError(path, str(e))

        if content is None:
            return CommentedMap()

        if not isinstance(content, dict):
            raise ConfigFileError(
                path,
                f"expected a mapping at root level, got {type(content).__name__}"
            )

        return content

    def supports(self, path: Path) -> bool:
        """Check if this loader supports the given file.

        :param path: Path to check.
        :return: True if path has .yaml or .yml extension.
        """
        return path.suffix.lower() in self._SUPPORTED_EXTENSIONS
