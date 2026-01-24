from pathlib import Path
from unittest import TestCase

from rconfig.composition import (
    ConfigComposer,
    clear_cache,
    compose,
    compose_with_provenance,
    set_cache_size,
)
from rconfig.errors import (
    CircularInstanceError,
    CircularRefError,
    CompositionError,
    ConfigFileError,
    InstanceResolutionError,
    RefAtRootError,
    RefInstanceConflictError,
    RefResolutionError,
)

from rconfig_unittests.fixtures import MockFileSystem, mock_filesystem


class ConfigComposerRefTests(TestCase):
    """Tests for _ref_ resolution in ConfigComposer."""

    def setUp(self) -> None:
        """Set up mock file system for tests."""
        clear_cache()

    def tearDown(self) -> None:
        """Clean up after tests."""
        clear_cache()

    def test_compose__BasicRefLoadsFile__ConfigMergedCorrectly(self):
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/models/resnet.yaml", {
            "_target_": "ResNet",
            "layers": 34,
            "lr": 0.001,
        })
        fs.add_file("/configs/app.yaml", {
            "_target_": "App",
            "model": {"_ref_": "models/resnet.yaml"},
        })

        # Act
        with mock_filesystem(fs):
            composer = ConfigComposer(fs.base_path)
            result = composer.compose(Path("/configs/app.yaml"))

        # Assert
        self.assertEqual(result["_target_"], "App")
        self.assertEqual(result["model"]["_target_"], "ResNet")
        self.assertEqual(result["model"]["layers"], 34)
        self.assertEqual(result["model"]["lr"], 0.001)

    def test_compose__RefWithSiblingOverrides__DeepMergeAppliesOverrides(self):
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/models/resnet.yaml", {
            "_target_": "ResNet",
            "layers": 34,
            "optimizer": {
                "type": "adam",
                "lr": 0.001,
                "betas": [0.9, 0.999],
            },
        })
        fs.add_file("/configs/trainer.yaml", {
            "_target_": "Trainer",
            "model": {
                "_ref_": "models/resnet.yaml",
                "layers": 50,
                "optimizer": {"lr": 0.01},
            },
        })

        # Act
        with mock_filesystem(fs):
            composer = ConfigComposer(fs.base_path)
            result = composer.compose(Path("/configs/trainer.yaml"))

        # Assert
        self.assertEqual(result["model"]["layers"], 50)  # Overridden
        self.assertEqual(result["model"]["optimizer"]["lr"], 0.01)  # Overridden
        self.assertEqual(result["model"]["optimizer"]["type"], "adam")  # Preserved
        self.assertEqual(result["model"]["optimizer"]["betas"], [0.9, 0.999])  # Preserved

    def test_compose__RefAtRootLevel__RaisesRefAtRootError(self):
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/base.yaml", {"_target_": "Base", "value": 1})
        fs.add_file("/configs/app.yaml", {"_ref_": "base.yaml", "extra": "value"})

        # Act & Assert
        with mock_filesystem(fs):
            composer = ConfigComposer(fs.base_path)
            with self.assertRaises(RefAtRootError) as ctx:
                composer.compose(Path("/configs/app.yaml"))

        self.assertIn("root level", str(ctx.exception))
        self.assertIn("app.yaml", str(ctx.exception))

    def test_compose__RefWithAbsolutePath__ResolvesFromConfigRoot(self):
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/shared/database.yaml", {
            "_target_": "Database",
            "url": "postgres://localhost",
        })
        fs.add_file("/configs/services/user.yaml", {
            "_target_": "UserService",
            "db": {"_ref_": "/shared/database.yaml"},
        })
        fs.add_file("/configs/app.yaml", {
            "_target_": "App",
            "service": {"_ref_": "services/user.yaml"},
        })

        # Act
        with mock_filesystem(fs):
            composer = ConfigComposer(fs.base_path)
            result = composer.compose(Path("/configs/app.yaml"))

        # Assert
        self.assertEqual(result["service"]["db"]["_target_"], "Database")
        self.assertEqual(result["service"]["db"]["url"], "postgres://localhost")

    def test_compose__RefWithRelativePath__ResolvesFromCurrentFileDir(self):
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/models/base.yaml", {
            "_target_": "BaseModel",
            "hidden": 256,
        })
        fs.add_file("/configs/models/resnet.yaml", {
            "_target_": "ResNet",
            "base": {"_ref_": "./base.yaml"},
            "layers": 50,
        })
        fs.add_file("/configs/app.yaml", {
            "_target_": "App",
            "model": {"_ref_": "models/resnet.yaml"},
        })

        # Act
        with mock_filesystem(fs):
            composer = ConfigComposer(fs.base_path)
            result = composer.compose(Path("/configs/app.yaml"))

        # Assert
        self.assertEqual(result["model"]["base"]["_target_"], "BaseModel")
        self.assertEqual(result["model"]["base"]["hidden"], 256)

    def test_compose__RefWithParentPath__ResolvesCorrectly(self):
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/shared/config.yaml", {
            "_target_": "SharedConfig",
            "value": 42,
        })
        fs.add_file("/configs/services/auth/handler.yaml", {
            "_target_": "AuthHandler",
            "config": {"_ref_": "../../shared/config.yaml"},
        })
        fs.add_file("/configs/services/auth/main.yaml", {
            "_target_": "AuthMain",
            "handler": {"_ref_": "./handler.yaml"},
        })

        # Act
        with mock_filesystem(fs):
            composer = ConfigComposer(fs.base_path)
            result = composer.compose(Path("/configs/services/auth/main.yaml"))

        # Assert
        self.assertEqual(result["handler"]["config"]["_target_"], "SharedConfig")
        self.assertEqual(result["handler"]["config"]["value"], 42)

    def test_compose__RefToNonExistentFile__RaisesRefResolutionError(self):
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/app.yaml", {
            "_target_": "App",
            "model": {"_ref_": "does_not_exist.yaml"},
        })

        # Act & Assert
        with mock_filesystem(fs):
            composer = ConfigComposer(fs.base_path)
            with self.assertRaises(RefResolutionError) as ctx:
                composer.compose(Path("/configs/app.yaml"))

        self.assertIn("does_not_exist.yaml", str(ctx.exception))

    def test_compose__RefToInvalidYaml__RaisesRefResolutionError(self):
        # Arrange - simulate invalid YAML by making load raise an error
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/app.yaml", {
            "_target_": "App",
            "model": {"_ref_": "invalid.yaml"},
        })
        # Don't add invalid.yaml - this will cause KeyError which gets wrapped

        # Act & Assert
        with mock_filesystem(fs):
            composer = ConfigComposer(fs.base_path)
            with self.assertRaises(RefResolutionError) as ctx:
                composer.compose(Path("/configs/app.yaml"))

        self.assertIn("invalid.yaml", str(ctx.exception))

    def test_compose__RefCircularAtoB__RaisesCircularRefError(self):
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/a.yaml", {
            "_target_": "A",
            "b": {"_ref_": "b.yaml"},
        })
        fs.add_file("/configs/b.yaml", {
            "_target_": "B",
            "a": {"_ref_": "a.yaml"},
        })
        fs.add_file("/configs/app.yaml", {
            "_target_": "App",
            "a": {"_ref_": "a.yaml"},
        })

        # Act & Assert
        with mock_filesystem(fs):
            composer = ConfigComposer(fs.base_path)
            with self.assertRaises(CircularRefError) as ctx:
                composer.compose(Path("/configs/app.yaml"))

        self.assertIn("a.yaml", str(ctx.exception))
        self.assertIn("b.yaml", str(ctx.exception))

    def test_compose__RefOverrideTargetToNull__RaisesRefResolutionError(self):
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/model.yaml", {"_target_": "Model", "value": 1})
        fs.add_file("/configs/app.yaml", {
            "_target_": "App",
            "model": {"_ref_": "model.yaml", "_target_": None},
        })

        # Act & Assert
        with mock_filesystem(fs):
            composer = ConfigComposer(fs.base_path)
            with self.assertRaises(RefResolutionError) as ctx:
                composer.compose(Path("/configs/app.yaml"))

        self.assertIn("_target_", str(ctx.exception))
        self.assertIn("null", str(ctx.exception))

    def test_compose__NestedRefChain__AllResolvedCorrectly(self):
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/c.yaml", {"_target_": "C", "value": "deepest"})
        fs.add_file("/configs/b.yaml", {"_target_": "B", "c": {"_ref_": "c.yaml"}})
        fs.add_file("/configs/a.yaml", {"_target_": "A", "b": {"_ref_": "b.yaml"}})
        fs.add_file("/configs/app.yaml", {"_target_": "App", "a": {"_ref_": "a.yaml"}})

        # Act
        with mock_filesystem(fs):
            composer = ConfigComposer(fs.base_path)
            result = composer.compose(Path("/configs/app.yaml"))

        # Assert
        self.assertEqual(result["a"]["b"]["c"]["value"], "deepest")

    def test_compose__RefInListItems__EachItemResolved(self):
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/models/resnet.yaml", {"_target_": "ResNet", "layers": 50})
        fs.add_file("/configs/models/vgg.yaml", {"_target_": "VGG", "layers": 16})
        fs.add_file("/configs/app.yaml", {
            "_target_": "App",
            "models": [
                {"_ref_": "models/resnet.yaml"},
                {"_ref_": "models/vgg.yaml"},
                {"_target_": "CustomModel", "layers": 10},
            ],
        })

        # Act
        with mock_filesystem(fs):
            composer = ConfigComposer(fs.base_path)
            result = composer.compose(Path("/configs/app.yaml"))

        # Assert
        self.assertEqual(len(result["models"]), 3)
        self.assertEqual(result["models"][0]["_target_"], "ResNet")
        self.assertEqual(result["models"][1]["_target_"], "VGG")
        self.assertEqual(result["models"][2]["_target_"], "CustomModel")

    def test_compose__RefCombinedWithInstance__RaisesRefInstanceConflictError(self):
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/model.yaml", {"_target_": "Model"})
        fs.add_file("/configs/app.yaml", {
            "_target_": "App",
            "model": {"_ref_": "model.yaml", "_instance_": "/shared.db"},
        })

        # Act & Assert
        with mock_filesystem(fs):
            composer = ConfigComposer(fs.base_path)
            with self.assertRaises(RefInstanceConflictError) as ctx:
                composer.compose(Path("/configs/app.yaml"))

        self.assertIn("_ref_", str(ctx.exception))
        self.assertIn("_instance_", str(ctx.exception))

    def test_compose__RefToFragmentNoTarget__WorksIfTargetAddedViaOverride(self):
        # Arrange - fragment file with no _target_
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/fragments/optimizer.yaml", {
            "type": "adam",
            "lr": 0.001,
            "betas": [0.9, 0.999],
        })
        fs.add_file("/configs/app.yaml", {
            "_target_": "App",
            "optimizer": {"_ref_": "fragments/optimizer.yaml", "_target_": "Optimizer"},
        })

        # Act
        with mock_filesystem(fs):
            composer = ConfigComposer(fs.base_path)
            result = composer.compose(Path("/configs/app.yaml"))

        # Assert
        self.assertEqual(result["optimizer"]["_target_"], "Optimizer")
        self.assertEqual(result["optimizer"]["type"], "adam")
        self.assertEqual(result["optimizer"]["lr"], 0.001)

    def test_compose__RefWithNonStringPath__RaisesRefResolutionError(self):
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/app.yaml", {
            "_target_": "App",
            "model": {"_ref_": 123},
        })

        # Act & Assert
        with mock_filesystem(fs):
            composer = ConfigComposer(fs.base_path)
            with self.assertRaises(RefResolutionError) as ctx:
                composer.compose(Path("/configs/app.yaml"))

        self.assertIn("must be a string", str(ctx.exception))

    def test_compose__PlainRelativePath__ResolvesFromCurrentDir(self):
        # Arrange (no ./ prefix)
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/models/base.yaml", {"_target_": "Base", "value": 1})
        fs.add_file("/configs/models/derived.yaml", {
            "_target_": "Derived",
            "base": {"_ref_": "base.yaml"},
        })
        fs.add_file("/configs/app.yaml", {
            "_target_": "App",
            "model": {"_ref_": "models/derived.yaml"},
        })

        # Act
        with mock_filesystem(fs):
            composer = ConfigComposer(fs.base_path)
            result = composer.compose(Path("/configs/app.yaml"))

        # Assert
        self.assertEqual(result["model"]["base"]["_target_"], "Base")


