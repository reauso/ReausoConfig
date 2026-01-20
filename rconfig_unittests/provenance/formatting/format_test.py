"""Tests for ProvenanceFormat builder and presets."""

from unittest import TestCase

from rconfig.provenance import (
    EntrySourceType,
    NodeSourceType,
    Provenance,
    ProvenanceBuilder,
    ProvenanceEntry,
    ProvenanceFormat,
    ProvenanceFormatContext,
    ProvenanceLayout,
    ProvenanceNode,
    TreeLayout,
)
from rconfig.provenance.formatting.model import ProvenanceDisplayModel


class ProvenanceFormatBuilderTests(TestCase):
    """Tests for ProvenanceFormat fluent builder methods."""

    def setUp(self) -> None:
        builder = ProvenanceBuilder()
        builder.add("model.lr", file="config.yaml", line=5)
        builder.add("model.epochs", file="config.yaml", line=6)
        builder.set_config({"model": {"lr": 0.01, "epochs": 100}})
        self.provenance = builder.build()

    def test_format__Default__ReturnsProvenanceFormat(self) -> None:
        result = ProvenanceFormat(self.provenance)

        self.assertIsInstance(result, ProvenanceFormat)

    def test_format__ShowHidePaths__SetsOverride(self) -> None:
        fmt = ProvenanceFormat(self.provenance)

        fmt.show_paths()
        ctx = fmt._ctx
        self.assertTrue(ctx.show_paths)

        fmt.hide_paths()
        ctx = fmt._ctx
        self.assertFalse(ctx.show_paths)

    def test_format__ShowHideValues__SetsOverride(self) -> None:
        fmt = ProvenanceFormat(self.provenance)

        fmt.show_values()
        ctx = fmt._ctx
        self.assertTrue(ctx.show_values)

        fmt.hide_values()
        ctx = fmt._ctx
        self.assertFalse(ctx.show_values)

    def test_format__ShowHideFiles__SetsOverride(self) -> None:
        fmt = ProvenanceFormat(self.provenance)

        fmt.show_files()
        ctx = fmt._ctx
        self.assertTrue(ctx.show_files)

        fmt.hide_files()
        ctx = fmt._ctx
        self.assertFalse(ctx.show_files)

    def test_format__ShowHideLines__SetsOverride(self) -> None:
        fmt = ProvenanceFormat(self.provenance)

        fmt.show_lines()
        ctx = fmt._ctx
        self.assertTrue(ctx.show_lines)

        fmt.hide_lines()
        ctx = fmt._ctx
        self.assertFalse(ctx.show_lines)

    def test_format__ShowHideSourceType__SetsOverride(self) -> None:
        fmt = ProvenanceFormat(self.provenance)

        fmt.show_source_type()
        ctx = fmt._ctx
        self.assertTrue(ctx.show_source_type)

        fmt.hide_source_type()
        ctx = fmt._ctx
        self.assertFalse(ctx.show_source_type)

    def test_format__ShowHideChain__SetsOverride(self) -> None:
        fmt = ProvenanceFormat(self.provenance)

        fmt.show_chain()
        ctx = fmt._ctx
        self.assertTrue(ctx.show_chain)

        fmt.hide_chain()
        ctx = fmt._ctx
        self.assertFalse(ctx.show_chain)

    def test_format__ShowHideOverrides__SetsOverride(self) -> None:
        fmt = ProvenanceFormat(self.provenance)

        fmt.show_overrides()
        ctx = fmt._ctx
        self.assertTrue(ctx.show_overrides)

        fmt.hide_overrides()
        ctx = fmt._ctx
        self.assertFalse(ctx.show_overrides)

    def test_format__ShowHideTargets__SetsOverride(self) -> None:
        fmt = ProvenanceFormat(self.provenance)

        fmt.show_targets()
        ctx = fmt._ctx
        self.assertTrue(ctx.show_targets)

        fmt.hide_targets()
        ctx = fmt._ctx
        self.assertFalse(ctx.show_targets)

    def test_format__MethodChaining__ReturnsSelf(self) -> None:
        fmt = ProvenanceFormat(self.provenance)

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
        fmt = ProvenanceFormat(self.provenance).minimal()
        ctx = fmt._ctx

        self.assertTrue(ctx.show_paths)
        self.assertFalse(ctx.show_values)
        self.assertTrue(ctx.show_files)
        self.assertTrue(ctx.show_lines)
        self.assertFalse(ctx.show_source_type)
        self.assertFalse(ctx.show_chain)
        self.assertFalse(ctx.show_overrides)
        self.assertFalse(ctx.show_targets)

    def test_format__CompactPreset__HidesChainAndOverrides(self) -> None:
        fmt = ProvenanceFormat(self.provenance).compact()
        ctx = fmt._ctx

        self.assertTrue(ctx.show_paths)
        self.assertTrue(ctx.show_values)
        self.assertTrue(ctx.show_files)
        self.assertTrue(ctx.show_lines)
        self.assertTrue(ctx.show_source_type)
        self.assertFalse(ctx.show_chain)
        self.assertFalse(ctx.show_overrides)
        self.assertTrue(ctx.show_targets)

    def test_format__FullPreset__ShowsEverything(self) -> None:
        fmt = ProvenanceFormat(self.provenance).full()
        ctx = fmt._ctx

        self.assertTrue(ctx.show_paths)
        self.assertTrue(ctx.show_values)
        self.assertTrue(ctx.show_files)
        self.assertTrue(ctx.show_lines)
        self.assertTrue(ctx.show_source_type)
        self.assertTrue(ctx.show_chain)
        self.assertTrue(ctx.show_overrides)
        self.assertTrue(ctx.show_targets)

    def test_format__PresetString__WorksLikeMethod(self) -> None:
        fmt_method = ProvenanceFormat(self.provenance).minimal()
        fmt_string = ProvenanceFormat(self.provenance).preset("minimal")

        ctx_method = fmt_method._ctx
        ctx_string = fmt_string._ctx

        self.assertEqual(ctx_method.show_values, ctx_string.show_values)
        self.assertEqual(ctx_method.show_chain, ctx_string.show_chain)

    def test_format__PresetWithOverride__OverrideWins(self) -> None:
        fmt = ProvenanceFormat(self.provenance).minimal().show_values()
        ctx = fmt._ctx

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
        fmt = ProvenanceFormat(self.provenance).for_path("/model.*")
        ctx = fmt._ctx

        self.assertEqual(["/model.*"], ctx.path_filters)

    def test_format__ForPathMultiple__AddsAllFilters(self) -> None:
        fmt = ProvenanceFormat(self.provenance).for_path("/model.*").for_path("/data.*")
        ctx = fmt._ctx

        self.assertEqual(["/model.*", "/data.*"], ctx.path_filters)

    def test_format__FromFile__AddsFilter(self) -> None:
        fmt = ProvenanceFormat(self.provenance).from_file("config.yaml")
        ctx = fmt._ctx

        self.assertEqual(["config.yaml"], ctx.file_filters)

    def test_format__FromFileMultiple__AddsAllFilters(self) -> None:
        fmt = ProvenanceFormat(self.provenance).from_file("*.yaml").from_file("*.json")
        ctx = fmt._ctx

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
            def render(self, model: ProvenanceDisplayModel) -> str:
                return "CUSTOM OUTPUT"

        fmt = ProvenanceFormat(self.provenance).layout(TestLayout())
        result = str(fmt)

        self.assertEqual("CUSTOM OUTPUT", result)


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
        fmt = ProvenanceFormat(self.provenance)

        # Act
        result = repr(fmt)

        # Assert
        self.assertIn("ProvenanceFormat", result)
        self.assertIn("TreeLayout", result)

    def test_format__IndentMethod__SetsIndentSize(self) -> None:
        """Test that indent() method sets indent size correctly."""
        # Arrange
        fmt = ProvenanceFormat(self.provenance).indent(4)

        # Act
        ctx = fmt._ctx

        # Assert
        self.assertEqual(4, ctx.indent_size)

    def test_format__FilterChaining__AllFiltersApplied(self) -> None:
        """Test that chaining filters adds them all."""
        # Arrange
        fmt = (
            ProvenanceFormat(self.provenance)
            .for_path("/model.*")
            .for_path("/data.*")
            .from_file("*.yaml")
            .from_file("*.json")
        )

        # Act
        ctx = fmt._ctx

        # Assert
        self.assertEqual(["/model.*", "/data.*"], ctx.path_filters)
        self.assertEqual(["*.yaml", "*.json"], ctx.file_filters)

    def test_format__PresetStringCompact__AppliesCorrectSettings(self) -> None:
        """Test that preset("compact") applies compact settings."""
        # Arrange
        fmt = ProvenanceFormat(self.provenance).preset("compact")

        # Act
        ctx = fmt._ctx

        # Assert
        self.assertTrue(ctx.show_paths)
        self.assertTrue(ctx.show_values)
        self.assertTrue(ctx.show_source_type)
        self.assertFalse(ctx.show_chain)
        self.assertFalse(ctx.show_overrides)

    def test_format__PresetStringFull__AppliesCorrectSettings(self) -> None:
        """Test that preset("full") applies full settings."""
        # Arrange
        fmt = ProvenanceFormat(self.provenance).preset("full")

        # Act
        ctx = fmt._ctx

        # Assert
        self.assertTrue(ctx.show_paths)
        self.assertTrue(ctx.show_values)
        self.assertTrue(ctx.show_source_type)
        self.assertTrue(ctx.show_chain)
        self.assertTrue(ctx.show_overrides)

    def test_format__ForPath__MutatesContext(self) -> None:
        """Test that for_path mutates the context directly."""
        # Arrange
        fmt = ProvenanceFormat(self.provenance)

        # Act
        fmt.for_path("/test")
        fmt.for_path("/test2")

        # Assert - filters are accumulated
        self.assertEqual(["/test", "/test2"], fmt._ctx.path_filters)

    def test_format__PresetThenOverride__OverrideWins(self) -> None:
        """Test that override after preset wins."""
        # Arrange
        fmt = ProvenanceFormat(self.provenance).minimal().show_values()

        # Act
        ctx = fmt._ctx

        # Assert - minimal sets show_values=False, but override sets True
        self.assertTrue(ctx.show_values)

    def test_format__OverrideThenPreset__PresetWins(self) -> None:
        """Test that preset after override wins."""
        # Arrange
        fmt = ProvenanceFormat(self.provenance).show_values().minimal()

        # Act
        ctx = fmt._ctx

        # Assert - minimal is applied after show_values, so minimal wins
        self.assertFalse(ctx.show_values)

    def test_format__EmptyProvenance__StrReturnsEmpty(self) -> None:
        """Test that formatting empty provenance returns empty string."""
        # Arrange
        empty_prov = Provenance()
        fmt = ProvenanceFormat(empty_prov)

        # Act
        result = str(fmt)

        # Assert
        self.assertEqual("", result)

    def test_format__MultipleFormatCalls__IndependentBuilders(self) -> None:
        """Test that each format() call creates an independent builder."""
        # Arrange & Act
        fmt1 = ProvenanceFormat(self.provenance)
        fmt1.hide_paths()

        fmt2 = ProvenanceFormat(self.provenance)

        # Assert - second builder should have default values
        self.assertFalse(fmt1._ctx.show_paths)
        self.assertTrue(fmt2._ctx.show_paths)


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
        fmt = ProvenanceFormat(self.provenance)

        fmt.show_deprecations()
        ctx = fmt._ctx
        self.assertTrue(ctx.show_deprecations)

        fmt.hide_deprecations()
        ctx = fmt._ctx
        self.assertFalse(ctx.show_deprecations)

    def test_format__DeprecationsPreset__SetsDeprecationsOnly(self) -> None:
        fmt = ProvenanceFormat(self.provenance).deprecations()
        ctx = fmt._ctx

        self.assertTrue(ctx.deprecations_only)
        self.assertTrue(ctx.show_deprecations)
        self.assertTrue(ctx.show_paths)
        self.assertTrue(ctx.show_values)
        self.assertFalse(ctx.show_chain)
        self.assertFalse(ctx.show_overrides)
        self.assertFalse(ctx.show_targets)

    def test_format__DeprecationsPreset__FiltersToDeprecatedOnly(self) -> None:
        result = str(ProvenanceFormat(self.provenance).deprecations())

        # Should include deprecated keys
        self.assertIn("learning_rate", result)
        self.assertIn("n_epochs", result)
        # Should NOT include non-deprecated keys
        self.assertNotIn("/model.lr", result)

    def test_format__DeprecationsPreset__ShowsDeprecationInfo(self) -> None:
        result = str(ProvenanceFormat(self.provenance).deprecations())

        # Should show deprecation details
        self.assertIn("DEPRECATED", result)
        self.assertIn("model.optimizer.lr", result)
        self.assertIn("2.0.0", result)
        self.assertIn("Use 'model.optimizer.lr' instead", result)

    def test_format__DeprecationsPreset__ShowsHeader(self) -> None:
        result = str(ProvenanceFormat(self.provenance).deprecations())

        self.assertIn("Deprecated Keys:", result)
        self.assertIn("-" * 16, result)

    def test_format__DeprecationsPreset__NoDeprecations__ShowsEmptyMessage(self) -> None:
        # Create provenance without deprecations
        builder = ProvenanceBuilder()
        builder.add("test", file="config.yaml", line=1)
        builder.set_config({"test": 42})
        empty_prov = builder.build()

        result = str(ProvenanceFormat(empty_prov).deprecations())

        self.assertEqual("No deprecated keys found.", result)

    def test_format__HideDeprecations__OmitsDeprecationInfo(self) -> None:
        result = str(ProvenanceFormat(self.provenance).hide_deprecations())

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
