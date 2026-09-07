# Interaction Spec — v0.1 Cheatsheet

Source: `E.V.A./docs/INTERACTION_SPEC_v0.1.md`  
Plan: `E.V.A./docs/INTERACTION_IMPLEMENTATION_PLAN.md`  
Notes: `E.V.A./docs/INTERACTION_IMPLEMENTATION_NOTES.md`  
Architecture review: `E.V.A./docs/INTERACTION_NOTES_ARCHITECTURE_REVIEW.md`  
Office model: `E.V.A./docs/INTERACTION_OFFICE_MODEL.md`  
Bureau constitution: `E.V.A./docs/INTERACTION_BUREAU_MODEL.md`  
Why the office analogy: `E.V.A./docs/INTERACTION_FUNDAMENTAL_PROBLEM.md`  
Three situation projections: `E.V.A./docs/INTERACTION_WORLD_MODEL.md`  
Office vs code: `E.V.A./docs/INTERACTION_OFFICE_GAP.md`  
Status: **canonical layer**; phases 0–5 in code = control plane (table dispatcher before FSM, desk snapshot / presence), not colleague-at-desk. Not NLU. Honest §16: Q1/Q3 yes; Q2/Q5 if focus; Q4/Q6 no. Do not rewrite `Event.type` further — consume `DispatchDecision`.

## Human model

```text
Desk (world)     — truth of the work (cards, fields)
Voice            — conversation_id / sessionId (where replies go)
Presence         — open Skill Runs the user can see / interrupt
```

Buttons are short phrases, not a second agent.

## Do not collapse

```text
conversation  ≠  skill run  ≠  entity  ≠  focus
1 conversation → 0..N concurrent works
```

Waiting on `conversation_id` must **not** swallow a card button just because the chat skill is waiting for the next message.

## Dispatcher (before FSM)

Classify the human act:

| Class | Do |
|-------|----|
| Reply to a work | `resume` that run |
| Correction | `amend` = cancel + start narrowed |
| New assignment | `start` skill (`разбери` + focus → parse event) |
| Side question | answer; do not cancel background work |
| Stop | `cancel` work, then chat |
| Underspecified | chat asks; do not guess |

`event.type` is a fact, not the skill picker.

## Dual effect

Agent act → world patch + optional utterance + optional `ui.proposal` + presence.

Desk wins over skill `vars` after a human edit.

## Web client minimum

Inbound: `conversation_id`, `actor_id`, `focus`, plus `intent`+`entity_ids` (gesture) or `text` (utterance). These fields are on the web ingress and in ai_supplier chat/dispatch.  
Outbound: text, entity patches, `ui.proposal`, presence snapshot.  
Client must expose a desk snapshot (context).

## Acceptance (all must be yes)

1. Side question while a parse batch runs, without aborting it  
2. Button «parse» and phrase «parse this» are the same work family  
3. Waiting chat does not steal the button via shared `conversation_id`  
4. Clarification visible on card **and** chat; either reply closes the wait  
5. «Do North first» amends the in-flight batch  
6. After a manual quantity edit, the agent speaks the new number
