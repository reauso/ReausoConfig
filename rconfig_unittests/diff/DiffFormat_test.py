"""Unit tests for DiffFormat fluent builder."""

from __future__ import annotations

import pytest

from rconfig.diff import (
    ConfigDiff,
    DiffEntry,
    DiffEntryType,
    DiffFlatLayout,
    DiffFormat,
    DiffFormatContext,
    DiffLayout,
    DiffMarkdownLayout,
    DiffTreeLayout,
)
from rconfig.diff.formatting.model import DiffDisplayModel


class TestDiffFormatShowHideToggles:
    """Tests for show/hide toggle methods."""

    @pytest.fixture
    def diff(self) -> ConfigDiff:
        """Create a sample diff for testing."""
        entries = {
            "a": DiffEntry("a", DiffEntryType.ADDED, right_value=1),
            "b": DiffEntry("b", DiffEntryType.REMOVED, left_value=2),
            "c": DiffEntry("c", DiffEntryType.CHANGED, 3, 4),
            "d": DiffEntry("d", DiffEntryType.UNCHANGED, 5, 5),
        }
        return ConfigDiff(entries)

    def test_show_paths(self, diff: ConfigDiff) -> None:
        """show_paths enables path display."""
        fmt = DiffFormat(diff)
        fmt.hide_paths().show_paths()
        assert fmt._ctx.show_paths is True

    def test_hide_paths(self, diff: ConfigDiff) -> None:
        """hide_paths disables path display."""
        fmt = DiffFormat(diff)
        fmt.hide_paths()
        assert fmt._ctx.show_paths is False

    def test_show_values(self, diff: ConfigDiff) -> None:
        """show_values enables value display."""
        fmt = DiffFormat(diff)
        fmt.hide_values().show_values()
        assert fmt._ctx.show_values is True

    def test_hide_values(self, diff: ConfigDiff) -> None:
        """hide_values disables value display."""
        fmt = DiffFormat(diff)
        fmt.hide_values()
        assert fmt._ctx.show_values is False

    def test_show_files(self, diff: ConfigDiff) -> None:
        """show_files enables file display."""
        fmt = DiffFormat(diff)
        fmt.hide_files().show_files()
        assert fmt._ctx.show_files is True

    def test_hide_files(self, diff: ConfigDiff) -> None:
        """hide_files disables file display."""
        fmt = DiffFormat(diff)
        fmt.hide_files()
        assert fmt._ctx.show_files is False

    def test_show_lines(self, diff: ConfigDiff) -> None:
        """show_lines enables line display."""
        fmt = DiffFormat(diff)
        fmt.hide_lines().show_lines()
        assert fmt._ctx.show_lines is True

    def test_hide_lines(self, diff: ConfigDiff) -> None:
        """hide_lines disables line display."""
        fmt = DiffFormat(diff)
        fmt.hide_lines()
        assert fmt._ctx.show_lines is False

    def test_show_provenance(self, diff: ConfigDiff) -> None:
        """show_provenance enables provenance display."""
        fmt = DiffFormat(diff)
        fmt.show_provenance()
        assert fmt._ctx.show_provenance is True

    def test_hide_provenance(self, diff: ConfigDiff) -> None:
        """hide_provenance disables provenance display."""
        fmt = DiffFormat(diff)
        fmt.show_provenance().hide_provenance()
        assert fmt._ctx.show_provenance is False

    def test_show_unchanged(self, diff: ConfigDiff) -> None:
        """show_unchanged enables unchanged entry display."""
        fmt = DiffFormat(diff)
        fmt.show_unchanged()
        assert fmt._ctx.show_unchanged is True

    def test_hide_unchanged(self, diff: ConfigDiff) -> None:
        """hide_unchanged disables unchanged entry display."""
        fmt = DiffFormat(diff)
        fmt.show_unchanged().hide_unchanged()
        assert fmt._ctx.show_unchanged is False

    def test_show_added(self, diff: ConfigDiff) -> None:
        """show_added enables added entry display."""
        fmt = DiffFormat(diff)
        fmt.hide_added().show_added()
        assert fmt._ctx.show_added is True

    def test_hide_added(self, diff: ConfigDiff) -> None:
        """hide_added disables added entry display."""
        fmt = DiffFormat(diff)
        fmt.hide_added()
        assert fmt._ctx.show_added is False

    def test_show_removed(self, diff: ConfigDiff) -> None:
        """show_removed enables removed entry display."""
        fmt = DiffFormat(diff)
        fmt.hide_removed().show_removed()
        assert fmt._ctx.show_removed is True

    def test_hide_removed(self, diff: ConfigDiff) -> None:
        """hide_removed disables removed entry display."""
        fmt = DiffFormat(diff)
        fmt.hide_removed()
        assert fmt._ctx.show_removed is False

    def test_show_changed(self, diff: ConfigDiff) -> None:
        """show_changed enables changed entry display."""
        fmt = DiffFormat(diff)
        fmt.hide_changed().show_changed()
        assert fmt._ctx.show_changed is True

    def test_hide_changed(self, diff: ConfigDiff) -> None:
        """hide_changed disables changed entry display."""
        fmt = DiffFormat(diff)
        fmt.hide_changed()
        assert fmt._ctx.show_changed is False

    def test_show_counts(self, diff: ConfigDiff) -> None:
        """show_counts enables summary statistics."""
        fmt = DiffFormat(diff)
        fmt.hide_counts().show_counts()
        assert fmt._ctx.show_counts is True

    def test_hide_counts(self, diff: ConfigDiff) -> None:
        """hide_counts disables summary statistics."""
        fmt = DiffFormat(diff)
        fmt.hide_counts()
        assert fmt._ctx.show_counts is False

    def test_chaining(self, diff: ConfigDiff) -> None:
        """Toggle methods return self for chaining."""
        fmt = DiffFormat(diff)
        result = (
            fmt.show_paths()
            .hide_values()
            .show_provenance()
            .hide_unchanged()
        )
        assert result is fmt


