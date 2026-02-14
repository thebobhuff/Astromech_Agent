import asyncio
import logging
import os
from typing import List

MAX_SUBSCRIBER_QUEUE_SIZE = 30
MAX_BROADCAST_MESSAGE_CHARS = 4000


class LogBroadcastHandler(logging.Handler):
    """
    A logging handler that broadcasts log records to a list of asyncio Queues.
    Used for streaming logs to WebSockets.
    """

    def __init__(self):
        super().__init__()
        self.queues: List[asyncio.Queue] = []

    def emit(self, record):
        try:
            msg = self.format(record)
            if len(msg) > MAX_BROADCAST_MESSAGE_CHARS:
                msg = f"{msg[:MAX_BROADCAST_MESSAGE_CHARS]} ... [truncated]"
            # Iterate over a copy of the list to allow safe removal during iteration if needed
            # (though removal happens in unsubscribe, called from other coroutines)
            for q in list(self.queues):
                try:
                    q.put_nowait(msg)
                except asyncio.QueueFull:
                    # Keep only the most recent records by dropping the oldest when full.
                    try:
                        q.get_nowait()
                        q.put_nowait(msg)
                    except (asyncio.QueueEmpty, asyncio.QueueFull):
                        # If queue state changed between operations, skip this record.
                        pass
        except Exception:
            self.handleError(record)

    async def subscribe(self) -> asyncio.Queue:
        """Create a new queue for a subscriber."""
        q = asyncio.Queue(maxsize=MAX_SUBSCRIBER_QUEUE_SIZE)
        self.queues.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue):
        """Remove a subscriber's queue."""
        if q in self.queues:
            self.queues.remove(q)
        # Drop buffered logs immediately so abandoned subscribers release memory quickly.
        while not q.empty():
            try:
                q.get_nowait()
            except asyncio.QueueEmpty:
                break


class ContextFormatter(logging.Formatter):
    """Formatter that appends optional context only when present."""

    _context_keys = ("event", "session_id", "turn", "attempt", "tool")
    _RESET = "\033[0m"
    _CATEGORY_COLORS = {
        "LLM": "\033[96m",     # cyan
        "TOOL": "\033[92m",    # green
        "MEMORY": "\033[93m",  # yellow
        "SKILL": "\033[94m",   # blue
        "API": "\033[95m",     # magenta
        "SYSTEM": "\033[90m",  # gray
        "ERROR": "\033[91m",   # red
    }

    def __init__(self, *args, use_color: bool = False, **kwargs):
        super().__init__(*args, **kwargs)
        self.use_color = use_color

    def _categorize(self, record: logging.LogRecord) -> str:
        if record.levelno >= logging.ERROR:
            return "ERROR"

        logger_name = record.name.lower()
        msg = record.getMessage().lower()
        event = str(getattr(record, "event", "")).lower()
        tool_name = getattr(record, "tool", None)

        if tool_name or event in {"tool", "guardian"}:
            return "TOOL"
        if "llm" in msg or "model" in msg or "ainvoke" in msg:
            return "LLM"
        if ".memory." in logger_name or event in {"summary", "memory"}:
            return "MEMORY"
        if ".skills." in logger_name:
            return "SKILL"
        if ".api." in logger_name or event.startswith("api_"):
            return "API"
        return "SYSTEM"

    def format(self, record: logging.LogRecord) -> str:
        # Shorten noisy logger paths (e.g., app.agents.orchestrator -> orchestrator)
        component = record.name.rsplit(".", 1)[-1]
        setattr(record, "component", component)

        category = self._categorize(record)
        category_label = f"[{category}]"
        if self.use_color:
            color = self._CATEGORY_COLORS.get(category, "")
            category_label = f"{color}{category_label}{self._RESET}"
        setattr(record, "category", category_label)

        context_parts = []
        for key in self._context_keys:
            value = getattr(record, key, None)
            if value is None:
                continue
            if isinstance(value, str) and not value.strip():
                continue
            context_parts.append(f"{key}={value}")

        setattr(record, "context_suffix", f" [{', '.join(context_parts)}]" if context_parts else "")
        return super().format(record)


def _build_formatter(use_color: bool = False) -> ContextFormatter:
    return ContextFormatter(
        fmt=(
            "%(asctime)s | %(levelname)-8s | %(component)s:%(lineno)d | "
            "%(category)s %(message)s%(context_suffix)s"
        ),
        datefmt="%H:%M:%S",
        use_color=use_color,
    )


# Global instance
broadcast_handler = LogBroadcastHandler()


def configure_logging(level: int = logging.INFO) -> None:
    """Configure root logger with a consistent backend console format."""
    root = logging.getLogger()
    root.setLevel(level)

    plain_formatter = _build_formatter(use_color=False)
    color_env = os.getenv("ASTROMECH_LOG_COLORS", "1").strip().lower()
    allow_color = color_env not in {"0", "false", "no", "off"}

    if not root.handlers:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(_build_formatter(use_color=allow_color))
        root.addHandler(console_handler)
    else:
        for handler in root.handlers:
            if isinstance(handler, LogBroadcastHandler):
                handler.setFormatter(plain_formatter)
                continue

            is_stream = isinstance(handler, logging.StreamHandler)
            stream = getattr(handler, "stream", None)
            is_tty = bool(stream and hasattr(stream, "isatty") and stream.isatty())
            handler.setFormatter(
                _build_formatter(use_color=allow_color and is_stream and is_tty)
            )

    broadcast_handler.setFormatter(plain_formatter)
    if broadcast_handler not in root.handlers:
        root.addHandler(broadcast_handler)
