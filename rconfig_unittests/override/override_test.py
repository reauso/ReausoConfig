"""Tests for the override module."""

from unittest import TestCase

from rconfig.errors import InvalidOverrideSyntaxError
from rconfig.override import (
    Override,
    apply_overrides,
    extract_cli_overrides,
    parse_cli_arg,
    parse_dict_overrides,
    parse_override_key,
    parse_override_value,
)


class ParseOverrideKeyTests(TestCase):
    def test_parse__SimpleKey__ReturnsPathAndSetOperation(self):
        path, operation = parse_override_key("model")

        self.assertEqual(path, ["model"])
        self.assertEqual(operation, "set")

    def test_parse__DottedKey__ReturnsSplitPath(self):
        path, operation = parse_override_key("model.lr")

        self.assertEqual(path, ["model", "lr"])
        self.assertEqual(operation, "set")

    def test_parse__DeepDottedKey__ReturnsSplitPath(self):
        path, operation = parse_override_key("model.optimizer.learning_rate")

        self.assertEqual(path, ["model", "optimizer", "learning_rate"])
        self.assertEqual(operation, "set")

    def test_parse__ListIndex__ReturnsIntInPath(self):
        path, operation = parse_override_key("layers[0]")

        self.assertEqual(path, ["layers", 0])
        self.assertEqual(operation, "set")

    def test_parse__ListIndexWithDot__ReturnsComplexPath(self):
        path, operation = parse_override_key("layers[0].size")

        self.assertEqual(path, ["layers", 0, "size"])
        self.assertEqual(operation, "set")

    def test_parse__MultipleListIndices__ReturnsCorrectPath(self):
        path, operation = parse_override_key("model.layers[1].weights[0]")

        self.assertEqual(path, ["model", "layers", 1, "weights", 0])
        self.assertEqual(operation, "set")

    def test_parse__AddPrefix__ReturnsAddOperation(self):
        path, operation = parse_override_key("+callbacks")

        self.assertEqual(path, ["callbacks"])
        self.assertEqual(operation, "add")

    def test_parse__AddPrefixWithDot__ReturnsAddOperation(self):
        path, operation = parse_override_key("+model.callbacks")

        self.assertEqual(path, ["model", "callbacks"])
        self.assertEqual(operation, "add")

    def test_parse__RemovePrefix__ReturnsRemoveOperation(self):
        path, operation = parse_override_key("~dropout")

        self.assertEqual(path, ["dropout"])
        self.assertEqual(operation, "remove")

    def test_parse__RemovePrefixWithDot__ReturnsRemoveOperation(self):
        path, operation = parse_override_key("~model.dropout")

        self.assertEqual(path, ["model", "dropout"])
        self.assertEqual(operation, "remove")

    def test_parse__UnderscoreInKey__Works(self):
        path, operation = parse_override_key("learning_rate")

        self.assertEqual(path, ["learning_rate"])
        self.assertEqual(operation, "set")

    def test_parse__InvalidSyntax__RaisesInvalidOverrideSyntaxError(self):
        with self.assertRaises(InvalidOverrideSyntaxError):
            parse_override_key("[invalid")

    def test_parse__EmptyString__RaisesInvalidOverrideSyntaxError(self):
        with self.assertRaises(InvalidOverrideSyntaxError):
            parse_override_key("")

    def test_parse__StartsWithNumber__RaisesInvalidOverrideSyntaxError(self):
        with self.assertRaises(InvalidOverrideSyntaxError):
            parse_override_key("123invalid")


