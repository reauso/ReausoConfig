"""Tests for rconfig.export.file_base module."""

from pathlib import Path
from typing import Any
from unittest import TestCase

from rconfig.export.file_base import FileExporter


class FileExporterTests(TestCase):
    """Tests for the FileExporter abstract base class."""

    def test_FileExporter__DirectInstantiation__RaisesTypeError(self):
        """Cannot instantiate FileExporter directly."""
        with self.assertRaises(TypeError) as ctx:
            FileExporter()  # type: ignore

        self.assertIn("abstract", str(ctx.exception).lower())

    def test_FileExporter__SubclassWithoutExportToFile__RaisesTypeError(self):
        """Subclass without export_to_file method cannot be instantiated."""

        class IncompleteExporter(FileExporter):
            pass

        with self.assertRaises(TypeError) as ctx:
            IncompleteExporter()  # type: ignore

        self.assertIn("abstract", str(ctx.exception).lower())

    def test_FileExporter__SubclassWithExportToFile__Instantiates(self):
        """Subclass implementing export_to_file can be instantiated."""

        class ConcreteExporter(FileExporter):
            def export_to_file(
                self,
                config: dict[str, Any],
                output_path: Path,
                *,
                source_path: Path | None = None,
                ref_graph: dict[str, list[str]] | None = None,
            ) -> None:
                pass

        exporter = ConcreteExporter()
        self.assertIsInstance(exporter, FileExporter)

    def test_FileExporter__ExportToFileSignature__AcceptsAllParameters(self):
        """Export method signature accepts all defined parameters."""
        calls = []

        class TrackingExporter(FileExporter):
            def export_to_file(
                self,
                config: dict[str, Any],
                output_path: Path,
                *,
                source_path: Path | None = None,
                ref_graph: dict[str, list[str]] | None = None,
            ) -> None:
                calls.append({
                    "config": config,
                    "output_path": output_path,
                    "source_path": source_path,
                    "ref_graph": ref_graph,
                })

        exporter = TrackingExporter()
        exporter.export_to_file(
            {"key": "value"},
            Path("/output"),
            source_path=Path("/source.yaml"),
            ref_graph={"/source.yaml": ["/ref.yaml"]},
        )

        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["config"], {"key": "value"})
        self.assertEqual(calls[0]["output_path"], Path("/output"))
        self.assertEqual(calls[0]["source_path"], Path("/source.yaml"))
        self.assertEqual(calls[0]["ref_graph"], {"/source.yaml": ["/ref.yaml"]})
