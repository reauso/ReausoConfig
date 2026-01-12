"""Integration tests for partial instantiation without root _target_.

These tests verify that configs without root-level _target_ work correctly
when using inner_path parameter for partial instantiation.
"""

from dataclasses import dataclass
from pathlib import Path
from unittest import TestCase

import rconfig as rc
from rconfig.composition import clear_cache


# Test dataclasses
@dataclass
class Database:
    port: int
    host: str = "localhost"


@dataclass
class Model:
    size: int
    database: Database


@dataclass
class Trainer:
    model: Model
    epochs: int


# Path to config files directory
CONFIG_DIR = Path(__file__).parent / "config_files"


class PartialInstantiationNoRootTargetTests(TestCase):
    """Integration tests for configs without root _target_."""

    def setUp(self):
        rc._store.clear()
        clear_cache()
        rc.register("database", Database)
        rc.register("model", Model)
        rc.register("trainer", Trainer)

    def test_instantiate__ConfigWithoutRootTarget__InnerPathToTargetSection(self):
        """Real file without root _target_, inner_path to section with _target_."""
        # Arrange
        config_path = CONFIG_DIR / "no_root_target.yaml"

        # Act
        result = rc.instantiate(config_path, inner_path="model", cli_overrides=False)

        # Assert
        self.assertIsInstance(result, Model)
        self.assertEqual(result.size, 256)
        self.assertIsInstance(result.database, Database)
        self.assertEqual(result.database.port, 5432)

    def test_instantiate__ConfigWithoutRootTarget__InnerPathToNestedWithTarget(self):
        """inner_path to nested section with explicit _target_ works."""
        # Arrange
        config_path = CONFIG_DIR / "no_root_target_nested.yaml"

        # Act - database has explicit _target_
        result = rc.instantiate(
            config_path, inner_path="model.database", cli_overrides=False
        )

        # Assert
        self.assertIsInstance(result, Database)
        self.assertEqual(result.port, 5432)
        self.assertEqual(result.host, "localhost")

    def test_instantiate__ConfigWithoutRootTarget__InnerPathWithInterpolation(self):
        """Config without root _target_ with interpolations resolved from full config."""
        # Arrange
        config_path = CONFIG_DIR / "no_root_target_interpolation.yaml"

        # Act
        result = rc.instantiate(config_path, inner_path="model", cli_overrides=False)

        # Assert - interpolation should have resolved from defaults
        self.assertIsInstance(result, Model)
        self.assertEqual(result.size, 512)  # From ${/defaults.hidden_size}

    def test_instantiate__ConfigWithoutRootTarget__InnerPathWithOverrides(self):
        """Config without root _target_ with overrides applied."""
        # Arrange
        config_path = CONFIG_DIR / "no_root_target.yaml"

        # Act
        result = rc.instantiate(
            config_path,
            inner_path="model",
            overrides={"model.size": 1024},
            cli_overrides=False,
        )

        # Assert
        self.assertEqual(result.size, 1024)

    def test_validate__ConfigWithoutRootTarget__InnerPathToValidSection(self):
        """validate() works on config without root _target_."""
        # Arrange
        config_path = CONFIG_DIR / "no_root_target.yaml"

        # Act
        result = rc.validate(config_path, inner_path="model", cli_overrides=False)

        # Assert
        self.assertTrue(result.valid)
        self.assertEqual(len(result.errors), 0)

    def test_instantiate__ConfigWithoutRootTarget__NoInnerPath__RaisesError(self):
        """Without inner_path, missing root _target_ raises AmbiguousTargetError."""
        # Arrange
        config_path = CONFIG_DIR / "no_root_target.yaml"

        # Act & Assert
        with self.assertRaises(rc.AmbiguousTargetError):
            rc.instantiate(config_path, cli_overrides=False)

    def test_instantiate__ConfigWithoutRootTarget__InnerPathToScalarSection__RaisesError(
        self,
    ):
        """inner_path to section without _target_ and not instantiable raises error."""
        # Arrange
        config_path = CONFIG_DIR / "no_root_target.yaml"

        # Act & Assert - raw_data has no _target_ and no parent to infer from
        with self.assertRaises(rc.AmbiguousTargetError):
            rc.instantiate(config_path, inner_path="raw_data", cli_overrides=False)


