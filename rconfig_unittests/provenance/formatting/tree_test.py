"""Tests for TreeLayout implementation."""

from unittest import TestCase

from rconfig.provenance import (
    InstanceRef,
    Provenance,
    ProvenanceBuilder,
    ProvenanceEntry,
    ProvenanceFormatContext,
    TreeLayout,
)
from rconfig.interpolation.evaluator import InterpolationSource


class TreeLayoutDefaultContextTests(TestCase):
    """Tests for TreeLayout.get_default_context()."""

    def test_getDefaultContext__ReturnsFullContext__AllEnabled(self) -> None:
        """Test that TreeLayout default context has all options enabled."""
        # Arrange
        layout = TreeLayout()

        # Act
        ctx = layout.get_default_context()

        # Assert
        self.assertTrue(ctx.show_paths)
        self.assertTrue(ctx.show_values)
        self.assertTrue(ctx.show_files)
        self.assertTrue(ctx.show_lines)
        self.assertTrue(ctx.show_source_type)
        self.assertTrue(ctx.show_chain)
        self.assertTrue(ctx.show_overrides)
        self.assertTrue(ctx.show_targets)

    def test_getDefaultContext__IndentSizeIsTwo(self) -> None:
        """Test that default indent size is 2."""
        # Arrange
        layout = TreeLayout()

        # Act
        ctx = layout.get_default_context()

        # Assert
        self.assertEqual(2, ctx.indent_size)


class TreeLayoutFilterTests(TestCase):
    """Tests for TreeLayout filter matching."""

    def setUp(self) -> None:
        self.layout = TreeLayout()

    def test_matchesFilters__NoFilters__MatchesEverything(self) -> None:
        """Test that entries match when no filters are set."""
        # Arrange
        entry = ProvenanceEntry(file="config.yaml", line=5, value=42)
        ctx = ProvenanceFormatContext()

        # Act
        result = self.layout._matches_filters("model.lr", entry, ctx)

        # Assert
        self.assertTrue(result)

    def test_matchesFilters__PathFilterMatch__ReturnsTrue(self) -> None:
        """Test that matching path filter returns True."""
        # Arrange
        entry = ProvenanceEntry(file="config.yaml", line=5, value=42)
        ctx = ProvenanceFormatContext(path_filters=["/model.*"])

        # Act
        result = self.layout._matches_filters("model.lr", entry, ctx)

        # Assert
        self.assertTrue(result)

    def test_matchesFilters__PathFilterNoMatch__ReturnsFalse(self) -> None:
        """Test that non-matching path filter returns False."""
        # Arrange
        entry = ProvenanceEntry(file="config.yaml", line=5, value=42)
        ctx = ProvenanceFormatContext(path_filters=["/data.*"])

        # Act
        result = self.layout._matches_filters("model.lr", entry, ctx)

        # Assert
        self.assertFalse(result)

    def test_matchesFilters__FileFilterMatch__ReturnsTrue(self) -> None:
        """Test that matching file filter returns True."""
        # Arrange
        entry = ProvenanceEntry(file="config.yaml", line=5, value=42)
        ctx = ProvenanceFormatContext(file_filters=["*.yaml"])

        # Act
        result = self.layout._matches_filters("model.lr", entry, ctx)

        # Assert
        self.assertTrue(result)

    def test_matchesFilters__FileFilterNoMatch__ReturnsFalse(self) -> None:
        """Test that non-matching file filter returns False."""
        # Arrange
        entry = ProvenanceEntry(file="config.yaml", line=5, value=42)
        ctx = ProvenanceFormatContext(file_filters=["*.json"])

        # Act
        result = self.layout._matches_filters("model.lr", entry, ctx)

        # Assert
        self.assertFalse(result)

    def test_matchesFilters__BothFilters__MustMatchBoth(self) -> None:
        """Test that both path and file filters must match (AND logic)."""
        # Arrange
        entry = ProvenanceEntry(file="config.yaml", line=5, value=42)
        ctx = ProvenanceFormatContext(path_filters=["/model.*"], file_filters=["*.json"])

        # Act
        result = self.layout._matches_filters("model.lr", entry, ctx)

        # Assert - path matches but file doesn't
        self.assertFalse(result)

    def test_matchesFilters__MultiplePathFilters__ORLogic(self) -> None:
        """Test that multiple path filters use OR logic."""
        # Arrange
        entry = ProvenanceEntry(file="config.yaml", line=5, value=42)
        ctx = ProvenanceFormatContext(path_filters=["/data.*", "/model.*"])

        # Act
        result = self.layout._matches_filters("model.lr", entry, ctx)

        # Assert
        self.assertTrue(result)

    def test_matchesFilters__MultipleFileFilters__ORLogic(self) -> None:
        """Test that multiple file filters use OR logic."""
        # Arrange
        entry = ProvenanceEntry(file="config.yaml", line=5, value=42)
        ctx = ProvenanceFormatContext(file_filters=["*.json", "*.yaml"])

        # Act
        result = self.layout._matches_filters("model.lr", entry, ctx)

        # Assert
        self.assertTrue(result)

    def test_matchesFilters__GlobPatternAsterisk__MatchesWildcard(self) -> None:
        """Test that glob wildcard patterns work correctly."""
        # Arrange
        entry = ProvenanceEntry(file="configs/model/base.yaml", line=5, value=42)
        ctx = ProvenanceFormatContext(file_filters=["configs/model/*.yaml"])

        # Act
        result = self.layout._matches_filters("model.lr", entry, ctx)

        # Assert
        self.assertTrue(result)

    def test_matchesFilters__PathWithLeadingSlash__Matches(self) -> None:
        """Test that path matching works with leading slash."""
        # Arrange
        entry = ProvenanceEntry(file="config.yaml", line=5, value=42)
        ctx = ProvenanceFormatContext(path_filters=["/model.lr"])

        # Act
        result = self.layout._matches_filters("model.lr", entry, ctx)

        # Assert
        self.assertTrue(result)

    def test_matchesFilters__PathWithoutLeadingSlash__Matches(self) -> None:
        """Test that path matching works without leading slash in filter."""
        # Arrange
        entry = ProvenanceEntry(file="config.yaml", line=5, value=42)
        ctx = ProvenanceFormatContext(path_filters=["model.lr"])

        # Act
        result = self.layout._matches_filters("model.lr", entry, ctx)

        # Assert
        self.assertTrue(result)


