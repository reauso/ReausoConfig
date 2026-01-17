"""Integration tests for real objects (non-dataclass) that don't store constructor params.

These tests verify that rconfig works correctly with regular Python classes where
constructor parameters are used for initialization but NOT stored as instance attributes.
"""

from pathlib import Path
from unittest.case import TestCase

import rconfig as rc


# =============================================================================
# Real object classes (NOT dataclasses)
# These classes use constructor params but don't store them as attributes
# =============================================================================


class Rectangle:
    """Computes area/perimeter from width/height, doesn't store originals."""

    def __init__(self, width: float, height: float):
        self._area = width * height
        self._perimeter = 2 * (width + height)

    @property
    def area(self) -> float:
        return self._area

    @property
    def perimeter(self) -> float:
        return self._perimeter


class ConnectionPool:
    """Creates slots array based on pool_size, doesn't store pool_size."""

    def __init__(self, pool_size: int, timeout: float):
        self._slots = [None] * pool_size
        self._timeout_ms = int(timeout * 1000)  # Transform to ms

    @property
    def capacity(self) -> int:
        return len(self._slots)

    @property
    def timeout_ms(self) -> int:
        return self._timeout_ms


class Canvas:
    """Contains Rectangle, transforms name to hash."""

    def __init__(self, name: str, shape: Rectangle):
        self._shape = shape
        self._name_hash = hash(name)

    @property
    def shape(self) -> Rectangle:
        return self._shape

    @property
    def name_hash(self) -> int:
        return self._name_hash


class Counter:
    """Stores only current count, not initial_value."""

    def __init__(self, initial_value: int):
        self._count = initial_value

    def get_count(self) -> int:
        return self._count

    def increment(self) -> int:
        self._count += 1
        return self._count


class ServiceA:
    """Service that uses a shared Counter."""

    def __init__(self, counter: Counter, name: str):
        self._counter = counter
        self._id = hash(name)

    @property
    def counter(self) -> Counter:
        return self._counter

    @property
    def service_id(self) -> int:
        return self._id


class ServiceB:
    """Service that uses a shared Counter."""

    def __init__(self, counter: Counter, name: str):
        self._counter = counter
        self._id = hash(name)

    @property
    def counter(self) -> Counter:
        return self._counter

    @property
    def service_id(self) -> int:
        return self._id


class CounterApp:
    """Application with shared counter across services."""

    def __init__(self, shared_counter: Counter, service_a: ServiceA, service_b: ServiceB):
        self._shared_counter = shared_counter
        self._service_a = service_a
        self._service_b = service_b

    @property
    def shared_counter(self) -> Counter:
        return self._shared_counter

    @property
    def service_a(self) -> ServiceA:
        return self._service_a

    @property
    def service_b(self) -> ServiceB:
        return self._service_b


# Path to config files directory
CONFIG_DIR = Path(__file__).parent / "config_files" / "real_objects"


class RealObjectsComputedStateTests(TestCase):
    """Tests for objects that compute/derive state from constructor params."""

    def setUp(self):
        rc._store._known_targets.clear()
        rc.clear_cache()
        rc.register("rectangle", Rectangle)

    def tearDown(self):
        rc.clear_cache()

    def test_instantiate__Rectangle__ComputesAreaCorrectly(self):
        """Rectangle computes area from width * height."""
        config_path = CONFIG_DIR / "rectangle.yaml"

        rect = rc.instantiate(config_path, cli_overrides=False)

        self.assertIsInstance(rect, Rectangle)
        # width=10, height=5 -> area=50
        self.assertEqual(rect.area, 50.0)

    def test_instantiate__Rectangle__ComputesPerimeterCorrectly(self):
        """Rectangle computes perimeter from 2*(width + height)."""
        config_path = CONFIG_DIR / "rectangle.yaml"

        rect = rc.instantiate(config_path, cli_overrides=False)

        # width=10, height=5 -> perimeter=30
        self.assertEqual(rect.perimeter, 30.0)

    def test_instantiate__Rectangle__DoesNotStoreWidth(self):
        """Rectangle does NOT have width attribute."""
        config_path = CONFIG_DIR / "rectangle.yaml"

        rect = rc.instantiate(config_path, cli_overrides=False)

        self.assertFalse(hasattr(rect, "width"))
        self.assertFalse(hasattr(rect, "_width"))

    def test_instantiate__Rectangle__DoesNotStoreHeight(self):
        """Rectangle does NOT have height attribute."""
        config_path = CONFIG_DIR / "rectangle.yaml"

        rect = rc.instantiate(config_path, cli_overrides=False)

        self.assertFalse(hasattr(rect, "height"))
        self.assertFalse(hasattr(rect, "_height"))