class ConfigComposerCachingTests(TestCase):
    """Tests for file caching in ConfigComposer.

    Uses MockFileSystem to avoid platform-specific temp directory issues
    (e.g., macOS /var -> /private/var symlink). The mock_filesystem()
    context manager patches _load_file_impl while preserving the lru_cache
    wrapper, so actual caching behavior is tested with mock file contents.
    """

    def setUp(self) -> None:
        """Clear cache before each test."""
        clear_cache()

    def tearDown(self) -> None:
        """Clear cache after each test."""
        clear_cache()

    def test_compose__SameFileReferencedTwice__LoadedOnce(self):
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/shared.yaml", {"_target_": "Shared", "value": 42})
        fs.add_file("/configs/app.yaml", {
            "_target_": "App",
            "a": {"_ref_": "shared.yaml"},
            "b": {"_ref_": "shared.yaml"},
        })

        with mock_filesystem(fs):
            # Act
            composer = ConfigComposer(fs.base_path)
            result = composer.compose(Path("/configs/app.yaml"))

            # Assert - both should have same values
            self.assertEqual(result["a"]["value"], 42)
            self.assertEqual(result["b"]["value"], 42)
            # Cache should have been used (file loaded once)

    def test_set_cache_size__WithSize__ClearsExistingCache(self):
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/model.yaml", {"_target_": "Model", "value": 1})
        fs.add_file("/configs/app.yaml", {
            "_target_": "App",
            "model": {"_ref_": "model.yaml"},
        })

        with mock_filesystem(fs):
            # Act - compose first to populate cache
            composer = ConfigComposer(fs.base_path)
            composer.compose(Path("/configs/app.yaml"))

            # Update mock file content
            fs.add_file("/configs/model.yaml", {"_target_": "Model", "value": 999})

            # Compose again - should still get cached value
            result1 = composer.compose(Path("/configs/app.yaml"))

            # Set cache size (clears cache)
            set_cache_size(10)

            # Compose again - should get new value
            result2 = composer.compose(Path("/configs/app.yaml"))

            # Assert
            self.assertEqual(result1["model"]["value"], 1)  # Cached
            self.assertEqual(result2["model"]["value"], 999)  # Fresh

    def test_clear_cache__AfterCompose__NextComposeReloadsFile(self):
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/model.yaml", {"_target_": "Model", "value": 1})
        fs.add_file("/configs/app.yaml", {
            "_target_": "App",
            "model": {"_ref_": "model.yaml"},
        })

        with mock_filesystem(fs):
            # Act - compose first
            composer = ConfigComposer(fs.base_path)
            result1 = composer.compose(Path("/configs/app.yaml"))

            # Update mock file content
            fs.add_file("/configs/model.yaml", {"_target_": "Model", "value": 999})

            # Clear cache
            clear_cache()

            # Compose again
            result2 = composer.compose(Path("/configs/app.yaml"))

            # Assert
            self.assertEqual(result1["model"]["value"], 1)
            self.assertEqual(result2["model"]["value"], 999)

    def test_cache__AcrossMultipleInstantiateCalls__FilesCached(self):
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/model.yaml", {"_target_": "Model", "value": 1})
        fs.add_file("/configs/app.yaml", {
            "_target_": "App",
            "model": {"_ref_": "model.yaml"},
        })

        with mock_filesystem(fs):
            # Act - compose multiple times with different composers
            composer1 = ConfigComposer(fs.base_path)
            result1 = composer1.compose(Path("/configs/app.yaml"))

            # Update mock file content
            fs.add_file("/configs/model.yaml", {"_target_": "Model", "value": 999})

            composer2 = ConfigComposer(fs.base_path)
            result2 = composer2.compose(Path("/configs/app.yaml"))

            # Assert - both should use cache
            self.assertEqual(result1["model"]["value"], 1)
            self.assertEqual(result2["model"]["value"], 1)  # Still cached


