# miru

CLI Python para servidor Ollama local com suporte multimodal e benchmarking.

## Instalação

```bash
pip install miru
```

## Uso

```bash
miru --help
```

### Listar modelos

```bash
miru list
miru list --format json
miru list --quiet
```

### Informações do modelo

```bash
miru info gemma3:latest
miru info qwen2.5:7b --format json
```

### Baixar modelo

```bash
miru pull gemma3:latest
miru pull llava:latest --quiet
```

### Executar prompt único

```bash
miru run gemma3:latest "Explique recursão"
miru run gemma3:latest "Descreva a imagem" --image foto.png
miru run gemma3:latest "Analise o código" --file main.py
miru run gemma3:latest "Transcreva" --audio reuniao.mp3

# Com parâmetros de inferência
miru run gemma3:latest "Teste" --temperature 0.7 --seed 42 --max-tokens 200

# Formatos de saída
miru run gemma3:latest "Teste" --format json
miru run gemma3:latest "Teste" --quiet
```

### Chat interativo

```bash
miru chat gemma3:latest
miru chat llava:latest --image foto.png
```

### Comparar modelos (benchmark)

```bash
# Comparação básica
miru compare gemma3:latest qwen2.5:7b --prompt "O que é closure?"

# Com seed para reprodutibilidade
miru compare gemma3 qwen2.5:7b --prompt "Teste" --seed 42

# Comparação multimodal
miru compare llava:latest moondream:latest --prompt "Descreva" --image diagrama.png

# Formato JSON para pipe
miru compare gemma3 qwen2.5:7b --prompt "Teste" --format json --quiet | jq '.[0].metrics'
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
```

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
├── inference_params.py # Parâmetros de inferência
├── renderer.py         # Compatibilidade (delegação)
├── commands/           # Comandos CLI
│   ├── chat.py        # Chat interativo
│   ├── compare.py     # Benchmark de modelos
│   ├── info.py        # Informações do modelo
│   ├── list.py        # Listar modelos
│   ├── pull.py        # Baixar modelo
│   └── run.py         # Prompt único
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

## Dependências

- `httpx` - Cliente HTTP async
- `typer` - CLI framework
- `rich` - Terminal formatting
- `pillow` - Validação de imagens (opcional)
- `pdfplumber` - Extração de PDF (opcional)
- `python-docx` - Extração de DOCX (opcional)

## Licença

MIT