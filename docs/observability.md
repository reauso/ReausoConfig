# Observability

## Provenance Tracking

Track the origin of every config value - essential for debugging complex configs.

### Basic Usage

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

### Accessing Specific Entries

```python
entry = prov.get("model.layers")
print(f"Defined at: {entry.file}:{entry.line}")
if entry.overrode:
    print(f"Overrode: {entry.overrode}")

# Iterate all entries
for path, entry in prov.items():
    print(f"{path}: {entry.file}:{entry.line}")
```

#### ProvenanceEntry Fields

Each `ProvenanceEntry` contains:

| Field           | Type                       | Description                               |
| --------------- | -------------------------- | ----------------------------------------- |
| `file`        | `str`                    | Source file path                          |
| `line`        | `int`                    | Line number in source file                |
| `value`       | `Any`                    | Resolved value                            |
| `source_type` | `SourceType`             | Origin type (file, cli, env, etc.)        |
| `overrode`    | `ProvenanceEntry \| None` | Entry that was overridden                 |
| `type_hint`   | `type \| None`            | Type hint (e.g.,`float`, `list[int]`) |
| `description` | `str \| None`             | Field description from structured config  |

```python
entry = prov.get("model.lr")
print(f"Type: {entry.type_hint}")  # <class 'float'>
print(f"Description: {entry.description}")  # "Learning rate for optimizer"
```

### Formatting Presets

| Preset          | Shows                                 | Use Case         |
| --------------- | ------------------------------------- | ---------------- |
| `default()`     | paths, values, files, lines, chain    | Reset to defaults|
| `minimal()`     | paths, files, lines                   | Quick overview   |
| `compact()`     | + values, source type, targets, types | Debugging values |
| `full()`        | everything                            | Complete tracing |
| `values()`      | paths and values only                 | Simple key=value |
| `help()`        | paths, types, values, descriptions    | CLI help display |
| `deprecations()`| only deprecated keys                  | Migration check  |

```python
# Use presets (named methods)
print(rc.format(prov).minimal())
print(rc.format(prov).compact())
print(rc.format(prov).full())

# String-based preset() method
print(rc.format(prov).preset("minimal"))
print(rc.format(prov).preset("values"))

# Reset to defaults after modifications
print(rc.format(prov).hide_chain().default())
```

### Custom Provenance Presets

Register your own presets for common formatting needs:

```python
import rconfig as rc

# Option 1: Register with lambda
rc.register_provenance_preset(
    "debug",
    lambda: rc.ProvenanceFormatContext(
        show_paths=True,
        show_values=True,
        show_files=True,
        show_lines=True,
        show_chain=True,
        show_types=True,
    ),
    "Full debug output with types",
)

# Option 2: Register with decorator
@rc.provenance_preset("source_only", "Show only source information")
def source_only_preset() -> rc.ProvenanceFormatContext:
    return rc.ProvenanceFormatContext(
        show_paths=True,
        show_values=False,
        show_files=True,
        show_lines=True,
        show_source_type=True,
    )

# Use custom presets
print(rc.format(prov).preset("debug"))
print(rc.format(prov).preset("source_only"))

# List all registered presets
for name, entry in rc.known_provenance_presets().items():
    builtin = "[builtin]" if entry.builtin else "[custom]"
    print(f"{name} {builtin}: {entry.description}")

# Unregister when no longer needed
rc.unregister_provenance_preset("debug")
```

### Show/Hide Toggles

```python
# All toggles (each has show/hide variant)
rc.format(prov)
    .show_paths()      .hide_paths()      # Config paths (/model.lr)
    .show_values()     .hide_values()     # Resolved values
    .show_files()      .hide_files()      # Source file names
    .show_lines()      .hide_lines()      # Line numbers
    .show_source_type().hide_source_type()# Source markers (CLI/env/file)
    .show_chain()      .hide_chain()      # Interpolation/instance chains
    .show_overrides()  .hide_overrides()  # Override information
    .show_targets()    .hide_targets()    # Target class information
    .show_types()      .hide_types()      # Type hints (float, list[int])
    .show_descriptions().hide_descriptions() # Field descriptions

# Combine with presets
print(rc.format(prov).minimal().show_values())
print(rc.format(prov).compact().hide_chain())
```

