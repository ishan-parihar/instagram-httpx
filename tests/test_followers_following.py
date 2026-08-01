"""
Tests for Instagram follower/following API methods.

Covers: _get_followers_or_following, get_followers, get_following,
anti-bot jitter, soft-block backoff, pagination, hard cap, and
scrape_user integration.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from instagram_mcp_server.scraping.api_client import (
    InstagramAPIClient,
    _JITTER_MAX,
    _JITTER_MIN,
    _MAX_FOLLOW_USERS,
    _SOFT_BLOCK_SLEEP,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_client(cookies: dict[str, str] | None = None) -> InstagramAPIClient:
    """Create a client with mocked httpx.AsyncClient."""
    if cookies is None:
        cookies = {"sessionid": "12345:abc:1234567890", "csrftoken": "csrf"}
    client = InstagramAPIClient(cookies)
    client._client = AsyncMock()
    client._client.close = AsyncMock()
    return client


def _mock_response(status_code: int, json_data: dict | None = None):
    """Create a mock httpx.Response."""
    resp = AsyncMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.text = json.dumps(json_data) if json_data else "{}"
    # Make awaitable: resp = await client._client.request(...)
    return resp


def _make_user(pk: int, username: str, **overrides) -> dict:
    """Create a user dict matching Instagram's API shape."""
    base = {
        "pk": pk,
        "username": username,
        "full_name": f"User {username}",
        "profile_pic_url": f"https://example.com/{username}.jpg",
        "is_private": False,
        "is_verified": False,
    }
    base.update(overrides)
    return base


def _paginate_response(users: list[dict], max_id: str | None = None) -> dict:
    """Simulate Instagram's paginated response."""
    resp: dict = {"users": users}
    if max_id:
        resp["next_max_id"] = max_id
    return resp


# ---------------------------------------------------------------------------
# _get_followers_or_following — core pagination logic
# ---------------------------------------------------------------------------