class ParseOverrideValueTests(TestCase):
    def test_parse__IntString_NoTypeHint__ReturnsInt(self):
        result = parse_override_value("42", None)

        self.assertEqual(result, 42)
        self.assertIsInstance(result, int)

    def test_parse__NegativeIntString_NoTypeHint__ReturnsInt(self):
        result = parse_override_value("-10", None)

        self.assertEqual(result, -10)
        self.assertIsInstance(result, int)

    def test_parse__FloatString_NoTypeHint__ReturnsFloat(self):
        result = parse_override_value("0.01", None)

        self.assertEqual(result, 0.01)
        self.assertIsInstance(result, float)

    def test_parse__NegativeFloatString_NoTypeHint__ReturnsFloat(self):
        result = parse_override_value("-3.14", None)

        self.assertEqual(result, -3.14)
        self.assertIsInstance(result, float)

    def test_parse__TrueLowercase_NoTypeHint__ReturnsBoolTrue(self):
        result = parse_override_value("true", None)

        self.assertIs(result, True)

    def test_parse__FalseLowercase_NoTypeHint__ReturnsBoolFalse(self):
        result = parse_override_value("false", None)

        self.assertIs(result, False)

    def test_parse__YesLowercase_NoTypeHint__ReturnsBoolTrue(self):
        result = parse_override_value("yes", None)

        self.assertIs(result, True)

    def test_parse__NoLowercase_NoTypeHint__ReturnsBoolFalse(self):
        result = parse_override_value("no", None)

        self.assertIs(result, False)

    def test_parse__NoneLowercase_NoTypeHint__ReturnsNone(self):
        result = parse_override_value("none", None)

        self.assertIsNone(result)

    def test_parse__NullLowercase_NoTypeHint__ReturnsNone(self):
        result = parse_override_value("null", None)

        self.assertIsNone(result)

    def test_parse__RegularString_NoTypeHint__ReturnsString(self):
        result = parse_override_value("hello", None)

        self.assertEqual(result, "hello")
        self.assertIsInstance(result, str)

    def test_parse__String_WithFloatTypeHint__ReturnsFloat(self):
        result = parse_override_value("42", float)

        self.assertEqual(result, 42.0)
        self.assertIsInstance(result, float)

    def test_parse__String_WithIntTypeHint__ReturnsInt(self):
        result = parse_override_value("42", int)

        self.assertEqual(result, 42)
        self.assertIsInstance(result, int)

    def test_parse__String_WithStrTypeHint__ReturnsStr(self):
        result = parse_override_value("42", str)

        self.assertEqual(result, "42")
        self.assertIsInstance(result, str)

    def test_parse__TrueString_WithBoolTypeHint__ReturnsBool(self):
        result = parse_override_value("true", bool)

        self.assertIs(result, True)

    def test_parse__InvalidValue_WithIntTypeHint__RaisesValueError(self):
        with self.assertRaises(ValueError):
            parse_override_value("abc", int)

    def test_parse__InvalidValue_WithFloatTypeHint__RaisesValueError(self):
        with self.assertRaises(ValueError):
            parse_override_value("abc", float)

    # --- Type Coercion: None type (lines 114-117) ---
    def test_parse__ValidNoneString_WithNoneTypeHint__ReturnsNone(self):
        self.assertIsNone(parse_override_value("none", type(None)))
        self.assertIsNone(parse_override_value("null", type(None)))
        self.assertIsNone(parse_override_value("~", type(None)))

    def test_parse__InvalidValue_WithNoneTypeHint__RaisesValueError(self):
        with self.assertRaises(ValueError) as ctx:
            parse_override_value("invalid", type(None))
        self.assertIn("Cannot convert", str(ctx.exception))

    # --- Type Coercion: Bool variants (lines 121-125) ---
    def test_parse__BoolFalseVariants_WithBoolTypeHint__ReturnsFalse(self):
        for value in ("false", "no", "0", "off"):
            with self.subTest(value=value):
                result = parse_override_value(value, bool)
                self.assertIs(result, False)

    def test_parse__BoolTrueVariants_WithBoolTypeHint__ReturnsTrue(self):
        for value in ("true", "yes", "1", "on"):
            with self.subTest(value=value):
                result = parse_override_value(value, bool)
                self.assertIs(result, True)

    def test_parse__InvalidBool_WithBoolTypeHint__RaisesValueError(self):
        with self.assertRaises(ValueError) as ctx:
            parse_override_value("maybe", bool)
        self.assertIn("Cannot convert", str(ctx.exception))
        self.assertIn("bool", str(ctx.exception))

    # --- Type Coercion: List type (lines 135-136) ---
    def test_parse__YamlList_WithListTypeHint__ReturnsList(self):
        result = parse_override_value("[1, 2, 3]", list)
        self.assertEqual(result, [1, 2, 3])

    def test_parse__YamlList_WithTypedListHint__ReturnsList(self):
        result = parse_override_value("[1, 2, 3]", list[int])
        self.assertEqual(result, [1, 2, 3])

    # --- Type Coercion: Dict type (lines 138-139) ---
    def test_parse__YamlDict_WithDictTypeHint__ReturnsDict(self):
        result = parse_override_value("{key: value}", dict)
        self.assertEqual(result, {"key": "value"})

    def test_parse__YamlDict_WithTypedDictHint__ReturnsDict(self):
        result = parse_override_value("{a: 1, b: 2}", dict[str, int])
        self.assertEqual(result, {"a": 1, "b": 2})

    # --- Type Coercion: Fallback (lines 141-145) ---
    def test_parse__CustomType_WithCallableTypeHint__CallsTypeConstructor(self):
        class CustomType:
            def __init__(self, value: str):
                self.value = value

        result = parse_override_value("test", CustomType)
        self.assertIsInstance(result, CustomType)
        self.assertEqual(result.value, "test")

    def test_parse__InvalidCustomType_WithNonCallableTypeHint__RaisesValueError(self):
        class NonConstructable:
            def __init__(self, a, b, c):  # Requires multiple args
                pass

        with self.assertRaises(ValueError) as ctx:
            parse_override_value("test", NonConstructable)
        self.assertIn("Cannot convert", str(ctx.exception))

    # --- YAML Parsing auto-inference (lines 173-177) ---
    def test_parse__YamlListSyntax_NoTypeHint__ReturnsListInferred(self):
        result = parse_override_value("[1, 2, 3]", None)
        self.assertEqual(result, [1, 2, 3])

    def test_parse__YamlDictSyntax_NoTypeHint__ReturnsDictInferred(self):
        result = parse_override_value("{key: value}", None)
        self.assertEqual(result, {"key": "value"})

    def test_parse__InvalidYamlSyntax_NoTypeHint__ReturnsStringFallback(self):
        # Invalid YAML that starts with [ but can't be parsed
        result = parse_override_value("[invalid yaml", None)
        self.assertEqual(result, "[invalid yaml")

    # --- YAML Parsing error (lines 185-191) ---
    def test_parse__InvalidYaml_WithListTypeHint__RaisesValueError(self):
        with self.assertRaises(ValueError) as ctx:
            parse_override_value("[[[invalid", list)
        self.assertIn("Cannot parse YAML", str(ctx.exception))


