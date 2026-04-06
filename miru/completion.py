"""Shell completion generation for bash, zsh, and fish."""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

console = Console()

BASH_COMPLETION = """# miru bash completion

_miru_completion() {
    local cur words
    cur="${COMP_WORDS[COMP_CWORD]}"
    words=()

    if [[ ${COMP_CWORD} -eq 1 ]]; then
        words=(
            'list' 'info' 'pull' 'run' 'chat' 'compare'
            'delete' 'copy' 'embed' 'batch' 'status'
            'ps' 'stop' 'search' 'config' 'history'
            'template' 'alias' 'logs' 'completion' 'version'
        )
    else
        case ${COMP_WORDS[1]} in
            run|chat|compare|batch)
                if [[ ${COMP_CWORD} -eq 2 ]]; then
                    # Try to get models from miru list --quiet
                    local models
                    models=$(miru list --quiet 2>/dev/null)
                    if [[ -n $models ]]; then
                        words=($models)
                    fi
                else
                    words=(--system --system-file --temperature --top-p --top-k
                           --max-tokens --seed --repeat-penalty --ctx --no-stream
                           --host --format --quiet --verbose)
                fi
                ;;
            info|pull|delete)
                if [[ ${COMP_CWORD} -eq 2 ]]; then
                    local models
                    models=$(miru list --quiet 2>/dev/null)
                    words=($models)
                fi
                ;;
            config)
                words=(set get list profile path reset)
                ;;
            template)
                words=(list save show delete run export import)
                ;;
            alias)
                words=(add list delete show)
                ;;
            history)
                words=(--limit --command --search --clear --format)
                ;;
        esac
    fi

    COMPREPLY=($(compgen -W "${words[*]}" -- "${cur}"))
}

complete -F _miru_completion miru
"""

ZSH_COMPLETION = """#compdef miru

local -a commands
commands=(
    'list:List available models'
    'info:Show model information'
    'pull:Download a model'
    'run:Generate text with a single prompt'
    'chat:Start interactive chat session'
    'compare:Compare responses from multiple models'
    'delete:Delete a model'
    'copy:Copy a model'
    'embed:Generate embeddings'
    'batch:Process multiple prompts'
    'status:Check Ollama server status'
    'ps:List loaded models'
    'stop:Unload a model'
    'search:Search models'
    'config:Manage configuration'
    'history:View prompt history'
    'template:Manage prompt templates'
    'alias:Manage model aliases'
    'logs:View logs'
    'completion:Generate shell completion'
    'version:Show version'
)

local -a common_opts
common_opts=(
    '--host[Ollama host URL]:host'
    '--format[Output format]:format:(text json jsonl)'
    '--quiet[Minimal output]'
    '--verbose[Verbose output]'
)

__miru_models() {
    local models
    models=$(miru list --quiet 2>/dev/null)
    _values 'models' ${(f)models}
}

_arguments -s \\
    '1:command:->commands' \\
    '*::arguments:->args'

case $state in
    commands)
        _describe 'command' commands
        ;;
    args)
        case $words[1] in
            run|chat|compare|batch)
                if (( CURRENT == 2 )); then
                    __miru_models
                else
                    _arguments \\
                        '--system[System prompt]:system' \\
                        '--system-file[System prompt file]:file:_files' \\
                        '--temperature[Temperature]:temperature' \\
                        '--top-p[Nucleus sampling]:top_p' \\
                        '--top-k[Top-k sampling]:top_k' \\
                        '--max-tokens[Max tokens]:tokens' \\
                        '--seed[Random seed]:seed' \\
                        '--host[Host URL]:host' \\
                        '--format[Format]:format:(text json)' \\
                        '--quiet[Quiet mode]' \\
                        '--verbose[Verbose mode]'
                fi
                ;;
            info|pull|delete)
                if (( CURRENT == 2 )); then
                    __miru_models
                fi
                ;;
            config)
                _values 'action' set get list profile path reset
                ;;
            template)
                _values 'action' list save show delete run export import
                ;;
            alias)
                _values 'action' add list delete show
                ;;
        esac
        ;;
esac
"""

