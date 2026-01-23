"""Unit tests for DiffLayout and DiffFormatContext."""

from __future__ import annotations

import pytest

from rconfig.diff import ConfigDiff, DiffEntry, DiffEntryType, DiffFormat, DiffFormatContext, DiffLayout
from rconfig.diff.formatting.model import DiffDisplayModel, DiffDisplayModelBuilder
from rconfig.provenance.models import ProvenanceEntry


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
        with pytest.raises(TypeError):
            DiffLayout()  # type: ignore

    def test_concrete_subclass_must_implement_render(self) -> None:
        """Concrete subclass must implement render method."""

        class IncompleteLayout(DiffLayout):
            pass

        with pytest.raises(TypeError):
            IncompleteLayout()  # type: ignore

    def test_concrete_subclass_with_render_works(self) -> None:
        """Concrete subclass with render method can be instantiated."""

        class MinimalLayout(DiffLayout):
            def render(self, model: DiffDisplayModel) -> str:
                return "rendered"

        layout = MinimalLayout()
        assert layout is not None


class TestDiffFormatValueFormatting:
    """Tests for value formatting used by DiffFormat.

    Value formatting is provided by format_value() from format_utils.
    """

    def test_format_value_none(self) -> None:
        """format_value handles None."""
        from rconfig._internal.format_utils import format_value

        assert format_value(None) == "null"

    def test_format_value_bool(self) -> None:
        """format_value handles booleans."""
        from rconfig._internal.format_utils import format_value

        assert format_value(True) == "true"
        assert format_value(False) == "false"

    def test_format_value_string(self) -> None:
        """format_value handles strings with quotes."""
        from rconfig._internal.format_utils import format_value

        assert format_value("hello") == "'hello'"

    def test_format_value_number(self) -> None:
        """format_value handles numbers."""
        from rconfig._internal.format_utils import format_value

        assert format_value(42) == "42"
        assert format_value(3.14) == "3.14"

    def test_format_value_truncates_long_values(self) -> None:
        """format_value truncates long lists/dicts."""
        from rconfig._internal.format_utils import format_value

        long_list = list(range(100))
        result = format_value(long_list)
        assert len(result) <= 50
        assert result.endswith("...")


class TestDiffFormatBuildModel:
    """Tests for DiffFormat._build_model()."""

    def test_build_creates_display_model(self) -> None:
        """_build_model() creates a complete display model."""
        entries = {
            "a": DiffEntry("a", DiffEntryType.ADDED, right_value=1),
            "b": DiffEntry("b", DiffEntryType.REMOVED, left_value=2),
            "c": DiffEntry("c", DiffEntryType.CHANGED, 3, 4),
        }
        diff = ConfigDiff(entries)
        fmt = DiffFormat(diff)

        model = fmt._build_model()

        assert len(model.entries) == 3
        assert model.empty_message is None

        # Check entry types
        added = [e for e in model.entries if e.diff_type == DiffEntryType.ADDED]
        removed = [e for e in model.entries if e.diff_type == DiffEntryType.REMOVED]
        changed = [e for e in model.entries if e.diff_type == DiffEntryType.CHANGED]
        assert len(added) == 1
        assert len(removed) == 1
        assert len(changed) == 1

    def test_build_respects_visibility_flags(self) -> None:
        """_build_model() respects show_added, show_removed, etc. flags."""
        entries = {
            "a": DiffEntry("a", DiffEntryType.ADDED, right_value=1),
            "b": DiffEntry("b", DiffEntryType.REMOVED, left_value=2),
        }
        diff = ConfigDiff(entries)
        fmt = DiffFormat(diff)
        fmt._ctx.show_added = False

        model = fmt._build_model()

        # Added should be filtered out
        added = [e for e in model.entries if e.diff_type == DiffEntryType.ADDED]
        removed = [e for e in model.entries if e.diff_type == DiffEntryType.REMOVED]
        assert len(added) == 0
        assert len(removed) == 1

    def test_build_empty_diff_shows_message(self) -> None:
        """_build_model() sets empty_message for empty diff."""
        diff = ConfigDiff({})
        fmt = DiffFormat(diff)

        model = fmt._build_model()

        assert model.empty_message is not None
        assert "No differences found" in model.empty_message


