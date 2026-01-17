"""Argparse help integration for CLI help generation.

This module provides ArgparseHelpIntegration which integrates config entries
into argparse help output via the epilog.
"""

from __future__ import annotations

import argparse
from typing import TYPE_CHECKING

from .integration import HelpIntegration
from .multirun_help import MULTIRUN_HELP

if TYPE_CHECKING:
    from rconfig.provenance import Provenance


class ArgparseHelpIntegration(HelpIntegration):
    """Integrates config entries into argparse help output.

    This adds config entries to the argparse parser's epilog,
    so they appear when the user runs --help.

    Uses consume_help_flag=False because argparse handles --help itself.

    Example::

        parser = argparse.ArgumentParser()
        parser.add_argument("--verbose", action="store_true")

        rc.set_help_integration(ArgparseHelpIntegration(parser))
        args = parser.parse_args()
        config = rc.instantiate(Path("config.yaml"))

        # --help shows argparse help WITH config entries
    """

    def __init__(self, parser: argparse.ArgumentParser) -> None:
        """Initialize the argparse help integration.

        :param parser: The argparse parser to integrate with.
        """
        super().__init__(consume_help_flag=False)
        self._parser = parser

    def integrate(self, provenance: Provenance, config_path: str) -> None:
        """Add config entries to parser's epilog.

        :param provenance: Provenance data with type hints and descriptions.
        :param config_path: Path to the config file.
        """
        epilog = self._formatted_config_entries(provenance, config_path)
        if self._parser.epilog:
            self._parser.epilog += "\n\n" + epilog
        else:
            self._parser.epilog = epilog

        # Set formatter class to preserve formatting
        self._parser.formatter_class = argparse.RawDescriptionHelpFormatter

    def _formatted_config_entries(
        self, provenance: Provenance, config_path: str
    ) -> str:
        """Format config entries for epilog.

        :param provenance: Provenance data.
        :param config_path: Path to the config file.
        :return: Formatted epilog string.
        """
        lines: list[str] = []

        # Header
        lines.append(f"Configuration options ({config_path}):")
        lines.append("-" * 40)

        # Collect entries for alignment
        entries: list[tuple[str, str, str, str]] = []
        for path, entry in provenance.items():
            type_str = self._formatted_type(entry.type_hint)
            value_str = self._formatted_value(entry.value)
            desc_str = entry.description or ""
            entries.append((path, type_str, value_str, desc_str))

        if not entries:
            lines.append("  No configuration options found.")
            return "\n".join(lines)

        # Calculate column widths
        path_width = max(len(e[0]) for e in entries)
        type_width = max(len(e[1]) for e in entries) if entries else 0
        value_width = max(len(e[2]) for e in entries) if entries else 0

        # Format entries
        for path, type_str, value_str, desc_str in entries:
            line = f"  {path:<{path_width}}  {type_str:<{type_width}}  {value_str:<{value_width}}"
            if desc_str:
                line += f"  {desc_str}"
            lines.append(line)

        lines.append("")
        lines.append("Override with: python script.py key=value")
        lines.append(MULTIRUN_HELP)

        return "\n".join(lines)

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
