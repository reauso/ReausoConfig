# ReausoConfig - Vision Document

## What is ReausoConfig?

A lightweight Python configuration library that turns YAML files into Python objects with **minimal runtime dependency**. Unlike Hydra, your application code doesn't need to know about ReausoConfig—only the startup/registration code does.

---

## The Problem We're Solving

**Hydra's Limitations:**
- Applications become tightly coupled to Hydra
- If Hydra breaks or changes, your application breaks
- Dependency injection requires custom implementation per-project
- Complex feature set with many things you don't need (multirun, sweepers, output directories, etc.)

**Our Solution:**
- Registration happens once in `main()`
- After instantiation, you get pure Python objects with no framework dependency
- Simple, focused feature set
- Modern Python (3.11+) makes this possible with better introspection and typing

---

## What Users Can Do

### ✓ 1. Define Configuration in YAML

```yaml
# config/model.yaml
_target_: my_model
learning_rate: 0.001
hidden_size: 256
dropout: 0.1
```

The `_target_` key maps to a class registered in the ConfigStore.

### ✓ 2. Register Classes Once

```python
# main.py - the ONLY place that depends on ReausoConfig
from rconfig import ConfigStore, load_config

store = ConfigStore()
store.register("my_model", MyModel)
store.register("my_dataset", MyDataset)

config = load_config("config/", store)
app = config.instantiate()

# From here on, app is pure Python - no rconfig dependency
run_training(app.model, app.dataset)
```

### ✓ 3. Override via Command Line

```bash
python main.py model.learning_rate=0.01 dataset.batch_size=64
```

### ✓ 4. Compose Configurations

```yaml
# config/trainer.yaml
_target_: trainer
model:
  _ref_: models/resnet.yaml   # Load from file
  pretrained: true            # Override: merged on top
optimizer:
  _ref_: optimizers/adam.yaml
  lr: 0.01
```

### ✓ 5. Reference Values Across Config

```yaml
optimizer:
  lr: ${/model.learning_rate}  # Reference another value
  scaled_lr: ${/model.learning_rate * 10}  # With expressions

dataset:
  path: ${env:DATA_PATH}       # Environment variable
  cache: ${env:CACHE_DIR,/tmp} # With default value
```

### ✓ 6. Include Other Files

```yaml
# Use _ref_ to include and merge configs from other files
model:
  _ref_: models/resnet.yaml
dataset:
  _ref_: datasets/imagenet.yaml
```

### 7. Provide Runtime Parameters

```yaml
# Some values can't be known at config time
_target_: data_loader
path: /data
num_workers: _RUNTIME_   # Must be passed when instantiating
```

```python
app = config.instantiate(num_workers=os.cpu_count())
```

---

## Core Features

### ✓ Minimal Dependency
- Only `main.py` imports ReausoConfig
- All domain classes are pure Python
- Instantiated objects have no framework coupling

### ✓ Type-Safe Configuration
- Validates config arguments against class signatures
- Reports type mismatches before instantiation
- Uses Python's `inspect` module for introspection

### ✓ Hierarchical Configs
- ✓ Nest configs within configs
- ✓ Include external files via `_ref_`
- ✓ Compose from referenced configs
- ✓ Share instances via `_instance_`

### ✓ CLI Override System
- ✓ Dot notation for nested values: `model.optimizer.lr=0.01`
- ✓ List indexing: `model.layers[0].size=128`
- ✓ Add/remove operations: `+callbacks=logger`, `~callbacks`

### ✓ Interpolation
- ✓ Reference other config values: `${/path.to.value}`, `${./relative}`, `${../parent}`
- ✓ Environment variables: `${env:VAR}` or `${env:VAR,default}`
- ✓ Full expression support: arithmetic, comparisons, boolean, list operations
- ✓ Circular reference detection
- ✓ Provenance tracking for interpolated values

### ✓ Validation
- ✓ Schema validation (valid YAML)
- ✓ Target validation (`_target_` exists in registry)
- ✓ Signature validation (all required params provided)
- ✓ Type validation (argument types match)

### ✓ Rich Error Messages
```
ConfigurationError: Missing required parameter 'hidden_size'

  File: config/model.yaml, line 5
  Target: my_model (MyModel)

  Expected: hidden_size (int, required)
  Provided: dropout=0.1
```

---

## Potential Additional Features

