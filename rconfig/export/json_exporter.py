"""JSON exporter for config data.

Exports resolved config as a JSON string using Python's standard library.
"""

import copy
import json
from typing import Any

from rconfig.export.base import Exporter


class JsonExporter(Exporter):
    """Export config as a JSON string.

    Uses Python's standard library json module.

    Example::

        exporter = JsonExporter(indent=4, exclude_markers=True)
        json_str = exporter.export(resolved_config)
    """

    def __init__(
        self,
        *,
        indent: int | None = 2,
        ensure_ascii: bool = False,
        sort_keys: bool = False,
        exclude_markers: bool = False,
        markers: tuple[str, ...] = ("_target_", "_ref_", "_instance_", "_lazy_"),
    ) -> None:
        """Initialize the JSON exporter.

        :param indent: Number of spaces for indentation, None for compact output.
        :param ensure_ascii: If True, escape non-ASCII characters.
        :param sort_keys: If True, sort dictionary keys alphabetically.
        :param exclude_markers: If True, remove internal config markers.
        :param markers: Tuple of marker keys to exclude.
        """
        self._indent = indent
        self._ensure_ascii = ensure_ascii
        self._sort_keys = sort_keys
        self._exclude_markers = exclude_markers
        self._markers = set(markers)

    def export(self, config: dict[str, Any]) -> str:
        """Export config as a JSON string.

        :param config: Fully resolved config dictionary.
        :return: JSON string representation.
        """
        data = copy.deepcopy(config)
        if self._exclude_markers:
            self._remove_markers(data)

        return json.dumps(
            data,
            indent=self._indent,
            ensure_ascii=self._ensure_ascii,
            sort_keys=self._sort_keys,
        )

    def _remove_markers(self, obj: Any) -> None:
        """Recursively remove marker keys from nested dicts."""
        if isinstance(obj, dict):
            for marker in self._markers:
                obj.pop(marker, None)
            for value in obj.values():
                self._remove_markers(value)
        elif isinstance(obj, list):
            for item in obj:
                self._remove_markers(item)
