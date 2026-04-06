"""Interactive approval for tool execution."""

from __future__ import annotations

from typing import Any

from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.table import Table

console = Console()


class ToolApprovalManager:
    """Manages interactive approval for tool execution."""

    def __init__(self) -> None:
        """Initialize approval manager."""
        self._approved_tools: set[str] = set()
        self._denied_tools: set[str] = set()
        self._session_approvals: dict[str, bool] = {}  # Remember approvals for session

    def request_approval(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        reason: str | None = None,
    ) -> tuple[bool, bool]:
        """
        Request approval for tool execution.

        Args:
            tool_name: Name of the tool
            arguments: Tool arguments
            reason: Reason why approval is needed

        Returns:
            Tuple of (approved, remember_for_session)
        """
        # Check if already approved/denied for this session
        if tool_name in self._session_approvals:
            return self._session_approvals[tool_name], True

        # Display tool information
        self._display_tool_info(tool_name, arguments, reason)

        # Ask for approval
        approved = Confirm.ask(
            f"\n[bold yellow]Allow execution of '[cyan]{tool_name}[/]'?[/]",
            default=False,
        )

        # Ask if should remember
        remember = False
        if approved:
            remember = Confirm.ask(
                "[dim]Remember this approval for the session?[/]",
                default=False,
            )

        # Store approval
        if remember:
            self._session_approvals[tool_name] = approved

        if approved:
            self._approved_tools.add(tool_name)
        else:
            self._denied_tools.add(tool_name)

        return approved, remember

    def _display_tool_info(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        reason: str | None = None,
    ) -> None:
        """Display tool information in a formatted way."""
        console.print()
        console.print("[bold red]⚠  Tool Execution Request[/]")
        console.print()

        # Create table
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Key", style="bold yellow")
        table.add_column("Value", style="white")

        table.add_row("Tool:", f"[cyan]{tool_name}[/]")

        if reason:
            table.add_row("Reason:", f"[yellow]{reason}[/]")

        # Add arguments
        for key, value in arguments.items():
            # Truncate long values
            value_str = str(value)
            if len(value_str) > 100:
                value_str = value_str[:97] + "..."
            table.add_row(f"  {key}:", value_str)

        console.print(table)
        console.print()

    def is_approved(self, tool_name: str) -> bool:
        """Check if tool is approved for this session."""
        return tool_name in self._session_approvals and self._session_approvals[tool_name]

    def is_denied(self, tool_name: str) -> bool:
        """Check if tool is denied for this session."""
        return tool_name in self._session_approvals and not self._session_approvals[tool_name]

    def clear_approvals(self) -> None:
        """Clear all session approvals."""
        self._session_approvals.clear()
        self._approved_tools.clear()
        self._denied_tools.clear()

    def show_approved_tools(self) -> None:
        """Show all approved tools."""
        if not self._approved_tools:
            console.print("[dim]No tools have been approved this session.[/]")
            return

        console.print("\n[bold green]✓ Approved Tools:[/]")
        for tool in sorted(self._approved_tools):
            console.print(f"  [green]•[/] {tool}")

    def show_denied_tools(self) -> None:
        """Show all denied tools."""
        if not self._denied_tools:
            console.print("[dim]No tools have been denied this session.[/]")
            return

        console.print("\n[bold red]✗ Denied Tools:[/]")
        for tool in sorted(self._denied_tools):
            console.print(f"  [red]•[/] {tool}")


class ToolApprovalFlow:
    """Manages approval flow with different modes."""

    def __init__(self, auto_approve_safe: bool = True) -> None:
        """
        Initialize approval flow.

        Args:
            auto_approve_safe: Automatically approve safe tools
        """
        self.auto_approve_safe = auto_approve_safe
        self.approval_manager = ToolApprovalManager()

        # Safe tools that can be auto-approved
        self.safe_tools = {
            "read_file",
            "file_exists",
            "get_file_info",
            "list_files",
            "search_files",
            "get_current_dir",
            "list_allowed_commands",
            "list_allowed_env_vars",
            "get_env",
        }

        # Dangerous tools that always require approval
        self.dangerous_tools = {
            "write_file",
            "edit_file",
            "delete_file",
            "run_command",
        }

    def should_request_approval(self, tool_name: str) -> bool:
        """
        Determine if approval should be requested.

        Args:
            tool_name: Name of the tool

        Returns:
            True if approval should be requested
        """
        # Check if already decided in this session
        if self.approval_manager.is_approved(tool_name):
            return False
        if self.approval_manager.is_denied(tool_name):
            return True  # Re-ask if denied before

        # Safe tools with auto-approve
        if self.auto_approve_safe and tool_name in self.safe_tools:
            return False

        # Dangerous tools always require approval
        if tool_name in self.dangerous_tools:
            return True

        # Unknown tools require approval
        return True

    def request_approval(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        reason: str | None = None,
    ) -> bool:
        """
        Request approval for tool execution.

        Args:
            tool_name: Name of the tool
            arguments: Tool arguments
            reason: Optional reason

        Returns:
            True if approved
        """
        approved, _ = self.approval_manager.request_approval(tool_name, arguments, reason)
        return approved

    def auto_approve(self, tool_name: str) -> None:
        """
        Auto-approve a tool for this session.

        Args:
            tool_name: Name of the tool
        """
        self.approval_manager._session_approvals[tool_name] = True
        self.approval_manager._approved_tools.add(tool_name)

    def auto_deny(self, tool_name: str) -> None:
        """
        Auto-deny a tool for this session.

        Args:
            tool_name: Name of the tool
        """
        self.approval_manager._session_approvals[tool_name] = False
        self.approval_manager._denied_tools.add(tool_name)


__all__ = [
    "ToolApprovalManager",
    "ToolApprovalFlow",
]
