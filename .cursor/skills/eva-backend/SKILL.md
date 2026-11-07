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
├── text/
│   ├── tool.py             # TextTool
│   ├── regex_utils.py
│   └── validators.py
├── ssh_commands/
│   ├── manifest.py         # ssh_commands catalog + run
│   ├── library.py          # per-instance command library
│   ├── runner.py           # OpenSSH client
│   └── tool.py             # SshCommandsTool
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
from tools.text import TextTool
from tools.web_client import WebClientTool, WebClientHttp, parse_web_client_binding_config
```

When adding a new tool: create `tools/<name>/manifest.py` + `tool.py`, register in `builtin_tools.py` aggregator and `definition_loader.py`. Frontend catalog loads from `GET /api/tools/catalog`.

A manifest without a runtime builder carries `"implemented": False` (see `definition/catalog/manifests/stubs.py`). `tests/test_catalog_completeness.py` fails when the flag and `definition_loader` disagree; validation reports an enabled unimplemented instance as `unimplemented_tool`.

What counts as a draft change against the latest publication is `_RUNTIME_PARTS` in `definition/services/agent_service.py`. A new document field that runtime reads from the publication belongs there.

`visible_run_memory` in `runtime/skill_run_query.py` is what a person may read from a run: `params` (lifted from `vars._skill_params`) and `vars` without keys that start with `_`. `GET /api/runtime/runs/{id}` and `GET /api/runtime/agents/{slug}/memory` both use it.

## Runtime model

```text
Event → EventRouter → SkillRunner (FSM) → ActionExecutor → Tool → Event
```

- Agent document: skills, actions, tool bindings
- `runtime/definition_loader.py` — builds ToolRegistry from agent bindings
- Specs: `docs/ACTIONS_SPEC_v0.1.md`, `docs/SKILLS_SPEC_v0.1.md`, `docs/EVENT_SPEC_v0.1.md`, `docs/TOOLS_SDK_SPEC_v0.1.md`, `docs/INTERACTION_SPEC_v0.1.md` (target: dispatcher / conversation ≠ run)
- Cursor cheatsheets: `.cursor/skills/eva-specs/`

## Tests

```bash
# full (postgres + redis)
docker compose run --rm backend pytest tests/ -q

# unit only
docker compose run --rm --no-deps backend pytest tests/ -q -m "not integration"
```
