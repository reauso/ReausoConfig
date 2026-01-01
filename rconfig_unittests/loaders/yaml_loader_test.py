import tempfile
from pathlib import Path
from unittest.case import TestCase
from unittest.mock import MagicMock, patch

from rconfig.errors import ConfigFileError
from rconfig.loaders.base import ConfigFileLoader
from rconfig.loaders.yaml_loader import YamlConfigLoader


class YamlConfigLoaderTests(TestCase):
    def test_YamlConfigLoader__IsConfigFileLoader__InheritsFromBase(self):
        # Act
        loader = YamlConfigLoader()

        # Assert
        self.assertIsInstance(loader, ConfigFileLoader)

    def test_supports__YamlExtension__ReturnsTrue(self):
        # Arrange
        loader = YamlConfigLoader()

        # Act & Assert
        self.assertTrue(loader.supports(Path("config.yaml")))
        self.assertTrue(loader.supports(Path("config.yml")))
        self.assertTrue(loader.supports(Path("/path/to/config.YAML")))
        self.assertTrue(loader.supports(Path("/path/to/config.YML")))

    def test_supports__NonYamlExtension__ReturnsFalse(self):
        # Arrange
        loader = YamlConfigLoader()

        # Act & Assert
        self.assertFalse(loader.supports(Path("config.json")))
        self.assertFalse(loader.supports(Path("config.toml")))
        self.assertFalse(loader.supports(Path("config.txt")))
        self.assertFalse(loader.supports(Path("config")))

    def test_load__ValidYamlFile__ReturnsDict(self):
        # Arrange
        loader = YamlConfigLoader()

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            f.write("_target_: my_model\nhidden_size: 256\ndropout: 0.1\n")
            path = Path(f.name)

        try:
            # Act
            result = loader.load(path)

            # Assert
            self.assertEqual(result["_target_"], "my_model")
            self.assertEqual(result["hidden_size"], 256)
            self.assertEqual(result["dropout"], 0.1)
        finally:
            path.unlink()

    def test_load__NestedYaml__ReturnsNestedDict(self):
        # Arrange
        loader = YamlConfigLoader()

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            f.write(
                "_target_: trainer\n"
                "model:\n"
                "  _target_: my_model\n"
                "  hidden_size: 256\n"
                "epochs: 10\n"
            )
            path = Path(f.name)

        try:
            # Act
            result = loader.load(path)

            # Assert
            self.assertEqual(result["_target_"], "trainer")
            self.assertEqual(result["epochs"], 10)
            self.assertIsInstance(result["model"], dict)
            self.assertEqual(result["model"]["_target_"], "my_model")
            self.assertEqual(result["model"]["hidden_size"], 256)
        finally:
            path.unlink()

    def test_load__EmptyFile__ReturnsEmptyDict(self):
        # Arrange
        loader = YamlConfigLoader()

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            f.write("")
            path = Path(f.name)

        try:
            # Act
            result = loader.load(path)

            # Assert
            self.assertEqual(result, {})
        finally:
            path.unlink()

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

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            f.write("invalid: yaml: syntax:\n  - broken")
            path = Path(f.name)

        try:
            # Act & Assert
            with self.assertRaises(ConfigFileError) as context:
                loader.load(path)

            self.assertEqual(context.exception.path, path)
            self.assertIn("invalid YAML", context.exception.reason)
        finally:
            path.unlink()

    def test_load__NonDictRoot__RaisesConfigFileError(self):
        # Arrange
        loader = YamlConfigLoader()

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            f.write("- item1\n- item2\n")
            path = Path(f.name)

        try:
            # Act & Assert
            with self.assertRaises(ConfigFileError) as context:
                loader.load(path)

            self.assertIn("mapping", context.exception.reason)
        finally:
            path.unlink()

    def test_load__YamlWithLists__PreservesListValues(self):
        # Arrange
        loader = YamlConfigLoader()

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            f.write("_target_: model\nlayers:\n  - 128\n  - 256\n  - 512\n")
            path = Path(f.name)

        try:
            # Act
            result = loader.load(path)

            # Assert
            self.assertEqual(result["layers"], [128, 256, 512])
        finally:
            path.unlink()

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

    def test_load_with_positions__ValidYaml__ReturnsCommentedMap(self):
        # Arrange
        from ruamel.yaml.comments import CommentedMap

        loader = YamlConfigLoader()

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            f.write("_target_: model\nlayers: 50\n")
            path = Path(f.name)

        try:
            # Act
            result = loader.load_with_positions(path)

            # Assert
            self.assertIsInstance(result, CommentedMap)
            self.assertEqual(result["_target_"], "model")
            self.assertEqual(result["layers"], 50)
        finally:
            path.unlink()

    def test_load_with_positions__HasLineInfo__CanGetLineNumbers(self):
        # Arrange
        loader = YamlConfigLoader()

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            f.write("_target_: model\nlayers: 50\nlr: 0.001\n")
            path = Path(f.name)

        try:
            # Act
            result = loader.load_with_positions(path)

            # Assert - line numbers are 0-indexed
            line, _ = result.lc.key("_target_")
            self.assertEqual(line, 0)

            line, _ = result.lc.key("layers")
            self.assertEqual(line, 1)

            line, _ = result.lc.key("lr")
            self.assertEqual(line, 2)
        finally:
            path.unlink()

    def test_load_with_positions__EmptyFile__ReturnsEmptyCommentedMap(self):
        # Arrange
        from ruamel.yaml.comments import CommentedMap

        loader = YamlConfigLoader()

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            f.write("")
            path = Path(f.name)

        try:
            # Act
            result = loader.load_with_positions(path)

            # Assert
            self.assertIsInstance(result, CommentedMap)
            self.assertEqual(len(result), 0)
        finally:
            path.unlink()

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

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            f.write("invalid: yaml: syntax")
            path = Path(f.name)

        try:
            # Act & Assert
            with self.assertRaises(ConfigFileError) as context:
                loader.load_with_positions(path)

            self.assertIn("invalid YAML", context.exception.reason)
        finally:
            path.unlink()

    def test_load_with_positions__NonDictRoot__RaisesConfigFileError(self):
        # Arrange
        loader = YamlConfigLoader()

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            f.write("- item1\n- item2\n")
            path = Path(f.name)

        try:
            # Act & Assert
            with self.assertRaises(ConfigFileError) as context:
                loader.load_with_positions(path)

            self.assertIn("mapping", context.exception.reason)
        finally:
            path.unlink()

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
