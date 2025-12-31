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

### `rc.instantiate(path, expected_type=None)`

Load, validate, and instantiate a config file.

```python
# Basic usage
model = rc.instantiate(Path("config.yaml"))

# Type-safe version (for IDE autocompletion)
model = rc.instantiate(Path("config.yaml"), ModelConfig)
```

### `rc.known_references()`

Get a read-only view of all registered references.

```python
refs = rc.known_references()
for name, ref in refs.items():
    print(f"{name}: {ref.target_class}")
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
├── ConfigFileError           # File loading issues
├── TargetNotFoundError       # Unknown _target_
├── ValidationError           # Validation failures
│   ├── MissingFieldError         # Required field missing
│   ├── TypeMismatchError         # Wrong type provided
│   ├── AmbiguousTargetError      # Cannot infer type (abstract/multiple impls)
│   ├── TargetTypeMismatchError   # Explicit _target_ wrong type
│   └── TypeInferenceError        # Inferred type validation failed
└── InstantiationError        # Object creation failed
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
- **Lightweight**: Focused feature set, no bloat
- **Pure Python output**: Instantiated objects have no framework dependency

### Cons

- **Early stage**: Some features from the vision are not yet implemented
- **No CLI overrides**: Cannot override config values from command line (planned)
- **No interpolation**: Cannot reference other config values with `${...}` (planned)
- **No config composition**: Cannot merge multiple config files (planned)

## Roadmap

See [VISION.md](VISION.md) for planned features including:

- CLI override system (`model.lr=0.01`)
- Value interpolation (`${model.learning_rate}`)
- Config composition and defaults
- Environment variable support
- Config groups

## License

MIT License - see LICENSE file for details.
