from pathlib import Path
from typing import Any
from unittest import TestCase

from rconfig.composition import clear_cache
from rconfig.errors import ConfigFileError
from rconfig.loaders import (
    ConfigFileLoader,
    YamlConfigLoader,
    get_loader,
    load_config,
    register_loader,
    unregister_loader,
)

from rconfig_unittests.fixtures import MockFileSystem, mock_filesystem


class _TestLoader(ConfigFileLoader):
    """Test loader for .test files."""

    _SUPPORTED_EXTENSIONS = (".test",)

    def load(self, path: Path) -> dict[str, Any]:
        return {"test_loader": True, "path": str(path)}

    def supports(self, path: Path) -> bool:
        return path.suffix == ".test"


class GetLoaderTests(TestCase):
    def test_get_loader__YamlFile__ReturnsYamlLoader(self):
        # Act
        loader = get_loader(Path("config.yaml"))

        # Assert
        self.assertIsInstance(loader, YamlConfigLoader)

    def test_get_loader__YmlFile__ReturnsYamlLoader(self):
        # Act
        loader = get_loader(Path("config.yml"))

        # Assert
        self.assertIsInstance(loader, YamlConfigLoader)

    def test_get_loader__UnsupportedFormat__RaisesConfigFileError(self):
        # Act & Assert
        with self.assertRaises(ConfigFileError) as context:
            get_loader(Path("config.unknown"))

        self.assertIn("unsupported file format", context.exception.reason)
        self.assertIn(".unknown", context.exception.reason)


class RegisterLoaderTests(TestCase):
    def tearDown(self):
        # Clean up any registered test loaders
        try:
            while True:
                test_loader = get_loader(Path("test.test"))
                unregister_loader(test_loader)
        except (ConfigFileError, ValueError):
            pass

    def test_register_loader__CustomLoader__CanLoadNewFormat(self):
        # Arrange
        test_loader = _TestLoader()
        register_loader(test_loader)

        try:
            # Act
            loader = get_loader(Path("config.test"))

            # Assert
            self.assertIsInstance(loader, _TestLoader)
        finally:
            unregister_loader(test_loader)

    def test_register_loader__TakesPriority__OverExistingLoaders(self):
        # Arrange
        class PriorityYamlLoader(ConfigFileLoader):
            _SUPPORTED_EXTENSIONS = (".yaml",)

            def load(self, path: Path) -> dict[str, Any]:
                return {"priority": True}

            def supports(self, path: Path) -> bool:
                return path.suffix == ".yaml"

        priority_loader = PriorityYamlLoader()
        register_loader(priority_loader)

        try:
            # Act
            loader = get_loader(Path("config.yaml"))

            # Assert
            self.assertIsInstance(loader, PriorityYamlLoader)
        finally:
            unregister_loader(priority_loader)


class UnregisterLoaderTests(TestCase):
    def test_unregister_loader__RegisteredLoader__Removes(self):
        # Arrange
        test_loader = _TestLoader()
        register_loader(test_loader)

        # Act
        unregister_loader(test_loader)

        # Assert
        with self.assertRaises(ConfigFileError):
            get_loader(Path("config.test"))

    def test_unregister_loader__NotRegistered__RaisesValueError(self):
        # Arrange
        test_loader = _TestLoader()

        # Act & Assert
        with self.assertRaises(ValueError):
            unregister_loader(test_loader)


class LoadConfigTests(TestCase):
    def setUp(self):
        clear_cache()

    def test_load_config__ValidYamlFile__ReturnsDict(self):
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/model.yaml", "_target_: my_model\nvalue: 42\n")

        with mock_filesystem(fs):
            # Act
            result = load_config(Path("/configs/model.yaml"))

            # Assert
            self.assertEqual(result["_target_"], "my_model")
            self.assertEqual(result["value"], 42)

    def test_load_config__UnsupportedFormat__RaisesConfigFileError(self):
        # Act & Assert
        with self.assertRaises(ConfigFileError) as context:
            load_config(Path("config.unknown"))

        self.assertIn("unsupported", context.exception.reason)

    def test_load_config__FileNotFound__RaisesConfigFileError(self):
        # Act & Assert
        with self.assertRaises(ConfigFileError) as context:
            load_config(Path("/nonexistent/config.yaml"))

        self.assertIn("not found", context.exception.reason)

    def test_load_config__CustomLoader__UsesRegisteredLoader(self):
        # Arrange
        test_loader = _TestLoader()
        register_loader(test_loader)

        fs = MockFileSystem("/configs")
        fs.add_file("/configs/test.test", "dummy content")

        try:
            with mock_filesystem(fs):
                # Act
                result = load_config(Path("/configs/test.test"))

                # Assert
                self.assertTrue(result["test_loader"])
                self.assertEqual(Path(result["path"]).as_posix(), "/configs/test.test")
        finally:
            unregister_loader(test_loader)
