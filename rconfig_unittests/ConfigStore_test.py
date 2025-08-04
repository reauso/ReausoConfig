from types import MappingProxyType
from unittest.case import TestCase

from rconfig.ConfigStore import ConfigStore


class ConfigStoreTests(TestCase):
    def _empty_store(self) -> ConfigStore:
        store = ConfigStore()
        store._known_references.clear()
        return store

    def test_register__WithTargetClass__StoreConfigReference(self):
        store = self._empty_store()

        class Example:
            def __init__(self, a, b, c=None):
                self.a = a
                self.b = b
                self.c = c

        store.register(name="example", target=Example)

        references = store.known_references
        self.assertIn("example", references)
        reference = references["example"]
        self.assertIs(reference.target_class, Example)
        self.assertEqual(list(reference.decisive_init_parameters.keys()), ["a", "b", "c"])
        self.assertIsInstance(reference.decisive_init_parameters, MappingProxyType)

    def test_register__TargetWithoutInitAttribute__RaisesAttributeError(self):
        store = self._empty_store()

        class NoInitMeta(type):
            def __getattribute__(cls, name):
                if name == "__init__":
                    raise AttributeError
                return super().__getattribute__(name)

        class NoInit(metaclass=NoInitMeta):
            pass

        with self.assertRaisesRegex(AttributeError, "has no '__init__'"):
            store.register(name="noinit", target=NoInit)

        self.assertEqual(len(store.known_references), 0)

    def test_register__TargetWithNonCallableInitAttribute__RaisesTypeError(self):
        store = self._empty_store()

        class InitNotCallable:
            __init__ = 42  # type: ignore[assignment]

        with self.assertRaises(TypeError):
            store.register(name="notcallable", target=InitNotCallable)

        self.assertEqual(len(store.known_references), 0)

    def test_register__NameAlreadyExists__OverridesExistingReference(self):
        store = self._empty_store()

        class First:
            pass

        class Second:
            pass

        store.register(name="dup", target=First)
        store.register(name="dup", target=Second)

        references = store.known_references
        self.assertEqual(len(references), 1)
        self.assertIs(references["dup"].target_class, Second)

    def test_known_references__ReturnMappingProxy__IsImmutable(self):
        store = self._empty_store()

        class Example:
            def __init__(self):
                pass

        store.register(name="example", target=Example)
        references = store.known_references

        self.assertIsInstance(references, MappingProxyType)
        with self.assertRaises(TypeError):
            references["new"] = object()

    def test_known_references__RetrievedViewReflectsRegistrations(self):
        store = self._empty_store()

        class Example:
            def __init__(self):
                pass

        references = store.known_references
        store.register(name="example", target=Example)

        self.assertIn("example", references)

