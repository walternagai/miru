# miru

**CLI Python para servidor Ollama local com suporte multimodal e benchmarking.**

Miru (見る) significa "ver" ou "olhar" em japonês. Representa a capacidade de visualizar e interagir com modelos de IA, tornando o invisível visível através de comandos claros e intuitivos.

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
miru copy gemma3:latest meu-modelo --force  # Sobrescrever se existir
```

### Gerar embeddings

```bash
# Embedding de texto simples
miru embed nomic-embed-text "Hello world"

# Embedding de arquivo
miru embed nomic-embed-text --file documento.txt

# Embedding em lote (um texto por linha)
miru embed nomic-embed-text --batch textos.txt --format jsonl

# Embedding com formato JSON
miru embed nomic-embed-text "Teste" --format json

# Embedding minimalista (apenas array)
miru embed nomic-embed-text "Teste" --quiet
```

### Executar prompt único

```bash
miru run gemma3:latest "Explique recursão"
miru run gemma3:latest "Descreva a imagem" --image foto.png
miru run gemma3:latest "Analise o código" --file main.py
miru run gemma3:latest "Transcreva" --audio reuniao.mp3

# Com system prompt para definir comportamento
miru run gemma3:latest "Explique decorators" --system "Você é um especialista em Python. Seja conciso."
miru run gemma3:latest "Analise" --system-file prompt_sistema.txt --file relatorio.pdf

# Com parâmetros de inferência
miru run gemma3:latest "Teste" --temperature 0.7 --seed 42 --max-tokens 200

# Download automático se modelo não existir
miru run gemma3:latest "Teste" --auto-pull

# Formatos de saída
miru run gemma3:latest "Teste" --format json
miru run gemma3:latest "Teste" --quiet
```

### Chat interativo

```bash
miru chat gemma3:latest
miru chat llava:latest --image foto.png

# Com system prompt
miru chat gemma3:latest --system "Você é um tutor paciente. Explique com exemplos."
miru chat qwen2.5:7b --system-file personagem.txt

# Modelo padrão configurado
miru config set default_model gemma3:latest
miru chat  # Usa modelo padrão
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
>>> /retry             # Re-executar último prompt
>>> /save <arquivo>    # Salvar conversa em arquivo
>>> /export <formato>  # Exportar (json/md/txt)
```

### Comparar modelos (benchmark)

```bash
# Comparação básica
miru compare gemma3:latest qwen2.5:7b --prompt "O que é closure?"

# Com seed para reprodutibilidade
miru compare gemma3 qwen2.5:7b --prompt "Teste" --seed 42

# Com system prompt para todos os modelos
miru compare gemma3 qwen2.5:7b --prompt "Explique" --system "Responda em português, máximo 2 parágrafos"

# Comparação multimodal
miru compare llava:latest moondream:latest --prompt "Descreva" --image diagrama.png

# Formato JSON para pipe
miru compare gemma3 qwen2.5:7b --prompt "Teste" --format json --quiet | jq '.[0].metrics'
```

### Processamento em lote

```bash
# Arquivo com prompts (um por linha)
miru batch gemma3:latest --prompts prompts.txt

# Arquivo JSONL com metadados
miru batch gemma3:latest --prompts data.jsonl --format json

# Com system prompt para todos
miru batch qwen2.5:7b --prompts prompts.txt --system "Seja conciso"

# Output em JSON
miru batch gemma3 --prompts prompts.txt --format json

# Output em JSONL (uma entrada por linha)
miru batch gemma3 --prompts prompts.txt --format jsonl --quiet > results.jsonl

# Parar no primeiro erro
miru batch gemma3 --prompts prompts.txt --stop-on-error

# Com parâmetros de inferência
miru batch gemma3 --prompts prompts.txt --temperature 0.7 --max-tokens 100
```

## Quick Commands

Comandos rápidos para tarefas comuns:

```bash
# Gerar código
miru quick code gemma3 --param language=python --param task="sort a list"

# Resumir texto
miru quick summarize gemma3 --param text="Long article..."

# Explicar tópico
miru quick explain gemma3 --param topic="machine learning"

# Traduzir para português
miru quick translate-pt gemma3 --param text="Hello world"

# Traduzir para inglês
miru quick translate-en gemma3 --param text="Olá mundo"

# Revisar código
miru quick review-code gemma3 --param language=python --param code="$(cat main.py)"

# Corrigir bugs
miru quick fix-code gemma3 --param language=python --param code="$(cat broken.py)"

# Gerar testes unitários
miru quick test gemma3 --param language=python --param code="$(cat main.py)"

# Refatorar código
miru quick refactor gemma3 --param language=python --param code="$(cat main.py)"

# Documentar código
miru quick document gemma3 --param language=python --param code="$(cat main.py)"

# Otimizar código
miru quick optimize gemma3 --param language=python --param code="$(cat main.py)"

# Analisar texto
miru quick analyze gemma3 --param text="Article..."

# Corrigir gramática
miru quick grammar gemma3 --param text="Text with errors..."

