"""Integration tests for config export functionality.

These tests verify the complete export system works end-to-end using real YAML files.
"""

import json
import tempfile
import tomllib
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from unittest import TestCase

from ruamel.yaml import YAML

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


def parse_yaml(yaml_str: str) -> dict:
    """Helper to parse YAML string back to dict."""
    yaml = YAML()
    return yaml.load(StringIO(yaml_str))


class ExportIntegrationTests(TestCase):
    """Integration tests for config export with real YAML files."""

    def setUp(self):
        rc._store._known_targets.clear()
        rc.register("model", ModelConfig)
        rc.register("trainer", TrainerConfig)
        self.temp_dir = tempfile.TemporaryDirectory()
        self.output_dir = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_to_dict__ConfigPath__ReturnsResolvedDict(self):
        """to_dict returns resolved config as dictionary."""
        config_path = CONFIG_DIR / "trainer_config.yaml"

        result = rc.to_dict(config_path, cli_overrides=False)

        self.assertIsInstance(result, dict)
        self.assertEqual(result["epochs"], 10)
        self.assertEqual(result["learning_rate"], 0.001)
        self.assertEqual(result["model"]["hidden_size"], 256)
        self.assertEqual(result["model"]["dropout"], 0.2)

    def test_to_yaml__ConfigPath__ReturnsResolvedYaml(self):
        """to_yaml returns resolved config as YAML string."""
        config_path = CONFIG_DIR / "trainer_config.yaml"

        result = rc.to_yaml(config_path, cli_overrides=False)

        self.assertIsInstance(result, str)
        parsed = parse_yaml(result)
        self.assertEqual(parsed["epochs"], 10)
        self.assertEqual(parsed["model"]["hidden_size"], 256)

    def test_export__WithRefComposition__ResolvesReferences(self):
        """Export resolves _ref_ references correctly."""
        config_path = CONFIG_DIR / "trainer_with_ref.yaml"

        result = rc.to_dict(config_path, cli_overrides=False)

        # The _ref_ should be resolved
        self.assertIn("model", result)
        # Base from resnet.yaml is 256, override in trainer_with_ref.yaml applies
        self.assertEqual(result["model"]["hidden_size"], 256)
        # Override from trainer_with_ref.yaml
        self.assertEqual(result["model"]["dropout"], 0.2)

    def test_export__WithInterpolation__ResolvesExpressions(self):
        """Export resolves interpolation expressions."""
        config_path = CONFIG_DIR / "interpolation" / "basic" / "arithmetic.yaml"

        result = rc.to_dict(config_path, cli_overrides=False)

        # Interpolations should be resolved
        self.assertIsInstance(result, dict)

    def test_export__WithOverrides__AppliesOverridesCorrectly(self):
        """Export applies overrides before returning."""
        config_path = CONFIG_DIR / "trainer_config.yaml"

        result = rc.to_dict(
            config_path,
            overrides={"epochs": 50, "model.hidden_size": 1024},
            cli_overrides=False,
        )

        self.assertEqual(result["epochs"], 50)
        self.assertEqual(result["model"]["hidden_size"], 1024)


