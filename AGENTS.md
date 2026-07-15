# AGENTS.md — Miru

Guia para agentes de IA trabalhando neste repositório.

## Visão Geral

Miru (見る — "ver/olhar") é uma CLI Python para servidor Ollama local com suporte multimodal, benchmarking, function calling e internacionalização (i18n). Permite visualizar e interagir com modelos de IA através de comandos intuitivos.

**Versão:** 0.5.0

## Stack

| Camada | Tecnologia |
|--------|-----------|
| Linguagem | Python 3.11+ |
| CLI | Click + Rich |
| AI | Ollama API (HTTP) |
| TUI | Textual (Rich-based) |
| Build | pyproject.toml |

## Comandos

```bash
pip install miru            # Instalação
miru setup                  # Setup interativo
miru chat                   # Modo chat
miru run <model> <prompt>   # Execução direta
miru compare <model-a> <model-b>  # Comparação
miru history                # Histórico de sessões
miru export                 # Exportar conversas
miru search <query>         # Busca semântica
miru help                   # Ajuda

# Desenvolvimento
pip install -e ".[dev]"
pytest -v
ruff check miru/
mypy miru/
```

## Estrutura

```
miru/
├── miru/              # Pacote principal
│   ├── cli.py         # Entry point (Click)
│   ├── commands/      # Comandos (chat, run, compare, etc.)
│   ├── core/          # Lógica central
│   ├── ollama/        # Integração com Ollama API
│   ├── ui/            # Interface de usuário
│   ├── tools/         # Function calling
│   └── output/        # Formatadores de saída
├── tests/             # Testes
└── docs/              # Documentação
```

## Regras

- Type hints em todas as funções
- Click para CLI, Rich para output formatado
- i18n: mensagens em resource files
- Testes com pytest
- Ruff + mypy antes de commit
- Commits em inglês (Conventional Commits)
