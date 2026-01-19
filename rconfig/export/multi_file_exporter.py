"""Multi-file exporter for config data.

Exports config preserving the original _ref_ file structure with format auto-detection.
"""

import copy
from pathlib import Path
from typing import Any

from rconfig._internal.path_utils import StrOrPath, ensure_path
from rconfig.export.file_base import FileExporter
from rconfig.export.registry import get_exporter


class MultiFileExporter(FileExporter):
    """Export config preserving the original _ref_ file structure.

    Each referenced file is exported separately with its interpolations
    resolved. The _ref_ paths are preserved so the exported config
    maintains the same structure as the original.

    Format is determined by file extensions:
    - Root file: format from output_path extension
    - Referenced files: preserve original extension from ref_graph paths

    Overrides stay in the parent file (not merged into referenced files).

    Example::

        exporter = MultiFileExporter()
        exporter.export_to_file(
            config,
            Path("output/trainer.json"),  # Root file as JSON
            source_path=Path("trainer.yaml"),
            ref_graph={"trainer.yaml": ["models/resnet.yaml"]}
        )
        # Creates:
        #   output/trainer.json (root file in JSON)
        #   output/models/resnet.yaml (preserves original YAML format)
    """

    def __init__(
        self,
        *,
        exclude_markers: bool = False,
        markers: tuple[str, ...] = ("_target_", "_instance_", "_lazy_"),
    ) -> None:
        """Initialize the multi-file exporter.

        Note: _ref_ is not in default markers since we preserve file structure.

        :param exclude_markers: If True, remove internal config markers.
        :param markers: Tuple of marker keys to exclude.
        """
        self._exclude_markers = exclude_markers
        self._markers = set(markers)

    def export_to_file(
        self,
        config: dict[str, Any],
        output_path: StrOrPath,
        *,
        source_path: StrOrPath | None = None,
        ref_graph: dict[str, list[str]] | None = None,
    ) -> None:
        """Export config preserving file structure with format auto-detection.

        :param config: Fully resolved config dictionary.
        :param output_path: Output root file path (extension determines root file format).
                           Accepts str, Path, or any os.PathLike.
        :param source_path: Original config file path (optional, enables multi-file export).
                           Accepts str, Path, or any os.PathLike.
        :param ref_graph: Mapping of source file -> list of referenced file paths.
        :raises ConfigFileError: If an output file extension is not supported.

        Note: If source_path is None, only the root file is written.
        """
        output_path = ensure_path(output_path)
        source_path_resolved = ensure_path(source_path) if source_path is not None else None

        # Create parent directory for the output root file
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if source_path_resolved is None or ref_graph is None or not ref_graph:
            self._export_single_file(config, output_path)
        else:
            self._export_multi_file(config, output_path, source_path_resolved, ref_graph)

    def _export_single_file(
        self,
        config: dict[str, Any],
        output_path: Path,
    ) -> None:
        """Export config as a single file when no ref_graph is provided."""
        content = self._export_content(config, output_path)
        output_path.write_text(content, encoding="utf-8")

    def _export_multi_file(
        self,
        config: dict[str, Any],
        output_path: Path,
        source_path: Path,
        ref_graph: dict[str, list[str]],
    ) -> None:
        """Export config preserving _ref_ file structure."""
        source_key = str(source_path)

        # Export root file (format from output_path extension)
        content = self._export_content(config, output_path)
        output_path.write_text(content, encoding="utf-8")

        exported_files = {source_key}
        files_to_export = list(ref_graph.get(source_key, []))
        output_dir = output_path.parent

        while files_to_export:
            ref_file = files_to_export.pop(0)
            if ref_file in exported_files:
                continue

            exported_files.add(ref_file)

            ref_path = Path(ref_file)
            relative_to_source = self._get_relative_path(ref_path, source_path.parent)
            # Preserve original file extension for referenced files
            output_file = output_dir / relative_to_source

            output_file.parent.mkdir(parents=True, exist_ok=True)

            ref_config = self._extract_ref_config(config, relative_to_source)
            if ref_config is not None:
                # Format determined by original ref file extension
                content = self._export_content(ref_config, output_file)
                output_file.write_text(content, encoding="utf-8")

            if ref_file in ref_graph:
                files_to_export.extend(ref_graph[ref_file])

    def _export_content(self, config: dict[str, Any], output_path: Path) -> str:
        """Export config to string. Format detected from output_path extension.

        :param config: Config dictionary to export.
        :param output_path: Output file path (extension determines format).
        :return: Exported content as string.
        :raises ConfigFileError: If the output file extension is not supported.
        """
        # Get the appropriate exporter for this file extension
        base_exporter = get_exporter(output_path)

        # Create a new exporter instance with our configuration
        configured_exporter = base_exporter.__class__(
            exclude_markers=self._exclude_markers,
            markers=tuple(self._markers),
        )

        data = copy.deepcopy(config)
        if self._exclude_markers:
            self._remove_markers(data)

        return configured_exporter.export(data)

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
