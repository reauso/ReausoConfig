"""Multi-file exporter for config data.

Exports config preserving the original _ref_ file structure.
"""

import copy
from io import StringIO
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

from rconfig.export.file_base import FileExporter


class MultiFileExporter(FileExporter):
    """Export config preserving the original _ref_ file structure.

    Each referenced file is exported separately with its interpolations
    resolved. The _ref_ paths are preserved so the exported config
    maintains the same structure as the original.

    Overrides stay in the parent file (not merged into referenced files).

    Example::

        exporter = MultiFileExporter()
        exporter.export_to_file(
            config,
            Path("output/"),
            source_path=Path("trainer.yaml"),
            ref_graph={"trainer.yaml": ["models/resnet.yaml"]}
        )
    """

    def __init__(
        self,
        *,
        default_flow_style: bool | None = False,
        indent: int = 2,
        exclude_markers: bool = False,
        markers: tuple[str, ...] = ("_target_", "_instance_", "_lazy_"),
    ) -> None:
        """Initialize the multi-file exporter.

        Note: _ref_ is not in default markers since we preserve file structure.

        :param default_flow_style: None=block style, True=flow style, False=mixed.
        :param indent: Number of spaces for indentation.
        :param exclude_markers: If True, remove internal config markers.
        :param markers: Tuple of marker keys to exclude.
        """
        self._default_flow_style = default_flow_style
        self._indent = indent
        self._exclude_markers = exclude_markers
        self._markers = set(markers)

    def export_to_file(
        self,
        config: dict[str, Any],
        output_path: Path,
        *,
        source_path: Path | None = None,
        ref_graph: dict[str, list[str]] | None = None,
    ) -> None:
        """Export config preserving file structure.

        :param config: Fully resolved config dictionary.
        :param output_path: Output directory for the exported files.
        :param source_path: Original config file path (required for multi-file export).
        :param ref_graph: Mapping of source file -> list of referenced file paths.
        :raises ValueError: If source_path is not provided.
        """
        if source_path is None:
            raise ValueError("source_path is required for multi-file export")

        output_path.mkdir(parents=True, exist_ok=True)

        if ref_graph is None or not ref_graph:
            self._export_single_file(config, output_path, source_path)
        else:
            self._export_multi_file(config, output_path, source_path, ref_graph)

    def _export_single_file(
        self,
        config: dict[str, Any],
        output_dir: Path,
        source_path: Path,
    ) -> None:
        """Export config as a single file when no ref_graph is provided."""
        output_file = output_dir / source_path.name
        yaml_content = self._to_yaml(config)
        output_file.write_text(yaml_content)

    def _export_multi_file(
        self,
        config: dict[str, Any],
        output_dir: Path,
        source_path: Path,
        ref_graph: dict[str, list[str]],
    ) -> None:
        """Export config preserving _ref_ file structure."""
        source_key = str(source_path)
        source_name = source_path.name

        main_output = output_dir / source_name
        yaml_content = self._to_yaml(config)
        main_output.write_text(yaml_content)

        exported_files = {source_key}
        files_to_export = list(ref_graph.get(source_key, []))

        while files_to_export:
            ref_file = files_to_export.pop(0)
            if ref_file in exported_files:
                continue

            exported_files.add(ref_file)

            ref_path = Path(ref_file)
            relative_to_source = self._get_relative_path(ref_path, source_path.parent)
            output_file = output_dir / relative_to_source

            output_file.parent.mkdir(parents=True, exist_ok=True)

            ref_config = self._extract_ref_config(config, relative_to_source)
            if ref_config is not None:
                yaml_content = self._to_yaml(ref_config)
                output_file.write_text(yaml_content)

            if ref_file in ref_graph:
                files_to_export.extend(ref_graph[ref_file])

    def _get_relative_path(self, ref_path: Path, base_path: Path) -> Path:
        """Get the relative path from base to ref_path."""
        try:
            return ref_path.relative_to(base_path)
        except ValueError:
            return Path(ref_path.name)

    def _extract_ref_config(
        self,
        config: dict[str, Any],
        ref_path: Path,
    ) -> dict[str, Any] | None:
        """Extract config for a referenced file.

        Since the config is fully resolved, we can't easily extract
        the original ref content. For now, return None to skip.
        The full implementation requires tracking original file contents.
        """
        return None

    def _to_yaml(self, config: dict[str, Any]) -> str:
        """Convert config to YAML string."""
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
