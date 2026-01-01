"""Tests for InstanceResolver module."""

from unittest import TestCase

from rconfig.CompositionWalker import InstanceMarker
from rconfig.errors import InstanceResolutionError
from rconfig.InstanceResolver import InstanceResolver
from rconfig.Provenance import Provenance


class InstanceResolverPropertyTests(TestCase):
    """Tests for InstanceResolver properties."""

    def test_instanceTargets__EmptyResolver__ReturnsEmptyDict(self):
        # Arrange
        provenance = Provenance()
        resolver = InstanceResolver(provenance)

        # Act
        targets = resolver.instance_targets

        # Assert
        self.assertEqual(targets, {})

    def test_instanceTargets__AfterResolve__ReturnsCopy(self):
        # Arrange
        provenance = Provenance()
        resolver = InstanceResolver(provenance)
        config = {
            "shared": {"_target_": "Database", "url": "postgres://localhost"},
            "service": {"_instance_": "/shared"},
        }
        instances = {
            "service": InstanceMarker("service", "/shared", "app.yaml", 5),
        }

        # Act
        resolver.resolve(instances, config)
        targets = resolver.instance_targets

        # Assert
        self.assertIn("service", targets)
        self.assertEqual(targets["service"], "shared")

    def test_instanceTargets__ReturnsCopy__ModificationDoesNotAffectOriginal(self):
        # Arrange
        provenance = Provenance()
        resolver = InstanceResolver(provenance)

        # Act
        targets = resolver.instance_targets
        targets["new_key"] = "new_value"

        # Assert
        self.assertNotIn("new_key", resolver.instance_targets)


class InstancePathResolutionTests(TestCase):
    """Tests for _resolve_instance_path method."""

    def test_resolvePath__AbsolutePath__StripsLeadingSlash(self):
        # Arrange
        provenance = Provenance()
        resolver = InstanceResolver(provenance)
        config = {"shared": {"_target_": "Database"}}

        # Act
        result = resolver._resolve_instance_path("/shared", "service", config)

        # Assert
        self.assertEqual(result, "shared")

    def test_resolvePath__RelativePathWithDotSlash__StripsPrefix(self):
        # Arrange
        provenance = Provenance()
        resolver = InstanceResolver(provenance)
        config = {"shared": {"_target_": "Database"}}

        # Act
        result = resolver._resolve_instance_path("./shared", "service", config)

        # Assert
        self.assertEqual(result, "shared")

    def test_resolvePath__PlainRelativePath__ReturnsAsIs(self):
        # Arrange
        provenance = Provenance()
        resolver = InstanceResolver(provenance)
        config = {"shared": {"_target_": "Database"}}

        # Act
        result = resolver._resolve_instance_path("shared", "service", config)

        # Assert
        self.assertEqual(result, "shared")

    def test_resolvePath__NestedPath__ResolvesCorrectly(self):
        # Arrange
        provenance = Provenance()
        resolver = InstanceResolver(provenance)
        config = {"data": {"sources": {"primary": {"_target_": "Source"}}}}

        # Act
        result = resolver._resolve_instance_path(
            "/data.sources.primary", "service.db", config
        )

        # Assert
        self.assertEqual(result, "data.sources.primary")

    def test_resolvePath__PathNotFound__RaisesInstanceResolutionError(self):
        # Arrange
        provenance = Provenance()
        resolver = InstanceResolver(provenance)
        config = {"shared": {"_target_": "Database"}}

        # Act & Assert
        with self.assertRaises(InstanceResolutionError) as ctx:
            resolver._resolve_instance_path("/nonexistent", "service", config)

        self.assertIn("nonexistent", str(ctx.exception))
        self.assertIn("not found", str(ctx.exception))


