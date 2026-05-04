"""Guard decorator for structured exception capture."""

import functools
import inspect
import traceback
from typing import Any, Callable, List, Optional, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


def guard(context: Optional[List[str]] = None) -> Callable[[F], F]:
    """Decorator factory that wraps a function in structured error capture.

    Args:
        context: Names of local variables to capture from the failing frame.
                 Stubbed — variable capture is not yet implemented.

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
                error_record = {
                    "type": type(exc).__name__,
                    "message": str(exc),
                    "function": fn.__qualname__,
                    "file": frame.f_code.co_filename,
                    "line": tb.tb_lineno,
                }
                print(error_record)
                # TODO: capture frame locals via inspect.currentframe() (or the tb frame above),
                #       filter to only the variable names listed in `context`, and add them to
                #       error_record under a "locals" key.
                # TODO: generate a stable fingerprint (e.g. sha256 of type + file + line) and
                #       add it to error_record under a "fingerprint" key.
                # TODO: persist error_record to the SQLite errors table opened by core.init().
                raise
        return wrapper  # type: ignore[return-value]
    return decorator
