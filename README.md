# miru

**CLI Python para servidor Ollama local com suporte multimodal, benchmarking, function calling e internacionalização (i18n).**

Miru (見る) significa "ver" ou "olhar" em japonês. Representa a capacidade de visualizar e interagir com modelos de IA através de comandos claros e intuitivos, com suporte completo a function calling para que modelos executem ações no seu sistema.

**Versão 0.5.0** - Novo: `/recall` para resgatar prompts anteriores e renderização Markdown em todos os comandos.

## Novidades da Versão 0.5.0

### `/recall` - Resgate Prompts Anteriores

No modo interativo (`miru chat`), use `/recall` para reutilizar prompts de sessões anteriores:

```bash
>>> /recall           # Lista interativa dos últimos 10 prompts
>>> /recall 3         # Carrega diretamente o prompt de índice 3
```

### Markdown Renderizado em Todo Lugar

Agora as respostas em Markdown são exibidas com formatação Rich:

- `miru history show <index>` - Respostas renderizadas
- `miru run --no-stream` - Output formatado
- Headers, código, tabelas, listas sempre bem formatados

## Instalação

```bash
pip install miru
```

## Início Rápido

```bash
# Setup interativo para novos usuários
miru setup

# Ver todos os comandos disponíveis
miru --help

# Ver versão e descrição
miru version
```

## Internacionalização (i18n)

O miru suporta **3 idiomas**: Português (Brasil), English, e Español.

### Definir Idioma

```bash
# Português (Brasil)
export MIRU_LANG=pt_BR

# English
export MIRU_LANG=en_US

# Español  
export MIRU_LANG=es_ES

# Ou via configuração
miru config set language pt_BR
```

### Exemplos por Idioma

**Português (Brasil):**
```bash
$ export MIRU_LANG=pt_BR
$ miru run modelo-inexistente "teste"
✗ Modelo 'modelo-inexistente' não encontrado.
Modelos disponíveis localmente:
  • gemma3:latest
  • qwen2.5:7b
  
Para baixar: miru pull modelo-inexistente
```

**English:**
```bash
$ export MIRU_LANG=en_US
$ miru run nonexistent-model "test"
✗ Model 'nonexistent-model' not found.
Available models locally:
  • gemma3:latest
  • qwen2.5:7b

To download: miru pull nonexistent-model
```

**Español:**
```bash
$ export MIRU_LANG=es_ES
$ miru run modelo-inexistente "prueba"
✗ Modelo 'modelo-inexistente' no encontrado.
Modelos disponibles localmente:
  • gemma3:latest
  • qwen2.5:7b

Para descargar: miru pull modelo-inexistente
```

### Idiomas Suportados

| Código  | Idioma          | Cobertura |
|---------|-----------------|-----------|
| pt_BR   | Português (BR)  | 100%      |
| en_US   | English         | 100%      |
| es_ES   | Español         | 100%      |

## Short Flags Padronizadas

A versão 0.4.0 introduz short flags consistentes em todos os comandos:

```bash
# Antes (verboso)
miru run gemma3 "test" --system "be concise" --temperature 0.7 --format json --quiet

# Depois (com short flags)
miru run gemma3 "test" -s "be concise" -t 0.7 -f json -q

# Host e formato
miru list -h http://custom:11434 -f json

# Imagens e arquivos
miru run llava "describe" -i photo.jpg -f document.txt

# Temperatura e parâmetros
miru run model "prompt" -t 0.7 -m 500 -p 0.9 -k 40
```

### Mapeamento Completo

| Flag Longa      | Flag Curta | Descrição                    |
|-----------------|------------|------------------------------|
| `--host`        | `-h`       | URL do servidor Ollama       |
| `--format`      | `-f`       | Formato de output (text/json)|
| `--quiet`       | `-q`       | Output minimal               |
| `--system`      | `-s`       | System prompt                |
| `--image`       | `-i`       | Arquivo de imagem            |
| `--file`        | `-f`       | Arquivo de input             |
| `--audio`       | `-a`       | Arquivo de áudio             |
| `--temperature` | `-t`       | Temperatura de amostragem    |
| `--max-tokens`  | `-m`       | Máximo de tokens             |
| `--top-p`       | `-p`       | Nucleus sampling             |
| `--top-k`       | `-k`       | Top-k sampling               |
| `--ctx`         | `-c`       | Janela de contexto           |

