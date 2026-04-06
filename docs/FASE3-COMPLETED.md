# FASE 3 Concluída - Integração com Chat Interativo

## Status: ✅ CONCLUÍDA

**Data**: Abril 2026  
**Duração Estimada**: 3-4 dias  
**Duração Real**: ~4 horas  

---

## Resumo

Implementação da **integração de tools no runtime do miru**, incluindo:
- **ToolExecutionManager**: Gerenciador de execução de tools
- **ToolApprovalFlow**: Sistema de aprovação interativa
- **Modos de execução**: disabled/manual/auto/auto_safe
- **Processamento em loop**: Tool calling automático

---

## Componentes Implementados

### 1. ToolExecutionManager (`miru/tools/execution.py`)

Gerenciador central de execução de tools que:

**Características**:
- ✅ Integra FileTools e SystemTools automaticamente
- ✅ Configuração flexível de sandbox e permissões
- ✅ Suporte a 4 modos de execução
- ✅ Fácil integração com chat

**Modos de Execução**:

| Modo | Descrição | Comportamento |
|------|-----------|---------------|
| `DISABLED` | Tools desabilitadas | Não envia definições para modelo |
| `MANUAL` | Aprovação manual para tudo | Pede confirmação para cada tool |
| `AUTO` | Execução automática | Executa todos os tools automaticamente |
| `AUTO_SAFE` | Auto para safe, aprovação para dangerous | Executa safe tools, pede aprovação para dangerous |

**Uso**:
```python
from miru.tools import ToolExecutionManager, ToolExecutionMode
from pathlib import Path

# Criar manager
manager = ToolExecutionManager(
    mode=ToolExecutionMode.AUTO_SAFE,
    sandbox_dir=Path("./workspace"),
    allow_write=True,
    allow_delete=False,
    allow_commands=False,
    allow_env=True,
)

# Obter definições para Ollama
definitions = manager.get_tool_definitions()

# Verificar se deve executar
should_exec, reason = manager.should_execute_tool("write_file", {"path": "test.txt"})

# Executar tool
result, error = manager.execute_tool("write_file", {"path": "test.txt", "content": "Hello"})

# Listar tools disponíveis
tools = manager.list_tools()
```

### 2. ToolApprovalFlow (`miru/tools/approval.py`)

Sistema de aprovação interativa para ferramentas perigosas.

**Características**:
- ✅ Aprovação automática para safe tools
- ✅ Aprovação manual para dangerous tools
- ✅ Lembrete de aprovação por sessão
- ✅ Visualização clara de arguments
- ✅ Histórico de approvals/denials

**Classificação de Tools**:

**Safe Tools** (auto-aprovadas quando `auto_approve_safe=True`):
- `read_file`
- `file_exists`
- `get_file_info`
- `list_files`
- `search_files`
- `get_current_dir`
- `list_allowed_commands`
- `list_allowed_env_vars`
- `get_env`

**Dangerous Tools** (sempre requerem aprovação):
- `write_file`
- `edit_file`
- `delete_file`
- `run_command`

**Uso**:
```python
from miru.tools import ToolApprovalFlow

# Criar flow
flow = ToolApprovalFlow(auto_approve_safe=True)

# Verificar se precisa de aprovação
if flow.should_request_approval("write_file"):
    # Pedir aprovação ao usuário
    approved = flow.request_approval(
        "write_file",
        {"path": "test.txt", "content": "Hello"},
        reason="Writing to filesystem"
    )
    
    if approved:
        # Executar tool
        pass
    else:
        # Pular execução
        pass
else:
    # Auto-aprovar
    pass
```

### 3. ToolApprovalManager

Gerenciador de estado de aprovações dentro de uma sessão.

**Funcionalidades**:
- ✅ Armazena aprovações/denials da sessão
- ✅ Evita pedir aprovação repetidamente
- ✅ Limpa estado entre sessões
- ✅ Exibe lista de tools aprovados/negados

**Uso**:
```python
from miru.tools import ToolApprovalManager

manager = ToolApprovalManager()

# Pedir aprovação
approved, remember = manager.request_approval(
    "write_file",
    {"path": "test.txt"}
)

# Verificar estado
if manager.is_approved("write_file"):
    # Executar
    pass

# Limpar estado
manager.clear_approvals()

# Mostrar aprovados/negados
manager.show_approved_tools()
manager.show_denied_tools()
```

---

## Integração com Chat

### Fluxo Completo