class TreeLayoutInterpolationTreeTests(TestCase):
    """Tests for TreeLayout interpolation tree formatting."""

    def setUp(self) -> None:
        self.layout = TreeLayout()
        self.ctx = ProvenanceFormatContext()

    def test_formatInterpolationTree__ExpressionWithOperator__FormatsOperator(self) -> None:
        """Test formatting expression with operator shows operator."""
        # Arrange
        source = InterpolationSource(
            kind="expression",
            expression="/a * 2",
            value=10,
            operator="*",
            sources=[
                InterpolationSource(kind="config", expression="/a", value=5, path="a"),
                InterpolationSource(kind="literal", expression="2", value=2),
            ],
        )

        # Act
        lines = self.layout._format_interpolation_tree(source, 0, self.ctx)

        # Assert
        self.assertTrue(any("*" in line for line in lines))

    def test_formatInterpolationTree__ConfigReference__FormatsPath(self) -> None:
        """Test formatting config reference shows the path."""
        # Arrange
        source = InterpolationSource(
            kind="config",
            expression="/model.lr",
            value=0.01,
            path="model.lr",
        )

        # Act
        lines = self.layout._format_interpolation_tree(source, 0, self.ctx)

        # Assert
        self.assertTrue(any("model.lr" in line for line in lines))

    def test_formatInterpolationTree__ConfigReferenceWithValue__ShowsValue(self) -> None:
        """Test formatting config reference shows the value when enabled."""
        # Arrange
        source = InterpolationSource(
            kind="config",
            expression="/model.lr",
            value=0.01,
            path="model.lr",
        )
        ctx = ProvenanceFormatContext(show_values=True)

        # Act
        lines = self.layout._format_interpolation_tree(source, 0, ctx)

        # Assert
        self.assertTrue(any("0.01" in line for line in lines))

    def test_formatInterpolationTree__ConfigReferenceWithLocation__ShowsLocation(self) -> None:
        """Test formatting config reference shows file:line."""
        # Arrange
        source = InterpolationSource(
            kind="config",
            expression="/model.lr",
            value=0.01,
            path="model.lr",
            file="config.yaml",
            line=5,
        )

        # Act
        lines = self.layout._format_interpolation_tree(source, 0, self.ctx)

        # Assert
        self.assertTrue(any("config.yaml" in line for line in lines))
        self.assertTrue(any("5" in line for line in lines))

    def test_formatInterpolationTree__EnvVariable__FormatsEnvVar(self) -> None:
        """Test formatting env reference shows env:VAR_NAME."""
        # Arrange
        source = InterpolationSource(
            kind="env",
            expression="env:DATA_PATH",
            value="/data",
            env_var="DATA_PATH",
        )

        # Act
        lines = self.layout._format_interpolation_tree(source, 0, self.ctx)

        # Assert
        self.assertTrue(any("env:DATA_PATH" in line for line in lines))

    def test_formatInterpolationTree__Literal__FormatsWithMarker(self) -> None:
        """Test formatting literal value shows (literal) marker."""
        # Arrange
        source = InterpolationSource(
            kind="literal",
            expression="42",
            value=42,
        )

        # Act
        lines = self.layout._format_interpolation_tree(source, 0, self.ctx)

        # Assert
        self.assertTrue(any("(literal)" in line for line in lines))

    def test_formatInterpolationTree__NestedExpression__RecursesCorrectly(self) -> None:
        """Test formatting nested expression recurses into children."""
        # Arrange
        source = InterpolationSource(
            kind="expression",
            expression="/a + /b",
            value=15,
            operator="+",
            sources=[
                InterpolationSource(kind="config", expression="/a", value=5, path="a"),
                InterpolationSource(kind="config", expression="/b", value=10, path="b"),
            ],
        )

        # Act
        lines = self.layout._format_interpolation_tree(source, 0, self.ctx)

        # Assert - should have lines for operator and both children
        self.assertGreaterEqual(len(lines), 3)


