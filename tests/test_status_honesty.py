"""Exhaustive tests for --status honesty (profile_info_and_exit / _check_session_api).

Verifies the two critical fixes:
1. Cache check runs BEFORE cooldown check (cooldown no longer bypasses cache)
2. Rate limit cooldown returns False (not True) when no cached result
3. HTTP 429 returns False (not True)
4. Expired session returns False
5. Valid session returns True
"""

from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from instagram_mcp_server.session_cache import SessionCache

# The local import inside _check_session_api uses `from instagram_mcp_server.session_cache import get_session_cache`
# So we patch at the session_cache module level.
PATCH_TARGET = "instagram_mcp_server.session_cache"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset_cache():
    """Reset global cache singleton between tests."""
    import instagram_mcp_server.session_cache as sc
    sc._cache = None
    yield
    sc._cache = None


@pytest.fixture
def fresh_cache(tmp_path, monkeypatch):
    """Create a fresh SessionCache with disk isolated to tmp_path."""
    cache_file = tmp_path / "session_cache.json"
    monkeypatch.setattr(
        "instagram_mcp_server.session_cache._SESSION_CACHE_FILE", cache_file
    )
    cache = SessionCache()
    return cache


def _make_httpx_mock(status_code: int = 200, json_data: dict | None = None, exception: Exception | None = None):
    """Build a mock httpx.AsyncClient that returns the given status/json."""
    mock_response = MagicMock()
    mock_response.status_code = status_code
    if json_data is not None:
        mock_response.json.return_value = json_data

    mock_client = AsyncMock()
    if exception is not None:
        mock_client.get = AsyncMock(side_effect=exception)
    else:
        mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    return mock_client


def _setup_cli_mocks(monkeypatch, fresh_cache, httpx_client=None):
    """Set up the common mocks for _check_session_api tests.

    Patches at the correct module-level targets:
    - instagram_mcp_server.session_cache.get_session_cache → fresh_cache
    - instagram_mcp_server.cli_main.load_cookies → valid cookies dict
    - httpx.AsyncClient → httpx_client mock
    """
    monkeypatch.setattr(f"{PATCH_TARGET}.get_session_cache", lambda: fresh_cache)
    monkeypatch.setattr(
        "instagram_mcp_server.cli_main.load_cookies",
        lambda: {"sessionid": "123:abc:123", "csrftoken": "x"},
    )
    if httpx_client is not None:
        monkeypatch.setattr("httpx.AsyncClient", lambda **kwargs: httpx_client)


# ===========================================================================
# 1. Cache-before-cooldown ordering
# ===========================================================================

class TestCacheBeforeCooldown:
    """The cache check MUST run before the cooldown check."""

    @pytest.mark.asyncio
    async def test_cached_valid_returns_even_during_cooldown(self, fresh_cache, monkeypatch):
        """If cache says valid=True and we're in cooldown, return True (from cache)."""
        from instagram_mcp_server.cli_main import _check_session_api

        fresh_cache.set("session_validity", {"valid": True})
        fresh_cache.set_rate_limit()
        assert fresh_cache.is_in_rate_limit_cooldown()

        monkeypatch.setattr(f"{PATCH_TARGET}.get_session_cache", lambda: fresh_cache)

        result = await _check_session_api()
        assert result is True

    @pytest.mark.asyncio
    async def test_cached_invalid_returns_even_during_cooldown(self, fresh_cache, monkeypatch):
        """If cache says valid=False and we're in cooldown, return False (from cache)."""
        from instagram_mcp_server.cli_main import _check_session_api

        fresh_cache.set("session_validity", {"valid": False})
        fresh_cache.set_rate_limit()
        assert fresh_cache.is_in_rate_limit_cooldown()

        monkeypatch.setattr(f"{PATCH_TARGET}.get_session_cache", lambda: fresh_cache)

        result = await _check_session_api()
        assert result is False

    @pytest.mark.asyncio
    async def test_no_cache_during_cooldown_returns_false(self, fresh_cache, monkeypatch):
        """No cache + in cooldown → return False (can't verify)."""
        from instagram_mcp_server.cli_main import _check_session_api

        assert fresh_cache.get("session_validity") is None
        fresh_cache.set_rate_limit()
        assert fresh_cache.is_in_rate_limit_cooldown()

        monkeypatch.setattr(f"{PATCH_TARGET}.get_session_cache", lambda: fresh_cache)

        result = await _check_session_api()
        assert result is False


