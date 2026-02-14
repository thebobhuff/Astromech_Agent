"""Structured error classification and recovery strategies for the agent orchestrator.

Provides a taxonomy of errors commonly encountered during LLM orchestration,
automatic classification of exceptions, and an async retry wrapper that applies
recovery strategies (context compaction, model rotation, backoff, etc.).
"""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ErrorClass(str, Enum):
    """Taxonomy of errors the orchestrator may encounter."""

    CONTEXT_OVERFLOW = "context_overflow"
    RATE_LIMIT = "rate_limit"
    AUTH_ERROR = "auth_error"
    TIMEOUT = "timeout"
    ROLE_ORDERING = "role_ordering"
    IMAGE_ERROR = "image_error"
    MODEL_UNAVAILABLE = "model_unavailable"
    TOOL_ERROR = "tool_error"
    PARSE_ERROR = "parse_error"
    UNKNOWN = "unknown"


class RecoveryStrategy(str, Enum):
    """Actions the orchestrator can take to recover from an error."""

    RETRY = "retry"
    COMPACT_CONTEXT = "compact_context"
    ROTATE_MODEL = "rotate_model"
    REDUCE_CONTEXT = "reduce_context"
    ABORT = "abort"
    SKIP_TOOL = "skip_tool"
    NONE = "none"


# ---------------------------------------------------------------------------
# Classified error dataclass
# ---------------------------------------------------------------------------

@dataclass
class ClassifiedError:
    """An exception enriched with classification metadata."""

    original_exception: Exception
    error_class: ErrorClass
    message: str
    is_retryable: bool
    recovery_strategy: RecoveryStrategy
    status_code: int | None = field(default=None, repr=False)
    extra: dict[str, Any] = field(default_factory=dict, repr=False)

    def __str__(self) -> str:
        return (
            f"[{self.error_class.value}] {self.message} "
            f"(retryable={self.is_retryable}, recovery={self.recovery_strategy.value})"
        )


# ---------------------------------------------------------------------------
# Classification helpers
# ---------------------------------------------------------------------------

# Pre-compiled patterns for efficiency.
_CONTEXT_OVERFLOW_RE = re.compile(
    r"context|token|too long|max\s*[\._-]?\s*length", re.IGNORECASE
)
_RATE_LIMIT_RE = re.compile(
    r"rate|429|quota|too many requests", re.IGNORECASE
)
_AUTH_RE = re.compile(
    r"auth|401|403|api[_\s]?key|permission", re.IGNORECASE
)
_TIMEOUT_RE = re.compile(
    r"timeout|timed?\s*out|deadline", re.IGNORECASE
)
_ROLE_ORDERING_RE = re.compile(
    r"role|turn|ordering|must alternate", re.IGNORECASE
)
_IMAGE_RE = re.compile(
    r"image|vision|media|dimension|size", re.IGNORECASE
)
_MODEL_UNAVAILABLE_RE = re.compile(
    r"model.{0,30}(?:not found|unavailable|deprecated)", re.IGNORECASE
)
_TOOL_ERROR_RE = re.compile(
    r"tool.{0,20}error|error.{0,20}tool", re.IGNORECASE
)
_PARSE_RE = re.compile(
    r"json|parse|decode", re.IGNORECASE
)


def _extract_status_code(exc: Exception) -> int | None:
    """Best-effort extraction of an HTTP status code from an exception."""
    for attr in ("status_code", "status", "code", "http_status"):
        val = getattr(exc, attr, None)
        if isinstance(val, int):
            return val
    return None


def _build_message(exc: Exception, context: str) -> str:
    """Combine exception text and optional context into a single searchable string."""
    parts: list[str] = []
    if context:
        parts.append(context)
    parts.append(str(exc))
    # Include nested exception text when available.
    if exc.__cause__:
        parts.append(str(exc.__cause__))
    return " | ".join(parts)


