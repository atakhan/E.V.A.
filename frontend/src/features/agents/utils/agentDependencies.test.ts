import { beforeEach, describe, expect, it } from "vitest";
import type { ActionDef, Agent } from "@/features/agents/types/agent";
import {
  skillActionIds,
  skillDependencies,
  toolUsage,
} from "@/features/agents/utils/agentDependencies";
import { evaluatePluginLink } from "@/features/agents/utils/evaluatePluginLink";
import { validateAgent } from "@/features/agents/utils/validateAgent";
import type { FsmState, FsmTransition } from "@/features/skills/types/fsm";
import { createEmptySkill, type Skill } from "@/features/skills/types/skill";
import { setToolCatalogForTests } from "@/features/tools/services/toolCatalogStore";
import type { ToolDefinition, ToolInstance } from "@/features/tools/types/tool";

const catalog: ToolDefinition[] = [
  {
    id: "web_client",
    name: "Web Client",
    description: "",
    world: true,
    commands: [
      { id: "get_snapshot", description: "" },
      { id: "send_message", description: "" },
    ],
    events: [{ id: "channel.message.received", description: "" }],
    states: [],
    credentialKind: "web_client",
  },
  {
    id: "telegram",
    name: "Telegram",
    description: "",
    world: true,
    commands: [{ id: "send_message", description: "" }],
    events: [{ id: "channel.message.received", description: "" }],
    states: [],
    credentialKind: "telegram_bot",
  },
  {
    id: "polza_ai_llm",
    name: "PolzaAI_LLM",
    description: "",
    commands: [{ id: "run_structured", description: "" }],
    events: [],
    states: [],
    credentialKind: "api_key",
  },
  {
    id: "text",
    name: "Text",
    description: "",
    commands: [{ id: "trim", description: "" }],
    events: [],
    states: [],
  },
  {
    id: "memory",
    name: "Memory",
    description: "",
    implemented: false,
    commands: [{ id: "search", description: "" }],
    events: [],
    states: [],
  },
];

function transition(event: string, actions: string[], to: string): FsmTransition {
  return { id: `${event}->${to}`, event, guard: "", actions, to };
}

function state(id: string, transitions: FsmTransition[], onEnter: string[] = []): FsmState {
  return { id, onEnter, final: false, transitions, x: 0, y: 0, width: 160, height: 80 };
}

function skill(id: string, states: FsmState[]): Skill {
  return { ...createEmptySkill({ id, name: id }), initial: states[0]?.id ?? null, states };
}

function action(id: string, recipe: Array<[tool: string, command: string]>): ActionDef {
  return {
    id,
    name: id,
    description: "",
    version: "0.1.0",
    policy: "auto",
    inputSchema: {},
    outputSchema: {},
    recipe: recipe.map(([tool, command], index) => ({ id: `s${index}`, tool, command, input: {} })),
    createdAt: "",
    updatedAt: "",
  };
}

function instance(id: string, toolId: string, partial?: Partial<ToolInstance>): ToolInstance {
  return { id, toolId, name: id, enabled: true, config: {}, ...partial };
}

const composeLetter = skill("compose_letter", [
  state("queued", [transition("ui.request.parse_requested", ["compose_draft"], "waiting")]),
  state("waiting", [
    transition("human.request.reviewed", ["record_letter", "missing_action"], "done"),
    transition("human.request.reviewed", ["compose_draft"], "waiting"),
  ]),
]);

function letterAgent(partial?: Partial<Agent>): Agent {
  return {
    id: "a1",
    slug: "sous-letter",
    name: "Letter",
    description: "",
    icon: "",
    createdAt: "",
    updatedAt: "",
    skills: [composeLetter],
    actions: [
      action("compose_draft", [
        ["web_client", "get_snapshot"],
        ["polza_ai_llm", "run_structured"],
        ["web_client", "send_message"],
      ]),
      action("record_letter", [["web_client", "send_message"]]),
    ],
    tools: [
      instance("web_client", "web_client"),
      instance("polza_ai_llm", "polza_ai_llm", { credentialId: "cred-1" }),
    ],
    world: { addresses: [] },
    ...partial,
  };
}

