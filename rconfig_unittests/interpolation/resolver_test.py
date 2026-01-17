"""Unit tests for interpolation resolver."""

import os
import unittest

from rconfig.interpolation import resolve_interpolations
from rconfig.errors import (
    CircularInterpolationError,
    EnvironmentVariableError,
    InterpolationResolutionError,
)


class ResolveInterpolationsTests(unittest.TestCase):
    """Tests for resolve_interpolations function."""

    # === Basic resolution ===

    def test_resolve__NoInterpolations__ReturnsConfigUnchanged(self):
        config = {"a": 1, "b": "hello"}
        result = resolve_interpolations(config)
        self.assertEqual(result, config)

    def test_resolve__SimpleReference__ResolvesToValue(self):
        config = {"a": 10, "b": "${/a}"}
        result = resolve_interpolations(config)
        self.assertEqual(result["b"], 10)

    def test_resolve__NestedReference__ResolvesToValue(self):
        config = {"model": {"lr": 0.01}, "training": {"lr": "${/model.lr}"}}
        result = resolve_interpolations(config)
        self.assertEqual(result["training"]["lr"], 0.01)

    def test_resolve__ListReference__ResolvesToList(self):
        config = {"items": [1, 2, 3], "copy": "${/items}"}
        result = resolve_interpolations(config)
        self.assertEqual(result["copy"], [1, 2, 3])

    # === Type preservation ===

    def test_resolve__StandaloneInteger__PreservesType(self):
        config = {"a": 42, "b": "${/a}"}
        result = resolve_interpolations(config)
        self.assertIsInstance(result["b"], int)
        self.assertEqual(result["b"], 42)

    def test_resolve__StandaloneFloat__PreservesType(self):
        config = {"a": 3.14, "b": "${/a}"}
        result = resolve_interpolations(config)
        self.assertIsInstance(result["b"], float)
        self.assertEqual(result["b"], 3.14)

    def test_resolve__StandaloneBool__PreservesType(self):
        config = {"a": True, "b": "${/a}"}
        result = resolve_interpolations(config)
        self.assertIsInstance(result["b"], bool)
        self.assertEqual(result["b"], True)

    def test_resolve__StandaloneList__PreservesType(self):
        config = {"a": [1, 2, 3], "b": "${/a}"}
        result = resolve_interpolations(config)
        self.assertIsInstance(result["b"], list)
        self.assertEqual(result["b"], [1, 2, 3])

    def test_resolve__EmbeddedInterpolation__BecomesString(self):
        config = {"a": 42, "b": "value: ${/a}"}
        result = resolve_interpolations(config)
        self.assertIsInstance(result["b"], str)
        self.assertEqual(result["b"], "value: 42")

    # === Arithmetic expressions ===

    def test_resolve__Addition__ComputesResult(self):
        config = {"a": 10, "b": 5, "c": "${/a + /b}"}
        result = resolve_interpolations(config)
        self.assertEqual(result["c"], 15)

    def test_resolve__Subtraction__ComputesResult(self):
        config = {"a": 10, "b": 3, "c": "${/a - /b}"}
        result = resolve_interpolations(config)
        self.assertEqual(result["c"], 7)

    def test_resolve__Multiplication__ComputesResult(self):
        config = {"a": 10, "b": 3, "c": "${/a * /b}"}
        result = resolve_interpolations(config)
        self.assertEqual(result["c"], 30)

    def test_resolve__Division__ComputesResult(self):
        config = {"a": 10, "b": 4, "c": "${/a / /b}"}
        result = resolve_interpolations(config)
        self.assertEqual(result["c"], 2.5)

    def test_resolve__FloorDivision__ComputesResult(self):
        config = {"a": 10, "b": 3, "c": "${/a // /b}"}
        result = resolve_interpolations(config)
        self.assertEqual(result["c"], 3)

    def test_resolve__Modulo__ComputesResult(self):
        config = {"a": 10, "b": 3, "c": "${/a % /b}"}
        result = resolve_interpolations(config)
        self.assertEqual(result["c"], 1)

    def test_resolve__Power__ComputesResult(self):
        config = {"a": 2, "c": "${/a ** 3}"}
        result = resolve_interpolations(config)
        self.assertEqual(result["c"], 8)

    def test_resolve__UnaryMinus__ComputesResult(self):
        config = {"a": 5, "c": "${-/a}"}
        result = resolve_interpolations(config)
        self.assertEqual(result["c"], -5)

    def test_resolve__ComplexExpression__ComputesResult(self):
        config = {"a": 10, "b": 5, "c": "${(/a + /b) * 2}"}
        result = resolve_interpolations(config)
        self.assertEqual(result["c"], 30)

    # === Comparison operators ===

    def test_resolve__GreaterThan__ReturnsBoolean(self):
        config = {"a": 10, "b": 5, "c": "${/a > /b}"}
        result = resolve_interpolations(config)
        self.assertEqual(result["c"], True)

    def test_resolve__LessThan__ReturnsBoolean(self):
        config = {"a": 3, "b": 5, "c": "${/a < /b}"}
        result = resolve_interpolations(config)
        self.assertEqual(result["c"], True)

    def test_resolve__Equality__ReturnsBoolean(self):
        config = {"a": 5, "c": "${/a == 5}"}
        result = resolve_interpolations(config)
        self.assertEqual(result["c"], True)

    def test_resolve__Inequality__ReturnsBoolean(self):
        config = {"a": 5, "c": "${/a != 3}"}
        result = resolve_interpolations(config)
        self.assertEqual(result["c"], True)

    # === Boolean operators ===

    def test_resolve__And__ReturnsBoolean(self):
        config = {"a": True, "b": True, "c": "${/a and /b}"}
        result = resolve_interpolations(config)
        self.assertEqual(result["c"], True)

    def test_resolve__Or__ReturnsBoolean(self):
        config = {"a": False, "b": True, "c": "${/a or /b}"}
        result = resolve_interpolations(config)
        self.assertEqual(result["c"], True)

    def test_resolve__Not__ReturnsBoolean(self):
        config = {"a": False, "c": "${not /a}"}
        result = resolve_interpolations(config)
        self.assertEqual(result["c"], True)

    def test_resolve__In__ReturnsBoolean(self):
        config = {"items": ["a", "b"], "c": '${"a" in /items}'}
        result = resolve_interpolations(config)
        self.assertEqual(result["c"], True)

    def test_resolve__NotIn__ReturnsBoolean(self):
        config = {"items": ["a", "b"], "c": '${"c" not in /items}'}
        result = resolve_interpolations(config)
        self.assertEqual(result["c"], True)

    # === List operations ===

    def test_resolve__ListConcat__ConcatenatesLists(self):
        config = {"a": [1, 2], "b": [3, 4], "c": "${/a + /b}"}
        result = resolve_interpolations(config)
        self.assertEqual(result["c"], [1, 2, 3, 4])

    def test_resolve__ListSubtract__RemovesElements(self):
        config = {"a": [1, 2, 3, 4], "c": "${/a - [2, 4]}"}
        result = resolve_interpolations(config)
        self.assertEqual(result["c"], [1, 3])

    def test_resolve__ListIndex__ReturnsElement(self):
        config = {"items": [10, 20, 30], "c": "${/items[1]}"}
        result = resolve_interpolations(config)
        self.assertEqual(result["c"], 20)

    def test_resolve__ListNegativeIndex__ReturnsElement(self):
        config = {"items": [10, 20, 30], "c": "${/items[-1]}"}
        result = resolve_interpolations(config)
        self.assertEqual(result["c"], 30)

    def test_resolve__ListSlice__ReturnsSublist(self):
        config = {"items": [1, 2, 3, 4, 5], "c": "${/items[1:4]}"}
        result = resolve_interpolations(config)
        self.assertEqual(result["c"], [2, 3, 4])

    def test_resolve__ListSliceFromStart__ReturnsSublist(self):
        config = {"items": [1, 2, 3, 4, 5], "c": "${/items[:3]}"}
        result = resolve_interpolations(config)
        self.assertEqual(result["c"], [1, 2, 3])

    def test_resolve__ListSliceToEnd__ReturnsSublist(self):
        config = {"items": [1, 2, 3, 4, 5], "c": "${/items[2:]}"}
        result = resolve_interpolations(config)
        self.assertEqual(result["c"], [3, 4, 5])

    def test_resolve__ListRemove__RemovesAtIndex(self):
        config = {"items": [1, 2, 3], "c": "${/items.remove(0)}"}
        result = resolve_interpolations(config)
        self.assertEqual(result["c"], [2, 3])

    def test_resolve__Len__ReturnsLength(self):
        config = {"items": [1, 2, 3, 4, 5], "c": "${len(/items)}"}
        result = resolve_interpolations(config)
        self.assertEqual(result["c"], 5)

    # === String operations ===

    def test_resolve__StringConcat__ConcatenatesStrings(self):
        config = {"name": "test", "c": '${"prefix_" + /name + "_suffix"}'}
        result = resolve_interpolations(config)
        self.assertEqual(result["c"], "prefix_test_suffix")

    def test_resolve__NumberToStringConcat__ConvertsAndConcatenates(self):
        config = {"num": 42, "c": '${"value_" + /num}'}
        result = resolve_interpolations(config)
        self.assertEqual(result["c"], "value_42")

    # === Environment variables ===

    def test_resolve__EnvVar__ResolvesFromEnvironment(self):
        os.environ["TEST_INTERP_VAR"] = "test_value"
        try:
            config = {"c": "${env:TEST_INTERP_VAR}"}
            result = resolve_interpolations(config)
            self.assertEqual(result["c"], "test_value")
        finally:
            del os.environ["TEST_INTERP_VAR"]

    def test_resolve__EnvVarWithDefault__UsesDefaultWhenMissing(self):
        config = {"c": '${env:NONEXISTENT_VAR_12345 ?: "default_value"}'}
        result = resolve_interpolations(config)
        self.assertEqual(result["c"], "default_value")

    def test_resolve__EnvVarWithPathDefault__UsesPathDefault(self):
        config = {"c": '${env:NONEXISTENT_VAR_12345 ?: "/default/path"}'}
        result = resolve_interpolations(config)
        self.assertEqual(result["c"], "/default/path")

    def test_resolve__EnvVarWithBoolDefault__UsesBoolDefault(self):
        config = {"c": "${env:NONEXISTENT_VAR_12345 ?: true}"}
        result = resolve_interpolations(config)
        self.assertEqual(result["c"], True)

    def test_resolve__EnvVarWithNumberDefault__UsesNumberDefault(self):
        config = {"c": "${env:NONEXISTENT_VAR_12345 ?: 42}"}
        result = resolve_interpolations(config)
        self.assertEqual(result["c"], 42)

    def test_resolve__MissingEnvVar__RaisesError(self):
        config = {"c": "${env:DEFINITELY_NOT_SET_VAR_XYZ}"}
        with self.assertRaises(EnvironmentVariableError) as ctx:
            resolve_interpolations(config)
        self.assertEqual(ctx.exception.var_name, "DEFINITELY_NOT_SET_VAR_XYZ")

    # === Embedded interpolations ===

    def test_resolve__MultipleEmbedded__ReplacesAll(self):
        config = {"a": "foo", "b": "bar", "c": "start_${/a}_middle_${/b}_end"}
        result = resolve_interpolations(config)
        self.assertEqual(result["c"], "start_foo_middle_bar_end")

    # === Error cases ===

    def test_resolve__MissingPath__RaisesError(self):
        config = {"c": "${/nonexistent.path}"}
        with self.assertRaises(InterpolationResolutionError):
            resolve_interpolations(config)

    def test_resolve__CircularReference__RaisesError(self):
        config = {"a": "${/b}", "b": "${/a}"}
        with self.assertRaises(CircularInterpolationError):
            resolve_interpolations(config)

    def test_resolve__SelfReference__RaisesError(self):
        config = {"a": "${/a}"}
        with self.assertRaises(CircularInterpolationError):
            resolve_interpolations(config)

    # === Nested structures ===

    def test_resolve__NestedDicts__ResolvesAllLevels(self):
        config = {
            "defaults": {"lr": 0.01},
            "model": {
                "training": {
                    "learning_rate": "${/defaults.lr}",
                }
            },
        }
        result = resolve_interpolations(config)
        self.assertEqual(result["model"]["training"]["learning_rate"], 0.01)

    def test_resolve__ListOfDicts__ResolvesAllElements(self):
        config = {
            "base": 100,
            "items": [
                {"value": "${/base}"},
                {"value": "${/base * 2}"},
            ],
        }
        result = resolve_interpolations(config)
        self.assertEqual(result["items"][0]["value"], 100)
        self.assertEqual(result["items"][1]["value"], 200)

    def test_resolve__DictInList__ResolvesCorrectly(self):
        config = {
            "callbacks": [
                {"name": "logger"},
                {"name": "checkpoint"},
            ],
            "first_callback": "${/callbacks[0].name}",
        }
        result = resolve_interpolations(config)
        self.assertEqual(result["first_callback"], "logger")


    # === Filter operations (CRITICAL) ===

    def test_resolve__FilterGreaterThan__FiltersCorrectly(self):
        config = {"items": [1, 3, 5, 7, 9], "result": "${/items | filter(x > 5)}"}
        result = resolve_interpolations(config)
        self.assertEqual(result["result"], [7, 9])

    def test_resolve__FilterLessThan__FiltersCorrectly(self):
        config = {"items": [1, 3, 5, 7, 9], "result": "${/items | filter(x < 5)}"}
        result = resolve_interpolations(config)
        self.assertEqual(result["result"], [1, 3])

    def test_resolve__FilterEquals__FiltersCorrectly(self):
        config = {"items": [1, 2, 1, 3, 1], "result": "${/items | filter(x == 1)}"}
        result = resolve_interpolations(config)
        self.assertEqual(result["result"], [1, 1, 1])

    def test_resolve__FilterNoMatches__ReturnsEmptyList(self):
        config = {"items": [1, 2, 3], "result": "${/items | filter(x > 100)}"}
        result = resolve_interpolations(config)
        self.assertEqual(result["result"], [])

    def test_resolve__FilterAllMatch__ReturnsAllItems(self):
        config = {"items": [1, 2, 3], "result": "${/items | filter(x > 0)}"}
        result = resolve_interpolations(config)
        self.assertEqual(result["result"], [1, 2, 3])

    # === Error handling (CRITICAL) ===

    def test_resolve__DivisionByZero__RaisesError(self):
        config = {"a": 10, "result": "${/a / 0}"}
        with self.assertRaises((ZeroDivisionError, InterpolationResolutionError)):
            resolve_interpolations(config)

    def test_resolve__FloorDivisionByZero__RaisesError(self):
        config = {"a": 10, "result": "${/a // 0}"}
        with self.assertRaises((ZeroDivisionError, InterpolationResolutionError)):
            resolve_interpolations(config)

    def test_resolve__ModuloByZero__RaisesError(self):
        config = {"a": 10, "result": "${/a % 0}"}
        with self.assertRaises((ZeroDivisionError, InterpolationResolutionError)):
            resolve_interpolations(config)

    def test_resolve__ListIndexOutOfBounds__RaisesError(self):
        config = {"items": [1, 2, 3], "result": "${/items[10]}"}
        with self.assertRaises((IndexError, InterpolationResolutionError)):
            resolve_interpolations(config)

    def test_resolve__ListNegativeIndexOutOfBounds__RaisesError(self):
        config = {"items": [1, 2, 3], "result": "${/items[-10]}"}
        with self.assertRaises((IndexError, InterpolationResolutionError)):
            resolve_interpolations(config)

    # === Empty collection operations (HIGH) ===

    def test_resolve__EmptyListConcatLeft__ReturnsOtherList(self):
        config = {"result": "${[] + [1, 2]}"}
        result = resolve_interpolations(config)
        self.assertEqual(result["result"], [1, 2])

    def test_resolve__EmptyListConcatRight__ReturnsOtherList(self):
        config = {"items": [1, 2], "result": "${/items + []}"}
        result = resolve_interpolations(config)
        self.assertEqual(result["result"], [1, 2])

    def test_resolve__EmptyListSubtract__ReturnsEmptyList(self):
        config = {"result": "${[] - [1]}"}
        result = resolve_interpolations(config)
        self.assertEqual(result["result"], [])

    def test_resolve__LenEmptyList__ReturnsZero(self):
        config = {"result": "${len([])}"}
        result = resolve_interpolations(config)
        self.assertEqual(result["result"], 0)

    def test_resolve__EmptyListIndex__RaisesError(self):
        config = {"result": "${[][0]}"}
        with self.assertRaises((IndexError, InterpolationResolutionError)):
            resolve_interpolations(config)

    # === Circular reference edge cases (HIGH) ===

    def test_resolve__ThreeWayCycle__RaisesError(self):
        config = {"a": "${/b}", "b": "${/c}", "c": "${/a}"}
        with self.assertRaises(CircularInterpolationError):
            resolve_interpolations(config)

    def test_resolve__CycleInSubset__RaisesError(self):
        config = {"x": 1, "a": "${/b}", "b": "${/a}"}
        with self.assertRaises(CircularInterpolationError):
            resolve_interpolations(config)

    def test_resolve__LinearChain__NoCycleDetected(self):
        config = {"a": 1, "b": "${/a}", "c": "${/b}"}
        result = resolve_interpolations(config)
        self.assertEqual(result["c"], 1)

    def test_resolve__ParallelChains__NoCycleDetected(self):
        config = {"a": 1, "b": "${/a}", "c": 2, "d": "${/c}"}
        result = resolve_interpolations(config)
        self.assertEqual(result["b"], 1)
        self.assertEqual(result["d"], 2)

    def test_resolve__DiamondPattern__NoCycleDetected(self):
        # a → b, a → c, b → d, c → d (diamond, not cycle)
        config = {"a": 1, "b": "${/a}", "c": "${/a}", "d": "${/b + /c}"}
        result = resolve_interpolations(config)
        self.assertEqual(result["d"], 2)

    # === Slice with negative indices (HIGH) ===

    def test_resolve__SliceLastTwo__ReturnsSublist(self):
        config = {"items": [1, 2, 3, 4, 5], "result": "${/items[-2:]}"}
        result = resolve_interpolations(config)
        self.assertEqual(result["result"], [4, 5])

    def test_resolve__SliceExceptLastTwo__ReturnsSublist(self):
        config = {"items": [1, 2, 3, 4, 5], "result": "${/items[:-2]}"}
        result = resolve_interpolations(config)
        self.assertEqual(result["result"], [1, 2, 3])

    def test_resolve__SliceNegativeStartPositiveEnd__ReturnsSublist(self):
        config = {"items": [1, 2, 3, 4, 5], "result": "${/items[-3:4]}"}
        result = resolve_interpolations(config)
        self.assertEqual(result["result"], [3, 4])

    # === Null/None handling (MEDIUM) ===

    def test_resolve__NullReference__PreservesNull(self):
        config = {"a": None, "b": "${/a}"}
        result = resolve_interpolations(config)
        self.assertIsNone(result["b"])

    def test_resolve__NullInList__PreservesNull(self):
        config = {"items": [None, 1, 2], "result": "${/items}"}
        result = resolve_interpolations(config)
        self.assertEqual(result["result"], [None, 1, 2])

    def test_resolve__StandaloneNullLiteral__PreservesType(self):
        config = {"result": "${null}"}
        result = resolve_interpolations(config)
        self.assertIsNone(result["result"])

    def test_resolve__NullEquality__WorksCorrectly(self):
        config = {"a": None, "result": "${/a == null}"}
        result = resolve_interpolations(config)
        self.assertEqual(result["result"], True)

    def test_resolve__NullInequality__WorksCorrectly(self):
        config = {"a": 5, "result": "${/a != null}"}
        result = resolve_interpolations(config)
        self.assertEqual(result["result"], True)

    # === Operator precedence (MEDIUM) ===

    def test_resolve__ArithmeticPrecedence__MultiplicationBeforeAddition(self):
        config = {"result": "${5 + 3 * 2}"}
        result = resolve_interpolations(config)
        self.assertEqual(result["result"], 11)  # Not 16

    def test_resolve__ArithmeticPrecedence__DivisionBeforeSubtraction(self):
        config = {"result": "${10 - 6 / 2}"}
        result = resolve_interpolations(config)
        self.assertEqual(result["result"], 7.0)  # Not 2

    def test_resolve__BooleanPrecedence__AndBeforeOr(self):
        config = {"result": "${true or false and false}"}
        result = resolve_interpolations(config)
        self.assertEqual(result["result"], True)  # true or (false and false) = true

    def test_resolve__ParenthesesOverride__CorrectOrder(self):
        config = {"result": "${(5 + 3) * 2}"}
        result = resolve_interpolations(config)
        self.assertEqual(result["result"], 16)

    def test_resolve__PowerRightAssociative__CorrectOrder(self):
        config = {"result": "${2 ** 3 ** 2}"}
        result = resolve_interpolations(config)
        self.assertEqual(result["result"], 512)  # 2^(3^2) = 2^9 = 512

    # === Multiple embedded interpolations (MEDIUM) ===

    def test_resolve__ThreeEmbeddedInterpolations__ResolvesAll(self):
        config = {"a": 1, "b": 2, "c": 3, "result": "${/a}${/b}${/c}"}
        result = resolve_interpolations(config)
        self.assertEqual(result["result"], "123")

    def test_resolve__EmbeddedWithExpression__ResolvesCorrectly(self):
        config = {"a": 10, "b": 3, "result": "${/a} - ${/b} = ${/a - /b}"}
        result = resolve_interpolations(config)
        self.assertEqual(result["result"], "10 - 3 = 7")

    def test_resolve__AdjacentInterpolations__ResolvesCorrectly(self):
        config = {"a": "hello", "b": "world", "result": "${/a}${/b}"}
        result = resolve_interpolations(config)
        self.assertEqual(result["result"], "helloworld")

    # === String edge cases (LOW) ===

    def test_resolve__EmptyStringConcat__WorksCorrectly(self):
        config = {"a": "test", "result": '${\"\" + /a}'}
        result = resolve_interpolations(config)
        self.assertEqual(result["result"], "test")

    def test_resolve__StringWithSpaces__PreservesSpaces(self):
        config = {"a": "hello world", "result": "${/a}"}
        result = resolve_interpolations(config)
        self.assertEqual(result["result"], "hello world")

    # === Scientific notation (LOW) ===

    def test_resolve__ScientificNotationLarge__ParsesCorrectly(self):
        config = {"result": "${1e10}"}
        result = resolve_interpolations(config)
        self.assertEqual(result["result"], 1e10)

    def test_resolve__ScientificNotationSmall__ParsesCorrectly(self):
        config = {"result": "${1e-10}"}
        result = resolve_interpolations(config)
        self.assertEqual(result["result"], 1e-10)

    def test_resolve__ScientificNotationNegative__ParsesCorrectly(self):
        config = {"result": "${-1.5e3}"}
        result = resolve_interpolations(config)
        self.assertEqual(result["result"], -1500.0)

    # === Chained references ===

    def test_resolve__ChainedReferences__ResolvesInOrder(self):
        config = {"a": 1, "b": "${/a + 1}", "c": "${/b + 1}"}
        result = resolve_interpolations(config)
        self.assertEqual(result["c"], 3)

    def test_resolve__DeeplyNested__ResolvesAllLevels(self):
        config = {
            "level1": {
                "level2": {
                    "level3": {
                        "value": 42
                    }
                }
            },
            "result": "${/level1.level2.level3.value}"
        }
        result = resolve_interpolations(config)
        self.assertEqual(result["result"], 42)

    # === List removal edge cases ===

    def test_resolve__RemoveNonExistentValue__ReturnsOriginalList(self):
        config = {"items": [1, 2, 3], "result": "${/items - [99]}"}
        result = resolve_interpolations(config)
        self.assertEqual(result["result"], [1, 2, 3])

    def test_resolve__RemoveAllValues__ReturnsEmptyList(self):
        config = {"items": [1, 2, 3], "result": "${/items - [1, 2, 3]}"}
        result = resolve_interpolations(config)
        self.assertEqual(result["result"], [])

    def test_resolve__RemoveDuplicates__RemovesAll(self):
        config = {"items": [1, 2, 1, 3, 1], "result": "${/items - [1]}"}
        result = resolve_interpolations(config)
        self.assertEqual(result["result"], [2, 3])

    # === Unary plus operator (evaluator line 245-246) ===

    def test_resolve__UnaryPlus__ReturnsValue(self):
        config = {"result": "${+5}"}
        result = resolve_interpolations(config)
        self.assertEqual(result["result"], 5)

    def test_resolve__UnaryPlusOnNegative__ReturnsNegative(self):
        config = {"result": "${+-5}"}
        result = resolve_interpolations(config)
        self.assertEqual(result["result"], -5)

    def test_resolve__UnaryPlusOnFloat__ReturnsFloat(self):
        config = {"result": "${+3.14}"}
        result = resolve_interpolations(config)
        self.assertEqual(result["result"], 3.14)

    # === Less-than-or-equal operator (evaluator line 277-278) ===

    def test_resolve__LessOrEqual__ReturnsTrue(self):
        config = {"result": "${5 <= 5}"}
        result = resolve_interpolations(config)
        self.assertEqual(result["result"], True)

    def test_resolve__LessOrEqualTrue__ReturnsTrue(self):
        config = {"result": "${3 <= 5}"}
        result = resolve_interpolations(config)
        self.assertEqual(result["result"], True)

    def test_resolve__LessOrEqualFalse__ReturnsFalse(self):
        config = {"result": "${5 <= 3}"}
        result = resolve_interpolations(config)
        self.assertEqual(result["result"], False)

    # === Greater-than-or-equal operator (evaluator line 283-284) ===

    def test_resolve__GreaterOrEqual__ReturnsTrue(self):
        config = {"result": "${5 >= 5}"}
        result = resolve_interpolations(config)
        self.assertEqual(result["result"], True)

    def test_resolve__GreaterOrEqualTrue__ReturnsTrue(self):
        config = {"result": "${5 >= 3}"}
        result = resolve_interpolations(config)
        self.assertEqual(result["result"], True)

    def test_resolve__GreaterOrEqualFalse__ReturnsFalse(self):
        config = {"result": "${3 >= 5}"}
        result = resolve_interpolations(config)
        self.assertEqual(result["result"], False)

    # === List subtraction with scalar (evaluator line 201) ===

    def test_resolve__ListSubtractScalar__RemovesMatchingElements(self):
        config = {"items": [1, 2, 3, 2, 1], "result": "${/items - 2}"}
        result = resolve_interpolations(config)
        self.assertEqual(result["result"], [1, 3, 1])

    def test_resolve__ListSubtractScalarString__RemovesMatchingStrings(self):
        config = {"items": ["a", "b", "a", "c"], "result": '${/items - "a"}'}
        result = resolve_interpolations(config)
        self.assertEqual(result["result"], ["b", "c"])

    # === Filter operators (evaluator lines 452, 457-461, 472, 487, 492) ===

    def test_resolve__FilterNotEquals__FiltersCorrectly(self):
        config = {"items": [1, 2, 3, 2], "result": "${/items | filter(x != 2)}"}
        result = resolve_interpolations(config)
        self.assertEqual(result["result"], [1, 3])

    def test_resolve__FilterLessOrEqual__FiltersCorrectly(self):
        config = {"items": [1, 2, 3, 4], "result": "${/items | filter(x <= 2)}"}
        result = resolve_interpolations(config)
        self.assertEqual(result["result"], [1, 2])

    def test_resolve__FilterGreaterOrEqual__FiltersCorrectly(self):
        config = {"items": [1, 2, 3, 4], "result": "${/items | filter(x >= 3)}"}
        result = resolve_interpolations(config)
        self.assertEqual(result["result"], [3, 4])

    # === Filter on non-list error (evaluator lines 421-423) ===

    def test_resolve__FilterOnScalar__RaisesError(self):
        config = {"value": 42, "result": "${/value | filter(x > 0)}"}
        with self.assertRaises(InterpolationResolutionError):
            resolve_interpolations(config)

    def test_resolve__FilterOnString__RaisesError(self):
        config = {"value": "hello", "result": "${/value | filter(x > 0)}"}
        with self.assertRaises(InterpolationResolutionError):
            resolve_interpolations(config)

    # === Env var defaults using coalesce operators ===

    def test_resolve__EnvVarWithDefaultWhenSet__UsesEnvValue(self):
        import os
        os.environ["RCONFIG_TEST_VAR"] = "actual_value"
        try:
            config = {"result": '${env:RCONFIG_TEST_VAR ?: "default_value"}'}
            result = resolve_interpolations(config)
            self.assertEqual(result["result"], "actual_value")
        finally:
            del os.environ["RCONFIG_TEST_VAR"]

    def test_resolve__EnvVarWithFalseDefault__UsesFalse(self):
        config = {"result": "${env:NONEXISTENT_VAR_12345 ?: false}"}
        result = resolve_interpolations(config)
        self.assertEqual(result["result"], False)

    def test_resolve__EnvVarWithNullDefault__UsesNull(self):
        config = {"result": "${env:NONEXISTENT_VAR_12345 ?: null}"}
        result = resolve_interpolations(config)
        self.assertIsNone(result["result"])

    def test_resolve__EnvVarWithStringDefault__UsesStringDefault(self):
        config = {"result": '${env:NONEXISTENT_VAR_12345 ?: "default_string"}'}
        result = resolve_interpolations(config)
        self.assertEqual(result["result"], "default_string")

    # === Type error handling (resolver lines 252-256) ===

    def test_resolve__TypeErrorInExpression__RaisesInterpolationError(self):
        config = {"result": '${\"hello\" - 5}'}
        with self.assertRaises(InterpolationResolutionError) as ctx:
            resolve_interpolations(config)
        self.assertIn("type error", str(ctx.exception).lower())

    def test_resolve__IndexOnNonIndexable__RaisesError(self):
        config = {"value": 42, "result": "${/value[0]}"}
        with self.assertRaises(InterpolationResolutionError):
            resolve_interpolations(config)

    # === Provenance tracking (resolver lines 117-119, 206-213, 279-282) ===

    def test_resolve__WithProvenance__TracksInterpolationSource(self):
        from rconfig.provenance import ProvenanceBuilder
        config = {"a": 5, "b": "${/a}"}
        builder = ProvenanceBuilder()
        builder.add("a", "test.yaml", 1)
        builder.add("b", "test.yaml", 2)
        result = resolve_interpolations(config, builder)
        entry = builder.get("b")
        self.assertIsNotNone(entry.interpolation)
        self.assertEqual(entry.interpolation.path, "a")

    def test_resolve__EmbeddedWithProvenance__TracksCompoundSource(self):
        from rconfig.provenance import ProvenanceBuilder
        config = {"a": 1, "b": 2, "result": "${/a} + ${/b}"}
        builder = ProvenanceBuilder()
        builder.add("a", "test.yaml", 1)
        builder.add("b", "test.yaml", 2)
        builder.add("result", "test.yaml", 3)
        result = resolve_interpolations(config, builder)
        entry = builder.get("result")
        self.assertIsNotNone(entry.interpolation)
        self.assertEqual(entry.interpolation.operator, "concat")

    # === Relative path resolution (evaluator lines 556-569) ===

    def test_resolve__SimplePath__ResolvesCorrectly(self):
        config = {"model": {"lr": 0.01}, "result": "${model.lr}"}
        result = resolve_interpolations(config)
        self.assertEqual(result["result"], 0.01)

    def test_resolve__RelativePathWithDot__ResolvesFromRoot(self):
        # ./value resolves as "value" from document root (not nested context)
        # This tests that ./ is stripped and path is resolved from root
        config = {"value": 42, "nested": {"ref": "${./value}"}}
        result = resolve_interpolations(config)
        self.assertEqual(result["nested"]["ref"], 42)

    def test_resolve__RelativePathNotFound__RaisesError(self):
        # When ./path references something not at root
        config = {"data": {"value": 42, "ref": "${./value}"}}
        with self.assertRaises(InterpolationResolutionError):
            resolve_interpolations(config)


