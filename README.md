# miru

**CLI Python para servidor Ollama local com suporte multimodal, benchmarking, function calling e internacionalização (i18n).**

Miru (見る) significa "ver" ou "olhar" em japonês. Representa a capacidade de visualizar e interagir com modelos de IA através de comandos claros e intuitivos, com suporte completo a function calling para que modelos executem ações no seu sistema.

**Versão 0.5.0**

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

O miru suporta **3 idiomas**: Português (Brasil), English e Español.

### Definir Idioma

```bash
# Português (Brasil)
export MIRU_LANG=pt_BR

# English
export MIRU_LANG=en_US

# Español
export MIRU_LANG=es_ES

# Ou via configuração persistente
miru config set language pt_BR
```

| Código | Idioma         | Cobertura |
|--------|----------------|-----------|
| pt_BR  | Português (BR) | 100%      |
| en_US  | English        | 100%      |
| es_ES  | Español        | 100%      |

## Short Flags

Flags curtas disponíveis nos comandos principais:

| Flag Longa      | Flag Curta | Descrição                     |
|-----------------|------------|-------------------------------|
| `--host`        | `-h`       | URL do servidor Ollama        |
| `--quiet`       | `-q`       | Output minimal                |
| `--verbose`     | `-v`       | Output verboso                |
| `--system`      | `-s`       | System prompt                 |
| `--image`       | `-i`       | Arquivo de imagem             |
| `--file`        | `-f`       | Arquivo de input              |
| `--audio`       | `-a`       | Arquivo de áudio              |
| `--temperature` | `-t`       | Temperatura de amostragem     |
| `--max-tokens`  | `-m`       | Máximo de tokens              |
| `--top-p`       | `-p`       | Nucleus sampling              |
| `--top-k`       | `-k`       | Top-k sampling                |
| `--ctx`         | `-c`       | Janela de contexto            |
| `--output`      | `-o`       | Arquivo de saída              |
| `--limit`       | `-n`       | Número de entradas            |

```bash
# Exemplos com short flags
miru run gemma3 "Explique closures" -s "Seja conciso" -t 0.7 -m 200
miru run llava "Descreva" -i foto.jpg -f notas.txt
miru list -q
miru history -n 50 -c run
```

## Uso

### Comandos Básicos

#### Listar modelos

```bash
miru list
miru list --format json
miru list --quiet
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

# Formato de saída
miru run gemma3:latest "Teste" --format json
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
miru chat --system "Você é um tutor paciente. Explique com exemplos."

# Modelo padrão configurado
miru config set default_model gemma3:latest
miru chat  # Usa modelo padrão

# Com Tavily web search
miru chat gemma3:latest --tavily

# Com todas as tools habilitadas
miru chat qwen2.5:7b --enable-tools --sandbox-dir ./workspace

# Parâmetros de inferência passados ao chat
miru chat gemma3 -t 0.3 --seed 42 --system "Seja conciso"
```

O `miru chat` abre a **interface TUI** (Terminal User Interface) quando o Textual está instalado, ou cai automaticamente para o **modo CLI interativo** se não estiver disponível.

#### Interface TUI

A TUI oferece um layout em três painéis:

- **Painel esquerdo** — lista de sessões salvas com filtro em tempo real
- **Área central** — histórico da conversa com renderização Markdown
- **Painel direito** — controles de modelo e parâmetros (temperatura, top-p, max tokens, seed, system prompt)

**Atalhos de teclado:**

| Atalho          | Ação                                 |
|-----------------|--------------------------------------|
| `Enter`         | Enviar mensagem                      |
| `Ctrl+N`        | Nova conversa                        |
| `Ctrl+S`        | Salvar sessão                        |
| `Ctrl+K`        | Abrir configurações globais          |
| `Ctrl+O`        | Selecionar personalidade (preset)    |
| `Ctrl+Z`        | Ativar/desativar modo Zen            |
| `Ctrl+P`        | Mostrar/ocultar painel de parâmetros |
| `Ctrl+F`        | Favoritar/desfavoritar sessão        |
| `Ctrl+L`        | Limpar campo de input                |
| `Ctrl+Shift+L`  | Limpar conversa (pede confirmação)   |
| `Ctrl+R`        | Recarregar lista de sessões          |
| `F2`            | Renomear sessão                      |
| `Delete`        | Deletar sessão (pede confirmação)    |
| `Ctrl+Q`        | Sair                                 |

**Personalidades (presets)** — `Ctrl+O` abre um menu com perfis pré-configurados:

