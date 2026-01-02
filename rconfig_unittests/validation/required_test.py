"""Unit tests for _required_ value detection and validation."""

from unittest import TestCase

from rconfig.validation.required import (
    RequiredMarker,
    extract_required_type,
    find_required_markers,
    is_required_marker,
)


class IsRequiredMarkerTests(TestCase):
    def test_isRequiredMarker__StringMarker__ReturnsTrue(self):
        self.assertTrue(is_required_marker("_required_"))

    def test_isRequiredMarker__DictMarkerWithType__ReturnsTrue(self):
        self.assertTrue(is_required_marker({"_required_": "int"}))

    def test_isRequiredMarker__DictMarkerWithNone__ReturnsTrue(self):
        self.assertTrue(is_required_marker({"_required_": None}))

    def test_isRequiredMarker__RegularString__ReturnsFalse(self):
        self.assertFalse(is_required_marker("some_value"))

    def test_isRequiredMarker__RegularNumber__ReturnsFalse(self):
        self.assertFalse(is_required_marker(42))

    def test_isRequiredMarker__RegularDict__ReturnsFalse(self):
        self.assertFalse(is_required_marker({"key": "value"}))

    def test_isRequiredMarker__DictWithRequiredAndOtherKeys__ReturnsFalse(self):
        # A dict with _required_ AND other keys is not a marker
        self.assertFalse(is_required_marker({"_required_": "int", "extra": "key"}))

    def test_isRequiredMarker__None__ReturnsFalse(self):
        self.assertFalse(is_required_marker(None))

    def test_isRequiredMarker__EmptyDict__ReturnsFalse(self):
        self.assertFalse(is_required_marker({}))


class ExtractRequiredTypeTests(TestCase):
    def test_extractRequiredType__SimpleMarker__ReturnsNone(self):
        self.assertIsNone(extract_required_type("_required_"))

    def test_extractRequiredType__IntType__ReturnsInt(self):
        self.assertEqual(extract_required_type({"_required_": "int"}), int)

    def test_extractRequiredType__FloatType__ReturnsFloat(self):
        self.assertEqual(extract_required_type({"_required_": "float"}), float)

    def test_extractRequiredType__StrType__ReturnsStr(self):
        self.assertEqual(extract_required_type({"_required_": "str"}), str)

    def test_extractRequiredType__BoolType__ReturnsBool(self):
        self.assertEqual(extract_required_type({"_required_": "bool"}), bool)

    def test_extractRequiredType__ListType__ReturnsList(self):
        self.assertEqual(extract_required_type({"_required_": "list"}), list)

    def test_extractRequiredType__DictType__ReturnsDict(self):
        self.assertEqual(extract_required_type({"_required_": "dict"}), dict)

    def test_extractRequiredType__UnknownType__ReturnsNone(self):
        self.assertIsNone(extract_required_type({"_required_": "unknown_type"}))

    def test_extractRequiredType__NoneValue__ReturnsNone(self):
        self.assertIsNone(extract_required_type({"_required_": None}))

    def test_extractRequiredType__TypeObject__ReturnsType(self):
        self.assertEqual(extract_required_type({"_required_": int}), int)


class FindRequiredMarkersTests(TestCase):
    def test_findRequiredMarkers__EmptyConfig__ReturnsEmptyList(self):
        markers = find_required_markers({})
        self.assertEqual(markers, [])

    def test_findRequiredMarkers__NoMarkers__ReturnsEmptyList(self):
        config = {"name": "value", "count": 42}
        markers = find_required_markers(config)
        self.assertEqual(markers, [])

    def test_findRequiredMarkers__SingleSimpleMarker__FindsIt(self):
        config = {"api_key": "_required_"}
        markers = find_required_markers(config)

        self.assertEqual(len(markers), 1)
        self.assertEqual(markers[0].path, "api_key")
        self.assertIsNone(markers[0].expected_type)

    def test_findRequiredMarkers__SingleTypedMarker__FindsWithType(self):
        config = {"timeout": {"_required_": "int"}}
        markers = find_required_markers(config)

        self.assertEqual(len(markers), 1)
        self.assertEqual(markers[0].path, "timeout")
        self.assertEqual(markers[0].expected_type, int)

    def test_findRequiredMarkers__MultipleMarkers__FindsAll(self):
        config = {
            "api_key": "_required_",
            "port": {"_required_": "int"},
            "name": "regular_value",
        }
        markers = find_required_markers(config)

        self.assertEqual(len(markers), 2)
        paths = {m.path for m in markers}
        self.assertIn("api_key", paths)
        self.assertIn("port", paths)

    def test_findRequiredMarkers__NestedConfig__FindsNested(self):
        config = {
            "database": {
                "url": "_required_",
                "timeout": {"_required_": "int"},
            }
        }
        markers = find_required_markers(config)

        self.assertEqual(len(markers), 2)
        paths = {m.path for m in markers}
        self.assertIn("database.url", paths)
        self.assertIn("database.timeout", paths)

    def test_findRequiredMarkers__DeeplyNested__FindsAll(self):
        config = {
            "level1": {
                "level2": {
                    "level3": {
                        "secret": "_required_",
                    }
                }
            }
        }
        markers = find_required_markers(config)

        self.assertEqual(len(markers), 1)
        self.assertEqual(markers[0].path, "level1.level2.level3.secret")

    def test_findRequiredMarkers__InList__FindsMarkers(self):
        config = {
            "items": ["_required_", "regular", "_required_"]
        }
        markers = find_required_markers(config)

        self.assertEqual(len(markers), 2)
        paths = {m.path for m in markers}
        self.assertIn("items[0]", paths)
        self.assertIn("items[2]", paths)

    def test_findRequiredMarkers__NestedInList__FindsMarkers(self):
        config = {
            "servers": [
                {"host": "_required_", "port": 8080},
                {"host": "localhost", "port": {"_required_": "int"}},
            ]
        }
        markers = find_required_markers(config)

        self.assertEqual(len(markers), 2)
        paths = {m.path for m in markers}
        self.assertIn("servers[0].host", paths)
        self.assertIn("servers[1].port", paths)

    def test_findRequiredMarkers__MixedNesting__FindsAll(self):
        config = {
            "api_key": "_required_",
            "database": {
                "url": "_required_",
                "replicas": [
                    {"host": "_required_"},
                ]
            },
            "port": 8080,
        }
        markers = find_required_markers(config)

        self.assertEqual(len(markers), 3)
        paths = {m.path for m in markers}
        self.assertIn("api_key", paths)
        self.assertIn("database.url", paths)
        self.assertIn("database.replicas[0].host", paths)

    def test_findRequiredMarkers__PreservesTypeInfo(self):
        config = {
            "simple": "_required_",
            "typed_int": {"_required_": "int"},
            "typed_str": {"_required_": "str"},
        }
        markers = find_required_markers(config)

        markers_by_path = {m.path: m for m in markers}

        self.assertIsNone(markers_by_path["simple"].expected_type)
        self.assertEqual(markers_by_path["typed_int"].expected_type, int)
        self.assertEqual(markers_by_path["typed_str"].expected_type, str)
