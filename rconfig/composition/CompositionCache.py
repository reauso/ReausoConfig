"""Composition cache for incremental config loading.

This module provides caching functionality for config composition,
allowing efficient reuse of loaded and partially composed configs.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class CachedFile:
    """A cached config file with modification tracking.

    :param path: Absolute path to the file.
    :param mtime: Modification time when cached.
    :param content: Parsed content of the file.
    :param position_map: Optional PositionMap with line info.
    """

    path: Path
    mtime: float
    content: dict[str, Any]
    position_map: Any = None  # PositionMap


@dataclass
class CachedComposition:
    """A cached partial composition result.

    :param root_path: Path to the root config file.
    :param inner_path: The inner_path used for this composition.
    :param config: The partially composed config dict.
    :param loaded_files: Set of files that were loaded.
    :param dependency_closure: Set of config paths in the closure.
    :param mtime_map: Map of file paths to their mtimes when cached.
    """

    root_path: Path
    inner_path: str
    config: dict[str, Any]
    loaded_files: set[Path]
    dependency_closure: set[str]
    mtime_map: dict[Path, float] = field(default_factory=dict)


class CompositionCache:
    """LRU cache for config compositions.

    Provides caching at two levels:
    1. File level - individual parsed config files
    2. Composition level - partial composition results with dependency closures

    Thread-safe: All operations are protected by internal locks.

    Example::

        cache = CompositionCache(max_files=100, max_compositions=50)

        # Check for cached composition
        result = cache.get_composition(Path("config.yaml"), "model")
        if result is None:
            # Compose and cache
            result = compose_incrementally(...)
            cache.put_composition(result)
    """

    def __init__(
        self,
        max_files: int = 1000,
        max_compositions: int = 100,
    ) -> None:
        """Initialize the cache.

        :param max_files: Maximum number of files to cache.
        :param max_compositions: Maximum number of compositions to cache.
        """
        self._max_files = max_files
        self._max_compositions = max_compositions

        self._file_cache: dict[Path, CachedFile] = {}
        self._file_order: list[Path] = []  # LRU order

        self._composition_cache: dict[tuple[Path, str], CachedComposition] = {}
        self._composition_order: list[tuple[Path, str]] = []  # LRU order

        self._lock = threading.Lock()

    def get_file(self, path: Path) -> CachedFile | None:
        """Get a cached file if it's still valid.

        :param path: Path to the config file.
        :return: CachedFile if valid and cached, None otherwise.
        """
        with self._lock:
            if path not in self._file_cache:
                return None

            cached = self._file_cache[path]

            # Check if file has been modified
            try:
                current_mtime = path.stat().st_mtime
                if current_mtime != cached.mtime:
                    # File changed - invalidate
                    self._invalidate_file_unlocked(path)
                    return None
            except OSError:
                # File doesn't exist - invalidate
                self._invalidate_file_unlocked(path)
                return None

            # Move to end of LRU order
            if path in self._file_order:
                self._file_order.remove(path)
            self._file_order.append(path)

            return cached

    def put_file(self, cached_file: CachedFile) -> None:
        """Cache a loaded file.

        :param cached_file: The file data to cache.
        """
        with self._lock:
            path = cached_file.path

            # If already cached, update and move to end
            if path in self._file_cache:
                self._file_cache[path] = cached_file
                if path in self._file_order:
                    self._file_order.remove(path)
                self._file_order.append(path)
                return

            # Evict oldest if at capacity
            while len(self._file_cache) >= self._max_files and self._file_order:
                oldest = self._file_order.pop(0)
                self._file_cache.pop(oldest, None)

            self._file_cache[path] = cached_file
            self._file_order.append(path)

    def get_composition(
        self,
        root_path: Path,
        inner_path: str,
    ) -> CachedComposition | None:
        """Get a cached composition if it's still valid.

        :param root_path: Path to the root config file.
        :param inner_path: The inner_path used for composition.
        :return: CachedComposition if valid and cached, None otherwise.
        """
        with self._lock:
            key = (root_path, inner_path)
            if key not in self._composition_cache:
                return None

            cached = self._composition_cache[key]

            # Check if any files have been modified
            for file_path, cached_mtime in cached.mtime_map.items():
                try:
                    current_mtime = file_path.stat().st_mtime
                    if current_mtime != cached_mtime:
                        # File changed - invalidate this composition
                        self._invalidate_composition_unlocked(key)
                        return None
                except OSError:
                    # File doesn't exist - invalidate
                    self._invalidate_composition_unlocked(key)
                    return None

            # Move to end of LRU order
            if key in self._composition_order:
                self._composition_order.remove(key)
            self._composition_order.append(key)

            return cached

    def put_composition(self, composition: CachedComposition) -> None:
        """Cache a composition result.

        :param composition: The composition result to cache.
        """
        with self._lock:
            key = (composition.root_path, composition.inner_path)

            # If already cached, update and move to end
            if key in self._composition_cache:
                self._composition_cache[key] = composition
                if key in self._composition_order:
                    self._composition_order.remove(key)
                self._composition_order.append(key)
                return

            # Evict oldest if at capacity
            while (
                len(self._composition_cache) >= self._max_compositions
                and self._composition_order
            ):
                oldest = self._composition_order.pop(0)
                self._composition_cache.pop(oldest, None)

            self._composition_cache[key] = composition
            self._composition_order.append(key)

    def invalidate_file(self, path: Path) -> None:
        """Invalidate a cached file and any compositions that depend on it.

        :param path: Path to the file to invalidate.
        """
        with self._lock:
            self._invalidate_file_unlocked(path)

    def invalidate_composition(self, root_path: Path, inner_path: str) -> None:
        """Invalidate a specific cached composition.

        :param root_path: Path to the root config file.
        :param inner_path: The inner_path of the composition.
        """
        with self._lock:
            key = (root_path, inner_path)
            self._invalidate_composition_unlocked(key)

    def clear(self) -> None:
        """Clear all caches."""
        with self._lock:
            self._file_cache.clear()
            self._file_order.clear()
            self._composition_cache.clear()
            self._composition_order.clear()

    def _invalidate_file_unlocked(self, path: Path) -> None:
        """Invalidate a file (internal, no lock).

        Also invalidates any compositions that loaded this file.
        """
        # Remove from file cache
        self._file_cache.pop(path, None)
        if path in self._file_order:
            self._file_order.remove(path)

        # Invalidate compositions that depend on this file
        keys_to_remove: list[tuple[Path, str]] = []
        for key, composition in self._composition_cache.items():
            if path in composition.loaded_files or path in composition.mtime_map:
                keys_to_remove.append(key)

        for key in keys_to_remove:
            self._invalidate_composition_unlocked(key)

    def _invalidate_composition_unlocked(self, key: tuple[Path, str]) -> None:
        """Invalidate a composition (internal, no lock)."""
        self._composition_cache.pop(key, None)
        if key in self._composition_order:
            self._composition_order.remove(key)

    @property
    def file_cache_size(self) -> int:
        """Get current file cache size."""
        with self._lock:
            return len(self._file_cache)

    @property
    def composition_cache_size(self) -> int:
        """Get current composition cache size."""
        with self._lock:
            return len(self._composition_cache)


# Global cache instance
_global_cache: CompositionCache | None = None
_global_cache_lock = threading.Lock()


def get_global_cache() -> CompositionCache:
    """Get the global composition cache (creates if needed).

    :return: The global CompositionCache instance.
    """
    global _global_cache
    if _global_cache is None:
        with _global_cache_lock:
            if _global_cache is None:
                _global_cache = CompositionCache()
    return _global_cache


def clear_global_cache() -> None:
    """Clear the global composition cache."""
    global _global_cache
    with _global_cache_lock:
        if _global_cache is not None:
            _global_cache.clear()


def set_global_cache_size(max_files: int = 1000, max_compositions: int = 100) -> None:
    """Configure the global cache sizes.

    Creates a new cache with the specified sizes.

    :param max_files: Maximum number of files to cache.
    :param max_compositions: Maximum number of compositions to cache.
    """
    global _global_cache
    with _global_cache_lock:
        _global_cache = CompositionCache(
            max_files=max_files,
            max_compositions=max_compositions,
        )