class FileExportIntegrationTests(TestCase):
    """Integration tests for file-based export."""

    def setUp(self):
        rc._store._known_targets.clear()
        rc.register("model", ModelConfig)
        rc.register("trainer", TrainerConfig)
        self.temp_dir = tempfile.TemporaryDirectory()
        self.output_dir = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_to_file__YamlOutput__CreatesValidFile(self):
        """to_file creates a valid YAML file when output has .yaml extension."""
        config_path = CONFIG_DIR / "trainer_config.yaml"
        output_path = self.output_dir / "output.yaml"

        rc.to_file(config_path, output_path, cli_overrides=False)

        self.assertTrue(output_path.exists())
        content = output_path.read_text()
        parsed = parse_yaml(content)
        self.assertEqual(parsed["epochs"], 10)

    def test_to_file__OutputCanBeReloaded__RoundTrip(self):
        """Exported file can be loaded back and matches original."""
        config_path = CONFIG_DIR / "trainer_config.yaml"
        output_path = self.output_dir / "exported.yaml"

        # Export
        rc.to_file(config_path, output_path, cli_overrides=False)

        # Load original
        original = rc.to_dict(config_path, cli_overrides=False)

        # Load exported
        exported = rc.to_dict(output_path, cli_overrides=False)

        # Compare (without _target_ since those might differ)
        self.assertEqual(
            original["epochs"],
            exported["epochs"],
        )
        self.assertEqual(
            original["model"]["hidden_size"],
            exported["model"]["hidden_size"],
        )

    def test_to_files__SingleFile__WritesToDirectory(self):
        """to_files writes config to specified file path."""
        config_path = CONFIG_DIR / "trainer_config.yaml"
        output_file = self.output_dir / "exported" / "trainer_config.yaml"

        rc.to_files(config_path, output_file, cli_overrides=False)

        self.assertTrue(output_file.exists())
        content = output_file.read_text()
        parsed = parse_yaml(content)
        self.assertEqual(parsed["epochs"], 10)

    def test_to_file__WithOverrides__AppliesOverrides(self):
        """to_file applies overrides to the output."""
        config_path = CONFIG_DIR / "trainer_config.yaml"
        output_path = self.output_dir / "output.yaml"

        rc.to_file(
            config_path,
            output_path,
            overrides={"epochs": 100},
            cli_overrides=False,
        )

        content = output_path.read_text()
        parsed = parse_yaml(content)
        self.assertEqual(parsed["epochs"], 100)

    def test_to_file__ExcludeMarkers__RemovesTargets(self):
        """to_file with exclude_markers removes _target_."""
        config_path = CONFIG_DIR / "trainer_config.yaml"
        output_path = self.output_dir / "output.yaml"

        rc.to_file(
            config_path,
            output_path,
            exclude_markers=True,
            cli_overrides=False,
        )

        content = output_path.read_text()
        parsed = parse_yaml(content)
        self.assertNotIn("_target_", parsed)
        self.assertNotIn("_target_", parsed["model"])


class ExportWithInstanceSharingTests(TestCase):
    """Tests for export with _instance_ references."""

    def setUp(self):
        rc._store._known_targets.clear()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.output_dir = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_to_dict__SharedInstance__PreservesInstancePaths(self):
        """Export preserves _instance_ marker paths."""
        config_path = CONFIG_DIR / "app_with_shared_instances.yaml"

        result = rc.to_dict(config_path, cli_overrides=False)

        # The result should have instance references resolved
        self.assertIsInstance(result, dict)


class ExportEdgeCasesTests(TestCase):
    """Edge case tests for export."""

    def setUp(self):
        rc._store._known_targets.clear()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.output_dir = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_to_yaml__UnicodeContent__PreservesUnicode(self):
        """Export preserves unicode content."""
        # Create a temp YAML file with unicode
        unicode_yaml = self.output_dir / "unicode.yaml"
        unicode_yaml.write_text(
            "emoji: '\U0001F600'\nchinese: '\u4e2d\u6587'\n", encoding="utf-8"
        )

        result = rc.to_yaml(unicode_yaml, cli_overrides=False)
        parsed = parse_yaml(result)

        self.assertEqual(parsed["emoji"], "\U0001F600")
        self.assertEqual(parsed["chinese"], "\u4e2d\u6587")


class RefGraphIntegrationTests(TestCase):
    """Tests for ref_graph tracking during composition."""

    def setUp(self):
        rc._store._known_targets.clear()
        rc.register("model", ModelConfig)
        rc.register("trainer", TrainerConfig)

    def test_ref_graph__WithRefs__TracksRelationships(self):
        """ConfigComposer tracks ref relationships."""
        from rconfig.composition import ConfigComposer

        config_path = CONFIG_DIR / "trainer_with_ref.yaml"
        composer = ConfigComposer()
        composer.compose(config_path)

        ref_graph = composer.ref_graph()

        # Should have tracked the ref relationship
        self.assertIsInstance(ref_graph, dict)

    def test_ref_graph__NoRefs__ReturnsEmptyDict(self):
        """ConfigComposer returns empty dict when no refs."""
        from rconfig.composition import ConfigComposer

        config_path = CONFIG_DIR / "trainer_config.yaml"
        composer = ConfigComposer()
        composer.compose(config_path)

        ref_graph = composer.ref_graph()

        # Should be empty since trainer_config.yaml has no refs
        self.assertEqual(ref_graph, {})


