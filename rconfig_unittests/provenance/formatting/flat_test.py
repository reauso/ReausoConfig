"""Tests for ProvenanceFlatLayout."""

from __future__ import annotations

from rconfig.deprecation.info import DeprecationInfo
from rconfig.provenance.formatting import (
    ProvenanceDisplayModelBuilder,
    ProvenanceFlatLayout,
)
from rconfig.provenance.models import EntrySourceType, InstanceRef


class TestProvenanceFlatLayoutRender:
    """Tests for ProvenanceFlatLayout.render()."""

    def test_render__EmptyMessage__ReturnsMessage(self) -> None:
        """render() returns empty message when model has empty_message."""
        # Arrange
        layout = ProvenanceFlatLayout()
        builder = ProvenanceDisplayModelBuilder()
        builder.set_empty_message("No entries found")
        model = builder.build()

        # Act
        result = layout.render(model)

        # Assert
        assert result == "No entries found"

    def test_render__PathOnly__FormatsAsPath(self) -> None:
        """render() formats entry with path only."""
        # Arrange
        layout = ProvenanceFlatLayout()
        builder = ProvenanceDisplayModelBuilder()
        builder.add_entry(path="model.lr")
        model = builder.build()

        # Act
        result = layout.render(model)

        # Assert
        assert result == "/model.lr"

    def test_render__PathAndValue__FormatsAsPathEqualsValue(self) -> None:
        """render() formats entry as /path = value."""
        # Arrange
        layout = ProvenanceFlatLayout()
        builder = ProvenanceDisplayModelBuilder()
        builder.add_entry(path="model.lr", value=0.001)
        model = builder.build()

        # Act
        result = layout.render(model)

        # Assert
        assert result == "/model.lr = 0.001"

    def test_render__StringValue__FormatsWithQuotes(self) -> None:
        """render() formats string values with quotes."""
        # Arrange
        layout = ProvenanceFlatLayout()
        builder = ProvenanceDisplayModelBuilder()
        builder.add_entry(path="model.name", value="transformer")
        model = builder.build()

        # Act
        result = layout.render(model)

        # Assert
        assert result == "/model.name = 'transformer'"

    def test_render__BoolValue__FormatsAsLowercase(self) -> None:
        """render() formats boolean values as lowercase."""
        # Arrange
        layout = ProvenanceFlatLayout()
        builder = ProvenanceDisplayModelBuilder()
        builder.add_entry(path="model.enabled", value=True)
        model = builder.build()

        # Act
        result = layout.render(model)

        # Assert
        assert result == "/model.enabled = true"

    def test_render__WithLocation__AddsLocationInParentheses(self) -> None:
        """render() adds location in parentheses after path=value."""
        # Arrange
        layout = ProvenanceFlatLayout()
        builder = ProvenanceDisplayModelBuilder()
        builder.add_entry(path="model.lr", value=0.001, file="config.yaml", line=5)
        model = builder.build()

        # Act
        result = layout.render(model)

        # Assert
        assert result == "/model.lr = 0.001 (config.yaml:5)"

    def test_render__WithFileNoLine__ShowsFileOnly(self) -> None:
        """render() shows file without line number when line is None."""
        # Arrange
        layout = ProvenanceFlatLayout()
        builder = ProvenanceDisplayModelBuilder()
        builder.add_entry(path="model.lr", value=0.001, file="config.yaml")
        model = builder.build()

        # Act
        result = layout.render(model)

        # Assert
        assert result == "/model.lr = 0.001 (config.yaml)"

    def test_render__WithCliSource__ShowsCliInfo(self) -> None:
        """render() shows CLI source information."""
        # Arrange
        layout = ProvenanceFlatLayout()
        builder = ProvenanceDisplayModelBuilder()
        builder.add_entry(
            path="model.lr",
            value=0.001,
            source_type=EntrySourceType.CLI,
            cli_arg="--lr",
        )
        model = builder.build()

        # Act
        result = layout.render(model)

        # Assert
        assert result == "/model.lr = 0.001 (CLI: --lr)"

    def test_render__WithEnvSource__ShowsEnvInfo(self) -> None:
        """render() shows environment variable source information."""
        # Arrange
        layout = ProvenanceFlatLayout()
        builder = ProvenanceDisplayModelBuilder()
        builder.add_entry(
            path="model.lr",
            value=0.001,
            source_type=EntrySourceType.ENV,
            env_var="MODEL_LR",
        )
        model = builder.build()

        # Act
        result = layout.render(model)

        # Assert
        assert result == "/model.lr = 0.001 (env: MODEL_LR)"

    def test_render__WithTarget__ShowsTargetInfo(self) -> None:
        """render() shows target information."""
        # Arrange
        layout = ProvenanceFlatLayout()
        builder = ProvenanceDisplayModelBuilder()
        builder.add_entry(
            path="model",
            target_name="transformer",
            target_class="Transformer",
            target_module="models",
        )
        model = builder.build()

        # Act
        result = layout.render(model)

        # Assert
        assert result == "/model (target: transformer -> models.Transformer)"

    def test_render__WithAutoRegisteredTarget__ShowsAutoSuffix(self) -> None:
        """render() shows (auto) suffix for auto-registered targets."""
        # Arrange
        layout = ProvenanceFlatLayout()
        builder = ProvenanceDisplayModelBuilder()
        builder.add_entry(
            path="model",
            target_name="transformer",
            target_class="Transformer",
            target_auto_registered=True,
        )
        model = builder.build()

        # Act
        result = layout.render(model)

        # Assert
        assert "(auto)" in result

    def test_render__WithInterpolation__ShowsExpression(self) -> None:
        """render() shows interpolation expression."""
        # Arrange
        layout = ProvenanceFlatLayout()
        builder = ProvenanceDisplayModelBuilder()
        builder.add_entry(
            path="model.lr",
            value=0.01,
            interpolation_expression="/defaults.lr * 2",
        )
        model = builder.build()

        # Act
        result = layout.render(model)

        # Assert
        assert "${/defaults.lr * 2}" in result

    def test_render__WithOverride__ShowsOverrideInfo(self) -> None:
        """render() shows override information."""
        # Arrange
        layout = ProvenanceFlatLayout()
        builder = ProvenanceDisplayModelBuilder()
        builder.add_entry(
            path="model.lr",
            value=0.001,
            file="config.yaml",
            line=5,
            overrode="defaults.yaml:10",
        )
        model = builder.build()

        # Act
        result = layout.render(model)

        # Assert
        assert "overrode: defaults.yaml:10" in result

    def test_render__WithDeprecation__ShowsDeprecatedMarker(self) -> None:
        """render() shows DEPRECATED marker."""
        # Arrange
        layout = ProvenanceFlatLayout()
        builder = ProvenanceDisplayModelBuilder()
        builder.add_entry(
            path="old_key",
            value=42,
            deprecation=DeprecationInfo(pattern="old_key", new_key="new_key"),
        )
        model = builder.build()

        # Act
        result = layout.render(model)

        # Assert
        assert "DEPRECATED -> new_key" in result

    def test_render__WithInstance__ShowsInstanceInfo(self) -> None:
        """render() shows instance reference information."""
        # Arrange
        layout = ProvenanceFlatLayout()
        builder = ProvenanceDisplayModelBuilder()
        builder.add_entry(
            path="model.encoder",
            instances=(InstanceRef(path="encoder", file="encoder.yaml", line=1),),
        )
        model = builder.build()

        # Act
        result = layout.render(model)

        # Assert
        assert "instance: encoder <- encoder.yaml:1" in result

    def test_render__MultipleEntries__JoinsWithNewline(self) -> None:
        """render() joins multiple entries with newlines."""
        # Arrange
        layout = ProvenanceFlatLayout()
        builder = ProvenanceDisplayModelBuilder()
        builder.add_entry(path="model.lr", value=0.001)
        builder.add_entry(path="model.dropout", value=0.1)
        model = builder.build()

        # Act
        result = layout.render(model)

        # Assert
        assert "/model.lr = 0.001" in result
        assert "/model.dropout = 0.1" in result
        assert "\n" in result

    def test_render__WithHeader__PrependsHeader(self) -> None:
        """render() prepends header to output."""
        # Arrange
        layout = ProvenanceFlatLayout()
        builder = ProvenanceDisplayModelBuilder()
        builder.set_header("Deprecated Keys:")
        builder.add_entry(path="old_key", value=42)
        model = builder.build()

        # Act
        result = layout.render(model)

        # Assert
        assert result.startswith("Deprecated Keys:\n")

    def test_render__MultipleDetails__JoinsWithComma(self) -> None:
        """render() joins multiple details with commas in parentheses."""
        # Arrange
        layout = ProvenanceFlatLayout()
        builder = ProvenanceDisplayModelBuilder()
        builder.add_entry(
            path="model.lr",
            value=0.001,
            file="config.yaml",
            line=5,
            overrode="defaults.yaml:10",
        )
        model = builder.build()

        # Act
        result = layout.render(model)

        # Assert
        assert "(" in result
        assert "config.yaml:5" in result
        assert "overrode: defaults.yaml:10" in result
        assert ")" in result

    def test_render__LongListValue__TruncatesWithEllipsis(self) -> None:
        """render() truncates long list values with ellipsis."""
        # Arrange
        layout = ProvenanceFlatLayout()
        builder = ProvenanceDisplayModelBuilder()
        builder.add_entry(path="data.items", value=list(range(100)))
        model = builder.build()

        # Act
        result = layout.render(model)

        # Assert
        assert "..." in result
        assert len(result) < 200  # Should be truncated