class ResolverProvenanceTrackingTests(unittest.TestCase):
    """Tests for provenance value tracking during interpolation resolution."""

    def test_resolve__StandaloneInterpolation__UpdatesProvenanceValue(self):
        """Test that standalone interpolation updates provenance entry value."""
        # Arrange
        from rconfig.provenance import ProvenanceBuilder

        config = {"a": 42, "b": "${/a}"}
        builder = ProvenanceBuilder()
        builder.add("a", "test.yaml", 1)
        builder.add("b", "test.yaml", 2)

        # Act
        resolve_interpolations(config, builder)

        # Assert
        entry = builder.get("b")
        self.assertEqual(42, entry.value)

    def test_resolve__EmbeddedInterpolation__UpdatesProvenanceWithCompound(self):
        """Test that embedded interpolation updates provenance with compound source."""
        # Arrange
        from rconfig.provenance import ProvenanceBuilder

        config = {"a": "foo", "b": "bar", "result": "${/a}_${/b}"}
        builder = ProvenanceBuilder()
        builder.add("a", "test.yaml", 1)
        builder.add("b", "test.yaml", 2)
        builder.add("result", "test.yaml", 3)

        # Act
        resolve_interpolations(config, builder)

        # Assert
        entry = builder.get("result")
        self.assertEqual("foo_bar", entry.value)
        self.assertIsNotNone(entry.interpolation)
        self.assertEqual(2, len(entry.interpolation.sources))

    def test_resolve__NoProvenanceEntry__NoUpdate(self):
        """Test that missing provenance entry doesn't cause error."""
        # Arrange
        from rconfig.provenance import ProvenanceBuilder

        config = {"a": 42, "b": "${/a}"}
        builder = ProvenanceBuilder()
        # Note: Not adding entries for a or b

        # Act - should not raise
        result = resolve_interpolations(config, builder)

        # Assert
        self.assertEqual(42, result["b"])

    def test_resolve__ProvenanceNone__SkipsUpdate(self):
        """Test that None provenance works without error."""
        # Arrange
        config = {"a": 42, "b": "${/a}"}

        # Act - should not raise
        result = resolve_interpolations(config, None)

        # Assert
        self.assertEqual(42, result["b"])

    def test_resolve__WithProvenance__SetsInterpolationSource(self):
        """Test that provenance entry gets interpolation source info."""
        # Arrange
        from rconfig.provenance import ProvenanceBuilder

        config = {"defaults": {"lr": 0.01}, "model": {"lr": "${/defaults.lr}"}}
        builder = ProvenanceBuilder()
        builder.add("defaults.lr", "defaults.yaml", 1)
        builder.add("model.lr", "model.yaml", 5)

        # Act
        resolve_interpolations(config, builder)

        # Assert
        entry = builder.get("model.lr")
        self.assertIsNotNone(entry.interpolation)
        self.assertEqual("config", entry.interpolation.kind)
        self.assertEqual("defaults.lr", entry.interpolation.path)

    def test_resolve__WithProvenance__SetsResolvedValue(self):
        """Test that provenance entry gets the resolved value."""
        # Arrange
        from rconfig.provenance import ProvenanceBuilder

        config = {"a": 10, "b": 5, "result": "${/a + /b}"}
        builder = ProvenanceBuilder()
        builder.add("a", "test.yaml", 1)
        builder.add("b", "test.yaml", 2)
        builder.add("result", "test.yaml", 3)

        # Act
        resolve_interpolations(config, builder)

        # Assert
        entry = builder.get("result")
        self.assertEqual(15, entry.value)

    def test_resolve__WithExpression__TracksOperator(self):
        """Test that expression operator is tracked in provenance."""
        # Arrange
        from rconfig.provenance import ProvenanceBuilder

        config = {"a": 10, "result": "${/a * 2}"}
        builder = ProvenanceBuilder()
        builder.add("a", "test.yaml", 1)
        builder.add("result", "test.yaml", 2)

        # Act
        resolve_interpolations(config, builder)

        # Assert
        entry = builder.get("result")
        self.assertEqual("*", entry.interpolation.operator)
        self.assertEqual(20, entry.value)

    def test_resolve__ChainedReferences__TracksAllSources(self):
        """Test that chained references track all sources."""
        # Arrange
        from rconfig.provenance import ProvenanceBuilder

        config = {"a": 1, "b": "${/a + 1}", "c": "${/b + 1}"}
        builder = ProvenanceBuilder()
        builder.add("a", "test.yaml", 1)
        builder.add("b", "test.yaml", 2)
        builder.add("c", "test.yaml", 3)

        # Act
        resolve_interpolations(config, builder)

        # Assert
        b_entry = builder.get("b")
        c_entry = builder.get("c")
        self.assertEqual(2, b_entry.value)
        self.assertEqual(3, c_entry.value)

    def test_resolve__EnvVarInterpolation__TracksEnvSource(self):
        """Test that env var interpolation tracks env source."""
        # Arrange
        import os
        from rconfig.provenance import ProvenanceBuilder

        os.environ["RCONFIG_TEST_VAL"] = "test_value"
        try:
            config = {"result": "${env:RCONFIG_TEST_VAL}"}
            builder = ProvenanceBuilder()
            builder.add("result", "test.yaml", 1)

            # Act
            resolve_interpolations(config, builder)

            # Assert
            entry = builder.get("result")
            self.assertIsNotNone(entry.interpolation)
            self.assertEqual("env", entry.interpolation.kind)
            self.assertEqual("RCONFIG_TEST_VAL", entry.interpolation.env_var)
        finally:
            del os.environ["RCONFIG_TEST_VAL"]


if __name__ == "__main__":
    unittest.main()
