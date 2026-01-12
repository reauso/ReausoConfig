"""Tests for extension-less _ref_ resolution in IncrementalComposer."""

import tempfile
from pathlib import Path
from unittest import TestCase

from rconfig.composition import IncrementalComposer, clear_cache
from rconfig.composition.ProvenanceBuilder import ProvenanceBuilder
from rconfig.errors import AmbiguousRefError, RefResolutionError


class HasExtensionTests(TestCase):
    """Tests for _has_extension helper method."""

    def setUp(self):
        self.builder = ProvenanceBuilder()
        self.walker = IncrementalComposer(None, self.builder)

    def test_hasExtension__WithYamlExtension__ReturnsTrue(self):
        # Act & Assert
        self.assertTrue(self.walker._has_extension("models/vit.yaml"))

    def test_hasExtension__WithYmlExtension__ReturnsTrue(self):
        # Act & Assert
        self.assertTrue(self.walker._has_extension("config.yml"))

    def test_hasExtension__WithJsonExtension__ReturnsTrue(self):
        # Act & Assert
        self.assertTrue(self.walker._has_extension("config.json"))

    def test_hasExtension__WithTomlExtension__ReturnsTrue(self):
        # Act & Assert
        self.assertTrue(self.walker._has_extension("config.toml"))

    def test_hasExtension__NoExtension__ReturnsFalse(self):
        # Act & Assert
        self.assertFalse(self.walker._has_extension("models/vit"))

    def test_hasExtension__NoExtensionWithPath__ReturnsFalse(self):
        # Act & Assert
        self.assertFalse(self.walker._has_extension("path/to/model"))

    def test_hasExtension__DotFile__ReturnsFalse(self):
        # A dotfile like .hidden has no extension
        # Act & Assert
        self.assertFalse(self.walker._has_extension(".hidden"))

    def test_hasExtension__DotFileWithExtension__ReturnsTrue(self):
        # .env.yaml has extension .yaml
        # Act & Assert
        self.assertTrue(self.walker._has_extension(".env.yaml"))

    def test_hasExtension__MultipleDots__ReturnsTrue(self):
        # config.backup.yaml has extension .yaml
        # Act & Assert
        self.assertTrue(self.walker._has_extension("config.backup.yaml"))


