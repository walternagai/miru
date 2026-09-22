# AGENTS.md — Miru

Guia para agentes de IA trabalhando neste repositório.

## Visão Geral

Miru (見る — "ver/olhar") é uma CLI Python para servidor Ollama local com suporte multimodal, benchmarking, function calling e i18n.

**Versão:** 0.6.0 · **Python:** >=3.10 (não 3.11+)

## Stack

| Camada | Tecnologia |
|--------|-----------|
| CLI | **Typer** + Rich (não Click) |
| AI | Ollama API (HTTP via httpx) |
| TUI | Textual |
| Build | pyproject.toml (hatchling) |

## Comandos de desenvolvimento

```bash
pip install -e ".[dev]"
pytest tests/ -q --tb=short        # suíte completa: ~2 min, 1251 testes
pytest tests/test_history.py -q    # um arquivo
pytest tests/test_history.py::TestSearchAndClear::test_clear_history  # um teste
ruff check miru/                   # TODO o pacote passa limpo
```

### Comandos que existem de fato

`version`, `list`, `info`, `pull`, `run`, `chat`, `tui`, `compare`, `delete`, `copy`,
`embed`, `batch`, `status`, `ps`, `stop`, `search`, `setup`, `quick`, `examples`,
`completion`, e os subgrupos `history`, `logs`, `config`, `template`, `alias`, `session`, `tools`.

- **Não existe** `miru help` nem `miru help <cmd>` → exit 2. `miru --help`/`miru -h` **sem argumentos** imprime ajuda categorizada.
- **Não existe** `miru export`. Exportação é `miru session export`.
- `miru search` filtra **modelos locais** por nome; não é busca semântica.

### Armadilha do `-h`

O `-h` é sobrecarregado: no app é `--help`, mas em vários comandos (`search`, `quick`,
`batch`, `embed`, `setup`, `list`, e os de status) é atalho de `--host`. `miru search -h`
falha com `Option '-h' requires an argument`. Use sempre `--help`.

## Verificação (escopo real)

`.kata/config.yaml` declara o escopo canônico que o `kata --check-only`/judge re-executa:

```
lint:             ruff check miru/ui/tui/
test:             pytest tests/ -q --tb=short
coverage:         pytest tests/ --cov=miru --cov-report=term-missing -q
gate de coverage: 85   (real atual: 87%)
```

Cuidados ao verificar:

- **`ruff check miru/` passa limpo, mas `ruff check tests/` tem ~437 erros pré-existentes.** Não rode `ruff check .` e não "conserte" `tests/` — é dívida conhecida, fora do escopo.
- **`mypy miru/` NÃO passa**: `strict = true` está configurado, mas há ~104 erros pré-existentes em 26 arquivos. Não use mypy como gate.
- `.kata/` é **gitignored** (local). Um clone novo não terá `.kata/config.yaml`; rode as verificações acima manualmente nesse caso.
- Não há CI nem pre-commit. As verificações só rodam quando alguém as roda.

## Estrutura

```
miru/
├── cli.py            # App Typer; registra comandos e subgrupos
├── commands/         # Um módulo por comando (run, chat, quick, embed, ...)
├── core/             # config.py (canônico), i18n.py, errors.py
├── ollama/client.py  # Cliente HTTP (streaming via aiter_lines)
├── tools/            # Function calling: registry, approval, execution, files sandbox
├── ui/tui/           # App Textual
├── output/           # Formatter, renderer, live_stream
├── config.py         # LEGADO — só get_host/DEFAULT_HOST
└── config_manager.py # Shim de compatibilidade -> core.config
```

Sem `__main__.py`: **`python -m miru` não funciona**. Use o console script `miru` ou chame `miru.cli:main`.

## Convenções específicas do repo

### Host do Ollama — use `resolve_host`

`miru/core/config.py:resolve_host` é a fonte canônica, com 5 níveis:
`--host` CLI > `OLLAMA_HOST` > `MIRU_DEFAULT_HOST` > config file (`default_host`) > default.

`miru.config.get_host` é legado com apenas 3 níveis e **não deve ser usado por comandos**.
`miru.config_manager` é só re-export de `core.config` — código novo importa de `miru.core.config`.

### i18n

Três locales: `pt_BR`, `en_US` (default), `es_ES`. `t("chave")` cai para `en_US` e,
em último caso, retorna a própria chave (falha silenciosa).

**Toda chave usada em `t("...")` precisa existir nos 3 locales** —
`tests/test_core_i18n.py::TestMessageKeyCoverage` varre `miru/**.py`, extrai as chaves
usadas e falha se faltar em algum locale. Ao adicionar `t("nova.chave")`, adicione nos 3.

`tests/conftest.py` tem fixture autouse que restaura o idioma global: `set_language()`
em um teste vaza para os outros sem ela.

### Testes

- `asyncio_mode = "auto"`: `async def test_*` funciona sem decorator.
- Não exigem Ollama real nem rede — clientes são mockados.
- Arquivos de estado (`HISTORY_FILE`, etc.) são redirecionados por fixture para `tmp_path`.
- A suíte completa leva ~2 min; com `--cov` passa de 4 min. Ajuste o timeout.

### Tools / sandbox

Tools são opt-in: `create_tool_manager` retorna `None` sem `--enable-tools`/`--tavily` (ou
`enable_tools` no config). Quando ligadas, o `sandbox_dir` default é **`./.miru_sandbox`**
(criado no cwd), não "sem sandbox".

`ToolExecutionManager` tem modos `disabled`/`manual`/`auto`/`auto_safe` (default
`auto_safe`) e passa por `ToolApprovalManager` (aprovação interativa). `run_command` usa
`shell=False` + whitelist com `shlex.split`, rejeita metacaracteres de shell e valida
`allowed_args` por token.

## Regras

- Type hints em todas as funções; `ruff` (E, F, I, N, W, UP; `E501` ignorado, line-length 100) limpo em `miru/`.
- Typer para CLI, Rich para output formatado.
- Commits em inglês, Conventional Commits (`fix(scope):`, `test:`, `refactor:`).
- Branch único `main`; sem fluxo de PR documentado.
