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
├── text/tool.py, regex_utils.py, validators.py
└── web_client/config.py, http.py, tool.py
```

Import via package: `from tools.telegram import TelegramTool`

## Credentials

- Stored per agent + tool binding
- Resolved at runtime via `credential_resolver.py`
- API routes under `/api/agents/{slug}/tools/{tool_id}/`

## Adding a new tool

1. `tools/<name>/manifest.py` — inputSchema per command
2. `tools/<name>/tool.py` + `__init__.py`
3. Register manifest in `definition/catalog/builtin_tools.py`
4. Wire in `runtime/definition_loader.py`
5. Frontend loads catalog from `GET /api/tools/catalog` (no manual TS duplicate)

Field schema: `E.V.A./docs/TOOL_FIELD_SCHEMA_v0.1.md`
Scaffold: `python -m tools.scaffold create <name> --commands "foo,bar"`

## Backend

- Protocol: `backend/tools/base.py`
- Field schema: `definition/catalog/field_schema.py`
- Catalog: `definition/catalog/builtin_tools.py` (manifest aggregator)

## Frontend

- Catalog store: `features/tools/services/toolCatalogStore.ts`
- Schema form: `shared/schema/SchemaDrivenForm.vue`
- Recipe fields: `features/actions/utils/commandInputSchema.ts`
