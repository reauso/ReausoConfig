"""Integration tests for StrOrPath support in public API.

Tests that string paths work correctly across all public API functions
that accept path parameters.
"""

import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent

import rconfig as rc
from rconfig.composition import clear_cache


@dataclass
class SimpleModel:
    """Simple test model for instantiation tests."""

    name: str
    value: int = 10


class StrOrPathInstantiateTests(unittest.TestCase):
    """Tests for string path support in instantiate()."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_root = Path(self.temp_dir.name)
        clear_cache()
        rc.register(name="simple_model", target=SimpleModel)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()
        clear_cache()
        rc.unregister("simple_model")

    def _write_config(self, name: str, content: str) -> Path:
        """Write a config file to the temporary directory."""
        path = self.config_root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def test_instantiate__StringPath__InstantiatesCorrectly(self):
        """Test that string paths work with instantiate()."""
        # Arrange
        config_path = self._write_config(
            "config.yaml",
            dedent("""
                _target_: simple_model
                name: test
                value: 42
            """),
        )

        # Act
        result = rc.instantiate(str(config_path), cli_overrides=False)

        # Assert
        self.assertIsInstance(result, SimpleModel)
        self.assertEqual(result.name, "test")
        self.assertEqual(result.value, 42)

    def test_instantiate__StringPathWithInnerPath__InstantiatesCorrectly(self):
        """Test that string paths work with inner_path parameter."""
        # Arrange
        config_path = self._write_config(
            "config.yaml",
            dedent("""
                _target_: simple_model
                name: outer
                nested:
                  _target_: simple_model
                  name: inner
                  value: 99
            """),
        )

        # Act
        result = rc.instantiate(
            str(config_path), inner_path="nested", cli_overrides=False
        )

        # Assert
        self.assertIsInstance(result, SimpleModel)
        self.assertEqual(result.name, "inner")
        self.assertEqual(result.value, 99)


class StrOrPathValidateTests(unittest.TestCase):
    """Tests for string path support in validate()."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_root = Path(self.temp_dir.name)
        clear_cache()
        rc.register(name="simple_model", target=SimpleModel)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()
        clear_cache()
        rc.unregister("simple_model")

    def _write_config(self, name: str, content: str) -> Path:
        """Write a config file to the temporary directory."""
        path = self.config_root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def test_validate__StringPath__ValidatesCorrectly(self):
        """Test that string paths work with validate()."""
        # Arrange
        config_path = self._write_config(
            "config.yaml",
            dedent("""
                _target_: simple_model
                name: test
            """),
        )

        # Act
        result = rc.validate(str(config_path), cli_overrides=False)

        # Assert
        self.assertTrue(result.valid)


class StrOrPathProvenanceTests(unittest.TestCase):
    """Tests for string path support in get_provenance()."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_root = Path(self.temp_dir.name)
        clear_cache()
        rc.register(name="simple_model", target=SimpleModel)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()
        clear_cache()
        rc.unregister("simple_model")

    def _write_config(self, name: str, content: str) -> Path:
        """Write a config file to the temporary directory."""
        path = self.config_root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def test_get_provenance__StringPath__ReturnsProvenance(self):
        """Test that string paths work with get_provenance()."""
        # Arrange
        config_path = self._write_config(
            "config.yaml",
            dedent("""
                _target_: simple_model
                name: test
                value: 42
            """),
        )

        # Act
        prov = rc.get_provenance(str(config_path), cli_overrides=False)

        # Assert
        self.assertIsNotNone(prov)
        entry = prov.get("name")
        self.assertIsNotNone(entry)


class StrOrPathDiffTests(unittest.TestCase):
    """Tests for string path support in diff()."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_root = Path(self.temp_dir.name)
        clear_cache()
        rc.register(name="simple_model", target=SimpleModel)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()
        clear_cache()
        rc.unregister("simple_model")

    def _write_config(self, name: str, content: str) -> Path:
        """Write a config file to the temporary directory."""
        path = self.config_root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def test_diff__StringPaths__ComparesCorrectly(self):
        """Test that string paths work with diff()."""
        # Arrange
        config_v1 = self._write_config(
            "v1.yaml",
            dedent("""
                _target_: simple_model
                name: test
                value: 10
            """),
        )
        config_v2 = self._write_config(
            "v2.yaml",
            dedent("""
                _target_: simple_model
                name: test
                value: 20
            """),
        )

        # Act
        diff = rc.diff(str(config_v1), str(config_v2), cli_overrides=False)

        # Assert
        self.assertIsNotNone(diff)
        # Check that we found changes (value changed from 10 to 20)
        self.assertGreater(len(diff.changed), 0)
        # Verify value is in the changed entries
        self.assertIn("value", diff.changed)

    def test_diff__MixedPathTypes__ComparesCorrectly(self):
        """Test that diff() accepts mixed path types (string and Path)."""
        # Arrange
        config_v1 = self._write_config(
            "v1.yaml",
            dedent("""
                _target_: simple_model
                name: test
                value: 10
            """),
        )
        config_v2 = self._write_config(
            "v2.yaml",
            dedent("""
                _target_: simple_model
                name: changed
                value: 10
            """),
        )

        # Act - string for left, Path for right
        diff = rc.diff(str(config_v1), config_v2, cli_overrides=False)

        # Assert
        self.assertIsNotNone(diff)
        # Check that we found changes (name changed)
        self.assertGreater(len(diff.changed), 0)
        # Verify name is in the changed entries
        self.assertIn("name", diff.changed)


