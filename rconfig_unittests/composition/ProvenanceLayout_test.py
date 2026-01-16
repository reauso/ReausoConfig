"""Tests for ProvenanceLayout base class and ProvenanceFormatContext dataclass."""

from unittest import TestCase

from rconfig.composition import (
    ProvenanceFormatContext,
    ProvenanceLayout,
    ProvenanceNode,
)


class ProvenanceFormatContextDefaultTests(TestCase):
    """Tests for ProvenanceFormatContext default initialization."""

    def test_ProvenanceFormatContext__DefaultInit__AllBoolFieldsTrue(self) -> None:
        """Test that default ProvenanceFormatContext has all boolean fields True."""
        # Act
        ctx = ProvenanceFormatContext()

        # Assert
        self.assertTrue(ctx.show_paths)
        self.assertTrue(ctx.show_values)
        self.assertTrue(ctx.show_files)
        self.assertTrue(ctx.show_lines)
        self.assertTrue(ctx.show_source_type)
        self.assertTrue(ctx.show_chain)
        self.assertTrue(ctx.show_overrides)
        self.assertTrue(ctx.show_targets)

    def test_ProvenanceFormatContext__DefaultInit__IndentSizeIsTwo(self) -> None:
        """Test that default indent size is 2."""
        # Act
        ctx = ProvenanceFormatContext()

        # Assert
        self.assertEqual(2, ctx.indent_size)

    def test_ProvenanceFormatContext__DefaultInit__FiltersAreEmptyLists(self) -> None:
        """Test that default filters are empty lists."""
        # Act
        ctx = ProvenanceFormatContext()

        # Assert
        self.assertEqual([], ctx.path_filters)
        self.assertEqual([], ctx.file_filters)


class ProvenanceFormatContextCustomValuesTests(TestCase):
    """Tests for ProvenanceFormatContext with custom values."""

    def test_ProvenanceFormatContext__CustomBoolValues__StoresCorrectly(self) -> None:
        """Test that custom boolean values are stored."""
        # Act
        ctx = ProvenanceFormatContext(
            show_paths=False,
            show_values=False,
            show_files=False,
            show_lines=False,
            show_source_type=False,
            show_chain=False,
            show_overrides=False,
        )

        # Assert
        self.assertFalse(ctx.show_paths)
        self.assertFalse(ctx.show_values)
        self.assertFalse(ctx.show_files)
        self.assertFalse(ctx.show_lines)
        self.assertFalse(ctx.show_source_type)
        self.assertFalse(ctx.show_chain)
        self.assertFalse(ctx.show_overrides)

    def test_ProvenanceFormatContext__CustomIndentSize__StoresCorrectly(self) -> None:
        """Test that custom indent size is stored."""
        # Act
        ctx = ProvenanceFormatContext(indent_size=4)

        # Assert
        self.assertEqual(4, ctx.indent_size)

    def test_ProvenanceFormatContext__ZeroIndentSize__StoredAsIs(self) -> None:
        """Test that zero indent size is stored without modification."""
        # Act
        ctx = ProvenanceFormatContext(indent_size=0)

        # Assert
        self.assertEqual(0, ctx.indent_size)

    def test_ProvenanceFormatContext__NegativeIndentSize__StoredAsIs(self) -> None:
        """Test that negative indent size is stored without validation."""
        # Act
        ctx = ProvenanceFormatContext(indent_size=-1)

        # Assert
        self.assertEqual(-1, ctx.indent_size)

    def test_ProvenanceFormatContext__CustomFilters__StoresCorrectly(self) -> None:
        """Test that custom filter lists are stored."""
        # Arrange
        path_filters = ["/model.*", "/data.*"]
        file_filters = ["*.yaml", "*.json"]

        # Act
        ctx = ProvenanceFormatContext(path_filters=path_filters, file_filters=file_filters)

        # Assert
        self.assertEqual(path_filters, ctx.path_filters)
        self.assertEqual(file_filters, ctx.file_filters)