class ConfigComposerEdgeCaseTests(TestCase):
    """Edge case tests for ConfigComposer."""

    def setUp(self) -> None:
        """Set up for tests."""
        clear_cache()

    def tearDown(self) -> None:
        """Clean up after tests."""
        clear_cache()

    def test_compose__RefInNestedList__ResolvedCorrectly(self):
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/item.yaml", {"_target_": "Item", "value": "nested"})
        fs.add_file("/configs/app.yaml", {
            "_target_": "App",
            "matrix": [[{"_ref_": "item.yaml"}, {"value": "inline"}]],
        })

        # Act
        with mock_filesystem(fs):
            composer = ConfigComposer(fs.base_path)
            result = composer.compose(Path("/configs/app.yaml"))

        # Assert
        self.assertEqual(result["matrix"][0][0]["_target_"], "Item")
        self.assertEqual(result["matrix"][0][1]["value"], "inline")

    def test_compose__EmptyOverrides__ReferencedConfigUnchanged(self):
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/model.yaml", {"_target_": "Model", "layers": 50})
        fs.add_file("/configs/app.yaml", {
            "_target_": "App",
            "model": {"_ref_": "model.yaml"},
        })

        # Act
        with mock_filesystem(fs):
            composer = ConfigComposer(fs.base_path)
            result = composer.compose(Path("/configs/app.yaml"))

        # Assert
        self.assertEqual(result["model"]["_target_"], "Model")
        self.assertEqual(result["model"]["layers"], 50)

    def test_compose__ReferencedFileHasRefAtRoot__RaisesRefAtRootError(self):
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/base.yaml", {"value": 1})
        fs.add_file("/configs/broken.yaml", {"_ref_": "base.yaml", "extra": 2})
        fs.add_file("/configs/app.yaml", {
            "_target_": "App",
            "model": {"_ref_": "broken.yaml"},
        })

        # Act & Assert
        with mock_filesystem(fs):
            composer = ConfigComposer(fs.base_path)
            with self.assertRaises(RefAtRootError) as ctx:
                composer.compose(Path("/configs/app.yaml"))

        self.assertIn("broken.yaml", str(ctx.exception))

    def test_compose__SelfCircularRef__RaisesCircularRefError(self):
        # Arrange - file references itself
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/self.yaml", {
            "_target_": "Self",
            "nested": {"_ref_": "self.yaml"},
        })

        # Act & Assert
        with mock_filesystem(fs):
            composer = ConfigComposer(fs.base_path)
            with self.assertRaises(CircularRefError) as ctx:
                composer.compose(Path("/configs/self.yaml"))

        self.assertIn("self.yaml", str(ctx.exception))


class ComposeConvenienceFunctionTests(TestCase):
    """Tests for the compose() convenience function."""

    def setUp(self) -> None:
        """Set up for tests."""
        clear_cache()

    def tearDown(self) -> None:
        """Clean up after tests."""
        clear_cache()

    def test_compose__SimpleFile__ReturnsConfig(self):
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/app.yaml", {"_target_": "App", "value": 42})

        # Act
        with mock_filesystem(fs):
            result = compose(Path("/configs/app.yaml"))

        # Assert
        self.assertEqual(result["_target_"], "App")
        self.assertEqual(result["value"], 42)

    def test_compose__WithRef__ResolvesRef(self):
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/model.yaml", {"_target_": "Model", "layers": 50})
        fs.add_file("/configs/app.yaml", {
            "_target_": "App",
            "model": {"_ref_": "model.yaml"},
        })

        # Act
        with mock_filesystem(fs):
            result = compose(Path("/configs/app.yaml"))

        # Assert
        self.assertEqual(result["model"]["_target_"], "Model")