## Uso

### Comandos Básicos

#### Listar modelos

```bash
miru list
miru list --format json    # ou: -f json
miru list --quiet          # ou: -q
```

#### Informações do modelo

```bash
miru info gemma3:latest
miru info qwen2.5:7b --format json
```

#### Baixar modelo

```bash
miru pull gemma3:latest
miru pull llava:latest --quiet
```

#### Deletar modelo

```bash
miru delete gemma3:latest
miru delete gemma3:latest --force  # Pular confirmação
```

#### Copiar modelo

```bash
miru copy gemma3:latest gemma3-backup
miru copy gemma3:latest meu-modelo --force
```

### Gerar embeddings

```bash
miru embed nomic-embed-text "Hello world"
miru embed nomic-embed-text --file documento.txt
miru embed nomic-embed-text --batch textos.txt --format jsonl
```

### Executar prompt único

```bash
miru run gemma3:latest "Explique recursão"
miru run llava:latest "Descreva a imagem" -i foto.png
miru run gemma3:latest "Analise o código" -f main.py
miru run gemma3:latest "Transcreva" -a reuniao.mp3

# Com system prompt
miru run gemma3:latest "Explique decorators" -s "Você é um especialista em Python. Seja conciso."

# Com parâmetros de inferência
miru run gemma3:latest "Teste" -t 0.7 --seed 42 -m 200

# Download automático se modelo não existir
miru run gemma3:latest "Teste" --auto-pull

# Formatos de saída
miru run gemma3:latest "Teste" -f json
miru run gemma3:latest "Teste" -q

# Com Tavily web search (requer API key)
miru config set tavily_api_key tvly-sua-api-key
miru run gemma3:latest --tavily "Quais são as novidades do Python 3.13?"

# Com todas as tools habilitadas
miru run gemma3:latest --enable-tools --sandbox-dir ./workspace "Busque informações e salve em arquivo"
```

### Chat interativo

```bash
miru chat gemma3:latest
miru chat llava:latest -i foto.png

# Com system prompt
miru chat gemma3:latest -s "Você é um tutor paciente. Explique com exemplos."

# Modelo padrão configurado
miru config set default_model gemma3:latest
miru chat  # Usa modelo padrão

# Com Tavily web search
miru chat gemma3:latest --tavily
>>> Quais são as últimas notícias sobre IA?

# Com todas as tools habilitadas
miru chat qwen2.5:7b --enable-tools --sandbox-dir ./workspace
>>> Analise este arquivo e busque mais informações na web

# Resgatar prompts anteriores
>>> /recall           # Lista interativa dos últimos 10 prompts
>>> /recall 3         # Carrega diretamente o prompt de índice 3
```

#### Comandos do chat interativo

```
>>> /help              # Lista comandos disponíveis
>>> /exit              # Encerrar sessão
>>> /clear             # Limpar histórico
>>> /history           # Mostrar contagem de turnos
>>> /stats             # Mostrar estatísticas da sessão
>>> /model <name>      # Trocar modelo
>>> /system <prompt>   # Alterar system prompt
>>> /recall [n]        # Resgatar prompt anterior (interativo ou por índice)
>>> /retry             # Re-executar último prompt
>>> /save <arquivo>    # Salvar conversa em arquivo
>>> /export <formato>  # Exportar (json/md/txt)
```

### Histórico de Prompts

O miru mantém um histórico de todos os prompts executados:

```bash
# Listar histórico
miru history

# Ver detalhes de uma entrada
miru history show 0

# Buscar no histórico
miru history --search "python"

# Filtrar por comando
miru history --command run

# Limpar histórico
miru history --clear
```

As respostas em `miru history show` são renderizadas com formatação Markdown (headers, código, tabelas).

### Comparar modelos (benchmark)

```bash
miru compare gemma3:latest qwen2.5:7b --prompt "O que é closure?"
miru compare gemma3 qwen2.5:7b --prompt "Teste" --seed 42
miru compare llava:latest moondream:latest --prompt "Descreva" -i diagrama.png
miru compare gemma3 qwen2.5:7b --prompt "Teste" -f json -q | jq '.[0].metrics'
```

