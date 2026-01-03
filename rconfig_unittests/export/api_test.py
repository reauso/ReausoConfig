"""Tests for export API functions in rconfig/__init__.py."""

import tempfile
from pathlib import Path
from typing import Any
from unittest import TestCase

from ruamel.yaml import YAML
from io import StringIO

import rconfig as rc
from rconfig.composition import clear_cache
from rconfig.export import Exporter
from rconfig_unittests.fixtures import MockFileSystem, mock_filesystem


class ToDictTests(TestCase):
    """Tests for rc.to_dict()."""

    def setUp(self):
        """Clear cache before each test."""
        clear_cache()

    def tearDown(self):
        """Clear cache after each test."""
        clear_cache()

    def _parse_yaml(self, yaml_str: str) -> dict:
        """Helper to parse YAML string back to dict."""
        yaml = YAML()
        return yaml.load(StringIO(yaml_str))

    def test_to_dict__SimpleConfig__ReturnsResolvedDict(self):
        """to_dict returns resolved config as dict."""
        fs = MockFileSystem()
        fs.add_file("/configs/app.yaml", {"key": "value", "number": 42})

        with mock_filesystem(fs):
            result = rc.to_dict(Path("/configs/app.yaml"), cli_overrides=False)

        self.assertEqual(result["key"], "value")
        self.assertEqual(result["number"], 42)

    def test_to_dict__WithInterpolation__ResolvesValues(self):
        """to_dict resolves interpolation expressions."""
        fs = MockFileSystem()
        fs.add_file(
            "/configs/app.yaml",
            {"base": 10, "doubled": "${base * 2}"},
        )

        with mock_filesystem(fs):
            result = rc.to_dict(Path("/configs/app.yaml"), cli_overrides=False)

        self.assertEqual(result["base"], 10)
        self.assertEqual(result["doubled"], 20)

    def test_to_dict__WithOverrides__AppliesOverrides(self):
        """to_dict applies programmatic overrides."""
        fs = MockFileSystem()
        fs.add_file("/configs/app.yaml", {"key": "original"})

        with mock_filesystem(fs):
            result = rc.to_dict(
                Path("/configs/app.yaml"),
                overrides={"key": "overridden"},
                cli_overrides=False,
            )

        self.assertEqual(result["key"], "overridden")

    def test_to_dict__ExcludeMarkersTrue__RemovesMarkers(self):
        """to_dict with exclude_markers removes markers."""
        fs = MockFileSystem()
        fs.add_file(
            "/configs/app.yaml",
            {"_target_": "SomeClass", "value": 42},
        )

        with mock_filesystem(fs):
            result = rc.to_dict(
                Path("/configs/app.yaml"),
                exclude_markers=True,
                cli_overrides=False,
            )

        self.assertNotIn("_target_", result)
        self.assertEqual(result["value"], 42)

    def test_to_dict__WithRef__ResolvesReferences(self):
        """to_dict resolves _ref_ references."""
        fs = MockFileSystem()
        fs.add_file(
            "/configs/app.yaml",
            {"model": {"_ref_": "./model.yaml", "override": "value"}},
        )
        fs.add_file("/configs/model.yaml", {"base": "config"})

        with mock_filesystem(fs):
            result = rc.to_dict(Path("/configs/app.yaml"), cli_overrides=False)

        self.assertEqual(result["model"]["base"], "config")
        self.assertEqual(result["model"]["override"], "value")


class ToYamlTests(TestCase):
    """Tests for rc.to_yaml()."""

    def setUp(self):
        """Clear cache before each test."""
        clear_cache()

    def tearDown(self):
        """Clear cache after each test."""
        clear_cache()

    def _parse_yaml(self, yaml_str: str) -> dict:
        """Helper to parse YAML string back to dict."""
        yaml = YAML()
        return yaml.load(StringIO(yaml_str))

    def test_to_yaml__SimpleConfig__ReturnsYamlString(self):
        """to_yaml returns valid YAML string."""
        fs = MockFileSystem()
        fs.add_file("/configs/app.yaml", {"key": "value"})

        with mock_filesystem(fs):
            result = rc.to_yaml(Path("/configs/app.yaml"), cli_overrides=False)

        self.assertIsInstance(result, str)
        parsed = self._parse_yaml(result)
        self.assertEqual(parsed["key"], "value")

    def test_to_yaml__WithInterpolation__ResolvesValues(self):
        """to_yaml resolves interpolation expressions."""
        fs = MockFileSystem()
        fs.add_file(
            "/configs/app.yaml",
            {"base": 5, "squared": "${base * base}"},
        )

        with mock_filesystem(fs):
            result = rc.to_yaml(Path("/configs/app.yaml"), cli_overrides=False)

        parsed = self._parse_yaml(result)
        self.assertEqual(parsed["squared"], 25)

    def test_to_yaml__WithOverrides__AppliesOverrides(self):
        """to_yaml applies programmatic overrides."""
        fs = MockFileSystem()
        fs.add_file("/configs/app.yaml", {"key": "original"})

        with mock_filesystem(fs):
            result = rc.to_yaml(
                Path("/configs/app.yaml"),
                overrides={"key": "overridden"},
                cli_overrides=False,
            )

        parsed = self._parse_yaml(result)
        self.assertEqual(parsed["key"], "overridden")


