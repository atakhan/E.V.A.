import { describe, expect, it } from "vitest";
import type { FsmState } from "@/features/skills/types/fsm";
import { BEHAVIOR_COMPILER_VERSION } from "@/features/skills/types/behavior";
import { compileBehavior } from "@/features/skills/utils/behaviorCompile";
import { fsmBehaviorallyEquivalent } from "@/features/skills/utils/behaviorEquivalence";
import { insertBehaviorStep } from "@/features/skills/utils/behaviorGraph";
import { liftFsmToBehavior } from "@/features/skills/utils/behaviorLift";
import { behaviorNarrative } from "@/features/skills/utils/behaviorNarrative";

function razgovorStates(): { states: FsmState[]; initial: string } {
  return {
    initial: "IDLE",
    states: [
      {
        id: "IDLE",
        onEnter: [],
        final: false,
        transitions: [
          {
            id: "t1",
            event: "channel.message.received",
            guard: "",
            actions: ["draft_reply"],
            to: "THINKING",
          },
        ],
        x: 0,
        y: 0,
        width: 160,
        height: 80,
      },
      {
        id: "THINKING",
        onEnter: [],
        final: false,
        transitions: [
          {
            id: "t2",
            event: "action.draft_reply.completed",
            guard: "",
            actions: ["send_reply"],
            to: "REPLIED",
          },
        ],
        x: 220,
        y: 0,
        width: 160,
        height: 80,
      },
      {
        id: "REPLIED",
        onEnter: [],
        final: false,
        transitions: [
          {
            id: "t3",
            event: "action.send_reply.completed",
            guard: "",
            actions: [],
            to: "IDLE",
          },
        ],
        x: 440,
        y: 0,
        width: 160,
        height: 80,
      },
    ],
  };
}

describe("behavior compile/lift", () => {
  it("is deterministic", () => {
    const { states, initial } = razgovorStates();
    const graph = liftFsmToBehavior(states, initial);
    const first = compileBehavior(graph);
    const second = compileBehavior(graph);
    expect(first.ok && second.ok).toBe(true);
    if (!first.ok || !second.ok) return;
    expect(first.artifact.compilerVersion).toBe(BEHAVIOR_COMPILER_VERSION);
    expect(first.artifact.states).toEqual(second.artifact.states);
  });

  it("lifts razgovor to wait + two dos without end", () => {
    const { states, initial } = razgovorStates();
    const graph = liftFsmToBehavior(states, initial);
    const types = graph.nodes.map((node) => node.type);
    expect(types.filter((item) => item === "wait")).toHaveLength(1);
    expect(types.filter((item) => item === "do")).toHaveLength(2);
    expect(types.includes("end")).toBe(false);
    const wait = graph.nodes.find((node) => node.type === "wait");
    expect(wait && wait.type === "wait" && wait.waitFor.type).toBe("input");
  });

  it("lift then compile is behaviorally equivalent to razgovor", () => {
    const { states, initial } = razgovorStates();
    const graph = liftFsmToBehavior(states, initial);
    const result = compileBehavior(graph);
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(
      fsmBehaviorallyEquivalent(states, initial, result.artifact.states, result.artifact.initial),
    ).toBe(true);
  });

  it("stamps origin ids", () => {
    const { states, initial } = razgovorStates();
    const result = compileBehavior(liftFsmToBehavior(states, initial));
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    for (const state of result.artifact.states) {
      expect(state.originNodeId).toBeTruthy();
      for (const transition of state.transitions) {
        expect(transition.originNodeId).toBeTruthy();
        expect(transition.originEdgeId).toBeTruthy();
      }
    }
  });

  it("compiles decide branches with guards", () => {
    const result = compileBehavior(
      {
        version: 1,
        entry: "w1",
        nodes: [
          {
            id: "w1",
            type: "wait",
            title: "Когда приходит сообщение",
            waitFor: { type: "event", event: "channel.message.received" },
          },
          {
            id: "d1",
            type: "decide",
            title: "",
            question: "Нашли несколько?",
            branches: [
              { id: "b_yes", label: "Да", guard: "results.length > 1", to: "do_many" },
              { id: "b_no", label: "Нет", guard: "results.length == 1", to: "do_one" },
            ],
          },
          { id: "do_many", type: "do", title: "Показать", actionId: "show_variants" },
          { id: "do_one", type: "do", title: "Предложить", actionId: "propose" },
          { id: "end1", type: "end", title: "Задача завершена" },
        ],
        edges: [
          { id: "e1", from: "w1", to: "d1", kind: "next" },
          { id: "e2", from: "do_many", to: "end1", kind: "next" },
          { id: "e3", from: "do_one", to: "end1", kind: "next" },
        ],
      },
      { actionIds: new Set(["show_variants", "propose"]) },
    );
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    const wait = result.artifact.states.find((state) => state.originNodeId === "w1");
    const guards = new Set(wait?.transitions.map((item) => item.guard));
    expect(guards.has("results.length > 1")).toBe(true);
    expect(guards.has("results.length == 1")).toBe(true);
  });

  it("builds a narrative", () => {
    const { states, initial } = razgovorStates();
    const text = behaviorNarrative(liftFsmToBehavior(states, initial));
    expect(text).toContain("Когда");
    expect(text).toContain("Возвращаюсь");
  });

  it("inserts a do step as node + edge", () => {
    let ids = 0;
    const makeId = () => `id_${(ids += 1)}`;
    const graph = {
      version: 1,
      entry: "w1",
      nodes: [
        {
          id: "w1",
          type: "wait" as const,
          title: "Когда",
          waitFor: { type: "input" as const, event: "channel.message.received" },
        },
      ],
      edges: [],
    };
    const next = insertBehaviorStep(
      graph,
      { id: "do1", type: "do", title: "Готовлю ответ", actionId: "draft_reply" },
      "w1",
      makeId,
    );
    expect(next.nodes.map((node) => node.id)).toEqual(["w1", "do1"]);
    expect(next.edges).toEqual([{ id: "edge_id_1", from: "w1", to: "do1", kind: "next" }]);
  });
});