### Processamento em lote

```bash
miru batch gemma3:latest --prompts prompts.txt
miru batch gemma3:latest --prompts data.jsonl --format json
miru batch qwen2.5:7b --prompts prompts.txt -s "Seja conciso"
miru batch gemma3 --prompts prompts.txt -f json
miru batch gemma3 --prompts prompts.txt --format jsonl -q > results.jsonl
miru batch gemma3 --prompts prompts.txt --stop-on-error
miru batch gemma3 --prompts prompts.txt -t 0.7 -m 100
```

## Quick Commands

Comandos rápidos para tarefas comuns:

```bash
miru quick code gemma3 --param language=python --param task="sort a list"
miru quick summarize gemma3 --param text="Long article..."
miru quick explain gemma3 --param topic="machine learning"
miru quick translate-pt gemma3 --param text="Hello world"
miru quick translate-en gemma3 --param text="Olá mundo"
miru quick review-code gemma3 --param language=python --param code="$(cat main.py)"
miru quick fix-code gemma3 --param language=python --param code="$(cat broken.py)"
miru quick test gemma3 --param language=python --param code="$(cat main.py)"
miru quick refactor gemma3 --param language=python --param code="$(cat main.py)"
miru quick document gemma3 --param language=python --param code="$(cat main.py)"
miru quick optimize gemma3 --param language=python --param code="$(cat main.py)"
miru quick analyze gemma3 --param text="Article..."
miru quick grammar gemma3 --param text="Text with errors..."
miru quick expand gemma3 --param text="Short text..."
miru quick simplify gemma3 --param text="Complex text..."
miru quick --list
```

## Setup Wizard

Primeira configuração interativa:

```bash
miru setup
```

O wizard interativo:
- Verifica se Ollama está rodando
- Lista modelos disponíveis
- Permite escolher modelo padrão
- Configura histórico de prompts
- Configura aliases
- Salva preferências em `~/.miru/config.toml`

```bash
miru setup --non-interactive
miru setup --host http://custom:11434
```

## Examples Browser

Navegador de exemplos de uso:

```bash
miru examples --list
miru examples --category code
miru examples --tag python
miru examples hello-world
miru examples hello-world --copy
miru examples --categories
```

Categorias disponíveis: `basics`, `code`, `text`, `translation`, `learning`, `chat`, `advanced`, `multimodal`, `document`, `templates`, `config`

## 🆕 Tools / Function Calling

O miru suporta **function calling** nativo do Ollama, permitindo que modelos executem ações no seu sistema de forma segura e controlada.

### conceitos

- **Tools**: Funções que o modelo pode chamar durante uma conversa
- **Sandbox**: Diretório restrito para operações de arquivo (previne acesso não autorizado)
- **Whitelist**: Lista de comandos/variáveis permitidas (segurança por padrão)
- **Approval**: Sistema de aprovação interativa para ferramentas perigosas

### Arquitetura de Segurança

```
┌─────────────────────────────────────────────┐
│         Model Response (Ollama)            │
│  "I need to read the file README.md..."    │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│      ToolExecutionManager (miru)            │
│  - Verifica se tool está habilitada        │
│  - Verifica se sandbox permite operação    │
│  - Verifica modo de execução               │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│         Security Checks                      │
│  - Sandbox path validation                  │
│  - Whitelist verification                   │
│  - Permission check (read/write/del)       │
└─────────────────┬───────────────────────────┘
                  │
                  ▼ (APPROVED)
┌─────────────────────────────────────────────┐
│          Tool Execution                     │
│  read_file("README.md")                    │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│       Response to Model (Ollama)            │
│  "# README.md\n\nContent of file..."        │
└─────────────────────────────────────────────┘
```

### Tools Disponíveis

#### File Tools (Operações de Arquivo)

| Tool | Descrição | Segurança |
|------|-----------|-----------|
| `read_file` | Lê conteúdo de arquivo | ✅ Safe |
| `write_file` | Escreve conteúdo em arquivo | ⚠️ Needs approval |
| `edit_file` | Edita arquivo (replace) | ⚠️ Needs approval |
| `list_files` | Lista arquivos por padrão | ✅ Safe |
| `search_files` | Busca arquivos por nome | ✅ Safe |
| `delete_file` | Deleta arquivo | 🔴 Dangerous |
| `file_exists` | Verifica se arquivo existe | ✅ Safe |
| `get_file_info` | Obtém metadados do arquivo | ✅ Safe |

