"""Tests for ProvenanceFormat builder and TreeLayout."""

from unittest import TestCase

from rconfig.composition import (
    Provenance,
    ProvenanceEntry,
    ProvenanceNode,
    ProvenanceFormat,
    ProvenancePreset,
    ProvenanceLayout,
    FormatContext,
    TreeLayout,
    EntrySourceType,
    NodeSourceType,
)
from rconfig.composition.ProvenanceBuilder import ProvenanceBuilder


class ProvenanceFormatBuilderTests(TestCase):
    """Tests for ProvenanceFormat fluent builder methods."""

    def setUp(self) -> None:
        builder = ProvenanceBuilder()
        builder.add("model.lr", file="config.yaml", line=5)
        builder.add("model.epochs", file="config.yaml", line=6)
        builder.set_config({"model": {"lr": 0.01, "epochs": 100}})
        self.provenance = builder.build()

    def test_format__Default__ReturnsProvenanceFormat(self) -> None:
        result = self.provenance.format()

        self.assertIsInstance(result, ProvenanceFormat)

    def test_format__ShowHidePaths__SetsOverride(self) -> None:
        fmt = self.provenance.format()

        fmt.show_paths()
        ctx = fmt._build_context()
        self.assertTrue(ctx.show_paths)

        fmt.hide_paths()
        ctx = fmt._build_context()
        self.assertFalse(ctx.show_paths)

    def test_format__ShowHideValues__SetsOverride(self) -> None:
        fmt = self.provenance.format()

        fmt.show_values()
        ctx = fmt._build_context()
        self.assertTrue(ctx.show_values)

        fmt.hide_values()
        ctx = fmt._build_context()
        self.assertFalse(ctx.show_values)

    def test_format__ShowHideFiles__SetsOverride(self) -> None:
        fmt = self.provenance.format()

        fmt.show_files()
        ctx = fmt._build_context()
        self.assertTrue(ctx.show_files)

        fmt.hide_files()
        ctx = fmt._build_context()
        self.assertFalse(ctx.show_files)

    def test_format__ShowHideLines__SetsOverride(self) -> None:
        fmt = self.provenance.format()

        fmt.show_lines()
        ctx = fmt._build_context()
        self.assertTrue(ctx.show_lines)

        fmt.hide_lines()
        ctx = fmt._build_context()
        self.assertFalse(ctx.show_lines)

    def test_format__ShowHideSourceType__SetsOverride(self) -> None:
        fmt = self.provenance.format()

        fmt.show_source_type()
        ctx = fmt._build_context()
        self.assertTrue(ctx.show_source_type)

        fmt.hide_source_type()
        ctx = fmt._build_context()
        self.assertFalse(ctx.show_source_type)

    def test_format__ShowHideChain__SetsOverride(self) -> None:
        fmt = self.provenance.format()

        fmt.show_chain()
        ctx = fmt._build_context()
        self.assertTrue(ctx.show_chain)

        fmt.hide_chain()
        ctx = fmt._build_context()
        self.assertFalse(ctx.show_chain)

    def test_format__ShowHideOverrides__SetsOverride(self) -> None:
        fmt = self.provenance.format()

        fmt.show_overrides()
        ctx = fmt._build_context()
        self.assertTrue(ctx.show_overrides)

        fmt.hide_overrides()
        ctx = fmt._build_context()
        self.assertFalse(ctx.show_overrides)

    def test_format__ShowHideTargets__SetsOverride(self) -> None:
        fmt = self.provenance.format()

        fmt.show_targets()
        ctx = fmt._build_context()
        self.assertTrue(ctx.show_targets)

        fmt.hide_targets()
        ctx = fmt._build_context()
        self.assertFalse(ctx.show_targets)

    def test_format__MethodChaining__ReturnsSelf(self) -> None:
        fmt = self.provenance.format()

        result = fmt.show_paths().hide_values().show_files()

        self.assertIs(result, fmt)


