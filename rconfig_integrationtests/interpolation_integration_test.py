"""Integration tests for interpolation feature.

These tests verify the complete interpolation system works end-to-end
using real YAML config files through the public API (rc.validate(), rc.instantiate()).
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from unittest.case import TestCase

import rconfig as rc
from rconfig.errors import (
    CircularInterpolationError,
    EnvironmentVariableError,
    InterpolationResolutionError,
)


# Path to interpolation config files directory
CONFIG_DIR = Path(__file__).parent / "config_files" / "interpolation"


# =============================================================================
# Test Dataclasses
# =============================================================================


@dataclass
class ConfigPathsTest:
    """Dataclass for config path reference tests."""

    source: dict
    items: list[int]
    results: dict


@dataclass
class ArithmeticTest:
    """Dataclass for arithmetic operation tests."""

    values: dict
    results: dict


@dataclass
class ComparisonTest:
    """Dataclass for comparison operation tests."""

    values: dict
    results: dict


@dataclass
class BooleanTest:
    """Dataclass for boolean operation tests."""

    flags: dict
    items: list[str]
    results: dict


@dataclass
class ListsTest:
    """Dataclass for list operation tests."""

    numbers: list[int]
    strings: list[str]
    to_remove: list[int]
    results: dict


@dataclass
class FilterTest:
    """Dataclass for filter operation tests."""

    numbers: list[int]
    threshold: int
    filtered: dict


@dataclass
class StringTest:
    """Dataclass for string operation tests."""

    name: str
    version: int
    prefix: str
    suffix: str
    results: dict


@dataclass
class EnvVarsTest:
    """Dataclass for environment variable tests."""

    paths: dict
    settings: dict
    raw_defaults: dict
    embedded: dict


@dataclass
class LiteralsTest:
    """Dataclass for literal value tests."""

    literals: dict
    computed: dict


@dataclass
class ChainedExpressionsTest:
    """Dataclass for chained expression tests."""

    values: dict
    precedence: dict
    logic: dict
    items: list[int]
    chained_list: dict
    list_arithmetic: dict


@dataclass
class NestedInterpolationTest:
    """Dataclass for nested interpolation tests."""

    level1: dict
    cross_references: dict
    model_names: list[str]
    model_sizes: list[int]
    models: list
    list_references: dict
    configs: list
    nested_access: dict


@dataclass
class AllOperationsTest:
    """Dataclass for comprehensive all-operations tests."""

    defaults: dict
    items: list[int]
    callbacks: list[str]
    name: str
    arithmetic: dict
    comparisons: dict
    booleans: dict
    lists: dict
    list_math: dict
    filtered: dict
    strings: dict
    env_values: dict
    combined: dict


@dataclass
class CircularRefTest:
    """Dataclass for circular reference error tests."""

    a: object
    b: object
    c: object


@dataclass
class SelfRefTest:
    """Dataclass for self-reference error tests."""

    value: object


@dataclass
class MissingPathTest:
    """Dataclass for missing path error tests."""

    value: object


@dataclass
class DivisionByZeroTest:
    """Dataclass for division by zero error tests."""

    numerator: int
    denominator: int
    result: object


@dataclass
class TypeErrorTest:
    """Dataclass for type error tests."""

    text: str
    number: int
    result: object


@dataclass
class IndexOutOfBoundsTest:
    """Dataclass for index out of bounds error tests."""

    items: list[int]
    result: object


@dataclass
class FilterOnNonListTest:
    """Dataclass for filter on non-list error tests."""

    value: int
    result: object


@dataclass
class FloorDivisionByZeroTest:
    """Dataclass for floor division by zero error tests."""

    numerator: int
    denominator: int
    result: object


@dataclass
class ModuloByZeroTest:
    """Dataclass for modulo by zero error tests."""

    numerator: int
    denominator: int
    result: object


@dataclass
class ListMultiplicationTest:
    """Dataclass for list multiplication error tests."""

    list_a: list[int]
    list_b: list[int]
    result: object


@dataclass
class StringSubtractionTest:
    """Dataclass for string subtraction error tests."""

    text_a: str
    text_b: str
    result: object


@dataclass
class UnaryMinusOnStringTest:
    """Dataclass for unary minus on string error tests."""

    text: str
    result: object


@dataclass
class UnaryPlusOnStringTest:
    """Dataclass for unary plus on string error tests."""

    text: str
    result: object


@dataclass
class PowerStringBaseTest:
    """Dataclass for power with string base error tests."""

    base: str
    exponent: int
    result: object


@dataclass
class PowerStringExponentTest:
    """Dataclass for power with string exponent error tests."""

    base: int
    exponent: str
    result: object


@dataclass
class InOperatorNonContainerTest:
    """Dataclass for in operator with non-container error tests."""

    value: int
    result: object


@dataclass
class NegativeIndexOutOfBoundsTest:
    """Dataclass for negative index out of bounds error tests."""

    items: list[int]
    result: object


@dataclass
class IndexOnNumberTest:
    """Dataclass for index on number error tests."""

    value: int
    result: object


@dataclass
class IndexOnBooleanTest:
    """Dataclass for index on boolean error tests."""

    value: bool
    result: object


@dataclass
class SliceOnNumberTest:
    """Dataclass for slice on number error tests."""

    value: int
    result: object


@dataclass
class LenOnNumberTest:
    """Dataclass for length on number error tests."""

    value: int
    result: object


@dataclass
class FilterOnDictTest:
    """Dataclass for filter on dict error tests."""

    data: dict
    result: object


@dataclass
class FilterOnStringTest:
    """Dataclass for filter on string error tests."""

    text: str
    result: object


@dataclass
class FilterTypeMismatchTest:
    """Dataclass for filter type mismatch error tests."""

    items: list
    result: object


@dataclass
class MissingEnvVarTest:
    """Dataclass for missing environment variable error tests."""

    value: object


@dataclass
class ThreeWayCycleTest:
    """Dataclass for three-way circular reference error tests."""

    a: object
    b: object
    c: object


@dataclass
class CycleWithNestedTest:
    """Dataclass for circular reference with nested path error tests."""

    a: object
    b: dict


@dataclass
class RemoveOnNumberTest:
    """Dataclass for remove on number error tests."""

    value: int
    result: object


@dataclass
class RemoveIndexOutOfBoundsTest:
    """Dataclass for remove index out of bounds error tests."""

    items: list[int]
    result: object


@dataclass
class BaseConfigTest:
    """Dataclass for base composition config."""

    defaults: dict
    model: dict


@dataclass
class RefInterpolationTest:
    """Dataclass for _ref_ with interpolation tests."""

    defaults: dict
    model: dict
    training: dict
    model_info: dict


@dataclass
class CacheConfig:
    """Dataclass for cache config in instance tests."""

    size: int
    ttl: int


@dataclass
class ServiceConfig:
    """Dataclass for service config in instance tests."""

    name: str
    cache: CacheConfig
    cache_size_check: int


@dataclass
class InstanceInterpolationTest:
    """Dataclass for _instance_ with interpolation tests."""

    shared_cache: CacheConfig
    cache_info: dict
    service_a: ServiceConfig
    service_b: ServiceConfig


# =============================================================================
# Config Path Reference Tests
# =============================================================================


class ConfigPathInterpolationTests(TestCase):
    """Tests for config path references: /path, ./path, path."""

    def setUp(self) -> None:
        rc._store._known_targets.clear()
        rc.register("config_paths_test", ConfigPathsTest)

    def test_instantiate__AbsolutePath__ResolvesCorrectly(self) -> None:
        config_path = CONFIG_DIR / "basic" / "config_paths.yaml"

        result = rc.instantiate(config_path, ConfigPathsTest, cli_overrides=False)

        self.assertEqual(result.results["absolute_path"], 42)

    def test_instantiate__NestedPath__ResolvesCorrectly(self) -> None:
        config_path = CONFIG_DIR / "basic" / "config_paths.yaml"

        result = rc.instantiate(config_path, ConfigPathsTest, cli_overrides=False)

        self.assertEqual(result.results["nested_path"], 100)

    def test_instantiate__ListIndexPath__ResolvesCorrectly(self) -> None:
        config_path = CONFIG_DIR / "basic" / "config_paths.yaml"

        result = rc.instantiate(config_path, ConfigPathsTest, cli_overrides=False)

        self.assertEqual(result.results["list_index"], 10)

    def test_instantiate__ListNegativeIndexPath__ResolvesCorrectly(self) -> None:
        config_path = CONFIG_DIR / "basic" / "config_paths.yaml"

        result = rc.instantiate(config_path, ConfigPathsTest, cli_overrides=False)

        self.assertEqual(result.results["list_negative_index"], 50)

    def test_instantiate__ImplicitPath__ResolvesCorrectly(self) -> None:
        config_path = CONFIG_DIR / "basic" / "config_paths.yaml"

        result = rc.instantiate(config_path, ConfigPathsTest, cli_overrides=False)

        self.assertEqual(result.results["implicit_path"], 42)


# =============================================================================
# Arithmetic Operator Tests
# =============================================================================


class ArithmeticOperatorTests(TestCase):
    """Tests for arithmetic: +, -, *, /, //, %, **, unary -/+."""

    def setUp(self) -> None:
        rc._store._known_targets.clear()
        rc.register("arithmetic_test", ArithmeticTest)

    def test_instantiate__Addition__ResolvesCorrectly(self) -> None:
        config_path = CONFIG_DIR / "basic" / "arithmetic.yaml"

        result = rc.instantiate(config_path, ArithmeticTest, cli_overrides=False)

        self.assertEqual(result.results["addition"], 13)  # 10 + 3

    def test_instantiate__Subtraction__ResolvesCorrectly(self) -> None:
        config_path = CONFIG_DIR / "basic" / "arithmetic.yaml"

        result = rc.instantiate(config_path, ArithmeticTest, cli_overrides=False)

        self.assertEqual(result.results["subtraction"], 7)  # 10 - 3

    def test_instantiate__Multiplication__ResolvesCorrectly(self) -> None:
        config_path = CONFIG_DIR / "basic" / "arithmetic.yaml"

        result = rc.instantiate(config_path, ArithmeticTest, cli_overrides=False)

        self.assertEqual(result.results["multiplication"], 30)  # 10 * 3

    def test_instantiate__Division__ResolvesCorrectly(self) -> None:
        config_path = CONFIG_DIR / "basic" / "arithmetic.yaml"

        result = rc.instantiate(config_path, ArithmeticTest, cli_overrides=False)

        self.assertAlmostEqual(result.results["division"], 10 / 3, places=5)

    def test_instantiate__FloorDivision__ResolvesCorrectly(self) -> None:
        config_path = CONFIG_DIR / "basic" / "arithmetic.yaml"

        result = rc.instantiate(config_path, ArithmeticTest, cli_overrides=False)

        self.assertEqual(result.results["floor_division"], 3)  # 10 // 3

    def test_instantiate__Modulo__ResolvesCorrectly(self) -> None:
        config_path = CONFIG_DIR / "basic" / "arithmetic.yaml"

        result = rc.instantiate(config_path, ArithmeticTest, cli_overrides=False)

        self.assertEqual(result.results["modulo"], 1)  # 10 % 3

    def test_instantiate__Power__ResolvesCorrectly(self) -> None:
        config_path = CONFIG_DIR / "basic" / "arithmetic.yaml"

        result = rc.instantiate(config_path, ArithmeticTest, cli_overrides=False)

        self.assertEqual(result.results["power"], 9)  # 3 ** 2

    def test_instantiate__UnaryNegative__ResolvesCorrectly(self) -> None:
        config_path = CONFIG_DIR / "basic" / "arithmetic.yaml"

        result = rc.instantiate(config_path, ArithmeticTest, cli_overrides=False)

        self.assertEqual(result.results["unary_negative"], -10)

    def test_instantiate__UnaryPositive__ResolvesCorrectly(self) -> None:
        config_path = CONFIG_DIR / "basic" / "arithmetic.yaml"

        result = rc.instantiate(config_path, ArithmeticTest, cli_overrides=False)

        self.assertEqual(result.results["unary_positive"], 10)

    def test_instantiate__ComplexExpression__ResolvesCorrectly(self) -> None:
        config_path = CONFIG_DIR / "basic" / "arithmetic.yaml"

        result = rc.instantiate(config_path, ArithmeticTest, cli_overrides=False)

        # (10 + 3) * 2.5 = 32.5
        self.assertEqual(result.results["complex_expr"], 32.5)

    def test_instantiate__ChainedExpression__FollowsPrecedence(self) -> None:
        config_path = CONFIG_DIR / "basic" / "arithmetic.yaml"

        result = rc.instantiate(config_path, ArithmeticTest, cli_overrides=False)

        # 10 + 3 * 2.5 = 10 + 7.5 = 17.5
        self.assertEqual(result.results["chained"], 17.5)


