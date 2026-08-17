from __future__ import annotations

from typing import Callable, TypeVar

from data_engine.core.exceptions import PipelineError
from data_engine.core.ports import Extractor

T = TypeVar("T", bound=Extractor)

_EXTRACTORS: dict[str, type[Extractor]] = {}


class UnknownExtractorError(PipelineError):
    """Config asked for an extractor name that was never registered -
    almost always a typo in config, or a missing import in
    extractors/__init__.py."""


def register_extractor(name: str) -> Callable[[type[T]], type[T]]:
    """
    Raises at IMPORT time (not silently) if `name` is already taken -
    catching a copy-pasted decorator with the wrong name in five seconds
    beats debugging "why is the wrong extractor running" later.
    """
    def wrapper(cls: type[T]) -> type[T]:
        if name in _EXTRACTORS:
            raise ValueError(
                f"Extractor name '{name}' is already registered to "
                f"{_EXTRACTORS[name].__name__} - choose a unique name."
            )
        _EXTRACTORS[name] = cls
        return cls
    return wrapper


def get_extractor(name: str) -> type[Extractor]:
    """Looked up by cli.py using a name from config/CLI args."""
    try:
        return _EXTRACTORS[name]
    except KeyError:
        available = ", ".join(sorted(_EXTRACTORS)) or "(none registered)"
        raise UnknownExtractorError(
            f"No extractor registered as '{name}'. Available: {available}. "
            f"Did you forget to import the extractor module in "
            f"extractors/__init__.py?"
        ) from None


def registered_extractors() -> list[str]:
    """Used by cli.py to list available sources, e.g. in --help."""
    return sorted(_EXTRACTORS)