class ProvenanceFormatContextIndependenceTests(TestCase):
    """Tests to verify ProvenanceFormatContext instances are independent."""

    def test_ProvenanceFormatContext__MultipleInstances__ListsAreIndependent(self) -> None:
        """Test that filter lists are not shared between instances."""
        # Arrange
        ctx1 = ProvenanceFormatContext()
        ctx2 = ProvenanceFormatContext()

        # Act
        ctx1.path_filters.append("/test")

        # Assert
        self.assertEqual(["/test"], ctx1.path_filters)
        self.assertEqual([], ctx2.path_filters)


class ProvenanceLayoutConcreteImplementation(ProvenanceLayout):
    """Concrete implementation for testing the abstract base class."""

    def format_provenance(self, provenance, ctx):
        return "formatted provenance"

    def format_entry(self, entry, path, ctx):
        return f"{path}: {entry.file}:{entry.line}"


class ProvenanceLayoutDefaultContextTests(TestCase):
    """Tests for ProvenanceLayout.get_default_context()."""

    def test_getDefaultContext__BaseImplementation__ReturnsDefaultContext(self) -> None:
        """Test that base implementation returns default ProvenanceFormatContext."""
        # Arrange
        layout = ProvenanceLayoutConcreteImplementation()

        # Act
        ctx = layout.get_default_context()

        # Assert
        self.assertIsInstance(ctx, ProvenanceFormatContext)
        self.assertTrue(ctx.show_paths)
        self.assertTrue(ctx.show_values)


class ProvenanceLayoutFormatPathTests(TestCase):
    """Tests for ProvenanceLayout.format_path()."""

    def test_formatPath__SimpleString__ReturnsUnchanged(self) -> None:
        """Test that format_path returns the path unchanged."""
        # Arrange
        layout = ProvenanceLayoutConcreteImplementation()
        ctx = ProvenanceFormatContext()

        # Act
        result = layout.format_path("/model.lr", ctx)

        # Assert
        self.assertEqual("/model.lr", result)

    def test_formatPath__EmptyString__ReturnsEmpty(self) -> None:
        """Test that format_path handles empty string."""
        # Arrange
        layout = ProvenanceLayoutConcreteImplementation()
        ctx = ProvenanceFormatContext()

        # Act
        result = layout.format_path("", ctx)

        # Assert
        self.assertEqual("", result)

    def test_formatPath__PathWithSpecialChars__ReturnsUnchanged(self) -> None:
        """Test that format_path handles special characters."""
        # Arrange
        layout = ProvenanceLayoutConcreteImplementation()
        ctx = ProvenanceFormatContext()

        # Act
        result = layout.format_path("/model[0].layers", ctx)

        # Assert
        self.assertEqual("/model[0].layers", result)


class ProvenanceLayoutFormatValueTests(TestCase):
    """Tests for ProvenanceLayout.format_value()."""

    def test_formatValue__None__ReturnsNull(self) -> None:
        """Test that None is formatted as 'null'."""
        # Arrange
        layout = ProvenanceLayoutConcreteImplementation()
        ctx = ProvenanceFormatContext()

        # Act
        result = layout.format_value(None, ctx)

        # Assert
        self.assertEqual("null", result)

    def test_formatValue__BoolTrue__ReturnsTrue(self) -> None:
        """Test that True is formatted as 'true'."""
        # Arrange
        layout = ProvenanceLayoutConcreteImplementation()
        ctx = ProvenanceFormatContext()

        # Act
        result = layout.format_value(True, ctx)

        # Assert
        self.assertEqual("true", result)

    def test_formatValue__BoolFalse__ReturnsFalse(self) -> None:
        """Test that False is formatted as 'false'."""
        # Arrange
        layout = ProvenanceLayoutConcreteImplementation()
        ctx = ProvenanceFormatContext()

        # Act
        result = layout.format_value(False, ctx)

        # Assert
        self.assertEqual("false", result)

    def test_formatValue__String__ReturnsRepr(self) -> None:
        """Test that strings are formatted with repr()."""
        # Arrange
        layout = ProvenanceLayoutConcreteImplementation()
        ctx = ProvenanceFormatContext()

        # Act
        result = layout.format_value("hello", ctx)

        # Assert
        self.assertEqual("'hello'", result)

    def test_formatValue__EmptyString__ReturnsEmptyRepr(self) -> None:
        """Test that empty string is formatted with repr()."""
        # Arrange
        layout = ProvenanceLayoutConcreteImplementation()
        ctx = ProvenanceFormatContext()

        # Act
        result = layout.format_value("", ctx)

        # Assert
        self.assertEqual("''", result)

    def test_formatValue__Integer__ReturnsStr(self) -> None:
        """Test that integers are formatted with str()."""
        # Arrange
        layout = ProvenanceLayoutConcreteImplementation()
        ctx = ProvenanceFormatContext()

        # Act
        result = layout.format_value(42, ctx)

        # Assert
        self.assertEqual("42", result)

    def test_formatValue__Float__ReturnsStr(self) -> None:
        """Test that floats are formatted with str()."""
        # Arrange
        layout = ProvenanceLayoutConcreteImplementation()
        ctx = ProvenanceFormatContext()

        # Act
        result = layout.format_value(3.14, ctx)

        # Assert
        self.assertEqual("3.14", result)

    def test_formatValue__List__ReturnsStr(self) -> None:
        """Test that lists are formatted with str()."""
        # Arrange
        layout = ProvenanceLayoutConcreteImplementation()
        ctx = ProvenanceFormatContext()

        # Act
        result = layout.format_value([1, 2, 3], ctx)

        # Assert
        self.assertEqual("[1, 2, 3]", result)

    def test_formatValue__Dict__ReturnsStr(self) -> None:
        """Test that dicts are formatted with str()."""
        # Arrange
        layout = ProvenanceLayoutConcreteImplementation()
        ctx = ProvenanceFormatContext()

        # Act
        result = layout.format_value({"a": 1}, ctx)

        # Assert
        self.assertEqual("{'a': 1}", result)


