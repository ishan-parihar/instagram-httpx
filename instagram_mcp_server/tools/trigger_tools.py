"""
Comment-based DM automation tools for Instagram MCP Server.

Provides tools for AI agents to set up automated DM responses when users
comment on specific posts with trigger words or phrases.
"""

import logging
from typing import Any

from fastmcp import Context, FastMCP
from fastmcp.dependencies import CurrentContext

from instagram_mcp_server.callbacks import MCPContextProgressCallback
from instagram_mcp_server.constants import TOOL_TIMEOUT_SECONDS
from instagram_mcp_server.dependencies import get_ready_extractor
from instagram_mcp_server.error_handler import raise_tool_error
from instagram_mcp_server.tools._guard import tool_guard
from instagram_mcp_server.trigger_system import (
    create_trigger,
    get_trigger,
    get_triggers_for_account,
    get_triggers_for_post,
    get_active_triggers,
    update_trigger,
    delete_trigger,
    pause_trigger,
    resume_trigger,
    check_comment_trigger,
    record_trigger_execution,
    get_trigger_executions,
    TriggerMatchType,
)

logger = logging.getLogger(__name__)


def register_trigger_tools(mcp: FastMCP) -> None:
    """Register all trigger automation tools with the MCP server."""

    @mcp.tool(
        timeout=TOOL_TIMEOUT_SECONDS,
        title="Create DM Trigger",
        annotations={"destructiveHint": True, "openWorldHint": True},
        tags={"automation", "triggers"},
    )
    async def create_dm_trigger(
        account_id: str,
        post_shortcode: str,
        post_url: str,
        trigger_words: list[str],
        dm_template: str,
        match_type: str = "contains",
        description: str | None = None,
        cooldown_minutes: int = 0,
        max_triggers_per_user: int = 1,
        case_sensitive: bool = False,
        ctx: Context = CurrentContext(),
    ) -> dict[str, Any]:
        """
        Create an automated DM trigger for post comments.
        
        When someone comments on the specified post with a trigger word,
        they will automatically receive a DM based on the template.
        
        Args:
            account_id: Account ID to use for sending DMs
            post_shortcode: Post shortcode (e.g., "Cxyz123")
            post_url: Full post URL
            trigger_words: List of words/phrases that trigger the DM
            dm_template: Message template for the DM (can use {username} placeholder)
            match_type: How to match trigger words (exact, contains, starts_with, ends_with, regex)
            description: Optional description for the trigger
            cooldown_minutes: Minimum minutes between triggers for same user (0 = no cooldown)
            max_triggers_per_user: Maximum times to trigger per user (0 = unlimited)
            case_sensitive: Whether matching should be case sensitive
        
        Returns:
            Created trigger information including trigger ID
        """
        try:
            # Validate match type
            valid_match_types = [e.value for e in TriggerMatchType]
            if match_type not in valid_match_types:
                return {
                    "success": False,
                    "message": f"Invalid match_type. Must be one of: {valid_match_types}",
                }
            
            trigger = create_trigger(
                account_id=account_id,
                post_shortcode=post_shortcode,
                post_url=post_url,
                trigger_words=trigger_words,
                dm_template=dm_template,
                match_type=match_type,
                description=description,
                cooldown_minutes=cooldown_minutes,
                max_triggers_per_user=max_triggers_per_user,
                case_sensitive=case_sensitive,
            )
            
            return {
                "success": True,
                "trigger_id": trigger.trigger_id,
                "account_id": trigger.account_id,
                "post_shortcode": trigger.post_shortcode,
                "trigger_words": trigger.trigger_words,
                "match_type": trigger.match_type,
                "status": trigger.status,
                "message": f"DM trigger created: {trigger.trigger_id}",
            }
        except Exception as e:
            logger.error(f"Failed to create DM trigger: {e}")
            raise_tool_error(e, "create_dm_trigger")

    @mcp.tool(
        timeout=TOOL_TIMEOUT_SECONDS,
        title="List DM Triggers",
        annotations={"readOnlyHint": True, "openWorldHint": True},
        tags={"automation", "triggers"},
    )
    async def list_dm_triggers(
        account_id: str | None = None,
        post_shortcode: str | None = None,
        status: str | None = None,
        ctx: Context = CurrentContext(),
    ) -> dict[str, Any]:
        """
        List DM triggers with optional filtering.
        
        Args:
            account_id: Filter by account ID
            post_shortcode: Filter by post shortcode
            status: Filter by status (active, paused, disabled)
        
        Returns:
            List of triggers matching the filters
        """
        try:
            if account_id:
                triggers = get_triggers_for_account(account_id)
            elif post_shortcode:
                triggers = get_triggers_for_post(post_shortcode)
            else:
                triggers = get_active_triggers() if status == "active" else []
                if not status:
                    # Get all triggers
                    from instagram_mcp_server.trigger_system import load_all_triggers
                    triggers = load_all_triggers()
            
            # Apply status filter if specified
            if status:
                triggers = [t for t in triggers if t.status == status]
            
            return {
                "triggers": [
                    {
                        "trigger_id": t.trigger_id,
                        "account_id": t.account_id,
                        "post_shortcode": t.post_shortcode,
                        "post_url": t.post_url,
                        "trigger_words": t.trigger_words,
                        "match_type": t.match_type,
                        "status": t.status,
                        "created_at": t.created_at,
                        "updated_at": t.updated_at,
                        "last_triggered": t.last_triggered,
                        "trigger_count": t.trigger_count,
                        "description": t.description,
                        "cooldown_minutes": t.cooldown_minutes,
                        "max_triggers_per_user": t.max_triggers_per_user,
                    }
                    for t in triggers
                ],
                "total_triggers": len(triggers),
            }
        except Exception as e:
            logger.error(f"Failed to list DM triggers: {e}")
            raise_tool_error(e, "list_dm_triggers")

    @mcp.tool(
        timeout=TOOL_TIMEOUT_SECONDS,
        title="Get DM Trigger",
        annotations={"readOnlyHint": True, "openWorldHint": True},
        tags={"automation", "triggers"},
    )
    async def get_dm_trigger(
        trigger_id: str,
        ctx: Context = CurrentContext(),
    ) -> dict[str, Any]:
        """
        Get details of a specific DM trigger.
        
        Args:
            trigger_id: The trigger ID to retrieve
        
        Returns:
            Trigger details or error if not found
        """
        try:
            trigger = get_trigger(trigger_id)
            
            if not trigger:
                return {
                    "success": False,
                    "message": f"Trigger {trigger_id} not found",
                }
            
            return {
                "success": True,
                "trigger": {
                    "trigger_id": trigger.trigger_id,
                    "account_id": trigger.account_id,
                    "post_shortcode": trigger.post_shortcode,
                    "post_url": trigger.post_url,
                    "trigger_words": trigger.trigger_words,
                    "match_type": trigger.match_type,
                    "dm_template": trigger.dm_template,
                    "status": trigger.status,
                    "created_at": trigger.created_at,
                    "updated_at": trigger.updated_at,
                    "last_triggered": trigger.last_triggered,
                    "trigger_count": trigger.trigger_count,
                    "description": trigger.description,
                    "cooldown_minutes": trigger.cooldown_minutes,
                    "max_triggers_per_user": trigger.max_triggers_per_user,
                    "case_sensitive": trigger.case_sensitive,
                },
            }
        except Exception as e:
            logger.error(f"Failed to get DM trigger: {e}")
            raise_tool_error(e, "get_dm_trigger")

    @mcp.tool(
        timeout=TOOL_TIMEOUT_SECONDS,
        title="Update DM Trigger",
        annotations={"destructiveHint": True, "openWorldHint": True},
        tags={"automation", "triggers"},
    )
    async def update_dm_trigger(
        trigger_id: str,
        trigger_words: list[str] | None = None,
        dm_template: str | None = None,
        status: str | None = None,
        description: str | None = None,
        cooldown_minutes: int | None = None,
        max_triggers_per_user: int | None = None,
        ctx: Context = CurrentContext(),
    ) -> dict[str, Any]:
        """
        Update an existing DM trigger.
        
        Args:
            trigger_id: The trigger ID to update
            trigger_words: New list of trigger words
            dm_template: New DM message template
            status: New status (active, paused, disabled)
            description: New description
            cooldown_minutes: New cooldown period
            max_triggers_per_user: New max triggers per user
        
        Returns:
            Updated trigger information
        """
        try:
            trigger = update_trigger(
                trigger_id=trigger_id,
                trigger_words=trigger_words,
                dm_template=dm_template,
                status=status,
                description=description,
                cooldown_minutes=cooldown_minutes,
                max_triggers_per_user=max_triggers_per_user,
            )
            
            if not trigger:
                return {
                    "success": False,
                    "message": f"Trigger {trigger_id} not found",
                }
            
            return {
                "success": True,
                "trigger_id": trigger.trigger_id,
                "message": f"Trigger {trigger_id} updated successfully",
            }
        except Exception as e:
            logger.error(f"Failed to update DM trigger: {e}")
            raise_tool_error(e, "update_dm_trigger")

    @mcp.tool(
        timeout=TOOL_TIMEOUT_SECONDS,
        title="Delete DM Trigger",
        annotations={"destructiveHint": True, "openWorldHint": True},
        tags={"automation", "triggers"},
    )
    async def delete_dm_trigger(
        trigger_id: str,
        ctx: Context = CurrentContext(),
    ) -> dict[str, Any]:
        """
        Delete a DM trigger.
        
        Args:
            trigger_id: The trigger ID to delete
        
        Returns:
            Success status
        """
        try:
            success = delete_trigger(trigger_id)
            
            if success:
                return {
                    "success": True,
                    "message": f"Trigger {trigger_id} deleted successfully",
                }
            else:
                return {
                    "success": False,
                    "message": f"Trigger {trigger_id} not found",
                }
        except Exception as e:
            logger.error(f"Failed to delete DM trigger: {e}")
            raise_tool_error(e, "delete_dm_trigger")

    @mcp.tool(
        timeout=TOOL_TIMEOUT_SECONDS,
        title="Pause DM Trigger",
        annotations={"destructiveHint": False, "openWorldHint": True},
        tags={"automation", "triggers"},
    )
    async def pause_dm_trigger(
        trigger_id: str,
        ctx: Context = CurrentContext(),
    ) -> dict[str, Any]:
        """
        Pause a DM trigger (temporarily disable without deleting).
        
        Args:
            trigger_id: The trigger ID to pause
        
        Returns:
            Success status
        """
        try:
            success = pause_trigger(trigger_id)
            
            if success:
                return {
                    "success": True,
                    "message": f"Trigger {trigger_id} paused successfully",
                }
            else:
                return {
                    "success": False,
                    "message": f"Trigger {trigger_id} not found",
                }
        except Exception as e:
            logger.error(f"Failed to pause DM trigger: {e}")
            raise_tool_error(e, "pause_dm_trigger")

    @mcp.tool(
        timeout=TOOL_TIMEOUT_SECONDS,
        title="Resume DM Trigger",
        annotations={"destructiveHint": False, "openWorldHint": True},
        tags={"automation", "triggers"},
    )
    async def resume_dm_trigger(
        trigger_id: str,
        ctx: Context = CurrentContext(),
    ) -> dict[str, Any]:
        """
        Resume a paused DM trigger.
        
        Args:
            trigger_id: The trigger ID to resume
        
        Returns:
            Success status
        """
        try:
            success = resume_trigger(trigger_id)
            
            if success:
                return {
                    "success": True,
                    "message": f"Trigger {trigger_id} resumed successfully",
                }
            else:
                return {
                    "success": False,
                    "message": f"Trigger {trigger_id} not found",
                }
        except Exception as e:
            logger.error(f"Failed to resume DM trigger: {e}")
            raise_tool_error(e, "resume_dm_trigger")

    @mcp.tool(
        timeout=TOOL_TIMEOUT_SECONDS,
        title="Check Comment for Triggers",
        annotations={"readOnlyHint": True, "openWorldHint": True},
        tags={"automation", "triggers"},
    )
    async def check_comment_for_triggers(
        post_shortcode: str,
        comment_text: str,
        commenter_username: str,
        comment_id: str,
        ctx: Context = CurrentContext(),
    ) -> dict[str, Any]:
        """
        Check if a comment matches any active triggers for the post.
        
        This is the main trigger evaluation function for automation workflows.
        
        Args:
            post_shortcode: Post shortcode to check triggers for
            comment_text: The comment text to evaluate
            commenter_username: Username of the commenter
            comment_id: ID of the comment
        
        Returns:
            Match result with trigger info and matched word if found
        """
        try:
            trigger, matched_word = check_comment_trigger(
                post_shortcode=post_shortcode,
                comment_text=comment_text,
                commenter_username=commenter_username,
                comment_id=comment_id,
            )
            
            if trigger:
                return {
                    "matched": True,
                    "trigger_id": trigger.trigger_id,
                    "matched_word": matched_word,
                    "account_id": trigger.account_id,
                    "dm_template": trigger.dm_template,
                    "message": f"Comment matched trigger {trigger.trigger_id}",
                }
            else:
                return {
                    "matched": False,
                    "message": "No trigger matched for this comment",
                }
        except Exception as e:
            logger.error(f"Failed to check comment for triggers: {e}")
            raise_tool_error(e, "check_comment_for_triggers")

    @mcp.tool(
        timeout=TOOL_TIMEOUT_SECONDS,
        title="Execute Trigger DM",
        annotations={"destructiveHint": True, "openWorldHint": True},
        tags={"automation", "triggers"},
    )
    @tool_guard("execute_trigger_dm")
    async def execute_trigger_dm(
        trigger_id: str,
        commenter_username: str,
        comment_id: str,
        matched_word: str,
        account_id: str | None = None,
        ctx: Context = CurrentContext(),
    ) -> dict[str, Any]:
        """
        Execute the DM action for a matched trigger.
        
        This sends the actual DM to the user and records the execution.
        
        Args:
            trigger_id: The trigger that was matched
            commenter_username: Username to send DM to
            comment_id: ID of the comment that triggered
            matched_word: The word that matched the trigger
            account_id: Override account ID (uses trigger's account if not provided)
        
        Returns:
            Execution result with DM status
        """
        try:
            trigger = get_trigger(trigger_id)
            if not trigger:
                return {
                    "success": False,
                    "message": f"Trigger {trigger_id} not found",
                }
            
            # Use trigger's account_id if not overridden
            target_account_id = account_id or trigger.account_id
            
            # Get extractor for the account
            extractor = await get_ready_extractor(ctx, tool_name="execute_trigger_dm", account_id=target_account_id)
            
            # Prepare DM message (replace {username} placeholder)
            dm_message = trigger.dm_template.replace("{username}", commenter_username)
            
            # Send DM
            cb = MCPContextProgressCallback(ctx)
            await cb.on_progress(f"Sending DM to @{commenter_username}", 0)
            
            result = await extractor.send_dm(commenter_username, dm_message)
            
            await cb.on_progress("Complete", 100)
            
            # Record execution
            dm_sent = result.get("sent", False)
            dm_message_id = result.get("message_id") if dm_sent else None
            
            record_trigger_execution(
                trigger=trigger,
                comment_id=comment_id,
                commenter_username=commenter_username,
                matched_word=matched_word,
                dm_sent=dm_sent,
                dm_message_id=dm_message_id,
                error_message=result.get("error") if not dm_sent else None,
            )
            
            return {
                "success": dm_sent,
                "dm_sent": dm_sent,
                "dm_message_id": dm_message_id,
                "trigger_id": trigger_id,
                "commenter_username": commenter_username,
                "message": f"DM {'sent successfully' if dm_sent else 'failed'}",
            }
        except Exception as e:
            logger.error(f"Failed to execute trigger DM: {e}")
            raise_tool_error(e, "execute_trigger_dm")

    @mcp.tool(
        timeout=TOOL_TIMEOUT_SECONDS,
        title="Get Trigger Executions",
        annotations={"readOnlyHint": True, "openWorldHint": True},
        tags={"automation", "triggers"},
    )
    async def get_trigger_executions_log(
        trigger_id: str,
        limit: int = 100,
        ctx: Context = CurrentContext(),
    ) -> dict[str, Any]:
        """
        Get execution history for a specific trigger.
        
        Useful for monitoring trigger performance and debugging.
        
        Args:
            trigger_id: The trigger ID to get executions for
            limit: Maximum number of executions to return (default 100)
        
        Returns:
            List of trigger executions with timestamps and results
        """
        try:
            executions = get_trigger_executions(trigger_id, limit=limit)
            
            return {
                "trigger_id": trigger_id,
                "executions": [
                    {
                        "execution_id": e.execution_id,
                        "comment_id": e.comment_id,
                        "commenter_username": e.commenter_username,
                        "matched_word": e.matched_word,
                        "dm_sent": e.dm_sent,
                        "dm_message_id": e.dm_message_id,
                        "error_message": e.error_message,
                        "executed_at": e.executed_at,
                    }
                    for e in executions
                ],
                "total_executions": len(executions),
            }
        except Exception as e:
            logger.error(f"Failed to get trigger executions: {e}")
            raise_tool_error(e, "get_trigger_executions_log")