"""Lazy instantiation proxy for deferred object creation.

This module provides a mechanism to create lazy proxy subclasses that delay
__init__ execution until first attribute access while maintaining
isinstance() compatibility.

The lazy proxy approach:
1. Creates a dynamic subclass of the target class
2. Overrides __init__ to store kwargs without calling super().__init__()
3. Intercepts attribute access to trigger real initialization
4. After init, the proxy behaves identically to the real object

Transparency guarantees:
- isinstance(lazy_obj, TargetClass) returns True
- All attribute access, method calls, and special methods work correctly
- User code does NOT need to import anything from rconfig

Known limitations:
- type(obj) returns the proxy class, not the original class
- obj.__class__ returns the proxy class, not the original class
Use isinstance() instead of type() for type checking.
"""

from typing import Any, Callable


# Attribute name used to store lazy state (prefixed to minimize collision risk)
_LAZY_STATE_ATTR = "__rconfig_lazy_state__"


class _LazyState:
    """Internal state container for lazy proxies.

    Stored on the proxy instance to track initialization state
    and constructor arguments.
    """

    __slots__ = ("initialized", "init_func", "kwargs")

    def __init__(self, init_func: Callable[[], None], kwargs: dict[str, Any]) -> None:
        """Initialize lazy state.

        :param init_func: Callable that runs the real __init__.
        :param kwargs: Original kwargs for inspection before init.
        """
        self.initialized = False
        self.init_func = init_func
        self.kwargs = kwargs


def create_lazy_proxy_class(target_class: type) -> type:
    """Create a lazy proxy subclass for the given target class.

    The returned class:
    - Is a subclass of target_class (passes isinstance checks)
    - Delays __init__ execution until first attribute access
    - Becomes indistinguishable from target_class after initialization

    :param target_class: The class to create a lazy proxy for.
    :return: A new class that lazily initializes target_class.
    """

    class LazyProxy(target_class):  # type: ignore[valid-type, misc]
        """Dynamic lazy proxy subclass.

        Intercepts all attribute access until the first real access
        triggers actual initialization via the parent class's __init__.
        """

        def __new__(cls, **kwargs: Any) -> "LazyProxy":
            """Create instance without calling __init__."""
            # Use object.__new__ to bypass target_class.__new__ if it has side effects
            # For most classes this is fine; for classes with custom __new__ that
            # require arguments, this may need adjustment
            try:
                instance = object.__new__(cls)
            except TypeError:
                # Some classes require arguments to __new__, fall back to target
                instance = target_class.__new__(cls)
            return instance

        def __init__(self, **kwargs: Any) -> None:
            """Store init arguments without calling parent __init__."""

            # Create the lazy state - DO NOT call super().__init__ yet
            def do_init() -> None:
                target_class.__init__(self, **kwargs)

            # Store state using object.__setattr__ to avoid triggering our __setattr__
            object.__setattr__(self, _LAZY_STATE_ATTR, _LazyState(do_init, kwargs))

        def _ensure_initialized(self) -> None:
            """Initialize the object if not already done."""
            try:
                state = object.__getattribute__(self, _LAZY_STATE_ATTR)
            except AttributeError:
                # Already initialized and state cleaned up, or not a lazy proxy
                return

            if not state.initialized:
                state.initialized = True
                state.init_func()

        def __getattribute__(self, name: str) -> Any:
            """Intercept attribute access to trigger lazy init."""
            # Allow access to our internal state without triggering init
            if name == _LAZY_STATE_ATTR or name == "_ensure_initialized":
                return object.__getattribute__(self, name)

            # Check if we need to initialize
            try:
                state = object.__getattribute__(self, _LAZY_STATE_ATTR)
                if not state.initialized:
                    state.initialized = True
                    state.init_func()
            except AttributeError:
                pass  # Already initialized or not a lazy proxy

            # Now delegate to normal attribute access
            return object.__getattribute__(self, name)

        def __setattr__(self, name: str, value: Any) -> None:
            """Intercept attribute setting to trigger lazy init."""
            if name == _LAZY_STATE_ATTR:
                object.__setattr__(self, name, value)
                return

            # Trigger initialization before allowing attribute set
            self._ensure_initialized()
            object.__setattr__(self, name, value)

        def __delattr__(self, name: str) -> None:
            """Intercept attribute deletion to trigger lazy init."""
            self._ensure_initialized()
            object.__delattr__(self, name)

        def __repr__(self) -> str:
            """Show lazy status in repr before init, normal repr after."""
            try:
                state = object.__getattribute__(self, _LAZY_STATE_ATTR)
                if not state.initialized:
                    return f"<LazyProxy[{target_class.__name__}] (not initialized)>"
            except AttributeError:
                pass
            # Trigger init and use normal repr
            self._ensure_initialized()
            # Call the target class's __repr__ if it has one
            if hasattr(target_class, "__repr__"):
                return target_class.__repr__(self)
            return object.__repr__(self)

    # Set a more informative name that includes the original class name
    LazyProxy.__name__ = f"Lazy{target_class.__name__}"
    LazyProxy.__qualname__ = f"Lazy{target_class.__qualname__}"

    return LazyProxy


# Cache of created proxy classes to avoid creating duplicates
_proxy_class_cache: dict[type, type] = {}


def get_lazy_proxy_class(target_class: type) -> type:
    """Get or create a cached lazy proxy class for the target.

    Uses a cache to avoid creating duplicate proxy classes for the same
    target class, which improves performance and ensures consistent behavior.

    :param target_class: The class to get a proxy for.
    :return: The cached or newly created proxy class.
    """
    if target_class not in _proxy_class_cache:
        _proxy_class_cache[target_class] = create_lazy_proxy_class(target_class)
    return _proxy_class_cache[target_class]


def is_lazy_proxy(obj: Any) -> bool:
    """Check if an object is an uninitialized lazy proxy.

    Returns True only if the object is a lazy proxy that has NOT yet been
    initialized. Returns False for:
    - Regular (non-lazy) objects
    - Lazy proxies that have already been initialized

    :param obj: Object to check.
    :return: True if obj is an uninitialized lazy proxy.
    """
    try:
        state = object.__getattribute__(obj, _LAZY_STATE_ATTR)
        return not state.initialized
    except AttributeError:
        return False


def force_initialize(obj: Any) -> None:
    """Force initialization of a lazy proxy without accessing attributes.

    This is useful when you want to trigger initialization explicitly
    rather than waiting for attribute access. No-op if the object is
    not a lazy proxy or is already initialized.

    :param obj: Object to initialize.
    """
    try:
        state = object.__getattribute__(obj, _LAZY_STATE_ATTR)
        if not state.initialized:
            state.initialized = True
            state.init_func()
    except AttributeError:
        pass  # Not a lazy proxy or already initialized


def clear_proxy_cache() -> None:
    """Clear the proxy class cache.

    Mainly useful for testing to ensure a clean state between tests.
    """
    _proxy_class_cache.clear()
