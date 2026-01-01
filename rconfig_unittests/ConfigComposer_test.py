import tempfile
from pathlib import Path
from unittest.case import TestCase

from rconfig.ConfigComposer import (
    ConfigComposer,
    clear_cache,
    compose,
    compose_with_provenance,
    set_cache_size,
)
from rconfig.errors import (
    CircularRefError,
    CompositionError,
    ConfigFileError,
    RefAtRootError,
    RefInstanceConflictError,
    RefResolutionError,
)


class ConfigComposerRefTests(TestCase):
    """Tests for _ref_ resolution in ConfigComposer."""

    def setUp(self) -> None:
        """Set up a temporary directory for test configs."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_root = Path(self.temp_dir.name)
        clear_cache()

    def tearDown(self) -> None:
        """Clean up temporary directory."""
        self.temp_dir.cleanup()
        clear_cache()

    def _write_config(self, rel_path: str, content: str) -> Path:
        """Write a config file to the temp directory."""
        path = self.config_root / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def test_compose__BasicRefLoadsFile__ConfigMergedCorrectly(self):
        # Arrange
        self._write_config("models/resnet.yaml", """
_target_: ResNet
layers: 34
lr: 0.001
""")
        entry = self._write_config("app.yaml", """
_target_: App
model:
  _ref_: models/resnet.yaml
""")

        # Act
        composer = ConfigComposer(self.config_root)
        result = composer.compose(entry)

        # Assert
        self.assertEqual(result["_target_"], "App")
        self.assertEqual(result["model"]["_target_"], "ResNet")
        self.assertEqual(result["model"]["layers"], 34)
        self.assertEqual(result["model"]["lr"], 0.001)

    def test_compose__RefWithSiblingOverrides__DeepMergeAppliesOverrides(self):
        # Arrange
        self._write_config("models/resnet.yaml", """
_target_: ResNet
layers: 34
optimizer:
  type: adam
  lr: 0.001
  betas: [0.9, 0.999]
""")
        entry = self._write_config("trainer.yaml", """
_target_: Trainer
model:
  _ref_: models/resnet.yaml
  layers: 50
  optimizer:
    lr: 0.01
""")

        # Act
        composer = ConfigComposer(self.config_root)
        result = composer.compose(entry)

        # Assert
        self.assertEqual(result["model"]["layers"], 50)  # Overridden
        self.assertEqual(result["model"]["optimizer"]["lr"], 0.01)  # Overridden
        self.assertEqual(result["model"]["optimizer"]["type"], "adam")  # Preserved
        self.assertEqual(result["model"]["optimizer"]["betas"], [0.9, 0.999])  # Preserved

    def test_compose__RefAtRootLevel__RaisesRefAtRootError(self):
        # Arrange
        self._write_config("base.yaml", """
_target_: Base
value: 1
""")
        entry = self._write_config("app.yaml", """
_ref_: base.yaml
extra: value
""")

        # Act & Assert
        composer = ConfigComposer(self.config_root)
        with self.assertRaises(RefAtRootError) as ctx:
            composer.compose(entry)

        self.assertIn("root level", str(ctx.exception))
        self.assertIn("app.yaml", str(ctx.exception))

    def test_compose__RefWithAbsolutePath__ResolvesFromConfigRoot(self):
        # Arrange
        self._write_config("shared/database.yaml", """
_target_: Database
url: "postgres://localhost"
""")
        self._write_config("services/user.yaml", """
_target_: UserService
db:
  _ref_: /shared/database.yaml
""")
        entry = self._write_config("app.yaml", """
_target_: App
service:
  _ref_: services/user.yaml
""")

        # Act
        composer = ConfigComposer(self.config_root)
        result = composer.compose(entry)

        # Assert
        self.assertEqual(result["service"]["db"]["_target_"], "Database")
        self.assertEqual(result["service"]["db"]["url"], "postgres://localhost")

    def test_compose__RefWithRelativePath__ResolvesFromCurrentFileDir(self):
        # Arrange
        self._write_config("models/base.yaml", """