# Expandir texto
miru quick expand gemma3 --param text="Short text..."

# Simplificar texto
miru quick simplify gemma3 --param text="Complex text..."

# Listar todos os comandos
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
# Não-interativo (usa defaults)
miru setup --non-interactive

# Com host customizado
miru setup --host http://custom:11434
```

## Examples Browser

Navegador de exemplos de uso:

```bash
# Listar todos os exemplos
miru examples --list

# Filtrar por categoria
miru examples --category code

# Filtrar por tag
miru examples --tag python

# Ver exemplo específico
miru examples hello-world

# Copiar comando para clipboard
miru examples hello-world --copy

# Listar categorias
miru examples --categories
```

Categorias disponíveis: `basics`, `code`, `text`, `translation`, `learning`, `chat`, `advanced`, `multimodal`, `document`, `templates`, `config`

## Gerenciamento de Modelos

### Status do servidor

```bash
# Verificar se Ollama está acessível
miru status

# Status detalhado
miru status --verbose
```

### Modelos carregados na VRAM

```bash
# Listar modelos atualmente na memória
miru ps

# Formato JSON
miru ps --format json
```

### Descarregar modelo

```bash
# Descarregar modelo da VRAM
miru stop gemma3:latest

# Forçar descarregamento imediato
miru stop gemma3:latest --force
```

### Buscar modelos

```bash
# Filtrar modelos por nome
miru search gemma
miru search llama --format json
```

## Configuração Persistente

### Gerenciar configuração

```bash
# Ver toda a configuração
miru config list

# Definir valor
miru config set default_host http://localhost:11434
miru config set default_model gemma3:latest
miru config set default_temperature 0.7
miru config set history_max_entries 500

# Obter valor
miru config get default_model

# Ver caminho do arquivo de configuração
miru config path

# Resetar para defaults
miru config reset --force
```

### Profiles de configuração

```bash
# Criar profile
miru config profile create work

# Configurar profile
miru config set default_host http://work-server:11434  # (com profile 'work' ativo)

# Alternar profile
miru config profile switch work

# Listar profiles
miru config profile list

# Deletar profile
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

## Histórico de Prompts

```bash
# Ver histórico
miru history

# Limitar entradas
miru history --limit 50

# Filtrar por comando
miru history --command run

# Buscar no histórico
miru history --search "python"

# Formato JSON
miru history --format json

# Limpar histórico
miru history --clear

# Ver detalhes de uma entrada
miru history-show 0
```

## Session Save/Restore

### comandos de sessão

```bash
# Listar sessões salvas
miru session list

# Ver detalhes de uma sessão
miru session show my-session

# Deletar sessão
miru session delete my-session --force

# Exportar sessão
miru session export my-session --output session.json
miru session export my-session --output session.md --format markdown
miru session export my-session --output session.txt --format txt

# Renomear sessão
miru session rename old-name new-name
```

### Durante o chat

```
>>> /save my-session    # Salvar sessão atual
>>> /export json        # Exportar sessão para JSON
>>> /export md          # Exportar sessão para Markdown
>>> /export txt         # Exportar sessão para TXT
```

## Templates de Prompts

### Gerenciar templates

```bash
# Listar templates
miru template list

# Criar template
miru template save code-review \
  --prompt "Review this code: {code}" \
  --description "Code review template"

# Criar template com system prompt
miru template save summarize \
  --prompt-file prompt.txt \
  --system "You are a helpful assistant"

# Ver template
miru template show code-review

# Deletar template
miru template delete code-review --force
```

### Executar template

```bash
# Executar template com parâmetros
miru template run code-review gemma3:latest \
  --param code="def hello(): pass"

# Com parâmetros múltiplos
miru template run template qwen2.5 \
  --param text="Long article..." \
  --param style="bullet points"

# Com texto adicional
miru template run summarize qwen2.5 \
  --param text="Article..." \
  --extra "Focus on key points"
```

### Exportar/Importar templates

```bash
# Exportar template
miru template export code-review --output template.json

# Importar template
miru template import template.json --name my-template
```

## Aliases de Modelos

### Gerenciar aliases

```bash
# Criar alias
miru alias add g3 gemma3:latest
miru alias add qwen qwen2.5:7b

# Listar aliases
miru alias list

# Ver alias
miru alias show g3

# Deletar alias
miru alias delete g3 --force
```

### Usar aliases

```bash
# Os aliases funcionam em todos os comandos
miru run g3 "Hello world"
miru chat qwen
miru compare g3 qwen --prompt "Test"
```

## Logs e Debugging

```bash
# Ver logs
miru logs

# Ver últimas N linhas
miru logs --lines 100

# Seguir logs em tempo real
miru logs --follow

# Ver apenas log mais recente
miru logs --latest

# Listar arquivos de log
miru logs --list

# Limpar logs
miru logs-clear --force
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
# Adicione ao .zshrc: fpath+=~/.zsh/completions
autoload -U compinit && compinit
```

### Fish

```bash
miru completion fish > ~/.config/fish/completions/miru.fish
```

## Multimodalidade

