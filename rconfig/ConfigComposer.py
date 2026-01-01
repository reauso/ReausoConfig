"""Config composer for resolving _ref_ references and composing configs.

This module provides functionality for loading config files that reference
other config files via `_ref_`, merging them together with deep merge semantics.
It also handles `_instance_` references for shared object instances.
"""

from pathlib import Path
from typing import Any

from .CompositionWalker import CompositionWalker, clear_cache, set_cache_size
from .InstanceResolver import InstanceResolver
from .Provenance import Provenance


# Re-export cache functions for backwards compatibility
__all__ = [
    "ConfigComposer",
    "compose",
    "compose_with_provenance",
    "set_cache_size",
    "clear_cache",
]


class ConfigComposer:
    """Composes config files by resolving _ref_ and _instance_ references.

    The composer loads a config file and recursively resolves any `_ref_`
    references found in the config tree. Referenced files are deep merged
    with any sibling override keys.

    After `_ref_` resolution, `_instance_` references are resolved to
    enable object sharing during instantiation.

    Example::

        composer = ConfigComposer(Path("/project/configs"))
        config = composer.compose(Path("/project/configs/app.yaml"))
    """

    def __init__(self, config_root: Path | None = None) -> None:
        """Initialize the composer.

        :param config_root: Root directory for absolute path resolution.
                           If None, derived from the composed file's parent.
        """
        self._config_root = config_root
        self._provenance: Provenance | None = None
        self._instance_resolver: InstanceResolver | None = None

    def compose(self, path: Path) -> dict[str, Any]:
        """Compose a config file by resolving all _ref_ references.

        :param path: Path to the entry-point config file.
        :return: Fully composed config dictionary.
        :raises ConfigFileError: If a file cannot be loaded.
        :raises CircularRefError: If circular references are detected.
        :raises RefAtRootError: If _ref_ is used at root level.
        :raises RefResolutionError: If a _ref_ cannot be resolved.
        :raises InstanceResolutionError: If an _instance_ path cannot be resolved.
        :raises CircularInstanceError: If circular _instance_ references detected.
        """
        # Always create provenance
        self._provenance = Provenance()

        # Compose the config tree, resolving _ref_ and collecting _instance_ markers
        walker = CompositionWalker(self._config_root, self._provenance)
        result = walker.compose(path)

        # Resolve all _instance_ references
        self._instance_resolver = InstanceResolver(self._provenance)
        config = self._instance_resolver.resolve(result.instances, result.config)

        self._provenance.set_config(config)
        return config

    @property
    def instance_targets(self) -> dict[str, str | None]:
        """Get the mapping of instance paths to their resolved target paths.

        This is used by ConfigInstantiator to share instantiated objects.
        Each key is a config path where an _instance_ reference was found,
        and the value is the target config path it resolves to (or None for null).

        Example::

            composer = ConfigComposer()
            config = composer.compose(Path("app.yaml"))
            # {
            #   "service_a.db": "shared.database",
            #   "service_b.db": "shared.database",  # Same target = shared object
            #   "service_c.db": None,               # _instance_: null
            # }
            targets = composer.instance_targets
        """
        if self._instance_resolver is None:
            return {}
        return self._instance_resolver.instance_targets

    @property
    def provenance(self) -> Provenance | None:
        """Get provenance from the last composition.

        Returns the Provenance object from the most recent compose() call,
        or None if compose() hasn't been called yet.

        Example::

            composer = ConfigComposer()
            config = composer.compose(Path("app.yaml"))
            prov = composer.provenance
            if prov:
                print(prov)  # Shows config with file:line annotations
        """
        return self._provenance

    def compose_with_provenance(self, path: Path) -> Provenance:
        """Compose a config file and track the origin of each value.

        :param path: Path to the entry-point config file.
        :return: Provenance object with origin information.
        :raises ConfigFileError: If a file cannot be loaded.
        :raises CircularRefError: If circular references are detected.
        :raises RefAtRootError: If _ref_ is used at root level.
        :raises RefResolutionError: If a _ref_ cannot be resolved.
        :raises InstanceResolutionError: If an _instance_ path cannot be resolved.
        :raises CircularInstanceError: If circular _instance_ references detected.

        Example::

            prov = composer.compose_with_provenance(Path("trainer.yaml"))
            print(prov)  # Shows config with file:line annotations
            entry = prov.get("model.layers")  # Get specific origin info
        """
        self.compose(path)
        assert self._provenance is not None
        return self._provenance


def compose(path: Path) -> dict[str, Any]:
    """Compose a config file by resolving all _ref_ references.

    This is a convenience function that creates a ConfigComposer and
    composes the given file.

    :param path: Path to the entry-point config file.
    :return: Fully composed config dictionary.
    """
    composer = ConfigComposer()
    return composer.compose(path)


def compose_with_provenance(path: Path) -> Provenance:
    """Compose a config file and track the origin of each value.

    This is a convenience function that creates a ConfigComposer and
    composes the given file with provenance tracking.

    :param path: Path to the entry-point config file.
    :return: Provenance object with origin information.
    """
    composer = ConfigComposer()
    return composer.compose_with_provenance(path)
