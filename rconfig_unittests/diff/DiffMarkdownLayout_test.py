"""Unit tests for DiffMarkdownLayout."""

from __future__ import annotations

import pytest

from rconfig.diff import (
    ConfigDiff,
    DiffEntry,
    DiffEntryType,
    DiffFormat,
    DiffFormatContext,
    DiffMarkdownLayout,
)


def build_and_render(layout: DiffMarkdownLayout, diff: ConfigDiff, ctx: DiffFormatContext) -> str:
    """Helper to build display model and render with layout.

    Uses DiffFormat to build the model since filtering logic is in Format.
    """
    fmt = DiffFormat(diff)
    fmt._ctx = ctx
    model = fmt._build_model()
    return layout.render(model)


class TestDiffMarkdownLayout:
    """Tests for DiffMarkdownLayout."""

    def test_format_empty_diff(self) -> None:
        """Empty diff shows italic message."""
        layout = DiffMarkdownLayout()
        diff = ConfigDiff({})
        ctx = DiffFormatContext()

        result = build_and_render(layout, diff, ctx)
        assert "_No differences found._" in result

    def test_table_has_header(self) -> None:
        """Output has markdown table header."""
        layout = DiffMarkdownLayout()
        entries = {
            "a": DiffEntry("a", DiffEntryType.ADDED, right_value=1),
        }
        diff = ConfigDiff(entries)
        ctx = DiffFormatContext()

        result = build_and_render(layout, diff, ctx)
        assert "| Type |" in result
        assert "| Path |" in result

    def test_table_has_separator(self) -> None:
        """Output has markdown table separator line."""
        layout = DiffMarkdownLayout()
        entries = {
            "a": DiffEntry("a", DiffEntryType.ADDED, right_value=1),
        }
        diff = ConfigDiff(entries)
        ctx = DiffFormatContext()

        result = build_and_render(layout, diff, ctx)
        lines = result.split("\n")
        # Second line should be separator
        assert lines[1].startswith("|")
        assert "------" in lines[1]

    def test_added_entry_row(self) -> None:
        """Added entry shows + in Type column."""
        layout = DiffMarkdownLayout()
        entries = {
            "model.dropout": DiffEntry(
                "model.dropout", DiffEntryType.ADDED, right_value=0.1
            ),
        }
        diff = ConfigDiff(entries)
        ctx = DiffFormatContext()

        result = build_and_render(layout, diff, ctx)
        # Find the data row (not header or separator)
        lines = result.split("\n")
        data_row = next(line for line in lines[2:] if "model.dropout" in line)
        assert "| + |" in data_row
        # Old value should be "-"
        parts = data_row.split("|")
        assert "-" in parts[3].strip()  # Old Value column
        assert "0.1" in parts[4].strip()  # New Value column

    def test_removed_entry_row(self) -> None:
        """Removed entry shows - in Type column."""
        layout = DiffMarkdownLayout()
        entries = {
            "legacy.param": DiffEntry(
                "legacy.param", DiffEntryType.REMOVED, left_value="old"
            ),
        }
        diff = ConfigDiff(entries)
        ctx = DiffFormatContext()

        result = build_and_render(layout, diff, ctx)
        lines = result.split("\n")
        data_row = next(line for line in lines[2:] if "legacy.param" in line)
        assert "| - |" in data_row
        parts = data_row.split("|")
        assert "'old'" in parts[3].strip()  # Old Value column
        assert parts[4].strip() == "-"  # New Value column (empty marker)

    def test_changed_entry_row(self) -> None:
        """Changed entry shows ~ in Type column."""
        layout = DiffMarkdownLayout()
        entries = {
            "model.lr": DiffEntry(
                "model.lr", DiffEntryType.CHANGED, 0.001, 0.01
            ),
        }
        diff = ConfigDiff(entries)
        ctx = DiffFormatContext()

        result = build_and_render(layout, diff, ctx)
        lines = result.split("\n")
        data_row = next(line for line in lines[2:] if "model.lr" in line)
        assert "| ~ |" in data_row
        parts = data_row.split("|")
        assert "0.001" in parts[3].strip()  # Old Value column
        assert "0.01" in parts[4].strip()  # New Value column

    def test_unchanged_entry_row(self) -> None:
        """Unchanged entry shows space in Type column."""
        layout = DiffMarkdownLayout()
        entries = {
            "model.layers": DiffEntry(
                "model.layers", DiffEntryType.UNCHANGED, 4, 4
            ),
        }
        diff = ConfigDiff(entries)
        ctx = DiffFormatContext(show_unchanged=True)

        result = build_and_render(layout, diff, ctx)
        lines = result.split("\n")
        data_row = next(line for line in lines[2:] if "model.layers" in line)
        # Type column should have space
        parts = data_row.split("|")
        assert parts[1].strip() == ""  # Type column is empty for unchanged

    def test_summary_in_bold(self) -> None:
        """Summary is in bold markdown format."""
        layout = DiffMarkdownLayout()
        entries = {
            "a": DiffEntry("a", DiffEntryType.ADDED, right_value=1),
        }
        diff = ConfigDiff(entries)
        ctx = DiffFormatContext()

        result = build_and_render(layout, diff, ctx)
        assert "**Summary:**" in result

    def test_summary_hidden_when_disabled(self) -> None:
        """Summary hidden when show_counts=False.

        Note: Layout always calculates summary from entries.
        Use the fluent API to test the Format behavior.
        """
        entries = {
            "a": DiffEntry("a", DiffEntryType.ADDED, right_value=1),
        }
        diff = ConfigDiff(entries)

        result = DiffFormat(diff).hide_counts().markdown()
        assert "**Summary:**" not in result

    def test_escapes_pipe_characters(self) -> None:
        """Pipe characters in values are escaped."""
        layout = DiffMarkdownLayout()
        entries = {
            "cmd": DiffEntry(
                "cmd", DiffEntryType.ADDED, right_value="a|b|c"
            ),
        }
        diff = ConfigDiff(entries)
        ctx = DiffFormatContext()

        result = build_and_render(layout, diff, ctx)
        # Pipe should be escaped
        assert "\\|" in result

    def test_hide_values(self) -> None:
        """Value columns hidden when show_values=False."""
        layout = DiffMarkdownLayout()
        entries = {
            "model.lr": DiffEntry("model.lr", DiffEntryType.ADDED, right_value=0.01),
        }
        diff = ConfigDiff(entries)
        ctx = DiffFormatContext(show_values=False)

        result = build_and_render(layout, diff, ctx)
        # Header should not have value columns
        assert "| Old Value |" not in result
        assert "| New Value |" not in result

    def test_show_provenance_column(self) -> None:
        """Source column appears when show_provenance=True."""
        from rconfig.composition import ProvenanceEntry

        layout = DiffMarkdownLayout()
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
        ctx = DiffFormatContext(show_provenance=True)

        result = build_and_render(layout, diff, ctx)
        assert "| Source |" in result
        assert "config.yaml" in result

    def test_sorted_entries(self) -> None:
        """Entries are sorted by path."""
        layout = DiffMarkdownLayout()
        entries = {
            "z.value": DiffEntry("z.value", DiffEntryType.ADDED, right_value=1),
            "a.value": DiffEntry("a.value", DiffEntryType.ADDED, right_value=2),
        }
        diff = ConfigDiff(entries)
        ctx = DiffFormatContext(show_counts=False)

        result = build_and_render(layout, diff, ctx)
        a_pos = result.find("a.value")
        z_pos = result.find("z.value")
        assert a_pos < z_pos

    def test_hide_added_entries(self) -> None:
        """Added entries hidden when show_added=False."""
        layout = DiffMarkdownLayout()
        entries = {
            "a": DiffEntry("a", DiffEntryType.ADDED, right_value=1),
            "b": DiffEntry("b", DiffEntryType.REMOVED, left_value=2),
        }
        diff = ConfigDiff(entries)
        ctx = DiffFormatContext(show_added=False, show_counts=False)

        result = build_and_render(layout, diff, ctx)
        assert "| + |" not in result
        assert "| - |" in result

    def test_hide_removed_entries(self) -> None:
        """Removed entries hidden when show_removed=False."""
        layout = DiffMarkdownLayout()
        entries = {
            "a": DiffEntry("a", DiffEntryType.ADDED, right_value=1),
            "b": DiffEntry("b", DiffEntryType.REMOVED, left_value=2),
        }
        diff = ConfigDiff(entries)
        ctx = DiffFormatContext(show_removed=False, show_counts=False)

        result = build_and_render(layout, diff, ctx)
        assert "| + |" in result
        # The "b" entry (removed) should not appear in output
        assert "| b |" not in result

    def test_path_filter(self) -> None:
        """Path filter applies to entries."""
        layout = DiffMarkdownLayout()
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