# =============================================================================
# Comparison Operator Tests
# =============================================================================


class ComparisonOperatorTests(TestCase):
    """Tests for comparisons: ==, !=, <, >, <=, >=."""

    def setUp(self) -> None:
        rc._store._known_targets.clear()
        rc.register("comparison_test", ComparisonTest)

    def test_instantiate__Equal__ResolvesCorrectly(self) -> None:
        config_path = CONFIG_DIR / "basic" / "comparison.yaml"

        result = rc.instantiate(config_path, ComparisonTest, cli_overrides=False)

        self.assertTrue(result.results["equal_true"])
        self.assertFalse(result.results["equal_false"])

    def test_instantiate__NotEqual__ResolvesCorrectly(self) -> None:
        config_path = CONFIG_DIR / "basic" / "comparison.yaml"

        result = rc.instantiate(config_path, ComparisonTest, cli_overrides=False)

        self.assertTrue(result.results["not_equal_true"])
        self.assertFalse(result.results["not_equal_false"])

    def test_instantiate__LessThan__ResolvesCorrectly(self) -> None:
        config_path = CONFIG_DIR / "basic" / "comparison.yaml"

        result = rc.instantiate(config_path, ComparisonTest, cli_overrides=False)

        self.assertTrue(result.results["less_than_true"])
        self.assertFalse(result.results["less_than_false"])

    def test_instantiate__GreaterThan__ResolvesCorrectly(self) -> None:
        config_path = CONFIG_DIR / "basic" / "comparison.yaml"

        result = rc.instantiate(config_path, ComparisonTest, cli_overrides=False)

        self.assertTrue(result.results["greater_than_true"])
        self.assertFalse(result.results["greater_than_false"])

    def test_instantiate__LessOrEqual__ResolvesCorrectly(self) -> None:
        config_path = CONFIG_DIR / "basic" / "comparison.yaml"

        result = rc.instantiate(config_path, ComparisonTest, cli_overrides=False)

        self.assertTrue(result.results["less_or_equal_true"])
        self.assertTrue(result.results["less_or_equal_equal"])
        self.assertFalse(result.results["less_or_equal_false"])

    def test_instantiate__GreaterOrEqual__ResolvesCorrectly(self) -> None:
        config_path = CONFIG_DIR / "basic" / "comparison.yaml"

        result = rc.instantiate(config_path, ComparisonTest, cli_overrides=False)

        self.assertTrue(result.results["greater_or_equal_true"])
        self.assertTrue(result.results["greater_or_equal_equal"])
        self.assertFalse(result.results["greater_or_equal_false"])


# =============================================================================
# Boolean Operator Tests
# =============================================================================


