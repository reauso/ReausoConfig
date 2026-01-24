"""File path resolution for _ref_ references.

This module provides FilePathResolver, which handles resolving _ref_
path strings to absolute filesystem paths. It supports relative paths,
absolute paths (from config root), and extension-less paths (resolved
by globbing against supported loader extensions).
"""

from pathlib import Path

from rconfig.errors import AmbiguousRefError, RefResolutionError
from rconfig.loaders import supported_loader_extensions


class FilePathResolver:
    """Resolves _ref_ file paths to absolute filesystem paths.

    Handles relative paths, absolute paths (from config root),
    and extension-less paths (globbed against supported extensions).

    Example::

        resolver = FilePathResolver(config_root=Path("/project/configs"))
        path = resolver.resolve("./model.yaml", current_dir, "trainer.model")
    """

    def __init__(self, config_root: Path | None) -> None:
        """Initialize the resolver.

        :param config_root: Root directory for absolute path resolution.
                           If None, absolute _ref_ paths will raise an error.
        """
        self._config_root = config_root

    def resolve(self, ref_path: str, current_dir: Path, config_path: str) -> Path:
        """Resolve a _ref_ path to an absolute file path.

        :param ref_path: The _ref_ path string.
        :param current_dir: Directory of current file.
        :param config_path: Current path in config (for error messages).
        :return: Resolved absolute path.
        """
        if ref_path.startswith("/"):
            if self._config_root is None:
                raise RefResolutionError(
                    ref_path,
                    "cannot use absolute path without config root",
                    config_path,
                    hint="Use a relative path (e.g., './file.yaml') or set config_root when composing.",
                )
            base_path = self._config_root / ref_path[1:]
        else:
            base_path = current_dir / ref_path

        # Check if path has an extension
        if self._has_extension(ref_path):
            resolved = base_path.resolve()
            if not resolved.exists():
                raise RefResolutionError(
                    ref_path,
                    "file not found",
                    config_path,
                    hint="Verify the file path is correct. Use './' for relative paths or '/' for paths from config root.",
                )
            return resolved

        # Extension-less resolution
        return self._resolve_extensionless_path(base_path, ref_path, config_path)

    def _has_extension(self, ref_path: str) -> bool:
        """Check if a path has a file extension."""
        filename = Path(ref_path).name
        return bool(Path(filename).suffix)

    def _resolve_extensionless_path(
        self,
        base_path: Path,
        ref_path: str,
        config_path: str,
    ) -> Path:
        """Resolve an extension-less _ref_ path by globbing.

        :param base_path: The base path without extension.
        :param ref_path: Original _ref_ path (for error messages).
        :param config_path: Current path in config (for error messages).
        :return: Resolved absolute path.
        """
        parent = base_path.parent.resolve()
        stem = base_path.name

        if not parent.exists():
            raise RefResolutionError(
                ref_path,
                f"directory not found: {parent}",
                config_path,
            )

        pattern = f"{stem}.*"
        all_matches = list(parent.glob(pattern))

        supported_exts = supported_loader_extensions()
        matching_files = [
            f for f in all_matches if f.is_file() and f.suffix.lower() in supported_exts
        ]

        if len(matching_files) == 0:
            if all_matches:
                found_exts = [f.suffix for f in all_matches if f.is_file()]
                raise RefResolutionError(
                    ref_path,
                    f"no config file found matching '{stem}.*' with supported extension. "
                    f"Found files with unsupported extensions: {found_exts}. "
                    f"Supported extensions: {sorted(supported_exts)}",
                    config_path,
                )
            else:
                raise RefResolutionError(
                    ref_path,
                    f"no config file found matching '{stem}.*' in {parent}",
                    config_path,
                )

        if len(matching_files) > 1:
            file_names = sorted([f.name for f in matching_files])
            raise AmbiguousRefError(ref_path, file_names, config_path)

        return matching_files[0]