#### System Tools (Operações de Sistema)

| Tool | Descrição | Segurança |
|------|-----------|-----------|
| `run_command` | Executa comando shell | 🔴 Dangerous (whitelist) |
| `get_env` | Lê variável de ambiente | ✅ Safe (whitelist) |
| `get_current_dir` | Diretório atual | ✅ Safe |
| `list_allowed_commands` | Lista comandos permitidos | ✅ Safe |
| `list_allowed_env_vars` | Lista variáveis permitidas | ✅ Safe |

#### Tavily Tools (Busca na Web)

O miru integra com a API Tavily para busca na web, permitindo que modelos busquem informações atualizadas na internet.

**Configuração:**

```bash
miru config set tavily_api_key tvly-your-api-key-here
miru config get tavily_api_key
miru config list
```

**Configurar Tools Automaticamente:**

```bash
miru config set enable_tavily true
miru config set enable_tools true
miru config set tool_mode auto_safe
miru config set sandbox_dir ./workspace
miru config list
```

**Obter API Key:**
1. Acesse: https://tavily.com
2. Crie uma conta gratuita
3. Copie sua API key (formato: `tvly-...`)
4. Configure: `miru config set tavily_api_key YOUR_KEY`

**Limites Gratuitos:**
- 1.000 requisições/mês
- Rate limit: 60 requisições/minuto

**Uso:**

```bash
miru run gemma3 --tavily "Quais são as novidades do Python 3.13?"
miru run gemma3 --enable-tools --sandbox-dir ./workspace "Busque informações e salve em arquivo"
```

| Tool | Descrição | Segurança |
|------|-----------|-----------|
| `tavily_search` | Busca web por informações | ✅ Safe |
| `tavily_search_images` | Busca web com resultados de imagens | ✅ Safe |
| `tavily_extract` | Extrai e limpa conteúdo de URLs | ✅ Safe |

### Modos de Execução

```python
from miru.tools import ToolExecutionMode

# 1. DISABLED: Tools desabilitadas (segurança máxima)
mode = ToolExecutionMode.DISABLED

# 2. MANUAL: Pede aprovação para CADA tool (controle total)
mode = ToolExecutionMode.MANUAL

# 3. AUTO: Executa TODAS as tools automaticamente (produtividade máxima)
mode = ToolExecutionMode.AUTO

# 4. AUTO_SAFE: Auto para safe, aprovação para dangerous (recomendado)
mode = ToolExecutionMode.AUTO_SAFE
```

### Uso Programático

```python
from pathlib import Path
from miru.ollama.client import OllamaClient
from miru.tools import ToolExecutionManager, ToolExecutionMode
from miru.tools.utils import extract_tool_calls

manager = ToolExecutionManager(
    mode=ToolExecutionMode.AUTO_SAFE,
    sandbox_dir=Path("./workspace"),
    allow_write=True,
    allow_delete=False,
    enable_tavily=True,
)

tool_definitions = manager.get_tool_definitions()

messages = [{"role": "user", "content": "Liste os arquivos Python no projeto"}]

async with OllamaClient("http://localhost:11434") as client:
    async for chunk in client.chat_with_tools("llama3.2", messages, tools=tool_definitions):
        tool_calls = extract_tool_calls(chunk)
        if tool_calls:
            for call in tool_calls:
                tool_name = call["name"]
                arguments = call["arguments"]
                result, error = manager.execute_tool(tool_name, arguments)
```

## Gerenciamento de Modelos

### Status do servidor

```bash
miru status
miru status --verbose
```

### Modelos carregados na VRAM

```bash
miru ps
miru ps --format json
```

### Descarregar modelo

```bash
miru stop gemma3:latest
miru stop gemma3:latest --force
```

### Buscar modelos

```bash
miru search gemma
miru search llama --format json
```

## Configuração Persistente

### Gerenciar configuração

