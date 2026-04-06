# Plano de Implementação: Tools/Function Calling no Miru

## Visão Geral

Adicionar suporte a **Function Calling** no `miru`, permitindo que modelos Ollama executem ferramentas internas durante conversas. Isso transformará o `miru` em um agente capaz de interagir com o sistema de arquivos, execute código, busque informações na web, etc.

## Contexto Atual

### Arquitetura Existente
- **Cliente HTTP**: `miru/ollama/client.py` com métodos `generate()` e `chat()`
- **Chat interativo**: `miru/commands/chat.py` com REPL
- **Processamento multimodal**: `miru/input/` (imagens, arquivos, áudio)
- **Output**: `miru/output/` (streaming, formatação)

### API Ollama - Function Calling
```json
{
  "model": "llama3.2",
  "messages": [...],
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "get_weather",
        "description": "Get weather for a city",
        "parameters": {
          "type": "object",
          "properties": {
            "city": {"type": "string", "description": "City name"}
          },
          "required": ["city"]
        }
      }
    }
  ]
}
```

Resposta do modelo:
```json
{
  "message": {
    "role": "assistant",
    "tool_calls": [
      {
        "function": {
          "name": "get_weather",
          "arguments": {"city": "Tokyo"}
        }
      }
    ]
  }
}
```

---

## Fases de Implementação

### FASE 1: Infraestrutura Básica (3-4 dias)

#### 1.1 Extender OllamaClient
**Arquivo**: `miru/ollama/client.py`

```python
async def chat_with_tools(
    self,
    model: str,
    messages: list[dict],
    tools: list[dict] | None = None,
    options: dict | None = None,
) -> AsyncIterator[dict]:
    """
    Chat com suporte a tools.
    
    Args:
        tools: Lista de definições de tools no formato Ollama
        
    Yields:
        Dict chunks incluindo tool_calls quando aplicável
    """
    body = {
        "model": model,
        "messages": messages,
        "stream": True,
    }
    
    if tools:
        body["tools"] = tools
        
    # Resto igual ao chat() existente
```

#### 1.2 Sistema de Tools Base
**Novo módulo**: `miru/tools/__init__.py`

```python
from dataclasses import dataclass
from typing import Any, Callable

@dataclass
class Tool:
    """Representa uma tool disponível."""
    name: str
    description: str
    parameters: dict[str, Any]
    handler: Callable[..., Any]
    
    def to_ollama_format(self) -> dict:
        """Converte para formato esperado pela API Ollama."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            }
        }
```

#### 1.3 Tool Registry
**Novo arquivo**: `miru/tools/registry.py`

```python
class ToolRegistry:
    """Gerencia tools disponíveis."""
    
    def __init__(self):
        self._tools: dict[str, Tool] = {}
    
    def register(self, tool: Tool) -> None:
        """Registra uma tool."""
        self._tools[tool.name] = tool
    
    def get_definitions(self) -> list[dict]:
        """Retorna definições para API Ollama."""
        return [t.to_ollama_format() for t in self._tools.values()]
    
    def execute(self, name: str, arguments: dict) -> Any:
        """Executa uma tool."""
        if name not in self._tools:
            raise ToolNotFoundError(name)
        return self._tools[name].handler(**arguments)
```

#### 1.4 Tests
- Testar `chat_with_tools()` com mock
- Testar execução de tools
- Testar parsing de `tool_calls`

---

### FASE 2: Tools Internas (4-5 dias)

#### 2.1 File Tools
**Novo arquivo**: `miru/tools/files.py`

Tools:
- `read_file(path)` - Ler arquivo de texto
- `write_file(path, content)` - Criar/sobrescrever arquivo
- `edit_file(path, old, new)` - Editar arquivo (substituição exata)
- `list_files(directory)` - Listar arquivos
- `search_files(pattern, path)` - Buscar arquivos por padrão

```python
from pathlib import Path

def register_file_tools(registry: ToolRegistry, sandbox_dir: Path) -> None:
    """Registra tools de sistema de arquivos com sandbox."""
    
    @registry.register
    def read_file(path: str) -> str:
        """Lê conteúdo de um arquivo de texto.
        
        Args:
            path: Caminho relativo ao diretório de trabalho
            
        Returns:
            Conteúdo do arquivo
        """
        full_path = sandbox_dir / path
        if not full_path.resolve().is_relative_to(sandbox_dir):
            raise PermissionError("Path outside sandbox")
        return full_path.read_text()
```

