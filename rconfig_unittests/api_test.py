"""Tests for the module-level API (rconfig.register, rconfig.instantiate, etc.)."""

import tempfile
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from unittest import TestCase

import rconfig as rc
from rconfig import (
    ConfigError,
    ConfigFileError,
    ConfigInstantiator,
    ConfigReference,
    ConfigStore,
    ConfigValidator,
    InstantiationError,
    InvalidOverridePathError,
    InvalidOverrideSyntaxError,
    MissingFieldError,
    Override,
    OverrideError,
    TargetNotFoundError,
    TypeMismatchError,
    ValidationError,
    ValidationResult,
)


class ModuleLevelAPITests(TestCase):
    def setUp(self):
        # Clear the store before each test
        rc._store.clear()

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
            result = rc.instantiate(path, cli_overrides=False)

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
        self.assertTrue(issubclass(OverrideError, ConfigError))
        self.assertTrue(issubclass(InvalidOverridePathError, OverrideError))
        self.assertTrue(issubclass(InvalidOverrideSyntaxError, OverrideError))

    def test_exports__OverrideClassAccessible(self):
        # Act - Create an instance to verify class is properly exported
        override = Override(path=["test"], value=1, operation="set")

        # Assert
        self.assertEqual(override.path, ["test"])
        self.assertEqual(override.value, 1)
        self.assertEqual(override.operation, "set")


class IntegrationTests(TestCase):
    def setUp(self):
        rc._store.clear()

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
            trainer = rc.instantiate(path, cli_overrides=False)

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
            trainer2 = rc.instantiate(path, cli_overrides=False)

            # Assert
            self.assertEqual(trainer2.epochs, 10)

        finally:
            path.unlink()


class InstantiateWithOverridesTests(TestCase):
    def setUp(self):
        rc._store.clear()

    def test_instantiate__WithDictOverrides__AppliesOverrides(self):
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
            result = rc.instantiate(
                path, overrides={"size": 512}, cli_overrides=False
            )

            # Assert
            self.assertEqual(result.size, 512)
        finally:
            path.unlink()

    def test_instantiate__WithCliOverridesFalse__IgnoresSysArgv(self):
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
            # Act - sys.argv may contain test runner args, but they should be ignored
            result = rc.instantiate(path, cli_overrides=False)

            # Assert - should use config value, not any CLI args
            self.assertEqual(result.size, 256)
        finally:
            path.unlink()

    def test_instantiate__WithNestedOverride__AppliesNestedValue(self):
        # Arrange
        @dataclass
        class ModelConfig:
            hidden_size: int

        @dataclass
        class TrainerConfig:
            model: ModelConfig
            epochs: int

        rc.register("model", ModelConfig)
        rc.register("trainer", TrainerConfig)

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            f.write("_target_: trainer\nmodel:\n  _target_: model\n  hidden_size: 256\nepochs: 10\n")
            path = Path(f.name)

        try:
            # Act
            result = rc.instantiate(
                path,
                overrides={"model.hidden_size": 1024},
                cli_overrides=False,
            )

            # Assert
            self.assertEqual(result.model.hidden_size, 1024)
            self.assertEqual(result.epochs, 10)
        finally:
            path.unlink()

    def test_instantiate__WithInvalidPath__RaisesInvalidOverridePathError(self):
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
            # Act & Assert
            with self.assertRaises(InvalidOverridePathError):
                rc.instantiate(
                    path,
                    overrides={"nonexistent": 123},
                    cli_overrides=False,
                )
        finally:
            path.unlink()

    def test_instantiate__WithTypeCoercion__ConvertsStringValue(self):
        # Arrange
        @dataclass
        class Model:
            lr: float

        rc.register("model", Model)

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            f.write("_target_: model\nlr: 0.1\n")
            path = Path(f.name)

        try:
            # Act - pass string value that should be coerced to float
            result = rc.instantiate(
                path,
                overrides={"lr": "0.01"},
                cli_overrides=False,
            )

            # Assert
            self.assertEqual(result.lr, 0.01)
            self.assertIsInstance(result.lr, float)
        finally:
            path.unlink()


