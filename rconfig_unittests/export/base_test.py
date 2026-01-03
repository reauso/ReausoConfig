"""Tests for rconfig.export.base module."""

from typing import Any
from unittest import TestCase

from rconfig.export.base import Exporter


class ExporterTests(TestCase):
    """Tests for the Exporter abstract base class."""

    def test_Exporter__DirectInstantiation__RaisesTypeError(self):
        """Cannot instantiate Exporter directly."""
        with self.assertRaises(TypeError) as ctx:
            Exporter()  # type: ignore

        self.assertIn("abstract", str(ctx.exception).lower())

    def test_Exporter__SubclassWithoutExport__RaisesTypeError(self):
        """Subclass without export method cannot be instantiated."""

        class IncompleteExporter(Exporter):
            pass

        with self.assertRaises(TypeError) as ctx:
            IncompleteExporter()  # type: ignore

        self.assertIn("abstract", str(ctx.exception).lower())

    def test_Exporter__SubclassWithExport__Instantiates(self):
        """Subclass implementing export can be instantiated."""

        class ConcreteExporter(Exporter):
            def export(self, config: dict[str, Any]) -> str:
                return "exported"

        exporter = ConcreteExporter()
        self.assertIsInstance(exporter, Exporter)

    def test_Exporter__SubclassExport__CanBeCalledWithConfig(self):
        """Subclass export method works correctly."""

        class ConcreteExporter(Exporter):
            def export(self, config: dict[str, Any]) -> dict[str, Any]:
                return {"result": config}

        exporter = ConcreteExporter()
        result = exporter.export({"key": "value"})
        self.assertEqual(result, {"result": {"key": "value"}})
