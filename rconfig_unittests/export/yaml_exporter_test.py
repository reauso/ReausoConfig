"""Tests for rconfig.export.yaml_exporter module."""

from unittest import TestCase

from ruamel.yaml import YAML
from io import StringIO

from rconfig.export.yaml_exporter import YamlExporter


class YamlExporterTests(TestCase):
    """Tests for YamlExporter."""

    def _parse_yaml(self, yaml_str: str) -> dict:
        """Helper to parse YAML string back to dict."""
        yaml = YAML()
        return yaml.load(StringIO(yaml_str))

    def test_export__SimpleConfig__ReturnsValidYaml(self):
        """Export returns valid parseable YAML."""
        exporter = YamlExporter()
        config = {"key": "value", "number": 42}

        result = exporter.export(config)

        # Parse it back
        parsed = self._parse_yaml(result)
        self.assertEqual(parsed["key"], "value")
        self.assertEqual(parsed["number"], 42)

    def test_export__NestedConfig__ProducesBlockStyle(self):
        """Export produces block style YAML for nested configs."""
        exporter = YamlExporter()
        config = {"parent": {"child": {"value": 42}}}

        result = exporter.export(config)

        # Block style uses newlines and indentation
        self.assertIn("\n", result)
        parsed = self._parse_yaml(result)
        self.assertEqual(parsed["parent"]["child"]["value"], 42)

    def test_export__IndentOption__RespectsIndentation(self):
        """Export respects the indent option."""
        exporter = YamlExporter(indent=4)
        config = {"parent": {"child": "value"}}

        result = exporter.export(config)

        # Check indentation is 4 spaces
        lines = result.split("\n")
        # Find the indented line
        for line in lines:
            if "child:" in line:
                indent = len(line) - len(line.lstrip())
                self.assertEqual(indent, 4)
                break

    def test_export__ExcludeMarkersTrue__RemovesMarkers(self):
        """Export with exclude_markers=True removes markers."""
        exporter = YamlExporter(exclude_markers=True)
        config = {
            "_target_": "SomeClass",
            "value": 42,
        }

        result = exporter.export(config)
        parsed = self._parse_yaml(result)

        self.assertNotIn("_target_", parsed)
        self.assertEqual(parsed["value"], 42)

    def test_export__FlowStyleTrue__ProducesFlowStyle(self):
        """Export with flow_style=True uses inline format."""
        exporter = YamlExporter(default_flow_style=True)
        config = {"key": "value", "nested": {"inner": 1}}

        result = exporter.export(config)

        # Flow style uses braces
        self.assertIn("{", result)

    def test_export__SpecialCharacters__EscapesCorrectly(self):
        """Export correctly handles special YAML characters."""
        exporter = YamlExporter()
        config = {
            "colon": "key: value",
            "hash": "# not a comment",
            "quotes": '"double" and \'single\'',
        }

        result = exporter.export(config)
        parsed = self._parse_yaml(result)

        self.assertEqual(parsed["colon"], "key: value")
        self.assertEqual(parsed["hash"], "# not a comment")
        self.assertEqual(parsed["quotes"], '"double" and \'single\'')

    def test_export__UnicodeContent__PreservesUnicode(self):
        """Export preserves unicode characters."""
        exporter = YamlExporter()
        config = {
            "emoji": "\U0001F600",
            "chinese": "\u4e2d\u6587",
            "math": "\u03C0 \u2248 3.14159",
        }

        result = exporter.export(config)
        parsed = self._parse_yaml(result)

        self.assertEqual(parsed["emoji"], "\U0001F600")
        self.assertEqual(parsed["chinese"], "\u4e2d\u6587")
        self.assertEqual(parsed["math"], "\u03C0 \u2248 3.14159")

    def test_export__MultilineStrings__PreservesFormatting(self):
        """Export handles multiline strings."""
        exporter = YamlExporter()
        config = {
            "multiline": "line1\nline2\nline3",
        }

        result = exporter.export(config)
        parsed = self._parse_yaml(result)

        self.assertEqual(parsed["multiline"], "line1\nline2\nline3")

    def test_export__EmptyConfig__ReturnsValidYaml(self):
        """Export of empty config returns valid YAML."""
        exporter = YamlExporter()
        result = exporter.export({})

        parsed = self._parse_yaml(result)
        self.assertEqual(parsed, {})

    def test_export__ListValues__ReturnsValidYaml(self):
        """Export handles list values correctly."""
        exporter = YamlExporter()
        config = {"items": [1, 2, 3], "nested": [{"a": 1}, {"b": 2}]}

        result = exporter.export(config)
        parsed = self._parse_yaml(result)

        self.assertEqual(parsed["items"], [1, 2, 3])
        self.assertEqual(parsed["nested"][0]["a"], 1)

    def test_export__MarkersInNestedDicts__RemovesRecursively(self):
        """Export removes markers from nested dicts."""
        exporter = YamlExporter(exclude_markers=True)
        config = {
            "_target_": "Root",
            "child": {"_target_": "Child", "value": 1},
        }

        result = exporter.export(config)
        parsed = self._parse_yaml(result)

        self.assertNotIn("_target_", parsed)
        self.assertNotIn("_target_", parsed["child"])

    def test_export__CustomMarkers__RemovesOnlySpecified(self):
        """Export with custom markers removes only those."""
        exporter = YamlExporter(
            exclude_markers=True,
            markers=("_custom_",),
        )
        config = {"_target_": "Keep", "_custom_": "Remove", "value": 42}

        result = exporter.export(config)
        parsed = self._parse_yaml(result)

        self.assertEqual(parsed["_target_"], "Keep")
        self.assertNotIn("_custom_", parsed)

    def test_export__BooleanValues__PreservesCorrectly(self):
        """Export preserves boolean values correctly."""
        exporter = YamlExporter()
        config = {"true_val": True, "false_val": False}

        result = exporter.export(config)
        parsed = self._parse_yaml(result)

        self.assertIs(parsed["true_val"], True)
        self.assertIs(parsed["false_val"], False)

    def test_export__NullValues__PreservesCorrectly(self):
        """Export preserves null values correctly."""
        exporter = YamlExporter()
        config = {"null_val": None}

        result = exporter.export(config)
        parsed = self._parse_yaml(result)

        self.assertIsNone(parsed["null_val"])

    def test_export__OriginalUnmodified__NoSideEffects(self):
        """Export does not modify the original config."""
        exporter = YamlExporter(exclude_markers=True)
        original = {"_target_": "Test", "value": 42}

        exporter.export(original)

        self.assertEqual(original["_target_"], "Test")
