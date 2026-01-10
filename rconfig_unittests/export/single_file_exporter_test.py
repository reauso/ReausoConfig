"""Tests for rconfig.export.single_file_exporter module."""

import json
import tempfile
import tomllib
from io import StringIO
from pathlib import Path
from unittest import TestCase

from ruamel.yaml import YAML

from rconfig.errors import ConfigFileError
from rconfig.export.single_file_exporter import SingleFileExporter


class SingleFileExporterTests(TestCase):
    """Tests for SingleFileExporter."""

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

    def test_export_to_file__SimpleConfig__WritesYamlFile(self):
        """Export writes config to a YAML file."""
        exporter = SingleFileExporter()
        config = {"key": "value", "number": 42}
        output_path = self.output_dir / "output.yaml"

        exporter.export_to_file(config, output_path)

        self.assertTrue(output_path.exists())
        content = output_path.read_text()
        parsed = self._parse_yaml(content)
        self.assertEqual(parsed["key"], "value")
        self.assertEqual(parsed["number"], 42)

    def test_export_to_file__OutputDirNotExists__CreatesDirectory(self):
        """Export creates parent directories if they don't exist."""
        exporter = SingleFileExporter()
        config = {"key": "value"}
        output_path = self.output_dir / "nested" / "deep" / "output.yaml"

        exporter.export_to_file(config, output_path)

        self.assertTrue(output_path.exists())
        self.assertTrue(output_path.parent.exists())

    def test_export_to_file__ExcludeMarkers__RemovesFromOutput(self):
        """Export with exclude_markers removes markers from output."""
        exporter = SingleFileExporter(exclude_markers=True)
        config = {"_target_": "Test", "value": 42}
        output_path = self.output_dir / "output.yaml"

        exporter.export_to_file(config, output_path)

        content = output_path.read_text()
        parsed = self._parse_yaml(content)
        self.assertNotIn("_target_", parsed)
        self.assertEqual(parsed["value"], 42)

    def test_export_to_file__ExistingFile__OverwritesFile(self):
        """Export overwrites existing file."""
        exporter = SingleFileExporter()
        output_path = self.output_dir / "output.yaml"

        # Write initial content
        output_path.write_text("old: content\n")

        # Export new content
        exporter.export_to_file({"new": "content"}, output_path)

        content = output_path.read_text()
        parsed = self._parse_yaml(content)
        self.assertNotIn("old", parsed)
        self.assertEqual(parsed["new"], "content")

    def test_export_to_file__NestedConfig__WritesCorrectly(self):
        """Export handles nested config correctly."""
        exporter = SingleFileExporter()
        config = {
            "parent": {
                "child": {
                    "value": 42,
                },
            },
        }
        output_path = self.output_dir / "output.yaml"

        exporter.export_to_file(config, output_path)

        content = output_path.read_text()
        parsed = self._parse_yaml(content)
        self.assertEqual(parsed["parent"]["child"]["value"], 42)

    def test_export_to_file__IgnoresSourcePath__NotUsed(self):
        """Export ignores source_path parameter (not used for single file)."""
        exporter = SingleFileExporter()
        config = {"key": "value"}
        output_path = self.output_dir / "output.yaml"

        # Should not raise even with source_path
        exporter.export_to_file(
            config, output_path, source_path=Path("/some/path.yaml")
        )

        self.assertTrue(output_path.exists())

    def test_export_to_file__IgnoresRefGraph__NotUsed(self):
        """Export ignores ref_graph parameter (not used for single file)."""
        exporter = SingleFileExporter()
        config = {"key": "value"}
        output_path = self.output_dir / "output.yaml"

        # Should not raise even with ref_graph
        exporter.export_to_file(
            config,
            output_path,
            ref_graph={"/some/path.yaml": ["/other.yaml"]},
        )

        self.assertTrue(output_path.exists())

    def test_export_to_file__CustomMarkers__RemovesOnlySpecified(self):
        """Export with custom markers removes only those."""
        exporter = SingleFileExporter(
            exclude_markers=True,
            markers=("_custom_",),
        )
        config = {"_target_": "Keep", "_custom_": "Remove", "value": 42}
        output_path = self.output_dir / "output.yaml"

        exporter.export_to_file(config, output_path)

        content = output_path.read_text()
        parsed = self._parse_yaml(content)
        self.assertEqual(parsed["_target_"], "Keep")
        self.assertNotIn("_custom_", parsed)


