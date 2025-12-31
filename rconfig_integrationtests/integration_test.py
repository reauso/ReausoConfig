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


# Path to config files directory
CONFIG_DIR = Path(__file__).parent / "config_files"


class IntegrationTests(TestCase):
    def setUp(self):
        # Clear the store before each test
        rc._store._known_references.clear()
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

        trainer = rc.instantiate(config_path)

        self.assertIsInstance(trainer, TrainerConfig)
        self.assertIsInstance(trainer.model, ModelConfig)
        self.assertEqual(trainer.epochs, 10)
        self.assertEqual(trainer.learning_rate, 0.001)
        self.assertEqual(trainer.model.hidden_size, 256)
        self.assertEqual(trainer.model.dropout, 0.2)

    def test_instantiate__WithExpectedType__ReturnsTypedInstance(self):
        config_path = CONFIG_DIR / "trainer_config.yaml"

        # Type-safe instantiation
        trainer = rc.instantiate(config_path, TrainerConfig)

        self.assertIsInstance(trainer, TrainerConfig)
        self.assertEqual(trainer.epochs, 10)

    def test_workflow__ValidateThenInstantiate__Works(self):
        config_path = CONFIG_DIR / "trainer_config.yaml"

        # Step 1: Validate (dry-run)
        result = rc.validate(config_path)
        self.assertTrue(result.valid)

        # Step 2: Instantiate
        trainer = rc.instantiate(config_path)

        # Verify final result
        self.assertIsInstance(trainer, TrainerConfig)
        self.assertIsInstance(trainer.model, ModelConfig)
        self.assertEqual(trainer.epochs, 10)
        self.assertEqual(trainer.learning_rate, 0.001)
        self.assertEqual(trainer.model.hidden_size, 256)
        self.assertEqual(trainer.model.dropout, 0.2)