class ProvenanceFormatPresetTests(TestCase):
    """Tests for preset methods."""

    def setUp(self) -> None:
        builder = ProvenanceBuilder()
        builder.add("test", file="test.yaml", line=1)
        builder.set_config({"test": 42})
        self.provenance = builder.build()

    def test_format__MinimalPreset__HidesValuesAndChain(self) -> None:
        fmt = self.provenance.format().minimal()
        ctx = fmt._build_context()

        self.assertTrue(ctx.show_paths)
        self.assertFalse(ctx.show_values)
        self.assertTrue(ctx.show_files)
        self.assertTrue(ctx.show_lines)
        self.assertFalse(ctx.show_source_type)
        self.assertFalse(ctx.show_chain)
        self.assertFalse(ctx.show_overrides)
        self.assertFalse(ctx.show_targets)

    def test_format__CompactPreset__HidesChainAndOverrides(self) -> None:
        fmt = self.provenance.format().compact()
        ctx = fmt._build_context()

        self.assertTrue(ctx.show_paths)
        self.assertTrue(ctx.show_values)
        self.assertTrue(ctx.show_files)
        self.assertTrue(ctx.show_lines)
        self.assertTrue(ctx.show_source_type)
        self.assertFalse(ctx.show_chain)
        self.assertFalse(ctx.show_overrides)
        self.assertTrue(ctx.show_targets)

    def test_format__FullPreset__ShowsEverything(self) -> None:
        fmt = self.provenance.format().full()
        ctx = fmt._build_context()

        self.assertTrue(ctx.show_paths)
        self.assertTrue(ctx.show_values)
        self.assertTrue(ctx.show_files)
        self.assertTrue(ctx.show_lines)
        self.assertTrue(ctx.show_source_type)
        self.assertTrue(ctx.show_chain)
        self.assertTrue(ctx.show_overrides)
        self.assertTrue(ctx.show_targets)

    def test_format__PresetEnum__WorksLikeMethod(self) -> None:
        fmt_method = self.provenance.format().minimal()
        fmt_enum = self.provenance.format().preset(ProvenancePreset.MINIMAL)

        ctx_method = fmt_method._build_context()
        ctx_enum = fmt_enum._build_context()

        self.assertEqual(ctx_method.show_values, ctx_enum.show_values)
        self.assertEqual(ctx_method.show_chain, ctx_enum.show_chain)

    def test_format__PresetWithOverride__OverrideWins(self) -> None:
        fmt = self.provenance.format().minimal().show_values()
        ctx = fmt._build_context()

        # Minimal sets show_values=False, but explicit override sets True
        self.assertTrue(ctx.show_values)


class ProvenanceFormatFilterTests(TestCase):
    """Tests for filter methods."""

    def setUp(self) -> None:
        builder = ProvenanceBuilder()
        builder.add("model.lr", file="config.yaml", line=5)
        builder.add("model.epochs", file="overrides.yaml", line=1)
        builder.add("data.path", file="data.yaml", line=2)
        builder.set_config({"model": {"lr": 0.01, "epochs": 100}, "data": {"path": "/data"}})
        self.provenance = builder.build()

    def test_format__ForPath__AddsFilter(self) -> None:
        fmt = self.provenance.format().for_path("/model.*")
        ctx = fmt._build_context()

        self.assertEqual(["/model.*"], ctx.path_filters)

    def test_format__ForPathMultiple__AddsAllFilters(self) -> None:
        fmt = self.provenance.format().for_path("/model.*").for_path("/data.*")
        ctx = fmt._build_context()

        self.assertEqual(["/model.*", "/data.*"], ctx.path_filters)

    def test_format__FromFile__AddsFilter(self) -> None:
        fmt = self.provenance.format().from_file("config.yaml")
        ctx = fmt._build_context()

        self.assertEqual(["config.yaml"], ctx.file_filters)

    def test_format__FromFileMultiple__AddsAllFilters(self) -> None:
        fmt = self.provenance.format().from_file("*.yaml").from_file("*.json")
        ctx = fmt._build_context()

        self.assertEqual(["*.yaml", "*.json"], ctx.file_filters)


class ProvenanceFormatLayoutTests(TestCase):
    """Tests for custom layout support."""

    def setUp(self) -> None:
        builder = ProvenanceBuilder()
        builder.add("test", file="test.yaml", line=1)
        builder.set_config({"test": 42})
        self.provenance = builder.build()

    def test_format__CustomLayout__UsesCustomLayout(self) -> None:
        class TestLayout(ProvenanceLayout):
            def format_provenance(self, prov, ctx):
                return "CUSTOM OUTPUT"

            def format_entry(self, entry, path, ctx):
                return f"{path}={entry.value}"

        fmt = self.provenance.format().layout(TestLayout())
        result = str(fmt)

        self.assertEqual("CUSTOM OUTPUT", result)

    def test_format__LayoutWithDefaults__UsesLayoutDefaults(self) -> None:
        class NoValuesLayout(ProvenanceLayout):
            def get_default_context(self):
                ctx = FormatContext()
                ctx.show_values = False
                return ctx

            def format_provenance(self, prov, ctx):
                return f"show_values={ctx.show_values}"

            def format_entry(self, entry, path, ctx):
                return ""

        fmt = self.provenance.format().layout(NoValuesLayout())
        result = str(fmt)

        self.assertEqual("show_values=False", result)

    def test_format__LayoutWithBuilderOverride__OverrideWins(self) -> None:
        class NoValuesLayout(ProvenanceLayout):
            def get_default_context(self):
                ctx = FormatContext()
                ctx.show_values = False
                return ctx

            def format_provenance(self, prov, ctx):
                return f"show_values={ctx.show_values}"

            def format_entry(self, entry, path, ctx):
                return ""

        fmt = self.provenance.format().layout(NoValuesLayout()).show_values()
        result = str(fmt)

        self.assertEqual("show_values=True", result)