```bash
miru config list
miru config set default_host http://localhost:11434
miru config set default_model gemma3:latest
miru config set default_temperature 0.7
miru config set history_max_entries 500
miru config get default_model
miru config path
miru config reset --force
```

### Profiles de configuração

```bash
miru config profile create work
miru config set default_host http://work-server:11434
miru config profile switch work
miru config profile list
miru config profile delete work
```

### Configurações disponíveis

- `default_host` - Host padrão do Ollama
- `default_model` - Modelo padrão para comandos
- `default_timeout` - Timeout padrão (segundos)
- `default_temperature` - Temperatura padrão
- `default_max_tokens` - Máximo de tokens padrão
- `default_top_p` - Top-p padrão
- `default_top_k` - Top-k padrão
- `default_seed` - Seed padrão
- `history_enabled` - Habilitar histórico (true/false)
- `history_max_entries` - Máximo de entradas no histórico
- `verbose` - Modo verboso padrão
- `language` - Idioma da interface (pt_BR, en_US, es_ES)

## Histórico de Prompts

```bash
miru history
miru history --limit 50
miru history --command run
miru history --search "python"
miru history --format json
miru history --clear
miru history show 0
miru history list
```

## Session Save/Restore

### comandos de sessão

```bash
miru session list
miru session show my-session
miru session delete my-session --force
miru session export my-session --output session.json
miru session export my-session --output session.md --format markdown
miru session export my-session --output session.txt --format txt
miru session rename old-name new-name
```

### Durante o chat

```
>>> /save my-session
>>> /export json
>>> /export md
>>> /export txt
```

## Templates de Prompts

### Gerenciar templates

```bash
miru template list
miru template save code-review --prompt "Review this code: {code}" --description "Code review template"
miru template save summarize --prompt-file prompt.txt --system "You are a helpful assistant"
miru template show code-review
miru template delete code-review --force
```

### Executar template

```bash
miru template run code-review gemma3:latest --param code="def hello(): pass"
miru template run template qwen2.5 --param text="Long article..." --param style="bullet points"
miru template run summarize qwen2.5 --param text="Article..." --extra "Focus on key points"
```

### Exportar/Importar templates

```bash
miru template export code-review --output template.json
miru template import template.json --name my-template
```

## Aliases de Modelos

### Gerenciar aliases

```bash
miru alias add g3 gemma3:latest
miru alias add qwen qwen2.5:7b
miru alias list
miru alias show g3
miru alias delete g3 --force
```

### Usar aliases

```bash
miru run g3 "Hello world"
miru chat qwen
miru compare g3 qwen --prompt "Test"
```

## Logs e Debugging

```bash
miru logs
miru logs --lines 100
miru logs --follow
miru logs --latest
miru logs --list
miru logs clear --force
```

## Shell Completion

### Bash

```bash
miru completion bash > ~/.local/share/bash-completion/completions/miru
source ~/.local/share/bash-completion/completions/miru
```

### Zsh

```bash
miru completion zsh > ~/.zsh/completions/_miru
echo 'fpath+=~/.zsh/completions' >> ~/.zshrc
autoload -U compinit && compinit
```

### Fish

```bash
miru completion fish > ~/.config/fish/completions/miru.fish
```

## Multimodalidade

### Imagens

```bash
miru run llava:latest "Descreva a imagem" -i foto.jpg -i diagrama.png
```

Modelos com visão: `llava:latest`, `moondream:latest`, `gemma3:latest` (se suportado)

### Arquivos

```bash
miru run gemma3:latest "Analise" -f relatorio.pdf -f dados.csv
```

Formatos suportados: `.txt`, `.md`, `.py`, `.js`, `.ts`, `.json`, `.yaml`, `.xml`, `.html`, `.pdf`, `.docx`

### Áudio

```bash
miru run gemma3:latest "Resuma a reunião" -a reuniao.mp3
```

Requer Whisper instalado: `pip install openai-whisper`

## Parâmetros de Inferência

```bash
miru run <model> "prompt" [opções]

Opções:
  --temperature FLOAT     Temperatura de amostragem (0.0-2.0)
  --top-p FLOAT          Nucleus sampling (0.0-1.0)
  --top-k INT            Top-k sampling
  --max-tokens INT       Máximo de tokens a gerar
  --seed INT             Seed para reprodutibilidade
  --repeat-penalty FLOAT Penalidade de repetição
  --ctx INT              Tamanho da janela de contexto
  --no-stream            Desabilita streaming
  --host HOST            URL do servidor Ollama
  --format [text|json]   Formato de saída
  --quiet                Output minimal
  --auto-pull            Baixar modelo automaticamente se não existir
```