class ParseCliArgTests(TestCase):
    def test_parse__SetOverride__ReturnsOverride(self):
        result = parse_cli_arg("model.lr=0.01")

        self.assertIsNotNone(result)
        self.assertEqual(result.path, ["model", "lr"])
        self.assertEqual(result.value, "0.01")
        self.assertEqual(result.operation, "set")

    def test_parse__AddOverride__ReturnsOverride(self):
        result = parse_cli_arg("+callbacks=logger")

        self.assertIsNotNone(result)
        self.assertEqual(result.path, ["callbacks"])
        self.assertEqual(result.value, "logger")
        self.assertEqual(result.operation, "add")

    def test_parse__RemoveOverride__ReturnsOverride(self):
        result = parse_cli_arg("~dropout")

        self.assertIsNotNone(result)
        self.assertEqual(result.path, ["dropout"])
        self.assertIsNone(result.value)
        self.assertEqual(result.operation, "remove")

    def test_parse__FlagArg__ReturnsNone(self):
        result = parse_cli_arg("--help")

        self.assertIsNone(result)

    def test_parse__ShortFlagArg__ReturnsNone(self):
        result = parse_cli_arg("-v")

        self.assertIsNone(result)

    def test_parse__PositionalArg__ReturnsNone(self):
        result = parse_cli_arg("config.yaml")

        self.assertIsNone(result)

    def test_parse__ValueWithEquals__PreservesFullValue(self):
        result = parse_cli_arg("path=/home/user=name/file")

        self.assertIsNotNone(result)
        self.assertEqual(result.path, ["path"])
        self.assertEqual(result.value, "/home/user=name/file")

    def test_parse__EmptyValue__ReturnsEmptyString(self):
        result = parse_cli_arg("key=")

        self.assertIsNotNone(result)
        self.assertEqual(result.path, ["key"])
        self.assertEqual(result.value, "")

    # --- Invalid syntax tests (lines 216-237) ---
    def test_parse__InvalidRemoveSyntax__ReturnsNone(self):
        # ~123invalid is not a valid identifier (starts with number)
        result = parse_cli_arg("~123invalid")
        self.assertIsNone(result)

    def test_parse__RemoveWithEquals__ReturnsNone(self):
        # ~key=value is invalid for remove
        result = parse_cli_arg("~key=value")
        self.assertIsNone(result)

    def test_parse__InvalidSetKeySyntax__ReturnsNone(self):
        # 123invalid=value is not valid (key starts with number)
        result = parse_cli_arg("123invalid=value")
        self.assertIsNone(result)

    def test_parse__TildeOnly__ReturnsNone(self):
        # Just ~ with no key
        result = parse_cli_arg("~")
        self.assertIsNone(result)


