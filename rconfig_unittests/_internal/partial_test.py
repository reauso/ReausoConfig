"""Tests for partial config extraction utilities."""

from unittest import TestCase

from rconfig._internal.partial import (
    collect_external_targets,
    extract_partial_config,
    process_instance_targets,
)
from rconfig.errors import InvalidInnerPathError


class ExtractPartialConfigTests(TestCase):
    """Tests for extract_partial_config function."""

    def test_extract_partial_config__ValidPath__ReturnsSubConfig(self):
        # Arrange
        config = {
            "_target_": "trainer",
            "model": {"_target_": "model", "hidden_size": 256},
            "epochs": 10,
        }
        instance_targets: dict[str, str | None] = {}

        # Act
        sub_config, processed_targets, external_targets = extract_partial_config(
            config=config,
            inner_path="model",
            instance_targets=instance_targets,
        )

        # Assert
        self.assertEqual(sub_config, {"_target_": "model", "hidden_size": 256})
        self.assertEqual(processed_targets, {})
        self.assertEqual(external_targets, set())

    def test_extract_partial_config__NestedPath__ReturnsDeepSubConfig(self):
        # Arrange
        config = {
            "_target_": "trainer",
            "model": {
                "_target_": "model",
                "encoder": {"_target_": "encoder", "layers": 6},
            },
        }
        instance_targets: dict[str, str | None] = {}

        # Act
        sub_config, processed_targets, external_targets = extract_partial_config(
            config=config,
            inner_path="model.encoder",
            instance_targets=instance_targets,
        )

        # Assert
        self.assertEqual(sub_config, {"_target_": "encoder", "layers": 6})

    def test_extract_partial_config__ListIndexPath__ReturnsListElement(self):
        # Arrange
        config = {
            "_target_": "trainer",
            "callbacks": [
                {"_target_": "callback", "name": "first"},
                {"_target_": "callback", "name": "second"},
            ],
        }
        instance_targets: dict[str, str | None] = {}

        # Act
        sub_config, processed_targets, external_targets = extract_partial_config(
            config=config,
            inner_path="callbacks[0]",
            instance_targets=instance_targets,
        )

        # Assert
        self.assertEqual(sub_config, {"_target_": "callback", "name": "first"})

    def test_extract_partial_config__InvalidPath__RaisesInvalidInnerPathError(self):
        # Arrange
        config = {"_target_": "model", "size": 256}
        instance_targets: dict[str, str | None] = {}

        # Act & Assert
        with self.assertRaises(InvalidInnerPathError) as ctx:
            extract_partial_config(
                config=config,
                inner_path="nonexistent",
                instance_targets=instance_targets,
            )

        self.assertEqual(ctx.exception.inner_path, "nonexistent")

    def test_extract_partial_config__PathToNonDict__RaisesInvalidInnerPathError(self):
        # Arrange
        config = {"_target_": "model", "size": 256}
        instance_targets: dict[str, str | None] = {}

        # Act & Assert
        with self.assertRaises(InvalidInnerPathError) as ctx:
            extract_partial_config(
                config=config,
                inner_path="size",
                instance_targets=instance_targets,
            )

        self.assertEqual(ctx.exception.inner_path, "size")
        self.assertIn("int", ctx.exception.reason)

    def test_extract_partial_config__DeepCopiesSubConfig(self):
        # Arrange
        config = {
            "_target_": "trainer",
            "model": {"_target_": "model", "nested": {"value": 42}},
        }
        instance_targets: dict[str, str | None] = {}

        # Act
        sub_config, _, _ = extract_partial_config(
            config=config,
            inner_path="model",
            instance_targets=instance_targets,
        )

        # Modify the extracted config
        sub_config["nested"]["value"] = 100

        # Assert - original should be unchanged
        self.assertEqual(config["model"]["nested"]["value"], 42)


