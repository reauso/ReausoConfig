"""Integration tests for the provenance system.

These tests verify the complete provenance tracking system works end-to-end
using real YAML config files and composition.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from unittest import TestCase

import rconfig as rc
from rconfig.composition import ConfigComposer


# Test dataclasses
@dataclass
class ModelConfig:
    hidden_size: int
    dropout: float = 0.1
    learning_rate: float = 0.001


@dataclass
class TrainerConfig:
    model: ModelConfig
    epochs: int
    learning_rate: float = 0.001


# Path to config files directory
CONFIG_DIR = Path(__file__).parent / "config_files"


class ProvenanceIntegrationTests(TestCase):
    """End-to-end integration tests for provenance tracking."""

    def setUp(self):
        # Clear the store before each test
        rc._store._known_targets.clear()
        # Register test targets
        rc.register("model", ModelConfig)
        rc.register("trainer", TrainerConfig)

    def test_getProvenance__SimpleConfig__TracksAllValues(self):
        """Test that provenance tracks all values in a simple config."""
        # Arrange
        config_path = CONFIG_DIR / "trainer_config.yaml"
        composer = ConfigComposer(config_path)

        # Act
        provenance = composer.compose_with_provenance(config_path)

        # Assert - should have entries for all values
        self.assertIsNotNone(provenance.get("epochs"))
        self.assertIsNotNone(provenance.get("model.hidden_size"))
        self.assertIsNotNone(provenance.get("model.dropout"))

    def test_getProvenance__WithInterpolation__TracksInterpolationSources(self):
        """Test that provenance tracks interpolation sources."""
        # Arrange - use interpolation resolver directly
        from rconfig.provenance import ProvenanceBuilder
        from rconfig.interpolation import resolve_interpolations

        config = {
            "defaults": {"lr": 0.01},
            "model": {"learning_rate": "${/defaults.lr}"},
        }
        builder = ProvenanceBuilder()
        builder.add("defaults.lr", file="config.yaml", line=1)
        builder.add("model.learning_rate", file="config.yaml", line=3)

        # Act
        resolve_interpolations(config, builder)

        # Assert
        entry = builder.get("model.learning_rate")
        self.assertIsNotNone(entry)
        self.assertIsNotNone(entry.interpolation)

    def test_formatProvenance__MinimalPreset__ShowsMinimalOutput(self):
        """Test that minimal preset shows only paths, files, and lines."""
        # Arrange
        config_path = CONFIG_DIR / "trainer_config.yaml"
        composer = ConfigComposer(config_path)
        provenance = composer.compose_with_provenance(config_path)

        # Act
        output = str(rc.format(provenance).minimal())

        # Assert - should have paths and files, no values
        self.assertIn("trainer_config.yaml", output)
        self.assertNotIn(" = ", output)  # Minimal hides values

    def test_formatProvenance__CompactPreset__ShowsValueAndLocation(self):
        """Test that compact preset shows values and locations."""
        # Arrange
        config_path = CONFIG_DIR / "trainer_config.yaml"
        composer = ConfigComposer(config_path)
        provenance = composer.compose_with_provenance(config_path)

        # Act
        output = str(rc.format(provenance).compact())

        # Assert - should have values and files
        self.assertIn("trainer_config.yaml", output)
        # Should include some value from config
        self.assertTrue(
            "10" in output or "256" in output or "0.2" in output,
            f"Expected to find config values in output: {output}"
        )

    def test_formatProvenance__FullPreset__ShowsEverything(self):
        """Test that full preset shows all information."""
        # Arrange
        config_path = CONFIG_DIR / "trainer_config.yaml"
        composer = ConfigComposer(config_path)
        provenance = composer.compose_with_provenance(config_path)

        # Act
        output = str(rc.format(provenance).full())

        # Assert - should have paths, values, and files
        self.assertIn("trainer_config.yaml", output)
        self.assertIn("/", output)  # Path prefixes

    def test_formatProvenance__WithFilters__FiltersCorrectly(self):
        """Test that path filter correctly filters output."""
        # Arrange
        config_path = CONFIG_DIR / "trainer_config.yaml"
        composer = ConfigComposer(config_path)
        provenance = composer.compose_with_provenance(config_path)

        # Act
        output = str(rc.format(provenance).for_path("/model.*"))

        # Assert - should only have model paths
        self.assertIn("/model", output)
        # epochs is at root level, should not appear
        self.assertNotIn("/epochs", output)

    def test_toDict__FullConfig__JSONSerializable(self):
        """Test that to_dict() output is JSON serializable."""
        # Arrange
        config_path = CONFIG_DIR / "trainer_config.yaml"
        composer = ConfigComposer(config_path)
        provenance = composer.compose_with_provenance(config_path)

        # Act
        prov_dict = provenance.to_dict()

        # Assert - should be JSON serializable
        try:
            json_str = json.dumps(prov_dict)
            self.assertIsInstance(json_str, str)
        except (TypeError, ValueError) as e:
            self.fail(f"Provenance dict is not JSON serializable: {e}")

    def test_toDict__HasExpectedStructure(self):
        """Test that to_dict() has the expected structure."""
        # Arrange
        config_path = CONFIG_DIR / "trainer_config.yaml"
        composer = ConfigComposer(config_path)
        provenance = composer.compose_with_provenance(config_path)

        # Act
        prov_dict = provenance.to_dict()

        # Assert - should have entries for config paths
        self.assertIn("epochs", prov_dict)
        self.assertIn("file", prov_dict["epochs"])
        self.assertIn("line", prov_dict["epochs"])

    def test_trace__BasicEntry__ReturnsNode(self):
        """Test that trace() returns a provenance node."""
        # Arrange
        config_path = CONFIG_DIR / "trainer_config.yaml"
        composer = ConfigComposer(config_path)
        provenance = composer.compose_with_provenance(config_path)

        # Act
        node = provenance.trace("epochs")

        # Assert
        self.assertIsNotNone(node)
        self.assertEqual("file", node.source_type)
        self.assertIn("trainer_config", node.file)

    def test_trace__NonexistentPath__ReturnsNone(self):
        """Test that trace() returns None for missing path."""
        # Arrange
        config_path = CONFIG_DIR / "trainer_config.yaml"
        composer = ConfigComposer(config_path)
        provenance = composer.compose_with_provenance(config_path)

        # Act
        node = provenance.trace("nonexistent.path")

        # Assert
        self.assertIsNone(node)

    def test_presetEnum__Minimal__MatchesMinimalMethod(self):
        """Test that enum preset matches method preset."""
        # Arrange
        config_path = CONFIG_DIR / "trainer_config.yaml"
        composer = ConfigComposer(config_path)
        provenance = composer.compose_with_provenance(config_path)

        # Act
        method_output = str(rc.format(provenance).minimal())
        string_output = str(rc.format(provenance).preset("minimal"))

        # Assert
        self.assertEqual(method_output, string_output)

    def test_presetString__Full__MatchesFullMethod(self):
        """Test that string preset matches method preset."""
        # Arrange
        config_path = CONFIG_DIR / "trainer_config.yaml"
        composer = ConfigComposer(config_path)
        provenance = composer.compose_with_provenance(config_path)

        # Act
        method_output = str(rc.format(provenance).full())
        string_output = str(rc.format(provenance).preset("full"))

        # Assert
        self.assertEqual(method_output, string_output)

    def test_setConfig__PopulatesValues(self):
        """Test that set_config populates entry values."""
        # Arrange
        config_path = CONFIG_DIR / "trainer_config.yaml"
        composer = ConfigComposer(config_path)
        provenance = composer.compose_with_provenance(config_path)

        # Assert - values should be populated
        epochs_entry = provenance.get("epochs")
        self.assertIsNotNone(epochs_entry.value)
        self.assertEqual(10, epochs_entry.value)

    def test_entryToDict__IncludesAllFields(self):
        """Test that entry to_dict includes all expected fields."""
        # Arrange
        config_path = CONFIG_DIR / "trainer_config.yaml"
        composer = ConfigComposer(config_path)
        provenance = composer.compose_with_provenance(config_path)

        # Act
        entry = provenance.get("epochs")
        entry_dict = entry.to_dict()

        # Assert
        self.assertIn("file", entry_dict)
        self.assertIn("line", entry_dict)
        self.assertIn("value", entry_dict)
        self.assertEqual(10, entry_dict["value"])


class ProvenanceWithOverridesIntegrationTests(TestCase):
    """Integration tests for provenance with overrides."""

    def setUp(self):
        # Clear the store before each test
        rc._store._known_targets.clear()
        rc.register("model", ModelConfig)
        rc.register("trainer", TrainerConfig)

    def test_applyOverrides__TracksCliSource(self):
        """Test that CLI overrides are tracked in provenance."""
        # Arrange
        from rconfig.override import Override, apply_overrides
        from rconfig.provenance import ProvenanceBuilder

        config = {"lr": 0.1, "epochs": 10}
        builder = ProvenanceBuilder()
        builder.add("lr", file="config.yaml", line=1)
        builder.add("epochs", file="config.yaml", line=2)

        overrides = [
            Override(
                path=["lr"],
                value=0.01,
                operation="set",
                source_type="cli",
                cli_arg="lr=0.01",
            )
        ]

        # Act
        apply_overrides(config, overrides, builder)

        # Assert
        entry = builder.get("lr")
        self.assertEqual("cli", entry.source_type)
        self.assertEqual("lr=0.01", entry.cli_arg)
        self.assertEqual("config.yaml:1", entry.overrode)

    def test_formatProvenance__WithCliOverride__ShowsCliSource(self):
        """Test that CLI override is shown in formatted output."""
        # Arrange
        from rconfig.override import Override, apply_overrides
        from rconfig.provenance import ProvenanceBuilder

        builder = ProvenanceBuilder()
        builder.add("lr", file="config.yaml", line=1, value=0.1)

        overrides = [
            Override(
                path=["lr"],
                value=0.01,
                operation="set",
                source_type="cli",
                cli_arg="lr=0.01",
            )
        ]
        apply_overrides({"lr": 0.1}, overrides, builder)
        provenance = builder.build()

        # Act
        output = str(rc.format(provenance).full())

        # Assert
        self.assertIn("CLI", output)
        self.assertIn("lr=0.01", output)


class ProvenanceWithInterpolationIntegrationTests(TestCase):
    """Integration tests for provenance with interpolation."""

    def test_resolveInterpolations__TracksInterpolationSource(self):
        """Test that interpolation sources are tracked."""
        # Arrange - use interpolation resolver directly
        from rconfig.provenance import ProvenanceBuilder
        from rconfig.interpolation import resolve_interpolations

        config = {
            "defaults": {"lr": 0.01},
            "model": {"learning_rate": "${/defaults.lr}"},
        }
        builder = ProvenanceBuilder()
        builder.add("defaults.lr", file="config.yaml", line=1)
        builder.add("model.learning_rate", file="config.yaml", line=3)

        # Act
        resolve_interpolations(config, builder)

        # Assert
        entry = builder.get("model.learning_rate")
        self.assertIsNotNone(entry)
        self.assertEqual(0.01, entry.value)
        self.assertIsNotNone(entry.interpolation)

    def test_resolveInterpolations__TracksExpressionOperator(self):
        """Test that expression operators are tracked."""
        # Arrange - use interpolation resolver directly
        from rconfig.provenance import ProvenanceBuilder
        from rconfig.interpolation import resolve_interpolations

        config = {
            "base_lr": 0.01,
            "model": {"learning_rate": "${/base_lr * 2}"},
        }
        builder = ProvenanceBuilder()
        builder.add("base_lr", file="config.yaml", line=1)
        builder.add("model.learning_rate", file="config.yaml", line=3)

        # Act
        resolve_interpolations(config, builder)

        # Assert
        entry = builder.get("model.learning_rate")
        self.assertIsNotNone(entry)
        self.assertEqual(0.02, entry.value)
        self.assertIsNotNone(entry.interpolation)
        self.assertEqual("*", entry.interpolation.operator)


class ProvenanceTargetIntegrationTests(TestCase):
    """Integration tests for provenance target info tracking."""

    def setUp(self):
        # Clear the store before each test
        rc._store._known_targets.clear()
        # Register test targets
        rc.register("model", ModelConfig)
        rc.register("trainer", TrainerConfig)

    def test_getProvenance__SimpleConfig__ShowsTargetInfo(self):
        """Test that get_provenance shows target class info for registered targets."""
        # Arrange
        config_path = CONFIG_DIR / "trainer_config.yaml"

        # Act
        prov = rc.get_provenance(config_path)

        # Assert
        entry = prov.get("")  # Root entry
        self.assertIsNotNone(entry)
        self.assertEqual("trainer", entry.target_name)
        self.assertEqual("TrainerConfig", entry.target_class)
        self.assertIn("provenance_integration_test", entry.target_module)

    def test_getProvenance__NestedConfigs__ShowsAllTargets(self):
        """Test that all nested targets get their info resolved."""
        # Arrange
        config_path = CONFIG_DIR / "trainer_config.yaml"

        # Act
        prov = rc.get_provenance(config_path)

        # Assert
        root_entry = prov.get("")
        self.assertEqual("TrainerConfig", root_entry.target_class)

        model_entry = prov.get("model")
        self.assertEqual("model", model_entry.target_name)
        self.assertEqual("ModelConfig", model_entry.target_class)

    def test_getProvenance__UnregisteredTarget__ShowsNotRegisteredInFormat(self):
        """Test that unregistered targets show 'not registered' when formatted."""
        # Arrange - clear registrations and use a config with unknown target
        rc._store._known_targets.clear()
        config_path = CONFIG_DIR / "trainer_config.yaml"

        # Act
        prov = rc.get_provenance(config_path)
        output = str(rc.format(prov).compact())

        # Assert - the target name is captured but not resolved
        root_entry = prov.get("")
        self.assertEqual("trainer", root_entry.target_name)
        self.assertIsNone(root_entry.target_class)
        # The formatted output should show "not registered"
        self.assertIn("(not registered)", output)

    def test_getProvenance__FormatMinimal__HidesTargets(self):
        """Test that minimal preset hides target info."""
        # Arrange
        config_path = CONFIG_DIR / "trainer_config.yaml"

        # Act
        prov = rc.get_provenance(config_path)
        output = str(rc.format(prov).minimal())

        # Assert
        self.assertNotIn("Target:", output)

    def test_getProvenance__FormatFull__ShowsTargets(self):
        """Test that full preset shows target info."""
        # Arrange
        config_path = CONFIG_DIR / "trainer_config.yaml"

        # Act
        prov = rc.get_provenance(config_path)
        output = str(rc.format(prov).full())

        # Assert
        self.assertIn("Target:", output)
        self.assertIn("TrainerConfig", output)


class GetProvenanceWithOverridesIntegrationTests(TestCase):
    """Integration tests for rc.get_provenance() with overrides and cli_overrides."""

    def setUp(self):
        rc._store._known_targets.clear()
        rc.register("model", ModelConfig)
        rc.register("trainer", TrainerConfig)

    def test_getProvenance__WithOverrides__ReflectsOverriddenValues(self):
        """Test that provenance shows overridden values."""
        # Arrange
        config_path = CONFIG_DIR / "trainer_config.yaml"

        # Act
        prov = rc.get_provenance(
            config_path,
            overrides={"epochs": 100},
            cli_overrides=False,
        )

        # Assert
        entry = prov.get("epochs")
        self.assertIsNotNone(entry)
        self.assertEqual(entry.value, 100)

    def test_getProvenance__WithNestedOverrides__AppliesNestedOverride(self):
        """Test that nested path overrides work in provenance."""
        # Arrange
        config_path = CONFIG_DIR / "trainer_config.yaml"

        # Act
        prov = rc.get_provenance(
            config_path,
            overrides={"model.hidden_size": 1024},
            cli_overrides=False,
        )

        # Assert
        entry = prov.get("model.hidden_size")
        self.assertIsNotNone(entry)
        self.assertEqual(entry.value, 1024)

    def test_getProvenance__WithInnerPathAndOverrides__CombinesBoth(self):
        """Test using both inner_path and overrides together."""
        # Arrange
        config_path = CONFIG_DIR / "trainer_config.yaml"

        # Act - inner_path controls lazy loading, but provenance still has full paths
        prov = rc.get_provenance(
            config_path,
            inner_path="model",
            overrides={"model.hidden_size": 512},
            cli_overrides=False,
        )

        # Assert - provenance should show overridden value
        entry = prov.get("model.hidden_size")
        self.assertIsNotNone(entry)
        self.assertEqual(entry.value, 512)


class ValidateWithInnerPathIntegrationTests(TestCase):
    """Integration tests for rc.validate() with inner_path parameter."""

    def setUp(self):
        rc._store._known_targets.clear()
        rc.register("model", ModelConfig)
        rc.register("trainer", TrainerConfig)

    def test_validate__InnerPathWithRef__ValidatesReferencedSection(self):
        """Test validate with inner_path on a config that uses _ref_."""
        # Arrange
        config_path = CONFIG_DIR / "trainer_with_ref.yaml"

        # Act
        result = rc.validate(
            config_path,
            inner_path="model",
            cli_overrides=False,
        )

        # Assert
        self.assertTrue(result.valid)

    def test_validate__InnerPathWithOverrides__AppliesOverridesFirst(self):
        """Test that overrides are applied before inner_path extraction."""
        # Arrange
        config_path = CONFIG_DIR / "trainer_config.yaml"

        # Act
        result = rc.validate(
            config_path,
            inner_path="model",
            overrides={"model.hidden_size": 2048},
            cli_overrides=False,
        )

        # Assert - validation should pass (override is valid)
        self.assertTrue(result.valid)
