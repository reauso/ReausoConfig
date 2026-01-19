"""Flat layout for provenance formatting.

This module provides a simple flat single-line layout for provenance,
displaying each entry on one line with details in parentheses.
"""

from __future__ import annotations

from typing import Any

from rconfig._internal.format_utils import format_type_hint, format_value
from rconfig.provenance.models import EntrySourceType

from .model import ProvenanceDisplayModel, ProvenanceEntryDisplayModel
from .layout import ProvenanceLayout


class ProvenanceFlatLayout(ProvenanceLayout):
    """Simple flat single-line layout for provenance.

    Displays provenance in a compact single-line format:
    /path = value (location, details...)

    Example output::

        /model.lr = 0.001 (config.yaml:5)
        /model.dropout = 0.1 (config.yaml:6, CLI: --dropout)
        /data.batch_size = 32 (base.yaml:10, overrode: defaults.yaml:5)
    """

    def render(self, model: ProvenanceDisplayModel) -> str:
        """Render the provenance model to string output.

        :param model: The display model.
        :return: Formatted string representation.
        """
        if model.empty_message:
            return model.empty_message

        entries = [self._render_entry(e) for e in model.entries]
        result = "\n".join(entries)

        if model.header:
            result = f"{model.header}\n{result}"

        return result

    def _render_entry(self, entry: ProvenanceEntryDisplayModel) -> str:
        """Render a single entry in flat format.

        :param entry: The entry display model.
        :return: Formatted entry string.
        """
        parts: list[str] = []

        # Entry start (path and/or value)
        if entry.path is not None or entry.value is not None:
            start = self._format_entry_start(entry.path, entry.value)
            if start:
                parts.append(start)

        # Location (source type or file:line)
        if entry.source_type and entry.source_type != EntrySourceType.FILE:
            location = self._format_source_type(
                entry.source_type, entry.cli_arg, entry.env_var
            )
            if location:
                parts.append(location)
        elif entry.file:
            location = self._format_location(entry.file, entry.line)
            if location:
                parts.append(location)

        # Target info
        if entry.target_name is not None:
            target = self._format_target(
                entry.target_name,
                entry.target_class,
                entry.target_module,
                entry.target_auto_registered,
            )
            if target:
                parts.append(target)

        # Interpolation expression (flat layout skips tree)
        if entry.interpolation_expression:
            parts.append(f"${{{entry.interpolation_expression}}}")

        # Instance chain
        if entry.instances:
            for ref in entry.instances:
                if ref.file:
                    loc = f"{ref.file}:{ref.line}" if ref.line else ref.file
                    parts.append(f"instance: {ref.path} <- {loc}")
                else:
                    parts.append(f"instance: {ref.path}")

        # Override
        if entry.overrode:
            parts.append(f"overrode: {entry.overrode}")

        # Deprecation
        if entry.deprecation:
            dep_parts = ["DEPRECATED"]
            if entry.deprecation.new_key:
                dep_parts.append(f"-> {entry.deprecation.new_key}")
            parts.append(" ".join(dep_parts))

        # Type hint
        if entry.type_hint is not None:
            parts.append(self._format_type_hint(entry.type_hint))

        # Description
        if entry.description:
            parts.append(entry.description)

        # Join: first part is path=value, rest are details in parentheses
        if not parts:
            return ""
        if len(parts) == 1:
            return parts[0]
        return f"{parts[0]} ({', '.join(parts[1:])})"

    def _format_entry_start(self, path: str | None, value: Any | None) -> str:
        """Format the entry start (path and value).

        :param path: The config path (without leading /), or None.
        :param value: The resolved value, or None.
        :return: Formatted entry start string.
        """
        result_parts: list[str] = []
        if path:
            result_parts.append(f"/{path}")
        if value is not None:
            result_parts.append(f" = {format_value(value)}")
        return "".join(result_parts)

    def _format_location(self, file: str, line: int | None) -> str:
        """Format the file location.

        :param file: The source file name.
        :param line: The line number, or None.
        :return: Formatted location string.
        """
        if line is not None:
            return f"{file}:{line}"
        return file

    def _format_source_type(
        self,
        source_type: EntrySourceType,
        cli_arg: str | None,
        env_var: str | None,
    ) -> str:
        """Format the source type (CLI/env/programmatic).

        :param source_type: The source type.
        :param cli_arg: CLI argument name, or None.
        :param env_var: Environment variable name, or None.
        :return: Formatted source type string.
        """
        match source_type:
            case EntrySourceType.CLI:
                return f"CLI: {cli_arg}" if cli_arg else "CLI"
            case EntrySourceType.ENV:
                return f"env: {env_var}" if env_var else "env"
            case EntrySourceType.PROGRAMMATIC:
                return "programmatic"
            case _:
                return ""

    def _format_target(
        self,
        name: str,
        class_: str | None,
        module: str | None,
        auto_registered: bool,
    ) -> str:
        """Format target class information.

        :param name: The target name.
        :param class_: The target class name, or None.
        :param module: The target module name, or None.
        :param auto_registered: Whether target was auto-registered.
        :return: Formatted target string.
        """
        suffix = " (auto)" if auto_registered else ""
        if class_:
            if module:
                return f"target: {name} -> {module}.{class_}{suffix}"
            return f"target: {name} -> {class_}{suffix}"
        return f"target: {name}{suffix}"

    def _format_type_hint(self, type_hint: Any) -> str:
        """Format type hint information.

        :param type_hint: The type hint.
        :return: Formatted type hint string.
        """
        return format_type_hint(type_hint, prefix="type")
