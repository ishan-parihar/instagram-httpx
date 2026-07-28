# DM Automation Comprehensive Testing Plan

## Test Scope
This plan covers full-scope testing of Instagram DM automation features including trigger management, message sending, and integration testing.

## Test Environment Setup
- **Required**: Valid Instagram account with session cookies
- **Test Account**: Dedicated test account (to avoid affecting production)
- **Test Posts**: Create test posts for trigger setup
- **Test Users**: Coordinate with test users for DM interactions

## Test Categories

### 1. Trigger Management Tests

#### 1.1 Create DM Trigger
**Test Cases:**
- **TC-DM-001**: Create basic trigger with single trigger word
  - Input: account_id, post_shortcode, post_url, trigger_words=["info"], dm_template="Thanks for your interest {username}!"
  - Expected: Trigger created successfully, trigger_id returned
  - Validation: Trigger appears in list_dm_triggers

- **TC-DM-002**: Create trigger with multiple trigger words
  - Input: trigger_words=["info", "details", "more"]
  - Expected: Trigger created with all words stored
  - Validation: All trigger words preserved in trigger details

- **TC-DM-003**: Create trigger with different match types
  - Test each match_type: "exact", "contains", "starts_with", "ends_with", "regex"
  - Expected: Each match type accepted and stored correctly
  - Validation: Match type preserved in trigger configuration

- **TC-DM-004**: Create trigger with cooldown period
  - Input: cooldown_minutes=30
  - Expected: Trigger created with cooldown configuration
  - Validation: Cooldown settings applied in execution

- **TC-DM-005**: Create trigger with max triggers per user limit
  - Input: max_triggers_per_user=3
  - Expected: Trigger created with limit configuration
  - Validation: Limit enforced during execution

- **TC-DM-006**: Create trigger with case-sensitive matching
  - Input: case_sensitive=True
  - Expected: Trigger created with case sensitivity enabled
  - Validation: Case sensitivity applied in matching

- **TC-DM-007**: Create trigger with description
  - Input: description="Test trigger for automation"
  - Expected: Trigger created with description
  - Validation: Description preserved in trigger details

- **TC-DM-008**: Invalid match type handling
  - Input: match_type="invalid_type"
  - Expected: Error returned, no trigger created
  - Validation: Appropriate error message

- **TC-DM-009**: Missing required parameters
  - Test missing: account_id, post_shortcode, trigger_words, dm_template
  - Expected: Error returned for each missing parameter
  - Validation: Proper error handling

#### 1.2 List DM Triggers
**Test Cases:**
- **TC-DM-010**: List all triggers (no filters)
  - Input: No parameters
  - Expected: All triggers returned
  - Validation: Count matches total triggers

- **TC-DM-011**: Filter by account_id
  - Input: account_id="test_account"
  - Expected: Only triggers for specified account
  - Validation: Filter applied correctly

- **TC-DM-012**: Filter by post_shortcode
  - Input: post_shortcode="ABC123"
  - Expected: Only triggers for specified post
  - Validation: Post-specific filtering works

- **TC-DM-013**: Filter by status
  - Input: status="active"
  - Expected: Only active triggers returned
  - Validation: Status filtering works for all statuses

- **TC-DM-014**: Combined filters
  - Input: account_id + status
  - Expected: Triggers matching both criteria
  - Validation: Multiple filters work together

#### 1.3 Get DM Trigger
**Test Cases:**
- **TC-DM-015**: Get existing trigger by ID
  - Input: Valid trigger_id
  - Expected: Complete trigger details returned
  - Validation: All fields present and correct

- **TC-DM-016**: Get non-existent trigger
  - Input: Invalid trigger_id
  - Expected: Error returned
  - Validation: Appropriate error message

#### 1.4 Update DM Trigger
**Test Cases:**
- **TC-DM-017**: Update trigger words
  - Input: trigger_words=["new_word"]
  - Expected: Trigger words updated
  - Validation: New words reflected in trigger details

- **TC-DM-018**: Update DM template
  - Input: dm_template="New template {username}"
  - Expected: Template updated
  - Validation: Template changed correctly

- **TC-DM-019**: Update trigger status
  - Input: status="paused"
  - Expected: Status changed to paused
  - Validation: Status update reflected

- **TC-DM-020**: Update cooldown period
  - Input: cooldown_minutes=60
  - Expected: Cooldown updated
  - Validation: New cooldown applied

- **TC-DM-021**: Update max triggers per user
  - Input: max_triggers_per_user=5
  - Expected: Limit updated
  - Validation: New limit enforced

