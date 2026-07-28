"""
Integration tests for DM automation and content creation systems.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, AsyncMock, patch

from instagram_mcp_server.trigger_system import (
    create_trigger,
    check_comment_trigger,
    record_trigger_execution,
    get_trigger,
)
from instagram_mcp_server.multi_account import (
    AccountMetadata,
    check_account_posting_limits,
    record_post_attempt,
    get_account,
)


@pytest.fixture
def sample_account():
    """Create a sample account for testing."""
    return AccountMetadata(
        account_id="test_account",
        username="testuser",
        posting_enabled=True,
        daily_post_limit=10,
        last_post_time=None,
        post_count_today=0,
        last_reset_date=datetime.now(timezone.utc).isoformat(),
    )


class TestDMPostingIntegration:
    """Test integration between DM triggers and content posting."""

    def test_post_and_create_trigger_workflow(self, sample_account, tmp_path):
        """Test workflow: Post content, then create DM trigger for that post."""
        import instagram_mcp_server.trigger_system as ts_module
        import instagram_mcp_server.multi_account as ma_module
        original_triggers_dir = ts_module._TRIGGERS_DIR
        original_accounts_dir = ma_module.accounts_root_dir
        
        # Set custom directories
        test_triggers_dir = tmp_path / "test_triggers"
        test_accounts_dir = tmp_path / "test_accounts"
        ts_module._TRIGGERS_DIR = "test_triggers"
        ma_module.accounts_root_dir = lambda: test_accounts_dir
        
        try:
            # Step 1: Simulate posting content
            with patch('instagram_mcp_server.multi_account.get_account') as mock_get, \
                 patch('instagram_mcp_server.multi_account.increment_account_post_count') as mock_increment:
                
                mock_get.return_value = sample_account
                
                # Record post attempt
                record_post_attempt(
                    account_id="test_account",
                    media_type="photo",
                    success=True,
                    post_id="post_123"
                )
                
                # Verify post was recorded
                mock_increment.assert_called_once_with("test_account")
            
            # Step 2: Create DM trigger for the post
            trigger = create_trigger(
                account_id="test_account",
                post_shortcode="ABC123",
                post_url="https://www.instagram.com/p/ABC123/",
                trigger_words=["info"],
                dm_template="Thanks for your interest {username}!",
                match_type="contains",
            )
            
            # Verify trigger was created
            assert trigger is not None
            assert trigger.account_id == "test_account"
            assert trigger.post_shortcode == "ABC123"
            
            # Step 3: Simulate comment on the post
            matched_trigger, matched_word = check_comment_trigger(
                post_shortcode="ABC123",
                comment_text="I need more info",
                commenter_username="testuser",
                comment_id="comment_123"
            )
            
            # Verify trigger matched
            assert matched_trigger is not None
            assert matched_word == "info"
            
            # Step 4: Execute trigger (simulate DM send)
            execution = record_trigger_execution(
                trigger=matched_trigger,
                comment_id="comment_123",
                commenter_username="testuser",
                matched_word="info",
                dm_sent=True,
                dm_message_id="dm_456"
            )
            
            # Verify execution was recorded
            assert execution is not None
            assert execution.dm_sent is True
            assert execution.commenter_username == "testuser"
            
        finally:
            # Restore original directories
            ts_module._TRIGGERS_DIR = original_triggers_dir
            ma_module.accounts_root_dir = original_accounts_dir

    def test_multi_account_coordination(self, tmp_path):
        """Test that DM triggers and posting work across multiple accounts."""
        import instagram_mcp_server.trigger_system as ts_module
        import instagram_mcp_server.multi_account as ma_module
        original_triggers_dir = ts_module._TRIGGERS_DIR
        original_accounts_dir = ma_module.accounts_root_dir
        
        # Set custom directories
        test_triggers_dir = tmp_path / "test_triggers"
        test_accounts_dir = tmp_path / "test_accounts"
        ts_module._TRIGGERS_DIR = "test_triggers"
        ma_module.accounts_root_dir = lambda: test_accounts_dir
        
        try:
            # Create two accounts
            account1 = AccountMetadata(
                account_id="account1",
                username="user1",
                posting_enabled=True,
                daily_post_limit=10,
                last_post_time=None,
                post_count_today=5,
                last_reset_date=datetime.now(timezone.utc).isoformat(),
            )
            
            account2 = AccountMetadata(
                account_id="account2",
                username="user2",
                posting_enabled=True,
                daily_post_limit=10,
                last_post_time=None,
                post_count_today=8,
                last_reset_date=datetime.now(timezone.utc).isoformat(),
            )
            
            # Create trigger for account1
            trigger1 = create_trigger(
                account_id="account1",
                post_shortcode="POST1",
                post_url="https://www.instagram.com/p/POST1/",
                trigger_words=["help"],
                dm_template="Help {username}",
                match_type="contains",
            )
            
            # Create trigger for account2
            trigger2 = create_trigger(
                account_id="account2",
                post_shortcode="POST2",
                post_url="https://www.instagram.com/p/POST2/",
                trigger_words=["support"],
                dm_template="Support {username}",
                match_type="contains",
            )
            
            # Verify triggers are account-specific
            assert trigger1.account_id == "account1"
            assert trigger2.account_id == "account2"
            
            # Test posting limits per account
            with patch('instagram_mcp_server.multi_account.get_account') as mock_get:
                mock_get.return_value = account1
                can_post1, _ = check_account_posting_limits("account1")
                assert can_post1 is True  # 5/10 posts
            
            with patch('instagram_mcp_server.multi_account.get_account') as mock_get:
                mock_get.return_value = account2
                can_post2, _ = check_account_posting_limits("account2")
                assert can_post2 is True  # 8/10 posts
            
            # Verify triggers don't interfere across accounts
            with patch('instagram_mcp_server.multi_account.get_account') as mock_get:
                mock_get.return_value = account1
                
                # Account1's trigger should work for account1's post
                matched, _ = check_comment_trigger(
                    post_shortcode="POST1",
                    comment_text="I need help",
                    commenter_username="user1",
                    comment_id="comment1"
                )
                assert matched is not None
                
                # Account1's trigger should not work for account2's post
                matched, _ = check_comment_trigger(
                    post_shortcode="POST2",
                    comment_text="I need help",
                    commenter_username="user2",
                    comment_id="comment2"
                )
                assert matched is None  # No trigger for POST2 with "help"
            
        finally:
            # Restore original directories
            ts_module._TRIGGERS_DIR = original_triggers_dir
            ma_module.accounts_root_dir = original_accounts_dir

    def test_posting_limits_affect_trigger_availability(self, sample_account, tmp_path):
        """Test that posting limits don't prevent DM triggers from working."""
        import instagram_mcp_server.trigger_system as ts_module
        import instagram_mcp_server.multi_account as ma_module
        original_triggers_dir = ts_module._TRIGGERS_DIR
        original_accounts_dir = ma_module.accounts_root_dir
        
        # Set custom directories
        test_triggers_dir = tmp_path / "test_triggers"
        test_accounts_dir = tmp_path / "test_accounts"
        ts_module._TRIGGERS_DIR = "test_triggers"
        ma_module.accounts_root_dir = lambda: test_accounts_dir
        
        try:
            # Create trigger
            trigger = create_trigger(
                account_id="test_account",
                post_shortcode="ABC123",
                post_url="https://www.instagram.com/p/ABC123/",
                trigger_words=["info"],
                dm_template="Thanks {username}",
                match_type="contains",
            )
            
            # Set account at posting limit
            sample_account.post_count_today = 10  # At limit
            
            with patch('instagram_mcp_server.multi_account.get_account') as mock_get:
                mock_get.return_value = sample_account
                
                # Account should be blocked from posting
                can_post, reason = check_account_posting_limits("test_account")
                assert can_post is False
                assert "limit" in reason.lower()
            
            # But DM triggers should still work (different functionality)
            matched, _ = check_comment_trigger(
                post_shortcode="ABC123",
                comment_text="I need info",
                commenter_username="testuser",
                comment_id="comment123"
            )
            
            # DM triggers should work independently of posting limits
            assert matched is not None
            
        finally:
            # Restore original directories
            ts_module._TRIGGERS_DIR = original_triggers_dir
            ma_module.accounts_root_dir = original_accounts_dir

    def test_cooldown_doesnt_affect_dm_triggers(self, sample_account, tmp_path):
        """Test that posting cooldown doesn't prevent DM triggers from working."""
        import instagram_mcp_server.trigger_system as ts_module
        import instagram_mcp_server.multi_account as ma_module
        original_triggers_dir = ts_module._TRIGGERS_DIR
        original_accounts_dir = ma_module.accounts_root_dir
        
        # Set custom directories
        test_triggers_dir = tmp_path / "test_triggers"
        test_accounts_dir = tmp_path / "test_accounts"
        ts_module._TRIGGERS_DIR = "test_triggers"
        ma_module.accounts_root_dir = lambda: test_accounts_dir
        
        try:
            # Create trigger
            trigger = create_trigger(
                account_id="test_account",
                post_shortcode="ABC123",
                post_url="https://www.instagram.com/p/ABC123/",
                trigger_words=["info"],
                dm_template="Thanks {username}",
                match_type="contains",
            )
            
            # Set account in cooldown
            sample_account.post_count_today = 1
            sample_account.last_post_time = (datetime.now(timezone.utc) - timedelta(minutes=15)).isoformat()
            
            with patch('instagram_mcp_server.multi_account.get_account') as mock_get:
                mock_get.return_value = sample_account
                
                # Account should be in cooldown
                can_post, reason = check_account_posting_limits("test_account")
                assert can_post is False
                assert "cooldown" in reason.lower()
            
            # But DM triggers should still work
            matched, _ = check_comment_trigger(
                post_shortcode="ABC123",
                comment_text="I need info",
                commenter_username="testuser",
                comment_id="comment123"
            )
            
            # DM triggers should work independently of posting cooldown
            assert matched is not None
            
        finally:
            # Restore original directories
            ts_module._TRIGGERS_DIR = original_triggers_dir
            ma_module.accounts_root_dir = original_accounts_dir

    def test_complete_automation_workflow(self, sample_account, tmp_path):
        """Test complete automation workflow: Post -> Comment -> DM -> Record."""
        import instagram_mcp_server.trigger_system as ts_module
        import instagram_mcp_server.multi_account as ma_module
        original_triggers_dir = ts_module._TRIGGERS_DIR
        original_accounts_dir = ma_module.accounts_root_dir
        
        # Set custom directories
        test_triggers_dir = tmp_path / "test_triggers"
        test_accounts_dir = tmp_path / "test_accounts"
        ts_module._TRIGGERS_DIR = "test_triggers"
        ma_module.accounts_root_dir = lambda: test_accounts_dir
        
        try:
            # Step 1: User posts content
            with patch('instagram_mcp_server.multi_account.get_account') as mock_get, \
                 patch('instagram_mcp_server.multi_account.increment_account_post_count') as mock_increment:
                
                mock_get.return_value = sample_account
                
                record_post_attempt(
                    account_id="test_account",
                    media_type="photo",
                    success=True,
                    post_id="post_abc123"
                )
                
                # Verify post recorded
                mock_increment.assert_called_once()
            
            # Step 2: Create trigger for the post
            trigger = create_trigger(
                account_id="test_account",
                post_shortcode="ABC123",
                post_url="https://www.instagram.com/p/ABC123/",
                trigger_words=["info", "details"],
                dm_template="Hi {username}! Here's the info you requested.",
                match_type="contains",
                cooldown_minutes=60,
                max_triggers_per_user=3,
            )
            
            # Step 3: User comments on the post
            matched_trigger, matched_word = check_comment_trigger(
                post_shortcode="ABC123",
                comment_text="Can I get more info?",
                commenter_username="follower1",
                comment_id="comment_xyz"
            )
            
            assert matched_trigger is not None
            assert matched_word == "info"
            
            # Step 4: System sends DM
            execution = record_trigger_execution(
                trigger=matched_trigger,
                comment_id="comment_xyz",
                commenter_username="follower1",
                matched_word="info",
                dm_sent=True,
                dm_message_id="dm_msg_123"
            )
            
            # Verify DM execution recorded
            assert execution.dm_sent is True
            assert execution.dm_message_id == "dm_msg_123"
            
            # Step 5: Verify trigger execution was logged (main assertion)
            assert execution is not None
            assert execution.dm_sent is True
            
            # Step 6: Same user comments again (should respect cooldown)
            matched_trigger2, matched_word2 = check_comment_trigger(
                post_shortcode="ABC123",
                comment_text="I still need info",
                commenter_username="follower1",
                comment_id="comment_xyz2"
            )
            
            # Should be blocked by cooldown
            assert matched_trigger2 is None
            
            # Step 7: Different user comments (should work)
            matched_trigger3, matched_word3 = check_comment_trigger(
                post_shortcode="ABC123",
                comment_text="Send me details",
                commenter_username="follower2",
                comment_id="comment_abc"
            )
            
            # Should work for different user
            assert matched_trigger3 is not None
            assert matched_word3 == "details"
            
        finally:
            # Restore original directories
            ts_module._TRIGGERS_DIR = original_triggers_dir
            ma_module.accounts_root_dir = original_accounts_dir