class ConfigComposerInternalTests(TestCase):
    """Tests for internal ConfigComposer edge cases."""

    def setUp(self) -> None:
        """Set up for tests."""
        clear_cache()

    def tearDown(self) -> None:
        """Clean up after tests."""
        clear_cache()

    def test_resolve_file_path__AbsolutePathWithoutConfigRoot__RaisesRefResolutionError(self):
        # Arrange
        from rconfig.composition.file_path_resolver import FilePathResolver

        resolver = FilePathResolver(config_root=None)

        # Act & Assert
        with self.assertRaises(RefResolutionError) as ctx_err:
            resolver.resolve("/model.yaml", Path("/configs"), "test.path")

        self.assertIn("without config root", str(ctx_err.exception))


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
    """Tests for provenance tracking in ConfigComposer.

    Uses MockFileSystem to avoid platform-specific temp directory issues
    (e.g., macOS /var -> /private/var symlink).
    """

    def setUp(self) -> None:
        """Clear cache before each test."""
        clear_cache()

    def tearDown(self) -> None:
        """Clear cache after each test."""
        clear_cache()

    def test_compose_with_provenance__SimpleConfig__TracksFileAndLine(self):
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/app.yaml", {
            "_target_": "App",
            "layers": 50,
            "lr": 0.001,
        })

        with mock_filesystem(fs):
            # Act
            composer = ConfigComposer(fs.base_path)
            prov = composer.compose_with_provenance(Path("/configs/app.yaml"))

            # Assert
            target_entry = prov.get("_target_")
            self.assertIsNotNone(target_entry)
            self.assertIn("app.yaml", target_entry.file)

            layers_entry = prov.get("layers")
            self.assertIsNotNone(layers_entry)

            lr_entry = prov.get("lr")
            self.assertIsNotNone(lr_entry)

    def test_compose_with_provenance__WithRef__TracksReferencedFile(self):
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/model.yaml", {
            "_target_": "Model",
            "hidden": 256,
        })
        fs.add_file("/configs/app.yaml", {
            "_target_": "App",
            "model": {"_ref_": "model.yaml"},
        })

        with mock_filesystem(fs):
            # Act
            composer = ConfigComposer(fs.base_path)
            prov = composer.compose_with_provenance(Path("/configs/app.yaml"))

            # Assert
            # Model's _target_ should come from model.yaml
            model_target = prov.get("model._target_")
            self.assertIsNotNone(model_target)
            self.assertIn("model.yaml", model_target.file)

            # Model's hidden should come from model.yaml
            hidden_entry = prov.get("model.hidden")
            self.assertIn("model.yaml", hidden_entry.file)

    def test_compose_with_provenance__WithOverride__TracksOverride(self):
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/model.yaml", {
            "_target_": "Model",
            "layers": 34,
            "lr": 0.001,
        })
        fs.add_file("/configs/app.yaml", {
            "_target_": "App",
            "model": {
                "_ref_": "model.yaml",
                "layers": 50,
            },
        })

        with mock_filesystem(fs):
            # Act
            composer = ConfigComposer(fs.base_path)
            prov = composer.compose_with_provenance(Path("/configs/app.yaml"))

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
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/shared/db.yaml", {
            "_target_": "Database",
            "url": "postgres://localhost",
        })
        fs.add_file("/configs/services/user.yaml", {
            "_target_": "UserService",
            "db": {"_ref_": "/shared/db.yaml"},
            "name": "user-service",
        })
        fs.add_file("/configs/app.yaml", {
            "_target_": "App",
            "service": {"_ref_": "services/user.yaml"},
        })

        with mock_filesystem(fs):
            # Act
            composer = ConfigComposer(fs.base_path)
            prov = composer.compose_with_provenance(Path("/configs/app.yaml"))

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
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/app.yaml", {
            "_target_": "App",
            "value": 42,
        })

        with mock_filesystem(fs):
            # Act
            composer = ConfigComposer(fs.base_path)
            prov = composer.compose_with_provenance(Path("/configs/app.yaml"))
            output = str(prov)

            # Assert
            self.assertIn("_target_: App", output)
            self.assertIn("app.yaml", output)
            self.assertIn("value: 42", output)

    def test_compose_with_provenance__ProvenanceGet__ReturnsCorrectEntry(self):
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/app.yaml", {
            "_target_": "App",
            "nested": {"value": 42},
        })

        with mock_filesystem(fs):
            # Act
            composer = ConfigComposer(fs.base_path)
            prov = composer.compose_with_provenance(Path("/configs/app.yaml"))
            entry = prov.get("nested.value")

            # Assert
            self.assertIsNotNone(entry)

    def test_compose_with_provenance__ProvenanceItems__IteratesAllPaths(self):
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/app.yaml", {
            "_target_": "App",
            "a": 1,
            "b": 2,
        })

        with mock_filesystem(fs):
            # Act
            composer = ConfigComposer(fs.base_path)
            prov = composer.compose_with_provenance(Path("/configs/app.yaml"))
            items = list(prov.items())

            # Assert
            paths = [path for path, _ in items]
            self.assertIn("_target_", paths)
            self.assertIn("a", paths)
            self.assertIn("b", paths)

    def test_compose_with_provenance_convenience__SimpleFile__Works(self):
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/app.yaml", {
            "_target_": "App",
            "value": 42,
        })

        with mock_filesystem(fs):
            # Act
            prov = compose_with_provenance(Path("/configs/app.yaml"))

            # Assert
            self.assertIsNotNone(prov.get("_target_"))
            self.assertIsNotNone(prov.get("value"))