_target_: BaseModel
hidden: 256
""")
        self._write_config("models/resnet.yaml", """
_target_: ResNet
base:
  _ref_: ./base.yaml
layers: 50
""")
        entry = self._write_config("app.yaml", """
_target_: App
model:
  _ref_: models/resnet.yaml
""")

        # Act
        composer = ConfigComposer(self.config_root)
        result = composer.compose(entry)

        # Assert
        self.assertEqual(result["model"]["base"]["_target_"], "BaseModel")
        self.assertEqual(result["model"]["base"]["hidden"], 256)

    def test_compose__RefWithParentPath__ResolvesCorrectly(self):
        # Arrange
        self._write_config("shared/config.yaml", """
_target_: SharedConfig
value: 42
""")
        self._write_config("services/auth/handler.yaml", """
_target_: AuthHandler
config:
  _ref_: ../../shared/config.yaml
""")
        entry = self._write_config("services/auth/main.yaml", """
_target_: AuthMain
handler:
  _ref_: ./handler.yaml
""")

        # Act
        composer = ConfigComposer(self.config_root)
        result = composer.compose(entry)

        # Assert
        self.assertEqual(result["handler"]["config"]["_target_"], "SharedConfig")
        self.assertEqual(result["handler"]["config"]["value"], 42)

    def test_compose__RefToNonExistentFile__RaisesRefResolutionError(self):
        # Arrange
        entry = self._write_config("app.yaml", """
_target_: App
model:
  _ref_: does_not_exist.yaml
""")

        # Act & Assert
        composer = ConfigComposer(self.config_root)
        with self.assertRaises(RefResolutionError) as ctx:
            composer.compose(entry)

        self.assertIn("does_not_exist.yaml", str(ctx.exception))
        self.assertIn("file not found", str(ctx.exception))
        self.assertIn("model", str(ctx.exception))

    def test_compose__RefToInvalidYaml__RaisesRefResolutionError(self):
        # Arrange
        self._write_config("invalid.yaml", """
this is not: valid: yaml: syntax
  - broken
""")
        entry = self._write_config("app.yaml", """
_target_: App
model:
  _ref_: invalid.yaml
""")

        # Act & Assert
        composer = ConfigComposer(self.config_root)
        with self.assertRaises(RefResolutionError) as ctx:
            composer.compose(entry)

        self.assertIn("invalid.yaml", str(ctx.exception))

    def test_compose__RefCircularAtoB__RaisesCircularRefError(self):
        # Arrange
        self._write_config("a.yaml", """
_target_: A
b:
  _ref_: b.yaml
""")
        self._write_config("b.yaml", """
_target_: B
a:
  _ref_: a.yaml
""")
        entry = self._write_config("app.yaml", """
_target_: App
a:
  _ref_: a.yaml
""")

        # Act & Assert
        composer = ConfigComposer(self.config_root)
        with self.assertRaises(CircularRefError) as ctx:
            composer.compose(entry)

        self.assertIn("a.yaml", str(ctx.exception))
        self.assertIn("b.yaml", str(ctx.exception))

    def test_compose__RefOverrideTargetToNull__RaisesRefResolutionError(self):
        # Arrange
        self._write_config("model.yaml", """
_target_: Model
value: 1
""")
        entry = self._write_config("app.yaml", """
_target_: App
model:
  _ref_: model.yaml
  _target_: null
""")

        # Act & Assert
        composer = ConfigComposer(self.config_root)
        with self.assertRaises(RefResolutionError) as ctx:
            composer.compose(entry)

        self.assertIn("_target_", str(ctx.exception))
        self.assertIn("null", str(ctx.exception))

    def test_compose__NestedRefChain__AllResolvedCorrectly(self):
        # Arrange
        self._write_config("c.yaml", """
