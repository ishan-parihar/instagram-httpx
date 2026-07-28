"""
Tests for DM trigger system functionality.
"""

import pytest
from pathlib import Path
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from instagram_mcp_server.trigger_system import (
    DMTrigger,
    TriggerExecution,
    TriggerMatchType,
    TriggerStatus,
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
    get_user_trigger_count,
    load_all_triggers,
    save_all_triggers,
    initialize_trigger_system,
    triggers_root_dir,
    trigger_config_path,
    trigger_executions_dir,
    trigger_execution_log_path,
)


@pytest.fixture
def sample_trigger():
    """Create a sample trigger for testing."""
    return DMTrigger(
        trigger_id=f"trigger_{uuid4().hex[:12]}",
        account_id="test_account",
        post_shortcode="ABC123",
        post_url="https://www.instagram.com/p/ABC123/",
        trigger_words=["info", "details"],
        match_type="contains",
        dm_template="Thanks for your interest {username}!",
        status="active",
        created_at="2025-01-01T00:00:00Z",
        updated_at="2025-01-01T00:00:00Z",
        description="Test trigger",
        cooldown_minutes=30,
        max_triggers_per_user=3,
        case_sensitive=False,
    )


@pytest.fixture
def sample_execution():
    """Create a sample trigger execution for testing."""
    return TriggerExecution(
        execution_id=f"exec_{uuid4().hex[:12]}",
        trigger_id="trigger_abc123",
        account_id="test_account",
        post_shortcode="ABC123",
        comment_id="comment_xyz",
        commenter_username="testuser",
        matched_word="info",
        dm_sent=True,
        dm_message_id="msg_123",
        executed_at="2025-01-01T12:00:00Z",
    )


