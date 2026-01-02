from types import MappingProxyType
from unittest import TestCase

from rconfig.store import ConfigStore


class ConfigStoreTests(TestCase):
    def _empty_store(self) -> ConfigStore:
        store = ConfigStore()
        store.clear()
        return store

    def test_register__WithTargetClass__StoreConfigReference(self):
        # Arrange
        store = self._empty_store()

        class Example:
            def __init__(self, a, b, c=None):
                self.a = a
                self.b = b
                self.c = c

        # Act
        store.register(name="example", target=Example)

        # Assert
        references = store.known_references
        self.assertIn("example", references)
        reference = references["example"]
        self.assertIs(reference.target_class, Example)
        self.assertEqual(list(reference.decisive_init_parameters.keys()), ["a", "b", "c"])
        self.assertIsInstance(reference.decisive_init_parameters, MappingProxyType)

    def test_register__TargetWithoutInitAttribute__RaisesAttributeError(self):
        # Arrange
        store = self._empty_store()

        class NoInitMeta(type):
            def __getattribute__(cls, name):
                if name == "__init__":
                    raise AttributeError
                return super().__getattribute__(name)

        class NoInit(metaclass=NoInitMeta):
            pass

        # Act & Assert
        with self.assertRaisesRegex(AttributeError, "has no '__init__'"):
            store.register(name="noinit", target=NoInit)

        self.assertEqual(len(store.known_references), 0)

    def test_register__TargetWithNonCallableInitAttribute__RaisesTypeError(self):
        # Arrange
        store = self._empty_store()

        class InitNotCallable:
            __init__ = 42  # type: ignore[assignment]

        # Act & Assert
        with self.assertRaises(TypeError):
            store.register(name="notcallable", target=InitNotCallable)

        self.assertEqual(len(store.known_references), 0)

    def test_register__NameAlreadyExists__OverridesExistingReference(self):
        # Arrange
        store = self._empty_store()

        class First:
            pass

        class Second:
            pass

        store.register(name="dup", target=First)

        # Act
        store.register(name="dup", target=Second)

        # Assert
        references = store.known_references
        self.assertEqual(len(references), 1)
        self.assertIs(references["dup"].target_class, Second)

    def test_known_references__ReturnMappingProxy__IsImmutable(self):
        # Arrange
        store = self._empty_store()

        class Example:
            def __init__(self):
                pass

        store.register(name="example", target=Example)

        # Act
        references = store.known_references

        # Assert
        self.assertIsInstance(references, MappingProxyType)
        with self.assertRaises(TypeError):
            references["new"] = object()

    def test_known_references__ReturnsSnapshot__DoesNotReflectLaterChanges(self):
        # Arrange
        store = self._empty_store()

        class Example:
            def __init__(self):
                pass

        # Get snapshot before registration
        references_before = store.known_references

        # Act
        store.register(name="example", target=Example)

        # Assert - snapshot should NOT reflect later changes (thread-safe behavior)
        self.assertNotIn("example", references_before)
        # But a new call should show the registration
        references_after = store.known_references
        self.assertIn("example", references_after)

    def test_unregister__RegisteredName__RemovesReference(self):
        # Arrange
        store = self._empty_store()

        class Example:
            pass

        store.register(name="example", target=Example)

        # Act
        store.unregister("example")

        # Assert
        self.assertNotIn("example", store.known_references)

    def test_unregister__UnknownName__RaisesKeyError(self):
        # Arrange
        store = self._empty_store()

        # Act & Assert
        with self.assertRaises(KeyError):
            store.unregister("unknown")

