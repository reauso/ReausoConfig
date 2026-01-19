"""Markdown table layout for provenance formatting.

This module provides a markdown table layout for provenance,
suitable for documentation and export.
"""

from __future__ import annotations

from rconfig._internal.format_utils import format_value
from rconfig.provenance.models import EntrySourceType

from .model import ProvenanceDisplayModel, ProvenanceEntryDisplayModel
from .layout import ProvenanceLayout


class ProvenanceMarkdownLayout(ProvenanceLayout):
    """Markdown table layout for provenance.

    Formats provenance as a markdown table for documentation or export.

    Example output::

        | Path | Value | Source | Details |
        |------|-------|--------|---------|
        | model.lr | 0.001 | config.yaml:5 | - |
        | model.dropout | 0.1 | config.yaml:6 | CLI: --dropout |
        | data.batch_size | 32 | base.yaml:10 | Overrode: defaults.yaml:5 |

        **Summary:** 3 entries
    """

    def render(self, model: ProvenanceDisplayModel) -> str:
        """Render the provenance model as a markdown table.

        :param model: The display model.
        :return: Formatted markdown string.
        """
        if model.empty_message:
            return "_No entries found._"

        # Pre-scan to determine which columns to show
        show_values = any(e.value is not None for e in model.entries)
        show_source = any(
            e.file or (e.source_type and e.source_type != EntrySourceType.FILE)
            for e in model.entries
        )
        show_details = any(
            e.target_name
            or e.interpolation_expression
            or e.overrode
            or e.deprecation
            or e.instances
            for e in model.entries
        )

        # Build header row
        header_parts: list[str] = ["Path"]
        if show_values:
            header_parts.append("Value")
        if show_source:
            header_parts.append("Source")
        if show_details:
            header_parts.append("Details")

        lines: list[str] = []
        lines.append("| " + " | ".join(header_parts) + " |")
        lines.append("|" + "|".join(["------"] * len(header_parts)) + "|")

        # Build data rows
        for entry in model.entries:
            row = self._render_row(entry, show_values, show_source, show_details)
            lines.append(row)

        result = "\n".join(lines)

        # Add header if present
        if model.header:
            result = f"**{model.header}**\n\n{result}"

        return result

    def _render_row(
        self,
        entry: ProvenanceEntryDisplayModel,
        show_values: bool,
        show_source: bool,
        show_details: bool,
    ) -> str:
        """Render a single provenance entry as a table row.

        :param entry: The entry display model.
        :param show_values: Whether to show value column.
        :param show_source: Whether to show source column.
        :param show_details: Whether to show details column.
        :return: Formatted markdown table row.
        """
        parts: list[str] = []

        # Path column (always present)
        path = f"/{entry.path}" if entry.path else "-"
        parts.append(self._escape_markdown(path))

        # Value column
        if show_values:
            if entry.value is not None:
                parts.append(self._escape_markdown(format_value(entry.value)))
            else:
                parts.append("-")

        # Source column
        if show_source:
            source = self._format_source(entry)
            parts.append(self._escape_markdown(source) if source else "-")

        # Details column
        if show_details:
            details = self._format_details(entry)
            parts.append(self._escape_markdown(details) if details else "-")

        return "| " + " | ".join(parts) + " |"

    def _format_source(self, entry: ProvenanceEntryDisplayModel) -> str | None:
        """Format source information for an entry.

        :param entry: The entry display model.
        :return: Formatted source string or None.
        """
        # Handle non-file source types
        if entry.source_type and entry.source_type != EntrySourceType.FILE:
            match entry.source_type:
                case EntrySourceType.CLI:
                    return f"CLI: {entry.cli_arg}" if entry.cli_arg else "CLI"
                case EntrySourceType.ENV:
                    return f"env: {entry.env_var}" if entry.env_var else "env"
                case EntrySourceType.PROGRAMMATIC:
                    return "programmatic"

        # Standard file:line format
        if entry.file:
            if entry.line is not None:
                return f"{entry.file}:{entry.line}"
            return entry.file

        return None

    def _format_details(self, entry: ProvenanceEntryDisplayModel) -> str | None:
        """Format details information for an entry.

        :param entry: The entry display model.
        :return: Formatted details string or None.
        """
        details: list[str] = []

        if entry.target_name:
            target_str = entry.target_name
            if entry.target_class:
                if entry.target_module:
                    target_str += f" -> {entry.target_module}.{entry.target_class}"
                else:
                    target_str += f" -> {entry.target_class}"
            if entry.target_auto_registered:
                target_str += " (auto)"
            details.append(f"Target: {target_str}")

        if entry.interpolation_expression:
            details.append(f"Interp: ${{{entry.interpolation_expression}}}")

        if entry.instances:
            for ref in entry.instances:
                if ref.file:
                    loc = f"{ref.file}:{ref.line}" if ref.line else ref.file
                    details.append(f"Instance: {ref.path} <- {loc}")
                else:
                    details.append(f"Instance: {ref.path}")

        if entry.overrode:
            details.append(f"Overrode: {entry.overrode}")

        if entry.deprecation:
            dep_str = "DEPRECATED"
            if entry.deprecation.new_key:
                dep_str += f" -> {entry.deprecation.new_key}"
            details.append(dep_str)

        return "; ".join(details) if details else None

    def _escape_markdown(self, text: str) -> str:
        """Escape markdown special characters in table cells.

        :param text: Text to escape.
        :return: Escaped text safe for markdown tables.
        """
        # Escape pipe characters which break table structure
        text = text.replace("|", "\\|")
        # Escape newlines
        text = text.replace("\n", " ")
        return text