class TreeLayoutChildSourceTests(TestCase):
    """Tests for TreeLayout child source formatting."""

    def setUp(self) -> None:
        self.layout = TreeLayout()
        self.ctx = ProvenanceFormatContext()

    def test_formatChildSource__IsLast__UsesLastConnector(self) -> None:
        """Test that last child uses +-- connector."""
        # Arrange
        source = InterpolationSource(
            kind="literal",
            expression="42",
            value=42,
        )

        # Act
        lines = self.layout._format_child_source(source, 0, is_last=True, ctx=self.ctx)

        # Assert
        self.assertTrue(any("+--" in line for line in lines))

    def test_formatChildSource__NotLast__UsesContinueConnector(self) -> None:
        """Test that non-last child uses |-- connector."""
        # Arrange
        source = InterpolationSource(
            kind="literal",
            expression="42",
            value=42,
        )

        # Act
        lines = self.layout._format_child_source(source, 0, is_last=False, ctx=self.ctx)

        # Assert
        self.assertTrue(any("|--" in line for line in lines))

    def test_formatChildSource__NestedExpression__RecursesWithChildren(self) -> None:
        """Test nested expressions recurse correctly with children."""
        # Arrange
        source = InterpolationSource(
            kind="expression",
            expression="/a * 2",
            value=10,
            operator="*",
            sources=[
                InterpolationSource(kind="config", expression="/a", value=5, path="a"),
                InterpolationSource(kind="literal", expression="2", value=2),
            ],
        )

        # Act
        lines = self.layout._format_child_source(source, 0, is_last=True, ctx=self.ctx)

        # Assert - should have lines for operator and its children
        self.assertGreaterEqual(len(lines), 3)

    def test_formatChildSource__ConfigWithLocation__ShowsLocationLine(self) -> None:
        """Test that config reference with location shows location on separate line."""
        # Arrange
        source = InterpolationSource(
            kind="config",
            expression="/model.lr",
            value=0.01,
            path="model.lr",
            file="config.yaml",
            line=5,
        )

        # Act
        lines = self.layout._format_child_source(source, 0, is_last=True, ctx=self.ctx)

        # Assert - should have two lines: ref and location
        self.assertEqual(2, len(lines))
        self.assertIn("config.yaml:5", lines[1])

    def test_formatChildSource__EnvSource__ShowsEnvVar(self) -> None:
        """Test that env source shows env:VAR_NAME format."""
        # Arrange
        source = InterpolationSource(
            kind="env",
            expression="env:PATH",
            value="/usr/bin",
            env_var="PATH",
        )

        # Act
        lines = self.layout._format_child_source(source, 0, is_last=True, ctx=self.ctx)

        # Assert
        self.assertTrue(any("env:PATH" in line for line in lines))

    def test_formatChildSource__LiteralSource__ShowsLiteralMarker(self) -> None:
        """Test that literal source shows (literal) marker."""
        # Arrange
        source = InterpolationSource(
            kind="literal",
            expression="100",
            value=100,
        )

        # Act
        lines = self.layout._format_child_source(source, 0, is_last=True, ctx=self.ctx)

        # Assert
        self.assertTrue(any("(literal)" in line for line in lines))


