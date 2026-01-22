"""Base class for class-based callbacks.

This module provides the Callback base class that allows users to define
callbacks with methods for each lifecycle phase.
"""

from __future__ import annotations

from rconfig.hooks.models import HookContext


class Callback:
    """Base class for class-based callbacks with full lifecycle access.

    Subclass and override methods for the phases you need. Methods that are
    not overridden do nothing by default.

    Example::

        class ExperimentTracker(rc.Callback):
            def __init__(self, tracking_uri: str):
                self.tracking_uri = tracking_uri
                self.run_id = None

            def on_config_loaded(self, ctx: HookContext) -> None:
                self.run_id = start_experiment_run(self.tracking_uri)
                log_config(self.run_id, ctx.config)

            def on_after_instantiate(self, ctx: HookContext) -> None:
                log_instantiation(self.run_id, ctx.target_name, ctx.instance)

            def on_error(self, ctx: HookContext) -> None:
                mark_run_failed(self.run_id, str(ctx.error))

        # Register the callback
        tracker = ExperimentTracker("http://mlflow.internal")
        rc.register_callback(tracker)

        # Later, unregister if needed
        rc.unregister_callback(tracker)
    """

    def on_config_loaded(self, ctx: HookContext) -> None:
        """Called after config is loaded and composed.

        Override this method to add custom logic after config composition
        but before interpolation resolution.

        :param ctx: Hook context with config_path and config.
        """
        pass

    def on_before_instantiate(self, ctx: HookContext) -> None:
        """Called before each object instantiation.

        Override this method to add custom logic before constructor calls.
        This is called for each nested config with a _target_.

        :param ctx: Hook context with config_path, config, inner_path, target_name.
        """
        pass

    def on_after_instantiate(self, ctx: HookContext) -> None:
        """Called after each object instantiation.

        Override this method to add custom logic after constructor returns.
        This is called for each nested config with a _target_.

        :param ctx: Hook context with config_path, config, inner_path,
                   target_name, and instance.
        """
        pass

    def on_error(self, ctx: HookContext) -> None:
        """Called when an error occurs during instantiation.

        Override this method to add custom error handling, logging, or cleanup.

        :param ctx: Hook context with config_path, config, and error.
                   May also include inner_path and target_name if the error
                   occurred during nested instantiation.
        """
        pass