class BooleanOperatorTests(TestCase):
    """Tests for booleans: and, or, not, in, not in."""

    def setUp(self) -> None:
        rc._store._known_targets.clear()
        rc.register("boolean_test", BooleanTest)

    def test_instantiate__And__ResolvesCorrectly(self) -> None:
        config_path = CONFIG_DIR / "basic" / "boolean.yaml"

        result = rc.instantiate(config_path, BooleanTest, cli_overrides=False)

        self.assertFalse(result.results["and_tf"])
        self.assertTrue(result.results["and_tt"])
        self.assertFalse(result.results["and_ff"])

    def test_instantiate__Or__ResolvesCorrectly(self) -> None:
        config_path = CONFIG_DIR / "basic" / "boolean.yaml"

        result = rc.instantiate(config_path, BooleanTest, cli_overrides=False)

        self.assertTrue(result.results["or_tf"])
        self.assertTrue(result.results["or_tt"])
        self.assertFalse(result.results["or_ff"])

    def test_instantiate__Not__ResolvesCorrectly(self) -> None:
        config_path = CONFIG_DIR / "basic" / "boolean.yaml"

        result = rc.instantiate(config_path, BooleanTest, cli_overrides=False)

        self.assertFalse(result.results["not_true"])
        self.assertTrue(result.results["not_false"])

    def test_instantiate__In__ResolvesCorrectly(self) -> None:
        config_path = CONFIG_DIR / "basic" / "boolean.yaml"

        result = rc.instantiate(config_path, BooleanTest, cli_overrides=False)

        self.assertTrue(result.results["in_true"])
        self.assertFalse(result.results["in_false"])

    def test_instantiate__NotIn__ResolvesCorrectly(self) -> None:
        config_path = CONFIG_DIR / "basic" / "boolean.yaml"

        result = rc.instantiate(config_path, BooleanTest, cli_overrides=False)

        self.assertTrue(result.results["not_in_true"])
        self.assertFalse(result.results["not_in_false"])


# =============================================================================
# List Operation Tests
# =============================================================================


class ListOperationTests(TestCase):
    """Tests for list ops: +, -, [], [:], .remove(), len()."""

    def setUp(self) -> None:
        rc._store._known_targets.clear()
        rc.register("lists_test", ListsTest)

    def test_instantiate__ListIndex__ResolvesCorrectly(self) -> None:
        config_path = CONFIG_DIR / "basic" / "lists.yaml"

        result = rc.instantiate(config_path, ListsTest, cli_overrides=False)

        self.assertEqual(result.results["first_item"], 1)
        self.assertEqual(result.results["last_item"], 5)
        self.assertEqual(result.results["third_item"], 3)

    def test_instantiate__ListSlice__ResolvesCorrectly(self) -> None:
        config_path = CONFIG_DIR / "basic" / "lists.yaml"

        result = rc.instantiate(config_path, ListsTest, cli_overrides=False)

        self.assertEqual(result.results["slice_middle"], [2, 3, 4])
        self.assertEqual(result.results["slice_from_start"], [1, 2, 3])
        self.assertEqual(result.results["slice_to_end"], [4, 5])

    def test_instantiate__ListLength__ResolvesCorrectly(self) -> None:
        config_path = CONFIG_DIR / "basic" / "lists.yaml"

        result = rc.instantiate(config_path, ListsTest, cli_overrides=False)

        self.assertEqual(result.results["length"], 5)
        self.assertEqual(result.results["string_length"], 3)

    def test_instantiate__ListConcat__ResolvesCorrectly(self) -> None:
        config_path = CONFIG_DIR / "basic" / "lists.yaml"

        result = rc.instantiate(config_path, ListsTest, cli_overrides=False)

        self.assertEqual(result.results["concat"], [1, 2, 3, 4, 5, 6, 7, 8])

    def test_instantiate__ListSubtract__ResolvesCorrectly(self) -> None:
        config_path = CONFIG_DIR / "basic" / "lists.yaml"

        result = rc.instantiate(config_path, ListsTest, cli_overrides=False)

        self.assertEqual(result.results["subtract"], [1, 4, 5])  # [1,2,3,4,5] - [2,3]

    def test_instantiate__ListRemove__ResolvesCorrectly(self) -> None:
        config_path = CONFIG_DIR / "basic" / "lists.yaml"

        result = rc.instantiate(config_path, ListsTest, cli_overrides=False)

        self.assertEqual(result.results["remove_first"], [2, 3, 4, 5])
        self.assertEqual(result.results["remove_last"], [1, 2, 3, 4])


# =============================================================================
# Filter Operation Tests
# =============================================================================


class FilterOperationTests(TestCase):
    """Tests for filter: | filter(x op value) with all operators."""

    def setUp(self) -> None:
        rc._store._known_targets.clear()
        rc.register("filter_test", FilterTest)

    def test_instantiate__FilterGreaterThan__FiltersCorrectly(self) -> None:
        config_path = CONFIG_DIR / "basic" / "filter.yaml"

        result = rc.instantiate(config_path, FilterTest, cli_overrides=False)

        self.assertEqual(result.filtered["greater_than"], [6, 7, 8, 9, 10])

    def test_instantiate__FilterLessThan__FiltersCorrectly(self) -> None:
        config_path = CONFIG_DIR / "basic" / "filter.yaml"

        result = rc.instantiate(config_path, FilterTest, cli_overrides=False)

        self.assertEqual(result.filtered["less_than"], [1, 2, 3, 4])

    def test_instantiate__FilterEquals__FiltersCorrectly(self) -> None:
        config_path = CONFIG_DIR / "basic" / "filter.yaml"

        result = rc.instantiate(config_path, FilterTest, cli_overrides=False)

        self.assertEqual(result.filtered["equals"], [5])

    def test_instantiate__FilterNotEquals__FiltersCorrectly(self) -> None:
        config_path = CONFIG_DIR / "basic" / "filter.yaml"

        result = rc.instantiate(config_path, FilterTest, cli_overrides=False)

        self.assertEqual(result.filtered["not_equals"], [1, 2, 3, 4, 6, 7, 8, 9, 10])

    def test_instantiate__FilterGreaterOrEqual__FiltersCorrectly(self) -> None:
        config_path = CONFIG_DIR / "basic" / "filter.yaml"

        result = rc.instantiate(config_path, FilterTest, cli_overrides=False)

        self.assertEqual(result.filtered["greater_or_equal"], [5, 6, 7, 8, 9, 10])

    def test_instantiate__FilterLessOrEqual__FiltersCorrectly(self) -> None:
        config_path = CONFIG_DIR / "basic" / "filter.yaml"

        result = rc.instantiate(config_path, FilterTest, cli_overrides=False)

        self.assertEqual(result.filtered["less_or_equal"], [1, 2, 3, 4, 5])

    def test_instantiate__FilterWithConfigRef__FiltersCorrectly(self) -> None:
        config_path = CONFIG_DIR / "basic" / "filter.yaml"

        result = rc.instantiate(config_path, FilterTest, cli_overrides=False)

        # Filter x > /threshold where threshold = 5
        self.assertEqual(result.filtered["with_config_ref"], [6, 7, 8, 9, 10])


# =============================================================================
# String Operation Tests
# =============================================================================


class StringOperationTests(TestCase):
    """Tests for string concatenation and embedded interpolation."""

    def setUp(self) -> None:
        rc._store._known_targets.clear()
        rc.register("string_test", StringTest)

    def test_instantiate__SimpleConcat__ResolvesCorrectly(self) -> None:
        config_path = CONFIG_DIR / "basic" / "strings.yaml"

        result = rc.instantiate(config_path, StringTest, cli_overrides=False)

        self.assertEqual(result.results["concat_simple"], "hello world")

    def test_instantiate__MultipleConcat__ResolvesCorrectly(self) -> None:
        config_path = CONFIG_DIR / "basic" / "strings.yaml"

        result = rc.instantiate(config_path, StringTest, cli_overrides=False)

        self.assertEqual(result.results["concat_multiple"], "hello_world_end")

    def test_instantiate__EmbeddedSingle__ResolvesCorrectly(self) -> None:
        config_path = CONFIG_DIR / "basic" / "strings.yaml"

        result = rc.instantiate(config_path, StringTest, cli_overrides=False)

        self.assertEqual(result.results["embedded_single"], "Hello world!")

    def test_instantiate__EmbeddedMultiple__ResolvesCorrectly(self) -> None:
        config_path = CONFIG_DIR / "basic" / "strings.yaml"

        result = rc.instantiate(config_path, StringTest, cli_overrides=False)

        self.assertEqual(result.results["embedded_multiple"], "v2: world")

    def test_instantiate__EmbeddedExpression__ResolvesCorrectly(self) -> None:
        config_path = CONFIG_DIR / "basic" / "strings.yaml"

        result = rc.instantiate(config_path, StringTest, cli_overrides=False)

        self.assertEqual(result.results["embedded_expression"], "world (v3)")

    def test_instantiate__ConcatWithNumber__ResolvesCorrectly(self) -> None:
        config_path = CONFIG_DIR / "basic" / "strings.yaml"

        result = rc.instantiate(config_path, StringTest, cli_overrides=False)

        self.assertEqual(result.results["concat_with_number"], "version_2")