class TreeLayoutFormatValueTests(TestCase):
    """Tests for TreeLayout.format_value()."""

    def setUp(self) -> None:
        self.layout = TreeLayout()
        self.ctx = ProvenanceFormatContext()

    def test_formatValue__LongList__Truncates(self) -> None:
        """Test that long lists are truncated with ellipsis."""
        # Arrange
        long_list = list(range(100))  # A list that stringifies to > 50 chars

        # Act
        result = self.layout.format_value(long_list, self.ctx)

        # Assert
        if len(str(long_list)) > 50:
            self.assertIn("...", result)
            self.assertLessEqual(len(result), 50)

    def test_formatValue__LongDict__Truncates(self) -> None:
        """Test that long dicts are truncated with ellipsis."""
        # Arrange
        long_dict = {f"key{i}": i for i in range(100)}

        # Act
        result = self.layout.format_value(long_dict, self.ctx)

        # Assert
        if len(str(long_dict)) > 50:
            self.assertIn("...", result)

    def test_formatValue__ShortList__NoTruncation(self) -> None:
        """Test that short lists are not truncated."""
        # Arrange
        short_list = [1, 2, 3]

        # Act
        result = self.layout.format_value(short_list, self.ctx)

        # Assert
        self.assertEqual("[1, 2, 3]", result)

    def test_formatValue__ExactlyFiftyChars__NoTruncation(self) -> None:
        """Test that exactly 50 char strings are not truncated."""
        # Arrange - string that stringifies to exactly 50 chars
        value = "x" * 48  # repr adds quotes making it 50 total

        # Act
        result = self.layout.format_value(value, self.ctx)

        # Assert
        self.assertNotIn("...", result)

    def test_formatValue__FiftyOneChars__Truncates(self) -> None:
        """Test that list/dict over 50 chars are truncated."""
        # Arrange - a long list
        long_list = list(range(50))  # Will stringify to much more than 50 chars

        # Act
        result = self.layout.format_value(long_list, self.ctx)

        # Assert
        self.assertIn("...", result)