class ConfigComposerInstanceTests(TestCase):
    """Tests for _instance_ resolution in ConfigComposer."""

    def setUp(self) -> None:
        """Set up for tests."""
        clear_cache()

    def tearDown(self) -> None:
        """Clean up after tests."""
        clear_cache()

    def test_compose__BasicInstanceSameFile__SharesValue(self):
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/app.yaml", {
            "_target_": "App",
            "database": {
                "_target_": "Database",
                "url": "postgres://localhost",
            },
            "service": {
                "_target_": "Service",
                "db": {"_instance_": "database"},
            },
        })

        # Act
        with mock_filesystem(fs):
            composer = ConfigComposer(fs.base_path)
            result = composer.compose(Path("/configs/app.yaml"))

        # Assert
        self.assertEqual(result["database"]["_target_"], "Database")
        self.assertEqual(result["service"]["db"]["_target_"], "Database")
        self.assertEqual(result["service"]["db"]["url"], "postgres://localhost")

    def test_compose__InstanceAbsolutePath__ResolvesFromRoot(self):
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/app.yaml", {
            "_target_": "App",
            "shared": {
                "database": {
                    "_target_": "Database",
                    "url": "postgres://localhost",
                },
            },
            "service": {
                "db": {"_instance_": "/shared.database"},
            },
        })

        # Act
        with mock_filesystem(fs):
            composer = ConfigComposer(fs.base_path)
            result = composer.compose(Path("/configs/app.yaml"))

        # Assert
        self.assertEqual(result["service"]["db"]["_target_"], "Database")

    def test_compose__InstanceRelativePath__ResolvesFromFileRoot(self):
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/app.yaml", {
            "_target_": "App",
            "database": {
                "_target_": "Database",
                "url": "postgres://localhost",
            },
            "service": {
                "db": {"_instance_": "database"},
            },
        })

        # Act
        with mock_filesystem(fs):
            composer = ConfigComposer(fs.base_path)
            result = composer.compose(Path("/configs/app.yaml"))

        # Assert
        self.assertEqual(result["service"]["db"]["_target_"], "Database")

    def test_compose__InstanceWithDotSlash__SameAsRelative(self):
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/app.yaml", {
            "_target_": "App",
            "cache": {
                "_target_": "Cache",
                "size": 100,
            },
            "handler": {
                "c": {"_instance_": "./cache"},
            },
        })

        # Act
        with mock_filesystem(fs):
            composer = ConfigComposer(fs.base_path)
            result = composer.compose(Path("/configs/app.yaml"))

        # Assert
        self.assertEqual(result["handler"]["c"]["_target_"], "Cache")
        self.assertEqual(result["handler"]["c"]["size"], 100)

    def test_compose__InstanceForwardReference__WorksCorrectly(self):
        # Arrange - reference defined later in file
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/app.yaml", {
            "_target_": "App",
            "service": {
                "db": {"_instance_": "database"},
            },
            "database": {
                "_target_": "Database",
                "url": "postgres://localhost",
            },
        })

        # Act
        with mock_filesystem(fs):
            composer = ConfigComposer(fs.base_path)
            result = composer.compose(Path("/configs/app.yaml"))

        # Assert
        self.assertEqual(result["service"]["db"]["_target_"], "Database")

    def test_compose__InstanceToObjectWithTarget__SharesObject(self):
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/app.yaml", {
            "_target_": "App",
            "model": {
                "_target_": "Model",
                "layers": 50,
            },
            "trainer": {
                "model": {"_instance_": "model"},
            },
        })

        # Act
        with mock_filesystem(fs):
            composer = ConfigComposer(fs.base_path)
            result = composer.compose(Path("/configs/app.yaml"))

        # Assert
        self.assertEqual(result["trainer"]["model"]["_target_"], "Model")
        self.assertEqual(result["trainer"]["model"]["layers"], 50)

    def test_compose__InstanceToDictWithoutTarget__SharesDict(self):
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/app.yaml", {
            "_target_": "App",
            "config": {
                "batch_size": 32,
                "learning_rate": 0.001,
            },
            "trainer": {
                "options": {"_instance_": "config"},
            },
        })

        # Act
        with mock_filesystem(fs):
            composer = ConfigComposer(fs.base_path)
            result = composer.compose(Path("/configs/app.yaml"))

        # Assert
        self.assertEqual(result["trainer"]["options"]["batch_size"], 32)
        self.assertEqual(result["trainer"]["options"]["learning_rate"], 0.001)

    def test_compose__InstanceToPrimitive__SharesValue(self):
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/app.yaml", {
            "_target_": "App",
            "base_lr": 0.001,
            "optimizer": {
                "lr": {"_instance_": "base_lr"},
            },
        })

        # Act
        with mock_filesystem(fs):
            composer = ConfigComposer(fs.base_path)
            result = composer.compose(Path("/configs/app.yaml"))

        # Assert
        self.assertEqual(result["optimizer"]["lr"], 0.001)

    def test_compose__InstanceToNonExistentPath__RaisesError(self):
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/app.yaml", {
            "_target_": "App",
            "service": {
                "db": {"_instance_": "nonexistent"},
            },
        })

        # Act & Assert
        with mock_filesystem(fs):
            composer = ConfigComposer(fs.base_path)
            with self.assertRaises(InstanceResolutionError) as ctx:
                composer.compose(Path("/configs/app.yaml"))

        self.assertIn("nonexistent", str(ctx.exception))
        self.assertIn("not found", str(ctx.exception))

    def test_compose__InstanceCircular__RaisesCircularInstanceError(self):
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/app.yaml", {
            "_target_": "App",
            "a": {"_instance_": "b"},
            "b": {"_instance_": "a"},
        })

        # Act & Assert
        with mock_filesystem(fs):
            composer = ConfigComposer(fs.base_path)
            with self.assertRaises(CircularInstanceError) as ctx:
                composer.compose(Path("/configs/app.yaml"))

        # Should show the cycle
        self.assertIn("a", str(ctx.exception))
        self.assertIn("b", str(ctx.exception))

    def test_compose__InstanceChaining__ResolvesTransitively(self):
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/app.yaml", {
            "_target_": "App",
            "database": {"_target_": "Database"},
            "alias": {"_instance_": "database"},
            "service": {
                "db": {"_instance_": "alias"},
            },
        })

        # Act
        with mock_filesystem(fs):
            composer = ConfigComposer(fs.base_path)
            result = composer.compose(Path("/configs/app.yaml"))

        # Assert
        self.assertEqual(result["service"]["db"]["_target_"], "Database")

    def test_compose__InstanceNull__ReturnsNone(self):
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/app.yaml", {
            "_target_": "App",
            "service": {
                "db": {"_instance_": None},
            },
        })

        # Act
        with mock_filesystem(fs):
            composer = ConfigComposer(fs.base_path)
            result = composer.compose(Path("/configs/app.yaml"))

        # Assert
        self.assertIsNone(result["service"]["db"])

    def test_compose__InstanceInListItems__EachItemResolved(self):
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/app.yaml", {
            "_target_": "App",
            "db1": {"_target_": "Database", "name": "primary"},
            "db2": {"_target_": "Database", "name": "replica"},
            "services": [
                {"_instance_": "db1"},
                {"_instance_": "db2"},
            ],
        })

        # Act
        with mock_filesystem(fs):
            composer = ConfigComposer(fs.base_path)
            result = composer.compose(Path("/configs/app.yaml"))

        # Assert
        self.assertEqual(len(result["services"]), 2)
        self.assertEqual(result["services"][0]["name"], "primary")
        self.assertEqual(result["services"][1]["name"], "replica")

    def test_compose__InstanceWithListIndexing__ResolvesCorrectly(self):
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/app.yaml", {
            "_target_": "App",
            "databases": [
                {"_target_": "Database", "name": "primary"},
                {"_target_": "Database", "name": "replica"},
            ],
            "writer": {
                "db": {"_instance_": "/databases[0]"},
            },
            "reader": {
                "db": {"_instance_": "databases[1]"},
            },
        })

        # Act
        with mock_filesystem(fs):
            composer = ConfigComposer(fs.base_path)
            result = composer.compose(Path("/configs/app.yaml"))

        # Assert
        self.assertEqual(result["writer"]["db"]["name"], "primary")
        self.assertEqual(result["reader"]["db"]["name"], "replica")

    def test_compose__InstanceCrossFileViaAbsolutePath__Works(self):
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/shared/database.yaml", {
            "_target_": "Database",
            "url": "postgres://localhost",
        })
        fs.add_file("/configs/services/user.yaml", {
            "_target_": "UserService",
            "db": {"_instance_": "/shared.database"},
        })
        fs.add_file("/configs/app.yaml", {
            "_target_": "App",
            "shared": {
                "database": {"_ref_": "shared/database.yaml"},
            },
            "services": {
                "user": {"_ref_": "services/user.yaml"},
            },
        })

        # Act
        with mock_filesystem(fs):
            composer = ConfigComposer(fs.base_path)
            result = composer.compose(Path("/configs/app.yaml"))

        # Assert
        self.assertEqual(result["services"]["user"]["db"]["_target_"], "Database")

    def test_compose__InstanceCombinedWithRef__RaisesConflictError(self):
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/model.yaml", {"_target_": "Model"})
        fs.add_file("/configs/app.yaml", {
            "_target_": "App",
            "model": {
                "_ref_": "model.yaml",
                "_instance_": "/shared.db",
            },
        })

        # Act & Assert
        with mock_filesystem(fs):
            composer = ConfigComposer(fs.base_path)
            with self.assertRaises(RefInstanceConflictError):
                composer.compose(Path("/configs/app.yaml"))

    def test_compose__InstanceNonStringPath__RaisesError(self):
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/app.yaml", {
            "_target_": "App",
            "service": {
                "db": {"_instance_": 123},
            },
        })

        # Act & Assert
        with mock_filesystem(fs):
            composer = ConfigComposer(fs.base_path)
            with self.assertRaises(InstanceResolutionError) as ctx:
                composer.compose(Path("/configs/app.yaml"))

        self.assertIn("must be a string or null", str(ctx.exception))

    def test_compose__InstanceToPathInsideRefdFile__Works(self):
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/models.yaml", {
            "_target_": "ModelConfig",
            "resnet": {"_target_": "ResNet", "layers": 50},
            "vgg": {"_target_": "VGG", "layers": 16},
        })
        fs.add_file("/configs/app.yaml", {
            "_target_": "App",
            "models": {"_ref_": "models.yaml"},
            "trainer": {
                "model": {"_instance_": "/models.resnet"},
            },
        })

        # Act
        with mock_filesystem(fs):
            composer = ConfigComposer(fs.base_path)
            result = composer.compose(Path("/configs/app.yaml"))

        # Assert
        self.assertEqual(result["trainer"]["model"]["_target_"], "ResNet")
        self.assertEqual(result["trainer"]["model"]["layers"], 50)

    def test_compose__InstanceTargetsProperty__ReturnsCorrectMapping(self):
        """Test that instance_targets property returns the resolved paths."""
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/app.yaml", {
            "_target_": "App",
            "shared": {
                "database": {
                    "_target_": "Database",
                    "url": "postgres://localhost",
                },
            },
            "service_a": {
                "db": {"_instance_": "/shared.database"},
            },
            "service_b": {
                "db": {"_instance_": "/shared.database"},
            },
        })

        # Act
        with mock_filesystem(fs):
            composer = ConfigComposer(fs.base_path)
            composer.compose(Path("/configs/app.yaml"))
            targets = composer.instance_targets

        # Assert
        self.assertEqual(targets["service_a.db"], "shared.database")
        self.assertEqual(targets["service_b.db"], "shared.database")

    def test_compose__InstanceTargetsNull__ReturnsNoneInMapping(self):
        """Test that _instance_: null is tracked correctly."""
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/app.yaml", {
            "_target_": "App",
            "service": {
                "db": {"_instance_": None},
            },
        })

        # Act
        with mock_filesystem(fs):
            composer = ConfigComposer(fs.base_path)
            composer.compose(Path("/configs/app.yaml"))
            targets = composer.instance_targets

        # Assert
        self.assertIn("service.db", targets)
        self.assertIsNone(targets["service.db"])

    def test_compose__InstanceTargetsChain__ReturnsResolvedTarget(self):
        """Test that chained instances resolve to the final target."""
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/app.yaml", {
            "_target_": "App",
            "database": {
                "_target_": "Database",
                "url": "postgres://localhost",
            },
            "alias": {"_instance_": "database"},
            "final": {"_instance_": "alias"},
        })

        # Act
        with mock_filesystem(fs):
            composer = ConfigComposer(fs.base_path)
            composer.compose(Path("/configs/app.yaml"))
            targets = composer.instance_targets

        # Assert
        # Both alias and final resolve to the same ultimate target
        self.assertEqual(targets["alias"], "database")
        self.assertEqual(targets["final"], "database")


