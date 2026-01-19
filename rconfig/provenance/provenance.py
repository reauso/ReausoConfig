"""Immutable provenance container.

This module provides the Provenance class, an immutable mapping of config
paths to their provenance entries.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from types import MappingProxyType
from typing import Any

from rconfig._internal.path_utils import build_child_path

from .models import ProvenanceEntry, ProvenanceNode


class Provenance(Mapping[str, ProvenanceEntry]):
    """Immutable mapping of config paths to their provenance entries.

    The Provenance object stores where each config value came from,
    including the source file, line number, and any values that were
    overridden during composition.

    Implements the ``Mapping`` protocol for Pythonic access::

        entry = prov["model.layers"]           # __getitem__
        entry = prov.get("model.layers")       # get() with None default
        "model.layers" in prov                 # __contains__
        len(prov)                              # __len__
        for path in prov:                      # __iter__ (keys)
            print(path)
        for path, entry in prov.items():       # items()
            print(f"{path}: {entry.file}:{entry.line}")

    Example::

        prov = rc.get_provenance("trainer.yaml")
        print(prov)
        # _target_: Trainer              # trainer.yaml:1
        # model:
        #   _target_: ResNet             # models/resnet.yaml:1
        #   layers: 50                   # trainer.yaml:5 (overrode models/resnet.yaml:2)

        origin = prov.get("model.layers")
        # ProvenanceEntry(file="trainer.yaml", line=5, overrode="models/resnet.yaml:2")
    """

    def __init__(
        self,
        entries: dict[str, ProvenanceEntry] | None = None,
        config: dict | None = None,
    ) -> None:
        """Initialize a provenance object with frozen entries.

        :param entries: Dictionary of path to ProvenanceEntry mappings.
        :param config: The composed configuration dictionary.
        """
        # Use MappingProxyType for true immutability
        self._entries: Mapping[str, ProvenanceEntry] = MappingProxyType(
            entries if entries is not None else {}
        )
        self._config: Mapping = MappingProxyType(
            config if config is not None else {}
        )

    # === Mapping protocol implementation ===

    def __getitem__(self, path: str) -> ProvenanceEntry:
        """Get origin info for a specific config path.

        :param path: The config path (e.g., "model.layers").
        :return: ProvenanceEntry for the path.
        :raises KeyError: If path is not found.
        """
        return self._entries[path]

    def __iter__(self) -> Iterator[str]:
        """Iterate over all config paths.

        :return: Iterator of config paths.
        """
        return iter(self._entries)

    def __len__(self) -> int:
        """Get the number of provenance entries.

        :return: Number of entries.
        """
        return len(self._entries)

    # === Additional methods (get, keys, values, items, __contains__) ===
    # are inherited from Mapping ABC

    # === Properties ===

    @property
    def config(self) -> Mapping:
        """Get the composed configuration dictionary.

        :return: Read-only view of the config dictionary.
        """
        return self._config

    # === Domain-specific methods ===

    def to_dict(self) -> dict[str, Any]:
        """Convert the entire provenance to a dictionary.

        :return: Dictionary with paths as keys and entry dicts as values.

        Example::

            data = prov.to_dict()
            for path, entry_data in data.items():
                print(f"{path}: {entry_data}")
        """
        return {path: entry.to_dict() for path, entry in self._entries.items()}

    def trace(self, path: str) -> ProvenanceNode | None:
        """Get the provenance tree for a specific path.

        Builds a tree structure showing the full origin chain including
        interpolations, instances, and refs.

        :param path: The config path to trace.
        :return: Root ProvenanceNode or None if path not found.

        Example::

            tree = prov.trace("model.lr")
            if tree:
                print(tree.to_dict())
        """
        entry = self._entries.get(path)
        if entry is None:
            return None
        return entry.trace()

    def __str__(self) -> str:
        """Format provenance as a string showing config with origins.

        :return: Formatted string with config values and their sources.
        """
        if not self._config:
            return ""

        lines: list[str] = []
        self._format_value(self._config, "", lines, 0)
        return "\n".join(lines)

    def __repr__(self) -> str:
        """Return a debug-friendly representation.

        :return: String representation showing entry count.
        """
        return f"Provenance(entries={len(self._entries)})"

    def __bool__(self) -> bool:
        """Return False if empty, True otherwise.

        :return: Boolean indicating if provenance has entries.
        """
        return len(self._entries) > 0

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

        if isinstance(value, Mapping):
            for key, val in value.items():
                current_path = f"{path}.{key}" if path else key
                entry = self._entries.get(current_path)
                annotation = self._format_annotation(entry)

                if isinstance(val, Mapping):
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
            item_path = build_child_path(path, i)
            entry = self._entries.get(item_path)
            annotation = self._format_annotation(entry)

            if isinstance(item, Mapping):
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
        if entry.interpolation:
            annotation += f" (interpolated: ${{{entry.interpolation.expression}}})"

        return annotation
