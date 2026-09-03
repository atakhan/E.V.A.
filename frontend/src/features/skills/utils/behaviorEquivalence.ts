import type { FsmState } from "@/features/skills/types/fsm";
import { normalizeGuard } from "@/features/skills/utils/behaviorGraph";

export function fsmBehaviorallyEquivalent(
  leftStates: FsmState[] | undefined,
  leftInitial: string | null | undefined,
  rightStates: FsmState[] | undefined,
  rightInitial: string | null | undefined,
): boolean {
  const left = leftStates ?? [];
  const right = rightStates ?? [];
  if (left.length === 0 && right.length === 0) return true;
  const leftIndex = new Map(left.map((state) => [state.id, state]));
  const rightIndex = new Map(right.map((state) => [state.id, state]));
  if (!leftInitial || !leftIndex.has(leftInitial)) return false;
  if (!rightInitial || !rightIndex.has(rightInitial)) return false;

  const mapping = new Map<string, string>();

  function labels(state: FsmState) {
    return [...state.transitions]
      .map((transition) => ({
        event: transition.event,
        guard: normalizeGuard(transition.guard),
        actions: transition.actions.filter(Boolean).join("\0"),
        to: transition.to,
      }))
      .sort((a, b) =>
        `${a.event}|${a.guard}|${a.actions}`.localeCompare(`${b.event}|${b.guard}|${b.actions}`),
      );
  }

  function match(leftId: string, rightId: string, stack: Set<string>): boolean {
    const pair = `${leftId}::${rightId}`;
    if (stack.has(pair)) return true;
    if (mapping.has(leftId)) return mapping.get(leftId) === rightId;
    const leftState = leftIndex.get(leftId);
    const rightState = rightIndex.get(rightId);
    if (!leftState || !rightState) return false;
    const leftRows = labels(leftState);
    const rightRows = labels(rightState);
    if (
      leftRows.map((row) => `${row.event}|${row.guard}|${row.actions}`).join(";") !==
      rightRows.map((row) => `${row.event}|${row.guard}|${row.actions}`).join(";")
    ) {
      return false;
    }
    if (leftRows.length === 0 && rightRows.length === 0 && Boolean(leftState.final) !== Boolean(rightState.final)) {
      return false;
    }
    mapping.set(leftId, rightId);
    stack.add(pair);
    for (let index = 0; index < leftRows.length; index += 1) {
      if (!match(leftRows[index].to, rightRows[index].to, stack)) return false;
    }
    return true;
  }

  return match(leftInitial, rightInitial, new Set());
}