# ===========================================================================
# 2. No lies during rate limit (429)
# ===========================================================================

class TestNoLiesDuringRateLimit:
    """Verify _check_session_api returns False (not True) when rate-limited."""

    @pytest.mark.asyncio
    async def test_429_returns_false(self, fresh_cache, monkeypatch):
        """HTTP 429 must return False, not True."""
        from instagram_mcp_server.cli_main import _check_session_api

        mock_client = _make_httpx_mock(status_code=429)
        _setup_cli_mocks(monkeypatch, fresh_cache, mock_client)

        result = await _check_session_api()
        assert result is False

    @pytest.mark.asyncio
    async def test_429_sets_rate_limit(self, fresh_cache, monkeypatch):
        """HTTP 429 should mark rate limit on cache."""
        from instagram_mcp_server.cli_main import _check_session_api

        mock_client = _make_httpx_mock(status_code=429)
        _setup_cli_mocks(monkeypatch, fresh_cache, mock_client)

        await _check_session_api()
        assert fresh_cache.is_in_rate_limit_cooldown()


# ===========================================================================
# 3. Valid session
# ===========================================================================

class TestValidSession:
    """Verify _check_session_api returns True for a valid 200 + status:ok."""

    @pytest.mark.asyncio
    async def test_valid_session_returns_true(self, fresh_cache, monkeypatch):
        from instagram_mcp_server.cli_main import _check_session_api

        mock_client = _make_httpx_mock(
            status_code=200,
            json_data={"status": "ok", "data": {"user": {"id": "123"}}},
        )
        _setup_cli_mocks(monkeypatch, fresh_cache, mock_client)

        result = await _check_session_api()
        assert result is True

    @pytest.mark.asyncio
    async def test_valid_session_caches_result(self, fresh_cache, monkeypatch):
        from instagram_mcp_server.cli_main import _check_session_api

        mock_client = _make_httpx_mock(
            status_code=200,
            json_data={"status": "ok", "data": {"user": {"id": "1"}}},
        )
        _setup_cli_mocks(monkeypatch, fresh_cache, mock_client)

        await _check_session_api()
        cached = fresh_cache.get("session_validity")
        assert cached == {"valid": True}


# ===========================================================================
# 4. Invalid/expired session
# ===========================================================================

class TestInvalidSession:
    """Various failure modes should all return False."""

    @pytest.mark.asyncio
    async def test_403_login_required_returns_false(self, fresh_cache, monkeypatch):
        from instagram_mcp_server.cli_main import _check_session_api

        mock_client = _make_httpx_mock(
            status_code=403,
            json_data={"message": "login_required"},
        )
        _setup_cli_mocks(monkeypatch, fresh_cache, mock_client)

        result = await _check_session_api()
        assert result is False

    @pytest.mark.asyncio
    async def test_200_with_status_fail_returns_false(self, fresh_cache, monkeypatch):
        from instagram_mcp_server.cli_main import _check_session_api

        mock_client = _make_httpx_mock(
            status_code=200,
            json_data={"status": "fail"},
        )
        _setup_cli_mocks(monkeypatch, fresh_cache, mock_client)

        result = await _check_session_api()
        assert result is False

    @pytest.mark.asyncio
    async def test_invalid_json_returns_false(self, fresh_cache, monkeypatch):
        from instagram_mcp_server.cli_main import _check_session_api

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("No JSON")

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        _setup_cli_mocks(monkeypatch, fresh_cache, mock_client)

        result = await _check_session_api()
        assert result is False

    @pytest.mark.asyncio
    async def test_no_cookies_returns_false(self, fresh_cache, monkeypatch):
        from instagram_mcp_server.cli_main import _check_session_api

        monkeypatch.setattr(f"{PATCH_TARGET}.get_session_cache", lambda: fresh_cache)
        monkeypatch.setattr(
            "instagram_mcp_server.cli_main.load_cookies", lambda: {}
        )

        result = await _check_session_api()
        assert result is False
        assert fresh_cache.get("session_validity") == {"valid": False}

    @pytest.mark.asyncio
    async def test_connection_error_returns_false(self, fresh_cache, monkeypatch):
        from instagram_mcp_server.cli_main import _check_session_api

        mock_client = _make_httpx_mock(exception=httpx.ConnectError("refused"))
        _setup_cli_mocks(monkeypatch, fresh_cache, mock_client)

        result = await _check_session_api()
        assert result is False

    @pytest.mark.asyncio
    async def test_timeout_returns_false(self, fresh_cache, monkeypatch):
        from instagram_mcp_server.cli_main import _check_session_api

        mock_client = _make_httpx_mock(exception=httpx.TimeoutException("timed out"))
        _setup_cli_mocks(monkeypatch, fresh_cache, mock_client)

        result = await _check_session_api()
        assert result is False

    @pytest.mark.asyncio
    async def test_invalid_result_caches_false(self, fresh_cache, monkeypatch):
        """A 403 failure should be cached as {valid: False}."""
        from instagram_mcp_server.cli_main import _check_session_api

        mock_client = _make_httpx_mock(
            status_code=403,
            json_data={"message": "login_required"},
        )
        _setup_cli_mocks(monkeypatch, fresh_cache, mock_client)

        await _check_session_api()
        cached = fresh_cache.get("session_validity")
        assert cached == {"valid": False}


