from abc import ABC, abstractmethod
from types import MappingProxyType

from rconfig.target import TargetRegistry
from rconfig_unittests.fixtures import BaseStoreTest


class TargetRegistryTests(BaseStoreTest):
    """Tests for TargetRegistry registration and lookup functionality."""

    def test_register__WithTargetClass__StoreTargetEntry(self):
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
        targets = store.known_targets
        self.assertIn("example", targets)
        entry = targets["example"]
        self.assertIs(entry.target_class, Example)
        self.assertEqual(list(entry.decisive_init_parameters.keys()), ["a", "b", "c"])
        self.assertIsInstance(entry.decisive_init_parameters, MappingProxyType)

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

        self.assertEqual(len(store.known_targets), 0)

    def test_register__TargetWithNonCallableInitAttribute__RaisesTypeError(self):
        # Arrange
        store = self._empty_store()

        class InitNotCallable:
            __init__ = 42  # type: ignore[assignment]

        # Act & Assert
        with self.assertRaises(TypeError):
            store.register(name="notcallable", target=InitNotCallable)

        self.assertEqual(len(store.known_targets), 0)

    def test_register__AbstractClass__RaisesTypeError(self):
        """Test that registering an abstract class raises TypeError."""
        # Arrange
        store = self._empty_store()

        class AbstractTarget(ABC):
            @abstractmethod
            def process(self):
                pass

        # Act & Assert
        with self.assertRaisesRegex(TypeError, "is abstract"):
            store.register(name="abstract", target=AbstractTarget)

        self.assertEqual(len(store.known_targets), 0)

    def test_register__PartiallyImplementedAbstractClass__RaisesTypeError(self):
        """Test that registering a partially implemented abstract class raises TypeError."""
        # Arrange
        store = self._empty_store()

        class Base(ABC):
            @abstractmethod
            def method1(self):
                pass

            @abstractmethod
            def method2(self):
                pass

        class Partial(Base):
            def method1(self):
                return "implemented"

        # Act & Assert
        with self.assertRaisesRegex(TypeError, "is abstract"):
            store.register(name="partial", target=Partial)

        self.assertEqual(len(store.known_targets), 0)

    def test_register__ConcreteSubclassOfAbstract__StoresTargetEntry(self):
        """Test that registering a concrete subclass of an ABC succeeds."""
        # Arrange
        store = self._empty_store()

        class Base(ABC):
            @abstractmethod
            def process(self):
                pass

        class Concrete(Base):
            def __init__(self, value):
                self.value = value

            def process(self):
                return self.value

        # Act
        store.register(name="concrete", target=Concrete)

        # Assert
        self.assertIn("concrete", store.known_targets)
        self.assertIs(store.known_targets["concrete"].target_class, Concrete)

    def test_register__NameAlreadyExists__OverridesExistingEntry(self):
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
        targets = store.known_targets
        self.assertEqual(len(targets), 1)
        self.assertIs(targets["dup"].target_class, Second)

    def test_known_targets__ReturnMappingProxy__IsImmutable(self):
        # Arrange
        store = self._empty_store()

        class Example:
            def __init__(self):
                pass

        store.register(name="example", target=Example)

        # Act
        targets = store.known_targets

        # Assert
        self.assertIsInstance(targets, MappingProxyType)
        with self.assertRaises(TypeError):
            targets["new"] = object()

    def test_known_targets__ReturnsLiveView__ReflectsLaterChanges(self):
        # Arrange
        store = self._empty_store()

        class Example:
            def __init__(self):
                pass

        # Get live view before registration
        targets = store.known_targets

        # Act
        store.register(name="example", target=Example)

        # Assert - live view DOES reflect later changes
        self.assertIn("example", targets)

    def test_unregister__RegisteredName__RemovesEntry(self):
        # Arrange
        store = self._empty_store()

        class Example:
            pass

        store.register(name="example", target=Example)

        # Act
        store.unregister("example")

        # Assert
        self.assertNotIn("example", store.known_targets)

    def test_unregister__UnknownName__RaisesKeyError(self):
        # Arrange
        store = self._empty_store()

        # Act & Assert
        with self.assertRaises(KeyError):
            store.unregister("unknown")

    # === Contains Tests ===

    def test_contains__RegisteredName__ReturnsTrue(self):
        # Arrange
        store = self._empty_store()

        class Example:
            pass

        store.register(name="example", target=Example)

        # Act & Assert
        self.assertTrue("example" in store)

    def test_contains__UnregisteredName__ReturnsFalse(self):
        # Arrange
        store = self._empty_store()

        # Act & Assert
        self.assertFalse("nonexistent" in store)

    def test_contains__AfterUnregister__ReturnsFalse(self):
        # Arrange
        store = self._empty_store()

        class Example:
            pass

        store.register(name="example", target=Example)
        store.unregister("example")

        # Act & Assert
        self.assertFalse("example" in store)