- **TC-DM-022**: Update description
  - Input: description="Updated description"
  - Expected: Description changed
  - Validation: Description updated correctly

- **TC-DM-023**: Update non-existent trigger
  - Input: Invalid trigger_id
  - Expected: Error returned
  - Validation: Appropriate error message

#### 1.5 Delete DM Trigger
**Test Cases:**
- **TC-DM-024**: Delete existing trigger
  - Input: Valid trigger_id
  - Expected: Trigger deleted successfully
  - Validation: Trigger no longer appears in list

- **TC-DM-025**: Delete non-existent trigger
  - Input: Invalid trigger_id
  - Expected: Error returned
  - Validation: Appropriate error message

#### 1.6 Pause/Resume DM Trigger
**Test Cases:**
- **TC-DM-026**: Pause active trigger
  - Input: Valid trigger_id (active status)
  - Expected: Trigger paused successfully
  - Validation: Status changed to "paused"

- **TC-DM-027**: Resume paused trigger
  - Input: Valid trigger_id (paused status)
  - Expected: Trigger resumed successfully
  - Validation: Status changed to "active"

- **TC-DM-028**: Pause already paused trigger
  - Input: Already paused trigger_id
  - Expected: Success (idempotent)
  - Validation: No errors, status remains paused

- **TC-DM-029**: Resume already active trigger
  - Input: Already active trigger_id
  - Expected: Success (idempotent)
  - Validation: No errors, status remains active

### 2. Trigger Execution Tests

#### 2.1 Check Comment for Triggers
**Test Cases:**
- **TC-DM-030**: Comment matches exact trigger
  - Input: comment_text="info", trigger with exact match
  - Expected: Match returned with trigger details
  - Validation: Correct trigger and matched word

- **TC-DM-031**: Comment contains trigger word
  - Input: comment_text="I need more info", trigger with contains match
  - Expected: Match returned
  - Validation: Contains matching works

- **TC-DM-032**: Comment starts with trigger word
  - Input: comment_text="Info please", trigger with starts_with match
  - Expected: Match returned
  - Validation: Starts with matching works

- **TC-DM-033**: Comment ends with trigger word
  - Input: comment_text="Send info", trigger with ends_with match
  - Expected: Match returned
  - Validation: Ends with matching works

- **TC-DM-034**: Comment matches regex pattern
  - Input: comment_text="test123", trigger with regex "\d+"
  - Expected: Match returned
  - Validation: Regex matching works

- **TC-DM-035**: Comment doesn't match any trigger
  - Input: comment_text="random text"
  - Expected: No match returned
  - Validation: Appropriate "no match" response

- **TC-DM-036**: Case-sensitive matching
  - Input: comment_text="Info", case_sensitive=True trigger
  - Expected: Match only if case matches exactly
  - Validation: Case sensitivity enforced

- **TC-DM-037**: Case-insensitive matching
  - Input: comment_text="INFO", case_sensitive=False trigger
  - Expected: Match regardless of case
  - Validation: Case insensitivity works

- **TC-DM-038**: User in cooldown period
  - Input: Recent execution within cooldown_minutes
  - Expected: No match due to cooldown
  - Validation: Cooldown enforced correctly

- **TC-DM-039**: User exceeded max triggers
  - Input: User already triggered max_triggers_per_user times
  - Expected: No match due to limit
  - Validation: Max triggers limit enforced

- **TC-DM-040**: Multiple triggers for same post
  - Input: Multiple active triggers for post_shortcode
  - Expected: First matching trigger returned
  - Validation: Priority handling works

#### 2.2 Execute Trigger DM
**Test Cases:**
- **TC-DM-041**: Execute successful DM send
  - Input: Valid trigger_id, commenter_username
  - Expected: DM sent successfully
  - Validation: DM appears in recipient's inbox

- **TC-DM-042**: DM template with username placeholder
  - Input: dm_template="Hi {username}!"
  - Expected: Username replaced in sent message
  - Validation: Placeholder substitution works

- **TC-DM-043**: Execute with account override
  - Input: account_id different from trigger's account
  - Expected: DM sent from override account
  - Validation: Account override works

- **TC-DM-044**: Execute non-existent trigger
  - Input: Invalid trigger_id
  - Expected: Error returned
  - Validation: Appropriate error message

- **TC-DM-045**: Execute paused trigger
  - Input: Paused trigger_id
  - Expected: Error or no execution
  - Validation: Paused triggers not executed