class ApiCliOverridesTests(TestCase):
    """Tests for CLI overrides in the API to improve coverage."""

    def setUp(self):
        # Clear the store before each test
        rc._store.clear()

    def test_instantiate__WithCliOverrides__AppliesOverrides(self):
        """Test instantiate with cli_overrides=True reads from sys.argv."""
        # Arrange - line 208
        import sys
        from unittest.mock import patch

        @dataclass
        class Model:
            lr: float
            epochs: int

        rc.register("model", Model)

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            f.write("_target_: model\nlr: 0.1\nepochs: 10\n")
            path = Path(f.name)

        try:
            # Mock sys.argv to include overrides
            with patch.object(sys, "argv", ["script.py", "lr=0.001", "epochs=100"]):
                # Act
                result = rc.instantiate(path, cli_overrides=True)

                # Assert - CLI overrides should be applied
                self.assertEqual(result.lr, 0.001)
                self.assertEqual(result.epochs, 100)
        finally:
            path.unlink()

    def test_instantiate__WithCliOverridesDisabled__IgnoresArgv(self):
        """Test instantiate with cli_overrides=False ignores sys.argv."""
        import sys
        from unittest.mock import patch

        @dataclass
        class Model:
            lr: float

        rc.register("model", Model)

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            f.write("_target_: model\nlr: 0.1\n")
            path = Path(f.name)

        try:
            # Mock sys.argv with overrides
            with patch.object(sys, "argv", ["script.py", "lr=999"]):
                # Act - cli_overrides=False should ignore sys.argv
                result = rc.instantiate(path, cli_overrides=False)

                # Assert - original value should be used
                self.assertEqual(result.lr, 0.1)
        finally:
            path.unlink()


class PartialInstantiationTests(TestCase):
    """Tests for partial instantiation with inner_path parameter."""

    def setUp(self):
        rc._store.clear()

    def test_instantiate__InnerPath__ReturnsSubConfig(self):
        """Test basic partial instantiation returns nested object."""

        @dataclass
        class Encoder:
            hidden_size: int

        @dataclass
        class Model:
            encoder: Encoder
            name: str

        @dataclass
        class Trainer:
            model: Model
            epochs: int

        rc.register("encoder", Encoder)
        rc.register("model", Model)
        rc.register("trainer", Trainer)

        yaml_content = """
_target_: trainer
model:
  _target_: model
  encoder:
    _target_: encoder
    hidden_size: 256
  name: gpt
epochs: 10
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            f.write(yaml_content)
            path = Path(f.name)

        try:
            # Act - instantiate only the model section
            result = rc.instantiate(path, inner_path="model", cli_overrides=False)

            # Assert
            self.assertIsInstance(result, Model)
            self.assertIsInstance(result.encoder, Encoder)
            self.assertEqual(result.encoder.hidden_size, 256)
            self.assertEqual(result.name, "gpt")
        finally:
            path.unlink()

    def test_instantiate__InnerPathNested__ReturnsDeepConfig(self):
        """Test partial instantiation with nested path like 'model.encoder'."""

        @dataclass
        class Encoder:
            layers: int

        @dataclass
        class Model:
            encoder: Encoder

        @dataclass
        class Trainer:
            model: Model

        rc.register("encoder", Encoder)
        rc.register("model", Model)
        rc.register("trainer", Trainer)

        yaml_content = """
_target_: trainer
model:
  _target_: model
  encoder:
    _target_: encoder
    layers: 6
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            f.write(yaml_content)
            path = Path(f.name)

        try:
            # Act - instantiate only the encoder
            result = rc.instantiate(
                path, inner_path="model.encoder", cli_overrides=False
            )

            # Assert
            self.assertIsInstance(result, Encoder)
            self.assertEqual(result.layers, 6)
        finally:
            path.unlink()

    def test_instantiate__InnerPathWithListIndex__ReturnsElement(self):
        """Test partial instantiation with list index path."""

        @dataclass
        class Callback:
            name: str

        @dataclass
        class Trainer:
            callbacks: list

        rc.register("callback", Callback)
        rc.register("trainer", Trainer)

        yaml_content = """
_target_: trainer
callbacks:
  - _target_: callback
    name: first
  - _target_: callback
    name: second
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            f.write(yaml_content)
            path = Path(f.name)

        try:
            # Act - instantiate first callback
            result = rc.instantiate(
                path, inner_path="callbacks[1]", cli_overrides=False
            )

            # Assert
            self.assertIsInstance(result, Callback)
            self.assertEqual(result.name, "second")
        finally:
            path.unlink()

    def test_instantiate__InnerPathWithInterpolation__ResolvesFromFullConfig(self):
        """Test interpolations resolve from full config before extraction."""

        @dataclass
        class Model:
            lr: float

        @dataclass
        class Trainer:
            defaults: dict
            model: Model

        rc.register("model", Model)
        rc.register("trainer", Trainer)

        yaml_content = """
_target_: trainer
defaults:
  learning_rate: 0.01