# =============================================================================
# Environment Variable Tests
# =============================================================================


class EnvironmentVariableTests(TestCase):
    """Tests for env var interpolation: ${env:VAR}, ${env:VAR,default}."""

    def setUp(self) -> None:
        rc._store._known_targets.clear()
        rc.register("env_vars_test", EnvVarsTest)
        # Clean up any test env vars
        for key in list(os.environ.keys()):
            if key.startswith("TEST_"):
                del os.environ[key]

    def tearDown(self) -> None:
        # Clean up test env vars after each test
        for key in list(os.environ.keys()):
            if key.startswith("TEST_"):
                del os.environ[key]

    def test_instantiate__EnvVarWithDefault__UsesDefaultWhenNotSet(self) -> None:
        config_path = CONFIG_DIR / "basic" / "env_vars.yaml"

        result = rc.instantiate(config_path, EnvVarsTest, cli_overrides=False)

        self.assertEqual(result.paths["data_dir"], "/default/data")
        self.assertEqual(result.settings["port"], 8080)
        self.assertEqual(result.settings["log_level"], "INFO")

    def test_instantiate__EnvVarWithDefault__UsesEnvValueWhenSet(self) -> None:
        os.environ["TEST_DATA_DIR"] = "/custom/data"
        os.environ["TEST_PORT"] = "9000"
        config_path = CONFIG_DIR / "basic" / "env_vars.yaml"

        result = rc.instantiate(config_path, EnvVarsTest, cli_overrides=False)

        self.assertEqual(result.paths["data_dir"], "/custom/data")
        # Env vars are always strings when set from environment
        self.assertEqual(result.settings["port"], "9000")

    def test_instantiate__EnvVarBooleanDefault__UsesCorrectType(self) -> None:
        config_path = CONFIG_DIR / "basic" / "env_vars.yaml"

        result = rc.instantiate(config_path, EnvVarsTest, cli_overrides=False)

        self.assertFalse(result.settings["debug"])
        self.assertTrue(result.settings["enabled"])

    def test_instantiate__EnvVarNullDefault__ResolvesToNone(self) -> None:
        config_path = CONFIG_DIR / "basic" / "env_vars.yaml"

        result = rc.instantiate(config_path, EnvVarsTest, cli_overrides=False)

        self.assertIsNone(result.settings["null_default"])

    def test_instantiate__EnvVarFloatDefault__UsesCorrectType(self) -> None:
        config_path = CONFIG_DIR / "basic" / "env_vars.yaml"

        result = rc.instantiate(config_path, EnvVarsTest, cli_overrides=False)

        self.assertEqual(result.settings["timeout"], 30.5)

    def test_instantiate__EnvVarEmbedded__ResolvesInString(self) -> None:
        config_path = CONFIG_DIR / "basic" / "env_vars.yaml"

        result = rc.instantiate(config_path, EnvVarsTest, cli_overrides=False)

        self.assertEqual(result.embedded["full_path"], "/home/output/anonymous")
        self.assertEqual(result.embedded["message"], "Running as user on port 8080")

    def test_instantiate__EnvVarRawPathDefault__ResolvesCorrectly(self) -> None:
        config_path = CONFIG_DIR / "basic" / "env_vars.yaml"

        result = rc.instantiate(config_path, EnvVarsTest, cli_overrides=False)

        self.assertEqual(result.raw_defaults["config_path"], "/etc/app/config.yaml")
        self.assertEqual(result.raw_defaults["cache_path"], "~/.cache/app")


# =============================================================================
# Literal Tests
# =============================================================================


class LiteralTests(TestCase):
    """Tests for literal values in interpolation expressions."""

    def setUp(self) -> None:
        rc._store._known_targets.clear()
        rc.register("literals_test", LiteralsTest)

    def test_instantiate__IntegerLiteral__PreservesType(self) -> None:
        config_path = CONFIG_DIR / "basic" / "literals.yaml"

        result = rc.instantiate(config_path, LiteralsTest, cli_overrides=False)

        self.assertEqual(result.literals["integer"], 42)
        self.assertIsInstance(result.literals["integer"], int)

    def test_instantiate__FloatLiteral__PreservesType(self) -> None:
        config_path = CONFIG_DIR / "basic" / "literals.yaml"

        result = rc.instantiate(config_path, LiteralsTest, cli_overrides=False)

        self.assertAlmostEqual(result.literals["float"], 3.14159, places=5)

    def test_instantiate__NegativeNumbers__PreservesSign(self) -> None:
        config_path = CONFIG_DIR / "basic" / "literals.yaml"

        result = rc.instantiate(config_path, LiteralsTest, cli_overrides=False)

        self.assertEqual(result.literals["negative_int"], -10)
        self.assertEqual(result.literals["negative_float"], -2.5)

    def test_instantiate__ScientificNotation__ParsesCorrectly(self) -> None:
        config_path = CONFIG_DIR / "basic" / "literals.yaml"

        result = rc.instantiate(config_path, LiteralsTest, cli_overrides=False)

        self.assertEqual(result.literals["scientific_large"], 1e10)
        self.assertEqual(result.literals["scientific_small"], 1e-5)

    def test_instantiate__StringLiteral__PreservesType(self) -> None:
        config_path = CONFIG_DIR / "basic" / "literals.yaml"

        result = rc.instantiate(config_path, LiteralsTest, cli_overrides=False)

        self.assertEqual(result.literals["string"], "hello world")

    def test_instantiate__BooleanLiterals__PreservesType(self) -> None:
        config_path = CONFIG_DIR / "basic" / "literals.yaml"

        result = rc.instantiate(config_path, LiteralsTest, cli_overrides=False)

        self.assertTrue(result.literals["bool_true"])
        self.assertFalse(result.literals["bool_false"])

    def test_instantiate__NullLiteral__PreservesType(self) -> None:
        config_path = CONFIG_DIR / "basic" / "literals.yaml"

        result = rc.instantiate(config_path, LiteralsTest, cli_overrides=False)

        self.assertIsNone(result.literals["null_value"])

    def test_instantiate__ListLiterals__PreservesType(self) -> None:
        config_path = CONFIG_DIR / "basic" / "literals.yaml"

        result = rc.instantiate(config_path, LiteralsTest, cli_overrides=False)

        self.assertEqual(result.literals["empty_list"], [])
        self.assertEqual(result.literals["number_list"], [1, 2, 3])

    def test_instantiate__LiteralExpressions__ComputesCorrectly(self) -> None:
        config_path = CONFIG_DIR / "basic" / "literals.yaml"

        result = rc.instantiate(config_path, LiteralsTest, cli_overrides=False)

        self.assertEqual(result.computed["literal_addition"], 15)
        self.assertEqual(result.computed["literal_multiplication"], 12)
        self.assertTrue(result.computed["literal_comparison"])
        self.assertFalse(result.computed["literal_boolean"])
        self.assertEqual(result.computed["literal_list_length"], 5)
        self.assertEqual(result.computed["literal_string_concat"], "hello world")
        self.assertTrue(result.computed["literal_in_check"])


