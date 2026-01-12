"""Integration tests for incremental composition with inner_path."""

import tempfile
import unittest
from pathlib import Path

import rconfig as rc
from rconfig.composition import ConfigComposer, clear_cache


class IncrementalCompositionBasicTests(unittest.TestCase):
    """Basic tests for incremental composition."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_root = Path(self.temp_dir.name)
        clear_cache()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()
        clear_cache()

    def _write_yaml(self, relative_path: str, content: str) -> Path:
        """Write a YAML file to the temp directory."""
        full_path = self.config_root / relative_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content)
        return full_path

    def test_compose__InnerPath__ProducesSameResultAsFullComposition(self):
        # Arrange
        self._write_yaml(
            "trainer.yaml",
            """
model:
  _target_: Model
  layers: 50
training:
  epochs: 100
  lr: 0.001
""",
        )

        # Act
        full = ConfigComposer().compose(self.config_root / "trainer.yaml")
        partial = ConfigComposer().compose(self.config_root / "trainer.yaml", inner_path="model")

        # Assert
        # Partial should include the model section and its structure
        self.assertEqual(full["model"], partial["model"])

    def test_compose__InnerPathWithRef__LoadsRefFile(self):
        # Arrange
        self._write_yaml(
            "models/resnet.yaml",
            """
_target_: ResNet
layers: 50
channels: 64
""",
        )
        self._write_yaml(
            "trainer.yaml",
            """
model:
  _ref_: ./models/resnet.yaml
data:
  _ref_: ./data.yaml
""",
        )
        # Note: data.yaml doesn't exist - but with inner_path="model", it shouldn't be loaded

        # Act
        result = ConfigComposer().compose(self.config_root / "trainer.yaml", inner_path="model")

        # Assert
        self.assertEqual("ResNet", result["model"]["_target_"])
        self.assertEqual(50, result["model"]["layers"])

    def test_compose__InnerPathWithCrossRef__LoadsDependency(self):
        # Arrange
        self._write_yaml(
            "defaults.yaml",
            """
learning_rate: 0.01
batch_size: 32
""",
        )
        self._write_yaml(
            "models/resnet.yaml",
            """
_target_: ResNet
lr: ${/defaults.learning_rate}
""",
        )
        self._write_yaml(
            "trainer.yaml",
            """
defaults:
  _ref_: ./defaults.yaml
model:
  _ref_: ./models/resnet.yaml
data:
  batch_size: ${/defaults.batch_size}
""",
        )

        # Act - model depends on defaults, so defaults should be loaded
        result = ConfigComposer().compose(self.config_root / "trainer.yaml", inner_path="model")

        # Assert
        # After interpolation resolution, model.lr should be resolved
        self.assertEqual("ResNet", result["model"]["_target_"])
        # The interpolation ${/defaults.learning_rate} should be in the model
        self.assertIn("lr", result["model"])


class IncrementalCompositionProvenanceTests(unittest.TestCase):
    """Tests for provenance with inner_path."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_root = Path(self.temp_dir.name)
        clear_cache()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()
        clear_cache()

    def _write_yaml(self, relative_path: str, content: str) -> Path:
        """Write a YAML file to the temp directory."""
        full_path = self.config_root / relative_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content)
        return full_path

    def test_get_provenance__InnerPath__TracksCorrectFile(self):
        # Arrange
        self._write_yaml(
            "models/resnet.yaml",
            """
_target_: ResNet
layers: 50
""",
        )
        self._write_yaml(
            "trainer.yaml",
            """
model:
  _ref_: ./models/resnet.yaml
training:
  epochs: 100
""",
        )

        # Act
        prov = rc.get_provenance(self.config_root / "trainer.yaml", inner_path="model")

        # Assert
        layers_entry = prov.get("model.layers")
        self.assertIsNotNone(layers_entry)
        self.assertIn("resnet.yaml", layers_entry.file)