def classify_error(exception: Exception, context: str = "") -> ClassifiedError:
    """Inspect *exception* and return a :class:`ClassifiedError`.

    Classification is performed by matching the stringified exception (and
    optional *context* hint) against known patterns.  The first matching rule
    wins; order reflects priority.

    Args:
        exception: The caught exception.
        context: Optional free-text hint (e.g. the tool name or API call).

    Returns:
        A ``ClassifiedError`` with the determined class, retryability, and
        recommended first recovery strategy.
    """
    msg = _build_message(exception, context)
    status = _extract_status_code(exception)

    # --- ordered classification rules ---

    if _CONTEXT_OVERFLOW_RE.search(msg):
        return ClassifiedError(
            original_exception=exception,
            error_class=ErrorClass.CONTEXT_OVERFLOW,
            message=msg,
            is_retryable=True,
            recovery_strategy=RecoveryStrategy.COMPACT_CONTEXT,
            status_code=status,
        )

    if _RATE_LIMIT_RE.search(msg) or status == 429:
        return ClassifiedError(
            original_exception=exception,
            error_class=ErrorClass.RATE_LIMIT,
            message=msg,
            is_retryable=True,
            recovery_strategy=RecoveryStrategy.ROTATE_MODEL,
            status_code=status,
        )

    if _AUTH_RE.search(msg) or status in (401, 403):
        return ClassifiedError(
            original_exception=exception,
            error_class=ErrorClass.AUTH_ERROR,
            message=msg,
            is_retryable=False,
            recovery_strategy=RecoveryStrategy.ROTATE_MODEL,
            status_code=status,
        )

    if isinstance(exception, (TimeoutError, asyncio.TimeoutError)) or _TIMEOUT_RE.search(msg):
        return ClassifiedError(
            original_exception=exception,
            error_class=ErrorClass.TIMEOUT,
            message=msg,
            is_retryable=True,
            recovery_strategy=RecoveryStrategy.RETRY,
            status_code=status,
        )

    if _ROLE_ORDERING_RE.search(msg):
        return ClassifiedError(
            original_exception=exception,
            error_class=ErrorClass.ROLE_ORDERING,
            message=msg,
            is_retryable=True,
            recovery_strategy=RecoveryStrategy.REDUCE_CONTEXT,
            status_code=status,
        )

    if _IMAGE_RE.search(msg):
        return ClassifiedError(
            original_exception=exception,
            error_class=ErrorClass.IMAGE_ERROR,
            message=msg,
            is_retryable=False,
            recovery_strategy=RecoveryStrategy.SKIP_TOOL,
            status_code=status,
        )

    if _MODEL_UNAVAILABLE_RE.search(msg):
        return ClassifiedError(
            original_exception=exception,
            error_class=ErrorClass.MODEL_UNAVAILABLE,
            message=msg,
            is_retryable=True,
            recovery_strategy=RecoveryStrategy.ROTATE_MODEL,
            status_code=status,
        )

    if _TOOL_ERROR_RE.search(msg):
        return ClassifiedError(
            original_exception=exception,
            error_class=ErrorClass.TOOL_ERROR,
            message=msg,
            is_retryable=False,
            recovery_strategy=RecoveryStrategy.SKIP_TOOL,
            status_code=status,
        )

    if _PARSE_RE.search(msg):
        return ClassifiedError(
            original_exception=exception,
            error_class=ErrorClass.PARSE_ERROR,
            message=msg,
            is_retryable=True,
            recovery_strategy=RecoveryStrategy.RETRY,
            status_code=status,
        )

    # Fallback
    return ClassifiedError(
        original_exception=exception,
        error_class=ErrorClass.UNKNOWN,
        message=msg,
        is_retryable=True,
        recovery_strategy=RecoveryStrategy.RETRY,
        status_code=status,
    )


# ---------------------------------------------------------------------------
# Recovery planning
# ---------------------------------------------------------------------------

# Maximum attempts before escalation, keyed by ErrorClass.
_MAX_RETRIES: dict[ErrorClass, int] = {
    ErrorClass.CONTEXT_OVERFLOW: 2,
    ErrorClass.RATE_LIMIT: 3,
    ErrorClass.AUTH_ERROR: 1,
    ErrorClass.TIMEOUT: 3,
    ErrorClass.ROLE_ORDERING: 2,
    ErrorClass.IMAGE_ERROR: 1,
    ErrorClass.MODEL_UNAVAILABLE: 2,
    ErrorClass.TOOL_ERROR: 1,
    ErrorClass.PARSE_ERROR: 2,
    ErrorClass.UNKNOWN: 2,
}