class TreeLayoutFormatEntryTests(TestCase):
    """Tests for TreeLayout.format_entry()."""

    def setUp(self) -> None:
        self.layout = TreeLayout()

    def test_formatEntry__ShowPathsTrue__IncludesPath(self) -> None:
        """Test that path is included when show_paths is True."""
        # Arrange
        entry = ProvenanceEntry(file="config.yaml", line=5, value=42)
        ctx = ProvenanceFormatContext(show_paths=True)

        # Act
        result = self.layout.format_entry(entry, "model.lr", ctx)

        # Assert
        self.assertIn("/model.lr", result)

    def test_formatEntry__ShowPathsFalse__OmitsPath(self) -> None:
        """Test that path is omitted when show_paths is False."""
        # Arrange
        entry = ProvenanceEntry(file="config.yaml", line=5, value=42)
        ctx = ProvenanceFormatContext(show_paths=False)

        # Act
        result = self.layout.format_entry(entry, "model.lr", ctx)

        # Assert
        self.assertNotIn("/model.lr", result)

    def test_formatEntry__ShowValuesTrue__IncludesValue(self) -> None:
        """Test that value is included when show_values is True."""
        # Arrange
        entry = ProvenanceEntry(file="config.yaml", line=5, value=42)
        ctx = ProvenanceFormatContext(show_values=True)

        # Act
        result = self.layout.format_entry(entry, "model.lr", ctx)

        # Assert
        self.assertIn("42", result)

    def test_formatEntry__ValueIsNone__OmitsValuePart(self) -> None:
        """Test that None value doesn't add empty '= null' part."""
        # Arrange
        entry = ProvenanceEntry(file="config.yaml", line=5, value=None)
        ctx = ProvenanceFormatContext(show_values=True)

        # Act
        result = self.layout.format_entry(entry, "model.lr", ctx)

        # Assert - should still have path, but not " = null"
        self.assertIn("/model.lr", result)
        self.assertNotIn("= null", result)

    def test_formatEntry__CliSourceWithArg__ShowsCliAndArg(self) -> None:
        """Test that CLI source shows CLI: and the argument."""
        # Arrange
        entry = ProvenanceEntry(
            file="<override>",
            line=0,
            value=0.01,
            source_type="cli",
            cli_arg="--model.lr=0.01",
        )
        ctx = ProvenanceFormatContext(show_source_type=True)

        # Act
        result = self.layout.format_entry(entry, "model.lr", ctx)

        # Assert
        self.assertIn("CLI", result)
        self.assertIn("--model.lr=0.01", result)

    def test_formatEntry__EnvSourceWithVar__ShowsEnvAndVar(self) -> None:
        """Test that env source shows env: and the variable name."""
        # Arrange
        entry = ProvenanceEntry(
            file="<override>",
            line=0,
            value="/data",
            source_type="env",
            env_var="DATA_PATH",
        )
        ctx = ProvenanceFormatContext(show_source_type=True)

        # Act
        result = self.layout.format_entry(entry, "data.path", ctx)

        # Assert
        self.assertIn("env", result)
        self.assertIn("DATA_PATH", result)

    def test_formatEntry__FileSourceWithLocation__ShowsLocation(self) -> None:
        """Test that file source shows file:line location."""
        # Arrange
        entry = ProvenanceEntry(file="config.yaml", line=5, value=42)
        ctx = ProvenanceFormatContext(show_files=True, show_lines=True)

        # Act
        result = self.layout.format_entry(entry, "model.lr", ctx)

        # Assert
        self.assertIn("config.yaml:5", result)

    def test_formatEntry__WithInterpolation__ShowsInterpolationSection(self) -> None:
        """Test that entry with interpolation shows Interpolation: section."""
        # Arrange
        entry = ProvenanceEntry(
            file="config.yaml",
            line=5,
            value=0.02,
            interpolation=InterpolationSource(
                kind="expression",
                expression="/defaults.lr * 2",
                value=0.02,
                operator="*",
                sources=[
                    InterpolationSource(kind="config", expression="/defaults.lr", value=0.01, path="defaults.lr"),
                    InterpolationSource(kind="literal", expression="2", value=2),
                ],
            ),
        )
        ctx = ProvenanceFormatContext(show_chain=True)

        # Act
        result = self.layout.format_entry(entry, "model.lr", ctx)

        # Assert
        self.assertIn("Interpolation:", result)
        self.assertIn("/defaults.lr * 2", result)

    def test_formatEntry__WithInstanceChain__ShowsInstances(self) -> None:
        """Test that entry with instance chain shows Instance: lines."""
        # Arrange
        entry = ProvenanceEntry(
            file="app.yaml",
            line=10,
            value={"host": "localhost"},
            instance=[
                InstanceRef(path="/shared.database", file="shared.yaml", line=5),
            ],
        )
        ctx = ProvenanceFormatContext(show_chain=True)

        # Act
        result = self.layout.format_entry(entry, "service.db", ctx)

        # Assert
        self.assertIn("Instance:", result)
        self.assertIn("/shared.database", result)
        self.assertIn("shared.yaml:5", result)

    def test_formatEntry__WithOverrode__ShowsOverrideSection(self) -> None:
        """Test that entry with overrode shows Overrode: line."""
        # Arrange
        entry = ProvenanceEntry(
            file="override.yaml",
            line=5,
            value=42,
            overrode="base.yaml:10",
        )
        ctx = ProvenanceFormatContext(show_overrides=True)

        # Act
        result = self.layout.format_entry(entry, "model.lr", ctx)

        # Assert
        self.assertIn("Overrode:", result)
        self.assertIn("base.yaml:10", result)

    def test_formatEntry__HideChain__OmitsInterpolationAndInstance(self) -> None:
        """Test that show_chain=False hides interpolation and instance info."""
        # Arrange
        entry = ProvenanceEntry(
            file="config.yaml",
            line=5,
            value=0.02,
            interpolation=InterpolationSource(
                kind="config",
                expression="/defaults.lr",
                value=0.01,
                path="defaults.lr",
            ),
            instance=[InstanceRef(path="/shared.db", file="shared.yaml", line=1)],
        )
        ctx = ProvenanceFormatContext(show_chain=False)

        # Act
        result = self.layout.format_entry(entry, "model.lr", ctx)

        # Assert
        self.assertNotIn("Interpolation:", result)
        self.assertNotIn("Instance:", result)

    def test_formatEntry__HideOverrides__OmitsOverrideSection(self) -> None:
        """Test that show_overrides=False hides override info."""
        # Arrange
        entry = ProvenanceEntry(
            file="override.yaml",
            line=5,
            value=42,
            overrode="base.yaml:10",
        )
        ctx = ProvenanceFormatContext(show_overrides=False)

        # Act
        result = self.layout.format_entry(entry, "model.lr", ctx)

        # Assert
        self.assertNotIn("Overrode:", result)

    def test_formatEntry__AllHidden__ReturnsMinimal(self) -> None:
        """Test that hiding all options returns minimal output."""
        # Arrange
        entry = ProvenanceEntry(file="config.yaml", line=5, value=42)
        ctx = ProvenanceFormatContext(
            show_paths=False,
            show_values=False,
            show_files=False,
            show_lines=False,
            show_source_type=False,
            show_chain=False,
            show_overrides=False,
        )

        # Act
        result = self.layout.format_entry(entry, "model.lr", ctx)

        # Assert
        self.assertEqual("", result)


