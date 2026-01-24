"""Config composer for resolving _ref_ references and composing configs.

This module provides functionality for loading config files that reference
other config files via `_ref_`, merging them together with deep merge semantics.
It also handles `_instance_` references for shared object instances.

The composition now uses an incremental algorithm that only loads files
needed for the requested inner_path (lazy composition optimization).
"""

from pathlib import Path
from typing import Any

from rconfig._internal.path_utils import StrOrPath, ensure_path
from .IncrementalComposer import IncrementalComposer, clear_cache, set_cache_size
from .InstanceResolver import InstanceResolver
from rconfig.provenance import Provenance, ProvenanceBuilder, NullProvenanceBuilder


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

    When an inner_path is specified, the composer uses incremental loading
    to only load the files needed to reach and resolve that path.

    Example::

        composer = ConfigComposer(Path("/project/configs"))

        # Full composition
        config = composer.compose(Path("/project/configs/app.yaml"))

        # Partial composition - only loads needed files
        config = composer.compose(Path("/project/configs/app.yaml"), inner_path="model")
    """

    def __init__(self, config_root: StrOrPath | None = None) -> None:
        """Initialize the composer.

        :param config_root: Root directory for absolute path resolution.
                           If None, derived from the composed file's parent.
                           Accepts str, Path, or any os.PathLike.
        """
        self._config_root = ensure_path(config_root) if config_root is not None else None
        self._provenance: Provenance | None = None
        self._provenance_builder: ProvenanceBuilder | None = None
        self._instance_resolver: InstanceResolver | None = None
        self._ref_graph: dict[str, list[str]] = {}
        self._loaded_files: set[Path] = set()
        self._dependency_closure: set[str] = set()

    def _compose_impl(
        self,
        path: StrOrPath,
        inner_path: str | None,
        provenance_builder: ProvenanceBuilder,
    ) -> dict[str, Any]:
        """Internal composition with the given provenance builder.

        :param path: Path to the entry-point config file.
        :param inner_path: Optional path to target subtree.
        :param provenance_builder: Builder to accumulate provenance entries.
                                  Use NullProvenanceBuilder to skip tracking.
        :return: Fully composed config dictionary.
        """
        path = ensure_path(path)
        self._provenance_builder = provenance_builder

        # Compose the config tree using incremental algorithm
        composer = IncrementalComposer(self._config_root, self._provenance_builder)
        result = composer.compose(path, inner_path=inner_path)

        # Store ref graph and loaded files from composer
        self._ref_graph = composer.ref_graph
        self._loaded_files = result.loaded_files
        self._dependency_closure = result.dependency_closure

        # Resolve all _instance_ references
        self._instance_resolver = InstanceResolver(self._provenance_builder)
        return self._instance_resolver.resolve(result.instances, result.config)

    def compose(
        self,
        path: StrOrPath,
        inner_path: str | None = None,
    ) -> dict[str, Any]:
        """Compose a config file by resolving all _ref_ references.

        Uses the unified incremental algorithm that only loads files needed
        to reach and resolve the specified inner_path. When inner_path is
        None or empty, all files are loaded (full composition).

        Provenance tracking is skipped for performance. Use
        compose_with_provenance() if you need origin information.

        :param path: Path to the entry-point config file. Accepts str, Path, or any os.PathLike.
        :param inner_path: Optional path to target subtree. If provided,
                          only files needed for this path are loaded.
        :return: Fully composed config dictionary.
        :raises ConfigFileError: If a file cannot be loaded.
        :raises CircularRefError: If circular references are detected.
        :raises RefAtRootError: If _ref_ is used at root level.
        :raises RefResolutionError: If a _ref_ cannot be resolved.
        :raises InstanceResolutionError: If an _instance_ path cannot be resolved.
        :raises CircularInstanceError: If circular _instance_ references detected.
        :raises InvalidInnerPathError: If inner_path doesn't exist.
        """
        config = self._compose_impl(path, inner_path, NullProvenanceBuilder())
        self._provenance = None
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

    @property
    def loaded_files(self) -> set[Path]:
        """Get the set of files loaded during the last composition.

        This is useful for understanding what files were actually needed
        for a partial composition with inner_path.

        Example::

            composer = ConfigComposer()
            config = composer.compose(Path("trainer.yaml"), inner_path="model")
            print(f"Loaded {len(composer.loaded_files)} files")
        """
        return self._loaded_files

    @property
    def dependency_closure(self) -> set[str]:
        """Get the dependency closure from the last composition.

        Returns the set of config paths that were identified as dependencies
        of the target inner_path (or all paths for full composition).

        Example::

            composer = ConfigComposer()
            config = composer.compose(Path("trainer.yaml"), inner_path="model")
            print(f"Dependencies: {composer.dependency_closure}")
        """
        return self._dependency_closure

    def ref_graph(self) -> dict[str, list[str]]:
        """Get the graph of _ref_ relationships from the last composition.

        Returns a mapping of source file path -> list of referenced file paths.
        This is populated during composition and can be used by multi-file
        exporters to preserve the original file structure.

        :return: Dictionary mapping file paths to their referenced file paths.

        Example::

            composer = ConfigComposer()
            config = composer.compose(Path("trainer.yaml"))
            graph = composer.ref_graph()
            # {
            #   "/path/to/trainer.yaml": ["/path/to/models/resnet.yaml"],
            #   "/path/to/models/resnet.yaml": ["/path/to/optim/adam.yaml"],
            # }
        """
        return self._ref_graph

    def compose_with_provenance(
        self,
        path: StrOrPath,
        inner_path: str | None = None,
    ) -> Provenance:
        """Compose a config file and track the origin of each value.

        :param path: Path to the entry-point config file. Accepts str, Path, or any os.PathLike.
        :param inner_path: Optional path to target subtree.
        :return: Provenance object with origin information.
        :raises ConfigFileError: If a file cannot be loaded.
        :raises CircularRefError: If circular references are detected.
        :raises RefAtRootError: If _ref_ is used at root level.
        :raises RefResolutionError: If a _ref_ cannot be resolved.
        :raises InstanceResolutionError: If an _instance_ path cannot be resolved.
        :raises CircularInstanceError: If circular _instance_ references detected.
        :raises InvalidInnerPathError: If inner_path doesn't exist.

        Example::

            prov = composer.compose_with_provenance(Path("trainer.yaml"))
            print(prov)  # Shows config with file:line annotations
            entry = prov.get("model.layers")  # Get specific origin info
        """
        builder = ProvenanceBuilder()
        config = self._compose_impl(path, inner_path, builder)
        builder.set_config(config)
        self._provenance = builder.build()
        return self._provenance


def compose(path: StrOrPath, inner_path: str | None = None) -> dict[str, Any]:
    """Compose a config file by resolving all _ref_ references.

    This is a convenience function that creates a ConfigComposer and
    composes the given file.

    :param path: Path to the entry-point config file. Accepts str, Path, or any os.PathLike.
    :param inner_path: Optional path to target subtree for lazy loading.
    :return: Fully composed config dictionary.
    """
    composer = ConfigComposer()
    return composer.compose(path, inner_path=inner_path)


def compose_with_provenance(
    path: StrOrPath, inner_path: str | None = None
) -> Provenance:
    """Compose a config file and track the origin of each value.

    This is a convenience function that creates a ConfigComposer and
    composes the given file with provenance tracking.

    :param path: Path to the entry-point config file. Accepts str, Path, or any os.PathLike.
    :param inner_path: Optional path to target subtree.
    :return: Provenance object with origin information.
    """
    composer = ConfigComposer()
    return composer.compose_with_provenance(path, inner_path=inner_path)
