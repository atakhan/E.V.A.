---
name: eva-spatial-ui
description: >-
  E.V.A. spatial desks, agent/project orbits, one-pass mode transitions, and
  handoff. Use when editing ProjectsListView, ProjectDeskView, ProjectsDesk,
  ProjectDesk, ConstructorView channel/layer motion, packedOrbit, orbitStyles,
  desk motion helpers, or when building UI around agent/project icons on orbits.
---

# E.V.A. Spatial UI (desks & orbits)

**Read first:** [`docs/06-experiments/constructor-orbit-ui-handoff.md`](../../../docs/06-experiments/constructor-orbit-ui-handoff.md).  
**Invariants:** [`docs/01-concept/spatial-ui-principles.md`](../../../docs/01-concept/spatial-ui-principles.md).  
AlwaysApply rules already encode collaboration + spatial design; follow them.

Also load `.cursor/skills/eva-frontend/SKILL.md` for general frontend layout.

## Non-negotiables

1. Modes are **zoom levels** of one desk, not separate page chrome.
2. **One center + packed upper orbit** (min chord; do not stretch the arc).
3. Transitions are **one pass** — no collapse-then-fly-then-reveal `await` phases.
4. **Handoff:** land destination (opacity snap) → next frame → drop flyer (`motion/handoff.ts`).
5. **Focus exempt** from satellite collapse while flying.
6. **One seat, one icon** — twins and end blinks are bugs.
7. Prefer **reuse/adapt** a working neighbor pattern over inventing a third.

## Where code lives

| Concern | Path |
|---------|------|
| Motion token / wait / frame | `frontend/src/features/projects/motion/useDeskMotion.ts` |
| Seat handoff | `frontend/src/features/projects/motion/handoff.ts` |
| Cross-desk pass state | `frontend/src/features/projects/motion/deskPass.ts` |
| Route-cleared leave mount | `frontend/src/features/projects/motion/leaveHold.ts` |
| Packed orbit algorithm | `frontend/src/features/projects/utils/packedOrbit.ts` |
| Place/icon CSS helpers | `frontend/src/features/projects/utils/orbitStyles.ts` |
| Hub orbit (projects) | `ProjectsDesk.vue` + `projectsHubLayout.ts` |
| Project orbit (agents) | `ProjectDesk.vue` + `deskLayout.ts` |
| Eva hub ↔ project | `ProjectsListView.vue` |
| Project ↔ agent constructor | `ProjectDeskView.vue` |
| Agent hub / channel / layer | `ConstructorView.vue` |

## Working with the owner

- Expect local symptoms + optional desired physics; treat named principles as acceptance.
- Minimal diff; check reverse transition and adjacent modes.
- One concern per pass; commit only when asked.
- Close the loop in symptom/physics language.

## When adding orbit chrome / icon UI

- Keep the composition as **center + satellites**, not a dashboard of cards.
- Hook into existing place/icon styles and desk components; don’t fork a second layout metaphor.
- After motion-related edits: manual checklist in spatial-ui-principles + `vue-tsc` / orbit+motion vitest.