#### 2.2 System Tools
**Novo arquivo**: `miru/tools/system.py`

Tools:
- `run_command(cmd)` - Executar comando shell (com whitelist)
- `get_env(var)` - Ler variável de ambiente (whitelist)
- `get_current_dir()` - Diretório atual

#### 2.3 Code Execution Tools (Opcional)
**Novo arquivo**: `miru/tools/code.py`

Tools:
- `run_python(code)` - Executar código Python em sandbox
- `run_javascript(code)` - Executar código JS (via node subprocess)

#### 2.4 Web Tools (Futuro)
**Novo arquivo**: `miru/tools/web.py`

Tools:
- `fetch_url(url)` - Baixar URL
- `search_web(query)` - Buscar na web (via API de busca)

---

### FASE 3: Integração no Chat (3-4 dias)

#### 3.1 Chat com Auto-Execução
**Modificar**: `miru/commands/chat.py`

```python
async def handle_tool_calls(
    self,
    tool_calls: list[dict],
    registry: ToolRegistry,
) -> list[dict]:
    """Processa tool_calls e retorna mensagens de resposta."""
    results = []
    
    for call in tool_calls:
        name = call["function"]["name"]
        args = call["function"]["arguments"]
        
        try:
            result = registry.execute(name, args)
            results.append({
                "role": "tool",
                "content": str(result),
                "tool_name": name,
            })
        except Exception as e:
            results.append({
                "role": "tool", 
                "content": f"Error: {e}",
                "tool_name": name,
            })
    
    return results
```

Fluxo no REPL:
```
User: "Liste os arquivos Python no diretório atual"
Model: tool_calls: [{"name": "list_files", "arguments": {"pattern": "*.py"}}]
System: Executa list_files("*.py") -> "main.py, utils.py, test.py"
Model: "Encontrei 3 arquivos Python: main.py, utils.py e test.py"
```

#### 3.2 Modos de Execução
```python
class ToolExecutionMode(Enum):
    DISABLED = "disabled"      # Tools não são enviadas ao modelo
    MANUAL = "manual"          # Pergunta antes de executar cada tool
    AUTO = "auto"              # Executa automaticamente
    AUTO_SAFE = "auto_safe"    # Executa apenas tools "seguras" automaticamente
```

#### 3.3 Comandos do Chat
```
>>> /tools              # Lista tools disponíveis
>>> /tools enable <n>   # Habilita tool
>>> /tools disable <n>  # Desabilita tool
>>> /mode auto          # Mudar modo de execução
>>> /sandbox <dir>      # Definir diretório sandbox
```

#### 3.4 Histórico com Tools
Extender `miru/history.py` para incluir:
- Tool calls nos registros
- Resultados de tools
- Estatísticas de uso

---

### FASE 4: CLI para Tools (2-3 dias)

#### 4.1 Comando `miru tools`
**Novo arquivo**: `miru/commands/tools_cmd.py`

```bash
# Listar tools disponíveis
miru tools list

# Ver detalhes de uma tool
miru tools show read_file

# Executar tool diretamente (para teste)
miru tools exec read_file --arg path="README.md"

# Gerar documentação de tools
miru tools docs --output TOOLS.md
```

#### 4.2 Configuração de Tools
**Extender**: `miru/config_manager.py`

```toml
[tools]
enabled = true
execution_mode = "auto"
sandbox_dir = "~/.miru/sandbox"

[tools.whitelist]
files = ["read_file", "list_files"]
system = ["get_current_dir"]
web = []

[tools.blacklist]
files = []
system = ["run_command"]  # Desabilitar por segurança
```

```bash
miru config set tools.enabled true
miru config set tools.execution_mode manual
miru config set tools.sandbox_dir ./workspace
```

---

### FASE 5: Safety & Sandbox (2-3 dias)

#### 5.1 Sandbox de Arquivos
**Novo arquivo**: `miru/tools/sandbox.py`

```python
class FileSandbox:
    """Gerencia sandbox para operações de arquivo."""
    
    def __init__(self, root: Path, allow_write: bool = False):
        self._root = root.resolve()
        self._allow_write = allow_write
    
    def resolve_path(self, path: str) -> Path:
        """Resolve path garantindo que está dentro do sandbox."""
        full = (self._root / path).resolve()
        if not full.is_relative_to(self._root):
            raise SecurityError(f"Path escapes sandbox: {path}")
        return full
    
    def read_file(self, path: str) -> str:
        return self.resolve_path(path).read_text()
    
    def write_file(self, path: str, content: str) -> None:
        if not self._allow_write:
            raise PermissionError("Write operations disabled")
        self.resolve_path(path).write_text(content)
```