class TestTriggerSystemBasics:
    """Test basic trigger system functionality."""

    def test_initialize_trigger_system(self, tmp_path):
        """Test trigger system initialization."""
        # Override the triggers root dir for testing
        import instagram_mcp_server.trigger_system as ts_module
        original_triggers_dir = ts_module._TRIGGERS_DIR
        
        # Set custom triggers dir
        test_triggers_dir = tmp_path / "test_triggers"
        ts_module._TRIGGERS_DIR = "test_triggers"
        
        try:
            initialize_trigger_system()
            
            assert triggers_root_dir().exists()
            assert trigger_executions_dir().exists()
            assert trigger_config_path().parent.exists()
        finally:
            # Restore original
            ts_module._TRIGGERS_DIR = original_triggers_dir

    def test_create_trigger(self, tmp_path):
        """Test creating a new trigger."""
        import instagram_mcp_server.trigger_system as ts_module
        original_triggers_dir = ts_module._TRIGGERS_DIR
        
        # Set custom triggers dir
        test_triggers_dir = tmp_path / "test_triggers"
        ts_module._TRIGGERS_DIR = "test_triggers"
        
        try:
            trigger = create_trigger(
                account_id="test_account",
                post_shortcode="ABC123",
                post_url="https://www.instagram.com/p/ABC123/",
                trigger_words=["info"],
                dm_template="Thanks {username}!",
                match_type="contains",
                description="Test trigger",
                cooldown_minutes=30,
                max_triggers_per_user=3,
                case_sensitive=False,
            )
            
            assert trigger.trigger_id.startswith("trigger_")
            assert trigger.account_id == "test_account"
            assert trigger.post_shortcode == "ABC123"
            assert trigger.trigger_words == ["info"]
            assert trigger.match_type == "contains"
            assert trigger.dm_template == "Thanks {username}!"
            assert trigger.status == "active"
            assert trigger.description == "Test trigger"
            assert trigger.cooldown_minutes == 30
            assert trigger.max_triggers_per_user == 3
            assert trigger.case_sensitive is False
        finally:
            # Restore original
            ts_module._TRIGGERS_DIR = original_triggers_dir

    def test_get_trigger(self, sample_trigger, tmp_path):
        """Test retrieving a trigger by ID."""
        import instagram_mcp_server.trigger_system as ts_module
        original_triggers_dir = ts_module._TRIGGERS_DIR
        
        # Set custom triggers dir
        test_triggers_dir = tmp_path / "test_triggers"
        ts_module._TRIGGERS_DIR = "test_triggers"
        
        try:
            # Save sample trigger
            save_all_triggers([sample_trigger])
            
            # Retrieve it
            retrieved = get_trigger(sample_trigger.trigger_id)
            
            assert retrieved is not None
            assert retrieved.trigger_id == sample_trigger.trigger_id
            assert retrieved.account_id == sample_trigger.account_id
        finally:
            # Restore original
            ts_module._TRIGGERS_DIR = original_triggers_dir

    def test_get_nonexistent_trigger(self, tmp_path):
        """Test retrieving a non-existent trigger."""
        import instagram_mcp_server.trigger_system as ts_module
        original_triggers_dir = ts_module._TRIGGERS_DIR
        
        # Set custom triggers dir
        test_triggers_dir = tmp_path / "test_triggers"
        ts_module._TRIGGERS_DIR = "test_triggers"
        
        try:
            retrieved = get_trigger("nonexistent_trigger")
            assert retrieved is None
        finally:
            # Restore original
            ts_module._TRIGGERS_DIR = original_triggers_dir

    def test_get_triggers_for_account(self, sample_trigger, tmp_path):
        """Test retrieving triggers for a specific account."""
        import instagram_mcp_server.trigger_system as ts_module
        original_triggers_dir = ts_module._TRIGGERS_DIR
        
        # Set custom triggers dir
        test_triggers_dir = tmp_path / "test_triggers"
        ts_module._TRIGGERS_DIR = "test_triggers"
        
        try:
            # Create triggers for different accounts
            trigger1 = sample_trigger
            trigger2 = DMTrigger(
                trigger_id=f"trigger_{uuid4().hex[:12]}",
                account_id="other_account",
                post_shortcode="XYZ789",
                post_url="https://www.instagram.com/p/XYZ789/",
                trigger_words=["help"],
                match_type="exact",
                dm_template="Help {username}",
                status="active",
                created_at="2025-01-01T00:00:00Z",
                updated_at="2025-01-01T00:00:00Z",
            )
            
            save_all_triggers([trigger1, trigger2])
            
            # Get triggers for test_account
            triggers = get_triggers_for_account("test_account")
            
            assert len(triggers) == 1
            assert triggers[0].account_id == "test_account"
        finally:
            # Restore original
            ts_module._TRIGGERS_DIR = original_triggers_dir

    def test_get_triggers_for_post(self, sample_trigger, tmp_path):
        """Test retrieving triggers for a specific post."""
        import instagram_mcp_server.trigger_system as ts_module
        original_triggers_dir = ts_module._TRIGGERS_DIR
        
        # Set custom triggers dir
        test_triggers_dir = tmp_path / "test_triggers"
        ts_module._TRIGGERS_DIR = "test_triggers"
        
        try:
            # Create triggers for different posts
            trigger1 = sample_trigger
            trigger2 = DMTrigger(
                trigger_id=f"trigger_{uuid4().hex[:12]}",
                account_id="test_account",
                post_shortcode="XYZ789",
                post_url="https://www.instagram.com/p/XYZ789/",
                trigger_words=["help"],
                match_type="exact",
                dm_template="Help {username}",
                status="active",
                created_at="2025-01-01T00:00:00Z",
                updated_at="2025-01-01T00:00:00Z",
            )
            
            save_all_triggers([trigger1, trigger2])
            
            # Get triggers for post ABC123
            triggers = get_triggers_for_post("ABC123")
            
            assert len(triggers) == 1
            assert triggers[0].post_shortcode == "ABC123"
        finally:
            # Restore original
            ts_module._TRIGGERS_DIR = original_triggers_dir

    def test_get_active_triggers(self, sample_trigger, tmp_path):
        """Test retrieving only active triggers."""
        import instagram_mcp_server.trigger_system as ts_module
        original_triggers_dir = ts_module._TRIGGERS_DIR
        
        # Set custom triggers dir
        test_triggers_dir = tmp_path / "test_triggers"
        ts_module._TRIGGERS_DIR = "test_triggers"
        
        try:
            # Create triggers with different statuses
            trigger1 = sample_trigger  # active
            trigger2 = DMTrigger(
                trigger_id=f"trigger_{uuid4().hex[:12]}",
                account_id="test_account",
                post_shortcode="XYZ789",
                post_url="https://www.instagram.com/p/XYZ789/",
                trigger_words=["help"],
                match_type="exact",
                dm_template="Help {username}",
                status="paused",
                created_at="2025-01-01T00:00:00Z",
                updated_at="2025-01-01T00:00:00Z",
            )
            trigger3 = DMTrigger(
                trigger_id=f"trigger_{uuid4().hex[:12]}",
                account_id="test_account",
                post_shortcode="DEF456",
                post_url="https://www.instagram.com/p/DEF456/",
                trigger_words=["support"],
                match_type="exact",
                dm_template="Support {username}",
                status="disabled",
                created_at="2025-01-01T00:00:00Z",
                updated_at="2025-01-01T00:00:00Z",
            )
            
            save_all_triggers([trigger1, trigger2, trigger3])
            
            # Get active triggers
            active_triggers = get_active_triggers()
            
            assert len(active_triggers) == 1
            assert active_triggers[0].status == "active"
        finally:
            # Restore original
            ts_module._TRIGGERS_DIR = original_triggers_dir