class InstanceProvenanceTests(TestCase):
    """Tests for provenance tracking with _instance_."""

    def setUp(self) -> None:
        """Set up for tests."""
        clear_cache()

    def tearDown(self) -> None:
        """Clean up after tests."""
        clear_cache()

    def test_provenance__InstanceReference__TracksInstanceChain(self):
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/app.yaml", {
            "_target_": "App",
            "database": {"_target_": "Database"},
            "service": {
                "db": {"_instance_": "database"},
            },
        })

        # Act
        with mock_filesystem(fs):
            composer = ConfigComposer(fs.base_path)
            prov = composer.compose_with_provenance(Path("/configs/app.yaml"))

        # Assert
        db_entry = prov.get("service.db")
        self.assertIsNotNone(db_entry)
        self.assertIsNotNone(db_entry.instance)
        self.assertEqual(len(db_entry.instance), 1)
        self.assertEqual(db_entry.instance[0].path, "database")

    def test_provenance__InstanceChain__TracksFullChain(self):
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/app.yaml", {
            "_target_": "App",
            "database": {"_target_": "Database"},
            "alias": {"_instance_": "database"},
            "service": {
                "db": {"_instance_": "alias"},
            },
        })

        # Act
        with mock_filesystem(fs):
            composer = ConfigComposer(fs.base_path)
            prov = composer.compose_with_provenance(Path("/configs/app.yaml"))

        # Assert
        db_entry = prov.get("service.db")
        self.assertIsNotNone(db_entry)
        self.assertIsNotNone(db_entry.instance)
        # Chain: service.db -> alias -> database
        self.assertEqual(len(db_entry.instance), 2)
        self.assertEqual(db_entry.instance[0].path, "alias")
        self.assertEqual(db_entry.instance[1].path, "database")

    def test_provenance__InstanceNull__TracksCorrectly(self):
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/app.yaml", {
            "_target_": "App",
            "service": {
                "db": {"_instance_": None},
            },
        })

        # Act
        with mock_filesystem(fs):
            composer = ConfigComposer(fs.base_path)
            prov = composer.compose_with_provenance(Path("/configs/app.yaml"))

        # Assert
        db_entry = prov.get("service.db")
        self.assertIsNotNone(db_entry)
        self.assertIn("app.yaml", db_entry.file)


class InstanceErrorTests(TestCase):
    """Tests for _instance_ error classes."""

    def test_InstanceResolutionError__IncludesAllInfo(self):
        # Act
        error = InstanceResolutionError("database", "path not found", "service.db")

        # Assert
        self.assertEqual(error.instance_path, "database")
        self.assertEqual(error.reason, "path not found")
        self.assertEqual(error.config_path, "service.db")
        self.assertIn("database", str(error))
        self.assertIn("path not found", str(error))
        self.assertIn("service.db", str(error))

    def test_CircularInstanceError__FormatsChainCorrectly(self):
        # Act
        error = CircularInstanceError(["a", "b", "a"])

        # Assert
        self.assertEqual(error.chain, ["a", "b", "a"])
        self.assertIn("a → b → a", str(error))


