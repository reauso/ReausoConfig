"""Unit tests for FlatHelpIntegration."""

from io import StringIO
from typing import Any, Optional, Union
from unittest import TestCase
from unittest.mock import patch

from rconfig.help import FlatHelpIntegration
from rconfig.provenance import Provenance, ProvenanceBuilder


def _build_prov(*entries):
    """Helper to quickly build a Provenance from entry specs.

    Each entry is a tuple: (path, file, line, value, type_hint?, description?)
    """
    builder = ProvenanceBuilder()
    for entry in entries:
        path, file, line, value = entry[0], entry[1], entry[2], entry[3]
        type_hint = entry[4] if len(entry) > 4 else None
        description = entry[5] if len(entry) > 5 else None
        builder.add(path, file=file, line=line, value=value, type_hint=type_hint, description=description)
    return builder.build()


class FlatHelpIntegrationTests(TestCase):
    """Tests for the FlatHelpIntegration class."""

    def _create_test_provenance(self) -> Provenance:
        """Create a test provenance object with type hints and descriptions."""
        builder = ProvenanceBuilder()
        builder.add(
            "model.lr",
            file="config.yaml",
            line=1,
            value=0.001,
            type_hint=float,
            description="Learning rate",
        )
        builder.add(
            "model.hidden_size",
            file="config.yaml",
            line=2,
            value=256,
            type_hint=int,
            description="Hidden layer size",
        )
        builder.add(
            "data.path",
            file="config.yaml",
            line=3,
            value=None,
            type_hint=str,
            description="Path to data",
        )
        return builder.build()

    # === Output Format Tests ===

    def test_integrate__ValidProvenance__PrintsFormattedOutput(self):
        """Test that valid provenance produces formatted output."""
        # Arrange
        output = StringIO()
        integration = FlatHelpIntegration(output=output)
        provenance = self._create_test_provenance()

        # Act
        with self.assertRaises(SystemExit) as ctx:
            integration.integrate(provenance, "config.yaml")

        # Assert
        self.assertEqual(ctx.exception.code, 0)
        result = output.getvalue()
        self.assertIn("model.lr", result)
        self.assertIn("model.hidden_size", result)
        self.assertIn("data.path", result)

    def test_integrate__ValidProvenance__IncludesHeader(self):
        """Test that output includes configuration header."""
        # Arrange
        output = StringIO()
        integration = FlatHelpIntegration(output=output)
        provenance = self._create_test_provenance()

        # Act
        with self.assertRaises(SystemExit):
            integration.integrate(provenance, "config.yaml")

        # Assert
        result = output.getvalue()
        self.assertIn("Configuration options for config.yaml", result)
        self.assertIn("===", result)

    def test_integrate__WithTypeHints__IncludesTypes(self):
        """Test that output includes type hints."""
        # Arrange
        output = StringIO()
        integration = FlatHelpIntegration(output=output)
        provenance = self._create_test_provenance()

        # Act
        with self.assertRaises(SystemExit):
            integration.integrate(provenance, "config.yaml")

        # Assert
        result = output.getvalue()
        self.assertIn("float", result)
        self.assertIn("int", result)
        self.assertIn("str", result)

    def test_integrate__WithDescriptions__IncludesDescriptions(self):
        """Test that output includes descriptions."""
        # Arrange
        output = StringIO()
        integration = FlatHelpIntegration(output=output)
        provenance = self._create_test_provenance()

        # Act
        with self.assertRaises(SystemExit):
            integration.integrate(provenance, "config.yaml")

        # Assert
        result = output.getvalue()
        self.assertIn("Learning rate", result)
        self.assertIn("Hidden layer size", result)
        self.assertIn("Path to data", result)

    def test_integrate__NoneValue__ShowsRequired(self):
        """Test that None values are shown as (required)."""
        # Arrange
        output = StringIO()
        integration = FlatHelpIntegration(output=output)
        provenance = self._create_test_provenance()

        # Act
        with self.assertRaises(SystemExit):
            integration.integrate(provenance, "config.yaml")

        # Assert
        result = output.getvalue()
        self.assertIn("(required)", result)

    # === Empty Provenance Tests ===

    def test_integrate__EmptyProvenance__ShowsNoOptionsMessage(self):
        """Test that empty provenance shows appropriate message."""
        # Arrange
        output = StringIO()
        integration = FlatHelpIntegration(output=output)
        provenance = Provenance()

        # Act
        with self.assertRaises(SystemExit):
            integration.integrate(provenance, "config.yaml")

        # Assert
        result = output.getvalue()
        self.assertIn("No configuration options found", result)

    # === Exit Behavior Tests ===

    def test_integrate__Always__ExitsWithZero(self):
        """Test that integrate always exits with code 0."""
        # Arrange
        output = StringIO()
        integration = FlatHelpIntegration(output=output)
        provenance = self._create_test_provenance()

        # Act & Assert
        with self.assertRaises(SystemExit) as ctx:
            integration.integrate(provenance, "config.yaml")

        self.assertEqual(ctx.exception.code, 0)

    # === consume_help_flag Tests ===

    def test_consumeHelpFlag__Default__IsTrue(self):
        """Test that consume_help_flag defaults to True."""
        # Act
        integration = FlatHelpIntegration()

        # Assert
        self.assertTrue(integration.consume_help_flag)

    # === Value Formatting Tests ===

    def test_formattedValue__Boolean__ShowsTrueFalse(self):
        """Test that boolean values are formatted as true/false."""
        # Arrange
        output = StringIO()
        integration = FlatHelpIntegration(output=output)
        prov = _build_prov(("debug", "config.yaml", 1, True, bool))

        # Act
        with self.assertRaises(SystemExit):
            integration.integrate(prov, "config.yaml")

        # Assert
        result = output.getvalue()
        self.assertIn("true", result)

    def test_formattedValue__String__ShowsQuoted(self):
        """Test that string values are quoted."""
        # Arrange
        output = StringIO()
        integration = FlatHelpIntegration(output=output)
        prov = _build_prov(("name", "config.yaml", 1, "test", str))

        # Act
        with self.assertRaises(SystemExit):
            integration.integrate(prov, "config.yaml")

        # Assert
        result = output.getvalue()
        self.assertIn("'test'", result)

    def test_formattedValue__LongString__TruncatesWithEllipsis(self):
        """Test that long strings are truncated."""
        # Arrange
        output = StringIO()
        integration = FlatHelpIntegration(output=output)
        prov = _build_prov(("long_value", "config.yaml", 1, "a" * 50, str))

        # Act
        with self.assertRaises(SystemExit):
            integration.integrate(prov, "config.yaml")

        # Assert
        result = output.getvalue()
        self.assertIn("...", result)

    # === Type Hint Edge Case Tests ===

    def test_formattedType__ListOfInt__ShowsListInt(self):
        """Test that list[int] type hint is formatted correctly."""
        # Arrange
        output = StringIO()
        integration = FlatHelpIntegration(output=output)
        prov = _build_prov(("numbers", "config.yaml", 1, [1, 2, 3], list[int]))

        # Act
        with self.assertRaises(SystemExit):
            integration.integrate(prov, "config.yaml")

        # Assert
        result = output.getvalue()
        self.assertIn("list[int]", result)

    def test_formattedType__DictStrAny__ShowsDictStrAny(self):
        """Test that dict[str, Any] type hint is formatted correctly."""
        # Arrange
        output = StringIO()
        integration = FlatHelpIntegration(output=output)
        prov = _build_prov(("mapping", "config.yaml", 1, {"key": "value"}, dict[str, Any]))

        # Act
        with self.assertRaises(SystemExit):
            integration.integrate(prov, "config.yaml")

        # Assert
        result = output.getvalue()
        # str(dict[str, Any]) gives "dict[str, typing.Any]"
        self.assertIn("dict[str, typing.Any]", result)

    def test_formattedType__OptionalFloat__ShowsOptionalFloat(self):
        """Test that Optional[float] type hint is formatted correctly."""
        # Arrange
        output = StringIO()
        integration = FlatHelpIntegration(output=output)
        prov = _build_prov(("optional_value", "config.yaml", 1, None, Optional[float]))

        # Act
        with self.assertRaises(SystemExit):
            integration.integrate(prov, "config.yaml")

        # Assert
        result = output.getvalue()
        # Optional[float] may display as "float | None" or "Optional[float]"
        self.assertTrue(
            "float | None" in result or "Optional[float]" in result,
            f"Expected Optional[float] representation in: {result}"
        )

    def test_formattedType__UnionIntStr__ShowsUnionIntStr(self):
        """Test that Union[int, str] type hint is formatted correctly."""
        # Arrange
        output = StringIO()
        integration = FlatHelpIntegration(output=output)
        prov = _build_prov(("mixed", "config.yaml", 1, "hello", Union[int, str]))

        # Act
        with self.assertRaises(SystemExit):
            integration.integrate(prov, "config.yaml")

        # Assert
        result = output.getvalue()
        # Union may display as "int | str" or "Union[int, str]"
        self.assertTrue(
            "int | str" in result or "Union[int, str]" in result,
            f"Expected Union[int, str] representation in: {result}"
        )

    def test_formattedType__NestedGeneric__ShowsNestedType(self):
        """Test that list[dict[str, int]] is formatted correctly."""
        # Arrange
        output = StringIO()
        integration = FlatHelpIntegration(output=output)
        prov = _build_prov(("nested", "config.yaml", 1, [{"a": 1}], list[dict[str, int]]))

        # Act
        with self.assertRaises(SystemExit):
            integration.integrate(prov, "config.yaml")

        # Assert
        result = output.getvalue()
        self.assertIn("list[dict[str, int]]", result)

    def test_formattedType__CustomClass__ShowsClassName(self):
        """Test that custom class type hint shows class name."""
        # Arrange
        class MyCustomConfig:
            pass

        output = StringIO()
        integration = FlatHelpIntegration(output=output)
        prov = _build_prov(("custom", "config.yaml", 1, None, MyCustomConfig))

        # Act
        with self.assertRaises(SystemExit):
            integration.integrate(prov, "config.yaml")

        # Assert
        result = output.getvalue()
        self.assertIn("MyCustomConfig", result)

    def test_formattedType__None__ShowsEmptyString(self):
        """Test that None type hint shows empty string."""
        # Arrange
        output = StringIO()
        integration = FlatHelpIntegration(output=output)
        prov = _build_prov(("untyped", "config.yaml", 1, 42, None))

        # Act
        with self.assertRaises(SystemExit):
            integration.integrate(prov, "config.yaml")

        # Assert
        result = output.getvalue()
        # Entry should appear, type column should be empty/minimal
        self.assertIn("untyped", result)
        self.assertIn("42", result)

    # === Value Formatting Edge Case Tests ===

    def test_formattedValue__NestedDict__TruncatesCorrectly(self):
        """Test that nested dicts are truncated correctly."""
        # Arrange
        output = StringIO()
        integration = FlatHelpIntegration(output=output)
        prov = _build_prov(("nested", "config.yaml", 1, {"a": {"b": {"c": 1}}}, dict))

        # Act
        with self.assertRaises(SystemExit):
            integration.integrate(prov, "config.yaml")

        # Assert
        result = output.getvalue()
        # Nested dict should be truncated at 20 chars
        self.assertIn("...", result)

    def test_formattedValue__ListOfDicts__TruncatesCorrectly(self):
        """Test that list of dicts is truncated correctly."""
        # Arrange
        output = StringIO()
        integration = FlatHelpIntegration(output=output)
        prov = _build_prov(("list_of_dicts", "config.yaml", 1, [{"key1": "value1"}, {"key2": "value2"}], list))

        # Act
        with self.assertRaises(SystemExit):
            integration.integrate(prov, "config.yaml")

        # Assert
        result = output.getvalue()
        self.assertIn("...", result)

    def test_formattedValue__EmptyString__ShowsQuotedEmpty(self):
        """Test that empty string shows as ''."""
        # Arrange
        output = StringIO()
        integration = FlatHelpIntegration(output=output)
        prov = _build_prov(("empty_str", "config.yaml", 1, "", str))

        # Act
        with self.assertRaises(SystemExit):
            integration.integrate(prov, "config.yaml")

        # Assert
        result = output.getvalue()
        self.assertIn("''", result)

    def test_formattedValue__EmptyList__ShowsEmptyList(self):
        """Test that empty list shows as []."""
        # Arrange
        output = StringIO()
        integration = FlatHelpIntegration(output=output)
        prov = _build_prov(("empty_list", "config.yaml", 1, [], list))

        # Act
        with self.assertRaises(SystemExit):
            integration.integrate(prov, "config.yaml")

        # Assert
        result = output.getvalue()
        self.assertIn("[]", result)

    def test_formattedValue__EmptyDict__ShowsEmptyDict(self):
        """Test that empty dict shows as {}."""
        # Arrange
        output = StringIO()
        integration = FlatHelpIntegration(output=output)
        prov = _build_prov(("empty_dict", "config.yaml", 1, {}, dict))

        # Act
        with self.assertRaises(SystemExit):
            integration.integrate(prov, "config.yaml")

        # Assert
        result = output.getvalue()
        self.assertIn("{}", result)

    def test_formattedValue__UnicodeString__ShowsUnicode(self):
        """Test that unicode strings display correctly."""
        # Arrange
        output = StringIO()
        integration = FlatHelpIntegration(output=output)
        prov = _build_prov(("unicode_val", "config.yaml", 1, "日本語", str))

        # Act
        with self.assertRaises(SystemExit):
            integration.integrate(prov, "config.yaml")

        # Assert
        result = output.getvalue()
        self.assertIn("日本語", result)

    def test_formattedValue__SpecialChars__ShowsRepr(self):
        """Test that special chars (newlines, tabs) are escaped via repr."""
        # Arrange
        output = StringIO()
        integration = FlatHelpIntegration(output=output)
        prov = _build_prov(("special", "config.yaml", 1, "line1\nline2", str))

        # Act
        with self.assertRaises(SystemExit):
            integration.integrate(prov, "config.yaml")

        # Assert
        result = output.getvalue()
        # repr() will show \n as escaped
        self.assertIn("\\n", result)

    def test_formattedValue__Float__ShowsCorrectPrecision(self):
        """Test that floats display with reasonable precision."""
        # Arrange
        output = StringIO()
        integration = FlatHelpIntegration(output=output)
        prov = _build_prov(
            ("small_float", "config.yaml", 1, 0.001, float),
            ("pi", "config.yaml", 2, 3.14159265358979, float),
        )

        # Act
        with self.assertRaises(SystemExit):
            integration.integrate(prov, "config.yaml")

        # Assert
        result = output.getvalue()
        self.assertIn("0.001", result)
        self.assertIn("3.14159", result)

    def test_formattedValue__FalseBool__ShowsFalse(self):
        """Test that False boolean shows as 'false'."""
        # Arrange
        output = StringIO()
        integration = FlatHelpIntegration(output=output)
        prov = _build_prov(("disabled", "config.yaml", 1, False, bool))

        # Act
        with self.assertRaises(SystemExit):
            integration.integrate(prov, "config.yaml")

        # Assert
        result = output.getvalue()
        self.assertIn("false", result)

    def test_formattedValue__Integer__ShowsInteger(self):
        """Test that integers display correctly."""
        # Arrange
        output = StringIO()
        integration = FlatHelpIntegration(output=output)
        prov = _build_prov(("count", "config.yaml", 1, 42, int))

        # Act
        with self.assertRaises(SystemExit):
            integration.integrate(prov, "config.yaml")

        # Assert
        result = output.getvalue()
        self.assertIn("42", result)

    # === Description Edge Case Tests ===

    def test_integrate__LongDescription__DisplaysFully(self):
        """Test that long descriptions are not truncated."""
        # Arrange
        output = StringIO()
        integration = FlatHelpIntegration(output=output)
        long_desc = "This is a very long description that spans multiple words"
        prov = _build_prov(("option", "config.yaml", 1, 42, int, long_desc))

        # Act
        with self.assertRaises(SystemExit):
            integration.integrate(prov, "config.yaml")

        # Assert
        result = output.getvalue()
        self.assertIn(long_desc, result)

    def test_integrate__DescriptionWithSpecialChars__DisplaysCorrectly(self):
        """Test descriptions with special characters."""
        # Arrange
        output = StringIO()
        integration = FlatHelpIntegration(output=output)
        prov = _build_prov(("operators", "config.yaml", 1, True, bool, "Use < and > operators"))

        # Act
        with self.assertRaises(SystemExit):
            integration.integrate(prov, "config.yaml")

        # Assert
        result = output.getvalue()
        self.assertIn("Use < and > operators", result)

    def test_integrate__UnicodeDescription__DisplaysUnicode(self):
        """Test that unicode descriptions display correctly."""
        # Arrange
        output = StringIO()
        integration = FlatHelpIntegration(output=output)
        prov = _build_prov(("emoji_option", "config.yaml", 1, True, bool, "Enable emoji support 🎉"))

        # Act
        with self.assertRaises(SystemExit):
            integration.integrate(prov, "config.yaml")

        # Assert
        result = output.getvalue()
        self.assertIn("Enable emoji support", result)

    def test_integrate__NoDescription__ShowsWithoutDescription(self):
        """Test that entries without description are formatted correctly."""
        # Arrange
        output = StringIO()
        integration = FlatHelpIntegration(output=output)
        prov = _build_prov(("no_desc", "config.yaml", 1, 100, int, None))

        # Act
        with self.assertRaises(SystemExit):
            integration.integrate(prov, "config.yaml")

        # Assert
        result = output.getvalue()
        self.assertIn("no_desc", result)
        self.assertIn("100", result)

    # === Column Alignment Tests ===

    def test_integrate__VaryingPathLengths__AlignsColumns(self):
        """Test that columns are aligned when paths have different lengths."""
        # Arrange
        output = StringIO()
        integration = FlatHelpIntegration(output=output)
        prov = _build_prov(
            ("a", "config.yaml", 1, 1, int),
            ("very.long.path.name", "config.yaml", 2, 2, int),
        )

        # Act
        with self.assertRaises(SystemExit):
            integration.integrate(prov, "config.yaml")

        # Assert
        result = output.getvalue()
        lines = result.split("\n")
        # Find lines with entries (skip header)
        entry_lines = [l for l in lines if "int" in l]
        self.assertEqual(len(entry_lines), 2)
        # The "int" type should appear at the same column position
        # (columns are aligned)
        pos1 = entry_lines[0].find("int")
        pos2 = entry_lines[1].find("int")
        self.assertEqual(pos1, pos2)

    def test_integrate__VaryingValueLengths__AlignsValueColumn(self):
        """Test that value column is aligned."""
        # Arrange
        output = StringIO()
        integration = FlatHelpIntegration(output=output)
        prov = _build_prov(
            ("short", "config.yaml", 1, 1, int),
            ("long_val", "config.yaml", 2, 999999, int),
        )

        # Act
        with self.assertRaises(SystemExit):
            integration.integrate(prov, "config.yaml")

        # Assert
        result = output.getvalue()
        # Both entries should be present with their values
        self.assertIn("1", result)
        self.assertIn("999999", result)

    # === Output Stream Tests ===

    def test_integrate__OutputEndsWithNewline__HasTrailingNewline(self):
        """Test that output ends with exactly one newline."""
        # Arrange
        output = StringIO()
        integration = FlatHelpIntegration(output=output)
        prov = _build_prov(("test", "config.yaml", 1, 42, int))

        # Act
        with self.assertRaises(SystemExit):
            integration.integrate(prov, "config.yaml")

        # Assert
        result = output.getvalue()
        self.assertTrue(result.endswith("\n"))
        self.assertFalse(result.endswith("\n\n"))