class DeepCopyResolutionTests(TestCase):
    """Tests for _deep_copy_with_resolved_instances method."""

    def test_deepCopy__ScalarValue__ReturnsSameValue(self):
        # Arrange
        provenance = Provenance()
        resolver = InstanceResolver(provenance)

        # Act
        result = resolver._deep_copy_with_resolved_instances(42, "path", {})

        # Assert
        self.assertEqual(result, 42)

    def test_deepCopy__StringValue__ReturnsSameValue(self):
        # Arrange
        provenance = Provenance()
        resolver = InstanceResolver(provenance)

        # Act
        result = resolver._deep_copy_with_resolved_instances("hello", "path", {})

        # Assert
        self.assertEqual(result, "hello")

    def test_deepCopy__ListValue__CopiesList(self):
        # Arrange
        provenance = Provenance()
        resolver = InstanceResolver(provenance)
        value = [1, 2, 3]

        # Act
        result = resolver._deep_copy_with_resolved_instances(value, "path", {})

        # Assert
        self.assertEqual(result, [1, 2, 3])
        self.assertIsNot(result, value)

    def test_deepCopy__DictValue__CopiesDict(self):
        # Arrange
        provenance = Provenance()
        resolver = InstanceResolver(provenance)
        value = {"a": 1, "b": 2}

        # Act
        result = resolver._deep_copy_with_resolved_instances(value, "path", {})

        # Assert
        self.assertEqual(result, {"a": 1, "b": 2})
        self.assertIsNot(result, value)

    def test_deepCopy__InstanceMarker__ReplacesWithResolvedValue(self):
        # Arrange
        provenance = Provenance()
        resolver = InstanceResolver(provenance)
        value = {"_instance_": "/shared"}
        resolved = {"path": {"_target_": "Database", "url": "localhost"}}

        # Act
        result = resolver._deep_copy_with_resolved_instances(value, "path", resolved)

        # Assert
        self.assertEqual(result, {"_target_": "Database", "url": "localhost"})

    def test_deepCopy__InstanceMarkerNull__ReturnsNone(self):
        # Arrange
        provenance = Provenance()
        resolver = InstanceResolver(provenance)
        value = {"_instance_": None}

        # Act
        result = resolver._deep_copy_with_resolved_instances(value, "path", {})

        # Assert
        self.assertIsNone(result)

    def test_deepCopy__NestedDict__RecursivelyCopies(self):
        # Arrange
        provenance = Provenance()
        resolver = InstanceResolver(provenance)
        value = {"outer": {"inner": {"deep": "value"}}}

        # Act
        result = resolver._deep_copy_with_resolved_instances(value, "", {})

        # Assert
        self.assertEqual(result["outer"]["inner"]["deep"], "value")
        self.assertIsNot(result["outer"], value["outer"])

    def test_deepCopy__NestedList__RecursivelyCopies(self):
        # Arrange
        provenance = Provenance()
        resolver = InstanceResolver(provenance)
        value = {"items": [{"a": 1}, {"b": 2}]}

        # Act
        result = resolver._deep_copy_with_resolved_instances(value, "", {})

        # Assert
        self.assertEqual(len(result["items"]), 2)
        self.assertEqual(result["items"][0], {"a": 1})
        self.assertIsNot(result["items"], value["items"])


class InstanceResolverIntegrationTests(TestCase):
    """Integration tests for InstanceResolver.resolve method."""

    def test_resolve__NoInstances__ReturnsConfigUnchanged(self):
        # Arrange
        provenance = Provenance()
        resolver = InstanceResolver(provenance)
        config = {"_target_": "App", "name": "test"}

        # Act
        result = resolver.resolve({}, config)

        # Assert
        self.assertEqual(result, config)

    def test_resolve__SimpleInstance__ReplacesMarkerWithValue(self):
        # Arrange
        provenance = Provenance()
        resolver = InstanceResolver(provenance)
        config = {
            "shared": {"_target_": "Database", "url": "postgres://localhost"},
            "service": {"_instance_": "/shared"},
        }
        instances = {
            "service": InstanceMarker("service", "/shared", "app.yaml", 5),
        }

        # Act
        result = resolver.resolve(instances, config)

        # Assert
        self.assertEqual(result["service"]["_target_"], "Database")
        self.assertEqual(result["service"]["url"], "postgres://localhost")

    def test_resolve__NullInstance__ReplacesWithNone(self):
        # Arrange
        provenance = Provenance()
        resolver = InstanceResolver(provenance)
        config = {
            "optional": {"_instance_": None},
        }
        instances = {
            "optional": InstanceMarker("optional", None, "app.yaml", 5),
        }

        # Act
        result = resolver.resolve(instances, config)

        # Assert
        self.assertIsNone(result["optional"])
