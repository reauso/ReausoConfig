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

### `rc.validate(path)`

Validate a config file without instantiating (dry-run).

```python
result = rc.validate(Path("config.yaml"))
if result.valid:
    print("Config is valid!")
else:
    for error in result.errors:
        print(error)
```

### `rc.instantiate(path, expected_type=None, *, overrides=None, cli_overrides=True)`

Load, validate, and instantiate a config file.

```python
# Basic usage (CLI overrides enabled by default)
model = rc.instantiate(Path("config.yaml"))

# Type-safe version (for IDE autocompletion)
model = rc.instantiate(Path("config.yaml"), ModelConfig)

# With programmatic overrides
model = rc.instantiate(Path("config.yaml"), overrides={"model.lr": 0.01})

# Disable CLI overrides (for tests)
model = rc.instantiate(Path("config.yaml"), cli_overrides=False)
```

### `rc.known_references()`

Get a read-only view of all registered references.

```python
refs = rc.known_references()
for name, ref in refs.items():
    print(f"{name}: {ref.target_class}")
```

### `rc.get_provenance(path)`

Track the origin of each config value (useful for debugging):

```python
prov = rc.get_provenance(Path("trainer.yaml"))
print(prov)  # Shows config with file:line annotations

entry = prov.get("model.dropout")
print(f"{entry.file}:{entry.line}")  # trainer.yaml:5
if entry.overrode:
    print(f"Overrode: {entry.overrode}")  # models/resnet.yaml:3
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
│   └── TypeInferenceError            # Inferred type validation failed
├── CompositionError              # Config composition issues
│   ├── CircularRefError              # Circular _ref_ detected
│   ├── RefResolutionError            # Cannot resolve _ref_ path
│   ├── RefAtRootError                # _ref_ at root level
│   ├── RefInstanceConflictError      # Both _ref_ and _instance_ in same block
│   ├── CircularInstanceError         # Circular _instance_ detected
│   ├── InstanceResolutionError       # Cannot resolve _instance_ path
│   └── MergeError                    # Deep merge failed
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
- **Type validation**: Catches type mismatches before instantiation
- **Implicit target inference**: Omit `_target_` for concrete nested types
- **Config composition**: Load and merge configs from files with `_ref_`
- **Instance sharing**: Share objects across config with `_instance_`
- **Provenance tracking**: Debug where each config value originated
- **Lightweight**: Focused feature set, no bloat
- **Pure Python output**: Instantiated objects have no framework dependency

### Cons

- **Early stage**: Some features from the vision are not yet implemented
- **No interpolation**: Cannot reference other config values with `${...}` (planned)

## Roadmap

See [VISION.md](VISION.md) for planned features including:

- Value interpolation (`${model.learning_rate}`)
- Environment variable support
- Config groups

## License

MIT License - see LICENSE file for details.
