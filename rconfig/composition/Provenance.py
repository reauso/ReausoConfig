"""Provenance tracking for config composition.

This module provides classes for tracking the origin of each value
in a composed configuration, including file paths, line numbers,
override information, and interpolation sources.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Iterator, Literal

from rconfig._internal.path_utils import build_child_path

if TYPE_CHECKING:
    from rconfig.interpolation.evaluator import InterpolationSource
    from .ProvenanceFormat import ProvenanceFormat
    from .ProvenanceLayout import ProvenanceLayout


@dataclass
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

    source_type: Literal[
        "file",
        "ref",
        "instance",
        "interpolation",
        "cli",
        "env",
        "programmatic",
        "operator",
        "resolver",
    ]
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
    children: list[ProvenanceNode] = field(default_factory=list)

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


@dataclass
class InstanceRef:
    """Reference to an instance in the instance chain.

    :param path: The instance path (e.g., "/shared.database" or "alias").
    :param file: File where the referenced object is defined.
    :param line: Line number where the referenced object is defined.
    """

    path: str
    file: str
    line: int


@dataclass
class ProvenanceEntry:
    """Origin information for a config value.

    :param file: Source file path.
    :param line: Line number in source file.
    :param overrode: What this value overrode (if any), format: "file:line".
    :param instance: Chain of instance references with origins.
    :param interpolation: Source info if value was interpolated.
    :param source_type: Type of source (file, cli, env, programmatic).
    :param cli_arg: CLI argument if source_type is "cli".
    :param env_var: Environment variable name if source_type is "env".
    :param value: The resolved value at this path.
    :param target_name: The _target_ string from config (e.g., "resnet").
    :param target_class: The resolved class name (e.g., "ResNet").
    :param target_module: The module path (e.g., "myapp.models").
    :param target_auto_registered: Whether the target was auto-registered.
    """

    file: str
    line: int
    overrode: str | None = None
    instance: list[InstanceRef] | None = None
    interpolation: InterpolationSource | None = None
    source_type: Literal["file", "cli", "env", "programmatic"] = "file"
    cli_arg: str | None = None
    env_var: str | None = None
    value: Any = None
    target_name: str | None = None
    target_class: str | None = None
    target_module: str | None = None
    target_auto_registered: bool = False

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

        return result

    def trace(self) -> ProvenanceNode:
        """Build a provenance tree from this entry.

        Follows interpolation sources recursively to build the full tree.

        :return: Root node of the provenance tree.
        """
        # Determine the root node type based on source_type
        if self.source_type == "cli":
            root = ProvenanceNode(
                source_type="cli",
                file=self.file,
                line=self.line,
                value=self.value,
                cli_arg=self.cli_arg,
            )
        elif self.source_type == "env":
            root = ProvenanceNode(
                source_type="env",
                file=self.file,
                line=self.line,
                value=self.value,
                env_var=self.env_var,
            )
        elif self.source_type == "programmatic":
            root = ProvenanceNode(
                source_type="programmatic",
                value=self.value,
            )
        else:
            root = ProvenanceNode(
                source_type="file",
                file=self.file,
                line=self.line,
                value=self.value,
            )

        # Add interpolation tree if present
        if self.interpolation:
            interp_node = self._build_interpolation_tree(self.interpolation)
            root.children.append(interp_node)

        # Add instance chain if present
        if self.instance:
            for ref in self.instance:
                instance_node = ProvenanceNode(
                    source_type="instance",
                    path=ref.path,
                    file=ref.file,
                    line=ref.line,
                )
                root.children.append(instance_node)

        return root

    def _build_interpolation_tree(
        self, source: InterpolationSource
    ) -> ProvenanceNode:
        """Recursively build tree from InterpolationSource.

        :param source: The interpolation source to convert.
        :return: ProvenanceNode representing this source.
        """
        if source.kind == "config":
            node = ProvenanceNode(
                source_type="interpolation",
                path=source.path,
                file=source.file,
                line=source.line,
                value=source.value,
                expression=source.expression,
            )
        elif source.kind == "env":
            node = ProvenanceNode(
                source_type="env",
                env_var=source.env_var,
                value=source.value,
                expression=source.expression,
            )
        elif source.kind == "literal":
            node = ProvenanceNode(
                source_type="file",
                value=source.value,
                expression=source.expression,
            )
        elif source.kind == "expression":
            node = ProvenanceNode(
                source_type="operator",
                operator=source.operator,
                value=source.value,
                expression=source.expression,
            )
            # Add children from compound expression
            for child_source in source.sources:
                child_node = self._build_interpolation_tree(child_source)
                node.children.append(child_node)
        elif source.kind == "resolver":
            node = ProvenanceNode(
                source_type="resolver",
                value=source.value,
                expression=source.expression,
                resolver_name=source.resolver_path,
                resolver_func=source.resolver_func,
                resolver_module=source.resolver_module,
            )
            # Add children from resolver arguments
            for child_source in source.sources:
                child_node = self._build_interpolation_tree(child_source)
                node.children.append(child_node)
        else:
            node = ProvenanceNode(
                source_type="file",
                value=source.value,
                expression=source.expression,
            )

        return node


class Provenance:
    """Tracks the origin of each value in a composed config.

    The Provenance object stores where each config value came from,
    including the source file, line number, and any values that were
    overridden during composition.

    Example::

        prov = composer.compose_with_provenance("trainer.yaml")
        print(prov)
        # _target_: Trainer              # trainer.yaml:1
        # model:
        #   _target_: ResNet             # models/resnet.yaml:1
        #   layers: 50                   # trainer.yaml:5 (overrode models/resnet.yaml:2)

        origin = prov.get("model.layers")
        # ProvenanceEntry(file="trainer.yaml", line=5, overrode="models/resnet.yaml:2")
    """

    def __init__(self) -> None:
        """Initialize an empty provenance tracker."""
        self._entries: dict[str, ProvenanceEntry] = {}
        self._config: dict = {}

    def add(
        self,
        path: str,
        file: str,
        line: int,
        overrode: str | None = None,
        instance: list[InstanceRef] | None = None,
        target_name: str | None = None,
    ) -> None:
        """Add a provenance entry for a config path.

        :param path: The config path (e.g., "model.layers").
        :param file: Source file path.
        :param line: Line number in source file.
        :param overrode: What this value overrode (format: "file:line").
        :param instance: Chain of instance references.
        :param target_name: The _target_ string if this entry has one.
        """
        self._entries[path] = ProvenanceEntry(
            file=file,
            line=line,
            overrode=overrode,
            instance=instance,
            target_name=target_name,
        )

    def set_config(self, config: dict) -> None:
        """Set the composed config for formatted output.

        Also populates the `value` field of each provenance entry from the
        resolved config, for entries that don't already have a value set
        (e.g., from interpolation resolution).

        :param config: The composed configuration dictionary.
        """
        from rconfig._internal.path_utils import get_value_at_path

        self._config = config

        # Populate values for all entries
        for path, entry in self._entries.items():
            if entry.value is None:
                try:
                    entry.value = get_value_at_path(config, path)
                except (KeyError, IndexError, TypeError):
                    # Path no longer exists in config (e.g., removed by override)
                    pass

    def get(self, path: str) -> ProvenanceEntry | None:
        """Get origin info for a specific config path.

        :param path: The config path (e.g., "model.layers").
        :return: ProvenanceEntry if path exists, None otherwise.

        Example::

            entry = prov.get("model.layers")
            if entry:
                print(f"Defined at {entry.file}:{entry.line}")
        """
        return self._entries.get(path)

    def items(self) -> Iterator[tuple[str, ProvenanceEntry]]:
        """Iterate over all paths and their origins.

        :return: Iterator of (path, ProvenanceEntry) tuples.

        Example::

            for path, entry in prov.items():
                print(f"{path}: {entry.file}:{entry.line}")
        """
        return iter(self._entries.items())

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

    def resolve_targets(
        self,
        known_references: dict[str, Any],
        auto_registered: set[str] | None = None,
    ) -> None:
        """Resolve target class information from registered targets.

        For each entry with a target_name, looks up the target in the
        known_references and populates target_class and target_module.

        :param known_references: Mapping of target names to ConfigReference objects.
                                Each ConfigReference must have a `target_class` attribute.
        :param auto_registered: Optional set of target names that were auto-registered.
                               These will be marked with target_auto_registered=True.

        Example::

            prov.resolve_targets(store.known_references)
        """
        auto_registered = auto_registered or set()

        for entry in self._entries.values():
            if entry.target_name is None:
                continue

            # Look up the target in known_references
            ref = known_references.get(entry.target_name)
            if ref is None:
                # Target not registered - leave target_class as None
                continue

            # Get class information
            target_class = ref.target_class
            entry.target_class = target_class.__name__
            entry.target_module = target_class.__module__

            # Mark if auto-registered
            if entry.target_name in auto_registered:
                entry.target_auto_registered = True

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

        if isinstance(value, dict):
            for key, val in value.items():
                current_path = f"{path}.{key}" if path else key
                entry = self._entries.get(current_path)
                annotation = self._format_annotation(entry)

                if isinstance(val, dict):
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

            if isinstance(item, dict):
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