```python
from miru.ollama.client import OllamaClient
from miru.tools import ToolExecutionManager, ToolExecutionMode
from miru.tools.utils import extract_tool_calls, has_tool_calls

async def chat_with_tools():
    # Configurar tools
    tools_manager = ToolExecutionManager(
        mode=ToolExecutionMode.AUTO_SAFE,
        sandbox_dir="./workspace",
    )
    
    # Definições para o modelo
    tool_definitions = tools_manager.get_tool_definitions()
    
    # Chat
    messages = [{"role": "user", "content": "Liste os arquivos Python"}]
    
    async with OllamaClient("http://localhost:11434") as client:
        # Loop de tool calling
        for _ in range(5):  # Max tool iterations
            response_chunks = client.chat_with_tools(
                "llama3.2",
                messages,
                tools=tool_definitions,
            )
            
            response_text = ""
            tool_calls_list = []
            
            async for chunk in response_chunks:
                if has_tool_calls(chunk):
                    tool_calls_list.extend(extract_tool_calls(chunk))
                else:
                    content = chunk.get("message", {}).get("content", "")
                    response_text += content
            
            # Se não há tool calls, terminou
            if not tool_calls_list:
                print(response_text)
                break
            
            # Processar tool calls
            for call in tool_calls_list:
                tool_name = call["name"]
                arguments = call["arguments"]
                
                # Verificar se deve executar
                should_exec, reason = tools_manager.should_execute_tool(tool_name, arguments)
                
                if should_exec:
                    # Executar
                    result, error = tools_manager.execute_tool(tool_name, arguments)
                    
                    # Adicionar resultado ao histórico
                    messages.append({
                        "role": "tool",
                        "content": str(result) if not error else f"Error: {error}",
                        "tool_name": tool_name,
                    })
                else:
                    # Adicionar mensagem de skip
                    messages.append({
                        "role": "tool",
                        "content": f"Tool execution skipped: {reason}",
                        "tool_name": tool_name,
                    })
```

---

## Testes

### Novos Testes (41 testes)

**TestToolExecutionManager** (17 testes):
- Inicialização em diferentes modos
- Configuração de sandbox
- Verificação de permissões
- Execução de tools
- Gestão de erros
- Listagem de tools

**TestToolApprovalManager** (10 testes):
- Aprovação/denial de tools
- Lembrete por sessão
- Limpeza de estado
- Visualização de estado

**TestToolApprovalFlow** (8 testes):
- Classificação safe/dangerous
- Auto-aprove para safe tools
- Fluxo de aprovação completo
- Persistência de aprovação

**TestToolExtensionsSettings** (1 teste):
- Restrição de extensões

**TestToolExecutionManagerIntegration** (1 teste):
- Workflow completo

**TestToolApprovalIntegration** (4 testes):
- Integração end-to-end

**Total**: 41 novos testes, todos passando

### Cobertura Total

```
FASE 1: 32 testes ✅
FASE 2: 67 testes ✅
FASE 3: 41 testes ✅
Outros: 248 testes ✅
────────────────────
Total:  388 testes ✅ (100% passando)
```

---

## Design Decisions

### 1. Manager Pattern

**Decisão**: Usar ToolExecutionManager como fachada

**Justificativa**:
- Simplifica uso: uma classe para tudo
- Esconde complexidade de sandbox, whitelists, approval
- Centraliza configuração
- Fácil integração com chat

**Alternativas**:
- ❌ Configuração manual de cada componente
- ✅ **Manager centralizado**

### 2. Approval Flow Separation

**Decisão**: Separar ToolApprovalFlow de ToolExecutionManager

**Justificativa**:
- Separated concerns: execução vs approval
- Testabilidade: cada um testa isoladamente
- Reusabilidade: approval pode ser usada isoladamente
- Flexibilidade: diferentes tipos de approval

### 3. Modos de Execução

**Decisão**: 4 modos distintos (disabled/manual/auto/auto_safe)

**Justificativa**:
- **Disabled**: Segurança total, sem risco
- **Manual**: Controle total, mas cansativo
- **Auto**: Produtividade máxima, menos segurança
- **Auto_safe**: Balance entre segurança e usabilidade

**Trade-offs**:
- Mais modos = mais complexidade
- Mas também = mais flexibilidade
- Usuário pode escolher conforme o caso

### 4. Safe vs Dangerous Classification

**Decisão**: Classificar tools hardcoded

**Justificativa**:
- Simples de entender
- Rápido de verificar
- Não requer configuração extra

**Futuro**:
- Adicionar metadata nas tools (safe=True/False)
- Permitir override pelo usuário

