"""Single file exporter for config data.

Exports resolved config to a single YAML file with all references flattened.
"""

from pathlib import Path
from typing import Any

from rconfig.export.file_base import FileExporter
from rconfig.export.yaml_exporter import YamlExporter


class SingleFileExporter(FileExporter):
    """Export resolved config to a single YAML file.

    All _ref_ references are resolved and flattened into one file.
    Interpolations are evaluated. The output is a standalone config.

    Example::

        exporter = SingleFileExporter(exclude_markers=True)
        exporter.export_to_file(config, Path("output.yaml"))
    """

    def __init__(
        self,
        *,
        default_flow_style: bool | None = False,
        indent: int = 2,
        exclude_markers: bool = False,
        markers: tuple[str, ...] = ("_target_", "_ref_", "_instance_", "_lazy_"),
    ) -> None:
        """Initialize the single file exporter.

        :param default_flow_style: None=block style, True=flow style, False=mixed.
        :param indent: Number of spaces for indentation.
        :param exclude_markers: If True, remove internal config markers.
        :param markers: Tuple of marker keys to exclude.
        """
        self._yaml_exporter = YamlExporter(
            default_flow_style=default_flow_style,
            indent=indent,
            exclude_markers=exclude_markers,
            markers=markers,
        )

    def export_to_file(
        self,
        config: dict[str, Any],
        output_path: Path,
        *,
        source_path: Path | None = None,
        ref_graph: dict[str, list[str]] | None = None,
    ) -> None:
        """Export config to a single YAML file.

        :param config: Fully resolved config dictionary.
        :param output_path: Output file path.
        :param source_path: Original config file path (unused for single file export).
        :param ref_graph: Graph of _ref_ relationships (unused for single file export).
        """
        yaml_content = self._yaml_exporter.export(config)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(yaml_content)
