"""Tests for JsonConfigLoader."""

from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from rconfig.composition import clear_cache
from rconfig.errors import ConfigFileError
from rconfig.loaders import JsonConfigLoader
from rconfig.loaders.position_map import PositionMap

from rconfig_unittests.fixtures import MockFileSystem, mock_filesystem


class JsonConfigLoaderTests(TestCase):
    """Tests for JsonConfigLoader class."""

    def setUp(self):
        clear_cache()

    def test_JsonConfigLoader__IsConfigFileLoader__InheritsFromBase(self):
        # Arrange
        from rconfig.loaders.base import ConfigFileLoader

        # Assert
        self.assertTrue(issubclass(JsonConfigLoader, ConfigFileLoader))

    def test_load__ValidJsonFile__ReturnsDict(self):
        # Arrange
        loader = JsonConfigLoader()
        fs = MockFileSystem("/configs")
        fs.add_file(
            "/configs/model.json",
            '{"_target_": "model", "layers": 50}',
        )

        with mock_filesystem(fs):
            # Act
            result = loader.load(Path("/configs/model.json"))

            # Assert
            self.assertEqual(result["_target_"], "model")
            self.assertEqual(result["layers"], 50)

    def test_load__NestedJson__ReturnsNestedDict(self):
        # Arrange
        loader = JsonConfigLoader()
        fs = MockFileSystem("/configs")
        fs.add_file(
            "/configs/model.json",
            '{"model": {"name": "resnet", "layers": 50}, "lr": 0.001}',
        )

        with mock_filesystem(fs):
            # Act
            result = loader.load(Path("/configs/model.json"))

            # Assert
            self.assertEqual(result["model"]["name"], "resnet")
            self.assertEqual(result["model"]["layers"], 50)
            self.assertEqual(result["lr"], 0.001)

    def test_load__JsonWithLists__PreservesListValues(self):
        # Arrange
        loader = JsonConfigLoader()
        fs = MockFileSystem("/configs")
        fs.add_file(
            "/configs/model.json",
            '{"layers": [64, 128, 256], "tags": ["ml", "vision"]}',
        )

        with mock_filesystem(fs):
            # Act
            result = loader.load(Path("/configs/model.json"))

            # Assert
            self.assertEqual(result["layers"], [64, 128, 256])
            self.assertEqual(result["tags"], ["ml", "vision"])

    def test_load__EmptyFile__ReturnsEmptyDict(self):
        # Arrange
        loader = JsonConfigLoader()
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/empty.json", "{}")

        with mock_filesystem(fs):
            # Act
            result = loader.load(Path("/configs/empty.json"))

            # Assert
            self.assertEqual(result, {})

    def test_load__NullContent__ReturnsEmptyDict(self):
        # Arrange
        loader = JsonConfigLoader()
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/null.json", "null")

        with mock_filesystem(fs):
            # Act
            result = loader.load(Path("/configs/null.json"))

            # Assert
            self.assertEqual(result, {})

    def test_load__FileNotFound__RaisesConfigFileError(self):
        # Arrange
        loader = JsonConfigLoader()
        path = Path("/nonexistent/path/config.json")

        # Act & Assert
        with self.assertRaises(ConfigFileError) as context:
            loader.load(path)

        self.assertIn("not found", context.exception.reason)

    def test_load__PermissionDenied__RaisesConfigFileError(self):
        # Arrange
        loader = JsonConfigLoader()
        path = Path("/some/path/config.json")

        with patch("builtins.open", side_effect=PermissionError("access denied")):
            # Act & Assert
            with self.assertRaises(ConfigFileError) as context:
                loader.load(path)

            self.assertIn("permission denied", context.exception.reason)

    def test_load__InvalidJsonSyntax__RaisesConfigFileError(self):
        # Arrange
        loader = JsonConfigLoader()
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/invalid.json", '{"key": invalid}')

        with mock_filesystem(fs):
            # Act & Assert
            with self.assertRaises(ConfigFileError) as context:
                loader.load(Path("/configs/invalid.json"))

            self.assertIn("invalid JSON", context.exception.reason)

    def test_load__NonDictRoot__RaisesConfigFileError(self):
        # Arrange
        loader = JsonConfigLoader()
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/array.json", '["item1", "item2"]')

        with mock_filesystem(fs):
            # Act & Assert
            with self.assertRaises(ConfigFileError) as context:
                loader.load(Path("/configs/array.json"))

            self.assertIn("mapping", context.exception.reason)

    def test_load__GenericException__RaisesConfigFileError(self):
        # Arrange
        loader = JsonConfigLoader()
        path = Path("/some/path/config.json")

        with patch("builtins.open", side_effect=OSError("disk error")):
            # Act & Assert
            with self.assertRaises(ConfigFileError) as context:
                loader.load(path)

            self.assertEqual(context.exception.path, path)
            self.assertIn("disk error", context.exception.reason)


