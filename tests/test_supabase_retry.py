"""Tests for the Supabase retry / transient-error helpers."""
import httpx
import pytest

from app.services.supabase_retry import execute_supabase, is_transient_supabase_error


class TestIsTransientSupabaseError:
    def test_read_error_is_transient(self):
        assert is_transient_supabase_error(httpx.ReadError("read fail", request=None))

    def test_connect_error_is_transient(self):
        assert is_transient_supabase_error(httpx.ConnectError("conn fail", request=None))

    def test_timeout_is_transient(self):
        assert is_transient_supabase_error(httpx.TimeoutException("timeout", request=None))

    def test_value_error_is_not_transient(self):
        assert not is_transient_supabase_error(ValueError("not transient"))

    def test_runtime_error_is_not_transient(self):
        assert not is_transient_supabase_error(RuntimeError("nope"))


class TestExecuteSupabase:
    def test_success_on_first_attempt(self):
        result = execute_supabase(lambda: 42)
        assert result == 42

    def test_retries_then_succeeds(self):
        calls = {"n": 0}

        def flaky():
            calls["n"] += 1
            if calls["n"] < 2:
                raise httpx.ReadError("transient", request=None)
            return "ok"

        assert execute_supabase(flaky, retries=2) == "ok"
        assert calls["n"] == 2

    def test_raises_after_exhausting_retries(self):
        def always_fail():
            raise httpx.ConnectError("no server", request=None)

        with pytest.raises(httpx.ConnectError):
            execute_supabase(always_fail, retries=1)

    def test_non_transient_error_not_retried(self):
        calls = {"n": 0}

        def boom():
            calls["n"] += 1
            raise ValueError("bad input")

        with pytest.raises(ValueError):
            execute_supabase(boom, retries=3)

        assert calls["n"] == 1
