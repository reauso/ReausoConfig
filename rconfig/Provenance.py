"""Provenance tracking for config composition.

This module provides classes for tracking the origin of each value
in a composed configuration, including file paths, line numbers,
and override information.
"""

from dataclasses import dataclass, field
from typing import Iterator


@dataclass
class InstanceRef:
    """Reference to an instance in the instance chain.

    :param path: The instance path (e.g., "/shared.database" or "alias").
    :param file: File where the referenced object is defined.
    :param line: Line number where the referenced object is defined.
    """

    path: str
    file: str
    line: int


@dataclass
class ProvenanceEntry:
    """Origin information for a config value.

    :param file: Source file path.
    :param line: Line number in source file.
    :param overrode: What this value overrode (if any), format: "file:line".
    :param instance: Chain of instance references with origins.
    """

    file: str
    line: int
    overrode: str | None = None
    instance: list[InstanceRef] | None = None


class Provenance:
    """Tracks the origin of each value in a composed config.

    The Provenance object stores where each config value came from,
    including the source file, line number, and any values that were
    overridden during composition.

    Example::

        prov = composer.compose_with_provenance("trainer.yaml")
        print(prov)
        # _target_: Trainer              # trainer.yaml:1
        # model:
        #   _target_: ResNet             # models/resnet.yaml:1
        #   layers: 50                   # trainer.yaml:5 (overrode models/resnet.yaml:2)

        origin = prov.get("model.layers")
        # ProvenanceEntry(file="trainer.yaml", line=5, overrode="models/resnet.yaml:2")
    """

    def __init__(self) -> None:
        """Initialize an empty provenance tracker."""
        self._entries: dict[str, ProvenanceEntry] = {}
        self._config: dict = {}

    def add(
        self,
        path: str,
        file: str,
        line: int,
        overrode: str | None = None,
        instance: list[InstanceRef] | None = None,
    ) -> None:
        """Add a provenance entry for a config path.

        :param path: The config path (e.g., "model.layers").
        :param file: Source file path.
        :param line: Line number in source file.
        :param overrode: What this value overrode (format: "file:line").
        :param instance: Chain of instance references.
        """
        self._entries[path] = ProvenanceEntry(
            file=file,
            line=line,
            overrode=overrode,
            instance=instance,
        )

    def set_config(self, config: dict) -> None:
        """Set the composed config for formatted output.

        :param config: The composed configuration dictionary.
        """
        self._config = config

    def get(self, path: str) -> ProvenanceEntry | None:
        """Get origin info for a specific config path.

        :param path: The config path (e.g., "model.layers").
        :return: ProvenanceEntry if path exists, None otherwise.

        Example::

            entry = prov.get("model.layers")
            if entry:
                print(f"Defined at {entry.file}:{entry.line}")
        """
        return self._entries.get(path)

    def items(self) -> Iterator[tuple[str, ProvenanceEntry]]:
        """Iterate over all paths and their origins.

        :return: Iterator of (path, ProvenanceEntry) tuples.

        Example::

            for path, entry in prov.items():
                print(f"{path}: {entry.file}:{entry.line}")
        """
        return iter(self._entries.items())

    def __str__(self) -> str:
        """Format provenance as a string showing config with origins.

        :return: Formatted string with config values and their sources.
        """
        if not self._config:
            return ""

        lines: list[str] = []
        self._format_value(self._config, "", lines, 0)
        return "\n".join(lines)

    def _format_value(
        self,
        value: object,
        path: str,
        lines: list[str],
        indent: int,
    ) -> None:
        """Recursively format a value with provenance annotations.

        :param value: The value to format.
        :param path: Current config path.
        :param lines: List to append formatted lines to.
        :param indent: Current indentation level.
        """
        prefix = "  " * indent

        if isinstance(value, dict):
            for key, val in value.items():
                current_path = f"{path}.{key}" if path else key
                entry = self._entries.get(current_path)
                annotation = self._format_annotation(entry)

                if isinstance(val, dict):
                    lines.append(f"{prefix}{key}:{annotation}")
                    self._format_value(val, current_path, lines, indent + 1)
                elif isinstance(val, list):
                    lines.append(f"{prefix}{key}:{annotation}")
                    self._format_list(val, current_path, lines, indent + 1)
                else:
                    lines.append(f"{prefix}{key}: {self._format_scalar(val)}{annotation}")
        else:
            entry = self._entries.get(path)
            annotation = self._format_annotation(entry)
            lines.append(f"{prefix}{self._format_scalar(value)}{annotation}")

    def _format_list(
        self,
        items: list,
        path: str,
        lines: list[str],
        indent: int,
    ) -> None:
        """Format a list with provenance annotations.

        :param items: The list to format.
        :param path: Current config path.
        :param lines: List to append formatted lines to.
        :param indent: Current indentation level.
        """
        prefix = "  " * indent
        for i, item in enumerate(items):
            item_path = f"{path}[{i}]"
            entry = self._entries.get(item_path)
            annotation = self._format_annotation(entry)

            if isinstance(item, dict):
                lines.append(f"{prefix}-{annotation}")
                self._format_value(item, item_path, lines, indent + 1)
            elif isinstance(item, list):
                lines.append(f"{prefix}-{annotation}")
                self._format_list(item, item_path, lines, indent + 1)
            else:
                lines.append(f"{prefix}- {self._format_scalar(item)}{annotation}")

    def _format_scalar(self, value: object) -> str:
        """Format a scalar value for display.

        :param value: The scalar value to format.
        :return: Formatted string representation.
        """
        if value is None:
            return "null"
        elif isinstance(value, bool):
            return "true" if value else "false"
        elif isinstance(value, str):
            # Quote strings that need it
            if " " in value or ":" in value or value.startswith(("'", '"')):
                return f'"{value}"'
            return value
        else:
            return str(value)

    def _format_annotation(self, entry: ProvenanceEntry | None) -> str:
        """Format a provenance annotation.

        :param entry: The provenance entry to format.
        :return: Formatted annotation string.
        """
        if entry is None:
            return ""

        annotation = f"  # {entry.file}:{entry.line}"
        if entry.overrode:
            annotation += f" (overrode {entry.overrode})"

        return annotation