class TestTriggerUpdates:
    """Test trigger update operations."""

    def test_update_trigger_words(self, sample_trigger, tmp_path):
        """Test updating trigger words."""
        import instagram_mcp_server.trigger_system as ts_module
        original_triggers_dir = ts_module._TRIGGERS_DIR
        
        # Set custom triggers dir
        test_triggers_dir = tmp_path / "test_triggers"
        ts_module._TRIGGERS_DIR = "test_triggers"
        
        try:
            save_all_triggers([sample_trigger])
            
            updated = update_trigger(
                sample_trigger.trigger_id,
                trigger_words=["new_word", "another_word"]
            )
            
            assert updated is not None
            assert updated.trigger_words == ["new_word", "another_word"]
        finally:
            # Restore original
            ts_module._TRIGGERS_DIR = original_triggers_dir

    def test_update_dm_template(self, sample_trigger, tmp_path):
        """Test updating DM template."""
        import instagram_mcp_server.trigger_system as ts_module
        original_triggers_dir = ts_module._TRIGGERS_DIR
        
        # Set custom triggers dir
        test_triggers_dir = tmp_path / "test_triggers"
        ts_module._TRIGGERS_DIR = "test_triggers"
        
        try:
            save_all_triggers([sample_trigger])
            
            updated = update_trigger(
                sample_trigger.trigger_id,
                dm_template="New template {username}"
            )
            
            assert updated is not None
            assert updated.dm_template == "New template {username}"
        finally:
            # Restore original
            ts_module._TRIGGERS_DIR = original_triggers_dir

    def test_update_trigger_status(self, sample_trigger, tmp_path):
        """Test updating trigger status."""
        import instagram_mcp_server.trigger_system as ts_module
        original_triggers_dir = ts_module._TRIGGERS_DIR
        
        # Set custom triggers dir
        test_triggers_dir = tmp_path / "test_triggers"
        ts_module._TRIGGERS_DIR = "test_triggers"
        
        try:
            save_all_triggers([sample_trigger])
            
            updated = update_trigger(
                sample_trigger.trigger_id,
                status="paused"
            )
            
            assert updated is not None
            assert updated.status == "paused"
        finally:
            # Restore original
            ts_module._TRIGGERS_DIR = original_triggers_dir

    def test_update_nonexistent_trigger(self, tmp_path):
        """Test updating a non-existent trigger."""
        import instagram_mcp_server.trigger_system as ts_module
        original_triggers_dir = ts_module._TRIGGERS_DIR
        
        # Set custom triggers dir
        test_triggers_dir = tmp_path / "test_triggers"
        ts_module._TRIGGERS_DIR = "test_triggers"
        
        try:
            updated = update_trigger("nonexistent_trigger", trigger_words=["new"])
            assert updated is None
        finally:
            # Restore original
            ts_module._TRIGGERS_DIR = original_triggers_dir