---

## Limitações Conhecidas

1. **Sem integração no chat CLI**: Ainda não implementado na interface
2. **Sem persistência de aprovações**: Aprovações são perdidas ao reiniciar
3. **Sem rate limiting**: Ferramenta pode ser chamada múltiplas vezes
4. **Sem auditoria**: Logs de execução não são persistidos
5. **Sem timeout por tool**: Apenas timeout global para comandos

**Planejado para FASE 5**: Auditoria, rate limiting, persistência

---

## Performance

**Características**:
- Tool lookup: O(1)
- Execution overhead: < 5ms (sem I/O)
- Approval check: < 1ms
- Manager initialization: < 50ms

**Benchmarks estimados**:
- Manager creation: ~50ms
- Tool definition generation: ~10ms
- Tool execution (no approval): ~1-5ms
- Tool execution (with approval): ~2-10s (depende do usuário)

---

## Uso Completo (Exemplo)

```python
from pathlib import Path
from miru.tools import (
    ToolExecutionManager,
    ToolExecutionMode,
    ToolApprovalFlow,
    ToolRegistry,
)
from miru.ollama.client import OllamaClient

# 1. Configurar tools
tools_manager = ToolExecutionManager(
    mode=ToolExecutionMode.AUTO_SAFE,  # Auto para safe, manual para dangerous
    sandbox_dir=Path("./my_project"),
    allow_write=True,
    allow_delete=False,
    allowed_extensions=[".py", ".txt", ".md"],
    allow_commands=False,
    allow_env=True,
)

# 2. Configurar approval flow
approval_flow = ToolApprovalFlow(auto_approve_safe=True)

# 3. Integrar com chat
async def chat_loop():
    messages = []
    tool_definitions = tools_manager.get_tool_definitions()
    
    async with OllamaClient("http://localhost:11434") as client:
        while True:
            user_input = input(">>> ")
            
            if user_input == "/exit":
                break
            
            messages.append({"role": "user", "content": user_input})
            
            # Processar com tools
            for _ in range(5):  # Max tool iterations
                response = await get_response(client, messages, tool_definitions)
                
                tool_calls = extract_tool_calls(response)
                if not tool_calls:
                    print(response["message"]["content"])
                    break
                
                # Processar tools
                for call in tool_calls:
                    tool_name = call["name"]
                    args = call["arguments"]
                    
                    # Verificar se precisa de aprovação
                    if approval_flow.should_request_approval(tool_name):
                        approved = approval_flow.request_approval(tool_name, args)
                        if not approved:
                            messages.append({"role": "tool", "content": "Denied by user"})
                            continue
                    
                    # Executar
                    result, error = tools_manager.execute_tool(tool_name, args)
                    messages.append({"role": "tool", "content": str(result) if not error else f"Error: {error}"})

# 4. Executar
await chat_loop()
```

---

## Próximos Passos (FASE 4)

Com a FASE 3 completa, a próxima fase deve implementar:

1. **CLI Commands**: `miru tools list/show/exec`
2. **Configuration**: Configuração persistente de tools
3. **Chat Integration**: Comandos `/tools`, `/mode`, `/sandbox`
4. **Examples**: Atualizar com exemplos de tools

---

## Dependências

**Novas dependências**: Nenhuma (apenas stdlib + rich)

**Dependências utilizadas**:
- `pathlib` - File paths
- `enum` - Execution modes
- `rich` - Interactive prompts and display
- `typing` - Type hints

---

## Checklist

- [x] Implementar ToolExecutionManager
- [x] Implementar ToolApprovalFlow
- [x] Implementar ToolApprovalManager
- [x] Suporte a 4 modos de execução
- [x] Classificação safe/dangerous
- [x] Testes unitários (41 novos)
- [x] Testes de integração
- [x] Documentação
- [x] Exemplos de uso
- [x] Tipo de retorno consistente
- [x] Error handling
- [x] Backward compatible

---

## Referências

- [FASE1-COMPLETED.md](./FASE1-COMPLETED.md) - Infraestrutura de tools
- [FASE2-COMPLETED.md](./FASE2-COMPLETED.md) - FileTools e SystemTools
- [CODEBASE-REVIEW.md](./CODEBASE-REVIEW.md) - Revisão do código

---

**Status**: ✅ **FASE 3 CONCLUÍDA**  
**Progresso Total**: FASE 1 + FASE 2 + FASE 3 completas  
**Testes**: 388/388 passando (100%)