class ProcessInstanceTargetsTests(TestCase):
    """Tests for process_instance_targets function."""

    def test_process_instance_targets__TargetWithinScope__RebasesPath(self):
        # Arrange
        original_targets = {
            "model.encoder": "model.shared_layer",  # Both within "model" scope
        }
        inner_path = "model"

        # Act
        processed, external = process_instance_targets(
            original_targets=original_targets,
            inner_path=inner_path,
        )

        # Assert - paths should be rebased relative to "model"
        self.assertEqual(processed, {"encoder": "shared_layer"})
        self.assertEqual(external, set())

    def test_process_instance_targets__TargetOutsideScope__MarksExternal(self):
        # Arrange
        original_targets = {
            "services.api.db": "shared_db",  # Target is outside "services.api"
        }
        inner_path = "services.api"

        # Act
        processed, external = process_instance_targets(
            original_targets=original_targets,
            inner_path=inner_path,
        )

        # Assert
        self.assertEqual(processed, {"db": "__external__:shared_db"})
        self.assertEqual(external, {"shared_db"})

    def test_process_instance_targets__InstanceOutsideScope__Ignored(self):
        # Arrange
        original_targets = {
            "trainer.model": "shared_model",  # Outside "services" scope
            "services.db": "shared_db",  # Inside "services" scope
        }
        inner_path = "services"

        # Act
        processed, external = process_instance_targets(
            original_targets=original_targets,
            inner_path=inner_path,
        )

        # Assert - only "services.db" is processed, "trainer.model" is ignored
        self.assertEqual(processed, {"db": "__external__:shared_db"})
        self.assertEqual(external, {"shared_db"})

    def test_process_instance_targets__NullTarget__PreservedAsNull(self):
        # Arrange
        original_targets = {
            "model.optional": None,  # _instance_: null
        }
        inner_path = "model"

        # Act
        processed, external = process_instance_targets(
            original_targets=original_targets,
            inner_path=inner_path,
        )

        # Assert
        self.assertEqual(processed, {"optional": None})
        self.assertEqual(external, set())

    def test_process_instance_targets__ExactInnerPath__RebasesToEmpty(self):
        # Arrange
        original_targets = {
            "model": "shared_model",  # Instance IS the inner_path
        }
        inner_path = "model"

        # Act
        processed, external = process_instance_targets(
            original_targets=original_targets,
            inner_path=inner_path,
        )

        # Assert - rebased to empty string (the root of the partial)
        self.assertEqual(processed, {"": "__external__:shared_model"})
        self.assertEqual(external, {"shared_model"})

    def test_process_instance_targets__MultipleInstancesPointingSameExternal__DeduplicatesExternals(
        self,
    ):
        # Arrange
        original_targets = {
            "services.a.cache": "shared_cache",
            "services.b.cache": "shared_cache",  # Same external target
        }
        inner_path = "services"

        # Act
        processed, external = process_instance_targets(
            original_targets=original_targets,
            inner_path=inner_path,
        )

        # Assert
        self.assertEqual(
            processed,
            {
                "a.cache": "__external__:shared_cache",
                "b.cache": "__external__:shared_cache",
            },
        )
        # External targets are deduplicated in the set
        self.assertEqual(external, {"shared_cache"})


class CollectExternalTargetsTests(TestCase):
    """Tests for collect_external_targets function."""

    def test_collect_external_targets__MultipleExternal__ReturnsUniquePaths(self):
        # Arrange
        instance_targets = {
            "a.cache": "__external__:/shared/cache",
            "b.cache": "__external__:/shared/cache",  # Same target
            "c.db": "__external__:/shared/db",  # Different target
            "d.internal": "local",  # Not external
        }

        # Act
        result = collect_external_targets(instance_targets)

        # Assert
        self.assertEqual(result, {"/shared/cache", "/shared/db"})

    def test_collect_external_targets__NoExternals__ReturnsEmptySet(self):
        # Arrange
        instance_targets = {
            "a.ref": "b.target",
            "c.ref": None,
        }

        # Act
        result = collect_external_targets(instance_targets)

        # Assert
        self.assertEqual(result, set())

    def test_collect_external_targets__EmptyTargets__ReturnsEmptySet(self):
        # Arrange
        instance_targets: dict[str, str | None] = {}

        # Act
        result = collect_external_targets(instance_targets)

        # Assert
        self.assertEqual(result, set())