## Variáveis de Ambiente

- `OLLAMA_HOST` - URL do servidor Ollama (padrão: `http://localhost:11434`)
- `MIRU_DEFAULT_HOST` - Host padrão do miru
- `MIRU_DEFAULT_MODEL` - Modelo padrão
- `MIRU_LANGUAGE` - Idioma da interface (pt_BR, en_US, es_ES)
- `MIRU_HISTORY_ENABLED` - Habilitar histórico (true/false)
- `MIRU_HISTORY_MAX_ENTRIES` - Máximo de entradas no histórico
- `MIRU_VERBOSE` - Modo verboso padrão

## Desenvolvimento

### Instalação para desenvolvimento

```bash
pip install -e ".[dev]"
```

### Executar testes

```bash
pytest
pytest --cov=miru
pytest tests/test_core_i18n.py tests/test_core_errors.py tests/test_core_config.py tests/test_ui_render.py tests/test_commands_i18n.py tests/test_integration.py -v
```

### Estrutura do projeto

```
miru/
├── cli.py              # Ponto de entrada CLI
├── cli_options.py      # Flags CLI padronizadas (NOVO 0.4.0)
├── core/               # Módulos core (NOVO 0.4.0)
│   ├── config.py      # Configuração unificada
│   ├── errors.py      # Exceções customizadas
│   └── i18n.py        # Internacionalização
├── ui/                 # Módulos de UI (NOVO 0.4.0)
│   ├── render.py      # Renderização de output
│   ├── progress.py    # Barras de progresso
│   └── prompts.py    # Prompts interativos
├── config_manager.py   # Wrapper de compatibilidade
├── history.py          # Histórico de prompts
├── logger.py           # Sistema de logging
├── alias.py            # Sistema de aliases
├── template.py          # Templates de prompts
├── completion.py       # Shell completion
├── session.py          # Session save/restore
├── inference_params.py # Parâmetros de inferência
├── commands/           # Comandos CLI
│   ├── batch.py
│   ├── chat.py
│   ├── compare.py
│   ├── config_cmd.py
│   └── ...
├── input/              # Processamento multimodal
│   ├── audio.py
│   ├── file.py
│   └── image.py
├── model/               # Modelo de dados
│   └── capabilities.py
├── ollama/              # Cliente HTTP
│   └── client.py
├── output/              # Renderização e formatação
│   ├── formatter.py
│   ├── renderer.py
│   └── streaming.py
└── tools/               # Function calling
    ├── files.py
    ├── system.py
    └── tavily.py
```

## Dependências

- `httpx` - Cliente HTTP async
- `rich` - Terminal formatting
- `typer` - CLI framework
- `tomli` - Leitura de TOML (Python < 3.11)
- `tomli-w` - Escrita de TOML
- `pillow` - Validação de imagens (opcional)
- `pdfplumber` - Extração de PDF (opcional)
- `python-docx` - Extração de DOCX (opcional)

## Arquitetura

### Módulo Core (0.4.0)

O módulo `core/` fornece a base para toda a aplicação:

- **`config.py`**: Configuração unificada com cache e profiles
- **`errors.py`**: Hierarquia de exceções com sugestões contextuais
- **`i18n.py`**: Sistema de internacionalização completo

### Módulo UI (0.4.0)

O módulo `ui/` separa apresentação da lógica:

- **`render.py`**: Output consistente com suporte i18n
- **`progress.py`**: Indicadores de progresso unificados
- **`prompts.py`**: Input interativo padronizado

### Módulo Tools

Sistema de function calling:

```python
from miru.tools import ToolExecutionManager, ToolExecutionMode

manager = ToolExecutionManager(
    mode=ToolExecutionMode.AUTO_SAFE,
    sandbox_dir=Path("./workspace"),
    enable_tavily=True,
)
```

## Licença

Apache License 2.0 - Veja o arquivo [LICENSE](LICENSE) para detalhes.