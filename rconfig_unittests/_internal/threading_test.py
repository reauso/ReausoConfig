"""Thread safety tests for rconfig components.

These tests verify that concurrent access to shared resources is safe.
Each test is designed to complete quickly (< 250ms) while still being comprehensive.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any
from unittest import TestCase

from rconfig._internal.singleton import Singleton
from rconfig.target import TargetRegistry
from rconfig.loaders import register_loader, unregister_loader, get_loader, PositionMap
from rconfig.loaders.base import ConfigFileLoader
from rconfig.composition.IncrementalComposer import set_cache_size, clear_cache
from rconfig.interpolation.parser import InterpolationParser


class SingletonThreadSafetyTests(TestCase):
    """Thread safety tests for the Singleton decorator."""

    def test_concurrent_instantiation__returns_same_instance(self) -> None:
        """Verify singleton returns same instance under concurrent access."""
        call_count = 0

        @Singleton
        class Counter:
            def __init__(self) -> None:
                nonlocal call_count
                call_count += 1

        instances: list[Any] = []
        errors: list[Exception] = []

        def get_instance() -> Any:
            try:
                return Counter()
            except Exception as e:
                errors.append(e)
                return None

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(get_instance) for _ in range(20)]
            instances = [f.result() for f in as_completed(futures)]

        # Filter out None results
        instances = [i for i in instances if i is not None]

        # All should be same instance
        self.assertEqual(len(set(id(i) for i in instances)), 1)
        # Constructor should only be called once
        self.assertEqual(call_count, 1)
        self.assertEqual(len(errors), 0)


class TargetRegistryThreadSafetyTests(TestCase):
    """Thread safety tests for TargetRegistry."""

    def setUp(self) -> None:
        self.store = TargetRegistry()
        self.store.clear()

    def tearDown(self) -> None:
        self.store.clear()

    def test_concurrent_register__all_registered(self) -> None:
        """Verify all registrations succeed under concurrent access."""
        errors: list[Exception] = []
        num_classes = 20

        def register_class(i: int) -> None:
            try:
                # Each thread registers a unique class
                cls = type(f"Class{i}", (), {"__init__": lambda self: None})
                self.store.register(f"class_{i}", cls)
            except Exception as e:
                errors.append(e)

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(register_class, i) for i in range(num_classes)]
            for f in as_completed(futures):
                pass

        self.assertEqual(len(errors), 0)
        self.assertEqual(len(self.store.known_targets), num_classes)

    def test_concurrent_register_unregister__no_errors(self) -> None:
        """Verify mixed register/unregister operations don't cause errors."""
        errors: list[Exception] = []

        # Pre-register some classes
        for i in range(10):
            cls = type(f"PreClass{i}", (), {"__init__": lambda self: None})
            self.store.register(f"pre_class_{i}", cls)

        def register_class(i: int) -> None:
            try:
                cls = type(f"NewClass{i}", (), {"__init__": lambda self: None})
                self.store.register(f"new_class_{i}", cls)
            except Exception as e:
                errors.append(e)

        def unregister_class(i: int) -> None:
            try:
                self.store.unregister(f"pre_class_{i}")
            except KeyError:
                pass  # Already unregistered by another thread
            except Exception as e:
                errors.append(e)

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            # Register new classes
            for i in range(10):
                futures.append(executor.submit(register_class, i))
            # Unregister pre-registered classes
            for i in range(10):
                futures.append(executor.submit(unregister_class, i))

            for f in as_completed(futures):
                pass

        self.assertEqual(len(errors), 0)

    def test_concurrent_read_during_write__no_errors(self) -> None:
        """Verify reads and writes can occur concurrently without errors."""
        errors: list[Exception] = []
        reads: list[int] = []

        # Pre-register some classes
        for i in range(5):
            cls = type(f"Initial{i}", (), {"__init__": lambda self: None})
            self.store.register(f"initial_{i}", cls)

        def reader() -> None:
            try:
                for _ in range(10):
                    refs = self.store.known_targets
                    reads.append(len(refs))
            except Exception as e:
                errors.append(e)

        def writer(i: int) -> None:
            try:
                cls = type(f"Writer{i}", (), {"__init__": lambda self: None})
                self.store.register(f"writer_{i}", cls)
            except Exception as e:
                errors.append(e)

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            # Start readers
            for _ in range(5):
                futures.append(executor.submit(reader))
            # Start writers
            for i in range(10):
                futures.append(executor.submit(writer, i))

            for f in as_completed(futures):
                pass

        self.assertEqual(len(errors), 0)
        # Should have some reads
        self.assertGreater(len(reads), 0)


