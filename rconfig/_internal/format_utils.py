"""Shared formatting utilities for provenance and diff layouts.

This module provides common formatting functions used across
multiple layout implementations to eliminate code duplication.
"""

from __future__ import annotations

from typing import Any


def format_value(value: Any, max_length: int = 50) -> str:
    """Format a value for display.

    Handles None, bool, str, and collection types with
    appropriate formatting and truncation.

    :param value: The value to format.
    :param max_length: Maximum string length before truncation.
    :return: Formatted value string.
    """
    match value:
        case None:
            return "null"
        case bool():
            return "true" if value else "false"
        case str():
            return repr(value)
        case list() | dict():
            s = str(value)
            if len(s) > max_length:
                return s[: max_length - 3] + "..."
            return s
        case _:
            return str(value)


def format_location(file: str | None, line: int | None) -> str:
    """Format file:line location string.

    :param file: The source file name.
    :param line: The line number, or None.
    :return: Formatted location string, or empty string if no file.
    """
    if not file:
        return ""
    if line is not None:
        return f"{file}:{line}"
    return file


def indent(text: str, level: int, indent_size: int = 2) -> str:
    """Add indentation to text.

    :param text: Text to indent.
    :param level: Indentation level.
    :param indent_size: Number of spaces per indentation level.
    :return: Indented text.
    """
    return " " * (level * indent_size) + text


def format_type_hint(type_hint: Any, prefix: str = "Type") -> str:
    """Format a type hint for display.

    :param type_hint: The type hint to format.
    :param prefix: Prefix for the formatted string (e.g., "Type" or "type").
    :return: Formatted type hint string, or empty string if None.
    """
    if type_hint is None:
        return ""
    if hasattr(type_hint, "__name__"):
        return f"{prefix}: {type_hint.__name__}"
    return f"{prefix}: {type_hint}"
