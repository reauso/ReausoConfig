"""Tests for ProvenanceMarkdownLayout."""

from __future__ import annotations

from rconfig.deprecation.info import DeprecationInfo
from rconfig.provenance.formatting import (
    ProvenanceDisplayModelBuilder,
    ProvenanceMarkdownLayout,
)
from rconfig.provenance.models import EntrySourceType, InstanceRef


class TestProvenanceMarkdownLayoutRender:
    """Tests for ProvenanceMarkdownLayout.render()."""

    def test_render__EmptyMessage__ReturnsItalicMessage(self) -> None:
        """render() returns italicized message when empty."""
        # Arrange
        layout = ProvenanceMarkdownLayout()
        builder = ProvenanceDisplayModelBuilder()
        builder.set_empty_message("No entries found")
        model = builder.build()

        # Act
        result = layout.render(model)

        # Assert
        assert result == "_No entries found._"

    def test_render__SingleEntry__CreatesValidMarkdownTable(self) -> None:
        """render() creates a valid markdown table."""
        # Arrange
        layout = ProvenanceMarkdownLayout()
        builder = ProvenanceDisplayModelBuilder()
        builder.add_entry(path="model.lr")
        model = builder.build()

        # Act
        result = layout.render(model)

        # Assert
        assert "| Path |" in result
        assert "|------|" in result
        assert "| /model.lr |" in result

    def test_render__WithValue__ShowsValueColumn(self) -> None:
        """render() shows Value column when entries have values."""
        # Arrange
        layout = ProvenanceMarkdownLayout()
        builder = ProvenanceDisplayModelBuilder()
        builder.add_entry(path="model.lr", value=0.001)
        model = builder.build()

        # Act
        result = layout.render(model)

        # Assert
        assert "| Path | Value |" in result
        assert "| /model.lr | 0.001 |" in result

    def test_render__WithoutValue__HidesValueColumn(self) -> None:
        """render() hides Value column when no entries have values."""
        # Arrange
        layout = ProvenanceMarkdownLayout()
        builder = ProvenanceDisplayModelBuilder()
        builder.add_entry(path="model.lr")
        builder.add_entry(path="model.dropout")
        model = builder.build()

        # Act
        result = layout.render(model)

        # Assert
        assert "| Path |" in result
        assert "Value" not in result

    def test_render__WithSource__ShowsSourceColumn(self) -> None:
        """render() shows Source column when entries have source info."""
        # Arrange
        layout = ProvenanceMarkdownLayout()
        builder = ProvenanceDisplayModelBuilder()
        builder.add_entry(path="model.lr", value=0.001, file="config.yaml", line=5)
        model = builder.build()

        # Act
        result = layout.render(model)

        # Assert
        assert "| Source |" in result
        assert "config.yaml:5" in result

    def test_render__WithCliSource__ShowsCliInfo(self) -> None:
        """render() shows CLI source in Source column."""
        # Arrange
        layout = ProvenanceMarkdownLayout()
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
        assert "CLI: --lr" in result

    def test_render__WithEnvSource__ShowsEnvInfo(self) -> None:
        """render() shows env source in Source column."""
        # Arrange
        layout = ProvenanceMarkdownLayout()
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
        assert "env: MODEL_LR" in result

    def test_render__WithTarget__ShowsDetailsColumn(self) -> None:
        """render() shows Details column with target info."""
        # Arrange
        layout = ProvenanceMarkdownLayout()
        builder = ProvenanceDisplayModelBuilder()
        builder.add_entry(
            path="model",
            target_name="transformer",
            target_class="Transformer",
        )
        model = builder.build()

        # Act
        result = layout.render(model)

        # Assert
        assert "| Details |" in result
        assert "Target: transformer -> Transformer" in result

    def test_render__WithInterpolation__ShowsInterpolationInDetails(self) -> None:
        """render() shows interpolation expression in Details column."""
        # Arrange
        layout = ProvenanceMarkdownLayout()
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
        assert "Interp: ${/defaults.lr * 2}" in result

    def test_render__WithOverride__ShowsOverrideInDetails(self) -> None:
        """render() shows override info in Details column."""
        # Arrange
        layout = ProvenanceMarkdownLayout()
        builder = ProvenanceDisplayModelBuilder()
        builder.add_entry(
            path="model.lr",
            value=0.001,
            overrode="defaults.yaml:10",
        )
        model = builder.build()

        # Act
        result = layout.render(model)

        # Assert
        assert "Overrode: defaults.yaml:10" in result

    def test_render__WithDeprecation__ShowsDeprecatedInDetails(self) -> None:
        """render() shows DEPRECATED in Details column."""
        # Arrange
        layout = ProvenanceMarkdownLayout()
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

    def test_render__WithInstance__ShowsInstanceInDetails(self) -> None:
        """render() shows instance reference in Details column."""
        # Arrange
        layout = ProvenanceMarkdownLayout()
        builder = ProvenanceDisplayModelBuilder()
        builder.add_entry(
            path="model.encoder",
            instances=(InstanceRef(path="encoder", file="encoder.yaml", line=1),),
        )
        model = builder.build()

        # Act
        result = layout.render(model)

        # Assert
        assert "Instance: encoder <- encoder.yaml:1" in result

    def test_render__MultipleDetails__JoinsWithSemicolon(self) -> None:
        """render() joins multiple details with semicolons."""
        # Arrange
        layout = ProvenanceMarkdownLayout()
        builder = ProvenanceDisplayModelBuilder()
        builder.add_entry(
            path="model.lr",
            value=0.001,
            overrode="defaults.yaml:10",
            deprecation=DeprecationInfo(pattern="model.lr", new_key="model.learning_rate"),
        )
        model = builder.build()

        # Act
        result = layout.render(model)

        # Assert
        assert "Overrode:" in result
        assert "DEPRECATED" in result
        assert ";" in result

    def test_render__PipeInValue__EscapesPipe(self) -> None:
        """render() escapes pipe characters in values."""
        # Arrange
        layout = ProvenanceMarkdownLayout()
        builder = ProvenanceDisplayModelBuilder()
        builder.add_entry(path="model.pattern", value="a|b|c")
        model = builder.build()

        # Act
        result = layout.render(model)

        # Assert
        assert "\\|" in result

    def test_render__WithHeader__PrependsBoldHeader(self) -> None:
        """render() prepends bold header to table."""
        # Arrange
        layout = ProvenanceMarkdownLayout()
        builder = ProvenanceDisplayModelBuilder()
        builder.set_header("Deprecated Keys")
        builder.add_entry(path="old_key", value=42)
        model = builder.build()

        # Act
        result = layout.render(model)

        # Assert
        assert result.startswith("**Deprecated Keys**")
        assert "\n\n|" in result  # Header followed by blank line then table

    def test_render__MultipleEntries__CreatesMultipleRows(self) -> None:
        """render() creates a row for each entry."""
        # Arrange
        layout = ProvenanceMarkdownLayout()
        builder = ProvenanceDisplayModelBuilder()
        builder.add_entry(path="model.lr", value=0.001)
        builder.add_entry(path="model.dropout", value=0.1)
        builder.add_entry(path="model.layers", value=6)
        model = builder.build()

        # Act
        result = layout.render(model)

        # Assert
        lines = result.split("\n")
        # Header + separator + 3 data rows = 5 lines
        assert len(lines) == 5
        assert "/model.lr" in result
        assert "/model.dropout" in result
        assert "/model.layers" in result

    def test_render__NoPath__ShowsDash(self) -> None:
        """render() shows dash for entries without path."""
        # Arrange
        layout = ProvenanceMarkdownLayout()
        builder = ProvenanceDisplayModelBuilder()
        builder.add_entry(value=42)
        model = builder.build()

        # Act
        result = layout.render(model)

        # Assert
        assert "| - |" in result

    def test_render__MixedColumnsPresent__ShowsAllRelevantColumns(self) -> None:
        """render() shows all columns that have data in any entry."""
        # Arrange
        layout = ProvenanceMarkdownLayout()
        builder = ProvenanceDisplayModelBuilder()
        # First entry has value but no source
        builder.add_entry(path="model.lr", value=0.001)
        # Second entry has source but no value
        builder.add_entry(path="model.name", file="config.yaml", line=5)
        model = builder.build()

        # Act
        result = layout.render(model)

        # Assert
        # Both columns should be present because at least one entry has each
        assert "| Value |" in result
        assert "| Source |" in result

    def test_render__StringValue__FormatsWithQuotes(self) -> None:
        """render() formats string values with quotes."""
        # Arrange
        layout = ProvenanceMarkdownLayout()
        builder = ProvenanceDisplayModelBuilder()
        builder.add_entry(path="model.name", value="transformer")
        model = builder.build()

        # Act
        result = layout.render(model)

        # Assert
        assert "'transformer'" in result

    def test_render__BoolValue__FormatsAsLowercase(self) -> None:
        """render() formats boolean values as lowercase."""
        # Arrange
        layout = ProvenanceMarkdownLayout()
        builder = ProvenanceDisplayModelBuilder()
        builder.add_entry(path="model.enabled", value=True)
        model = builder.build()

        # Act
        result = layout.render(model)

        # Assert
        assert "true" in result
