"""Tests for rconfig.export.json_exporter module."""

import json
from unittest import TestCase

from rconfig.export.json_exporter import JsonExporter


class JsonExporterTests(TestCase):
    """Tests for JsonExporter."""

    def _parse_json(self, json_str: str) -> dict:
        """Helper to parse JSON string back to dict."""
        return json.loads(json_str)

    def test_export__SimpleConfig__ReturnsValidJson(self):
        """Export returns valid parseable JSON."""
        exporter = JsonExporter()
        config = {"key": "value", "number": 42}

        result = exporter.export(config)

        parsed = self._parse_json(result)
        self.assertEqual(parsed["key"], "value")
        self.assertEqual(parsed["number"], 42)

    def test_export__NestedConfig__ProducesValidJson(self):
        """Export produces valid JSON for nested configs."""
        exporter = JsonExporter()
        config = {"parent": {"child": {"value": 42}}}

        result = exporter.export(config)

        parsed = self._parse_json(result)
        self.assertEqual(parsed["parent"]["child"]["value"], 42)

    def test_export__IndentOption__RespectsIndentation(self):
        """Export respects the indent option."""
        exporter = JsonExporter(indent=4)
        config = {"parent": {"child": "value"}}

        result = exporter.export(config)

        # Check indentation is 4 spaces
        lines = result.split("\n")
        for line in lines:
            if '"child"' in line:
                indent = len(line) - len(line.lstrip())
                self.assertEqual(indent, 8)  # 2 levels * 4 spaces
                break

    def test_export__IndentNone__ProducesCompactOutput(self):
        """Export with indent=None produces compact output."""
        exporter = JsonExporter(indent=None)
        config = {"key": "value", "nested": {"inner": 1}}

        result = exporter.export(config)

        # Compact output has no newlines
        self.assertNotIn("\n", result)

    def test_export__ExcludeMarkersTrue__RemovesMarkers(self):
        """Export with exclude_markers=True removes markers."""
        exporter = JsonExporter(exclude_markers=True)
        config = {
            "_target_": "SomeClass",
            "value": 42,
        }

        result = exporter.export(config)
        parsed = self._parse_json(result)

        self.assertNotIn("_target_", parsed)
        self.assertEqual(parsed["value"], 42)

    def test_export__SortKeysTrue__SortsKeys(self):
        """Export with sort_keys=True sorts keys alphabetically."""
        exporter = JsonExporter(sort_keys=True)
        config = {"zebra": 1, "apple": 2, "mango": 3}

        result = exporter.export(config)

        # Keys should appear in alphabetical order
        apple_pos = result.find('"apple"')
        mango_pos = result.find('"mango"')
        zebra_pos = result.find('"zebra"')
        self.assertLess(apple_pos, mango_pos)
        self.assertLess(mango_pos, zebra_pos)

    def test_export__EnsureAsciiTrue__EscapesNonAscii(self):
        """Export with ensure_ascii=True escapes non-ASCII characters."""
        exporter = JsonExporter(ensure_ascii=True)
        config = {"emoji": "\U0001F600", "chinese": "\u4e2d\u6587"}

        result = exporter.export(config)

        # Non-ASCII should be escaped
        self.assertNotIn("\U0001F600", result)
        self.assertNotIn("\u4e2d", result)
        self.assertIn("\\u", result)

    def test_export__EnsureAsciiFalse__PreservesUnicode(self):
        """Export with ensure_ascii=False preserves unicode characters."""
        exporter = JsonExporter(ensure_ascii=False)
        config = {
            "emoji": "\U0001F600",
            "chinese": "\u4e2d\u6587",
            "math": "\u03C0 \u2248 3.14159",
        }

        result = exporter.export(config)
        parsed = self._parse_json(result)

        self.assertEqual(parsed["emoji"], "\U0001F600")
        self.assertEqual(parsed["chinese"], "\u4e2d\u6587")
        self.assertEqual(parsed["math"], "\u03C0 \u2248 3.14159")

    def test_export__SpecialCharacters__EscapesCorrectly(self):
        """Export correctly handles special JSON characters."""
        exporter = JsonExporter()
        config = {
            "quotes": '"double" and backslash\\',
            "newlines": "line1\nline2",
            "tabs": "col1\tcol2",
        }

        result = exporter.export(config)
        parsed = self._parse_json(result)

        self.assertEqual(parsed["quotes"], '"double" and backslash\\')
        self.assertEqual(parsed["newlines"], "line1\nline2")
        self.assertEqual(parsed["tabs"], "col1\tcol2")

    def test_export__EmptyConfig__ReturnsValidJson(self):
        """Export of empty config returns valid JSON."""
        exporter = JsonExporter()
        result = exporter.export({})

        parsed = self._parse_json(result)
        self.assertEqual(parsed, {})

    def test_export__ListValues__ReturnsValidJson(self):
        """Export handles list values correctly."""
        exporter = JsonExporter()
        config = {"items": [1, 2, 3], "nested": [{"a": 1}, {"b": 2}]}

        result = exporter.export(config)
        parsed = self._parse_json(result)

        self.assertEqual(parsed["items"], [1, 2, 3])
        self.assertEqual(parsed["nested"][0]["a"], 1)

    def test_export__MarkersInNestedDicts__RemovesRecursively(self):
        """Export removes markers from nested dicts."""
        exporter = JsonExporter(exclude_markers=True)
        config = {
            "_target_": "Root",
            "child": {"_target_": "Child", "value": 1},
        }

        result = exporter.export(config)
        parsed = self._parse_json(result)

        self.assertNotIn("_target_", parsed)
        self.assertNotIn("_target_", parsed["child"])

    def test_export__MarkersInLists__RemovesRecursively(self):
        """Export removes markers from dicts inside lists."""
        exporter = JsonExporter(exclude_markers=True)
        config = {
            "_target_": "Root",
            "items": [{"_target_": "Item", "value": 1}],
        }

        result = exporter.export(config)
        parsed = self._parse_json(result)

        self.assertNotIn("_target_", parsed)
        self.assertNotIn("_target_", parsed["items"][0])
        self.assertEqual(parsed["items"][0]["value"], 1)

    def test_export__CustomMarkers__RemovesOnlySpecified(self):
        """Export with custom markers removes only those."""
        exporter = JsonExporter(
            exclude_markers=True,
            markers=("_custom_",),
        )
        config = {"_target_": "Keep", "_custom_": "Remove", "value": 42}

        result = exporter.export(config)
        parsed = self._parse_json(result)

        self.assertEqual(parsed["_target_"], "Keep")
        self.assertNotIn("_custom_", parsed)

    def test_export__BooleanValues__PreservesCorrectly(self):
        """Export preserves boolean values correctly."""
        exporter = JsonExporter()
        config = {"true_val": True, "false_val": False}

        result = exporter.export(config)
        parsed = self._parse_json(result)

        self.assertIs(parsed["true_val"], True)
        self.assertIs(parsed["false_val"], False)

    def test_export__NullValues__PreservesCorrectly(self):
        """Export preserves null values correctly."""
        exporter = JsonExporter()
        config = {"null_val": None}

        result = exporter.export(config)
        parsed = self._parse_json(result)

        self.assertIsNone(parsed["null_val"])

    def test_export__NumericValues__PreservesTypes(self):
        """Export preserves numeric types correctly."""
        exporter = JsonExporter()
        config = {
            "integer": 42,
            "float": 3.14159,
            "negative": -100,
            "zero": 0,
        }

        result = exporter.export(config)
        parsed = self._parse_json(result)

        self.assertEqual(parsed["integer"], 42)
        self.assertAlmostEqual(parsed["float"], 3.14159)
        self.assertEqual(parsed["negative"], -100)
        self.assertEqual(parsed["zero"], 0)

    def test_export__OriginalUnmodified__NoSideEffects(self):
        """Export does not modify the original config."""
        exporter = JsonExporter(exclude_markers=True)
        original = {"_target_": "Test", "value": 42}

        exporter.export(original)

        self.assertEqual(original["_target_"], "Test")

    def test_export__DeeplyNestedConfig__HandlesCorrectly(self):
        """Export handles deeply nested structures."""
        exporter = JsonExporter()
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
        parsed = self._parse_json(result)

        self.assertEqual(
            parsed["level1"]["level2"]["level3"]["level4"]["value"], "deep"
        )

    def test_export__MixedNestedStructures__HandlesCorrectly(self):
        """Export handles mixed nested lists and dicts."""
        exporter = JsonExporter()
        config = {
            "data": [
                {"items": [1, 2, {"nested": True}]},
                [{"deep": "value"}],
            ]
        }

        result = exporter.export(config)
        parsed = self._parse_json(result)

        self.assertEqual(parsed["data"][0]["items"][2]["nested"], True)
        self.assertEqual(parsed["data"][1][0]["deep"], "value")

    def test_export__DefaultIndent__IsTwoSpaces(self):
        """Export uses 2-space indentation by default."""
        exporter = JsonExporter()
        config = {"parent": {"child": "value"}}

        result = exporter.export(config)

        lines = result.split("\n")
        for line in lines:
            if '"parent"' in line:
                indent = len(line) - len(line.lstrip())
                self.assertEqual(indent, 2)  # 1 level * 2 spaces
                break

    def test_export__AllDefaultMarkers__RemovedWhenExcluded(self):
        """Export removes all default markers when exclude_markers=True."""
        exporter = JsonExporter(exclude_markers=True)
        config = {
            "_target_": "SomeClass",
            "_ref_": "some.reference",
            "_instance_": "shared_instance",
            "_lazy_": True,
            "value": 42,
        }

        result = exporter.export(config)
        parsed = self._parse_json(result)

        self.assertNotIn("_target_", parsed)
        self.assertNotIn("_ref_", parsed)
        self.assertNotIn("_instance_", parsed)
        self.assertNotIn("_lazy_", parsed)
        self.assertEqual(parsed["value"], 42)

