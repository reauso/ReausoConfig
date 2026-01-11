"""MultirunIterator class for lazy iteration over multirun results.

This module defines the iterator type returned by instantiate_multirun(),
providing lazy instantiation with length, slicing, and reversal support.
"""

from __future__ import annotations

from typing import Any, Callable, Generic, TypeVar, overload

from .result import MultirunResult

T = TypeVar("T")


class MultirunIterator(Generic[T]):
    """Lazy iterator with length and slicing support for progress tracking.

    Enables efficient iteration over multirun configurations with support for:
    - `len()` for progress tracking (e.g., with tqdm)
    - Slicing for subset iteration (e.g., `iterator[50:]` to resume)
    - Reversal for reverse order iteration
    - Single index access for debugging specific runs

    Example::

        results = rc.instantiate_multirun(...)

        # Progress tracking with tqdm (auto-detects __len__)
        for result in tqdm(results):
            train(result.instance)

        # Resume from crash
        for result in results[50:]:
            train(result.instance)

        # Distribute across workers
        worker1_results = results[0:25]
        worker2_results = results[25:50]

        # Run in reverse order
        for result in reversed(results):
            train(result.instance)

        # Debug specific run
        single_result = results[3]
    """

    def __init__(
        self,
        run_configs: list[dict[str, Any]],
        instantiate_fn: Callable[[dict[str, Any]], MultirunResult[T]],
    ) -> None:
        """Initialize the multirun iterator.

        :param run_configs: List of override dicts for each run.
        :param instantiate_fn: Function that instantiates a single run config.
        """
        self._run_configs = run_configs
        self._instantiate_fn = instantiate_fn
        self._index = 0

    def __len__(self) -> int:
        """Return the total number of runs.

        :return: Number of run configurations.
        """
        return len(self._run_configs)

    def __iter__(self) -> "MultirunIterator[T]":
        """Return a fresh iterator.

        :return: New iterator starting from the beginning.
        """
        return MultirunIterator(self._run_configs, self._instantiate_fn)

    def __next__(self) -> MultirunResult[T]:
        """Yield the next result.

        :return: MultirunResult for the next run.
        :raises StopIteration: When all runs have been iterated.
        """
        if self._index >= len(self._run_configs):
            raise StopIteration
        result = self._instantiate_fn(self._run_configs[self._index])
        self._index += 1
        return result

    def __reversed__(self) -> "MultirunIterator[T]":
        """Return an iterator in reverse order.

        :return: New iterator with reversed run order.
        """
        return MultirunIterator(
            list(reversed(self._run_configs)),
            self._instantiate_fn,
        )

    @overload
    def __getitem__(self, key: int) -> MultirunResult[T]: ...

    @overload
    def __getitem__(self, key: slice) -> MultirunIterator[T]: ...

    def __getitem__(self, key: int | slice) -> MultirunResult[T] | MultirunIterator[T]:
        """Access runs by index or slice.

        :param key: Integer index or slice.
        :return: MultirunResult for single index, MultirunIterator for slice.
        :raises TypeError: If key is not an int or slice.
        :raises IndexError: If integer index is out of range.
        """
        if isinstance(key, int):
            if key < 0:
                key = len(self) + key
            if key < 0 or key >= len(self):
                raise IndexError(f"Index {key} out of range for {len(self)} runs")
            return self._instantiate_fn(self._run_configs[key])
        elif isinstance(key, slice):
            return MultirunIterator(self._run_configs[key], self._instantiate_fn)
        else:
            raise TypeError(
                f"Indices must be integers or slices, not {type(key).__name__}"
            )