# ===========================================================================
# 5. Cache TTL expiry
# ===========================================================================

class TestCacheTTLExpiry:
    """Verify expired cache entries are not used."""

    @pytest.mark.asyncio
    async def test_expired_cache_entry_ignored(self, fresh_cache, monkeypatch):
        """Cache entry older than TTL should be ignored, triggering an API call."""
        from instagram_mcp_server.cli_main import _check_session_api

        # Manually insert an expired cache entry (timestamp in the past)
        fresh_cache._cache_data["session_validity"] = {
            "value": {"valid": True},
            "timestamp": time.time() - 600,  # 10 minutes ago (TTL is 5 min)
        }

        mock_client = _make_httpx_mock(
            status_code=200,
            json_data={"status": "ok", "data": {"user": {"id": "1"}}},
        )
        _setup_cli_mocks(monkeypatch, fresh_cache, mock_client)

        # Should NOT return the stale True — should make a fresh API call
        result = await _check_session_api()
        assert result is True
        mock_client.get.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_fresh_cache_skips_api_call(self, fresh_cache, monkeypatch):
        """Fresh cache hit should skip the API call entirely."""
        from instagram_mcp_server.cli_main import _check_session_api

        fresh_cache.set("session_validity", {"valid": False})

        # This should NOT be called since cache is fresh
        monkeypatch.setattr(f"{PATCH_TARGET}.get_session_cache", lambda: fresh_cache)

        result = await _check_session_api()
        assert result is False


# ===========================================================================
# 6. profile_info_and_exit output
# ===========================================================================

class TestProfileInfoAndExit:
    """Verify --status prints correct output for valid and expired sessions."""

    def _setup_profile_mocks(self, monkeypatch, valid: bool):
        """Common setup for profile_info_and_exit tests."""
        async def _mock_check():
            return valid
        monkeypatch.setattr(
            "instagram_mcp_server.cli_main._check_session_api",
            _mock_check,
        )
        monkeypatch.setattr(
            "instagram_mcp_server.cli_main.get_config",
            lambda: MagicMock(
                server=MagicMock(log_level="WARNING", log_file=None),
                is_interactive=False,
            ),
        )
        monkeypatch.setattr(
            "instagram_mcp_server.cli_main.configure_logging", lambda **kw: None
        )
        monkeypatch.setattr(
            "instagram_mcp_server.cli_main.get_profile_dir",
            lambda: Path("/tmp/profile"),
        )
        monkeypatch.setattr(
            "instagram_mcp_server.cli_main.portable_cookie_path",
            lambda p: p / "cookies.json",
        )
        monkeypatch.setattr(
            "instagram_mcp_server.cli_main.load_source_state",
            lambda p: MagicMock(source_runtime_id="rt1", login_generation=1),
        )
        monkeypatch.setattr(
            "instagram_mcp_server.cli_main.profile_exists", lambda p: True
        )
        monkeypatch.setattr(
            "instagram_mcp_server.cli_main.get_runtime_id", lambda: "rt1"
        )
        monkeypatch.setattr("pathlib.Path.exists", lambda self: True)
        # Suppress sys.exit calls
        monkeypatch.setattr("sys.exit", lambda code: (_ for _ in ()).throw(SystemExit(code)))

    def test_valid_prints_valid(self, monkeypatch, capsys):
        from instagram_mcp_server.cli_main import profile_info_and_exit

        self._setup_profile_mocks(monkeypatch, valid=True)

        with pytest.raises(SystemExit) as exc_info:
            profile_info_and_exit()
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "status: valid" in captured.out

    def test_expired_prints_expired(self, monkeypatch, capsys):
        from instagram_mcp_server.cli_main import profile_info_and_exit

        self._setup_profile_mocks(monkeypatch, valid=False)

        with pytest.raises(SystemExit) as exc_info:
            profile_info_and_exit()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "status: expired" in captured.out


