"""File system tools with sandbox security."""

from __future__ import annotations

import fnmatch
from pathlib import Path
from typing import Any

from miru.tools.base import Tool, create_tool


class FileSandbox:
    """
    Sandbox for file system operations.

    Restricts file access to a specific directory tree,
    preventing path traversal attacks and unauthorized access.
    """

    def __init__(
        self,
        root: Path | str,
        allow_write: bool = True,
        allow_delete: bool = False,
        allowed_extensions: list[str] | None = None,
    ) -> None:
        """
        Initialize file sandbox.

        Args:
            root: Root directory for sandbox (all paths are relative to this)
            allow_write: Whether write operations are permitted
            allow_delete: Whether delete operations are permitted
            allowed_extensions: List of allowed file extensions (e.g., ['.txt', '.md'])
                                 None means all extensions allowed
        """
        self.root = Path(root).resolve()
        self.allow_write = allow_write
        self.allow_delete = allow_delete
        self.allowed_extensions = allowed_extensions

        # Create root if it doesn't exist
        if not self.root.exists():
            self.root.mkdir(parents=True)

    def resolve_path(self, path: str) -> Path:
        """
        Resolve and validate a path within the sandbox.

        Args:
            path: Relative path within sandbox

        Returns:
            Absolute path within sandbox

        Raises:
            SecurityError: If path escapes sandbox
            FileNotFoundError: If path doesn't exist (for read operations)
        """
        # Handle both relative and absolute-looking paths
        path_obj = Path(path)

        # If path is absolute, use only the basename relative to root
        if path_obj.is_absolute():
            # Extract just the filename and use it relative to root
            path_obj = Path(path_obj.name)

        # Resolve the full path
        full_path = (self.root / path_obj).resolve()

        # Security check: ensure path is within sandbox
        if not full_path.is_relative_to(self.root):
            raise SecurityError(f"Path escapes sandbox: {path}")

        # Extension check
        if self.allowed_extensions and full_path.suffix not in self.allowed_extensions:
            raise SecurityError(
                f"File extension '{full_path.suffix}' not allowed. "
                f"Allowed: {', '.join(self.allowed_extensions)}"
            )

        return full_path

    def check_write_permission(self) -> None:
        """Check if write operations are allowed."""
        if not self.allow_write:
            raise SecurityError("Write operations are disabled in this sandbox")

    def check_delete_permission(self) -> None:
        """Check if delete operations are allowed."""
        if not self.allow_delete:
            raise SecurityError("Delete operations are disabled in this sandbox")


class SecurityError(Exception):
    """Security-related error in tool execution."""

    pass


