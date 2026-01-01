"""Tests for path_utils module."""

import unittest

from rconfig.path_utils import (
    PathNavigationError,
    get_value_at_path,
    navigate_path,
    parse_path_segments,
)


class ParsePathSegmentsTests(unittest.TestCase):
    """Tests for parse_path_segments function."""

    def test_parse__SimpleDotPath__ReturnsSegments(self):
        result = parse_path_segments("model.layers")
        self.assertEqual(result, ["model", "layers"])

    def test_parse__ListIndex__ReturnsIntSegment(self):
        result = parse_path_segments("callbacks[0]")
        self.assertEqual(result, ["callbacks", 0])

    def test_parse__MixedPath__ReturnsCorrectTypes(self):
        result = parse_path_segments("callbacks[0].name")
        self.assertEqual(result, ["callbacks", 0, "name"])

    def test_parse__MultipleIndices__ReturnsAllInts(self):
        result = parse_path_segments("data[0][1]")
        self.assertEqual(result, ["data", 0, 1])

    def test_parse__EmptyString__ReturnsEmptyList(self):
        result = parse_path_segments("")
        self.assertEqual(result, [])


class NavigatePathTests(unittest.TestCase):
    """Tests for navigate_path function."""

    def test_navigate__EmptyPath__ReturnsConfig(self):
        config = {"key": "value"}
        result = navigate_path(config, [])
        self.assertEqual(result, config)

    def test_navigate__SingleDictKey__ReturnsValue(self):
        config = {"key": "value"}
        result = navigate_path(config, ["key"])
        self.assertEqual(result, "value")

    def test_navigate__NestedDictKeys__ReturnsNestedValue(self):
        config = {"outer": {"inner": "value"}}
        result = navigate_path(config, ["outer", "inner"])
        self.assertEqual(result, "value")

    def test_navigate__ListIndex__ReturnsElement(self):
        config = {"items": [1, 2, 3]}
        result = navigate_path(config, ["items", 1])
        self.assertEqual(result, 2)

    def test_navigate__MixedPath__ReturnsCorrectValue(self):
        config = {"items": [{"name": "first"}, {"name": "second"}]}
        result = navigate_path(config, ["items", 0, "name"])
        self.assertEqual(result, "first")

    def test_navigate__StopBeforeLast__ReturnsParent(self):
        config = {"outer": {"inner": "value"}}
        result = navigate_path(config, ["outer", "inner"], stop_before_last=True)
        self.assertEqual(result, {"inner": "value"})

    def test_navigate__StopBeforeLastWithList__ReturnsParentList(self):
        config = {"items": [1, 2, 3]}
        result = navigate_path(config, ["items", 1], stop_before_last=True)
        self.assertEqual(result, [1, 2, 3])

    def test_navigate__StopBeforeLastSingleSegment__ReturnsConfig(self):
        config = {"key": "value"}
        result = navigate_path(config, ["key"], stop_before_last=True)
        self.assertEqual(result, config)


class NavigatePathErrorTests(unittest.TestCase):
    """Tests for navigate_path error handling."""

    def test_navigate__KeyNotFound__RaisesPathNavigationError(self):
        config = {"key": "value"}
        with self.assertRaises(PathNavigationError) as ctx:
            navigate_path(config, ["missing"])

        self.assertEqual(ctx.exception.segment_index, 0)
        self.assertEqual(ctx.exception.path, ["missing"])
        self.assertIn("not found", ctx.exception.message)

    def test_navigate__IndexOutOfRange__RaisesPathNavigationError(self):
        config = {"items": [1, 2]}
        with self.assertRaises(PathNavigationError) as ctx:
            navigate_path(config, ["items", 5])

        self.assertEqual(ctx.exception.segment_index, 1)
        self.assertEqual(ctx.exception.path, ["items", 5])
        self.assertIn("out of range", ctx.exception.message)

    def test_navigate__NegativeIndex__RaisesPathNavigationError(self):
        config = {"items": [1, 2]}
        with self.assertRaises(PathNavigationError) as ctx:
            navigate_path(config, ["items", -1])

        self.assertEqual(ctx.exception.segment_index, 1)
        self.assertIn("out of range", ctx.exception.message)

    def test_navigate__IndexOnDict__RaisesPathNavigationError(self):
        config = {"key": "value"}
        with self.assertRaises(PathNavigationError) as ctx:
            navigate_path(config, [0])

        self.assertEqual(ctx.exception.segment_index, 0)
        self.assertIn("non-list", ctx.exception.message)

    def test_navigate__KeyOnList__RaisesPathNavigationError(self):
        config = {"items": [1, 2, 3]}
        with self.assertRaises(PathNavigationError) as ctx:
            navigate_path(config, ["items", "key"])

        self.assertEqual(ctx.exception.segment_index, 1)
        self.assertIn("non-dict", ctx.exception.message)

    def test_navigate__NestedError__ReportsCorrectIndex(self):
        config = {"outer": {"inner": [1, 2]}}
        with self.assertRaises(PathNavigationError) as ctx:
            navigate_path(config, ["outer", "inner", 10])

        self.assertEqual(ctx.exception.segment_index, 2)
        self.assertEqual(ctx.exception.path, ["outer", "inner", 10])