class TreeLayoutTests(TestCase):
    """Tests for TreeLayout formatting."""

    def setUp(self) -> None:
        self.layout = TreeLayout()
        self.provenance = Provenance()
        self._builder = ProvenanceBuilder()  # For building provenance in tests

    def test_formatProvenance__EmptyProvenance__ReturnsEmpty(self) -> None:
        ctx = FormatContext()
        result = self.layout.format_provenance(self.provenance, ctx)

        self.assertEqual("", result)

    def test_formatProvenance__SingleEntry__FormatsCorrectly(self) -> None:
        builder = ProvenanceBuilder()
        builder.add("model.lr", file="config.yaml", line=5)
        builder.set_config({"model": {"lr": 0.01}})
        prov = builder.build()
        ctx = FormatContext()

        result = self.layout.format_provenance(prov, ctx)

        self.assertIn("/model.lr", result)
        self.assertIn("0.01", result)
        self.assertIn("config.yaml", result)
        self.assertIn("5", result)

    def test_formatProvenance__MultipleEntries__SeparatesWithBlankLine(self) -> None:
        builder = ProvenanceBuilder()
        builder.add("a", file="a.yaml", line=1)
        builder.add("b", file="b.yaml", line=2)
        builder.set_config({"a": 1, "b": 2})
        prov = builder.build()
        ctx = FormatContext()

        result = self.layout.format_provenance(prov, ctx)

        # Entries should be separated by blank lines
        self.assertIn("\n\n", result)

    def test_formatProvenance__HideValues__OmitsValues(self) -> None:
        builder = ProvenanceBuilder()
        builder.add("test", file="test.yaml", line=1)
        builder.set_config({"test": 42})
        prov = builder.build()
        ctx = FormatContext(show_values=False)

        result = self.layout.format_provenance(prov, ctx)

        self.assertIn("/test", result)
        self.assertNotIn("42", result)

    def test_formatProvenance__HidePaths__OmitsPaths(self) -> None:
        builder = ProvenanceBuilder()
        builder.add("test", file="test.yaml", line=1)
        builder.set_config({"test": 42})
        prov = builder.build()
        ctx = FormatContext(show_paths=False)

        result = self.layout.format_provenance(prov, ctx)

        self.assertNotIn("/test", result)
        self.assertIn("42", result)

    def test_formatProvenance__PathFilter__FiltersEntries(self) -> None:
        builder = ProvenanceBuilder()
        builder.add("model.lr", file="config.yaml", line=1)
        builder.add("data.path", file="config.yaml", line=2)
        builder.set_config({"model": {"lr": 0.01}, "data": {"path": "/data"}})
        prov = builder.build()
        ctx = FormatContext(path_filters=["/model.*"])

        result = self.layout.format_provenance(prov, ctx)

        self.assertIn("/model.lr", result)
        self.assertNotIn("/data.path", result)

    def test_formatProvenance__FileFilter__FiltersEntries(self) -> None:
        builder = ProvenanceBuilder()
        builder.add("a", file="config.yaml", line=1)
        builder.add("b", file="other.json", line=2)
        builder.set_config({"a": 1, "b": 2})
        prov = builder.build()
        ctx = FormatContext(file_filters=["*.yaml"])

        result = self.layout.format_provenance(prov, ctx)

        self.assertIn("config.yaml", result)
        self.assertNotIn("other.json", result)

    def test_formatProvenance__CliSourceType__ShowsCliMarker(self) -> None:
        builder = ProvenanceBuilder()
        builder.add("test", file="config.yaml", line=1, source_type=EntrySourceType.CLI, cli_arg="--test=42")
        builder.set_config({"test": 42})
        prov = builder.build()
        ctx = FormatContext()

        result = self.layout.format_provenance(prov, ctx)

        self.assertIn("CLI", result)
        self.assertIn("--test=42", result)

    def test_formatProvenance__EnvSourceType__ShowsEnvMarker(self) -> None:
        builder = ProvenanceBuilder()
        builder.add("test", file="config.yaml", line=1, source_type=EntrySourceType.ENV, env_var="DATA_PATH")
        builder.set_config({"test": "/data"})
        prov = builder.build()
        ctx = FormatContext()

        result = self.layout.format_provenance(prov, ctx)

        self.assertIn("env", result)
        self.assertIn("DATA_PATH", result)

    def test_formatProvenance__Override__ShowsOverrideInfo(self) -> None:
        builder = ProvenanceBuilder()
        builder.add("test", file="override.yaml", line=5, overrode="base.yaml:10")
        builder.set_config({"test": 42})
        prov = builder.build()
        ctx = FormatContext()

        result = self.layout.format_provenance(prov, ctx)

        self.assertIn("Overrode", result)
        self.assertIn("base.yaml:10", result)