class RealObjectsFactoryPatternTests(TestCase):
    """Tests for factory pattern objects that create internal structures."""

    def setUp(self):
        rc._store._known_targets.clear()
        rc.clear_cache()
        rc.register("connection_pool", ConnectionPool)

    def tearDown(self):
        rc.clear_cache()

    def test_instantiate__ConnectionPool__CreatesCorrectCapacity(self):
        """ConnectionPool creates slots array of size pool_size."""
        config_path = CONFIG_DIR / "pool.yaml"

        pool = rc.instantiate(config_path, cli_overrides=False)

        self.assertIsInstance(pool, ConnectionPool)
        # pool_size=5 -> capacity=5
        self.assertEqual(pool.capacity, 5)

    def test_instantiate__ConnectionPool__TransformsTimeout(self):
        """ConnectionPool converts timeout seconds to milliseconds."""
        config_path = CONFIG_DIR / "pool.yaml"

        pool = rc.instantiate(config_path, cli_overrides=False)

        # timeout=30.0 -> timeout_ms=30000
        self.assertEqual(pool.timeout_ms, 30000)

    def test_instantiate__ConnectionPool__DoesNotStorePoolSize(self):
        """ConnectionPool does NOT have pool_size attribute."""
        config_path = CONFIG_DIR / "pool.yaml"

        pool = rc.instantiate(config_path, cli_overrides=False)

        self.assertFalse(hasattr(pool, "pool_size"))
        self.assertFalse(hasattr(pool, "_pool_size"))

    def test_instantiate__ConnectionPool__DoesNotStoreTimeout(self):
        """ConnectionPool does NOT have timeout attribute (only timeout_ms)."""
        config_path = CONFIG_DIR / "pool.yaml"

        pool = rc.instantiate(config_path, cli_overrides=False)

        self.assertFalse(hasattr(pool, "timeout"))
        self.assertFalse(hasattr(pool, "_timeout"))


class RealObjectsNestedTests(TestCase):
    """Tests for nested real objects."""

    def setUp(self):
        rc._store._known_targets.clear()
        rc.clear_cache()
        rc.register("canvas", Canvas)
        rc.register("rectangle", Rectangle)

    def tearDown(self):
        rc.clear_cache()

    def test_instantiate__Canvas__HasNestedRectangle(self):
        """Canvas contains a Rectangle instance."""
        config_path = CONFIG_DIR / "canvas.yaml"

        canvas = rc.instantiate(config_path, cli_overrides=False)

        self.assertIsInstance(canvas, Canvas)
        self.assertIsInstance(canvas.shape, Rectangle)

    def test_instantiate__Canvas__NestedRectangleHasCorrectValues(self):
        """Nested Rectangle computes correct area/perimeter."""
        config_path = CONFIG_DIR / "canvas.yaml"

        canvas = rc.instantiate(config_path, cli_overrides=False)

        # width=8, height=4 -> area=32, perimeter=24
        self.assertEqual(canvas.shape.area, 32.0)
        self.assertEqual(canvas.shape.perimeter, 24.0)

    def test_instantiate__Canvas__TransformsName(self):
        """Canvas transforms name to hash, doesn't store name."""
        config_path = CONFIG_DIR / "canvas.yaml"

        canvas = rc.instantiate(config_path, cli_overrides=False)

        # name_hash should be computed from "my_canvas"
        self.assertEqual(canvas.name_hash, hash("my_canvas"))
        self.assertFalse(hasattr(canvas, "name"))
        self.assertFalse(hasattr(canvas, "_name"))