# =============================================================================
# Complex Expression Tests
# =============================================================================


class ComplexExpressionTests(TestCase):
    """Tests for chained ops, precedence, parentheses."""

    def setUp(self) -> None:
        rc._store._known_targets.clear()
        rc.register("chained_expressions_test", ChainedExpressionsTest)

    def test_instantiate__OperatorPrecedence__FollowsMathRules(self) -> None:
        config_path = CONFIG_DIR / "complex" / "chained_expressions.yaml"

        result = rc.instantiate(config_path, ChainedExpressionsTest, cli_overrides=False)

        # 10 + (5 * 2) = 20
        self.assertEqual(result.precedence["mul_before_add"], 20)

    def test_instantiate__ParenthesesOverride__WorksCorrectly(self) -> None:
        config_path = CONFIG_DIR / "complex" / "chained_expressions.yaml"

        result = rc.instantiate(config_path, ChainedExpressionsTest, cli_overrides=False)

        # (10 + 5) * 2 = 30
        self.assertEqual(result.precedence["parentheses_override"], 30)

    def test_instantiate__PowerBeforeMul__FollowsPrecedence(self) -> None:
        config_path = CONFIG_DIR / "complex" / "chained_expressions.yaml"

        result = rc.instantiate(config_path, ChainedExpressionsTest, cli_overrides=False)

        # (2 ** 3) * 5 = 40
        self.assertEqual(result.precedence["power_before_mul"], 40)

    def test_instantiate__NestedParentheses__WorksCorrectly(self) -> None:
        config_path = CONFIG_DIR / "complex" / "chained_expressions.yaml"

        result = rc.instantiate(config_path, ChainedExpressionsTest, cli_overrides=False)

        # ((10 + 5) * 2) / 3 = 10
        self.assertEqual(result.precedence["nested_parens"], 10)

    def test_instantiate__ChainedLogic__WorksCorrectly(self) -> None:
        config_path = CONFIG_DIR / "complex" / "chained_expressions.yaml"

        result = rc.instantiate(config_path, ChainedExpressionsTest, cli_overrides=False)

        self.assertTrue(result.logic["and_chain"])  # 10 > 5 and 5 < 10 and 2 == 2
        self.assertTrue(result.logic["or_chain"])  # 10 < 5 or 5 < 10 or 2 > 5
        self.assertTrue(result.logic["mixed_logic"])  # (10 > 5 and 5 > 2) or 2 == 0
        self.assertTrue(result.logic["not_in_chain"])  # not (10 < 5) and 5 < 10

    def test_instantiate__ChainedListOps__WorksCorrectly(self) -> None:
        config_path = CONFIG_DIR / "complex" / "chained_expressions.yaml"

        result = rc.instantiate(config_path, ChainedExpressionsTest, cli_overrides=False)

        # Filter then slice
        self.assertEqual(result.chained_list["filter_then_slice"], [4, 5, 6])
        self.assertEqual(result.chained_list["slice_result"], [3, 4, 5, 6, 7])
        self.assertEqual(result.chained_list["length_of_filtered"], 5)

    def test_instantiate__ListArithmetic__WorksCorrectly(self) -> None:
        config_path = CONFIG_DIR / "complex" / "chained_expressions.yaml"

        result = rc.instantiate(config_path, ChainedExpressionsTest, cli_overrides=False)

        self.assertEqual(result.list_arithmetic["sum_first_two"], 3)  # 1 + 2
        self.assertEqual(result.list_arithmetic["product_with_scalar"], 6)  # 3 * 2


# =============================================================================
# Nested Interpolation Tests
# =============================================================================


class NestedInterpolationTests(TestCase):
    """Tests for deeply nested configs with interpolation."""

    def setUp(self) -> None:
        rc._store._known_targets.clear()
        rc.register("nested_interpolation_test", NestedInterpolationTest)

    def test_instantiate__CrossLevelReferences__ResolveCorrectly(self) -> None:
        config_path = CONFIG_DIR / "complex" / "nested_interpolation.yaml"

        result = rc.instantiate(config_path, NestedInterpolationTest, cli_overrides=False)

        self.assertEqual(result.cross_references["ref_level1"], 100)
        self.assertEqual(result.cross_references["ref_level2"], 200)
        self.assertEqual(result.cross_references["ref_level3"], 300)
        self.assertEqual(result.cross_references["ref_level4"], 400)
        self.assertEqual(result.cross_references["sum_all"], 1000)

    def test_instantiate__ListObjectReferences__ResolveCorrectly(self) -> None:
        config_path = CONFIG_DIR / "complex" / "nested_interpolation.yaml"

        result = rc.instantiate(config_path, NestedInterpolationTest, cli_overrides=False)

        # Using direct list value references (grammar limitation: can't do list[0].field)
        self.assertEqual(result.list_references["first_model_name"], "model_a")
        self.assertEqual(result.list_references["second_model_size"], 200)
        self.assertEqual(result.list_references["last_model_name"], "model_c")
        self.assertEqual(result.list_references["total_size"], 600)

    def test_instantiate__NestedDictInList__ResolvesCorrectly(self) -> None:
        config_path = CONFIG_DIR / "complex" / "nested_interpolation.yaml"

        result = rc.instantiate(config_path, NestedInterpolationTest, cli_overrides=False)

        self.assertEqual(result.nested_access["training_lr"], 0.001)
        self.assertEqual(result.nested_access["validation_batch"], 32)


# =============================================================================
# Comprehensive All-Operations Tests
# =============================================================================


class AllOperationsTests(TestCase):
    """Tests for comprehensive config using all operations."""

    def setUp(self) -> None:
        rc._store._known_targets.clear()
        rc.register("all_operations_test", AllOperationsTest)
        # Clean up any test env vars
        for key in list(os.environ.keys()):
            if key.startswith("INTEGRATION_TEST_"):
                del os.environ[key]

    def tearDown(self) -> None:
        for key in list(os.environ.keys()):
            if key.startswith("INTEGRATION_TEST_"):
                del os.environ[key]

    def test_instantiate__AllArithmetic__ResolvesCorrectly(self) -> None:
        config_path = CONFIG_DIR / "complex" / "all_operations.yaml"

        result = rc.instantiate(config_path, AllOperationsTest, cli_overrides=False)

        self.assertEqual(result.arithmetic["doubled_lr"], 0.002)
        self.assertEqual(result.arithmetic["effective_batch"], 128)
        self.assertEqual(result.arithmetic["epochs_remaining"], 75)
        self.assertEqual(result.arithmetic["power_test"], 1024)
        self.assertEqual(result.arithmetic["floor_div"], 3)
        self.assertEqual(result.arithmetic["modulo"], 10)

    def test_instantiate__AllComparisons__ResolvesCorrectly(self) -> None:
        config_path = CONFIG_DIR / "complex" / "all_operations.yaml"

        result = rc.instantiate(config_path, AllOperationsTest, cli_overrides=False)

        self.assertTrue(result.comparisons["is_long_training"])
        self.assertFalse(result.comparisons["is_short_training"])
        self.assertTrue(result.comparisons["is_exact_epochs"])
        self.assertTrue(result.comparisons["is_not_epochs"])

    def test_instantiate__AllBooleans__ResolvesCorrectly(self) -> None:
        config_path = CONFIG_DIR / "complex" / "all_operations.yaml"

        result = rc.instantiate(config_path, AllOperationsTest, cli_overrides=False)

        self.assertTrue(result.booleans["is_valid_lr"])
        self.assertFalse(result.booleans["needs_adjustment"])
        self.assertTrue(result.booleans["is_not_long"])
        self.assertTrue(result.booleans["has_logger"])
        self.assertTrue(result.booleans["no_debug"])

    def test_instantiate__AllLists__ResolvesCorrectly(self) -> None:
        config_path = CONFIG_DIR / "complex" / "all_operations.yaml"

        result = rc.instantiate(config_path, AllOperationsTest, cli_overrides=False)

        self.assertEqual(result.lists["first_item"], 1)
        self.assertEqual(result.lists["last_item"], 10)
        self.assertEqual(result.lists["subset"], [3, 4, 5])
        self.assertEqual(result.lists["item_count"], 10)

    def test_instantiate__AllFilters__ResolvesCorrectly(self) -> None:
        config_path = CONFIG_DIR / "complex" / "all_operations.yaml"

        result = rc.instantiate(config_path, AllOperationsTest, cli_overrides=False)

        self.assertEqual(result.filtered["greater_than_5"], [6, 7, 8, 9, 10])
        self.assertEqual(result.filtered["less_than_5"], [1, 2, 3, 4])
        self.assertEqual(result.filtered["equals_5"], [5])

    def test_instantiate__AllStrings__ResolvesCorrectly(self) -> None:
        config_path = CONFIG_DIR / "complex" / "all_operations.yaml"

        result = rc.instantiate(config_path, AllOperationsTest, cli_overrides=False)

        self.assertEqual(result.strings["run_name"], "run_experiment_v1")
        self.assertEqual(result.strings["batch_info"], "Batch size: 32")

    def test_instantiate__CombinedExpressions__ResolvesCorrectly(self) -> None:
        config_path = CONFIG_DIR / "complex" / "all_operations.yaml"

        result = rc.instantiate(config_path, AllOperationsTest, cli_overrides=False)

        # 0.001 * 100 > 0.5 = 0.1 > 0.5 = False
        self.assertFalse(result.combined["scaled_and_checked"])
        # len([6,7,8,9,10]) > 3 = 5 > 3 = True
        self.assertTrue(result.combined["dynamic_threshold"])


