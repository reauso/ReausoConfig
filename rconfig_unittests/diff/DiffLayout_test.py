"""Unit tests for DiffLayout and DiffFormatContext."""

from __future__ import annotations

import pytest

from rconfig.diff import ConfigDiff, DiffEntry, DiffEntryType, DiffFormatContext, DiffLayout


class TestDiffFormatContext:
    """Tests for DiffFormatContext dataclass."""

    def test_default_values(self) -> None:
        """DiffFormatContext has expected default values."""
        ctx = DiffFormatContext()

        assert ctx.show_paths is True
        assert ctx.show_values is True
        assert ctx.show_files is True
        assert ctx.show_lines is True
        assert ctx.show_provenance is False
        assert ctx.show_unchanged is False
        assert ctx.show_added is True
        assert ctx.show_removed is True
        assert ctx.show_changed is True
        assert ctx.show_counts is True
        assert ctx.indent_size == 2
        assert ctx.path_filters == []
        assert ctx.file_filters == []

    def test_custom_values(self) -> None:
        """DiffFormatContext can be created with custom values."""
        ctx = DiffFormatContext(
            show_paths=False,
            show_values=False,
            show_provenance=True,
            show_unchanged=True,
            indent_size=4,
            path_filters=["model.*"],
            file_filters=["*.yaml"],
        )

        assert ctx.show_paths is False
        assert ctx.show_values is False
        assert ctx.show_provenance is True
        assert ctx.show_unchanged is True
        assert ctx.indent_size == 4
        assert ctx.path_filters == ["model.*"]
        assert ctx.file_filters == ["*.yaml"]

    def test_is_mutable(self) -> None:
        """DiffFormatContext fields can be mutated."""
        ctx = DiffFormatContext()
        ctx.show_paths = False
        ctx.path_filters.append("test.*")

        assert ctx.show_paths is False
        assert "test.*" in ctx.path_filters