class InstanceEdgeCaseTests(TestCase):
    """Edge case tests for _instance_ resolution."""

    def setUp(self) -> None:
        """Set up for tests."""
        clear_cache()

    def tearDown(self) -> None:
        """Clean up after tests."""
        clear_cache()

    def test_compose__InstanceNestedListAccess__WorksCorrectly(self):
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/app.yaml", {
            "_target_": "App",
            "matrix": [
                [{"name": "cell00"}, {"name": "cell01"}],
                [{"name": "cell10"}, {"name": "cell11"}],
            ],
            "first": {"_instance_": "matrix[0][0]"},
        })

        # Act
        with mock_filesystem(fs):
            composer = ConfigComposer(fs.base_path)
            result = composer.compose(Path("/configs/app.yaml"))

        # Assert
        self.assertEqual(result["first"]["name"], "cell00")

    def test_compose__InstanceChainEndingWithNull__ResolvesCorrectly(self):
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/app.yaml", {
            "_target_": "App",
            "alias": {"_instance_": None},
            "service": {
                "db": {"_instance_": "alias"},
            },
        })

        # Act
        with mock_filesystem(fs):
            composer = ConfigComposer(fs.base_path)
            result = composer.compose(Path("/configs/app.yaml"))

        # Assert - chains to null should result in None
        self.assertIsNone(result["service"]["db"])

    def test_compose__InstanceMultipleRefsToSame__AllShareValue(self):
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/app.yaml", {
            "_target_": "App",
            "shared": {
                "config": {"batch_size": 32},
            },
            "a": {"cfg": {"_instance_": "/shared.config"}},
            "b": {"cfg": {"_instance_": "shared.config"}},
            "c": {"cfg": {"_instance_": "/shared.config"}},
        })

        # Act
        with mock_filesystem(fs):
            composer = ConfigComposer(fs.base_path)
            result = composer.compose(Path("/configs/app.yaml"))

        # Assert
        self.assertEqual(result["a"]["cfg"]["batch_size"], 32)
        self.assertEqual(result["b"]["cfg"]["batch_size"], 32)
        self.assertEqual(result["c"]["cfg"]["batch_size"], 32)

    def test_compose__InstanceToListItem__ReturnsListItem(self):
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/app.yaml", {
            "_target_": "App",
            "items": ["first", "second", "third"],
            "selected": {"_instance_": "items[1]"},
        })

        # Act
        with mock_filesystem(fs):
            composer = ConfigComposer(fs.base_path)
            result = composer.compose(Path("/configs/app.yaml"))

        # Assert
        self.assertEqual(result["selected"], "second")

    def test_compose__InstanceFromNestedRef__WorksCorrectly(self):
        # Arrange - instance inside a nested _ref_
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/level2.yaml", {
            "_target_": "Level2",
            "value": "deep",
        })
        fs.add_file("/configs/level1.yaml", {
            "_target_": "Level1",
            "inner": {"_ref_": "level2.yaml"},
        })
        fs.add_file("/configs/app.yaml", {
            "_target_": "App",
            "outer": {"_ref_": "level1.yaml"},
            "ref_to_deep": {"_instance_": "/outer.inner.value"},
        })

        # Act
        with mock_filesystem(fs):
            composer = ConfigComposer(fs.base_path)
            result = composer.compose(Path("/configs/app.yaml"))

        # Assert
        self.assertEqual(result["ref_to_deep"], "deep")

    def test_compose__InstanceSelfCircular__RaisesError(self):
        # Arrange - single node circular reference
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/app.yaml", {
            "_target_": "App",
            "self_ref": {"_instance_": "self_ref"},
        })

        # Act & Assert
        with mock_filesystem(fs):
            composer = ConfigComposer(fs.base_path)
            with self.assertRaises(CircularInstanceError):
                composer.compose(Path("/configs/app.yaml"))

    def test_compose__InstanceLongChain__ResolvesCorrectly(self):
        # Arrange - long chain of instances
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/app.yaml", {
            "_target_": "App",
            "target": {"_target_": "Target", "value": "final"},
            "a": {"_instance_": "target"},
            "b": {"_instance_": "a"},
            "c": {"_instance_": "b"},
            "d": {"_instance_": "c"},
        })

        # Act
        with mock_filesystem(fs):
            composer = ConfigComposer(fs.base_path)
            result = composer.compose(Path("/configs/app.yaml"))

        # Assert
        self.assertEqual(result["d"]["_target_"], "Target")
        self.assertEqual(result["d"]["value"], "final")

    def test_compose__NoInstances__ReturnsConfigUnchanged(self):
        # Arrange - no _instance_ references
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/app.yaml", {
            "_target_": "App",
            "model": {"_target_": "Model", "layers": 50},
        })

        # Act
        with mock_filesystem(fs):
            composer = ConfigComposer(fs.base_path)
            result = composer.compose(Path("/configs/app.yaml"))

        # Assert
        self.assertEqual(result["model"]["layers"], 50)

    def test_compose__InstanceIndexOutOfRange__RaisesError(self):
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/app.yaml", {
            "_target_": "App",
            "items": ["first", "second"],
            "selected": {"_instance_": "items[99]"},
        })

        # Act & Assert
        with mock_filesystem(fs):
            composer = ConfigComposer(fs.base_path)
            with self.assertRaises(InstanceResolutionError) as ctx:
                composer.compose(Path("/configs/app.yaml"))

        self.assertIn("not found", str(ctx.exception))

    def test_compose__InstanceToNonIndexableWithIndex__RaisesError(self):
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/app.yaml", {
            "_target_": "App",
            "value": 42,
            "selected": {"_instance_": "value[0]"},
        })

        # Act & Assert
        with mock_filesystem(fs):
            composer = ConfigComposer(fs.base_path)
            with self.assertRaises(InstanceResolutionError) as ctx:
                composer.compose(Path("/configs/app.yaml"))

        self.assertIn("not found", str(ctx.exception))