describe("agent dependencies", () => {
  beforeEach(() => {
    setToolCatalogForTests(catalog);
  });

  it("lists skill actions once, in order of first reference", () => {
    expect(skillActionIds(composeLetter)).toEqual(["compose_draft", "record_letter", "missing_action"]);
  });

  it("splits what a skill needs into channels and plugins through its actions", () => {
    const deps = skillDependencies(letterAgent(), composeLetter);

    expect(deps.channels.map((item) => [item.name, item.actionIds])).toEqual([
      ["Web Client", ["compose_draft", "record_letter"]],
    ]);
    expect(deps.plugins.map((item) => [item.name, item.status, item.actionIds])).toEqual([
      ["polza_ai_llm", "ok", ["compose_draft"]],
    ]);
    expect(deps.actions.find((item) => item.actionId === "missing_action")?.action).toBeNull();
  });

  it("counts a channel the skill listens to even without actions", () => {
    const inbox = skill("inbox", [state("idle", [transition("channel.message.received", [], "idle")])]);
    const agent = letterAgent({ skills: [inbox], tools: [instance("tg", "telegram")] });

    const deps = skillDependencies(agent, inbox);

    expect(deps.channels.map((item) => [item.instanceId, item.events])).toEqual([
      ["tg", ["channel.message.received"]],
    ]);
  });

  it("marks plugins without runtime implementation", () => {
    const recall = skill("recall", [state("idle", [], ["remember"])]);
    const agent = letterAgent({
      skills: [recall],
      actions: [action("remember", [["memory", "search"]])],
      tools: [instance("memory", "memory")],
    });

    expect(skillDependencies(agent, recall).plugins[0]?.status).toBe("unimplemented");
  });

  it("finds who uses a plugin instance and a channel type", () => {
    const agent = letterAgent();

    const polza = toolUsage(agent, { kind: "instance", instanceId: "polza_ai_llm" });
    expect(polza.actions.map((item) => [item.action.id, item.commands])).toEqual([
      ["compose_draft", ["run_structured"]],
    ]);
    expect(polza.skills.map((item) => [item.skill.id, item.actionIds])).toEqual([
      ["compose_letter", ["compose_draft"]],
    ]);

    const web = toolUsage(agent, { kind: "type", typeId: "web_client" });
    expect(web.actions.map((item) => [item.action.id, item.commands])).toEqual([
      ["compose_draft", ["get_snapshot", "send_message"]],
      ["record_letter", ["send_message"]],
    ]);
  });
});

describe("evaluatePluginLink", () => {
  beforeEach(() => {
    setToolCatalogForTests(catalog);
  });

  it("is green when configured and called by an action", () => {
    const agent = letterAgent();
    expect(evaluatePluginLink(agent, agent.tools[1]!).status).toBe("green");
  });

  it("is red without a required credential", () => {
    const polza = instance("polza_ai_llm", "polza_ai_llm");
    const agent = letterAgent({ tools: [instance("web_client", "web_client"), polza] });
    expect(evaluatePluginLink(agent, polza).status).toBe("red");
  });

  it("stays green when no action calls it yet", () => {
    const text = instance("text", "text");
    expect(evaluatePluginLink(letterAgent(), text).status).toBe("green");
  });

  it("is red for a type without runtime implementation", () => {
    const memory = instance("memory", "memory");
    expect(evaluatePluginLink(letterAgent({ tools: [memory] }), memory).status).toBe("red");
  });
});

describe("validateAgent: unimplemented tools", () => {
  beforeEach(() => {
    setToolCatalogForTests(catalog);
  });

  it("rejects an enabled instance of a type without implementation", () => {
    const report = validateAgent(letterAgent({ tools: [instance("memory", "memory")] }));
    const issue = report.issues.find((item) => item.code === "unimplemented_tool");
    expect(issue?.severity).toBe("error");
  });

  it("allows a disabled one", () => {
    const report = validateAgent(letterAgent({ tools: [instance("memory", "memory", { enabled: false })] }));
    expect(report.issues.some((item) => item.code === "unimplemented_tool")).toBe(false);
  });
});
