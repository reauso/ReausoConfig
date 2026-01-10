"""Tests for rconfig.export.multi_file_exporter module."""

import json
import tempfile
import tomllib
from io import StringIO
from pathlib import Path
from unittest import TestCase

from ruamel.yaml import YAML

from rconfig.errors import ConfigFileError
from rconfig.export.multi_file_exporter import MultiFileExporter


class MultiFileExporterTests(TestCase):
    """Tests for MultiFileExporter."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.output_dir = Path(self.temp_dir.name)

    def tearDown(self):
        """Clean up test fixtures."""
        self.temp_dir.cleanup()

    def _parse_yaml(self, yaml_str: str) -> dict:
        """Helper to parse YAML string back to dict."""
        yaml = YAML()
        return yaml.load(StringIO(yaml_str))

    def test_export_to_file__NoSourcePath__WritesRootFileOnly(self):
        """Export without source_path writes root file only (dict input mode)."""
        exporter = MultiFileExporter()
        config = {"key": "value", "number": 42}
        output_path = self.output_dir / "app.yaml"

        exporter.export_to_file(config, output_path)

        self.assertTrue(output_path.exists())
        content = output_path.read_text()
        parsed = self._parse_yaml(content)
        self.assertEqual(parsed["key"], "value")
        self.assertEqual(parsed["number"], 42)

    def test_export_to_file__SingleFile__WritesToDirectory(self):
        """Export with no refs writes single file."""
        exporter = MultiFileExporter()
        config = {"key": "value", "number": 42}
        source_path = Path("/configs/app.yaml")
        output_path = self.output_dir / "app.yaml"

        exporter.export_to_file(config, output_path, source_path=source_path)

        self.assertTrue(output_path.exists())
        content = output_path.read_text()
        parsed = self._parse_yaml(content)
        self.assertEqual(parsed["key"], "value")

    def test_export_to_file__CreatesOutputDir__IfNotExists(self):
        """Export creates output directory if it doesn't exist."""
        exporter = MultiFileExporter()
        config = {"key": "value"}
        nested_output = self.output_dir / "nested" / "dir" / "app.yaml"
        source_path = Path("/configs/app.yaml")

        exporter.export_to_file(config, nested_output, source_path=source_path)

        self.assertTrue(nested_output.exists())

    def test_export_to_file__ExcludeMarkers__RemovesFromOutput(self):
        """Export with exclude_markers removes markers."""
        exporter = MultiFileExporter(exclude_markers=True)
        config = {"_target_": "Test", "_instance_": "/shared", "value": 42}
        source_path = Path("/configs/app.yaml")
        output_path = self.output_dir / "app.yaml"

        exporter.export_to_file(config, output_path, source_path=source_path)

        content = output_path.read_text()
        parsed = self._parse_yaml(content)
        self.assertNotIn("_target_", parsed)
        self.assertNotIn("_instance_", parsed)
        self.assertEqual(parsed["value"], 42)

    def test_export_to_file__DefaultMarkers__ExcludesRefMarker(self):
        """Default markers for MultiFileExporter exclude _ref_."""
        exporter = MultiFileExporter()

        # _ref_ should NOT be in the default markers since we preserve structure
        self.assertNotIn("_ref_", exporter._markers)

    def test_export_to_file__PreservesRefInOutput__WhenNotExcluded(self):
        """Export preserves _ref_ marker when not excluded."""
        exporter = MultiFileExporter(exclude_markers=False)
        config = {
            "_ref_": "./other.yaml",
            "value": 42,
        }
        source_path = Path("/configs/app.yaml")
        output_path = self.output_dir / "app.yaml"

        exporter.export_to_file(config, output_path, source_path=source_path)

        content = output_path.read_text()
        parsed = self._parse_yaml(content)
        self.assertEqual(parsed["_ref_"], "./other.yaml")

    def test_export_to_file__EmptyRefGraph__WritesSingleFile(self):
        """Export with empty ref_graph writes only main file."""
        exporter = MultiFileExporter()
        config = {"key": "value"}
        source_path = Path("/configs/app.yaml")
        output_path = self.output_dir / "app.yaml"

        exporter.export_to_file(
            config,
            output_path,
            source_path=source_path,
            ref_graph={},
        )

        self.assertTrue(output_path.exists())

    def test_export_to_file__NestedConfig__PreservesStructure(self):
        """Export preserves nested config structure."""
        exporter = MultiFileExporter()
        config = {
            "model": {
                "layers": [128, 256],
                "activation": "relu",
            },
        }
        source_path = Path("/configs/trainer.yaml")
        output_path = self.output_dir / "trainer.yaml"

        exporter.export_to_file(config, output_path, source_path=source_path)

        content = output_path.read_text()
        parsed = self._parse_yaml(content)
        self.assertEqual(parsed["model"]["layers"], [128, 256])
        self.assertEqual(parsed["model"]["activation"], "relu")

    def test_export_to_file__CustomMarkers__RemovesOnlySpecified(self):
        """Export with custom markers removes only those."""
        exporter = MultiFileExporter(
            exclude_markers=True,
            markers=("_custom_",),
        )
        config = {"_target_": "Keep", "_custom_": "Remove", "value": 42}
        source_path = Path("/configs/app.yaml")
        output_path = self.output_dir / "app.yaml"

        exporter.export_to_file(config, output_path, source_path=source_path)

        content = output_path.read_text()
        parsed = self._parse_yaml(content)
        self.assertEqual(parsed["_target_"], "Keep")
        self.assertNotIn("_custom_", parsed)