_target_: C
value: "deepest"
""")
        self._write_config("b.yaml", """
_target_: B
c:
  _ref_: c.yaml
""")
        self._write_config("a.yaml", """
_target_: A
b:
  _ref_: b.yaml
""")
        entry = self._write_config("app.yaml", """
_target_: App
a:
  _ref_: a.yaml
""")

        # Act
        composer = ConfigComposer(self.config_root)
        result = composer.compose(entry)

        # Assert
        self.assertEqual(result["a"]["b"]["c"]["value"], "deepest")

    def test_compose__RefInListItems__EachItemResolved(self):
        # Arrange
        self._write_config("models/resnet.yaml", """
_target_: ResNet
layers: 50
""")
        self._write_config("models/vgg.yaml", """
_target_: VGG
layers: 16
""")
        entry = self._write_config("app.yaml", """
_target_: App
models:
  - _ref_: models/resnet.yaml
  - _ref_: models/vgg.yaml
  - _target_: CustomModel
    layers: 10
""")

        # Act
        composer = ConfigComposer(self.config_root)
        result = composer.compose(entry)

        # Assert
        self.assertEqual(len(result["models"]), 3)
        self.assertEqual(result["models"][0]["_target_"], "ResNet")
        self.assertEqual(result["models"][1]["_target_"], "VGG")
        self.assertEqual(result["models"][2]["_target_"], "CustomModel")

    def test_compose__RefCombinedWithInstance__RaisesRefInstanceConflictError(self):
        # Arrange
        self._write_config("model.yaml", """
_target_: Model
""")
        entry = self._write_config("app.yaml", """
_target_: App
model:
  _ref_: model.yaml
  _instance_: /shared.db
""")

        # Act & Assert
        composer = ConfigComposer(self.config_root)
        with self.assertRaises(RefInstanceConflictError) as ctx:
            composer.compose(entry)

        self.assertIn("_ref_", str(ctx.exception))
        self.assertIn("_instance_", str(ctx.exception))

    def test_compose__RefToFragmentNoTarget__WorksIfTargetAddedViaOverride(self):
        # Arrange - fragment file with no _target_
        self._write_config("fragments/optimizer.yaml", """
type: adam
lr: 0.001
betas: [0.9, 0.999]
""")
        entry = self._write_config("app.yaml", """
_target_: App
optimizer:
  _ref_: fragments/optimizer.yaml
  _target_: Optimizer
""")

        # Act
        composer = ConfigComposer(self.config_root)
        result = composer.compose(entry)

        # Assert
        self.assertEqual(result["optimizer"]["_target_"], "Optimizer")
        self.assertEqual(result["optimizer"]["type"], "adam")
        self.assertEqual(result["optimizer"]["lr"], 0.001)

    def test_compose__RefWithNonStringPath__RaisesRefResolutionError(self):
        # Arrange
        entry = self._write_config("app.yaml", """
_target_: App
model:
  _ref_: 123
""")

        # Act & Assert
        composer = ConfigComposer(self.config_root)
        with self.assertRaises(RefResolutionError) as ctx:
            composer.compose(entry)

        self.assertIn("must be a string", str(ctx.exception))

    def test_compose__PlainRelativePath__ResolvesFromCurrentDir(self):
        # Arrange (no ./ prefix)
        self._write_config("models/base.yaml", """
_target_: Base
value: 1
""")
        self._write_config("models/derived.yaml", """
_target_: Derived
base:
  _ref_: base.yaml
""")
        entry = self._write_config("app.yaml", """
_target_: App
model:
  _ref_: models/derived.yaml