class ProvenanceNodeTests(TestCase):
    """Tests for ProvenanceNode dataclass."""

    def test_toDict__BasicNode__ReturnsDict(self) -> None:
        node = ProvenanceNode(
            source_type=NodeSourceType.FILE,
            file="test.yaml",
            line=5,
            value=42,
        )

        result = node.to_dict()

        self.assertEqual("file", result["source_type"])
        self.assertEqual("test.yaml", result["file"])
        self.assertEqual(5, result["line"])
        self.assertEqual(42, result["value"])

    def test_toDict__WithChildren__IncludesChildren(self) -> None:
        child = ProvenanceNode(source_type=NodeSourceType.FILE, value=1)
        parent = ProvenanceNode(source_type=NodeSourceType.OPERATOR, operator="+", children=(child,))

        result = parent.to_dict()

        self.assertEqual("+", result["operator"])
        self.assertEqual(1, len(result["children"]))
        self.assertEqual(1, result["children"][0]["value"])

    def test_toDict__OmitsNoneFields__ReturnsCompact(self) -> None:
        node = ProvenanceNode(source_type=NodeSourceType.FILE)

        result = node.to_dict()

        self.assertNotIn("path", result)
        self.assertNotIn("file", result)
        self.assertNotIn("line", result)
        self.assertNotIn("children", result)


class ProvenanceEntryToDictTests(TestCase):
    """Tests for ProvenanceEntry.to_dict()."""

    def test_toDict__BasicEntry__ReturnsDict(self) -> None:
        entry = ProvenanceEntry(file="test.yaml", line=5, value=42)

        result = entry.to_dict()

        self.assertEqual("test.yaml", result["file"])
        self.assertEqual(5, result["line"])
        self.assertEqual("file", result["source_type"])
        self.assertEqual(42, result["value"])

    def test_toDict__WithOverride__IncludesOverride(self) -> None:
        entry = ProvenanceEntry(
            file="test.yaml", line=5, overrode="base.yaml:10"
        )

        result = entry.to_dict()

        self.assertEqual("base.yaml:10", result["overrode"])

    def test_toDict__CliSource__IncludesCliArg(self) -> None:
        entry = ProvenanceEntry(
            file="test.yaml",
            line=5,
            source_type=EntrySourceType.CLI,
            cli_arg="--lr=0.01",
        )

        result = entry.to_dict()

        self.assertEqual("cli", result["source_type"])
        self.assertEqual("--lr=0.01", result["cli_arg"])


class ProvenanceToDictTests(TestCase):
    """Tests for Provenance.to_dict()."""

    def test_toDict__Empty__ReturnsEmptyDict(self) -> None:
        provenance = Provenance()

        result = provenance.to_dict()

        self.assertEqual({}, result)

    def test_toDict__WithEntries__ReturnsDictOfEntries(self) -> None:
        builder = ProvenanceBuilder()
        builder.add("a", file="a.yaml", line=1)
        builder.add("b", file="b.yaml", line=2)
        provenance = builder.build()

        result = provenance.to_dict()

        self.assertIn("a", result)
        self.assertIn("b", result)
        self.assertEqual("a.yaml", result["a"]["file"])
        self.assertEqual("b.yaml", result["b"]["file"])


