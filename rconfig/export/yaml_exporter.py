"""YAML exporter for config data.

Exports resolved config as a YAML string using ruamel.yaml.
"""

import copy
from io import StringIO
from typing import Any

from ruamel.yaml import YAML

from rconfig.export.base import Exporter


class YamlExporter(Exporter):
    """Export config as a YAML string.

    Uses ruamel.yaml for YAML generation, consistent with the loader.

    Example::

        exporter = YamlExporter(indent=4, exclude_markers=True)
        yaml_str = exporter.export(resolved_config)
    """

    def __init__(
        self,
        *,
        default_flow_style: bool | None = False,
        indent: int = 2,
        exclude_markers: bool = False,
        markers: tuple[str, ...] = ("_target_", "_ref_", "_instance_", "_lazy_"),
    ) -> None:
        """Initialize the YAML exporter.

        :param default_flow_style: None=block style, True=flow style, False=mixed.
        :param indent: Number of spaces for indentation.
        :param exclude_markers: If True, remove internal config markers.
        :param markers: Tuple of marker keys to exclude.
        """
        self._default_flow_style = default_flow_style
        self._indent = indent
        self._exclude_markers = exclude_markers
        self._markers = set(markers)

    def export(self, config: dict[str, Any]) -> str:
        """Export config as a YAML string.

        :param config: Fully resolved config dictionary.
        :return: YAML string representation.
        """
        data = copy.deepcopy(config)
        if self._exclude_markers:
            self._remove_markers(data)

        yaml = YAML()
        yaml.default_flow_style = self._default_flow_style
        yaml.indent(mapping=self._indent, sequence=self._indent, offset=self._indent)

        stream = StringIO()
        yaml.dump(data, stream)
        return stream.getvalue()

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