# =============================================================================
# Error Tests
# =============================================================================


class InterpolationErrorTests(TestCase):
    """Tests for error cases: circular, missing, type errors."""

    def setUp(self) -> None:
        rc._store._known_targets.clear()
        # Existing error test registrations
        rc.register("circular_ref_test", CircularRefTest)
        rc.register("self_ref_test", SelfRefTest)
        rc.register("missing_path_test", MissingPathTest)
        rc.register("division_by_zero_test", DivisionByZeroTest)
        rc.register("type_error_test", TypeErrorTest)
        rc.register("index_out_of_bounds_test", IndexOutOfBoundsTest)
        rc.register("filter_on_non_list_test", FilterOnNonListTest)
        # New error test registrations
        rc.register("floor_division_by_zero_test", FloorDivisionByZeroTest)
        rc.register("modulo_by_zero_test", ModuloByZeroTest)
        rc.register("list_multiplication_test", ListMultiplicationTest)
        rc.register("string_subtraction_test", StringSubtractionTest)
        rc.register("unary_minus_on_string_test", UnaryMinusOnStringTest)
        rc.register("unary_plus_on_string_test", UnaryPlusOnStringTest)
        rc.register("power_string_base_test", PowerStringBaseTest)
        rc.register("power_string_exponent_test", PowerStringExponentTest)
        rc.register("in_operator_non_container_test", InOperatorNonContainerTest)
        rc.register("negative_index_out_of_bounds_test", NegativeIndexOutOfBoundsTest)
        rc.register("index_on_number_test", IndexOnNumberTest)
        rc.register("index_on_boolean_test", IndexOnBooleanTest)
        rc.register("slice_on_number_test", SliceOnNumberTest)
        rc.register("len_on_number_test", LenOnNumberTest)
        rc.register("filter_on_dict_test", FilterOnDictTest)
        rc.register("filter_on_string_test", FilterOnStringTest)
        rc.register("filter_type_mismatch_test", FilterTypeMismatchTest)
        rc.register("missing_env_var_test", MissingEnvVarTest)
        rc.register("three_way_cycle_test", ThreeWayCycleTest)
        rc.register("cycle_with_nested_test", CycleWithNestedTest)
        rc.register("remove_on_number_test", RemoveOnNumberTest)
        rc.register("remove_index_out_of_bounds_test", RemoveIndexOutOfBoundsTest)

    # =========================================================================
    # Original Error Tests
    # =========================================================================

    def test_instantiate__CircularReference__RaisesError(self) -> None:
        config_path = CONFIG_DIR / "errors" / "circular_ref.yaml"

        with self.assertRaises(CircularInterpolationError):
            rc.instantiate(config_path, cli_overrides=False)

    def test_instantiate__SelfReference__RaisesError(self) -> None:
        config_path = CONFIG_DIR / "errors" / "self_ref.yaml"

        with self.assertRaises(CircularInterpolationError):
            rc.instantiate(config_path, cli_overrides=False)

    def test_instantiate__MissingPath__RaisesError(self) -> None:
        config_path = CONFIG_DIR / "errors" / "missing_path.yaml"

        with self.assertRaises(InterpolationResolutionError):
            rc.instantiate(config_path, cli_overrides=False)

    def test_instantiate__DivisionByZero__RaisesError(self) -> None:
        config_path = CONFIG_DIR / "errors" / "division_by_zero.yaml"

        with self.assertRaises(InterpolationResolutionError):
            rc.instantiate(config_path, cli_overrides=False)

    def test_instantiate__TypeError__RaisesError(self) -> None:
        config_path = CONFIG_DIR / "errors" / "type_error.yaml"

        with self.assertRaises(InterpolationResolutionError):
            rc.instantiate(config_path, cli_overrides=False)

    def test_instantiate__IndexOutOfBounds__RaisesError(self) -> None:
        config_path = CONFIG_DIR / "errors" / "index_out_of_bounds.yaml"

        with self.assertRaises(InterpolationResolutionError):
            rc.instantiate(config_path, cli_overrides=False)

    def test_instantiate__FilterOnNonList__RaisesError(self) -> None:
        config_path = CONFIG_DIR / "errors" / "filter_on_non_list.yaml"

        with self.assertRaises(InterpolationResolutionError):
            rc.instantiate(config_path, cli_overrides=False)

    # =========================================================================
    # Division/Modulo By Zero Tests
    # =========================================================================

    def test_instantiate__FloorDivisionByZero__RaisesError(self) -> None:
        config_path = CONFIG_DIR / "errors" / "floor_division_by_zero.yaml"

        with self.assertRaises(InterpolationResolutionError):
            rc.instantiate(config_path, cli_overrides=False)

    def test_instantiate__ModuloByZero__RaisesError(self) -> None:
        config_path = CONFIG_DIR / "errors" / "modulo_by_zero.yaml"

        with self.assertRaises(InterpolationResolutionError):
            rc.instantiate(config_path, cli_overrides=False)

    # =========================================================================
    # Type Mismatch Operation Tests
    # =========================================================================

    def test_instantiate__ListMultiplication__RaisesError(self) -> None:
        config_path = CONFIG_DIR / "errors" / "list_multiplication.yaml"

        with self.assertRaises(InterpolationResolutionError):
            rc.instantiate(config_path, cli_overrides=False)

    def test_instantiate__StringSubtraction__RaisesError(self) -> None:
        config_path = CONFIG_DIR / "errors" / "string_subtraction.yaml"

        with self.assertRaises(InterpolationResolutionError):
            rc.instantiate(config_path, cli_overrides=False)

    def test_instantiate__UnaryMinusOnString__RaisesError(self) -> None:
        config_path = CONFIG_DIR / "errors" / "unary_minus_on_string.yaml"

        with self.assertRaises(InterpolationResolutionError):
            rc.instantiate(config_path, cli_overrides=False)

    def test_instantiate__UnaryPlusOnString__RaisesError(self) -> None:
        config_path = CONFIG_DIR / "errors" / "unary_plus_on_string.yaml"

        with self.assertRaises(InterpolationResolutionError):
            rc.instantiate(config_path, cli_overrides=False)

    def test_instantiate__PowerStringBase__RaisesError(self) -> None:
        config_path = CONFIG_DIR / "errors" / "power_string_base.yaml"

        with self.assertRaises(InterpolationResolutionError):
            rc.instantiate(config_path, cli_overrides=False)

    def test_instantiate__PowerStringExponent__RaisesError(self) -> None:
        config_path = CONFIG_DIR / "errors" / "power_string_exponent.yaml"

        with self.assertRaises(InterpolationResolutionError):
            rc.instantiate(config_path, cli_overrides=False)

    def test_instantiate__InOperatorNonContainer__RaisesError(self) -> None:
        config_path = CONFIG_DIR / "errors" / "in_operator_non_container.yaml"

        with self.assertRaises(InterpolationResolutionError):
            rc.instantiate(config_path, cli_overrides=False)

    # =========================================================================
    # Index/Access Error Tests
    # =========================================================================

    def test_instantiate__NegativeIndexOutOfBounds__RaisesError(self) -> None:
        config_path = CONFIG_DIR / "errors" / "negative_index_out_of_bounds.yaml"

        with self.assertRaises(InterpolationResolutionError):
            rc.instantiate(config_path, cli_overrides=False)

    def test_instantiate__IndexOnNumber__RaisesError(self) -> None:
        config_path = CONFIG_DIR / "errors" / "index_on_number.yaml"

        with self.assertRaises(InterpolationResolutionError):
            rc.instantiate(config_path, cli_overrides=False)

    def test_instantiate__IndexOnBoolean__RaisesError(self) -> None:
        config_path = CONFIG_DIR / "errors" / "index_on_boolean.yaml"

        with self.assertRaises(InterpolationResolutionError):
            rc.instantiate(config_path, cli_overrides=False)

    def test_instantiate__SliceOnNumber__RaisesError(self) -> None:
        config_path = CONFIG_DIR / "errors" / "slice_on_number.yaml"

        with self.assertRaises(InterpolationResolutionError):
            rc.instantiate(config_path, cli_overrides=False)

    def test_instantiate__LenOnNumber__RaisesError(self) -> None:
        config_path = CONFIG_DIR / "errors" / "len_on_number.yaml"

        with self.assertRaises(InterpolationResolutionError):
            rc.instantiate(config_path, cli_overrides=False)

    def test_instantiate__RemoveOnNumber__RaisesError(self) -> None:
        config_path = CONFIG_DIR / "errors" / "remove_on_number.yaml"

        with self.assertRaises(InterpolationResolutionError):
            rc.instantiate(config_path, cli_overrides=False)

    def test_instantiate__RemoveIndexOutOfBounds__RaisesError(self) -> None:
        config_path = CONFIG_DIR / "errors" / "remove_index_out_of_bounds.yaml"

        with self.assertRaises(InterpolationResolutionError):
            rc.instantiate(config_path, cli_overrides=False)

    # =========================================================================
    # Filter Error Tests
    # =========================================================================

    def test_instantiate__FilterOnDict__RaisesError(self) -> None:
        config_path = CONFIG_DIR / "errors" / "filter_on_dict.yaml"

        with self.assertRaises(InterpolationResolutionError):
            rc.instantiate(config_path, cli_overrides=False)

    def test_instantiate__FilterOnString__RaisesError(self) -> None:
        config_path = CONFIG_DIR / "errors" / "filter_on_string.yaml"

        with self.assertRaises(InterpolationResolutionError):
            rc.instantiate(config_path, cli_overrides=False)

    def test_instantiate__FilterTypeMismatch__RaisesError(self) -> None:
        config_path = CONFIG_DIR / "errors" / "filter_type_mismatch.yaml"

        with self.assertRaises(InterpolationResolutionError):
            rc.instantiate(config_path, cli_overrides=False)

    # =========================================================================
    # Environment Variable Error Tests
    # =========================================================================

    def test_instantiate__MissingEnvVar__RaisesError(self) -> None:
        config_path = CONFIG_DIR / "errors" / "missing_env_var.yaml"

        with self.assertRaises(EnvironmentVariableError):
            rc.instantiate(config_path, cli_overrides=False)

    # =========================================================================
    # Circular Reference Edge Case Tests
    # =========================================================================

    def test_instantiate__ThreeWayCycle__RaisesError(self) -> None:
        config_path = CONFIG_DIR / "errors" / "three_way_cycle.yaml"

        with self.assertRaises(CircularInterpolationError):
            rc.instantiate(config_path, cli_overrides=False)

    def test_instantiate__CycleWithNested__RaisesError(self) -> None:
        config_path = CONFIG_DIR / "errors" / "cycle_with_nested.yaml"

        with self.assertRaises(CircularInterpolationError):
            rc.instantiate(config_path, cli_overrides=False)


