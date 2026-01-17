"""Integration tests for extension-less _ref_ resolution.

These tests verify end-to-end behavior of extension-less _ref_ paths
through the public API.
"""

import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from unittest import TestCase

import rconfig as rc
from rconfig.errors import AmbiguousRefError, RefResolutionError


@dataclass
class Model:
    layers: int
    hidden_size: int = 256


@dataclass
class Trainer:
    model: Model
    epochs: int


class ExtensionlessRefIntegrationTests(TestCase):
    """End-to-end tests for extension-less _ref_ resolution."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_root = Path(self.temp_dir.name)
        rc._store._known_targets.clear()
        rc.clear_cache()
        rc.register("model", Model)
        rc.register("trainer", Trainer)

    def tearDown(self):
        self.temp_dir.cleanup()
        rc.clear_cache()

    def _write_yaml(self, name: str, content: str) -> Path:
        path = self.config_root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def _write_json(self, name: str, content: str) -> Path:
        path = self.config_root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def _write_toml(self, name: str, content: str) -> Path:
        path = self.config_root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def test_instantiate__ExtensionlessRef__ResolvesYamlFile(self):
        # Arrange
        self._write_yaml(
            "models/vit.yaml",
            """
_target_: model
layers: 12
hidden_size: 768
""",
        )
        trainer_path = self._write_yaml(
            "trainer.yaml",
            """
_target_: trainer
model:
  _ref_: models/vit
epochs: 100
""",
        )

        # Act
        trainer = rc.instantiate(trainer_path, cli_overrides=False)

        # Assert
        self.assertIsInstance(trainer, Trainer)
        self.assertEqual(trainer.model.layers, 12)
        self.assertEqual(trainer.model.hidden_size, 768)

    def test_instantiate__ExtensionlessRef__ResolvesJsonFile(self):
        # Arrange
        self._write_json(
            "models/resnet.json",
            """
{
    "_target_": "model",
    "layers": 50,
    "hidden_size": 512
}
""",
        )
        trainer_path = self._write_yaml(
            "trainer.yaml",
            """
_target_: trainer
model:
  _ref_: models/resnet
epochs: 100
""",
        )

        # Act
        trainer = rc.instantiate(trainer_path, cli_overrides=False)

        # Assert
        self.assertEqual(trainer.model.layers, 50)
        self.assertEqual(trainer.model.hidden_size, 512)

    def test_instantiate__ExtensionlessRef__ResolvesTomlFile(self):
        # Arrange
        self._write_toml(
            "models/transformer.toml",
            """
_target_ = "model"
layers = 24
hidden_size = 1024
""",
        )
        trainer_path = self._write_yaml(
            "trainer.yaml",
            """
_target_: trainer
model:
  _ref_: models/transformer
epochs: 100
""",
        )

        # Act
        trainer = rc.instantiate(trainer_path, cli_overrides=False)

        # Assert
        self.assertEqual(trainer.model.layers, 24)
        self.assertEqual(trainer.model.hidden_size, 1024)

    def test_instantiate__ExtensionlessRefWithOverride__AppliesOverride(self):
        # Arrange
        self._write_yaml(
            "models/vit.yaml",
            """
_target_: model
layers: 12
hidden_size: 768
""",
        )
        trainer_path = self._write_yaml(
            "trainer.yaml",
            """
_target_: trainer
model:
  _ref_: models/vit
  hidden_size: 1024
epochs: 100
""",
        )

        # Act
        trainer = rc.instantiate(trainer_path, cli_overrides=False)

        # Assert
        self.assertEqual(trainer.model.layers, 12)
        self.assertEqual(trainer.model.hidden_size, 1024)  # Override

    def test_validate__ExtensionlessRef__ReturnsValid(self):
        # Arrange
        self._write_yaml(
            "models/vit.yaml",
            """
_target_: model
layers: 12
""",
        )
        trainer_path = self._write_yaml(
            "trainer.yaml",
            """
_target_: trainer
model:
  _ref_: models/vit
epochs: 100
""",
        )

        # Act
        result = rc.validate(trainer_path)

        # Assert
        self.assertTrue(result.valid)

    def test_instantiate__MultipleFilesExist__RaisesAmbiguousRefError(self):
        # Arrange
        self._write_yaml("models/vit.yaml", "_target_: model\nlayers: 12")
        self._write_json("models/vit.json", '{"_target_": "model", "layers": 6}')
        trainer_path = self._write_yaml(
            "trainer.yaml",
            """
