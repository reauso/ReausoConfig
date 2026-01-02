"""Unit tests for interpolation parser."""

import unittest

from rconfig.interpolation import (
    InterpolationParser,
    InterpolationMatch,
    find_interpolations,
    has_interpolation,
    is_standalone_interpolation,
)
from rconfig.errors import InterpolationSyntaxError


class FindInterpolationsTests(unittest.TestCase):
    """Tests for find_interpolations function."""

    def test_find_interpolations__EmptyString__ReturnsEmptyList(self):
        result = find_interpolations("")
        self.assertEqual(result, [])

    def test_find_interpolations__NoInterpolations__ReturnsEmptyList(self):
        result = find_interpolations("hello world")
        self.assertEqual(result, [])

    def test_find_interpolations__SingleInterpolation__ReturnsMatch(self):
        result = find_interpolations("${/model.lr}")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].expression, "/model.lr")
        self.assertEqual(result[0].start, 0)
        self.assertEqual(result[0].end, 12)

    def test_find_interpolations__MultipleInterpolations__ReturnsAllMatches(self):
        result = find_interpolations("${/a} and ${/b}")
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].expression, "/a")
        self.assertEqual(result[1].expression, "/b")

    def test_find_interpolations__EmbeddedInterpolation__ReturnsCorrectPositions(self):
        text = "prefix_${env:NAME}_suffix"
        result = find_interpolations(text)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].expression, "env:NAME")
        self.assertEqual(result[0].start, 7)
        self.assertEqual(result[0].end, 18)


class HasInterpolationTests(unittest.TestCase):
    """Tests for has_interpolation function."""

    def test_has_interpolation__WithInterpolation__ReturnsTrue(self):
        self.assertTrue(has_interpolation("${/model.lr}"))

    def test_has_interpolation__WithoutInterpolation__ReturnsFalse(self):
        self.assertFalse(has_interpolation("hello world"))

    def test_has_interpolation__EmptyString__ReturnsFalse(self):
        self.assertFalse(has_interpolation(""))


class IsStandaloneInterpolationTests(unittest.TestCase):
    """Tests for is_standalone_interpolation function."""

    def test_is_standalone__ExactInterpolation__ReturnsTrue(self):
        self.assertTrue(is_standalone_interpolation("${/model.lr}"))

    def test_is_standalone__WithWhitespace__ReturnsTrue(self):
        self.assertTrue(is_standalone_interpolation("  ${/model.lr}  "))

    def test_is_standalone__WithPrefix__ReturnsFalse(self):
        self.assertFalse(is_standalone_interpolation("prefix${/model.lr}"))

    def test_is_standalone__WithSuffix__ReturnsFalse(self):
        self.assertFalse(is_standalone_interpolation("${/model.lr}suffix"))

    def test_is_standalone__MultipleInterpolations__ReturnsFalse(self):
        self.assertFalse(is_standalone_interpolation("${/a}${/b}"))


