"""Tests for IncrementalComposer module."""

from unittest import TestCase

from ruamel.yaml.comments import CommentedMap

from rconfig.composition import (
    CompositionResult,
    InstanceMarker,
    clear_cache,
    set_cache_size,
    IncrementalComposer,
)
from rconfig.provenance import ProvenanceBuilder
from rconfig.loaders.position_map import PositionMap


class InstanceMarkerTests(TestCase):
    """Tests for InstanceMarker dataclass."""

    def test_InstanceMarker__AllFields__StoresValues(self):
        # Act
        marker = InstanceMarker(
            config_path="model.encoder",
            instance_path="/shared.encoder",
            file_path="/configs/app.yaml",
            line=42,
        )

        # Assert
        self.assertEqual(marker.config_path, "model.encoder")
        self.assertEqual(marker.instance_path, "/shared.encoder")
        self.assertEqual(marker.file_path, "/configs/app.yaml")
        self.assertEqual(marker.line, 42)

    def test_InstanceMarker__NullInstancePath__AllowsNone(self):
        # Act
        marker = InstanceMarker(
            config_path="model.encoder",
            instance_path=None,
            file_path="/configs/app.yaml",
            line=10,
        )

        # Assert
        self.assertIsNone(marker.instance_path)

    def test_InstanceMarker__Equality__ComparesAllFields(self):
        # Arrange
        marker1 = InstanceMarker("path", "/target", "file.yaml", 1)
        marker2 = InstanceMarker("path", "/target", "file.yaml", 1)
        marker3 = InstanceMarker("path", "/target", "file.yaml", 2)

        # Assert
        self.assertEqual(marker1, marker2)
        self.assertNotEqual(marker1, marker3)


class CompositionResultTests(TestCase):
    """Tests for CompositionResult dataclass."""

    def test_CompositionResult__WithConfig__StoresConfig(self):
        # Arrange
        config = {"_target_": "Model", "layers": 50}

        # Act
        result = CompositionResult(config=config)

        # Assert
        self.assertEqual(result.config, config)
        self.assertEqual(result.instances, {})

    def test_CompositionResult__WithInstances__StoresInstances(self):
        # Arrange
        config = {"_target_": "Model"}
        instances = {
            "db": InstanceMarker("db", "/shared.db", "app.yaml", 5),
        }

        # Act
        result = CompositionResult(config=config, instances=instances)

        # Assert
        self.assertEqual(result.config, config)
        self.assertEqual(len(result.instances), 1)
        self.assertIn("db", result.instances)

    def test_CompositionResult__DefaultInstances__IsEmptyDict(self):
        # Act
        result = CompositionResult(config={})

        # Assert
        self.assertIsInstance(result.instances, dict)
        self.assertEqual(len(result.instances), 0)


class CacheFunctionTests(TestCase):
    """Tests for cache-related functions."""

    def setUp(self):
        clear_cache()

    def tearDown(self):
        clear_cache()

    def test_clearCache__AfterCall__NoErrors(self):
        # Act & Assert - should not raise
        clear_cache()

    def test_setCacheSize__PositiveSize__NoErrors(self):
        # Act & Assert - should not raise
        set_cache_size(100)

    def test_setCacheSize__ZeroSize__MeansUnlimited(self):
        # Act & Assert - should not raise
        set_cache_size(0)


class LineNumberExtractionTests(TestCase):
    """Tests for line number extraction from CommentedMap."""

    def test_getLineNumber__PositionMapWithLineInfo__ReturnsLine(self):
        # Arrange
        provenance = ProvenanceBuilder()
        walker = IncrementalComposer(None, provenance)

        # Create a PositionMap with line info
        config = PositionMap({"key": "value"})
        config.set_position("key", 6, 1)  # line 6, column 1 (1-indexed)

        # Act
        line = walker._get_line_number(config, "key")

        # Assert - should be 1-indexed
        self.assertEqual(line, 6)

    def test_getLineNumber__RegularDict__ReturnsNone(self):
        # Arrange
        provenance = ProvenanceBuilder()
        walker = IncrementalComposer(None, provenance)
        config = {"key": "value"}

        # Act
        line = walker._get_line_number(config, "key")

        # Assert
        self.assertIsNone(line)

    def test_getLineNumber__KeyNotInPositionMap__ReturnsNone(self):
        # Arrange
        provenance = ProvenanceBuilder()
        walker = IncrementalComposer(None, provenance)
        config = PositionMap({"key": "value"})
        # No position info added

        # Act
        line = walker._get_line_number(config, "key")

        # Assert
        self.assertIsNone(line)