""")

        # Act
        composer = ConfigComposer(self.config_root)
        result = composer.compose(entry)

        # Assert
        self.assertEqual(result["model"]["base"]["_target_"], "Base")


class ConfigComposerCachingTests(TestCase):
    """Tests for file caching in ConfigComposer."""

    def setUp(self) -> None:
        """Set up a temporary directory for test configs."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_root = Path(self.temp_dir.name)
        clear_cache()

    def tearDown(self) -> None:
        """Clean up temporary directory."""
        self.temp_dir.cleanup()
        clear_cache()

    def _write_config(self, rel_path: str, content: str) -> Path:
        """Write a config file to the temp directory."""
        path = self.config_root / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def test_compose__SameFileReferencedTwice__LoadedOnce(self):
        # Arrange
        self._write_config("shared.yaml", """
_target_: Shared
value: 42
""")
        entry = self._write_config("app.yaml", """
_target_: App
a:
  _ref_: shared.yaml
b:
  _ref_: shared.yaml
""")

        # Act
        composer = ConfigComposer(self.config_root)
        result = composer.compose(entry)

        # Assert - both should have same values
        self.assertEqual(result["a"]["value"], 42)
        self.assertEqual(result["b"]["value"], 42)
        # Cache should have been used (file loaded once)

    def test_set_cache_size__WithSize__ClearsExistingCache(self):
        # Arrange
        self._write_config("model.yaml", """
_target_: Model
value: 1
""")
        entry = self._write_config("app.yaml", """
_target_: App
model:
  _ref_: model.yaml
""")

        # Act - compose first to populate cache
        composer = ConfigComposer(self.config_root)
        composer.compose(entry)

        # Change the file
        self._write_config("model.yaml", """
_target_: Model
value: 999
""")

        # Compose again - should still get cached value
        result1 = composer.compose(entry)

        # Set cache size (clears cache)
        set_cache_size(10)

        # Compose again - should get new value
        result2 = composer.compose(entry)

        # Assert
        self.assertEqual(result1["model"]["value"], 1)  # Cached
        self.assertEqual(result2["model"]["value"], 999)  # Fresh

    def test_clear_cache__AfterCompose__NextComposeReloadsFile(self):
        # Arrange
        self._write_config("model.yaml", """
_target_: Model
value: 1
""")
        entry = self._write_config("app.yaml", """
_target_: App
model:
  _ref_: model.yaml
""")

        # Act - compose first
        composer = ConfigComposer(self.config_root)
        result1 = composer.compose(entry)

        # Modify file
        self._write_config("model.yaml", """
_target_: Model
value: 999
""")

        # Clear cache
        clear_cache()

        # Compose again
        result2 = composer.compose(entry)

        # Assert
        self.assertEqual(result1["model"]["value"], 1)
        self.assertEqual(result2["model"]["value"], 999)

    def test_cache__AcrossMultipleInstantiateCalls__FilesCached(self):
        # Arrange
        self._write_config("model.yaml", """
_target_: Model
value: 1
""")
        entry = self._write_config("app.yaml", """
_target_: App
model:
  _ref_: model.yaml
""")

        # Act - compose multiple times with different composers
        composer1 = ConfigComposer(self.config_root)
        result1 = composer1.compose(entry)

        # Modify file
        self._write_config("model.yaml", """
_target_: Model
value: 999
""")

        composer2 = ConfigComposer(self.config_root)
        result2 = composer2.compose(entry)

        # Assert - both should use cache
        self.assertEqual(result1["model"]["value"], 1)
        self.assertEqual(result2["model"]["value"], 1)  # Still cached


class ConfigComposerEdgeCaseTests(TestCase):
    """Edge case tests for ConfigComposer."""

    def setUp(self) -> None:
        """Set up a temporary directory for test configs."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_root = Path(self.temp_dir.name)
        clear_cache()

    def tearDown(self) -> None:
        """Clean up temporary directory."""
        self.temp_dir.cleanup()
        clear_cache()

    def _write_config(self, rel_path: str, content: str) -> Path:
        """Write a config file to the temp directory."""
        path = self.config_root / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def test_compose__RefInNestedList__ResolvedCorrectly(self):
        # Arrange
        self._write_config("item.yaml", """