class ProvenanceLayoutFormatLocationTests(TestCase):
    """Tests for ProvenanceLayout.format_location()."""

    def test_formatLocation__BothFilesAndLines__CombinesCorrectly(self) -> None:
        """Test that file and line are combined when both shown."""
        # Arrange
        layout = ProvenanceLayoutConcreteImplementation()
        ctx = ProvenanceFormatContext(show_files=True, show_lines=True)

        # Act
        result = layout.format_location("config.yaml", 42, ctx)

        # Assert
        self.assertEqual("config.yaml:42", result)

    def test_formatLocation__ShowFilesOnly__ReturnsFile(self) -> None:
        """Test that only file is shown when show_lines is False."""
        # Arrange
        layout = ProvenanceLayoutConcreteImplementation()
        ctx = ProvenanceFormatContext(show_files=True, show_lines=False)

        # Act
        result = layout.format_location("config.yaml", 42, ctx)

        # Assert
        self.assertEqual("config.yaml", result)

    def test_formatLocation__ShowLinesOnly__ReturnsLine(self) -> None:
        """Test that only line is shown when show_files is False."""
        # Arrange
        layout = ProvenanceLayoutConcreteImplementation()
        ctx = ProvenanceFormatContext(show_files=False, show_lines=True)

        # Act
        result = layout.format_location("config.yaml", 42, ctx)

        # Assert
        self.assertEqual("42", result)

    def test_formatLocation__NeitherShown__ReturnsEmpty(self) -> None:
        """Test that empty string is returned when both are hidden."""
        # Arrange
        layout = ProvenanceLayoutConcreteImplementation()
        ctx = ProvenanceFormatContext(show_files=False, show_lines=False)

        # Act
        result = layout.format_location("config.yaml", 42, ctx)

        # Assert
        self.assertEqual("", result)

    def test_formatLocation__LineZero__IncludesZero(self) -> None:
        """Test that line 0 is included in output."""
        # Arrange
        layout = ProvenanceLayoutConcreteImplementation()
        ctx = ProvenanceFormatContext(show_files=True, show_lines=True)

        # Act
        result = layout.format_location("config.yaml", 0, ctx)

        # Assert
        self.assertEqual("config.yaml:0", result)


