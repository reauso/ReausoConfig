"""Tests for rconfig.export.toml_exporter module."""

import tomllib
from unittest import TestCase

from rconfig.export.toml_exporter import TomlExporter


class TomlExporterTests(TestCase):
    """Tests for TomlExporter."""

    def _parse_toml(self, toml_str: str) -> dict:
        """Helper to parse TOML string back to dict."""
        return tomllib.loads(toml_str)

    def test_export__SimpleConfig__ReturnsValidToml(self):
        """Export returns valid parseable TOML."""
        exporter = TomlExporter()
        config = {"key": "value", "number": 42}

        result = exporter.export(config)

        parsed = self._parse_toml(result)
        self.assertEqual(parsed["key"], "value")
        self.assertEqual(parsed["number"], 42)

    def test_export__NestedConfig__ProducesValidToml(self):
        """Export produces valid TOML for nested configs."""
        exporter = TomlExporter()
        config = {"parent": {"child": {"value": 42}}}

        result = exporter.export(config)

        parsed = self._parse_toml(result)
        self.assertEqual(parsed["parent"]["child"]["value"], 42)

    def test_export__ExcludeMarkersTrue__RemovesMarkers(self):
        """Export with exclude_markers=True removes markers."""
        exporter = TomlExporter(exclude_markers=True)
        config = {
            "_target_": "SomeClass",
            "value": 42,
        }

        result = exporter.export(config)
        parsed = self._parse_toml(result)

        self.assertNotIn("_target_", parsed)
        self.assertEqual(parsed["value"], 42)

    def test_export__UnicodeContent__PreservesUnicode(self):
        """Export preserves unicode characters."""
        exporter = TomlExporter()
        config = {
            "emoji": "\U0001F600",
            "chinese": "\u4e2d\u6587",
            "math": "\u03C0 \u2248 3.14159",
        }

        result = exporter.export(config)
        parsed = self._parse_toml(result)

        self.assertEqual(parsed["emoji"], "\U0001F600")
        self.assertEqual(parsed["chinese"], "\u4e2d\u6587")
        self.assertEqual(parsed["math"], "\u03C0 \u2248 3.14159")

    def test_export__SpecialCharacters__EscapesCorrectly(self):
        """Export correctly handles special characters."""
        exporter = TomlExporter()
        config = {
            "quotes": '"double" and backslash\\',
            "tabs": "col1\tcol2",
        }

        result = exporter.export(config)
        parsed = self._parse_toml(result)

        self.assertEqual(parsed["quotes"], '"double" and backslash\\')
        self.assertEqual(parsed["tabs"], "col1\tcol2")

    def test_export__EmptyConfig__ReturnsValidToml(self):
        """Export of empty config returns valid TOML."""
        exporter = TomlExporter()
        result = exporter.export({})

        parsed = self._parse_toml(result)
        self.assertEqual(parsed, {})

    def test_export__ListValues__ReturnsValidToml(self):
        """Export handles list values correctly."""
        exporter = TomlExporter()
        config = {"items": [1, 2, 3], "tags": ["ml", "vision"]}

        result = exporter.export(config)
        parsed = self._parse_toml(result)

        self.assertEqual(parsed["items"], [1, 2, 3])
        self.assertEqual(parsed["tags"], ["ml", "vision"])

    def test_export__MarkersInNestedDicts__RemovesRecursively(self):
        """Export removes markers from nested dicts."""
        exporter = TomlExporter(exclude_markers=True)
        config = {
            "_target_": "Root",
            "child": {"_target_": "Child", "value": 1},
        }

        result = exporter.export(config)
        parsed = self._parse_toml(result)

        self.assertNotIn("_target_", parsed)
        self.assertNotIn("_target_", parsed["child"])

    def test_export__CustomMarkers__RemovesOnlySpecified(self):
        """Export with custom markers removes only those."""
        exporter = TomlExporter(
            exclude_markers=True,
            markers=("_custom_",),
        )
        config = {"_target_": "Keep", "_custom_": "Remove", "value": 42}

        result = exporter.export(config)
        parsed = self._parse_toml(result)

        self.assertEqual(parsed["_target_"], "Keep")
        self.assertNotIn("_custom_", parsed)

    def test_export__BooleanValues__PreservesCorrectly(self):
        """Export preserves boolean values correctly."""
        exporter = TomlExporter()
        config = {"true_val": True, "false_val": False}

        result = exporter.export(config)
        parsed = self._parse_toml(result)

        self.assertIs(parsed["true_val"], True)
        self.assertIs(parsed["false_val"], False)

    def test_export__NumericValues__PreservesTypes(self):
        """Export preserves numeric types correctly."""
        exporter = TomlExporter()
        config = {
            "integer": 42,
            "float": 3.14159,
            "negative": -100,
            "zero": 0,
        }

        result = exporter.export(config)
        parsed = self._parse_toml(result)

        self.assertEqual(parsed["integer"], 42)
        self.assertAlmostEqual(parsed["float"], 3.14159)
        self.assertEqual(parsed["negative"], -100)
        self.assertEqual(parsed["zero"], 0)

    def test_export__OriginalUnmodified__NoSideEffects(self):
        """Export does not modify the original config."""
        exporter = TomlExporter(exclude_markers=True)
        original = {"_target_": "Test", "value": 42}

        exporter.export(original)

        self.assertEqual(original["_target_"], "Test")

    def test_export__DeeplyNestedConfig__HandlesCorrectly(self):
        """Export handles deeply nested structures."""
        exporter = TomlExporter()
        config = {
            "level1": {
                "level2": {
                    "level3": {
                        "level4": {"value": "deep"}
                    }
                }
            }
        }

        result = exporter.export(config)
        parsed = self._parse_toml(result)

        self.assertEqual(
            parsed["level1"]["level2"]["level3"]["level4"]["value"], "deep"
        )

    def test_export__AllDefaultMarkers__RemovedWhenExcluded(self):
        """Export removes all default markers when exclude_markers=True."""
        exporter = TomlExporter(exclude_markers=True)
        config = {
            "_target_": "SomeClass",
            "_ref_": "some.reference",
            "_instance_": "shared_instance",
            "_lazy_": True,
            "value": 42,
        }

        result = exporter.export(config)
        parsed = self._parse_toml(result)

        self.assertNotIn("_target_", parsed)
        self.assertNotIn("_ref_", parsed)
        self.assertNotIn("_instance_", parsed)
        self.assertNotIn("_lazy_", parsed)
        self.assertEqual(parsed["value"], 42)

    def test_export__MultilineStringsTrue__FormatsMultilineStrings(self):
        """Export with multiline_strings=True formats long strings."""
        exporter = TomlExporter(multiline_strings=True)
        config = {"multiline": "line1\nline2\nline3"}

        result = exporter.export(config)
        parsed = self._parse_toml(result)

        self.assertEqual(parsed["multiline"], "line1\nline2\nline3")

    def test_export__MultilineStringsFalse__SingleLineStrings(self):
        """Export with multiline_strings=False uses single-line escaping."""
        exporter = TomlExporter(multiline_strings=False)
        config = {"multiline": "line1\nline2\nline3"}

        result = exporter.export(config)
        parsed = self._parse_toml(result)

        self.assertEqual(parsed["multiline"], "line1\nline2\nline3")
        # Should use escape sequences, not literal newlines in string value
        # (though result after parsing should be the same)

    def test_export__NestedTables__ProducesValidToml(self):
        """Export creates proper TOML table structure."""
        exporter = TomlExporter()
        config = {
            "database": {
                "host": "localhost",
                "port": 5432,
            },
            "cache": {
                "enabled": True,
                "ttl": 3600,
            },
        }

        result = exporter.export(config)
        parsed = self._parse_toml(result)

        self.assertEqual(parsed["database"]["host"], "localhost")
        self.assertEqual(parsed["database"]["port"], 5432)
        self.assertEqual(parsed["cache"]["enabled"], True)
        self.assertEqual(parsed["cache"]["ttl"], 3600)

    def test_export__MixedScalarsAndTables__HandlesCorrectly(self):
        """Export handles configs with both scalars and nested tables."""
        exporter = TomlExporter()
        config = {
            "name": "myapp",
            "version": "1.0.0",
            "settings": {
                "debug": False,
                "log_level": "info",
            },
        }

        result = exporter.export(config)
        parsed = self._parse_toml(result)

        self.assertEqual(parsed["name"], "myapp")
        self.assertEqual(parsed["version"], "1.0.0")
        self.assertEqual(parsed["settings"]["debug"], False)
        self.assertEqual(parsed["settings"]["log_level"], "info")

    def test_export__ArrayOfDicts__ProducesValidToml(self):
        """Export handles arrays of dictionaries."""
        exporter = TomlExporter()
        config = {
            "servers": [
                {"name": "alpha", "ip": "10.0.0.1"},
                {"name": "beta", "ip": "10.0.0.2"},
            ]
        }

        result = exporter.export(config)
        parsed = self._parse_toml(result)

        self.assertEqual(len(parsed["servers"]), 2)
        self.assertEqual(parsed["servers"][0]["name"], "alpha")
        self.assertEqual(parsed["servers"][1]["name"], "beta")

    def test_export__MarkersInListDicts__RemovesRecursively(self):
        """Export removes markers from dicts inside lists."""
        exporter = TomlExporter(exclude_markers=True)
        config = {
            "_target_": "Root",
            "items": [{"_target_": "Item", "value": 1}],
        }

        result = exporter.export(config)
        parsed = self._parse_toml(result)

        self.assertNotIn("_target_", parsed)
        self.assertNotIn("_target_", parsed["items"][0])
        self.assertEqual(parsed["items"][0]["value"], 1)

