from __future__ import annotations

from typing import AsyncIterator, Protocol, runtime_checkable

from data_engine.domain.dlq_models import DeadLetter
from data_engine.domain.models import RawRecord, TransformedRecord, ValidatedRecord


@runtime_checkable
class Extractor(Protocol):
    """Anything that can pull records from a source."""

    def extract(self) -> AsyncIterator[RawRecord]:
        ...


@runtime_checkable
class Validator(Protocol):
    """Confirms a RawRecord's shape/types, producing a ValidatedRecord.
    Raises ValidationError (core/exceptions.py) on failure - never
    returns None or a sentinel for a bad record."""

    def validate(self, record: RawRecord) -> ValidatedRecord: ...


@runtime_checkable
class Transformer(Protocol):
    """Cleanses/reshapes a ValidatedRecord into a TransformedRecord.
    Raises TransformError on failure."""

    def transform(self, record: ValidatedRecord) -> TransformedRecord: ...


@runtime_checkable
class Loader(Protocol):
    """Writes a BATCH of TransformedRecord objects to a destination.
    Takes a batch, not one record at a time, deliberately - upserting
    row-by-row is orders of magnitude slower than one batched statement,
    and batching is a loader concern, not something every upstream stage
    needs to know about."""

    async def load(self, records: list[TransformedRecord]) -> int:
        """Returns the number of records successfully written."""
        ...


@runtime_checkable
class DLQSink(Protocol):
    """Where failed records go. file_dlq.py implements this now; a
    postgres_dlq.py could later, with zero changes to anything that
    only depends on this Protocol."""

    async def send(self, dead_letter: DeadLetter) -> None: ...


@runtime_checkable
class StateStore(Protocol):
    """Checkpoint/watermark storage - lets a pipeline resume from where
    it left off instead of reprocessing everything after a crash."""

    async def get_checkpoint(self, source_name: str) -> str | None: ...
    async def set_checkpoint(self, source_name: str, value: str) -> None: ...