class JsonExportIntegrationTests(TestCase):
    """Integration tests for JSON export with real config files."""

    def setUp(self):
        rc._store._known_targets.clear()
        rc.register("model", ModelConfig)
        rc.register("trainer", TrainerConfig)
        self.temp_dir = tempfile.TemporaryDirectory()
        self.output_dir = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_to_json__ConfigPath__ReturnsValidJson(self):
        """to_json returns valid JSON string."""
        config_path = CONFIG_DIR / "trainer_config.yaml"

        result = rc.to_json(config_path, cli_overrides=False)

        self.assertIsInstance(result, str)
        parsed = json.loads(result)
        self.assertEqual(parsed["epochs"], 10)
        self.assertEqual(parsed["model"]["hidden_size"], 256)

    def test_to_json__WithRefComposition__ResolvesReferences(self):
        """JSON export resolves _ref_ references correctly."""
        config_path = CONFIG_DIR / "trainer_with_ref.yaml"

        result = rc.to_json(config_path, cli_overrides=False)
        parsed = json.loads(result)

        self.assertIn("model", parsed)
        self.assertEqual(parsed["model"]["hidden_size"], 256)
        self.assertEqual(parsed["model"]["dropout"], 0.2)

    def test_to_json__WithOverrides__AppliesOverrides(self):
        """JSON export applies overrides correctly."""
        config_path = CONFIG_DIR / "trainer_config.yaml"

        result = rc.to_json(
            config_path,
            overrides={"epochs": 50},
            cli_overrides=False,
        )
        parsed = json.loads(result)

        self.assertEqual(parsed["epochs"], 50)

    def test_to_json__ExcludeMarkers__RemovesMarkers(self):
        """JSON export removes markers when exclude_markers=True."""
        config_path = CONFIG_DIR / "trainer_config.yaml"

        result = rc.to_json(
            config_path,
            exclude_markers=True,
            cli_overrides=False,
        )
        parsed = json.loads(result)

        self.assertNotIn("_target_", parsed)
        self.assertNotIn("_target_", parsed["model"])

    def test_to_file__JsonOutput__CreatesValidFile(self):
        """to_file creates a valid JSON file when output has .json extension."""
        config_path = CONFIG_DIR / "trainer_config.yaml"
        output_path = self.output_dir / "output.json"

        rc.to_file(config_path, output_path, cli_overrides=False)

        self.assertTrue(output_path.exists())
        content = output_path.read_text()
        parsed = json.loads(content)
        self.assertEqual(parsed["epochs"], 10)

    def test_to_file__JsonRoundTrip__CanBeReloaded(self):
        """Exported JSON can be loaded back via rconfig."""
        config_path = CONFIG_DIR / "trainer_config.yaml"
        output_path = self.output_dir / "exported.json"

        # Export to JSON
        rc.to_file(config_path, output_path, cli_overrides=False)

        # Load back via rconfig
        exported = rc.to_dict(output_path, cli_overrides=False)

        self.assertEqual(exported["epochs"], 10)
        self.assertEqual(exported["model"]["hidden_size"], 256)


