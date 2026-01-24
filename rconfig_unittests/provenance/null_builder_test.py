"""Tests for NullProvenanceBuilder."""

from unittest import TestCase

from rconfig.provenance import (
    NullProvenanceBuilder,
    ProvenanceBuilder,
)


class NullProvenanceBuilderTests(TestCase):
    """Tests for NullProvenanceBuilder class."""

    def test_init__NoArgs__CreatesInstance(self):
        """Test that NullProvenanceBuilder can be created without errors."""
        # Act
        builder = NullProvenanceBuilder()

        # Assert
        self.assertIsInstance(builder, NullProvenanceBuilder)

    def test_subclass__IsSubclassOfProvenanceBuilder(self):
        """Test that NullProvenanceBuilder is a subclass of ProvenanceBuilder."""
        # Assert
        self.assertTrue(issubclass(NullProvenanceBuilder, ProvenanceBuilder))

    def test_isinstance__AcceptedAsProvenanceBuilder(self):
        """Test that instances pass isinstance checks for ProvenanceBuilder."""
        # Arrange
        builder = NullProvenanceBuilder()

        # Assert
        self.assertIsInstance(builder, ProvenanceBuilder)

    def test_add__AnyArgs__NoOp(self):
        """Test that add() is a no-op and doesn't raise."""
        # Arrange
        builder = NullProvenanceBuilder()

        # Act & Assert (no exception)
        builder.add("model.lr", file="config.yaml", line=5)
        builder.add(
            "db.host",
            file="app.yaml",
            line=10,
            overrode="base.yaml:5",
            target_name="MyModel",
        )

    def test_set_config__AnyConfig__NoOp(self):
        """Test that set_config() is a no-op and doesn't raise."""
        # Arrange
        builder = NullProvenanceBuilder()

        # Act & Assert (no exception)
        builder.set_config({"model": {"lr": 0.01}})

    def test_resolve_targets__AnyTargets__NoOp(self):
        """Test that resolve_targets() is a no-op and doesn't raise."""
        # Arrange
        builder = NullProvenanceBuilder()

        # Act & Assert (no exception)
        builder.resolve_targets({"model": object()}, auto_registered={"model"})

    def test_get__AnyPath__ReturnsNone(self):
        """Test that get() always returns None."""
        # Arrange
        builder = NullProvenanceBuilder()
        builder.add("model.lr", file="config.yaml", line=5)

        # Act
        result = builder.get("model.lr")

        # Assert
        self.assertIsNone(result)

    def test_get__NonexistentPath__ReturnsNone(self):
        """Test that get() returns None for non-existent paths."""
        # Arrange
        builder = NullProvenanceBuilder()

        # Act
        result = builder.get("anything.at.all")

        # Assert
        self.assertIsNone(result)

    def test_get_entry__AnyPath__ReturnsNone(self):
        """Test that get_entry() always returns None."""
        # Arrange
        builder = NullProvenanceBuilder()
        builder.add("model.lr", file="config.yaml", line=5)

        # Act
        result = builder.get_entry("model.lr")

        # Assert
        self.assertIsNone(result)

    def test_build__AfterAdds__ReturnsNone(self):
        """Test that build() returns None regardless of adds."""
        # Arrange
        builder = NullProvenanceBuilder()
        builder.add("model.lr", file="config.yaml", line=5)

        # Act
        result = builder.build()

        # Assert
        self.assertIsNone(result)

    def test_build__EmptyBuilder__ReturnsNone(self):
        """Test that build() returns None on fresh builder."""
        # Arrange
        builder = NullProvenanceBuilder()

        # Act
        result = builder.build()

        # Assert
        self.assertIsNone(result)

    def test_items__AfterAdds__ReturnsEmptyIterator(self):
        """Test that items() returns empty iterator regardless of adds."""
        # Arrange
        builder = NullProvenanceBuilder()
        builder.add("model.lr", file="config.yaml", line=5)

        # Act
        result = list(builder.items())

        # Assert
        self.assertEqual(result, [])

    def test_config__AfterSetConfig__ReturnsEmptyDict(self):
        """Test that config property returns empty dict."""
        # Arrange
        builder = NullProvenanceBuilder()
        builder.set_config({"model": {"lr": 0.01}})

        # Act
        result = builder.config

        # Assert
        self.assertEqual(result, {})

    def test_init__DoesNotAllocateState(self):
        """Test that NullProvenanceBuilder doesn't create internal dicts."""
        # Arrange & Act
        builder = NullProvenanceBuilder()

        # Assert - should not have _entries or _config from parent
        self.assertFalse(hasattr(builder, "_entries"))
        self.assertFalse(hasattr(builder, "_config"))
