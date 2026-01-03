"""Dictionary exporter for config data.

Returns a deep copy of the resolved config as a plain Python dictionary.
"""

import copy
from typing import Any

from rconfig.export.base import Exporter


class DictExporter(Exporter):
    """Export config as a plain Python dictionary.

    This exporter returns a deep copy of the resolved config dictionary,
    optionally excluding internal markers like _target_, _ref_, _instance_.

    Example::

        exporter = DictExporter(exclude_markers=True)
        config = exporter.export(resolved_config)
    """

    def __init__(
        self,
        *,
        exclude_markers: bool = False,
        markers: tuple[str, ...] = ("_target_", "_ref_", "_instance_", "_lazy_"),
    ) -> None:
        """Initialize the dict exporter.

        :param exclude_markers: If True, remove internal config markers from output.
        :param markers: Tuple of marker keys to exclude when exclude_markers=True.
        """
        self._exclude_markers = exclude_markers
        self._markers = set(markers)

    def export(self, config: dict[str, Any]) -> dict[str, Any]:
        """Export config as a dictionary.

        :param config: Fully resolved config dictionary.
        :return: Deep copy of the config, optionally with markers removed.
        """
        result = copy.deepcopy(config)
        if self._exclude_markers:
            self._remove_markers(result)
        return result

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
