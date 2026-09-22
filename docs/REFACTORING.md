# Refatoração do Miru - Documentação de Mudanças

## Visão Geral

Esta refatoração implementa o plano principal de melhorias de usabilidade, focando em:

1. **Sistema de i18n** com suporte a Português (Brasil), Inglês e Espanhol
2. **Módulo core/** com configuração unificada e tratamento de erros
3. **Módulo ui/** separado da lógica de negócio
4. **Short flags consistentes** em todos os comandos

## Estrutura de Diretórios

```
miru/
├── core/               # NOVO - Config, errors, i18n
│   ├── __init__.py
│   ├── config.py      # Configuração unificada
│   ├── errors.py      # Exceções customizadas
│   └── i18n.py        # Sistema de internacionalização
├── ui/                 # NOVO - Interface do usuário
│   ├── __init__.py
│   ├── progress.py    # Barras de progresso
│   ├── prompts.py     # Prompts interativos
│   └── render.py      # Renderização de output
├── cli_options.py      # NOVO - Flags CLI consistentes
├── config_manager.py   # MODIFICADO - Wrapper de compatibilidade
└── ...                 # Resto dos módulos existentes
```

## Sistema de Internacionalização (i18n)

### Uso Básico

```python
from miru.core.i18n import t, set_language, init_i18n

# Inicialização automática no import
# Usa MIRU_LANG, LANG, ou locale do sistema

# Trocar idioma manualmente
set_language("pt_BR")  # ou "en_US", "es_ES"

# Traduzir mensagens
msg = t("error.model_not_found", model="gemma3")
# PT: "Modelo 'gemma3' não encontrado."
# EN: "Model 'gemma3' not found."
# ES: "Modelo 'gemma3' no encontrado."
```

### Detecção de Idioma

Precedência:
1. Variável de ambiente `MIRU_LANG` (ex: `MIRU_LANG=pt_BR`)
2. Variável de ambiente `LANG` (sistema)
3. Locale do sistema
4. Default: `en_US`

### Mensagens Disponíveis

Categorizadas em:
- `error.*`: Mensagens de erro
- `success.*`: Mensagens de sucesso
- `suggestion.*`: Sugestões de ação
- `chat.*`: Comandos e estados do chat
- `tools.*`: Mensagens de tools
- `models.*`: Operações de modelo
- `config.*`: Configuração
- `setup.*`: Wizard de setup
- `status.*`: Status do sistema

## Módulo de Erros (core/errors.py)

### Exceções Customizadas

```python
from miru.core.errors import ModelNotFoundError, ConnectionError

# ModelNotFoundError com sugestões automáticas
raise ModelNotFoundError("gemma3", available_models=["llama3", "qwen2"])
# Mensagem: "Modelo 'gemma3' não encontrado."
# Sugestão: "Available models:\n  • llama3\n  • qwen2\n\nPara baixar: miru pull gemma3"

# ConnectionError com sugestões
raise ConnectionError("http://localhost:11434")
# Mensagem: "Falha ao conectar em 'http://localhost:11434'."
# Sugestão: "Certifique-se de que o Ollama está rodando: ollama serve"
```

### Hierarquia

```
MiruError (base)
├── ModelNotFoundError
├── ConnectionError
├── ValidationError
├── ToolExecutionError
├── ConfigError
└── FileProcessingError
```

## Módulo UI

### Renderização (ui/render.py)

```python
from miru.ui.render import render_error, render_success, render_warning, render_info
from miru.core.i18n import t, set_language

set_language("pt_BR")
render_error(t("error.model_not_found", model="test"))
# ✗ Modelo 'test' não encontrado.

render_success(t("success.session_saved", filename="session.json"))
# ✓ Sessão salva em 'session.json'.

render_warning("Operação pode demorar")
# ⚠ Operação pode demorar

render_info("Processando arquivos...")
# ℹ Processando arquivos...
```

### Progresso (ui/progress.py)

```python
from miru.ui.progress import ProgressReporter, track_progress

# Context manager
with track_progress("Comparando modelos", total=3) as progress:
    for model in models:
        result = run_model(model)
        progress.update()

# Manual
reporter = ProgressReporter("Processando")
reporter.start(total=100)
for i in range(100):
    process(i)
    reporter.update()
reporter.stop()
```

### Prompts Interativos (ui/prompts.py)

```python
from miru.ui.prompts import confirm, prompt_input, prompt_choice

# Confirmação
if confirm("Delete file?", default=False):
    delete_file()

# Input de texto
name = prompt_input("Enter name:", default="anonymous")

# Escolha única
language = prompt_choice(
    "Select language:",
    choices=["pt_BR", "en_US", "es_ES"],
    default="en_US",
)
```

## CLI Options Padronizadas (cli_options.py)

### Flags Curtas Consistentes

**Antes:**
```python
# Verboso e inconsistente
miru run gemma3 "test" --system "prompt" --image photo.jpg --file doc.pdf --temperature 0.7
```

**Depois:**
```python
# Flags curtas consistentes
miru run gemma3 "test" -s "prompt" -i photo.jpg -f doc.pdf --temperature 0.7
```

### Mapeamento Completo

| Flag Longa      | Flag Curta | Descrição                    |
|-----------------|------------|------------------------------|
| `--host`        | `-h`       | URL do servidor Ollama       |
| `--format`      | `-f`       | Formato de output (text/json) |
| `--quiet`       | `-q`       | Output minimal               |
| `--verbose`     | `-v`       | Output verboso               |
| `--system`      | `-s`       | System prompt                |
| `--image`       | `-i`       | Arquivo de imagem            |
| `--file`        | `-f`       | Arquivo de input             |
| `--audio`       | `-a`       | Arquivo de áudio             |
| `--temperature` | `-t`       | Temperatura de amostragem    |
| `--max-tokens`  | `-m`       | Máximo de tokens             |
| `--top-p`       | `-p`       | Nucleus sampling             |
| `--top-k`       | `-k`       | Top-k sampling               |
| `--timeout`     |            | Timeout em segundos          |
| `--ctx`         | `-c`       | Janela de contexto           |
| `--force`       | `-f`       | Pular confirmação            |

## Configuração Unificada (core/config.py)

### Melhorias

1. **Módulo único**: Configuração agrupada em um arquivo
2. **Cache**: Config carregada uma vez e cacheada
3. **Precedência clara**: CLI > Env > Config > Default
4. **Suporte a idioma**: Config armazena preferência de idioma

### Uso

```python
from miru.core.config import get_config, reload_config, Config

# Obter config (cacheada)
config = get_config()
print(config.default_model)
print(config.language)

# Recarregar do disco
config = reload_config()

# Modificar e salvar
config.language = "pt_BR"
save_config(config)
```

## Compatibilidade

### Módulos Antigos

Todos os módulos antigos mantêm compatibilidade através de wrappers:

```python
# config_manager.py é um wrapper para core/config.py
from miru.config_manager import load_config  # Ainda funciona

# renderer.py é um wrapper para output/renderer.py
from miru.renderer import render_error  # Ainda funciona
```

### Migração Gradual

Os módulos podem ser migrados gradualmente:

1. **Fase 1**: Usar `from miru.core.i18n import t` em novos comandos
2. **Fase 2**: Atualizar comandos existentes um por vez
3. **Fase 3**: Remover wrappers legados

## Benefícios

### Para Usuários

1. **Idiomas**: Interface em PT-BR, EN-US, ES-ES
2. **Flags curtas**: Comandos mais concisos
3. **Mensagens consistentes**: Estilo uniforme
4. **Sugestões úteis**: Erros com contexto

### Para Desenvolvedores

1. **Separação clara**: UI vs lógica
2. **Testável**: Módulos isolados
3. **Extensível**: Fácil adicionar idiomas
4. **Manutenível**: Código organizado

## Próximos Passos

1. **i18n em `info.py` e `list.py`** — os dois únicos comandos que ainda não usam `t()`
2. **Adicionar mais idiomas**: Fácil adicionar mensagens para novos idiomas
3. **Remover wrappers legados**: `config_manager.py` e `renderer.py` (Fase 3 da migração)
4. **Reduzir dívida de lint/testes**: ~437 erros ruff em `tests/`, ~104 erros mypy em `miru/`

## Variáveis de Ambiente

```bash
# Idioma
export MIRU_LANG=pt_BR

# Config padrões (sobrescrevem config.toml)
export MIRU_DEFAULT_MODEL=gemma3:latest
export MIRU_DEFAULT_HOST=http://localhost:11434
export MIRU_ENABLE_TOOLS=true
export MIRU_ENABLE_TAVILY=true

# Ollama host (padrão do Ollama)
export OLLAMA_HOST=http://localhost:11434
```

## Exemplos de Uso

### Idiomas

```bash
# Português (Brasil)
export MIRU_LANG=pt_BR
miru run gemma3 "Explique recursão"
# ✗ Modelo 'gemma3' não encontrado.
# Para baixar: miru pull gemma3

# Inglês
export MIRU_LANG=en_US
miru run gemma3 "Explain recursion"
# ✗ Model 'gemma3' not found.
# To download: miru pull gemma3

# Espanhol
export MIRU_LANG=es_ES
miru run gemma3 "Explica recursión"
# ✗ Modelo 'gemma3' no encontrado.
# Para descargar: miru pull gemma3
```

### Short Flags

```bash
# Antes
miru run llama3 "test" --system "be concise" --image photo.png --temperature 0.7

# Depois
miru run llama3 "test" -s "be concise" -i photo.png --temperature 0.7

# Comandos chat também suportam
miru chat llama3 -s "be helpful" --temperature 0.7
```

> Nota: `-t` é `--timeout` (segundos) em `run`/`chat`/`batch`, não temperatura.
> `--temperature` não tem flag curta.

## Checklist de Implementação

- [x] Sistema de i18n (pt_BR, en_US, es_ES)
- [x] Módulo core/errors.py
- [x] Módulo core/config.py
- [x] Módulo ui/render.py
- [x] Módulo ui/progress.py
- [x] Módulo ui/prompts.py
- [x] cli_options.py com short flags
- [x] Wrapper de compatibilidade config_manager.py
- [x] Atualização do __init__.py
- [x] Refatorar commands/chat.py
- [x] Refatorar commands/run.py
- [x] Refatorar commands/compare.py
- [x] Refatorar commands/batch.py
- [x] Refatorar outros comandos (16 de 18 importam i18n; `info.py` e `list.py` ainda não usam `t()`)
- [x] Testes de integração (`tests/test_integration.py`, `tests/test_tool_integration.py`)
- [x] Documentação atualizada

> Atualizado em 2026-09-22: os comandos pendentes acima foram refatorados entre
> os releases 0.5.0 e 0.6.0. O wrapper `renderer.py` continua valendo.
