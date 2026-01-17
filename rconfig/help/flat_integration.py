"""Flat help integration for CLI help generation.

This module provides FlatHelpIntegration which displays config entries
as flat paths in a tabular format.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, TextIO

from .integration import HelpIntegration
from .multirun_help import MULTIRUN_HELP

if TYPE_CHECKING:
    from rconfig.provenance import Provenance


class FlatHelpIntegration(HelpIntegration):
    """Displays entries as flat paths. Default integration.

    Output::

        Configuration options for config.yaml
        =====================================

        model.lr              float       0.001      Learning rate
        model.hidden_size     int         256        Hidden layer size
        data.path             str         (required) Path to data
    """

    def __init__(self, *, output: TextIO | None = None) -> None:
        """Initialize the flat help integration.

        :param output: Output stream to write to. Defaults to sys.stdout.
        """
        super().__init__(consume_help_flag=True)
        self._output = output if output is not None else sys.stdout

    def integrate(self, provenance: Provenance, config_path: str) -> None:
        """Display help as flat aligned table, then exit.

        :param provenance: Provenance data with type hints and descriptions.
        :param config_path: Path to the config file.
        """
        lines = self._formatted_help(provenance, config_path)
        self._output.write("\n".join(lines))
        self._output.write("\n")
        sys.exit(0)

    def _formatted_help(
        self, provenance: Provenance, config_path: str
    ) -> list[str]:
        """Format provenance as help output.

        :param provenance: Provenance data.
        :param config_path: Path to the config file.
        :return: List of formatted lines.
        """
        lines: list[str] = []

        # Header
        title = f"Configuration options for {config_path}"
        lines.append(title)
        lines.append("=" * len(title))
        lines.append("")

        # Collect entries for alignment
        entries: list[tuple[str, str, str, str]] = []
        for path, entry in provenance.items():
            type_str = self._formatted_type(entry.type_hint)
            value_str = self._formatted_value(entry.value)
            desc_str = entry.description or ""
            entries.append((path, type_str, value_str, desc_str))

        if not entries:
            lines.append("No configuration options found.")
            return lines

        # Calculate column widths
        path_width = max(len(e[0]) for e in entries)
        type_width = max(len(e[1]) for e in entries) if entries else 0
        value_width = max(len(e[2]) for e in entries) if entries else 0

        # Format entries
        for path, type_str, value_str, desc_str in entries:
            line = f"{path:<{path_width}}  {type_str:<{type_width}}  {value_str:<{value_width}}"
            if desc_str:
                line += f"  {desc_str}"
            lines.append(line)

        # Add multirun help
        lines.append(MULTIRUN_HELP)

        return lines

    def _formatted_type(self, type_hint: type | None) -> str:
        """Format a type hint for display.

        :param type_hint: The type hint.
        :return: Formatted type string.
        """
        if type_hint is None:
            return ""
        # For generic types (list[int], dict[str, Any], etc.), use str()
        # which gives the full parameterized type representation
        if hasattr(type_hint, "__origin__"):
            return str(type_hint)
        if hasattr(type_hint, "__name__"):
            return type_hint.__name__
        return str(type_hint)

    def _formatted_value(self, value: object) -> str:
        """Format a value for display.

        :param value: The value to format.
        :return: Formatted value string.
        """
        if value is None:
            return "(required)"
        elif isinstance(value, bool):
            return "true" if value else "false"
        elif isinstance(value, str):
            if len(value) > 20:
                return repr(value[:17] + "...")
            return repr(value)
        elif isinstance(value, (list, dict)):
            s = str(value)
            if len(s) > 20:
                return s[:17] + "..."
            return s
        else:
            return str(value)
