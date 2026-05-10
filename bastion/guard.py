"""Guard decorator for structured exception capture."""
# note: implemented

import functools
import hashlib
import json
import traceback
from typing import Any, Callable, List, Optional, TypeVar

from bastion.db import upsert_error

F = TypeVar("F", bound=Callable[..., Any])

_SENSITIVE_KEYS = {"password", "secret", "token", "api_key", "auth", "credential", "ssn", "card", "cvv", "pin"}


def guard(context: Optional[List[str]] = None) -> Callable[[F], F]:
    """Decorator factory that wraps a function in structured error capture.

    Args:
        context: Names of local variables to capture from the failing frame.
                 When None, all locals are captured (sensitive keys are redacted).

    Example::

        @bastion.guard(context=["user_id", "payload"])
        def process(user_id, payload):
            ...
    """
    def decorator(fn: F) -> F:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return fn(*args, **kwargs)
            except Exception as exc:
                tb = exc.__traceback__
                # Walk to the innermost frame for accurate file/line info.
                while tb.tb_next is not None:
                    tb = tb.tb_next
                frame = tb.tb_frame

                # fingerprint for deduplication of errors
                fingerprint = hashlib.sha256(
                    f"{type(exc).__name__}:{frame.f_code.co_filename}:{tb.tb_lineno}".encode()
                ).hexdigest()

                raw_locals = frame.f_locals
                if context is not None:
                    raw_locals = {k: v for k, v in raw_locals.items() if k in context}
                redacted = {
                    k: "[redacted]" if any(s in k.lower() for s in _SENSITIVE_KEYS) else v
                    for k, v in raw_locals.items()
                }

                error_record = {
                    "type": type(exc).__name__,                   # str
                    "message": str(exc),                          # str
                    "function": fn.__qualname__,                  # str
                    "file": frame.f_code.co_filename,             # str
                    "line": tb.tb_lineno,                         # int
                    "fingerprint": fingerprint,                   # str — sha256 hex digest
                    "locals": json.dumps(redacted, default=str),  # str — JSON
                }
                print(error_record)

                try:
                    upsert_error(error_record)
                except Exception:
                    # db error catch
                    pass

                raise
        return wrapper  # type: ignore[return-value]
    return decorator