class PathNavigationErrorTests(unittest.TestCase):
    """Tests for PathNavigationError class."""

    def test_init__SetsAllAttributes(self):
        error = PathNavigationError("test message", segment_index=2, path=["a", "b", "c"])

        self.assertEqual(error.message, "test message")
        self.assertEqual(error.segment_index, 2)
        self.assertEqual(error.path, ["a", "b", "c"])

    def test_str__ReturnsMessage(self):
        error = PathNavigationError("test message", segment_index=0, path=["key"])

        self.assertEqual(str(error), "test message")


class GetValueAtPathTests(unittest.TestCase):
    """Tests for get_value_at_path function."""

    def test_getValue__EmptyPath__ReturnsConfig(self):
        config = {"key": "value"}
        result = get_value_at_path(config, "")
        self.assertEqual(result, config)

    def test_getValue__SimplePath__ReturnsValue(self):
        config = {"key": "value"}
        result = get_value_at_path(config, "key")
        self.assertEqual(result, "value")

    def test_getValue__NestedPath__ReturnsNestedValue(self):
        config = {"outer": {"inner": "value"}}
        result = get_value_at_path(config, "outer.inner")
        self.assertEqual(result, "value")

    def test_getValue__ListIndex__ReturnsElement(self):
        config = {"items": [1, 2, 3]}
        result = get_value_at_path(config, "items[1]")
        self.assertEqual(result, 2)

    def test_getValue__MixedPath__ReturnsCorrectValue(self):
        config = {"items": [{"name": "first"}, {"name": "second"}]}
        result = get_value_at_path(config, "items[0].name")
        self.assertEqual(result, "first")


class GetValueAtPathErrorTests(unittest.TestCase):
    """Tests for get_value_at_path error handling."""

    def test_getValue__KeyNotFound__RaisesKeyError(self):
        config = {"key": "value"}
        with self.assertRaises(KeyError) as ctx:
            get_value_at_path(config, "missing")

        self.assertIn("not found", str(ctx.exception))

    def test_getValue__NestedKeyNotFound__RaisesKeyError(self):
        config = {"outer": {"inner": "value"}}
        with self.assertRaises(KeyError) as ctx:
            get_value_at_path(config, "outer.missing")

        self.assertIn("not found", str(ctx.exception))

    def test_getValue__IndexOutOfRange__RaisesIndexError(self):
        config = {"items": [1, 2]}
        with self.assertRaises(IndexError) as ctx:
            get_value_at_path(config, "items[5]")

        self.assertIn("out of range", str(ctx.exception))

    def test_getValue__IndexOnDict__RaisesTypeError(self):
        config = {"key": "value"}
        with self.assertRaises(TypeError) as ctx:
            get_value_at_path(config, "key[0]")

        self.assertIn("non-list", str(ctx.exception))

    def test_getValue__KeyOnList__RaisesTypeError(self):
        config = {"items": [1, 2, 3]}
        with self.assertRaises(TypeError) as ctx:
            get_value_at_path(config, "items.key")

        self.assertIn("non-dict", str(ctx.exception))

    def test_getValue__KeyOnScalar__RaisesTypeError(self):
        config = {"value": 42}
        with self.assertRaises(TypeError) as ctx:
            get_value_at_path(config, "value.nested")

        self.assertIn("non-dict", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