FISH_COMPLETION = """# miru fish completion

complete -c miru -f

# Main commands
complete -c miru -n __fish_use_subcommand -a list -d 'List available models'
complete -c miru -n __fish_use_subcommand -a info -d 'Show model information'
complete -c miru -n __fish_use_subcommand -a pull -d 'Download a model'
complete -c miru -n __fish_use_subcommand -a run -d 'Generate text with a single prompt'
complete -c miru -n __fish_use_subcommand -a chat -d 'Start interactive chat session'
complete -c miru -n __fish_use_subcommand -a compare -d 'Compare responses from multiple models'
complete -c miru -n __fish_use_subcommand -a delete -d 'Delete a model'
complete -c miru -n __fish_use_subcommand -a copy -d 'Copy a model'
complete -c miru -n __fish_use_subcommand -a embed -d 'Generate embeddings'
complete -c miru -n __fish_use_subcommand -a batch -d 'Process multiple prompts'
complete -c miru -n __fish_use_subcommand -a status -d 'Check Ollama server status'
complete -c miru -n __fish_use_subcommand -a ps -d 'List loaded models'
complete -c miru -n __fish_use_subcommand -a stop -d 'Unload a model'
complete -c miru -n __fish_use_subcommand -a search -d 'Search models'
complete -c miru -n __fish_use_subcommand -a config -d 'Manage configuration'
complete -c miru -n __fish_use_subcommand -a history -d 'View prompt history'
complete -c miru -n __fish_use_subcommand -a template -d 'Manage prompt templates'
complete -c miru -n __fish_use_subcommand -a alias -d 'Manage model aliases'
complete -c miru -n __fish_use_subcommand -a logs -d 'View logs'
complete -c miru -n __fish_use_subcommand -a completion -d 'Generate shell completion'
complete -c miru -n __fish_use_subcommand -a version -d 'Show version'

# Model completion for run, chat, info, pull, delete
complete -c miru -n '__fish_seen_subcommand_from run chat compare batch' -a '(miru list --quiet)'
complete -c miru -n '__fish_seen_subcommand_from info pull delete' -a '(miru list --quiet)'

# Common options
complete -c miru -l host -d 'Ollama host URL'
complete -c miru -l format -d 'Output format' -a 'text json jsonl'
complete -c miru -l quiet -s q -d 'Minimal output'
complete -c miru -l verbose -s v -d 'Verbose output'

# run/chat options
complete -c miru -n '__fish_seen_subcommand_from run chat' -l system -d 'System prompt'
complete -c miru -n '__fish_seen_subcommand_from run chat' -l system-file -d 'System prompt file'
complete -c miru -n '__fish_seen_subcommand_from run chat' -l temperature -d 'Sampling temperature'
complete -c miru -n '__fish_seen_subcommand_from run chat' -l max-tokens -d 'Max tokens to generate'
complete -c miru -n '__fish_seen_subcommand_from run chat' -l seed -d 'Random seed'

# config subcommands
complete -c miru -n '__fish_seen_subcommand_from config' -a 'set get list profile path reset'

# template subcommands
complete -c miru -n '__fish_seen_subcommand_from template' -a 'list save show delete run export import'

# alias subcommands
complete -c miru -n '__fish_seen_subcommand_from alias' -a 'add list delete show'
"""


def completion(
    shell: Annotated[str, typer.Argument(help="Shell type: bash, zsh, fish")] = "bash",
    output: Annotated[str | None, typer.Option("--output", "-o", help="Output file")] = None,
) -> None:
    """Generate shell completion script.

    Examples:
        miru completion bash > ~/.local/share/bash-completion/completions/miru
        miru completion zsh > ~/.zsh/completions/_miru
        miru completion fish > ~/.config/fish/completions/miru.fish
    """
    if shell == "bash":
        script = BASH_COMPLETION
    elif shell == "zsh":
        script = ZSH_COMPLETION
    elif shell == "fish":
        script = FISH_COMPLETION
    else:
        console.print(f"[red bold]✗[/] Shell não suportado: {shell}")
        console.print("[dim]Shells suportados: bash, zsh, fish")
        raise typer.Exit(code=1)

    if output:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(script, encoding="utf-8")
        console.print(f"[green bold]✓[/] Completion script saved to {output}")
        console.print()
        console.print("[dim]Para ativar:[/]")
        if shell == "bash":
            console.print(f"  source {output}")
        elif shell == "zsh":
            console.print(f"  Adicione ao .zshrc: fpath+=({path.parent})")
        elif shell == "fish":
            console.print(f"  O arquivo já está emFish completions directory")
    else:
        print(script)
