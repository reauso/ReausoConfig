"""Integration tests for the rconfig library.

These tests verify the complete system works end-to-end using real YAML config files.
"""

from dataclasses import dataclass
from pathlib import Path
from unittest.case import TestCase

import rconfig as rc


# Test dataclasses
@dataclass
class ModelConfig:
    hidden_size: int
    dropout: float = 0.1


@dataclass
class TrainerConfig:
    model: ModelConfig
    epochs: int
    learning_rate: float = 0.001


@dataclass
class Level3:
    value: int


@dataclass
class Level2:
    level3: Level3


@dataclass
class Level1:
    level2: Level2


# Path to config files directory
CONFIG_DIR = Path(__file__).parent / "config_files"


class IntegrationTests(TestCase):
    def setUp(self):
        # Clear the store before each test
        rc._store._known_targets.clear()
        # Register test targets
        rc.register("model", ModelConfig)
        rc.register("trainer", TrainerConfig)

    def test_validate__ConfigPath__ReturnsValidResult(self):
        config_path = CONFIG_DIR / "trainer_config.yaml"

        result = rc.validate(config_path)

        self.assertTrue(result.valid)
        self.assertEqual(len(result.errors), 0)

    def test_instantiate__FromPath__ReturnsNestedInstance(self):
        config_path = CONFIG_DIR / "trainer_config.yaml"

        trainer = rc.instantiate(config_path, cli_overrides=False)

        self.assertIsInstance(trainer, TrainerConfig)
        self.assertIsInstance(trainer.model, ModelConfig)
        self.assertEqual(trainer.epochs, 10)
        self.assertEqual(trainer.learning_rate, 0.001)
        self.assertEqual(trainer.model.hidden_size, 256)
        self.assertEqual(trainer.model.dropout, 0.2)

    def test_instantiate__WithExpectedType__ReturnsTypedInstance(self):
        config_path = CONFIG_DIR / "trainer_config.yaml"

        # Type-safe instantiation
        trainer = rc.instantiate(config_path, TrainerConfig, cli_overrides=False)

        self.assertIsInstance(trainer, TrainerConfig)
        self.assertEqual(trainer.epochs, 10)

    def test_workflow__ValidateThenInstantiate__Works(self):
        config_path = CONFIG_DIR / "trainer_config.yaml"

        # Step 1: Validate (dry-run)
        result = rc.validate(config_path)
        self.assertTrue(result.valid)

        # Step 2: Instantiate
        trainer = rc.instantiate(config_path, cli_overrides=False)

        # Verify final result
        self.assertIsInstance(trainer, TrainerConfig)
        self.assertIsInstance(trainer.model, ModelConfig)
        self.assertEqual(trainer.epochs, 10)
        self.assertEqual(trainer.learning_rate, 0.001)
        self.assertEqual(trainer.model.hidden_size, 256)
        self.assertEqual(trainer.model.dropout, 0.2)


class ImplicitTargetIntegrationTests(TestCase):
    """Integration tests for implicit _target_ inference with real YAML files."""

    def setUp(self):
        rc._store._known_targets.clear()
        rc.register("model", ModelConfig)
        rc.register("trainer", TrainerConfig)
        rc.register("l1", Level1)
        rc.register("l2", Level2)
        rc.register("l3", Level3)

    def test_validate__ImplicitNestedConfig__ReturnsValidResult(self):
        config_path = CONFIG_DIR / "trainer_implicit_config.yaml"

        result = rc.validate(config_path)

        self.assertTrue(result.valid)
        self.assertEqual(len(result.errors), 0)

    def test_instantiate__ImplicitNestedConfig__ReturnsCorrectInstance(self):
        config_path = CONFIG_DIR / "trainer_implicit_config.yaml"

        trainer = rc.instantiate(config_path, cli_overrides=False)

        self.assertIsInstance(trainer, TrainerConfig)
        self.assertIsInstance(trainer.model, ModelConfig)
        self.assertEqual(trainer.epochs, 20)
        self.assertEqual(trainer.model.hidden_size, 512)
        self.assertEqual(trainer.model.dropout, 0.3)

    def test_instantiate__DeeplyNestedImplicit__ReturnsCorrectInstance(self):
        config_path = CONFIG_DIR / "deeply_nested_implicit_config.yaml"

        result = rc.instantiate(config_path, cli_overrides=False)

        self.assertIsInstance(result, Level1)
        self.assertIsInstance(result.level2, Level2)
        self.assertIsInstance(result.level2.level3, Level3)
        self.assertEqual(result.level2.level3.value, 42)

    def test_workflow__ValidateThenInstantiate__WorksWithImplicitTargets(self):
        config_path = CONFIG_DIR / "trainer_implicit_config.yaml"

        # Step 1: Validate (dry-run)
        result = rc.validate(config_path)
        self.assertTrue(result.valid)

        # Step 2: Instantiate
        trainer = rc.instantiate(config_path, cli_overrides=False)

        # Verify final result
        self.assertIsInstance(trainer, TrainerConfig)
        self.assertIsInstance(trainer.model, ModelConfig)
        self.assertEqual(trainer.epochs, 20)
        self.assertEqual(trainer.model.hidden_size, 512)
