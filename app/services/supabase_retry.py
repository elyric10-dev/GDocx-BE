import time
from typing import Callable, Optional, TypeVar

import httpx

T = TypeVar("T")

TRANSIENT_SUPABASE_ERRORS = (
    httpx.ReadError,
    httpx.ConnectError,
    httpx.RemoteProtocolError,
    httpx.WriteError,
    httpx.TimeoutException,
    httpx.NetworkError,
)


def is_transient_supabase_error(exc: Exception) -> bool:
    return isinstance(exc, TRANSIENT_SUPABASE_ERRORS)


def execute_supabase(fn: Callable[[], T], retries: int = 2) -> T:
    last_exc: Optional[Exception] = None

    for attempt in range(retries + 1):
        try:
            return fn()
        except TRANSIENT_SUPABASE_ERRORS as exc:
            last_exc = exc
            if attempt < retries:
                time.sleep(0.15 * (2**attempt))
                continue
            raise

    if last_exc:
        raise last_exc
    raise RuntimeError("execute_supabase failed without an exception")
