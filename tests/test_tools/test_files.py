"""Tests for file tools with sandbox security."""

import tempfile
from pathlib import Path

import pytest

from miru.tools import (
    FileSandbox,
    SecurityError,
    ToolRegistry,
    create_file_tools,
)


class TestFileSandbox:
    """Tests for FileSandbox class."""

    def test_sandbox_creation(self, tmp_path: Path) -> None:
        """Test creating a sandbox."""
        sandbox = FileSandbox(tmp_path)

        assert sandbox.root == tmp_path
        assert sandbox.allow_write is True
        assert sandbox.allow_delete is False

    def test_sandbox_creates_directory(self) -> None:
        """Test sandbox creates root directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmp:
            sandbox_path = Path(tmp) / "new_sandbox"
            sandbox = FileSandbox(sandbox_path)

            assert sandbox.root.exists()
            assert sandbox.root.is_dir()

    def test_sandbox_custom_settings(self, tmp_path: Path) -> None:
        """Test sandbox with custom settings."""
        sandbox = FileSandbox(
            tmp_path,
            allow_write=False,
            allow_delete=True,
            allowed_extensions=[".txt", ".md"],
        )

        assert sandbox.allow_write is False
        assert sandbox.allow_delete is True
        assert sandbox.allowed_extensions == [".txt", ".md"]

    def test_resolve_path_inside_sandbox(self, tmp_path: Path) -> None:
        """Test resolving path inside sandbox."""
        sandbox = FileSandbox(tmp_path)

        resolved = sandbox.resolve_path("test.txt")

        assert resolved == tmp_path / "test.txt"

    def test_resolve_path_with_subdirectories(self, tmp_path: Path) -> None:
        """Test resolving path with subdirectories."""
        sandbox = FileSandbox(tmp_path)

        resolved = sandbox.resolve_path("sub/dir/test.txt")

        assert resolved == tmp_path / "sub" / "dir" / "test.txt"

    def test_resolve_path_absolute_inside_sandbox(self, tmp_path: Path) -> None:
        """Test resolving absolute path that's inside sandbox."""
        sandbox = FileSandbox(tmp_path)

        # Create a file to test absolute path resolution
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")

        # When given absolute path, it should use the basename and resolve from root
        resolved = sandbox.resolve_path(str(test_file))

        # It should resolve to the same file using basename
        assert resolved.name == "test.txt"
        assert resolved.parent == tmp_path

    def test_resolve_path_escapes_sandbox(self, tmp_path: Path) -> None:
        """Test that path escaping sandbox raises error."""
        sandbox = FileSandbox(tmp_path)

        with pytest.raises(SecurityError, match="escapes sandbox"):
            sandbox.resolve_path("../outside_sandbox.txt")

    def test_resolve_path_escalation_attack(self, tmp_path: Path) -> None:
        """Test that path traversal attack is blocked."""
        sandbox = FileSandbox(tmp_path)

        # Various path traversal attempts
        with pytest.raises(SecurityError):
            sandbox.resolve_path("../../../etc/passwd")

        with pytest.raises(SecurityError):
            sandbox.resolve_path("sub/../../outside.txt")

    def test_resolve_path_extension_check(self, tmp_path: Path) -> None:
        """Test extension check in sandbox."""
        sandbox = FileSandbox(tmp_path, allowed_extensions=[".txt"])

        # Allowed extension
        resolved = sandbox.resolve_path("test.txt")
        assert resolved.suffix == ".txt"

        # Blocked extension
        with pytest.raises(SecurityError, match="not allowed"):
            sandbox.resolve_path("test.py")

    def test_check_write_permission_allowed(self, tmp_path: Path) -> None:
        """Test write permission check when allowed."""
        sandbox = FileSandbox(tmp_path, allow_write=True)

        # Should not raise
        sandbox.check_write_permission()

    def test_check_write_permission_denied(self, tmp_path: Path) -> None:
        """Test write permission check when denied."""
        sandbox = FileSandbox(tmp_path, allow_write=False)

        with pytest.raises(SecurityError, match="Write operations are disabled"):
            sandbox.check_write_permission()

    def test_check_delete_permission_allowed(self, tmp_path: Path) -> None:
        """Test delete permission check when allowed."""
        sandbox = FileSandbox(tmp_path, allow_delete=True)

        # Should not raise
        sandbox.check_delete_permission()

    def test_check_delete_permission_denied(self, tmp_path: Path) -> None:
        """Test delete permission check when denied."""
        sandbox = FileSandbox(tmp_path, allow_delete=False)

        with pytest.raises(SecurityError, match="Delete operations are disabled"):
            sandbox.check_delete_permission()


