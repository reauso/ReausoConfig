"""Unit tests for ResolverRegistry."""

from types import MappingProxyType
from typing import Any
from unittest import TestCase
from unittest.mock import MagicMock, patch

from rconfig.errors import ResolverExecutionError, UnknownResolverError
from rconfig.interpolation.registry import (
    ResolverReference,
    ResolverRegistry,
)


class ResolverReferenceTests(TestCase):
    """Tests for the ResolverReference dataclass."""

    def test_init__AllFields__CreatesImmutableReference(self):
        # Arrange
        import inspect

        def my_func(x: int) -> str:
            return str(x)

        sig = inspect.signature(my_func)

        # Act
        ref = ResolverReference(
            path="test",
            func=my_func,
            needs_config=False,
            signature=sig,
        )

        # Assert
        self.assertEqual(ref.path, "test")
        self.assertEqual(ref.func, my_func)
        self.assertFalse(ref.needs_config)
        self.assertEqual(ref.signature, sig)

    def test_frozen__Immutable__CannotModify(self):
        # Arrange
        import inspect

        def my_func() -> str:
            return "test"

        ref = ResolverReference(
            path="test",
            func=my_func,
            needs_config=False,
            signature=inspect.signature(my_func),
        )

        # Act & Assert
        with self.assertRaises(Exception):  # FrozenInstanceError
            ref.path = "modified"


