from pathlib import Path
from unittest import TestCase
from unittest.mock import MagicMock, patch

from rconfig.composition import clear_cache
from rconfig.errors import ConfigFileError
from rconfig.loaders.base import ConfigFileLoader
from rconfig.loaders.yaml_loader import YamlConfigLoader

from rconfig_unittests.fixtures import MockFileSystem, mock_filesystem


class YamlConfigLoaderTests(TestCase):
    def setUp(self):
        clear_cache()

    def test_YamlConfigLoader__IsConfigFileLoader__InheritsFromBase(self):
        # Act
        loader = YamlConfigLoader()

        # Assert
        self.assertIsInstance(loader, ConfigFileLoader)

    def test_load__ValidYamlFile__ReturnsDict(self):
        # Arrange
        loader = YamlConfigLoader()
        fs = MockFileSystem("/configs")
        fs.add_file(
            "/configs/model.yaml",
            "_target_: my_model\nhidden_size: 256\ndropout: 0.1\n",
        )

        with mock_filesystem(fs):
            # Act
            result = loader.load(Path("/configs/model.yaml"))

            # Assert
            self.assertEqual(result["_target_"], "my_model")
            self.assertEqual(result["hidden_size"], 256)
            self.assertEqual(result["dropout"], 0.1)

    def test_load__NestedYaml__ReturnsNestedDict(self):
        # Arrange
        loader = YamlConfigLoader()
        fs = MockFileSystem("/configs")
        fs.add_file(
            "/configs/trainer.yaml",
            "_target_: trainer\n"
            "model:\n"
            "  _target_: my_model\n"
            "  hidden_size: 256\n"
            "epochs: 10\n",
        )

        with mock_filesystem(fs):
            # Act
            result = loader.load(Path("/configs/trainer.yaml"))

            # Assert
            self.assertEqual(result["_target_"], "trainer")
            self.assertEqual(result["epochs"], 10)
            self.assertIsInstance(result["model"], dict)
            self.assertEqual(result["model"]["_target_"], "my_model")
            self.assertEqual(result["model"]["hidden_size"], 256)

    def test_load__EmptyFile__ReturnsEmptyDict(self):
        # Arrange
        loader = YamlConfigLoader()
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/empty.yaml", "")

        with mock_filesystem(fs):
            # Act
            result = loader.load(Path("/configs/empty.yaml"))

            # Assert
            self.assertEqual(result, {})

    def test_load__FileNotFound__RaisesConfigFileError(self):
        # Arrange
        loader = YamlConfigLoader()
        path = Path("/nonexistent/path/config.yaml")

        # Act & Assert
        with self.assertRaises(ConfigFileError) as context:
            loader.load(path)

        self.assertEqual(context.exception.path, path)
        self.assertIn("not found", context.exception.reason)

    def test_load__InvalidYamlSyntax__RaisesConfigFileError(self):
        # Arrange
        loader = YamlConfigLoader()
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/invalid.yaml", "invalid: yaml: syntax:\n  - broken")

        with mock_filesystem(fs):
            # Act & Assert
            with self.assertRaises(ConfigFileError) as context:
                loader.load(Path("/configs/invalid.yaml"))

            self.assertEqual(context.exception.path, Path("/configs/invalid.yaml"))
            self.assertIn("invalid YAML", context.exception.reason)

    def test_load__NonDictRoot__RaisesConfigFileError(self):
        # Arrange
        loader = YamlConfigLoader()
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/list.yaml", "- item1\n- item2\n")

        with mock_filesystem(fs):
            # Act & Assert
            with self.assertRaises(ConfigFileError) as context:
                loader.load(Path("/configs/list.yaml"))

            self.assertIn("mapping", context.exception.reason)

    def test_load__YamlWithLists__PreservesListValues(self):
        # Arrange
        loader = YamlConfigLoader()
        fs = MockFileSystem("/configs")
        fs.add_file(
            "/configs/model.yaml", "_target_: model\nlayers:\n  - 128\n  - 256\n  - 512\n"
        )

        with mock_filesystem(fs):
            # Act
            result = loader.load(Path("/configs/model.yaml"))

            # Assert
            self.assertEqual(result["layers"], [128, 256, 512])

    def test_load__PermissionDenied__RaisesConfigFileError(self):
        # Arrange
        loader = YamlConfigLoader()
        path = Path("/some/path/config.yaml")

        with patch("builtins.open", side_effect=PermissionError("access denied")):
            # Act & Assert
            with self.assertRaises(ConfigFileError) as context:
                loader.load(path)

            self.assertEqual(context.exception.path, path)
            self.assertIn("permission denied", context.exception.reason)

    def test_load__GenericException__RaisesConfigFileError(self):
        # Arrange
        loader = YamlConfigLoader()
        path = Path("/some/path/config.yaml")

        with patch("builtins.open", side_effect=OSError("disk error")):
            # Act & Assert
            with self.assertRaises(ConfigFileError) as context:
                loader.load(path)

            self.assertEqual(context.exception.path, path)
            self.assertIn("disk error", context.exception.reason)