class TestDiffFormatPresets:
    """Tests for preset methods."""

    @pytest.fixture
    def diff(self) -> ConfigDiff:
        """Create a sample diff for testing."""
        entries = {"a": DiffEntry("a", DiffEntryType.ADDED, right_value=1)}
        return ConfigDiff(entries)

    def test_changes_only_preset(self, diff: ConfigDiff) -> None:
        """changes_only preset shows only changes."""
        fmt = DiffFormat(diff)
        fmt.changes_only()

        assert fmt._ctx.show_added is True
        assert fmt._ctx.show_removed is True
        assert fmt._ctx.show_changed is True
        assert fmt._ctx.show_unchanged is False
        assert fmt._ctx.show_counts is True

    def test_with_context_preset(self, diff: ConfigDiff) -> None:
        """with_context preset shows changes plus unchanged."""
        fmt = DiffFormat(diff)
        fmt.with_context()

        assert fmt._ctx.show_added is True
        assert fmt._ctx.show_removed is True
        assert fmt._ctx.show_changed is True
        assert fmt._ctx.show_unchanged is True
        assert fmt._ctx.show_counts is True

    def test_full_preset(self, diff: ConfigDiff) -> None:
        """full preset shows everything including provenance."""
        fmt = DiffFormat(diff)
        fmt.full()

        assert fmt._ctx.show_added is True
        assert fmt._ctx.show_removed is True
        assert fmt._ctx.show_changed is True
        assert fmt._ctx.show_unchanged is True
        assert fmt._ctx.show_provenance is True
        assert fmt._ctx.show_counts is True

    def test_summary_preset(self, diff: ConfigDiff) -> None:
        """summary preset shows only counts."""
        fmt = DiffFormat(diff)
        fmt.summary()

        assert fmt._ctx.show_added is False
        assert fmt._ctx.show_removed is False
        assert fmt._ctx.show_changed is False
        assert fmt._ctx.show_unchanged is False
        assert fmt._ctx.show_counts is True

    def test_preset_method(self, diff: ConfigDiff) -> None:
        """preset() method applies named presets."""
        fmt = DiffFormat(diff)

        fmt.preset("full")
        assert fmt._ctx.show_provenance is True

        fmt.preset("summary")
        assert fmt._ctx.show_added is False

    def test_preset_chaining(self, diff: ConfigDiff) -> None:
        """Preset methods return self for chaining."""
        fmt = DiffFormat(diff)
        result = fmt.changes_only()
        assert result is fmt


class TestDiffFormatFiltering:
    """Tests for filtering methods."""

    @pytest.fixture
    def diff(self) -> ConfigDiff:
        """Create a sample diff for testing."""
        entries = {"a": DiffEntry("a", DiffEntryType.ADDED, right_value=1)}
        return ConfigDiff(entries)

    def test_for_path(self, diff: ConfigDiff) -> None:
        """for_path adds path filter."""
        fmt = DiffFormat(diff)
        fmt.for_path("model.*")

        assert "model.*" in fmt._ctx.path_filters

    def test_for_path_multiple(self, diff: ConfigDiff) -> None:
        """Multiple for_path calls accumulate."""
        fmt = DiffFormat(diff)
        fmt.for_path("model.*").for_path("data.*")

        assert "model.*" in fmt._ctx.path_filters
        assert "data.*" in fmt._ctx.path_filters

    def test_from_file(self, diff: ConfigDiff) -> None:
        """from_file adds file filter."""
        fmt = DiffFormat(diff)
        fmt.from_file("*.yaml")

        assert "*.yaml" in fmt._ctx.file_filters

    def test_from_file_multiple(self, diff: ConfigDiff) -> None:
        """Multiple from_file calls accumulate."""
        fmt = DiffFormat(diff)
        fmt.from_file("*.yaml").from_file("*.json")

        assert "*.yaml" in fmt._ctx.file_filters
        assert "*.json" in fmt._ctx.file_filters

    def test_filter_chaining(self, diff: ConfigDiff) -> None:
        """Filter methods return self for chaining."""
        fmt = DiffFormat(diff)
        result = fmt.for_path("*").from_file("*")
        assert result is fmt