| Preset         | Temperatura | Uso                              |
|----------------|-------------|----------------------------------|
| Preciso        | 0.3         | Respostas objetivas e factuais   |
| Criativo       | 1.0         | Exploração livre de ideias       |
| Programador    | 0.2         | Código estruturado e comentado   |
| Acadêmico      | 0.4         | Rigor técnico e terminologia     |
| Conversacional | 0.8         | Tom amigável e natural           |

**Ações em mensagens** — cada resposta do modelo exibe botões:
- **Copiar** — copia o texto completo da mensagem
- **Copiar Código** — extrai e copia apenas os blocos de código
- **Regenerar** — reexecuta a última pergunta com nova resposta

#### Modo CLI interativo (fallback)

Quando a TUI não está disponível, o chat opera em modo texto puro com os seguintes comandos:

```
>>> /help              # Listar comandos disponíveis
>>> /exit              # Encerrar sessão
>>> /clear             # Limpar histórico da conversa
>>> /history           # Mostrar contagem de turnos
>>> /stats             # Mostrar estatísticas da sessão (tokens, velocidade)
>>> /model <nome>      # Trocar modelo durante a sessão
>>> /system <prompt>   # Alterar system prompt
>>> /recall            # Listar últimos prompts (seleção interativa)
>>> /recall <n>        # Carregar e executar prompt pelo índice
>>> /retry             # Re-executar último prompt
>>> /save <arquivo>    # Salvar conversa em arquivo Markdown
```

**`/recall`** — resgata prompts de sessões anteriores do histórico:

```bash
>>> /recall           # Exibe lista dos últimos 10 prompts para seleção
>>> /recall 0         # Carrega e executa o prompt de índice 0 imediatamente
>>> /recall 3         # Carrega e executa o prompt de índice 3 imediatamente
```

### Histórico de Prompts

O miru mantém um histórico de todos os prompts executados em `~/.miru/history.jsonl`:

```bash
# Listar histórico
miru history

# Ver detalhes de uma entrada (resposta renderizada em Markdown)
miru history show 0

# Buscar no histórico
miru history --search "python"

# Filtrar por comando
miru history --command run

# Limitar entradas
miru history --limit 50

# Exportar como JSON
miru history --format json

# Limpar histórico
miru history --clear
```

### Comparar modelos (benchmark)

```bash
miru compare gemma3:latest qwen2.5:7b --prompt "O que é closure?"
miru compare gemma3 qwen2.5:7b --prompt "Teste" --seed 42
miru compare llava:latest moondream:latest --prompt "Descreva" -i diagrama.png
miru compare gemma3 qwen2.5:7b --prompt "Teste" --format json -q | jq '.[0].metrics'
```

### Processamento em lote

```bash
miru batch gemma3:latest --prompts prompts.txt
miru batch gemma3:latest --prompts data.jsonl --format json
miru batch qwen2.5:7b --prompts prompts.txt -s "Seja conciso"
miru batch gemma3 --prompts prompts.txt --format jsonl -q > results.jsonl
miru batch gemma3 --prompts prompts.txt --stop-on-error
miru batch gemma3 --prompts prompts.txt -t 0.7 -m 100
```

O arquivo de prompts pode ser texto simples (um prompt por linha) ou JSONL com campos `prompt`, `text` ou `question`.

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
miru setup --non-interactive
miru setup --host http://custom:11434
```

O wizard:
- Verifica se Ollama está rodando
- Lista modelos disponíveis
- Permite escolher modelo padrão
- Configura histórico de prompts
- Configura aliases
- Salva preferências em `~/.miru/config.toml`

## Examples Browser

```bash
miru examples --list
miru examples --category code
miru examples --tag python
miru examples hello-world
miru examples hello-world --copy
miru examples --categories
```

Categorias: `basics`, `code`, `text`, `translation`, `learning`, `chat`, `advanced`, `multimodal`, `document`, `templates`, `config`

## Tools / Function Calling

O miru suporta **function calling** nativo do Ollama, permitindo que modelos executem ações no sistema de forma segura e controlada.

### Conceitos

- **Tools** — funções que o modelo pode chamar durante a conversa
- **Sandbox** — diretório restrito para operações de arquivo (previne acesso não autorizado)
- **Whitelist** — lista de comandos/variáveis permitidos (segurança por padrão)
- **Approval** — sistema de aprovação interativa para ferramentas perigosas

### Arquitetura de Segurança

```
Model Response → ToolExecutionManager → Security Checks → Tool Execution → Response
                  (mode check)          (sandbox, whitelist,  (read_file,
                                         permission)          run_command…)