### Filtering

```python
# Filter by config path (glob patterns)
print(rc.format(prov).for_path("/model.*"))      # Only model paths
print(rc.format(prov).for_path("/training.*"))   # Only training paths

# Filter by source file
print(rc.format(prov).from_file("trainer.yaml")) # Only from trainer.yaml
print(rc.format(prov).from_file("models/*.yaml"))# From any file in models/

# Combine filters (multiple calls = OR logic)
print(rc.format(prov)
    .for_path("/model.*")
    .from_file("config.yaml")
)
```

### Source Types

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

### Override Tracking

When values are overridden, provenance shows the chain:

```python
# /model.lr = 0.01
#   trainer.yaml:5
#   Overrode: models/base.yaml:10

entry = prov.get("model.lr")
if entry.overrode:
    print(f"Replaced value from: {entry.overrode}")
```

### Interpolation Chains

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

### Tree Tracing

Build a full provenance tree for complex chains:

```python
tree = prov.trace("model.lr")
if tree:
    print(tree.source_type)  # "file", "cli", "env", etc.
    print(tree.file, tree.line)
    for child in tree.children:
        print(f"  {child.source_type}: {child.path}")
```

### Dict Export

Export provenance as a dictionary for programmatic access:

```python
# Export entire provenance
data = prov.to_dict()

# Export single entry
entry_data = prov.get("model.lr").to_dict()

# Export tree node
tree_data = prov.trace("model.lr").to_dict()
```

### Built-in Layouts

| Layout | Method | Description |
|--------|--------|-------------|
| `tree` | `.tree()` | Tree-style multiline format with connectors (default) |
| `flat` | `.flat()` | Single-line compact format |
| `markdown` | `.markdown()` | Markdown table format for documentation |

```python
# Use layouts by name
print(rc.format(prov).layout("tree"))
print(rc.format(prov).layout("flat"))
print(rc.format(prov).layout("markdown"))

# Or use convenience methods
print(rc.format(prov).tree())
print(rc.format(prov).flat())
print(rc.format(prov).markdown())
```

### Custom Layouts

Create custom output formats by extending ProvenanceLayout:

```python
from rconfig.provenance.formatting import ProvenanceLayout, ProvenanceDisplayModel

class TableLayout(ProvenanceLayout):
    def render(self, model: ProvenanceDisplayModel) -> str:
        if model.empty_message:
            return model.empty_message
        lines = ["| Path | File | Line |", "|------|------|------|"]
        for entry in model.entries:
            lines.append(f"| /{entry.path} | {entry.file} | {entry.line} |")
        return "\n".join(lines)

# Use custom layout directly
print(rc.format(prov).layout(TableLayout()))
```

### Custom Layout Registration

Register custom layouts for reuse across your project:

```python
import rconfig as rc
from rconfig.provenance.formatting import ProvenanceLayout, ProvenanceDisplayModel

class TableLayout(ProvenanceLayout):
    def render(self, model: ProvenanceDisplayModel) -> str:
        # ... implementation ...

# Register the layout
rc.register_provenance_layout(
    "table",
    lambda: TableLayout(),
    "Custom table format",
)

# Use by name
print(rc.format(prov).layout("table"))

# List all registered layouts
for name, entry in rc.known_provenance_layouts().items():
    builtin = "[builtin]" if entry.builtin else "[custom]"
    print(f"{name} {builtin}: {entry.description}")

# Unregister when no longer needed
rc.unregister_provenance_layout("table")
```

## Config Diffing

Compare two configurations and report differences. Accepts Path objects or Provenance objects directly.