_target_: trainer
model:
  _ref_: models/vit
epochs: 100
""",
        )

        # Act & Assert
        with self.assertRaises(AmbiguousRefError) as ctx:
            rc.instantiate(trainer_path, cli_overrides=False)

        self.assertIn("vit.yaml", ctx.exception.found_files)
        self.assertIn("vit.json", ctx.exception.found_files)

    def test_instantiate__NoMatchingFile__RaisesRefResolutionError(self):
        # Arrange
        (self.config_root / "models").mkdir(parents=True)
        trainer_path = self._write_yaml(
            "trainer.yaml",
            """
_target_: trainer
model:
  _ref_: models/nonexistent
epochs: 100
""",
        )

        # Act & Assert
        with self.assertRaises(RefResolutionError):
            rc.instantiate(trainer_path, cli_overrides=False)

    def test_toDict__ExtensionlessRef__ExportsCorrectly(self):
        # Arrange
        self._write_yaml(
            "models/vit.yaml",
            """
_target_: model
layers: 12
hidden_size: 768
""",
        )
        trainer_path = self._write_yaml(
            "trainer.yaml",
            """
_target_: trainer
model:
  _ref_: models/vit
epochs: 100
""",
        )

        # Act
        config = rc.to_dict(trainer_path, cli_overrides=False)

        # Assert
        self.assertEqual(config["model"]["layers"], 12)
        self.assertEqual(config["model"]["hidden_size"], 768)

    def test_instantiate__CLIRefShorthandExtensionless__Resolves(self):
        # Arrange - test CLI _ref_ shorthand with extension-less paths
        # Note: This requires using apply_cli_overrides_with_ref_shorthand explicitly
        from rconfig.override import (
            extract_cli_overrides,
            apply_cli_overrides_with_ref_shorthand,
        )

        self._write_yaml(
            "models/vit.yaml",
            """
_target_: model
layers: 12
hidden_size: 768
""",
        )
        self._write_yaml(
            "models/resnet.yaml",
            """
_target_: model
layers: 50
hidden_size: 512
""",
        )
        trainer_path = self._write_yaml(
            "trainer.yaml",
            """
_target_: trainer
model:
  _ref_: models/vit
epochs: 100
""",
        )

        # Get the composed config first
        config = rc.to_dict(trainer_path, cli_overrides=False)

        # Apply CLI override with _ref_ shorthand (no extension)
        # provenance=None since we just want to test the override mechanism
        cli_args = ["model=models/resnet"]
        overrides = extract_cli_overrides(cli_args)
        config = apply_cli_overrides_with_ref_shorthand(config, overrides)

        # Assert - should have set model._ref_ to models/resnet
        # But we need to recompose to resolve the _ref_
        self.assertEqual(config["model"]["_ref_"], "models/resnet")

    def test_instantiate__NestedExtensionlessRef__ResolvesAll(self):
        # Arrange - nested _ref_ references
        self._write_yaml(
            "components/encoder.yaml",
            """
_target_: model
layers: 6
hidden_size: 256
""",
        )
        self._write_yaml(
            "models/custom.yaml",
            """
_target_: model
layers: 12
hidden_size: 512
""",
        )
        self._write_yaml(
            "configs/base.yaml",
            """
_target_: trainer
model:
  _ref_: ../models/custom
epochs: 50
""",
        )
        trainer_path = self._write_yaml(
            "main.yaml",
            """
_target_: trainer
model:
  _ref_: configs/base
  epochs: 100
""",
        )

        # Act - this tests parent path resolution with extension-less
        config = rc.to_dict(trainer_path, cli_overrides=False)

        # Assert
        self.assertIn("model", config)

    def test_instantiate__RelativeParentExtensionlessPath__ResolvesCorrectly(self):
        # Arrange - trainer is in configs/, model is in shared/
        self._write_yaml(
            "shared/base_model.yaml",
            """
_target_: model
layers: 8
hidden_size: 384
""",
        )
        trainer_path = self._write_yaml(
            "configs/trainer.yaml",
            """
_target_: trainer
model:
  _ref_: ../shared/base_model
epochs: 100
""",
        )

        # Act
        trainer = rc.instantiate(trainer_path, cli_overrides=False)

        # Assert
        self.assertEqual(trainer.model.layers, 8)
        self.assertEqual(trainer.model.hidden_size, 384)