class ResolverRegistryTests(TestCase):
    """Tests for the ResolverRegistry class."""

    def setUp(self) -> None:
        self.registry = ResolverRegistry()
        self.registry.clear()  # Ensure clean state for each test

    # === Registration Tests ===

    def test_register__SinglePath__RegistersResolver(self):
        # Arrange
        def my_resolver() -> str:
            return "result"

        # Act
        self.registry.register("uuid", func=my_resolver)

        # Assert
        self.assertIn("uuid", self.registry)
        self.assertEqual(self.registry.known_resolvers["uuid"].func, my_resolver)

    def test_register__NestedPath__RegistersWithColonJoinedKey(self):
        # Arrange
        def my_resolver() -> dict:
            return {"key": "value"}

        # Act
        self.registry.register("db", "lookup", func=my_resolver)

        # Assert
        self.assertIn("db:lookup", self.registry)
        self.assertEqual(self.registry.known_resolvers["db:lookup"].func, my_resolver)

    def test_register__DeeplyNestedPath__RegistersCorrectly(self):
        # Arrange
        def my_resolver() -> str:
            return "cached"

        # Act
        self.registry.register("db", "cache", "get", func=my_resolver)

        # Assert
        self.assertIn("db:cache:get", self.registry)

    def test_register__WithConfigParam__DetectsNeedsConfig(self):
        # Arrange
        def resolver_with_config(*, _config_: dict) -> str:
            return str(_config_)

        # Act
        self.registry.register("derive", func=resolver_with_config)

        # Assert
        self.assertTrue(self.registry.known_resolvers["derive"].needs_config)

    def test_register__WithoutConfigParam__DoesNotNeedConfig(self):
        # Arrange
        def simple_resolver() -> str:
            return "simple"

        # Act
        self.registry.register("simple", func=simple_resolver)

        # Assert
        self.assertFalse(self.registry.known_resolvers["simple"].needs_config)

    def test_register__EmptyPath__RaisesValueError(self):
        # Arrange
        def my_resolver() -> str:
            return "result"

        # Act & Assert
        with self.assertRaises(ValueError) as ctx:
            self.registry.register(func=my_resolver)
        self.assertIn("empty", str(ctx.exception).lower())

    def test_register__NotCallable__RaisesValueError(self):
        # Act & Assert
        with self.assertRaises(ValueError) as ctx:
            self.registry.register("test", func="not a function")
        self.assertIn("callable", str(ctx.exception).lower())

    def test_register__SamePath__OverwritesExisting(self):
        # Arrange
        def first_resolver() -> str:
            return "first"

        def second_resolver() -> str:
            return "second"

        self.registry.register("test", func=first_resolver)

        # Act
        self.registry.register("test", func=second_resolver)

        # Assert
        self.assertEqual(self.registry.known_resolvers["test"].func, second_resolver)

    def test_register__ColonDelimitedString__RegistersCorrectly(self):
        # Arrange
        def my_resolver() -> str:
            return "result"

        # Act
        self.registry.register("db:lookup", func=my_resolver)

        # Assert
        self.assertIn("db:lookup", self.registry)
        self.assertEqual(self.registry.known_resolvers["db:lookup"].func, my_resolver)

    def test_register__DotDelimitedString__RegistersWithColonKey(self):
        # Arrange
        def my_resolver() -> str:
            return "result"

        # Act
        self.registry.register("db.lookup", func=my_resolver)

        # Assert
        self.assertIn("db:lookup", self.registry)
        self.assertEqual(self.registry.known_resolvers["db:lookup"].func, my_resolver)

    def test_register__DeeplyNestedColonString__RegistersCorrectly(self):
        # Arrange
        def my_resolver() -> str:
            return "cached"

        # Act
        self.registry.register("db:cache:get", func=my_resolver)

        # Assert
        self.assertIn("db:cache:get", self.registry)

    def test_register__DeeplyNestedDotString__RegistersCorrectly(self):
        # Arrange
        def my_resolver() -> str:
            return "cached"

        # Act
        self.registry.register("db.cache.get", func=my_resolver)

        # Assert
        self.assertIn("db:cache:get", self.registry)

    def test_register__AllSyntaxesEquivalent__SameResult(self):
        # Arrange
        def resolver1() -> str:
            return "r1"

        def resolver2() -> str:
            return "r2"

        def resolver3() -> str:
            return "r3"

        # Act - register with each syntax
        self.registry.register("ns", "func", func=resolver1)
        key1 = list(self.registry.known_resolvers.keys())[-1]

        self.registry.clear()
        self.registry.register("ns:func", func=resolver2)
        key2 = list(self.registry.known_resolvers.keys())[-1]

        self.registry.clear()
        self.registry.register("ns.func", func=resolver3)
        key3 = list(self.registry.known_resolvers.keys())[-1]

        # Assert - all produce the same key
        self.assertEqual(key1, "ns:func")
        self.assertEqual(key2, "ns:func")
        self.assertEqual(key3, "ns:func")

    # === Unregistration Tests ===

    def test_unregister__ExistingPath__RemovesResolver(self):
        # Arrange
        def my_resolver() -> str:
            return "result"

        self.registry.register("test", func=my_resolver)

        # Act
        self.registry.unregister("test")

        # Assert
        self.assertNotIn("test", self.registry)

    def test_unregister__NestedPath__RemovesCorrectly(self):
        # Arrange
        def my_resolver() -> str:
            return "result"

        self.registry.register("db", "lookup", func=my_resolver)

        # Act
        self.registry.unregister("db", "lookup")

        # Assert
        self.assertNotIn("db:lookup", self.registry)

    def test_unregister__NonExistentPath__RaisesKeyError(self):
        # Act & Assert
        with self.assertRaises(KeyError):
            self.registry.unregister("nonexistent")

    def test_unregister__ColonDelimitedString__RemovesCorrectly(self):
        # Arrange
        def my_resolver() -> str:
            return "result"

        self.registry.register("db", "lookup", func=my_resolver)

        # Act
        self.registry.unregister("db:lookup")

        # Assert
        self.assertNotIn("db:lookup", self.registry)

    def test_unregister__DotDelimitedString__RemovesCorrectly(self):
        # Arrange
        def my_resolver() -> str:
            return "result"

        self.registry.register("db", "lookup", func=my_resolver)

        # Act
        self.registry.unregister("db.lookup")

        # Assert
        self.assertNotIn("db:lookup", self.registry)

    # === Contains Tests ===

    def test_contains__RegisteredPath__ReturnsTrue(self):
        # Arrange
        self.registry.register("uuid", func=lambda: "test")

        # Act & Assert
        self.assertTrue("uuid" in self.registry)

    def test_contains__UnregisteredPath__ReturnsFalse(self):
        # Act & Assert
        self.assertFalse("nonexistent" in self.registry)

    def test_contains__NestedPath__WorksCorrectly(self):
        # Arrange
        self.registry.register("db", "lookup", func=lambda: "test")

        # Act & Assert
        self.assertTrue("db:lookup" in self.registry)
        self.assertFalse("db" in self.registry)
        self.assertFalse("lookup" in self.registry)

    # === Known Resolvers Property Tests ===

    def test_known_resolvers__Empty__ReturnsEmptyMapping(self):
        # Act
        resolvers = self.registry.known_resolvers

        # Assert
        self.assertEqual(len(resolvers), 0)
        self.assertIsInstance(resolvers, MappingProxyType)

    def test_known_resolvers__WithResolvers__ReturnsReadOnlyView(self):
        # Arrange
        self.registry.register("a", func=lambda: "a")
        self.registry.register("b", "c", func=lambda: "bc")

        # Act
        resolvers = self.registry.known_resolvers

        # Assert
        self.assertEqual(len(resolvers), 2)
        self.assertIn("a", resolvers)
        self.assertIn("b:c", resolvers)

    def test_known_resolvers__Immutable__CannotModify(self):
        # Arrange
        self.registry.register("test", func=lambda: "test")
        resolvers = self.registry.known_resolvers

        # Act & Assert
        with self.assertRaises(TypeError):
            resolvers["new"] = "value"

    # === Resolution Tests ===

    def test_resolve__NoArgs__CallsResolverWithoutArgs(self):
        # Arrange
        mock_func = MagicMock(return_value="result")
        self.registry.register("test", func=mock_func)

        # Act
        result = self.registry.resolve("test", [], {}, None)

        # Assert
        self.assertEqual(result, "result")
        mock_func.assert_called_once_with()

    def test_resolve__PositionalArgs__PassesCorrectly(self):
        # Arrange
        mock_func = MagicMock(return_value="result")
        self.registry.register("test", func=mock_func)

        # Act
        result = self.registry.resolve("test", ["arg1", 42], {}, None)

        # Assert
        mock_func.assert_called_once_with("arg1", 42)

    def test_resolve__KeywordArgs__PassesCorrectly(self):
        # Arrange
        mock_func = MagicMock(return_value="result")
        self.registry.register("test", func=mock_func)

        # Act
        result = self.registry.resolve("test", [], {"key": "value", "num": 10}, None)

        # Assert
        mock_func.assert_called_once_with(key="value", num=10)

    def test_resolve__MixedArgs__PassesCorrectly(self):
        # Arrange
        mock_func = MagicMock(return_value="result")
        self.registry.register("test", func=mock_func)

        # Act
        result = self.registry.resolve("test", ["pos"], {"key": "kw"}, None)

        # Assert
        mock_func.assert_called_once_with("pos", key="kw")

    def test_resolve__NeedsConfig__PassesConfigAsReadOnly(self):
        # Arrange
        received_config = None

        def resolver_with_config(*, _config_: Any) -> str:
            nonlocal received_config
            received_config = _config_
            return "result"

        self.registry.register("test", func=resolver_with_config)
        config = {"key": "value"}

        # Act
        result = self.registry.resolve("test", [], {}, config)

        # Assert
        self.assertEqual(result, "result")
        self.assertIsInstance(received_config, MappingProxyType)
        self.assertEqual(received_config["key"], "value")

    def test_resolve__NeedsConfigNoneProvided__PassesEmptyMapping(self):
        # Arrange
        received_config = None

        def resolver_with_config(*, _config_: Any) -> str:
            nonlocal received_config
            received_config = _config_
            return "result"

        self.registry.register("test", func=resolver_with_config)

        # Act
        result = self.registry.resolve("test", [], {}, None)

        # Assert
        self.assertIsInstance(received_config, MappingProxyType)
        self.assertEqual(len(received_config), 0)

    def test_resolve__UnknownPath__RaisesUnknownResolverError(self):
        # Act & Assert
        with self.assertRaises(UnknownResolverError) as ctx:
            self.registry.resolve("nonexistent", [], {}, None)

        self.assertEqual(ctx.exception.path, "nonexistent")
        self.assertEqual(ctx.exception.available, [])

    def test_resolve__UnknownPathWithOthers__IncludesAvailableInError(self):
        # Arrange
        self.registry.register("a", func=lambda: "a")
        self.registry.register("b", func=lambda: "b")

        # Act & Assert
        with self.assertRaises(UnknownResolverError) as ctx:
            self.registry.resolve("nonexistent", [], {}, None)

        self.assertEqual(ctx.exception.path, "nonexistent")
        self.assertIn("a", ctx.exception.available)
        self.assertIn("b", ctx.exception.available)

    def test_resolve__ResolverRaisesException__WrapsInResolverExecutionError(self):
        # Arrange
        def failing_resolver() -> str:
            raise RuntimeError("Something went wrong")

        self.registry.register("fail", func=failing_resolver)

        # Act & Assert
        with self.assertRaises(ResolverExecutionError) as ctx:
            self.registry.resolve("fail", [], {}, None)

        self.assertEqual(ctx.exception.path, "fail")
        self.assertIsInstance(ctx.exception.original_error, RuntimeError)
        self.assertIn("Something went wrong", str(ctx.exception))

    def test_resolve__ReturnsNone__IsValidResult(self):
        # Arrange
        def null_resolver() -> None:
            return None

        self.registry.register("null", func=null_resolver)

        # Act
        result = self.registry.resolve("null", [], {}, None)

        # Assert
        self.assertIsNone(result)

    # === Thread Safety Tests ===

    def test_register__Concurrent__ThreadSafe(self):
        import threading

        # Arrange
        errors = []

        def register_many(prefix: str, count: int) -> None:
            try:
                for i in range(count):
                    self.registry.register(f"{prefix}_{i}", func=lambda: i)
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=register_many, args=(f"t{i}", 50))
            for i in range(5)
        ]

        # Act
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Assert
        self.assertEqual(errors, [])
        self.assertEqual(len(self.registry.known_resolvers), 250)


class ResolverRegistrySingletonTests(TestCase):
    """Tests for the ResolverRegistry @Singleton decorator behavior."""

    def test_singleton__MultipleCalls__ReturnsSameInstance(self):
        # Act
        registry1 = ResolverRegistry()
        registry2 = ResolverRegistry()

        # Assert
        self.assertIs(registry1, registry2)

    def test_singleton__ReturnsResolverRegistryInstance(self):
        # Act
        registry = ResolverRegistry()

        # Assert
        # Note: With @Singleton decorator, ResolverRegistry is actually the
        # Singleton wrapper class, so we check the wrapped class
        self.assertIsInstance(registry, ResolverRegistry.wrapped_class)