### Basic Usage

```python
import rconfig as rc
from pathlib import Path

# Compare two config files
diff = rc.diff(Path("config_v1.yaml"), Path("config_v2.yaml"))

# Check if configs are identical
if diff.is_empty():
    print("Configs are identical")

# Access differences by type
for path, entry in diff.added.items():
    print(f"Added: {path} = {entry.right_value}")

for path, entry in diff.removed.items():
    print(f"Removed: {path}")

for path, entry in diff.changed.items():
    print(f"Changed: {path}: {entry.left_value} -> {entry.right_value}")
```

### Programmatic Access

```python
# Access the ConfigDiff as a mapping
diff = rc.diff(Path("v1.yaml"), Path("v2.yaml"))

print(len(diff))                    # Total entry count
print(len(diff.added))              # Added entry count
print("model.lr" in diff)           # Check if path exists
entry = diff["model.lr"]            # Get specific entry

# Get dictionary representation
data = diff.to_dict()
```

### Diff with Overrides

```python
# Compare same file with different overrides
diff = rc.diff(
    Path("config.yaml"),
    Path("config.yaml"),
    left_overrides={"model.lr": 0.001},
    right_overrides={"model.lr": 0.01},
)

# Reuse existing provenance for efficiency
prov_v1 = rc.get_provenance(Path("v1.yaml"))
prov_v2 = rc.get_provenance(Path("v2.yaml"))
diff = rc.diff(prov_v1, prov_v2)
```

### Output Formats

```python
diff = rc.diff(Path("v1.yaml"), Path("v2.yaml"))

# Terminal output (default flat layout)
print(rc.format(diff).terminal())
# + model.dropout: 0.1
# - model.legacy: 'old'
# ~ model.lr: 0.001 -> 0.01
#
# Added: 1, Removed: 1, Changed: 1

# Tree layout (grouped by change type)
print(rc.format(diff).tree())
# ConfigDiff:
#   Added:
#     + model.dropout: 0.1
#   Removed:
#     - model.legacy: 'old'
#   Changed:
#     ~ model.lr: 0.001 -> 0.01

# Markdown table
print(rc.format(diff).markdown())
# | Type | Path | Old Value | New Value |
# |------|------|-----------|-----------|
# | + | model.dropout | - | 0.1 |
# | - | model.legacy | 'old' | - |
# | ~ | model.lr | 0.001 | 0.01 |

# Dictionary for JSON serialization
data = rc.format(diff).json()
```

### Formatting Presets

| Preset          | Shows                          | Use Case              |
| --------------- | ------------------------------ | --------------------- |
| `default()`     | added/removed/changed, counts  | Reset to defaults     |
| `changes_only()`| added/removed/changed, counts  | Focus on changes      |
| `with_context()`| + unchanged entries            | See context           |
| `full()`        | + provenance info              | Complete debugging    |
| `summary()`     | only statistics                | Quick overview        |

```python
diff = rc.diff(Path("v1.yaml"), Path("v2.yaml"))

# Named methods
rc.format(diff).changes_only().terminal()
rc.format(diff).with_context().terminal()
rc.format(diff).full().terminal()
rc.format(diff).summary().terminal()
# Added: 2, Removed: 1, Changed: 3

# String-based preset() method
rc.format(diff).preset("changes_only").terminal()
rc.format(diff).preset("summary").terminal()

# Reset to defaults after modifications
rc.format(diff).show_unchanged().default().terminal()
```

### Custom Diff Presets

Register your own presets for common diff formatting needs:

```python
import rconfig as rc

# Option 1: Register with lambda
rc.register_diff_preset(
    "added_only",
    lambda: rc.DiffFormatContext(
        show_added=True,
        show_removed=False,
        show_changed=False,
        show_unchanged=False,
    ),
    "Show only newly added entries",
)

# Option 2: Register with decorator
@rc.diff_preset("removed_only", "Show only removed entries")
def removed_only_preset() -> rc.DiffFormatContext:
    return rc.DiffFormatContext(
        show_added=False,
        show_removed=True,
        show_changed=False,
        show_unchanged=False,
    )

# Use custom presets
print(rc.format(diff).preset("added_only"))
print(rc.format(diff).preset("removed_only"))

# List all registered presets
for name, entry in rc.known_diff_presets().items():
    print(f"{name}: {entry.description}")
```

### Show/Hide Toggles

```python
diff = rc.diff(Path("v1.yaml"), Path("v2.yaml"))

# Show provenance (file:line) info
rc.format(diff).show_provenance().terminal()

# Hide summary statistics
rc.format(diff).hide_counts().terminal()

# Show only specific change types
rc.format(diff).hide_added().hide_removed().terminal()

# Chain multiple options
rc.format(diff).show_provenance().show_unchanged().hide_counts().markdown()
```

### Filtering

```python
diff = rc.diff(Path("v1.yaml"), Path("v2.yaml"))

# Filter by path pattern
rc.format(diff).for_path("model.*").terminal()

# Filter by source file
rc.format(diff).from_file("*.yaml").terminal()

# Combine filters
rc.format(diff).for_path("training.*").from_file("configs/*.yaml").terminal()
```

### Built-in Layouts

| Layout | Method | Description |
|--------|--------|-------------|
| `flat` | `.flat()` / `.terminal()` | Single-line compact format (default) |
| `tree` | `.tree()` | Tree-style grouped by change type |
| `markdown` | `.markdown()` | Markdown table format |

```python
# Use layouts by name
print(rc.format(diff).layout("flat"))
print(rc.format(diff).layout("tree"))
print(rc.format(diff).layout("markdown"))

# Or use convenience methods
print(rc.format(diff).terminal())  # alias for flat()
print(rc.format(diff).tree())
print(rc.format(diff).markdown())
```

### Custom Layouts

Create custom output formats by extending DiffLayout:

```python
from rconfig.diff.formatting import DiffLayout, DiffDisplayModel

class JsonLinesLayout(DiffLayout):
    def render(self, model: DiffDisplayModel) -> str:
        import json
        if model.empty_message:
            return model.empty_message
        lines = []
        for entry in model.entries:
            lines.append(json.dumps({
                "path": entry.path,
                "type": entry.diff_type.value,
                "left": entry.left_value,
                "right": entry.right_value,
            }))
        return "\n".join(lines)

# Use custom layout directly
print(rc.format(diff).layout(JsonLinesLayout()))
```

### Custom Layout Registration

Register custom layouts for reuse:

```python
import rconfig as rc
from rconfig.diff.formatting import DiffLayout, DiffDisplayModel

class JsonLinesLayout(DiffLayout):
    def render(self, model: DiffDisplayModel) -> str:
        # ... implementation ...

# Register the layout
rc.register_diff_layout(
    "jsonlines",
    lambda: JsonLinesLayout(),
    "JSON Lines format",
)

# Use by name
print(rc.format(diff).layout("jsonlines"))

# List all registered layouts
for name, entry in rc.known_diff_layouts().items():
    builtin = "[builtin]" if entry.builtin else "[custom]"
    print(f"{name} {builtin}: {entry.description}")

# Unregister when no longer needed
rc.unregister_diff_layout("jsonlines")
```

## Deprecation Warnings

Mark configuration keys as deprecated while maintaining backwards compatibility. Deprecated keys are tracked in the provenance system, providing a single source of truth.

### Registering Deprecations

```python
import rconfig as rc

# Register a deprecated key with migration path
rc.deprecate(
    old_key="learning_rate",
    new_key="model.optimizer.lr",
    message="Use 'model.optimizer.lr' instead",
    remove_in="2.0.0"
)

# Register multiple deprecations
rc.deprecate(old_key="n_epochs", new_key="training.epochs", remove_in="2.0.0")
rc.deprecate(old_key="old_param", message="This parameter is no longer used")
```