class ProvenanceLayoutFormatSourceTypeTests(TestCase):
    """Tests for ProvenanceLayout.format_source_type()."""

    def test_formatSourceType__Cli__ReturnsCLI(self) -> None:
        """Test that 'cli' source type is formatted as 'CLI'."""
        # Arrange
        layout = ProvenanceLayoutConcreteImplementation()
        ctx = ProvenanceFormatContext()

        # Act
        result = layout.format_source_type("cli", ctx)

        # Assert
        self.assertEqual("CLI", result)

    def test_formatSourceType__Env__ReturnsEnv(self) -> None:
        """Test that 'env' source type is formatted as 'env'."""
        # Arrange
        layout = ProvenanceLayoutConcreteImplementation()
        ctx = ProvenanceFormatContext()

        # Act
        result = layout.format_source_type("env", ctx)

        # Assert
        self.assertEqual("env", result)

    def test_formatSourceType__Programmatic__ReturnsProgrammatic(self) -> None:
        """Test that 'programmatic' source type is formatted as 'programmatic'."""
        # Arrange
        layout = ProvenanceLayoutConcreteImplementation()
        ctx = ProvenanceFormatContext()

        # Act
        result = layout.format_source_type("programmatic", ctx)

        # Assert
        self.assertEqual("programmatic", result)

    def test_formatSourceType__File__ReturnsEmpty(self) -> None:
        """Test that 'file' source type returns empty string."""
        # Arrange
        layout = ProvenanceLayoutConcreteImplementation()
        ctx = ProvenanceFormatContext()

        # Act
        result = layout.format_source_type("file", ctx)

        # Assert
        self.assertEqual("", result)

    def test_formatSourceType__UnknownType__ReturnsEmpty(self) -> None:
        """Test that unknown source type returns empty string."""
        # Arrange
        layout = ProvenanceLayoutConcreteImplementation()
        ctx = ProvenanceFormatContext()

        # Act
        result = layout.format_source_type("unknown", ctx)

        # Assert
        self.assertEqual("", result)


class ProvenanceLayoutFormatChainTests(TestCase):
    """Tests for ProvenanceLayout.format_chain()."""

    def test_formatChain__SimpleNode__ReturnsStringRepresentation(self) -> None:
        """Test that format_chain returns string representation of node."""
        # Arrange
        layout = ProvenanceLayoutConcreteImplementation()
        ctx = ProvenanceFormatContext()
        node = ProvenanceNode(source_type="file", file="test.yaml", line=5, value=42)

        # Act
        result = layout.format_chain(node, 0, ctx)

        # Assert
        self.assertIn("file", result)


class ProvenanceLayoutFormatTreeTests(TestCase):
    """Tests for ProvenanceLayout.format_tree()."""

    def test_formatTree__SingleNode__ReturnsFormattedLine(self) -> None:
        """Test that single node is formatted as single line."""
        # Arrange
        layout = ProvenanceLayoutConcreteImplementation()
        ctx = ProvenanceFormatContext()
        node = ProvenanceNode(source_type="file", value=42)

        # Act
        result = layout.format_tree(node, ctx)

        # Assert
        self.assertIsInstance(result, str)
        # Should be a single line (no newlines except at end potentially)
        self.assertIn("file", result)

    def test_formatTree__WithChildren__RecursesCorrectly(self) -> None:
        """Test that tree with children formats all nodes."""
        # Arrange
        layout = ProvenanceLayoutConcreteImplementation()
        ctx = ProvenanceFormatContext()
        child1 = ProvenanceNode(source_type="file", value=1)
        child2 = ProvenanceNode(source_type="file", value=2)
        parent = ProvenanceNode(
            source_type="operator", operator="+", children=[child1, child2]
        )

        # Act
        result = layout.format_tree(parent, ctx)

        # Assert
        # Should have multiple lines (one per node)
        lines = result.split("\n")
        self.assertEqual(3, len(lines))  # parent + 2 children

    def test_formatTree__DeeplyNested__FormatsAllLevels(self) -> None:
        """Test that deeply nested tree formats all levels."""
        # Arrange
        layout = ProvenanceLayoutConcreteImplementation()
        ctx = ProvenanceFormatContext()
        grandchild = ProvenanceNode(source_type="file", value=1)
        child = ProvenanceNode(source_type="operator", operator="*", children=[grandchild])
        parent = ProvenanceNode(source_type="operator", operator="+", children=[child])

        # Act
        result = layout.format_tree(parent, ctx)

        # Assert
        lines = result.split("\n")
        self.assertEqual(3, len(lines))


