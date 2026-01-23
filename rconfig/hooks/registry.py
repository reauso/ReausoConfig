"""Thread-safe registry for lifecycle hooks.

This module provides the HookRegistry singleton class for registering,
unregistering, and invoking hooks at various configuration lifecycle stages.
"""

from __future__ import annotations

import fnmatch
import threading
from types import MappingProxyType
from typing import Any, Callable, overload

from rconfig._internal import Singleton
from rconfig.hooks.models import HookContext, HookEntry, HookPhase


@Singleton
class HookRegistry:
    """Thread-safe registry for lifecycle hooks.

    Follows the same pattern as ResolverRegistry for API consistency.
    Hooks are organized by phase and sorted by priority when invoked.

    Example::

        registry = HookRegistry()

        # Register a hook
        registry.register(
            HookPhase.CONFIG_LOADED,
            my_hook_func,
            name="validate_paths",
            priority=10,
        )

        # Invoke hooks for a phase (fire-and-forget)
        context = HookContext(phase=HookPhase.CONFIG_LOADED, config_path="config.yaml")
        registry.invoke(HookPhase.CONFIG_LOADED, context)

        # Invoke hooks with config (allows hooks to modify config)
        config = registry.invoke(HookPhase.CONFIG_LOADED, context, config)

        # Get all registered hooks
        for phase, hooks in registry.known_hooks.items():
            for hook in hooks:
                print(f"{phase.name}: {hook.name}")
    """

    def __init__(self) -> None:
        """Initialize an empty hook registry."""
        self._hooks: dict[HookPhase, list[HookEntry]] = {
            phase: [] for phase in HookPhase
        }
        self._lock = threading.RLock()

    @property
    def known_hooks(self) -> MappingProxyType[HookPhase, tuple[HookEntry, ...]]:
        """Read-only view of all registered hooks organized by phase.

        :return: Mapping from HookPhase to tuple of HookEntry objects.
        """
        with self._lock:
            return MappingProxyType(
                {phase: tuple(hooks) for phase, hooks in self._hooks.items()}
            )

    def register(
        self,
        phase: HookPhase,
        func: Callable[[HookContext], None],
        *,
        name: str | None = None,
        pattern: str | None = None,
        priority: int = 50,
    ) -> None:
        """Register a hook for a lifecycle phase.

        :param phase: The lifecycle phase when this hook should be invoked.
        :param func: The hook function. Must accept a HookContext parameter.
        :param name: Unique identifier for the hook. Defaults to function name.
        :param pattern: Optional glob pattern for conditional execution.
                       Hook only runs when config_path matches the pattern.
        :param priority: Execution order (lower values run first, default 50).
        :raises ValueError: If func is not callable.
        """
        if not callable(func):
            raise ValueError(f"Hook must be callable, got {type(func).__name__}")

        hook_name = name if name is not None else func.__name__

        entry = HookEntry(
            name=hook_name,
            phase=phase,
            func=func,
            pattern=pattern,
            priority=priority,
        )

        with self._lock:
            # Remove existing hook with same name in this phase
            self._hooks[phase] = [h for h in self._hooks[phase] if h.name != hook_name]
            self._hooks[phase].append(entry)

    def unregister(self, name: str, phase: HookPhase | None = None) -> None:
        """Unregister a hook by name.

        :param name: The name of the hook to unregister.
        :param phase: If specified, only unregister from this phase.
                     If None, unregister from all phases.
        :raises KeyError: If no hook with that name exists.
        """
        with self._lock:
            found = False
            phases = [phase] if phase is not None else list(HookPhase)

            for p in phases:
                original_count = len(self._hooks[p])
                self._hooks[p] = [h for h in self._hooks[p] if h.name != name]
                if len(self._hooks[p]) < original_count:
                    found = True

            if not found:
                raise KeyError(f"Hook '{name}' is not registered")

    @overload
    def invoke(self, phase: HookPhase, context: HookContext) -> None: ...
    @overload
    def invoke(self, phase: HookPhase, context: HookContext, config: dict[str, Any]) -> dict[str, Any]: ...

    def invoke(
        self,
        phase: HookPhase,
        context: HookContext,
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """Invoke all hooks registered for a phase.

        Hooks are invoked in priority order (lower values first).
        If a hook has a pattern, it only runs when config_path matches.

        When config is provided, hooks can return a dict to replace
        the config. The updated config is passed to subsequent hooks.
        Returns the final (potentially modified) config dict.

        When config is omitted, hook return values are ignored and
        this method returns None.

        :param phase: The lifecycle phase to invoke hooks for.
        :param context: The context to pass to each hook function.
        :param config: Optional config dict for hooks that modify config.
        :return: The (potentially modified) config if provided, else None.
        :raises HookExecutionError: If a hook raises an exception.
        """
        # Import here to avoid circular dependency
        from rconfig.errors import HookExecutionError

        with self._lock:
            hooks = sorted(self._hooks[phase], key=lambda h: h.priority)

        for hook in hooks:
            # Check pattern match if specified
            if hook.pattern is not None:
                if not fnmatch.fnmatch(context.config_path, hook.pattern):
                    continue

            try:
                result = hook.func(context)

                # When config is provided, allow hooks to return modified config
                if config is not None and isinstance(result, dict):
                    config = result
                    # Update context with new config for next hook
                    context = HookContext(
                        phase=context.phase,
                        config_path=context.config_path,
                        config=MappingProxyType(config),
                    )
            except Exception as e:
                raise HookExecutionError(hook.name, phase, e) from e

        return config

    def clear(self) -> None:
        """Clear all registered hooks.

        Thread-safe: protected by internal lock.
        This is primarily intended for testing purposes to reset the registry
        between test cases.
        """
        with self._lock:
            for phase in HookPhase:
                self._hooks[phase] = []

    def __contains__(self, name: str) -> bool:
        """Check if a hook with the given name is registered in any phase.

        :param name: The hook name to check.
        :return: True if a hook with that name exists.
        """
        with self._lock:
            for hooks in self._hooks.values():
                if any(h.name == name for h in hooks):
                    return True
            return False