class TreeLayoutFormatProvenanceTests(TestCase):
    """Tests for TreeLayout.format_provenance()."""

    def setUp(self) -> None:
        self.layout = TreeLayout()

    def test_formatProvenance__EmptyProvenance__ReturnsEmpty(self) -> None:
        """Test that empty provenance returns empty string."""
        # Arrange
        provenance = Provenance()
        ctx = ProvenanceFormatContext()

        # Act
        result = self.layout.format_provenance(provenance, ctx)

        # Assert
        self.assertEqual("", result)

    def test_formatProvenance__SingleEntry__FormatsCorrectly(self) -> None:
        """Test single entry is formatted correctly."""
        # Arrange
        builder = ProvenanceBuilder()
        builder.add("model.lr", file="config.yaml", line=5, value=0.01)
        provenance = builder.build()
        ctx = ProvenanceFormatContext()

        # Act
        result = self.layout.format_provenance(provenance, ctx)

        # Assert
        self.assertIn("/model.lr", result)
        self.assertIn("0.01", result)
        self.assertIn("config.yaml:5", result)

    def test_formatProvenance__MultipleEntries__SeparatesWithBlankLine(self) -> None:
        """Test multiple entries are separated by blank lines."""
        # Arrange
        builder = ProvenanceBuilder()
        builder.add("a", file="a.yaml", line=1, value=1)
        builder.add("b", file="b.yaml", line=2, value=2)
        provenance = builder.build()
        ctx = ProvenanceFormatContext()

        # Act
        result = self.layout.format_provenance(provenance, ctx)

        # Assert
        self.assertIn("\n\n", result)

    def test_formatProvenance__FilterApplied__FiltersEntries(self) -> None:
        """Test that path filter is applied to entries."""
        # Arrange
        builder = ProvenanceBuilder()
        builder.add("model.lr", file="config.yaml", line=1, value=0.01)
        builder.add("data.path", file="config.yaml", line=2, value="/data")
        provenance = builder.build()
        ctx = ProvenanceFormatContext(path_filters=["/model.*"])

        # Act
        result = self.layout.format_provenance(provenance, ctx)

        # Assert
        self.assertIn("/model.lr", result)
        self.assertNotIn("/data.path", result)


class TreeLayoutJoinEntriesTests(TestCase):
    """Tests for TreeLayout.join_entries()."""

    def test_joinEntries__MultipleEntries__JoinsWithDoubleNewlines(self) -> None:
        """Test that entries are joined with double newlines."""
        # Arrange
        layout = TreeLayout()
        ctx = ProvenanceFormatContext()
        entries = ["entry1", "entry2", "entry3"]

        # Act
        result = layout.join_entries(entries, ctx)

        # Assert
        self.assertEqual("entry1\n\nentry2\n\nentry3", result)

    def test_joinEntries__EmptyList__ReturnsEmpty(self) -> None:
        """Test that empty list returns empty string."""
        # Arrange
        layout = TreeLayout()
        ctx = ProvenanceFormatContext()

        # Act
        result = layout.join_entries([], ctx)

        # Assert
        self.assertEqual("", result)


class TreeLayoutProgrammaticSourceTests(TestCase):
    """Tests for programmatic source type formatting."""

    def test_formatEntry__ProgrammaticSourceWithoutCliArg__ShowsSourceType(self) -> None:
        """Test that programmatic source without cli_arg shows just source type."""
        # Arrange
        layout = TreeLayout()
        entry = ProvenanceEntry(
            file="<override>",
            line=0,
            value=42,
            source_type="programmatic",
        )
        ctx = ProvenanceFormatContext(show_source_type=True)

        # Act
        result = layout.format_entry(entry, "test", ctx)

        # Assert
        self.assertIn("programmatic", result)

    def test_formatEntry__EnvSourceWithoutEnvVar__ShowsSourceType(self) -> None:
        """Test that env source without env_var shows just source type."""
        # Arrange
        layout = TreeLayout()
        entry = ProvenanceEntry(
            file="<override>",
            line=0,
            value="/data",
            source_type="env",
            env_var=None,
        )
        ctx = ProvenanceFormatContext(show_source_type=True)

        # Act
        result = layout.format_entry(entry, "test", ctx)

        # Assert
        self.assertIn("env", result)