class InterpolationParserTests(unittest.TestCase):
    """Tests for InterpolationParser class."""

    def setUp(self):
        self.parser = InterpolationParser()

    # === Config path references ===

    def test_parse__AbsolutePath__Succeeds(self):
        tree = self.parser.parse("/model.lr")
        self.assertIsNotNone(tree)

    def test_parse__RelativePath__Succeeds(self):
        tree = self.parser.parse("./local.value")
        self.assertIsNotNone(tree)

    def test_parse__SimplePath__Succeeds(self):
        tree = self.parser.parse("model.lr")
        self.assertIsNotNone(tree)

    def test_parse__PathWithIndex__Succeeds(self):
        tree = self.parser.parse("/items[0]")
        self.assertIsNotNone(tree)

    def test_parse__PathWithMultipleIndices__Succeeds(self):
        tree = self.parser.parse("/model.layers[0].weights[1]")
        self.assertIsNotNone(tree)

    # === Environment variables ===

    def test_parse__EnvVar__Succeeds(self):
        tree = self.parser.parse("env:PATH")
        self.assertIsNotNone(tree)

    def test_parse__EnvVarWithDefaultCoalesce__Succeeds(self):
        tree = self.parser.parse('env:HOME ?: "/default"')
        self.assertIsNotNone(tree)

    def test_parse__EnvVarWithStringDefaultCoalesce__Succeeds(self):
        tree = self.parser.parse('env:NAME ?: "default_value"')
        self.assertIsNotNone(tree)

    def test_parse__EnvVarWithNumberDefaultCoalesce__Succeeds(self):
        tree = self.parser.parse("env:PORT ?: 8080")
        self.assertIsNotNone(tree)

    def test_parse__EnvVarWithBoolDefaultCoalesce__Succeeds(self):
        tree = self.parser.parse("env:DEBUG ?: true")
        self.assertIsNotNone(tree)

    # === Arithmetic operators ===

    def test_parse__Addition__Succeeds(self):
        tree = self.parser.parse("/a + /b")
        self.assertIsNotNone(tree)

    def test_parse__Subtraction__Succeeds(self):
        tree = self.parser.parse("/a - /b")
        self.assertIsNotNone(tree)

    def test_parse__Multiplication__Succeeds(self):
        tree = self.parser.parse("/a * /b")
        self.assertIsNotNone(tree)

    def test_parse__Division__Succeeds(self):
        tree = self.parser.parse("/a / /b")
        self.assertIsNotNone(tree)

    def test_parse__FloorDivision__Succeeds(self):
        tree = self.parser.parse("/a // /b")
        self.assertIsNotNone(tree)

    def test_parse__Modulo__Succeeds(self):
        tree = self.parser.parse("/a % /b")
        self.assertIsNotNone(tree)

    def test_parse__Power__Succeeds(self):
        tree = self.parser.parse("/a ** 2")
        self.assertIsNotNone(tree)

    def test_parse__UnaryMinus__Succeeds(self):
        tree = self.parser.parse("-/a")
        self.assertIsNotNone(tree)

    def test_parse__Parentheses__Succeeds(self):
        tree = self.parser.parse("(/a + /b) * 2")
        self.assertIsNotNone(tree)

    # === Comparison operators ===

    def test_parse__Equality__Succeeds(self):
        tree = self.parser.parse("/a == /b")
        self.assertIsNotNone(tree)

    def test_parse__Inequality__Succeeds(self):
        tree = self.parser.parse("/a != /b")
        self.assertIsNotNone(tree)

    def test_parse__LessThan__Succeeds(self):
        tree = self.parser.parse("/a < /b")
        self.assertIsNotNone(tree)

    def test_parse__GreaterThan__Succeeds(self):
        tree = self.parser.parse("/a > /b")
        self.assertIsNotNone(tree)

    def test_parse__LessOrEqual__Succeeds(self):
        tree = self.parser.parse("/a <= /b")
        self.assertIsNotNone(tree)

    def test_parse__GreaterOrEqual__Succeeds(self):
        tree = self.parser.parse("/a >= /b")
        self.assertIsNotNone(tree)

    # === Boolean operators ===

    def test_parse__And__Succeeds(self):
        tree = self.parser.parse("/a and /b")
        self.assertIsNotNone(tree)

    def test_parse__Or__Succeeds(self):
        tree = self.parser.parse("/a or /b")
        self.assertIsNotNone(tree)

    def test_parse__Not__Succeeds(self):
        tree = self.parser.parse("not /a")
        self.assertIsNotNone(tree)

    def test_parse__In__Succeeds(self):
        tree = self.parser.parse('"x" in /items')
        self.assertIsNotNone(tree)

    def test_parse__NotIn__Succeeds(self):
        tree = self.parser.parse('"x" not in /items')
        self.assertIsNotNone(tree)

    # === List operations ===

    def test_parse__ListLiteral__Succeeds(self):
        tree = self.parser.parse("[1, 2, 3]")
        self.assertIsNotNone(tree)

    def test_parse__ListConcat__Succeeds(self):
        tree = self.parser.parse("/a + /b")
        self.assertIsNotNone(tree)

    def test_parse__ListIndex__Succeeds(self):
        tree = self.parser.parse("/items[0]")
        self.assertIsNotNone(tree)

    def test_parse__ListSlice__Succeeds(self):
        tree = self.parser.parse("/items[1:3]")
        self.assertIsNotNone(tree)

    def test_parse__ListSliceFromStart__Succeeds(self):
        tree = self.parser.parse("/items[:3]")
        self.assertIsNotNone(tree)

    def test_parse__ListSliceToEnd__Succeeds(self):
        tree = self.parser.parse("/items[2:]")
        self.assertIsNotNone(tree)

    def test_parse__ListRemove__Succeeds(self):
        tree = self.parser.parse("/items.remove(0)")
        self.assertIsNotNone(tree)

    def test_parse__LenFunction__Succeeds(self):
        tree = self.parser.parse("len(/items)")
        self.assertIsNotNone(tree)

    # === Literals ===

    def test_parse__IntegerLiteral__Succeeds(self):
        tree = self.parser.parse("42")
        self.assertIsNotNone(tree)

    def test_parse__FloatLiteral__Succeeds(self):
        tree = self.parser.parse("3.14")
        self.assertIsNotNone(tree)

    def test_parse__StringLiteral__Succeeds(self):
        tree = self.parser.parse('"hello"')
        self.assertIsNotNone(tree)

    def test_parse__TrueLiteral__Succeeds(self):
        tree = self.parser.parse("true")
        self.assertIsNotNone(tree)

    def test_parse__FalseLiteral__Succeeds(self):
        tree = self.parser.parse("false")
        self.assertIsNotNone(tree)

    def test_parse__NullLiteral__Succeeds(self):
        tree = self.parser.parse("null")
        self.assertIsNotNone(tree)

    # === Complex expressions ===

    def test_parse__ComplexExpression__Succeeds(self):
        tree = self.parser.parse("/model.lr * 2 + 0.001")
        self.assertIsNotNone(tree)

    def test_parse__StringConcatenation__Succeeds(self):
        tree = self.parser.parse('"prefix_" + /name + "_suffix"')
        self.assertIsNotNone(tree)

    def test_parse__BooleanExpression__Succeeds(self):
        tree = self.parser.parse("/epochs > 100 and /lr < 0.01")
        self.assertIsNotNone(tree)

    # === Filter operations ===

    def test_parse__FilterBasic__Succeeds(self):
        tree = self.parser.parse("/items | filter(x > 5)")
        self.assertIsNotNone(tree)

    def test_parse__FilterWithComparison__Succeeds(self):
        tree = self.parser.parse("/items | filter(x == 0)")
        self.assertIsNotNone(tree)

    def test_parse__FilterWithLessThan__Succeeds(self):
        tree = self.parser.parse("/items | filter(x < 10)")
        self.assertIsNotNone(tree)

    def test_parse__FilterWithNotEquals__Succeeds(self):
        tree = self.parser.parse("/items | filter(x != null)")
        self.assertIsNotNone(tree)

    # === Parent-relative paths ===

    def test_parse__ParentPath__Succeeds(self):
        tree = self.parser.parse("../sibling.value")
        self.assertIsNotNone(tree)

    def test_parse__MultipleParentPath__Succeeds(self):
        tree = self.parser.parse("../../ancestor.value")
        self.assertIsNotNone(tree)

    # === Edge cases ===

    def test_parse__EmptyListLiteral__Succeeds(self):
        tree = self.parser.parse("[]")
        self.assertIsNotNone(tree)

    def test_parse__NestedListLiteral__Succeeds(self):
        tree = self.parser.parse("[[1, 2], [3, 4]]")
        self.assertIsNotNone(tree)

    def test_parse__NegativeNumber__Succeeds(self):
        tree = self.parser.parse("-42")
        self.assertIsNotNone(tree)

    def test_parse__NegativeFloat__Succeeds(self):
        tree = self.parser.parse("-3.14")
        self.assertIsNotNone(tree)

    def test_parse__ScientificNotation__Succeeds(self):
        tree = self.parser.parse("1e10")
        self.assertIsNotNone(tree)

    def test_parse__ScientificNotationNegativeExponent__Succeeds(self):
        tree = self.parser.parse("1e-5")
        self.assertIsNotNone(tree)

    def test_parse__ScientificNotationWithDecimal__Succeeds(self):
        tree = self.parser.parse("1.5e3")
        self.assertIsNotNone(tree)

    # === Slice with negative indices ===

    def test_parse__SliceNegativeStart__Succeeds(self):
        tree = self.parser.parse("/items[-2:]")
        self.assertIsNotNone(tree)

    def test_parse__SliceNegativeEnd__Succeeds(self):
        tree = self.parser.parse("/items[:-2]")
        self.assertIsNotNone(tree)

    def test_parse__SliceBothNegative__Succeeds(self):
        tree = self.parser.parse("/items[-3:-1]")
        self.assertIsNotNone(tree)

    # === Complex operator combinations ===

    def test_parse__ChainedComparisons__Succeeds(self):
        tree = self.parser.parse("/a > 0 and /a < 100")
        self.assertIsNotNone(tree)

    def test_parse__NestedParentheses__Succeeds(self):
        tree = self.parser.parse("((/a + /b) * /c) / /d")
        self.assertIsNotNone(tree)

    def test_parse__MixedOperators__Succeeds(self):
        tree = self.parser.parse("/a + /b * /c - /d / /e")
        self.assertIsNotNone(tree)

    # === App resolver syntax ===

    def test_parse__AppResolverNoArgs__Succeeds(self):
        """app:uuid - no parens, no args"""
        tree = self.parser.parse("app:uuid")
        self.assertIsNotNone(tree)

    def test_parse__AppResolverEmptyParens__Succeeds(self):
        """app:uuid() - explicit empty parens"""
        tree = self.parser.parse("app:uuid()")
        self.assertIsNotNone(tree)

    def test_parse__AppResolverSingleStringArg__Succeeds(self):
        """app:greet("World") - single string arg"""
        tree = self.parser.parse('app:greet("World")')
        self.assertIsNotNone(tree)

    def test_parse__AppResolverMultipleNumericArgs__Succeeds(self):
        """app:add(1, 2) - multiple numeric args"""
        tree = self.parser.parse("app:add(1, 2)")
        self.assertIsNotNone(tree)

    def test_parse__AppResolverNamespaced__Succeeds(self):
        """app:math:add(1, 2) - namespaced with args"""
        tree = self.parser.parse("app:math:add(1, 2)")
        self.assertIsNotNone(tree)

    def test_parse__AppResolverKeywordArg__Succeeds(self):
        """app:now(fmt="%Y-%m-%d") - keyword argument"""
        tree = self.parser.parse('app:now(fmt="%Y-%m-%d")')
        self.assertIsNotNone(tree)

    def test_parse__AppResolverDeepNamespaceWithKwargs__Succeeds(self):
        """app:db:cache:get("key", ttl=300) - deep namespace with mixed args"""
        tree = self.parser.parse('app:db:cache:get("key", ttl=300)')
        self.assertIsNotNone(tree)

    def test_parse__AppResolverConfigRefAsArg__Succeeds(self):
        """app:derive(/config.path) - config ref as argument"""
        tree = self.parser.parse("app:derive(/config.path)")
        self.assertIsNotNone(tree)

    def test_parse__AppResolverExpressionAsArg__Succeeds(self):
        """app:compute(/path, 2 + 3) - expression as argument"""
        tree = self.parser.parse("app:compute(/path, 2 + 3)")
        self.assertIsNotNone(tree)

    def test_parse__AppResolverNestedCall__Succeeds(self):
        """app:outer(app:inner()) - resolver result as argument"""
        tree = self.parser.parse("app:outer(app:inner())")
        self.assertIsNotNone(tree)

    def test_parse__AppResolverInExpression__Succeeds(self):
        """app:get_value() + 10 - resolver in arithmetic expression"""
        tree = self.parser.parse("app:get_value() + 10")
        self.assertIsNotNone(tree)

    def test_parse__AppResolverMixedPositionalAndKeyword__Succeeds(self):
        """app:func("pos1", "pos2", key1=1, key2=2)"""
        tree = self.parser.parse('app:func("pos1", "pos2", key1=1, key2=2)')
        self.assertIsNotNone(tree)

    # === Ternary operator ===

    def test_parse__TernaryBasic__Succeeds(self):
        """/debug ? "verbose" : "quiet" - basic ternary"""
        tree = self.parser.parse('/debug ? "verbose" : "quiet"')
        self.assertIsNotNone(tree)

    def test_parse__TernaryWithComparison__Succeeds(self):
        """/count > 10 ? "high" : "low" - comparison as condition"""
        tree = self.parser.parse('/count > 10 ? "high" : "low"')
        self.assertIsNotNone(tree)

    def test_parse__TernaryWithResolver__Succeeds(self):
        """app:ready() ? "go" : "wait" - resolver as condition"""
        tree = self.parser.parse('app:ready() ? "go" : "wait"')
        self.assertIsNotNone(tree)

    def test_parse__TernaryNested__Succeeds(self):
        """a ? b : c ? d : e - nested ternary (right-associative)"""
        tree = self.parser.parse('/a ? /b : /c ? /d : /e')
        self.assertIsNotNone(tree)

    def test_parse__TernaryInExpression__Succeeds(self):
        """(/a ? /b : /c) + 1 - ternary in expression"""
        tree = self.parser.parse("(/a ? /b : /c) + 1")
        self.assertIsNotNone(tree)

    def test_parse__TernaryWithBooleanCondition__Succeeds(self):
        """/a and /b ? 1 : 0 - boolean condition"""
        tree = self.parser.parse("/a and /b ? 1 : 0")
        self.assertIsNotNone(tree)

    def test_parse__TernaryWithLiterals__Succeeds(self):
        """true ? 1 : 0 - literal condition"""
        tree = self.parser.parse("true ? 1 : 0")
        self.assertIsNotNone(tree)

    # === Coalesce operators ===

    def test_parse__ElvisCoalesceWithResolver__Succeeds(self):
        """app:uuid ?: "fallback" - Elvis coalesce with resolver"""
        tree = self.parser.parse('app:uuid ?: "fallback"')
        self.assertIsNotNone(tree)

    def test_parse__ElvisCoalesceWithEnv__Succeeds(self):
        """env:VAR ?: "default" - Elvis coalesce with env"""
        tree = self.parser.parse('env:VAR ?: "default"')
        self.assertIsNotNone(tree)

    def test_parse__ErrorCoalesceWithResolver__Succeeds(self):
        """app:risky() ?? "safe" - error coalesce with resolver"""
        tree = self.parser.parse('app:risky() ?? "safe"')
        self.assertIsNotNone(tree)

    def test_parse__ErrorCoalesceWithEnv__Succeeds(self):
        """env:VAR ?? "default" - error coalesce with env"""
        tree = self.parser.parse('env:VAR ?? "default"')
        self.assertIsNotNone(tree)

    def test_parse__ChainedErrorCoalesce__Succeeds(self):
        """app:a ?? app:b ?? "c" - chained (right-associative)"""
        tree = self.parser.parse('app:a ?? app:b ?? "c"')
        self.assertIsNotNone(tree)

    def test_parse__ChainedElvisCoalesce__Succeeds(self):
        """app:a ?: app:b ?: "c" - chained Elvis coalesce"""
        tree = self.parser.parse('app:a ?: app:b ?: "c"')
        self.assertIsNotNone(tree)

    def test_parse__NullWithCoalesce__Succeeds(self):
        """null ?: "fallback" - literal null with coalesce"""
        tree = self.parser.parse('null ?: "fallback"')
        self.assertIsNotNone(tree)

    def test_parse__CoalesceWithConfigRef__Succeeds(self):
        """app:x ?? /fallback.path - config ref as fallback"""
        tree = self.parser.parse("app:x ?? /fallback.path")
        self.assertIsNotNone(tree)

    def test_parse__CoalesceWithExpression__Succeeds(self):
        """app:x + 1 ?: 0 - expression with coalesce"""
        tree = self.parser.parse("app:x + 1 ?: 0")
        self.assertIsNotNone(tree)

    def test_parse__MixedCoalesceOperators__Succeeds(self):
        """app:a ?: app:b ?? "c" - mixed coalesce types"""
        tree = self.parser.parse('app:a ?: app:b ?? "c"')
        self.assertIsNotNone(tree)

    # === Combined operators (ternary + coalesce) ===

    def test_parse__CoalesceInTernaryCondition__Succeeds(self):
        """(app:x ?? 0) > 5 ? "high" : "low" - coalesce in ternary condition"""
        tree = self.parser.parse('(app:x ?? 0) > 5 ? "high" : "low"')
        self.assertIsNotNone(tree)

    def test_parse__TernaryWithCoalesceBranches__Succeeds(self):
        """/flag ? app:a ?? "x" : app:b ?? "y" - coalesce in ternary branches"""
        tree = self.parser.parse('/flag ? app:a ?? "x" : app:b ?? "y"')
        self.assertIsNotNone(tree)

    def test_parse__ResolverInTernaryBranch__Succeeds(self):
        """/debug ? app:verbose_log() : app:quiet_log()"""
        tree = self.parser.parse("/debug ? app:verbose_log() : app:quiet_log()")
        self.assertIsNotNone(tree)

    # === App resolver error cases ===

    def test_parse__AppResolverMissingName__RaisesError(self):
        """app: alone should fail"""
        with self.assertRaises(InterpolationSyntaxError):
            self.parser.parse("app:")

    def test_parse__AppResolverEmptyArg__RaisesError(self):
        """app:resolver(,) - empty argument should fail"""
        with self.assertRaises(InterpolationSyntaxError):
            self.parser.parse("app:resolver(,)")

    def test_parse__AppResolverMissingKeywordValue__RaisesError(self):
        """app:resolver(key=) - missing keyword value should fail"""
        with self.assertRaises(InterpolationSyntaxError):
            self.parser.parse("app:resolver(key=)")

    def test_parse__AppResolverUnclosedParens__RaisesError(self):
        """app:resolver( - unclosed parentheses should fail"""
        with self.assertRaises(InterpolationSyntaxError):
            self.parser.parse("app:resolver(")

    # === Ternary error cases ===

    def test_parse__TernaryMissingColon__RaisesError(self):
        """/a ? /b - missing colon should fail"""
        with self.assertRaises(InterpolationSyntaxError):
            self.parser.parse("/a ? /b")

    def test_parse__TernaryMissingFalseBranch__RaisesError(self):
        """/a ? /b : - missing false branch should fail"""
        with self.assertRaises(InterpolationSyntaxError):
            self.parser.parse("/a ? /b :")

    # === Error cases ===

    def test_parse__InvalidSyntax__RaisesError(self):
        with self.assertRaises(InterpolationSyntaxError):
            self.parser.parse("+++")

    def test_parse__UnbalancedParentheses__RaisesError(self):
        with self.assertRaises(InterpolationSyntaxError):
            self.parser.parse("(/a + /b")

    def test_parse__UnbalancedBrackets__RaisesError(self):
        with self.assertRaises(InterpolationSyntaxError):
            self.parser.parse("/items[0")

    def test_parse__InvalidOperator__RaisesError(self):
        with self.assertRaises(InterpolationSyntaxError):
            self.parser.parse("/a @ /b")

    def test_parse__IncompleteExpression__RaisesError(self):
        with self.assertRaises(InterpolationSyntaxError):
            self.parser.parse("/a +")


if __name__ == "__main__":
    unittest.main()
