"""Tests for AXI CLI wrappers: --list-tools and --tool-info (AXI §8/§9)."""

import json
import sys
import types

# Mock google.genai before importing anything from instagram_mcp_server
# This is needed because google-generativeai is not installed in test env
google_mod = types.ModuleType('google')
genai_mod = types.ModuleType('google.genai')
genai_types = types.ModuleType('google.genai.types')
genai_mod.types = genai_types
google_mod.genai = genai_mod
sys.modules.setdefault('google', google_mod)
sys.modules.setdefault('google.genai', genai_mod)
sys.modules.setdefault('google.genai.types', genai_types)

import pytest  # noqa: E402

from instagram_mcp_server.cli_main import list_tools_and_exit, tool_info_and_exit  # noqa: E402


class TestListTools:
    """Tests for the --list-tools flag (AXI §8 content-first)."""

    def test_list_tools_exits_with_code_zero(self, capsys):
        """list_tools_and_exit should exit with code 0."""
        with pytest.raises(SystemExit) as exc_info:
            list_tools_and_exit()
        assert exc_info.value.code == 0

    def test_list_tools_output_contains_tool_header(self, capsys):
        """Output should contain the TOON-style tools header."""
        with pytest.raises(SystemExit):
            list_tools_and_exit()
        out = capsys.readouterr().out
        assert "tools[16]" in out

    def test_list_tools_output_contains_all_16_tools(self, capsys):
        """All 16 tools should be listed."""
        with pytest.raises(SystemExit):
            list_tools_and_exit()
        out = capsys.readouterr().out

        expected_tools = [
            "ias_get_user_profile",
            "ias_get_user_stories",
            "ias_get_user_highlights",
            "ias_get_media_feed",
            "ias_get_media_detail",
            "ias_get_media_comments",
            "ias_get_user_reels",
            "ias_search_users",
            "ias_get_followers",
            "ias_get_following",
            "ias_send_direct_message",
            "ias_get_direct_messages",
            "ias_create_post_container",
            "ias_publish_media",
            "ias_like_media",
            "ias_comment_on_media",
        ]
        for tool in expected_tools:
            assert tool in out, f"Tool '{tool}' not found in --list-tools output"

    def test_list_tools_output_contains_help_hints(self, capsys):
        """Output should contain AXI §9 help hints."""
        with pytest.raises(SystemExit):
            list_tools_and_exit()
        out = capsys.readouterr().out
        assert "help[" in out
        assert "--tool-info" in out
        assert "--list-tools" not in out or "instagram-httpx-mcp" in out

    def test_list_tools_output_format_is_toon(self, capsys):
        """Output should use TOON-style formatting, not raw JSON."""
        with pytest.raises(SystemExit):
            list_tools_and_exit()
        out = capsys.readouterr().out
        # TOON format uses comma-separated fields, not JSON braces
        assert not out.strip().startswith("{")
        assert not out.strip().startswith("[")


class TestToolInfo:
    """Tests for the --tool-info flag (AXI §9 contextual disclosure)."""

    def test_tool_info_exits_with_code_zero_for_known_tool(self, capsys):
        """tool_info_and_exit should exit with code 0 for a known tool."""
        with pytest.raises(SystemExit) as exc_info:
            tool_info_and_exit("ias_get_user_profile")
        assert exc_info.value.code == 0

    def test_tool_info_outputs_valid_json(self, capsys):
        """Output for a known tool should be valid JSON."""
        with pytest.raises(SystemExit):
            tool_info_and_exit("ias_get_user_profile")
        out = capsys.readouterr().out
        data = json.loads(out)
        assert isinstance(data, dict)

    def test_tool_info_contains_required_fields(self, capsys):
        """Output should contain name, description, parameters, and returns."""
        with pytest.raises(SystemExit):
            tool_info_and_exit("ias_get_user_profile")
        out = capsys.readouterr().out
        data = json.loads(out)
        assert "name" in data
        assert "description" in data
        assert "parameters" in data
        assert "returns" in data

    def test_tool_info_user_profile_has_username_param(self, capsys):
        """ias_get_user_profile should require a username parameter."""
        with pytest.raises(SystemExit):
            tool_info_and_exit("ias_get_user_profile")
        out = capsys.readouterr().out
        data = json.loads(out)
        assert "username" in data["parameters"]

    def test_tool_info_media_feed_has_user_id_param(self, capsys):
        """ias_get_media_feed should require a user_id parameter."""
        with pytest.raises(SystemExit):
            tool_info_and_exit("ias_get_media_feed")
        out = capsys.readouterr().out
        data = json.loads(out)
        assert "user_id" in data["parameters"]

    def test_tool_info_unknown_tool_exits_with_code_2(self, capsys):
        """Unknown tool should exit with code 2 (AXI §6 structured error)."""
        with pytest.raises(SystemExit) as exc_info:
            tool_info_and_exit("nonexistent_tool")
        assert exc_info.value.code == 2

    def test_tool_info_unknown_tool_outputs_error_json(self, capsys):
        """Unknown tool should output structured error JSON."""
        with pytest.raises(SystemExit):
            tool_info_and_exit("nonexistent_tool")
        out = capsys.readouterr().out
        data = json.loads(out)
        assert "error" in data
        assert "nonexistent_tool" in data["error"]

    def test_tool_info_unknown_tool_suggests_valid_tools(self, capsys):
        """Unknown tool error should suggest valid tool names."""
        with pytest.raises(SystemExit):
            tool_info_and_exit("nonexistent_tool")
        out = capsys.readouterr().out
        data = json.loads(out)
        assert "help" in data
        assert "Valid tools" in data["help"]
