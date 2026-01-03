"""Tests for rconfig.export.dict_exporter module."""

from unittest import TestCase

from rconfig.export.dict_exporter import DictExporter


class DictExporterTests(TestCase):
    """Tests for DictExporter."""

    def test_export__SimpleConfig__ReturnsDeepCopy(self):
        """Export returns a deep copy of the config."""
        exporter = DictExporter()
        original = {"key": "value", "nested": {"inner": 42}}

        result = exporter.export(original)

        self.assertEqual(result, original)
        # Verify it's a deep copy
        result["key"] = "modified"
        self.assertEqual(original["key"], "value")

    def test_export__NestedConfig__ReturnsDeepCopy(self):
        """Export returns a deep copy of nested config."""
        exporter = DictExporter()
        original = {"level1": {"level2": {"level3": "deep"}}}

        result = exporter.export(original)

        # Modify the result deeply
        result["level1"]["level2"]["level3"] = "modified"
        self.assertEqual(original["level1"]["level2"]["level3"], "deep")

    def test_export__ExcludeMarkersTrue__RemovesAllMarkers(self):
        """Export with exclude_markers=True removes all default markers."""
        exporter = DictExporter(exclude_markers=True)
        config = {
            "_target_": "SomeClass",
            "_ref_": "./other.yaml",
            "_instance_": "/shared.db",
            "_lazy_": True,
            "actual": "value",
        }

        result = exporter.export(config)

        self.assertNotIn("_target_", result)
        self.assertNotIn("_ref_", result)
        self.assertNotIn("_instance_", result)
        self.assertNotIn("_lazy_", result)
        self.assertEqual(result["actual"], "value")

    def test_export__ExcludeMarkersFalse__PreservesMarkers(self):
        """Export with exclude_markers=False preserves all markers."""
        exporter = DictExporter(exclude_markers=False)
        config = {
            "_target_": "SomeClass",
            "_ref_": "./other.yaml",
            "actual": "value",
        }

        result = exporter.export(config)

        self.assertEqual(result["_target_"], "SomeClass")
        self.assertEqual(result["_ref_"], "./other.yaml")
        self.assertEqual(result["actual"], "value")

    def test_export__CustomMarkers__RemovesOnlySpecifiedKeys(self):
        """Export with custom markers removes only those keys."""
        exporter = DictExporter(
            exclude_markers=True,
            markers=("_custom_", "_special_"),
        )
        config = {
            "_target_": "SomeClass",
            "_custom_": "removed",
            "_special_": "also removed",
            "actual": "value",
        }

        result = exporter.export(config)

        # Custom markers removed
        self.assertNotIn("_custom_", result)
        self.assertNotIn("_special_", result)
        # Default markers preserved
        self.assertEqual(result["_target_"], "SomeClass")
        self.assertEqual(result["actual"], "value")

    def test_export__EmptyConfig__ReturnsEmptyDict(self):
        """Export of empty config returns empty dict."""
        exporter = DictExporter()
        result = exporter.export({})
        self.assertEqual(result, {})

    def test_export__ConfigWithLists__PreservesListStructure(self):
        """Export preserves list structure."""
        exporter = DictExporter()
        config = {
            "items": [1, 2, {"nested": True}],
            "nested_list": [[1, 2], [3, 4]],
        }

        result = exporter.export(config)

        self.assertEqual(result["items"], [1, 2, {"nested": True}])
        self.assertEqual(result["nested_list"], [[1, 2], [3, 4]])

    def test_export__OriginalConfigUnmodified__NoSideEffects(self):
        """Export does not modify the original config."""
        exporter = DictExporter(exclude_markers=True)
        original = {
            "_target_": "SomeClass",
            "value": 42,
            "nested": {"_target_": "NestedClass", "x": 1},
        }

        exporter.export(original)

        # Original should still have markers
        self.assertEqual(original["_target_"], "SomeClass")
        self.assertEqual(original["nested"]["_target_"], "NestedClass")

    def test_export__MarkersInNestedDicts__RemovesRecursively(self):
        """Export removes markers from nested dicts."""
        exporter = DictExporter(exclude_markers=True)
        config = {
            "_target_": "Root",
            "child": {
                "_target_": "Child",
                "grandchild": {
                    "_target_": "GrandChild",
                    "value": 42,
                },
            },
        }

        result = exporter.export(config)

        self.assertNotIn("_target_", result)
        self.assertNotIn("_target_", result["child"])
        self.assertNotIn("_target_", result["child"]["grandchild"])
        self.assertEqual(result["child"]["grandchild"]["value"], 42)

    def test_export__MarkersInLists__RemovesFromListItems(self):
        """Export removes markers from dicts inside lists."""
        exporter = DictExporter(exclude_markers=True)
        config = {
            "items": [
                {"_target_": "Item1", "value": 1},
                {"_target_": "Item2", "value": 2},
            ],
        }

        result = exporter.export(config)

        self.assertNotIn("_target_", result["items"][0])
        self.assertNotIn("_target_", result["items"][1])
        self.assertEqual(result["items"][0]["value"], 1)
        self.assertEqual(result["items"][1]["value"], 2)

    def test_export__DefaultExcludeMarkers__IsFalse(self):
        """Default exclude_markers is False."""
        exporter = DictExporter()
        config = {"_target_": "Test"}

        result = exporter.export(config)

        self.assertIn("_target_", result)

    def test_export__NullValuesPreserved__ReturnsNone(self):
        """Export preserves None/null values."""
        exporter = DictExporter()
        config = {"value": None, "nested": {"also_null": None}}

        result = exporter.export(config)

        self.assertIsNone(result["value"])
        self.assertIsNone(result["nested"]["also_null"])