class TestFileTools:
    """Tests for file tools."""

    def test_read_file(self, tmp_path: Path) -> None:
        """Test reading a file."""
        sandbox = FileSandbox(tmp_path)
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")

        tools = create_file_tools(sandbox)
        registry = ToolRegistry()
        for tool in tools:
            registry.register(tool)

        result = registry.execute("read_file", {"path": "test.txt"})

        assert result == "Hello, World!"

    def test_read_nonexistent_file(self, tmp_path: Path) -> None:
        """Test reading nonexistent file."""
        sandbox = FileSandbox(tmp_path)
        tools = create_file_tools(sandbox)
        registry = ToolRegistry()
        for tool in tools:
            registry.register(tool)

        from miru.tools.exceptions import ToolExecutionError

        with pytest.raises(ToolExecutionError, match="File not found"):
            registry.execute("read_file", {"path": "nonexistent.txt"})

    def test_read_directory_instead_of_file(self, tmp_path: Path) -> None:
        """Test reading a directory."""
        sandbox = FileSandbox(tmp_path)
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()

        tools = create_file_tools(sandbox)
        registry = ToolRegistry()
        for tool in tools:
            registry.register(tool)

        from miru.tools.exceptions import ToolExecutionError

        with pytest.raises(ToolExecutionError, match="Not a file"):
            registry.execute("read_file", {"path": "test_dir"})

    def test_write_file(self, tmp_path: Path) -> None:
        """Test writing a file."""
        sandbox = FileSandbox(tmp_path)
        tools = create_file_tools(sandbox)
        registry = ToolRegistry()
        for tool in tools:
            registry.register(tool)

        result = registry.execute("write_file", {"path": "test.txt", "content": "Hello"})

        assert "success" in result.lower()
        assert (tmp_path / "test.txt").read_text() == "Hello"

    def test_write_file_creates_directories(self, tmp_path: Path) -> None:
        """Test writing creates parent directories."""
        sandbox = FileSandbox(tmp_path)
        tools = create_file_tools(sandbox)
        registry = ToolRegistry()
        for tool in tools:
            registry.register(tool)

        registry.execute("write_file", {"path": "sub/dir/test.txt", "content": "test"})

        assert (tmp_path / "sub" / "dir" / "test.txt").read_text() == "test"

    def test_write_disabled(self, tmp_path: Path) -> None:
        """Test writing disabled in sandbox."""
        sandbox = FileSandbox(tmp_path, allow_write=False)
        tools = create_file_tools(sandbox)
        registry = ToolRegistry()
        for tool in tools:
            registry.register(tool)

        from miru.tools.exceptions import ToolExecutionError

        with pytest.raises(ToolExecutionError, match="Write operations are disabled"):
            registry.execute("write_file", {"path": "test.txt", "content": "test"})

    def test_edit_file(self, tmp_path: Path) -> None:
        """Test editing a file."""
        sandbox = FileSandbox(tmp_path)
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello World")

        tools = create_file_tools(sandbox)
        registry = ToolRegistry()
        for tool in tools:
            registry.register(tool)

        result = registry.execute(
            "edit_file", {"path": "test.txt", "old": "World", "new": "Universe"}
        )

        assert "1 occurrence" in result
        assert test_file.read_text() == "Hello Universe"

    def test_edit_file_multiple_occurrences(self, tmp_path: Path) -> None:
        """Test editing file with multiple occurrences."""
        sandbox = FileSandbox(tmp_path)
        test_file = tmp_path / "test.txt"
        test_file.write_text("test test test")

        tools = create_file_tools(sandbox)
        registry = ToolRegistry()
        for tool in tools:
            registry.register(tool)

        result = registry.execute("edit_file", {"path": "test.txt", "old": "test", "new": "passed"})

        assert "3 occurrence" in result
        assert test_file.read_text() == "passed passed passed"

    def test_edit_file_not_found_text(self, tmp_path: Path) -> None:
        """Test editing file with text not found."""
        sandbox = FileSandbox(tmp_path)
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello")

        tools = create_file_tools(sandbox)
        registry = ToolRegistry()
        for tool in tools:
            registry.register(tool)

        from miru.tools.exceptions import ToolExecutionError

        with pytest.raises(ToolExecutionError, match="Text not found"):
            registry.execute("edit_file", {"path": "test.txt", "old": "World", "new": "Universe"})

    def test_list_files(self, tmp_path: Path) -> None:
        """Test listing files."""
        sandbox = FileSandbox(tmp_path)
        (tmp_path / "file1.txt").write_text("test")
        (tmp_path / "file2.txt").write_text("test")
        (tmp_path / "file3.py").write_text("test")

        tools = create_file_tools(sandbox)
        registry = ToolRegistry()
        for tool in tools:
            registry.register(tool)

        result = registry.execute("list_files", {"directory": ".", "pattern": "*"})
        assert "file1.txt" in result
        assert "file2.txt" in result
        assert "file3.py" in result

        result = registry.execute("list_files", {"directory": ".", "pattern": "*.txt"})
        assert len(result) == 2

    def test_list_files_subdirectory(self, tmp_path: Path) -> None:
        """Test listing files in subdirectory."""
        sandbox = FileSandbox(tmp_path)
        sub_dir = tmp_path / "sub"
        sub_dir.mkdir()
        (sub_dir / "file1.txt").write_text("test")
        (sub_dir / "file2.txt").write_text("test")

        tools = create_file_tools(sandbox)
        registry = ToolRegistry()
        for tool in tools:
            registry.register(tool)

        result = registry.execute("list_files", {"directory": "sub", "pattern": "*"})

        assert len(result) == 2
        assert "sub/file1.txt" in result or "file1.txt" in result

    def test_search_files(self, tmp_path: Path) -> None:
        """Test searching files by pattern."""
        sandbox = FileSandbox(tmp_path)
        (tmp_path / "test_file.py").write_text("test")
        (tmp_path / "test_file.txt").write_text("test")
        (tmp_path / "TEST_FILE.PY").write_text("test")

        tools = create_file_tools(sandbox)
        registry = ToolRegistry()
        for tool in tools:
            registry.register(tool)

        result = registry.execute("search_files", {"pattern": "*.py"})

        assert len(result) == 2
        assert any("test_file.py" in f for f in result)
        assert any("TEST_FILE.PY" in f for f in result)

    def test_delete_file(self, tmp_path: Path) -> None:
        """Test deleting a file."""
        sandbox = FileSandbox(tmp_path, allow_delete=True)
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")

        tools = create_file_tools(sandbox)
        registry = ToolRegistry()
        for tool in tools:
            registry.register(tool)

        result = registry.execute("delete_file", {"path": "test.txt"})

        assert "deleted" in result.lower()
        assert not test_file.exists()

    def test_delete_disabled(self, tmp_path: Path) -> None:
        """Test deleting disabled in sandbox."""
        sandbox = FileSandbox(tmp_path, allow_delete=False)
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")

        tools = create_file_tools(sandbox)
        registry = ToolRegistry()
        for tool in tools:
            registry.register(tool)

        from miru.tools.exceptions import ToolExecutionError

        with pytest.raises(ToolExecutionError, match="Delete operations are disabled"):
            registry.execute("delete_file", {"path": "test.txt"})

    def test_file_exists(self, tmp_path: Path) -> None:
        """Test checking if file exists."""
        sandbox = FileSandbox(tmp_path)
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")

        tools = create_file_tools(sandbox)
        registry = ToolRegistry()
        for tool in tools:
            registry.register(tool)

        result = registry.execute("file_exists", {"path": "test.txt"})
        assert result is True

        result = registry.execute("file_exists", {"path": "nonexistent.txt"})
        assert result is False

    def test_get_file_info(self, tmp_path: Path) -> None:
        """Test getting file info."""
        sandbox = FileSandbox(tmp_path)
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello World")

        tools = create_file_tools(sandbox)
        registry = ToolRegistry()
        for tool in tools:
            registry.register(tool)

        result = registry.execute("get_file_info", {"path": "test.txt"})

        assert isinstance(result, dict)
        assert result["path"] == "test.txt"
        assert result["size"] == 11
        assert result["extension"] == ".txt"
        assert result["name"] == "test.txt"


