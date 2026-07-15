"""Example demonstrating Tavily web search integration with miru."""

from pathlib import Path
from miru.tools import ToolExecutionManager, ToolExecutionMode

# Example 1: Basic usage with configured API key
def example_basic_usage():
    """Basic usage with API key from config."""
    
    # Initialize manager with Tavily enabled
    # API key is read from ~/.miru/config.toml or MIRU_TAVILY_API_KEY env var
    manager = ToolExecutionManager(
        mode=ToolExecutionMode.AUTO_SAFE,
        enable_tavily=True,
    )
    
    # List available tools
    print("Available tools:")
    for tool in manager.list_tools():
        print(f"  - {tool['name']}: {tool['description']}")
    
    # Perform a web search
    print("\nSearching for 'Python 3.13 new features'...")
    result, error = manager.execute_tool(
        "tavily_search",
        {"query": "Python 3.13 new features", "max_results": 5}
    )
    
    if error:
        print(f"Error: {error}")
    else:
        print(result)


# Example 2: Using explicit API key
def example_explicit_api_key():
    """Use explicit API key instead of config."""
    
    manager = ToolExecutionManager(
        mode=ToolExecutionMode.AUTO_SAFE,
        enable_tavily=True,
        tavily_api_key="tvly-YOUR_API_KEY_HERE",
    )
    
    # Search with images
    result, error = manager.execute_tool(
        "tavily_search_images",
        {"query": "Python asyncio tutorial", "max_results": 3}
    )
    
    if error:
        print(f"Error: {error}")
    else:
        print(result)


# Example 3: Extract content from URLs
def example_extract_urls():
    """Extract and clean content from web pages."""
    
    manager = ToolExecutionManager(
        mode=ToolExecutionMode.AUTO_SAFE,
        enable_tavily=True,
        tavily_api_key="tvly-YOUR_API_KEY_HERE",
    )
    
    # Extract content from multiple URLs
    result, error = manager.execute_tool(
        "tavily_extract",
        {"urls": "https://docs.python.org/3/library/asyncio.html, https://realpython.com/async-io-python/"}
    )
    
    if error:
        print(f"Error: {error}")
    else:
        print(result)


# Example 4: Combined with file tools
def example_combined_tools():
    """Use Tavily together with file tools."""
    
    manager = ToolExecutionManager(
        mode=ToolExecutionMode.AUTO_SAFE,
        sandbox_dir=Path("./workspace"),
        allow_write=True,
        enable_tavily=True,
        tavily_api_key="tvly-YOUR_API_KEY_HERE",
    )
    
    # Search for information
    search_result, _ = manager.execute_tool(
        "tavily_search",
        {"query": "Python decorators tutorial"}
    )
    
    # Save findings to file
    if search_result:
        manager.execute_tool(
            "write_file",
            {"path": "python_decorators_research.md", "content": search_result}
        )
        print("Research saved to python_decorators_research.md")


if __name__ == "__main__":
    print("Tavily Integration Examples")
    print("=" * 50)
    print("\nTo use these examples:")
    print("1. Get API key from https://tavily.com")
    print("2. Configure: miru config set tavily_api_key tvly-YOUR_KEY")
    print("3. Run this file\n")
    
    # Uncomment to run examples:
    # example_basic_usage()
    # example_explicit_api_key()
    # example_extract_urls()
    # example_combined_tools()