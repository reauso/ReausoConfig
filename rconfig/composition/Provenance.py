"""Provenance tracking for config composition.

This module provides classes for tracking the origin of each value
in a composed configuration, including file paths, line numbers,
override information, and interpolation sources.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from rconfig._internal.path_utils import build_child_path


class EntrySourceType(StrEnum):
    """Origin of a config value (where it was defined).

    Used by ProvenanceEntry to indicate the source type of a configuration value.
    These represent the initial source of a value before any transformations.
    """

    FILE = "file"
    """Value came from a YAML/config file."""

    CLI = "cli"
    """Value was set via command-line argument."""

    ENV = "env"
    """Value was set via environment variable."""

    PROGRAMMATIC = "programmatic"
    """Value was set programmatically in code."""


class NodeSourceType(StrEnum):
    """Type of node in a provenance trace tree.

    Used by ProvenanceNode to indicate the type of each node in the
    provenance tree. Includes all entry source types plus additional
    node types for tracing value transformations.
    """

    FILE = "file"
    """Value came from a file."""

    REF = "ref"
    """Value came from a _ref_ reference."""

    INSTANCE = "instance"
    """Value came from an instance chain."""

    INTERPOLATION = "interpolation"
    """Value was computed via interpolation."""

    CLI = "cli"
    """Value was set via command-line argument."""

    ENV = "env"
    """Value was set via environment variable."""

    PROGRAMMATIC = "programmatic"
    """Value was set programmatically in code."""

    OPERATOR = "operator"
    """Value is result of an operator expression (e.g., +, *, /)."""

    RESOLVER = "resolver"
    """Value came from a resolver function."""

if TYPE_CHECKING:
    from rconfig.deprecation.info import DeprecationInfo
    from rconfig.interpolation.evaluator import InterpolationSource
    from .ProvenanceFormat import ProvenanceFormat
    from .ProvenanceLayout import ProvenanceLayout


@dataclass(frozen=True)
class ProvenanceNode:
    """Node in a provenance tree.

    Used for tracing the full origin of a value through refs, instances,
    interpolations, operators, and resolvers. Forms a tree structure for compound
    expressions.

    :param source_type: Type of source (file, ref, instance, interpolation,
                        cli, env, programmatic, operator, resolver).
    :param path: Config path (e.g., "/model.lr").
    :param file: Source file name.
    :param line: Line number in source file.
    :param value: The resolved value at this node.
    :param expression: Interpolation expression (e.g., "${/a + /b}").
    :param operator: Operator for compound expressions (+, *, etc.).
    :param env_var: Environment variable name for env sources.
    :param cli_arg: CLI argument for CLI sources.
    :param resolver_name: Registered resolver path (e.g., "uuid", "db:lookup").
    :param resolver_func: Function name of the resolver (e.g., "gen_uuid").
    :param resolver_module: Module where the resolver is defined (e.g., "myapp.resolvers").
    :param children: Child nodes in the tree.
    """

    source_type: NodeSourceType
    path: str | None = None
    file: str | None = None
    line: int | None = None
    value: Any = None
    expression: str | None = None
    operator: str | None = None
    env_var: str | None = None
    cli_arg: str | None = None
    resolver_name: str | None = None
    resolver_func: str | None = None
    resolver_module: str | None = None
    children: tuple[ProvenanceNode, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        """Convert to a dictionary representation.

        :return: Dictionary representation of this node and its children.
        """
        result: dict[str, Any] = {"source_type": self.source_type}

        if self.path is not None:
            result["path"] = self.path
        if self.file is not None:
            result["file"] = self.file
        if self.line is not None:
            result["line"] = self.line
        if self.value is not None:
            result["value"] = self.value
        if self.expression is not None:
            result["expression"] = self.expression
        if self.operator is not None:
            result["operator"] = self.operator
        if self.env_var is not None:
            result["env_var"] = self.env_var
        if self.cli_arg is not None:
            result["cli_arg"] = self.cli_arg
        if self.resolver_name is not None:
            result["resolver_name"] = self.resolver_name
        if self.resolver_func is not None:
            result["resolver_func"] = self.resolver_func
        if self.resolver_module is not None:
            result["resolver_module"] = self.resolver_module
        if self.children:
            result["children"] = [child.to_dict() for child in self.children]

        return result


@dataclass(frozen=True)
class InstanceRef:
    """Reference to an instance in the instance chain.

    :param path: The instance path (e.g., "/shared.database" or "alias").
    :param file: File where the referenced object is defined.
    :param line: Line number where the referenced object is defined.
    """

    path: str
    file: str
    line: int


@dataclass(frozen=True)
class ProvenanceEntry:
    """Origin information for a config value.

    :param file: Source file path.
    :param line: Line number in source file.
    :param overrode: What this value overrode (if any), format: "file:line".
    :param instance: Chain of instance references with origins (immutable tuple).
    :param interpolation: Source info if value was interpolated.
    :param source_type: Type of source (file, cli, env, programmatic).
    :param cli_arg: CLI argument if source_type is "cli".
    :param env_var: Environment variable name if source_type is "env".
    :param value: The resolved value at this path.
    :param target_name: The _target_ string from config (e.g., "resnet").
    :param target_class: The resolved class name (e.g., "ResNet").
    :param target_module: The module path (e.g., "myapp.models").
    :param target_auto_registered: Whether the target was auto-registered.
    :param deprecation: Deprecation info if this key is deprecated.
    :param type_hint: Type hint for this config value (e.g., float, list[int]).
    :param description: Description from structured config (Pydantic Field, etc.).
    """

    file: str
    line: int
    overrode: str | None = None
    instance: tuple[InstanceRef, ...] | None = None
    interpolation: InterpolationSource | None = None
    source_type: EntrySourceType = EntrySourceType.FILE
    cli_arg: str | None = None
    env_var: str | None = None
    value: Any = None
    target_name: str | None = None
    target_class: str | None = None
    target_module: str | None = None
    target_auto_registered: bool = False
    deprecation: DeprecationInfo | None = None
    type_hint: type | None = None
    description: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to a dictionary representation.

        :return: Dictionary representation of this entry.
        """
        result: dict[str, Any] = {
            "file": self.file,
            "line": self.line,
            "source_type": self.source_type,
        }

        if self.overrode is not None:
            result["overrode"] = self.overrode
        if self.instance is not None:
            result["instance"] = [
                {"path": ref.path, "file": ref.file, "line": ref.line}
                for ref in self.instance
            ]
        if self.interpolation is not None:
            result["interpolation"] = {
                "kind": self.interpolation.kind,
                "expression": self.interpolation.expression,
                "value": self.interpolation.value,
            }
            if self.interpolation.path:
                result["interpolation"]["path"] = self.interpolation.path
            if self.interpolation.file:
                result["interpolation"]["file"] = self.interpolation.file
            if self.interpolation.line:
                result["interpolation"]["line"] = self.interpolation.line
        if self.cli_arg is not None:
            result["cli_arg"] = self.cli_arg
        if self.env_var is not None:
            result["env_var"] = self.env_var
        if self.value is not None:
            result["value"] = self.value
        if self.target_name is not None:
            result["target_name"] = self.target_name
        if self.target_class is not None:
            result["target_class"] = self.target_class
        if self.target_module is not None:
            result["target_module"] = self.target_module
        if self.target_auto_registered:
            result["target_auto_registered"] = True
        if self.deprecation is not None:
            result["deprecation"] = self.deprecation.to_dict()
        if self.type_hint is not None:
            result["type_hint"] = (
                self.type_hint.__name__
                if hasattr(self.type_hint, "__name__")
                else str(self.type_hint)
            )
        if self.description is not None:
            result["description"] = self.description

        return result

    def trace(self) -> ProvenanceNode:
        """Build a provenance tree from this entry.

        Follows interpolation sources recursively to build the full tree.

        :return: Root node of the provenance tree.
        """
        # Build children first (frozen dataclass requires immutable children)
        children: list[ProvenanceNode] = []

        # Add interpolation tree if present
        if self.interpolation:
            interp_node = self._build_interpolation_tree(self.interpolation)
            children.append(interp_node)

        # Add instance chain if present
        if self.instance:
            for ref in self.instance:
                instance_node = ProvenanceNode(
                    source_type=NodeSourceType.INSTANCE,
                    path=ref.path,
                    file=ref.file,
                    line=ref.line,
                )
                children.append(instance_node)

        # Convert children to tuple for frozen dataclass
        children_tuple = tuple(children)

        # Determine the root node type based on source_type
        if self.source_type == EntrySourceType.CLI:
            return ProvenanceNode(
                source_type=NodeSourceType.CLI,
                file=self.file,
                line=self.line,
                value=self.value,
                cli_arg=self.cli_arg,
                children=children_tuple,
            )
        elif self.source_type == EntrySourceType.ENV:
            return ProvenanceNode(
                source_type=NodeSourceType.ENV,
                file=self.file,
                line=self.line,
                value=self.value,
                env_var=self.env_var,
                children=children_tuple,
            )
        elif self.source_type == EntrySourceType.PROGRAMMATIC:
            return ProvenanceNode(
                source_type=NodeSourceType.PROGRAMMATIC,
                value=self.value,
                children=children_tuple,
            )
        else:
            return ProvenanceNode(
                source_type=NodeSourceType.FILE,
                file=self.file,
                line=self.line,
                value=self.value,
                children=children_tuple,
            )

    def _build_interpolation_tree(
        self, source: InterpolationSource
    ) -> ProvenanceNode:
        """Recursively build tree from InterpolationSource.

        :param source: The interpolation source to convert.
        :return: ProvenanceNode representing this source.
        """
        if source.kind == "config":
            return ProvenanceNode(
                source_type=NodeSourceType.INTERPOLATION,
                path=source.path,
                file=source.file,
                line=source.line,
                value=source.value,
                expression=source.expression,
            )
        elif source.kind == "env":
            return ProvenanceNode(
                source_type=NodeSourceType.ENV,
                env_var=source.env_var,
                value=source.value,
                expression=source.expression,
            )
        elif source.kind == "literal":
            return ProvenanceNode(
                source_type=NodeSourceType.FILE,
                value=source.value,
                expression=source.expression,
            )
        elif source.kind == "expression":
            # Build children first for frozen dataclass
            children = tuple(
                self._build_interpolation_tree(child_source)
                for child_source in source.sources
            )
            return ProvenanceNode(
                source_type=NodeSourceType.OPERATOR,
                operator=source.operator,
                value=source.value,
                expression=source.expression,
                children=children,
            )
        elif source.kind == "resolver":
            # Build children first for frozen dataclass
            children = tuple(
                self._build_interpolation_tree(child_source)
                for child_source in source.sources
            )
            return ProvenanceNode(
                source_type=NodeSourceType.RESOLVER,
                value=source.value,
                expression=source.expression,
                resolver_name=source.resolver_path,
                resolver_func=source.resolver_func,
                resolver_module=source.resolver_module,
                children=children,
            )
        else:
            return ProvenanceNode(
                source_type=NodeSourceType.FILE,
                value=source.value,
                expression=source.expression,
            )


