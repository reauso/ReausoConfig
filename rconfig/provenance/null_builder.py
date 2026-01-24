"""Null implementation of ProvenanceBuilder for when tracking is disabled.

This module provides NullProvenanceBuilder, a no-op subclass of
ProvenanceBuilder used when provenance tracking is not needed (e.g.,
during instantiate() which never exposes provenance). All methods are
no-ops that return immediately, eliminating tracking overhead.
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from .builder import ProvenanceBuilder

if TYPE_CHECKING:
    from rconfig.deprecation.info import DeprecationInfo
    from rconfig.interpolation.evaluator import InterpolationSource
    from .models import EntrySourceType, InstanceRef


class NullProvenanceBuilder(ProvenanceBuilder):
    """No-op provenance builder for when tracking is disabled.

    All methods are no-ops that return immediately. This allows
    composition and instance resolution code to call provenance
    methods unconditionally without performance cost.

    Used internally by ConfigComposer.compose() since instantiate()
    never exposes provenance to callers.

    Example::

        builder = NullProvenanceBuilder()
        builder.add("model.lr", "config.yaml", 5)  # No-op
        builder.set_config({})  # No-op
        builder.build()  # Returns None
    """

    def __init__(self) -> None:
        """Initialize without allocating any internal state."""

    def add(
        self,
        path: str,
        file: str,
        line: int,
        overrode: str | None = None,
        instance: "list[InstanceRef] | None" = None,
        target_name: str | None = None,
        source_type: "EntrySourceType | None" = None,
        cli_arg: str | None = None,
        env_var: str | None = None,
        deprecation: "DeprecationInfo | None" = None,
        interpolation: "InterpolationSource | None" = None,
        value: Any = None,
        type_hint: type | None = None,
        description: str | None = None,
    ) -> None:
        """No-op: discard provenance entry."""

    def set_config(self, config: dict) -> None:
        """No-op: discard config."""

    def resolve_targets(
        self,
        known_targets: dict[str, Any],
        auto_registered: set[str] | None = None,
    ) -> None:
        """No-op: skip target resolution."""

    def get(self, path: str) -> None:
        """Always returns None."""
        return None

    def get_entry(self, path: str) -> None:
        """Always returns None."""
        return None

    def build(self) -> None:
        """Returns None (no provenance collected)."""
        return None

    def items(self):
        """Returns empty iterator."""
        return iter([])

    @property
    def config(self) -> dict:
        """Returns empty dict."""
        return {}