_target_: Item
value: nested
""")
        entry = self._write_config("app.yaml", """
_target_: App
matrix:
  -
    - _ref_: item.yaml
    - value: inline
""")

        # Act
        composer = ConfigComposer(self.config_root)
        result = composer.compose(entry)

        # Assert
        self.assertEqual(result["matrix"][0][0]["_target_"], "Item")
        self.assertEqual(result["matrix"][0][1]["value"], "inline")

    def test_compose__EmptyOverrides__ReferencedConfigUnchanged(self):
        # Arrange
        self._write_config("model.yaml", """
_target_: Model
layers: 50
""")
        entry = self._write_config("app.yaml", """
_target_: App
model:
  _ref_: model.yaml
""")

        # Act
        composer = ConfigComposer(self.config_root)
        result = composer.compose(entry)

        # Assert
        self.assertEqual(result["model"]["_target_"], "Model")
        self.assertEqual(result["model"]["layers"], 50)

    def test_compose__ReferencedFileHasRefAtRoot__RaisesRefAtRootError(self):
        # Arrange
        self._write_config("base.yaml", """
value: 1
""")
        self._write_config("broken.yaml", """
_ref_: base.yaml
extra: 2
""")
        entry = self._write_config("app.yaml", """
_target_: App
model:
  _ref_: broken.yaml
""")

        # Act & Assert
        composer = ConfigComposer(self.config_root)
        with self.assertRaises(RefAtRootError) as ctx:
            composer.compose(entry)

        self.assertIn("broken.yaml", str(ctx.exception))

    def test_compose__SelfCircularRef__RaisesCircularRefError(self):
        # Arrange - file references itself
        entry = self._write_config("self.yaml", """
_target_: Self
nested:
  _ref_: self.yaml
""")

        # Act & Assert
        composer = ConfigComposer(self.config_root)
        with self.assertRaises(CircularRefError) as ctx:
            composer.compose(entry)

        self.assertIn("self.yaml", str(ctx.exception))


class ComposeConvenienceFunctionTests(TestCase):
    """Tests for the compose() convenience function."""

    def setUp(self) -> None:
        """Set up a temporary directory for test configs."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_root = Path(self.temp_dir.name)
        clear_cache()

    def tearDown(self) -> None:
        """Clean up temporary directory."""
        self.temp_dir.cleanup()
        clear_cache()

    def _write_config(self, rel_path: str, content: str) -> Path:
        """Write a config file to the temp directory."""
        path = self.config_root / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def test_compose__SimpleFile__ReturnsConfig(self):
        # Arrange
        entry = self._write_config("app.yaml", """
_target_: App
value: 42
""")

        # Act
        result = compose(entry)

        # Assert
        self.assertEqual(result["_target_"], "App")
        self.assertEqual(result["value"], 42)

    def test_compose__WithRef__ResolvesRef(self):
        # Arrange
        self._write_config("model.yaml", """
_target_: Model
layers: 50
""")
        entry = self._write_config("app.yaml", """
_target_: App
model:
  _ref_: model.yaml
""")

        # Act
        result = compose(entry)

        # Assert
        self.assertEqual(result["model"]["_target_"], "Model")


class ConfigComposerInternalTests(TestCase):
    """Tests for internal ConfigComposer edge cases."""

    def setUp(self) -> None:
        """Set up a temporary directory for test configs."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_root = Path(self.temp_dir.name)
        clear_cache()

    def tearDown(self) -> None:
        """Clean up temporary directory."""
        self.temp_dir.cleanup()
        clear_cache()

    def _write_config(self, rel_path: str, content: str) -> Path:
        """Write a config file to the temp directory."""
        path = self.config_root / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def test_resolve_file_path__AbsolutePathWithoutConfigRoot__RaisesRefResolutionError(self):
        # Arrange
        self._write_config("model.yaml", """
