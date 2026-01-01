"""Tests for type_utils module."""

from abc import ABC, abstractmethod
from typing import Optional, Union
from unittest import TestCase

from rconfig.ConfigStore import ConfigStore
from rconfig.type_utils import (
    TARGET_KEY,
    could_be_implicit_nested,
    extract_class_from_hint,
    find_exact_match,
    find_registered_subclasses,
    is_class_type,
    is_concrete_type,
)


class IsClassTypeTests(TestCase):
    """Tests for is_class_type function."""

    def test_isClassType__PrimitiveInt__ReturnsFalse(self):
        self.assertFalse(is_class_type(int))

    def test_isClassType__PrimitiveStr__ReturnsFalse(self):
        self.assertFalse(is_class_type(str))

    def test_isClassType__PrimitiveFloat__ReturnsFalse(self):
        self.assertFalse(is_class_type(float))

    def test_isClassType__PrimitiveBool__ReturnsFalse(self):
        self.assertFalse(is_class_type(bool))

    def test_isClassType__PrimitiveBytes__ReturnsFalse(self):
        self.assertFalse(is_class_type(bytes))

    def test_isClassType__NoneType__ReturnsFalse(self):
        self.assertFalse(is_class_type(type(None)))

    def test_isClassType__BuiltinList__ReturnsFalse(self):
        self.assertFalse(is_class_type(list))

    def test_isClassType__BuiltinDict__ReturnsFalse(self):
        self.assertFalse(is_class_type(dict))

    def test_isClassType__BuiltinSet__ReturnsFalse(self):
        self.assertFalse(is_class_type(set))

    def test_isClassType__BuiltinTuple__ReturnsFalse(self):
        self.assertFalse(is_class_type(tuple))

    def test_isClassType__GenericList__ReturnsFalse(self):
        self.assertFalse(is_class_type(list[int]))

    def test_isClassType__GenericDict__ReturnsFalse(self):
        self.assertFalse(is_class_type(dict[str, int]))

    def test_isClassType__OptionalType__ReturnsFalse(self):
        self.assertFalse(is_class_type(Optional[int]))

    def test_isClassType__UnionType__ReturnsFalse(self):
        self.assertFalse(is_class_type(Union[int, str]))

    def test_isClassType__CustomClass__ReturnsTrue(self):
        class MyClass:
            pass

        self.assertTrue(is_class_type(MyClass))

    def test_isClassType__AbstractClass__ReturnsTrue(self):
        class AbstractClass(ABC):
            @abstractmethod
            def method(self):
                pass

        self.assertTrue(is_class_type(AbstractClass))


class ExtractClassFromHintTests(TestCase):
    """Tests for extract_class_from_hint function."""

    def test_extract__PlainClass__ReturnsClass(self):
        class MyClass:
            pass

        result = extract_class_from_hint(MyClass)
        self.assertIs(result, MyClass)

    def test_extract__OptionalClass__ReturnsInnerClass(self):
        class MyClass:
            pass

        result = extract_class_from_hint(Optional[MyClass])
        self.assertIs(result, MyClass)

    def test_extract__UnionWithNone__ReturnsNonNoneType(self):
        class MyClass:
            pass

        result = extract_class_from_hint(Union[MyClass, None])
        self.assertIs(result, MyClass)

    def test_extract__UnionMultipleTypes__ReturnsNone(self):
        class ClassA:
            pass

        class ClassB:
            pass

        result = extract_class_from_hint(Union[ClassA, ClassB])
        self.assertIsNone(result)

    def test_extract__PrimitiveType__ReturnsNone(self):
        result = extract_class_from_hint(int)
        self.assertIsNone(result)

    def test_extract__OptionalPrimitive__ReturnsNone(self):
        result = extract_class_from_hint(Optional[int])
        self.assertIsNone(result)

    def test_extract__GenericList__ReturnsNone(self):
        result = extract_class_from_hint(list[int])
        self.assertIsNone(result)


class CouldBeImplicitNestedTests(TestCase):
    """Tests for could_be_implicit_nested function."""

    def test_couldBeImplicit__DictWithoutTarget_ClassType__ReturnsTrue(self):
        class MyClass:
            pass

        value = {"field": "value"}
        self.assertTrue(could_be_implicit_nested(value, MyClass))

    def test_couldBeImplicit__DictWithTarget__ReturnsFalse(self):
        class MyClass:
            pass

        value = {TARGET_KEY: "target", "field": "value"}
        self.assertFalse(could_be_implicit_nested(value, MyClass))

    def test_couldBeImplicit__NonDict__ReturnsFalse(self):
        class MyClass:
            pass

        self.assertFalse(could_be_implicit_nested("string", MyClass))
        self.assertFalse(could_be_implicit_nested(123, MyClass))
        self.assertFalse(could_be_implicit_nested([1, 2, 3], MyClass))

    def test_couldBeImplicit__NoneExpectedType__ReturnsFalse(self):
        value = {"field": "value"}
        self.assertFalse(could_be_implicit_nested(value, None))

    def test_couldBeImplicit__PrimitiveExpectedType__ReturnsFalse(self):
        value = {"field": "value"}
        self.assertFalse(could_be_implicit_nested(value, int))
        self.assertFalse(could_be_implicit_nested(value, str))

    def test_couldBeImplicit__OptionalClassType__ReturnsTrue(self):
        class MyClass:
            pass

        value = {"field": "value"}
        self.assertTrue(could_be_implicit_nested(value, Optional[MyClass]))


