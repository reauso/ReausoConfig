"""JSON configuration file loader.

This module provides JSON file loading support using Python's standard library.
"""

import json
import re
from pathlib import Path
from typing import Any

from rconfig.errors import ConfigFileError
from rconfig.loaders.base import ConfigFileLoader
from rconfig.loaders.position_map import Position, PositionMap


class JsonConfigLoader(ConfigFileLoader):
    """JSON config file loader using Python's standard library.

    Supports files with ``.json`` extension.
    Register with: ``register_loader(JsonConfigLoader(), ".json")``

    Position Tracking Notes:
        Position tracking uses a state-machine parser to identify actual
        JSON keys (as opposed to strings that happen to contain ``"key":``
        patterns). For duplicate keys in the source, only the first
        occurrence is tracked. Position information is best-effort and
        intended for error reporting, not for source modification.
    """

    def load(self, path: Path) -> dict[str, Any]:
        """Load a JSON config file.

        :param path: Path to the JSON file.
        :return: Parsed JSON content as a dictionary.
        :raises ConfigFileError: If file not found or contains invalid JSON.
        """
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = json.load(f)
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
        except json.JSONDecodeError as e:
            raise ConfigFileError(
                path,
                f"invalid JSON syntax: {e}",
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
                hint="Ensure the root of the file is a JSON object ({...}).",
            )

        return content

    def load_with_positions(self, path: Path) -> PositionMap:
        """Load a JSON config file preserving line position information.

        :param path: Path to the JSON file.
        :return: PositionMap with position information.
        :raises ConfigFileError: If file not found or contains invalid JSON.

        Example::

            config = loader.load_with_positions(Path("config.json"))
            pos = config.get_position("_target_")  # Position(line=2, column=3)
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
        except Exception as e:
            raise ConfigFileError(path, str(e))

        if not source.strip():
            return PositionMap()

        try:
            content = json.loads(source)
        except json.JSONDecodeError as e:
            raise ConfigFileError(
                path,
                f"invalid JSON syntax: {e}",
                hint="Check the file for syntax errors at the indicated location.",
            )

        if not isinstance(content, dict):
            raise ConfigFileError(
                path,
                f"expected a mapping at root level, got {type(content).__name__}",
                hint="Ensure the root of the file is a JSON object ({...}).",
            )

        positions = self._extract_positions(source)
        return self._build_position_map(content, positions)

    def _extract_positions(self, source: str) -> dict[str, Position]:
        """Extract key positions (line and column) from JSON source.

        Uses a state-machine approach to distinguish between keys and
        string values, avoiding false positives from patterns like
        ``{"data": "contains \\"key\\": pattern"}``.

        :param source: The JSON source text.
        :return: Dict mapping keys to Position objects.
        """
        positions: dict[str, Position] = {}

        # Normalize line endings
        source = source.replace("\r\n", "\n").replace("\r", "\n")

        # Find valid key positions using state machine
        key_positions = self._find_key_positions(source)

        for char_pos, raw_key in key_positions:
            # Properly unescape the key using JSON parser
            try:
                key = json.loads(f'"{raw_key}"')
            except json.JSONDecodeError:
                key = raw_key

            # Calculate line and column (1-indexed)
            line = source[:char_pos].count("\n") + 1
            last_newline = source.rfind("\n", 0, char_pos)
            if last_newline == -1:
                column = char_pos + 1  # First line, no newline before
            else:
                column = char_pos - last_newline

            # Store first occurrence of each key
            if key not in positions:
                positions[key] = Position(line, column)

        return positions

    def _find_key_positions(self, source: str) -> list[tuple[int, str]]:
        """Find positions of JSON keys using state machine parsing.

        This method tracks the JSON structure to distinguish actual keys
        from strings that happen to look like ``"key":`` patterns.

        :param source: The JSON source text.
        :return: List of (char_position, raw_key) tuples.
        """
        results: list[tuple[int, str]] = []
        i = 0
        n = len(source)

        # Stack to track whether we're inside an object (True) or array (False)
        # Only strings followed by : inside objects are keys
        context_stack: list[bool] = []

        while i < n:
            char = source[i]

            # Skip whitespace
            if char in " \t\n\r":
                i += 1
                continue

            # Start of object - push object context
            if char == "{":
                context_stack.append(True)  # True = object context
                i += 1
                continue

            # End of object - pop context
            if char == "}":
                if context_stack:
                    context_stack.pop()
                i += 1
                continue

            # Start of array - push array context
            if char == "[":
                context_stack.append(False)  # False = array context
                i += 1
                continue

            # End of array - pop context
            if char == "]":
                if context_stack:
                    context_stack.pop()
                i += 1
                continue

            # Comma - just skip
            if char == ",":
                i += 1
                continue

            # Colon - just skip (we handle keys when we see strings)
            if char == ":":
                i += 1
                continue

            # String - could be a key (if in object context and followed by :)
            if char == '"':
                string_start = i
                i += 1  # Skip opening quote
                string_content = ""

                # Read string content
                while i < n:
                    c = source[i]
                    if c == "\\":
                        # Escape sequence
                        if i + 1 < n:
                            string_content += c + source[i + 1]
                            i += 2
                        else:
                            i += 1
                    elif c == '"':
                        i += 1  # Skip closing quote
                        break
                    else:
                        string_content += c
                        i += 1

                # Skip whitespace after string
                while i < n and source[i] in " \t\n\r":
                    i += 1

                # If in object context and followed by colon, this is a key
                in_object = context_stack and context_stack[-1]
                if in_object and i < n and source[i] == ":":
                    results.append((string_start, string_content))

                continue

            # Other characters (numbers, true, false, null) - skip
            while i < n and source[i] not in ",}] \t\n\r":
                i += 1

        return results

    def _build_position_map(
        self,
        data: dict[str, Any],
        positions: dict[str, Position],
    ) -> PositionMap:
        """Build PositionMap from parsed data and extracted positions.

        :param data: The parsed JSON data.
        :param positions: Dict mapping keys to positions.
        :return: PositionMap with data and positions.
        """
        result = PositionMap(data)

        for key in data:
            if key in positions:
                pos = positions[key]
                result.set_position(key, pos.line, pos.column)

            # Recursively process nested dicts
            value = data[key]
            if isinstance(value, dict):
                # For nested dicts, we need to find their keys in the source too
                # The positions dict contains all keys found in the source
                nested = self._build_position_map(value, positions)
                result[key] = nested
            elif isinstance(value, list):
                result[key] = self._process_list(value, positions)

        return result

    def _process_list(
        self,
        items: list[Any],
        positions: dict[str, Position],
    ) -> list[Any]:
        """Process a list, converting nested dicts to PositionMaps.

        :param items: The list to process.
        :param positions: Dict mapping keys to positions.
        :return: Processed list.
        """
        result = []
        for item in items:
            if isinstance(item, dict):
                result.append(self._build_position_map(item, positions))
            elif isinstance(item, list):
                result.append(self._process_list(item, positions))
            else:
                result.append(item)
        return result
