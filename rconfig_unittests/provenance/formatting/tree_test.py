"""Tests for TreeLayout implementation."""

from unittest import TestCase

from rconfig.provenance import (
    InstanceRef,
    Provenance,
    ProvenanceBuilder,
    ProvenanceEntry,
    ProvenanceFormatContext,
    ProvenanceFormat,
    TreeLayout,
)
from rconfig.interpolation.evaluator import InterpolationSource


def build_and_render(layout: TreeLayout, provenance: Provenance, ctx: ProvenanceFormatContext) -> str:
    """Helper to build display model via format and render with layout."""
    fmt = ProvenanceFormat(provenance, layout)
    # Apply context settings
    fmt._ctx = ctx
    return str(fmt)


class FormatFilterTests(TestCase):
    """Tests for ProvenanceFormat filter matching."""

    def test_matchesFilters__NoFilters__MatchesEverything(self) -> None:
        """Test that entries match when no filters are set."""
        builder = ProvenanceBuilder()
        builder.add("model.lr", file="config.yaml", line=5, value=42)
        prov = builder.build()

        result = str(ProvenanceFormat(prov))

        self.assertIn("model.lr", result)

    def test_matchesFilters__PathFilterMatch__ReturnsTrue(self) -> None:
        """Test that matching path filter includes entry."""
        builder = ProvenanceBuilder()
        builder.add("model.lr", file="config.yaml", line=5, value=42)
        builder.add("data.path", file="config.yaml", line=6, value="/data")
        prov = builder.build()

        result = str(ProvenanceFormat(prov).for_path("/model.*"))

        self.assertIn("model.lr", result)
        self.assertNotIn("data.path", result)

    def test_matchesFilters__PathFilterNoMatch__ReturnsFalse(self) -> None:
        """Test that non-matching path filter excludes entry."""
        builder = ProvenanceBuilder()
        builder.add("model.lr", file="config.yaml", line=5, value=42)
        prov = builder.build()

        result = str(ProvenanceFormat(prov).for_path("/data.*"))

        self.assertNotIn("model.lr", result)

    def test_matchesFilters__FileFilterMatch__ReturnsTrue(self) -> None:
        """Test that matching file filter includes entry."""
        builder = ProvenanceBuilder()
        builder.add("model.lr", file="config.yaml", line=5, value=42)
        builder.add("data.path", file="config.json", line=6, value="/data")
        prov = builder.build()

        result = str(ProvenanceFormat(prov).from_file("*.yaml"))

        self.assertIn("model.lr", result)
        self.assertNotIn("data.path", result)

    def test_matchesFilters__FileFilterNoMatch__ReturnsFalse(self) -> None:
        """Test that non-matching file filter excludes entry."""
        builder = ProvenanceBuilder()
        builder.add("model.lr", file="config.yaml", line=5, value=42)
        prov = builder.build()

        result = str(ProvenanceFormat(prov).from_file("*.json"))

        self.assertNotIn("model.lr", result)

    def test_matchesFilters__BothFilters__MustMatchBoth(self) -> None:
        """Test that both path and file filters must match (AND logic)."""
        builder = ProvenanceBuilder()
        builder.add("model.lr", file="config.yaml", line=5, value=42)
        prov = builder.build()

        result = str(ProvenanceFormat(prov).for_path("/model.*").from_file("*.json"))

        self.assertNotIn("model.lr", result)

    def test_matchesFilters__MultiplePathFilters__ORLogic(self) -> None:
        """Test that multiple path filters use OR logic."""
        builder = ProvenanceBuilder()
        builder.add("model.lr", file="config.yaml", line=5, value=42)
        builder.add("data.path", file="config.yaml", line=6, value="/data")
        prov = builder.build()

        result = str(ProvenanceFormat(prov).for_path("/data.*").for_path("/model.*"))

        self.assertIn("model.lr", result)
        self.assertIn("data.path", result)

    def test_matchesFilters__MultipleFileFilters__ORLogic(self) -> None:
        """Test that multiple file filters use OR logic."""
        builder = ProvenanceBuilder()
        builder.add("model.lr", file="config.yaml", line=5, value=42)
        builder.add("data.path", file="config.json", line=6, value="/data")
        prov = builder.build()

        result = str(ProvenanceFormat(prov).from_file("*.json").from_file("*.yaml"))

        self.assertIn("model.lr", result)
        self.assertIn("data.path", result)

    def test_matchesFilters__GlobPatternAsterisk__MatchesWildcard(self) -> None:
        """Test that glob wildcard patterns work correctly."""
        builder = ProvenanceBuilder()
        builder.add("model.lr", file="configs/model/base.yaml", line=5, value=42)
        builder.add("other", file="configs/other.yaml", line=6, value=1)
        prov = builder.build()

        result = str(ProvenanceFormat(prov).from_file("configs/model/*.yaml"))

        self.assertIn("model.lr", result)
        self.assertNotIn("other", result)

    def test_matchesFilters__PathWithLeadingSlash__Matches(self) -> None:
        """Test that path matching works with leading slash."""
        builder = ProvenanceBuilder()
        builder.add("model.lr", file="config.yaml", line=5, value=42)
        prov = builder.build()

        result = str(ProvenanceFormat(prov).for_path("/model.lr"))

        self.assertIn("model.lr", result)

    def test_matchesFilters__PathWithoutLeadingSlash__Matches(self) -> None:
        """Test that path matching works without leading slash in filter."""
        builder = ProvenanceBuilder()
        builder.add("model.lr", file="config.yaml", line=5, value=42)
        prov = builder.build()

        result = str(ProvenanceFormat(prov).for_path("model.lr"))

        self.assertIn("model.lr", result)