#### 5.2 Rate Limiting
```python
class RateLimiter:
    """Limita execuções de tools."""
    
    def __init__(self, max_calls: int = 10, window: int = 60):
        self._max = max_calls
        self._window = window
        self._calls: list[float] = []
    
    def check(self) -> bool:
        """Verifica se pode executar."""
        now = time.time()
        self._calls = [c for c in self._calls if now - c < self._window]
        
        if len(self._calls) >= self._max:
            raise RateLimitError(f"Max {self._max} calls per {self._window}s")
        
        self._calls.append(now)
        return True
```

#### 5.3 Auditoria
```python
class ToolAudit:
    """Registra todas as execuções de tools."""
    
    def log(self, name: str, args: dict, result: Any, error: Exception | None) -> None:
        entry = {
            "timestamp": datetime.now().isoformat(),
            "tool": name,
            "args": args,
            "result": str(result)[:500],  # Truncar
            "error": str(error) if error else None,
        }
        self._append_to_log(entry)
```

Logs em `~/.miru/tools_audit.jsonl`

---

### FASE 6: Features Avançadas (3-4 dias)

#### 6.1 Tools Customizadas
Permitir usuários definirem suas próprias tools:

**Arquivo**: `miru/tools/custom.py`

```python
def load_custom_tools(path: Path) -> list[Tool]:
    """Carrega tools customizadas de arquivo Python."""
    spec = importlib.util.spec_from_file_location("custom_tools", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    
    tools = []
    for name, obj in inspect.getmembers(module):
        if hasattr(obj, "_tool_definition"):
            tools.append(Tool(
                name=obj.__name__,
                description=obj.__doc__,
                parameters=obj._tool_definition,
                handler=obj,
            ))
    return tools
```

Exemplo de arquivo de custom tools:
```python
# ~/.miru/tools/my_tools.py

def get_my_api_data(endpoint: str) -> dict:
    """Busca dados da minha API interna.
    
    Args:
        endpoint: Endpoint da API (ex: /users)
    """
    import requests
    return requests.get(f"http://myapi:8000{endpoint}").json()

get_my_api_data._tool_definition = {
    "type": "object",
    "properties": {
        "endpoint": {"type": "string"}
    },
    "required": ["endpoint"]
}
```

```bash
miru tools load ~/.miru/tools/my_tools.py
```

#### 6.2 Tool Chaining
Permitir que models chamem múltiplas tools em sequência:

```python
async def process_tool_loop(
    self,
    messages: list[dict],
    max_iterations: int = 5,
) -> str:
    """Loop de execução de tools até resposta final."""
    for _ in range(max_iterations):
        response = await self.client.chat_with_tools(
            model=self.model,
            messages=messages,
            tools=self.registry.get_definitions(),
        )
        
        tool_calls = extract_tool_calls(response)
        
        if not tool_calls:
            return response["message"]["content"]
        
        tool_results = await self.handle_tool_calls(tool_calls)
        messages.extend(tool_results)
    
    raise MaxIterationsError()
```

#### 6.3 Context Injection
Injetar contexto automaticamente:

```python
@registry.register
def get_current_file() -> str:
    """Retorna o arquivo sendo editado (se houver)."""
    # Injetado automaticamente pelo chat quando user passa --file
    return registry.context.get("current_file")
```

---

### FASE 7: Documentação e Examples (2 dias)

#### 7.1 Documentação de Tools
**Novo arquivo**: `docs/TOOLS.md`

- Lista de todas as tools
- Parâmetros e exemplos
- Guia de segurança
- Como criar tools customizadas

#### 7.2 Examples
**Extender**: `miru/commands/examples.py`

```python
examples = {
    "tools-list-files": {
        "command": "miru chat --sandbox . --tools files',
        "description": "Chat com tools de arquivo",
    },
    ...
}
```

#### 7.3 README Updates
Adicionar seção sobre Tools:
```markdown
## Tools / Function Calling

Miru suporta **function calling** nativo do Ollama, permitindo que modelos executem ações:

miru chat --tools files,system --sandbox ~/projects

Tools disponíveis:
- **files**: Ler, escrever, buscar arquivos
- **system**: Comandos de sistema (whitelist)
- **web**: Buscar URLs

### Modos de Execução

- `--tool-disable`: Desabilita todas as tools
- `--tool-ask`: Pergunta antes de executar cada tool
- `--tool-auto`: Executa automaticamente (padrão para tools seguras)
```

