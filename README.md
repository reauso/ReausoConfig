# ReausoConfig

A lightweight Python configuration library that turns YAML files into Python objects with minimal runtime coupling.

## What is ReausoConfig?

ReausoConfig provides a simple way to load YAML configuration files and instantiate Python objects from them. Unlike heavier frameworks, your application code doesn't need to know about ReausoConfig—only the startup/registration code does.

After instantiation, you get pure Python objects with no framework dependency.

## Installation

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

### 2. Create a YAML config file

```yaml
# config.yaml
_target_: model
hidden_size: 256
dropout: 0.2
```

The `_target_` key maps to a registered class name.

### 3. Register and instantiate

```python
import rconfig as rc
from pathlib import Path

# Register your class
rc.register("model", ModelConfig)

# Instantiate the object (validates automatically)
model = rc.instantiate(Path("config.yaml"), ModelConfig)
print(model.hidden_size)  # 256
print(model.dropout)      # 0.2

# Optional: validate without instantiating (dry-run)
result = rc.validate(Path("config.yaml"))
if not result.valid:
    for error in result.errors:
        print(error)
```

## Core Concepts

### The `_target_` Key

Every config must have a `_target_` field that maps to a registered class name:

```yaml
_target_: my_model  # Must match a registered name
learning_rate: 0.001
```

### ConfigStore

The registry that maps string names to Python classes:

```python
rc.register("my_model", MyModel)
rc.register("my_dataset", MyDataset)
```

### Validation

Before instantiation, configs are validated for:
- Required fields (parameters without defaults)
- Type compatibility
- Target existence in registry

### CLI Overrides

Override config values from the command line:

```bash
python main.py model.hidden_size=512 epochs=20
```

Or programmatically:

```python
trainer = rc.instantiate(
    Path("config.yaml"),
    overrides={"model.hidden_size": 512, "epochs": 20},
)
```

#### Override Syntax

| Syntax | Example | Description |
|--------|---------|-------------|
| Dot notation | `model.lr=0.01` | Set nested value |
| List indexing | `layers[0].size=128` | Set list element |
| Add to list | `+callbacks=logger` | Append to list |
| Remove key | `~dropout` | Delete key |

#### Disabling CLI Overrides

For tests or library usage, disable automatic CLI parsing:

```python
model = rc.instantiate(path, cli_overrides=False)
```

#### Override Priority

When both programmatic and CLI overrides are provided, CLI wins:

```python
# CLI: python main.py model.lr=0.05
trainer = rc.instantiate(path, overrides={"model.lr": 0.01})
# Result: model.lr = 0.05 (CLI wins)
```

### Partial Instantiation

Instantiate only a specific section of the config tree:

```python
# Load trainer config, but only instantiate the model
model = rc.instantiate(Path("trainer.yaml"), inner_path="model")

# Works with nested paths
encoder = rc.instantiate(Path("trainer.yaml"), inner_path="model.encoder")

# And list indices
first_callback = rc.instantiate(Path("trainer.yaml"), inner_path="callbacks[0]")
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
model = rc.instantiate(Path("trainer.yaml"), inner_path="model")
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
service = rc.instantiate(Path("app.yaml"), inner_path="services.api")
print(service.cache.size)  # 100
```

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
model = rc.instantiate(Path("config.yaml"))

# Provide required values via overrides
model = rc.instantiate(
    Path("config.yaml"),
    overrides={"api_key": "secret123", "database_url": "postgres://..."},
)

# Or validate first to check what's missing
result = rc.validate(Path("config.yaml"))
if not result.valid:
    for error in result.errors:
        print(error)  # Shows which _required_ values are missing
```

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

#### Implicit Target Inference

When a nested config field has a concrete type hint (a class that is registered with no subclasses), the `_target_` can be omitted and will be automatically inferred:

```python
@dataclass
class ModelConfig:
    hidden_size: int

@dataclass
class TrainerConfig:
    model: ModelConfig  # Concrete type - _target_ can be inferred
    epochs: int

rc.register("model", ModelConfig)
rc.register("trainer", TrainerConfig)
```

```yaml
# _target_ for model is optional here
_target_: trainer
model:
  hidden_size: 256  # No _target_ needed - inferred from type hint
epochs: 10
```

**When `_target_` is required:**
- Abstract classes (cannot be instantiated directly)
- Base classes with multiple registered subclasses (ambiguous)

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

rc.register("transformer", TransformerEncoder)
rc.register("lstm", LSTMEncoder)
rc.register("model", Model)
```

```yaml
_target_: model
encoder:
  _target_: transformer  # Required - BaseEncoder is abstract
  layers: 6
```

#### Auto-registration of Explicit Targets

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

rc.register("trainer", TrainerConfig)
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

**Auto-registration requirements:**
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
- `models/resnet.yaml` - Relative to current file
- `./local.yaml` - Explicit relative
- `../shared/base.yaml` - Parent directory
- `/models/resnet.yaml` - Absolute from config root

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
- `shared_cache` - Relative to config root
- `/shared.database` - Absolute from composed root
- `databases[0]` - List indexing supported

