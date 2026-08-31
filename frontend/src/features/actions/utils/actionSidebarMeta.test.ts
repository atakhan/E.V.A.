import { describe, expect, it } from "vitest";
import type { Agent } from "@/features/agents/types/agent";
import type { ActionDef } from "@/features/actions/types/action";
import { getActionRecipeStatus, getRecipeStepStatus } from "@/features/actions/utils/actionSidebarMeta";
import { resolveRecipeTool } from "@/features/tools/utils/resolveToolInstance";

const agentBase: Pick<Agent, "tools"> = {
  tools: [
    {
      id: "llm",
      toolId: "llm",
      name: "LLM",
      enabled: true,
      config: {},
    },
  ],
};

const baseAction: ActionDef = {
  id: "parse_request",
  name: "Parse",
  description: "",
  version: "0.1.0",
  policy: "auto",
  inputSchema: {},
  outputSchema: {},
  recipe: [],
  createdAt: "",
  updatedAt: "",
};

describe("actionSidebarMeta", () => {
  it("returns empty for no recipe steps", () => {
    expect(getActionRecipeStatus(agentBase, baseAction)).toBe("empty");
  });

  it("detects disabled instance", () => {
    const agent: Pick<Agent, "tools"> = {
      tools: [{ id: "p1", toolId: "polza_ai_llm", name: "Polza", enabled: false, config: {} }],
    };
    const action: ActionDef = {
      ...baseAction,
      recipe: [{ id: "s1", tool: "p1", command: "run", input: {} }],
    };
    expect(getActionRecipeStatus(agent, action)).toBe("tool_off");
    expect(getRecipeStepStatus(agent, action.recipe[0]!)).toBe("disabled");
  });

  it("returns ok when instance enabled and command valid", () => {
    const action: ActionDef = {
      ...baseAction,
      recipe: [{ id: "s1", tool: "llm", command: "run", input: {} }],
    };
    expect(getActionRecipeStatus(agentBase, action)).toBe("ok");
  });
});

describe("resolveRecipeTool", () => {
  it("resolves instance id directly", () => {
    const agent: Pick<Agent, "tools"> = {
      tools: [{ id: "bot1", toolId: "telegram", name: "Bot", enabled: true, config: {} }],
    };
    expect(resolveRecipeTool(agent, "bot1").status).toBe("ok");
  });

  it("falls back to single type instance", () => {
    expect(resolveRecipeTool(agentBase, "llm").instanceId).toBe("llm");
  });

  it("flags ambiguous type reference", () => {
    const agent: Pick<Agent, "tools"> = {
      tools: [
        { id: "t1", toolId: "telegram", name: "A", enabled: true, config: {} },
        { id: "t2", toolId: "telegram", name: "B", enabled: true, config: {} },
      ],
    };
    expect(resolveRecipeTool(agent, "telegram").status).toBe("ambiguous");
  });
});