class TestTriggerDeletion:
    """Test trigger deletion operations."""

    def test_delete_trigger(self, sample_trigger, tmp_path):
        """Test deleting a trigger."""
        import instagram_mcp_server.trigger_system as ts_module
        original_triggers_dir = ts_module._TRIGGERS_DIR
        
        # Set custom triggers dir
        test_triggers_dir = tmp_path / "test_triggers"
        ts_module._TRIGGERS_DIR = "test_triggers"
        
        try:
            save_all_triggers([sample_trigger])
            
            success = delete_trigger(sample_trigger.trigger_id)
            
            assert success is True
            assert get_trigger(sample_trigger.trigger_id) is None
        finally:
            # Restore original
            ts_module._TRIGGERS_DIR = original_triggers_dir

    def test_delete_nonexistent_trigger(self, tmp_path):
        """Test deleting a non-existent trigger."""
        import instagram_mcp_server.trigger_system as ts_module
        original_triggers_dir = ts_module._TRIGGERS_DIR
        
        # Set custom triggers dir
        test_triggers_dir = tmp_path / "test_triggers"
        ts_module._TRIGGERS_DIR = "test_triggers"
        
        try:
            success = delete_trigger("nonexistent_trigger")
            assert success is False
        finally:
            # Restore original
            ts_module._TRIGGERS_DIR = original_triggers_dir

    def test_pause_trigger(self, sample_trigger, tmp_path):
        """Test pausing a trigger."""
        import instagram_mcp_server.trigger_system as ts_module
        original_triggers_dir = ts_module._TRIGGERS_DIR
        
        # Set custom triggers dir
        test_triggers_dir = tmp_path / "test_triggers"
        ts_module._TRIGGERS_DIR = "test_triggers"
        
        try:
            sample_trigger.status = "active"
            save_all_triggers([sample_trigger])
            
            success = pause_trigger(sample_trigger.trigger_id)
            
            assert success is True
            assert get_trigger(sample_trigger.trigger_id).status == "paused"
        finally:
            # Restore original
            ts_module._TRIGGERS_DIR = original_triggers_dir

    def test_resume_trigger(self, sample_trigger, tmp_path):
        """Test resuming a paused trigger."""
        import instagram_mcp_server.trigger_system as ts_module
        original_triggers_dir = ts_module._TRIGGERS_DIR
        
        # Set custom triggers dir
        test_triggers_dir = tmp_path / "test_triggers"
        ts_module._TRIGGERS_DIR = "test_triggers"
        
        try:
            sample_trigger.status = "paused"
            save_all_triggers([sample_trigger])
            
            success = resume_trigger(sample_trigger.trigger_id)
            
            assert success is True
            assert get_trigger(sample_trigger.trigger_id).status == "active"
        finally:
            # Restore original
            ts_module._TRIGGERS_DIR = original_triggers_dir