class ProvenanceTraceTests(TestCase):
    """Tests for Provenance.trace()."""

    def test_trace__NonexistentPath__ReturnsNone(self) -> None:
        provenance = Provenance()

        result = provenance.trace("nonexistent")

        self.assertIsNone(result)

    def test_trace__BasicEntry__ReturnsNode(self) -> None:
        builder = ProvenanceBuilder()
        builder.add("test", file="test.yaml", line=5)
        builder.set_config({"test": 42})
        provenance = builder.build()

        result = provenance.trace("test")

        self.assertIsNotNone(result)
        self.assertEqual("file", result.source_type)
        self.assertEqual("test.yaml", result.file)
        self.assertEqual(5, result.line)
        self.assertEqual(42, result.value)

    def test_trace__CliEntry__ReturnsCliNode(self) -> None:
        builder = ProvenanceBuilder()
        builder.add("test", file="test.yaml", line=5, source_type=EntrySourceType.CLI, cli_arg="--test=42")
        builder.set_config({"test": 42})
        provenance = builder.build()

        result = provenance.trace("test")

        self.assertEqual("cli", result.source_type)
        self.assertEqual("--test=42", result.cli_arg)


class ProvenanceSetConfigTests(TestCase):
    """Tests for ProvenanceBuilder.set_config() value population."""

    def test_setConfig__PopulatesValues__FillsEntryValues(self) -> None:
        builder = ProvenanceBuilder()
        builder.add("model.lr", file="config.yaml", line=5)
        builder.add("model.epochs", file="config.yaml", line=6)
        config = {"model": {"lr": 0.01, "epochs": 100}}

        builder.set_config(config)
        provenance = builder.build()

        self.assertEqual(0.01, provenance.get("model.lr").value)
        self.assertEqual(100, provenance.get("model.epochs").value)

    def test_setConfig__PreservesExistingValues__DoesNotOverwrite(self) -> None:
        # Entry with value already set (e.g., from interpolation resolution)
        # Simulate by adding directly with value to builder's internal state
        builder = ProvenanceBuilder()
        builder.add("model.lr", file="config.yaml", line=5)
        # Set value directly via the mutable entry
        builder._entries["model.lr"].value = 999
        config = {"model": {"lr": 0.01}}

        builder.set_config(config)
        provenance = builder.build()

        # Should preserve the existing value, not overwrite
        self.assertEqual(999, provenance.get("model.lr").value)

    def test_setConfig__MissingPath__KeepsNone(self) -> None:
        builder = ProvenanceBuilder()
        builder.add("deleted.path", file="config.yaml", line=5)
        config = {}  # Path doesn't exist

        builder.set_config(config)
        provenance = builder.build()

        self.assertIsNone(provenance.get("deleted.path").value)

    def test_setConfig__NestedPath__PopulatesCorrectly(self) -> None:
        builder = ProvenanceBuilder()
        builder.add("a.b.c.d", file="config.yaml", line=5)
        config = {"a": {"b": {"c": {"d": "deep_value"}}}}

        builder.set_config(config)
        provenance = builder.build()

        self.assertEqual("deep_value", provenance.get("a.b.c.d").value)


