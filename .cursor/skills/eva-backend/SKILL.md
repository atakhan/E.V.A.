---
name: eva-backend
description: >-
  E.V.A. backend architecture (FastAPI, runtime, tools). Use when editing
  E.V.A./backend, adding tools, runtime logic, API routes, or working with
  agents/skills/actions/events/tools execution.
---

# E.V.A. Backend

**Read this skill first** when the task touches `E.V.A./backend/`.

Stack: Python 3 + FastAPI + PostgreSQL + Redis + pytest.

## Directory layout

```
E.V.A./backend/
├── app/              # FastAPI entry, API routes, config
├── domain/           # Agent, Skill, Action, Event models
├── definition/       # Mappers, validation, catalog, services
├── runtime/          # FSM, skill runner, action executor, loader
├── infrastructure/   # Postgres, Redis, stores
├── tools/            # Tool implementations (one package per tool)
├── workers/          # Background workers (runtime, telegram poller)
├── scenarios/        # Demo / seed scenarios (foreman)
└── tests/
```

## Tools layout

Each built-in tool lives in its own package under `tools/`:

```
tools/
├── base.py                 # Tool protocol
├── registry.py             # ToolRegistry
├── credential_resolver.py  # shared credential helpers
├── llm/
│   └── stub.py             # LlmStubTool
├── telegram/
│   ├── tool.py             # TelegramTool
│   └── stub.py             # TelegramStubTool
├── polza/
│   ├── client.py           # PolzaClient, PolzaApiError
│   └── llm.py              # PolzaAiLlmTool
└── web_client/
    ├── config.py
    ├── http.py
    └── tool.py
```

Import via package `__init__.py` — not from internal modules:

```python
from tools.llm import LlmStubTool
from tools.telegram import TelegramTool, TelegramStubTool
from tools.polza import PolzaClient, PolzaApiError, PolzaAiLlmTool
from tools.web_client import WebClientTool, WebClientHttp, parse_web_client_binding_config
```

When adding a new tool: create `tools/<name>/`, export public API from `__init__.py`, register in `definition_loader.py` and `definition/catalog/builtin_tools.py`.

## Runtime model

```text
Event → EventRouter → SkillRunner (FSM) → ActionExecutor → Tool → Event
```

- Agent document: skills, actions, tool bindings
- `runtime/definition_loader.py` — builds ToolRegistry from agent bindings
- Specs: `docs/ACTIONS_SPEC_v0.1.md`, `docs/SKILLS_SPEC_v0.1.md`, `docs/EVENT_SPEC_v0.1.md`, `docs/TOOLS_SDK_SPEC_v0.1.md`
- Cursor cheatsheets: `.cursor/skills/eva-specs/`

## Tests

```bash
# full (postgres + redis)
docker compose run --rm backend pytest tests/ -q

# unit only
docker compose run --rm --no-deps backend pytest tests/ -q -m "not integration"
```
