"""Hooks module for lifecycle callbacks.

This module provides the public API for registering and invoking hooks
at various stages of the configuration lifecycle.

Example::

    import rconfig as rc
    from rconfig.hooks import HookContext, HookPhase

    @rc.on_config_loaded
    def validate_paths(ctx: HookContext) -> None:
        '''Validate that data paths exist after config is loaded.'''
        if ctx.config and "data" in ctx.config:
            data_path = Path(ctx.config["data"].get("path", ""))
            if not data_path.exists():
                raise ValueError(f"Data path does not exist: {data_path}")

    @rc.on_after_instantiate
    def log_instantiation(ctx: HookContext) -> None:
        '''Log each object instantiation.'''
        print(f"Created {ctx.target_name} at {ctx.inner_path}")

    # Or use class-based callbacks
    class ExperimentTracker(rc.Callback):
        def on_config_loaded(self, ctx: HookContext) -> None:
            start_tracking(ctx.config)

        def on_error(self, ctx: HookContext) -> None:
            log_failure(ctx.error)

    rc.register_callback(ExperimentTracker())
"""

from rconfig.hooks.base import Callback
from rconfig.hooks.models import HookContext, HookEntry, HookPhase
from rconfig.hooks.registry import HookRegistry

__all__ = [
    # Models
    "HookPhase",
    "HookEntry",
    "HookContext",
    # Base class
    "Callback",
    # Registry
    "HookRegistry",
]