class OverrideProvenanceTests(TestCase):
    """Tests for CLI and programmatic override provenance tracking."""

    def test_applyOverrides__CliOverride__SetsCliSourceType(self) -> None:
        from rconfig.override import Override, apply_overrides

        builder = ProvenanceBuilder()
        builder.add("model.lr", file="config.yaml", line=5)
        builder.set_config({"model": {"lr": 0.001}})
        config = {"model": {"lr": 0.001}}
        overrides = [
            Override(
                path=["model", "lr"],
                value=0.01,
                operation="set",
                source_type=EntrySourceType.CLI,
                cli_arg="model.lr=0.01",
            )
        ]

        apply_overrides(config, overrides, builder)
        provenance = builder.build()

        entry = provenance.get("model.lr")
        self.assertEqual("cli", entry.source_type)
        self.assertEqual("model.lr=0.01", entry.cli_arg)
        self.assertEqual(0.01, entry.value)
        self.assertEqual("config.yaml:5", entry.overrode)

    def test_applyOverrides__ProgrammaticOverride__SetsProgrammaticSourceType(self) -> None:
        from rconfig.override import Override, apply_overrides

        builder = ProvenanceBuilder()
        builder.add("model.epochs", file="config.yaml", line=6)
        builder.set_config({"model": {"epochs": 100}})
        config = {"model": {"epochs": 100}}
        overrides = [
            Override(
                path=["model", "epochs"],
                value=200,
                operation="set",
                source_type=EntrySourceType.PROGRAMMATIC,
            )
        ]

        apply_overrides(config, overrides, builder)
        provenance = builder.build()

        entry = provenance.get("model.epochs")
        self.assertEqual("programmatic", entry.source_type)
        self.assertIsNone(entry.cli_arg)
        self.assertEqual(200, entry.value)

    def test_applyOverrides__NewPath__CreatesEntry(self) -> None:
        from rconfig.override import Override, apply_overrides

        builder = ProvenanceBuilder()
        config = {"model": {}}
        overrides = [
            Override(
                path=["model", "new_param"],
                value=42,
                operation="set",
                source_type=EntrySourceType.CLI,
                cli_arg="model.new_param=42",
            )
        ]

        apply_overrides(config, overrides, builder)
        provenance = builder.build()

        entry = provenance.get("model.new_param")
        self.assertIsNotNone(entry)
        self.assertEqual("cli", entry.source_type)
        self.assertIsNone(entry.overrode)  # Nothing to override

    def test_parseCliArg__SetsSourceTypeAndCliArg(self) -> None:
        from rconfig.override import parse_cli_arg

        result = parse_cli_arg("model.lr=0.01")

        self.assertIsNotNone(result)
        self.assertEqual("cli", result.source_type)
        self.assertEqual("model.lr=0.01", result.cli_arg)

    def test_parseDictOverrides__SetsProgrammaticSourceType(self) -> None:
        from rconfig.override import parse_dict_overrides

        result = parse_dict_overrides({"model.lr": 0.01})

        self.assertEqual(1, len(result))
        self.assertEqual("programmatic", result[0].source_type)
        self.assertIsNone(result[0].cli_arg)


class ProvenanceFormatEdgeCaseTests(TestCase):
    """Edge case tests for ProvenanceFormat builder."""

    def setUp(self) -> None:
        builder = ProvenanceBuilder()
        builder.add("test", file="test.yaml", line=1)
        builder.set_config({"test": 42})
        self.provenance = builder.build()

    def test_format__Repr__ReturnsLayoutClassName(self) -> None:
        """Test that __repr__ returns layout class name."""
        # Arrange
        fmt = self.provenance.format()

        # Act
        result = repr(fmt)

        # Assert
        self.assertIn("ProvenanceFormat", result)
        self.assertIn("TreeLayout", result)

    def test_format__IndentMethod__SetsIndentSize(self) -> None:
        """Test that indent() method sets indent size correctly."""
        # Arrange
        fmt = self.provenance.format().indent(4)

        # Act
        ctx = fmt._build_context()

        # Assert
        self.assertEqual(4, ctx.indent_size)

    def test_format__FilterChaining__AllFiltersApplied(self) -> None:
        """Test that chaining filters adds them all."""
        # Arrange
        fmt = (
            self.provenance.format()
            .for_path("/model.*")
            .for_path("/data.*")
            .from_file("*.yaml")
            .from_file("*.json")
        )

        # Act
        ctx = fmt._build_context()

        # Assert
        self.assertEqual(["/model.*", "/data.*"], ctx.path_filters)
        self.assertEqual(["*.yaml", "*.json"], ctx.file_filters)

    def test_format__PresetEnumCompact__AppliesCorrectSettings(self) -> None:
        """Test that preset(COMPACT) applies compact settings."""
        # Arrange
        fmt = self.provenance.format().preset(ProvenancePreset.COMPACT)

        # Act
        ctx = fmt._build_context()

        # Assert
        self.assertTrue(ctx.show_paths)
        self.assertTrue(ctx.show_values)
        self.assertTrue(ctx.show_source_type)
        self.assertFalse(ctx.show_chain)
        self.assertFalse(ctx.show_overrides)

    def test_format__PresetEnumFull__AppliesCorrectSettings(self) -> None:
        """Test that preset(FULL) applies full settings."""
        # Arrange
        fmt = self.provenance.format().preset(ProvenancePreset.FULL)

        # Act
        ctx = fmt._build_context()

        # Assert
        self.assertTrue(ctx.show_paths)
        self.assertTrue(ctx.show_values)
        self.assertTrue(ctx.show_source_type)
        self.assertTrue(ctx.show_chain)
        self.assertTrue(ctx.show_overrides)

    def test_format__BuildContext__CopiesListFilters(self) -> None:
        """Test that _build_context creates copies of filter lists."""
        # Arrange
        fmt = self.provenance.format().for_path("/test")
        ctx1 = fmt._build_context()

        # Act - modify first context's filters
        ctx1.path_filters.append("/modified")
        ctx2 = fmt._build_context()

        # Assert - second context should not see modification
        self.assertEqual(["/test"], ctx2.path_filters)

    def test_format__LayoutSwitch__GetsNewDefaults(self) -> None:
        """Test that switching layout gets new default context."""
        # Arrange
        class CustomLayout(ProvenanceLayout):
            def get_default_context(self):
                return FormatContext(show_values=False, indent_size=8)

            def format_provenance(self, prov, ctx):
                return f"custom: indent={ctx.indent_size}"

            def format_entry(self, entry, path, ctx):
                return ""

        # Act
        fmt = self.provenance.format().layout(CustomLayout())
        result = str(fmt)

        # Assert
        self.assertIn("custom", result)
        self.assertIn("indent=8", result)

    def test_format__PresetThenOverride__OverrideWins(self) -> None:
        """Test that override after preset wins."""
        # Arrange
        fmt = self.provenance.format().minimal().show_values()

        # Act
        ctx = fmt._build_context()

        # Assert - minimal sets show_values=False, but override sets True
        self.assertTrue(ctx.show_values)

    def test_format__OverrideThenPreset__PresetWins(self) -> None:
        """Test that preset after override wins."""
        # Arrange
        fmt = self.provenance.format().show_values().minimal()

        # Act
        ctx = fmt._build_context()

        # Assert - minimal is applied after show_values, so minimal wins
        self.assertFalse(ctx.show_values)

    def test_format__EmptyProvenance__StrReturnsEmpty(self) -> None:
        """Test that formatting empty provenance returns empty string."""
        # Arrange
        empty_prov = Provenance()
        fmt = empty_prov.format()

        # Act
        result = str(fmt)

        # Assert
        self.assertEqual("", result)

    def test_format__MultipleBuildContext__IndependentResults(self) -> None:
        """Test that multiple _build_context calls are independent."""
        # Arrange
        fmt = self.provenance.format()

        # Act
        ctx1 = fmt._build_context()
        ctx1.show_paths = False  # Modify first
        ctx2 = fmt._build_context()

        # Assert - second should have default value
        self.assertTrue(ctx2.show_paths)