class ExtensionlessResolutionTests(TestCase):
    """Tests for extension-less _ref_ resolution."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_root = Path(self.temp_dir.name)
        clear_cache()

    def tearDown(self):
        self.temp_dir.cleanup()
        clear_cache()

    def _write_file(self, name: str, content: str) -> Path:
        """Write a file to temp directory."""
        path = self.config_root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def _create_walker(self) -> IncrementalComposer:
        """Create a walker with the temp directory as root."""
        builder = ProvenanceBuilder()
        return IncrementalComposer(self.config_root, builder)

    # === Single file resolution ===

    def test_resolveExtensionless__SingleYamlFile__ReturnsYamlPath(self):
        # Arrange
        self._write_file("models/vit.yaml", "_target_: model\nlayers: 12")
        walker = self._create_walker()

        # Act
        resolved = walker._resolve_file_path(
            "models/vit", self.config_root, "model"
        )

        # Assert
        self.assertEqual(resolved.name, "vit.yaml")

    def test_resolveExtensionless__SingleYmlFile__ReturnsYmlPath(self):
        # Arrange
        self._write_file("models/resnet.yml", "_target_: model\nlayers: 50")
        walker = self._create_walker()

        # Act
        resolved = walker._resolve_file_path(
            "models/resnet", self.config_root, "model"
        )

        # Assert
        self.assertEqual(resolved.name, "resnet.yml")

    def test_resolveExtensionless__SingleJsonFile__ReturnsJsonPath(self):
        # Arrange
        self._write_file("models/resnet.json", '{"_target_": "model"}')
        walker = self._create_walker()

        # Act
        resolved = walker._resolve_file_path(
            "models/resnet", self.config_root, "model"
        )

        # Assert
        self.assertEqual(resolved.name, "resnet.json")

    def test_resolveExtensionless__SingleTomlFile__ReturnsTomlPath(self):
        # Arrange
        self._write_file("config.toml", '_target_ = "model"')
        walker = self._create_walker()

        # Act
        resolved = walker._resolve_file_path(
            "config", self.config_root, "settings"
        )

        # Assert
        self.assertEqual(resolved.name, "config.toml")

    # === No files found ===

    def test_resolveExtensionless__NoFilesExist__RaisesRefResolutionError(self):
        # Arrange
        (self.config_root / "models").mkdir(parents=True)
        walker = self._create_walker()

        # Act & Assert
        with self.assertRaises(RefResolutionError) as ctx:
            walker._resolve_file_path("models/missing", self.config_root, "model")

        self.assertIn("no config file found", str(ctx.exception))
        self.assertIn("missing.*", str(ctx.exception))

    def test_resolveExtensionless__DirectoryNotExists__RaisesRefResolutionError(self):
        # Arrange
        walker = self._create_walker()

        # Act & Assert
        with self.assertRaises(RefResolutionError) as ctx:
            walker._resolve_file_path(
                "nonexistent/model", self.config_root, "model"
            )

        self.assertIn("directory not found", str(ctx.exception))

    # === Multiple files found ===

    def test_resolveExtensionless__MultipleFiles__RaisesAmbiguousRefError(self):
        # Arrange
        self._write_file("models/vit.yaml", "_target_: model")
        self._write_file("models/vit.json", '{"_target_": "model"}')
        walker = self._create_walker()

        # Act & Assert
        with self.assertRaises(AmbiguousRefError) as ctx:
            walker._resolve_file_path("models/vit", self.config_root, "model")

        self.assertEqual(ctx.exception.ref_path, "models/vit")
        self.assertIn("vit.json", ctx.exception.found_files)
        self.assertIn("vit.yaml", ctx.exception.found_files)

    def test_resolveExtensionless__YamlAndYml__RaisesAmbiguousRefError(self):
        # Arrange - both .yaml and .yml exist
        self._write_file("config.yaml", "_target_: app")
        self._write_file("config.yml", "_target_: app")
        walker = self._create_walker()

        # Act & Assert
        with self.assertRaises(AmbiguousRefError) as ctx:
            walker._resolve_file_path("config", self.config_root, "app")

        self.assertEqual(len(ctx.exception.found_files), 2)

    def test_resolveExtensionless__ThreeFormats__RaisesAmbiguousRefError(self):
        # Arrange
        self._write_file("config.yaml", "_target_: app")
        self._write_file("config.json", '{"_target_": "app"}')
        self._write_file("config.toml", '_target_ = "app"')
        walker = self._create_walker()

        # Act & Assert
        with self.assertRaises(AmbiguousRefError) as ctx:
            walker._resolve_file_path("config", self.config_root, "app")

        self.assertEqual(len(ctx.exception.found_files), 3)

    # === Unsupported extensions ===

    def test_resolveExtensionless__OnlyUnsupportedExtensions__RaisesRefResolutionError(self):
        # Arrange
        self._write_file("models/vit.bak", "backup file")
        self._write_file("models/vit.txt", "text file")
        walker = self._create_walker()

        # Act & Assert
        with self.assertRaises(RefResolutionError) as ctx:
            walker._resolve_file_path("models/vit", self.config_root, "model")

        self.assertIn("unsupported extension", str(ctx.exception))

    def test_resolveExtensionless__MixedSupportedUnsupported__IgnoresUnsupported(self):
        # Arrange
        self._write_file("models/vit.yaml", "_target_: model")
        self._write_file("models/vit.bak", "backup file")
        walker = self._create_walker()

        # Act
        resolved = walker._resolve_file_path(
            "models/vit", self.config_root, "model"
        )

        # Assert - should find yaml, ignoring bak
        self.assertEqual(resolved.name, "vit.yaml")

    # === Explicit extensions still work ===

    def test_resolveFilePath__ExplicitExtension__WorksAsNormal(self):
        # Arrange
        self._write_file("models/vit.yaml", "_target_: model")
        walker = self._create_walker()

        # Act
        resolved = walker._resolve_file_path(
            "models/vit.yaml", self.config_root, "model"
        )

        # Assert
        self.assertEqual(resolved.name, "vit.yaml")

    def test_resolveFilePath__ExplicitExtensionNotFound__RaisesError(self):
        # Arrange
        self._write_file("models/vit.yaml", "_target_: model")
        walker = self._create_walker()

        # Act & Assert - looking for .json specifically should fail
        with self.assertRaises(RefResolutionError):
            walker._resolve_file_path(
                "models/vit.json", self.config_root, "model"
            )

    # === Path types ===

    def test_resolveExtensionless__AbsolutePath__ResolvesFromRoot(self):
        # Arrange
        self._write_file("shared/utils.yaml", "_target_: utils")
        walker = self._create_walker()

        # Act
        resolved = walker._resolve_file_path(
            "/shared/utils", self.config_root, "tools"
        )

        # Assert
        self.assertEqual(resolved.name, "utils.yaml")

    def test_resolveExtensionless__RelativeParentPath__Resolves(self):
        # Arrange
        self._write_file("shared/base.yaml", "_target_: base")
        self._write_file("models/vit.yaml", "_target_: model")
        walker = self._create_walker()
        models_dir = self.config_root / "models"

        # Act
        resolved = walker._resolve_file_path(
            "../shared/base", models_dir, "model"
        )

        # Assert
        self.assertEqual(resolved.name, "base.yaml")

    def test_resolveExtensionless__CurrentDirPath__Resolves(self):
        # Arrange
        self._write_file("models/base.yaml", "_target_: base")
        walker = self._create_walker()
        models_dir = self.config_root / "models"

        # Act
        resolved = walker._resolve_file_path(
            "./base", models_dir, "model"
        )

        # Assert
        self.assertEqual(resolved.name, "base.yaml")
