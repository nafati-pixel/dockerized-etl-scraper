from __future__ import annotations

import logging
import sys

import structlog

from data_engine.core.config import Settings


def configure_logging(settings: Settings) -> None:
    """
    Call this exactly once, at the very top of cli.py's entrypoint -
    before orchestrator.pipeline or anything that logs is ever imported
    and run. Calling it more than once, or not calling it at all before
    logging happens, leaves structlog on its (much less useful) defaults.
    """
    # Route stdlib logging (used by some third-party libraries, e.g.
    # sqlalchemy's own internal logging) through structlog too, so you
    # get ONE consistent log format instead of two different styles
    # interleaved in your terminal/log aggregator.
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=settings.log_level.upper(),
    )

    shared_processors: list = [
        structlog.contextvars.merge_contextvars,  # pulls in run_id/extractor from context.py
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,      # renders exceptions cleanly, incl. our
                                                     # PipelineError subclasses from core/exceptions.py
    ]

    if settings.log_json:
        # Production / anywhere logs get shipped to an aggregator (e.g.
        # Loki, CloudWatch, Datadog) that expects one JSON object per line.
        renderer = structlog.processors.JSONRenderer()
    else:
        # Local dev: colored, human-readable console output. This is
        # what you actually want staring at your terminal while debugging.
        renderer = structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=shared_processors + [renderer],
        wrapper_class=structlog.make_filtering_bound_logger(
            # getattr(logging, "INFO") etc. - NOT logging.getLevelName("INFO").
            # getLevelName's documented contract is int -> str; using it in
            # reverse (str -> int) only works because of undocumented legacy
            # behavior that the stdlib docs explicitly warn against relying on.
            getattr(logging, settings.log_level.upper(), logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(**initial_context: object) -> structlog.types.FilteringBoundLogger:
    """
    Thin wrapper so call sites do `from data_engine.core.logging import
    get_logger` instead of importing structlog directly everywhere.
    One indirection point - if you ever need to change HOW loggers are
    obtained (e.g. inject a module name automatically), this is the
    only place that changes.

    Usage, at the top of any module:

        logger = get_logger(module=__name__)
        ...
        logger.info("extraction_started", source=self.path)
    """
    return structlog.get_logger(**initial_context)
