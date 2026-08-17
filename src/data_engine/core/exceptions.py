"""
Typed exception hierarchy for the entire pipeline.

WHY THIS EXISTS: dlq/classifier.py has to decide, for every failure,
"is this worth retrying automatically, or does a human need to look at
it?" Doing that by parsing exception MESSAGES is brittle - a library
updating its wording ("Connection timed out" -> "connection timeout")
silently breaks your classification in production with zero warning,
and you won't notice until your DLQ fills up with things that should
have auto-retried.

Encoding the answer in the exception's TYPE instead means classification
becomes a single isinstance() check (see dlq/classifier.py), and - more
importantly - the decision gets made at the point the error is RAISED,
by whoever wrote that code and knows the failure mode best, not guessed
later by someone reading a caught exception out of context.

THE RULE FOR EVERY MODULE YOU WRITE: never raise a bare Exception or an
unwrapped library exception (e.g. `except psycopg.OperationalError` ->
just re-raising it). Catch it and raise the appropriate PipelineError
subclass instead, so it's correctly DLQ-routed automatically:

    try:
        response = await http_client.get(url)
    except httpx.TimeoutException as exc:
        raise ExtractionError(f"timed out fetching {url}") from exc

The `from exc` matters - it preserves the original traceback for
debugging while still giving classifier.py a clean type to check.
"""


class PipelineError(Exception):
    """
    Base class for every error this pipeline raises ON PURPOSE.

    Stage boundaries (see orchestrator/pipeline.py's run_stage helper)
    catch PipelineError specifically - NOT the bare Exception. That's
    deliberate: a genuine bug (a KeyError from a typo, an AttributeError
    from broken code) will NOT be a PipelineError, so it propagates and
    crashes loudly instead of being silently swallowed into the DLQ and
    hidden from you. The DLQ is for bad DATA, not for bugs in your code.
    """


class TransientError(PipelineError):
    """
    Retrying will probably help: a timeout, a connection reset, a 429/503
    from an API, a temporarily locked file, a deadlock on write.
    dlq/replay.py treats every TransientError subclass as an automatic
    retry candidate.
    """


class PermanentError(PipelineError):
    """
    Retrying changes NOTHING: malformed data, a schema violation, a
    business-rule failure. dlq/replay.py will never auto-retry these -
    they sit in the DLQ until a human fixes the data or the code.
    """



class ExtractionError(TransientError):
    """
    Pulling from the source failed in a way likely to succeed on a later
    attempt: network blip, rate limit, source temporarily unavailable.
    """


class DecodingError(PermanentError):
    """
    The source itself is malformed in a way no retry will fix - an
    unreadable encoding across every fallback we tried, a corrupt file.
    Deliberately PERMANENT (not ExtractionError): the fix here is manual
    (re-export the file correctly), not "wait and try again".
    """



class ValidationError(PermanentError):
    """
    A record's shape or types don't match the expected schema. Always
    permanent - the record is simply wrong, and it'll still be wrong on
    the 10th retry.
    """



class TransformError(PermanentError):
    """
    A record passed validation (structurally sound) but still can't be
    transformed - e.g. it violates a business rule that the schema layer 
    can't express, like a total that doesn't match its line items.
    """



class LoadError(TransientError):
    """
    A write to the destination failed. Almost always transient in
    practice - dropped connection, deadlock with a concurrent writer,
    momentary constraint violation - so it defaults to retry-eligible.
    """



class CircuitOpenError(TransientError):
    """
    Raised by resilience/circuit_breaker.py when the breaker is OPEN and
    refuses to even attempt the call, to avoid hammering a downstream
    system that's already known to be failing. Transient by definition -
    the breaker itself will allow attempts again once its cooldown
    (reset_timeout) elapses.
    """
