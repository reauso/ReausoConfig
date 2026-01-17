"""Instance resolution for config composition.

This module provides the InstanceResolver class for resolving _instance_
references that were collected during config tree walking.
"""

from __future__ import annotations

from typing import Any

from .IncrementalComposer import InstanceMarker
from rconfig.errors import CircularInstanceError, InstanceResolutionError
from rconfig._internal.path_utils import build_child_path, get_value_at_path
from rconfig.provenance import InstanceRef, ProvenanceBuilder


# Special key for instance markers
_INSTANCE_KEY = "_instance_"


class InstanceResolver:
    """Resolves _instance_ references for object sharing.

    This class takes collected instance markers from IncrementalComposer
    and resolves them to actual values, handling chains, cycles, and
    null instances. Provenance is always tracked.

    Example::

        builder = ProvenanceBuilder()
        resolver = InstanceResolver(builder)
        config = resolver.resolve(walk_result.instances, walk_result.config)
    """

    def __init__(self, provenance: ProvenanceBuilder) -> None:
        """Initialize the resolver.

        :param provenance: ProvenanceBuilder to record value origins.
        """
        self._provenance = provenance
        self._instance_targets: dict[str, str | None] = {}

    @property
    def instance_targets(self) -> dict[str, str | None]:
        """Get the mapping of instance paths to their resolved target paths.

        This is used by ConfigInstantiator to share instantiated objects.
        Each key is a config path where an _instance_ reference was found,
        and the value is the target config path it resolves to (or None for null).
        """
        return self._instance_targets.copy()

    def resolve(
        self,
        instances: dict[str, InstanceMarker],
        config: dict[str, Any],
    ) -> dict[str, Any]:
        """Resolve all _instance_ references in the config.

        :param instances: Instance markers collected during walking.
        :param config: The config with _instance_ markers to resolve.
        :return: Config with all _instance_ references resolved.
        :raises InstanceResolutionError: If an instance path cannot be resolved.
        :raises CircularInstanceError: If circular instance references detected.
        """
        if not instances:
            return config

        # Build a resolution order to detect cycles
        # and resolve chained instances correctly
        resolved: dict[str, Any] = {}
        resolving: set[str] = set()

        def resolve_instance_at_path(config_path: str) -> Any:
            """Resolve a single instance reference, handling chains."""
            if config_path in resolved:
                return resolved[config_path]

            if config_path not in instances:
                # Not an instance reference, get value from config
                return get_value_at_path(config, config_path)

            if config_path in resolving:
                # Cycle detected
                cycle = list(resolving) + [config_path]
                raise CircularInstanceError(cycle)

            resolving.add(config_path)

            marker = instances[config_path]

            # Handle _instance_: null
            if marker.instance_path is None:
                resolved[config_path] = None
                self._instance_targets[config_path] = None
                resolving.discard(config_path)
                # Track provenance for null instance
                self._provenance.add(
                    config_path, file=marker.file_path, line=marker.line
                )
                return None

            # Resolve the instance path to an absolute config path
            target_config_path = self._resolve_instance_path(
                marker.instance_path, config_path, config
            )

            # Build the instance chain for provenance
            instance_chain: list[InstanceRef] = []

            # Follow the chain if target is also an instance
            current_target = target_config_path
            visited_for_chain: set[str] = {config_path}
            chain_ends_with_null = False

            while current_target in instances:
                if current_target in visited_for_chain:
                    # Cycle in the chain
                    cycle = [config_path] + list(visited_for_chain) + [current_target]
                    raise CircularInstanceError(cycle)
                visited_for_chain.add(current_target)

                chain_marker = instances[current_target]
                instance_chain.append(
                    InstanceRef(
                        path=chain_marker.instance_path or "",
                        file=chain_marker.file_path,
                        line=chain_marker.line,
                    )
                )

                if chain_marker.instance_path is None:
                    # Chain ends with null
                    chain_ends_with_null = True
                    break

                # Resolve the next hop
                current_target = self._resolve_instance_path(
                    chain_marker.instance_path, current_target, config
                )

            # Get the actual value from the resolved path
            if chain_ends_with_null:
                value = None
                # Track that this instance resolves to null
                self._instance_targets[config_path] = None
            else:
                value = get_value_at_path(config, current_target)
                # Track the final target for instance sharing
                self._instance_targets[config_path] = current_target
            resolved[config_path] = value

            # Track provenance with instance chain
            full_chain = [
                InstanceRef(
                    path=marker.instance_path,
                    file=marker.file_path,
                    line=marker.line,
                )
            ] + instance_chain

            # Get the origin of the final target
            target_entry = self._provenance.get(current_target)
            target_file = target_entry.file if target_entry else marker.file_path
            target_line = target_entry.line if target_entry else marker.line

            self._provenance.add(
                config_path,
                file=target_file,
                line=target_line,
                instance=full_chain,
            )

            resolving.discard(config_path)
            return value

        # Resolve all instances
        for config_path in instances:
            resolve_instance_at_path(config_path)

        # Replace markers in config with resolved values
        return self._config_with_resolved_instances(config, resolved)

    def _resolve_instance_path(
        self,
        instance_path: str,
        config_path: str,
        config: dict[str, Any],
    ) -> str:
        """Resolve an _instance_ path to an absolute config path.

        Path resolution rules:
        - `/path.to.key` - Absolute from composed config root
        - `path.to.key` - Relative (same as absolute for now)
        - `./path.to.key` - Same as above (relative)

        :param instance_path: The _instance_ path string.
        :param config_path: The config path where the instance reference is.
        :param config: The full composed config.
        :return: Absolute config path.
        :raises InstanceResolutionError: If path cannot be resolved.
        """
        # Normalize the path
        if instance_path.startswith("/"):
            # Absolute path from config root
            target_path = instance_path[1:]
        elif instance_path.startswith("./"):
            # Explicit relative from file root
            target_path = instance_path[2:]
        else:
            # Relative path (same as ./)
            target_path = instance_path

        # Verify the path exists in the config
        try:
            get_value_at_path(config, target_path)
        except (KeyError, IndexError, TypeError) as e:
            raise InstanceResolutionError(
                instance_path,
                f"path not found in config: {e}",
                config_path,
                hint="Ensure the path exists in the config. Use dot notation (e.g., 'database.connection').",
            )

        return target_path

    def _config_with_resolved_instances(
        self,
        config: dict[str, Any],
        resolved: dict[str, Any],
    ) -> dict[str, Any]:
        """Return config with all _instance_ markers replaced with resolved values.

        :param config: The config with markers.
        :param resolved: Map of config paths to resolved values.
        :return: Config with markers replaced.
        """
        result = self._deep_copy_with_resolved_instances(config, "", resolved)
        return result

    def _deep_copy_with_resolved_instances(
        self,
        value: Any,
        path: str,
        resolved: dict[str, Any],
    ) -> Any:
        """Return deep copy of value with _instance_ markers replaced by resolved values.

        :param value: The value to copy.
        :param path: Current path in config.
        :param resolved: Map of config paths to resolved values.
        :return: Copied value with instances resolved.
        """
        if isinstance(value, dict):
            # Check if this is an _instance_ marker
            if _INSTANCE_KEY in value and len(value) == 1:
                if path in resolved:
                    return resolved[path]
                # If not in resolved, it means _instance_: null -> return None
                return None

            # Regular dict - recursively process
            result = {}
            for key, val in value.items():
                child_path = f"{path}.{key}" if path else key
                result[key] = self._deep_copy_with_resolved_instances(
                    val, child_path, resolved
                )
            return result

        elif isinstance(value, list):
            result = []
            for i, item in enumerate(value):
                item_path = build_child_path(path, i)
                result.append(
                    self._deep_copy_with_resolved_instances(item, item_path, resolved)
                )
            return result

        else:
            return value
