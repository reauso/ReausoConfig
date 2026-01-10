"""TOML exporter for config data.

Exports resolved config as a TOML string using tomli_w.
"""

import copy
from typing import Any

import tomli_w

from rconfig.export.base import Exporter


class TomlExporter(Exporter):
    """Export config as a TOML string.

    Uses tomli_w for TOML generation (the official companion to stdlib tomllib).

    Example::

        exporter = TomlExporter(exclude_markers=True)
        toml_str = exporter.export(resolved_config)
    """

    def __init__(
        self,
        *,
        multiline_strings: bool = False,
        exclude_markers: bool = False,
        markers: tuple[str, ...] = ("_target_", "_ref_", "_instance_", "_lazy_"),
    ) -> None:
        """Initialize the TOML exporter.

        :param multiline_strings: If True, use multiline format for long strings.
        :param exclude_markers: If True, remove internal config markers.
        :param markers: Tuple of marker keys to exclude.
        """
        self._multiline_strings = multiline_strings
        self._exclude_markers = exclude_markers
        self._markers = set(markers)

    def export(self, config: dict[str, Any]) -> str:
        """Export config as a TOML string.

        :param config: Fully resolved config dictionary.
        :return: TOML string representation.
        """
        data = copy.deepcopy(config)
        if self._exclude_markers:
            self._remove_markers(data)

        return tomli_w.dumps(data, multiline_strings=self._multiline_strings)

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
