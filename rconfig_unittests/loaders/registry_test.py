from pathlib import Path
from typing import Any
from unittest import TestCase

from rconfig.composition import clear_cache
from rconfig.errors import ConfigFileError
from rconfig.loaders import (
    ConfigFileLoader,
    PositionMap,
    YamlConfigLoader,
    get_loader,
    load_config,
    register_loader,
    supported_loader_extensions,
    unregister_loader,
)

from rconfig_unittests.fixtures import MockFileSystem, mock_filesystem


class _TestLoader(ConfigFileLoader):
    """Test loader for .test files."""

    def load(self, path: Path) -> dict[str, Any]:
        return {"test_loader": True, "path": str(path)}

    def load_with_positions(self, path: Path) -> PositionMap:
        result = PositionMap({"test_loader": True, "path": str(path)})
        result.set_position("test_loader", 1, 1)
        result.set_position("path", 2, 1)
        return result


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

    def test_get_loader__CaseInsensitive__ReturnsLoader(self):
        # Act
        loader = get_loader(Path("config.YAML"))

        # Assert
        self.assertIsInstance(loader, YamlConfigLoader)

    def test_get_loader__UnsupportedFormat__RaisesConfigFileError(self):
        # Act & Assert
        with self.assertRaises(ConfigFileError) as context:
            get_loader(Path("config.unknown"))

        self.assertIn("unsupported file format", context.exception.reason)
        self.assertIn(".unknown", context.exception.reason)

    def test_get_loader__TypoInExtension__SuggestsSimilar(self):
        # Act & Assert
        with self.assertRaises(ConfigFileError) as context:
            get_loader(Path("config.ymal"))

        self.assertIn("Did you mean", context.exception.reason)


class RegisterLoaderTests(TestCase):
    def tearDown(self):
        # Clean up any registered test loaders
        try:
            unregister_loader(".test")
        except KeyError:
            pass

    def test_register_loader__ValidExtensions__RegistersSuccessfully(self):
        # Arrange
        test_loader = _TestLoader()

        # Act
        register_loader(test_loader, ".test")

        # Assert
        loader = get_loader(Path("config.test"))
        self.assertIsInstance(loader, _TestLoader)

    def test_register_loader__MultipleExtensions__RegistersAll(self):
        # Arrange
        test_loader = _TestLoader()
        register_loader(test_loader, ".test", ".tst")

        try:
            # Act & Assert
            loader1 = get_loader(Path("config.test"))
            loader2 = get_loader(Path("config.tst"))
            self.assertIsInstance(loader1, _TestLoader)
            self.assertIsInstance(loader2, _TestLoader)
        finally:
            unregister_loader(".tst")

    def test_register_loader__DuplicateExtension__ReplacesExisting(self):
        # Arrange
        class PriorityYamlLoader(ConfigFileLoader):
            def load(self, path: Path) -> dict[str, Any]:
                return {"priority": True}

            def load_with_positions(self, path: Path) -> PositionMap:
                return PositionMap({"priority": True})

        priority_loader = PriorityYamlLoader()

        # Save original loader
        original_loader = get_loader(Path("config.yaml"))

        # Act
        register_loader(priority_loader, ".yaml")

        try:
            # Assert - new loader takes over
            loader = get_loader(Path("config.yaml"))
            self.assertIsInstance(loader, PriorityYamlLoader)
        finally:
            # Restore original
            register_loader(original_loader, ".yaml")

    def test_register_loader__CustomLoader__CanLoadNewFormat(self):
        # Arrange
        test_loader = _TestLoader()
        register_loader(test_loader, ".test")

        try:
            # Act
            loader = get_loader(Path("config.test"))

            # Assert
            self.assertIsInstance(loader, _TestLoader)
        finally:
            unregister_loader(".test")


class UnregisterLoaderTests(TestCase):
    def test_unregister_loader__RegisteredExtension__RemovesLoader(self):
        # Arrange
        test_loader = _TestLoader()
        register_loader(test_loader, ".test")

        # Act
        unregister_loader(".test")

        # Assert
        with self.assertRaises(ConfigFileError):
            get_loader(Path("config.test"))

    def test_unregister_loader__UnknownExtension__RaisesKeyError(self):
        # Act & Assert
        with self.assertRaises(KeyError):
            unregister_loader(".nonexistent")


class SupportedLoaderExtensionsTests(TestCase):
    def test_supported_loader_extensions__DefaultRegistrations__ReturnsFrozenset(self):
        # Act
        extensions = supported_loader_extensions()

        # Assert
        self.assertIsInstance(extensions, frozenset)
        self.assertIn(".yaml", extensions)
        self.assertIn(".yml", extensions)
        self.assertIn(".json", extensions)
        self.assertIn(".toml", extensions)

    def test_supported_loader_extensions__AfterRegister__IncludesNew(self):
        # Arrange
        test_loader = _TestLoader()
        register_loader(test_loader, ".test")

        try:
            # Act
            extensions = supported_loader_extensions()

            # Assert
            self.assertIn(".test", extensions)
        finally:
            unregister_loader(".test")


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
        register_loader(test_loader, ".test")

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
            unregister_loader(".test")
