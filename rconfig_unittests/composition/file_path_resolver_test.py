"""Tests for FilePathResolver."""

import tempfile
from pathlib import Path
from unittest import TestCase

from rconfig.composition.file_path_resolver import FilePathResolver
from rconfig.errors import AmbiguousRefError, RefResolutionError


class HasExtensionTests(TestCase):
    """Tests for _has_extension helper method."""

    def setUp(self):
        self.resolver = FilePathResolver(None)

    def test_hasExtension__WithYamlExtension__ReturnsTrue(self):
        # Act & Assert
        self.assertTrue(self.resolver._has_extension("models/vit.yaml"))

    def test_hasExtension__WithYmlExtension__ReturnsTrue(self):
        # Act & Assert
        self.assertTrue(self.resolver._has_extension("config.yml"))

    def test_hasExtension__WithJsonExtension__ReturnsTrue(self):
        # Act & Assert
        self.assertTrue(self.resolver._has_extension("config.json"))

    def test_hasExtension__WithTomlExtension__ReturnsTrue(self):
        # Act & Assert
        self.assertTrue(self.resolver._has_extension("config.toml"))

    def test_hasExtension__NoExtension__ReturnsFalse(self):
        # Act & Assert
        self.assertFalse(self.resolver._has_extension("models/vit"))

    def test_hasExtension__NoExtensionWithPath__ReturnsFalse(self):
        # Act & Assert
        self.assertFalse(self.resolver._has_extension("path/to/model"))

    def test_hasExtension__DotFile__ReturnsFalse(self):
        # A dotfile like .hidden has no extension
        # Act & Assert
        self.assertFalse(self.resolver._has_extension(".hidden"))

    def test_hasExtension__DotFileWithExtension__ReturnsTrue(self):
        # .env.yaml has extension .yaml
        # Act & Assert
        self.assertTrue(self.resolver._has_extension(".env.yaml"))

    def test_hasExtension__MultipleDots__ReturnsTrue(self):
        # config.backup.yaml has extension .yaml
        # Act & Assert
        self.assertTrue(self.resolver._has_extension("config.backup.yaml"))


