# ReausoConfig

A lightweight Python configuration library that turns YAML, JSON, and TOML files into Python objects with minimal runtime coupling.

## What is ReausoConfig?

ReausoConfig provides a simple way to load configuration files (YAML, JSON, or TOML) and instantiate Python objects from them. Unlike heavier frameworks, your application code doesn't need to know about ReausoConfig—only the startup/registration code does.

After instantiation, you get pure Python objects with no framework dependency.

## Installation

Install ReausoConfig from GitHub using pip:

```bash
pip install git+https://github.com/reauso/ReausoConfig.git
```

### Development Setup

For contributing or running tests, use pixi:

```bash
pixi install
pixi run test
```

## Quick Start

### 1. Define your classes

```python
from dataclasses import dataclass

@dataclass
class ModelConfig:
    hidden_size: int
    dropout: float = 0.1
```

### 2. Create a config file

**YAML** (config.yaml):
```yaml
_target_: model
hidden_size: 256
dropout: 0.2
```

**JSON** (config.json):
```json
{
    "_target_": "model",
    "hidden_size": 256,
    "dropout": 0.2
}
```

**TOML** (config.toml):
```toml
_target_ = "model"
hidden_size = 256
dropout = 0.2
```

The `_target_` key maps to a registered class name.

### 3. Register and instantiate

```python
import rconfig as rc
from pathlib import Path

# Register your class
rc.register(name="model", target=ModelConfig)

# Instantiate the object (validates automatically)
model = rc.instantiate(path=Path("config.yaml"), expected_type=ModelConfig)
print(model.hidden_size)  # 256
print(model.dropout)      # 0.2

# Optional: validate without instantiating (dry-run)
result = rc.validate(path=Path("config.yaml"))
if not result.valid:
    for error in result.errors:
        print(error)
```

## Core Concepts

### Supported File Formats

ReausoConfig has built-in support for three configuration formats:

| Format | Extensions | Notes |
|--------|------------|-------|
| YAML | `.yaml`, `.yml` | Primary format, preserves comments with ruamel.yaml |
| JSON | `.json` | Standard JSON, good for programmatic generation |
| TOML | `.toml` | Python 3.11+ (uses stdlib tomllib) |

The loader is selected automatically based on file extension:

```python
# All work the same way
model = rc.instantiate(path=Path("config.yaml"))
model = rc.instantiate(path=Path("config.json"))
model = rc.instantiate(path=Path("config.toml"))
```

**Cross-format composition:** You can mix formats with `_ref_`:

```yaml
# trainer.yaml
_target_: trainer
model:
  _ref_: ./models/resnet.json  # Load JSON from YAML
settings:
  _ref_: ./settings.toml       # Load TOML from YAML
```

### The `_target_` Key

The `_target_` key maps a config block to a registered Python class.

**Root config file:** The root configuration file **must** have a `_target_` field:

```yaml
_target_: my_model  # Required at root level
learning_rate: 0.001
```

