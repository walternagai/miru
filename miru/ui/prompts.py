"""Interactive prompts for user input.

Provides consistent user interaction patterns.
"""

from typing import TypeVar

from rich.console import Console
from rich.prompt import Prompt

console = Console()

T = TypeVar("T")


def confirm(
    message: str,
    default: bool = False,
) -> bool:
    """Prompt user for confirmation.
    
    Args:
        message: Prompt message
        default: Default value if user presses Enter
        
    Returns:
        True if confirmed, False otherwise
        
    Example:
        >>> if confirm("Delete file?", default=False):
        ...     delete_file()
    """
    return Prompt.ask(
        f"[bold]{message}[/]",
        choices=["y", "n"],
        default="y" if default else "n",
    ).lower() == "y"


def prompt_input(
    message: str,
    default: str | None = None,
    password: bool = False,
) -> str:
    """Prompt user for text input.
    
    Args:
        message: Prompt message
        default: Default value
        password: Whether to hide input
        
    Returns:
        User input string
        
    Example:
        >>> name = prompt_input("Enter name:", default="anonymous")
    """
    return Prompt.ask(
        f"[bold]{message}[/]",
        default=default,
        password=password,
    )


def prompt_choice(
    message: str,
    choices: list[str],
    default: str | None = None,
) -> str:
    """Prompt user to choose from a list.
    
    Args:
        message: Prompt message
        choices: List of valid choices
        default: Default choice
        
    Returns:
        Selected choice
        
    Example:
        >>> language = prompt_choice(
        ...     "Select language:",
        ...     choices=["pt_BR", "en_US", "es_ES"],
        ...     default="en_US",
        ... )
    """
    return Prompt.ask(
        f"[bold]{message}[/]",
        choices=choices,
        default=default,
    )


def prompt_multiselect(
    message: str,
    options: list[str],
    defaults: list[str] | None = None,
) -> list[str]:
    """Prompt user to select multiple options.
    
    Args:
        message: Prompt message
        options: Available options
        defaults: Default selections
        
    Returns:
        List of selected options
        
    Example:
        >>> selected = prompt_multiselect(
        ...     "Select features:",
        ...     options=["tools", "history", "templates"],
        ...     defaults=["history"],
        ... )
    """
    console.print(f"[bold]{message}[/]")
    
    for i, option in enumerate(options, 1):
        default_marker = " (default)" if defaults and option in defaults else ""
        console.print(f"  {i}. {option}{default_marker}")
    
    console.print()
    console.print("[dim]Enter numbers separated by spaces, or press Enter for defaults[/]")
    
    answer = Prompt.ask("Selection", default="").strip()
    
    if not answer:
        return defaults or []
    
    try:
        indices = [int(x) for x in answer.split()]
        return [options[i - 1] for i in indices if 1 <= i <= len(options)]
    except (ValueError, IndexError):
        return defaults or []