class StrOrPathExportTests(unittest.TestCase):
    """Tests for string path support in export functions."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_root = Path(self.temp_dir.name)
        clear_cache()
        rc.register(name="simple_model", target=SimpleModel)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()
        clear_cache()
        rc.unregister("simple_model")

    def _write_config(self, name: str, content: str) -> Path:
        """Write a config file to the temporary directory."""
        path = self.config_root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def test_to_dict__StringPath__ReturnsDict(self):
        """Test that string paths work with to_dict()."""
        # Arrange
        config_path = self._write_config(
            "config.yaml",
            dedent("""
                _target_: simple_model
                name: test
                value: 42
            """),
        )

        # Act
        result = rc.to_dict(str(config_path), cli_overrides=False)

        # Assert
        self.assertIsInstance(result, dict)
        self.assertEqual(result["name"], "test")

    def test_to_yaml__StringPath__ReturnsYamlString(self):
        """Test that string paths work with to_yaml()."""
        # Arrange
        config_path = self._write_config(
            "config.yaml",
            dedent("""
                _target_: simple_model
                name: test
            """),
        )

        # Act
        result = rc.to_yaml(str(config_path), cli_overrides=False)

        # Assert
        self.assertIsInstance(result, str)
        self.assertIn("name: test", result)

    def test_to_json__StringPath__ReturnsJsonString(self):
        """Test that string paths work with to_json()."""
        # Arrange
        config_path = self._write_config(
            "config.yaml",
            dedent("""
                _target_: simple_model
                name: test
            """),
        )

        # Act
        result = rc.to_json(str(config_path), cli_overrides=False)

        # Assert
        self.assertIsInstance(result, str)
        self.assertIn('"name"', result)

    def test_to_toml__StringPath__ReturnsTomlString(self):
        """Test that string paths work with to_toml()."""
        # Arrange
        config_path = self._write_config(
            "config.yaml",
            dedent("""
                _target_: simple_model
                name: test
            """),
        )

        # Act
        result = rc.to_toml(str(config_path), cli_overrides=False)

        # Assert
        self.assertIsInstance(result, str)
        self.assertIn('name = "test"', result)

    def test_to_file__StringSourceAndOutput__ExportsCorrectly(self):
        """Test that string paths work with to_file() for both source and output."""
        # Arrange
        config_path = self._write_config(
            "config.yaml",
            dedent("""
                _target_: simple_model
                name: test
                value: 42
            """),
        )
        output_path = self.config_root / "output.json"

        # Act
        rc.to_file(str(config_path), str(output_path), cli_overrides=False)

        # Assert
        self.assertTrue(output_path.exists())
        with open(output_path) as f:
            content = f.read()
        self.assertIn('"name"', content)

    def test_to_files__StringSourceAndOutput__ExportsCorrectly(self):
        """Test that string paths work with to_files()."""
        # Arrange
        config_path = self._write_config(
            "config.yaml",
            dedent("""
                _target_: simple_model
                name: test
            """),
        )
        output_path = self.config_root / "output" / "config.yaml"

        # Act
        rc.to_files(str(config_path), str(output_path), cli_overrides=False)

        # Assert
        self.assertTrue(output_path.exists())


class StrOrPathLoaderTests(unittest.TestCase):
    """Tests for string path support in loader functions."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_root = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _write_config(self, name: str, content: str) -> Path:
        """Write a config file to the temporary directory."""
        path = self.config_root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def test_get_loader__StringPath__ReturnsLoader(self):
        """Test that string paths work with get_loader()."""
        # Arrange
        from rconfig.loaders import get_loader

        config_path = self._write_config("config.yaml", "key: value\n")

        # Act
        loader = get_loader(str(config_path))

        # Assert
        self.assertIsNotNone(loader)

    def test_load_config__StringPath__LoadsConfig(self):
        """Test that string paths work with load_config()."""
        # Arrange
        from rconfig.loaders import load_config

        config_path = self._write_config("config.yaml", "key: value\n")

        # Act
        result = load_config(str(config_path))

        # Assert
        self.assertEqual(result["key"], "value")


class StrOrPathComposerTests(unittest.TestCase):
    """Tests for string path support in composer functions."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_root = Path(self.temp_dir.name)
        clear_cache()
        rc.register(name="simple_model", target=SimpleModel)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()
        clear_cache()
        rc.unregister("simple_model")

    def _write_config(self, name: str, content: str) -> Path:
        """Write a config file to the temporary directory."""
        path = self.config_root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def test_compose__StringPath__ComposesCorrectly(self):
        """Test that string paths work with compose()."""
        # Arrange
        from rconfig.composition import compose

        config_path = self._write_config(
            "config.yaml",
            dedent("""
                _target_: simple_model
                name: test
            """),
        )

        # Act
        result = compose(str(config_path))

        # Assert
        self.assertEqual(result["name"], "test")

    def test_ConfigComposer__StringPath__ComposesCorrectly(self):
        """Test that string paths work with ConfigComposer.compose()."""
        # Arrange
        from rconfig.composition import ConfigComposer

        config_path = self._write_config(
            "config.yaml",
            dedent("""
                _target_: simple_model
                name: test
            """),
        )
        composer = ConfigComposer()

        # Act
        result = composer.compose(str(config_path))

        # Assert
        self.assertEqual(result["name"], "test")

    def test_ConfigComposer__StringConfigRoot__InitializesCorrectly(self):
        """Test that ConfigComposer accepts string for config_root."""
        # Arrange
        from rconfig.composition import ConfigComposer

        config_path = self._write_config(
            "config.yaml",
            dedent("""
                _target_: simple_model
                name: test
            """),
        )

        # Act
        composer = ConfigComposer(config_root=str(self.config_root))
        result = composer.compose(config_path)

        # Assert
        self.assertEqual(result["name"], "test")


if __name__ == "__main__":
    unittest.main()
