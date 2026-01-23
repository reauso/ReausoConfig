"""Tests for path_utils module."""

import unittest

from rconfig._internal.path_utils import (
    PathNavigationError,
    build_child_path,
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

    def test_parse__DoubleQuotedKey__ReturnsStringSegment(self):
        result = parse_path_segments('models["resnet"]')
        self.assertEqual(result, ["models", "resnet"])

    def test_parse__SingleQuotedKey__ReturnsStringSegment(self):
        result = parse_path_segments("models['resnet']")
        self.assertEqual(result, ["models", "resnet"])

    def test_parse__MixedPathWithStringKey__ParsesCorrectly(self):
        result = parse_path_segments('parent.models["resnet"].layers[0]')
        self.assertEqual(result, ["parent", "models", "resnet", "layers", 0])

    def test_parse__StringKeyWithSpaces__PreservesSpaces(self):
        result = parse_path_segments('data["key with spaces"]')
        self.assertEqual(result, ["data", "key with spaces"])

    def test_parse__CombinedBracketAndDot__ParsesAll(self):
        result = parse_path_segments('config["db"].host')
        self.assertEqual(result, ["config", "db", "host"])

    def test_parse__NumericStringKey__ReturnsStringSegment(self):
        """Quoted numeric key ["0"] is a string, not an int."""
        result = parse_path_segments('data["0"]')
        self.assertEqual(result, ["data", "0"])

    def test_parse__KeyWithSpecialChars__PreservesChars(self):
        """Quoted keys with dots and dashes are preserved as-is."""
        result = parse_path_segments('config["my-key.name"]')
        self.assertEqual(result, ["config", "my-key.name"])


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


class PathExistsTests(unittest.TestCase):
    """Tests for path_exists function."""

    def test_pathExists__ExistingPath__ReturnsTrue(self):
        from rconfig._internal.path_utils import path_exists

        config = {"model": {"lr": 0.01}}
        self.assertTrue(path_exists(config, "model.lr"))

    def test_pathExists__NonExistingPath__ReturnsFalse(self):
        from rconfig._internal.path_utils import path_exists

        config = {"model": {"lr": 0.01}}
        self.assertFalse(path_exists(config, "model.epochs"))

    def test_pathExists__EmptyPath__ReturnsTrue(self):
        from rconfig._internal.path_utils import path_exists

        config = {"key": "value"}
        self.assertTrue(path_exists(config, ""))

    def test_pathExists__NestedPath__WorksCorrectly(self):
        from rconfig._internal.path_utils import path_exists

        config = {"a": {"b": {"c": "value"}}}
        self.assertTrue(path_exists(config, "a.b.c"))
        self.assertFalse(path_exists(config, "a.b.d"))


class SetValueAtPathTests(unittest.TestCase):
    """Tests for set_value_at_path function."""

    def test_setValue__SimplePath__SetsValue(self):
        from rconfig._internal.path_utils import set_value_at_path

        config = {"existing": "value"}
        set_value_at_path(config, "new_key", 42)
        self.assertEqual(config["new_key"], 42)

    def test_setValue__NestedPath__SetsValueWithCreateParents(self):
        from rconfig._internal.path_utils import set_value_at_path

        config = {}
        set_value_at_path(config, "a.b.c", "value", create_parents=True)
        self.assertEqual(config["a"]["b"]["c"], "value")

    def test_setValue__NestedPathNoCreateParents__RaisesKeyError(self):
        from rconfig._internal.path_utils import set_value_at_path

        config = {}
        with self.assertRaises(KeyError):
            set_value_at_path(config, "a.b.c", "value", create_parents=False)

    def test_setValue__ExistingNestedPath__OverwritesValue(self):
        from rconfig._internal.path_utils import set_value_at_path

        config = {"model": {"lr": 0.001}}
        set_value_at_path(config, "model.lr", 0.01)
        self.assertEqual(config["model"]["lr"], 0.01)

    def test_setValue__EmptyPath__RaisesValueError(self):
        from rconfig._internal.path_utils import set_value_at_path

        config = {}
        with self.assertRaises(ValueError):
            set_value_at_path(config, "", "value")

    def test_setValue__ListIndex__RaisesTypeError(self):
        from rconfig._internal.path_utils import set_value_at_path

        config = {}
        with self.assertRaises(TypeError):
            set_value_at_path(config, "items[0]", "value", create_parents=True)


class BuildChildPathTests(unittest.TestCase):
    """Tests for build_child_path function."""

    def test_buildChildPath__EmptyParentWithStringKey__ReturnsKey(self):
        result = build_child_path("", "model")
        self.assertEqual(result, "model")

    def test_buildChildPath__NonEmptyParentWithStringKey__ReturnsDotSeparated(self):
        result = build_child_path("model", "layers")
        self.assertEqual(result, "model.layers")

    def test_buildChildPath__EmptyParentWithIntIndex__ReturnsBracketNotation(self):
        result = build_child_path("", 0)
        self.assertEqual(result, "[0]")

    def test_buildChildPath__NonEmptyParentWithIntIndex__ReturnsBracketNotation(self):
        result = build_child_path("callbacks", 0)
        self.assertEqual(result, "callbacks[0]")

    def test_buildChildPath__NestedPathWithStringKey__AppendsCorrectly(self):
        result = build_child_path("model.encoder", "hidden_size")
        self.assertEqual(result, "model.encoder.hidden_size")

    def test_buildChildPath__NestedPathWithIntIndex__AppendsCorrectly(self):
        result = build_child_path("model.layers", 2)
        self.assertEqual(result, "model.layers[2]")


if __name__ == "__main__":
    unittest.main()
