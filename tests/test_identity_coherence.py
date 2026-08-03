"""One sessionid must never be presented under two different UA/TLS pairings.

Regression test for the bot-detection root cause: the API client, the CLI
status check, the browser validator, and the media downloader each built
their own request headers, which meant the same cookie jar was replayed with
a mobile UA + desktop TLS, a desktop Chrome 134 UA, and plain httpx — a
fingerprint inconsistency that gets sessions flagged and invalidated.
"""

from instagram_mcp_server.scraping import api_client, identity
from instagram_mcp_server.drivers import browser as browser_driver
from instagram_mcp_server.media import downloader

REQUIRED_HINTS = {
    "sec-ch-ua",
    "sec-ch-ua-mobile",
    "sec-ch-ua-platform",
    "Sec-Fetch-Dest",
    "Sec-Fetch-Mode",
    "Sec-Fetch-Site",
}


def test_identity_is_desktop_coherent():
    """UA + TLS impersonation + Client Hints must describe one desktop Chrome."""
    assert identity.IMPERSONATE == "chrome131"
    assert "Mobile" not in identity.USER_AGENT
    hints = identity.client_hints()
    assert set(hints) == REQUIRED_HINTS
    assert hints["sec-ch-ua-mobile"] == "?0"
    assert '"Google Chrome";v="131"' in hints["sec-ch-ua"]
    assert "Chrome/131" in identity.USER_AGENT


def test_api_client_defaults_to_shared_identity():
    """Default client must use the shared bundle, not a private UA."""
    assert api_client._IMPERSONATE == identity.IMPERSONATE
    assert api_client._SHARED_UA == identity.USER_AGENT
    assert api_client._client_hints() == identity.client_hints()


def test_no_stale_mobile_fingerprint_in_module():
    assert not hasattr(api_client, "MOBILE_UA")
    assert not hasattr(api_client, "DESKTOP_UA")


def test_validate_and_download_share_bundle():
    assert browser_driver.identity is identity
    assert downloader.identity is identity