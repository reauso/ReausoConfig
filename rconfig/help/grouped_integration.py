"""Grouped help integration for CLI help generation.

This module provides GroupedHelpIntegration which displays config entries
grouped by top-level key with indentation.
"""

from __future__ import annotations

import sys
from collections import defaultdict
from typing import TYPE_CHECKING, TextIO

from .integration import HelpIntegration
from .multirun_help import MULTIRUN_HELP

if TYPE_CHECKING:
    from rconfig.provenance import Provenance, ProvenanceEntry


class GroupedHelpIntegration(HelpIntegration):
    """Displays entries grouped by top-level key with indentation.

    Output::

        Configuration options for config.yaml
        =====================================

        model:
          lr                  float       0.001      Learning rate
          hidden_size         int         256        Hidden layer size
        data:
          path                str         (required) Path to data
    """

    def __init__(self, *, output: TextIO | None = None) -> None:
        """Initialize the grouped help integration.

        :param output: Output stream to write to. Defaults to sys.stdout.
        """
        super().__init__(consume_help_flag=True)
        self._output = output if output is not None else sys.stdout

    def integrate(self, provenance: Provenance, config_path: str) -> None:
        """Display help as grouped structure, then exit.

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
        """Format provenance as grouped help output.

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

        # Group entries by top-level key
        groups: dict[str, list[tuple[str, ProvenanceEntry]]] = defaultdict(list)
        for path, entry in provenance.items():
            if "." in path:
                group, rest = path.split(".", 1)
                groups[group].append((rest, entry))
            else:
                groups[path].append(("", entry))

        if not groups:
            lines.append("No configuration options found.")
            return lines

        # Calculate column widths within each group
        for group_name in sorted(groups.keys()):
            entries = groups[group_name]
            lines.append(f"{group_name}:")

            # Prepare entries for alignment
            formatted_entries: list[tuple[str, str, str, str]] = []
            for subpath, entry in entries:
                display_path = subpath if subpath else "(root)"
                type_str = self._formatted_type(entry.type_hint)
                value_str = self._formatted_value(entry.value)
                desc_str = entry.description or ""
                formatted_entries.append((display_path, type_str, value_str, desc_str))

            if not formatted_entries:
                continue

            # Calculate column widths for this group
            path_width = max(len(e[0]) for e in formatted_entries)
            type_width = max(len(e[1]) for e in formatted_entries) if formatted_entries else 0
            value_width = max(len(e[2]) for e in formatted_entries) if formatted_entries else 0

            # Format entries with indentation
            for path, type_str, value_str, desc_str in formatted_entries:
                line = f"  {path:<{path_width}}  {type_str:<{type_width}}  {value_str:<{value_width}}"
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