class MultiFileExporterFormatDetectionTests(TestCase):
    """Tests for format auto-detection in MultiFileExporter."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.output_dir = Path(self.temp_dir.name)

    def tearDown(self):
        """Clean up test fixtures."""
        self.temp_dir.cleanup()

    def test_export_to_file__JsonExtension__ExportsAsJson(self):
        """Export to .json file produces valid JSON."""
        exporter = MultiFileExporter()
        config = {"key": "value", "number": 42}
        source_path = Path("/configs/app.yaml")
        output_path = self.output_dir / "app.json"

        exporter.export_to_file(config, output_path, source_path=source_path)

        self.assertTrue(output_path.exists())
        content = output_path.read_text()
        parsed = json.loads(content)
        self.assertEqual(parsed["key"], "value")
        self.assertEqual(parsed["number"], 42)

    def test_export_to_file__TomlExtension__ExportsAsToml(self):
        """Export to .toml file produces valid TOML."""
        exporter = MultiFileExporter()
        config = {"key": "value", "number": 42}
        source_path = Path("/configs/app.yaml")
        output_path = self.output_dir / "app.toml"

        exporter.export_to_file(config, output_path, source_path=source_path)

        self.assertTrue(output_path.exists())
        content = output_path.read_text()
        parsed = tomllib.loads(content)
        self.assertEqual(parsed["key"], "value")
        self.assertEqual(parsed["number"], 42)

    def test_export_to_file__UnsupportedExtension__RaisesConfigFileError(self):
        """Export to unsupported extension raises ConfigFileError."""
        exporter = MultiFileExporter()
        config = {"key": "value"}
        source_path = Path("/configs/app.yaml")
        output_path = self.output_dir / "app.unknown"

        with self.assertRaises(ConfigFileError) as context:
            exporter.export_to_file(config, output_path, source_path=source_path)

        self.assertIn("unsupported export format", context.exception.reason)

    def test_export_to_file__JsonWithExcludeMarkers__RemovesMarkers(self):
        """Export to JSON with exclude_markers removes markers."""
        exporter = MultiFileExporter(exclude_markers=True)
        config = {"_target_": "Test", "value": 42}
        source_path = Path("/configs/app.yaml")
        output_path = self.output_dir / "app.json"

        exporter.export_to_file(config, output_path, source_path=source_path)

        content = output_path.read_text()
        parsed = json.loads(content)
        self.assertNotIn("_target_", parsed)
        self.assertEqual(parsed["value"], 42)

    def test_export_to_file__CaseInsensitiveExtension__DetectsFormat(self):
        """Export with uppercase extension still detects format."""
        exporter = MultiFileExporter()
        config = {"key": "value"}
        source_path = Path("/configs/app.yaml")
        output_path = self.output_dir / "app.JSON"

        exporter.export_to_file(config, output_path, source_path=source_path)

        self.assertTrue(output_path.exists())
        content = output_path.read_text()
        parsed = json.loads(content)
        self.assertEqual(parsed["key"], "value")