def create_file_tools(sandbox: FileSandbox) -> list[Tool]:
    """
    Create file system tools with sandbox restrictions.

    Args:
        sandbox: FileSandbox instance to restrict file access

    Returns:
        List of Tool instances for file operations
    """

    def read_file(path: str) -> str:
        """
        Read contents of a text file.

        Args:
            path: Relative path to file within sandbox

        Returns:
            File contents as string

        Raises:
            SecurityError: If path escapes sandbox
            FileNotFoundError: If file doesn't exist
        """
        full_path = sandbox.resolve_path(path)

        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        if not full_path.is_file():
            raise ValueError(f"Not a file: {path}")

        return full_path.read_text(encoding="utf-8")

    def write_file(path: str, content: str) -> str:
        """
        Write content to a file, creating it if it doesn't exist.

        Args:
            path: Relative path to file within sandbox
            content: Content to write

        Returns:
            Success message with file path

        Raises:
            SecurityError: If path escapes sandbox or writes are disabled
        """
        sandbox.check_write_permission()
        full_path = sandbox.resolve_path(path)

        # Create parent directories if needed
        full_path.parent.mkdir(parents=True, exist_ok=True)

        full_path.write_text(content, encoding="utf-8")
        return f"File written successfully: {path}"

    def edit_file(path: str, old: str, new: str) -> str:
        """
        Edit a file by replacing exact text occurrences.

        Args:
            path: Relative path to file within sandbox
            old: Text to find and replace (must match exactly)
            new: Text to replace with

        Returns:
            Success message with number of replacements

        Raises:
            SecurityError: If path escapes sandbox or writes are disabled
            ValueError: If old text not found or multiple unique matches
        """
        sandbox.check_write_permission()
        full_path = sandbox.resolve_path(path)

        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        content = full_path.read_text(encoding="utf-8")

        if old not in content:
            raise ValueError(f"Text not found in file: {old!r}")

        # Count occurrences
        count = content.count(old)

        # Replace all occurrences
        new_content = content.replace(old, new)
        full_path.write_text(new_content, encoding="utf-8")

        return f"Replaced {count} occurrence(s) in {path}"

    def list_files(directory: str = ".", pattern: str = "*") -> list[str]:
        """
        List files in a directory matching a pattern.

        Args:
            directory: Relative path to directory within sandbox (default: current)
            pattern: Glob pattern to filter files (e.g., '*.py', '*.txt')

        Returns:
            List of relative file paths

        Raises:
            SecurityError: If path escapes sandbox
            FileNotFoundError: If directory doesn't exist
        """
        full_path = sandbox.resolve_path(directory)

        if not full_path.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")

        if not full_path.is_dir():
            raise ValueError(f"Not a directory: {directory}")

        # Find all matching files
        files = []
        for match in full_path.rglob(pattern):
            if match.is_file():
                # Get relative path from sandbox root
                rel_path = match.relative_to(sandbox.root)
                files.append(str(rel_path))

        return sorted(files)

    def search_files(pattern: str, directory: str = ".") -> list[str]:
        """
        Search for files by name pattern.

        Args:
            pattern: Filename pattern (supports * and ? wildcards)
            directory: Relative path to directory within sandbox (default: current)

        Returns:
            List of matching relative file paths

        Raises:
            SecurityError: If path escapes sandbox
        """
        full_path = sandbox.resolve_path(directory)

        if not full_path.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")

        matches = []

        # Walk directory tree
        for root_dir in full_path.rglob("*"):
            # Check each file against pattern
            if root_dir.is_file():
                for filename in [root_dir.name, root_dir.name.lower()]:
                    if fnmatch.fnmatch(filename, pattern) or fnmatch.fnmatch(
                        filename.lower(), pattern.lower()
                    ):
                        # Get relative path from sandbox root
                        rel_path = root_dir.relative_to(sandbox.root)
                        matches.append(str(rel_path))
                        break

        return sorted(matches)

    def delete_file(path: str) -> str:
        """
        Delete a file from the sandbox.

        Args:
            path: Relative path to file within sandbox

        Returns:
            Success message

        Raises:
            SecurityError: If path escapes sandbox or deletes are disabled
            FileNotFoundError: If file doesn't exist
        """
        sandbox.check_delete_permission()
        full_path = sandbox.resolve_path(path)

        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        if not full_path.is_file():
            raise ValueError(f"Not a file: {path}")

        full_path.unlink()
        return f"File deleted: {path}"

    def file_exists(path: str) -> bool:
        """
        Check if a file exists.

        Args:
            path: Relative path to file within sandbox

        Returns:
            True if file exists, False otherwise

        Raises:
            SecurityError: If path escapes sandbox
        """
        try:
            full_path = sandbox.resolve_path(path)
            return full_path.exists() and full_path.is_file()
        except (SecurityError, FileNotFoundError):
            return False

    def get_file_info(path: str) -> dict[str, Any]:
        """
        Get information about a file.

        Args:
            path: Relative path to file within sandbox

        Returns:
            Dict with file information (size, modified time, etc.)

        Raises:
            SecurityError: If path escapes sandbox
            FileNotFoundError: If file doesn't exist
        """
        full_path = sandbox.resolve_path(path)

        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        if not full_path.is_file():
            raise ValueError(f"Not a file: {path}")

        stat = full_path.stat()

        return {
            "path": path,
            "size": stat.st_size,
            "modified": stat.st_mtime,
            "created": stat.st_ctime,
            "extension": full_path.suffix,
            "name": full_path.name,
            "parent": str(full_path.parent.relative_to(sandbox.root)),
        }

    # Create Tool objects
    tools = [
        create_tool(
            name="read_file",
            description="Read the contents of a text file",
            parameters={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path to the file within sandbox",
                    }
                },
                "required": ["path"],
            },
        )(read_file),
        create_tool(
            name="write_file",
            description="Write content to a file, creating it if it doesn't exist",
            parameters={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path to the file within sandbox",
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write to the file",
                    },
                },
                "required": ["path", "content"],
            },
        )(write_file),
        create_tool(
            name="edit_file",
            description="Edit a file by replacing exact text occurrences",
            parameters={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path to the file within sandbox",
                    },
                    "old": {
                        "type": "string",
                        "description": "Text to find and replace (must match exactly)",
                    },
                    "new": {
                        "type": "string",
                        "description": "Text to replace with",
                    },
                },
                "required": ["path", "old", "new"],
            },
        )(edit_file),
        create_tool(
            name="list_files",
            description="List files in a directory matching a pattern",
            parameters={
                "type": "object",
                "properties": {
                    "directory": {
                        "type": "string",
                        "description": "Relative path to directory (default: current directory)",
                    },
                    "pattern": {
                        "type": "string",
                        "description": "Glob pattern to filter files (e.g., '*.py', '*.txt')",
                    },
                },
                "required": [],
            },
        )(list_files),
        create_tool(
            name="search_files",
            description="Search for files by name pattern",
            parameters={
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Filename pattern (supports * and ? wildcards)",
                    },
                    "directory": {
                        "type": "string",
                        "description": "Relative path to directory (default: current directory)",
                    },
                },
                "required": ["pattern"],
            },
        )(search_files),
        create_tool(
            name="delete_file",
            description="Delete a file from the sandbox (requires permission)",
            parameters={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path to the file within sandbox",
                    }
                },
                "required": ["path"],
            },
        )(delete_file),
        create_tool(
            name="file_exists",
            description="Check if a file exists",
            parameters={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path to the file within sandbox",
                    }
                },
                "required": ["path"],
            },
        )(file_exists),
        create_tool(
            name="get_file_info",
            description="Get information about a file",
            parameters={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path to the file within sandbox",
                    }
                },
                "required": ["path"],
            },
        )(get_file_info),
    ]

    # Extract Tool objects from decorated functions
    extracted: list[Tool] = []
    for func in tools:
        tool = get_tool_from_function(func)
        if tool is not None:
            extracted.append(tool)
    return extracted


__all__ = ["FileSandbox", "SecurityError", "create_file_tools"]


# Import at end to avoid circular dependency
from miru.tools.base import get_tool_from_function