class TestCorePagination:
    """Test the shared pagination engine."""

    @pytest.mark.asyncio
    async def test_single_page_no_next(self):
        """No next_max_id → returns one page of results."""
        client = _make_client()
        users = [_make_user(i, f"user{i}") for i in range(5)]

        # Mock _resolve_user_id_cached to avoid profile API call
        client._user_id_cache = {"testuser": "999"}

        # Mock _get to return one page with no next_max_id
        client._get = AsyncMock(return_value=_paginate_response(users))

        with patch("instagram_mcp_server.scraping.api_client.random.randint", return_value=50):
            with patch.object(client, "_sleep", new_callable=AsyncMock):
                result = await client.get_followers("testuser", max_count=50)

        assert result["total"] == 5
        assert result["has_more"] is False
        assert result["pages_fetched"] == 1
        assert len(result["users"]) == 5
        assert result["users"][0]["username"] == "user0"

    @pytest.mark.asyncio
    async def test_multi_page_pagination(self):
        """Multiple pages with next_max_id cursor."""
        client = _make_client()
        client._user_id_cache = {"testuser": "999"}

        page1_users = [_make_user(i, f"user{i}") for i in range(5)]
        page2_users = [_make_user(i + 5, f"user{i + 5}") for i in range(3)]

        call_count = 0

        async def _mock_get(path, params=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _paginate_response(page1_users, max_id="cursor_abc")
            elif call_count == 2:
                return _paginate_response(page2_users)
            return _paginate_response([])

        client._get = _mock_get

        with patch("instagram_mcp_server.scraping.api_client.random.randint", return_value=50):
            with patch.object(client, "_sleep", new_callable=AsyncMock):
                result = await client.get_following("testuser", max_count=20)

        assert result["total"] == 8
        assert result["pages_fetched"] == 2
        assert result["has_more"] is False

    @pytest.mark.asyncio
    async def test_empty_response_stops(self):
        """Empty users list → returns immediately."""
        client = _make_client()
        client._user_id_cache = {"testuser": "999"}
        client._get = AsyncMock(return_value={"users": []})

        result = await client.get_followers("testuser", max_count=100)

        assert result["total"] == 0
        assert result["users"] == []

    @pytest.mark.asyncio
    async def test_hard_cap_enforced(self):
        """max_count > _MAX_FOLLOW_USERS is clamped."""
        client = _make_client()
        client._user_id_cache = {"testuser": "999"}

        users = [_make_user(i, f"user{i}") for i in range(100)]

        page_count = 0

        async def _mock_get(path, params=None):
            nonlocal page_count
            page_count += 1
            if page_count <= 10:
                return _paginate_response(users, max_id=f"cursor_{page_count}")
            return _paginate_response([])

        client._get = _mock_get

        with patch("instagram_mcp_server.scraping.api_client.random.randint", return_value=50):
            with patch.object(client, "_sleep", new_callable=AsyncMock):
                result = await client.get_followers("testuser", max_count=9999)

        assert result["total"] <= _MAX_FOLLOW_USERS

    @pytest.mark.asyncio
    async def test_max_count_zero_uses_default(self):
        """max_count=0 → uses _MAX_FOLLOW_USERS default."""
        client = _make_client()
        client._user_id_cache = {"testuser": "999"}
        client._get = AsyncMock(return_value=_paginate_response([]))

        with patch.object(client, "_sleep", new_callable=AsyncMock):
            result = await client.get_followers("testuser", max_count=0)

        # Should attempt with the default cap
        assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_has_more_when_limit_reached(self):
        """has_more=True when we hit max_count but there are more pages."""
        client = _make_client()
        client._user_id_cache = {"testuser": "999"}

        page_count = 0

        async def _mock_get(path, params=None):
            nonlocal page_count
            page_count += 1
            # Always return users with a next cursor
            return _paginate_response(
                [_make_user(page_count * 10 + i, f"user{i}") for i in range(10)],
                max_id="more",
            )

        client._get = _mock_get

        with patch("instagram_mcp_server.scraping.api_client.random.randint", return_value=50):
            with patch.object(client, "_sleep", new_callable=AsyncMock):
                result = await client.get_followers("testuser", max_count=5)

        assert result["total"] == 5
        assert result["has_more"] is True


# ---------------------------------------------------------------------------
# Anti-bot jitter
# ---------------------------------------------------------------------------


class TestAntiBotMeasures:
    """Verify jitter, soft-block backoff, and rate-limit behavior."""

    @pytest.mark.asyncio
    async def test_jitter_between_pages(self):
        """Each page transition triggers a randomized sleep."""
        client = _make_client()
        client._user_id_cache = {"testuser": "999"}

        page_count = 0

        async def _mock_get(path, params=None):
            nonlocal page_count
            page_count += 1
            if page_count <= 2:
                return _paginate_response(
                    [_make_user(page_count, f"user{page_count}")],
                    max_id="next",
                )
            return _paginate_response([])

        client._get = _mock_get

        sleep_calls = []

        async def _mock_sleep(secs):
            sleep_calls.append(secs)

        with patch("instagram_mcp_server.scraping.api_client.random.randint", return_value=50):
            with patch.object(client, "_sleep", side_effect=_mock_sleep):
                await client.get_followers("testuser", max_count=5)

        # Should have jitter sleeps between pages (at least 1)
        assert len(sleep_calls) >= 1
        for s in sleep_calls:
            assert _JITTER_MIN <= s <= _JITTER_MAX

    @pytest.mark.asyncio
    async def test_no_jitter_after_last_page(self):
        """No jitter after the final page (no next_max_id)."""
        client = _make_client()
        client._user_id_cache = {"testuser": "999"}

        # Single page, no next
        client._get = AsyncMock(return_value=_paginate_response([_make_user(1, "a")]))

        sleep_calls = []

        async def _mock_sleep(secs):
            sleep_calls.append(secs)

        with patch.object(client, "_sleep", side_effect=_mock_sleep):
            await client.get_followers("testuser", max_count=10)

        assert len(sleep_calls) == 0

    @pytest.mark.asyncio
    async def test_soft_block_backoff(self):
        """Soft-block (please_wait) triggers sleep + retry."""
        client = _make_client()
        client._user_id_cache = {"testuser": "999"}

        from instagram_mcp_server.core.exceptions import AuthenticationError

        call_count = 0

        async def _mock_get(path, params=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise AuthenticationError("please_wait_a_few_minutes")
            return _paginate_response([_make_user(1, "a")])

        client._get = _mock_get

        sleep_calls = []

        async def _mock_sleep(secs):
            sleep_calls.append(secs)

        with patch("instagram_mcp_server.scraping.api_client.random.randint", return_value=50):
            with patch.object(client, "_sleep", side_effect=_mock_sleep):
                result = await client.get_followers("testuser", max_count=10)

        # Should have slept for soft-block + no jitter for single page
        assert any(s >= _SOFT_BLOCK_SLEEP for s in sleep_calls)
        assert result["total"] == 1

    @pytest.mark.asyncio
    async def test_soft_block_max_retries_exceeded(self):
        """After 3 soft-blocks, re-raise the error."""
        client = _make_client()
        client._user_id_cache = {"testuser": "999"}

        from instagram_mcp_server.core.exceptions import AuthenticationError

        async def _mock_get(path, params=None):
            raise AuthenticationError("please_wait_a_few_minutes")

        client._get = _mock_get

        with patch.object(client, "_sleep", new_callable=AsyncMock):
            with pytest.raises(AuthenticationError, match="wait"):
                await client.get_followers("testuser", max_count=10)

    @pytest.mark.asyncio
    async def test_non_softblock_auth_error_propagates(self):
        """Non-soft-block AuthenticationError is not retried."""
        client = _make_client()
        client._user_id_cache = {"testuser": "999"}

        from instagram_mcp_server.core.exceptions import AuthenticationError

        async def _mock_get(path, params=None):
            raise AuthenticationError("login_required")

        client._get = _mock_get

        with pytest.raises(AuthenticationError, match="login_required"):
            await client.get_followers("testuser", max_count=10)

    @pytest.mark.asyncio
    async def test_ratelimit_error_propagates(self):
        """RateLimitError (from HTTP 429 exhaustion) propagates without retry."""
        client = _make_client()
        client._user_id_cache = {"testuser": "999"}

        from instagram_mcp_server.core.exceptions import RateLimitError

        async def _mock_get(path, params=None):
            raise RateLimitError("Instagram rate-limited this request")

        client._get = _mock_get

        with pytest.raises(RateLimitError, match="rate-limited"):
            await client.get_followers("testuser", max_count=10)

    @pytest.mark.asyncio
    async def test_soft_block_counter_resets_after_success(self):
        """Soft-block counter resets to 0 after a successful page fetch."""
        client = _make_client()
        client._user_id_cache = {"testuser": "999"}

        from instagram_mcp_server.core.exceptions import AuthenticationError

        call_count = 0

        async def _mock_get(path, params=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise AuthenticationError("please_wait_a_few_minutes")
            if call_count == 2:
                # Success — counter should reset
                return _paginate_response([_make_user(1, "a")], max_id="next")
            if call_count == 3:
                # Another soft-block — should be retried since counter reset
                raise AuthenticationError("please_wait_a_few_minutes")
            return _paginate_response([_make_user(2, "b")])

        client._get = _mock_get

        sleep_calls = []

        async def _mock_sleep(secs):
            sleep_calls.append(secs)

        with patch.object(client, "_sleep", side_effect=_mock_sleep):
            result = await client.get_followers("testuser", max_count=10)

        # Both soft-blocks should have been retried, total 2 successes
        assert result["total"] == 2
        soft_block_sleeps = [s for s in sleep_calls if s >= _SOFT_BLOCK_SLEEP]
        assert len(soft_block_sleeps) == 2  # one per soft-block

    @pytest.mark.asyncio
    async def test_randomised_page_size(self):
        """Page size uses random.randint, not a fixed value."""
        client = _make_client()
        client._user_id_cache = {"testuser": "999"}

        captured_params = []

        async def _mock_get(path, params=None):
            captured_params.append(params or {})
            if len(captured_params) < 3:
                return _paginate_response(
                    [_make_user(len(captured_params), f"u{len(captured_params)}")],
                    max_id="next",
                )
            return _paginate_response([])

        client._get = _mock_get

        with patch("instagram_mcp_server.scraping.api_client.random.randint", return_value=42):
            with patch.object(client, "_sleep", new_callable=AsyncMock):
                await client.get_followers("testuser", max_count=10)

        # All pages should have count=42 (from mocked randint)
        for p in captured_params:
            assert p.get("count") == 42


# ---------------------------------------------------------------------------
# get_followers / get_following — thin wrappers
# ---------------------------------------------------------------------------


class TestGetFollowersAndFollowing:
    """Verify the convenience methods route correctly."""

    @pytest.mark.asyncio
    async def test_get_followers_uses_followers_endpoint(self):
        client = _make_client()
        client._user_id_cache = {"testuser": "999"}
        client._get = AsyncMock(return_value=_paginate_response([]))

        with patch.object(client, "_sleep", new_callable=AsyncMock):
            result = await client.get_followers("testuser", max_count=50)

        assert result["url"] == "https://www.instagram.com/testuser/followers/"

    @pytest.mark.asyncio
    async def test_get_following_uses_following_endpoint(self):
        client = _make_client()
        client._user_id_cache = {"testuser": "999"}
        client._get = AsyncMock(return_value=_paginate_response([]))

        with patch.object(client, "_sleep", new_callable=AsyncMock):
            result = await client.get_following("testuser", max_count=50)

        assert result["url"] == "https://www.instagram.com/testuser/following/"

    @pytest.mark.asyncio
    async def test_user_fields_extracted(self):
        """Each user entry has the expected fields."""
        client = _make_client()
        client._user_id_cache = {"testuser": "999"}

        users = [_make_user(42, "jane", full_name="Jane Doe", is_verified=True, is_private=True)]
        client._get = AsyncMock(return_value=_paginate_response(users))

        with patch.object(client, "_sleep", new_callable=AsyncMock):
            result = await client.get_followers("testuser", max_count=10)

        u = result["users"][0]
        assert u["pk"] == 42
        assert u["username"] == "jane"
        assert u["full_name"] == "Jane Doe"
        assert u["is_verified"] is True
        assert u["is_private"] is True
        assert "profile_pic_url" in u


# ---------------------------------------------------------------------------
# scrape_user integration
# ---------------------------------------------------------------------------


class TestScrapeUserFollowersIntegration:
    """Verify scrape_user calls the real follower/following endpoints."""

    @pytest.mark.asyncio
    async def test_scrape_user_with_followers_section(self):
        """scrape_user with 'followers' section calls get_followers."""
        client = _make_client()
        client._user_id_cache = {"testuser": "999"}

        # Mock profile API
        profile_user = {
            "username": "testuser",
            "full_name": "Test",
            "biography": "hello",
            "follower_count": 5000,
            "following_count": 200,
            "media_count": 10,
            "is_private": False,
            "is_verified": False,
            "profile_pic_url": "pic.jpg",
            "profile_pic_url_hd": "pic_hd.jpg",
        }

        call_count = 0

        async def _mock_get(path, params=None):
            nonlocal call_count
            call_count += 1
            if "web_profile_info" in path:
                return {"data": {"user": profile_user}}
            elif "friendships" in path and "followers" in path:
                return _paginate_response(
                    [
                        _make_user(1, "alice"),
                        _make_user(2, "bob"),
                    ]
                )
            return {"users": []}

        client._get = _mock_get

        with patch("instagram_mcp_server.scraping.api_client.random.randint", return_value=50):
            with patch.object(client, "_sleep", new_callable=AsyncMock):
                result = await client.scrape_user("testuser", requested={"followers"})

        # Should have followers section with real usernames
        assert "followers" in result["sections"]
        followers_text = result["sections"]["followers"]
        assert "alice" in followers_text
        assert "bob" in followers_text
        assert "Followers: 5000 total" in followers_text

        # Should also have followers_json
        assert "followers_json" in result["sections"]
        followers_json = json.loads(result["sections"]["followers_json"])
        assert len(followers_json) == 2
        assert followers_json[0]["username"] == "alice"

    @pytest.mark.asyncio
    async def test_scrape_user_with_following_section(self):
        """scrape_user with 'following' section calls get_following."""
        client = _make_client()
        client._user_id_cache = {"testuser": "999"}

        profile_user = {
            "username": "testuser",
            "full_name": "Test",
            "biography": "",
            "follower_count": 100,
            "following_count": 3,
            "media_count": 0,
            "is_private": False,
            "is_verified": False,
            "profile_pic_url": "",
            "profile_pic_url_hd": "",
        }

        async def _mock_get(path, params=None):
            if "web_profile_info" in path:
                return {"data": {"user": profile_user}}
            elif "friendships" in path and "following" in path:
                return _paginate_response(
                    [
                        _make_user(10, "charlie"),
                    ]
                )
            return {"users": []}

        client._get = _mock_get

        with patch("instagram_mcp_server.scraping.api_client.random.randint", return_value=50):
            with patch.object(client, "_sleep", new_callable=AsyncMock):
                result = await client.scrape_user("testuser", requested={"following"})

        assert "following" in result["sections"]
        assert "charlie" in result["sections"]["following"]
        assert "Following: 3 total" in result["sections"]["following"]

    @pytest.mark.asyncio
    async def test_scrape_user_has_more_indicator(self):
        """When follower list is truncated, shows '(has more)' indicator."""
        client = _make_client()
        client._user_id_cache = {"testuser": "999"}

        profile_user = {
            "username": "testuser",
            "full_name": "Test",
            "biography": "",
            "follower_count": 10000,
            "following_count": 50,
            "media_count": 0,
            "is_private": False,
            "is_verified": False,
            "profile_pic_url": "",
            "profile_pic_url_hd": "",
        }

        async def _mock_get(path, params=None):
            if "web_profile_info" in path:
                return {"data": {"user": profile_user}}
            elif "friendships" in path:
                # Always return full pages with more available
                return _paginate_response(
                    [_make_user(i, f"u{i}") for i in range(50)],
                    max_id="more_cursor",
                )
            return {"users": []}

        client._get = _mock_get

        with patch("instagram_mcp_server.scraping.api_client.random.randint", return_value=50):
            with patch.object(client, "_sleep", new_callable=AsyncMock):
                result = await client.scrape_user("testuser", requested={"followers"})

        assert "has more" in result["sections"]["followers"]


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Stress-test boundary conditions."""

    @pytest.mark.asyncio
    async def test_user_id_resolution_failure(self):
        """User not found → AuthenticationError propagated."""
        client = _make_client()
        client._get = AsyncMock(return_value={"data": {"user": None}})

        from instagram_mcp_server.core.exceptions import AuthenticationError

        with pytest.raises(AuthenticationError, match="Could not resolve user id"):
            await client.get_followers("nonexistent_user", max_count=10)

    @pytest.mark.asyncio
    async def test_empty_cursor_stops_pagination(self):
        """If next_max_id is empty string (not None), pagination stops."""
        client = _make_client()
        client._user_id_cache = {"testuser": "999"}
        client._get = AsyncMock(return_value={"users": [_make_user(1, "a")], "next_max_id": ""})

        with patch.object(client, "_sleep", new_callable=AsyncMock):
            result = await client.get_followers("testuser", max_count=10)

        assert result["has_more"] is False
        assert result["total"] == 1

    @pytest.mark.asyncio
    async def test_exactly_at_limit_stops(self):
        """When user count exactly equals max_count, pagination stops."""
        client = _make_client()
        client._user_id_cache = {"testuser": "999"}

        users = [_make_user(i, f"u{i}") for i in range(50)]
        client._get = AsyncMock(return_value=_paginate_response(users, max_id="more"))

        with patch.object(client, "_sleep", new_callable=AsyncMock):
            result = await client.get_followers("testuser", max_count=50)

        assert result["total"] == 50
        assert result["has_more"] is True

    @pytest.mark.asyncio
    async def test_max_count_1(self):
        """Single user requested."""
        client = _make_client()
        client._user_id_cache = {"testuser": "999"}
        client._get = AsyncMock(
            return_value=_paginate_response([_make_user(1, "only")], max_id="more")
        )

        with patch.object(client, "_sleep", new_callable=AsyncMock):
            result = await client.get_followers("testuser", max_count=1)

        assert result["total"] == 1
        assert result["users"][0]["username"] == "only"

    @pytest.mark.asyncio
    async def test_pages_fetched_count_accurate(self):
        """pages_fetched matches the number of API calls that returned users."""
        client = _make_client()
        client._user_id_cache = {"testuser": "999"}

        page_count = 0

        async def _mock_get(path, params=None):
            nonlocal page_count
            page_count += 1
            if page_count <= 3:
                return _paginate_response(
                    [_make_user(page_count, f"u{page_count}")],
                    max_id="next",
                )
            return _paginate_response([])

        client._get = _mock_get

        with patch("instagram_mcp_server.scraping.api_client.random.randint", return_value=50):
            with patch.object(client, "_sleep", new_callable=AsyncMock):
                result = await client.get_followers("testuser", max_count=100)

        assert result["pages_fetched"] == 3
        assert result["total"] == 3