class PartialInstantiationWithRefNoRootTargetTests(TestCase):
    """Tests for _ref_ usage in configs without root _target_."""

    def setUp(self):
        rc._store.clear()
        clear_cache()
        rc.register("database", Database)
        rc.register("model", Model)

    def test_instantiate__ConfigWithoutRootTarget__InnerPathWithRef(self):
        """Config without root _target_ using _ref_ in inner section."""
        # Arrange
        config_path = CONFIG_DIR / "no_root_target_ref.yaml"

        # Act
        result = rc.instantiate(config_path, inner_path="model", cli_overrides=False)

        # Assert - model should be composed from base_model via _ref_
        self.assertIsInstance(result, Model)
        self.assertEqual(result.size, 256)  # From base_model.yaml


class PartialInstantiationWithInstanceNoRootTargetTests(TestCase):
    """Tests for _instance_ usage in configs without root _target_."""

    def setUp(self):
        rc._store.clear()
        clear_cache()

        @dataclass
        class Cache:
            size: int

        @dataclass
        class Service:
            cache: Cache

        rc.register("cache", Cache)
        rc.register("service", Service)
        self.Cache = Cache
        self.Service = Service

    def test_instantiate__ConfigWithoutRootTarget__InnerPathWithInstance(self):
        """Config without root _target_ using _instance_ in inner section."""
        # Arrange
        config_path = CONFIG_DIR / "no_root_target_instance.yaml"

        # Act
        result = rc.instantiate(config_path, inner_path="service", cli_overrides=False)

        # Assert - service.cache should reference shared_cache via _instance_
        self.assertIsInstance(result, self.Service)
        self.assertIsInstance(result.cache, self.Cache)
        self.assertEqual(result.cache.size, 100)


class GetProvenanceNoRootTargetTests(TestCase):
    """Tests for get_provenance() with configs without root _target_."""

    def setUp(self):
        rc._store.clear()
        clear_cache()
        rc.register("database", Database)
        rc.register("model", Model)

    def test_getProvenance__ConfigWithoutRootTarget__InnerPathWorks(self):
        """get_provenance() with inner_path works on config without root _target_."""
        # Arrange
        config_path = CONFIG_DIR / "no_root_target.yaml"

        # Act
        prov = rc.get_provenance(config_path, inner_path="model", cli_overrides=False)

        # Assert - should have provenance entries for model section
        self.assertIsNotNone(prov.get("model.size"))
        self.assertIsNotNone(prov.get("model._target_"))

    def test_getProvenance__ConfigWithoutRootTarget__FullConfigWorks(self):
        """get_provenance() without inner_path works on config without root _target_."""
        # Arrange - provenance is about composition, not instantiation
        config_path = CONFIG_DIR / "no_root_target.yaml"

        # Act - get provenance for full config
        prov = rc.get_provenance(config_path, cli_overrides=False)

        # Assert - should have provenance for all values
        self.assertIsNotNone(prov.get("model.size"))
        self.assertIsNotNone(prov.get("raw_data.path"))


class TypeInferenceFromParentIntegrationTests(TestCase):
    """Integration tests for type inference from parent's type hints."""

    def setUp(self):
        rc._store.clear()
        clear_cache()
        rc.register("database", Database)
        rc.register("model", Model)

    def test_instantiate__TypeInferredFromParent__Works(self):
        """inner_path to section without _target_ works when type inferred from parent."""
        # Arrange
        config_path = CONFIG_DIR / "no_root_target.yaml"

        # Act - database type inferred from Model.database type hint
        result = rc.instantiate(
            config_path, inner_path="model.database", cli_overrides=False
        )

        # Assert
        self.assertIsInstance(result, Database)
        self.assertEqual(result.port, 5432)

    def test_validate__TypeInferredFromParent__Works(self):
        """validate() with type inference from parent works."""
        # Arrange
        config_path = CONFIG_DIR / "no_root_target.yaml"

        # Act
        result = rc.validate(
            config_path, inner_path="model.database", cli_overrides=False
        )

        # Assert
        self.assertTrue(result.valid)