class TreeLayoutTargetDisplayTests(TestCase):
    """Tests for TreeLayout target info display."""

    def test_formatEntry__WithTargetInfo__ShowsTargetLine(self) -> None:
        """Test that target info is displayed."""
        # Arrange
        layout = TreeLayout()
        entry = ProvenanceEntry(
            file="config.yaml",
            line=5,
            target_name="model",
            target_class="MyModel",
            target_module="myapp.models",
        )
        ctx = ProvenanceFormatContext(show_targets=True)

        # Act
        result = layout.format_entry(entry, "model", ctx)

        # Assert
        self.assertIn("Target: model -> myapp.models.MyModel", result)

    def test_formatEntry__WithAutoRegisteredTarget__ShowsAutoRegisteredMarker(
        self,
    ) -> None:
        """Test that auto-registered targets are marked."""
        # Arrange
        layout = TreeLayout()
        entry = ProvenanceEntry(
            file="config.yaml",
            line=5,
            target_name="model",
            target_class="MyModel",
            target_module="myapp.models",
            target_auto_registered=True,
        )
        ctx = ProvenanceFormatContext(show_targets=True)

        # Act
        result = layout.format_entry(entry, "model", ctx)

        # Assert
        self.assertIn("(auto-registered)", result)

    def test_formatEntry__UnregisteredTarget__ShowsNotRegistered(self) -> None:
        """Test that unregistered targets show 'not registered'."""
        # Arrange
        layout = TreeLayout()
        entry = ProvenanceEntry(
            file="config.yaml",
            line=5,
            target_name="unknown",
            target_class=None,
            target_module=None,
        )
        ctx = ProvenanceFormatContext(show_targets=True)

        # Act
        result = layout.format_entry(entry, "model", ctx)

        # Assert
        self.assertIn("Target: unknown (not registered)", result)

    def test_formatEntry__ShowTargetsFalse__OmitsTargetLine(self) -> None:
        """Test that targets are hidden when show_targets is False."""
        # Arrange
        layout = TreeLayout()
        entry = ProvenanceEntry(
            file="config.yaml",
            line=5,
            target_name="model",
            target_class="MyModel",
            target_module="myapp.models",
        )
        ctx = ProvenanceFormatContext(show_targets=False)

        # Act
        result = layout.format_entry(entry, "model", ctx)

        # Assert
        self.assertNotIn("Target:", result)

    def test_formatEntry__NoTargetName__OmitsTargetLine(self) -> None:
        """Test that entries without target_name don't show Target line."""
        # Arrange
        layout = TreeLayout()
        entry = ProvenanceEntry(
            file="config.yaml",
            line=5,
        )
        ctx = ProvenanceFormatContext(show_targets=True)

        # Act
        result = layout.format_entry(entry, "model.layers", ctx)

        # Assert
        self.assertNotIn("Target:", result)


class TreeLayoutFormatValueEdgeCaseTests(TestCase):
    """Tests for TreeLayout.format_value() edge cases."""

    def setUp(self) -> None:
        self.layout = TreeLayout()
        self.ctx = ProvenanceFormatContext()

    def test_formatValue__None__ReturnsNull(self) -> None:
        """Test that None value is formatted as 'null'."""
        # Act
        result = self.layout.format_value(None, self.ctx)

        # Assert
        self.assertEqual(result, "null")

    def test_formatValue__BoolTrue__ReturnsTrue(self) -> None:
        """Test that True is formatted as 'true'."""
        # Act
        result = self.layout.format_value(True, self.ctx)

        # Assert
        self.assertEqual(result, "true")

    def test_formatValue__BoolFalse__ReturnsFalse(self) -> None:
        """Test that False is formatted as 'false'."""
        # Act
        result = self.layout.format_value(False, self.ctx)

        # Assert
        self.assertEqual(result, "false")

    def test_formatValue__String__ReturnsQuotedRepr(self) -> None:
        """Test that strings are formatted with quotes."""
        # Act
        result = self.layout.format_value("hello", self.ctx)

        # Assert
        self.assertEqual(result, "'hello'")

    def test_formatValue__Integer__ReturnsStringified(self) -> None:
        """Test that integers are formatted correctly."""
        # Act
        result = self.layout.format_value(42, self.ctx)

        # Assert
        self.assertEqual(result, "42")


class TreeLayoutTargetWithoutModuleTests(TestCase):
    """Tests for _format_target when target_class exists but no module."""

    def test_formatTarget__ClassWithoutModule__FormatsCorrectly(self) -> None:
        """Test target formatting when class is present but module is None."""
        # Arrange
        layout = TreeLayout()
        entry = ProvenanceEntry(
            file="config.yaml",
            line=5,
            target_name="model",
            target_class="MyModel",
            target_module=None,  # No module
        )
        ctx = ProvenanceFormatContext(show_targets=True)

        # Act
        result = layout.format_entry(entry, "model", ctx)

        # Assert
        self.assertIn("Target: model -> MyModel", result)

    def test_formatTarget__ClassWithoutModuleAutoRegistered__ShowsMarker(self) -> None:
        """Test that auto-registered marker shows for class without module."""
        # Arrange
        layout = TreeLayout()
        entry = ProvenanceEntry(
            file="config.yaml",
            line=5,
            target_name="model",
            target_class="MyModel",
            target_module=None,
            target_auto_registered=True,
        )
        ctx = ProvenanceFormatContext(show_targets=True)

        # Act
        result = layout.format_entry(entry, "model", ctx)

        # Assert
        self.assertIn("Target: model -> MyModel", result)
        self.assertIn("(auto-registered)", result)