class TestToolDefinitions:
    """Tests for tool definitions."""

    def test_all_tools_have_correct_names(self, tmp_path: Path) -> None:
        """Test all tools have expected names."""
        sandbox = FileSandbox(tmp_path)
        tools = create_file_tools(sandbox)

        expected_names = {
            "read_file",
            "write_file",
            "edit_file",
            "list_files",
            "search_files",
            "delete_file",
            "file_exists",
            "get_file_info",
        }

        actual_names = {tool.name for tool in tools}

        assert actual_names == expected_names

    def test_tools_have_required_parameters(self, tmp_path: Path) -> None:
        """Test tools have required parameter definitions."""
        sandbox = FileSandbox(tmp_path)
        tools = create_file_tools(sandbox)

        # Check read_file
        read_tool = next(t for t in tools if t.name == "read_file")
        assert "path" in read_tool.parameters["properties"]
        assert read_tool.parameters["required"] == ["path"]

        # Check write_file
        write_tool = next(t for t in tools if t.name == "write_file")
        assert "path" in write_tool.parameters["properties"]
        assert "content" in write_tool.parameters["properties"]
        assert set(write_tool.parameters["required"]) == {"path", "content"}

    def test_tools_to_ollama_format(self, tmp_path: Path) -> None:
        """Test converting tools to Ollama format."""
        sandbox = FileSandbox(tmp_path)
        tools = create_file_tools(sandbox)

        for tool in tools:
            ollama_format = tool.to_ollama_format()

            assert ollama_format["type"] == "function"
            assert "function" in ollama_format
            assert ollama_format["function"]["name"] == tool.name
            assert "description" in ollama_format["function"]
            assert "parameters" in ollama_format["function"]