class JsonConfigLoaderPositionsTests(TestCase):
    """Tests for load_with_positions method."""

    def setUp(self):
        clear_cache()

    def test_load_with_positions__ValidJson__ReturnsPositionMap(self):
        # Arrange
        loader = JsonConfigLoader()
        fs = MockFileSystem("/configs")
        fs.add_file(
            "/configs/model.json",
            '{"_target_": "model", "layers": 50}',
        )

        with mock_filesystem(fs):
            # Act
            result = loader.load_with_positions(Path("/configs/model.json"))

            # Assert
            self.assertIsInstance(result, PositionMap)
            self.assertEqual(result["_target_"], "model")
            self.assertEqual(result["layers"], 50)

    def test_load_with_positions__HasLineInfo__CanGetLineNumbers(self):
        # Arrange
        loader = JsonConfigLoader()
        content = """{
    "_target_": "model",
    "layers": 50,
    "lr": 0.001
}"""
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/model.json", content)

        with mock_filesystem(fs):
            # Act
            result = loader.load_with_positions(Path("/configs/model.json"))

            # Assert - line numbers are 1-indexed
            self.assertEqual(result.get_line("_target_"), 2)
            self.assertEqual(result.get_line("layers"), 3)
            self.assertEqual(result.get_line("lr"), 4)

    def test_load_with_positions__HasColumnInfo__CanGetColumnNumbers(self):
        # Arrange
        loader = JsonConfigLoader()
        content = '{"_target_": "model", "layers": 50}'
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/model.json", content)

        with mock_filesystem(fs):
            # Act
            result = loader.load_with_positions(Path("/configs/model.json"))

            # Assert - column numbers are 1-indexed
            self.assertEqual(result.get_column("_target_"), 2)  # After {
            self.assertEqual(result.get_column("layers"), 23)  # After ", "

    def test_load_with_positions__EmptyFile__ReturnsEmptyPositionMap(self):
        # Arrange
        loader = JsonConfigLoader()
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/empty.json", "")

        with mock_filesystem(fs):
            # Act
            result = loader.load_with_positions(Path("/configs/empty.json"))

            # Assert
            self.assertIsInstance(result, PositionMap)
            self.assertEqual(len(result), 0)

    def test_load_with_positions__FileNotFound__RaisesConfigFileError(self):
        # Arrange
        loader = JsonConfigLoader()
        path = Path("/nonexistent/path/config.json")

        # Act & Assert
        with self.assertRaises(ConfigFileError) as context:
            loader.load_with_positions(path)

        self.assertIn("not found", context.exception.reason)

    def test_load_with_positions__InvalidJson__RaisesConfigFileError(self):
        # Arrange
        loader = JsonConfigLoader()
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/invalid.json", '{"key": invalid}')

        with mock_filesystem(fs):
            # Act & Assert
            with self.assertRaises(ConfigFileError) as context:
                loader.load_with_positions(Path("/configs/invalid.json"))

            self.assertIn("invalid JSON", context.exception.reason)

    def test_load_with_positions__NonDictRoot__RaisesConfigFileError(self):
        # Arrange
        loader = JsonConfigLoader()
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/array.json", '["item1", "item2"]')

        with mock_filesystem(fs):
            # Act & Assert
            with self.assertRaises(ConfigFileError) as context:
                loader.load_with_positions(Path("/configs/array.json"))

            self.assertIn("mapping", context.exception.reason)

    def test_load_with_positions__PermissionDenied__RaisesConfigFileError(self):
        # Arrange
        loader = JsonConfigLoader()
        path = Path("/some/path/config.json")

        with patch("builtins.open", side_effect=PermissionError("access denied")):
            # Act & Assert
            with self.assertRaises(ConfigFileError) as context:
                loader.load_with_positions(path)

            self.assertIn("permission denied", context.exception.reason)

    def test_load_with_positions__NestedObjects__TracksAllLevels(self):
        # Arrange
        loader = JsonConfigLoader()
        content = """{
    "model": {
        "name": "resnet",
        "layers": 50
    }
}"""
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/nested.json", content)

        with mock_filesystem(fs):
            # Act
            result = loader.load_with_positions(Path("/configs/nested.json"))

            # Assert
            self.assertEqual(result.get_line("model"), 2)
            # Nested dict should also be a PositionMap
            self.assertIsInstance(result["model"], PositionMap)
            self.assertEqual(result["model"].get_line("name"), 3)
            self.assertEqual(result["model"].get_line("layers"), 4)

    def test_load_with_positions__EscapedQuotesInKey__HandlesCorrectly(self):
        # Arrange
        loader = JsonConfigLoader()
        content = '{"key\\"with\\"quotes": "value"}'
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/escaped.json", content)

        with mock_filesystem(fs):
            # Act
            result = loader.load_with_positions(Path("/configs/escaped.json"))

            # Assert
            self.assertIn('key"with"quotes', result)

    def test_load_with_positions__UnicodeKeys__TracksPosition(self):
        # Arrange
        loader = JsonConfigLoader()
        content = '{"キー": "value", "ключ": "значение"}'
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/unicode.json", content)

        with mock_filesystem(fs):
            # Act
            result = loader.load_with_positions(Path("/configs/unicode.json"))

            # Assert
            self.assertIn("キー", result)
            self.assertIn("ключ", result)
            self.assertIsNotNone(result.get_line("キー"))

    def test_load_with_positions__GenericException__RaisesConfigFileError(self):
        # Arrange
        loader = JsonConfigLoader()
        path = Path("/some/path/config.json")

        with patch("builtins.open", side_effect=OSError("disk error")):
            # Act & Assert
            with self.assertRaises(ConfigFileError) as context:
                loader.load_with_positions(path)

            self.assertEqual(context.exception.path, path)
            self.assertIn("disk error", context.exception.reason)

    def test_load_with_positions__ListWithNestedDicts__ProcessesList(self):
        # Arrange
        loader = JsonConfigLoader()
        content = '{"items": [{"name": "first"}, {"name": "second"}]}'
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/list.json", content)

        with mock_filesystem(fs):
            # Act
            result = loader.load_with_positions(Path("/configs/list.json"))

            # Assert
            self.assertIsInstance(result["items"], list)
            self.assertEqual(len(result["items"]), 2)
            self.assertIsInstance(result["items"][0], PositionMap)
            self.assertEqual(result["items"][0]["name"], "first")
            self.assertEqual(result["items"][1]["name"], "second")

    def test_load_with_positions__NestedListsWithDicts__ProcessesCorrectly(self):
        # Arrange
        loader = JsonConfigLoader()
        content = '{"matrix": [[{"a": 1}], [{"b": 2}]]}'
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/nested_list.json", content)

        with mock_filesystem(fs):
            # Act
            result = loader.load_with_positions(Path("/configs/nested_list.json"))

            # Assert
            self.assertIsInstance(result["matrix"], list)
            self.assertEqual(len(result["matrix"]), 2)
            self.assertIsInstance(result["matrix"][0], list)
            self.assertIsInstance(result["matrix"][0][0], PositionMap)
            self.assertEqual(result["matrix"][0][0]["a"], 1)
            self.assertEqual(result["matrix"][1][0]["b"], 2)

    def test_load_with_positions__ListWithPrimitives__PreservesValues(self):
        # Arrange
        loader = JsonConfigLoader()
        content = '{"numbers": [1, 2, 3], "strings": ["a", "b"]}'
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/primitives.json", content)

        with mock_filesystem(fs):
            # Act
            result = loader.load_with_positions(Path("/configs/primitives.json"))

            # Assert
            self.assertEqual(result["numbers"], [1, 2, 3])
            self.assertEqual(result["strings"], ["a", "b"])

    def test_load_with_positions__KeyPatternInsideStringValue__IgnoresFalsePositive(self):
        # Arrange
        loader = JsonConfigLoader()
        # String value contains a pattern that looks like "key": but isn't an actual key
        content = '{"data": "contains \\"fake\\": pattern", "real": 42}'
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/false_positive.json", content)

        with mock_filesystem(fs):
            # Act
            result = loader.load_with_positions(Path("/configs/false_positive.json"))

            # Assert - "fake" should NOT be tracked as a key
            self.assertIn("data", result)
            self.assertIn("real", result)
            self.assertIsNotNone(result.get_position("data"))
            self.assertIsNotNone(result.get_position("real"))
            # "fake" is not a real key, so it shouldn't have a position
            self.assertNotIn("fake", result)

    def test_load_with_positions__ComplexNestedWithFakeKeys__OnlyTracksRealKeys(self):
        # Arrange
        loader = JsonConfigLoader()
        content = """{
    "config": {
        "description": "Set \\"mode\\": \\"debug\\" in settings",
        "mode": "production"
    }
}"""
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/complex.json", content)

        with mock_filesystem(fs):
            # Act
            result = loader.load_with_positions(Path("/configs/complex.json"))

            # Assert - only real keys should be tracked
            self.assertEqual(result.get_line("config"), 2)
            self.assertIsInstance(result["config"], PositionMap)
            self.assertEqual(result["config"].get_line("description"), 3)
            self.assertEqual(result["config"].get_line("mode"), 4)