# ===========================================================================
# 7. Profile exit with missing files
# ===========================================================================

class TestProfileExitMissingFiles:
    """Verify --status exits with error when profile/cookies are missing."""

    def test_no_source_state_exits_with_error(self, monkeypatch, capsys):
        from instagram_mcp_server.cli_main import profile_info_and_exit

        monkeypatch.setattr(
            "instagram_mcp_server.cli_main.get_config",
            lambda: MagicMock(
                server=MagicMock(log_level="WARNING", log_file=None),
                is_interactive=False,
            ),
        )
        monkeypatch.setattr(
            "instagram_mcp_server.cli_main.configure_logging", lambda **kw: None
        )
        monkeypatch.setattr(
            "instagram_mcp_server.cli_main.get_profile_dir",
            lambda: Path("/tmp/profile"),
        )
        monkeypatch.setattr(
            "instagram_mcp_server.cli_main.portable_cookie_path",
            lambda p: p / "cookies.json",
        )
        monkeypatch.setattr(
            "instagram_mcp_server.cli_main.load_source_state", lambda p: None
        )
        monkeypatch.setattr("pathlib.Path.exists", lambda self: False)
        monkeypatch.setattr("sys.exit", lambda code: (_ for _ in ()).throw(SystemExit(code)))

        with pytest.raises(SystemExit) as exc_info:
            profile_info_and_exit()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "No valid source session" in captured.out


# ===========================================================================
# 8. Edge cases: concurrent check + cache update
# ===========================================================================

class TestEdgeCases:
    """Edge cases for the status check."""

    @pytest.mark.asyncio
    async def test_second_call_uses_cache(self, fresh_cache, monkeypatch):
        """Second API call should use cached result, not hit API again."""
        from instagram_mcp_server.cli_main import _check_session_api

        call_count = 0

        async def counting_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"status": "ok", "data": {"user": {"id": "1"}}}
            return mock_resp

        mock_client = AsyncMock()
        mock_client.get = counting_get
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        _setup_cli_mocks(monkeypatch, fresh_cache, mock_client)

        # First call → hits API
        result1 = await _check_session_api()
        assert result1 is True
        assert call_count == 1

        # Second call → cache hit, no API call
        result2 = await _check_session_api()
        assert result2 is True
        assert call_count == 1  # still 1

    @pytest.mark.asyncio
    async def test_failed_result_prevents_cooldown_override(self, fresh_cache, monkeypatch):
        """Cache stores False from a failed check; cooldown should not override with True."""
        from instagram_mcp_server.cli_main import _check_session_api

        # Step 1: Do a check that fails → caches False
        mock_client_fail = _make_httpx_mock(
            status_code=403, json_data={"message": "login_required"}
        )
        _setup_cli_mocks(monkeypatch, fresh_cache, mock_client_fail)
        result1 = await _check_session_api()
        assert result1 is False
        assert fresh_cache.get("session_validity") == {"valid": False}

        # Step 2: Put cache in cooldown
        fresh_cache.set_rate_limit()
        assert fresh_cache.is_in_rate_limit_cooldown()

        # Step 3: Another check → should return False from cache, not True
        result2 = await _check_session_api()
        assert result2 is False

    @pytest.mark.asyncio
    async def test_500_returns_false(self, fresh_cache, monkeypatch):
        """HTTP 500 should return False."""
        from instagram_mcp_server.cli_main import _check_session_api

        mock_client = _make_httpx_mock(
            status_code=500, json_data={"message": "Internal Server Error"}
        )
        _setup_cli_mocks(monkeypatch, fresh_cache, mock_client)

        result = await _check_session_api()
        assert result is False

    @pytest.mark.asyncio
    async def test_empty_json_body_returns_false(self, fresh_cache, monkeypatch):
        """Empty JSON body (no 'status' key) should return False."""
        from instagram_mcp_server.cli_main import _check_session_api

        mock_client = _make_httpx_mock(
            status_code=200, json_data={}
        )
        _setup_cli_mocks(monkeypatch, fresh_cache, mock_client)

        result = await _check_session_api()
        assert result is False