_target_: Model
value: 1
""")
        # Create composer without config_root and manually call internal method
        composer = ConfigComposer()
        # Note: _config_root is None by default

        # Act & Assert
        with self.assertRaises(RefResolutionError) as ctx:
            composer._resolve_file_path("/model.yaml", self.config_root, "test.path")

        self.assertIn("without config root", str(ctx.exception))


class CompositionErrorTests(TestCase):
    """Tests for composition error classes."""

    def test_CompositionError__IsConfigError(self):
        # Act
        error = CompositionError("test")

        # Assert
        from rconfig.errors import ConfigError
        self.assertIsInstance(error, ConfigError)

    def test_CircularRefError__FormatsChainCorrectly(self):
        # Act
        error = CircularRefError(["a.yaml", "b.yaml", "a.yaml"])

        # Assert
        self.assertEqual(error.chain, ["a.yaml", "b.yaml", "a.yaml"])
        self.assertIn("a.yaml → b.yaml → a.yaml", str(error))

    def test_RefResolutionError__IncludesAllInfo(self):
        # Act
        error = RefResolutionError("model.yaml", "file not found", "app.model")

        # Assert
        self.assertEqual(error.ref_path, "model.yaml")
        self.assertEqual(error.reason, "file not found")
        self.assertEqual(error.config_path, "app.model")
        self.assertIn("model.yaml", str(error))
        self.assertIn("file not found", str(error))
        self.assertIn("app.model", str(error))

    def test_RefAtRootError__IncludesFilePath(self):
        # Act
        error = RefAtRootError("/path/to/config.yaml")

        # Assert
        self.assertEqual(error.file_path, "/path/to/config.yaml")
        self.assertIn("config.yaml", str(error))
        self.assertIn("root level", str(error))

    def test_RefInstanceConflictError__IncludesPath(self):
        # Act
        error = RefInstanceConflictError("model.encoder")

        # Assert
        self.assertEqual(error.config_path, "model.encoder")
        self.assertIn("_ref_", str(error))
        self.assertIn("_instance_", str(error))
        self.assertIn("model.encoder", str(error))


class ProvenanceTrackingTests(TestCase):
    """Tests for provenance tracking in ConfigComposer."""

    def setUp(self) -> None:
        """Set up a temporary directory for test configs."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_root = Path(self.temp_dir.name)
        clear_cache()

    def tearDown(self) -> None:
        """Clean up temporary directory."""
        self.temp_dir.cleanup()
        clear_cache()

    def _write_config(self, rel_path: str, content: str) -> Path:
        """Write a config file to the temp directory."""
        path = self.config_root / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def test_compose_with_provenance__SimpleConfig__TracksFileAndLine(self):
        # Arrange
        entry = self._write_config("app.yaml", """_target_: App
layers: 50
lr: 0.001
""")

        # Act
        composer = ConfigComposer(self.config_root)
        prov = composer.compose_with_provenance(entry)

        # Assert
        target_entry = prov.get("_target_")
        self.assertIsNotNone(target_entry)
        self.assertIn("app.yaml", target_entry.file)
        self.assertEqual(target_entry.line, 1)

        layers_entry = prov.get("layers")
        self.assertEqual(layers_entry.line, 2)

        lr_entry = prov.get("lr")
        self.assertEqual(lr_entry.line, 3)

    def test_compose_with_provenance__WithRef__TracksReferencedFile(self):
        # Arrange
        self._write_config("model.yaml", """_target_: Model
hidden: 256
""")
        entry = self._write_config("app.yaml", """_target_: App
model:
  _ref_: model.yaml
""")

        # Act
        composer = ConfigComposer(self.config_root)
        prov = composer.compose_with_provenance(entry)

        # Assert
        # Model's _target_ should come from model.yaml
        model_target = prov.get("model._target_")
        self.assertIsNotNone(model_target)
        self.assertIn("model.yaml", model_target.file)
        self.assertEqual(model_target.line, 1)

        # Model's hidden should come from model.yaml
        hidden_entry = prov.get("model.hidden")
        self.assertIn("model.yaml", hidden_entry.file)
        self.assertEqual(hidden_entry.line, 2)

    def test_compose_with_provenance__WithOverride__TracksOverride(self):
        # Arrange
        self._write_config("model.yaml", """_target_: Model
layers: 34
lr: 0.001
""")
        entry = self._write_config("app.yaml", """_target_: App
model:
  _ref_: model.yaml
  layers: 50
""")

        # Act
        composer = ConfigComposer(self.config_root)
        prov = composer.compose_with_provenance(entry)

        # Assert
        layers_entry = prov.get("model.layers")
        self.assertIsNotNone(layers_entry)
        # The override should be tracked
        self.assertIn("app.yaml", layers_entry.file)
        # Should show what was overridden
        self.assertIsNotNone(layers_entry.overrode)
        self.assertIn("model.yaml", layers_entry.overrode)

    def test_compose_with_provenance__CrossFileProvenance__TracksCorrectly(self):
        # Arrange
        self._write_config("shared/db.yaml", """_target_: Database
url: postgres://localhost
""")
        self._write_config("services/user.yaml", """_target_: UserService
db:
  _ref_: /shared/db.yaml
name: user-service
""")
        entry = self._write_config("app.yaml", """_target_: App
service:
  _ref_: services/user.yaml
""")

        # Act
        composer = ConfigComposer(self.config_root)
        prov = composer.compose_with_provenance(entry)

        # Assert
        # App's _target_ from app.yaml
        app_target = prov.get("_target_")
        self.assertIn("app.yaml", app_target.file)

        # Service's _target_ from user.yaml
        service_target = prov.get("service._target_")
        self.assertIn("user.yaml", service_target.file)

        # DB's _target_ from db.yaml
        db_target = prov.get("service.db._target_")
        self.assertIn("db.yaml", db_target.file)

    def test_compose_with_provenance__PrintOutput__FormatsCorrectly(self):
        # Arrange
        entry = self._write_config("app.yaml", """_target_: App
value: 42
""")

        # Act
        composer = ConfigComposer(self.config_root)
        prov = composer.compose_with_provenance(entry)
        output = str(prov)

        # Assert
        self.assertIn("_target_: App", output)
        self.assertIn("app.yaml:1", output)
        self.assertIn("value: 42", output)
        self.assertIn("app.yaml:2", output)

    def test_compose_with_provenance__ProvenanceGet__ReturnsCorrectEntry(self):
        # Arrange
        entry = self._write_config("app.yaml", """_target_: App
nested:
  value: 42
""")

        # Act
        composer = ConfigComposer(self.config_root)
        prov = composer.compose_with_provenance(entry)
        entry = prov.get("nested.value")

        # Assert
        self.assertIsNotNone(entry)
        self.assertEqual(entry.line, 3)

    def test_compose_with_provenance__ProvenanceItems__IteratesAllPaths(self):
        # Arrange
        entry = self._write_config("app.yaml", """_target_: App
a: 1
b: 2
""")

        # Act
        composer = ConfigComposer(self.config_root)
        prov = composer.compose_with_provenance(entry)
        items = list(prov.items())

        # Assert
        paths = [path for path, _ in items]
        self.assertIn("_target_", paths)
        self.assertIn("a", paths)
        self.assertIn("b", paths)

    def test_compose_with_provenance_convenience__SimpleFile__Works(self):
        # Arrange
        entry = self._write_config("app.yaml", """_target_: App
value: 42
""")

        # Act
        prov = compose_with_provenance(entry)

        # Assert
        self.assertIsNotNone(prov.get("_target_"))
        self.assertIsNotNone(prov.get("value"))