class TreeLayoutRenderTests(TestCase):
    """Tests for TreeLayout rendering."""

    def setUp(self) -> None:
        self.layout = TreeLayout()

    def test_render__EmptyProvenance__ReturnsEmpty(self) -> None:
        """Test that empty provenance returns empty string."""
        provenance = Provenance()
        ctx = ProvenanceFormatContext()

        result = build_and_render(self.layout, provenance, ctx)

        self.assertEqual("", result)

    def test_render__SingleEntry__FormatsCorrectly(self) -> None:
        """Test single entry is formatted correctly."""
        builder = ProvenanceBuilder()
        builder.add("model.lr", file="config.yaml", line=5, value=0.01)
        provenance = builder.build()
        ctx = ProvenanceFormatContext()

        result = build_and_render(self.layout, provenance, ctx)

        self.assertIn("/model.lr", result)
        self.assertIn("0.01", result)
        self.assertIn("config.yaml:5", result)

    def test_render__MultipleEntries__SeparatesWithBlankLine(self) -> None:
        """Test multiple entries are separated by blank lines."""
        builder = ProvenanceBuilder()
        builder.add("a", file="a.yaml", line=1, value=1)
        builder.add("b", file="b.yaml", line=2, value=2)
        provenance = builder.build()
        ctx = ProvenanceFormatContext()

        result = build_and_render(self.layout, provenance, ctx)

        self.assertIn("\n\n", result)

    def test_render__FilterApplied__FiltersEntries(self) -> None:
        """Test that path filter is applied to entries."""
        builder = ProvenanceBuilder()
        builder.add("model.lr", file="config.yaml", line=1, value=0.01)
        builder.add("data.path", file="config.yaml", line=2, value="/data")
        provenance = builder.build()
        ctx = ProvenanceFormatContext(path_filters=["/model.*"])

        result = build_and_render(self.layout, provenance, ctx)

        self.assertIn("/model.lr", result)
        self.assertNotIn("/data.path", result)

    def test_render__ShowPathsTrue__IncludesPath(self) -> None:
        """Test that path is included when show_paths is True."""
        builder = ProvenanceBuilder()
        builder.add("model.lr", file="config.yaml", line=5, value=42)
        provenance = builder.build()
        ctx = ProvenanceFormatContext(show_paths=True)

        result = build_and_render(self.layout, provenance, ctx)

        self.assertIn("/model.lr", result)

    def test_render__ShowPathsFalse__OmitsPath(self) -> None:
        """Test that path is omitted when show_paths is False."""
        builder = ProvenanceBuilder()
        builder.add("model.lr", file="config.yaml", line=5, value=42)
        provenance = builder.build()
        ctx = ProvenanceFormatContext(show_paths=False)

        result = build_and_render(self.layout, provenance, ctx)

        self.assertNotIn("/model.lr", result)

    def test_render__ShowValuesTrue__IncludesValue(self) -> None:
        """Test that value is included when show_values is True."""
        builder = ProvenanceBuilder()
        builder.add("model.lr", file="config.yaml", line=5, value=42)
        provenance = builder.build()
        ctx = ProvenanceFormatContext(show_values=True)

        result = build_and_render(self.layout, provenance, ctx)

        self.assertIn("42", result)

    def test_render__CliSourceWithArg__ShowsCliAndArg(self) -> None:
        """Test that CLI source shows CLI: and the argument."""
        builder = ProvenanceBuilder()
        builder.add(
            "model.lr",
            file="<override>",
            line=0,
            value=0.01,
            source_type="cli",
            cli_arg="--model.lr=0.01",
        )
        provenance = builder.build()
        ctx = ProvenanceFormatContext(show_source_type=True)

        result = build_and_render(self.layout, provenance, ctx)

        self.assertIn("CLI", result)
        self.assertIn("--model.lr=0.01", result)

    def test_render__EnvSourceWithVar__ShowsEnvAndVar(self) -> None:
        """Test that env source shows env: and the variable name."""
        builder = ProvenanceBuilder()
        builder.add(
            "data.path",
            file="<override>",
            line=0,
            value="/data",
            source_type="env",
            env_var="DATA_PATH",
        )
        provenance = builder.build()
        ctx = ProvenanceFormatContext(show_source_type=True)

        result = build_and_render(self.layout, provenance, ctx)

        self.assertIn("env", result)
        self.assertIn("DATA_PATH", result)

    def test_render__FileSourceWithLocation__ShowsLocation(self) -> None:
        """Test that file source shows file:line location."""
        builder = ProvenanceBuilder()
        builder.add("model.lr", file="config.yaml", line=5, value=42)
        provenance = builder.build()
        ctx = ProvenanceFormatContext(show_files=True, show_lines=True)

        result = build_and_render(self.layout, provenance, ctx)

        self.assertIn("config.yaml:5", result)

    def test_render__WithInterpolation__ShowsInterpolationSection(self) -> None:
        """Test that entry with interpolation shows Interpolation: section."""
        builder = ProvenanceBuilder()
        builder.add(
            "model.lr",
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
        provenance = builder.build()
        ctx = ProvenanceFormatContext(show_chain=True)

        result = build_and_render(self.layout, provenance, ctx)

        self.assertIn("Interpolation:", result)
        self.assertIn("/defaults.lr * 2", result)

    def test_render__WithInstanceChain__ShowsInstances(self) -> None:
        """Test that entry with instance chain shows Instance: lines."""
        builder = ProvenanceBuilder()
        builder.add(
            "service.db",
            file="app.yaml",
            line=10,
            value={"host": "localhost"},
            instance=[
                InstanceRef(path="/shared.database", file="shared.yaml", line=5),
            ],
        )
        provenance = builder.build()
        ctx = ProvenanceFormatContext(show_chain=True)

        result = build_and_render(self.layout, provenance, ctx)

        self.assertIn("Instance:", result)
        self.assertIn("/shared.database", result)
        self.assertIn("shared.yaml:5", result)

    def test_render__WithOverrode__ShowsOverrideSection(self) -> None:
        """Test that entry with overrode shows Overrode: line."""
        builder = ProvenanceBuilder()
        builder.add(
            "model.lr",
            file="override.yaml",
            line=5,
            value=42,
            overrode="base.yaml:10",
        )
        provenance = builder.build()
        ctx = ProvenanceFormatContext(show_overrides=True)

        result = build_and_render(self.layout, provenance, ctx)

        self.assertIn("Overrode:", result)
        self.assertIn("base.yaml:10", result)

    def test_render__HideChain__OmitsInterpolationAndInstance(self) -> None:
        """Test that show_chain=False hides interpolation and instance info."""
        builder = ProvenanceBuilder()
        builder.add(
            "model.lr",
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
        provenance = builder.build()
        ctx = ProvenanceFormatContext(show_chain=False)

        result = build_and_render(self.layout, provenance, ctx)

        self.assertNotIn("Interpolation:", result)
        self.assertNotIn("Instance:", result)

    def test_render__HideOverrides__OmitsOverrideSection(self) -> None:
        """Test that show_overrides=False hides override info."""
        builder = ProvenanceBuilder()
        builder.add(
            "model.lr",
            file="override.yaml",
            line=5,
            value=42,
            overrode="base.yaml:10",
        )
        provenance = builder.build()
        ctx = ProvenanceFormatContext(show_overrides=False)

        result = build_and_render(self.layout, provenance, ctx)

        self.assertNotIn("Overrode:", result)

    def test_render__AllHidden__ReturnsMinimal(self) -> None:
        """Test that hiding all options returns minimal output."""
        builder = ProvenanceBuilder()
        builder.add("model.lr", file="config.yaml", line=5, value=42)
        provenance = builder.build()
        ctx = ProvenanceFormatContext(
            show_paths=False,
            show_values=False,
            show_files=False,
            show_lines=False,
            show_source_type=False,
            show_chain=False,
            show_overrides=False,
        )

        result = build_and_render(self.layout, provenance, ctx)

        self.assertEqual("", result)


class TreeLayoutProgrammaticSourceTests(TestCase):
    """Tests for programmatic source type formatting."""

    def setUp(self) -> None:
        self.layout = TreeLayout()

    def test_render__ProgrammaticSourceWithoutCliArg__ShowsSourceType(self) -> None:
        """Test that programmatic source without cli_arg shows just source type."""
        builder = ProvenanceBuilder()
        builder.add(
            "test",
            file="<override>",
            line=0,
            value=42,
            source_type="programmatic",
        )
        provenance = builder.build()
        ctx = ProvenanceFormatContext(show_source_type=True)

        result = build_and_render(self.layout, provenance, ctx)

        self.assertIn("programmatic", result)

    def test_render__EnvSourceWithoutEnvVar__ShowsSourceType(self) -> None:
        """Test that env source without env_var shows just source type."""
        builder = ProvenanceBuilder()
        builder.add(
            "test",
            file="<override>",
            line=0,
            value="/data",
            source_type="env",
        )
        provenance = builder.build()
        ctx = ProvenanceFormatContext(show_source_type=True)

        result = build_and_render(self.layout, provenance, ctx)

        self.assertIn("env", result)


class TreeLayoutTargetDisplayTests(TestCase):
    """Tests for TreeLayout target info display."""

    def setUp(self) -> None:
        self.layout = TreeLayout()

    def _build_provenance_with_entry(self, path: str, entry: ProvenanceEntry) -> Provenance:
        """Build a Provenance with a single entry."""
        return Provenance({path: entry})

    def test_render__WithTargetInfo__ShowsTargetLine(self) -> None:
        """Test that target info is displayed."""
        entry = ProvenanceEntry(
            file="config.yaml",
            line=5,
            target_name="model",
            target_class="MyModel",
            target_module="myapp.models",
        )
        provenance = self._build_provenance_with_entry("model", entry)
        ctx = ProvenanceFormatContext(show_targets=True)

        result = build_and_render(self.layout, provenance, ctx)

        self.assertIn("Target: model -> myapp.models.MyModel", result)

    def test_render__WithAutoRegisteredTarget__ShowsAutoRegisteredMarker(self) -> None:
        """Test that auto-registered targets are marked."""
        entry = ProvenanceEntry(
            file="config.yaml",
            line=5,
            target_name="model",
            target_class="MyModel",
            target_module="myapp.models",
            target_auto_registered=True,
        )
        provenance = self._build_provenance_with_entry("model", entry)
        ctx = ProvenanceFormatContext(show_targets=True)

        result = build_and_render(self.layout, provenance, ctx)

        self.assertIn("(auto-registered)", result)

    def test_render__UnregisteredTarget__ShowsNotRegistered(self) -> None:
        """Test that unregistered targets show 'not registered'."""
        entry = ProvenanceEntry(
            file="config.yaml",
            line=5,
            target_name="unknown",
        )
        provenance = self._build_provenance_with_entry("model", entry)
        ctx = ProvenanceFormatContext(show_targets=True)

        result = build_and_render(self.layout, provenance, ctx)

        self.assertIn("Target: unknown (not registered)", result)

    def test_render__ShowTargetsFalse__OmitsTargetLine(self) -> None:
        """Test that targets are hidden when show_targets is False."""
        entry = ProvenanceEntry(
            file="config.yaml",
            line=5,
            target_name="model",
            target_class="MyModel",
            target_module="myapp.models",
        )
        provenance = self._build_provenance_with_entry("model", entry)
        ctx = ProvenanceFormatContext(show_targets=False)

        result = build_and_render(self.layout, provenance, ctx)

        self.assertNotIn("Target:", result)

    def test_render__NoTargetName__OmitsTargetLine(self) -> None:
        """Test that entries without target_name don't show Target line."""
        builder = ProvenanceBuilder()
        builder.add("model.layers", file="config.yaml", line=5)
        provenance = builder.build()
        ctx = ProvenanceFormatContext(show_targets=True)

        result = build_and_render(self.layout, provenance, ctx)

        self.assertNotIn("Target:", result)

    def test_render__ClassWithoutModule__FormatsCorrectly(self) -> None:
        """Test target formatting when class is present but module is None."""
        entry = ProvenanceEntry(
            file="config.yaml",
            line=5,
            target_name="model",
            target_class="MyModel",
        )
        provenance = self._build_provenance_with_entry("model", entry)
        ctx = ProvenanceFormatContext(show_targets=True)

        result = build_and_render(self.layout, provenance, ctx)

        self.assertIn("Target: model -> MyModel", result)


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

    def test_render__WithDeprecation__ShowsDeprecatedMarker(self) -> None:
        ctx = ProvenanceFormatContext()

        result = build_and_render(self.layout, self.provenance, ctx)

        self.assertIn("DEPRECATED", result)

    def test_render__WithNewKey__ShowsNewKeyInArrow(self) -> None:
        ctx = ProvenanceFormatContext()

        result = build_and_render(self.layout, self.provenance, ctx)

        self.assertIn("-> new_key", result)

    def test_render__WithRemoveIn__ShowsVersion(self) -> None:
        ctx = ProvenanceFormatContext()

        result = build_and_render(self.layout, self.provenance, ctx)

        self.assertIn("remove in 3.0.0", result)

    def test_render__WithMessage__ShowsMessage(self) -> None:
        ctx = ProvenanceFormatContext()

        result = build_and_render(self.layout, self.provenance, ctx)

        self.assertIn("Message: Custom deprecation message", result)

    def test_render__HideDeprecations__OmitsDeprecationInfo(self) -> None:
        ctx = ProvenanceFormatContext(show_deprecations=False)

        result = build_and_render(self.layout, self.provenance, ctx)

        self.assertNotIn("DEPRECATED", result)
        self.assertNotIn("new_key", result)

    def test_render__MinimalDeprecation__ShowsOnlyDeprecated(self) -> None:
        from rconfig.deprecation.info import DeprecationInfo

        builder = ProvenanceBuilder()
        builder.add(
            "simple",
            file="config.yaml",
            line=10,
            value="val",
            deprecation=DeprecationInfo(pattern="simple"),
        )
        provenance = builder.build()
        ctx = ProvenanceFormatContext()

        result = build_and_render(self.layout, provenance, ctx)

        self.assertIn("DEPRECATED", result)
        self.assertNotIn("->", result)
        self.assertNotIn("remove in", result)
        self.assertNotIn("Message:", result)

    def test_render__DeprecationsOnly__FiltersCorrectly(self) -> None:
        from rconfig.deprecation.info import DeprecationInfo

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

        result = build_and_render(self.layout, prov, ctx)

        self.assertIn("old_key", result)
        self.assertNotIn("normal", result)

    def test_render__DeprecationsOnly__AddsHeader(self) -> None:
        ctx = ProvenanceFormatContext(deprecations_only=True)

        result = build_and_render(self.layout, self.provenance, ctx)

        self.assertIn("Deprecated Keys:", result)

    def test_render__DeprecationsOnlyEmpty__ShowsMessage(self) -> None:
        builder = ProvenanceBuilder()
        builder.add("normal", file="config.yaml", line=1)
        builder.set_config({"normal": 42})
        empty_prov = builder.build()
        ctx = ProvenanceFormatContext(deprecations_only=True)

        result = build_and_render(self.layout, empty_prov, ctx)

        self.assertEqual("No deprecated keys found.", result)


class TreeLayoutFormatValueTests(TestCase):
    """Tests for format_value utility function (used by TreeLayout)."""

    def test_formatValue__LongList__Truncates(self) -> None:
        """Test that long lists are truncated with ellipsis."""
        from rconfig._internal.format_utils import format_value

        long_list = list(range(100))

        result = format_value(long_list)

        if len(str(long_list)) > 50:
            self.assertIn("...", result)
            self.assertLessEqual(len(result), 50)

    def test_formatValue__LongDict__Truncates(self) -> None:
        """Test that long dicts are truncated with ellipsis."""
        from rconfig._internal.format_utils import format_value

        long_dict = {f"key{i}": i for i in range(100)}

        result = format_value(long_dict)

        if len(str(long_dict)) > 50:
            self.assertIn("...", result)

    def test_formatValue__ShortList__NoTruncation(self) -> None:
        """Test that short lists are not truncated."""
        from rconfig._internal.format_utils import format_value

        short_list = [1, 2, 3]

        result = format_value(short_list)

        self.assertEqual("[1, 2, 3]", result)

    def test_formatValue__None__ReturnsNull(self) -> None:
        """Test that None value is formatted as 'null'."""
        from rconfig._internal.format_utils import format_value

        result = format_value(None)

        self.assertEqual(result, "null")

    def test_formatValue__BoolTrue__ReturnsTrue(self) -> None:
        """Test that True is formatted as 'true'."""
        from rconfig._internal.format_utils import format_value

        result = format_value(True)

        self.assertEqual(result, "true")

    def test_formatValue__BoolFalse__ReturnsFalse(self) -> None:
        """Test that False is formatted as 'false'."""
        from rconfig._internal.format_utils import format_value

        result = format_value(False)

        self.assertEqual(result, "false")

    def test_formatValue__String__ReturnsQuotedRepr(self) -> None:
        """Test that strings are formatted with quotes."""
        from rconfig._internal.format_utils import format_value

        result = format_value("hello")

        self.assertEqual(result, "'hello'")

    def test_formatValue__Integer__ReturnsStringified(self) -> None:
        """Test that integers are formatted correctly."""
        from rconfig._internal.format_utils import format_value

        result = format_value(42)

        self.assertEqual(result, "42")