class TestTriggerMatching:
    """Test trigger comment matching logic."""

    def test_exact_match(self, sample_trigger, tmp_path):
        """Test exact match type."""
        import instagram_mcp_server.trigger_system as ts_module
        original_triggers_dir = ts_module._TRIGGERS_DIR
        
        # Set custom triggers dir
        test_triggers_dir = tmp_path / "test_triggers"
        ts_module._TRIGGERS_DIR = "test_triggers"
        
        try:
            sample_trigger.match_type = "exact"
            sample_trigger.trigger_words = ["info"]
            sample_trigger.status = "active"
            save_all_triggers([sample_trigger])
            
            # Test exact match
            trigger, matched_word = check_comment_trigger(
                "ABC123", "info", "testuser", "comment123"
            )
            
            assert trigger is not None
            assert matched_word == "info"
        finally:
            # Restore original
            ts_module._TRIGGERS_DIR = original_triggers_dir

    def test_contains_match(self, sample_trigger, tmp_path):
        """Test contains match type."""
        import instagram_mcp_server.trigger_system as ts_module
        original_triggers_dir = ts_module._TRIGGERS_DIR
        
        # Set custom triggers dir
        test_triggers_dir = tmp_path / "test_triggers"
        ts_module._TRIGGERS_DIR = "test_triggers"
        
        try:
            sample_trigger.match_type = "contains"
            sample_trigger.trigger_words = ["info"]
            sample_trigger.status = "active"
            save_all_triggers([sample_trigger])
            
            # Test contains match
            trigger, matched_word = check_comment_trigger(
                "ABC123", "I need more info", "testuser", "comment123"
            )
            
            assert trigger is not None
            assert matched_word == "info"
        finally:
            # Restore original
            ts_module._TRIGGERS_DIR = original_triggers_dir

    def test_starts_with_match(self, sample_trigger, tmp_path):
        """Test starts_with match type."""
        import instagram_mcp_server.trigger_system as ts_module
        original_triggers_dir = ts_module._TRIGGERS_DIR
        
        # Set custom triggers dir
        test_triggers_dir = tmp_path / "test_triggers"
        ts_module._TRIGGERS_DIR = "test_triggers"
        
        try:
            sample_trigger.match_type = "starts_with"
            sample_trigger.trigger_words = ["info"]
            sample_trigger.status = "active"
            save_all_triggers([sample_trigger])
            
            # Test starts_with match
            trigger, matched_word = check_comment_trigger(
                "ABC123", "Info please", "testuser", "comment123"
            )
            
            assert trigger is not None
            assert matched_word == "info"
        finally:
            # Restore original
            ts_module._TRIGGERS_DIR = original_triggers_dir

    def test_ends_with_match(self, sample_trigger, tmp_path):
        """Test ends_with match type."""
        import instagram_mcp_server.trigger_system as ts_module
        original_triggers_dir = ts_module._TRIGGERS_DIR
        
        # Set custom triggers dir
        test_triggers_dir = tmp_path / "test_triggers"
        ts_module._TRIGGERS_DIR = "test_triggers"
        
        try:
            sample_trigger.match_type = "ends_with"
            sample_trigger.trigger_words = ["info"]
            sample_trigger.status = "active"
            save_all_triggers([sample_trigger])
            
            # Test ends_with match
            trigger, matched_word = check_comment_trigger(
                "ABC123", "Send info", "testuser", "comment123"
            )
            
            assert trigger is not None
            assert matched_word == "info"
        finally:
            # Restore original
            ts_module._TRIGGERS_DIR = original_triggers_dir

    def test_regex_match(self, sample_trigger, tmp_path):
        """Test regex match type."""
        import instagram_mcp_server.trigger_system as ts_module
        original_triggers_dir = ts_module._TRIGGERS_DIR
        
        # Set custom triggers dir
        test_triggers_dir = tmp_path / "test_triggers"
        ts_module._TRIGGERS_DIR = "test_triggers"
        
        try:
            sample_trigger.match_type = "regex"
            sample_trigger.trigger_words = [r"\d+"]
            sample_trigger.status = "active"
            save_all_triggers([sample_trigger])
            
            # Test regex match
            trigger, matched_word = check_comment_trigger(
                "ABC123", "test123", "testuser", "comment123"
            )
            
            assert trigger is not None
            assert matched_word == r"\d+"
        finally:
            # Restore original
            ts_module._TRIGGERS_DIR = original_triggers_dir

    def test_case_sensitive_match(self, sample_trigger, tmp_path):
        """Test case-sensitive matching."""
        import instagram_mcp_server.trigger_system as ts_module
        original_triggers_dir = ts_module._TRIGGERS_DIR
        
        # Set custom triggers dir
        test_triggers_dir = tmp_path / "test_triggers"
        ts_module._TRIGGERS_DIR = "test_triggers"
        
        try:
            sample_trigger.match_type = "exact"
            sample_trigger.trigger_words = ["Info"]
            sample_trigger.case_sensitive = True
            sample_trigger.status = "active"
            save_all_triggers([sample_trigger])
            
            # Test case-sensitive match (should match)
            trigger, matched_word = check_comment_trigger(
                "ABC123", "Info", "testuser", "comment123"
            )
            assert trigger is not None
            
            # Test case-sensitive match (should not match)
            trigger, matched_word = check_comment_trigger(
                "ABC123", "info", "testuser", "comment456"
            )
            assert trigger is None
        finally:
            # Restore original
            ts_module._TRIGGERS_DIR = original_triggers_dir

    def test_no_match(self, sample_trigger, tmp_path):
        """Test when comment doesn't match any trigger."""
        import instagram_mcp_server.trigger_system as ts_module
        original_triggers_dir = ts_module._TRIGGERS_DIR
        
        # Set custom triggers dir
        test_triggers_dir = tmp_path / "test_triggers"
        ts_module._TRIGGERS_DIR = "test_triggers"
        
        try:
            sample_trigger.match_type = "contains"
            sample_trigger.trigger_words = ["info"]
            sample_trigger.status = "active"
            save_all_triggers([sample_trigger])
            
            # Test no match
            trigger, matched_word = check_comment_trigger(
                "ABC123", "random text", "testuser", "comment123"
            )
            
            assert trigger is None
            assert matched_word is None
        finally:
            # Restore original
            ts_module._TRIGGERS_DIR = original_triggers_dir


