import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import type { Agent } from "@/features/agents/types/agent";
import { previewSkillPack } from "@/features/skills/utils/skillPackImport";
import { parseSkillYamlDocument, skillFromYaml, skillToYaml } from "@/features/skills/utils/skillYaml";
import { createEmptySkill } from "@/features/skills/types/skill";

const fixtureDir = dirname(fileURLToPath(import.meta.url));
const fixtureYaml = readFileSync(
  join(fixtureDir, "../fixtures/parse_foreman_request.fsm.yaml"),
  "utf8",
);

const emptyAgent: Agent = {
  id: "a1",
  name: "Test",
  slug: "test",
  description: "",
  skills: [],
  actions: [{ id: "parse_request", name: "Parse", description: "", version: "0.1.0", policy: "auto", inputSchema: {}, outputSchema: {}, recipe: [], createdAt: "", updatedAt: "" }],
  tools: [],
  createdAt: "",
  updatedAt: "",
};

describe("parseSkillYamlDocument v0.3 subset", () => {
  it("parses shorthand transitions and skill id", () => {
    const doc = parseSkillYamlDocument(fixtureYaml);
    expect("error" in doc).toBe(false);
    if ("error" in doc) return;
    expect(doc.skillId).toBe("skill.parse_foreman_request");
    expect(doc.states?.map((state) => state.id)).toEqual(["ingest", "parse", "clarify", "done"]);
    expect(doc.warnings?.some((w) => w.includes("guards"))).toBe(true);
    const clarify = doc.states?.find((state) => state.id === "clarify");
    expect(clarify?.transitions[0]?.actions).toEqual(["parse_request"]);
  });
});

describe("previewSkillPack", () => {
  it("reports missing actions and conflicts", () => {
    const preview = previewSkillPack(
      [{ fileName: "parse_foreman_request.fsm.yaml", content: fixtureYaml }],
      emptyAgent,
    );
    expect(preview.entries).toHaveLength(1);
    const entry = preview.entries[0]!;
    expect(entry.skillId).toBe("parse_foreman_request");
    expect(entry.missingActionIds).toContain("ingest_channel_message");
    expect(entry.missingActionIds).not.toContain("parse_request");
  });

  it("detects conflict with existing skill id", () => {
    const agent: Agent = {
      ...emptyAgent,
      skills: [
        {
          id: "parse_foreman_request",
          name: "Existing",
          description: "",
          version: "0.1.0",
          createdAt: "",
          updatedAt: "",
          initial: null,
          params: [],
          states: [],
          viewport: { panX: 0, panY: 0, zoom: 1 },
        },
      ],
    };
    const preview = previewSkillPack(
      [{ fileName: "parse_foreman_request.fsm.yaml", content: fixtureYaml }],
      agent,
    );
    expect(preview.entries[0]?.conflict?.existingName).toBe("Existing");
  });
});

describe("behavior YAML/JSON", () => {
  it("round-trips behavior as canonical export", () => {
    const skill = createEmptySkill({ name: "Разговор", id: "razgovor" });
    skill.behavior = {
      version: 1,
      entry: "w1",
      nodes: [
        {
          id: "w1",
          type: "wait",
          title: "Когда приходит новое сообщение",
          waitFor: { type: "input", event: "channel.message.received" },
        },
      ],
      edges: [],
    };
    const yaml = skillToYaml(skill);
    expect(yaml).toContain('"behavior"');
    expect(yaml.toLowerCase()).toContain("generated");
    const imported = skillFromYaml(yaml, skill);
    expect("error" in imported).toBe(false);
    if ("error" in imported) return;
    expect(imported.behavior?.entry).toBe("w1");
    expect(imported.behavior?.nodes[0]?.type).toBe("wait");
  });
});