class YamlConfigLoaderPositionsTests(TestCase):
    """Tests for load_with_positions method."""

    def setUp(self):
        clear_cache()

    def test_load_with_positions__ValidYaml__ReturnsPositionMap(self):
        # Arrange
        from rconfig.loaders.position_map import PositionMap

        loader = YamlConfigLoader()
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/model.yaml", "_target_: model\nlayers: 50\n")

        with mock_filesystem(fs):
            # Act
            result = loader.load_with_positions(Path("/configs/model.yaml"))

            # Assert
            self.assertIsInstance(result, PositionMap)
            self.assertEqual(result["_target_"], "model")
            self.assertEqual(result["layers"], 50)

    def test_load_with_positions__HasLineInfo__CanGetLineNumbers(self):
        # Arrange
        loader = YamlConfigLoader()
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/model.yaml", "_target_: model\nlayers: 50\nlr: 0.001\n")

        with mock_filesystem(fs):
            # Act
            result = loader.load_with_positions(Path("/configs/model.yaml"))

            # Assert - line numbers are 1-indexed in PositionMap
            self.assertEqual(result.get_line("_target_"), 1)
            self.assertEqual(result.get_line("layers"), 2)
            self.assertEqual(result.get_line("lr"), 3)

    def test_load_with_positions__HasColumnInfo__CanGetColumnNumbers(self):
        # Arrange
        loader = YamlConfigLoader()
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/model.yaml", "_target_: model\nlayers: 50\n")

        with mock_filesystem(fs):
            # Act
            result = loader.load_with_positions(Path("/configs/model.yaml"))

            # Assert - column numbers are 1-indexed
            self.assertEqual(result.get_column("_target_"), 1)
            self.assertEqual(result.get_column("layers"), 1)

    def test_load_with_positions__EmptyFile__ReturnsEmptyPositionMap(self):
        # Arrange
        from rconfig.loaders.position_map import PositionMap

        loader = YamlConfigLoader()
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/empty.yaml", "")

        with mock_filesystem(fs):
            # Act
            result = loader.load_with_positions(Path("/configs/empty.yaml"))

            # Assert
            self.assertIsInstance(result, PositionMap)
            self.assertEqual(len(result), 0)

    def test_load_with_positions__FileNotFound__RaisesConfigFileError(self):
        # Arrange
        loader = YamlConfigLoader()
        path = Path("/nonexistent/path/config.yaml")

        # Act & Assert
        with self.assertRaises(ConfigFileError) as context:
            loader.load_with_positions(path)

        self.assertIn("not found", context.exception.reason)

    def test_load_with_positions__InvalidYaml__RaisesConfigFileError(self):
        # Arrange
        loader = YamlConfigLoader()
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/invalid.yaml", "invalid: yaml: syntax")

        with mock_filesystem(fs):
            # Act & Assert
            with self.assertRaises(ConfigFileError) as context:
                loader.load_with_positions(Path("/configs/invalid.yaml"))

            self.assertIn("invalid YAML", context.exception.reason)

    def test_load_with_positions__NonDictRoot__RaisesConfigFileError(self):
        # Arrange
        loader = YamlConfigLoader()
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/list.yaml", "- item1\n- item2\n")

        with mock_filesystem(fs):
            # Act & Assert
            with self.assertRaises(ConfigFileError) as context:
                loader.load_with_positions(Path("/configs/list.yaml"))

            self.assertIn("mapping", context.exception.reason)

    def test_load_with_positions__PermissionDenied__RaisesConfigFileError(self):
        # Arrange
        loader = YamlConfigLoader()
        path = Path("/some/path/config.yaml")

        with patch("builtins.open", side_effect=PermissionError("access denied")):
            # Act & Assert
            with self.assertRaises(ConfigFileError) as context:
                loader.load_with_positions(path)

            self.assertIn("permission denied", context.exception.reason)

    def test_load_with_positions__GenericException__RaisesConfigFileError(self):
        # Arrange
        loader = YamlConfigLoader()
        path = Path("/some/path/config.yaml")

        with patch("builtins.open", side_effect=OSError("disk error")):
            # Act & Assert
            with self.assertRaises(ConfigFileError) as context:
                loader.load_with_positions(path)

            self.assertIn("disk error", context.exception.reason)