- **TC-DM-046**: Execute with invalid username
  - Input: Non-existent commenter_username
  - Expected: Error returned
  - Validation: Invalid username handling

- **TC-DM-047**: DM send failure handling
  - Input: Trigger DM send fails (network/API error)
  - Expected: Error recorded in execution log
  - Validation: Failure logged correctly

#### 2.3 Get Trigger Executions Log
**Test Cases:**
- **TC-DM-048**: Get executions for trigger
  - Input: Valid trigger_id
  - Expected: List of executions returned
  - Validation: Execution count matches actual

- **TC-DM-049**: Get executions with limit
  - Input: trigger_id, limit=10
  - Expected: Maximum 10 executions returned
  - Validation: Limit enforced

- **TC-DM-050**: Get executions for trigger with no history
  - Input: New trigger_id
  - Expected: Empty list returned
  - Validation: Empty list handling

- **TC-DM-051**: Execution log contains all fields
  - Input: trigger_id with executions
  - Expected: All execution fields present
  - Validation: Complete execution data

### 3. DM Messaging Tests

#### 3.1 Get Direct Inbox
**Test Cases:**
- **TC-DM-052**: Get inbox with default limit
  - Input: No parameters
  - Expected: Up to 20 conversations returned
  - Validation: Default limit applied

- **TC-DM-053**: Get inbox with custom limit
  - Input: limit=10
  - Expected: Up to 10 conversations returned
  - Validation: Custom limit applied

- **TC-DM-054**: Get inbox with maximum limit
  - Input: limit=50
  - Expected: Up to 50 conversations returned
  - Validation: Maximum limit enforced

- **TC-DM-055**: Get inbox with invalid limit (too low)
  - Input: limit=0
  - Expected: Error returned
  - Validation: Minimum limit enforced

- **TC-DM-056**: Get inbox with invalid limit (too high)
  - Input: limit=100
  - Expected: Error returned
  - Validation: Maximum limit enforced

- **TC-DM-057**: Get inbox with account_id
  - Input: account_id="test_account"
  - Expected: Inbox for specified account
  - Validation: Multi-account support works

#### 3.2 Get DM Conversation
**Test Cases:**
- **TC-DM-058**: Get conversation by username
  - Input: username="testuser"
  - Expected: Conversation messages returned
  - Validation: Correct conversation retrieved

- **TC-DM-059**: Get conversation by thread_id
  - Input: thread_id="valid_thread_id"
  - Expected: Conversation messages returned
  - Validation: Thread-based retrieval works

- **TC-DM-060**: Get conversation with custom limit
  - Input: limit=25
  - Expected: Up to 25 messages returned
  - Validation: Custom limit applied

- **TC-DM-061**: Get conversation with no identifier
  - Input: No username or thread_id
  - Expected: Error returned
  - Validation: Required parameter validation

- **TC-DM-062**: Get conversation with both identifiers
  - Input: Both username and thread_id
  - Expected: Conversation returned (username priority)
  - Validation: Parameter priority handling

#### 3.3 Send DM
**Test Cases:**
- **TC-DM-063**: Send DM with confirm_send=True
  - Input: username, message, confirm_send=True
  - Expected: DM sent successfully
  - Validation: Message appears in recipient's inbox

- **TC-DM-064**: Send DM with confirm_send=False
  - Input: username, message, confirm_send=False
  - Expected: DM not sent, confirmation message
  - Validation: Safety mechanism works

- **TC-DM-065**: Send DM with account_id
  - Input: account_id="test_account"
  - Expected: DM sent from specified account
  - Validation: Multi-account sending works

- **TC-DM-066**: Send DM to invalid username
  - Input: username="nonexistent_user"
  - Expected: Error returned
  - Validation: Invalid username handling

- **TC-DM-067**: Send DM with empty message
  - Input: message=""
  - Expected: Error returned
  - Validation: Empty message validation

- **TC-DM-068**: Send DM with very long message
  - Input: Message > 1000 characters
  - Expected: Error or truncation
  - Validation: Message length handling

### 4. Integration Tests

#### 4.1 Trigger Workflow Integration
**Test Cases:**
- **TC-DM-069**: Complete trigger lifecycle
  - Flow: Create → Activate → Match → Execute → Pause → Resume → Delete
  - Expected: All operations complete successfully
  - Validation: End-to-end workflow works

- **TC-DM-070**: Multi-trigger post scenario
  - Setup: Multiple triggers on same post
  - Expected: Appropriate trigger matched based on priority
  - Validation: Multi-trigger coordination works