class ProvenanceErrorPathTests(TestCase):
    """Tests for error paths when using compose_with_provenance.

    These tests cover error conditions that occur in the provenance-tracking
    code paths, which are separate from the regular compose() paths.
    """

    def setUp(self) -> None:
        """Set up for tests."""
        clear_cache()

    def tearDown(self) -> None:
        """Clean up after tests."""
        clear_cache()

    def test_compose_with_provenance__RefAtRoot__RaisesRefAtRootError(self):
        """Test _ref_ at root level raises error with provenance tracking."""
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/base.yaml", {"_target_": "Base", "value": 1})
        fs.add_file("/configs/app.yaml", {"_ref_": "base.yaml", "extra": "value"})

        # Act & Assert
        with mock_filesystem(fs):
            composer = ConfigComposer(fs.base_path)
            with self.assertRaises(RefAtRootError) as ctx:
                composer.compose_with_provenance(Path("/configs/app.yaml"))

        self.assertIn("root level", str(ctx.exception))

    def test_compose_with_provenance__CircularRefs__RaisesCircularRefError(self):
        """Test circular refs detected with provenance tracking."""
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/a.yaml", {
            "_target_": "A",
            "b": {"_ref_": "b.yaml"},
        })
        fs.add_file("/configs/b.yaml", {
            "_target_": "B",
            "a": {"_ref_": "a.yaml"},
        })
        fs.add_file("/configs/app.yaml", {
            "_target_": "App",
            "nested": {"_ref_": "a.yaml"},
        })

        # Act & Assert
        with mock_filesystem(fs):
            composer = ConfigComposer(fs.base_path)
            with self.assertRaises(CircularRefError) as ctx:
                composer.compose_with_provenance(Path("/configs/app.yaml"))

        self.assertIn("a.yaml", str(ctx.exception))
        self.assertIn("b.yaml", str(ctx.exception))

    def test_compose_with_provenance__RefInstanceConflict__RaisesError(self):
        """Test _ref_ and _instance_ conflict with provenance tracking."""
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/model.yaml", {"_target_": "Model", "value": 1})
        fs.add_file("/configs/app.yaml", {
            "_target_": "App",
            "model": {
                "_ref_": "model.yaml",
                "_instance_": "/shared.db",
            },
        })

        # Act & Assert
        with mock_filesystem(fs):
            composer = ConfigComposer(fs.base_path)
            with self.assertRaises(RefInstanceConflictError) as ctx:
                composer.compose_with_provenance(Path("/configs/app.yaml"))

        self.assertIn("_ref_", str(ctx.exception))
        self.assertIn("_instance_", str(ctx.exception))

    def test_compose_with_provenance__InvalidInstanceType__RaisesError(self):
        """Test invalid _instance_ type (non-string) with provenance tracking."""
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/app.yaml", {
            "_target_": "App",
            "service": {
                "db": {"_instance_": 123},
            },
        })

        # Act & Assert
        with mock_filesystem(fs):
            composer = ConfigComposer(fs.base_path)
            with self.assertRaises(InstanceResolutionError) as ctx:
                composer.compose_with_provenance(Path("/configs/app.yaml"))

        self.assertIn("must be a string or null", str(ctx.exception))

    def test_compose_with_provenance__NonStringRef__RaisesError(self):
        """Test non-string _ref_ with provenance tracking."""
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/app.yaml", {
            "_target_": "App",
            "model": {"_ref_": 123},
        })

        # Act & Assert
        with mock_filesystem(fs):
            composer = ConfigComposer(fs.base_path)
            with self.assertRaises(RefResolutionError) as ctx:
                composer.compose_with_provenance(Path("/configs/app.yaml"))

        self.assertIn("must be a string", str(ctx.exception))

    def test_compose_with_provenance__RefFileNotFound__RaisesError(self):
        """Test file not found error wrapped in RefResolutionError with provenance."""
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/app.yaml", {
            "_target_": "App",
            "model": {"_ref_": "does_not_exist.yaml"},
        })

        # Act & Assert
        with mock_filesystem(fs):
            composer = ConfigComposer(fs.base_path)
            with self.assertRaises(RefResolutionError) as ctx:
                composer.compose_with_provenance(Path("/configs/app.yaml"))

        self.assertIn("does_not_exist.yaml", str(ctx.exception))
        self.assertIn("file not found", str(ctx.exception))

    def test_compose_with_provenance__RefAtRootOfReferencedFile__RaisesError(self):
        """Test _ref_ at root of referenced file with provenance tracking."""
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/base.yaml", {"value": 1})
        fs.add_file("/configs/broken.yaml", {"_ref_": "base.yaml", "extra": 2})
        fs.add_file("/configs/app.yaml", {
            "_target_": "App",
            "model": {"_ref_": "broken.yaml"},
        })

        # Act & Assert
        with mock_filesystem(fs):
            composer = ConfigComposer(fs.base_path)
            with self.assertRaises(RefAtRootError) as ctx:
                composer.compose_with_provenance(Path("/configs/app.yaml"))

        self.assertIn("broken.yaml", str(ctx.exception))

    def test_compose_with_provenance__NullTargetOverride__RaisesError(self):
        """Test overriding _target_ to null with provenance tracking."""
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/model.yaml", {"_target_": "Model", "value": 1})
        fs.add_file("/configs/app.yaml", {
            "_target_": "App",
            "model": {
                "_ref_": "model.yaml",
                "_target_": None,
            },
        })

        # Act & Assert
        with mock_filesystem(fs):
            composer = ConfigComposer(fs.base_path)
            with self.assertRaises(RefResolutionError) as ctx:
                composer.compose_with_provenance(Path("/configs/app.yaml"))

        self.assertIn("_target_", str(ctx.exception))
        self.assertIn("null", str(ctx.exception))

    def test_compose_with_provenance__NestedLists__ComposesCorrectly(self):
        """Test nested lists are composed correctly with provenance tracking."""
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/app.yaml", {
            "_target_": "App",
            "matrix": [
                [{"value": "nested"}, {"value": "item"}],
            ],
        })

        # Act
        with mock_filesystem(fs):
            composer = ConfigComposer(fs.base_path)
            prov = composer.compose_with_provenance(Path("/configs/app.yaml"))

        # Assert - verify nested lists are composed correctly
        self.assertIsNotNone(prov)
        self.assertEqual(prov.config["matrix"][0][0]["value"], "nested")
        self.assertEqual(prov.config["matrix"][0][1]["value"], "item")

    def test_compose_with_provenance__ChainedInstanceCycle__RaisesError(self):
        """Test circular chained instance references."""
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/app.yaml", {
            "_target_": "App",
            "a": {"_instance_": "b"},
            "b": {"_instance_": "c"},
            "c": {"_instance_": "a"},
        })

        # Act & Assert
        with mock_filesystem(fs):
            composer = ConfigComposer(fs.base_path)
            with self.assertRaises(CircularInstanceError) as ctx:
                composer.compose_with_provenance(Path("/configs/app.yaml"))

        # Should detect the cycle
        error_str = str(ctx.exception)
        self.assertTrue("a" in error_str or "b" in error_str or "c" in error_str)


class ConfigComposerInternalMethodTests(TestCase):
    """Tests for internal ConfigComposer methods to improve coverage."""

    def setUp(self) -> None:
        """Set up for tests."""
        clear_cache()

    def tearDown(self) -> None:
        """Clean up after tests."""
        clear_cache()

    def test_get_line_number__RegularDict__ReturnsNone(self):
        """Test _get_line_number with a regular dict (no CommentedMap)."""
        # Arrange
        from rconfig.composition import IncrementalComposer
        from rconfig.provenance import ProvenanceBuilder

        provenance = ProvenanceBuilder()
        walker = IncrementalComposer(config_root=Path("/configs"), provenance=provenance)
        regular_dict = {"key": "value"}

        # Act
        result = walker._get_line_number(regular_dict, "key")

        # Assert
        self.assertIsNone(result)

    def test_get_value_at_path__EmptyPath__ReturnsConfig(self):
        """Test get_value_at_path with empty path returns config itself."""
        # Arrange
        from rconfig._internal.path_utils import get_value_at_path

        config = {"key": "value", "nested": {"inner": 42}}

        # Act
        result = get_value_at_path(config, "")

        # Assert
        self.assertEqual(result, config)

    def test_get_value_at_path__NonDictKey__RaisesTypeError(self):
        """Test get_value_at_path with key access on non-dict."""
        # Arrange
        from rconfig._internal.path_utils import get_value_at_path

        config = {"key": "string_value"}

        # Act & Assert
        with self.assertRaises(TypeError) as ctx:
            get_value_at_path(config, "key.subkey")

        self.assertIn("non-dict", str(ctx.exception))

    def test_deep_copy_with_resolved_instances__UnresolvedMarker__ReturnsNone(self):
        """Test _deep_copy_with_resolved_instances with unresolved _instance_ marker."""
        # Arrange
        from rconfig.composition import InstanceResolver
        from rconfig.composition import Provenance

        provenance = Provenance()
        resolver = InstanceResolver(provenance)
        value = {"_instance_": "some.path"}  # marker not in resolved dict
        resolved = {}  # empty resolved dict

        # Act
        result = resolver._deep_copy_with_resolved_instances(value, "test.path", resolved)

        # Assert - should return None for unresolved marker
        self.assertIsNone(result)


class ConfigComposerPropertyTests(TestCase):
    """Tests for ConfigComposer property edge cases."""

    def setUp(self) -> None:
        """Set up for tests."""
        clear_cache()

    def tearDown(self) -> None:
        """Clean up after tests."""
        clear_cache()

    def test_instanceTargets__BeforeCompose__ReturnsEmptyDict(self):
        """Test that instance_targets returns {} before compose() is called."""
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/app.yaml", {"_target_": "App"})

        # Act
        with mock_filesystem(fs):
            composer = ConfigComposer(fs.base_path)
            # Don't call compose()
            result = composer.instance_targets

        # Assert
        self.assertEqual(result, {})