class Provenance(Mapping[str, ProvenanceEntry]):
    """Immutable mapping of config paths to their provenance entries.

    The Provenance object stores where each config value came from,
    including the source file, line number, and any values that were
    overridden during composition.

    Implements the ``Mapping`` protocol for Pythonic access::

        entry = prov["model.layers"]           # __getitem__
        entry = prov.get("model.layers")       # get() with None default
        "model.layers" in prov                 # __contains__
        len(prov)                              # __len__
        for path in prov:                      # __iter__ (keys)
            print(path)
        for path, entry in prov.items():       # items()
            print(f"{path}: {entry.file}:{entry.line}")

    Example::

        prov = rc.get_provenance("trainer.yaml")
        print(prov)
        # _target_: Trainer              # trainer.yaml:1
        # model:
        #   _target_: ResNet             # models/resnet.yaml:1
        #   layers: 50                   # trainer.yaml:5 (overrode models/resnet.yaml:2)

        origin = prov.get("model.layers")
        # ProvenanceEntry(file="trainer.yaml", line=5, overrode="models/resnet.yaml:2")
    """

    def __init__(
        self,
        entries: dict[str, ProvenanceEntry] | None = None,
        config: dict | None = None,
    ) -> None:
        """Initialize a provenance object with frozen entries.

        :param entries: Dictionary of path to ProvenanceEntry mappings.
        :param config: The composed configuration dictionary.
        """
        # Use MappingProxyType for true immutability
        self._entries: Mapping[str, ProvenanceEntry] = MappingProxyType(
            entries if entries is not None else {}
        )
        self._config: Mapping = MappingProxyType(
            config if config is not None else {}
        )

    # === Mapping protocol implementation ===

    def __getitem__(self, path: str) -> ProvenanceEntry:
        """Get origin info for a specific config path.

        :param path: The config path (e.g., "model.layers").
        :return: ProvenanceEntry for the path.
        :raises KeyError: If path is not found.
        """
        return self._entries[path]

    def __iter__(self) -> Iterator[str]:
        """Iterate over all config paths.

        :return: Iterator of config paths.
        """
        return iter(self._entries)

    def __len__(self) -> int:
        """Get the number of provenance entries.

        :return: Number of entries.
        """
        return len(self._entries)

    # === Additional methods (get, keys, values, items, __contains__) ===
    # are inherited from Mapping ABC

    # === Properties ===

    @property
    def config(self) -> Mapping:
        """Get the composed configuration dictionary.

        :return: Read-only view of the config dictionary.
        """
        return self._config

    # === Domain-specific methods ===

    def format(self, layout: ProvenanceLayout | None = None) -> ProvenanceFormat:
        """Create a format builder for customizing provenance output.

        :param layout: Optional custom layout. Uses TreeLayout if None.
        :return: ProvenanceFormat builder for method chaining.

        Example::

            # Use default full format
            print(prov.format())

            # Use minimal preset
            print(prov.format().minimal())

            # Custom options
            print(prov.format().hide_chain().for_path("/model.*"))

            # Custom layout
            print(prov.format(layout=TableLayout()))
        """
        from .ProvenanceFormat import ProvenanceFormat

        return ProvenanceFormat(self, layout)

    def to_dict(self) -> dict[str, Any]:
        """Convert the entire provenance to a dictionary.

        :return: Dictionary with paths as keys and entry dicts as values.

        Example::

            data = prov.to_dict()
            for path, entry_data in data.items():
                print(f"{path}: {entry_data}")
        """
        return {path: entry.to_dict() for path, entry in self._entries.items()}

    def trace(self, path: str) -> ProvenanceNode | None:
        """Get the provenance tree for a specific path.

        Builds a tree structure showing the full origin chain including
        interpolations, instances, and refs.

        :param path: The config path to trace.
        :return: Root ProvenanceNode or None if path not found.

        Example::

            tree = prov.trace("model.lr")
            if tree:
                print(tree.to_dict())
        """
        entry = self._entries.get(path)
        if entry is None:
            return None
        return entry.trace()

    def __str__(self) -> str:
        """Format provenance as a string showing config with origins.

        :return: Formatted string with config values and their sources.
        """
        if not self._config:
            return ""

        lines: list[str] = []
        self._format_value(self._config, "", lines, 0)
        return "\n".join(lines)

    def __repr__(self) -> str:
        """Return a debug-friendly representation.

        :return: String representation showing entry count.
        """
        return f"Provenance(entries={len(self._entries)})"

    def __bool__(self) -> bool:
        """Return False if empty, True otherwise.

        :return: Boolean indicating if provenance has entries.
        """
        return len(self._entries) > 0

    def _format_value(
        self,
        value: object,
        path: str,
        lines: list[str],
        indent: int,
    ) -> None:
        """Recursively format a value with provenance annotations.

        :param value: The value to format.
        :param path: Current config path.
        :param lines: List to append formatted lines to.
        :param indent: Current indentation level.
        """
        prefix = "  " * indent

        if isinstance(value, Mapping):
            for key, val in value.items():
                current_path = f"{path}.{key}" if path else key
                entry = self._entries.get(current_path)
                annotation = self._format_annotation(entry)

                if isinstance(val, Mapping):
                    lines.append(f"{prefix}{key}:{annotation}")
                    self._format_value(val, current_path, lines, indent + 1)
                elif isinstance(val, list):
                    lines.append(f"{prefix}{key}:{annotation}")
                    self._format_list(val, current_path, lines, indent + 1)
                else:
                    lines.append(f"{prefix}{key}: {self._format_scalar(val)}{annotation}")
        else:
            entry = self._entries.get(path)
            annotation = self._format_annotation(entry)
            lines.append(f"{prefix}{self._format_scalar(value)}{annotation}")

    def _format_list(
        self,
        items: list,
        path: str,
        lines: list[str],
        indent: int,
    ) -> None:
        """Format a list with provenance annotations.

        :param items: The list to format.
        :param path: Current config path.
        :param lines: List to append formatted lines to.
        :param indent: Current indentation level.
        """
        prefix = "  " * indent
        for i, item in enumerate(items):
            item_path = build_child_path(path, i)
            entry = self._entries.get(item_path)
            annotation = self._format_annotation(entry)

            if isinstance(item, Mapping):
                lines.append(f"{prefix}-{annotation}")
                self._format_value(item, item_path, lines, indent + 1)
            elif isinstance(item, list):
                lines.append(f"{prefix}-{annotation}")
                self._format_list(item, item_path, lines, indent + 1)
            else:
                lines.append(f"{prefix}- {self._format_scalar(item)}{annotation}")

    def _format_scalar(self, value: object) -> str:
        """Format a scalar value for display.

        :param value: The scalar value to format.
        :return: Formatted string representation.
        """
        if value is None:
            return "null"
        elif isinstance(value, bool):
            return "true" if value else "false"
        elif isinstance(value, str):
            # Quote strings that need it
            if " " in value or ":" in value or value.startswith(("'", '"')):
                return f'"{value}"'
            return value
        else:
            return str(value)

    def _format_annotation(self, entry: ProvenanceEntry | None) -> str:
        """Format a provenance annotation.

        :param entry: The provenance entry to format.
        :return: Formatted annotation string.
        """
        if entry is None:
            return ""

        annotation = f"  # {entry.file}:{entry.line}"
        if entry.overrode:
            annotation += f" (overrode {entry.overrode})"
        if entry.interpolation:
            annotation += f" (interpolated: ${{{entry.interpolation.expression}}})"

        return annotation
