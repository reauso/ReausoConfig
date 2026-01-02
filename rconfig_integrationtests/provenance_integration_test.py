"""Integration tests for the provenance system.

These tests verify the complete provenance tracking system works end-to-end
using real YAML config files and composition.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from unittest import TestCase

import rconfig as rc
from rconfig.composition import ConfigComposer, ProvenancePreset


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
        rc._store._known_references.clear()
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
        from rconfig.composition import Provenance
        from rconfig.interpolation import resolve_interpolations

        config = {
            "defaults": {"lr": 0.01},
            "model": {"learning_rate": "${/defaults.lr}"},
        }
        provenance = Provenance()
        provenance.add("defaults.lr", "config.yaml", 1)
        provenance.add("model.learning_rate", "config.yaml", 3)

        # Act
        resolve_interpolations(config, provenance)

        # Assert
        entry = provenance.get("model.learning_rate")
        self.assertIsNotNone(entry)
        self.assertIsNotNone(entry.interpolation)

    def test_formatProvenance__MinimalPreset__ShowsMinimalOutput(self):
        """Test that minimal preset shows only paths, files, and lines."""
        # Arrange
        config_path = CONFIG_DIR / "trainer_config.yaml"
        composer = ConfigComposer(config_path)
        provenance = composer.compose_with_provenance(config_path)

        # Act
        output = str(provenance.format().minimal())

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
        output = str(provenance.format().compact())

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
        output = str(provenance.format().full())

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
        output = str(provenance.format().for_path("/model.*"))

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
        method_output = str(provenance.format().minimal())
        enum_output = str(provenance.format().preset(ProvenancePreset.MINIMAL))

        # Assert
        self.assertEqual(method_output, enum_output)

    def test_presetEnum__Full__MatchesFullMethod(self):
        """Test that enum preset matches method preset."""
        # Arrange
        config_path = CONFIG_DIR / "trainer_config.yaml"
        composer = ConfigComposer(config_path)
        provenance = composer.compose_with_provenance(config_path)

        # Act
        method_output = str(provenance.format().full())
        enum_output = str(provenance.format().preset(ProvenancePreset.FULL))

        # Assert
        self.assertEqual(method_output, enum_output)

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
        rc._store._known_references.clear()
        rc.register("model", ModelConfig)
        rc.register("trainer", TrainerConfig)

    def test_applyOverrides__TracksCliSource(self):
        """Test that CLI overrides are tracked in provenance."""
        # Arrange
        from rconfig.override import Override, apply_overrides
        from rconfig.composition import Provenance, ProvenanceEntry

        config = {"lr": 0.1, "epochs": 10}
        provenance = Provenance()
        provenance.add("lr", "config.yaml", 1)
        provenance.add("epochs", "config.yaml", 2)

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
        apply_overrides(config, overrides, provenance)

        # Assert
        entry = provenance.get("lr")
        self.assertEqual("cli", entry.source_type)
        self.assertEqual("lr=0.01", entry.cli_arg)
        self.assertEqual("config.yaml:1", entry.overrode)

    def test_formatProvenance__WithCliOverride__ShowsCliSource(self):
        """Test that CLI override is shown in formatted output."""
        # Arrange
        from rconfig.override import Override, apply_overrides
        from rconfig.composition import Provenance, ProvenanceEntry

        provenance = Provenance()
        provenance.add("lr", "config.yaml", 1)
        provenance._entries["lr"].value = 0.1

        overrides = [
            Override(
                path=["lr"],
                value=0.01,
                operation="set",
                source_type="cli",
                cli_arg="lr=0.01",
            )
        ]
        apply_overrides({"lr": 0.1}, overrides, provenance)

        # Act
        output = str(provenance.format().full())

        # Assert
        self.assertIn("CLI", output)
        self.assertIn("lr=0.01", output)


class ProvenanceWithInterpolationIntegrationTests(TestCase):
    """Integration tests for provenance with interpolation."""

    def test_resolveInterpolations__TracksInterpolationSource(self):
        """Test that interpolation sources are tracked."""
        # Arrange - use interpolation resolver directly
        from rconfig.composition import Provenance
        from rconfig.interpolation import resolve_interpolations

        config = {
            "defaults": {"lr": 0.01},
            "model": {"learning_rate": "${/defaults.lr}"},
        }
        provenance = Provenance()
        provenance.add("defaults.lr", "config.yaml", 1)
        provenance.add("model.learning_rate", "config.yaml", 3)

        # Act
        resolve_interpolations(config, provenance)

        # Assert
        entry = provenance.get("model.learning_rate")
        self.assertIsNotNone(entry)
        self.assertEqual(0.01, entry.value)
        self.assertIsNotNone(entry.interpolation)

    def test_resolveInterpolations__TracksExpressionOperator(self):
        """Test that expression operators are tracked."""
        # Arrange - use interpolation resolver directly
        from rconfig.composition import Provenance
        from rconfig.interpolation import resolve_interpolations

        config = {
            "base_lr": 0.01,
            "model": {"learning_rate": "${/base_lr * 2}"},
        }
        provenance = Provenance()
        provenance.add("base_lr", "config.yaml", 1)
        provenance.add("model.learning_rate", "config.yaml", 3)

        # Act
        resolve_interpolations(config, provenance)

        # Assert
        entry = provenance.get("model.learning_rate")
        self.assertIsNotNone(entry)
        self.assertEqual(0.02, entry.value)
        self.assertIsNotNone(entry.interpolation)
        self.assertEqual("*", entry.interpolation.operator)


class ProvenanceTargetIntegrationTests(TestCase):
    """Integration tests for provenance target info tracking."""

    def setUp(self):
        # Clear the store before each test
        rc._store._known_references.clear()
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
        rc._store._known_references.clear()
        config_path = CONFIG_DIR / "trainer_config.yaml"

        # Act
        prov = rc.get_provenance(config_path)
        output = str(prov.format().compact())

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
        output = str(prov.format().minimal())

        # Assert
        self.assertNotIn("Target:", output)

    def test_getProvenance__FormatFull__ShowsTargets(self):
        """Test that full preset shows target info."""
        # Arrange
        config_path = CONFIG_DIR / "trainer_config.yaml"

        # Act
        prov = rc.get_provenance(config_path)
        output = str(prov.format().full())

        # Assert
        self.assertIn("Target:", output)
        self.assertIn("TrainerConfig", output)
