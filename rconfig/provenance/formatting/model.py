"""Display models for provenance formatting.

This module provides data structures that represent provenance data
ready for display by layouts. The display models contain only
the data that should be displayed - layouts render what's present.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from rconfig.deprecation.info import DeprecationInfo
from rconfig.provenance.models import EntrySourceType, InstanceRef


class InterpolationKind(StrEnum):
    """Kind of interpolation source node.

    :cvar EXPRESSION: Compound expression with operator.
    :cvar CONFIG: Config path reference.
    :cvar ENV: Environment variable reference.
    :cvar LITERAL: Literal value.
    """

    EXPRESSION = "expression"
    CONFIG = "config"
    ENV = "env"
    LITERAL = "literal"


@dataclass(frozen=True)
class InterpolationNodeDisplayModel:
    """Single interpolation tree node to display.

    Contains the data needed to render an interpolation source node.
    Layouts decide how to format connectors and structure.

    :param kind: Type of node.
    :param is_last: Whether this is the last sibling (for connector choice).
    :param text: The main text (path, operator, or value).
    :param value: The resolved value, or None if hidden.
    :param file: Source file, or None if hidden.
    :param line: Line number, or None if hidden.
    :param children: Child nodes for compound expressions.
    """

    kind: InterpolationKind
    is_last: bool
    text: str
    value: Any | None
    file: str | None
    line: int | None
    children: tuple[InterpolationNodeDisplayModel, ...]


@dataclass(frozen=True)
class ProvenanceEntryDisplayModel:
    """Single provenance entry to display.

    Contains only the data that will be displayed. Layouts render
    what's present without checking visibility flags.

    :param path: The config path (without leading /), or None if hidden.
    :param value: The resolved value, or None if hidden.
    :param file: Source file name, or None if hidden.
    :param line: Line number, or None if hidden.
    :param source_type: Source type (CLI/env/file), or None if hidden.
    :param cli_arg: CLI argument name if source is CLI, or None.
    :param env_var: Environment variable name if source is env, or None.
    :param target_name: Target name, or None if hidden.
    :param target_class: Target class name, or None.
    :param target_module: Target module name, or None.
    :param target_auto_registered: Whether target was auto-registered.
    :param interpolation_expression: Interpolation expression, or None if hidden.
    :param interpolation_tree: Tree of interpolation nodes, or None if hidden.
    :param instances: Tuple of instance refs, or None if hidden.
    :param overrode: What was overridden, or None if hidden.
    :param deprecation: Deprecation info, or None if hidden.
    :param type_hint: Type hint, or None if hidden.
    :param description: Description text, or None if hidden.
    """

    path: str | None
    value: Any | None
    file: str | None
    line: int | None
    source_type: EntrySourceType | None
    cli_arg: str | None
    env_var: str | None
    target_name: str | None
    target_class: str | None
    target_module: str | None
    target_auto_registered: bool
    interpolation_expression: str | None
    interpolation_tree: tuple[InterpolationNodeDisplayModel, ...] | None
    instances: tuple[InstanceRef, ...] | None
    overrode: str | None
    deprecation: DeprecationInfo | None
    type_hint: Any | None
    description: str | None


@dataclass(frozen=True)
class ProvenanceDisplayModel:
    """Complete display model for provenance output.

    Contains all entries to display and optional header/empty message.

    :param entries: Tuple of entry display models to render.
    :param header: Optional header text (e.g., "Deprecated Keys:").
    :param empty_message: Message to show when no entries match.
    """

    entries: tuple[ProvenanceEntryDisplayModel, ...]
    header: str | None
    empty_message: str | None


class ProvenanceDisplayModelBuilder:
    """Builds ProvenanceDisplayModel via add calls.

    The builder collects entries via add_entry() calls and builds
    the final model. It has no filtering logic - the Format class
    decides what to add.
    """

    def __init__(self) -> None:
        """Initialize the builder."""
        self._entries: list[ProvenanceEntryDisplayModel] = []
        self._header: str | None = None
        self._empty_message: str | None = None

    def add_entry(
        self,
        path: str | None = None,
        value: Any | None = None,
        file: str | None = None,
        line: int | None = None,
        source_type: EntrySourceType | None = None,
        cli_arg: str | None = None,
        env_var: str | None = None,
        target_name: str | None = None,
        target_class: str | None = None,
        target_module: str | None = None,
        target_auto_registered: bool = False,
        interpolation_expression: str | None = None,
        interpolation_tree: tuple[InterpolationNodeDisplayModel, ...] | None = None,
        instances: tuple[InstanceRef, ...] | None = None,
        overrode: str | None = None,
        deprecation: DeprecationInfo | None = None,
        type_hint: Any | None = None,
        description: str | None = None,
    ) -> None:
        """Add an entry to display.

        :param path: The config path (without leading /), or None if hidden.
        :param value: The resolved value, or None if hidden.
        :param file: Source file name, or None if hidden.
        :param line: Line number, or None if hidden.
        :param source_type: Source type, or None if hidden.
        :param cli_arg: CLI argument name, or None.
        :param env_var: Environment variable name, or None.
        :param target_name: Target name, or None if hidden.
        :param target_class: Target class name, or None.
        :param target_module: Target module name, or None.
        :param target_auto_registered: Whether target was auto-registered.
        :param interpolation_expression: Interpolation expression, or None.
        :param interpolation_tree: Interpolation tree nodes, or None.
        :param instances: Instance refs, or None if hidden.
        :param overrode: Override info, or None if hidden.
        :param deprecation: Deprecation info, or None if hidden.
        :param type_hint: Type hint, or None if hidden.
        :param description: Description, or None if hidden.
        """
        self._entries.append(
            ProvenanceEntryDisplayModel(
                path=path,
                value=value,
                file=file,
                line=line,
                source_type=source_type,
                cli_arg=cli_arg,
                env_var=env_var,
                target_name=target_name,
                target_class=target_class,
                target_module=target_module,
                target_auto_registered=target_auto_registered,
                interpolation_expression=interpolation_expression,
                interpolation_tree=interpolation_tree,
                instances=instances,
                overrode=overrode,
                deprecation=deprecation,
                type_hint=type_hint,
                description=description,
            )
        )

    def set_header(self, header: str) -> None:
        """Set the header text.

        :param header: The header text to display.
        """
        self._header = header

    def set_empty_message(self, message: str) -> None:
        """Set message for empty result.

        :param message: The empty message to display.
        """
        self._empty_message = message

    def build(self) -> ProvenanceDisplayModel:
        """Build the final display model.

        :return: The display model ready for layout rendering.
        """
        return ProvenanceDisplayModel(
            entries=tuple(self._entries),
            header=self._header,
            empty_message=self._empty_message,
        )
