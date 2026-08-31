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
├── agents/       # CRUD, overview, validateAgent
├── skills/       # Skill FSM canvas
├── actions/      # Action catalog + recipes
├── tools/        # Tool registry + bindings
└── workspace/
```

## Data model

```ts
Agent { skills, actions, tools: ToolBinding[] }
Skill { initial, params, states[], viewport }
ActionDef { id, version, policy, inputSchema, outputSchema, recipe: { id, tool, command, input, when? }[] }
ToolBinding { toolId, enabled, configNote }
```

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

`/agents` · `/runtime` · `/:slug/overview|skills|actions|tools|runtime` · `/:slug/runtime/simulate` · `/:slug/runtime/runs/:runId`

## Dev

```bash
cd frontend && npm run build
```
