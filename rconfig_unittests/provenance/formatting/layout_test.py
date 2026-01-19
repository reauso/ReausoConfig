"""Tests for ProvenanceLayout base class and ProvenanceFormatContext dataclass."""

from __future__ import annotations

import pytest

from rconfig.provenance import ProvenanceBuilder
from rconfig.provenance.formatting import (
    ProvenanceDisplayModel,
    ProvenanceFormat,
    ProvenanceFormatContext,
    ProvenanceLayout,
)


class TestProvenanceFormatContext:
    """Tests for ProvenanceFormatContext dataclass."""

    def test_default_values(self) -> None:
        """ProvenanceFormatContext has expected default values."""
        ctx = ProvenanceFormatContext()

        assert ctx.show_paths is True
        assert ctx.show_values is True
        assert ctx.show_files is True
        assert ctx.show_lines is True
        assert ctx.show_source_type is True
        assert ctx.show_chain is True
        assert ctx.show_overrides is True
        assert ctx.show_targets is True
        assert ctx.show_deprecations is True
        assert ctx.show_types is False
        assert ctx.show_descriptions is False
        assert ctx.deprecations_only is False
        assert ctx.indent_size == 2
        assert ctx.path_filters == []
        assert ctx.file_filters == []

    def test_custom_values(self) -> None:
        """ProvenanceFormatContext can be created with custom values."""
        ctx = ProvenanceFormatContext(
            show_paths=False,
            show_values=False,
            show_files=False,
            show_lines=False,
            show_source_type=False,
            show_chain=False,
            show_overrides=False,
            show_targets=False,
            show_deprecations=False,
            show_types=True,
            show_descriptions=True,
            deprecations_only=True,
            indent_size=4,
            path_filters=["/model.*"],
            file_filters=["*.yaml"],
        )

        assert ctx.show_paths is False
        assert ctx.show_values is False
        assert ctx.show_files is False
        assert ctx.show_lines is False
        assert ctx.show_source_type is False
        assert ctx.show_chain is False
        assert ctx.show_overrides is False
        assert ctx.show_targets is False
        assert ctx.show_deprecations is False
        assert ctx.show_types is True
        assert ctx.show_descriptions is True
        assert ctx.deprecations_only is True
        assert ctx.indent_size == 4
        assert ctx.path_filters == ["/model.*"]
        assert ctx.file_filters == ["*.yaml"]

    def test_is_mutable(self) -> None:
        """ProvenanceFormatContext fields can be mutated."""
        ctx = ProvenanceFormatContext()
        ctx.show_paths = False
        ctx.path_filters.append("test.*")

        assert ctx.show_paths is False
        assert "test.*" in ctx.path_filters

    def test_multiple_instances_have_independent_lists(self) -> None:
        """Filter lists are not shared between instances."""
        ctx1 = ProvenanceFormatContext()
        ctx2 = ProvenanceFormatContext()

        ctx1.path_filters.append("/test")

        assert ctx1.path_filters == ["/test"]
        assert ctx2.path_filters == []


class TestProvenanceLayoutABC:
    """Tests for ProvenanceLayout abstract base class."""

    def test_cannot_instantiate_directly(self) -> None:
        """ProvenanceLayout is abstract and cannot be instantiated directly."""
        with pytest.raises(TypeError):
            ProvenanceLayout()  # type: ignore

    def test_concrete_subclass_must_implement_render(self) -> None:
        """Concrete subclass must implement render method."""

        class IncompleteLayout(ProvenanceLayout):
            pass

        with pytest.raises(TypeError):
            IncompleteLayout()  # type: ignore

    def test_concrete_subclass_with_render_works(self) -> None:
        """Concrete subclass with render method can be instantiated."""

        class MinimalLayout(ProvenanceLayout):
            def render(self, model: ProvenanceDisplayModel) -> str:
                return "rendered"

        layout = MinimalLayout()
        assert layout is not None