class RealObjectsInstanceSharingTests(TestCase):
    """Tests for _instance_ sharing with real objects."""

    def setUp(self):
        rc._store._known_targets.clear()
        rc.clear_cache()
        rc.register("counter_app", CounterApp)
        rc.register("counter", Counter)
        rc.register("service_a", ServiceA)
        rc.register("service_b", ServiceB)

    def tearDown(self):
        rc.clear_cache()

    def test_instantiate__CounterApp__AllComponentsInstantiated(self):
        """CounterApp has all components as correct types."""
        config_path = CONFIG_DIR / "shared_counter_app.yaml"

        app = rc.instantiate(config_path, cli_overrides=False)

        self.assertIsInstance(app, CounterApp)
        self.assertIsInstance(app.shared_counter, Counter)
        self.assertIsInstance(app.service_a, ServiceA)
        self.assertIsInstance(app.service_b, ServiceB)

    def test_instantiate__CounterApp__CounterIsShared(self):
        """Both services share the same Counter instance."""
        config_path = CONFIG_DIR / "shared_counter_app.yaml"

        app = rc.instantiate(config_path, cli_overrides=False)

        # All three references should be the exact same object
        self.assertIs(app.shared_counter, app.service_a.counter)
        self.assertIs(app.shared_counter, app.service_b.counter)
        self.assertIs(app.service_a.counter, app.service_b.counter)

    def test_instantiate__CounterApp__SharedCounterHasCorrectValue(self):
        """Shared counter has the configured initial value."""
        config_path = CONFIG_DIR / "shared_counter_app.yaml"

        app = rc.instantiate(config_path, cli_overrides=False)

        # initial_value=100
        self.assertEqual(app.shared_counter.get_count(), 100)
        self.assertEqual(app.service_a.counter.get_count(), 100)
        self.assertEqual(app.service_b.counter.get_count(), 100)

    def test_instantiate__CounterApp__MutationAffectsAllReferences(self):
        """Mutating shared counter affects all references."""
        config_path = CONFIG_DIR / "shared_counter_app.yaml"

        app = rc.instantiate(config_path, cli_overrides=False)

        # Increment via one reference
        app.service_a.counter.increment()

        # All references should see the change
        self.assertEqual(app.shared_counter.get_count(), 101)
        self.assertEqual(app.service_a.counter.get_count(), 101)
        self.assertEqual(app.service_b.counter.get_count(), 101)


class RealObjectsRefCompositionTests(TestCase):
    """Tests for _ref_ composition with real objects."""

    def setUp(self):
        rc._store._known_targets.clear()
        rc.clear_cache()
        rc.register("canvas", Canvas)
        rc.register("rectangle", Rectangle)

    def tearDown(self):
        rc.clear_cache()

    def test_instantiate__CanvasWithRefShape__MergesBaseRectangleValues(self):
        """Canvas with nested _ref_ shape gets base rectangle values merged."""
        config_path = CONFIG_DIR / "canvas_with_ref.yaml"

        canvas = rc.instantiate(config_path, cli_overrides=False)

        # Base rectangle: width=20, height=10
        # Override: height=15
        # Final: width=20, height=15
        # area = 20 * 15 = 300
        self.assertEqual(canvas.shape.area, 300.0)
        # perimeter = 2 * (20 + 15) = 70
        self.assertEqual(canvas.shape.perimeter, 70.0)

    def test_instantiate__CanvasWithRefShape__NestedObjectIsCorrectType(self):
        """Canvas with nested _ref_ shape creates Rectangle instance."""
        config_path = CONFIG_DIR / "canvas_with_ref.yaml"

        canvas = rc.instantiate(config_path, cli_overrides=False)

        self.assertIsInstance(canvas, Canvas)
        self.assertIsInstance(canvas.shape, Rectangle)


class RealObjectsOverrideTests(TestCase):
    """Tests for overrides applied to real objects."""

    def setUp(self):
        rc._store._known_targets.clear()
        rc.clear_cache()
        rc.register("rectangle", Rectangle)

    def tearDown(self):
        rc.clear_cache()

    def test_instantiate__Rectangle__OverrideAffectsComputedState(self):
        """Overriding width/height affects computed area/perimeter."""
        config_path = CONFIG_DIR / "rectangle.yaml"

        rect = rc.instantiate(
            config_path,
            overrides={"width": 20.0, "height": 10.0},
            cli_overrides=False,
        )

        # Overridden: width=20, height=10
        # area = 20 * 10 = 200
        self.assertEqual(rect.area, 200.0)
        # perimeter = 2 * (20 + 10) = 60
        self.assertEqual(rect.perimeter, 60.0)

    def test_instantiate__Rectangle__PartialOverride(self):
        """Overriding only one dimension works."""
        config_path = CONFIG_DIR / "rectangle.yaml"

        rect = rc.instantiate(
            config_path,
            overrides={"width": 100.0},
            cli_overrides=False,
        )

        # width=100 (override), height=5 (from file)
        # area = 100 * 5 = 500
        self.assertEqual(rect.area, 500.0)