class ProvenanceFormatDeprecationTests(TestCase):
    """Tests for deprecation-related ProvenanceFormat features."""

    def setUp(self) -> None:
        from rconfig.deprecation.info import DeprecationInfo

        builder = ProvenanceBuilder()
        builder.add(
            "learning_rate",
            file="config.yaml",
            line=5,
            deprecation=DeprecationInfo(
                pattern="learning_rate",
                new_key="model.optimizer.lr",
                message="Use 'model.optimizer.lr' instead",
                remove_in="2.0.0",
            ),
        )
        builder.add("model.lr", file="config.yaml", line=10)
        builder.add(
            "n_epochs",
            file="config.yaml",
            line=15,
            deprecation=DeprecationInfo(
                pattern="n_epochs",
                new_key="training.epochs",
            ),
        )
        builder.set_config({"learning_rate": 0.01, "model": {"lr": 0.01}, "n_epochs": 100})
        self.provenance = builder.build()

    def test_format__ShowHideDeprecations__SetsOverride(self) -> None:
        fmt = self.provenance.format()

        fmt.show_deprecations()
        ctx = fmt._build_context()
        self.assertTrue(ctx.show_deprecations)

        fmt.hide_deprecations()
        ctx = fmt._build_context()
        self.assertFalse(ctx.show_deprecations)

    def test_format__DeprecationsPreset__SetsDeprecationsOnly(self) -> None:
        fmt = self.provenance.format().deprecations()
        ctx = fmt._build_context()

        self.assertTrue(ctx.deprecations_only)
        self.assertTrue(ctx.show_deprecations)
        self.assertTrue(ctx.show_paths)
        self.assertTrue(ctx.show_values)
        self.assertFalse(ctx.show_chain)
        self.assertFalse(ctx.show_overrides)
        self.assertFalse(ctx.show_targets)

    def test_format__DeprecationsPreset__FiltersToDeprecatedOnly(self) -> None:
        result = str(self.provenance.format().deprecations())

        # Should include deprecated keys
        self.assertIn("learning_rate", result)
        self.assertIn("n_epochs", result)
        # Should NOT include non-deprecated keys
        self.assertNotIn("/model.lr", result)

    def test_format__DeprecationsPreset__ShowsDeprecationInfo(self) -> None:
        result = str(self.provenance.format().deprecations())

        # Should show deprecation details
        self.assertIn("DEPRECATED", result)
        self.assertIn("model.optimizer.lr", result)
        self.assertIn("2.0.0", result)
        self.assertIn("Use 'model.optimizer.lr' instead", result)

    def test_format__DeprecationsPreset__ShowsHeader(self) -> None:
        result = str(self.provenance.format().deprecations())

        self.assertIn("Deprecated Keys:", result)
        self.assertIn("-" * 16, result)

    def test_format__DeprecationsPreset__NoDeprecations__ShowsEmptyMessage(self) -> None:
        # Create provenance without deprecations
        builder = ProvenanceBuilder()
        builder.add("test", file="config.yaml", line=1)
        builder.set_config({"test": 42})
        empty_prov = builder.build()

        result = str(empty_prov.format().deprecations())

        self.assertEqual("No deprecated keys found.", result)

    def test_format__HideDeprecations__OmitsDeprecationInfo(self) -> None:
        result = str(self.provenance.format().hide_deprecations())

        # Should NOT show deprecation details
        self.assertNotIn("DEPRECATED", result)
        self.assertNotIn("model.optimizer.lr", result)


