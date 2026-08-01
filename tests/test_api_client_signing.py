"""Exhaustive tests for InstagramAPIClient POST signing and user-id header injection.

These tests verify the two critical fixes:
1. POST requests use signed_body format (SHA-256 + JSON, form-encoded)
2. IG-INTENDED-USER-ID / IG-U-DS-USER-ID headers are sent
"""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from instagram_mcp_server.scraping.api_client import (
    InstagramAPIClient,
    API_URL,
    IG_APP_ID,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def cookies_normal() -> dict[str, str]:
    """Cookies with a well-formed sessionid (colon-separated)."""
    return {
        "sessionid": "1234567890:abc123def:1700000000",
        "csrftoken": "csrf_token_value",
        "mid": "YAbCdEfGhIjKlMnOpQrSt",
        "ds_user_id": "1234567890",
    }


@pytest.fixture
def cookies_url_encoded() -> dict[str, str]:
    """Cookies with URL-encoded sessionid (%3A instead of colons)."""
    return {
        "sessionid": "9876543210%3Atoken456%3A1700000000",
        "csrftoken": "csrf_xyz",
    }


@pytest.fixture
def cookies_no_sessionid() -> dict[str, str]:
    """Cookies without sessionid."""
    return {
        "csrftoken": "csrf_token_only",
        "mid": "some_mid",
    }


@pytest.fixture
def cookies_empty() -> dict[str, str]:
    return {}


@pytest.fixture
def cookies_malformed() -> dict[str, str]:
    """sessionid that doesn't follow the expected format."""
    return {
        "sessionid": "not-a-valid-sessionid",
        "csrftoken": "csrf_token",
    }


# ===========================================================================
# 1. _extract_user_id tests
# ===========================================================================

class TestExtractUserId:
    """Test user-ID extraction from sessionid cookie."""

    def test_normal_colon_separated(self, cookies_normal):
        client = InstagramAPIClient(cookies_normal)
        assert client._user_id == "1234567890"

    def test_url_encoded_colons(self, cookies_url_encoded):
        client = InstagramAPIClient(cookies_url_encoded)
        assert client._user_id == "9876543210"

    def test_no_sessionid(self, cookies_no_sessionid):
        client = InstagramAPIClient(cookies_no_sessionid)
        assert client._user_id == ""

    def test_empty_cookies(self, cookies_empty):
        client = InstagramAPIClient(cookies_empty)
        assert client._user_id == ""

    def test_malformed_sessionid(self, cookies_malformed):
        client = InstagramAPIClient(cookies_malformed)
        assert client._user_id == ""

    def test_sessionid_only_numeric_token(self):
        """sessionid with numeric token but no timestamp."""
        client = InstagramAPIClient({"sessionid": "1234567890:token"})
        assert client._user_id == "1234567890"

    def test_sessionid_with_extra_parts(self):
        """sessionid with more than 3 parts."""
        client = InstagramAPIClient({"sessionid": "1234567890:token:12345:extra"})
        assert client._user_id == "1234567890"

    def test_sessionid_starts_with_non_digit(self):
        """sessionid where first part is not numeric."""
        client = InstagramAPIClient({"sessionid": "abc:token:12345"})
        assert client._user_id == ""


# ===========================================================================
# 2. _sign_body tests
# ===========================================================================

class TestSignBody:
    """Test SHA-256 signed_body format generation."""

    def test_basic_signature(self):
        data = {"key": "value"}
        result = InstagramAPIClient._sign_body(data)
        body_json = json.dumps(data, separators=(",", ":"))
        expected_sig = hashlib.sha256(body_json.encode()).hexdigest()
        assert result == f"{expected_sig}.{body_json}"

    def test_empty_dict(self):
        result = InstagramAPIClient._sign_body({})
        sig, body = result.split(".", 1)
        assert len(sig) == 64  # SHA-256 hex digest
        assert body == "{}"

    def test_nested_data(self):
        data = {"_csrftoken": "abc", "text": "hello", "users": ["1", "2"]}
        result = InstagramAPIClient._sign_body(data)
        sig, body = result.split(".", 1)
        assert len(sig) == 64  # SHA-256 hex digest
        parsed = json.loads(body)
        assert parsed == data

    def test_signature_is_sha256(self):
        data = {"test": 123}
        result = InstagramAPIClient._sign_body(data)
        sig = result.split(".")[0]
        # SHA-256 hex digest is 64 chars
        assert len(sig) == 64
        assert all(c in "0123456789abcdef" for c in sig)

    def test_deterministic(self):
        """Same input always produces same output."""
        data = {"foo": "bar"}
        r1 = InstagramAPIClient._sign_body(data)
        r2 = InstagramAPIClient._sign_body(data)
        assert r1 == r2

    def test_different_data_different_signature(self):
        """Different payloads produce different signatures."""
        r1 = InstagramAPIClient._sign_body({"a": 1})
        r2 = InstagramAPIClient._sign_body({"a": 2})
        assert r1 != r2

    def test_separators_are_compact(self):
        """JSON must use compact separators (no spaces after comma/colon)."""
        data = {"a": 1, "b": 2}
        result = InstagramAPIClient._sign_body(data)
        body = result.split(".", 1)[1]
        assert ", " not in body
        assert ": " not in body


# ===========================================================================
# 3. _request POST form-encoding tests
# ===========================================================================

class TestRequestPostFormEncoding:
    """Test that POST requests with data use signed_body form encoding."""

    @pytest.mark.asyncio
    async def test_post_with_data_uses_form_encoding(self, cookies_normal):
        """POST with data should send signed_body as form-encoded, not JSON."""
        client = InstagramAPIClient(cookies_normal)
        try:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "ok"}
            mock_response.raise_for_status = MagicMock()

            with patch.object(client._client, "request", new_callable=AsyncMock) as mock_req:
                mock_req.return_value = mock_response
                await client._post("/test/endpoint/", data={"key": "value"})

                mock_req.assert_called_once()
                call_args = mock_req.call_args
                # Should use data= (form-encoded), NOT json=
                assert "data" in call_args.kwargs
                assert "json" not in call_args.kwargs
                # data should contain signed_body key
                form_data = call_args.kwargs["data"]
                assert "signed_body" in form_data
        finally:
            await client._client.aclose()

    @pytest.mark.asyncio
    async def test_post_without_data_sends_no_body(self, cookies_normal):
        """POST without data should not send a body."""
        client = InstagramAPIClient(cookies_normal)
        try:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "ok"}
            mock_response.raise_for_status = MagicMock()

            with patch.object(client._client, "request", new_callable=AsyncMock) as mock_req:
                mock_req.return_value = mock_response
                await client._post("/friendships/create/123/")

                call_args = mock_req.call_args
                # Should NOT have data= or json= keyword
                assert "data" not in call_args.kwargs
                assert "json" not in call_args.kwargs
        finally:
            await client._client.aclose()

    @pytest.mark.asyncio
    async def test_post_signed_body_format(self, cookies_normal):
        """The signed_body value must be {sha256}.{json}."""
        client = InstagramAPIClient(cookies_normal)
        try:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "ok"}
            mock_response.raise_for_status = MagicMock()

            data = {"_csrftoken": "token", "text": "hello"}
            with patch.object(client._client, "request", new_callable=AsyncMock) as mock_req:
                mock_req.return_value = mock_response
                await client._post("/test/", data=data)

                form_data = mock_req.call_args.kwargs["data"]
                signed_body = form_data["signed_body"]
                sig, body = signed_body.split(".", 1)

                # Verify SHA-256 signature
                expected_sig = hashlib.sha256(
                    json.dumps(data, separators=(",", ":")).encode()
                ).hexdigest()
                assert sig == expected_sig
                assert json.loads(body) == data
        finally:
            await client._client.aclose()

    @pytest.mark.asyncio
    async def test_post_signed_body_contains_csrf(self, cookies_normal):
        """DM payload with _csrftoken should be properly signed."""
        client = InstagramAPIClient(cookies_normal)
        try:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "ok"}
            mock_response.raise_for_status = MagicMock()

            dm_data = {
                "_csrftoken": "csrf_token_value",
                "text": "test message",
                "recipient_users": json.dumps(["123"]),
            }
            with patch.object(client._client, "request", new_callable=AsyncMock) as mock_req:
                mock_req.return_value = mock_response
                await client._post("/direct_v2/threads/broadcast/text/", data=dm_data)

                form_data = mock_req.call_args.kwargs["data"]
                signed_body = form_data["signed_body"]
                _, body_json = signed_body.split(".", 1)
                parsed = json.loads(body_json)
                assert parsed["_csrftoken"] == "csrf_token_value"
                assert parsed["text"] == "test message"
        finally:
            await client._client.aclose()