class LoaderRegistryThreadSafetyTests(TestCase):
    """Thread safety tests for the loader registry."""

    def test_concurrent_register_unregister__no_errors(self) -> None:
        """Verify mixed loader registration doesn't cause errors."""
        errors: list[Exception] = []
        extensions: list[str] = [f".test{i}" for i in range(10)]

        def register_and_unregister(ext: str) -> None:
            try:
                class TestLoader(ConfigFileLoader):
                    def load(self, path: Path) -> dict:
                        return {}

                    def load_with_positions(self, path: Path) -> PositionMap:
                        return PositionMap()

                register_loader(TestLoader(), ext)
                # Small operation in between
                unregister_loader(ext)
            except KeyError:
                pass  # Already unregistered
            except Exception as e:
                errors.append(e)

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(register_and_unregister, ext) for ext in extensions]
            for f in as_completed(futures):
                pass

        self.assertEqual(len(errors), 0)

    def test_get_loader_during_modification__no_errors(self) -> None:
        """Verify get_loader works while loaders are being registered."""
        errors: list[Exception] = []

        def call_get_loader() -> None:
            try:
                for _ in range(5):
                    try:
                        get_loader(Path("test.yaml"))
                    except Exception:
                        pass  # May fail if no loader supports it
            except Exception as e:
                errors.append(e)

        def register_dummy_loader(i: int) -> None:
            try:
                class DummyLoader(ConfigFileLoader):
                    def load(self, path: Path) -> dict:
                        return {}

                    def load_with_positions(self, path: Path) -> PositionMap:
                        return PositionMap()

                ext = f".dummy{i}"
                register_loader(DummyLoader(), ext)
                unregister_loader(ext)
            except KeyError:
                pass  # Already unregistered
            except Exception as e:
                errors.append(e)

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for _ in range(5):
                futures.append(executor.submit(call_get_loader))
            for i in range(5):
                futures.append(executor.submit(register_dummy_loader, i))

            for f in as_completed(futures):
                pass

        self.assertEqual(len(errors), 0)


class CacheThreadSafetyTests(TestCase):
    """Thread safety tests for cache management functions."""

    def test_concurrent_cache_resize__no_errors(self) -> None:
        """Verify cache can be resized under concurrent access."""
        errors: list[Exception] = []

        def resize_cache(size: int) -> None:
            try:
                set_cache_size(size)
            except Exception as e:
                errors.append(e)

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(resize_cache, i % 10) for i in range(20)]
            for f in as_completed(futures):
                pass

        self.assertEqual(len(errors), 0)

    def test_concurrent_clear_cache__no_errors(self) -> None:
        """Verify cache can be cleared under concurrent access."""
        errors: list[Exception] = []

        def clear() -> None:
            try:
                clear_cache()
            except Exception as e:
                errors.append(e)

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(clear) for _ in range(20)]
            for f in as_completed(futures):
                pass

        self.assertEqual(len(errors), 0)


class InterpolationParserThreadSafetyTests(TestCase):
    """Thread safety tests for InterpolationParser."""

    def test_concurrent_parser_access__same_instance(self) -> None:
        """Verify parser singleton is thread-safe."""
        instances: list[InterpolationParser] = []
        errors: list[Exception] = []

        def get_parser() -> InterpolationParser | None:
            try:
                parser = InterpolationParser()
                # Also test parsing to ensure parser is initialized
                parser.parse("1 + 2")
                return parser
            except Exception as e:
                errors.append(e)
                return None

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(get_parser) for _ in range(20)]
            instances = [f.result() for f in as_completed(futures)]

        # Filter out None results
        instances = [i for i in instances if i is not None]

        # All should be same instance
        self.assertEqual(len(set(id(i) for i in instances)), 1)
        self.assertEqual(len(errors), 0)