class ExtractCliOverridesTests(TestCase):
    def test_extract__MixedArgs__ReturnsOnlyOverrides(self):
        argv = ["--debug", "model.lr=0.01", "-v", "epochs=10"]

        result = extract_cli_overrides(argv)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].path, ["model", "lr"])
        self.assertEqual(result[1].path, ["epochs"])

    def test_extract__EmptyList__ReturnsEmpty(self):
        result = extract_cli_overrides([])

        self.assertEqual(result, [])

    def test_extract__NoOverrides__ReturnsEmpty(self):
        result = extract_cli_overrides(["--help", "-v", "config.yaml"])

        self.assertEqual(result, [])

    def test_extract__AllOverrides__ReturnsAll(self):
        argv = ["lr=0.01", "+callback=log", "~dropout"]

        result = extract_cli_overrides(argv)

        self.assertEqual(len(result), 3)


class ParseDictOverridesTests(TestCase):
    def test_parse__SimpleDict__ReturnsOverrides(self):
        result = parse_dict_overrides({"model.lr": 0.01})

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].path, ["model", "lr"])
        self.assertEqual(result[0].value, 0.01)
        self.assertEqual(result[0].operation, "set")

    def test_parse__MultipleKeys__ReturnsAllOverrides(self):
        result = parse_dict_overrides({
            "model.lr": 0.01,
            "epochs": 100,
        })

        self.assertEqual(len(result), 2)

    def test_parse__WithOperations__ReturnsCorrectOperations(self):
        result = parse_dict_overrides({
            "+callbacks": "logger",
            "~dropout": None,
        })

        self.assertEqual(len(result), 2)

        add_override = next(o for o in result if o.operation == "add")
        remove_override = next(o for o in result if o.operation == "remove")

        self.assertEqual(add_override.path, ["callbacks"])
        self.assertEqual(add_override.value, "logger")
        self.assertEqual(remove_override.path, ["dropout"])

    def test_parse__EmptyDict__ReturnsEmpty(self):
        result = parse_dict_overrides({})

        self.assertEqual(result, [])


