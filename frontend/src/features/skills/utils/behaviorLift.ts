import type {
  BehaviorEdge,
  BehaviorGraph,
  BehaviorNode,
  DecideBranch,
  WaitFor,
} from "@/features/skills/types/behavior";
import { BEHAVIOR_GRAPH_VERSION, emptyBehaviorGraph } from "@/features/skills/types/behavior";
import type { FsmState } from "@/features/skills/types/fsm";
import {
  EVENT_TITLES,
  actionIdFromCompletedEvent,
  defaultWaitTitle,
} from "@/features/skills/utils/behaviorGraph";
import {
  branchId,
  decideNodeId,
  doNodeId,
  edgeId,
  endNodeId,
  waitNodeId,
} from "@/features/skills/utils/behaviorGraph";

export function liftFsmToBehavior(states: FsmState[], initial: string | null): BehaviorGraph {
  if (states.length === 0) return emptyBehaviorGraph();

  const stateById = new Map(states.map((state) => [state.id, state]));
  const incomingActions = new Map<string, Set<string>>();
  for (const state of states) incomingActions.set(state.id, new Set());
  for (const state of states) {
    for (const transition of state.transitions) {
      const bucket = incomingActions.get(transition.to) ?? new Set<string>();
      for (const action of transition.actions) bucket.add(action);
      incomingActions.set(transition.to, bucket);
    }
  }

  function isCompletion(stateId: string): boolean {
    const state = stateById.get(stateId);
    if (!state || state.transitions.length === 0) return false;
    const completed = state.transitions.map((item) => actionIdFromCompletedEvent(item.event));
    if (completed.some((item) => item === null)) return false;
    const fired = incomingActions.get(stateId) ?? new Set();
    return completed.some((item) => item && fired.has(item));
  }

  const nodes: BehaviorNode[] = [];
  const edges: BehaviorEdge[] = [];
  const known = new Set<string>();
  const waitForState = new Map<string, string>();
  const processedOutgoing = new Set<string>();
  let edgeIndex = 0;

  function addNode(node: BehaviorNode) {
    if (known.has(node.id)) return;
    known.add(node.id);
    nodes.push(node);
  }

  function addEdge(from: string, to: string, kind: "next" | "loop" = "next"): string {
    edgeIndex += 1;
    const id = edgeId(from, to, edgeIndex);
    edges.push({ id, from, to, kind });
    return id;
  }

  function layoutFrom(state: FsmState, order: number) {
    return {
      story: { x: 48, y: 48 + order * 140, width: 280, height: 96 },
      logic: { x: state.x, y: state.y, width: state.width, height: state.height },
    };
  }

  function classifyEvent(event: string): WaitFor {
    const actionId = actionIdFromCompletedEvent(event);
    if (actionId) return { type: "action", actionId };
    if (event === "channel.message.received") return { type: "input", event };
    return { type: "event", event };
  }

  function ensureWait(stateId: string): string {
    const existing = waitForState.get(stateId);
    if (existing) return existing;
    const state = stateById.get(stateId)!;
    const order = nodes.length;
    if (state.final && state.transitions.length === 0) {
      const id = endNodeId(stateId);
      addNode({
        id,
        type: "end",
        title: state.name?.trim() || "Задача завершена",
        layout: layoutFrom(state, order),
      });
      waitForState.set(stateId, id);
      return id;
    }
    const event = state.transitions[0]?.event || "event";
    const waitFor = classifyEvent(event);
    const id = waitNodeId(stateId);
    let title = state.name?.trim() || defaultWaitTitle(waitFor);
    if (title === stateId && (waitFor.type === "event" || waitFor.type === "input")) {
      const eventName = waitFor.type === "event" ? waitFor.event : waitFor.event || event;
      title = EVENT_TITLES[eventName] ?? title;
    }
    addNode({
      id,
      type: "wait",
      title,
      waitFor,
      layout: layoutFrom(state, order),
    });
    waitForState.set(stateId, id);
    return id;
  }

  function emitActionChain(transition: FsmState["transitions"][number]): {
    first: string | null;
    last: string | null;
  } {
    const actions = transition.actions.filter(Boolean);
    if (actions.length === 0) return { first: null, last: null };
    const key = transition.id || `${transition.event}_${transition.to}`;
    const created: string[] = [];
    for (const action of actions) {
      const id = doNodeId(key, action);
      addNode({ id, type: "do", title: action, actionId: action });
      created.push(id);
    }
    for (let index = 0; index < created.length - 1; index += 1) {
      addEdge(created[index], created[index + 1], "next");
    }
    return { first: created[0], last: created[created.length - 1] };
  }

  function connectTarget(
    fromNodeId: string,
    transition: FsmState["transitions"][number],
    entryWait: string,
  ) {
    const targetStateId = transition.to;
    if (!targetStateId) return;
    if (isCompletion(targetStateId)) {
      processOutgoing(targetStateId, fromNodeId, entryWait);
      return;
    }
    const targetNode = ensureWait(targetStateId);
    const kind = targetNode === entryWait ? "loop" : "next";
    if (fromNodeId !== targetNode) addEdge(fromNodeId, targetNode, kind);
    processOutgoing(targetStateId, targetNode, entryWait);
  }

  function processOutgoing(stateId: string, fromNodeId: string, entryWait: string) {
    if (processedOutgoing.has(stateId)) return;
    processedOutgoing.add(stateId);
    const state = stateById.get(stateId);
    if (!state) return;
    const transitions = state.transitions;
    if (transitions.length === 0) return;
    const needsDecide =
      transitions.length > 1 || transitions.some((item) => item.guard.trim().length > 0);

    if (needsDecide) {
      const event = transitions[0]?.event || "event";
      const id = decideNodeId(stateId, event);
      const branches: DecideBranch[] = [];
      transitions.forEach((transition, index) => {
        const { first, last } = emitActionChain(transition);
        const transId = transition.id || `${stateId}_${index}`;
        const label = branchLabel(transition.guard, index, transitions.length);
        if (first) {
          branches.push({
            id: branchId(transId, index),
            label,
            guard: transition.guard.trim(),
            to: first,
          });
          connectTarget(last || first, transition, entryWait);
          return;
        }
        const targetStateId = transition.to;
        const targetNode = isCompletion(targetStateId)
          ? fromNodeId
          : targetStateId
            ? ensureWait(targetStateId)
            : fromNodeId;
        branches.push({
          id: branchId(transId, index),
          label,
          guard: transition.guard.trim(),
          to: targetNode,
        });
        if (targetStateId) {
          if (isCompletion(targetStateId)) {
            processOutgoing(targetStateId, fromNodeId, entryWait);
          } else {
            processOutgoing(targetStateId, targetNode, entryWait);
          }
        }
      });
      addNode({
        id,
        type: "decide",
        title: "",
        question: "Какая ветка?",
        branches,
      });
      addEdge(fromNodeId, id, "next");
      return;
    }

    const transition = transitions[0];
    const { first, last } = emitActionChain(transition);
    if (first) {
      addEdge(fromNodeId, first, "next");
      connectTarget(last || first, transition, entryWait);
      return;
    }
    connectTarget(fromNodeId, transition, entryWait);
  }

  let start = initial || "";
  if (!start || !stateById.has(start)) start = states[0].id;
  const entry = ensureWait(start);
  processOutgoing(start, entry, entry);
  return { version: BEHAVIOR_GRAPH_VERSION, entry, nodes, edges };
}

function branchLabel(guard: string, index: number, total: number): string {
  if (!guard.trim()) return "Иначе";
  if (total === 2) return index === 0 ? "Да" : "Нет";
  return `Ветка ${index + 1}`;
}