# ===========================================================================
# 4. Header injection tests
# ===========================================================================

class TestHeaderInjection:
    """Test that IG-INTENDED-USER-ID and IG-U-DS-USER-ID are set."""

    async def test_user_id_headers_present_with_valid_sessionid(self, cookies_normal):
        client = InstagramAPIClient(cookies_normal)
        try:
            headers = client._client.headers
            assert headers.get("IG-INTENDED-USER-ID") == "1234567890"
            assert headers.get("IG-U-DS-USER-ID") == "1234567890"
        finally:
            await client._client.aclose()

    async def test_user_id_headers_absent_without_sessionid(self, cookies_no_sessionid):
        client = InstagramAPIClient(cookies_no_sessionid)
        try:
            headers = client._client.headers
            assert "IG-INTENDED-USER-ID" not in headers
            assert "IG-U-DS-USER-ID" not in headers
        finally:
            await client._client.aclose()

    async def test_csrf_token_header(self, cookies_normal):
        client = InstagramAPIClient(cookies_normal)
        try:
            assert client._client.headers.get("X-CSRFToken") == "csrf_token_value"
        finally:
            await client._client.aclose()

    async def test_app_id_header(self, cookies_normal):
        client = InstagramAPIClient(cookies_normal)
        try:
            assert client._client.headers.get("X-IG-App-ID") == IG_APP_ID
        finally:
            await client._client.aclose()

    async def test_x_requested_with_header(self, cookies_normal):
        client = InstagramAPIClient(cookies_normal)
        try:
            assert client._client.headers.get("X-Requested-With") == "XMLHttpRequest"
        finally:
            await client._client.aclose()

    async def test_origin_and_referer(self, cookies_normal):
        client = InstagramAPIClient(cookies_normal)
        try:
            assert client._client.headers.get("Origin") == "https://www.instagram.com"
            assert client._client.headers.get("Referer") == "https://www.instagram.com/"
        finally:
            await client._client.aclose()

    async def test_url_encoded_sessionid_sets_user_id(self, cookies_url_encoded):
        client = InstagramAPIClient(cookies_url_encoded)
        try:
            assert client._user_id == "9876543210"
            assert client._client.headers.get("IG-INTENDED-USER-ID") == "9876543210"
        finally:
            await client._client.aclose()

    async def test_user_id_headers_on_all_requests(self, cookies_normal):
        """Verify headers are set on the httpx client (applied to every request)."""
        client = InstagramAPIClient(cookies_normal)
        try:
            h = client._client.headers
            assert "IG-INTENDED-USER-ID" in h
            assert "IG-U-DS-USER-ID" in h
        finally:
            await client._client.aclose()