class TestFormatValueFunction:
    """Tests for format_value from format_utils."""

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
        """format_value handles strings with repr."""
        from rconfig._internal.format_utils import format_value

        assert format_value("hello") == "'hello'"
        assert format_value("") == "''"

    def test_format_value_numbers(self) -> None:
        """format_value handles integers and floats."""
        from rconfig._internal.format_utils import format_value

        assert format_value(42) == "42"
        assert format_value(3.14) == "3.14"

    def test_format_value_list(self) -> None:
        """format_value handles lists."""
        from rconfig._internal.format_utils import format_value

        assert format_value([1, 2, 3]) == "[1, 2, 3]"
        assert format_value({"a": 1}) == "{'a': 1}"

    def test_format_value_truncates_long_values(self) -> None:
        """format_value truncates long lists/dicts."""
        from rconfig._internal.format_utils import format_value

        long_list = list(range(100))
        result = format_value(long_list)
        assert len(result) <= 50
        assert result.endswith("...")


class TestTreeLayoutFormatMethods:
    """Tests for TreeLayout specific formatting methods."""

    def test_format_source_type_cli(self) -> None:
        """_format_source_type handles CLI source."""
        from rconfig.provenance import EntrySourceType
        from rconfig.provenance.formatting import TreeLayout

        layout = TreeLayout()
        assert layout._format_source_type(EntrySourceType.CLI) == "CLI"

    def test_format_source_type_env(self) -> None:
        """_format_source_type handles env source."""
        from rconfig.provenance import EntrySourceType
        from rconfig.provenance.formatting import TreeLayout

        layout = TreeLayout()
        assert layout._format_source_type(EntrySourceType.ENV) == "env"

    def test_format_source_type_programmatic(self) -> None:
        """_format_source_type handles programmatic source."""
        from rconfig.provenance import EntrySourceType
        from rconfig.provenance.formatting import TreeLayout

        layout = TreeLayout()
        assert layout._format_source_type(EntrySourceType.PROGRAMMATIC) == "programmatic"

    def test_format_source_type_file(self) -> None:
        """_format_source_type returns empty for file source."""
        from rconfig.provenance import EntrySourceType
        from rconfig.provenance.formatting import TreeLayout

        layout = TreeLayout()
        assert layout._format_source_type(EntrySourceType.FILE) == ""

    def test_format_source_type_none(self) -> None:
        """_format_source_type returns empty for None."""
        from rconfig.provenance.formatting import TreeLayout

        layout = TreeLayout()
        assert layout._format_source_type(None) == ""


class TestProvenanceFormatting:
    """Tests for ProvenanceFormat display model building."""

    def test_build_creates_display_model(self) -> None:
        """Formatting provenance creates a display model with entries."""
        builder = ProvenanceBuilder()
        builder.add("model.lr", "config.yaml", 1, value=0.001)
        builder.add("model.epochs", "config.yaml", 2, value=100)
        prov = builder.build()

        # Format outputs a string via the display model
        result = str(ProvenanceFormat(prov))

        assert "model.lr" in result
        assert "model.epochs" in result

    def test_format_respects_path_filters(self) -> None:
        """Formatting respects path filter settings."""
        builder = ProvenanceBuilder()
        builder.add("model.lr", "config.yaml", 1, value=0.001)
        builder.add("data.path", "config.yaml", 2, value="/tmp")
        prov = builder.build()

        result = str(ProvenanceFormat(prov).for_path("/model.*"))

        assert "model.lr" in result
        assert "data.path" not in result

    def test_format_respects_file_filters(self) -> None:
        """Formatting respects file filter settings."""
        builder = ProvenanceBuilder()
        builder.add("model.lr", "config.yaml", 1, value=0.001)
        builder.add("data.path", "config.json", 2, value="/tmp")
        prov = builder.build()

        result = str(ProvenanceFormat(prov).from_file("*.yaml"))

        assert "model.lr" in result
        assert "data.path" not in result

    def test_format_respects_visibility_flags(self) -> None:
        """Formatting respects show_* flags."""
        builder = ProvenanceBuilder()
        builder.add("model.lr", "config.yaml", 1, value=0.001)
        prov = builder.build()

        result = str(ProvenanceFormat(prov).hide_values())

        assert "model.lr" in result
        assert "0.001" not in result


