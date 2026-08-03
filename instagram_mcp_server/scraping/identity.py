"""Single coherent Chrome wire-identity for the Instagram private API.

Every request surface (API client, CLI status check, browser validate,
media downloader) must present ONE fingerprint bundle — identical User-Agent,
TLS/HTTP2 impersonation, and Client Hints. Presenting one ``sessionid`` under
two different UA+TLS pairings is a bot-detection tell that gets the session
flagged and the cookies invalidated.

``curl_cffi``'s ``chrome131`` impersonation ships a **desktop** Chrome JA3/JA4
fingerprint, so the UA and Client Hints here must be desktop Chrome as well.
A mobile UA paired with the desktop TLS stack is internally inconsistent.
"""

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

IMPERSONATE = "chrome131"


def client_hints() -> dict[str, str]:
    """Client-Hints + Sec-Fetch* headers that a real desktop Chrome 131 sends.

    These are cross-checked against the TLS fingerprint and the User-Agent;
    their absence is itself a bot signal.
    """
    return {
        "sec-ch-ua": '"Not_A Brand";v="24", "Chromium";v="131", "Google Chrome";v="131"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Linux"',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
    }