class ResolveTests(TestCase):
    """Tests for FilePathResolver.resolve()."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_root = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _write_file(self, name: str, content: str) -> Path:
        """Write a file to temp directory."""
        path = self.config_root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def _create_resolver(self) -> FilePathResolver:
        """Create a resolver with the temp directory as root."""
        return FilePathResolver(self.config_root)

    # === Single file resolution ===

    def test_resolve__SingleYamlFile__ReturnsYamlPath(self):
        # Arrange
        self._write_file("models/vit.yaml", "_target_: model\nlayers: 12")
        resolver = self._create_resolver()

        # Act
        resolved = resolver.resolve("models/vit", self.config_root, "model")

        # Assert
        self.assertEqual(resolved.name, "vit.yaml")

    def test_resolve__SingleYmlFile__ReturnsYmlPath(self):
        # Arrange
        self._write_file("models/resnet.yml", "_target_: model\nlayers: 50")
        resolver = self._create_resolver()

        # Act
        resolved = resolver.resolve("models/resnet", self.config_root, "model")

        # Assert
        self.assertEqual(resolved.name, "resnet.yml")

    def test_resolve__SingleJsonFile__ReturnsJsonPath(self):
        # Arrange
        self._write_file("models/resnet.json", '{"_target_": "model"}')
        resolver = self._create_resolver()

        # Act
        resolved = resolver.resolve("models/resnet", self.config_root, "model")

        # Assert
        self.assertEqual(resolved.name, "resnet.json")

    def test_resolve__SingleTomlFile__ReturnsTomlPath(self):
        # Arrange
        self._write_file("config.toml", '_target_ = "model"')
        resolver = self._create_resolver()

        # Act
        resolved = resolver.resolve("config", self.config_root, "settings")

        # Assert
        self.assertEqual(resolved.name, "config.toml")

    # === No files found ===

    def test_resolve__NoFilesExist__RaisesRefResolutionError(self):
        # Arrange
        (self.config_root / "models").mkdir(parents=True)
        resolver = self._create_resolver()

        # Act & Assert
        with self.assertRaises(RefResolutionError) as ctx:
            resolver.resolve("models/missing", self.config_root, "model")

        self.assertIn("no config file found", str(ctx.exception))
        self.assertIn("missing.*", str(ctx.exception))

    def test_resolve__DirectoryNotExists__RaisesRefResolutionError(self):
        # Arrange
        resolver = self._create_resolver()

        # Act & Assert
        with self.assertRaises(RefResolutionError) as ctx:
            resolver.resolve("nonexistent/model", self.config_root, "model")

        self.assertIn("directory not found", str(ctx.exception))

    # === Multiple files found ===

    def test_resolve__MultipleFiles__RaisesAmbiguousRefError(self):
        # Arrange
        self._write_file("models/vit.yaml", "_target_: model")
        self._write_file("models/vit.json", '{"_target_": "model"}')
        resolver = self._create_resolver()

        # Act & Assert
        with self.assertRaises(AmbiguousRefError) as ctx:
            resolver.resolve("models/vit", self.config_root, "model")

        self.assertEqual(ctx.exception.ref_path, "models/vit")
        self.assertIn("vit.json", ctx.exception.found_files)
        self.assertIn("vit.yaml", ctx.exception.found_files)

    def test_resolve__YamlAndYml__RaisesAmbiguousRefError(self):
        # Arrange - both .yaml and .yml exist
        self._write_file("config.yaml", "_target_: app")
        self._write_file("config.yml", "_target_: app")
        resolver = self._create_resolver()

        # Act & Assert
        with self.assertRaises(AmbiguousRefError) as ctx:
            resolver.resolve("config", self.config_root, "app")

        self.assertEqual(len(ctx.exception.found_files), 2)

    def test_resolve__ThreeFormats__RaisesAmbiguousRefError(self):
        # Arrange
        self._write_file("config.yaml", "_target_: app")
        self._write_file("config.json", '{"_target_": "app"}')
        self._write_file("config.toml", '_target_ = "app"')
        resolver = self._create_resolver()

        # Act & Assert
        with self.assertRaises(AmbiguousRefError) as ctx:
            resolver.resolve("config", self.config_root, "app")

        self.assertEqual(len(ctx.exception.found_files), 3)

    # === Unsupported extensions ===

    def test_resolve__OnlyUnsupportedExtensions__RaisesRefResolutionError(self):
        # Arrange
        self._write_file("models/vit.bak", "backup file")
        self._write_file("models/vit.txt", "text file")
        resolver = self._create_resolver()

        # Act & Assert
        with self.assertRaises(RefResolutionError) as ctx:
            resolver.resolve("models/vit", self.config_root, "model")

        self.assertIn("unsupported extension", str(ctx.exception))

    def test_resolve__MixedSupportedUnsupported__IgnoresUnsupported(self):
        # Arrange
        self._write_file("models/vit.yaml", "_target_: model")
        self._write_file("models/vit.bak", "backup file")
        resolver = self._create_resolver()

        # Act
        resolved = resolver.resolve("models/vit", self.config_root, "model")

        # Assert - should find yaml, ignoring bak
        self.assertEqual(resolved.name, "vit.yaml")

    # === Explicit extensions still work ===

    def test_resolve__ExplicitExtension__WorksAsNormal(self):
        # Arrange
        self._write_file("models/vit.yaml", "_target_: model")
        resolver = self._create_resolver()

        # Act
        resolved = resolver.resolve("models/vit.yaml", self.config_root, "model")

        # Assert
        self.assertEqual(resolved.name, "vit.yaml")

    def test_resolve__ExplicitExtensionNotFound__RaisesError(self):
        # Arrange
        self._write_file("models/vit.yaml", "_target_: model")
        resolver = self._create_resolver()

        # Act & Assert - looking for .json specifically should fail
        with self.assertRaises(RefResolutionError):
            resolver.resolve("models/vit.json", self.config_root, "model")

    # === Path types ===

    def test_resolve__AbsolutePath__ResolvesFromRoot(self):
        # Arrange
        self._write_file("shared/utils.yaml", "_target_: utils")
        resolver = self._create_resolver()

        # Act
        resolved = resolver.resolve("/shared/utils", self.config_root, "tools")

        # Assert
        self.assertEqual(resolved.name, "utils.yaml")

    def test_resolve__AbsolutePathWithoutConfigRoot__RaisesRefResolutionError(self):
        # Arrange
        resolver = FilePathResolver(config_root=None)

        # Act & Assert
        with self.assertRaises(RefResolutionError) as ctx:
            resolver.resolve("/shared/utils", self.config_root, "tools")

        self.assertIn("cannot use absolute path without config root", str(ctx.exception))

    def test_resolve__RelativeParentPath__Resolves(self):
        # Arrange
        self._write_file("shared/base.yaml", "_target_: base")
        self._write_file("models/vit.yaml", "_target_: model")
        resolver = self._create_resolver()
        models_dir = self.config_root / "models"

        # Act
        resolved = resolver.resolve("../shared/base", models_dir, "model")

        # Assert
        self.assertEqual(resolved.name, "base.yaml")

    def test_resolve__CurrentDirPath__Resolves(self):
        # Arrange
        self._write_file("models/base.yaml", "_target_: base")
        resolver = self._create_resolver()
        models_dir = self.config_root / "models"

        # Act
        resolved = resolver.resolve("./base", models_dir, "model")

        # Assert
        self.assertEqual(resolved.name, "base.yaml")