class TreeLayoutDeprecationTests(TestCase):
    """Tests for TreeLayout deprecation formatting."""

    def setUp(self) -> None:
        from rconfig.deprecation.info import DeprecationInfo

        self.layout = TreeLayout()
        builder = ProvenanceBuilder()
        builder.add(
            "old_key",
            file="config.yaml",
            line=5,
            deprecation=DeprecationInfo(
                pattern="old_key",
                new_key="new_key",
                message="Custom deprecation message",
                remove_in="3.0.0",
            ),
        )
        builder.set_config({"old_key": 42})
        self.provenance = builder.build()

    def test_formatEntry__WithDeprecation__ShowsDeprecatedMarker(self) -> None:
        entry = self.provenance.get("old_key")
        ctx = ProvenanceFormatContext()

        result = self.layout.format_entry(entry, "old_key", ctx)

        self.assertIn("DEPRECATED", result)

    def test_formatEntry__WithNewKey__ShowsNewKeyInArrow(self) -> None:
        entry = self.provenance.get("old_key")
        ctx = ProvenanceFormatContext()

        result = self.layout.format_entry(entry, "old_key", ctx)

        self.assertIn("-> new_key", result)

    def test_formatEntry__WithRemoveIn__ShowsVersion(self) -> None:
        entry = self.provenance.get("old_key")
        ctx = ProvenanceFormatContext()

        result = self.layout.format_entry(entry, "old_key", ctx)

        self.assertIn("remove in 3.0.0", result)

    def test_formatEntry__WithMessage__ShowsMessage(self) -> None:
        entry = self.provenance.get("old_key")
        ctx = ProvenanceFormatContext()

        result = self.layout.format_entry(entry, "old_key", ctx)

        self.assertIn("Message: Custom deprecation message", result)

    def test_formatEntry__HideDeprecations__OmitsDeprecationInfo(self) -> None:
        entry = self.provenance.get("old_key")
        ctx = ProvenanceFormatContext(show_deprecations=False)

        result = self.layout.format_entry(entry, "old_key", ctx)

        self.assertNotIn("DEPRECATED", result)
        self.assertNotIn("new_key", result)

    def test_formatEntry__MinimalDeprecation__ShowsOnlyDeprecated(self) -> None:
        from rconfig.deprecation.info import DeprecationInfo

        # Entry with only pattern, no new_key/message/remove_in
        entry = ProvenanceEntry(
            file="config.yaml",
            line=10,
            value="val",
            deprecation=DeprecationInfo(pattern="simple"),
        )
        ctx = ProvenanceFormatContext()

        result = self.layout.format_entry(entry, "simple", ctx)

        self.assertIn("DEPRECATED", result)
        self.assertNotIn("->", result)  # No new_key
        self.assertNotIn("remove in", result)  # No remove_in
        self.assertNotIn("Message:", result)  # No message

    def test_formatProvenance__DeprecationsOnly__FiltersCorrectly(self) -> None:
        from rconfig.deprecation.info import DeprecationInfo

        # Build a provenance with both deprecated and normal entries
        builder = ProvenanceBuilder()
        builder.add(
            "old_key",
            file="config.yaml",
            line=5,
            deprecation=DeprecationInfo(
                pattern="old_key",
                new_key="new_key",
                message="Custom deprecation message",
                remove_in="3.0.0",
            ),
        )
        builder.add("normal", file="config.yaml", line=20)
        builder.set_config({"old_key": 42, "normal": "normal_value"})
        prov = builder.build()
        ctx = ProvenanceFormatContext(deprecations_only=True)

        result = self.layout.format_provenance(prov, ctx)

        self.assertIn("old_key", result)
        self.assertNotIn("normal", result)

    def test_formatProvenance__DeprecationsOnly__AddsHeader(self) -> None:
        ctx = ProvenanceFormatContext(deprecations_only=True)

        result = self.layout.format_provenance(self.provenance, ctx)

        self.assertIn("Deprecated Keys:", result)

    def test_formatProvenance__DeprecationsOnlyEmpty__ShowsMessage(self) -> None:
        builder = ProvenanceBuilder()
        builder.add("normal", file="config.yaml", line=1)
        builder.set_config({"normal": 42})
        empty_prov = builder.build()
        ctx = ProvenanceFormatContext(deprecations_only=True)

        result = self.layout.format_provenance(empty_prov, ctx)

        self.assertEqual("No deprecated keys found.", result)
