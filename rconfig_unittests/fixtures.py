"""Test fixtures and helpers for rconfig unit tests.

This module provides test utilities for creating mock configs and
asserting validation results.
"""

from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator
from unittest.mock import patch

from ruamel.yaml.comments import CommentedMap


def make_commented_map(data: dict[str, Any]) -> CommentedMap:
    """Create a CommentedMap from a dict, recursively converting nested dicts.

    :param data: Dictionary to convert.
    :return: CommentedMap with the same structure.
    """
    result = CommentedMap(data)
    for key, value in data.items():
        if isinstance(value, dict):
            result[key] = make_commented_map(value)
        elif isinstance(value, list):
            result[key] = [
                make_commented_map(item) if isinstance(item, dict) else item
                for item in value
            ]
    return result


class MockFileSystem:
    """A mock file system for testing config composition without real files.

    Use with the `mock_filesystem()` context manager to mock Path operations
    and file loading so tests don't access the real filesystem.

    Example::

        fs = MockFileSystem("/configs")
        fs.add_file("/configs/app.yaml", {"_target_": "App", "value": 42})

        with mock_filesystem(fs):
            composer = ConfigComposer(fs.base_path)
            result = composer.compose(Path("/configs/app.yaml"))
    """

    def __init__(self, base_path: str = "/configs") -> None:
        """Initialize the mock file system.

        :param base_path: Base path for relative file resolution.
        """
        self._files: dict[str, dict[str, Any]] = {}
        self._base_path = Path(base_path)

    def add_file(self, path: str, content: dict[str, Any]) -> "MockFileSystem":
        """Add a file to the mock file system.

        :param path: Absolute path to the file (as string).
        :param content: Config dictionary to return when this file is loaded.
        :return: Self for method chaining.
        """
        self._files[path] = content
        return self

    def exists(self, path: str) -> bool:
        """Check if a file exists in the mock file system.

        :param path: Path to check (as string).
        :return: True if the file exists in the mock filesystem.
        """
        return path in self._files

    def load(self, path: str) -> CommentedMap:
        """Load a file from the mock file system.

        This method signature matches _load_file_cached.

        :param path: Path to the file (as string).
        :return: CommentedMap with the file contents.
        :raises KeyError: If the file is not found.
        """
        if path in self._files:
            return make_commented_map(self._files[path])
        raise KeyError(f"Mock file not found: {path}")

    @property
    def base_path(self) -> Path:
        """Return the base path for this mock file system."""
        return self._base_path


@contextmanager
def mock_filesystem(fs: MockFileSystem) -> Generator[None, None, None]:
    """Context manager that mocks Path operations to use a MockFileSystem.

    This patches:
    - `_load_file_cached` to load from the mock filesystem
    - `Path.exists()` to check the mock filesystem
    - `Path.resolve()` to normalize paths (handles `..` and `.` segments)

    Example::

        fs = MockFileSystem("/configs")
        fs.add_file("/configs/app.yaml", {"_target_": "App"})

        with mock_filesystem(fs):
            walker = CompositionWalker(Path("/configs"), Provenance())
            result = walker.compose(Path("/configs/app.yaml"))

    :param fs: The MockFileSystem instance to use.
    """
    import posixpath

    def mock_exists(path_self: Path) -> bool:
        return fs.exists(str(path_self))

    def mock_resolve(path_self: Path) -> Path:
        # Normalize the path to handle .. and . segments
        # Use posixpath.normpath to resolve parent references
        normalized = posixpath.normpath(str(path_self))
        return Path(normalized)

    with (
        patch("rconfig.composition.Walker._load_file_cached", fs.load),
        patch.object(Path, "exists", mock_exists),
        patch.object(Path, "resolve", mock_resolve),
    ):
        yield