# =============================================================================
# Composition Integration Tests
# =============================================================================


class InterpolationCompositionTests(TestCase):
    """Tests for interpolation + _ref_ + _instance_."""

    def setUp(self) -> None:
        rc._store._known_targets.clear()
        rc.register("base_config_test", BaseConfigTest)
        rc.register("ref_interpolation_test", RefInterpolationTest)
        rc.register("cache_config", CacheConfig)
        rc.register("service_config", ServiceConfig)
        rc.register("instance_interpolation_test", InstanceInterpolationTest)

    def test_instantiate__RefWithInterpolation__ResolvesCorrectly(self) -> None:
        config_path = CONFIG_DIR / "composition" / "with_ref.yaml"

        result = rc.instantiate(config_path, RefInterpolationTest, cli_overrides=False)

        # Check values from included base.yaml
        self.assertEqual(result.defaults["learning_rate"], 0.001)
        self.assertEqual(result.defaults["batch_size"], 32)

        # Check interpolated values
        self.assertEqual(result.training["effective_lr"], 0.01)  # 0.001 * 10
        self.assertEqual(result.training["doubled_batch"], 64)  # 32 * 2
        self.assertEqual(result.training["total_steps"], 100000)  # 100 * 1000

        # Check model info references
        self.assertEqual(result.model_info["layer_count"], 3)
        self.assertEqual(result.model_info["first_layer"], 64)
        self.assertEqual(result.model_info["last_layer"], 256)
        self.assertEqual(result.model_info["full_name"], "model_base_model")

    def test_instantiate__InstanceWithInterpolation__SharesInstances(self) -> None:
        config_path = CONFIG_DIR / "composition" / "with_instance.yaml"

        result = rc.instantiate(config_path, InstanceInterpolationTest, cli_overrides=False)

        # Verify shared cache is the same instance
        self.assertIs(result.service_a.cache, result.shared_cache)
        self.assertIs(result.service_b.cache, result.shared_cache)

        # Verify cache values
        self.assertEqual(result.shared_cache.size, 1000)
        self.assertEqual(result.shared_cache.ttl, 3600)

        # Verify interpolated cache info
        self.assertEqual(result.cache_info["doubled_size"], 2000)
        self.assertEqual(result.cache_info["half_ttl"], 1800)

        # Verify interpolated values in services
        self.assertEqual(result.service_a.cache_size_check, 1000)
        self.assertEqual(result.service_b.cache_size_check, 1000)


# =============================================================================
# Custom Resolver Integration Tests
# =============================================================================


@dataclass
class ResolverTest:
    """Dataclass for resolver integration tests."""

    base_value: int
    debug_mode: bool
    flag_off: bool
    items: list[int]
    resolver_results: dict
    ternary_results: dict
    coalesce_results: dict
    combined_results: dict