class TestTriggerExecutions:
    """Test trigger execution logging and retrieval."""

    def test_record_trigger_execution(self, sample_trigger, sample_execution, tmp_path):
        """Test recording a trigger execution."""
        import instagram_mcp_server.trigger_system as ts_module
        original_triggers_dir = ts_module._TRIGGERS_DIR
        
        # Set custom triggers dir
        test_triggers_dir = tmp_path / "test_triggers"
        ts_module._TRIGGERS_DIR = "test_triggers"
        
        try:
            sample_trigger.status = "active"
            save_all_triggers([sample_trigger])
            
            execution = record_trigger_execution(
                trigger=sample_trigger,
                comment_id="comment123",
                commenter_username="testuser",
                matched_word="info",
                dm_sent=True,
                dm_message_id="msg123",
            )
            
            assert execution.execution_id.startswith("exec_")
            assert execution.trigger_id == sample_trigger.trigger_id
            assert execution.commenter_username == "testuser"
            assert execution.dm_sent is True
            assert execution.dm_message_id == "msg123"
        finally:
            # Restore original
            ts_module._TRIGGERS_DIR = original_triggers_dir

    def test_get_trigger_executions(self, sample_trigger, sample_execution, tmp_path):
        """Test retrieving trigger executions."""
        import instagram_mcp_server.trigger_system as ts_module
        original_triggers_dir = ts_module._TRIGGERS_DIR
        
        # Set custom triggers dir
        test_triggers_dir = tmp_path / "test_triggers"
        ts_module._TRIGGERS_DIR = "test_triggers"
        
        try:
            sample_trigger.status = "active"
            save_all_triggers([sample_trigger])
            
            # Record multiple executions
            record_trigger_execution(
                trigger=sample_trigger,
                comment_id="comment1",
                commenter_username="user1",
                matched_word="info",
                dm_sent=True,
            )
            record_trigger_execution(
                trigger=sample_trigger,
                comment_id="comment2",
                commenter_username="user2",
                matched_word="info",
                dm_sent=True,
            )
            
            executions = get_trigger_executions(sample_trigger.trigger_id, limit=10)
            
            assert len(executions) == 2
            assert executions[0].commenter_username == "user2"  # Most recent first
        finally:
            # Restore original
            ts_module._TRIGGERS_DIR = original_triggers_dir

    def test_get_user_trigger_count(self, sample_trigger, tmp_path):
        """Test getting trigger count for a specific user."""
        import instagram_mcp_server.trigger_system as ts_module
        original_triggers_dir = ts_module._TRIGGERS_DIR
        
        # Set custom triggers dir
        test_triggers_dir = tmp_path / "test_triggers"
        ts_module._TRIGGERS_DIR = "test_triggers"
        
        try:
            sample_trigger.status = "active"
            save_all_triggers([sample_trigger])
            
            # Record executions for same user
            record_trigger_execution(
                trigger=sample_trigger,
                comment_id="comment1",
                commenter_username="testuser",
                matched_word="info",
                dm_sent=True,
            )
            record_trigger_execution(
                trigger=sample_trigger,
                comment_id="comment2",
                commenter_username="testuser",
                matched_word="info",
                dm_sent=True,
            )
            record_trigger_execution(
                trigger=sample_trigger,
                comment_id="comment3",
                commenter_username="otheruser",
                matched_word="info",
                dm_sent=True,
            )
            
            count = get_user_trigger_count(sample_trigger.trigger_id, "testuser")
            
            assert count == 2
        finally:
            # Restore original
            ts_module._TRIGGERS_DIR = original_triggers_dir

    def test_cooldown_enforcement(self, sample_trigger, tmp_path):
        """Test cooldown period enforcement."""
        import instagram_mcp_server.trigger_system as ts_module
        original_triggers_dir = ts_module._TRIGGERS_DIR
        
        # Set custom triggers dir
        test_triggers_dir = tmp_path / "test_triggers"
        ts_module._TRIGGERS_DIR = "test_triggers"
        
        try:
            sample_trigger.cooldown_minutes = 30
            sample_trigger.status = "active"
            save_all_triggers([sample_trigger])
            
            # Record recent execution
            record_trigger_execution(
                trigger=sample_trigger,
                comment_id="comment1",
                commenter_username="testuser",
                matched_word="info",
                dm_sent=True,
            )
            
            # Try to match again immediately (should be in cooldown)
            trigger, matched_word = check_comment_trigger(
                "ABC123", "info", "testuser", "comment2"
            )
            
            assert trigger is None  # Should not match due to cooldown
        finally:
            # Restore original
            ts_module._TRIGGERS_DIR = original_triggers_dir

    def test_max_triggers_enforcement(self, sample_trigger, tmp_path):
        """Test max triggers per user enforcement."""
        import instagram_mcp_server.trigger_system as ts_module
        original_triggers_dir = ts_module._TRIGGERS_DIR
        
        # Set custom triggers dir
        test_triggers_dir = tmp_path / "test_triggers"
        ts_module._TRIGGERS_DIR = "test_triggers"
        
        try:
            sample_trigger.max_triggers_per_user = 2
            sample_trigger.status = "active"
            save_all_triggers([sample_trigger])
            
            # Record executions up to limit
            record_trigger_execution(
                trigger=sample_trigger,
                comment_id="comment1",
                commenter_username="testuser",
                matched_word="info",
                dm_sent=True,
            )
            record_trigger_execution(
                trigger=sample_trigger,
                comment_id="comment2",
                commenter_username="testuser",
                matched_word="info",
                dm_sent=True,
            )
            
            # Try to match again (should exceed limit)
            trigger, matched_word = check_comment_trigger(
                "ABC123", "info", "testuser", "comment3"
            )
            
            assert trigger is None  # Should not match due to limit
        finally:
            # Restore original
            ts_module._TRIGGERS_DIR = original_triggers_dir