def get_recovery_plan(error: ClassifiedError, attempt: int) -> RecoveryStrategy:
    """Recommend a recovery strategy given the classified *error* and current *attempt*.

    As attempts increase the strategy may escalate (e.g. from ``RETRY`` to
    ``ABORT``).  The *attempt* counter is **1-based** (first retry = 1).

    Args:
        error: The classified error.
        attempt: Current retry attempt (1-based).

    Returns:
        The recommended :class:`RecoveryStrategy`.
    """
    max_retries = _MAX_RETRIES.get(error.error_class, 2)

    if attempt > max_retries:
        return RecoveryStrategy.ABORT

    match error.error_class:
        case ErrorClass.CONTEXT_OVERFLOW:
            return RecoveryStrategy.COMPACT_CONTEXT

        case ErrorClass.RATE_LIMIT:
            # First attempt: rotate model. Subsequent: still rotate (caller
            # should apply exponential backoff via the wrapper).
            return RecoveryStrategy.ROTATE_MODEL

        case ErrorClass.AUTH_ERROR:
            return RecoveryStrategy.ROTATE_MODEL if attempt <= 1 else RecoveryStrategy.ABORT

        case ErrorClass.TIMEOUT:
            # Timeouts on provider calls are often model/provider-specific.
            # Rotate early instead of repeating the same failing call.
            return RecoveryStrategy.ROTATE_MODEL

        case ErrorClass.ROLE_ORDERING:
            return RecoveryStrategy.REDUCE_CONTEXT

        case ErrorClass.IMAGE_ERROR:
            return RecoveryStrategy.SKIP_TOOL

        case ErrorClass.MODEL_UNAVAILABLE:
            return RecoveryStrategy.ROTATE_MODEL

        case ErrorClass.TOOL_ERROR:
            return RecoveryStrategy.SKIP_TOOL if attempt <= 1 else RecoveryStrategy.ABORT

        case ErrorClass.PARSE_ERROR:
            return RecoveryStrategy.RETRY

        case ErrorClass.UNKNOWN:
            return RecoveryStrategy.RETRY if attempt <= 2 else RecoveryStrategy.ABORT

        case _:
            return RecoveryStrategy.ABORT


# ---------------------------------------------------------------------------
# Async retry wrapper
# ---------------------------------------------------------------------------

def _backoff_delay(attempt: int, base: float = 1.0, cap: float = 30.0) -> float:
    """Exponential backoff with jitter capped at *cap* seconds."""
    import random
    delay = min(base * (2 ** (attempt - 1)), cap)
    return delay * (0.5 + random.random() * 0.5)  # noqa: S311


async def execute_with_recovery(
    coro_factory: Callable[[], Awaitable[Any]],
    *,
    max_attempts: int = 3,
    on_retry: Optional[Callable[[ClassifiedError, int, RecoveryStrategy], None]] = None,
) -> Any:
    """Execute an async callable with automatic error classification and recovery.

    *coro_factory* must be a **zero-argument async callable** that produces a
    fresh coroutine on each invocation (e.g. ``lambda: some_async_func(args)``).

    On failure the exception is classified, a recovery strategy is chosen, and
    — if retryable — the call is retried up to *max_attempts* times with
    exponential backoff.

    Args:
        coro_factory: Async callable returning a new awaitable each call.
        max_attempts: Total number of attempts (including the initial one).
        on_retry: Optional callback invoked before each retry with the
            classified error, attempt number (1-based), and chosen strategy.

    Returns:
        The result of the successful invocation.

    Raises:
        The original exception (wrapped in ``ClassifiedError`` info via
        ``__cause__``) if all attempts are exhausted or the error is
        non-retryable.
    """
    last_error: ClassifiedError | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            return await coro_factory()
        except Exception as exc:
            classified = classify_error(exc)
            strategy = get_recovery_plan(classified, attempt)

            logger.warning(
                "Attempt %d/%d failed: %s → strategy=%s",
                attempt,
                max_attempts,
                classified,
                strategy.value,
            )

            last_error = classified

            if strategy is RecoveryStrategy.ABORT or attempt >= max_attempts:
                logger.error(
                    "Aborting after %d attempt(s): %s",
                    attempt,
                    classified,
                )
                raise

            if not classified.is_retryable:
                logger.error(
                    "Non-retryable error on attempt %d: %s",
                    attempt,
                    classified,
                )
                raise

            if on_retry is not None:
                on_retry(classified, attempt, strategy)

            # Apply backoff for rate-limit errors; brief pause for others.
            if classified.error_class is ErrorClass.RATE_LIMIT:
                delay = _backoff_delay(attempt, base=2.0)
            else:
                delay = _backoff_delay(attempt, base=0.5)

            logger.info("Waiting %.2fs before retry…", delay)
            await asyncio.sleep(delay)

    # Should be unreachable, but satisfy the type checker.
    assert last_error is not None  # noqa: S101
    raise last_error.original_exception