**Nested configs:** For nested configuration blocks, `_target_` is **optional** when the parent class has a type hint pointing to a concrete, registered class. See [Target Resolution](#target-resolution) for details on when `_target_` can be omitted.

### ConfigStore

ConfigStore is the central registry that implements **target mappings** - the association between string identifiers and Python classes. When you register a target:

```python
rc.register(name="my_model", target=MyModel)
rc.register(name="my_dataset", target=MyDataset)
```

The registered names (`"my_model"`, `"my_dataset"`) are exactly the values you use for `_target_` in your config files:

```yaml
_target_: my_model    # Maps to MyModel class
hidden_size: 256
```

This decoupling allows config files to reference classes by stable string identifiers, independent of Python module paths or class renaming.

**Viewing registered targets:**

```python
refs = rc.known_references()
for name, ref in refs.items():
    print(f"{name}: {ref.target_class}")
```

### Validation

Before instantiation, configs are validated for:

- Required fields (parameters without defaults)
- Type compatibility
- Target existence in registry

### Object-Oriented Instantiation

ReausoConfig's key feature is **object-oriented configuration**: your config files describe object relationships, and the library instantiates a fully-connected object graph by calling actual class constructors.

This enables **full object instantiation** - not just data containers, but factories, service objects, logic components, and complete application wiring. Your entire application can be assembled from configuration.

#### How It Works

When you call `rc.instantiate()`:

1. **Config loading**: The config file is loaded and composed (resolving `_ref_` references)
2. **Validation**: The config structure is validated against registered class constructors
3. **Recursive instantiation**: Each nested config with a `_target_` becomes an actual object instance
4. **Constructor mapping**: Config keys become constructor keyword arguments

```python
@dataclass
class Database:
    host: str
    port: int

@dataclass
class Service:
    name: str
    db: Database  # Nested object

rc.register(name="database", target=Database)
rc.register(name="service", target=Service)
```

```yaml
# service.yaml
_target_: service
name: "api"
db:
  _target_: database
  host: "localhost"
  port: 5432
```

```python
# This creates: Service(name="api", db=Database(host="localhost", port=5432))
service = rc.instantiate(path=Path("service.yaml"))

# Result is pure Python objects - no framework dependency
assert isinstance(service, Service)
assert isinstance(service.db, Database)
assert service.db.host == "localhost"
```

#### Beyond Data Classes: Factories and Logic Objects

ReausoConfig works with **any callable** - not just dataclasses. Constructor parameters don't need to be stored as attributes. This makes it perfect for factories, builders, and objects that perform logic during initialization:

```python
class Rectangle:
    """Constructor values are used for computation, not stored directly."""
    def __init__(self, width: float, height: float):
        self._area = width * height
        self._perimeter = 2 * (width + height)

    @property
    def area(self) -> float:
        return self._area

class ConnectionPool:
    """Factory that creates internal resources from config values."""
    def __init__(self, host: str, port: int, pool_size: int):
        self._connections = [
            self._create_connection(host, port)
            for _ in range(pool_size)
        ]

    def _create_connection(self, host: str, port: int):
        # Create actual connection...
        pass

class ApplicationBootstrapper:
    """Orchestrates application startup from config."""
    def __init__(self, db: ConnectionPool, cache: ConnectionPool, workers: int):
        self._db = db
        self._cache = cache
        self._start_workers(workers)

    def _start_workers(self, count: int):
        # Initialize worker threads...
        pass

rc.register(name="rectangle", target=Rectangle)
rc.register(name="pool", target=ConnectionPool)
rc.register(name="app", target=ApplicationBootstrapper)
```

```yaml
# app.yaml - Wire your entire application from config
_target_: app
workers: 4
db:
  _target_: pool
  host: "db.example.com"
  port: 5432
  pool_size: 10
cache:
  _target_: pool
  host: "cache.example.com"
  port: 6379
  pool_size: 5
```

```python
# One call bootstraps your entire application
app = rc.instantiate(path=Path("app.yaml"))
```

#### Type-Driven Polymorphism

Type hints enable runtime substitution of implementations:

```python
from abc import ABC, abstractmethod

class Optimizer(ABC):
    @abstractmethod
    def step(self): pass

class Adam(Optimizer):
    def __init__(self, lr: float):
        self.lr = lr
    def step(self): pass

class SGD(Optimizer):
    def __init__(self, lr: float, momentum: float):
        self.lr = lr
        self.momentum = momentum
    def step(self): pass

@dataclass
class Trainer:
    optimizer: Optimizer  # Accepts any Optimizer subclass

rc.register(name="adam", target=Adam)
rc.register(name="sgd", target=SGD)
rc.register(name="trainer", target=Trainer)
```

```yaml
# Switch implementations by changing _target_ - no code changes needed
_target_: trainer
optimizer:
  _target_: adam  # or "sgd"
  lr: 0.001
```

#### Framework Independence

After instantiation, your objects have **no dependency on ReausoConfig**:

- Objects are pure Python instances of your classes
- No base classes or mixins required
- No framework imports needed in your application code
- Works with dataclasses, regular classes, or any callable

This means your application code remains clean and testable - only your startup/configuration code needs to import rconfig.

### Nested Configs

Configs can contain nested configs that are instantiated recursively:

```yaml
_target_: trainer
model:
  _target_: model
  hidden_size: 256
optimizer:
  _target_: optimizer
  lr: 0.001
```

#### Target Resolution

ReausoConfig can automatically determine the target class for nested configs in two ways:

##### 1. Implicit Inference from Type Hints

When a nested config field has a concrete type hint (a class that is registered with no subclasses), the `_target_` can be omitted and will be automatically inferred:

```python
@dataclass
class ModelConfig:
    hidden_size: int

@dataclass
class TrainerConfig:
    model: ModelConfig  # Concrete type - _target_ can be inferred
    epochs: int

rc.register(name="model", target=ModelConfig)
rc.register(name="trainer", target=TrainerConfig)
```

```yaml
# _target_ for model is optional here
_target_: trainer
model:
  hidden_size: 256  # No _target_ needed - inferred from type hint
epochs: 10
```

##### 2. Auto-registration from Explicit Targets

When a nested config has an explicit `_target_` that matches the expected type's class name (case-insensitive), the class is automatically registered if not already:

```python
@dataclass
class ResNet:
    layers: int
    pretrained: bool

@dataclass
class TrainerConfig:
    model: ResNet  # Type hint provides the class
    epochs: int

rc.register(name="trainer", target=TrainerConfig)
# Note: ResNet is NOT registered manually
```

```yaml
_target_: trainer
model:
  _target_: resnet  # Auto-registers ResNet (matches class name)
  layers: 50
  pretrained: false
epochs: 100
```

This is useful with `_ref_` composition - referenced files can specify their own `_target_` without pre-registration:

```yaml
# models/resnet.yaml (referenced via _ref_)
_target_: resnet
layers: 50
pretrained: false
```

##### When `_target_` is Required

- **Root config file** - Always required
- **Abstract base classes** - Cannot be instantiated directly
- **Base classes with multiple registered subclasses** - Ambiguous which to use
- **Union types** - Cannot determine which type to use

```python
from abc import ABC, abstractmethod

class BaseEncoder(ABC):
    @abstractmethod
    def encode(self): pass

class TransformerEncoder(BaseEncoder):
    def __init__(self, layers: int):
        self.layers = layers
    def encode(self): pass

class LSTMEncoder(BaseEncoder):
    def __init__(self, hidden_size: int):
        self.hidden_size = hidden_size
    def encode(self): pass

@dataclass
class Model:
    encoder: BaseEncoder  # Abstract - _target_ required!

rc.register(name="transformer", target=TransformerEncoder)
rc.register(name="lstm", target=LSTMEncoder)
rc.register(name="model", target=Model)
```

```yaml
_target_: model
encoder:
  _target_: transformer  # Required - BaseEncoder is abstract
  layers: 6
```

##### Auto-registration Requirements

- Parent field must have a type hint
- `_target_` name must match the type hint's class name (case-insensitive)
- The class must not be abstract
- The type hint must be a single class (not `Union[A, B]`)

**When auto-registration fails:**

- `TargetNotFoundError`: Target name doesn't match expected class
- `AmbiguousTargetError`: Type is abstract or has multiple implementations

### Config Composition with `_ref_`

Load configurations from other files and merge them:

```yaml
# models/resnet.yaml
_target_: model
hidden_size: 256
dropout: 0.1

# trainer.yaml
_target_: trainer
model:
  _ref_: models/resnet.yaml  # Load from file
  dropout: 0.2               # Override: merged on top
epochs: 10
```

**Path resolution:**

| Syntax | Example | Description |
|--------|---------|-------------|
| Relative (implicit) | `models/resnet.yaml` | Relative to current file |
| Relative (explicit) | `./local.yaml` | Explicit relative to current file |
| Parent directory | `../shared/base.yaml` | Navigate up directories |
| Absolute | `/models/resnet.yaml` | From config root directory |

**Deep merge:** Sibling keys override values from the referenced file.

### Instance Sharing with `_instance_`

Share object instances across your config:

```yaml
_target_: app
shared_cache:
  _target_: cache
  size: 100

service_a:
  _target_: service
  cache:
    _instance_: shared_cache  # Same object as shared_cache

service_b:
  _target_: service
  cache:
    _instance_: shared_cache  # Same object, shared with service_a
```

**Path resolution:**

| Syntax | Example | Description |
|--------|---------|-------------|
| Absolute | `/shared.database` | From composed config root |
| Relative (implicit) | `shared_cache` | Relative to config root |
| Relative (explicit) | `./shared` | Explicit relative syntax |
| Parent | `../sibling.value` | Parent-relative path |
| Nested | `data.sources.primary` | Dot notation for nesting |
| List indexing | `databases[0]` | Access list element |

**Special values:**

- `_instance_: null` - Passes `None` to constructor

### CLI Overrides

Override config values from the command line:

```bash
python main.py model.hidden_size=512 epochs=20
```

Or programmatically:

```python
trainer = rc.instantiate(
    path=Path("config.yaml"),
    overrides={"model.hidden_size": 512, "epochs": 20},
)
```

#### Override Syntax

| Syntax        | Example                | Description      |
| ------------- | ---------------------- | ---------------- |
| Dot notation  | `model.lr=0.01`      | Set nested value |
| List indexing | `layers[0].size=128` | Set list element |
| Add to list   | `+callbacks=logger`  | Append to list   |
| Remove key    | `~dropout`           | Delete key       |

#### Disabling CLI Overrides

For tests or library usage, disable automatic CLI parsing:

```python
model = rc.instantiate(path=Path("config.yaml"), cli_overrides=False)
```

#### Override Priority

When both programmatic and CLI overrides are provided, CLI wins:

```python
# CLI: python main.py model.lr=0.05
trainer = rc.instantiate(path=Path("config.yaml"), overrides={"model.lr": 0.01})
# Result: model.lr = 0.05 (CLI wins)
```

## Advanced Features

### Required Values with `_required_`

Mark config values that must be provided externally (via CLI, programmatic overrides, or environment variables):

```yaml
# config.yaml
_target_: app
api_key: _required_           # Must be provided
database_url: _required_      # Must be provided
port: 8080                    # Has default, optional

# With optional type hint
timeout:
  _required_: int             # Must be int when provided
```

Required values can be satisfied by:

- CLI overrides: `api_key=secret123`
- Programmatic overrides: `overrides={"api_key": "secret"}`
- Environment variable interpolation: `api_key: ${env:API_KEY}`

```python
# This will raise RequiredValueError - api_key not provided
model = rc.instantiate(path=Path("config.yaml"))

# Provide required values via overrides
model = rc.instantiate(
    path=Path("config.yaml"),
    overrides={"api_key": "secret123", "database_url": "postgres://..."},
)

# Or validate first to check what's missing
result = rc.validate(path=Path("config.yaml"))
if not result.valid:
    for error in result.errors:
        print(error)  # Shows which _required_ values are missing
```

### Partial Instantiation

Instantiate only a specific section of the config tree:

```python
# Load trainer config, but only instantiate the model
model = rc.instantiate(path=Path("trainer.yaml"), inner_path="model")

# Works with nested paths
encoder = rc.instantiate(path=Path("trainer.yaml"), inner_path="model.encoder")

# And list indices
first_callback = rc.instantiate(path=Path("trainer.yaml"), inner_path="callbacks[0]")
```

**How it works:**

1. The full config is composed (all `_ref_` resolved)
2. Overrides are applied to the full config
3. Interpolations (`${...}`) are resolved from the full config
4. The sub-config at `inner_path` is extracted and instantiated

This means interpolations can reference values outside the partial:

```yaml
# trainer.yaml
_target_: trainer
defaults:
  learning_rate: 0.01
model:
  _target_: model
  lr: ${/defaults.learning_rate}  # References outside model section
```

```python
# This works! Interpolation resolved before extraction
model = rc.instantiate(path=Path("trainer.yaml"), inner_path="model")
print(model.lr)  # 0.01
```

**Instance sharing with external targets:**

If the partial section has `_instance_` references to targets outside the section, those targets are automatically instantiated and shared:

```yaml
_target_: app
shared_cache:
  _target_: cache
  size: 100
services:
  api:
    _target_: service
    cache:
      _instance_: /shared_cache  # Outside "services.api" scope
```

```python
# Instantiates both the service AND the shared_cache it references
service = rc.instantiate(path=Path("app.yaml"), inner_path="services.api")
print(service.cache.size)  # 100
```

### Lazy Instantiation

Delay object creation until first attribute access. Useful for expensive initialization (loading models, database connections) that may not always be used.

#### Global Lazy Mode

Make all nested configs lazy:

```python
# All nested objects delay __init__ until first access
trainer = rc.instantiate(path=Path("trainer.yaml"), lazy=True)

# trainer.model is lazy - __init__ not called yet
print(rc.is_lazy_proxy(obj=trainer.model))  # True

# Accessing any attribute triggers initialization
print(trainer.model.hidden_size)  # NOW model.__init__ is called
print(rc.is_lazy_proxy(obj=trainer.model))  # False
```

#### Per-Field Lazy Mode

Mark specific fields as lazy in YAML:

```yaml
_target_: trainer
model:
  _target_: model
  _lazy_: true  # Only model is lazy
  hidden_size: 256
optimizer:
  _target_: optimizer  # optimizer is eager (normal)
  lr: 0.001
```

```python
trainer = rc.instantiate(path=Path("trainer.yaml"))
print(rc.is_lazy_proxy(obj=trainer.model))      # True - lazy
print(rc.is_lazy_proxy(obj=trainer.optimizer))  # False - eager
```

**Note:** `_lazy_: true` only affects that specific field, not its children (non-cascading).

#### Checking Lazy Status

```python
from rconfig import is_lazy_proxy, force_initialize

trainer = rc.instantiate(path=Path("trainer.yaml"), lazy=True)

# Check if object is uninitialized
if is_lazy_proxy(trainer.model):
    print("Model not yet initialized")

# Force initialization without accessing attributes
force_initialize(trainer.model)
print(is_lazy_proxy(trainer.model))  # False
```

#### How It Works

- Lazy proxies are dynamic subclasses of your target class
- `isinstance(lazy_obj, TargetClass)` returns `True`
- After initialization, the object behaves identically to an eager instance
- Works correctly with `_instance_` sharing - all references share the same lazy proxy
- **No framework dependency in user code**: The returned objects work without importing anything from rconfig

#### Transparency Guarantees

Lazy proxies are designed to be completely transparent to user code:

| Operation                    | Works? | Notes                                  |
| ---------------------------- | ------ | -------------------------------------- |
| `isinstance(obj, MyClass)` | Yes | Proxy is a subclass of your class      |
| `obj.attribute`            | Yes | Triggers init, then returns value      |
| `obj.method()`             | Yes | Triggers init, then calls method       |
| `hasattr(obj, 'attr')`     | Yes | Triggers init, then checks             |
| `len(obj)`                 | Yes | Triggers init, then calls `__len__`  |
| `for x in obj`             | Yes | Triggers init, then iterates           |
| `obj[key]`                 | Yes | Triggers init, then indexes            |
| `obj()`                    | Yes | Triggers init, then calls `__call__` |
| `dataclasses.asdict(obj)`  | Yes | Triggers init, then converts           |
| `str(obj)` / `repr(obj)` | Yes | Triggers init, then formats            |

#### Known Limitations

These edge cases behave differently from regular objects:

| Operation                    | Behavior            | Workaround                       |
| ---------------------------- | ------------------- | -------------------------------- |
| `type(obj)`                | Returns proxy class | Use `isinstance()` instead     |
| `obj.__class__`            | Returns proxy class | Use `isinstance()` instead     |
| `obj.__class__ == MyClass` | Returns `False`   | Use `isinstance(obj, MyClass)` |

**Impact**: These limitations only affect code that uses `type()` or `__class__` for exact type comparison. This is rare in practice - most code uses `isinstance()` which works correctly.

#### Use Cases

1. **Expensive resources**: Models that load weights, database connections
2. **Conditional initialization**: Components only needed in certain code paths
3. **Faster startup**: Defer heavy initialization until actually needed

```yaml
_target_: app
# Large model only loaded if inference is called
inference_model:
  _target_: llm
  _lazy_: true
  model_path: /path/to/large_model.bin

# Always needed
config:
  _target_: config
  debug: false
```

### Interpolation

Reference config values and environment variables with `${...}` syntax:

```yaml
_target_: trainer
defaults:
  learning_rate: 0.01
  batch_size: 32

model:
  _target_: model
  lr: ${/defaults.learning_rate}     # Reference another config value
  scaled_lr: ${/defaults.learning_rate * 10}  # Arithmetic expressions

training:
  effective_batch: ${/defaults.batch_size * 4}
  output_dir: ${env:OUTPUT_DIR,./output}  # Environment variable with default
  user_path: /data/${env:USER}/runs       # Embedded in string
```

#### Config Path References

| Syntax   | Example                 | Description                  |
| -------- | ----------------------- | ---------------------------- |
| Absolute | `${/model.lr}`        | From root of composed config |
| Relative | `${./local.value}`    | From current document root   |
| Implicit | `${model.lr}`         | Same as relative             |
| Parent   | `${../sibling.value}` | Parent-relative path         |

#### Environment Variables

```yaml
# Required (raises error if not set)
data_path: ${env:DATA_PATH}

# With default value
log_level: ${env:LOG_LEVEL,INFO}
port: ${env:PORT,8080}  # Numbers are parsed
debug: ${env:DEBUG,false}  # Booleans are parsed
```

#### Expression Support

Full Python-like expression evaluation:

```yaml
# Arithmetic
doubled: ${/learning_rate * 2}
ratio: ${/a / /b}
power: ${/base ** 2}

# Comparisons
is_large: ${/epochs > 100}
is_valid: ${/lr >= 0.001 and /lr <= 1.0}

# Boolean
enabled: ${/use_gpu and not /debug_mode}

# String concatenation
filename: ${"model_" + /name + "_v" + /version}
```

#### List Operations

```yaml
items: [1, 2, 3, 4, 5]
callbacks: [logger, checkpoint, early_stop]

# Indexing and slicing
first: ${/items[0]}          # 1
last: ${/items[-1]}          # 5
subset: ${/items[1:3]}       # [2, 3]
from_start: ${/items[:3]}    # [1, 2, 3]
to_end: ${/items[2:]}        # [3, 4, 5]

# Concatenation
all: ${/base_list + /extra_list}

# Removal by value
filtered: ${/callbacks - ["early_stop"]}  # [logger, checkpoint]

# Remove by index
without_first: ${/items.remove(0)}  # [2, 3, 4, 5]

# Length
count: ${len(/items)}  # 5

# Membership
has_gpu: ${"gpu" in /devices}
```

#### Conditional Expressions

##### Ternary Operator

Conditional expressions using `condition ? if_true : if_false` syntax:

```yaml
# Basic ternary with boolean
mode: '${/debug ? "verbose" : "quiet"}'

# With comparison
level: '${/count > 10 ? "high" : "low"}'

# With resolver as condition
status: '${app:is_ready() ? "go" : "wait"}'

# Nested ternary (right-associative)
result: '${/a ? "first" : /b ? "second" : "third"}'
```

##### Coalesce Operators

Two coalesce operators for handling null values and errors:

| Operator | Name | Catches |
|----------|------|---------|
| `?:` | Elvis (soft) | `None`, missing resolver/env |
| `??` | Error (hard) | `None`, missing resolver/env, **all exceptions** |

```yaml
# Elvis coalesce - catches null and missing
safe_id: '${app:uuid ?: "fallback-id"}'
env_val: '${env:API_KEY ?: "dev-key"}'

# Error coalesce - also catches exceptions
risky_value: '${app:might_fail() ?? "safe-default"}'

# Chained coalesce (right-associative)
value: '${app:primary() ?? app:backup() ?? "ultimate-fallback"}'

# Combined with ternary
result: '${(app:get_value() ?? 0) > 5 ? "high" : "low"}'
```

**Elvis (`?:`) vs Error (`??`) Coalesce:**

- Use `?:` when you want resolver exceptions to propagate (fail fast)
- Use `??` when you want to catch all errors and use a fallback

```yaml
# ?: propagates errors from app:risky
critical: '${app:risky() ?: "fallback"}'  # Raises if risky() throws

# ?? catches all errors
safe: '${app:risky() ?? "fallback"}'  # Returns "fallback" if risky() throws
```

#### Type Behavior

- **Standalone** `${expr}`: Preserves type (number stays number)
- **Embedded** `"text ${expr} more"`: Result is always string

```yaml
# Standalone - type preserved
lr: ${/defaults.learning_rate}     # float: 0.01
count: ${len(/items)}               # int: 5
enabled: ${/use_gpu}                # bool: true

# Embedded - becomes string
message: "Learning rate is ${/defaults.learning_rate}"  # str: "Learning rate is 0.01"
```

#### Circular Reference Detection

Circular references are detected and raise `CircularInterpolationError`:

```yaml
# This will raise an error
a: ${/b}
b: ${/a}  # Circular: a -> b -> a
```

### Custom Resolvers

Register Python functions that can be called from interpolation expressions using the `app:` prefix:

```python
import rconfig as rc
from datetime import datetime
import uuid

# Simple resolver (no arguments)
@rc.resolver("uuid")
def gen_uuid() -> str:
    return str(uuid.uuid4())

# Resolver with arguments
@rc.resolver("now")
def now(fmt: str = "%Y-%m-%d") -> str:
    return datetime.now().strftime(fmt)

# Namespaced resolver - all three syntaxes are equivalent:
@rc.resolver("db", "lookup")      # Multiple arguments
@rc.resolver("db:lookup")         # Colon-delimited string
@rc.resolver("db.lookup")         # Dot-delimited string
def db_lookup(table: str, id: int) -> dict:
    return database.get(table, id)

# Deeply nested namespace
@rc.resolver("db", "cache", "get")  # or "db:cache:get" or "db.cache.get"
def cache_get(key: str, ttl: int = 60) -> Any:
    return cache.get(key, ttl=ttl)

# Resolver with config access (special _config_ parameter)
@rc.resolver("derive")
def derive(path: str, *, _config_: dict) -> Any:
    return _config_.get(path)
```

#### Resolver Syntax

```yaml
_target_: experiment

# No arguments (parentheses optional)
id: '${app:uuid}'
id_alt: '${app:uuid()}'  # Also valid

# Positional arguments
timestamp: '${app:now("%Y-%m-%d_%H-%M-%S")}'

# Keyword arguments
timestamp2: '${app:now(fmt="%Y-%m-%d")}'

# Namespaced resolver with arguments
user: '${app:db:lookup("users", 42)}'

# Deep namespace with kwargs
cached: '${app:db:cache:get("session", ttl=300)}'

# Config reference as argument
base_lr: 0.01
scaled_lr: '${app:scale(/base_lr, 2)}'

# Expression as argument
doubled: '${app:math:multiply(/base_lr, 2)}'
```

#### Config Access in Resolvers

Resolvers can access the full config by declaring a `_config_` keyword-only parameter:

```python
@rc.resolver("derive")
def derive(key: str, *, _config_: dict) -> Any:
    """Access config values from within a resolver."""
    return _config_.get(key)
```

The `_config_` parameter receives a read-only view of the raw config dictionary (before instantiation).

**Note:** Resolvers can be used with conditional expressions (ternary `?:`, coalesce `?:` and `??`). See [Conditional Expressions](#conditional-expressions) for details.

#### Unregistering Resolvers

```python
# Unregister a resolver
rc.unregister_resolver("uuid")
rc.unregister_resolver("db", "lookup")  # Namespaced
```

### Config Export / Serialization

Export resolved configs to various formats without instantiation:

```python
import rconfig as rc
from pathlib import Path

# Export to Python dict (fully resolved)
config_dict = rc.to_dict(path=Path("config.yaml"))
print(config_dict["model"]["hidden_size"])  # 256

# Export to YAML string
yaml_str = rc.to_yaml(path=Path("config.yaml"))

# Export to JSON string
json_str = rc.to_json(path=Path("config.yaml"))

# Export to TOML string
toml_str = rc.to_toml(path=Path("config.yaml"))

# With overrides
config = rc.to_dict(
    path=Path("config.yaml"),
    overrides={"model.lr": 0.01}
)

# Remove internal markers (_target_, _ref_, _instance_, _lazy_)
clean_dict = rc.to_dict(path=Path("config.yaml"), exclude_markers=True)
```

#### File Export

Export to files with automatic format detection based on output file extension:

```python
# Single file export - format auto-detected from extension
rc.to_file(source=Path("trainer.yaml"), output_path=Path("output.json"))   # YAML -> JSON
rc.to_file(source=Path("trainer.yaml"), output_path=Path("output.toml"))   # YAML -> TOML
rc.to_file(source=Path("trainer.yaml"), output_path=Path("output.yaml"))   # YAML -> YAML

# Export from dict (useful for post-processing)
config = {"model": {"lr": 0.01}, "epochs": 10}
rc.to_file(source=config, output_path=Path("output.yaml"))

# Post-processing workflow
config = rc.to_dict(path=Path("config.yaml"), cli_overrides=False)
config["extra_key"] = "added_value"
rc.to_file(source=config, output_path=Path("output.json"))

# Multi-file export preserving _ref_ structure
rc.to_files(source=Path("trainer.yaml"), config_root_file=Path("output/trainer.json"))
# Creates:
#   output/trainer.json (root file in JSON format)
#   output/models/resnet.yaml (preserves original YAML format)
#   output/settings.toml (preserves original TOML format)
```

#### Cross-Format Export

Load configs from any format and export to another:

```python
# Load YAML, export as JSON string
json_str = rc.to_json(path=Path("config.yaml"))

# Load TOML, export as YAML string
yaml_str = rc.to_yaml(path=Path("config.toml"))

# Load JSON, export to TOML file
rc.to_file(source=Path("config.json"), output_path=Path("output.toml"))
```

#### Custom Exporters

Register custom exporters for additional formats:

```python
from rconfig import Exporter, register_exporter

class XmlExporter(Exporter):
    def export(self, config: dict) -> str:
        # Custom XML serialization logic
        return dict_to_xml(config)

# Register for .xml extension
register_exporter(XmlExporter(), ".xml")

# Now works with to_file
rc.to_file(source=Path("config.yaml"), output_path=Path("output.xml"))
```

For more control, use the `export()` function with a custom exporter instance:

```python
result = rc.export(path=Path("config.yaml"), exporter=MyCustomExporter())
```

### Provenance Tracking

Track the origin of every config value - essential for debugging complex configs.

#### Basic Usage

```python
prov = rc.get_provenance(path=Path("trainer.yaml"))
print(prov)  # Shows config with file:line annotations

# Example output:
# /model.layers = 50
#   trainer.yaml:5
#   Target: model -> myapp.models.Model
#   Overrode: models/resnet.yaml:2
# /model.dropout = 0.2
#   models/resnet.yaml:3
```

#### Accessing Specific Entries

```python
entry = prov.get("model.layers")
print(f"Defined at: {entry.file}:{entry.line}")
if entry.overrode:
    print(f"Overrode: {entry.overrode}")

# Iterate all entries
for path, entry in prov.items():
    print(f"{path}: {entry.file}:{entry.line}")
```

#### Formatting Presets

| Preset        | Shows                          | Use Case         |
| ------------- | ------------------------------ | ---------------- |
| `minimal()` | paths, files, lines            | Quick overview   |
| `compact()` | + values, source type, targets | Debugging values |
| `full()`    | everything (default)           | Complete tracing |

```python
# Use presets
print(prov.format().minimal())
print(prov.format().compact())
print(prov.format().full())  # Default

# Enum alternative
from rconfig.composition import ProvenancePreset
print(prov.format().preset(ProvenancePreset.MINIMAL))
```

#### Show/Hide Toggles

```python
# All toggles (each has show/hide variant)
prov.format()
    .show_paths()      .hide_paths()      # Config paths (/model.lr)
    .show_values()     .hide_values()     # Resolved values
    .show_files()      .hide_files()      # Source file names
    .show_lines()      .hide_lines()      # Line numbers
    .show_source_type().hide_source_type()# Source markers (CLI/env/file)
    .show_chain()      .hide_chain()      # Interpolation/instance chains
    .show_overrides()  .hide_overrides()  # Override information
    .show_targets()    .hide_targets()    # Target class information

# Combine with presets
print(prov.format().minimal().show_values())
print(prov.format().compact().hide_chain())
```

#### Filtering

```python
# Filter by config path (glob patterns)
print(prov.format().for_path("/model.*"))      # Only model paths
print(prov.format().for_path("/training.*"))   # Only training paths

# Filter by source file
print(prov.format().from_file("trainer.yaml")) # Only from trainer.yaml
print(prov.format().from_file("models/*.yaml"))# From any file in models/

# Combine filters (multiple calls = OR logic)
print(prov.format()
    .for_path("/model.*")
    .from_file("config.yaml")
)
```

#### Source Types

Provenance tracks where values originate:

| Source       | Marker            | Description           |
| ------------ | ----------------- | --------------------- |
| file         | (none)            | Regular config file   |
| cli          | `CLI:`          | Command-line override |
| env          | `env:`          | Environment variable  |
| programmatic | `programmatic:` | Set via Python code   |

```python
# CLI overrides show the argument
# /model.lr = 0.01
#   CLI: model.lr=0.01
#   Overrode: config.yaml:5

# Environment variables show the var name
# /data.path = "/data/user"
#   env: DATA_PATH
```

#### Override Tracking

When values are overridden, provenance shows the chain:

```python
# /model.lr = 0.01
#   trainer.yaml:5
#   Overrode: models/base.yaml:10

entry = prov.get("model.lr")
if entry.overrode:
    print(f"Replaced value from: {entry.overrode}")
```

#### Interpolation Chains

For interpolated values, provenance shows the source tree:

```
# /model.lr = 0.02
#   config.yaml:5
#   Interpolation: ${/defaults.lr * 2}
#     +-- *
#          |-- /defaults.lr = 0.01
#          |     defaults.yaml:3
#          +-- 2 (literal)
```

#### Tree Tracing

Build a full provenance tree for complex chains:

```python
tree = prov.trace("model.lr")
if tree:
    print(tree.source_type)  # "file", "cli", "env", etc.
    print(tree.file, tree.line)
    for child in tree.children:
        print(f"  {child.source_type}: {child.path}")
```

#### Dict Export

Export provenance as a dictionary for programmatic access:

```python
# Export entire provenance
data = prov.to_dict()

# Export single entry
entry_data = prov.get("model.lr").to_dict()

# Export tree node
tree_data = prov.trace("model.lr").to_dict()
```

#### Custom Layouts

Create custom output formats by extending ProvenanceLayout:

```python
from rconfig.composition import ProvenanceLayout, FormatContext

class TableLayout(ProvenanceLayout):
    def format_provenance(self, provenance, ctx: FormatContext) -> str:
        lines = ["| Path | File | Line |", "|------|------|------|"]
        for path, entry in provenance.items():
            lines.append(f"| {path} | {entry.file} | {entry.line} |")
        return "\n".join(lines)

    def format_entry(self, entry, path, ctx: FormatContext) -> str:
        return f"| {path} | {entry.file} | {entry.line} |"

# Use custom layout
print(prov.format().layout(TableLayout()))
```

## API Reference

### `rc.register(name, target)`

Register a target class under a unique name for use in config files.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | `str` | required | Unique identifier for the target class. This is the value used in `_target_` fields. |
| `target` | `type` | required | The Python class to register. |

**Returns:** `None`

**Raises:**

| Exception | Condition |
|-----------|-----------|
| `ValueError` | If `name` is already registered |

**Examples:**

```python
rc.register(name="model", target=ModelConfig)
rc.register(name="my_dataset", target=MyDataset)
```

### `rc.unregister(name)`

Remove a previously registered configuration reference.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | `str` | required | Identifier of the reference to unregister. |

**Returns:** `None`

**Raises:**

| Exception | Condition |
|-----------|-----------|
| `KeyError` | If no reference with that name exists |

**Examples:**

```python
rc.unregister(name="model")
```

### `rc.validate(path, *, overrides=None, cli_overrides=True)`

Validate a config file without instantiating (dry-run). Checks all `_required_` values have been satisfied.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `path` | `Path` | required | Path to the configuration file. |
| `overrides` | `dict[str, Any] \| None` | `None` | Dictionary of config overrides using dot notation keys. |
| `cli_overrides` | `bool` | `True` | Whether to parse CLI overrides from `sys.argv`. |

**Returns:** `ValidationResult` with fields:
- `valid` (`bool`): `True` if validation passed with no errors
- `errors` (`list[ValidationError]`): List of validation errors found

**Raises:**

| Exception | Condition |
|-----------|-----------|
| `ConfigFileError` | If file cannot be loaded or parsed |

**Examples:**

```python
result = rc.validate(path=Path("config.yaml"))
if result.valid:
    print("Config is valid!")
else:
    for error in result.errors:
        print(error)

# With overrides to satisfy _required_ values
result = rc.validate(
    path=Path("config.yaml"),
    overrides={"api_key": "secret123"},
)
```

### `rc.instantiate(path, expected_type=None, *, inner_path=None, overrides=None, cli_overrides=True, lazy=False)`

Load, compose, validate, and instantiate a configuration file into Python objects.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `path` | `Path` | required | Path to the configuration file. Supports `.yaml`, `.yml`, `.json`, `.toml`. |
| `expected_type` | `type[T] \| None` | `None` | Optional type for type-safe returns. Enables IDE autocompletion and type checking. |
| `inner_path` | `str \| None` | `None` | Dot-notation path to instantiate only a section (e.g., `"model.encoder"`). Interpolations are resolved from the full config before extraction. |
| `overrides` | `dict[str, Any] \| None` | `None` | Config overrides using dot notation keys. Applied before CLI overrides. |
| `cli_overrides` | `bool` | `True` | Whether to parse CLI overrides from `sys.argv`. Set to `False` for tests or library usage. |
| `lazy` | `bool` | `False` | If `True`, all nested configs delay `__init__` until first attribute access. |

**Returns:** `T` if `expected_type` provided, otherwise `Any`

**Raises:**

| Exception | Condition |
|-----------|-----------|
| `ConfigFileError` | File cannot be loaded or parsed |
| `TargetNotFoundError` | `_target_` value not registered |
| `ValidationError` | Config structure is invalid |
| `RequiredValueError` | `_required_` value not provided |
| `CircularRefError` | Circular `_ref_` references detected |
| `CircularInstanceError` | Circular `_instance_` references detected |
| `RefResolutionError` | A `_ref_` cannot be resolved |
| `InstanceResolutionError` | An `_instance_` path cannot be resolved |
| `InvalidInnerPathError` | `inner_path` doesn't exist in config |
| `InvalidOverridePathError` | An override path doesn't exist |
| `InvalidOverrideSyntaxError` | An override string is malformed |
| `InstantiationError` | Object creation fails |

**Examples:**

```python
# Basic usage
model = rc.instantiate(path=Path("config.yaml"))

# Type-safe with IDE autocompletion
model = rc.instantiate(path=Path("config.yaml"), expected_type=ModelConfig)

# Partial instantiation
encoder = rc.instantiate(path=Path("trainer.yaml"), inner_path="model.encoder")

# With overrides, no CLI parsing (for tests)
model = rc.instantiate(
    path=Path("config.yaml"),
    overrides={"learning_rate": 0.001},
    cli_overrides=False,
)

# Lazy instantiation
app = rc.instantiate(path=Path("app.yaml"), lazy=True)
```

### `rc.known_references()`

Get a read-only view of all registered configuration references.

**Parameters:** None

**Returns:** `MappingProxyType[str, ConfigReference]` - Immutable mapping of name to `ConfigReference`

`ConfigReference` has attributes:
- `name` (`str`): Identifier for the target class
- `target_class` (`type[Any]`): The registered class
- `decisive_init_parameters` (`MappingProxyType[str, Parameter]`): Constructor parameters

**Examples:**

```python
refs = rc.known_references()
for name, ref in refs.items():
    print(f"{name}: {ref.target_class}")
    for param_name, param in ref.decisive_init_parameters.items():
        print(f"  {param_name}: {param.annotation}")
```

### `rc.get_provenance(path)`

Compose a config file and track the origin of each value.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `path` | `Path` | required | Path to the entry-point config file. |

**Returns:** `Provenance` object with methods:
- `get(path: str) -> ProvenanceEntry | None`: Get entry for a specific config path
- `items() -> Iterator[tuple[str, ProvenanceEntry]]`: Iterate all (path, entry) tuples
- `format() -> ProvenanceLayout`: Get fluent builder for customized output
- `trace(path: str) -> ProvenanceNode | None`: Get full tree for a path
- `to_dict() -> dict`: Export as dictionary

**Examples:**

```python
prov = rc.get_provenance(path=Path("trainer.yaml"))
print(prov)  # Default formatting

entry = prov.get("model.layers")
print(f"Defined at: {entry.file}:{entry.line}")

# Custom formatting
print(prov.format().minimal())
print(prov.format().for_path("/model.*"))
```

### `rc.set_cache_size(size)`

Configure the LRU cache for loaded config files.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `size` | `int` | required | Cache size. Use `0` for unlimited (default behavior). |

**Returns:** `None`

**Examples:**

```python
rc.set_cache_size(size=100)  # Cache up to 100 files
rc.set_cache_size(size=0)    # Unlimited (default)
```

### `rc.clear_cache()`

Clear the config file cache.

**Parameters:** None

**Returns:** `None`

**Examples:**

```python
rc.clear_cache()
```

### `rc.is_lazy_proxy(obj)`

Check if an object is an uninitialized lazy proxy.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `obj` | `Any` | required | Object to check. |

**Returns:** `bool` - `True` if object is a lazy proxy that hasn't been initialized yet

**Examples:**

```python
model = rc.instantiate(path=Path("config.yaml"), lazy=True)
print(rc.is_lazy_proxy(obj=model))  # True
_ = model.hidden_size  # Triggers initialization
print(rc.is_lazy_proxy(obj=model))  # False
```

### `rc.force_initialize(obj)`

Force initialization of a lazy proxy without accessing attributes. No-op for regular objects.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `obj` | `Any` | required | Lazy proxy or regular object. |

**Returns:** `None`

**Examples:**

```python
model = rc.instantiate(path=Path("config.yaml"), lazy=True)
rc.force_initialize(obj=model)  # model.__init__ called now
print(rc.is_lazy_proxy(obj=model))  # False
```

### `rc.to_dict(path, *, overrides=None, cli_overrides=True, exclude_markers=False)`

Export resolved config as a Python dictionary.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `path` | `Path` | required | Path to config file. |
| `overrides` | `dict[str, Any] \| None` | `None` | Dictionary of config overrides. |
| `cli_overrides` | `bool` | `True` | Whether to parse CLI overrides. |
| `exclude_markers` | `bool` | `False` | If `True`, remove internal markers (`_target_`, `_ref_`, `_instance_`, `_lazy_`). |

**Returns:** `dict[str, Any]` - Resolved config as a dictionary

**Examples:**

```python
config = rc.to_dict(path=Path("config.yaml"))
clean = rc.to_dict(path=Path("config.yaml"), exclude_markers=True)
```

### `rc.to_yaml(path, *, overrides=None, cli_overrides=True, exclude_markers=False)`

Export resolved config as a YAML string.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `path` | `Path` | required | Path to config file. |
| `overrides` | `dict[str, Any] \| None` | `None` | Dictionary of config overrides. |
| `cli_overrides` | `bool` | `True` | Whether to parse CLI overrides. |
| `exclude_markers` | `bool` | `False` | If `True`, remove internal markers. |

**Returns:** `str` - Resolved config as a YAML string

**Examples:**

```python
yaml_str = rc.to_yaml(path=Path("config.yaml"))
```

### `rc.to_json(path, *, overrides=None, cli_overrides=True, exclude_markers=False, indent=2)`

Export resolved config as a JSON string.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `path` | `Path` | required | Path to config file. |
| `overrides` | `dict[str, Any] \| None` | `None` | Dictionary of config overrides. |
| `cli_overrides` | `bool` | `True` | Whether to parse CLI overrides. |
| `exclude_markers` | `bool` | `False` | If `True`, remove internal markers. |
| `indent` | `int \| None` | `2` | Number of spaces for indentation. `None` for compact output. |

**Returns:** `str` - Resolved config as a JSON string

**Examples:**

```python
json_str = rc.to_json(path=Path("config.yaml"))
compact = rc.to_json(path=Path("config.yaml"), indent=None)
```

### `rc.to_toml(path, *, overrides=None, cli_overrides=True, exclude_markers=False)`

Export resolved config as a TOML string.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `path` | `Path` | required | Path to config file. |
| `overrides` | `dict[str, Any] \| None` | `None` | Dictionary of config overrides. |
| `cli_overrides` | `bool` | `True` | Whether to parse CLI overrides. |
| `exclude_markers` | `bool` | `False` | If `True`, remove internal markers. |

**Returns:** `str` - Resolved config as a TOML string

**Examples:**

```python
toml_str = rc.to_toml(path=Path("config.yaml"))
```

### `rc.to_file(source, output_path, *, overrides=None, cli_overrides=True, exclude_markers=False)`

Export config to a single file with format auto-detected from output path extension.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `source` | `Path \| dict[str, Any]` | required | Path to config file, or dict. |
| `output_path` | `Path` | required | Output file path. Extension determines format (`.yaml`, `.json`, `.toml`). |
| `overrides` | `dict[str, Any] \| None` | `None` | Config overrides. Ignored if source is dict. |
| `cli_overrides` | `bool` | `True` | Parse CLI overrides. Ignored if source is dict. |
| `exclude_markers` | `bool` | `False` | If `True`, remove internal markers. |

**Returns:** `None`

**Raises:**

| Exception | Condition |
|-----------|-----------|
| `ConfigFileError` | Output file extension not supported |

**Examples:**

```python
# From file path
rc.to_file(source=Path("config.yaml"), output_path=Path("output.json"))

# From dict
config = {"model": {"lr": 0.01}, "epochs": 10}
rc.to_file(source=config, output_path=Path("output.yaml"))
```

### `rc.to_files(source, config_root_file, *, overrides=None, cli_overrides=True, exclude_markers=False)`

Export config preserving file structure (with `_ref_` relationships).

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `source` | `Path \| dict[str, Any]` | required | Path to config file, or dict. |
| `config_root_file` | `Path` | required | Output root file path. Extension determines root format. |
| `overrides` | `dict[str, Any] \| None` | `None` | Config overrides. Ignored if source is dict. |
| `cli_overrides` | `bool` | `True` | Parse CLI overrides. Ignored if source is dict. |
| `exclude_markers` | `bool` | `False` | If `True`, remove internal markers. |

**Returns:** `None`

**Behavior:**
- Root file format determined by `config_root_file` extension
- Referenced files preserve their original formats
- When source is dict, only root file is written

**Examples:**

```python
rc.to_files(source=Path("trainer.yaml"), config_root_file=Path("output/trainer.json"))
# Creates:
#   output/trainer.json (root in JSON)
#   output/models/resnet.yaml (preserves YAML)
```

### `rc.export(path, exporter, *, overrides=None, cli_overrides=True)`

Export resolved config using a custom exporter.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `path` | `Path` | required | Path to config file. |
| `exporter` | `Exporter` | required | Exporter instance to use. |
| `overrides` | `dict[str, Any] \| None` | `None` | Dictionary of config overrides. |
| `cli_overrides` | `bool` | `True` | Parse CLI overrides. |

**Returns:** The exported data in the exporter's target format

**Examples:**

```python
class MyExporter(Exporter):
    def export(self, config: dict) -> str:
        return json.dumps(config)

result = rc.export(path=Path("config.yaml"), exporter=MyExporter())
```

### `rc.register_exporter(exporter, *extensions)`

Register an exporter for specific file extensions.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `exporter` | `Exporter` | required | Exporter instance to register. |
| `*extensions` | `str` | required | Extensions to register (e.g., `".xml"`, `".protobuf"`). |

**Returns:** `None`

**Examples:**

```python
class XmlExporter(Exporter):
    def export(self, config: dict) -> str:
        return dict_to_xml(config)

rc.register_exporter(XmlExporter(), ".xml")
```

### `rc.unregister_exporter(extension)`

Unregister an exporter by extension.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `extension` | `str` | required | The extension to unregister. |

**Returns:** `None`

**Raises:**

| Exception | Condition |
|-----------|-----------|
| `KeyError` | Extension not registered |

**Examples:**

```python
rc.unregister_exporter(extension=".xml")
```

### `rc.supported_exporter_extensions()`

Get all supported export file extensions.

**Parameters:** None

**Returns:** `frozenset[str]` - Supported extensions (lowercase, e.g., `{'.yaml', '.json', '.toml'}`)

**Examples:**

```python
extensions = rc.supported_exporter_extensions()
# frozenset({'.yaml', '.yml', '.json', '.toml'})
```

### `rc.register_loader(loader, *extensions)`

Register a config file loader for specific extensions.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `loader` | `ConfigFileLoader` | required | A `ConfigFileLoader` instance to register. |
| `*extensions` | `str` | required | Extensions to register (e.g., `".ini"`, `".conf"`). |

**Returns:** `None`

**Examples:**

```python
class IniConfigLoader(ConfigFileLoader):
    def load(self, path: Path) -> dict[str, Any]:
        import configparser
        parser = configparser.ConfigParser()
        parser.read(path)
        return {s: dict(parser[s]) for s in parser.sections()}

    def load_with_positions(self, path: Path) -> PositionMap:
        return PositionMap(self.load(path))

rc.register_loader(IniConfigLoader(), ".ini")
```

### `rc.unregister_loader(extension)`

Unregister a config file loader by extension.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `extension` | `str` | required | The extension to unregister. |

**Returns:** `None`

**Raises:**

| Exception | Condition |
|-----------|-----------|
| `KeyError` | Extension not registered |

**Examples:**

```python
rc.unregister_loader(extension=".ini")
```

### `rc.supported_loader_extensions()`

Get all supported loader file extensions.

**Parameters:** None

**Returns:** `frozenset[str]` - Supported extensions (lowercase, e.g., `{'.yaml', '.yml', '.json', '.toml'}`)

**Examples:**

```python
extensions = rc.supported_loader_extensions()
```

### `@rc.resolver(*path)`

Decorator to register a resolver function for use in interpolation expressions.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `*path` | `str` | required | Path components. Accepts multiple arguments (`"db", "lookup"`) or a single delimited string (`"db:lookup"` or `"db.lookup"`). |

**Returns:** Decorator function

**Special Parameters (in decorated function):**
- `_config_` (`dict`): Keyword-only parameter that receives read-only view of current config

**Examples:**

```python
# All equivalent ways to register "db:lookup":
@rc.resolver("db", "lookup")
def lookup1(table: str, id: int) -> dict:
    return database.get(table, id)

@rc.resolver("db:lookup")
def lookup2(table: str, id: int) -> dict:
    return database.get(table, id)

@rc.resolver("db.lookup")
def lookup3(table: str, id: int) -> dict:
    return database.get(table, id)

# Simple resolver
@rc.resolver("uuid")
def gen_uuid() -> str:
    import uuid
    return str(uuid.uuid4())

# Resolver with config access
@rc.resolver("derive")
def derive(path: str, *, _config_: dict) -> Any:
    return _config_.get(path)
```

### `rc.register_resolver(*path, func)`

Register a custom resolver function for use in interpolation expressions.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `*path` | `str` | required | Path components. Accepts multiple arguments (`"db", "lookup"`) or a single delimited string (`"db:lookup"` or `"db.lookup"`). |
| `func` | `Callable[..., Any]` | required | The resolver function to register. |

**Returns:** `None`

**Raises:**

| Exception | Condition |
|-----------|-----------|
| `ValueError` | If path is empty or func is not callable |

**Examples:**

```python
def gen_uuid() -> str:
    import uuid
    return str(uuid.uuid4())

# All equivalent:
rc.register_resolver("uuid", func=gen_uuid)
rc.register_resolver("db", "lookup", func=my_lookup)
rc.register_resolver("db:lookup", func=my_lookup)
rc.register_resolver("db.lookup", func=my_lookup)
```

### `rc.unregister_resolver(*path)`

Unregister a previously registered resolver.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `*path` | `str` | required | Path components. Accepts multiple arguments (`"db", "lookup"`) or a single delimited string (`"db:lookup"` or `"db.lookup"`). |

**Returns:** `None`

**Raises:**

| Exception | Condition |
|-----------|-----------|
| `KeyError` | No resolver with that path exists |

**Examples:**

```python
rc.unregister_resolver("uuid")

# All equivalent ways to unregister "db:lookup":
rc.unregister_resolver("db", "lookup")
rc.unregister_resolver("db:lookup")
rc.unregister_resolver("db.lookup")
```

## Advanced Usage

### Using Classes Directly

For more control, use the underlying classes:

```python
from rconfig import ConfigStore, ConfigValidator, ConfigInstantiator

store = ConfigStore()
store.register(name="model", target=ModelConfig)

validator = ConfigValidator(store)
instantiator = ConfigInstantiator(store, validator)

config = {"_target_": "model", "hidden_size": 256}
result = validator.validate(config)
if result.valid:
    model = instantiator.instantiate(config)
```

### Custom File Loaders

ReausoConfig includes built-in loaders for YAML, JSON, and TOML:

- `YamlConfigLoader` - `.yaml`, `.yml` files
- `JsonConfigLoader` - `.json` files
- `TomlConfigLoader` - `.toml` files (Python 3.11+)

To add support for additional file formats, create a custom loader and register it for specific extensions:

```python
from rconfig import ConfigFileLoader, register_loader
from pathlib import Path
from typing import Any
import configparser

class IniConfigLoader(ConfigFileLoader):
    def load(self, path: Path) -> dict[str, Any]:
        parser = configparser.ConfigParser()
        parser.read(path)
        # Convert to nested dict
        return {s: dict(parser[s]) for s in parser.sections()}

# Register for .ini extension
register_loader(IniConfigLoader(), ".ini")

# Now works with instantiate
model = rc.instantiate(path=Path("config.ini"))
```

## Thread Safety

ReausoConfig is thread-safe for concurrent access. The following operations can be safely called from multiple threads:

- `rc.register()` / `rc.unregister()` - Thread-safe class registration
- `rc.instantiate()` - Thread-safe config loading and instantiation
- `rc.validate()` - Thread-safe validation
- `rc.set_cache_size()` / `rc.clear_cache()` - Thread-safe cache management
- `register_loader()` / `unregister_loader()` - Thread-safe loader registration
- `register_exporter()` / `unregister_exporter()` - Thread-safe exporter registration

**Note:** `rc.known_references()` returns a live view of registrations. Individual read operations are thread-safe, but iteration during concurrent mutation may raise RuntimeError.

## Error Handling

ReausoConfig provides a hierarchy of exceptions:

```
ConfigError (base)
├── ConfigFileError               # File loading issues
├── TargetNotFoundError           # Unknown _target_
├── ValidationError               # Validation failures
│   ├── MissingFieldError             # Required field missing
│   ├── TypeMismatchError             # Wrong type provided
│   ├── AmbiguousTargetError          # Cannot infer type (abstract/multiple impls)
│   ├── TargetTypeMismatchError       # Explicit _target_ wrong type
│   ├── TypeInferenceError            # Inferred type validation failed
│   └── RequiredValueError            # _required_ value not provided
├── CompositionError              # Config composition issues
│   ├── CircularRefError              # Circular _ref_ detected
│   ├── RefResolutionError            # Cannot resolve _ref_ path
│   ├── RefAtRootError                # _ref_ at root level
│   ├── RefInstanceConflictError      # Both _ref_ and _instance_ in same block
│   ├── CircularInstanceError         # Circular _instance_ detected
│   ├── InstanceResolutionError       # Cannot resolve _instance_ path
│   ├── InvalidInnerPathError         # Invalid inner_path for partial instantiation
│   └── MergeError                    # Deep merge failed
├── InterpolationError            # Interpolation issues
│   ├── InterpolationSyntaxError      # Invalid ${...} syntax
│   ├── InterpolationResolutionError  # Path/env not found
│   ├── CircularInterpolationError    # Circular ${...} reference
│   ├── EnvironmentVariableError      # Required env var not set
│   └── ResolverError                 # Custom resolver issues
│       ├── UnknownResolverError          # Resolver path not registered
│       └── ResolverExecutionError        # Resolver function raised exception
├── OverrideError                 # Override-related errors
│   ├── InvalidOverridePathError      # Override path doesn't exist
│   └── InvalidOverrideSyntaxError    # Override string malformed
└── InstantiationError            # Object creation failed
```

Example error handling:

```python
from rconfig import (
    ConfigFileError, ValidationError, InstantiationError,
    AmbiguousTargetError, TypeInferenceError,
    UnknownResolverError, ResolverExecutionError
)

try:
    model = rc.instantiate(path=Path("config.yaml"))
except AmbiguousTargetError as e:
    print(f"Cannot infer type: {e}")
    print(f"Available targets: {e.available_targets}")
except TypeInferenceError as e:
    print(f"Inferred type validation failed: {e}")
except UnknownResolverError as e:
    print(f"Unknown resolver: {e}")
except ResolverExecutionError as e:
    print(f"Resolver failed: {e}")
except ConfigFileError as e:
    print(f"Could not load file: {e}")
except ValidationError as e:
    print(f"Invalid config: {e}")
except InstantiationError as e:
    print(f"Could not create object: {e}")
```

## Pros and Cons

### Pros

- **Minimal coupling**: Only your startup code imports rconfig
- **Simple API**: Just `register`, `validate`, `instantiate`
- **Lazy instantiation**: Defer expensive initialization until first access
- **Type validation**: Catches type mismatches before instantiation
- **Implicit target inference**: Omit `_target_` for concrete nested types
- **Config composition**: Load and merge configs from files with `_ref_`
- **Instance sharing**: Share objects across config with `_instance_`
- **Interpolation**: Reference values with `${...}`, env vars, and full expressions
- **Provenance tracking**: Debug where each config value originated
- **Lightweight**: Focused feature set, no bloat
- **Pure Python output**: Instantiated objects have no framework dependency

## License

MIT License - see LICENSE file for details.
