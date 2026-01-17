"""Builder for constructing Provenance objects.

This module provides ProvenanceBuilder, a mutable builder class that
accumulates provenance entries during config composition and produces
an immutable Provenance object when complete.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from rconfig._internal.path_utils import get_value_at_path

from .models import EntrySourceType, InstanceRef

if TYPE_CHECKING:
    from rconfig.deprecation.info import DeprecationInfo
    from rconfig.interpolation.evaluator import InterpolationSource


@dataclass
class _MutableEntry:
    """Mutable entry used during building.

    This is converted to a frozen ProvenanceEntry when build() is called.
    """

    file: str
    line: int
    overrode: str | None = None
    instance: list[InstanceRef] | None = None
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


class ProvenanceBuilder:
    """Mutable builder for constructing Provenance objects.

    Used internally during config composition to accumulate provenance
    entries. Call build() to produce an immutable Provenance object.

    Example::

        builder = ProvenanceBuilder()
        builder.add("model.lr", "config.yaml", 5)
        builder.add("model.layers", "config.yaml", 6)
        builder.set_config({"model": {"lr": 0.01, "layers": 50}})
        provenance = builder.build()
    """

    def __init__(self) -> None:
        """Initialize an empty provenance builder."""
        self._entries: dict[str, _MutableEntry] = {}
        self._config: dict = {}

    def add(
        self,
        path: str,
        file: str,
        line: int,
        overrode: str | None = None,
        instance: list[InstanceRef] | None = None,
        target_name: str | None = None,
        source_type: EntrySourceType = EntrySourceType.FILE,
        cli_arg: str | None = None,
        env_var: str | None = None,
        deprecation: "DeprecationInfo | None" = None,
        interpolation: "InterpolationSource | None" = None,
        value: Any = None,
        type_hint: type | None = None,
        description: str | None = None,
    ) -> None:
        """Add a provenance entry for a config path.

        :param path: The config path (e.g., "model.layers").
        :param file: Source file path.
        :param line: Line number in source file.
        :param overrode: What this value overrode (format: "file:line").
        :param instance: Chain of instance references.
        :param target_name: The _target_ string if this entry has one.
        :param source_type: Source type (file, cli, env, programmatic).
        :param cli_arg: CLI argument string if from CLI.
        :param env_var: Environment variable name if from env.
        :param deprecation: Deprecation info if key is deprecated.
        :param interpolation: Interpolation source info.
        :param value: Pre-set value (overrides config lookup).
        :param type_hint: Type hint for the value.
        :param description: Description from structured config.
        """
        self._entries[path] = _MutableEntry(
            file=file,
            line=line,
            overrode=overrode,
            instance=instance,
            target_name=target_name,
            source_type=source_type,
            cli_arg=cli_arg,
            env_var=env_var,
            deprecation=deprecation,
            interpolation=interpolation,
            value=value,
            type_hint=type_hint,
            description=description,
        )

    def set_config(self, config: dict) -> None:
        """Set the composed config for formatted output.

        Also populates the `value` field of each provenance entry from the
        resolved config, for entries that don't already have a value set
        (e.g., from interpolation resolution).

        :param config: The composed configuration dictionary.
        """
        self._config = config

        # Populate values for all entries
        for path, entry in self._entries.items():
            if entry.value is None:
                try:
                    entry.value = get_value_at_path(config, path)
                except (KeyError, IndexError, TypeError):
                    # Path no longer exists in config (e.g., removed by override)
                    pass

    def resolve_targets(
        self,
        known_targets: dict[str, Any],
        auto_registered: set[str] | None = None,
    ) -> None:
        """Resolve target class information from registered targets.

        For each entry with a target_name, looks up the target in the
        known_targets and populates target_class and target_module.

        :param known_targets: Mapping of target names to TargetEntry objects.
                                Each TargetEntry must have a `target_class` attribute.
        :param auto_registered: Optional set of target names that were auto-registered.
                               These will be marked with target_auto_registered=True.

        Example::

            builder.resolve_targets(store.known_targets)
        """
        auto_registered = auto_registered or set()

        for entry in self._entries.values():
            if entry.target_name is None:
                continue

            # Look up the target in known_targets
            ref = known_targets.get(entry.target_name)
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

    def get(self, path: str) -> _MutableEntry | None:
        """Get a mutable entry for a path.

        :param path: The config path to look up.
        :return: Mutable entry if exists, None otherwise.
        """
        return self._entries.get(path)

    def get_entry(self, path: str) -> _MutableEntry | None:
        """Get a mutable entry for a path (internal use during composition).

        Alias for get() for compatibility.

        :param path: The config path to look up.
        :return: Mutable entry if exists, None otherwise.
        """
        return self._entries.get(path)

    def build(self) -> "Provenance":
        """Build an immutable Provenance object from accumulated entries.

        :return: Immutable Provenance object.
        """
        from .provenance import Provenance
        from .models import ProvenanceEntry

        # Convert mutable entries to frozen ProvenanceEntry objects
        frozen_entries: dict[str, ProvenanceEntry] = {}
        for path, entry in self._entries.items():
            # Convert instance list to tuple for frozen dataclass
            instance_tuple = (
                tuple(entry.instance) if entry.instance is not None else None
            )
            frozen_entries[path] = ProvenanceEntry(
                file=entry.file,
                line=entry.line,
                overrode=entry.overrode,
                instance=instance_tuple,
                interpolation=entry.interpolation,
                source_type=entry.source_type,
                cli_arg=entry.cli_arg,
                env_var=entry.env_var,
                value=entry.value,
                target_name=entry.target_name,
                target_class=entry.target_class,
                target_module=entry.target_module,
                target_auto_registered=entry.target_auto_registered,
                deprecation=entry.deprecation,
                type_hint=entry.type_hint,
                description=entry.description,
            )

        return Provenance(frozen_entries, self._config)

    def items(self):
        """Iterate over (path, entry) pairs.

        :return: Iterator of (path, _MutableEntry) tuples.
        """
        return self._entries.items()

    @property
    def config(self) -> dict:
        """Get the config dictionary (for use during composition).

        :return: The config dictionary.
        """
        return self._config