class IncrementalCompositionMultirunTests(unittest.TestCase):
    """Tests for multirun with incremental composition."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_root = Path(self.temp_dir.name)
        clear_cache()
        # Register the SimpleModel target
        rc.register(
            "rconfig_integrationtests.incremental_composition_test.SimpleModel",
            SimpleModel,
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()
        clear_cache()
        try:
            rc.unregister(
                "rconfig_integrationtests.incremental_composition_test.SimpleModel"
            )
        except KeyError:
            pass

    def _write_yaml(self, relative_path: str, content: str) -> Path:
        """Write a YAML file to the temp directory."""
        full_path = self.config_root / relative_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content)
        return full_path

    def test_instantiate_multirun__InnerPath__EachRunGetsCorrectOverrides(self):
        # Arrange
        self._write_yaml(
            "model.yaml",
            """
_target_: rconfig_integrationtests.incremental_composition_test.SimpleModel
layers: 50
lr: 0.001
""",
        )
        self._write_yaml(
            "trainer.yaml",
            """
model:
  _ref_: ./model.yaml
data:
  batch_size: 32
""",
        )

        # Act
        # Note: sweep keys are relative to config root, not inner_path
        results = list(
            rc.instantiate_multirun(
                path=self.config_root / "trainer.yaml",
                inner_path="model",
                sweep={"model.lr": [0.001, 0.01, 0.1]},
            )
        )

        # Assert
        self.assertEqual(3, len(results))
        lrs = [r.instance.lr for r in results]
        self.assertEqual([0.001, 0.01, 0.1], lrs)
        # All should have same layers value
        for r in results:
            self.assertEqual(50, r.instance.layers)


class SimpleModel:
    """Simple model class for testing."""

    def __init__(self, layers: int, lr: float):
        self.layers = layers
        self.lr = lr


class IncrementalCompositionEdgeCaseTests(unittest.TestCase):
    """Edge case tests for incremental composition."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_root = Path(self.temp_dir.name)
        clear_cache()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()
        clear_cache()

    def _write_yaml(self, relative_path: str, content: str) -> Path:
        """Write a YAML file to the temp directory."""
        full_path = self.config_root / relative_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content)
        return full_path

    def test_compose__InvalidInnerPath__RaisesError(self):
        # Arrange
        self._write_yaml(
            "trainer.yaml",
            """
model:
  layers: 50
""",
        )

        # Act & Assert
        with self.assertRaises(rc.InvalidInnerPathError):
            ConfigComposer().compose(self.config_root / "trainer.yaml", inner_path="nonexistent")

    def test_compose__EmptyInnerPath__ComposesAll(self):
        # Arrange
        self._write_yaml(
            "models/resnet.yaml",
            """
_target_: ResNet
layers: 50
""",
        )
        self._write_yaml(
            "data/imagenet.yaml",
            """
_target_: ImageNet
size: 224
""",
        )
        self._write_yaml(
            "trainer.yaml",
            """
model:
  _ref_: ./models/resnet.yaml
data:
  _ref_: ./data/imagenet.yaml
""",
        )

        # Act
        result = ConfigComposer().compose(self.config_root / "trainer.yaml", inner_path="")

        # Assert - both refs should be resolved
        self.assertEqual("ResNet", result["model"]["_target_"])
        self.assertEqual("ImageNet", result["data"]["_target_"])

    def test_compose__NestedInnerPath__LoadsCorrectFiles(self):
        # Arrange
        self._write_yaml(
            "encoders/vit.yaml",
            """
_target_: ViT
patch_size: 16
""",
        )
        self._write_yaml(
            "models/resnet.yaml",
            """
_target_: ResNet
encoder:
  _ref_: ../encoders/vit.yaml
""",
        )
        self._write_yaml(
            "trainer.yaml",
            """
model:
  _ref_: ./models/resnet.yaml
""",
        )

        # Act
        result = ConfigComposer().compose(
            self.config_root / "trainer.yaml", inner_path="model.encoder"
        )

        # Assert
        self.assertEqual("ViT", result["model"]["encoder"]["_target_"])
        self.assertEqual(16, result["model"]["encoder"]["patch_size"])


if __name__ == "__main__":
    unittest.main()