class ResolverIntegrationTests(TestCase):
    """Tests for custom resolvers, ternary, and coalesce operators.

    No mocks - tests real component interactions.
    """

    @classmethod
    def setUpClass(cls) -> None:
        """Register test resolvers."""
        import uuid as uuid_module
        from datetime import datetime

        # Simple resolvers
        @rc.resolver("uuid")
        def gen_uuid() -> str:
            # Return a fixed value for test reproducibility
            return "test-uuid-1234"

        @rc.resolver("scale")
        def scale(value: int, factor: int) -> int:
            return value * factor

        @rc.resolver("now")
        def now(fmt: str = "%Y-%m-%d") -> str:
            # Return fixed value for reproducibility
            return "2025-01-02"

        # Namespaced resolvers
        @rc.resolver("math", "multiply")
        def math_multiply(a: int, b: int) -> int:
            return a * b

        @rc.resolver("db", "cache", "get")
        def cache_get(key: str) -> str:
            return f"cached:{key}"

        # Resolver with config access
        @rc.resolver("get_config_value")
        def get_config_value(path: str, *, _config_: dict) -> Any:
            return _config_.get(path)

        # Resolvers for coalesce testing
        @rc.resolver("get_value")
        def get_value() -> int:
            return 42

        @rc.resolver("return_null")
        def return_null() -> None:
            return None

        @rc.resolver("raise_error")
        def raise_error() -> str:
            raise RuntimeError("Intentional error for testing")

    @classmethod
    def tearDownClass(cls) -> None:
        """Unregister test resolvers."""
        rc.unregister_resolver("uuid")
        rc.unregister_resolver("scale")
        rc.unregister_resolver("now")
        rc.unregister_resolver("math", "multiply")
        rc.unregister_resolver("db", "cache", "get")
        rc.unregister_resolver("get_config_value")
        rc.unregister_resolver("get_value")
        rc.unregister_resolver("return_null")
        rc.unregister_resolver("raise_error")

    def setUp(self) -> None:
        rc._store._known_targets.clear()
        rc.register("resolver_test", ResolverTest)

    # === App Resolver Tests ===

    def test_instantiate__AppResolverNoArgs__ResolvesCorrectly(self) -> None:
        config_path = CONFIG_DIR / "basic" / "resolvers.yaml"

        result = rc.instantiate(config_path, ResolverTest, cli_overrides=False)

        self.assertEqual(result.resolver_results["uuid"], "test-uuid-1234")
        self.assertEqual(result.resolver_results["uuid_with_parens"], "test-uuid-1234")

    def test_instantiate__AppResolverPositionalArgs__ResolvesCorrectly(self) -> None:
        config_path = CONFIG_DIR / "basic" / "resolvers.yaml"

        result = rc.instantiate(config_path, ResolverTest, cli_overrides=False)

        self.assertEqual(result.resolver_results["scaled"], 10)  # 5 * 2

    def test_instantiate__AppResolverKeywordArgs__ResolvesCorrectly(self) -> None:
        config_path = CONFIG_DIR / "basic" / "resolvers.yaml"

        result = rc.instantiate(config_path, ResolverTest, cli_overrides=False)

        self.assertEqual(result.resolver_results["formatted_date"], "2025-01-02")

    def test_instantiate__AppResolverNamespaced__ResolvesCorrectly(self) -> None:
        config_path = CONFIG_DIR / "basic" / "resolvers.yaml"

        result = rc.instantiate(config_path, ResolverTest, cli_overrides=False)

        self.assertEqual(result.resolver_results["namespaced"], 12)  # 3 * 4
        self.assertEqual(result.resolver_results["deep_namespace"], "cached:test_key")

    def test_instantiate__AppResolverConfigRefArg__ResolvesCorrectly(self) -> None:
        config_path = CONFIG_DIR / "basic" / "resolvers.yaml"

        result = rc.instantiate(config_path, ResolverTest, cli_overrides=False)

        self.assertEqual(result.resolver_results["config_ref_arg"], 30)  # 10 * 3
        self.assertEqual(result.resolver_results["expr_arg"], 30)  # (10 + 5) * 2

    def test_instantiate__AppResolverConfigAccess__ResolvesCorrectly(self) -> None:
        config_path = CONFIG_DIR / "basic" / "resolvers.yaml"

        result = rc.instantiate(config_path, ResolverTest, cli_overrides=False)

        self.assertEqual(result.resolver_results["config_aware"], 10)

    # === Ternary Operator Tests ===

    def test_instantiate__TernaryBasic__ResolvesCorrectly(self) -> None:
        config_path = CONFIG_DIR / "basic" / "resolvers.yaml"

        result = rc.instantiate(config_path, ResolverTest, cli_overrides=False)

        self.assertEqual(result.ternary_results["basic_true"], "enabled")
        self.assertEqual(result.ternary_results["basic_false"], "disabled")

    def test_instantiate__TernaryComparison__ResolvesCorrectly(self) -> None:
        config_path = CONFIG_DIR / "basic" / "resolvers.yaml"

        result = rc.instantiate(config_path, ResolverTest, cli_overrides=False)

        self.assertEqual(result.ternary_results["comparison"], "high")  # 10 > 5

    def test_instantiate__TernaryNested__ResolvesCorrectly(self) -> None:
        config_path = CONFIG_DIR / "basic" / "resolvers.yaml"

        result = rc.instantiate(config_path, ResolverTest, cli_overrides=False)

        self.assertEqual(result.ternary_results["nested"], "high_debug")

    def test_instantiate__TernaryArithmetic__ResolvesCorrectly(self) -> None:
        config_path = CONFIG_DIR / "basic" / "resolvers.yaml"

        result = rc.instantiate(config_path, ResolverTest, cli_overrides=False)

        self.assertEqual(result.ternary_results["arithmetic"], 20)  # 10 * 2

    # === Coalesce Operator Tests ===

    def test_instantiate__ElvisCoalescePresent__ReturnsValue(self) -> None:
        config_path = CONFIG_DIR / "basic" / "resolvers.yaml"

        result = rc.instantiate(config_path, ResolverTest, cli_overrides=False)

        self.assertEqual(result.coalesce_results["elvis_present"], 42)

    def test_instantiate__ElvisCoalesceNull__ReturnsFallback(self) -> None:
        config_path = CONFIG_DIR / "basic" / "resolvers.yaml"

        result = rc.instantiate(config_path, ResolverTest, cli_overrides=False)

        self.assertEqual(result.coalesce_results["elvis_null"], "fallback")

    def test_instantiate__ElvisCoalesceMissing__ReturnsFallback(self) -> None:
        config_path = CONFIG_DIR / "basic" / "resolvers.yaml"

        result = rc.instantiate(config_path, ResolverTest, cli_overrides=False)

        self.assertEqual(result.coalesce_results["elvis_missing"], "fallback")

    def test_instantiate__ErrorCoalesceException__CatchesAndReturnsFallback(self) -> None:
        config_path = CONFIG_DIR / "basic" / "resolvers.yaml"

        result = rc.instantiate(config_path, ResolverTest, cli_overrides=False)

        self.assertEqual(result.coalesce_results["error_exception"], "caught")

    def test_instantiate__ChainedCoalesce__ResolvesCorrectly(self) -> None:
        config_path = CONFIG_DIR / "basic" / "resolvers.yaml"

        result = rc.instantiate(config_path, ResolverTest, cli_overrides=False)

        self.assertEqual(result.coalesce_results["chained"], "final_fallback")

    def test_instantiate__CoalesceConfigFallback__ResolvesCorrectly(self) -> None:
        config_path = CONFIG_DIR / "basic" / "resolvers.yaml"

        result = rc.instantiate(config_path, ResolverTest, cli_overrides=False)

        self.assertEqual(result.coalesce_results["config_fallback"], 10)

    # === Combined Operator Tests ===

    def test_instantiate__CoalesceInTernary__ResolvesCorrectly(self) -> None:
        config_path = CONFIG_DIR / "basic" / "resolvers.yaml"

        result = rc.instantiate(config_path, ResolverTest, cli_overrides=False)

        self.assertEqual(result.combined_results["coalesce_in_ternary"], "low")  # (null ?? 0) > 5 = false
        self.assertEqual(result.combined_results["coalesce_in_ternary_with_value"], "high")  # (42 ?? 0) > 5 = true

    def test_instantiate__TernaryWithResolverBranches__ResolvesCorrectly(self) -> None:
        config_path = CONFIG_DIR / "basic" / "resolvers.yaml"

        result = rc.instantiate(config_path, ResolverTest, cli_overrides=False)

        self.assertEqual(result.combined_results["resolver_branches"], 20)  # debug_mode is true, so 10 * 2