model:
  _target_: model
  lr: ${/defaults.learning_rate}
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            f.write(yaml_content)
            path = Path(f.name)

        try:
            # Act - instantiate only the model
            result = rc.instantiate(path, inner_path="model", cli_overrides=False)

            # Assert - interpolation should have resolved from full config
            self.assertIsInstance(result, Model)
            self.assertEqual(result.lr, 0.01)
        finally:
            path.unlink()

    def test_instantiate__InnerPathWithOverrides__AppliesOverridesFirst(self):
        """Test overrides are applied to full config before extraction."""

        @dataclass
        class Model:
            size: int

        @dataclass
        class Trainer:
            model: Model

        rc.register("model", Model)
        rc.register("trainer", Trainer)

        yaml_content = """
_target_: trainer
model:
  _target_: model
  size: 256
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            f.write(yaml_content)
            path = Path(f.name)

        try:
            # Act - override the model size, then extract model
            result = rc.instantiate(
                path,
                inner_path="model",
                overrides={"model.size": 512},
                cli_overrides=False,
            )

            # Assert
            self.assertEqual(result.size, 512)
        finally:
            path.unlink()

    def test_instantiate__InvalidInnerPath__RaisesInvalidInnerPathError(self):
        """Test that invalid inner_path raises InvalidInnerPathError."""

        @dataclass
        class Model:
            size: int

        rc.register("model", Model)

        yaml_content = "_target_: model\nsize: 256\n"
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            f.write(yaml_content)
            path = Path(f.name)

        try:
            with self.assertRaises(rc.InvalidInnerPathError):
                rc.instantiate(path, inner_path="nonexistent", cli_overrides=False)
        finally:
            path.unlink()

    def test_instantiate__InnerPathToScalar__RaisesInvalidInnerPathError(self):
        """Test that path to non-dict raises InvalidInnerPathError."""

        @dataclass
        class Model:
            size: int

        rc.register("model", Model)

        yaml_content = "_target_: model\nsize: 256\n"
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            f.write(yaml_content)
            path = Path(f.name)

        try:
            with self.assertRaises(rc.InvalidInnerPathError):
                rc.instantiate(path, inner_path="size", cli_overrides=False)
        finally:
            path.unlink()

    def test_instantiate__InnerPathNone__FullInstantiation(self):
        """Test that inner_path=None gives normal full instantiation."""

        @dataclass
        class Model:
            size: int

        rc.register("model", Model)

        yaml_content = "_target_: model\nsize: 256\n"
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            f.write(yaml_content)
            path = Path(f.name)

        try:
            # Act - inner_path=None (default)
            result = rc.instantiate(path, inner_path=None, cli_overrides=False)

            # Assert - full instantiation
            self.assertIsInstance(result, Model)
            self.assertEqual(result.size, 256)
        finally:
            path.unlink()

    def test_instantiate__InnerPathWithExpectedType__ReturnsTypedResult(self):
        """Test that expected_type works with inner_path."""

        @dataclass
        class Encoder:
            dim: int

        @dataclass
        class Model:
            encoder: Encoder

        rc.register("encoder", Encoder)
        rc.register("model", Model)

        yaml_content = """
_target_: model
encoder:
  _target_: encoder
  dim: 512
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            f.write(yaml_content)
            path = Path(f.name)

        try:
            # Act - use expected_type with inner_path
            result = rc.instantiate(
                path, Encoder, inner_path="encoder", cli_overrides=False
            )

            # Assert
            self.assertIsInstance(result, Encoder)
            self.assertEqual(result.dim, 512)
        finally:
            path.unlink()

    def test_instantiate__InnerPathWithExternalInstance__InstantiatesTarget(self):
        """Test _instance_ refs to targets outside partial scope work."""

        @dataclass
        class Cache:
            size: int

        @dataclass
        class Service:
            cache: Cache

        @dataclass
        class App:
            shared_cache: Cache
            service: Service

        rc.register("cache", Cache)
        rc.register("service", Service)
        rc.register("app", App)

        yaml_content = """
_target_: app
shared_cache:
  _target_: cache
  size: 100
service:
  _target_: service
  cache:
    _instance_: /shared_cache
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            f.write(yaml_content)
            path = Path(f.name)

        try:
            # Act - instantiate only the service, which has _instance_ to external
            result = rc.instantiate(path, inner_path="service", cli_overrides=False)

            # Assert
            self.assertIsInstance(result, Service)
            self.assertIsInstance(result.cache, Cache)
            self.assertEqual(result.cache.size, 100)
        finally:
            path.unlink()
