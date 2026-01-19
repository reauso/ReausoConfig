"""Single file exporter for config data.

Exports resolved config to a single file with format auto-detection.
"""

from pathlib import Path
from typing import Any

from rconfig._internal.path_utils import StrOrPath, ensure_path
from rconfig.export.file_base import FileExporter
from rconfig.export.registry import get_exporter


class SingleFileExporter(FileExporter):
    """Export resolved config to a single file with format auto-detection.

    All _ref_ references are resolved and flattened into one file.
    Interpolations are evaluated. The output is a standalone config.
    Format is determined by the output file extension.

    Example::

        exporter = SingleFileExporter(exclude_markers=True)
        exporter.export_to_file(config, Path("output.yaml"))  # YAML format
        exporter.export_to_file(config, Path("output.json"))  # JSON format
        exporter.export_to_file(config, Path("output.toml"))  # TOML format
    """

    def __init__(
        self,
        *,
        exclude_markers: bool = False,
        markers: tuple[str, ...] = ("_target_", "_ref_", "_instance_", "_lazy_"),
    ) -> None:
        """Initialize the single file exporter.

        :param exclude_markers: If True, remove internal config markers.
        :param markers: Tuple of marker keys to exclude.
        """
        self._exclude_markers = exclude_markers
        self._markers = markers

    def export_to_file(
        self,
        config: dict[str, Any],
        output_path: StrOrPath,
        *,
        source_path: StrOrPath | None = None,
        ref_graph: dict[str, list[str]] | None = None,
    ) -> None:
        """Export config to a single file with format auto-detection.

        :param config: Fully resolved config dictionary.
        :param output_path: Output file path (extension determines format).
                           Accepts str, Path, or any os.PathLike.
        :param source_path: Original config file path (unused for single file export).
                           Accepts str, Path, or any os.PathLike.
        :param ref_graph: Graph of _ref_ relationships (unused for single file export).
        :raises ConfigFileError: If the output file extension is not supported.
        """
        output_path = ensure_path(output_path)

        # Get the appropriate exporter for this file extension
        base_exporter = get_exporter(output_path)

        # Create a new exporter instance with our configuration
        configured_exporter = base_exporter.__class__(
            exclude_markers=self._exclude_markers,
            markers=self._markers,
        )

        content = configured_exporter.export(config)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")
