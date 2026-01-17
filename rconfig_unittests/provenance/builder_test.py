"""Tests for ProvenanceBuilder."""

from unittest import TestCase

from rconfig.provenance import (
    Provenance,
    ProvenanceBuilder,
    ProvenanceEntry,
)


class ProvenanceBuilderTests(TestCase):
    """Tests for ProvenanceBuilder class."""

    def test_build__EmptyBuilder__ReturnsEmptyProvenance(self):
        """Test that empty builder returns empty provenance."""
        # Arrange
        builder = ProvenanceBuilder()

        # Act
        prov = builder.build()

        # Assert
        self.assertEqual(list(prov.items()), [])

    def test_add__SingleEntry__AddsToProvenance(self):
        """Test that add creates an entry."""
        # Arrange
        builder = ProvenanceBuilder()

        # Act
        builder.add("model.lr", file="config.yaml", line=5)
        prov = builder.build()

        # Assert
        entry = prov.get("model.lr")
        self.assertIsNotNone(entry)
        self.assertEqual(entry.file, "config.yaml")
        self.assertEqual(entry.line, 5)

    def test_add__WithAllParameters__StoresAllValues(self):
        """Test that all parameters are stored."""
        # Arrange
        from rconfig.provenance import InstanceRef, EntrySourceType

        builder = ProvenanceBuilder()
        instance_chain = [InstanceRef("/shared.db", "shared.yaml", 5)]

        # Act
        builder.add(
            "db.host",
            file="app.yaml",
            line=10,
            overrode="base.yaml:5",
            instance=instance_chain,
            source_type=EntrySourceType.CLI,
            cli_arg="--db.host=localhost",
        )
        prov = builder.build()

        # Assert
        entry = prov.get("db.host")
        self.assertEqual(entry.overrode, "base.yaml:5")
        self.assertEqual(len(entry.instance), 1)
        self.assertEqual(entry.source_type, "cli")
        self.assertEqual(entry.cli_arg, "--db.host=localhost")

    def test_get__ExistingPath__ReturnsMutableEntry(self):
        """Test that get returns the mutable entry for modification."""
        # Arrange
        builder = ProvenanceBuilder()
        builder.add("test", file="config.yaml", line=1)

        # Act
        entry = builder.get("test")
        entry.value = 42
        prov = builder.build()

        # Assert
        self.assertEqual(prov.get("test").value, 42)

    def test_get__NonExistentPath__ReturnsNone(self):
        """Test that get returns None for non-existent paths."""
        # Arrange
        builder = ProvenanceBuilder()

        # Act
        entry = builder.get("nonexistent")

        # Assert
        self.assertIsNone(entry)

    def test_setConfig__PopulatesValues__FillsEntryValues(self):
        """Test that set_config populates values from config."""
        # Arrange
        builder = ProvenanceBuilder()
        builder.add("model.lr", file="config.yaml", line=5)
        config = {"model": {"lr": 0.01}}

        # Act
        builder.set_config(config)
        prov = builder.build()

        # Assert
        self.assertEqual(prov.get("model.lr").value, 0.01)

    def test_setConfig__PreservesExistingValues__DoesNotOverwrite(self):
        """Test that set_config doesn't overwrite existing values."""
        # Arrange
        builder = ProvenanceBuilder()
        builder.add("model.lr", file="config.yaml", line=5)
        builder._entries["model.lr"].value = 999  # Pre-set value
        config = {"model": {"lr": 0.01}}

        # Act
        builder.set_config(config)
        prov = builder.build()

        # Assert
        self.assertEqual(prov.get("model.lr").value, 999)

    def test_setConfig__NestedPath__PopulatesCorrectly(self):
        """Test that deeply nested paths are populated."""
        # Arrange
        builder = ProvenanceBuilder()
        builder.add("a.b.c.d", file="config.yaml", line=1)
        config = {"a": {"b": {"c": {"d": "deep"}}}}

        # Act
        builder.set_config(config)
        prov = builder.build()

        # Assert
        self.assertEqual(prov.get("a.b.c.d").value, "deep")

    def test_items__ReturnsAllEntries(self):
        """Test that items returns all entries."""
        # Arrange
        builder = ProvenanceBuilder()
        builder.add("a", file="a.yaml", line=1)
        builder.add("b", file="b.yaml", line=2)
        builder.add("c", file="c.yaml", line=3)

        # Act
        items = list(builder.items())

        # Assert
        self.assertEqual(len(items), 3)
        paths = [path for path, _ in items]
        self.assertIn("a", paths)
        self.assertIn("b", paths)
        self.assertIn("c", paths)

    def test_build__ReturnsImmutableProvenance(self):
        """Test that build returns an immutable Provenance instance."""
        # Arrange
        builder = ProvenanceBuilder()
        builder.add("test", file="config.yaml", line=1)
        builder.set_config({"test": 42})

        # Act
        prov = builder.build()

        # Assert
        self.assertIsInstance(prov, Provenance)
        # Verify immutability
        with self.assertRaises(TypeError):
            prov.config["new"] = "value"