### Pattern Matching

Use glob-style patterns to deprecate multiple keys:

```python
# Exact path (default)
rc.deprecate("model.learning_rate", new_key="model.optimizer.lr")

# Single wildcard (*) - matches one level
rc.deprecate("*.lr", message="Use full path 'optimizer.learning_rate'")
# Matches: model.lr, encoder.lr
# Does NOT match: model.encoder.lr

# Double wildcard (**) - matches any depth
rc.deprecate("**.dropout", message="Dropout is configured in training section")
# Matches: model.dropout, model.encoder.dropout, a.b.c.dropout
```

### Auto-Mapping Values

When a deprecated key has a `new_key`, values are automatically mapped (creating intermediate structures as needed):

```yaml
# old_config.yaml (deprecated style)
learning_rate: 0.001
n_epochs: 100
model:
  name: resnet
```

```python
from rconfig.deprecation import auto_map_deprecated_values

# Values automatically available at new locations (intermediate structures created)
# After auto-mapping: config.model.optimizer.lr = 0.001
#                     config.training.epochs = 100
```

### Deprecation Reports via Provenance

Use the `.deprecations()` preset to view only deprecated keys:

```python
prov = rc.get_provenance(path=Path("config.yaml"))

# Show only deprecated keys
print(rc.format(prov).deprecations())
# Deprecated Keys:
# ----------------
# /learning_rate
#   config.yaml:1
#   DEPRECATED -> model.optimizer.lr (remove in 2.0.0)
#   Message: Use 'model.optimizer.lr' instead
#
# /n_epochs
#   config.yaml:2
#   DEPRECATED -> training.epochs (remove in 2.0.0)

# Check programmatically
deprecated_entries = [
    (path, entry) for path, entry in prov.items()
    if entry.deprecation is not None
]
if deprecated_entries:
    print(f"Found {len(deprecated_entries)} deprecated keys")
```

### Deprecation Policies

Control how deprecated keys are handled:

```python
# Global policy (default: "warn")
rc.set_deprecation_policy("warn")   # Emit warnings (default)
rc.set_deprecation_policy("error")  # Raise DeprecatedKeyError
rc.set_deprecation_policy("ignore") # Silent

# Per-deprecation policy override
rc.deprecate(
    old_key="critical_old_key",
    new_key="new_key",
    policy="error"  # Always error, regardless of global policy
)
```

### Custom Warning Handlers

Customize how deprecation warnings are emitted:

```python
from rconfig.deprecation import DeprecationHandler, DeprecationInfo

# Using a class
class LoggingHandler(DeprecationHandler):
    def handle(self, info: DeprecationInfo, path: str, file: str, line: int) -> None:
        import logging
        logging.warning(f"Deprecated key '{path}' at {file}:{line}")

rc.set_deprecation_handler(LoggingHandler())

# Using a decorator
@rc.deprecation_handler
def my_handler(info: DeprecationInfo, path: str, file: str, line: int) -> None:
    print(f"DEPRECATED: {path} -> {info.new_key}")
```

The default handler uses Python's `warnings.warn()` with `RconfigDeprecationWarning`, which integrates with Python's warnings filter system.

### API Reference

| Function                                                          | Description                                        |
| ----------------------------------------------------------------- | -------------------------------------------------- |
| `rc.deprecate(old_key, *, new_key, message, remove_in, policy)` | Register a deprecated key (supports glob patterns) |
| `rc.undeprecate(old_key)`                                       | Remove a deprecation registration                  |
| `rc.set_deprecation_policy(policy)`                             | Set global policy (warn/error/ignore)              |
| `rc.set_deprecation_handler(handler)`                           | Set custom warning handler                         |
| `@rc.deprecation_handler`                                       | Decorator to register a function as handler        |
| `rc.format(prov).deprecations()`                                | Show only deprecated keys in provenance            |
