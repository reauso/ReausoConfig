"""Unit tests for DiffFlatLayout."""

from __future__ import annotations

import pytest

from rconfig.diff import ConfigDiff, DiffEntry, DiffEntryType, DiffFlatLayout, DiffFormat, DiffFormatContext


def build_and_render(layout: DiffFlatLayout, diff: ConfigDiff, ctx: DiffFormatContext) -> str:
    """Helper to build display model and render with layout.

    Uses DiffFormat to build the model since filtering logic is in Format.
    """
    fmt = DiffFormat(diff)
    fmt._ctx = ctx
    model = fmt._build_model()
    return layout.render(model)


class TestDiffFlatLayout:
    """Tests for DiffFlatLayout."""

    def test_format_empty_diff(self) -> None:
        """Empty diff shows 'No differences found.'"""
        layout = DiffFlatLayout()
        diff = ConfigDiff({})
        ctx = DiffFormatContext()

        result = build_and_render(layout, diff, ctx)
        assert "No differences found" in result

    def test_format_added_entries(self) -> None:
        """Added entries have + prefix."""
        layout = DiffFlatLayout()
        entries = {
            "model.dropout": DiffEntry(
                "model.dropout", DiffEntryType.ADDED, right_value=0.1
            ),
        }
        diff = ConfigDiff(entries)
        ctx = DiffFormatContext()

        result = build_and_render(layout, diff, ctx)
        assert "+ model.dropout" in result
        assert "0.1" in result

    def test_format_removed_entries(self) -> None:
        """Removed entries have - prefix."""
        layout = DiffFlatLayout()
        entries = {
            "legacy.param": DiffEntry(
                "legacy.param", DiffEntryType.REMOVED, left_value="old"
            ),
        }
        diff = ConfigDiff(entries)
        ctx = DiffFormatContext()

        result = build_and_render(layout, diff, ctx)
        assert "- legacy.param" in result
        assert "'old'" in result

    def test_format_changed_entries(self) -> None:
        """Changed entries have ~ prefix with arrow."""
        layout = DiffFlatLayout()
        entries = {
            "model.lr": DiffEntry(
                "model.lr", DiffEntryType.CHANGED, 0.001, 0.01
            ),
        }
        diff = ConfigDiff(entries)
        ctx = DiffFormatContext()

        result = build_and_render(layout, diff, ctx)
        assert "~ model.lr" in result
        assert "0.001" in result
        assert "->" in result
        assert "0.01" in result

    def test_format_unchanged_hidden_by_default(self) -> None:
        """Unchanged entries are hidden by default."""
        layout = DiffFlatLayout()
        entries = {
            "model.layers": DiffEntry(
                "model.layers", DiffEntryType.UNCHANGED, 4, 4
            ),
        }
        diff = ConfigDiff(entries)
        ctx = DiffFormatContext()

        result = build_and_render(layout, diff, ctx)
        # Should show "No differences" since unchanged is hidden
        assert "No differences found" in result

    def test_format_unchanged_when_enabled(self) -> None:
        """Unchanged entries are shown when enabled."""
        layout = DiffFlatLayout()
        entries = {
            "model.layers": DiffEntry(
                "model.layers", DiffEntryType.UNCHANGED, 4, 4
            ),
        }
        diff = ConfigDiff(entries)
        ctx = DiffFormatContext(show_unchanged=True)

        result = build_and_render(layout, diff, ctx)
        assert "model.layers" in result
        assert "4" in result

    def test_summary_shown_by_default(self) -> None:
        """Summary statistics are shown by default."""
        layout = DiffFlatLayout()
        entries = {
            "a": DiffEntry("a", DiffEntryType.ADDED, right_value=1),
            "b": DiffEntry("b", DiffEntryType.REMOVED, left_value=2),
            "c": DiffEntry("c", DiffEntryType.CHANGED, 3, 4),
        }
        diff = ConfigDiff(entries)
        ctx = DiffFormatContext()

        result = build_and_render(layout, diff, ctx)
        assert "Added: 1" in result
        assert "Removed: 1" in result
        assert "Changed: 1" in result

    def test_summary_hidden_when_disabled(self) -> None:
        """Summary hidden when show_counts=False.

        Note: With the new architecture, show_counts is a layout decision.
        The layout always renders a summary from entries. The caller
        can choose not to include it by using a layout that doesn't
        render summaries.
        """
        layout = DiffFlatLayout()
        entries = {
            "a": DiffEntry("a", DiffEntryType.ADDED, right_value=1),
        }
        diff = ConfigDiff(entries)
        ctx = DiffFormatContext(show_counts=False)

        # Use the fluent API which respects show_counts
        result = DiffFormat(diff).hide_counts().terminal()
        # Layout derives summary from entries, so we check via Format
        assert "Added: 1" not in result

    def test_sorted_output(self) -> None:
        """Entries are sorted by path."""
        layout = DiffFlatLayout()
        entries = {
            "z.value": DiffEntry("z.value", DiffEntryType.ADDED, right_value=1),
            "a.value": DiffEntry("a.value", DiffEntryType.ADDED, right_value=2),
            "m.value": DiffEntry("m.value", DiffEntryType.ADDED, right_value=3),
        }
        diff = ConfigDiff(entries)
        ctx = DiffFormatContext(show_counts=False)

        result = build_and_render(layout, diff, ctx)
        lines = result.strip().split("\n")
        # Extract paths from lines
        paths = [line.split(":")[0].strip("+ ") for line in lines if line.startswith("+")]
        assert paths == ["a.value", "m.value", "z.value"]

    def test_hide_added(self) -> None:
        """Added entries hidden when show_added=False."""
        layout = DiffFlatLayout()
        entries = {
            "a": DiffEntry("a", DiffEntryType.ADDED, right_value=1),
            "b": DiffEntry("b", DiffEntryType.REMOVED, left_value=2),
        }
        diff = ConfigDiff(entries)
        ctx = DiffFormatContext(show_added=False, show_counts=False)

        result = build_and_render(layout, diff, ctx)
        assert "+" not in result
        assert "-" in result

    def test_hide_removed(self) -> None:
        """Removed entries hidden when show_removed=False."""
        layout = DiffFlatLayout()
        entries = {
            "a": DiffEntry("a", DiffEntryType.ADDED, right_value=1),
            "b": DiffEntry("b", DiffEntryType.REMOVED, left_value=2),
        }
        diff = ConfigDiff(entries)
        ctx = DiffFormatContext(show_removed=False, show_counts=False)

        result = build_and_render(layout, diff, ctx)
        assert "+" in result
        assert "- b" not in result

    def test_hide_changed(self) -> None:
        """Changed entries hidden when show_changed=False."""
        layout = DiffFlatLayout()
        entries = {
            "a": DiffEntry("a", DiffEntryType.ADDED, right_value=1),
            "b": DiffEntry("b", DiffEntryType.CHANGED, 2, 3),
        }
        diff = ConfigDiff(entries)
        ctx = DiffFormatContext(show_changed=False, show_counts=False)

        result = build_and_render(layout, diff, ctx)
        assert "+" in result
        assert "~" not in result

    def test_path_filter_match(self) -> None:
        """Path filter includes matching entries."""
        layout = DiffFlatLayout()
        entries = {
            "model.lr": DiffEntry("model.lr", DiffEntryType.ADDED, right_value=0.01),
            "data.batch_size": DiffEntry(
                "data.batch_size", DiffEntryType.ADDED, right_value=32
            ),
        }
        diff = ConfigDiff(entries)
        ctx = DiffFormatContext(path_filters=["model.*"], show_counts=False)

        result = build_and_render(layout, diff, ctx)
        assert "model.lr" in result
        assert "data.batch_size" not in result

    def test_path_filter_with_leading_slash(self) -> None:
        """Path filter works with /path pattern."""
        layout = DiffFlatLayout()
        entries = {
            "model.lr": DiffEntry("model.lr", DiffEntryType.ADDED, right_value=0.01),
        }
        diff = ConfigDiff(entries)
        ctx = DiffFormatContext(path_filters=["/model.*"], show_counts=False)

        result = build_and_render(layout, diff, ctx)
        assert "model.lr" in result

    def test_provenance_shown_when_enabled(self) -> None:
        """Provenance info shown when show_provenance=True."""
        from rconfig.composition import ProvenanceEntry

        layout = DiffFlatLayout()
        prov = ProvenanceEntry(value=0.01, file="config.yaml", line=10)
        entries = {
            "model.lr": DiffEntry(
                "model.lr",
                DiffEntryType.ADDED,
                right_value=0.01,
                right_provenance=prov,
            ),
        }
        diff = ConfigDiff(entries)
        ctx = DiffFormatContext(show_provenance=True, show_counts=False)

        result = build_and_render(layout, diff, ctx)
        assert "config.yaml" in result
        assert "10" in result

    def test_provenance_hidden_by_default(self) -> None:
        """Provenance info hidden by default."""
        from rconfig.composition import ProvenanceEntry

        layout = DiffFlatLayout()
        prov = ProvenanceEntry(value=0.01, file="config.yaml", line=10)
        entries = {
            "model.lr": DiffEntry(
                "model.lr",
                DiffEntryType.ADDED,
                right_value=0.01,
                right_provenance=prov,
            ),
        }
        diff = ConfigDiff(entries)
        ctx = DiffFormatContext(show_provenance=False, show_counts=False)

        result = build_and_render(layout, diff, ctx)
        # Should not contain file:line info
        assert "config.yaml:10" not in result