class ApplyOverridesTests(TestCase):
    def test_apply__SetTopLevelValue__ModifiesConfig(self):
        config = {"lr": 0.1, "epochs": 10}
        overrides = [Override(path=["lr"], value=0.01, operation="set")]

        result = apply_overrides(config, overrides)

        self.assertEqual(result["lr"], 0.01)
        self.assertEqual(result["epochs"], 10)
        # Original unchanged
        self.assertEqual(config["lr"], 0.1)

    def test_apply__SetNestedValue__ModifiesConfig(self):
        config = {"model": {"lr": 0.1, "size": 256}}
        overrides = [Override(path=["model", "lr"], value=0.01, operation="set")]

        result = apply_overrides(config, overrides)

        self.assertEqual(result["model"]["lr"], 0.01)
        self.assertEqual(result["model"]["size"], 256)

    def test_apply__SetListElement__ModifiesConfig(self):
        config = {"layers": [{"size": 64}, {"size": 64}]}
        overrides = [Override(path=["layers", 1, "size"], value=128, operation="set")]

        result = apply_overrides(config, overrides)

        self.assertEqual(result["layers"][0]["size"], 64)
        self.assertEqual(result["layers"][1]["size"], 128)

    def test_apply__AddToExistingList__AppendsValue(self):
        config = {"callbacks": ["a", "b"]}
        overrides = [Override(path=["callbacks"], value="c", operation="add")]

        result = apply_overrides(config, overrides)

        self.assertEqual(result["callbacks"], ["a", "b", "c"])

    def test_apply__AddToNonexistentKey__CreatesList(self):
        config = {"lr": 0.01}
        overrides = [Override(path=["callbacks"], value="logger", operation="add")]

        result = apply_overrides(config, overrides)

        self.assertEqual(result["callbacks"], ["logger"])

    def test_apply__RemoveKey__DeletesKey(self):
        config = {"dropout": 0.1, "lr": 0.01}
        overrides = [Override(path=["dropout"], value=None, operation="remove")]

        result = apply_overrides(config, overrides)

        self.assertNotIn("dropout", result)
        self.assertIn("lr", result)

    def test_apply__RemoveListElement__DeletesElement(self):
        config = {"layers": [{"size": 64}, {"size": 128}, {"size": 256}]}
        overrides = [Override(path=["layers", 1], value=None, operation="remove")]

        result = apply_overrides(config, overrides)

        self.assertEqual(len(result["layers"]), 2)
        self.assertEqual(result["layers"][0]["size"], 64)
        self.assertEqual(result["layers"][1]["size"], 256)

    def test_apply__MultipleOverrides_SamePath__LastWins(self):
        config = {"lr": 0.1}
        overrides = [
            Override(path=["lr"], value=0.01, operation="set"),
            Override(path=["lr"], value=0.001, operation="set"),
        ]

        result = apply_overrides(config, overrides)

        self.assertEqual(result["lr"], 0.001)

    def test_apply__EmptyOverrides__ReturnsUnchangedCopy(self):
        config = {"lr": 0.1}

        result = apply_overrides(config, [])

        self.assertEqual(result, config)
        self.assertIsNot(result, config)

    def test_apply__InvalidPath__RaisesKeyError(self):
        config = {"lr": 0.1}
        overrides = [Override(path=["nonexistent", "key"], value=1, operation="set")]

        with self.assertRaises(KeyError):
            apply_overrides(config, overrides)

    def test_apply__ListIndexOutOfRange__RaisesKeyError(self):
        config = {"layers": [{"size": 64}]}
        overrides = [Override(path=["layers", 5, "size"], value=128, operation="set")]

        with self.assertRaises(KeyError):
            apply_overrides(config, overrides)

    def test_apply__AddToNonList__RaisesValueError(self):
        config = {"lr": 0.1}
        overrides = [Override(path=["lr"], value="x", operation="add")]

        with self.assertRaises(ValueError):
            apply_overrides(config, overrides)

    # --- Empty path (line 300-301) ---
    def test_apply__EmptyPath__NoOp(self):
        config = {"lr": 0.1}
        overrides = [Override(path=[], value=999, operation="set")]

        result = apply_overrides(config, overrides)

        # Config unchanged (empty path is a no-op)
        self.assertEqual(result, {"lr": 0.1})

    # --- Set on non-dict (line 324-325) ---
    def test_apply__SetOnNonDict__RaisesKeyError(self):
        config = {"value": "string"}
        overrides = [Override(path=["value", "nested"], value=1, operation="set")]

        with self.assertRaises(KeyError) as ctx:
            apply_overrides(config, overrides)
        self.assertIn("non-dict", str(ctx.exception))

    # --- Add with list index (line 329-330) ---
    def test_apply__AddWithListIndex__RaisesValueError(self):
        config = {"items": ["a", "b", "c"]}
        overrides = [Override(path=["items", 0], value="new", operation="add")]

        with self.assertRaises(ValueError) as ctx:
            apply_overrides(config, overrides)
        self.assertIn("add operation with list index", str(ctx.exception))

    # --- Add on non-dict target (line 331-332) ---
    def test_apply__AddOnNonDictTarget__RaisesKeyError(self):
        config = {"value": "string"}
        overrides = [Override(path=["value", "key"], value="x", operation="add")]

        with self.assertRaises(KeyError) as ctx:
            apply_overrides(config, overrides)
        self.assertIn("non-dict", str(ctx.exception))

    # --- Remove list index out of range (line 342-343) ---
    def test_apply__RemoveListIndexOutOfRange__RaisesKeyError(self):
        config = {"items": ["a", "b"]}
        overrides = [Override(path=["items", 99], value=None, operation="remove")]

        with self.assertRaises(KeyError) as ctx:
            apply_overrides(config, overrides)
        self.assertIn("out of range", str(ctx.exception))

    # --- Remove on non-dict target (line 346-347) ---
    def test_apply__RemoveOnNonDictTarget__RaisesKeyError(self):
        config = {"value": "string"}
        overrides = [Override(path=["value", "key"], value=None, operation="remove")]

        with self.assertRaises(KeyError) as ctx:
            apply_overrides(config, overrides)
        self.assertIn("non-dict", str(ctx.exception))

    # --- Remove non-existent key (line 348-349) ---
    def test_apply__RemoveNonExistentKey__RaisesKeyError(self):
        config = {"existing": 1}
        overrides = [Override(path=["nonexistent"], value=None, operation="remove")]

        with self.assertRaises(KeyError) as ctx:
            apply_overrides(config, overrides)
        self.assertIn("not found for removal", str(ctx.exception))


