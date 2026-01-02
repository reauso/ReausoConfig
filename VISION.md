# rconfig Vision: Future Features Roadmap

This document outlines potential features for rconfig based on analysis of state-of-the-art configuration libraries including Hydra, OmegaConf, Pydantic Settings, Dynaconf, Confuse, and ConfigArgParse.

---

## Table of Contents

1. [Custom Resolvers](#1-custom-resolvers)
2. [Config Export / Serialization](#2-config-export--serialization)
3. [Built-in TOML and JSON Loaders](#3-built-in-toml-and-json-loaders)
4. [Frozen Config Mode](#4-frozen-config-mode)
5. [Structured Config Schemas](#5-structured-config-schemas)
6. [Deprecation Warnings](#6-deprecation-warnings)
7. [Defaults List / Composition Groups](#7-defaults-list--composition-groups)
8. [Multi-Environment Profiles](#8-multi-environment-profiles)
9. [Config Diffing](#9-config-diffing)
10. [Callbacks and Hooks](#10-callbacks-and-hooks)
11. [XDG Base Directory Support](#11-xdg-base-directory-support)

---

## 1. Custom Resolvers ✅

**Adopted by:** OmegaConf, Hydra, Dynaconf

**Status:** Implemented

### Description

Custom resolvers allow users to register their own functions that can be invoked within interpolation expressions. This transforms the configuration system from a static value store into a dynamic, extensible computation engine. Users can define domain-specific logic that gets evaluated at config resolution time, enabling powerful patterns like dynamic path construction, timestamp generation, or integration with external systems.

### Why It Adds Value

- **Extensibility**: Users can extend the interpolation system without modifying rconfig's source code
- **Domain-Specific Logic**: Enable patterns specific to ML, web development, DevOps, etc.
- **Reduces Boilerplate**: Common patterns (timestamps, UUIDs, paths) become one-liners in config
- **Keeps Configs Declarative**: Logic lives in Python, configs remain readable YAML

### Usage Example

```python
import rconfig
from datetime import datetime
from pathlib import Path
import uuid

# Register custom resolvers
rconfig.register_resolver("now", lambda fmt="%Y-%m-%d": datetime.now().strftime(fmt))
rconfig.register_resolver("uuid", lambda: str(uuid.uuid4()))
rconfig.register_resolver("project_root", lambda: str(Path(__file__).parent))
rconfig.register_resolver("join_path", lambda *parts: str(Path(*parts)))

# Resolver with arguments
rconfig.register_resolver("multiply", lambda x, y: x * y)
```

```yaml
# config.yaml
experiment:
  # No-argument resolver
  id: ${uuid}

  # Resolver with format argument
  timestamp: ${now:%Y-%m-%d_%H-%M-%S}

  # Path construction
  output_dir: ${join_path:${project_root},outputs,${now:%Y-%m-%d}}

  # Arithmetic resolver
  total_steps: ${multiply:${epochs},${steps_per_epoch}}

model:
  # Combine with existing interpolation
  checkpoint: ${project_root}/checkpoints/${experiment.id}.pt
```

```python
config = rconfig.instantiate("config.yaml")
print(config.experiment.id)          # "a1b2c3d4-e5f6-..."
print(config.experiment.timestamp)   # "2024-01-15_14-30-22"
print(config.experiment.output_dir)  # "/home/user/project/outputs/2024-01-15"
```

### Advanced: Resolver with Context Access

```python
# Resolver that can access other config values
@rconfig.resolver("derive_from")
def derive_from(path: str, *, _config_: dict) -> Any:
    """Access other config values within a resolver."""
    return rconfig.get_value(_config_, path)
```

---

## 2. Config Export / Serialization

**Adopted by:** OmegaConf, Dynaconf, Pydantic Settings

### Description

Config export allows users to serialize a fully-resolved configuration back to various formats (dict, YAML, JSON, TOML). After all interpolations are evaluated, references resolved, and overrides applied, users can capture the final "flattened" configuration. This is essential for debugging, reproducibility, and sharing configurations.

### Why It Adds Value

- **Debugging**: See exactly what values were computed after all interpolations
- **Reproducibility**: Save the exact config used for an experiment/run
- **Sharing**: Export configs for documentation or sharing with team members
- **Diffing**: Compare configurations between runs (enables feature #9)
- **Caching**: Store resolved configs to avoid recomputation

### Usage Example

```python
import rconfig

# Export to Python dict (fully resolved)
config_dict = rconfig.to_dict("config.yaml")
print(config_dict)
# {
#     "model": {"lr": 0.001, "hidden_size": 256},
#     "data": {"path": "/data/train.csv", "batch_size": 32}
# }

# Export to YAML string
yaml_str = rconfig.to_yaml("config.yaml")
print(yaml_str)
# model:
#   lr: 0.001
#   hidden_size: 256
# data:
#   path: /data/train.csv
#   batch_size: 32

# Export to YAML file
rconfig.to_yaml("config.yaml", output_path="resolved_config.yaml")

# Export to JSON
json_str = rconfig.to_json("config.yaml", indent=2)

# Export with overrides applied
config_dict = rconfig.to_dict(
    "config.yaml",
    overrides={"model.lr": 0.01}
)

# Export only a section
model_dict = rconfig.to_dict("config.yaml", inner_path="model")
```

### Integration with Instantiate

```python
# After instantiation, export the config that was used
config = rconfig.instantiate("config.yaml", overrides={"model.lr": 0.01})

# Get the resolved config dict from the instantiation
resolved = rconfig.last_resolved_config()
# or
resolved = rconfig.to_dict("config.yaml", overrides={"model.lr": 0.01})

# Save for reproducibility
with open("experiment_config.yaml", "w") as f:
    f.write(rconfig.to_yaml("config.yaml", overrides={"model.lr": 0.01}))
```

---

## 3. Built-in TOML and JSON Loaders

**Adopted by:** Standard across all configuration libraries

### Description

While rconfig has a plugin system for custom loaders, shipping built-in support for TOML and JSON makes the library immediately useful for projects using these formats. TOML has become Python's de-facto standard for project configuration (pyproject.toml), and JSON is ubiquitous across the software industry.

### Why It Adds Value

- **Zero Configuration**: Works out of the box with common formats
- **Modern Python Standard**: TOML is used by pip, poetry, black, pytest, etc.
- **Interoperability**: JSON configs from JavaScript/web ecosystems work directly
- **Migration Path**: Easy to adopt rconfig in existing projects without converting files

### Usage Example

```toml
# config.toml
[model]
name = "resnet50"
learning_rate = 0.001
layers = [64, 128, 256]

[model.optimizer]
_target_ = "Adam"
weight_decay = 0.01

[data]
path = "/data/imagenet"
batch_size = 32
augmentations = ["flip", "rotate", "crop"]
```

```json
// config.json
{
  "model": {
    "name": "resnet50",
    "learning_rate": 0.001,
    "_target_": "ResNet"
  },
  "data": {
    "path": "/data/imagenet",
    "batch_size": 32
  }
}
```

```python
import rconfig

# Automatic format detection by extension
model = rconfig.instantiate("config.toml", expected_type=Model)
model = rconfig.instantiate("config.json", expected_type=Model)

# Explicit format specification
model = rconfig.instantiate("config.cfg", format="toml")

# Mixed format composition (YAML referencing TOML)
# config.yaml
# model:
#   _ref_: ./model_config.toml
#   learning_rate: 0.01  # Override TOML value
```

### Cross-Format References

```yaml
# main.yaml - Can reference TOML and JSON files
defaults:
  _ref_: ./defaults.toml

model:
  _ref_: ./models/resnet.json

data:
  _ref_: ./data_config.toml
  batch_size: 64  # Override
```

---

## 4. Frozen Config Mode

**Adopted by:** OmegaConf, Pydantic (frozen models)

### Description

Frozen config mode makes configuration objects immutable after instantiation. Any attempt to modify a frozen config raises an error. This prevents accidental mutations that could lead to subtle bugs, especially in long-running applications or when configs are passed between components.

### Why It Adds Value

- **Bug Prevention**: Catches accidental config modifications at runtime
- **Reproducibility**: Guarantees config stays constant throughout execution
- **Thread Safety**: Immutable objects are inherently thread-safe
- **Intent Clarity**: Makes it explicit that configs should not change
- **Debugging**: Mutations are caught immediately, not discovered later

### Usage Example

```python
import rconfig

# Freeze at instantiation time
config = rconfig.instantiate("config.yaml", freeze=True)

# Attempting to modify raises an error
config.model.lr = 0.01  # Raises FrozenConfigError!

# Attempting to add new keys raises an error
config.model.new_param = 42  # Raises FrozenConfigError!

# Attempting to delete raises an error
del config.model.dropout  # Raises FrozenConfigError!
```

### Selective Freezing

```python
# Freeze only specific sections
config = rconfig.instantiate("config.yaml")
rconfig.freeze(config.model)  # Only model section is frozen
rconfig.freeze(config.data)   # Now data is also frozen

config.model.lr = 0.01     # Raises FrozenConfigError
config.training.epochs = 10 # OK - training section not frozen
```

### Thaw for Controlled Modifications

```python
# Temporarily unfreeze for controlled modifications
config = rconfig.instantiate("config.yaml", freeze=True)

with rconfig.thaw(config) as mutable_config:
    mutable_config.model.lr = 0.01  # OK within context

# Config is frozen again after context exits
config.model.lr = 0.02  # Raises FrozenConfigError
```

### Check Frozen Status

```python
config = rconfig.instantiate("config.yaml", freeze=True)

rconfig.is_frozen(config)        # True
rconfig.is_frozen(config.model)  # True

# Create unfrozen copy for experimentation
config_copy = rconfig.unfreeze(config)  # Returns mutable deep copy
config_copy.model.lr = 0.01  # OK
```

---

## 5. Structured Config Schemas

**Adopted by:** Hydra (via OmegaConf), Pydantic Settings, attrs

### Description

Structured config schemas allow users to define their configuration structure using Python dataclasses, Pydantic models, or attrs classes. The config system then validates loaded configs against these schemas, providing static type checking (via mypy/pyright), IDE autocompletion, and automatic documentation. This bridges the gap between dynamic YAML configs and static Python typing.

### Why It Adds Value

- **IDE Support**: Full autocompletion when accessing config values
- **Static Type Checking**: mypy/pyright catch config access errors before runtime
- **Documentation**: Schema serves as self-documenting config specification
- **Validation**: Automatic type validation during config loading
- **Refactoring Safety**: Rename config keys with IDE refactoring tools
- **Default Values**: Define defaults directly in Python

### Usage Example

```python
from dataclasses import dataclass, field
from typing import Optional, List
import rconfig

@dataclass
class OptimizerConfig:
    name: str = "adam"
    lr: float = 0.001
    weight_decay: float = 0.0
    betas: tuple[float, float] = (0.9, 0.999)

@dataclass
class ModelConfig:
    name: str
    hidden_size: int = 256
    num_layers: int = 4
    dropout: float = 0.1
    optimizer: OptimizerConfig = field(default_factory=OptimizerConfig)

@dataclass
class DataConfig:
    path: str
    batch_size: int = 32
    num_workers: int = 4
    augmentations: List[str] = field(default_factory=list)

@dataclass
class Config:
    model: ModelConfig
    data: DataConfig
    experiment_name: str = "default"
    seed: Optional[int] = None
```

```yaml
# config.yaml - Only specify what differs from defaults
model:
  name: resnet50
  hidden_size: 512
  optimizer:
    lr: 0.0001

data:
  path: /data/imagenet
  batch_size: 64
  augmentations: [flip, rotate]

seed: 42
```

```python
# Type-safe instantiation
config: Config = rconfig.instantiate("config.yaml", schema=Config)

# IDE autocompletion works!
print(config.model.hidden_size)      # 512
print(config.model.optimizer.lr)     # 0.0001
print(config.model.optimizer.betas)  # (0.9, 0.999) - from default

# Type errors caught by mypy
config.model.hidden_size = "big"  # mypy error: expected int
```

### Pydantic Integration

```python
from pydantic import BaseModel, Field
from typing import Literal

class ModelConfig(BaseModel):
    name: str
    hidden_size: int = Field(ge=1, le=4096, default=256)
    activation: Literal["relu", "gelu", "silu"] = "gelu"

    class Config:
        frozen = True  # Integrates with frozen config mode

class Config(BaseModel):
    model: ModelConfig

# Pydantic validation runs automatically
config = rconfig.instantiate("config.yaml", schema=Config)
# Raises ValidationError if hidden_size > 4096
```

### Schema as Documentation

```python
# Generate markdown documentation from schema
rconfig.generate_schema_docs(Config, output="CONFIG_DOCS.md")

# Generate JSON Schema for external tools
json_schema = rconfig.to_json_schema(Config)
```

---

## 6. Deprecation Warnings

**Adopted by:** OmegaConf

### Description

Deprecation warnings allow library maintainers and teams to mark configuration keys as deprecated while maintaining backwards compatibility. When a deprecated key is used, a warning is issued pointing users to the new key or pattern. This enables smooth migrations without breaking existing configs.

### Why It Adds Value

- **Backwards Compatibility**: Old configs continue to work during migration period
- **Clear Migration Path**: Warnings tell users exactly what to change
- **Gradual Adoption**: Teams can migrate configs incrementally
- **No Silent Breakage**: Users are informed rather than experiencing errors
- **Versioning Support**: Deprecate across library/API versions

### Usage Example

```python
import rconfig

# Register deprecations
rconfig.deprecate(
    old_key="learning_rate",
    new_key="model.optimizer.lr",
    message="'learning_rate' is deprecated, use 'model.optimizer.lr' instead",
    remove_in="2.0.0"
)

rconfig.deprecate(
    old_key="n_epochs",
    new_key="training.epochs",
    remove_in="2.0.0"
)
```

```yaml
# old_config.yaml (deprecated style)
learning_rate: 0.001
n_epochs: 100
model:
  name: resnet
```

```python
config = rconfig.instantiate("old_config.yaml")
# Warning: 'learning_rate' is deprecated and will be removed in version 2.0.0.
#          Use 'model.optimizer.lr' instead.
# Warning: 'n_epochs' is deprecated and will be removed in version 2.0.0.
#          Use 'training.epochs' instead.

# Values are automatically mapped to new locations
print(config.model.optimizer.lr)  # 0.001
print(config.training.epochs)     # 100
```

### In-Config Deprecation Markers

```yaml
# config.yaml
model:
  # Mark a key as deprecated directly in config
  old_param:
    _deprecated_:
      message: "Use 'new_param' instead"
      value: 42

  # Or use interpolation to redirect
  old_learning_rate: ${deprecated:model.optimizer.lr,"Use 'model.optimizer.lr'"}
```

### Deprecation Policies

```python
import rconfig
import warnings

# Control deprecation behavior
rconfig.set_deprecation_policy("warn")   # Default: emit warnings
rconfig.set_deprecation_policy("error")  # Strict: raise errors
rconfig.set_deprecation_policy("ignore") # Silent: no warnings

# Or use Python's warnings filter
warnings.filterwarnings("error", category=rconfig.DeprecationWarning)
```

### Migration Report

```python
# Generate a migration report for a config
report = rconfig.check_deprecations("old_config.yaml")
print(report)
# Deprecation Report for old_config.yaml:
# ----------------------------------------
# - learning_rate -> model.optimizer.lr (remove in 2.0.0)
# - n_epochs -> training.epochs (remove in 2.0.0)
#
# Run `rconfig migrate old_config.yaml` to auto-fix.

# Auto-migrate config file
rconfig.migrate("old_config.yaml", output="new_config.yaml")
```

---

## 7. Defaults List / Composition Groups

**Adopted by:** Hydra (core feature)

### Description

The defaults list is a powerful composition mechanism that allows configs to declare which other config files should be composed together, and in what order. Instead of manually managing `_ref_` across files, users specify a list of config "groups" that are automatically loaded and merged. This enables modular, swappable configuration components.

### Why It Adds Value

- **Modular Configs**: Swap components (models, optimizers, datasets) easily
- **Reduced Duplication**: Share common settings across experiments
- **Clear Dependencies**: Explicit list of what a config depends on
- **CLI Integration**: Override defaults from command line
- **Experiment Management**: Combine components for different experiment setups

### Usage Example

**Directory Structure:**
```
configs/
├── config.yaml          # Main config with defaults list
├── model/
│   ├── resnet.yaml
│   ├── vit.yaml
│   └── mlp.yaml
├── optimizer/
│   ├── adam.yaml
│   ├── sgd.yaml
│   └── adamw.yaml
├── dataset/
│   ├── imagenet.yaml
│   ├── cifar10.yaml
│   └── custom.yaml
└── experiment/
    ├── baseline.yaml
    └── ablation.yaml
```

```yaml
# configs/config.yaml
defaults:
  - model: resnet        # Load configs/model/resnet.yaml
  - optimizer: adam      # Load configs/optimizer/adam.yaml
  - dataset: imagenet    # Load configs/dataset/imagenet.yaml
  - experiment: baseline # Load configs/experiment/baseline.yaml
  - _self_               # Apply this file's values last

# Values here override defaults
training:
  epochs: 100
  seed: 42
```

```yaml
# configs/model/resnet.yaml
model:
  _target_: models.ResNet
  name: resnet50
  num_layers: 50
  pretrained: true
```

```yaml
# configs/model/vit.yaml
model:
  _target_: models.VisionTransformer
  name: vit_base
  patch_size: 16
  num_heads: 12
```

```yaml
# configs/optimizer/adam.yaml
optimizer:
  _target_: torch.optim.Adam
  lr: 0.001
  betas: [0.9, 0.999]
  weight_decay: 0.0
```

### Swapping Components

```python
import rconfig

# Use defaults from config.yaml
model = rconfig.instantiate("configs/config.yaml")

# Override defaults via CLI
# python train.py model=vit optimizer=adamw dataset=cifar10

# Override defaults programmatically
model = rconfig.instantiate(
    "configs/config.yaml",
    defaults={"model": "vit", "optimizer": "adamw"}
)
```

### Optional and Conditional Defaults

```yaml
# configs/config.yaml
defaults:
  - model: resnet
  - optimizer: adam
  - optional callbacks: null     # Optional: use null if file doesn't exist
  - override dataset: ${env:DATASET,imagenet}  # Dynamic default selection

training:
  epochs: 100
```

### Hierarchical Defaults

```yaml
# configs/experiment/ablation.yaml
defaults:
  - /model: vit           # Absolute path reference
  - /optimizer: adamw
  - override /dataset: cifar10  # Force override parent's dataset choice

experiment:
  name: ablation_study
  notes: "Testing ViT on CIFAR-10"
```

### Package Directive

```yaml
# configs/model/resnet.yaml
# @package model
# This config's contents go under the 'model' key

_target_: models.ResNet
name: resnet50
num_layers: 50

# Equivalent to:
# model:
#   _target_: models.ResNet
#   name: resnet50
#   num_layers: 50
```

---

## 8. Multi-Environment Profiles

**Adopted by:** Dynaconf, Spring Boot, Rails

### Description

Multi-environment profiles provide built-in support for environment-specific configurations (development, staging, production, testing). Instead of maintaining separate config files, all environments are defined in a single file with environment-specific overrides. The active environment is selected at runtime via environment variable or explicit parameter.

### Why It Adds Value

- **Single Source of Truth**: All environment configs in one place
- **Reduced File Proliferation**: No need for config.dev.yaml, config.prod.yaml, etc.
- **12-Factor Compliance**: Environment-based configuration is a best practice
- **Easy Comparison**: See differences between environments at a glance
- **Secure Defaults**: Development defaults are safe; production requires explicit config

### Usage Example

```yaml
# config.yaml
# Default values (typically safe development defaults)
default:
  database:
    host: localhost
    port: 5432
    name: myapp_dev
    pool_size: 5

  cache:
    backend: memory
    ttl: 60

  debug: true
  log_level: DEBUG

# Development environment (inherits from default)
development:
  # Uses all defaults, can override specific values
  debug: true

# Testing environment
testing:
  database:
    name: myapp_test
    pool_size: 2
  cache:
    backend: memory
    ttl: 0  # No caching in tests
  debug: true
  log_level: WARNING

# Staging environment
staging:
  database:
    host: staging-db.internal
    name: myapp_staging
    pool_size: 10
  cache:
    backend: redis
    host: staging-redis.internal
  debug: false
  log_level: INFO

# Production environment
production:
  database:
    host: ${env:DATABASE_HOST}  # Required from environment
    port: ${env:DATABASE_PORT,5432}
    name: ${env:DATABASE_NAME}
    pool_size: ${env:DATABASE_POOL_SIZE,20}
  cache:
    backend: redis
    host: ${env:REDIS_HOST}
    ttl: 3600
  debug: false
  log_level: WARNING
```

```python
import rconfig

# Auto-detect from RCONFIG_ENV environment variable
# export RCONFIG_ENV=production
config = rconfig.instantiate("config.yaml")

# Or specify explicitly
config = rconfig.instantiate("config.yaml", env="production")

# Or use shorthand
config = rconfig.instantiate("config.yaml", env="prod")  # Matches "production"

print(config.database.host)  # Value from DATABASE_HOST env var
print(config.debug)          # False
```

### Environment Inheritance

```yaml
# config.yaml
default:
  base_url: http://localhost:8000
  features:
    - basic
    - search

development:
  _inherits_: default  # Explicit (default behavior)

staging:
  _inherits_: development  # Staging inherits from development
  base_url: https://staging.example.com

production:
  _inherits_: staging  # Production inherits from staging
  base_url: https://example.com
  features:
    _extend_:
      - analytics
      - premium
```

### Environment Validation

```python
import rconfig

# Ensure production has required values
rconfig.require_in_env("production", [
    "database.host",
    "database.name",
    "cache.host"
])

# This will fail if production env is missing required keys
config = rconfig.instantiate("config.yaml", env="production")
```

---

## 9. Config Diffing

**Adopted by:** General DevOps best practice, Terraform, Kubernetes

### Description

Config diffing compares two configurations and reports the differences. This is useful for understanding what changed between config versions, reviewing pull requests with config changes, debugging unexpected behavior, and tracking configuration drift over time.

### Why It Adds Value

- **Change Review**: Understand exactly what changed in a config update
- **Debugging**: Compare working vs broken configs to find issues
- **Audit Trail**: Track configuration changes over time
- **PR Reviews**: Clear diff visualization for config change reviews
- **Drift Detection**: Compare deployed config against source of truth

### Usage Example

```python
import rconfig

# Compare two config files
diff = rconfig.diff("config_v1.yaml", "config_v2.yaml")

print(diff)
# ConfigDiff:
#   Added:
#     + model.dropout: 0.1
#     + training.early_stopping: true
#
#   Removed:
#     - model.legacy_param: "old_value"
#
#   Changed:
#     ~ model.learning_rate: 0.001 -> 0.0001
#     ~ data.batch_size: 32 -> 64
#     ~ training.epochs: 100 -> 200
```

### Programmatic Access

```python
diff = rconfig.diff("config_v1.yaml", "config_v2.yaml")

# Access diff components
for key, value in diff.added.items():
    print(f"Added: {key} = {value}")

for key in diff.removed:
    print(f"Removed: {key}")

for key, (old, new) in diff.changed.items():
    print(f"Changed: {key}: {old} -> {new}")

# Check if configs are identical
if diff.is_empty():
    print("Configs are identical")

# Get summary stats
print(f"Total changes: {len(diff)}")
print(f"Added: {len(diff.added)}, Removed: {len(diff.removed)}, Changed: {len(diff.changed)}")
```

### Diff with Overrides

```python
# Compare config with and without overrides
diff = rconfig.diff(
    "config.yaml",
    "config.yaml",
    left_overrides={},
    right_overrides={"model.lr": 0.01, "training.epochs": 200}
)

print(diff)
# Changed:
#   ~ model.lr: 0.001 -> 0.01
#   ~ training.epochs: 100 -> 200
```

### Output Formats

```python
diff = rconfig.diff("v1.yaml", "v2.yaml")

# Colored terminal output (default)
print(diff.to_terminal())

# Markdown for documentation/PRs
print(diff.to_markdown())
# | Path | Old Value | New Value |
# |------|-----------|-----------|
# | model.lr | 0.001 | 0.0001 |
# | data.batch_size | 32 | 64 |

# JSON for programmatic processing
print(diff.to_json())

# Unified diff format
print(diff.to_unified())
# --- config_v1.yaml
# +++ config_v2.yaml
# @@ model @@
# -  learning_rate: 0.001
# +  learning_rate: 0.0001
# +  dropout: 0.1
```

### CLI Integration

```bash
# Command line diffing
rconfig diff config_v1.yaml config_v2.yaml

# With output format
rconfig diff config_v1.yaml config_v2.yaml --format=markdown

# Diff with overrides
rconfig diff config.yaml config.yaml --right-override="model.lr=0.01"

# Exit code for CI/CD (0 = identical, 1 = different)
rconfig diff config_v1.yaml config_v2.yaml --exit-code
```

---

## 10. Callbacks and Hooks

**Adopted by:** Hydra, pytest, many frameworks

### Description

Callbacks and hooks provide extension points for users to inject custom logic at various stages of the configuration lifecycle. This enables validation, logging, transformation, and integration with external systems without modifying core rconfig code.

### Why It Adds Value

- **Custom Validation**: Add domain-specific validation rules
- **Logging/Monitoring**: Track config loading and usage
- **Transformation**: Post-process configs before use
- **Integration**: Connect with external systems (secrets managers, feature flags)
- **Debugging**: Inspect configs at various lifecycle stages

### Usage Example

```python
import rconfig
from pathlib import Path

# Register lifecycle hooks
@rconfig.on_config_loaded
def validate_paths(config: dict, path: str) -> None:
    """Validate that data paths exist after config is loaded."""
    if "data" in config and "path" in config["data"]:
        data_path = Path(config["data"]["path"])
        if not data_path.exists():
            raise ValueError(f"Data path does not exist: {data_path}")

@rconfig.on_config_loaded
def log_config(config: dict, path: str) -> None:
    """Log loaded configuration for debugging."""
    import logging
    logging.info(f"Loaded config from {path}")
    logging.debug(f"Config: {config}")

@rconfig.on_before_instantiate
def inject_secrets(config: dict) -> dict:
    """Inject secrets from external source before instantiation."""
    import os
    if config.get("database", {}).get("password") == "_from_vault_":
        config["database"]["password"] = get_secret_from_vault("db_password")
    return config

@rconfig.on_after_instantiate
def register_metrics(instance: object, config: dict) -> None:
    """Register instantiated objects with metrics system."""
    if hasattr(instance, "name"):
        metrics.register_component(instance.name, instance)
```

### Hook Types

```python
import rconfig

# Called when config file is loaded (before interpolation)
@rconfig.on_file_loaded
def hook(raw_config: dict, file_path: str) -> dict:
    return raw_config  # Can modify raw config

# Called after composition and interpolation
@rconfig.on_config_loaded
def hook(resolved_config: dict, path: str) -> None:
    pass  # Read-only inspection

# Called after validation, before instantiation
@rconfig.on_before_instantiate
def hook(config: dict) -> dict:
    return config  # Can modify config

# Called after instantiation
@rconfig.on_after_instantiate
def hook(instance: object, config: dict) -> None:
    pass  # Post-instantiation logic

# Called on errors
@rconfig.on_error
def hook(error: Exception, context: dict) -> None:
    pass  # Error handling/logging
```

### Conditional Hooks

```python
import rconfig

# Hook only for specific config patterns
@rconfig.on_config_loaded(pattern="**/model/*.yaml")
def validate_model_config(config: dict, path: str) -> None:
    """Only runs for configs matching the pattern."""
    assert "model" in config, "Model config must have 'model' key"

# Hook with priority (lower runs first)
@rconfig.on_config_loaded(priority=10)
def early_hook(config: dict, path: str) -> None:
    pass

@rconfig.on_config_loaded(priority=100)
def late_hook(config: dict, path: str) -> None:
    pass
```

### Class-Based Callbacks

```python
import rconfig

class ExperimentTracker(rconfig.Callback):
    """Track experiments with full lifecycle hooks."""

    def __init__(self, tracking_uri: str):
        self.tracking_uri = tracking_uri
        self.run_id = None

    def on_config_loaded(self, config: dict, path: str) -> None:
        self.run_id = start_experiment_run(self.tracking_uri)
        log_config(self.run_id, config)

    def on_after_instantiate(self, instance: object, config: dict) -> None:
        log_instantiation(self.run_id, type(instance).__name__)

    def on_error(self, error: Exception, context: dict) -> None:
        mark_run_failed(self.run_id, str(error))

# Register callback instance
rconfig.register_callback(ExperimentTracker("http://mlflow.internal"))
```

---

## 11. XDG Base Directory Support

**Adopted by:** Confuse, many Linux CLI applications

### Description

XDG Base Directory support enables automatic discovery of configuration files in platform-specific standard locations. On Linux, this follows the XDG Base Directory Specification; on macOS and Windows, it uses platform-appropriate locations. This is essential for CLI tools and desktop applications.

### Why It Adds Value

- **Platform Conventions**: Follows OS-specific best practices
- **User Configuration**: Users can customize without modifying app directory
- **System-Wide Defaults**: Admin can set defaults in /etc
- **No Hardcoded Paths**: App doesn't need to know where configs live
- **Override Hierarchy**: Local configs override system configs

### Usage Example

```python
import rconfig

# Auto-discover configs for an application
# Searches (in order, later overrides earlier):
#   1. /etc/myapp/config.yaml (system-wide)
#   2. ~/.config/myapp/config.yaml (XDG user config)
#   3. ./config.yaml (current directory)
#   4. Environment variable MYAPP_CONFIG

config = rconfig.instantiate_app("myapp")

# Or with explicit app configuration
config = rconfig.instantiate_app(
    "myapp",
    config_name="settings.yaml",
    search_paths=[
        "/etc/myapp",
        "~/.config/myapp",
        "~/.myapp",  # Legacy location
        ".",
    ]
)
```

### Search Path Resolution

```python
import rconfig

# Get the paths that would be searched
paths = rconfig.get_config_paths("myapp")
print(paths)
# [
#   PosixPath('/etc/myapp/config.yaml'),
#   PosixPath('/home/user/.config/myapp/config.yaml'),
#   PosixPath('./config.yaml')
# ]

# Find first existing config
config_path = rconfig.find_config("myapp")
print(config_path)
# PosixPath('/home/user/.config/myapp/config.yaml')

# Find all existing configs (for layered loading)
all_configs = rconfig.find_all_configs("myapp")
print(all_configs)
# [
#   PosixPath('/etc/myapp/config.yaml'),       # System defaults
#   PosixPath('/home/user/.config/myapp/config.yaml')  # User overrides
# ]
```

### Platform-Specific Paths

```python
import rconfig

# Linux (XDG)
# System: /etc/myapp/
# User: ~/.config/myapp/ (or $XDG_CONFIG_HOME/myapp/)

# macOS
# System: /Library/Application Support/myapp/
# User: ~/Library/Application Support/myapp/

# Windows
# System: C:\ProgramData\myapp\
# User: C:\Users\<user>\AppData\Roaming\myapp\

# Get platform-appropriate paths
paths = rconfig.get_platform_config_dirs("myapp")
```

### Layered Configuration Loading

```python
import rconfig

# Load and merge configs from all locations
config = rconfig.instantiate_app(
    "myapp",
    merge_strategy="deep",  # Deep merge all found configs
)

# Equivalent to:
# 1. Load /etc/myapp/config.yaml (system defaults)
# 2. Deep merge ~/.config/myapp/config.yaml (user preferences)
# 3. Deep merge ./config.yaml (project-specific)
# 4. Apply MYAPP_* environment variables
# 5. Apply CLI overrides
```

### Initialize User Config

```python
import rconfig

# Create user config directory and default config
rconfig.init_user_config(
    "myapp",
    default_config={
        "theme": "dark",
        "language": "en",
    }
)
# Creates ~/.config/myapp/config.yaml with defaults

# Or copy from bundled defaults
rconfig.init_user_config(
    "myapp",
    from_template="package://myapp/default_config.yaml"
)
```

---

## Summary

This vision document outlines 11 features that would enhance rconfig based on proven patterns from the configuration library ecosystem. The features are prioritized by community adoption and general-purpose utility:

### High Priority (Widely Adopted)
1. ✅ Custom Resolvers
2. Config Export / Serialization
3. Built-in TOML and JSON Loaders
4. Frozen Config Mode
5. Structured Config Schemas
6. Deprecation Warnings
7. Defaults List / Composition Groups

### Medium Priority (Common Patterns)
8. Multi-Environment Profiles
9. Config Diffing
10. Callbacks and Hooks
11. XDG Base Directory Support

Each feature includes detailed usage examples showing how users would interact with the functionality, highlighting the key benefits and use cases.