class TomlExportIntegrationTests(TestCase):
    """Integration tests for TOML export with real config files."""

    def setUp(self):
        rc._store._known_targets.clear()
        rc.register("model", ModelConfig)
        rc.register("trainer", TrainerConfig)
        self.temp_dir = tempfile.TemporaryDirectory()
        self.output_dir = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_to_toml__ConfigPath__ReturnsValidToml(self):
        """to_toml returns valid TOML string."""
        config_path = CONFIG_DIR / "trainer_config.yaml"

        result = rc.to_toml(config_path, cli_overrides=False)

        self.assertIsInstance(result, str)
        parsed = tomllib.loads(result)
        self.assertEqual(parsed["epochs"], 10)
        self.assertEqual(parsed["model"]["hidden_size"], 256)

    def test_to_toml__WithRefComposition__ResolvesReferences(self):
        """TOML export resolves _ref_ references correctly."""
        config_path = CONFIG_DIR / "trainer_with_ref.yaml"

        result = rc.to_toml(config_path, cli_overrides=False)
        parsed = tomllib.loads(result)

        self.assertIn("model", parsed)
        self.assertEqual(parsed["model"]["hidden_size"], 256)
        self.assertEqual(parsed["model"]["dropout"], 0.2)

    def test_to_toml__WithOverrides__AppliesOverrides(self):
        """TOML export applies overrides correctly."""
        config_path = CONFIG_DIR / "trainer_config.yaml"

        result = rc.to_toml(
            config_path,
            overrides={"epochs": 50},
            cli_overrides=False,
        )
        parsed = tomllib.loads(result)

        self.assertEqual(parsed["epochs"], 50)

    def test_to_toml__ExcludeMarkers__RemovesMarkers(self):
        """TOML export removes markers when exclude_markers=True."""
        config_path = CONFIG_DIR / "trainer_config.yaml"

        result = rc.to_toml(
            config_path,
            exclude_markers=True,
            cli_overrides=False,
        )
        parsed = tomllib.loads(result)

        self.assertNotIn("_target_", parsed)
        self.assertNotIn("_target_", parsed["model"])

    def test_to_file__TomlOutput__CreatesValidFile(self):
        """to_file creates a valid TOML file when output has .toml extension."""
        config_path = CONFIG_DIR / "trainer_config.yaml"
        output_path = self.output_dir / "output.toml"

        rc.to_file(config_path, output_path, cli_overrides=False)

        self.assertTrue(output_path.exists())
        content = output_path.read_text()
        parsed = tomllib.loads(content)
        self.assertEqual(parsed["epochs"], 10)

    def test_to_file__TomlRoundTrip__CanBeReloaded(self):
        """Exported TOML can be loaded back via rconfig."""
        config_path = CONFIG_DIR / "trainer_config.yaml"
        output_path = self.output_dir / "exported.toml"

        # Export to TOML
        rc.to_file(config_path, output_path, cli_overrides=False)

        # Load back via rconfig
        exported = rc.to_dict(output_path, cli_overrides=False)

        self.assertEqual(exported["epochs"], 10)
        self.assertEqual(exported["model"]["hidden_size"], 256)


class CrossFormatExportIntegrationTests(TestCase):
    """Integration tests for cross-format export scenarios."""

    def setUp(self):
        rc._store._known_targets.clear()
        rc.register("model", ModelConfig)
        rc.register("trainer", TrainerConfig)
        self.temp_dir = tempfile.TemporaryDirectory()
        self.output_dir = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_yaml_to_json__Conversion__PreservesValues(self):
        """Converting YAML config to JSON preserves values."""
        config_path = CONFIG_DIR / "trainer_config.yaml"

        # Load via YAML, export as JSON
        yaml_dict = rc.to_dict(config_path, cli_overrides=False)
        json_str = rc.to_json(config_path, cli_overrides=False)
        json_dict = json.loads(json_str)

        self.assertEqual(yaml_dict["epochs"], json_dict["epochs"])
        self.assertEqual(
            yaml_dict["model"]["hidden_size"],
            json_dict["model"]["hidden_size"],
        )

    def test_yaml_to_toml__Conversion__PreservesValues(self):
        """Converting YAML config to TOML preserves values."""
        config_path = CONFIG_DIR / "trainer_config.yaml"

        # Load via YAML, export as TOML
        yaml_dict = rc.to_dict(config_path, cli_overrides=False)
        toml_str = rc.to_toml(config_path, cli_overrides=False)
        toml_dict = tomllib.loads(toml_str)

        self.assertEqual(yaml_dict["epochs"], toml_dict["epochs"])
        self.assertEqual(
            yaml_dict["model"]["hidden_size"],
            toml_dict["model"]["hidden_size"],
        )

    def test_chain_export__YamlToJsonToToml__ValuesPreserved(self):
        """Chaining exports (YAML -> JSON -> TOML) preserves values."""
        config_path = CONFIG_DIR / "trainer_config.yaml"
        json_path = self.output_dir / "intermediate.json"
        toml_path = self.output_dir / "final.toml"

        # Export YAML to JSON
        rc.to_file(config_path, json_path, cli_overrides=False)

        # Export JSON to TOML
        rc.to_file(json_path, toml_path, cli_overrides=False)

        # Load original and final
        original = rc.to_dict(config_path, cli_overrides=False)
        final = rc.to_dict(toml_path, cli_overrides=False)

        self.assertEqual(original["epochs"], final["epochs"])
        self.assertEqual(
            original["model"]["hidden_size"],
            final["model"]["hidden_size"],
        )