# ===========================================================================
# 5. GET requests should NOT be form-encoded
# ===========================================================================

class TestGetRequestsUnchanged:
    """Verify GET requests are not affected by the signing changes."""

    @pytest.mark.asyncio
    async def test_get_no_body(self, cookies_normal):
        client = InstagramAPIClient(cookies_normal)
        try:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "ok", "data": {}}
            mock_response.raise_for_status = MagicMock()

            with patch.object(client._client, "request", new_callable=AsyncMock) as mock_req:
                mock_req.return_value = mock_response
                await client._get("/test/", params={"key": "value"})

                call_args = mock_req.call_args
                assert call_args.args[0] == "GET"
                assert "params" in call_args.kwargs
                assert "data" not in call_args.kwargs
                assert "json" not in call_args.kwargs
        finally:
            await client._client.aclose()


# ===========================================================================
# 6. Retry and error handling with new signing
# ===========================================================================

class TestRetryAndErrors:
    """Verify retry logic still works with the new POST signing path."""

    @pytest.mark.asyncio
    async def test_post_retries_on_timeout(self, cookies_normal):
        client = InstagramAPIClient(cookies_normal)
        try:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "ok"}
            mock_response.raise_for_status = MagicMock()

            with patch.object(client._client, "request", new_callable=AsyncMock) as mock_req:
                mock_req.side_effect = [
                    httpx.TimeoutException("timeout"),
                    mock_response,
                ]
                with patch("instagram_mcp_server.scraping.api_client._async_sleep", new_callable=AsyncMock):
                    result = await client._post("/test/", data={"x": 1})
                    assert result["status"] == "ok"
                    assert mock_req.call_count == 2
        finally:
            await client._client.aclose()

    @pytest.mark.asyncio
    async def test_post_raises_auth_error_on_403_login_required(self, cookies_normal):
        from instagram_mcp_server.core.exceptions import AuthenticationError

        client = InstagramAPIClient(cookies_normal)
        try:
            mock_response = MagicMock()
            mock_response.status_code = 403
            mock_response.json.return_value = {"message": "login_required"}

            with patch.object(client._client, "request", new_callable=AsyncMock) as mock_req:
                mock_req.return_value = mock_response
                with pytest.raises(AuthenticationError, match="expired"):
                    await client._post("/test/", data={"x": 1})
        finally:
            await client._client.aclose()

    @pytest.mark.asyncio
    async def test_post_raises_rate_limit_on_429(self, cookies_normal):
        from instagram_mcp_server.core.exceptions import RateLimitError

        client = InstagramAPIClient(cookies_normal)
        try:
            mock_response = MagicMock()
            mock_response.status_code = 429

            with patch.object(client._client, "request", new_callable=AsyncMock) as mock_req:
                mock_req.return_value = mock_response
                with patch("instagram_mcp_server.scraping.api_client._async_sleep", new_callable=AsyncMock):
                    with pytest.raises(RateLimitError):
                        await client._post("/test/", data={"x": 1})
        finally:
            await client._client.aclose()


