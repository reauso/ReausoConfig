"""Tests for type_utils module."""

from abc import ABC, abstractmethod
from collections.abc import Mapping, MutableMapping, MutableSequence, Sequence
from dataclasses import dataclass
from typing import Annotated, NewType, Optional, Union
from unittest import TestCase

from rconfig.target import TargetRegistry
from rconfig._internal.type_utils import (
    TARGET_KEY,
    could_be_implicit_nested,
    extract_class_from_hint,
    extracted_container_element_type,
    find_exact_match,
    find_registered_subclasses,
    is_class_type,
    is_concrete_type,
    register_inferred_target,
    resolved_union_candidate,
    unwrapped_hint,
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

    def test_extract__NewType__ExtractsUnderlyingClass(self):
        """NewType wrapping a class extracts the underlying class."""

        class Database:
            pass

        DatabaseConfig = NewType("DatabaseConfig", Database)
        result = extract_class_from_hint(DatabaseConfig)
        self.assertIs(result, Database)

    def test_extract__NewTypePrimitive__ReturnsNone(self):
        """NewType wrapping a primitive returns None."""
        UserId = NewType("UserId", int)
        result = extract_class_from_hint(UserId)
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

    def test_couldBeImplicit__EmptyDict_ClassType__ReturnsTrue(self):
        """Empty dict without _target_ with class type returns True."""

        class MyClass:
            pass

        self.assertTrue(could_be_implicit_nested({}, MyClass))

    def test_couldBeImplicit__UnionType__ReturnsTrue(self):
        """Union type allows dict through for structural matching."""

        @dataclass
        class A:
            x: int

        @dataclass
        class B:
            y: str

        value = {"x": 42}
        self.assertTrue(could_be_implicit_nested(value, Union[A, B]))

    def test_couldBeImplicit__NewTypeClass__ReturnsTrue(self):
        """NewType wrapping a class is recognized as implicit nested."""

        class Database:
            pass

        DatabaseConfig = NewType("DatabaseConfig", Database)
        value = {"port": 5432}
        self.assertTrue(could_be_implicit_nested(value, DatabaseConfig))


class FindRegisteredSubclassesTests(TestCase):
    """Tests for find_registered_subclasses function."""

    def _empty_store(self) -> TargetRegistry:
        store = TargetRegistry()
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

    def _empty_store(self) -> TargetRegistry:
        store = TargetRegistry()
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

    def _empty_store(self) -> TargetRegistry:
        store = TargetRegistry()
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

    def test_isConcrete__ConcreteNoRegistration__ReturnsConcreteNoTarget(self):
        store = self._empty_store()

        class MyClass:
            pass

        is_concrete, target_name, matching = is_concrete_type(store, MyClass)

        self.assertTrue(is_concrete)
        self.assertIsNone(target_name)
        self.assertEqual(matching, [])
        # Pure query — NOT registered
        self.assertNotIn("myclass", store.known_targets)

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

class RegisterInferredTargetTests(TestCase):
    """Tests for register_inferred_target function."""

    def _empty_store(self) -> TargetRegistry:
        store = TargetRegistry()
        store.clear()
        return store

    def test_registerInferred__SimpleClass__RegistersLowercaseName(self):
        store = self._empty_store()

        class MyClass:
            pass

        target_name = register_inferred_target(store, MyClass)

        self.assertEqual(target_name, "myclass")
        self.assertIn("myclass", store.known_targets)

    def test_registerInferred__NameCollision__UsesFullyQualifiedName(self):
        store = self._empty_store()

        class myclass:  # noqa: N801 - lowercase intentional for test
            pass

        class OtherClass:
            pass

        store.register("myclass", OtherClass)

        target_name = register_inferred_target(store, myclass)

        self.assertIn(".", target_name)
        self.assertIn("myclass", target_name)

    def test_registerInferred__AbstractClass__RaisesValueError(self):
        store = self._empty_store()

        class AbstractBase(ABC):
            @abstractmethod
            def method(self):
                pass

        with self.assertRaises(ValueError):
            register_inferred_target(store, AbstractBase)


class UnwrappedHintTests(TestCase):
    """Tests for unwrapped_hint function."""

    def test_unwrappedHint__PlainClass__ReturnsSame(self):
        class MyClass:
            pass

        result = unwrapped_hint(MyClass)
        self.assertIs(result, MyClass)

    def test_unwrappedHint__OptionalClass__ReturnsInner(self):
        class MyClass:
            pass

        result = unwrapped_hint(Optional[MyClass])
        self.assertIs(result, MyClass)

    def test_unwrappedHint__AnnotatedClass__ReturnsInner(self):
        class MyClass:
            pass

        result = unwrapped_hint(Annotated[MyClass, "metadata"])
        self.assertIs(result, MyClass)

    def test_unwrappedHint__AnnotatedOptional__ReturnsInnermost(self):
        class MyClass:
            pass

        result = unwrapped_hint(Annotated[Optional[MyClass], "meta"])
        self.assertIs(result, MyClass)

    def test_unwrappedHint__MultiOptionUnion__ReturnsSame(self):
        class A:
            pass

        class B:
            pass

        hint = Union[A, B]
        result = unwrapped_hint(hint)
        self.assertEqual(result, hint)

    def test_unwrappedHint__PrimitiveType__ReturnsSame(self):
        result = unwrapped_hint(int)
        self.assertIs(result, int)

    def test_unwrappedHint__OptionalPrimitive__ReturnsInner(self):
        result = unwrapped_hint(Optional[int])
        self.assertIs(result, int)

    def test_unwrappedHint__NewType__UnwrapsToSupertype(self):
        """NewType is stripped to expose the underlying type."""

        class MyClass:
            pass

        MyAlias = NewType("MyAlias", MyClass)
        result = unwrapped_hint(MyAlias)
        self.assertIs(result, MyClass)

    def test_unwrappedHint__NewTypeOptional__UnwrapsRecursively(self):
        """NewType wrapping Optional composes unwrapping layers."""

        class MyClass:
            pass

        MyAlias = NewType("MyAlias", Optional[MyClass])
        result = unwrapped_hint(MyAlias)
        self.assertIs(result, MyClass)


class ExtractedContainerElementTypeTests(TestCase):
    """Tests for extracted_container_element_type function."""

    def test_extractedContainerElementType__ListWithInt__ReturnsElementType(self):
        class Item:
            pass

        result = extracted_container_element_type(list[Item], 0)
        self.assertIs(result, Item)

    def test_extractedContainerElementType__TuplePositional__ReturnsCorrectType(self):
        class A:
            pass

        class B:
            pass

        result = extracted_container_element_type(tuple[A, B], 1)
        self.assertIs(result, B)

    def test_extractedContainerElementType__TupleOutOfBounds__ReturnsNone(self):
        class A:
            pass

        result = extracted_container_element_type(tuple[A], 5)
        self.assertIsNone(result)

    def test_extractedContainerElementType__TupleVariadic__ReturnsElementType(self):
        class A:
            pass

        result = extracted_container_element_type(tuple[A, ...], 99)
        self.assertIs(result, A)

    def test_extractedContainerElementType__DictWithStr__ReturnsValueType(self):
        class Model:
            pass

        result = extracted_container_element_type(dict[str, Model], "resnet")
        self.assertIs(result, Model)

    def test_extractedContainerElementType__UnparameterizedList__ReturnsNone(self):
        result = extracted_container_element_type(list, 0)
        self.assertIsNone(result)

    def test_extractedContainerElementType__IntOnDict__ReturnsNone(self):
        result = extracted_container_element_type(dict[str, int], 0)
        self.assertIsNone(result)

    def test_extractedContainerElementType__StrOnList__ReturnsNone(self):
        result = extracted_container_element_type(list[int], "key")
        self.assertIsNone(result)

    def test_extractedContainerElementType__BareTuple__ReturnsNone(self):
        """Unparameterized tuple returns None."""
        result = extracted_container_element_type(tuple, 0)
        self.assertIsNone(result)

    def test_extractedContainerElementType__TupleNegativeIndex__ReturnsNone(self):
        """Negative index on positional tuple returns None."""

        class A:
            pass

        result = extracted_container_element_type(tuple[A], -1)
        self.assertIsNone(result)

    def test_extractedContainerElementType__Set__ReturnsElementType(self):
        """set[X] with integer index returns X."""

        class Item:
            pass

        result = extracted_container_element_type(set[Item], 0)
        self.assertIs(result, Item)

    def test_extractedContainerElementType__FrozenSet__ReturnsElementType(self):
        """frozenset[X] with integer index returns X."""

        class Item:
            pass

        result = extracted_container_element_type(frozenset[Item], 0)
        self.assertIs(result, Item)

    def test_extractedContainerElementType__BareSet__ReturnsNone(self):
        """Unparameterized set returns None."""
        result = extracted_container_element_type(set, 0)
        self.assertIsNone(result)

    def test_extractedContainerElementType__Sequence__ReturnsElementType(self):
        """Sequence[X] with integer index returns X."""

        class Item:
            pass

        result = extracted_container_element_type(Sequence[Item], 0)
        self.assertIs(result, Item)

    def test_extractedContainerElementType__MutableSequence__ReturnsElementType(self):
        """MutableSequence[X] with integer index returns X."""

        class Item:
            pass

        result = extracted_container_element_type(MutableSequence[Item], 0)
        self.assertIs(result, Item)

    def test_extractedContainerElementType__Mapping__ReturnsValueType(self):
        """Mapping[K, V] with string key returns V."""

        class Model:
            pass

        result = extracted_container_element_type(Mapping[str, Model], "resnet")
        self.assertIs(result, Model)

    def test_extractedContainerElementType__MutableMapping__ReturnsValueType(self):
        """MutableMapping[K, V] with string key returns V."""

        class Model:
            pass

        result = extracted_container_element_type(MutableMapping[str, Model], "key")
        self.assertIs(result, Model)


class ResolvedUnionCandidateTests(TestCase):
    """Tests for resolved_union_candidate function."""

    def _empty_store(self) -> TargetRegistry:
        store = TargetRegistry()
        store.clear()
        return store

    def test_resolvedUnionCandidate__UniqueFieldMatch__ReturnsSingleCandidate(self):
        store = self._empty_store()

        @dataclass
        class Encoder:
            hidden_size: int
            num_layers: int

        @dataclass
        class Decoder:
            hidden_size: int
            output_vocab: int

        config = {"hidden_size": 256, "num_layers": 4}
        result = resolved_union_candidate(Union[Encoder, Decoder], config, store)
        self.assertIs(result, Encoder)

    def test_resolvedUnionCandidate__AmbiguousCandidates__ReturnsNone(self):
        store = self._empty_store()

        @dataclass
        class Encoder:
            hidden_size: int = 256

        @dataclass
        class Decoder:
            hidden_size: int = 128

        config = {"hidden_size": 256}
        result = resolved_union_candidate(Union[Encoder, Decoder], config, store)
        self.assertIsNone(result)

    def test_resolvedUnionCandidate__NoCandidatesMatch__ReturnsNone(self):
        store = self._empty_store()

        @dataclass
        class Encoder:
            hidden_size: int

        @dataclass
        class Decoder:
            output_vocab: int

        config = {"unknown_field": 42}
        result = resolved_union_candidate(Union[Encoder, Decoder], config, store)
        self.assertIsNone(result)

    def test_resolvedUnionCandidate__AbstractMember__ExpandsToConcreteSubclasses(self):
        store = self._empty_store()

        class BaseEncoder(ABC):
            @abstractmethod
            def encode(self):
                pass

        @dataclass
        class ConcreteEncoder(BaseEncoder):
            hidden_size: int

            def encode(self):
                pass

        @dataclass
        class Decoder:
            output_vocab: int

        config = {"hidden_size": 256}
        result = resolved_union_candidate(Union[BaseEncoder, Decoder], config, store)
        self.assertIs(result, ConcreteEncoder)

    def test_resolvedUnionCandidate__KwargsClass__AcceptsAnyKeys(self):
        store = self._empty_store()

        class FlexibleClass:
            def __init__(self, **kwargs):
                pass

        @dataclass
        class StrictClass:
            specific_field: int

        # Config has "any_field" which StrictClass doesn't have
        # FlexibleClass accepts anything via **kwargs
        config = {"any_field": 42}
        result = resolved_union_candidate(Union[FlexibleClass, StrictClass], config, store)
        self.assertIs(result, FlexibleClass)

    def test_resolvedUnionCandidate__EmptyConfig__AllDefaultsAmbiguous(self):
        store = self._empty_store()

        @dataclass
        class A:
            x: int = 1

        @dataclass
        class B:
            y: int = 2

        config = {}
        result = resolved_union_candidate(Union[A, B], config, store)
        self.assertIsNone(result)  # Both match empty config

    def test_resolvedUnionCandidate__RequiredFieldMissing__DisqualifiesCandidate(self):
        store = self._empty_store()

        @dataclass
        class A:
            required_field: int

        @dataclass
        class B:
            optional_field: int = 10

        config = {}  # A requires required_field, B has all defaults
        result = resolved_union_candidate(Union[A, B], config, store)
        self.assertIs(result, B)

    def test_resolvedUnionCandidate__UnknownKeyInConfig__DisqualifiesCandidate(self):
        store = self._empty_store()

        @dataclass
        class A:
            x: int

        @dataclass
        class B:
            x: int
            y: int

        config = {"x": 1, "y": 2}  # A doesn't have 'y'
        result = resolved_union_candidate(Union[A, B], config, store)
        self.assertIs(result, B)

    def test_resolvedUnionCandidate__TypeIncompatibleValue__DisqualifiesCandidate(self):
        store = self._empty_store()

        @dataclass
        class A:
            value: int

        @dataclass
        class B:
            value: str

        config = {"value": "hello"}
        result = resolved_union_candidate(Union[A, B], config, store)
        self.assertIs(result, B)

    def test_resolvedUnionCandidate__OptionalUnion__IgnoresNoneType(self):
        store = self._empty_store()

        @dataclass
        class A:
            x: int

        @dataclass
        class B:
            y: str

        # Optional[Union[A, B]] is Union[A, B, None]
        config = {"x": 42}
        result = resolved_union_candidate(Union[A, B, None], config, store)
        self.assertIs(result, A)

    def test_resolvedUnionCandidate__NotAUnion__ReturnsNone(self):
        store = self._empty_store()

        class MyClass:
            pass

        result = resolved_union_candidate(MyClass, {"x": 1}, store)
        self.assertIsNone(result)

    def test_resolvedUnionCandidate__CandidateWithVarPositional__SkipsVarParams(self):
        """Class with *args doesn't require positional params from config."""
        store = self._empty_store()

        class FlexClass:
            def __init__(self, name: str, *args):
                self.name = name

        @dataclass
        class StrictClass:
            value: int

        config = {"name": "test"}
        result = resolved_union_candidate(Union[FlexClass, StrictClass], config, store)
        self.assertIs(result, FlexClass)

    def test_resolvedUnionCandidate__AllAbstractNoSubclasses__ReturnsNone(self):
        """Union of only abstract types with no concrete subclasses returns None."""
        store = self._empty_store()

        class AbstractA(ABC):
            @abstractmethod
            def method_a(self):
                pass

        class AbstractB(ABC):
            @abstractmethod
            def method_b(self):
                pass

        config = {"x": 1}
        result = resolved_union_candidate(Union[AbstractA, AbstractB], config, store)
        self.assertIsNone(result)

    def test_resolvedUnionCandidate__ConfigWithNoneValue__StillMatches(self):
        """None values in config are always type-compatible."""
        store = self._empty_store()

        @dataclass
        class A:
            x: int
            y: str = "default"

        @dataclass
        class B:
            z: float

        config = {"x": None}
        result = resolved_union_candidate(Union[A, B], config, store)
        self.assertIs(result, A)

    def test_resolvedUnionCandidate__BoolVsIntCompatibility__BothMatch(self):
        """Bool is subclass of int — candidates with int fields match bool values."""
        store = self._empty_store()

        @dataclass
        class A:
            flag: int

        @dataclass
        class B:
            flag: str

        config = {"flag": True}
        result = resolved_union_candidate(Union[A, B], config, store)
        self.assertIs(result, A)


class ValueIsTypeCompatibleTests(TestCase):
    """Tests for _value_is_type_compatible private function."""

    def test_valueIsTypeCompatible__ListValueWithTupleExpected__ReturnsTrue(self):
        """List values are compatible with tuple expected types."""
        from rconfig._internal.type_utils import _value_is_type_compatible

        self.assertTrue(_value_is_type_compatible([1, 2], tuple[int, ...]))

    def test_valueIsTypeCompatible__ListValueWithDictExpected__ReturnsFalse(self):
        """List values are not compatible with dict expected types."""
        from rconfig._internal.type_utils import _value_is_type_compatible

        self.assertFalse(_value_is_type_compatible([1, 2], dict[str, int]))
