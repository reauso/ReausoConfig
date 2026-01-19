"""Abstract base class for file-based config exporters.

This module defines the interface for exporters that write config data
to one or more files on disk.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from rconfig._internal.path_utils import StrOrPath


class FileExporter(ABC):
    """Abstract base class for file-based config exporters.

    Subclass this to add support for new file export strategies.
    Implementations write resolved config data to one or more files.

    Example::

        class JsonFileExporter(FileExporter):
            def export_to_file(
                self,
                config: dict[str, Any],
                output_path: Path,
                *,
                source_path: Path | None = None,
                ref_graph: dict[str, list[str]] | None = None,
            ) -> None:
                import json
                output_path.write_text(json.dumps(config, indent=2))
    """

    @abstractmethod
    def export_to_file(
        self,
        config: dict[str, Any],
        output_path: StrOrPath,
        *,
        source_path: StrOrPath | None = None,
        ref_graph: dict[str, list[str]] | None = None,
    ) -> None:
        """Export config to file(s).

        :param config: Fully resolved config dictionary.
        :param output_path: Output file path (single file) or directory (multi-file).
                           Accepts str, Path, or any os.PathLike.
        :param source_path: Original config file path (for relative path resolution).
                           Accepts str, Path, or any os.PathLike.
        :param ref_graph: Graph of _ref_ relationships for multi-file export.
                          Maps file path -> list of referenced file paths.
        """