- **TC-DM-071**: Cooldown integration
  - Flow: Trigger execution → Cooldown period → Second attempt
  - Expected: Second attempt blocked during cooldown
  - Validation: Cooldown system integrated correctly

- **TC-DM-072**: Max triggers integration
  - Flow: Execute trigger max_triggers_per_user times → Attempt +1
  - Expected: Additional execution blocked
  - Validation: Limit system integrated correctly

#### 4.2 Multi-Account Integration
**Test Cases:**
- **TC-DM-073**: Trigger on account A, execute from account B
  - Setup: Trigger created on account A, override with account B
  - Expected: DM sent from account B
  - Validation: Cross-account execution works

- **TC-DM-074**: Account-specific trigger filtering
  - Setup: Triggers on multiple accounts
  - Expected: list_dm_triggers with account_id returns correct subset
  - Validation: Account isolation works

#### 4.3 Error Recovery Integration
**Test Cases:**
- **TC-DM-075**: Failed execution recovery
  - Setup: Simulate DM send failure
  - Expected: Error logged, trigger remains active
  - Validation: Error recovery doesn't break system

- **TC-DM-076**: Invalid session handling
  - Setup: Expired session cookies
  - Expected: Appropriate authentication error
  - Validation: Session management integrated

### 5. Performance Tests

#### 5.1 Scalability Tests
**Test Cases:**
- **TC-DM-077**: Large trigger list performance
  - Setup: 100+ triggers
  - Expected: list_dm_triggers returns within acceptable time
  - Validation: Performance acceptable (< 2 seconds)

- **TC-DM-078**: Large execution log performance
  - Setup: 1000+ trigger executions
  - Expected: get_trigger_executions_log returns within acceptable time
  - Validation: Performance acceptable (< 3 seconds)

#### 5.2 Concurrency Tests
**Test Cases:**
- **TC-DM-079**: Simultaneous trigger checks
  - Setup: Multiple concurrent check_comment_for_triggers calls
  - Expected: All calls complete successfully
  - Validation: No race conditions

- **TC-DM-080**: Simultaneous DM executions
  - Setup: Multiple concurrent execute_trigger_dm calls
  - Expected: All DMs sent successfully
  - Validation: No conflicts or duplicates

### 6. Security Tests

#### 6.1 Input Validation
**Test Cases:**
- **TC-DM-081**: SQL injection in trigger words
  - Input: trigger_words=["'; DROP TABLE--"]
  - Expected: Input sanitized or rejected
  - Validation: No SQL injection vulnerability

- **TC-DM-082**: XSS in DM template
  - Input: dm_template="<script>alert('xss')</script>"
  - Expected: Input sanitized
  - Validation: No XSS vulnerability

- **TC-DM-083**: Path traversal in account_id
  - Input: account_id="../../../etc/passwd"
  - Expected: Invalid account error
  - Validation: No path traversal vulnerability

#### 6.2 Authorization Tests
**Test Cases:**
- **TC-DM-084**: Cross-account trigger access
  - Setup: Account A tries to access Account B's triggers
  - Expected: Access denied or only own triggers returned
  - Validation: Account isolation enforced

- **TC-DM-085**: Unauthorized DM sending
  - Setup: Invalid session cookies
  - Expected: Authentication error
  - Validation: Authorization enforced

## Test Execution Procedure

### Prerequisites
1. Ensure test environment is set up with valid Instagram account
2. Create test posts for trigger setup
3. Coordinate with test users for DM interactions
4. Backup existing trigger configurations

### Execution Order
1. Run Trigger Management Tests (1.1-1.6)
2. Run Trigger Execution Tests (2.1-2.3)
3. Run DM Messaging Tests (3.1-3.3)
4. Run Integration Tests (4.1-4.3)
5. Run Performance Tests (5.1-5.2)
6. Run Security Tests (6.1-6.2)

### Test Data Cleanup
- Delete all test triggers after testing
- Clean up test DMs
- Restore original configurations

## Success Criteria
- **Functional**: 95%+ of test cases pass
- **Performance**: All performance tests meet time thresholds
- **Security**: All security tests show no vulnerabilities
- **Integration**: All integration workflows complete successfully
- **Reliability**: No system crashes or data corruption during testing

## Test Reporting
Document results for each test case including:
- Test case ID and description
- Input parameters
- Expected vs actual results
- Pass/fail status
- Screenshots/logs where applicable
- Bug reports for failed tests

## Known Limitations
- Tests require valid Instagram session cookies
- Some tests require coordination with other users
- Rate limiting may affect test execution speed
- Instagram API changes may affect test reliability