**Special values:**
- `_instance_: null` - Passes `None` to constructor

### Lazy Instantiation

Delay object creation until first attribute access. Useful for expensive initialization (loading models, database connections) that may not always be used.

#### Global Lazy Mode

Make all nested configs lazy:

```python
# All nested objects delay __init__ until first access
trainer = rc.instantiate(Path("trainer.yaml"), lazy=True)

# trainer.model is lazy - __init__ not called yet
print(rc.is_lazy_proxy(trainer.model))  # True

# Accessing any attribute triggers initialization
print(trainer.model.hidden_size)  # NOW model.__init__ is called
print(rc.is_lazy_proxy(trainer.model))  # False
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
trainer = rc.instantiate(Path("trainer.yaml"))
print(rc.is_lazy_proxy(trainer.model))      # True - lazy
print(rc.is_lazy_proxy(trainer.optimizer))  # False - eager
```

**Note:** `_lazy_: true` only affects that specific field, not its children (non-cascading).

#### Checking Lazy Status

```python
from rconfig import is_lazy_proxy, force_initialize

trainer = rc.instantiate(Path("trainer.yaml"), lazy=True)

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

| Operation | Works? | Notes |
|-----------|--------|-------|
| `isinstance(obj, MyClass)` | ✅ Yes | Proxy is a subclass of your class |
| `obj.attribute` | ✅ Yes | Triggers init, then returns value |
| `obj.method()` | ✅ Yes | Triggers init, then calls method |
| `hasattr(obj, 'attr')` | ✅ Yes | Triggers init, then checks |
| `len(obj)` | ✅ Yes | Triggers init, then calls `__len__` |
| `for x in obj` | ✅ Yes | Triggers init, then iterates |
| `obj[key]` | ✅ Yes | Triggers init, then indexes |
| `obj()` | ✅ Yes | Triggers init, then calls `__call__` |
| `dataclasses.asdict(obj)` | ✅ Yes | Triggers init, then converts |
| `str(obj)` / `repr(obj)` | ✅ Yes | Triggers init, then formats |

#### Known Limitations

These edge cases behave differently from regular objects:

| Operation | Behavior | Workaround |
|-----------|----------|------------|
| `type(obj)` | Returns proxy class | Use `isinstance()` instead |
| `obj.__class__` | Returns proxy class | Use `isinstance()` instead |
| `obj.__class__ == MyClass` | Returns `False` | Use `isinstance(obj, MyClass)` |

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

| Syntax | Example | Description |
|--------|---------|-------------|
| Absolute | `${/model.lr}` | From root of composed config |
| Relative | `${./local.value}` | From current document root |
| Implicit | `${model.lr}` | Same as relative |
| Parent | `${../sibling.value}` | Parent-relative path |

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
b: ${/a}  # Circular: a → b → a
```

### Provenance Tracking

Track the origin of every config value - essential for debugging complex configs.

#### Basic Usage

```python
prov = rc.get_provenance(Path("trainer.yaml"))
print(prov)  # Shows config with file:line annotations

# Example output:
# /model.layers = 50
#   trainer.yaml:5
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

| Preset | Shows | Use Case |
|--------|-------|----------|
| `minimal()` | paths, files, lines | Quick overview |
| `compact()` | + values, source type | Debugging values |
| `full()` | everything (default) | Complete tracing |

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

| Source | Marker | Description |
|--------|--------|-------------|
| file | (none) | Regular config file |
| cli | `CLI:` | Command-line override |
| env | `env:` | Environment variable |
| programmatic | `programmatic:` | Set via Python code |

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

Register a target class under a unique name.

```python
rc.register("model", ModelConfig)
```

### `rc.unregister(name)`

Remove a previously registered reference.

```python
rc.unregister("model")  # Raises KeyError if not found
```

### `rc.validate(path, *, overrides=None, cli_overrides=True)`

Validate a config file without instantiating (dry-run). Also checks that all `_required_` values have been satisfied.

```python
result = rc.validate(Path("config.yaml"))
if result.valid:
    print("Config is valid!")
else:
    for error in result.errors:
        print(error)

# With overrides to satisfy _required_ values
result = rc.validate(
    Path("config.yaml"),
    overrides={"api_key": "secret123"},
)
```

### `rc.instantiate(path, expected_type=None, *, inner_path=None, overrides=None, cli_overrides=True, lazy=False)`

Load, validate, and instantiate a config file.

```python
# Basic usage (CLI overrides enabled by default)
model = rc.instantiate(Path("config.yaml"))

# Type-safe version (for IDE autocompletion)
model = rc.instantiate(Path("config.yaml"), ModelConfig)

# Partial instantiation - only instantiate a section
model = rc.instantiate(Path("trainer.yaml"), inner_path="model")
encoder = rc.instantiate(Path("trainer.yaml"), inner_path="model.encoder")

