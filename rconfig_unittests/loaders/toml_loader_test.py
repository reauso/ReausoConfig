"""Tests for TomlConfigLoader."""

from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from rconfig.composition import clear_cache
from rconfig.errors import ConfigFileError
from rconfig.loaders import TomlConfigLoader
from rconfig.loaders.position_map import PositionMap

from rconfig_unittests.fixtures import MockFileSystem, mock_filesystem


class TomlConfigLoaderTests(TestCase):
    """Tests for TomlConfigLoader class."""

    def setUp(self):
        clear_cache()

    def test_TomlConfigLoader__IsConfigFileLoader__InheritsFromBase(self):
        # Arrange
        from rconfig.loaders.base import ConfigFileLoader

        # Assert
        self.assertTrue(issubclass(TomlConfigLoader, ConfigFileLoader))

    def test_load__ValidTomlFile__ReturnsDict(self):
        # Arrange
        loader = TomlConfigLoader()
        fs = MockFileSystem("/configs")
        fs.add_file(
            "/configs/model.toml",
            '_target_ = "model"\nlayers = 50\n',
        )

        with mock_filesystem(fs):
            # Act
            result = loader.load(Path("/configs/model.toml"))

            # Assert
            self.assertEqual(result["_target_"], "model")
            self.assertEqual(result["layers"], 50)

    def test_load__NestedToml__ReturnsNestedDict(self):
        # Arrange
        loader = TomlConfigLoader()
        content = """[model]
name = "resnet"
layers = 50

[training]
lr = 0.001
"""
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/model.toml", content)

        with mock_filesystem(fs):
            # Act
            result = loader.load(Path("/configs/model.toml"))

            # Assert
            self.assertEqual(result["model"]["name"], "resnet")
            self.assertEqual(result["model"]["layers"], 50)
            self.assertEqual(result["training"]["lr"], 0.001)

    def test_load__TomlWithLists__PreservesListValues(self):
        # Arrange
        loader = TomlConfigLoader()
        content = 'layers = [64, 128, 256]\ntags = ["ml", "vision"]\n'
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/model.toml", content)

        with mock_filesystem(fs):
            # Act
            result = loader.load(Path("/configs/model.toml"))

            # Assert
            self.assertEqual(result["layers"], [64, 128, 256])
            self.assertEqual(result["tags"], ["ml", "vision"])

    def test_load__EmptyFile__ReturnsEmptyDict(self):
        # Arrange
        loader = TomlConfigLoader()
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/empty.toml", "")

        with mock_filesystem(fs):
            # Act
            result = loader.load(Path("/configs/empty.toml"))

            # Assert
            self.assertEqual(result, {})

    def test_load__FileNotFound__RaisesConfigFileError(self):
        # Arrange
        loader = TomlConfigLoader()
        path = Path("/nonexistent/path/config.toml")

        # Act & Assert
        with self.assertRaises(ConfigFileError) as context:
            loader.load(path)

        self.assertIn("not found", context.exception.reason)

    def test_load__PermissionDenied__RaisesConfigFileError(self):
        # Arrange
        loader = TomlConfigLoader()
        path = Path("/some/path/config.toml")

        with patch("builtins.open", side_effect=PermissionError("access denied")):
            # Act & Assert
            with self.assertRaises(ConfigFileError) as context:
                loader.load(path)

            self.assertIn("permission denied", context.exception.reason)

    def test_load__InvalidTomlSyntax__RaisesConfigFileError(self):
        # Arrange
        loader = TomlConfigLoader()
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/invalid.toml", "key = [unclosed")

        with mock_filesystem(fs):
            # Act & Assert
            with self.assertRaises(ConfigFileError) as context:
                loader.load(Path("/configs/invalid.toml"))

            self.assertIn("invalid TOML", context.exception.reason)

    def test_load__GenericException__RaisesConfigFileError(self):
        # Arrange
        loader = TomlConfigLoader()
        path = Path("/some/path/config.toml")

        with patch("builtins.open", side_effect=OSError("disk error")):
            # Act & Assert
            with self.assertRaises(ConfigFileError) as context:
                loader.load(path)

            self.assertEqual(context.exception.path, path)
            self.assertIn("disk error", context.exception.reason)


class TomlConfigLoaderPositionsTests(TestCase):
    """Tests for load_with_positions method."""

    def setUp(self):
        clear_cache()

    def test_load_with_positions__ValidToml__ReturnsPositionMap(self):
        # Arrange
        loader = TomlConfigLoader()
        fs = MockFileSystem("/configs")
        fs.add_file(
            "/configs/model.toml",
            '_target_ = "model"\nlayers = 50\n',
        )

        with mock_filesystem(fs):
            # Act
            result = loader.load_with_positions(Path("/configs/model.toml"))

            # Assert
            self.assertIsInstance(result, PositionMap)
            self.assertEqual(result["_target_"], "model")
            self.assertEqual(result["layers"], 50)

    def test_load_with_positions__HasLineInfo__CanGetLineNumbers(self):
        # Arrange
        loader = TomlConfigLoader()
        content = """_target_ = "model"
layers = 50
lr = 0.001
"""
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/model.toml", content)

        with mock_filesystem(fs):
            # Act
            result = loader.load_with_positions(Path("/configs/model.toml"))

            # Assert - line numbers are 1-indexed
            self.assertEqual(result.get_line("_target_"), 1)
            self.assertEqual(result.get_line("layers"), 2)
            self.assertEqual(result.get_line("lr"), 3)

    def test_load_with_positions__HasColumnInfo__CanGetColumnNumbers(self):
        # Arrange
        loader = TomlConfigLoader()
        content = '_target_ = "model"\n  layers = 50\n'
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/model.toml", content)

        with mock_filesystem(fs):
            # Act
            result = loader.load_with_positions(Path("/configs/model.toml"))

            # Assert - column numbers are 1-indexed
            self.assertEqual(result.get_column("_target_"), 1)
            self.assertEqual(result.get_column("layers"), 3)  # After 2 spaces

    def test_load_with_positions__EmptyFile__ReturnsEmptyPositionMap(self):
        # Arrange
        loader = TomlConfigLoader()
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/empty.toml", "")

        with mock_filesystem(fs):
            # Act
            result = loader.load_with_positions(Path("/configs/empty.toml"))

            # Assert
            self.assertIsInstance(result, PositionMap)
            self.assertEqual(len(result), 0)

    def test_load_with_positions__FileNotFound__RaisesConfigFileError(self):
        # Arrange
        loader = TomlConfigLoader()
        path = Path("/nonexistent/path/config.toml")

        # Act & Assert
        with self.assertRaises(ConfigFileError) as context:
            loader.load_with_positions(path)

        self.assertIn("not found", context.exception.reason)

    def test_load_with_positions__InvalidToml__RaisesConfigFileError(self):
        # Arrange
        loader = TomlConfigLoader()
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/invalid.toml", "key = [unclosed")

        with mock_filesystem(fs):
            # Act & Assert
            with self.assertRaises(ConfigFileError) as context:
                loader.load_with_positions(Path("/configs/invalid.toml"))

            self.assertIn("invalid TOML", context.exception.reason)

    def test_load_with_positions__PermissionDenied__RaisesConfigFileError(self):
        # Arrange
        loader = TomlConfigLoader()
        path = Path("/some/path/config.toml")

        with patch("builtins.open", side_effect=PermissionError("access denied")):
            # Act & Assert
            with self.assertRaises(ConfigFileError) as context:
                loader.load_with_positions(path)

            self.assertIn("permission denied", context.exception.reason)

    def test_load_with_positions__TableSection__TracksKeysWithTablePrefix(self):
        # Arrange
        loader = TomlConfigLoader()
        content = """[model]
name = "resnet"
layers = 50
"""
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/nested.toml", content)

        with mock_filesystem(fs):
            # Act
            result = loader.load_with_positions(Path("/configs/nested.toml"))

            # Assert
            self.assertIsInstance(result["model"], PositionMap)
            self.assertEqual(result["model"].get_line("name"), 2)
            self.assertEqual(result["model"].get_line("layers"), 3)

    def test_load_with_positions__NestedTables__BuildsFullPath(self):
        # Arrange
        loader = TomlConfigLoader()
        content = """[model.optimizer]
type = "adam"
lr = 0.001
"""
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/nested.toml", content)

        with mock_filesystem(fs):
            # Act
            result = loader.load_with_positions(Path("/configs/nested.toml"))

            # Assert
            self.assertEqual(result["model"]["optimizer"]["type"], "adam")
            self.assertEqual(result["model"]["optimizer"]["lr"], 0.001)

    def test_load_with_positions__ArrayOfTables__TracksEachEntry(self):
        # Arrange
        loader = TomlConfigLoader()
        content = """[[servers]]
name = "alpha"
ip = "10.0.0.1"

[[servers]]
name = "beta"
ip = "10.0.0.2"
"""
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/array.toml", content)

        with mock_filesystem(fs):
            # Act
            result = loader.load_with_positions(Path("/configs/array.toml"))

            # Assert
            self.assertEqual(len(result["servers"]), 2)
            self.assertEqual(result["servers"][0]["name"], "alpha")
            self.assertEqual(result["servers"][1]["name"], "beta")

    def test_load_with_positions__Comments__IgnoresCommentLines(self):
        # Arrange
        loader = TomlConfigLoader()
        content = """# This is a comment
_target_ = "model"
# Another comment
layers = 50
"""
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/comments.toml", content)

        with mock_filesystem(fs):
            # Act
            result = loader.load_with_positions(Path("/configs/comments.toml"))

            # Assert
            self.assertEqual(result.get_line("_target_"), 2)
            self.assertEqual(result.get_line("layers"), 4)

    def test_load_with_positions__QuotedKeys__HandlesCorrectly(self):
        # Arrange
        loader = TomlConfigLoader()
        content = '"key.with.dots" = "value"\n"spaced key" = 42\n'
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/quoted.toml", content)

        with mock_filesystem(fs):
            # Act
            result = loader.load_with_positions(Path("/configs/quoted.toml"))

            # Assert
            self.assertIn("key.with.dots", result)
            self.assertIn("spaced key", result)

    def test_load_with_positions__UnicodeKeys__TracksPosition(self):
        # Arrange
        loader = TomlConfigLoader()
        # TOML requires non-ASCII keys to be quoted
        content = '"キー" = "value"\n"ключ" = "значение"\n'
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/unicode.toml", content)

        with mock_filesystem(fs):
            # Act
            result = loader.load_with_positions(Path("/configs/unicode.toml"))

            # Assert
            self.assertIn("キー", result)
            self.assertIn("ключ", result)
            self.assertIsNotNone(result.get_line("キー"))

    def test_load_with_positions__InlineTable__TracksPosition(self):
        # Arrange
        loader = TomlConfigLoader()
        content = 'point = { x = 1, y = 2 }\n'
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/inline.toml", content)

        with mock_filesystem(fs):
            # Act
            result = loader.load_with_positions(Path("/configs/inline.toml"))

            # Assert
            self.assertEqual(result["point"]["x"], 1)
            self.assertEqual(result["point"]["y"], 2)

    def test_load_with_positions__InlineTableKeys__TracksInnerKeyPositions(self):
        # Arrange
        loader = TomlConfigLoader()
        content = 'point = { x = 1, y = 2 }\n'
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/inline.toml", content)

        with mock_filesystem(fs):
            # Act
            result = loader.load_with_positions(Path("/configs/inline.toml"))

            # Assert - inner keys should have position tracking
            self.assertIsInstance(result["point"], PositionMap)
            self.assertIsNotNone(result["point"].get_line("x"))
            self.assertIsNotNone(result["point"].get_line("y"))
            # Both should be on line 1
            self.assertEqual(result["point"].get_line("x"), 1)
            self.assertEqual(result["point"].get_line("y"), 1)

    def test_load_with_positions__NestedInlineTable__TracksAllKeys(self):
        # Arrange
        loader = TomlConfigLoader()
        content = 'config = { db = { host = "localhost", port = 5432 } }\n'
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/nested_inline.toml", content)

        with mock_filesystem(fs):
            # Act
            result = loader.load_with_positions(Path("/configs/nested_inline.toml"))

            # Assert
            self.assertEqual(result["config"]["db"]["host"], "localhost")
            self.assertEqual(result["config"]["db"]["port"], 5432)
            # Position tracking for top-level inline table key
            self.assertIsNotNone(result.get_line("config"))

    def test_load_with_positions__GenericException__RaisesConfigFileError(self):
        # Arrange
        loader = TomlConfigLoader()
        path = Path("/some/path/config.toml")

        with patch("builtins.open", side_effect=OSError("disk error")):
            # Act & Assert
            with self.assertRaises(ConfigFileError) as context:
                loader.load_with_positions(path)

            self.assertEqual(context.exception.path, path)
            self.assertIn("disk error", context.exception.reason)

    def test_load_with_positions__ArrayOfTablesWithNestedArrays__ProcessesCorrectly(self):
        # Arrange
        loader = TomlConfigLoader()
        content = """[[products]]
name = "Hammer"
tags = ["tool", "metal"]

[[products]]
name = "Nail"
tags = ["small", "metal"]
"""
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/nested_array.toml", content)

        with mock_filesystem(fs):
            # Act
            result = loader.load_with_positions(Path("/configs/nested_array.toml"))

            # Assert
            self.assertEqual(len(result["products"]), 2)
            self.assertEqual(result["products"][0]["tags"], ["tool", "metal"])
            self.assertEqual(result["products"][1]["tags"], ["small", "metal"])

    def test_load_with_positions__QuotedTablePath__HandlesCorrectly(self):
        # Arrange
        loader = TomlConfigLoader()
        content = """["server.config"]
host = "localhost"
port = 8080
"""
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/quoted_table.toml", content)

        with mock_filesystem(fs):
            # Act
            result = loader.load_with_positions(Path("/configs/quoted_table.toml"))

            # Assert
            self.assertIn("server.config", result)
            self.assertEqual(result["server.config"]["host"], "localhost")
