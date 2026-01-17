"""Tests for InstanceResolver module."""

from unittest import TestCase

from rconfig.composition import InstanceMarker, InstanceResolver
from rconfig.provenance import ProvenanceBuilder
from rconfig.errors import CircularInstanceError, InstanceResolutionError


class InstanceResolverPropertyTests(TestCase):
    """Tests for InstanceResolver properties."""

    def test_instanceTargets__EmptyResolver__ReturnsEmptyDict(self):
        # Arrange
        builder = ProvenanceBuilder()
        resolver = InstanceResolver(builder)

        # Act
        targets = resolver.instance_targets

        # Assert
        self.assertEqual(targets, {})

    def test_instanceTargets__AfterResolve__ReturnsCopy(self):
        # Arrange
        builder = ProvenanceBuilder()
        resolver = InstanceResolver(builder)
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
        builder = ProvenanceBuilder()
        resolver = InstanceResolver(builder)

        # Act
        targets = resolver.instance_targets
        targets["new_key"] = "new_value"

        # Assert
        self.assertNotIn("new_key", resolver.instance_targets)


class InstancePathResolutionTests(TestCase):
    """Tests for _resolve_instance_path method."""

    def test_resolvePath__AbsolutePath__StripsLeadingSlash(self):
        # Arrange
        builder = ProvenanceBuilder()
        resolver = InstanceResolver(builder)
        config = {"shared": {"_target_": "Database"}}

        # Act
        result = resolver._resolve_instance_path("/shared", "service", config)

        # Assert
        self.assertEqual(result, "shared")

    def test_resolvePath__RelativePathWithDotSlash__StripsPrefix(self):
        # Arrange
        builder = ProvenanceBuilder()
        resolver = InstanceResolver(builder)
        config = {"shared": {"_target_": "Database"}}

        # Act
        result = resolver._resolve_instance_path("./shared", "service", config)

        # Assert
        self.assertEqual(result, "shared")

    def test_resolvePath__PlainRelativePath__ReturnsAsIs(self):
        # Arrange
        builder = ProvenanceBuilder()
        resolver = InstanceResolver(builder)
        config = {"shared": {"_target_": "Database"}}

        # Act
        result = resolver._resolve_instance_path("shared", "service", config)

        # Assert
        self.assertEqual(result, "shared")

    def test_resolvePath__NestedPath__ResolvesCorrectly(self):
        # Arrange
        builder = ProvenanceBuilder()
        resolver = InstanceResolver(builder)
        config = {"data": {"sources": {"primary": {"_target_": "Source"}}}}

        # Act
        result = resolver._resolve_instance_path(
            "/data.sources.primary", "service.db", config
        )

        # Assert
        self.assertEqual(result, "data.sources.primary")

    def test_resolvePath__PathNotFound__RaisesInstanceResolutionError(self):
        # Arrange
        builder = ProvenanceBuilder()
        resolver = InstanceResolver(builder)
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
        builder = ProvenanceBuilder()
        resolver = InstanceResolver(builder)

        # Act
        result = resolver._deep_copy_with_resolved_instances(42, "path", {})

        # Assert
        self.assertEqual(result, 42)

    def test_deepCopy__StringValue__ReturnsSameValue(self):
        # Arrange
        builder = ProvenanceBuilder()
        resolver = InstanceResolver(builder)

        # Act
        result = resolver._deep_copy_with_resolved_instances("hello", "path", {})

        # Assert
        self.assertEqual(result, "hello")

    def test_deepCopy__ListValue__CopiesList(self):
        # Arrange
        builder = ProvenanceBuilder()
        resolver = InstanceResolver(builder)
        value = [1, 2, 3]

        # Act
        result = resolver._deep_copy_with_resolved_instances(value, "path", {})

        # Assert
        self.assertEqual(result, [1, 2, 3])
        self.assertIsNot(result, value)

    def test_deepCopy__DictValue__CopiesDict(self):
        # Arrange
        builder = ProvenanceBuilder()
        resolver = InstanceResolver(builder)
        value = {"a": 1, "b": 2}

        # Act
        result = resolver._deep_copy_with_resolved_instances(value, "path", {})

        # Assert
        self.assertEqual(result, {"a": 1, "b": 2})
        self.assertIsNot(result, value)

    def test_deepCopy__InstanceMarker__ReplacesWithResolvedValue(self):
        # Arrange
        builder = ProvenanceBuilder()
        resolver = InstanceResolver(builder)
        value = {"_instance_": "/shared"}
        resolved = {"path": {"_target_": "Database", "url": "localhost"}}

        # Act
        result = resolver._deep_copy_with_resolved_instances(value, "path", resolved)

        # Assert
        self.assertEqual(result, {"_target_": "Database", "url": "localhost"})

    def test_deepCopy__InstanceMarkerNull__ReturnsNone(self):
        # Arrange
        builder = ProvenanceBuilder()
        resolver = InstanceResolver(builder)
        value = {"_instance_": None}

        # Act
        result = resolver._deep_copy_with_resolved_instances(value, "path", {})

        # Assert
        self.assertIsNone(result)

    def test_deepCopy__NestedDict__RecursivelyCopies(self):
        # Arrange
        builder = ProvenanceBuilder()
        resolver = InstanceResolver(builder)
        value = {"outer": {"inner": {"deep": "value"}}}

        # Act
        result = resolver._deep_copy_with_resolved_instances(value, "", {})

        # Assert
        self.assertEqual(result["outer"]["inner"]["deep"], "value")
        self.assertIsNot(result["outer"], value["outer"])

    def test_deepCopy__NestedList__RecursivelyCopies(self):
        # Arrange
        builder = ProvenanceBuilder()
        resolver = InstanceResolver(builder)
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
        builder = ProvenanceBuilder()
        resolver = InstanceResolver(builder)
        config = {"_target_": "App", "name": "test"}

        # Act
        result = resolver.resolve({}, config)

        # Assert
        self.assertEqual(result, config)

    def test_resolve__SimpleInstance__ReplacesMarkerWithValue(self):
        # Arrange
        builder = ProvenanceBuilder()
        resolver = InstanceResolver(builder)
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
        builder = ProvenanceBuilder()
        resolver = InstanceResolver(builder)
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