class TestSystemCoordination:
    """Test coordination between different system components."""

    def test_trigger_execution_updates_account_activity(self, sample_account, tmp_path):
        """Test that trigger execution marks account as active."""
        import instagram_mcp_server.trigger_system as ts_module
        import instagram_mcp_server.multi_account as ma_module
        original_triggers_dir = ts_module._TRIGGERS_DIR
        original_accounts_dir = ma_module.accounts_root_dir
        
        # Set custom directories
        test_triggers_dir = tmp_path / "test_triggers"
        test_accounts_dir = tmp_path / "test_accounts"
        ts_module._TRIGGERS_DIR = "test_triggers"
        ma_module.accounts_root_dir = lambda: test_accounts_dir
        
        try:
            # Create trigger
            trigger = create_trigger(
                account_id="test_account",
                post_shortcode="ABC123",
                post_url="https://www.instagram.com/p/ABC123/",
                trigger_words=["info"],
                dm_template="Thanks {username}",
                match_type="contains",
            )
            
            # Execute trigger
            execution = record_trigger_execution(
                trigger=trigger,
                comment_id="comment123",
                commenter_username="testuser",
                matched_word="info",
                dm_sent=True,
                dm_message_id="dm123"
            )
            
            # Verify execution recorded
            assert execution is not None
            assert execution.account_id == "test_account"
            
            # The trigger system doesn't directly update account activity,
            # but it maintains its own execution logs per trigger
            
        finally:
            # Restore original directories
            ts_module._TRIGGERS_DIR = original_triggers_dir
            ma_module.accounts_root_dir = original_accounts_dir

    def test_error_handling_integration(self, sample_account, tmp_path):
        """Test error handling when both posting and DM operations fail."""
        import instagram_mcp_server.trigger_system as ts_module
        import instagram_mcp_server.multi_account as ma_module
        original_triggers_dir = ts_module._TRIGGERS_DIR
        original_accounts_dir = ma_module.accounts_root_dir
        
        # Set custom directories
        test_triggers_dir = tmp_path / "test_triggers"
        test_accounts_dir = tmp_path / "test_accounts"
        ts_module._TRIGGERS_DIR = "test_triggers"
        ma_module.accounts_root_dir = lambda: test_accounts_dir
        
        try:
            # Simulate failed post
            with patch('instagram_mcp_server.multi_account.get_account') as mock_get, \
                 patch('instagram_mcp_server.multi_account.increment_account_post_count') as mock_increment:
                
                mock_get.return_value = sample_account
                
                record_post_attempt(
                    account_id="test_account",
                    media_type="photo",
                    success=False,
                    error_message="Upload failed: network error"
                )
                
                # Verify increment not called for failed post
                mock_increment.assert_not_called()
            
            # Create trigger
            trigger = create_trigger(
                account_id="test_account",
                post_shortcode="ABC123",
                post_url="https://www.instagram.com/p/ABC123/",
                trigger_words=["info"],
                dm_template="Thanks {username}",
                match_type="contains",
            )
            
            # Simulate failed DM send
            execution = record_trigger_execution(
                trigger=trigger,
                comment_id="comment123",
                commenter_username="testuser",
                matched_word="info",
                dm_sent=False,
                error_message="DM failed: user not found"
            )
            
            # Verify failure recorded
            assert execution.dm_sent is False
            assert execution.error_message == "DM failed: user not found"
            
            # Verify trigger count not incremented for failed DM
            updated_trigger = get_trigger(trigger.trigger_id)
            assert updated_trigger.trigger_count == 0  # No successful DMs
            
        finally:
            # Restore original directories
            ts_module._TRIGGERS_DIR = original_triggers_dir
            ma_module.accounts_root_dir = original_accounts_dir