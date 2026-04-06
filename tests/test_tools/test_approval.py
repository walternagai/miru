"""Tests for tool approval system."""

import pytest
from unittest.mock import patch, MagicMock
from io import StringIO

from miru.tools.approval import ToolApprovalManager, ToolApprovalFlow


class TestToolApprovalManager:
    """Tests for ToolApprovalManager class."""

    def test_init(self) -> None:
        """Test initializing approval manager."""
        manager = ToolApprovalManager()

        assert len(manager._approved_tools) == 0
        assert len(manager._denied_tools) == 0
        assert len(manager._session_approvals) == 0

    def test_auto_approve_safe_tool(self) -> None:
        """Test auto-approving safe tools."""
        flow = ToolApprovalFlow(auto_approve_safe=True)

        # Safe tools should not require approval
        assert flow.should_request_approval("read_file") is False
        assert flow.should_request_approval("list_files") is False
        assert flow.should_request_approval("get_current_dir") is False

    def test_dangerous_tool_requires_approval(self) -> None:
        """Test that dangerous tools always require approval."""
        flow = ToolApprovalFlow(auto_approve_safe=True)

        # Dangerous tools should require approval
        assert flow.should_request_approval("write_file") is True
        assert flow.should_request_approval("delete_file") is True
        assert flow.should_request_approval("run_command") is True

    def test_request_approval_approved(self) -> None:
        """Test requesting approval and getting approved."""
        flow = ToolApprovalFlow(auto_approve_safe=False)

        with patch("rich.prompt.Confirm.ask", return_value=True):
            with patch("builtins.input", return_value="n"):  # Don't remember
                approved = flow.request_approval("write_file", {"path": "test.txt"})

        assert approved is True

    def test_request_approval_denied(self) -> None:
        """Test requesting approval and getting denied."""
        flow = ToolApprovalFlow(auto_approve_safe=False)

        with patch("rich.prompt.Confirm.ask", return_value=False):
            approved = flow.request_approval("write_file", {"path": "test.txt"})

        assert approved is False

    def test_session_approval_remembers(self) -> None:
        """Test that session approvals are remembered."""
        manager = ToolApprovalManager()

        # Mock user input
        with patch("rich.prompt.Confirm.ask") as mock_confirm:
            mock_confirm.side_effect = [True, True]  # Approve and remember
            approved, remember = manager.request_approval("write_file", {"path": "test.txt"})

        assert approved is True
        assert remember is True
        assert manager.is_approved("write_file")

        # Subsequent calls should use cached approval
        assert manager.is_approved("write_file") is True
        assert manager.is_denied("write_file") is False

    def test_clear_approvals(self) -> None:
        """Test clearing session approvals."""
        manager = ToolApprovalManager()

        # Add some approvals
        manager._session_approvals["tool1"] = True
        manager._session_approvals["tool2"] = False
        manager._approved_tools.add("tool1")
        manager._denied_tools.add("tool2")

        manager.clear_approvals()

        assert len(manager._session_approvals) == 0
        assert len(manager._approved_tools) == 0
        assert len(manager._denied_tools) == 0

    def test_show_approved_tools(self) -> None:
        """Test showing approved tools."""
        manager = ToolApprovalManager()

        # No tools approved
        with patch("rich.console.Console.print") as mock_print:
            manager.show_approved_tools()
            assert any("No tools" in str(call) for call in mock_print.call_args_list)

        # Add approval
        manager._approved_tools.add("write_file")

        with patch("rich.console.Console.print") as mock_print:
            manager.show_approved_tools()
            # Should show write_file
            printed_text = str(mock_print.call_args_list)
            assert "Approved Tools" in printed_text or "write_file" in printed_text

    def test_show_denied_tools(self) -> None:
        """Test showing denied tools."""
        manager = ToolApprovalManager()

        # No tools denied
        with patch("rich.console.Console.print") as mock_print:
            manager.show_denied_tools()
            assert any("No tools" in str(call) for call in mock_print.call_args_list)

        # Add denial
        manager._denied_tools.add("delete_file")

        with patch("rich.console.Console.print") as mock_print:
            manager.show_denied_tools()
            printed_text = str(mock_print.call_args_list)
            assert "Denied Tools" in printed_text or "delete_file" in printed_text


