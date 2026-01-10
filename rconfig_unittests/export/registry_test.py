"""Tests for exporter registry."""

from pathlib import Path
from typing import Any
from unittest import TestCase

from rconfig.errors import ConfigFileError
from rconfig.export import (
    Exporter,
    YamlExporter,
    JsonExporter,
    TomlExporter,
    get_exporter,
    register_exporter,
    unregister_exporter,
    supported_exporter_extensions,
)


class _TestExporter(Exporter):
    """Test exporter for .test files."""

    def export(self, config: dict[str, Any]) -> str:
        return f"test_exporter: {config}"


class GetExporterTests(TestCase):
    def test_get_exporter__YamlFile__ReturnsYamlExporter(self):
        # Act
        exporter = get_exporter(Path("config.yaml"))

        # Assert
        self.assertIsInstance(exporter, YamlExporter)

    def test_get_exporter__YmlFile__ReturnsYamlExporter(self):
        # Act
        exporter = get_exporter(Path("config.yml"))

        # Assert
        self.assertIsInstance(exporter, YamlExporter)

    def test_get_exporter__JsonFile__ReturnsJsonExporter(self):
        # Act
        exporter = get_exporter(Path("config.json"))

        # Assert
        self.assertIsInstance(exporter, JsonExporter)

    def test_get_exporter__TomlFile__ReturnsTomlExporter(self):
        # Act
        exporter = get_exporter(Path("config.toml"))

        # Assert
        self.assertIsInstance(exporter, TomlExporter)

    def test_get_exporter__CaseInsensitive__ReturnsExporter(self):
        # Act
        exporter = get_exporter(Path("config.YAML"))

        # Assert
        self.assertIsInstance(exporter, YamlExporter)

    def test_get_exporter__UnsupportedFormat__RaisesConfigFileError(self):
        # Act & Assert
        with self.assertRaises(ConfigFileError) as context:
            get_exporter(Path("config.unknown"))

        self.assertIn("unsupported export format", context.exception.reason)
        self.assertIn(".unknown", context.exception.reason)

    def test_get_exporter__TypoInExtension__SuggestsSimilar(self):
        # Act & Assert
        with self.assertRaises(ConfigFileError) as context:
            get_exporter(Path("config.ymal"))

        self.assertIn("Did you mean", context.exception.reason)


class RegisterExporterTests(TestCase):
    def tearDown(self):
        # Clean up any registered test exporters
        try:
            unregister_exporter(".test")
        except KeyError:
            pass

    def test_register_exporter__ValidExtensions__RegistersSuccessfully(self):
        # Arrange
        test_exporter = _TestExporter()

        # Act
        register_exporter(test_exporter, ".test")

        # Assert
        exporter = get_exporter(Path("config.test"))
        self.assertIsInstance(exporter, _TestExporter)

    def test_register_exporter__MultipleExtensions__RegistersAll(self):
        # Arrange
        test_exporter = _TestExporter()
        register_exporter(test_exporter, ".test", ".tst")

        try:
            # Act & Assert
            exporter1 = get_exporter(Path("config.test"))
            exporter2 = get_exporter(Path("config.tst"))
            self.assertIsInstance(exporter1, _TestExporter)
            self.assertIsInstance(exporter2, _TestExporter)
        finally:
            unregister_exporter(".tst")

    def test_register_exporter__DuplicateExtension__ReplacesExisting(self):
        # Arrange
        class PriorityYamlExporter(Exporter):
            def export(self, config: dict[str, Any]) -> str:
                return "priority"

        priority_exporter = PriorityYamlExporter()

        # Save original exporter
        original_exporter = get_exporter(Path("config.yaml"))

        # Act
        register_exporter(priority_exporter, ".yaml")

        try:
            # Assert - new exporter takes over
            exporter = get_exporter(Path("config.yaml"))
            self.assertIsInstance(exporter, PriorityYamlExporter)
        finally:
            # Restore original
            register_exporter(original_exporter, ".yaml")

    def test_register_exporter__CustomExporter__CanExportNewFormat(self):
        # Arrange
        test_exporter = _TestExporter()
        register_exporter(test_exporter, ".test")

        try:
            # Act
            exporter = get_exporter(Path("config.test"))

            # Assert
            self.assertIsInstance(exporter, _TestExporter)
        finally:
            unregister_exporter(".test")


class UnregisterExporterTests(TestCase):
    def test_unregister_exporter__RegisteredExtension__RemovesExporter(self):
        # Arrange
        test_exporter = _TestExporter()
        register_exporter(test_exporter, ".test")

        # Act
        unregister_exporter(".test")

        # Assert
        with self.assertRaises(ConfigFileError):
            get_exporter(Path("config.test"))

    def test_unregister_exporter__UnknownExtension__RaisesKeyError(self):
        # Act & Assert
        with self.assertRaises(KeyError):
            unregister_exporter(".nonexistent")


class SupportedExporterExtensionsTests(TestCase):
    def test_supported_exporter_extensions__DefaultRegistrations__ReturnsFrozenset(self):
        # Act
        extensions = supported_exporter_extensions()

        # Assert
        self.assertIsInstance(extensions, frozenset)
        self.assertIn(".yaml", extensions)
        self.assertIn(".yml", extensions)
        self.assertIn(".json", extensions)
        self.assertIn(".toml", extensions)

    def test_supported_exporter_extensions__AfterRegister__IncludesNew(self):
        # Arrange
        test_exporter = _TestExporter()
        register_exporter(test_exporter, ".test")

        try:
            # Act
            extensions = supported_exporter_extensions()

            # Assert
            self.assertIn(".test", extensions)
        finally:
            unregister_exporter(".test")