class TestDiffFormatLayout:
    """Tests for layout method."""

    @pytest.fixture
    def diff(self) -> ConfigDiff:
        """Create a sample diff for testing."""
        entries = {"a": DiffEntry("a", DiffEntryType.ADDED, right_value=1)}
        return ConfigDiff(entries)

    def test_default_layout_is_flat(self, diff: ConfigDiff) -> None:
        """Default layout is DiffFlatLayout when _get_layout() is called."""
        fmt = DiffFormat(diff)
        # Layout is None until _get_layout() is called
        assert fmt._layout is None
        # When _get_layout() is called, it returns DiffFlatLayout
        layout = fmt._get_layout()
        assert isinstance(layout, DiffFlatLayout)

    def test_set_custom_layout(self, diff: ConfigDiff) -> None:
        """layout() sets custom layout."""

        class CustomLayout(DiffLayout):
            def render(self, model: DiffDisplayModel) -> str:
                return "custom"

        fmt = DiffFormat(diff)
        fmt.layout(CustomLayout())
        assert isinstance(fmt._layout, CustomLayout)

    def test_layout_chaining(self, diff: ConfigDiff) -> None:
        """layout() returns self for chaining."""
        fmt = DiffFormat(diff)
        result = fmt.layout(DiffTreeLayout())
        assert result is fmt


class TestDiffFormatOutputMethods:
    """Tests for output format methods."""

    @pytest.fixture
    def diff(self) -> ConfigDiff:
        """Create a sample diff for testing."""
        entries = {
            "a": DiffEntry("a", DiffEntryType.ADDED, right_value=1),
            "b": DiffEntry("b", DiffEntryType.CHANGED, 2, 3),
        }
        return ConfigDiff(entries)

    def test_terminal(self, diff: ConfigDiff) -> None:
        """terminal() returns flat layout output."""
        fmt = DiffFormat(diff)
        result = fmt.terminal()

        assert isinstance(result, str)
        assert "+ a" in result
        assert "~ b" in result

    def test_tree(self, diff: ConfigDiff) -> None:
        """tree() returns tree layout output."""
        fmt = DiffFormat(diff)
        result = fmt.tree()

        assert isinstance(result, str)
        assert "ConfigDiff:" in result
        assert "Added:" in result

    def test_markdown(self, diff: ConfigDiff) -> None:
        """markdown() returns markdown table output."""
        fmt = DiffFormat(diff)
        result = fmt.markdown()

        assert isinstance(result, str)
        assert "| Type |" in result
        assert "| + |" in result

    def test_json(self, diff: ConfigDiff) -> None:
        """json() returns dict output."""
        fmt = DiffFormat(diff)
        result = fmt.json()

        assert isinstance(result, dict)
        assert "a" in result
        assert result["a"]["diff_type"] == "added"

    def test_str(self, diff: ConfigDiff) -> None:
        """str() returns formatted string with current layout."""
        fmt = DiffFormat(diff)
        result = str(fmt)

        assert isinstance(result, str)
        # Default layout is flat
        assert "+ a" in result

    def test_terminal_uses_flat_layout(self, diff: ConfigDiff) -> None:
        """terminal() switches to FlatLayout."""
        fmt = DiffFormat(diff)
        fmt.layout(DiffTreeLayout())  # Set different layout first
        result = fmt.terminal()

        # Should be flat output, not tree
        assert "ConfigDiff:" not in result or "+ a" in result

    def test_options_apply_to_output(self, diff: ConfigDiff) -> None:
        """Options affect the output."""
        fmt = DiffFormat(diff)
        result = fmt.hide_counts().terminal()

        # Summary should not appear
        assert "Added:" not in result or "Added: 1" not in result


class TestDiffFormatIntegration:
    """Integration tests for complete workflows."""

    def test_full_workflow(self) -> None:
        """Complete workflow with multiple options."""
        entries = {
            "model.lr": DiffEntry("model.lr", DiffEntryType.ADDED, right_value=0.01),
            "model.layers": DiffEntry(
                "model.layers", DiffEntryType.UNCHANGED, 4, 4
            ),
            "data.batch_size": DiffEntry(
                "data.batch_size", DiffEntryType.CHANGED, 32, 64
            ),
        }
        diff = ConfigDiff(entries)

        result = (
            DiffFormat(diff)
            .show_unchanged()
            .for_path("model.*")
            .hide_counts()
            .terminal()
        )

        # Should include model.* entries
        assert "model.lr" in result
        assert "model.layers" in result
        # Should exclude data.*
        assert "data.batch_size" not in result

    def test_preset_then_override(self) -> None:
        """Can apply preset then override specific settings."""
        entries = {
            "a": DiffEntry("a", DiffEntryType.ADDED, right_value=1),
        }
        diff = ConfigDiff(entries)

        # Start with full preset, then hide provenance
        fmt = DiffFormat(diff).full().hide_provenance()

        assert fmt._ctx.show_unchanged is True  # From preset
        assert fmt._ctx.show_provenance is False  # Overridden
