import { describe, expect, it } from "vitest";
import { createEmptySkill } from "@/features/skills/types/skill";
import { validateSkill } from "@/features/skills/utils/validateSkill";

describe("validateSkill locators", () => {
  it("marks unknown action on transition", () => {
    const skill = createEmptySkill({ name: "Test" });
    skill.initial = "start";
    skill.states = [
      {
        id: "start",
        onEnter: [],
        final: false,
        transitions: [
          {
            id: "t1",
            event: "go",
            guard: "",
            actions: ["missing_action"],
            to: "end",
          },
        ],
        x: 0,
        y: 0,
        width: 160,
        height: 80,
      },
      {
        id: "end",
        onEnter: [],
        final: true,
        transitions: [],
        x: 200,
        y: 0,
        width: 160,
        height: 80,
      },
    ];

    const issues = validateSkill(skill, new Set());
    const unknown = issues.find((issue) => issue.code === "unknown_action");
    expect(unknown).toBeDefined();
    expect(unknown?.actionId).toBe("missing_action");
    expect(unknown?.locator).toEqual({
      kind: "transition",
      stateId: "start",
      transitionId: "t1",
    });
  });

  it("marks invalid transition target", () => {
    const skill = createEmptySkill({ name: "Test" });
    skill.initial = "start";
    skill.states = [
      {
        id: "start",
        onEnter: [],
        final: false,
        transitions: [
          {
            id: "t2",
            event: "go",
            guard: "",
            actions: [],
            to: "ghost",
          },
        ],
        x: 0,
        y: 0,
        width: 160,
        height: 80,
      },
    ];

    const issues = validateSkill(skill, new Set());
    const badTarget = issues.find((issue) => issue.code === "invalid_transition_target");
    expect(badTarget?.locator).toEqual({
      kind: "transition",
      stateId: "start",
      transitionId: "t2",
    });
  });

  it("marks invalid guard syntax", () => {
    const skill = createEmptySkill({ name: "Test" });
    skill.initial = "start";
    skill.states = [
      {
        id: "start",
        onEnter: [],
        final: false,
        transitions: [
          {
            id: "t3",
            event: "evt",
            guard: "not valid guard",
            actions: [],
            to: "start",
          },
        ],
        x: 0,
        y: 0,
        width: 160,
        height: 80,
      },
    ];

    const issues = validateSkill(skill, new Set());
    expect(issues.some((issue) => issue.code === "invalid_guard_syntax")).toBe(true);
  });
});
