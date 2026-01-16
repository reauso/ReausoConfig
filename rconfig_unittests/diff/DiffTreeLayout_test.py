"""Unit tests for DiffTreeLayout."""

from __future__ import annotations

import pytest

from rconfig.diff import ConfigDiff, DiffEntry, DiffEntryType, DiffFormatContext, DiffTreeLayout


class TestDiffTreeLayout:
    """Tests for DiffTreeLayout."""

    def test_format_empty_diff(self) -> None:
        """Empty diff shows 'No differences found.'"""
        layout = DiffTreeLayout()
        diff = ConfigDiff({})
        ctx = DiffFormatContext()

        result = layout.format_diff(diff, ctx)
        assert "No differences found" in result

    def test_format_has_header(self) -> None:
        """Output starts with 'ConfigDiff:'"""
        layout = DiffTreeLayout()
        entries = {
            "a": DiffEntry("a", DiffEntryType.ADDED, right_value=1),
        }
        diff = ConfigDiff(entries)
        ctx = DiffFormatContext()

        result = layout.format_diff(diff, ctx)
        assert result.startswith("ConfigDiff:")

    def test_added_section(self) -> None:
        """Added entries appear in 'Added:' section."""
        layout = DiffTreeLayout()
        entries = {
            "model.dropout": DiffEntry(
                "model.dropout", DiffEntryType.ADDED, right_value=0.1
            ),
        }
        diff = ConfigDiff(entries)
        ctx = DiffFormatContext()

        result = layout.format_diff(diff, ctx)
        assert "Added:" in result
        assert "model.dropout" in result

    def test_removed_section(self) -> None:
        """Removed entries appear in 'Removed:' section."""
        layout = DiffTreeLayout()
        entries = {
            "legacy.param": DiffEntry(
                "legacy.param", DiffEntryType.REMOVED, left_value="old"
            ),
        }
        diff = ConfigDiff(entries)
        ctx = DiffFormatContext()

        result = layout.format_diff(diff, ctx)
        assert "Removed:" in result
        assert "legacy.param" in result

    def test_changed_section(self) -> None:
        """Changed entries appear in 'Changed:' section."""
        layout = DiffTreeLayout()
        entries = {
            "model.lr": DiffEntry(
                "model.lr", DiffEntryType.CHANGED, 0.001, 0.01
            ),
        }
        diff = ConfigDiff(entries)
        ctx = DiffFormatContext()

        result = layout.format_diff(diff, ctx)
        assert "Changed:" in result
        assert "model.lr" in result

    def test_unchanged_section_when_enabled(self) -> None:
        """Unchanged section appears when show_unchanged=True."""
        layout = DiffTreeLayout()
        entries = {
            "model.layers": DiffEntry(
                "model.layers", DiffEntryType.UNCHANGED, 4, 4
            ),
        }
        diff = ConfigDiff(entries)
        ctx = DiffFormatContext(show_unchanged=True)

        result = layout.format_diff(diff, ctx)
        assert "Unchanged:" in result
        assert "model.layers" in result

    def test_unchanged_section_hidden_by_default(self) -> None:
        """Unchanged section hidden by default."""
        layout = DiffTreeLayout()
        entries = {
            "a": DiffEntry("a", DiffEntryType.ADDED, right_value=1),
            "b": DiffEntry("b", DiffEntryType.UNCHANGED, 2, 2),
        }
        diff = ConfigDiff(entries)
        ctx = DiffFormatContext()

        result = layout.format_diff(diff, ctx)
        assert "Unchanged:" not in result

    def test_sections_grouped(self) -> None:
        """All entries of same type appear in same section."""
        layout = DiffTreeLayout()
        entries = {
            "a": DiffEntry("a", DiffEntryType.ADDED, right_value=1),
            "b": DiffEntry("b", DiffEntryType.ADDED, right_value=2),
            "c": DiffEntry("c", DiffEntryType.REMOVED, left_value=3),
        }
        diff = ConfigDiff(entries)
        ctx = DiffFormatContext()

        result = layout.format_diff(diff, ctx)
        # Both added entries should appear after the Added: header
        lines = result.split("\n")
        added_idx = next(i for i, line in enumerate(lines) if "Added:" in line)
        removed_idx = next(i for i, line in enumerate(lines) if "Removed:" in line)

        # Find entries between sections
        entries_in_added = [
            line for line in lines[added_idx + 1 : removed_idx]
            if "+" in line
        ]
        assert len(entries_in_added) == 2

    def test_summary_shown(self) -> None:
        """Summary statistics appear at end."""
        layout = DiffTreeLayout()
        entries = {
            "a": DiffEntry("a", DiffEntryType.ADDED, right_value=1),
            "b": DiffEntry("b", DiffEntryType.REMOVED, left_value=2),
        }
        diff = ConfigDiff(entries)
        ctx = DiffFormatContext()

        result = layout.format_diff(diff, ctx)
        assert "Added: 1" in result
        assert "Removed: 1" in result

    def test_summary_hidden_when_disabled(self) -> None:
        """Summary hidden when show_counts=False."""
        layout = DiffTreeLayout()
        entries = {
            "a": DiffEntry("a", DiffEntryType.ADDED, right_value=1),
        }
        diff = ConfigDiff(entries)
        ctx = DiffFormatContext(show_counts=False)

        result = layout.format_diff(diff, ctx)
        assert "Added:" in result  # Section header
        # But not the count summary
        lines = result.split("\n")
        assert not any("Added: 1" in line for line in lines[-3:])

    def test_sorted_entries_within_section(self) -> None:
        """Entries within each section are sorted by path."""
        layout = DiffTreeLayout()
        entries = {
            "z.value": DiffEntry("z.value", DiffEntryType.ADDED, right_value=1),
            "a.value": DiffEntry("a.value", DiffEntryType.ADDED, right_value=2),
            "m.value": DiffEntry("m.value", DiffEntryType.ADDED, right_value=3),
        }
        diff = ConfigDiff(entries)
        ctx = DiffFormatContext(show_counts=False)

        result = layout.format_diff(diff, ctx)
        # Find positions in output
        a_pos = result.find("a.value")
        m_pos = result.find("m.value")
        z_pos = result.find("z.value")
        assert a_pos < m_pos < z_pos

    def test_hide_added_section(self) -> None:
        """No Added section when show_added=False."""
        layout = DiffTreeLayout()
        entries = {
            "a": DiffEntry("a", DiffEntryType.ADDED, right_value=1),
            "b": DiffEntry("b", DiffEntryType.REMOVED, left_value=2),
        }
        diff = ConfigDiff(entries)
        ctx = DiffFormatContext(show_added=False, show_counts=False)

        result = layout.format_diff(diff, ctx)
        assert "Added:" not in result
        assert "Removed:" in result

    def test_hide_removed_section(self) -> None:
        """No Removed section when show_removed=False."""
        layout = DiffTreeLayout()
        entries = {
            "a": DiffEntry("a", DiffEntryType.ADDED, right_value=1),
            "b": DiffEntry("b", DiffEntryType.REMOVED, left_value=2),
        }
        diff = ConfigDiff(entries)
        ctx = DiffFormatContext(show_removed=False, show_counts=False)

        result = layout.format_diff(diff, ctx)
        assert "Added:" in result
        assert "Removed:" not in result

    def test_hide_changed_section(self) -> None:
        """No Changed section when show_changed=False."""
        layout = DiffTreeLayout()
        entries = {
            "a": DiffEntry("a", DiffEntryType.ADDED, right_value=1),
            "b": DiffEntry("b", DiffEntryType.CHANGED, 2, 3),
        }
        diff = ConfigDiff(entries)
        ctx = DiffFormatContext(show_changed=False, show_counts=False)

        result = layout.format_diff(diff, ctx)
        assert "Added:" in result
        assert "Changed:" not in result

    def test_path_filter(self) -> None:
        """Path filter applies to all sections."""
        layout = DiffTreeLayout()
        entries = {
            "model.lr": DiffEntry("model.lr", DiffEntryType.ADDED, right_value=0.01),
            "data.batch_size": DiffEntry(
                "data.batch_size", DiffEntryType.ADDED, right_value=32
            ),
        }
        diff = ConfigDiff(entries)
        ctx = DiffFormatContext(path_filters=["model.*"], show_counts=False)

        result = layout.format_diff(diff, ctx)
        assert "model.lr" in result
        assert "data.batch_size" not in result

    def test_indentation(self) -> None:
        """Entries are indented within sections."""
        layout = DiffTreeLayout()
        entries = {
            "a": DiffEntry("a", DiffEntryType.ADDED, right_value=1),
        }
        diff = ConfigDiff(entries)
        ctx = DiffFormatContext(show_counts=False)

        result = layout.format_diff(diff, ctx)
        lines = result.split("\n")

        # Header has no indent
        assert lines[0] == "ConfigDiff:"

        # Section header has indent
        section_line = next(line for line in lines if "Added:" in line)
        assert section_line.startswith("  ")

        # Entries have more indent
        entry_line = next(line for line in lines if "+ a" in line)
        assert entry_line.startswith("    ")

    def test_provenance_when_enabled(self) -> None:
        """Provenance shown when show_provenance=True."""
        from rconfig.composition import ProvenanceEntry

        layout = DiffTreeLayout()
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

        result = layout.format_diff(diff, ctx)
        assert "config.yaml" in result

    def test_format_entry_delegates_correctly(self) -> None:
        """format_entry delegates to correct type formatter."""
        layout = DiffTreeLayout()
        ctx = DiffFormatContext()

        added = DiffEntry("a", DiffEntryType.ADDED, right_value=1)
        removed = DiffEntry("b", DiffEntryType.REMOVED, left_value=2)
        changed = DiffEntry("c", DiffEntryType.CHANGED, 3, 4)

        assert "+" in layout.format_entry(added, ctx)
        assert "-" in layout.format_entry(removed, ctx)
        assert "~" in layout.format_entry(changed, ctx)