```

### Tools Disponíveis

#### File Tools

| Tool           | Descrição                    | Segurança          |
|----------------|------------------------------|--------------------|
| `read_file`    | Lê conteúdo de arquivo       | ✅ Safe             |
| `write_file`   | Escreve conteúdo em arquivo  | ⚠️ Needs approval  |
| `edit_file`    | Edita arquivo (replace)      | ⚠️ Needs approval  |
| `list_files`   | Lista arquivos por padrão    | ✅ Safe             |
| `search_files` | Busca arquivos por nome      | ✅ Safe             |
| `delete_file`  | Deleta arquivo               | 🔴 Dangerous        |
| `file_exists`  | Verifica se arquivo existe   | ✅ Safe             |
| `get_file_info`| Obtém metadados do arquivo   | ✅ Safe             |

#### System Tools

| Tool                   | Descrição                        | Segurança               |
|------------------------|----------------------------------|-------------------------|
| `run_command`          | Executa comando shell            | 🔴 Dangerous (whitelist) |
| `get_env`              | Lê variável de ambiente          | ✅ Safe (whitelist)      |
| `get_current_dir`      | Diretório atual                  | ✅ Safe                  |
| `list_allowed_commands`| Lista comandos permitidos        | ✅ Safe                  |
| `list_allowed_env_vars`| Lista variáveis permitidas       | ✅ Safe                  |

#### Tavily Tools (Busca na Web)

| Tool                   | Descrição                        | Segurança |
|------------------------|----------------------------------|-----------|
| `tavily_search`        | Busca web por informações        | ✅ Safe    |
| `tavily_search_images` | Busca web com resultados visuais | ✅ Safe    |
| `tavily_extract`       | Extrai e limpa conteúdo de URLs  | ✅ Safe    |

**Configuração do Tavily:**

```bash
miru config set tavily_api_key tvly-your-api-key-here

# Habilitar automaticamente em todas as sessões
miru config set enable_tavily true
miru config set enable_tools true
miru config set tool_mode auto_safe
miru config set sandbox_dir ./workspace
```

Obtenha sua API key gratuita em https://tavily.com (1.000 req/mês no plano free).

### Modos de Execução

| Modo        | Comportamento                                          |
|-------------|--------------------------------------------------------|
| `disabled`  | Tools desabilitadas                                    |
| `manual`    | Pede aprovação para cada tool                          |
| `auto`      | Executa todas as tools automaticamente                 |
| `auto_safe` | Auto para safe, aprovação para dangerous (recomendado) |

```bash
miru run gemma3 --tavily "Quais são as novidades do Python 3.13?"
miru run gemma3 --enable-tools --tool-mode manual "Liste os arquivos do projeto"
miru chat qwen --enable-tools --sandbox-dir ./workspace --tool-mode auto_safe
```

### Uso Programático

```python
from pathlib import Path
from miru.ollama.client import OllamaClient
from miru.tools import ToolExecutionManager, ToolExecutionMode

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
        ...
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

### Descarregar modelo da VRAM

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

O miru salva configurações em `~/.miru/config.toml`.

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

| Chave                  | Descrição                                    | Padrão              |
|------------------------|----------------------------------------------|---------------------|
| `default_host`         | URL do servidor Ollama                       | `http://localhost:11434` |
| `default_model`        | Modelo padrão para comandos                  | —                   |
| `default_timeout`      | Timeout de requisição (segundos)             | `30`                |
| `default_temperature`  | Temperatura de amostragem                    | —                   |
| `default_max_tokens`   | Máximo de tokens por resposta                | —                   |
| `default_top_p`        | Nucleus sampling                             | —                   |
| `default_top_k`        | Top-k sampling                               | —                   |
| `default_seed`         | Seed para reprodutibilidade                  | —                   |
| `history_enabled`      | Habilitar histórico de prompts               | `true`              |
| `history_max_entries`  | Máximo de entradas no histórico              | `1000`              |
| `verbose`              | Modo verboso padrão                          | `false`             |
| `language`             | Idioma da interface                          | `en_US`             |
| `enable_tools`         | Habilitar function calling                   | `false`             |
| `enable_tavily`        | Habilitar busca web via Tavily               | `false`             |
| `tool_mode`            | Modo de execução de tools                    | `auto_safe`         |
| `sandbox_dir`          | Diretório sandbox para file tools            | —                   |
| `tavily_api_key`       | API key do Tavily                            | —                   |

## Session Save/Restore

Sessões são salvas automaticamente em `~/.miru/sessions/` durante o chat na TUI.

### Comandos de sessão

```bash
miru session list
miru session show my-session
miru session delete my-session --force
miru session export my-session --output session.json
miru session export my-session --output session.md --format markdown
miru session export my-session --output session.txt --format txt
miru session rename old-name new-name
```

### Durante o chat (modo CLI)

```
>>> /save my-session     # Salva conversa em arquivo Markdown
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
miru template run summarize qwen2.5 --param text="Long article..." --extra "Focus on key points"
```