class CircularInstanceTests(TestCase):
    """Tests for circular instance reference detection (lines 77, 81, 85-86)."""

    def test_resolve__CircularInstanceReference__RaisesError(self):
        """Test that circular _instance_ references are detected."""
        builder = ProvenanceBuilder()
        resolver = InstanceResolver(builder)
        config = {
            "a": {"_instance_": "/b"},
            "b": {"_instance_": "/a"},
        }
        instances = {
            "a": InstanceMarker("a", "/b", "app.yaml", 1),
            "b": InstanceMarker("b", "/a", "app.yaml", 2),
        }

        # Act & Assert
        with self.assertRaises(CircularInstanceError) as ctx:
            resolver.resolve(instances, config)
        # Verify cycle information is captured
        self.assertIn("a", ctx.exception.chain)
        self.assertIn("b", ctx.exception.chain)

    def test_resolve__SelfReference__RaisesCircularError(self):
        """Test that self-referencing _instance_ is detected."""
        builder = ProvenanceBuilder()
        resolver = InstanceResolver(builder)
        config = {
            "a": {"_instance_": "/a"},
        }
        instances = {
            "a": InstanceMarker("a", "/a", "app.yaml", 1),
        }

        # Act & Assert
        with self.assertRaises(CircularInstanceError):
            resolver.resolve(instances, config)

    def test_resolve__ThreeWayCycle__RaisesError(self):
        """Test that three-way circular reference is detected."""
        builder = ProvenanceBuilder()
        resolver = InstanceResolver(builder)
        config = {
            "a": {"_instance_": "/b"},
            "b": {"_instance_": "/c"},
            "c": {"_instance_": "/a"},
        }
        instances = {
            "a": InstanceMarker("a", "/b", "app.yaml", 1),
            "b": InstanceMarker("b", "/c", "app.yaml", 2),
            "c": InstanceMarker("c", "/a", "app.yaml", 3),
        }

        # Act & Assert
        with self.assertRaises(CircularInstanceError):
            resolver.resolve(instances, config)

    def test_resolve__AlreadyResolved__ReturnsCachedValue(self):
        """Test that already resolved instances are returned from cache (line 77)."""
        builder = ProvenanceBuilder()
        resolver = InstanceResolver(builder)
        config = {
            "shared": {"_target_": "Database", "url": "postgres://localhost"},
            "service1": {"_instance_": "/shared"},
            "service2": {"_instance_": "/shared"},
        }
        instances = {
            "service1": InstanceMarker("service1", "/shared", "app.yaml", 2),
            "service2": InstanceMarker("service2", "/shared", "app.yaml", 3),
        }

        # Act
        result = resolver.resolve(instances, config)

        # Assert - both resolve to the same target value
        self.assertEqual(result["service1"], result["service2"])

    def test_resolve__NonInstancePath__GetsValueFromConfig(self):
        """Test that non-instance paths get value directly from config (line 81)."""
        builder = ProvenanceBuilder()
        resolver = InstanceResolver(builder)
        config = {
            "data": {"value": 42},
            "ref": {"_instance_": "/data"},
        }
        instances = {
            "ref": InstanceMarker("ref", "/data", "app.yaml", 2),
        }

        # Act
        result = resolver.resolve(instances, config)

        # Assert
        self.assertEqual(result["ref"], {"value": 42})