### Config Groups
Organize configs by category with easy swapping:
```
config/
├── model/
│   ├── resnet.yaml
│   └── vgg.yaml
├── dataset/
│   ├── imagenet.yaml
│   └── cifar.yaml
└── config.yaml
```
```bash
python main.py model=vgg dataset=cifar
```

### (partial) Dry-Run Mode
Validate and preview what would be instantiated without actually doing it:
```python
config.validate()  # ✓ Check everything is valid
config.preview()   # Show instantiation plan
```

### Serialization
Dump instantiated config back to YAML:
```python
config.to_yaml("output_config.yaml")
```

### IDE Support
Generate JSON Schema from registered classes for YAML autocompletion in VSCode/PyCharm.

### Partial Instantiation
Instantiate only part of the config tree:
```python
model = config.instantiate("model")  # Only instantiate model section
```

### Lazy Instantiation
Objects created on first access rather than all at once:
```python
config = load_config("config/", lazy=True)
# Nothing instantiated yet
model = config.model  # Now model is created
```

### Factory Support
Classes that create other objects based on config:
```yaml
_target_: model_factory
model_type: resnet
num_layers: 50
```

### Config Inheritance
One config extends another:
```yaml
_extends_: base_model.yaml
hidden_size: 512  # Override base
```

---

## Challenges to Address

### ✓ 1. Dependency Resolution
When config A references config B which references config C:
- ✓ Topological sort determines instantiation order
- ✓ Circular `_ref_` and `_instance_` references are detected and error
- ✓ `_ref_` loads config (new instance), `_instance_` shares object

### 2. Runtime Parameters
Values that can't be in config files (e.g., `num_workers = cpu_count()`):
- How do we mark them in YAML?
- How do we pass them during instantiation?
- What if a nested config needs runtime params?

### 3. Type Coercion
YAML gives us strings, ints, lists, dicts. But classes may need:
- Enums
- Path objects
- Custom types
- Nested dataclasses

How aggressive should automatic conversion be?

### 4. Error Locality
When something fails:
- Which file caused it?
- Which line?
- What was the full path to the problematic value?

YAML parsing loses line information—how do we preserve it?

### ✓ 5. Interpolation Timing
When to resolve `${references}`:
- ✓ Resolved after overrides, before validation
- ✓ Topological resolution handles dependencies
- ✓ Circular references detected and reported

### ✓ 6. Config vs Instance Identity
```yaml
# _ref_ creates separate instances
trainer:
  model:
    _ref_: model.yaml    # New instance
evaluator:
  model:
    _ref_: model.yaml    # Another new instance

# _instance_ shares the same object
shared_model:
  _target_: model
  hidden_size: 256
trainer:
  model:
    _instance_: shared_model  # Same object
evaluator:
  model:
    _instance_: shared_model  # Same object as trainer.model
```

✓ `_ref_` creates new instances, `_instance_` shares objects.

### 7. Backwards Compatibility
As the library evolves:
- How do we version config formats?
- What happens when users upgrade?
- Can old configs still work?

---

## What We're NOT Building

To keep the library focused and simple:

- **No multirun/sweeping** - Use external tools for hyperparameter search
- **No automatic output directories** - Let users manage their own outputs
- **No job launching** - Not a workflow orchestrator
- **No distributed config** - Single-machine focus
- **No GUI** - CLI and programmatic only

---

## Design Principles

1. **Explicit over implicit** - Clear mapping between config and code
2. **Fail fast, fail clearly** - Validate early with helpful errors
3. **Minimal magic** - Behavior should be predictable
4. **Composition over inheritance** - Build configs from pieces
5. **Pure Python output** - No framework lock-in after instantiation

---

## Open Questions

1. **Instantiation Strategy**: Eager (all at once) vs lazy (on demand)?
2. **Singleton Behavior**: Should same config path create same instance?
3. **Type Coercion**: Automatic conversion vs explicit converters?
4. **Thread Safety**: Multi-threaded registration/instantiation?
5. **Async Support**: Async factory functions?

---

## Comparison with Alternatives

| Aspect | Hydra | OmegaConf | Pydantic | ReausoConfig |
|--------|-------|-----------|----------|--------------|
| Primary focus | Full framework | Config containers | Validation | Object instantiation |
| Runtime coupling | High | Medium | Low | Minimal |
| Learning curve | Steep | Medium | Medium | Low |
| Features | Many | Medium | Many | Focused |
| Instantiation | Built-in | Manual | Manual | Built-in |
| CLI overrides | Yes | No | No | Yes |

---

*Vision Document v1.1 - 2026-01-01*