class TestToolApprovalFlow:
    """Tests for ToolApprovalFlow class."""

    def test_init_default(self) -> None:
        """Test initializing approval flow with defaults."""
        flow = ToolApprovalFlow()

        assert flow.auto_approve_safe is True
        assert flow.approval_manager is not None

    def test_init_no_auto_approve(self) -> None:
        """Test initializing without auto-approve."""
        flow = ToolApprovalFlow(auto_approve_safe=False)

        assert flow.auto_approve_safe is False
        # Even safe tools require approval
        assert flow.should_request_approval("read_file") is True

    def test_tool_categories(self) -> None:
        """Test safe and dangerous tool categories."""
        flow = ToolApprovalFlow(auto_approve_safe=True)

        # Safe tools
        assert "read_file" in flow.safe_tools
        assert "list_files" in flow.safe_tools
        assert "get_current_dir" in flow.safe_tools

        # Dangerous tools
        assert "write_file" in flow.dangerous_tools
        assert "delete_file" in flow.dangerous_tools
        assert "run_command" in flow.dangerous_tools

    def test_should_request_approval_logic(self) -> None:
        """Test should_request_approval logic."""
        flow = ToolApprovalFlow(auto_approve_safe=True)

        # Already approved
        flow.auto_approve("read_file")
        assert flow.should_request_approval("read_file") is False

        # Already denied
        flow.auto_deny("delete_file")
        # Should re-ask for denied tools
        assert flow.should_request_approval("delete_file") is True

        # Unknown tool
        assert flow.should_request_approval("unknown_tool") is True

    def test_auto_approve(self) -> None:
        """Test auto_approve method."""
        flow = ToolApprovalFlow()

        flow.auto_approve("write_file")

        assert "write_file" in flow.approval_manager._session_approvals
        assert flow.approval_manager.is_approved("write_file")

    def test_auto_deny(self) -> None:
        """Test auto_deny method."""
        flow = ToolApprovalFlow()

        flow.auto_deny("delete_file")

        assert "delete_file" in flow.approval_manager._session_approvals
        assert flow.approval_manager.is_denied("delete_file")

    def test_request_approval_already_approved(self) -> None:
        """Test request_approval when already approved."""
        flow = ToolApprovalFlow()

        # Auto-approve first
        flow.auto_approve("write_file")

        # Should not ask again
        approved = flow.request_approval("write_file", {"path": "test.txt"})

        assert approved is True

    def test_unknown_tool_needs_approval(self) -> None:
        """Test that unknown tools require approval."""
        flow = ToolApprovalFlow(auto_approve_safe=True)

        # Unknown tool should require approval even with auto_approve_safe
        assert flow.should_request_approval("unknown_custom_tool") is True


class TestToolApprovalIntegration:
    """Integration tests for approval system."""

    def test_full_workflow_approved(self) -> None:
        """Test full approval workflow - approved."""
        flow = ToolApprovalFlow(auto_approve_safe=False)

        with patch("rich.prompt.Confirm.ask", return_value=True):  # Approve
            with patch("rich.prompt.Prompt.ask", return_value="n"):  # Don't remember
                approved = flow.request_approval(
                    "write_file", {"path": "test.txt", "content": "Hello"}
                )

        assert approved is True

    def test_full_workflow_denied(self) -> None:
        """Test full approval workflow - denied."""
        flow = ToolApprovalFlow(auto_approve_safe=False)

        with patch("rich.prompt.Confirm.ask", return_value=False):  # Deny
            approved = flow.request_approval("delete_file", {"path": "test.txt"})

        assert approved is False

    def test_session_persistence(self) -> None:
        """Test that approvals persist within session."""
        flow = ToolApprovalFlow(auto_approve_safe=False)

        # First request - approve and remember
        with patch("rich.prompt.Confirm.ask", side_effect=[True, True]):  # Approve, Remember
            approved = flow.request_approval("write_file", {"path": "test.txt"})

        assert approved is True

        # Second request - should use cached approval
        approved = flow.request_approval("write_file", {"path": "test2.txt"})
        assert approved is True

        # Verify session state
        assert flow.approval_manager.is_approved("write_file")

    def test_mixed_tools(self) -> None:
        """Test mixed safe and dangerous tools."""
        flow = ToolApprovalFlow(auto_approve_safe=True)

        # Safe tool - auto-approved
        assert flow.should_request_approval("read_file") is False

        # Dangerous tool - requires approval
        assert flow.should_request_approval("delete_file") is True

        # After auto-approve dangerous tool
        flow.auto_approve("delete_file")
        assert flow.should_request_approval("delete_file") is False