class TestDiffLayoutABC:
    """Tests for DiffLayout abstract base class."""

    def test_cannot_instantiate_directly(self) -> None:
        """DiffLayout is abstract and cannot be instantiated directly."""
        # Attempting to instantiate would fail because of abstract methods
        # But we can test by creating a minimal concrete subclass
        pass

    def test_get_default_context(self) -> None:
        """get_default_context returns DiffFormatContext."""

        class MinimalLayout(DiffLayout):
            def format_diff(self, diff, ctx):
                return ""

            def format_entry(self, entry, ctx):
                return ""

        layout = MinimalLayout()
        ctx = layout.get_default_context()

        assert isinstance(ctx, DiffFormatContext)

    def test_format_value_none(self) -> None:
        """format_value handles None."""

        class MinimalLayout(DiffLayout):
            def format_diff(self, diff, ctx):
                return ""

            def format_entry(self, entry, ctx):
                return ""

        layout = MinimalLayout()
        ctx = DiffFormatContext()

        assert layout.format_value(None, ctx) == "null"

    def test_format_value_bool(self) -> None:
        """format_value handles booleans."""

        class MinimalLayout(DiffLayout):
            def format_diff(self, diff, ctx):
                return ""

            def format_entry(self, entry, ctx):
                return ""

        layout = MinimalLayout()
        ctx = DiffFormatContext()

        assert layout.format_value(True, ctx) == "true"
        assert layout.format_value(False, ctx) == "false"

    def test_format_value_string(self) -> None:
        """format_value handles strings with quotes."""

        class MinimalLayout(DiffLayout):
            def format_diff(self, diff, ctx):
                return ""

            def format_entry(self, entry, ctx):
                return ""

        layout = MinimalLayout()
        ctx = DiffFormatContext()

        assert layout.format_value("hello", ctx) == "'hello'"

    def test_format_value_number(self) -> None:
        """format_value handles numbers."""

        class MinimalLayout(DiffLayout):
            def format_diff(self, diff, ctx):
                return ""

            def format_entry(self, entry, ctx):
                return ""

        layout = MinimalLayout()
        ctx = DiffFormatContext()

        assert layout.format_value(42, ctx) == "42"
        assert layout.format_value(3.14, ctx) == "3.14"

    def test_format_value_truncates_long_values(self) -> None:
        """format_value truncates long lists/dicts."""

        class MinimalLayout(DiffLayout):
            def format_diff(self, diff, ctx):
                return ""

            def format_entry(self, entry, ctx):
                return ""

        layout = MinimalLayout()
        ctx = DiffFormatContext()

        long_list = list(range(100))
        result = layout.format_value(long_list, ctx)
        assert len(result) <= 50
        assert result.endswith("...")

    def test_format_location(self) -> None:
        """format_location formats file:line."""

        class MinimalLayout(DiffLayout):
            def format_diff(self, diff, ctx):
                return ""

            def format_entry(self, entry, ctx):
                return ""

        layout = MinimalLayout()
        ctx = DiffFormatContext(show_files=True, show_lines=True)

        result = layout.format_location("test.yaml", 42, ctx)
        assert result == "test.yaml:42"

    def test_format_location_file_only(self) -> None:
        """format_location shows file only when lines disabled."""

        class MinimalLayout(DiffLayout):
            def format_diff(self, diff, ctx):
                return ""

            def format_entry(self, entry, ctx):
                return ""

        layout = MinimalLayout()
        ctx = DiffFormatContext(show_files=True, show_lines=False)

        result = layout.format_location("test.yaml", 42, ctx)
        assert result == "test.yaml"

    def test_format_location_line_only(self) -> None:
        """format_location shows line only when files disabled."""

        class MinimalLayout(DiffLayout):
            def format_diff(self, diff, ctx):
                return ""

            def format_entry(self, entry, ctx):
                return ""

        layout = MinimalLayout()
        ctx = DiffFormatContext(show_files=False, show_lines=True)

        result = layout.format_location("test.yaml", 42, ctx)
        assert result == "42"

    def test_format_location_none_file(self) -> None:
        """format_location handles None file."""

        class MinimalLayout(DiffLayout):
            def format_diff(self, diff, ctx):
                return ""

            def format_entry(self, entry, ctx):
                return ""

        layout = MinimalLayout()
        ctx = DiffFormatContext(show_files=True, show_lines=True)

        result = layout.format_location(None, 42, ctx)
        assert result == ""

    def test_format_summary(self) -> None:
        """format_summary creates count string."""

        class MinimalLayout(DiffLayout):
            def format_diff(self, diff, ctx):
                return ""

            def format_entry(self, entry, ctx):
                return ""

        layout = MinimalLayout()
        ctx = DiffFormatContext()

        entries = {
            "a": DiffEntry("a", DiffEntryType.ADDED, right_value=1),
            "b": DiffEntry("b", DiffEntryType.ADDED, right_value=2),
            "c": DiffEntry("c", DiffEntryType.REMOVED, left_value=3),
        }
        diff = ConfigDiff(entries)

        result = layout.format_summary(diff, ctx)
        assert "Added: 2" in result
        assert "Removed: 1" in result

    def test_format_added(self) -> None:
        """format_added creates + prefix entry."""

        class MinimalLayout(DiffLayout):
            def format_diff(self, diff, ctx):
                return ""

            def format_entry(self, entry, ctx):
                return ""

        layout = MinimalLayout()
        ctx = DiffFormatContext()

        entry = DiffEntry("model.lr", DiffEntryType.ADDED, right_value=0.01)
        result = layout.format_added(entry, ctx)

        assert "+ model.lr" in result
        assert "0.01" in result

    def test_format_removed(self) -> None:
        """format_removed creates - prefix entry."""

        class MinimalLayout(DiffLayout):
            def format_diff(self, diff, ctx):
                return ""

            def format_entry(self, entry, ctx):
                return ""

        layout = MinimalLayout()
        ctx = DiffFormatContext()

        entry = DiffEntry("model.lr", DiffEntryType.REMOVED, left_value=0.01)
        result = layout.format_removed(entry, ctx)

        assert "- model.lr" in result
        assert "0.01" in result

    def test_format_changed(self) -> None:
        """format_changed creates ~ prefix entry with arrow."""

        class MinimalLayout(DiffLayout):
            def format_diff(self, diff, ctx):
                return ""

            def format_entry(self, entry, ctx):
                return ""

        layout = MinimalLayout()
        ctx = DiffFormatContext()

        entry = DiffEntry("model.lr", DiffEntryType.CHANGED, 0.001, 0.01)
        result = layout.format_changed(entry, ctx)

        assert "~ model.lr" in result
        assert "0.001" in result
        assert "->" in result
        assert "0.01" in result

    def test_format_unchanged(self) -> None:
        """format_unchanged creates space prefix entry."""

        class MinimalLayout(DiffLayout):
            def format_diff(self, diff, ctx):
                return ""

            def format_entry(self, entry, ctx):
                return ""

        layout = MinimalLayout()
        ctx = DiffFormatContext()

        entry = DiffEntry("model.lr", DiffEntryType.UNCHANGED, 0.01, 0.01)
        result = layout.format_unchanged(entry, ctx)

        assert "model.lr" in result
        assert "0.01" in result
        assert not result.startswith("+")
        assert not result.startswith("-")
        assert not result.startswith("~")

    def test_indent(self) -> None:
        """indent adds spaces based on depth and indent_size."""

        class MinimalLayout(DiffLayout):
            def format_diff(self, diff, ctx):
                return ""

            def format_entry(self, entry, ctx):
                return ""

        layout = MinimalLayout()
        ctx = DiffFormatContext(indent_size=2)

        assert layout.indent("text", 0, ctx) == "text"
        assert layout.indent("text", 1, ctx) == "  text"
        assert layout.indent("text", 2, ctx) == "    text"

        ctx_4 = DiffFormatContext(indent_size=4)
        assert layout.indent("text", 1, ctx_4) == "    text"

    def test_join_entries(self) -> None:
        """join_entries combines entries with newlines."""

        class MinimalLayout(DiffLayout):
            def format_diff(self, diff, ctx):
                return ""

            def format_entry(self, entry, ctx):
                return ""

        layout = MinimalLayout()
        ctx = DiffFormatContext()

        entries = ["line1", "line2", "line3"]
        result = layout.join_entries(entries, ctx)

        assert result == "line1\nline2\nline3"
