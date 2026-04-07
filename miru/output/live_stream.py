"""Live streaming module for real-time Markdown rendering."""

import re
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

from rich.console import Console,Group
from rich.live import Live
from rich.markdown import Markdown
from rich.syntax import Syntax

if TYPE_CHECKING:
    pass

console = Console()


def _detect_code_blocks(text: str) -> tuple[str, list[tuple[str, str]]]:
    """
    Detect complete and incomplete code blocks in text.
    
    Returns:
        Tuple of (text_without_complete_blocks, list of (lang, code) tuples)
    """
    pattern = r'```(\w*)\n(.*?)```'
    matches = list(re.finditer(pattern, text, re.DOTALL))
    
    code_blocks = []
    for match in matches:
        lang = match.group(1) or "text"
        code = match.group(2)
        code_blocks.append((lang, code))
    
    return text, code_blocks


def _render_with_syntax_highlight(text: str) -> Markdown:
    """
    Render text with syntax highlighting for complete code blocks.
    
    Incomplete code blocks remain as plain text until completed.
    
    Args:
        text: Full text buffer
        
    Returns:
        Rich Markdown object with highlighted code blocks
    """
    md = Markdown(text)
    return md


def _has_incomplete_code_block(text: str) -> bool:
    """
    Check if there's an incomplete code block.
    
    Returns:
        True if there's an odd number of ``` markers
    """
    return text.count("```") % 2 == 1


def _get_incomplete_code_block(text: str) -> str | None:
    """
    Get the language and content of an incomplete code block.
    
    Returns:
        Tuple of (language, code) or None if no incomplete block
    """
    if not _has_incomplete_code_block(text):
        return None
    
    last_fence = text.rfind("```")
    if last_fence == -1:
        return None
    
    after_fence = text[last_fence + 3:]
    lines = after_fence.split("\n", 1)
    
    if len(lines) == 1:
        return lines[0] if lines[0] else ""
    
    return lines[1] if len(lines) > 1 else None


async def stream_as_markdown_live(
    chunks: AsyncIterator[dict],
    quiet: bool = False,
    show_metrics: bool = True,
) -> tuple[str, dict | None]:
    """
    Stream chunks in real-time with Rich Live Display.
    
    Features:
    - Line buffer: renders on encountering \\n
    - Progressive Markdown rendering
    - Syntax highlighting for complete code blocks
    - Metrics display at end
    
    Args:
        chunks: Async iterator of response chunks
        quiet: If True, suppress all output (only return text)
        show_metrics: If True, show metrics after rendering
        
    Returns:
        Tuple of (full_response_text, final_chunk)
    """
    from miru.output.renderer import render_metrics
    
    text_buffer = ""
    final_chunk = None
    
    if quiet:
        async for chunk in chunks:
            content = chunk.get("response", "") or chunk.get("message", {}).get("content", "")
            if content:
                text_buffer += content
            
            if chunk.get("done"):
                final_chunk = chunk
        
        return text_buffer, final_chunk
    
    with Live(console=console, refresh_per_second=10, vertical_overflow="visible") as live:
        async for chunk in chunks:
            content = chunk.get("response", "") or chunk.get("message", {}).get("content", "")
            
            if content:
                text_buffer += content
                
                md = _render_with_syntax_highlight(text_buffer)
                live.update(md)
            
            if chunk.get("done"):
                final_chunk = chunk
    
    if show_metrics and final_chunk and text_buffer:
        print()
        render_metrics(final_chunk)
    
    return text_buffer, final_chunk