### Exportar/Importar templates

```bash
miru template export code-review --output template.json
miru template import template.json --name my-template
```

## Aliases de Modelos

```bash
miru alias add g3 gemma3:latest
miru alias add qwen qwen2.5:7b
miru alias list
miru alias show g3
miru alias delete g3 --force

# Usar aliases em qualquer comando
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

Modelos com visão: `llava:latest`, `moondream:latest`, `gemma3:latest`

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

```
--temperature FLOAT     Temperatura de amostragem (0.0–2.0)
--top-p FLOAT           Nucleus sampling (0.0–1.0)
--top-k INT             Top-k sampling
--max-tokens INT        Máximo de tokens a gerar
--seed INT              Seed para reprodutibilidade
--repeat-penalty FLOAT  Penalidade de repetição
--ctx INT               Tamanho da janela de contexto
--no-stream             Desabilita streaming
--host HOST             URL do servidor Ollama
--format [text|json]    Formato de saída (run/batch)
--quiet                 Output minimal
--auto-pull             Baixar modelo automaticamente se não existir
```

## Variáveis de Ambiente

| Variável                  | Descrição                               |
|---------------------------|-----------------------------------------|
| `OLLAMA_HOST`             | URL do servidor Ollama                  |
| `MIRU_DEFAULT_HOST`       | Host padrão do miru                     |
| `MIRU_DEFAULT_MODEL`      | Modelo padrão                           |
| `MIRU_LANG`               | Idioma da interface (pt_BR/en_US/es_ES) |
| `MIRU_HISTORY_ENABLED`    | Habilitar histórico (true/false)        |
| `MIRU_HISTORY_MAX_ENTRIES`| Máximo de entradas no histórico         |
| `MIRU_VERBOSE`            | Modo verboso padrão                     |
| `MIRU_TAVILY_API_KEY`     | API key do Tavily                       |

## Desenvolvimento

### Instalação para desenvolvimento

```bash
pip install -e ".[dev]"
```

### Executar testes

```bash
pytest
pytest --cov=miru
pytest tests/test_core_i18n.py tests/test_core_errors.py tests/test_core_config.py -v
```

### Estrutura do projeto

```
miru/
├── cli.py                  # Ponto de entrada CLI
├── cli_options.py          # Flags CLI padronizadas
├── core/
│   ├── config.py           # Configuração unificada com profiles
│   ├── errors.py           # Exceções customizadas com sugestões
│   └── i18n.py             # Internacionalização (pt_BR/en_US/es_ES)
├── ui/
│   ├── render.py           # Renderização de output
│   ├── progress.py         # Barras de progresso
│   ├── prompts.py          # Prompts interativos
│   └── tui/
│       ├── app.py          # Aplicação TUI principal
│       ├── config_screen.py# Tela de configurações
│       ├── confirm_screen.py# Modal de confirmação
│       ├── preset_screen.py# Seleção de personalidades
│       └── rename_screen.py# Renomear sessão
├── commands/               # Comandos CLI (batch, chat, run, …)
├── input/                  # Processamento multimodal
│   ├── audio.py            # Transcrição com Whisper
│   ├── file.py             # Extração de texto
│   └── image.py            # Encoding de imagens
├── model/
│   └── capabilities.py     # Detecção de capacidades do modelo
├── ollama/
│   └── client.py           # Cliente HTTP async para Ollama
├── output/                 # Renderização e formatação
│   ├── formatter.py
│   ├── renderer.py
│   └── streaming.py
├── tools/                  # Function calling
│   ├── files.py
│   ├── system.py
│   └── tavily.py
├── history.py              # Histórico de prompts
├── session.py              # Session save/restore
├── alias.py                # Sistema de aliases
└── template.py             # Templates de prompts
```

## Dependências

| Pacote        | Descrição                           | Obrigatório |
|---------------|-------------------------------------|-------------|
| `httpx`       | Cliente HTTP async                  | ✅           |
| `rich`        | Terminal formatting                 | ✅           |
| `typer`       | CLI framework                       | ✅           |
| `textual`     | TUI framework                       | ✅           |
| `tomli`       | Leitura de TOML (Python < 3.11)     | ✅           |
| `tomli-w`     | Escrita de TOML                     | ✅           |
| `pillow`      | Validação de imagens                | Opcional    |
| `pdfplumber`  | Extração de PDF                     | Opcional    |
| `python-docx` | Extração de DOCX                    | Opcional    |
| `openai-whisper` | Transcrição de áudio             | Opcional    |
| `pyperclip`   | Copiar para clipboard               | Opcional    |

## Licença

Apache License 2.0 — veja o arquivo [LICENSE](LICENSE) para detalhes.
