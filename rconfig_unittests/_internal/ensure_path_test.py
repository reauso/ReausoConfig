"""Tests for ensure_path() conversion helper.

Tests the StrOrPath type alias and ensure_path function that
converts string/PathLike inputs to Path objects.
"""

import os
import unittest
from pathlib import Path, PurePosixPath, PureWindowsPath

from rconfig._internal.path_utils import StrOrPath, ensure_path


class EnsurePathTests(unittest.TestCase):
    """Tests for ensure_path() conversion helper."""

    def test_ensure_path__StringInput__ReturnsPath(self):
        """Test that string input is converted to Path."""
        # Arrange
        path_str = "config.yaml"

        # Act
        result = ensure_path(path_str)

        # Assert
        self.assertIsInstance(result, Path)
        self.assertEqual(str(result), path_str)

    def test_ensure_path__PathInput__ReturnsSamePath(self):
        """Test that Path input is returned unchanged (same object)."""
        # Arrange
        path = Path("config.yaml")

        # Act
        result = ensure_path(path)

        # Assert
        self.assertIs(result, path)

    def test_ensure_path__StringWithSubdirectory__ReturnsPath(self):
        """Test that string path with subdirectories is converted correctly."""
        # Arrange
        path_str = "configs/models/resnet.yaml"

        # Act
        result = ensure_path(path_str)

        # Assert
        self.assertIsInstance(result, Path)
        # Use Path comparison to handle platform-specific separators
        self.assertEqual(result, Path("configs/models/resnet.yaml"))

    def test_ensure_path__AbsoluteStringPath__ReturnsAbsolutePath(self):
        """Test that absolute string path is converted correctly."""
        # Arrange
        if os.name == "nt":
            path_str = "C:\\configs\\config.yaml"
        else:
            path_str = "/home/user/configs/config.yaml"

        # Act
        result = ensure_path(path_str)

        # Assert
        self.assertIsInstance(result, Path)
        self.assertTrue(result.is_absolute())

    def test_ensure_path__PurePosixPath__ReturnsPath(self):
        """Test that PurePosixPath input is converted to Path."""
        # Arrange
        pure_path = PurePosixPath("config.yaml")

        # Act
        result = ensure_path(pure_path)

        # Assert
        self.assertIsInstance(result, Path)
        self.assertEqual(result.name, "config.yaml")

    def test_ensure_path__PureWindowsPath__ReturnsPath(self):
        """Test that PureWindowsPath input is converted to Path."""
        # Arrange
        pure_path = PureWindowsPath("configs\\config.yaml")

        # Act
        result = ensure_path(pure_path)

        # Assert
        self.assertIsInstance(result, Path)

    def test_ensure_path__CustomPathLike__ReturnsPath(self):
        """Test that custom PathLike object is converted to Path."""
        # Arrange
        class CustomPath:
            def __fspath__(self) -> str:
                return "custom/config.yaml"

        custom = CustomPath()

        # Act
        result = ensure_path(custom)

        # Assert
        self.assertIsInstance(result, Path)
        # Use Path comparison to handle platform-specific separators
        self.assertEqual(result, Path("custom/config.yaml"))

    def test_ensure_path__EmptyString__ReturnsEmptyPath(self):
        """Test that empty string returns Path with empty name."""
        # Arrange
        path_str = ""

        # Act
        result = ensure_path(path_str)

        # Assert
        self.assertIsInstance(result, Path)
        self.assertEqual(str(result), ".")

    def test_ensure_path__PathWithExtension__PreservesExtension(self):
        """Test that file extension is preserved after conversion."""
        # Arrange
        path_str = "config.yaml"

        # Act
        result = ensure_path(path_str)

        # Assert
        self.assertEqual(result.suffix, ".yaml")

    def test_ensure_path__PathPreservesSuffix__ForJsonFile(self):
        """Test that .json extension is preserved."""
        # Arrange
        path_str = "config.json"

        # Act
        result = ensure_path(path_str)

        # Assert
        self.assertEqual(result.suffix, ".json")

    def test_ensure_path__PathPreservesSuffix__ForTomlFile(self):
        """Test that .toml extension is preserved."""
        # Arrange
        path_str = "config.toml"

        # Act
        result = ensure_path(path_str)

        # Assert
        self.assertEqual(result.suffix, ".toml")


class StrOrPathTypeAliasTests(unittest.TestCase):
    """Tests verifying StrOrPath type alias behavior."""

    def test_StrOrPath__AcceptsString__TypeCheckPasses(self):
        """Test that StrOrPath type hint accepts string at runtime."""
        # Arrange
        def accept_path(path: StrOrPath) -> Path:
            return ensure_path(path)

        # Act
        result = accept_path("config.yaml")

        # Assert
        self.assertIsInstance(result, Path)

    def test_StrOrPath__AcceptsPath__TypeCheckPasses(self):
        """Test that StrOrPath type hint accepts Path at runtime."""
        # Arrange
        def accept_path(path: StrOrPath) -> Path:
            return ensure_path(path)

        # Act
        result = accept_path(Path("config.yaml"))

        # Assert
        self.assertIsInstance(result, Path)

    def test_StrOrPath__AcceptsPathLike__TypeCheckPasses(self):
        """Test that StrOrPath type hint accepts os.PathLike at runtime."""
        # Arrange
        class MyPathLike:
            def __fspath__(self) -> str:
                return "my/path.yaml"

        def accept_path(path: StrOrPath) -> Path:
            return ensure_path(path)

        # Act
        result = accept_path(MyPathLike())

        # Assert
        self.assertIsInstance(result, Path)


if __name__ == "__main__":
    unittest.main()