class SingleFileExporterFormatDetectionTests(TestCase):
    """Tests for format auto-detection in SingleFileExporter."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.output_dir = Path(self.temp_dir.name)

    def tearDown(self):
        """Clean up test fixtures."""
        self.temp_dir.cleanup()

    def test_export_to_file__JsonExtension__ExportsAsJson(self):
        """Export to .json file produces valid JSON."""
        exporter = SingleFileExporter()
        config = {"key": "value", "number": 42}
        output_path = self.output_dir / "output.json"

        exporter.export_to_file(config, output_path)

        self.assertTrue(output_path.exists())
        content = output_path.read_text()
        parsed = json.loads(content)
        self.assertEqual(parsed["key"], "value")
        self.assertEqual(parsed["number"], 42)

    def test_export_to_file__TomlExtension__ExportsAsToml(self):
        """Export to .toml file produces valid TOML."""
        exporter = SingleFileExporter()
        config = {"key": "value", "number": 42}
        output_path = self.output_dir / "output.toml"

        exporter.export_to_file(config, output_path)

        self.assertTrue(output_path.exists())
        content = output_path.read_text()
        parsed = tomllib.loads(content)
        self.assertEqual(parsed["key"], "value")
        self.assertEqual(parsed["number"], 42)

    def test_export_to_file__YmlExtension__ExportsAsYaml(self):
        """Export to .yml file produces valid YAML."""
        exporter = SingleFileExporter()
        config = {"key": "value", "number": 42}
        output_path = self.output_dir / "output.yml"

        exporter.export_to_file(config, output_path)

        self.assertTrue(output_path.exists())
        yaml = YAML()
        parsed = yaml.load(StringIO(output_path.read_text()))
        self.assertEqual(parsed["key"], "value")
        self.assertEqual(parsed["number"], 42)

    def test_export_to_file__UnsupportedExtension__RaisesConfigFileError(self):
        """Export to unsupported extension raises ConfigFileError."""
        exporter = SingleFileExporter()
        config = {"key": "value"}
        output_path = self.output_dir / "output.unknown"

        with self.assertRaises(ConfigFileError) as context:
            exporter.export_to_file(config, output_path)

        self.assertIn("unsupported export format", context.exception.reason)

    def test_export_to_file__JsonWithExcludeMarkers__RemovesMarkers(self):
        """Export to JSON with exclude_markers removes markers."""
        exporter = SingleFileExporter(exclude_markers=True)
        config = {"_target_": "Test", "value": 42}
        output_path = self.output_dir / "output.json"

        exporter.export_to_file(config, output_path)

        content = output_path.read_text()
        parsed = json.loads(content)
        self.assertNotIn("_target_", parsed)
        self.assertEqual(parsed["value"], 42)

    def test_export_to_file__TomlWithExcludeMarkers__RemovesMarkers(self):
        """Export to TOML with exclude_markers removes markers."""
        exporter = SingleFileExporter(exclude_markers=True)
        config = {"_target_": "Test", "value": 42}
        output_path = self.output_dir / "output.toml"

        exporter.export_to_file(config, output_path)

        content = output_path.read_text()
        parsed = tomllib.loads(content)
        self.assertNotIn("_target_", parsed)
        self.assertEqual(parsed["value"], 42)

    def test_export_to_file__CaseInsensitiveExtension__DetectsFormat(self):
        """Export with uppercase extension still detects format."""
        exporter = SingleFileExporter()
        config = {"key": "value"}
        output_path = self.output_dir / "output.JSON"

        exporter.export_to_file(config, output_path)

        self.assertTrue(output_path.exists())
        content = output_path.read_text()
        parsed = json.loads(content)
        self.assertEqual(parsed["key"], "value")
