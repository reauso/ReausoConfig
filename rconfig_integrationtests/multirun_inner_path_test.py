"""Integration tests for inner_path parameter in instantiate_multirun.

These tests verify inner_path works end-to-end with real config files.
"""

from dataclasses import dataclass
from pathlib import Path
from unittest import TestCase

import rconfig as rc
from rconfig.composition import clear_cache


# Test dataclasses
@dataclass
class ModelConfig:
    hidden_size: int
    dropout: float = 0.1


@dataclass
class OptimizerConfig:
    lr: float
    weight_decay: float = 0.01


@dataclass
class TrainerConfig:
    model: ModelConfig
    optimizer: OptimizerConfig
    epochs: int


# Path to config files directory
CONFIG_DIR = Path(__file__).parent / "config_files"


class MultirunInnerPathIntegrationTests(TestCase):
    """Integration tests for instantiate_multirun with inner_path."""

    def setUp(self):
        rc._store.clear()
        clear_cache()
        rc.register("model", ModelConfig)
        rc.register("trainer", TrainerConfig)

    def test_multirun_inner_path__real_yaml_file__instantiates_subsection(self):
        """End-to-end test: inner_path instantiates only the model section."""
        # Arrange
        config_path = CONFIG_DIR / "trainer_config.yaml"

        # Act - sweep paths are relative to full config
        results = list(
            rc.instantiate_multirun(
                path=config_path,
                inner_path="model",
                sweep={"model.hidden_size": [256, 512]},
                cli_overrides=False,
            )
        )

        # Assert
        self.assertEqual(len(results), 2)
        for result in results:
            # Should be ModelConfig, not TrainerConfig
            self.assertIsInstance(result.instance, ModelConfig)

        hidden_sizes = [r.instance.hidden_size for r in results]
        self.assertIn(256, hidden_sizes)
        self.assertIn(512, hidden_sizes)

    def test_multirun_inner_path__with_ref_composition__resolves_correctly(self):
        """Test inner_path with _ref_ composition in config."""
        # Arrange
        config_path = CONFIG_DIR / "trainer_with_ref.yaml"

        # Act - sweep paths are relative to full config
        results = list(
            rc.instantiate_multirun(
                path=config_path,
                inner_path="model",
                sweep={"model.dropout": [0.1, 0.2]},
                cli_overrides=False,
            )
        )

        # Assert
        self.assertEqual(len(results), 2)
        for result in results:
            self.assertIsInstance(result.instance, ModelConfig)

        dropouts = [r.instance.dropout for r in results]
        self.assertIn(0.1, dropouts)
        self.assertIn(0.2, dropouts)

    def test_multirun_inner_path__iterator_features_preserved(self):
        """Verify iterator features (len, slicing) work with inner_path."""
        # Arrange
        config_path = CONFIG_DIR / "trainer_config.yaml"

        # Act - sweep paths are relative to full config
        results = rc.instantiate_multirun(
            path=config_path,
            inner_path="model",
            sweep={"model.hidden_size": [256, 512, 1024]},
            cli_overrides=False,
        )

        # Assert - len works
        self.assertEqual(len(results), 3)

        # Assert - slicing works
        sliced = results[1:]
        self.assertEqual(len(sliced), 2)

        # Assert - indexing works
        single = results[0]
        self.assertIsInstance(single.instance, ModelConfig)

    def test_multirun_inner_path__with_expected_type__type_preserved(self):
        """Verify expected_type works with inner_path."""
        # Arrange
        config_path = CONFIG_DIR / "trainer_config.yaml"

        # Act - sweep paths are relative to full config
        results = rc.instantiate_multirun(
            config_path,
            ModelConfig,  # expected_type
            inner_path="model",
            sweep={"model.hidden_size": [256]},
            cli_overrides=False,
        )

        # Assert
        result = list(results)[0]
        self.assertIsInstance(result.instance, ModelConfig)

    def test_multirun_inner_path__combined_sweep_and_experiments(self):
        """Test inner_path with both sweep and experiments."""
        # Arrange
        config_path = CONFIG_DIR / "trainer_config.yaml"

        # Act - all paths are relative to full config
        results = list(
            rc.instantiate_multirun(
                path=config_path,
                inner_path="model",
                experiments=[{"model.hidden_size": 256}, {"model.hidden_size": 512}],
                sweep={"model.dropout": [0.1, 0.2]},
                cli_overrides=False,
            )
        )

        # Assert - 2 experiments x 2 dropout values = 4 total
        self.assertEqual(len(results), 4)
        for result in results:
            self.assertIsInstance(result.instance, ModelConfig)

    def test_multirun_inner_path__result_config_contains_full_config(self):
        """Verify result.config contains the full resolved config, not just subsection."""
        # Arrange
        config_path = CONFIG_DIR / "trainer_config.yaml"

        # Act - sweep paths are relative to full config
        results = list(
            rc.instantiate_multirun(
                path=config_path,
                inner_path="model",
                sweep={"model.hidden_size": [256]},
                cli_overrides=False,
            )
        )

        # Assert
        result = results[0]
        # The config should still have the full structure
        self.assertIn("model", result.config)
        self.assertIn("epochs", result.config)

    def test_multirun_inner_path__error_handling_preserved(self):
        """Verify error handling works correctly with inner_path."""
        # Arrange
        config_path = CONFIG_DIR / "trainer_config.yaml"

        # Act - use valid sweep path but invalid inner_path
        results = rc.instantiate_multirun(
            path=config_path,
            inner_path="nonexistent_path",
            sweep={"epochs": [5]},
            cli_overrides=False,
        )

        # Assert - error should be captured in result
        result = next(iter(results))
        # Accessing instance should raise the error
        with self.assertRaises(Exception):
            _ = result.instance


class MultirunInnerPathNestedTests(TestCase):
    """Tests for deeply nested inner_path."""

    def setUp(self):
        rc._store.clear()
        clear_cache()
        rc.register("model", ModelConfig)

    def test_multirun_inner_path__models_from_ref__instantiates_correctly(self):
        """Test inner_path pointing to a section loaded via _ref_."""
        # Arrange - trainer_with_ref.yaml uses _ref_ for model
        config_path = CONFIG_DIR / "trainer_with_ref.yaml"

        # Act - sweep paths are relative to full config
        results = list(
            rc.instantiate_multirun(
                path=config_path,
                inner_path="model",
                sweep={"model.hidden_size": [128, 256]},
                cli_overrides=False,
            )
        )

        # Assert
        self.assertEqual(len(results), 2)
        for result in results:
            self.assertIsInstance(result.instance, ModelConfig)
