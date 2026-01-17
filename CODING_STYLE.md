# Coding Style Guide

This guide documents the coding conventions for this project, derived from:

- **Clean Code** by Robert C. Martin
- **Clean Architecture** by Robert C. Martin
- **The Art of Unit Testing** by Roy Osherove
- **SOLID Principles**

---

## Table of Contents

1. [Python Naming Conventions (PEP 8)](#python-naming-conventions-pep-8)
2. [SOLID Principles](#solid-principles)
3. [Method Naming Conventions](#method-naming-conventions)
4. [Class Design](#class-design)
5. [Code Hygiene](#code-hygiene)
6. [Error Handling](#error-handling)
7. [Unit Tests](#unit-tests)
8. [Integration Tests](#integration-tests)

---

## Python Naming Conventions (PEP 8)

This project follows PEP 8, Python's official style guide. Key conventions:

### File and Module Names

Use **lowercase with underscores** (snake_case):

```python
# Good
target_registry.py
config_loader.py
type_utils.py

# Bad
TargetRegistry.py
ConfigLoader.py
TypeUtils.py
```

**Why:** Python modules are typically imported by name. Lowercase names are easier to type and avoid confusion with class names.

### Package Names

Use **short, lowercase names** without underscores if possible:

```python
# Good
rconfig/target/
rconfig/validation/

# Acceptable (when needed for clarity)
rconfig/type_utils/
```

### Class Names

Use **PascalCase** (CapWords):

```python
# Good
class TargetRegistry: ...
class ConfigValidator: ...

# Bad
class target_registry: ...
class config_validator: ...
```

### Function and Variable Names

Use **lowercase with underscores** (snake_case):

```python
# Good
def validate_config(): ...
target_name = "model"

# Bad
def validateConfig(): ...
targetName = "model"
```

### Constants

Use **UPPERCASE with underscores**:

```python
# Good
MAX_RETRIES = 3
DEFAULT_TIMEOUT = 30

# Bad
maxRetries = 3
default_timeout = 30
```

### Private Members

Prefix with a single underscore:

```python
# Good - internal use only
self._known_targets = {}
def _validate_type(self): ...

# Convention - "name mangling" (rarely needed)
self.__private = value
```

### Summary Table

| Element | Convention | Example |
|---------|------------|---------|
| Module/File | snake_case | `target_registry.py` |
| Package | lowercase | `rconfig/target/` |
| Class | PascalCase | `TargetRegistry` |
| Function | snake_case | `validate_config()` |
| Variable | snake_case | `target_name` |
| Constant | UPPER_SNAKE | `MAX_RETRIES` |
| Private | `_prefix` | `_internal_method()` |

---

## SOLID Principles

Keep these principles in mind when designing and implementing code.

### Single Responsibility Principle (SRP)

Each class should have one, and only one, reason to change.

```python
# Good - Each class has a single responsibility
class TargetRegistry:
    """Only manages registration and lookup of config references."""

class ConfigValidator:
    """Only validates configurations."""

class ConfigInstantiator:
    """Only instantiates objects from configurations."""
```

### Open/Closed Principle (OCP)

Classes should be open for extension but closed for modification.

```python
# Good - Extensible through registration, not modification
class TargetRegistry:
    def register(self, name: str, target: type) -> None:
        """Extend behavior by registering new targets."""
```

**Use `singledispatchmethod` for extensibility:**

```python
from functools import singledispatchmethod

class CardCollection:
    @singledispatchmethod
    def filter(self, attribute_value) -> Self:
        """Base method raises TypeError for unsupported types."""
        message = f"Invalid value type '{type(attribute_value)}'"
        raise TypeError(message)

    @filter.register
    def _(self, attribute_value: CardType) -> Self:
        """Filter by card type - extends without modifying base."""
        return self.__class__([card for card in self if card.card_type == attribute_value])

    @filter.register
    def _(self, attribute_value: FactionType) -> Self:
        """Filter by faction type - extends without modifying base."""
        return self.__class__([card for card in self if card.faction_type == attribute_value])
```

This pattern allows adding new filter types without changing existing code. Always consider `singledispatchmethod` when you need type-based polymorphism.

### Liskov Substitution Principle (LSP)

Subtypes must be substitutable for their base types.

```python
# Good - All ValidationError subtypes can be used where ValidationError is expected
class ValidationError(ConfigError): ...
class MissingFieldError(ValidationError): ...
class TypeMismatchError(ValidationError): ...
```

### Interface Segregation Principle (ISP)

Clients should not be forced to depend on interfaces they don't use.

```python
# Good - Return read-only views instead of full mutable objects
@property
def known_targets(self) -> MappingProxyType[str, TargetEntry]:
    """Clients only need to read, not modify."""
    return MappingProxyType(self._known_targets)
```

### Dependency Inversion Principle (DIP)

Depend on abstractions, not concretions. Inject dependencies via constructor.

```python
# Good - Dependencies injected, easy to test with mocks
class ConfigInstantiator:
    def __init__(self, store: TargetRegistry, validator: ConfigValidator) -> None:
        self._store = store
        self._validator = validator
```

---

## Method Naming Conventions

Method names should clearly communicate their purpose.

### Methods That Return Values

The name should describe **what is returned**, not the process.

#### Noun-based Names

Use for methods that collect, find, or retrieve existing things:

```python
# Good - describes what is returned
def _type_errors() -> list[ValidationError]: ...
def _missing_field_errors() -> list[MissingFieldError]: ...
def _target_not_found_error() -> TargetNotFoundError | None: ...

# Bad - describes the process
def _validate_types() -> list[ValidationError]: ...
def _check_required_fields() -> list[MissingFieldError]: ...
```

#### Past Participle Names

Use for methods that transform or produce something new:

```python
# Good - indicates transformation occurred
def _processed_arguments() -> dict[str, Any]: ...
def _instantiated_value() -> Any: ...
def _resolved_dict() -> dict[str, Any]: ...

# Bad - describes the action
def _process_arguments() -> dict[str, Any]: ...
def _walk_dict() -> dict[str, Any]: ...
```

### Methods That Perform Actions (No Return Value)

Use **imperative verbs**:

```python
def register(self, name: str, target: type) -> None: ...
def clear_cache() -> None: ...
```

### Validation Methods That Raise Exceptions

Methods that validate and raise exceptions on failure should use the imperative verb `validate_`:

```python
# Good - imperative verb, raises exception on failure
def _validate_reputation(self) -> None:
    """Validate reputation and raise ValueError if invalid."""
    if self.card_type in types_with_reputation and self.reputation is None:
        raise ValueError("Expected reputation")

def _validate_faction_type(self) -> None:
    """Validate faction type and raise ValueError if invalid."""
    if self.card_type == CardType.FACTION and self.faction_type is None:
        raise ValueError("Expected faction_type")
```

**Note:** This is distinct from methods that *collect* errors for accumulation:

```python
# Different pattern - returns errors for accumulation
def _type_errors(self) -> list[ValidationError]:
    """Collect and return type validation errors."""
    errors = []
    # ... collect errors ...
    return errors
```

**When to use each:**
- Use `validate_*()` (raises) for fail-fast validation in `__post_init__`
- Use `*_errors()` (returns) for error accumulation in validation scenarios

### Boolean-Returning Methods

Use predicates that read naturally as questions:

```python
# Good
def _is_nested_config(self, value: Any) -> bool: ...
def _type_matches(self, value: Any, expected_type: type) -> bool: ...

# Bad
def _validate(self) -> bool: ...
def _check_errors(self) -> bool: ...
```

### Summary Table

| Returns             | Naming Pattern                              | Example                       |
| ------------------- | ------------------------------------------- | ----------------------------- |
| Collection of items | Noun (plural)                               | `_type_errors()`            |
| Single item or None | Noun (singular)                             | `_target_not_found_error()` |
| Transformed data    | Past participle                             | `_resolved_config()`        |
| Boolean             | Predicate (`is_`, `has_`, `_matches`) | `_is_valid()`               |
| Nothing (void)      | Imperative verb                             | `register()`                |

---

## Class Design

### Method Organization

Organize methods in this order:

1. Special methods (`__init__`, `__post_init__`, etc.)
2. Properties (`@property`)
3. Public methods (API)
4. Private helper methods (prefixed with `_`)

### Immutable Data Structures

Use frozen dataclasses for value objects:

```python
@dataclass(frozen=True, kw_only=True)
class TargetEntry:
    """Immutable reference to a configuration class."""
    name: str
    target_class: type[Any]
```

### Read-Only Views

Return immutable data structures to prevent mutation. The key requirement is **immutability**, not a specific type:

- For dictionaries: Use `MappingProxyType`
- For lists: Use `tuple` (tuples are immutable and therefore read-only)
- For sets: Use `frozenset`

```python
# Good - tuple is immutable
@property
def cards(self) -> tuple[Card, ...]:
    return tuple(self._cards)

# Good - MappingProxyType for dict
@property
def known_targets(self) -> MappingProxyType[str, TargetEntry]:
    return MappingProxyType(self._known_targets)

# Good - frozenset is immutable
@property
def tags(self) -> frozenset[str]:
    return frozenset(self._tags)
```

### Type Hints

Use modern Python 3.9+ type hint syntax:

| Old Style (typing module) | Modern Style (built-in) |
| ------------------------- | ----------------------- |
| `Type[X]`               | `type[X]`             |
| `Optional[X]`           | `X \| None`            |
| `List[X]`               | `list[X]`             |
| `Dict[K, V]`            | `dict[K, V]`          |
| `Tuple[X, Y]`           | `tuple[X, Y]`         |
| `Set[X]`                | `set[X]`              |

---

## Separation of Concerns: Construction and Public APIs

### Factory Pattern for Complex Construction

Use factory classes to separate object construction from business logic. Factories handle the complexity of creating objects, allowing domain classes to focus on their core responsibilities.

**When to use factories:**
- Objects require complex initialization or validation
- Construction involves data transformation (e.g., JSON → domain objects)
- Multiple construction methods are needed (from file, from dict, etc.)
- Dependencies need to be injected

**Example from this codebase:**

```python
# Good - Factory handles complex construction
class CardFactory:
    def __init__(self, effect_factory: EffectFactory) -> None:
        self._effect_factory = effect_factory

    def from_json_dict(self, data: dict) -> Card:
        # Normalize data
        data = {key.lower(): value for key, value in data.items()}

        # Transform types
        data['card_type'] = CardType(data['card_type'].lower())

        # Conditional field handling
        if 'reputation' in data:
            data['reputation'] = Reputation(data['reputation'].lower())

        # Delegate to nested factory
        data['effect'] = self._effect_factory.from_json_list(data=data['effect'])

        # Simple construction at the end
        return Card(**data)
```

**Domain class stays focused:**

```python
# Good - Card focuses on validation, not construction
@dataclass(kw_only=True, frozen=True)
class Card:
    card_type: CardType
    name: str
    base_value: int
    effect: Effect
    reputation: Reputation | None = None
    faction_type: FactionType | None = None

    def __post_init__(self):
        # Only validation logic here, not construction
        self._validate_reputation()
        self._validate_faction_type()
```

**Factory chains support Dependency Inversion:**

```python
# Good - Dependencies injected through constructors
effect_factory = EffectFactory()
card_factory = CardFactory(effect_factory)
deck_factory = CardDeckFactory(card_factory)
```

**When NOT to use factories:**
- Simple objects with no transformation logic
- Objects that are straightforward to construct directly
- When the constructor is already simple and clear

### Facade Pattern for Module APIs

Expose a public API through module `__init__.py` files to provide a single import location, hide internal implementation details, and enable loose coupling.

**When to use facades:**
- Modules with multiple internal files
- Clear distinction between public API and internal implementation
- Users would otherwise need to know the directory structure
- You want to enable refactoring without breaking external code

**Before (fragmented imports):**

```python
# Bad - Users must know internal structure
from n7tactics.gameobjects.card_collection import CardDeckFactory
from n7tactics.gameobjects.cards import CardFactory
from n7tactics.gameobjects.effects import EffectFactory
from n7tactics.gameobjects.effects.evaluator import LarkEffectEvaluator  # Deep import
from n7tactics.gameobjects.hand import HandCards
```

**After (facade pattern):**

```python
# Good - Single import location with clear public API
from n7tactics.gameobjects import (
    CardDeckFactory,
    CardFactory,
    EffectFactory,
    LarkEffectEvaluator,
    HandCards
)
```

**Example facade implementation:**

```python
# n7tactics/gameobjects/__init__.py
"""Public API for game objects."""

# Core data classes
from .cards import Card, CardFactory, CardType, FactionType, Reputation, WeaponType
from .card_collection import CardCollection, CardDeck, CardDeckFactory
from .hand import HandCards

# Effects (re-exported from effects module)
from .effects import Effect, SubEffect, SubEffectType, EffectFactory, LarkEffectEvaluator

__all__ = [
    # Cards
    'Card', 'CardFactory', 'CardType', 'FactionType', 'Reputation', 'WeaponType',
    # Collections
    'CardCollection', 'CardDeck', 'CardDeckFactory',
    'HandCards',
    # Effects
    'Effect', 'SubEffect', 'SubEffectType', 'EffectFactory', 'LarkEffectEvaluator',
]
```

**Benefits:**
- **Discoverability**: Users know where to find the public API
- **Loose coupling**: Internal refactoring doesn't break external code
- **Reduced cognitive load**: One import location instead of memorizing directory structure
- **Clear boundaries**: Distinguishes public API from internal implementation

**When NOT to use facades:**
- Single-file modules
- Internal packages not meant for external use
- When every class is part of the public API anyway

**Connection to SOLID:**
- Supports **Interface Segregation Principle** by exposing only what clients need
- Enables **Dependency Inversion** by providing stable abstractions
- Maintains **Single Responsibility** by keeping API concerns separate from implementation

---

## Code Hygiene

### Avoid Dead Code

Remove code that is not used. Dead code creates confusion and maintenance burden.

### Helper Function Guidelines

- **Inline** helpers that are used only once and are short (< 5 lines)
- **Extract** helpers when logic is reused in multiple places
- **Extract** helpers when the logic is complex enough to benefit from a descriptive name

### Use Extension Points

When providing extensibility APIs (like custom loaders), ensure they are actually used in the main code path:

```python
# Bad - registry exists but main code bypasses it
_yaml_loader = YamlConfigLoader()

def _load_file(path: Path) -> dict:
    return _yaml_loader.load(path)  # Custom loaders never used!

# Good - use the registry so extensions work
def _load_file(path: Path) -> dict:
    loader = get_loader(path)  # Respects registered loaders
    return loader.load(path)
```

### No Scratch Files in Repository

Development scratch files, debug scripts, and temporary code should not be committed:

- Use `.gitignore` for local scratch files
- Keep experiments in separate branches
- Remove `print()` debugging statements before committing

---

## Code Quality Examples

This section documents excellent patterns found in this codebase that should be followed.

### Frozen Dataclasses for Immutability

```python
@dataclass(kw_only=True, frozen=True)
class Card:
    """Immutable card representation with keyword-only arguments."""
    card_type: CardType
    name: str
    base_value: int
    effect: Effect
    reputation: Reputation | None = None
```

**Why this is excellent:**
- `frozen=True` ensures immutability after creation
- `kw_only=True` forces explicit field names at call sites (better readability)
- Comprehensive type hints

### Singledispatch for Type-Based Polymorphism

```python
from functools import singledispatchmethod

class CardCollection:
    @singledispatchmethod
    def filter(self, attribute_value) -> Self:
        raise TypeError(f"Invalid type: {type(attribute_value)}")

    @filter.register
    def _(self, attribute_value: CardType) -> Self:
        return self.__class__([card for card in self if card.card_type == attribute_value])
```

**Why this is excellent:**
- Open/Closed Principle - extend without modifying base
- Type-safe dispatch
- Clear error for unsupported types

### Guard Clauses for Readability

```python
def _implicit_nested_errors(self, value: dict, expected_type: type) -> list[ValidationError]:
    class_type = extract_class_from_hint(expected_type)

    # Guard clause - early return reduces nesting
    if class_type is None:
        return []

    # Main logic continues with minimal nesting
    # ...
```

**Why this is excellent:**
- Reduces cognitive complexity
- Happy path is not buried in nesting
- Makes preconditions explicit

---

## Error Handling

### Fail Fast (Default Approach)

For most code, fail immediately when an error is detected. This makes debugging easier and prevents cascading failures.

```python
# Good - Fail fast with guard clauses
def instantiate(self, config: dict[str, Any]) -> Any:
    if TARGET_KEY not in config:
        raise MissingFieldError(TARGET_KEY, "(root)")

    target_name = config[TARGET_KEY]
    if target_name not in self._store.known_targets:
        raise TargetNotFoundError(target_name)

    # Happy path continues here
    ...
```

### Error Accumulation (Validation Only)

**Exception:** When validating configuration structure, accumulate all errors to give users complete feedback in one pass.

```python
# Good - Accumulate errors only for validation
def validate(self, config: dict[str, Any]) -> ValidationResult:
    errors: list[ValidationError] = []

    # Collect all validation errors
    errors.extend(self._missing_field_errors(config, reference))
    errors.extend(self._type_errors(config, reference))

    return ValidationResult(valid=len(errors) == 0, errors=errors)
```

### Guard Clauses

Prefer guard clauses (early returns) over nested conditionals:

```python
# Good - Guard clauses reduce nesting
def _implicit_nested_errors(self, value: dict, expected_type: type) -> list[ValidationError]:
    class_type = extract_class_from_hint(expected_type)

    if class_type is None:
        return []

    # Main logic here with reduced nesting
    ...

# Bad - Deep nesting
def _implicit_nested_errors(self, value: dict, expected_type: type) -> list[ValidationError]:
    class_type = extract_class_from_hint(expected_type)

    if class_type is not None:
        # Main logic buried in nesting
        ...
```

### Custom Exceptions

**Prefer built-in exceptions when they accurately represent the error:**

- `ValueError` - invalid value for the type
- `TypeError` - wrong type passed
- `KeyError` - missing dictionary key
- `AttributeError` - missing attribute
- `IndexError` - index out of range

**Create custom exceptions when you need:**
- Domain-specific error handling (catch specific business logic errors)
- Rich structured context beyond a message string
- Error hierarchies for granular exception handling

```python
# Good - ValueError is appropriate for card validation
def _validate_reputation(self):
    if self.card_type in types_with_reputation and self.reputation is None:
        raise ValueError(f"Card type {self.card_type} requires reputation")

# Good - Custom exception when you need structured context for caller
class CircularReferenceError(Exception):
    """Raised when circular references detected in config chain."""
    def __init__(self, reference_chain: list[str]):
        self.reference_chain = reference_chain
        chain_str = " -> ".join(reference_chain)
        super().__init__(f"Circular reference detected: {chain_str}")

# Good - Custom exception with rich context
class TypeMismatchError(ValidationError):
    """Raised when a config value doesn't match the expected type."""

    def __init__(
        self,
        field: str,
        expected: type | str,
        actual: type,
        config_path: str = "",
    ) -> None:
        self.field = field
        self.expected = expected
        self.actual = actual
        super().__init__(
            f"Type mismatch for field '{field}': expected {expected}, got {actual.__name__}",
            config_path,
        )
```

Only create custom exceptions where they provide clear value.

---

## Unit Tests

Based on **The Art of Unit Testing** by Roy Osherove.

### Test Naming Convention

Use the descriptive naming pattern:

```
test_<MethodName>__<Scenario>__<ExpectedBehavior>
```

Examples:

```python
def test_validate__ValidConfig__ReturnsValidResult(self): ...
def test_validate__MissingTarget__ReturnsError(self): ...
def test_instantiate__NestedConfig__InstantiatesRecursively(self): ...
```

### AAA Structure

Every test follows the **Arrange-Act-Assert** pattern with explicit comments:

```python
def test_validate__ValidConfig__ReturnsValidResult(self):
    """Test that valid config returns a valid result."""
    # Arrange
    store = self._empty_store()

    @dataclass
    class Model:
        hidden_size: int
        dropout: float = 0.1

    store.register("model", Model)
    validator = ConfigValidator(store)
    config = {"_target_": "model", "hidden_size": 256}

    # Act
    result = validator.validate(config)

    # Assert
    self.assertTrue(result.valid)
    self.assertEqual(len(result.errors), 0)
```

For exception testing, combine Act & Assert:

```python
def test_instantiate__MissingRequiredField__RaisesError(self):
    """Test that missing required field raises MissingFieldError."""
    # Arrange
    store = self._empty_store()
    # ... setup ...

    # Act & Assert
    with self.assertRaises(MissingFieldError) as ctx:
        instantiator.instantiate(config)

    self.assertEqual(ctx.exception.field, "required_value")
```

### Test Isolation with Mocks

Use mocks to isolate the unit under test from its dependencies:

```python
from unittest.mock import patch

def test_validate__TypeHintsUnavailable__SkipsTypeValidation(self):
    """Test that validation continues when type hints fail."""
    # Arrange
    store = self._empty_store()
    # ... setup ...

    # Act
    with patch(
        "rconfig.ConfigValidator.get_type_hints",
        side_effect=NameError("name 'NonExistentType' is not defined"),
    ):
        result = validator.validate(config)

    # Assert
    self.assertTrue(result.valid)
```

### Test Class Organization

Group tests by behavior domain:

```python
class ConfigValidatorTests(unittest.TestCase):
    """Basic validation functionality tests."""

class ConfigValidatorEdgeCaseTests(unittest.TestCase):
    """Edge cases and boundary conditions."""

class ConfigValidatorImplicitTargetTests(unittest.TestCase):
    """Tests for implicit target inference."""
```

### Helper Methods

Use helper methods to reduce test setup duplication:

```python
class ConfigValidatorTests(unittest.TestCase):

    def _empty_store(self) -> TargetRegistry:
        """Create a clean TargetRegistry for testing."""
        store = TargetRegistry()
        store._known_targets.clear()
        return store
```

---

## Integration Tests

### File-Based Test Setup

Use `setUp` and `tearDown` for temporary resources:

```python
class ConfigComposerIntegrationTests(unittest.TestCase):

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_root = Path(self.temp_dir.name)
        clear_cache()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()
        clear_cache()

    def _write_config(self, name: str, content: dict[str, Any]) -> Path:
        """Write a config file to the temporary directory."""
        path = self.config_root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            yaml.dump(content, f)
        return path
```

### Integration Test Naming

Follow the same naming convention as unit tests:

```python
def test_compose__RefChainThreeDeep__ResolvesCorrectly(self): ...
def test_compose__CircularRef__RaisesCircularRefError(self): ...
def test_instantiate__SharedInstance__ReturnsSameObject(self): ...
```

### End-to-End Scenarios

Test complete workflows:

```python
def test_compose_and_instantiate__CompleteWorkflow__ProducesValidObject(self):
    """Test full workflow from YAML to instantiated object."""
    # Arrange
    self._write_config("model.yaml", {
        "_target_": "transformer",
        "hidden_size": 512,
        "encoder": {"_ref_": "encoder.yaml"},
    })
    self._write_config("encoder.yaml", {
        "_target_": "encoder",
        "layers": 6,
    })

    # Act
    config = compose(self.config_root / "model.yaml")
    model = instantiate(config)

    # Assert
    self.assertIsInstance(model, Transformer)
    self.assertEqual(model.hidden_size, 512)
```
