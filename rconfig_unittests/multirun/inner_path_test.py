"""Unit tests for inner_path parameter in instantiate_multirun.

These tests verify that inner_path works correctly to instantiate
only a subsection of the config during multirun sweeps.
"""

from dataclasses import dataclass
from pathlib import Path
from unittest import TestCase

import rconfig as rc
from rconfig.composition import clear_cache
from rconfig.errors import InvalidInnerPathError

from rconfig_unittests.fixtures import MockFileSystem, mock_filesystem


@dataclass
class ModelConfig:
    """Test model with configurable parameters."""

    hidden_size: int
    lr: float = 0.001


@dataclass
class EncoderConfig:
    """Nested encoder for testing deep paths."""

    hidden_dim: int
    layers: int = 4


@dataclass
class NestedModelConfig:
    """Model with nested encoder."""

    encoder: EncoderConfig
    dropout: float = 0.1


@dataclass
class TrainerConfig:
    """Full trainer config with model."""

    model: ModelConfig
    epochs: int


class InnerPathMultirunTests(TestCase):
    """Tests for inner_path parameter in instantiate_multirun."""

    def setUp(self):
        rc._store.clear()
        clear_cache()
        rc.register("model", ModelConfig)
        rc.register("trainer", TrainerConfig)

    def test_instantiate_multirun__inner_path_selects_subsection__returns_instantiated_subsection(
        self,
    ):
        """Verify inner_path extracts and instantiates only the specified section."""
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file(
            "/configs/trainer.yaml",
            """
_target_: trainer
model:
  _target_: model
  hidden_size: 256
  lr: 0.001
epochs: 10
""",
        )

        with mock_filesystem(fs):
            # Act - sweep path is relative to full config, not inner_path
            results = list(
                rc.instantiate_multirun(
                    path=Path("/configs/trainer.yaml"),
                    inner_path="model",
                    sweep={"model.lr": [0.01]},
                    cli_overrides=False,
                )
            )

            # Assert
            self.assertEqual(len(results), 1)
            # The result should be a ModelConfig, not TrainerConfig
            self.assertIsInstance(results[0].instance, ModelConfig)
            self.assertEqual(results[0].instance.hidden_size, 256)
            self.assertEqual(results[0].instance.lr, 0.01)

    def test_instantiate_multirun__inner_path_with_sweep__applies_sweep_to_subsection(
        self,
    ):
        """Verify sweep parameters work correctly with inner_path."""
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file(
            "/configs/trainer.yaml",
            """
_target_: trainer
model:
  _target_: model
  hidden_size: 256
  lr: 0.001
epochs: 10
""",
        )

        with mock_filesystem(fs):
            # Act - sweep path is relative to full config
            results = list(
                rc.instantiate_multirun(
                    path=Path("/configs/trainer.yaml"),
                    inner_path="model",
                    sweep={"model.lr": [0.01, 0.001]},
                    cli_overrides=False,
                )
            )

            # Assert
            self.assertEqual(len(results), 2)
            learning_rates = [r.instance.lr for r in results]
            self.assertIn(0.01, learning_rates)
            self.assertIn(0.001, learning_rates)

    def test_instantiate_multirun__inner_path_invalid_path__raises_InvalidInnerPathError(
        self,
    ):
        """Verify invalid inner_path raises appropriate error."""
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file(
            "/configs/trainer.yaml",
            """
_target_: trainer
model:
  _target_: model
  hidden_size: 256
epochs: 10
""",
        )

        with mock_filesystem(fs):
            # Act - use a valid sweep path, but invalid inner_path
            results = rc.instantiate_multirun(
                path=Path("/configs/trainer.yaml"),
                inner_path="nonexistent",
                sweep={"epochs": [5]},
                cli_overrides=False,
            )

            # Assert - error is raised when accessing instance
            result = next(iter(results))
            with self.assertRaises(InvalidInnerPathError):
                _ = result.instance

    def test_instantiate_multirun__inner_path_with_experiments__works_correctly(self):
        """Verify inner_path works with experiments parameter."""
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file(
            "/configs/trainer.yaml",
            """
_target_: trainer
model:
  _target_: model
  hidden_size: 256
  lr: 0.001
epochs: 10
""",
        )

        with mock_filesystem(fs):
            # Act - experiment paths are relative to full config
            results = list(
                rc.instantiate_multirun(
                    path=Path("/configs/trainer.yaml"),
                    inner_path="model",
                    experiments=[{"model.hidden_size": 512}, {"model.hidden_size": 1024}],
                    cli_overrides=False,
                )
            )

            # Assert
            self.assertEqual(len(results), 2)
            hidden_sizes = [r.instance.hidden_size for r in results]
            self.assertIn(512, hidden_sizes)
            self.assertIn(1024, hidden_sizes)

    def test_instantiate_multirun__inner_path_with_overrides__applies_to_subsection(
        self,
    ):
        """Verify constant overrides work with inner_path."""
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file(
            "/configs/trainer.yaml",
            """
_target_: trainer
model:
  _target_: model
  hidden_size: 256
  lr: 0.001
epochs: 10
""",
        )

        with mock_filesystem(fs):
            # Act - all paths are relative to full config
            results = list(
                rc.instantiate_multirun(
                    path=Path("/configs/trainer.yaml"),
                    inner_path="model",
                    sweep={"model.lr": [0.01, 0.001]},
                    overrides={"model.hidden_size": 512},
                    cli_overrides=False,
                )
            )

            # Assert
            self.assertEqual(len(results), 2)
            # All results should have the overridden hidden_size
            for result in results:
                self.assertEqual(result.instance.hidden_size, 512)

    def test_instantiate_multirun__inner_path_none__full_config_instantiated(self):
        """Verify None inner_path (default) instantiates full config."""
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file(
            "/configs/trainer.yaml",
            """
_target_: trainer
model:
  _target_: model
  hidden_size: 256
epochs: 10
""",
        )

        with mock_filesystem(fs):
            # Act
            results = list(
                rc.instantiate_multirun(
                    path=Path("/configs/trainer.yaml"),
                    inner_path=None,  # Explicit None
                    sweep={"epochs": [5, 10]},
                    cli_overrides=False,
                )
            )

            # Assert
            self.assertEqual(len(results), 2)
            # Should be TrainerConfig, not ModelConfig
            self.assertIsInstance(results[0].instance, TrainerConfig)
            self.assertIsInstance(results[0].instance.model, ModelConfig)


