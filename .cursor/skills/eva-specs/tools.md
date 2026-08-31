# Tools Spec — v0.1 Cheatsheet

Source: `E.V.A./docs/TOOLS_SDK_SPEC_v0.1.md`

## Definition

Tool = agent capability. Exposes commands and may emit events. No business logic.

```text
Agent → Skill → Action → Tool (command) → Event
```

## Principles

1. Tool does not know business domain (requests, foremen, procurement).
2. Tool does not control FSM — emits events, runtime routes to FSM.
3. Runtime depends on manifest/contract, not implementation library.

## Manifest (conceptual)

```yaml
id: telegram
version: "1.0.0"
commands:
  - id: send_message
    input_schema: ...
    output_schema: ...
events:
  - id: message.received   # → channel.message.received at platform level
```

## Command execution

```python
result = await tool.run(command, input, context)
# result.ok, result.data, result.events
```

Tool may return domain events in `result.events`; runtime publishes them.

## Package layout (E.V.A.)

```text
backend/tools/
├── base.py, registry.py, credential_resolver.py
├── llm/stub.py
├── telegram/tool.py, stub.py
├── polza/client.py, llm.py
└── web_client/config.py, http.py, tool.py
```

Import via package: `from tools.telegram import TelegramTool`

## Credentials

- Stored per agent + tool binding
- Resolved at runtime via `credential_resolver.py`
- API routes under `/api/agents/{slug}/tools/{tool_id}/`

## Adding a new tool

1. Create `backend/tools/<name>/` package
2. Export public API from `__init__.py`
3. Register in `definition/catalog/builtin_tools.py`
4. Wire in `runtime/definition_loader.py`
5. Add frontend entry in `features/tools/registry/builtinTools.ts`

## Backend

- Protocol: `backend/tools/base.py`
- Registry: `backend/tools/registry.py`
- Loader: `backend/runtime/definition_loader.py`
- Catalog: `backend/definition/catalog/builtin_tools.py`

## Frontend

- Registry: `frontend/src/features/tools/registry/builtinTools.ts`
- Bindings UI: `frontend/src/features/tools/views/ToolsListView.vue`
