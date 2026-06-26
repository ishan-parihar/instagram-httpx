"""Auth error handling decorator for MCP tools."""

from functools import wraps
from typing import Any, Awaitable, Callable

from instagram_mcp_server.core.exceptions import AuthenticationError
from instagram_mcp_server.dependencies import handle_auth_error
from instagram_mcp_server.error_handler import raise_tool_error


def tool_guard(tool_name: str) -> Callable:
    """Wrap a tool function with standard auth error handling.

    Catches AuthenticationError and triggers re-login, then catches
    all other exceptions and raises them as ToolError.
    """

    def decorator(fn: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        @wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await fn(*args, **kwargs)
            except AuthenticationError as e:
                try:
                    await handle_auth_error(e, kwargs.get("ctx"))
                except Exception as relogin_exc:
                    raise_tool_error(relogin_exc, tool_name)
            except Exception as e:
                raise_tool_error(e, tool_name)

        return wrapper

    return decorator