---

## Cronograma Estimado

| Fase | Duração | Prioridade |
|------|---------|------------|
| FASE 1: Infraestrutura | 3-4 dias | Alta |
| FASE 2: Tools Internas | 4-5 dias | Alta |
| FASE 3: Integração Chat | 3-4 dias | Alta |
| FASE 4: CLI Tools | 2-3 dias | Média |
| FASE 5: Safety & Sandbox | 2-3 dias | Alta |
| FASE 6: Features Avançadas | 3-4 dias | Baixa |
| FASE 7: Documentação | 2 dias | Média |
| **TOTAL** | **19-25 dias** | |

---

## Riscos e Mitigações

### Risco 1: Segurança
- **Problema**: Execução arbitrária de código/comandos
- **Mitigação**: Sandbox, whitelists, rate limiting, auditoria, modo manual

### Risco 2: Compatibilidade de Modelos
- **Problema**: Nem todos os modelos suportam function calling bem
- **Mitigação**: Documentação clara, warning se modelo não suporta, graceful degradation

### Risco 3: Loop Infinito
- **Problema**: Modelo chama tools indefinidamente
- **Mitigação**: Max iterations, timeout, detecção de loops

### Risco 4: Performance
- **Problema**: Tool calls podem ser lentos
- **Mitigação**: Caching, async, timeout por tool

---

## Dependencies

### Novas dependencies
- Nenhuma obrigatória (stdlib é suficiente)
- **Opcional**: 
  - `pydantic` para validação de schemas de tools
  - ` RestrictedPython` para sandbox Python mais robusta

---

## Success Metrics

1. **Funcionalidade**: Modelos podem executar tools via chat interativo
2. **Segurança**: Nenhuma execução de código arbitrário sem aprovação
3. **UX**: Fluxo natural de conversa com tools
4. **Performance**: Tool execution < 500ms (95th percentile)
5. **Testes**: >80% code coverage em módulos de tools

---

## Próximos Passos Imediatos

1. **Implementar FASE 1** (infraestrutura)
   - Extender `OllamaClient` com suporte a tools
   - Criar classes `Tool` e `ToolRegistry`
   - Escrever testes unitários

2. **Validar com modelo real**
   - Testar com `llama3.2` (suporta function calling)
   - Verificar parsing de tool_calls
   - Testar tool simples (ex: `read_file`)

3. **Implementar FASE 3** (integração chat)
   - Modificar `miru/commands/chat.py`
   - Adicionar loop de tool execution
   - Command handlers para `/tools`, `/mode`

4. **Adicionar segurança (FASE 5)**
   - Sandbox de arquivos
   - Rate limiting
   - Auditoria

---

## Exemplo de Uso Final

```bash
# 1. Iniciar chat com tools
miru chat llama3.2 --tools files,system --sandbox ./project

# 2. User pergunta
>>> "Analise os arquivos Python neste projeto e sugira melhorias"

# 3. Modelo chama tools automaticamente
[Tool: list_files(pattern="*.py")]
→ Found: main.py, utils.py, config.py

[Tool: read_file(path="main.py")]
→ class DataProcessor: ...

[Tool: read_file(path="utils.py")]
→ def helper(): ...

# 4. Modelo responde
"Analisando o código, identifiquei 3 melhorias possíveis..."

# 5. User pede ação
>>> "Crie um arquivo com as sugestões"

# 6. Modelo executa
[Tool: write_file(path="suggestions.md", content="# Sugestões...")]
→ File created

# 7. Confirmação
"Criei suggestions.md com as sugestões!"
```

---

## Notas de Implementação

### Models com Function Calling
- `llama3.1`, `llama3.2`: ✅ Suportado
- `qwen2.5`: ✅ Suportado
- `mistral`: ✅ Suportado
- Modelos antigos: ❌ Não suportam

### Formato de tool_calls
```json
{
  "tool_calls": [
    {
      "function": {
        "name": "tool_name",
        "arguments": {"arg1": "value1"}
      }
    }
  ]
}
```

### Ordem de Precedência de Config
1. CLI flags (`--tools`, `--sandbox`)
2. Environment variables (`MIRU_TOOLS_ENABLED`)
3. Config file (`~/.miru/config.toml`)
4. Defaults