# With programmatic overrides
model = rc.instantiate(Path("config.yaml"), overrides={"model.lr": 0.01})

# Combine partial with overrides
model = rc.instantiate(
    Path("trainer.yaml"),
    inner_path="model",
    overrides={"model.hidden_size": 512},
)

# Disable CLI overrides (for tests)
model = rc.instantiate(Path("config.yaml"), cli_overrides=False)

# With lazy instantiation (all nested configs are lazy)
model = rc.instantiate(Path("config.yaml"), lazy=True)
```

**Parameters:**
- `lazy`: If `True`, all nested configs are lazily instantiated. Objects delay `__init__` until first attribute access. Default: `False`.

### `rc.known_references()`

Get a read-only view of all registered references.

```python
refs = rc.known_references()
for name, ref in refs.items():
    print(f"{name}: {ref.target_class}")
```

### `rc.get_provenance(path)`

Get provenance tracking for a config file, showing where each value originated.

Returns a `Provenance` object with methods:
- `get(path)` - Get `ProvenanceEntry` for a specific config path
- `items()` - Iterate all (path, entry) tuples
- `format()` - Get fluent builder for customized output
- `trace(path)` - Get full `ProvenanceNode` tree for a path
- `to_dict()` - Export as dictionary

See [Provenance Tracking](#provenance-tracking) for full documentation.

```python
prov = rc.get_provenance(Path("trainer.yaml"))

# Print with default formatting
print(prov)

# Use presets
print(prov.format().minimal())

# Filter output
print(prov.format().for_path("/model.*"))

# Access specific entry
entry = prov.get("model.lr")
print(f"{entry.file}:{entry.line}")
```

### `rc.set_cache_size(size)`

Configure the LRU cache for loaded config files:

```python
rc.set_cache_size(100)  # Cache up to 100 files
rc.set_cache_size(0)    # Unlimited (default)
```

### `rc.clear_cache()`

Clear the config file cache:

```python
rc.clear_cache()
```

### `rc.is_lazy_proxy(obj)`

Check if an object is an uninitialized lazy proxy.

```python
model = rc.instantiate(Path("config.yaml"), lazy=True)
print(rc.is_lazy_proxy(model))  # True
_ = model.some_attr  # triggers init
print(rc.is_lazy_proxy(model))  # False
```

### `rc.force_initialize(obj)`

Force initialization of a lazy proxy without accessing attributes. No-op for regular objects.

```python
model = rc.instantiate(Path("config.yaml"), lazy=True)
rc.force_initialize(model)  # model.__init__ called now
```

## Advanced Usage

### Using Classes Directly

For more control, use the underlying classes:

```python
from rconfig import ConfigStore, ConfigValidator, ConfigInstantiator

store = ConfigStore()
store.register("model", ModelConfig)

validator = ConfigValidator(store)
instantiator = ConfigInstantiator(store, validator)

config = {"_target_": "model", "hidden_size": 256}
result = validator.validate(config)
if result.valid:
    model = instantiator.instantiate(config)
```

### Custom File Loaders

Add support for additional file formats:

```python
from rconfig.loaders import ConfigFileLoader, register_loader
from pathlib import Path
from typing import Any
import json

class JsonConfigLoader(ConfigFileLoader):
    def load(self, path: Path) -> dict[str, Any]:
        with open(path) as f:
            return json.load(f)

    def supports(self, path: Path) -> bool:
        return path.suffix.lower() == '.json'

register_loader(JsonConfigLoader())
```

## Thread Safety

ReausoConfig is thread-safe for concurrent access. The following operations can be safely called from multiple threads:

- `rc.register()` / `rc.unregister()` - Thread-safe class registration
- `rc.instantiate()` - Thread-safe config loading and instantiation
- `rc.validate()` - Thread-safe validation
- `rc.set_cache_size()` / `rc.clear_cache()` - Thread-safe cache management
- `register_loader()` / `unregister_loader()` - Thread-safe loader registration

**Note:** `rc.known_references()` returns a snapshot of registrations at call time. Changes made after the call are not reflected in the returned mapping.

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
│   └── EnvironmentVariableError      # Required env var not set
├── OverrideError                 # Override-related errors
│   ├── InvalidOverridePathError      # Override path doesn't exist
│   └── InvalidOverrideSyntaxError    # Override string malformed
└── InstantiationError            # Object creation failed
```

Example error handling:

```python
from rconfig import (
    ConfigFileError, ValidationError, InstantiationError,
    AmbiguousTargetError, TypeInferenceError
)

try:
    model = rc.instantiate(Path("config.yaml"))
except AmbiguousTargetError as e:
    print(f"Cannot infer type: {e}")
    print(f"Available targets: {e.available_targets}")
except TypeInferenceError as e:
    print(f"Inferred type validation failed: {e}")
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

### Cons

- **Early stage**: Some features from the vision are not yet implemented

## Roadmap

See [VISION.md](VISION.md) for planned features including:

- Config groups

## License

MIT License - see LICENSE file for details.