class NestedInnerPathTests(TestCase):
    """Tests for nested inner_path like 'model.encoder'."""

    def setUp(self):
        rc._store.clear()
        clear_cache()
        rc.register("encoder", EncoderConfig)
        rc.register("nested_model", NestedModelConfig)

    def test_instantiate_multirun__inner_path_nested__extracts_deeply_nested_section(
        self,
    ):
        """Verify nested paths like 'model.encoder' work."""
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file(
            "/configs/model.yaml",
            """
_target_: nested_model
encoder:
  _target_: encoder
  hidden_dim: 256
  layers: 4
dropout: 0.1
""",
        )

        with mock_filesystem(fs):
            # Act - sweep path is relative to full config
            results = list(
                rc.instantiate_multirun(
                    path=Path("/configs/model.yaml"),
                    inner_path="encoder",
                    sweep={"encoder.hidden_dim": [256, 512]},
                    cli_overrides=False,
                )
            )

            # Assert
            self.assertEqual(len(results), 2)
            # Should be EncoderConfig instances
            for result in results:
                self.assertIsInstance(result.instance, EncoderConfig)
            hidden_dims = [r.instance.hidden_dim for r in results]
            self.assertIn(256, hidden_dims)
            self.assertIn(512, hidden_dims)


class InnerPathWithExternalInstanceTests(TestCase):
    """Tests for inner_path with _instance_ references outside the inner path."""

    def setUp(self):
        rc._store.clear()
        clear_cache()

    def test_instantiate_multirun__inner_path_with_external_instance_ref__pre_instantiates_external(
        self,
    ):
        """Verify _instance_ refs outside inner_path are pre-instantiated."""

        @dataclass
        class SharedCache:
            name: str

        @dataclass
        class Service:
            cache: SharedCache

        @dataclass
        class App:
            shared_cache: SharedCache
            service: Service

        rc.register("cache", SharedCache)
        rc.register("service", Service)
        rc.register("app", App)

        fs = MockFileSystem("/configs")
        fs.add_file(
            "/configs/app.yaml",
            """
_target_: app
shared_cache:
  _target_: cache
  name: redis
service:
  _target_: service
  cache:
    _instance_: shared_cache
""",
        )

        with mock_filesystem(fs):
            # Act - use valid path for experiment
            results = list(
                rc.instantiate_multirun(
                    path=Path("/configs/app.yaml"),
                    inner_path="service",
                    experiments=[{"shared_cache.name": "memcached"}],
                    cli_overrides=False,
                )
            )

            # Assert
            self.assertEqual(len(results), 1)
            # Service should be instantiated with the shared cache
            self.assertIsInstance(results[0].instance, Service)
            self.assertIsInstance(results[0].instance.cache, SharedCache)


class InnerPathWithSweepAndExperimentsTests(TestCase):
    """Tests combining inner_path with both sweep and experiments."""

    def setUp(self):
        rc._store.clear()
        clear_cache()
        rc.register("model", ModelConfig)
        rc.register("trainer", TrainerConfig)

    def test_instantiate_multirun__inner_path_with_both_sweep_and_experiments__cartesian_product(
        self,
    ):
        """Verify inner_path works with both sweep and experiments (cartesian product)."""
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file(
            "/configs/trainer.yaml",
            """
_target_: trainer
model:
  _target_: model
  hidden_size: 256
  lr: 0.001
epochs: 10
""",
        )

        with mock_filesystem(fs):
            # Act - all paths are relative to full config
            results = list(
                rc.instantiate_multirun(
                    path=Path("/configs/trainer.yaml"),
                    inner_path="model",
                    experiments=[{"model.hidden_size": 256}, {"model.hidden_size": 512}],
                    sweep={"model.lr": [0.01, 0.001]},
                    cli_overrides=False,
                )
            )

            # Assert - 2 experiments x 2 lr values = 4 total
            self.assertEqual(len(results), 4)
            for result in results:
                self.assertIsInstance(result.instance, ModelConfig)