### Imagens

```bash
miru run llava:latest "Descreva a imagem" --image foto.jpg --image diagrama.png
```

Modelos com visão: `llava:latest`, `moondream:latest`, `gemma3:latest` (se suportado)

### Arquivos

```bash
miru run gemma3:latest "Analise" --file relatorio.pdf --file dados.csv
```

Formatos suportados: `.txt`, `.md`, `.py`, `.js`, `.ts`, `.json`, `.yaml`, `.xml`, `.html`, `.pdf`, `.docx`

### Áudio

```bash
miru run gemma3:latest "Resuma a reunião" --audio reuniao.mp3
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
```

### Estrutura do projeto

```
miru/
├── cli.py              # Ponto de entrada CLI
├── config.py           # Configuração (OLLAMA_HOST)
├── config_manager.py   # Gerenciamento de configuração persistente
├── history.py          # Histórico de prompts
├── logger.py           # Sistema de logging
├── alias.py            # Sistema de aliases
├── template.py         # Templates de prompts
├── completion.py       # Shell completion
├── session.py          # Session save/restore
├── inference_params.py # Parâmetros de inferência
├── renderer.py         # Compatibilidade (delegação)
├── commands/           # Comandos CLI
│   ├── batch.py        # Processamento em lote
│   ├── chat.py         # Chat interativo
│   ├── compare.py      # Benchmark de modelos
│   ├── config_cmd.py   # Gerenciamento de configuração
│   ├── examples.py     # Navegador de exemplos
│   ├── history_cmd.py  # Comandos de histórico
│   ├── logs.py         # Visualização de logs
│   ├── quick.py        # Quick commands
│   ├── run.py          # Prompt único
│   ├── setup.py        # Setup wizard
│   ├── status.py       # Status, ps, stop, search
│   └── ...
├── input/              # Processamento multimodal
│   ├── audio.py       # Transcrição Whisper
│   ├── file.py        # Extração de texto
│   └── image.py        # Encoding base64
├── model/              # Modelo de dados
│   └── capabilities.py # Detecção de capacidades
├── ollama/             # Cliente HTTP
│   └── client.py      # Cliente async Ollama
└── output/             # Renderização e formatação
    ├── formatter.py   # Serialização JSON
    ├── renderer.py     # Renderização Rich
    └── streaming.py    # Streaming de tokens
```

## Arquitetura

### Módulo Input

- `image.py`: Encoding de imagens para base64 (JPEG, PNG, GIF, WEBP)
- `file.py`: Extração de texto de arquivos (PDF, DOCX, TXT, código)
- `audio.py`: Transcrição via Whisper local (subprocess)

### Módulo Output

- `renderer.py`: Renderização Rich para terminal (tabelas, métricas, progress)
- `formatter.py`: Serialização limpa JSON/stdio (stdlib-only)
- `streaming.py`: Compatibilidade backward com generators

### Cliente Ollama

Cliente HTTP async com suporte a:
- Streaming de tokens
- Geração com imagens
- Chat multi-turn
- Pull de modelos com progress

### Gerenciamento de Configuração

- Configuração persistente em `~/.miru/config.toml`
- Profiles múltiplos para diferentes ambientes
- Precedência: CLI > Variável de ambiente > Configuração > Default

### Histórico

- Histórico de prompts em `~/.miru/history.jsonl`
- Rotação automática com limite de entradas
- Busca e filtros por comando

### Templates

- Templates salvos em `~/.miru/templates/`
- Parâmetros substituíveis com `{param}`
- Importação/exportação em JSON

### Logs

- Logs de execução em `~/.miru/logs/`
- Formato estruturado JSON
- Modo verbose para debugging

### Sessions

- Sessões salvas em `~/.miru/sessions/`
- Exportação para JSON, Markdown, TXT
- Restauração de contexto completo

## Dependências

- `httpx` - Cliente HTTP async
- `typer` - CLI framework
- `rich` - Terminal formatting
- `tomli` - Leitura de TOML (Python < 3.11)
- `tomli-w` - Escrita de TOML
- `pillow` - Validação de imagens (opcional)
- `pdfplumber` - Extração de PDF (opcional)
- `python-docx` - Extração de DOCX (opcional)

## Funcionalidades Principais

| Funcionalidade | Comando | Descrição |
|---------------|---------|-----------|
| Setup Wizard | `miru setup` | Configuração interativa inicial |
| Quick Commands | `miru quick <cmd>` | Comandos rápidos para tarefas comuns |
| Examples Browser | `miru examples` | Navegador de exemplos de uso |
| Session Management | `miru session` | Salvar/restaurar sessões de chat |
| Model Aliases | `miru alias` | Atalhos para modelos frequentes |
| Prompt Templates | `miru template` | Templates reutilizáveis |
| History | `miru history` | Histórico de prompts |
| Config Profiles | `miru config profile` | Multiplos ambientes |
| Auto-pull | `--auto-pull` | Download automático de modelos |
| Shell Completion | `miru completion` | Autocomplete para bash/zsh/fish |

## Licença

MIT