class ProvenanceLayoutFormatOverrideTests(TestCase):
    """Tests for ProvenanceLayout.format_override()."""

    def test_formatOverride__SimpleOverrode__FormatsWithPrefix(self) -> None:
        """Test that override info is formatted with 'Overrode:' prefix."""
        # Arrange
        layout = ProvenanceLayoutConcreteImplementation()
        ctx = ProvenanceFormatContext()

        # Act
        result = layout.format_override("base.yaml:10", ctx)

        # Assert
        self.assertEqual("Overrode: base.yaml:10", result)

    def test_formatOverride__EmptyString__FormatsWithPrefix(self) -> None:
        """Test that empty override string still gets prefix."""
        # Arrange
        layout = ProvenanceLayoutConcreteImplementation()
        ctx = ProvenanceFormatContext()

        # Act
        result = layout.format_override("", ctx)

        # Assert
        self.assertEqual("Overrode: ", result)


class ProvenanceLayoutJoinEntriesTests(TestCase):
    """Tests for ProvenanceLayout.join_entries()."""

    def test_joinEntries__MultipleEntries__JoinsWithNewlines(self) -> None:
        """Test that multiple entries are joined with newlines."""
        # Arrange
        layout = ProvenanceLayoutConcreteImplementation()
        ctx = ProvenanceFormatContext()
        entries = ["entry1", "entry2", "entry3"]

        # Act
        result = layout.join_entries(entries, ctx)

        # Assert
        self.assertEqual("entry1\nentry2\nentry3", result)

    def test_joinEntries__EmptyList__ReturnsEmpty(self) -> None:
        """Test that empty list returns empty string."""
        # Arrange
        layout = ProvenanceLayoutConcreteImplementation()
        ctx = ProvenanceFormatContext()

        # Act
        result = layout.join_entries([], ctx)

        # Assert
        self.assertEqual("", result)

    def test_joinEntries__SingleEntry__ReturnsEntry(self) -> None:
        """Test that single entry is returned without modification."""
        # Arrange
        layout = ProvenanceLayoutConcreteImplementation()
        ctx = ProvenanceFormatContext()

        # Act
        result = layout.join_entries(["only entry"], ctx)

        # Assert
        self.assertEqual("only entry", result)


class ProvenanceLayoutIndentTests(TestCase):
    """Tests for ProvenanceLayout.indent()."""

    def test_indent__ZeroDepth__NoIndent(self) -> None:
        """Test that depth 0 adds no indentation."""
        # Arrange
        layout = ProvenanceLayoutConcreteImplementation()
        ctx = ProvenanceFormatContext(indent_size=2)

        # Act
        result = layout.indent("text", 0, ctx)

        # Assert
        self.assertEqual("text", result)

    def test_indent__PositiveDepth__AddsSpaces(self) -> None:
        """Test that positive depth adds correct number of spaces."""
        # Arrange
        layout = ProvenanceLayoutConcreteImplementation()
        ctx = ProvenanceFormatContext(indent_size=2)

        # Act
        result = layout.indent("text", 2, ctx)

        # Assert
        self.assertEqual("    text", result)  # 2 * 2 = 4 spaces

    def test_indent__LargeIndentSize__AddsCorrectSpaces(self) -> None:
        """Test that large indent size works correctly."""
        # Arrange
        layout = ProvenanceLayoutConcreteImplementation()
        ctx = ProvenanceFormatContext(indent_size=4)

        # Act
        result = layout.indent("text", 3, ctx)

        # Assert
        self.assertEqual("            text", result)  # 4 * 3 = 12 spaces

    def test_indent__NegativeDepth__StillWorks(self) -> None:
        """Test that negative depth doesn't crash (returns text as-is)."""
        # Arrange
        layout = ProvenanceLayoutConcreteImplementation()
        ctx = ProvenanceFormatContext(indent_size=2)

        # Act
        result = layout.indent("text", -1, ctx)

        # Assert
        # Negative depth * indent_size = negative, so empty prefix
        self.assertEqual("text", result)

    def test_indent__EmptyText__ReturnsOnlySpaces(self) -> None:
        """Test that empty text with depth returns only spaces."""
        # Arrange
        layout = ProvenanceLayoutConcreteImplementation()
        ctx = ProvenanceFormatContext(indent_size=2)

        # Act
        result = layout.indent("", 2, ctx)

        # Assert
        self.assertEqual("    ", result)
