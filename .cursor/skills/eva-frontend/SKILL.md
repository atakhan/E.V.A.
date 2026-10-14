---
name: eva-frontend
description: >-
  E.V.A. frontend architecture (Vue 3, TypeScript, feature-based layout).
  Use when editing frontend, adding modules, routes, composables,
  components, or working with agents/skills/actions/tools/FSM canvas UI.
---

# E.V.A. Frontend

**Read this skill first** when the task touches `frontend/`.

Stack: Vue 3 + TypeScript + Vue Router + Tailwind v4 + daisyUI. Path alias `@/` → `src/`.

## Directory layout

```
features/
├── agents/       # CRUD, overview, validateAgent, world addresses
├── constructor/  # docking table: addresses, world channels, agent, skills
├── skills/       # FSM canvas editor
├── actions/      # Action catalog + recipes
├── tools/        # Tool registry + bindings; library splits world vs action tools
├── runtime/      # cockpit, runs, simulate
└── workspace/    # floating section menu
```

World-axis contract: `docs/03-architecture/constructor-world-axis.md`.

## Data model

```ts
Agent { skills, actions, tools: ToolBinding[], defaultSkillId?, constructorLayout?, world?: { addresses } }
Skill { initial, params, states[] }
ActionDef { id, version, policy, inputSchema, outputSchema, recipe: { id, tool, command, input, when? }[] }
ToolBinding { toolId, enabled, configNote }
```

Skill editor source of truth is the FSM (`states[]`). UI: FsmCanvas + SkillInspector.  
Canvas geometry (orthogonal routing, obstacles, labels): `docs/FSM_CANVAS_GEOMETRY.md`, code `features/skills/utils/geometry/`.
The agent docking table (`features/constructor/`) is a separate canvas.

## Validation (constructor)

`agents/utils/validateAgent.ts` — no runtime:

- initial exists among states
- transition `to` known
- FSM action ids exist in catalog
- recipe tools enabled + commands known
- unused actions / empty skills as info/warning

Overview shows report + linked Skills / Actions / enabled Tools.

## Specs

Platform contracts: `.cursor/skills/eva-specs/SKILL.md` (Actions, Skills, Events, Tools).

## Routing

`/agents` · `/tools` · `/runtime` · `/:slug/constructor|overview|skills|actions|tools|logs|runtime` · `/:slug/runtime/simulate` · `/:slug/runtime/runs/:runId`

## Dev

```bash
cd frontend && npm run build
```