class FindRegisteredSubclassesTests(TestCase):
    """Tests for find_registered_subclasses function."""

    def _empty_store(self) -> ConfigStore:
        store = ConfigStore()
        store.clear()
        return store

    def test_findSubclasses__NoRegisteredTargets__ReturnsEmptyList(self):
        store = self._empty_store()

        class Base:
            pass

        result = find_registered_subclasses(store, Base)
        self.assertEqual(result, [])

    def test_findSubclasses__ExactMatchRegistered__ReturnsMatch(self):
        store = self._empty_store()

        class Base:
            pass

        store.register("base", Base)
        result = find_registered_subclasses(store, Base)
        self.assertEqual(result, ["base"])

    def test_findSubclasses__SubclassRegistered__ReturnsSubclass(self):
        store = self._empty_store()

        class Base:
            pass

        class Derived(Base):
            pass

        store.register("derived", Derived)
        result = find_registered_subclasses(store, Base)
        self.assertEqual(result, ["derived"])

    def test_findSubclasses__MultipleSubclasses__ReturnsAll(self):
        store = self._empty_store()

        class Base:
            pass

        class DerivedA(Base):
            pass

        class DerivedB(Base):
            pass

        store.register("a", DerivedA)
        store.register("b", DerivedB)

        result = find_registered_subclasses(store, Base)
        self.assertEqual(sorted(result), ["a", "b"])

    def test_findSubclasses__UnrelatedClass__ReturnsEmpty(self):
        store = self._empty_store()

        class Base:
            pass

        class Unrelated:
            pass

        store.register("unrelated", Unrelated)
        result = find_registered_subclasses(store, Base)
        self.assertEqual(result, [])


class FindExactMatchTests(TestCase):
    """Tests for find_exact_match function."""

    def _empty_store(self) -> ConfigStore:
        store = ConfigStore()
        store.clear()
        return store

    def test_findExact__NoRegisteredTargets__ReturnsNone(self):
        store = self._empty_store()

        class MyClass:
            pass

        result = find_exact_match(store, MyClass)
        self.assertIsNone(result)

    def test_findExact__ExactMatchExists__ReturnsName(self):
        store = self._empty_store()

        class MyClass:
            pass

        store.register("myclass", MyClass)
        result = find_exact_match(store, MyClass)
        self.assertEqual(result, "myclass")

    def test_findExact__OnlySubclassRegistered__ReturnsNone(self):
        store = self._empty_store()

        class Base:
            pass

        class Derived(Base):
            pass

        store.register("derived", Derived)
        result = find_exact_match(store, Base)
        self.assertIsNone(result)


class IsConcreteTypeTests(TestCase):
    """Tests for is_concrete_type function."""

    def _empty_store(self) -> ConfigStore:
        store = ConfigStore()
        store.clear()
        return store

    def test_isConcrete__AbstractClass__ReturnsFalseWithSubclasses(self):
        store = self._empty_store()

        class AbstractBase(ABC):
            @abstractmethod
            def method(self):
                pass

        class Concrete(AbstractBase):
            def method(self):
                pass

        store.register("concrete", Concrete)

        is_concrete, target_name, matching = is_concrete_type(store, AbstractBase)

        self.assertFalse(is_concrete)
        self.assertIsNone(target_name)
        self.assertIn("concrete", matching)

    def test_isConcrete__ConcreteWithExactMatch__ReturnsTrue(self):
        store = self._empty_store()

        class MyClass:
            pass

        store.register("myclass", MyClass)

        is_concrete, target_name, matching = is_concrete_type(store, MyClass)

        self.assertTrue(is_concrete)
        self.assertEqual(target_name, "myclass")
        self.assertEqual(matching, ["myclass"])

    def test_isConcrete__ConcreteNoRegistration__AutoRegisters(self):
        store = self._empty_store()

        class MyClass:
            pass

        is_concrete, target_name, matching = is_concrete_type(store, MyClass)

        self.assertTrue(is_concrete)
        self.assertEqual(target_name, "myclass")
        self.assertIn("myclass", matching)
        # Verify it was actually registered
        self.assertIn("myclass", store.known_references)

    def test_isConcrete__ConcreteWithSubclasses__ReturnsFalse(self):
        store = self._empty_store()

        class Base:
            pass

        class Derived(Base):
            pass

        store.register("base", Base)
        store.register("derived", Derived)

        is_concrete, target_name, matching = is_concrete_type(store, Base)

        self.assertFalse(is_concrete)
        self.assertIsNone(target_name)
        self.assertEqual(sorted(matching), ["base", "derived"])

    def test_isConcrete__AutoRegisterNameCollision__UsesFullyQualifiedName(self):
        store = self._empty_store()

        class myclass:  # noqa: N801 - lowercase intentional for test
            pass

        # Pre-register a different class with the same lowercase name
        class OtherClass:
            pass

        store.register("myclass", OtherClass)

        is_concrete, target_name, matching = is_concrete_type(store, myclass)

        self.assertTrue(is_concrete)
        # Should use fully qualified name due to collision
        self.assertIn(".", target_name)
        self.assertIn("myclass", target_name)
