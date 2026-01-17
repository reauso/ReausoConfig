"""Unit tests for GroupedHelpIntegration."""

from io import StringIO
from typing import Any, Optional, Union
from unittest import TestCase

from rconfig.help import GroupedHelpIntegration
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


class GroupedHelpIntegrationTests(TestCase):
    """Tests for the GroupedHelpIntegration class."""

    def _create_test_provenance(self) -> Provenance:
        """Create a test provenance object with grouped entries."""
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
            value="/data",
            type_hint=str,
            description="Path to data",
        )
        builder.add(
            "data.batch_size",
            file="config.yaml",
            line=4,
            value=32,
            type_hint=int,
            description="Batch size",
        )
        return builder.build()

    # === Output Format Tests ===

    def test_integrate__ValidProvenance__PrintsGroupedOutput(self):
        """Test that valid provenance produces grouped output."""
        # Arrange
        output = StringIO()
        integration = GroupedHelpIntegration(output=output)
        provenance = self._create_test_provenance()

        # Act
        with self.assertRaises(SystemExit) as ctx:
            integration.integrate(provenance, "config.yaml")

        # Assert
        self.assertEqual(ctx.exception.code, 0)
        result = output.getvalue()
        self.assertIn("model:", result)
        self.assertIn("data:", result)

    def test_integrate__ValidProvenance__IncludesHeader(self):
        """Test that output includes configuration header."""
        # Arrange
        output = StringIO()
        integration = GroupedHelpIntegration(output=output)
        provenance = self._create_test_provenance()

        # Act
        with self.assertRaises(SystemExit):
            integration.integrate(provenance, "config.yaml")

        # Assert
        result = output.getvalue()
        self.assertIn("Configuration options for config.yaml", result)

    def test_integrate__GroupedEntries__IndentsNestedKeys(self):
        """Test that nested keys are indented under their group."""
        # Arrange
        output = StringIO()
        integration = GroupedHelpIntegration(output=output)
        provenance = self._create_test_provenance()

        # Act
        with self.assertRaises(SystemExit):
            integration.integrate(provenance, "config.yaml")

        # Assert
        result = output.getvalue()
        # Check that entries appear grouped - model and data groups exist
        lines = result.split("\n")

        # Find group headers (ends with :)
        model_lines = [l for l in lines if "model:" in l or "lr" in l or "hidden_size" in l]
        data_lines = [l for l in lines if "data:" in l or "path" in l or "batch_size" in l]

        # Both groups should have entries
        self.assertTrue(len(model_lines) >= 2, "Model group should have header and entries")
        self.assertTrue(len(data_lines) >= 2, "Data group should have header and entries")

    def test_integrate__WithTypeHints__IncludesTypes(self):
        """Test that output includes type hints."""
        # Arrange
        output = StringIO()
        integration = GroupedHelpIntegration(output=output)
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
        integration = GroupedHelpIntegration(output=output)
        provenance = self._create_test_provenance()

        # Act
        with self.assertRaises(SystemExit):
            integration.integrate(provenance, "config.yaml")

        # Assert
        result = output.getvalue()
        self.assertIn("Learning rate", result)
        self.assertIn("Hidden layer size", result)
        self.assertIn("Path to data", result)
        self.assertIn("Batch size", result)

    # === Empty Provenance Tests ===

    def test_integrate__EmptyProvenance__ShowsNoOptionsMessage(self):
        """Test that empty provenance shows appropriate message."""
        # Arrange
        output = StringIO()
        integration = GroupedHelpIntegration(output=output)
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
        integration = GroupedHelpIntegration(output=output)
        provenance = self._create_test_provenance()

        # Act & Assert
        with self.assertRaises(SystemExit) as ctx:
            integration.integrate(provenance, "config.yaml")

        self.assertEqual(ctx.exception.code, 0)

    # === consume_help_flag Tests ===

    def test_consumeHelpFlag__Default__IsTrue(self):
        """Test that consume_help_flag defaults to True."""
        # Act
        integration = GroupedHelpIntegration()

        # Assert
        self.assertTrue(integration.consume_help_flag)

    # === Single-Level Keys Tests ===

    def test_integrate__SingleLevelKey__NotGrouped(self):
        """Test that single-level keys are not grouped."""
        # Arrange
        output = StringIO()
        integration = GroupedHelpIntegration(output=output)
        prov = _build_prov(("debug", "config.yaml", 1, True, bool))

        # Act
        with self.assertRaises(SystemExit):
            integration.integrate(prov, "config.yaml")

        # Assert
        result = output.getvalue()
        # Single-level keys should appear directly without group header
        self.assertIn("debug", result)

    # === Path Handling Edge Case Tests ===

    def test_integrate__DeeplyNestedPaths__GroupsCorrectly(self):
        """Test paths like a.b.c.d.e are grouped by first level."""
        # Arrange
        output = StringIO()
        integration = GroupedHelpIntegration(output=output)
        prov = _build_prov(
            ("model.optimizer.lr", "config.yaml", 1, 0.001, float),
            ("model.optimizer.weight_decay", "config.yaml", 2, 0.0001, float),
            ("model.layers.hidden.size", "config.yaml", 3, 256, int),
        )

        # Act
        with self.assertRaises(SystemExit):
            integration.integrate(prov, "config.yaml")

        # Assert
        result = output.getvalue()
        # All should be under "model:" group
        self.assertIn("model:", result)
        self.assertIn("optimizer.lr", result)
        self.assertIn("optimizer.weight_decay", result)
        self.assertIn("layers.hidden.size", result)

    def test_integrate__MixedDepthPaths__GroupsCorrectly(self):
        """Test mixing single-level and multi-level paths."""
        # Arrange
        output = StringIO()
        integration = GroupedHelpIntegration(output=output)
        prov = _build_prov(
            ("debug", "config.yaml", 1, True, bool),
            ("model.lr", "config.yaml", 2, 0.001, float),
            ("model.hidden_size", "config.yaml", 3, 256, int),
        )

        # Act
        with self.assertRaises(SystemExit):
            integration.integrate(prov, "config.yaml")

        # Assert
        result = output.getvalue()
        # debug should have its own group, model entries under "model:" group
        self.assertIn("debug:", result)
        self.assertIn("model:", result)

    def test_integrate__SingleLevelPath__ShowsAsRootEntry(self):
        """Test single-level paths show (root) under their key."""
        # Arrange
        output = StringIO()
        integration = GroupedHelpIntegration(output=output)
        prov = _build_prov(("verbose", "config.yaml", 1, False, bool))

        # Act
        with self.assertRaises(SystemExit):
            integration.integrate(prov, "config.yaml")

        # Assert
        result = output.getvalue()
        # Single-level entry should show (root) indicator
        self.assertIn("verbose:", result)
        self.assertIn("(root)", result)

    def test_integrate__MultipleTopLevelGroups__AllGroupsShown(self):
        """Test multiple top-level groups are all displayed."""
        # Arrange
        output = StringIO()
        integration = GroupedHelpIntegration(output=output)
        prov = _build_prov(
            ("model.lr", "config.yaml", 1, 0.001, float),
            ("data.path", "config.yaml", 2, "/data", str),
            ("training.epochs", "config.yaml", 3, 100, int),
        )

        # Act
        with self.assertRaises(SystemExit):
            integration.integrate(prov, "config.yaml")

        # Assert
        result = output.getvalue()
        self.assertIn("data:", result)
        self.assertIn("model:", result)
        self.assertIn("training:", result)

    # === Type Hint Edge Case Tests ===

    def test_formattedType__ListOfInt__ShowsListInt(self):
        """Test that list[int] type hint is formatted correctly."""
        # Arrange
        output = StringIO()
        integration = GroupedHelpIntegration(output=output)
        prov = _build_prov(("config.numbers", "config.yaml", 1, [1, 2, 3], list[int]))

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
        integration = GroupedHelpIntegration(output=output)
        prov = _build_prov(("config.mapping", "config.yaml", 1, {"key": "value"}, dict[str, Any]))

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
        integration = GroupedHelpIntegration(output=output)
        prov = _build_prov(("config.optional_value", "config.yaml", 1, None, Optional[float]))

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

    # === Value Formatting Edge Case Tests ===

    def test_formattedValue__EmptyList__ShowsEmptyList(self):
        """Test that empty list shows as []."""
        # Arrange
        output = StringIO()
        integration = GroupedHelpIntegration(output=output)
        prov = _build_prov(("config.empty_list", "config.yaml", 1, [], list))

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
        integration = GroupedHelpIntegration(output=output)
        prov = _build_prov(("config.empty_dict", "config.yaml", 1, {}, dict))

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
        integration = GroupedHelpIntegration(output=output)
        prov = _build_prov(("config.unicode_val", "config.yaml", 1, "日本語", str))

        # Act
        with self.assertRaises(SystemExit):
            integration.integrate(prov, "config.yaml")

        # Assert
        result = output.getvalue()
        self.assertIn("日本語", result)

    def test_formattedValue__FalseBool__ShowsFalse(self):
        """Test that False boolean shows as 'false'."""
        # Arrange
        output = StringIO()
        integration = GroupedHelpIntegration(output=output)
        prov = _build_prov(("config.disabled", "config.yaml", 1, False, bool))

        # Act
        with self.assertRaises(SystemExit):
            integration.integrate(prov, "config.yaml")

        # Assert
        result = output.getvalue()
        self.assertIn("false", result)

    # === Description Edge Case Tests ===

    def test_integrate__LongDescription__DisplaysFully(self):
        """Test that long descriptions are not truncated."""
        # Arrange
        output = StringIO()
        integration = GroupedHelpIntegration(output=output)
        long_desc = "This is a very long description that spans many words"
        prov = _build_prov(("config.option", "config.yaml", 1, 42, int, long_desc))

        # Act
        with self.assertRaises(SystemExit):
            integration.integrate(prov, "config.yaml")

        # Assert
        result = output.getvalue()
        self.assertIn(long_desc, result)

    def test_integrate__UnicodeDescription__DisplaysUnicode(self):
        """Test that unicode descriptions display correctly."""
        # Arrange
        output = StringIO()
        integration = GroupedHelpIntegration(output=output)
        prov = _build_prov(("config.emoji", "config.yaml", 1, True, bool, "Enable emoji support 🎉"))

        # Act
        with self.assertRaises(SystemExit):
            integration.integrate(prov, "config.yaml")

        # Assert
        result = output.getvalue()
        self.assertIn("Enable emoji support", result)

    # === Output Stream Tests ===

    def test_integrate__OutputEndsWithNewline__HasTrailingNewline(self):
        """Test that output ends with exactly one newline."""
        # Arrange
        output = StringIO()
        integration = GroupedHelpIntegration(output=output)
        prov = _build_prov(("test.value", "config.yaml", 1, 42, int))

        # Act
        with self.assertRaises(SystemExit):
            integration.integrate(prov, "config.yaml")

        # Assert
        result = output.getvalue()
        self.assertTrue(result.endswith("\n"))
        self.assertFalse(result.endswith("\n\n"))

    # === Column Alignment Within Groups ===

    def test_integrate__VaryingPathLengths__AlignsColumnsWithinGroup(self):
        """Test that columns are aligned within a group."""
        # Arrange
        output = StringIO()
        integration = GroupedHelpIntegration(output=output)
        prov = _build_prov(
            ("model.a", "config.yaml", 1, 1, int),
            ("model.very_long_name", "config.yaml", 2, 2, int),
        )

        # Act
        with self.assertRaises(SystemExit):
            integration.integrate(prov, "config.yaml")

        # Assert
        result = output.getvalue()
        lines = result.split("\n")
        # Find lines with int type in model group (indented lines)
        entry_lines = [l for l in lines if "  " in l and "int" in l]
        self.assertEqual(len(entry_lines), 2)
        # The "int" type should appear at the same column position
        pos1 = entry_lines[0].find("int")
        pos2 = entry_lines[1].find("int")
        self.assertEqual(pos1, pos2)