class ExportTests(TestCase):
    """Tests for rc.export()."""

    def setUp(self):
        """Clear cache before each test."""
        clear_cache()

    def tearDown(self):
        """Clear cache after each test."""
        clear_cache()

    def test_export__CustomExporter__UsesExporter(self):
        """export uses custom exporter."""

        class UpperCaseExporter(Exporter):
            def export(self, config: dict[str, Any]) -> str:
                return str(config).upper()

        fs = MockFileSystem()
        fs.add_file("/configs/app.yaml", {"key": "value"})

        with mock_filesystem(fs):
            result = rc.export(
                Path("/configs/app.yaml"),
                exporter=UpperCaseExporter(),
                cli_overrides=False,
            )

        self.assertIsInstance(result, str)
        self.assertIn("KEY", result)
        self.assertIn("VALUE", result)


class ToYamlFileTests(TestCase):
    """Tests for rc.to_yaml_file()."""

    def setUp(self):
        """Set up test fixtures."""
        clear_cache()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.output_dir = Path(self.temp_dir.name)

    def tearDown(self):
        """Clean up test fixtures."""
        self.temp_dir.cleanup()
        clear_cache()

    def _parse_yaml(self, yaml_str: str) -> dict:
        """Helper to parse YAML string back to dict."""
        yaml = YAML()
        return yaml.load(StringIO(yaml_str))

    def test_to_yaml_file__SimpleConfig__WritesFile(self):
        """to_yaml_file writes config to file."""
        fs = MockFileSystem()
        fs.add_file("/configs/app.yaml", {"key": "value"})
        output_path = self.output_dir / "output.yaml"

        with mock_filesystem(fs):
            rc.to_yaml_file(
                Path("/configs/app.yaml"),
                output_path,
                cli_overrides=False,
            )

        self.assertTrue(output_path.exists())
        content = output_path.read_text()
        parsed = self._parse_yaml(content)
        self.assertEqual(parsed["key"], "value")

    def test_to_yaml_file__WithOverrides__AppliesOverrides(self):
        """to_yaml_file applies overrides."""
        fs = MockFileSystem()
        fs.add_file("/configs/app.yaml", {"key": "original"})
        output_path = self.output_dir / "output.yaml"

        with mock_filesystem(fs):
            rc.to_yaml_file(
                Path("/configs/app.yaml"),
                output_path,
                overrides={"key": "overridden"},
                cli_overrides=False,
            )

        content = output_path.read_text()
        parsed = self._parse_yaml(content)
        self.assertEqual(parsed["key"], "overridden")


class ToYamlFilesTests(TestCase):
    """Tests for rc.to_yaml_files()."""

    def setUp(self):
        """Set up test fixtures."""
        clear_cache()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.output_dir = Path(self.temp_dir.name) / "output"

    def tearDown(self):
        """Clean up test fixtures."""
        self.temp_dir.cleanup()
        clear_cache()

    def _parse_yaml(self, yaml_str: str) -> dict:
        """Helper to parse YAML string back to dict."""
        yaml = YAML()
        return yaml.load(StringIO(yaml_str))

    def test_to_yaml_files__SingleFile__WritesToDirectory(self):
        """to_yaml_files writes to directory."""
        fs = MockFileSystem()
        fs.add_file("/configs/app.yaml", {"key": "value"})

        with mock_filesystem(fs):
            rc.to_yaml_files(
                Path("/configs/app.yaml"),
                self.output_dir,
                cli_overrides=False,
            )

        output_file = self.output_dir / "app.yaml"
        self.assertTrue(output_file.exists())
        content = output_file.read_text()
        parsed = self._parse_yaml(content)
        self.assertEqual(parsed["key"], "value")


class ExportErrorTests(TestCase):
    """Tests for export error handling."""

    def setUp(self):
        """Clear cache before each test."""
        clear_cache()

    def tearDown(self):
        """Clear cache after each test."""
        clear_cache()

    def test_to_dict__RequiredNotSatisfied__RaisesRequiredValueError(self):
        """to_dict raises RequiredValueError for unsatisfied _required_."""
        fs = MockFileSystem()
        fs.add_file(
            "/configs/app.yaml",
            {"value": {"_required_": "int"}},
        )

        with mock_filesystem(fs):
            with self.assertRaises(rc.RequiredValueError):
                rc.to_dict(Path("/configs/app.yaml"), cli_overrides=False)

    def test_to_dict__FileNotFound__RaisesConfigFileError(self):
        """to_dict raises ConfigFileError for missing file."""
        with self.assertRaises(rc.ConfigFileError):
            rc.to_dict(Path("/nonexistent/file.yaml"), cli_overrides=False)

    def test_to_dict__CircularRef__RaisesCircularRefError(self):
        """to_dict raises CircularRefError for circular refs."""
        fs = MockFileSystem()
        fs.add_file("/configs/a.yaml", {"child": {"_ref_": "./b.yaml"}})
        fs.add_file("/configs/b.yaml", {"child": {"_ref_": "./a.yaml"}})

        with mock_filesystem(fs):
            with self.assertRaises(rc.CircularRefError):
                rc.to_dict(Path("/configs/a.yaml"), cli_overrides=False)