class ProvenanceEntryDeprecationTests(TestCase):
    """Tests for ProvenanceEntry deprecation field."""

    def test_toDict__WithDeprecation__IncludesDeprecation(self) -> None:
        from rconfig.deprecation.info import DeprecationInfo

        entry = ProvenanceEntry(
            file="test.yaml",
            line=5,
            value=42,
            deprecation=DeprecationInfo(
                pattern="old_key",
                new_key="new_key",
                message="Use new_key",
                remove_in="2.0.0",
            ),
        )

        result = entry.to_dict()

        self.assertIn("deprecation", result)
        self.assertEqual("old_key", result["deprecation"]["pattern"])
        self.assertEqual("new_key", result["deprecation"]["new_key"])
        self.assertEqual("Use new_key", result["deprecation"]["message"])
        self.assertEqual("2.0.0", result["deprecation"]["remove_in"])

    def test_toDict__NoDeprecation__OmitsDeprecation(self) -> None:
        entry = ProvenanceEntry(file="test.yaml", line=5, value=42)

        result = entry.to_dict()

        self.assertNotIn("deprecation", result)


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
        ctx = FormatContext()

        result = self.layout.format_entry(entry, "old_key", ctx)

        self.assertIn("DEPRECATED", result)

    def test_formatEntry__WithNewKey__ShowsNewKeyInArrow(self) -> None:
        entry = self.provenance.get("old_key")
        ctx = FormatContext()

        result = self.layout.format_entry(entry, "old_key", ctx)

        self.assertIn("-> new_key", result)

    def test_formatEntry__WithRemoveIn__ShowsVersion(self) -> None:
        entry = self.provenance.get("old_key")
        ctx = FormatContext()

        result = self.layout.format_entry(entry, "old_key", ctx)

        self.assertIn("remove in 3.0.0", result)

    def test_formatEntry__WithMessage__ShowsMessage(self) -> None:
        entry = self.provenance.get("old_key")
        ctx = FormatContext()

        result = self.layout.format_entry(entry, "old_key", ctx)

        self.assertIn("Message: Custom deprecation message", result)

    def test_formatEntry__HideDeprecations__OmitsDeprecationInfo(self) -> None:
        entry = self.provenance.get("old_key")
        ctx = FormatContext(show_deprecations=False)

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
        ctx = FormatContext()

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
        ctx = FormatContext(deprecations_only=True)

        result = self.layout.format_provenance(prov, ctx)

        self.assertIn("old_key", result)
        self.assertNotIn("normal", result)

    def test_formatProvenance__DeprecationsOnly__AddsHeader(self) -> None:
        ctx = FormatContext(deprecations_only=True)

        result = self.layout.format_provenance(self.provenance, ctx)

        self.assertIn("Deprecated Keys:", result)

    def test_formatProvenance__DeprecationsOnlyEmpty__ShowsMessage(self) -> None:
        builder = ProvenanceBuilder()
        builder.add("normal", file="config.yaml", line=1)
        builder.set_config({"normal": 42})
        empty_prov = builder.build()
        ctx = FormatContext(deprecations_only=True)

        result = self.layout.format_provenance(empty_prov, ctx)

        self.assertEqual("No deprecated keys found.", result)
