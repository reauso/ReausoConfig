"""Integration tests for config composition with _ref_ and _instance_.

These tests verify that the public API correctly handles composition,
including _ref_ resolution, _instance_ sharing, and provenance tracking.
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
class Cache:
    size: int


@dataclass
class ServiceA:
    cache: Cache


@dataclass
class ServiceB:
    cache: Cache


@dataclass
class App:
    shared_cache: Cache
    service_a: ServiceA
    service_b: ServiceB


# Path to config files directory
CONFIG_DIR = Path(__file__).parent / "config_files"


class RefCompositionIntegrationTests(TestCase):
    """Tests for _ref_ resolution through the public API."""

    def setUp(self):
        rc._store._known_targets.clear()
        rc.clear_cache()
        rc.register("model", ModelConfig)
        rc.register("trainer", TrainerConfig)

    def tearDown(self):
        rc.clear_cache()

    def test_validate__ConfigWithRef__ReturnsValidResult(self):
        config_path = CONFIG_DIR / "trainer_with_ref.yaml"

        result = rc.validate(config_path)

        self.assertTrue(result.valid)
        self.assertEqual(len(result.errors), 0)

    def test_instantiate__ConfigWithRef__ResolvesAndInstantiates(self):
        config_path = CONFIG_DIR / "trainer_with_ref.yaml"

        trainer = rc.instantiate(config_path, cli_overrides=False)

        self.assertIsInstance(trainer, TrainerConfig)
        self.assertIsInstance(trainer.model, ModelConfig)
        # Values from referenced file
        self.assertEqual(trainer.model.hidden_size, 256)
        # Overridden value
        self.assertEqual(trainer.model.dropout, 0.2)
        self.assertEqual(trainer.epochs, 10)

    def test_instantiate__ConfigWithRef_TypedVersion__ReturnsTypedInstance(self):
        config_path = CONFIG_DIR / "trainer_with_ref.yaml"

        trainer = rc.instantiate(config_path, TrainerConfig, cli_overrides=False)

        self.assertIsInstance(trainer, TrainerConfig)
        self.assertEqual(trainer.epochs, 10)


class InstanceSharingIntegrationTests(TestCase):
    """Tests for _instance_ sharing through the public API."""

    def setUp(self):
        rc._store._known_targets.clear()
        rc.clear_cache()
        rc.register("cache", Cache)
        rc.register("service_a", ServiceA)
        rc.register("service_b", ServiceB)
        rc.register("app", App)

    def tearDown(self):
        rc.clear_cache()

    def test_validate__ConfigWithInstance__ReturnsValidResult(self):
        config_path = CONFIG_DIR / "app_with_shared_instances.yaml"

        result = rc.validate(config_path)

        self.assertTrue(result.valid)
        self.assertEqual(len(result.errors), 0)

    def test_instantiate__ConfigWithInstance__SharesObjects(self):
        config_path = CONFIG_DIR / "app_with_shared_instances.yaml"

        app = rc.instantiate(config_path, cli_overrides=False)

        self.assertIsInstance(app, App)
        self.assertIsInstance(app.shared_cache, Cache)
        self.assertIsInstance(app.service_a, ServiceA)
        self.assertIsInstance(app.service_b, ServiceB)

        # The key assertion: both services share the same cache object
        self.assertIs(app.service_a.cache, app.shared_cache)
        self.assertIs(app.service_b.cache, app.shared_cache)
        self.assertIs(app.service_a.cache, app.service_b.cache)

    def test_instantiate__ConfigWithInstance_CacheValue__IsCorrect(self):
        config_path = CONFIG_DIR / "app_with_shared_instances.yaml"

        app = rc.instantiate(config_path, cli_overrides=False)

        # Verify the shared object has the correct value
        self.assertEqual(app.shared_cache.size, 100)
        self.assertEqual(app.service_a.cache.size, 100)
        self.assertEqual(app.service_b.cache.size, 100)


class ProvenanceIntegrationTests(TestCase):
    """Tests for provenance tracking through the public API."""

    def setUp(self):
        rc._store._known_targets.clear()
        rc.clear_cache()
        rc.register("model", ModelConfig)
        rc.register("trainer", TrainerConfig)

    def tearDown(self):
        rc.clear_cache()

    def test_getProvenance__ConfigWithRef__TracksOrigins(self):
        config_path = CONFIG_DIR / "trainer_with_ref.yaml"

        prov = rc.get_provenance(config_path)

        # Check that provenance is tracked
        self.assertIsNotNone(prov)

        # Check that we can get specific entries
        epochs_entry = prov.get("epochs")
        self.assertIsNotNone(epochs_entry)
        self.assertIn("trainer_with_ref.yaml", epochs_entry.file)

        # Check that referenced file values are tracked
        hidden_size_entry = prov.get("model.hidden_size")
        self.assertIsNotNone(hidden_size_entry)
        self.assertIn("resnet.yaml", hidden_size_entry.file)

    def test_getProvenance__Override__TracksOverride(self):
        config_path = CONFIG_DIR / "trainer_with_ref.yaml"

        prov = rc.get_provenance(config_path)

        # dropout was overridden in trainer_with_ref.yaml
        dropout_entry = prov.get("model.dropout")
        self.assertIsNotNone(dropout_entry)
        self.assertIn("trainer_with_ref.yaml", dropout_entry.file)
        # Should have overrode info
        self.assertIsNotNone(dropout_entry.overrode)


class CacheControlIntegrationTests(TestCase):
    """Tests for cache control functions."""

    def setUp(self):
        rc._store._known_targets.clear()
        rc.clear_cache()
        rc.register("model", ModelConfig)
        rc.register("trainer", TrainerConfig)

    def tearDown(self):
        rc.clear_cache()

    def test_setCacheSize__SetsSize__DoesNotRaiseError(self):
        # Should not raise
        rc.set_cache_size(100)
        rc.set_cache_size(0)  # Unlimited

    def test_clearCache__ClearsCache__DoesNotRaiseError(self):
        # Load a config to populate cache
        config_path = CONFIG_DIR / "trainer_with_ref.yaml"
        rc.instantiate(config_path, cli_overrides=False)

        # Should not raise
        rc.clear_cache()


class OverridesWithCompositionIntegrationTests(TestCase):
    """Tests for overrides combined with composition."""

    def setUp(self):
        rc._store._known_targets.clear()
        rc.clear_cache()
        rc.register("model", ModelConfig)
        rc.register("trainer", TrainerConfig)

    def tearDown(self):
        rc.clear_cache()

    def test_instantiate__OverrideValueInReferencedConfig__AppliesOverride(self):
        config_path = CONFIG_DIR / "trainer_with_ref.yaml"

        trainer = rc.instantiate(
            config_path,
            overrides={"model.hidden_size": 512},
            cli_overrides=False,
        )

        # Override should be applied
        self.assertEqual(trainer.model.hidden_size, 512)
        # Other values should be preserved
        self.assertEqual(trainer.model.dropout, 0.2)
        self.assertEqual(trainer.epochs, 10)

    def test_instantiate__OverrideTopLevelValue__AppliesOverride(self):
        config_path = CONFIG_DIR / "trainer_with_ref.yaml"

        trainer = rc.instantiate(
            config_path,
            overrides={"epochs": 100},
            cli_overrides=False,
        )

        self.assertEqual(trainer.epochs, 100)
        # Other values should be preserved
        self.assertEqual(trainer.model.hidden_size, 256)