class OverrideCoverageTests(TestCase):
    """Tests to improve override.py coverage for edge cases."""

    def test_parse_cli_arg__TildeWithEmptyKey__ReturnsNone(self):
        """Test parsing tilde with empty/invalid key returns None."""
        # Arrange - line 219
        # Act - empty key after ~
        result = parse_cli_arg("~")

        # Assert
        self.assertIsNone(result)

    def test_parse_cli_arg__TildeWithEquals__ReturnsNone(self):
        """Test parsing ~key=value (invalid remove syntax) returns None."""
        # The ~key=value is actually parsed as a valid remove in some cases
        # but ~=value should fail
        result = parse_cli_arg("~=value")

        # This should be None (invalid key syntax)
        self.assertIsNone(result)

    def test_apply_single_override__SetListIndex__UpdatesItem(self):
        """Test setting a list item by index."""
        # Arrange - lines 320-322
        config = {"items": ["a", "b", "c"]}
        override = Override(path=["items", 1], value="updated", operation="set")

        # Act - apply_overrides returns a new dict
        result = apply_overrides(config, [override])

        # Assert - the result should have the updated value
        self.assertEqual(result["items"][1], "updated")

    def test_apply_single_override__SetListIndexOutOfRange__RaisesKeyError(self):
        """Test setting a list item with out of range index."""
        # Arrange - lines 320-321
        config = {"items": ["a", "b"]}
        override = Override(path=["items", 99], value="x", operation="set")

        # Act & Assert
        with self.assertRaises(KeyError) as ctx:
            apply_overrides(config, [override])
        self.assertIn("out of range", str(ctx.exception))
