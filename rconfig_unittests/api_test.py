"""Tests for the module-level API (rconfig.register, rconfig.instantiate, etc.)."""

import tempfile
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from unittest.case import TestCase

import rconfig as rc
from rconfig import (
    ConfigError,
    ConfigFileError,
    ConfigInstantiator,
    ConfigReference,
    ConfigStore,
    ConfigValidator,
    InstantiationError,
    MissingFieldError,
    TargetNotFoundError,
    TypeMismatchError,
    ValidationError,
    ValidationResult,
)


class ModuleLevelAPITests(TestCase):
    def setUp(self):
        # Clear the store before each test
        rc._store._known_references.clear()

    def test_register__TargetClass__AddsToKnownReferences(self):
        # Arrange
        @dataclass
        class Model:
            size: int

        # Act
        rc.register("model", Model)

        # Assert
        refs = rc.known_references()
        self.assertIn("model", refs)
        self.assertIs(refs["model"].target_class, Model)

    def test_unregister__RegisteredName__RemovesReference(self):
        # Arrange
        @dataclass
        class Model:
            size: int

        rc.register("model", Model)

        # Act
        rc.unregister("model")

        # Assert
        refs = rc.known_references()
        self.assertNotIn("model", refs)

    def test_unregister__UnknownName__RaisesKeyError(self):
        # Act & Assert
        with self.assertRaises(KeyError):
            rc.unregister("unknown")

    def test_validate__FilePath__LoadsAndValidates(self):
        # Arrange
        @dataclass
        class Model:
            size: int

        rc.register("model", Model)

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            f.write("_target_: model\nsize: 256\n")
            path = Path(f.name)

        try:
            # Act
            result = rc.validate(path)

            # Assert
            self.assertIsInstance(result, ValidationResult)
            self.assertTrue(result.valid)
        finally:
            path.unlink()

    def test_validate__NonexistentFile__RaisesConfigFileError(self):
        # Act & Assert
        with self.assertRaises(ConfigFileError):
            rc.validate(Path("/nonexistent/config.yaml"))

    def test_instantiate__FilePath__LoadsAndInstantiates(self):
        # Arrange
        @dataclass
        class Model:
            size: int

        rc.register("model", Model)

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            f.write("_target_: model\nsize: 512\n")
            path = Path(f.name)

        try:
            # Act
            result = rc.instantiate(path)

            # Assert
            self.assertIsInstance(result, Model)
            self.assertEqual(result.size, 512)
        finally:
            path.unlink()

    def test_known_references__ReturnsImmutableMapping(self):
        # Arrange
        @dataclass
        class Model:
            size: int

        rc.register("model", Model)

        # Act
        refs = rc.known_references()

        # Assert
        self.assertIsInstance(refs, MappingProxyType)
        with self.assertRaises(TypeError):
            refs["new"] = object()  # type: ignore[index]


class ExportsTests(TestCase):
    def test_exports__AllClassesAccessible(self):
        # Act & Assert
        self.assertTrue(issubclass(ConfigStore, object))
        self.assertTrue(issubclass(ConfigReference, object))
        self.assertTrue(issubclass(ConfigValidator, object))
        self.assertTrue(issubclass(ConfigInstantiator, object))

    def test_exports__AllExceptionsAccessible(self):
        # Act & Assert
        self.assertTrue(issubclass(ConfigError, Exception))
        self.assertTrue(issubclass(ConfigFileError, ConfigError))
        self.assertTrue(issubclass(TargetNotFoundError, ConfigError))
        self.assertTrue(issubclass(ValidationError, ConfigError))
        self.assertTrue(issubclass(MissingFieldError, ValidationError))
        self.assertTrue(issubclass(TypeMismatchError, ValidationError))
        self.assertTrue(issubclass(InstantiationError, ConfigError))


class IntegrationTests(TestCase):
    def setUp(self):
        rc._store._known_references.clear()

    def test_full_workflow__YamlFileToInstance__Works(self):
        # Arrange
        @dataclass
        class ModelConfig:
            hidden_size: int
            dropout: float = 0.1

        @dataclass
        class TrainerConfig:
            model: ModelConfig
            epochs: int

        rc.register("model", ModelConfig)
        rc.register("trainer", TrainerConfig)

        yaml_content = """
_target_: trainer
model:
  _target_: model
  hidden_size: 256
  dropout: 0.2
epochs: 10
"""

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            f.write(yaml_content)
            path = Path(f.name)

        try:
            # Act - Method 1: One-liner
            trainer = rc.instantiate(path)

            # Assert
            self.assertIsInstance(trainer, TrainerConfig)
            self.assertIsInstance(trainer.model, ModelConfig)
            self.assertEqual(trainer.model.hidden_size, 256)
            self.assertEqual(trainer.model.dropout, 0.2)
            self.assertEqual(trainer.epochs, 10)

            # Act - Method 2: Validate first (dry-run), then instantiate
            result = rc.validate(path)

            # Assert
            self.assertTrue(result.valid)

            # Act
            trainer2 = rc.instantiate(path)

            # Assert
            self.assertEqual(trainer2.epochs, 10)

        finally:
            path.unlink()
