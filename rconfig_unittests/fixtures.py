"""Test fixtures and helpers for rconfig unit tests.

This module provides test utilities for creating mock configs and
asserting validation results.
"""

from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Generator
from unittest import TestCase
from unittest.mock import patch

from rconfig.target import TargetRegistry


# =============================================================================
# Base Test Classes
# =============================================================================


class BaseStoreTest(TestCase):
    """Base class for tests that need a clean TargetRegistry.

    Provides the `_empty_store()` helper method that creates a fresh
    TargetRegistry with all targets cleared. This is the standard pattern
    for test isolation in rconfig tests.

    Example::

        class MyTests(BaseStoreTest):
            def test_something__SomeScenario__ExpectedResult(self):
                # Arrange
                store = self._empty_store()
                store.register("model", ModelClass)

                # Act
                result = do_something(store)

                # Assert
                self.assertEqual(result, expected)
    """

    def _empty_store(self) -> TargetRegistry:
        """Create a fresh TargetRegistry with all targets cleared.

        :return: A new TargetRegistry instance with no registered targets.
        """
        store = TargetRegistry()
        store.clear()
        return store


# =============================================================================
# Shared Test Dataclasses
# =============================================================================


@dataclass
class SimpleModel:
    """Simple test model with a single value."""

    value: int


@dataclass
class NestedInner:
    """Inner nested model for testing nested configs."""

    count: int


@dataclass
class NestedOuter:
    """Outer nested model for testing nested configs."""

    inner: NestedInner


@dataclass
class OptionalFieldsModel:
    """Model with optional fields for testing default values."""

    required: int
    optional: str = "default"


# =============================================================================
# Mock File System
# =============================================================================


class MockFileSystem:
    """A mock file system for testing config composition without real files.

    Use with the `mock_filesystem()` context manager to mock Path operations
    and file loading so tests don't access the real filesystem.

    Files can be added as either:
    - dict: Converted to YAML string for parsing (supports line numbers)
    - str: Used directly as YAML content

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
        self._files: dict[str, str] = {}
        self._base_path = Path(base_path)

    def add_file(
        self, path: str, content: dict[str, Any] | str
    ) -> "MockFileSystem":
        """Add a file to the mock file system.

        :param path: Absolute path to the file (as string).
        :param content: Config dict (converted to YAML) or YAML string.
        :return: Self for method chaining.
        """
        if isinstance(content, dict):
            from ruamel.yaml import YAML

            yaml = YAML()
            yaml.default_flow_style = False
            from io import StringIO

            stream = StringIO()
            yaml.dump(content, stream)
            self._files[Path(path).as_posix()] = stream.getvalue()
        else:
            self._files[Path(path).as_posix()] = content
        return self

    def exists(self, path: str) -> bool:
        """Check if a file exists in the mock file system.

        :param path: Path to check (as string).
        :return: True if the file exists in the mock filesystem.
        """
        return Path(path).as_posix() in self._files

    def get_content(self, path: str) -> str:
        """Get the YAML content of a file.

        :param path: Path to the file (as string).
        :return: YAML string content.
        :raises KeyError: If the file is not found.
        """
        posix_path = Path(path).as_posix()
        if posix_path in self._files:
            return self._files[posix_path]
        raise KeyError(f"Mock file not found: {path}")

    @property
    def base_path(self) -> Path:
        """Return the base path for this mock file system."""
        return self._base_path


@contextmanager
def mock_filesystem(fs: MockFileSystem) -> Generator[None, None, None]:
    """Context manager that mocks file I/O to use a MockFileSystem.

    This patches:
    - `builtins.open` to return mock file contents
    - `Path.exists()` to check the mock filesystem
    - `Path.resolve()` to normalize paths (handles `..` and `.` segments)

    The real YAML parser runs on the mock content, so line numbers and
    other YAML metadata are preserved. The real lru_cache works naturally.

    Example::

        fs = MockFileSystem("/configs")
        fs.add_file("/configs/app.yaml", {"_target_": "App"})

        with mock_filesystem(fs):
            walker = IncrementalComposer(Path("/configs"), ProvenanceBuilder())
            result = walker.compose(Path("/configs/app.yaml"))

    :param fs: The MockFileSystem instance to use.
    """
    import builtins
    import posixpath
    from io import StringIO

    original_open = builtins.open

    def mock_open(file, mode="r", *args, **kwargs):
        path_str = str(file)
        if fs.exists(path_str):
            content = fs.get_content(path_str)
            return StringIO(content)
        # Fall back to real open for non-mocked files
        return original_open(file, mode, *args, **kwargs)

    def mock_exists(path_self: Path) -> bool:
        return fs.exists(str(path_self))

    def mock_resolve(path_self: Path) -> Path:
        # Normalize the path to handle .. and . segments
        # Use as_posix() to ensure consistent forward slashes on all platforms
        posix_str = path_self.as_posix()
        normalized = posixpath.normpath(posix_str)
        return Path(normalized)

    with (
        patch.object(builtins, "open", mock_open),
        patch.object(Path, "exists", mock_exists),
        patch.object(Path, "resolve", mock_resolve),
    ):
        yield
