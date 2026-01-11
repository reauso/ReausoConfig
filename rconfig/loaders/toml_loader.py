"""TOML configuration file loader.

This module provides TOML file loading support using Python's standard library.
Requires Python 3.11+ for tomllib.
"""

import re
import tomllib
from pathlib import Path
from typing import Any

from rconfig.errors import ConfigFileError
from rconfig.loaders.base import ConfigFileLoader
from rconfig.loaders.position_map import Position, PositionMap


class TomlConfigLoader(ConfigFileLoader):
    """TOML config file loader using Python's standard library.

    Supports files with ``.toml`` extension.
    Requires Python 3.11+ for the tomllib module.
    Register with: ``register_loader(TomlConfigLoader(), ".toml")``

    Position Tracking Notes:
        Position tracking uses regex-based extraction to identify key
        positions from the source text. Supports standard tables, arrays
        of tables, dotted keys, quoted keys, and inline tables. For
        duplicate keys, only the first occurrence is tracked. Position
        information is best-effort and intended for error reporting.
    """

    def load(self, path: Path) -> dict[str, Any]:
        """Load a TOML config file.

        :param path: Path to the TOML file.
        :return: Parsed TOML content as a dictionary.
        :raises ConfigFileError: If file not found or contains invalid TOML.
        """
        try:
            with open(path, "r", encoding="utf-8") as f:
                source = f.read()
            content = tomllib.loads(source)
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
        except tomllib.TOMLDecodeError as e:
            raise ConfigFileError(
                path,
                f"invalid TOML syntax: {e}",
                hint="Check the file for syntax errors at the indicated location.",
            )
        except Exception as e:
            raise ConfigFileError(path, str(e))

        return content

    def load_with_positions(self, path: Path) -> PositionMap:
        """Load a TOML config file preserving line position information.

        :param path: Path to the TOML file.
        :return: PositionMap with position information.
        :raises ConfigFileError: If file not found or contains invalid TOML.

        Example::

            config = loader.load_with_positions(Path("config.toml"))
            pos = config.get_position("model.name")  # Position(line=3, column=1)
        """
        try:
            with open(path, "r", encoding="utf-8") as f:
                source = f.read()
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
        except UnicodeDecodeError as e:
            raise ConfigFileError(
                path,
                f"invalid encoding: {e}",
                hint="Ensure the file is UTF-8 encoded.",
            )
        except Exception as e:
            raise ConfigFileError(path, str(e))

        if not source.strip():
            return PositionMap()

        try:
            content = tomllib.loads(source)
        except tomllib.TOMLDecodeError as e:
            raise ConfigFileError(
                path,
                f"invalid TOML syntax: {e}",
                hint="Check the file for syntax errors at the indicated location.",
            )

        positions = self._extract_positions(source)
        return self._build_position_map(content, positions)

    def _extract_positions(self, source: str) -> dict[str, Position]:
        """Extract key positions (line and column) from TOML source.

        :param source: The TOML source text.
        :return: Dict mapping dotted key paths to Position objects.
        """
        positions: dict[str, Position] = {}

        # Normalize line endings
        source = source.replace("\r\n", "\n").replace("\r", "\n")
        lines = source.split("\n")

        current_table: list[str] = []

        for line_num, line in enumerate(lines, start=1):
            stripped = line.strip()

            # Skip empty lines and comments
            if not stripped or stripped.startswith("#"):
                continue

            # Check for array of tables [[table.path]]
            array_table_match = re.match(r"^\[\[([^\[\]]+)\]\]", stripped)
            if array_table_match:
                table_path = array_table_match.group(1).strip()
                current_table = self._parse_table_path(table_path)
                continue

            # Check for table header [table.path]
            table_match = re.match(r"^\[([^\[\]]+)\]", stripped)
            if table_match:
                table_path = table_match.group(1).strip()
                current_table = self._parse_table_path(table_path)
                continue

            # Check for key = value (must contain = and not be a table header)
            if "=" in stripped:
                # Extract key part (before first =)
                key_part = stripped.split("=", 1)[0].strip()
                value_part = stripped.split("=", 1)[1].strip()

                # Parse the key (may be dotted, may be quoted)
                key_parts = self._parse_key(key_part)
                if key_parts:
                    # Build full path
                    full_path_parts = current_table + key_parts
                    full_path = ".".join(full_path_parts)

                    # Find column position of key in original line
                    column = line.find(key_part) + 1  # 1-indexed

                    if full_path not in positions:
                        positions[full_path] = Position(line_num, column)

                    # Also store the leaf key without table prefix
                    # (for direct lookup in nested PositionMaps)
                    leaf_key = key_parts[-1]
                    if leaf_key not in positions:
                        positions[leaf_key] = Position(line_num, column)

                    # Check for inline table: key = { ... }
                    if value_part.startswith("{"):
                        inline_positions = self._extract_inline_table_keys(
                            value_part, line_num, line, full_path
                        )
                        for k, pos in inline_positions.items():
                            if k not in positions:
                                positions[k] = pos

        return positions

    def _extract_inline_table_keys(
        self,
        inline_str: str,
        line_num: int,
        full_line: str,
        parent_path: str,
    ) -> dict[str, Position]:
        """Extract key positions from an inline table like { x = 1, y = 2 }.

        :param inline_str: The inline table string starting with {.
        :param line_num: The line number (1-indexed).
        :param full_line: The full line text for column calculation.
        :param parent_path: The path of the parent key.
        :return: Dict mapping keys to positions.
        """
        positions: dict[str, Position] = {}

        # Remove outer braces
        inner = inline_str.strip()
        if inner.startswith("{"):
            inner = inner[1:]
        if inner.endswith("}"):
            inner = inner[:-1]

        # Split by comma, handling nested structures
        parts = self._split_inline_table(inner)

        for part in parts:
            part = part.strip()
            if "=" in part:
                key_part = part.split("=", 1)[0].strip()
                key_parts = self._parse_key(key_part)
                if key_parts:
                    leaf_key = key_parts[-1]
                    full_key_path = f"{parent_path}.{leaf_key}"

                    # Find column position in the original line
                    # Search for the key pattern in the line
                    key_idx = full_line.find(key_part)
                    if key_idx != -1:
                        column = key_idx + 1  # 1-indexed

                        if full_key_path not in positions:
                            positions[full_key_path] = Position(line_num, column)
                        if leaf_key not in positions:
                            positions[leaf_key] = Position(line_num, column)

        return positions

    def _split_inline_table(self, inner: str) -> list[str]:
        """Split inline table content by commas, respecting nested structures.

        :param inner: The content inside the braces.
        :return: List of key=value pairs.
        """
        parts: list[str] = []
        current = ""
        depth = 0
        in_quotes = False
        quote_char = ""

        for char in inner:
            if char in ('"', "'") and not in_quotes:
                in_quotes = True
                quote_char = char
                current += char
            elif char == quote_char and in_quotes:
                in_quotes = False
                quote_char = ""
                current += char
            elif char == "{" and not in_quotes:
                depth += 1
                current += char
            elif char == "}" and not in_quotes:
                depth -= 1
                current += char
            elif char == "[" and not in_quotes:
                depth += 1
                current += char
            elif char == "]" and not in_quotes:
                depth -= 1
                current += char
            elif char == "," and depth == 0 and not in_quotes:
                if current.strip():
                    parts.append(current.strip())
                current = ""
            else:
                current += char

        if current.strip():
            parts.append(current.strip())

        return parts

    def _parse_table_path(self, path: str) -> list[str]:
        """Parse a table path like 'model.optimizer' into parts.

        Handles quoted keys in table paths.

        :param path: The table path string.
        :return: List of path parts.
        """
        parts: list[str] = []
        current = ""
        in_quotes = False
        quote_char = ""

        for char in path:
            if char in ('"', "'") and not in_quotes:
                in_quotes = True
                quote_char = char
            elif char == quote_char and in_quotes:
                in_quotes = False
                quote_char = ""
            elif char == "." and not in_quotes:
                if current.strip():
                    parts.append(current.strip().strip("\"'"))
                current = ""
            else:
                current += char

        if current.strip():
            parts.append(current.strip().strip("\"'"))

        return parts

    def _parse_key(self, key_str: str) -> list[str]:
        """Parse a key string that may be dotted or quoted.

        Examples:
            'name' -> ['name']
            'model.name' -> ['model', 'name']
            '"quoted.key"' -> ['quoted.key']

        :param key_str: The key string to parse.
        :return: List of key parts.
        """
        parts: list[str] = []
        current = ""
        in_quotes = False
        quote_char = ""

        for char in key_str:
            if char in ('"', "'") and not in_quotes:
                in_quotes = True
                quote_char = char
            elif char == quote_char and in_quotes:
                in_quotes = False
                quote_char = ""
            elif char == "." and not in_quotes:
                if current.strip():
                    parts.append(current.strip().strip("\"'"))
                current = ""
            else:
                current += char

        if current.strip():
            parts.append(current.strip().strip("\"'"))

        return parts

    def _build_position_map(
        self,
        data: dict[str, Any],
        positions: dict[str, Position],
        prefix: str = "",
    ) -> PositionMap:
        """Build PositionMap from parsed data and extracted positions.

        :param data: The parsed TOML data.
        :param positions: Dict mapping keys to positions.
        :param prefix: Current path prefix for nested keys.
        :return: PositionMap with data and positions.
        """
        result = PositionMap(data)

        for key in data:
            full_path = f"{prefix}.{key}" if prefix else key

            # Try to find position by full path first, then by leaf key
            pos = positions.get(full_path) or positions.get(key)
            if pos:
                result.set_position(key, pos.line, pos.column)

            # Recursively process nested dicts
            value = data[key]
            if isinstance(value, dict):
                nested = self._build_position_map(value, positions, full_path)
                result[key] = nested
            elif isinstance(value, list):
                result[key] = self._process_list(value, positions, full_path)

        return result

    def _process_list(
        self,
        items: list[Any],
        positions: dict[str, Position],
        prefix: str,
    ) -> list[Any]:
        """Process a list, converting nested dicts to PositionMaps.

        :param items: The list to process.
        :param positions: Dict mapping keys to positions.
        :param prefix: Current path prefix.
        :return: Processed list.
        """
        result = []
        for i, item in enumerate(items):
            item_prefix = f"{prefix}[{i}]"
            if isinstance(item, dict):
                result.append(self._build_position_map(item, positions, item_prefix))
            elif isinstance(item, list):
                result.append(self._process_list(item, positions, item_prefix))
            else:
                result.append(item)
        return result