# ===========================================================================
# 7. Real action endpoint signing
# ===========================================================================

class TestActionEndpointSigning:
    """Verify each action endpoint sends properly signed POST requests."""

    def _mock_success(self, client, response_data: dict[str, Any] = None):
        """Set up mock for successful POST."""
        if response_data is None:
            response_data = {"status": "ok", "friendship_status": {"following": True}}
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = response_data
        mock_response.raise_for_status = MagicMock()
        return mock_response

    @pytest.mark.asyncio
    async def test_follow_user_sends_post(self, cookies_normal):
        client = InstagramAPIClient(cookies_normal)
        try:
            mock_response = self._mock_success(client)
            with patch.object(client._client, "request", new_callable=AsyncMock) as mock_req:
                mock_req.return_value = mock_response
                # Mock the _resolve_user_id call
                with patch.object(client, "_resolve_user_id_cached", new_callable=AsyncMock) as mock_resolve:
                    mock_resolve.return_value = "12345"
                    result = await client.follow_user("testuser")

                    mock_req.assert_called_once()
                    call_args = mock_req.call_args
                    assert call_args.args[0] == "POST"
                    assert "/friendships/create/12345/" in call_args.args[1]
                    # No body for follow (data=None path)
                    assert "data" not in call_args.kwargs
        finally:
            await client._client.aclose()

    @pytest.mark.asyncio
    async def test_unfollow_user_sends_post(self, cookies_normal):
        client = InstagramAPIClient(cookies_normal)
        try:
            mock_response = self._mock_success(client, {"status": "ok"})
            with patch.object(client._client, "request", new_callable=AsyncMock) as mock_req:
                mock_req.return_value = mock_response
                with patch.object(client, "_resolve_user_id_cached", new_callable=AsyncMock) as mock_resolve:
                    mock_resolve.return_value = "12345"
                    result = await client.unfollow_user("testuser")

                    call_args = mock_req.call_args
                    assert call_args.args[0] == "POST"
                    assert "/friendships/destroy/12345/" in call_args.args[1]
        finally:
            await client._client.aclose()

    @pytest.mark.asyncio
    async def test_like_post_sends_post(self, cookies_normal):
        client = InstagramAPIClient(cookies_normal)
        try:
            mock_response = self._mock_success(client, {"status": "ok"})
            with patch.object(client._client, "request", new_callable=AsyncMock) as mock_req:
                mock_req.return_value = mock_response
                with patch.object(client, "_resolve_user_id_cached", new_callable=AsyncMock):
                    result = await client.like_post("https://www.instagram.com/p/ABC123/")

                    call_args = mock_req.call_args
                    assert call_args.args[0] == "POST"
                    assert "/like/" in call_args.args[1]
        finally:
            await client._client.aclose()

    @pytest.mark.asyncio
    async def test_unlike_post_sends_post(self, cookies_normal):
        client = InstagramAPIClient(cookies_normal)
        try:
            mock_response = self._mock_success(client, {"status": "ok"})
            with patch.object(client._client, "request", new_callable=AsyncMock) as mock_req:
                mock_req.return_value = mock_response
                with patch.object(client, "_resolve_user_id_cached", new_callable=AsyncMock):
                    result = await client.unlike_post("https://www.instagram.com/p/XYZ789/")

                    call_args = mock_req.call_args
                    assert call_args.args[0] == "POST"
                    assert "/unlike/" in call_args.args[1]
        finally:
            await client._client.aclose()

    @pytest.mark.asyncio
    async def test_comment_on_post_uses_signed_body(self, cookies_normal):
        client = InstagramAPIClient(cookies_normal)
        try:
            mock_response = self._mock_success(client, {"status": "ok"})
            with patch.object(client._client, "request", new_callable=AsyncMock) as mock_req:
                mock_req.return_value = mock_response
                with patch.object(client, "_resolve_user_id_cached", new_callable=AsyncMock):
                    result = await client.comment_on_post(
                        "https://www.instagram.com/p/ABC123/", "Great post!"
                    )

                    call_args = mock_req.call_args
                    assert call_args.args[0] == "POST"
                    # Comment sends data → should be signed
                    assert "data" in call_args.kwargs
                    form_data = call_args.kwargs["data"]
                    assert "signed_body" in form_data
                    # Verify comment text is in the signed body
                    signed_body = form_data["signed_body"]
                    _, body_json = signed_body.split(".", 1)
                    parsed = json.loads(body_json)
                    assert parsed.get("comment_text") == "Great post!"
        finally:
            await client._client.aclose()

    @pytest.mark.asyncio
    async def test_send_dm_uses_signed_body(self, cookies_normal):
        client = InstagramAPIClient(cookies_normal)
        try:
            mock_response = self._mock_success(client, {"status": "ok"})
            with patch.object(client._client, "request", new_callable=AsyncMock) as mock_req:
                mock_req.return_value = mock_response
                with patch.object(client, "_resolve_user_id_cached", new_callable=AsyncMock) as mock_resolve:
                    mock_resolve.return_value = "99999"
                    result = await client.send_dm("testuser", "Hello!")

                    call_args = mock_req.call_args
                    assert call_args.args[0] == "POST"
                    # DM sends data → should be signed
                    assert "data" in call_args.kwargs
                    form_data = call_args.kwargs["data"]
                    assert "signed_body" in form_data
                    # Verify DM content is in the signed body
                    signed_body = form_data["signed_body"]
                    _, body_json = signed_body.split(".", 1)
                    parsed = json.loads(body_json)
                    assert parsed["text"] == "Hello!"
                    assert "recipient_users" in parsed
        finally:
            await client._client.aclose()

    @pytest.mark.asyncio
    async def test_save_post_sends_post(self, cookies_normal):
        client = InstagramAPIClient(cookies_normal)
        try:
            mock_response = self._mock_success(client, {"status": "ok"})
            with patch.object(client._client, "request", new_callable=AsyncMock) as mock_req:
                mock_req.return_value = mock_response
                with patch.object(client, "_resolve_user_id_cached", new_callable=AsyncMock):
                    result = await client.save_post("https://www.instagram.com/p/ABC123/")

                    call_args = mock_req.call_args
                    assert call_args.args[0] == "POST"
                    assert "/save/" in call_args.args[1]
        finally:
            await client._client.aclose()
