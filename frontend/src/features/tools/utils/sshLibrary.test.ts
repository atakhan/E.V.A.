import { describe, expect, it } from "vitest";
import type { ActionDef } from "@/features/actions/types/action";
import { mergeSchemaConfig } from "@/features/tools/utils/instanceConfig";
import {
  connectionConfigPatch,
  isSshLibraryAction,
  readSshLibrary,
  recipeFromCommandIds,
  writeSshLibrary,
} from "@/features/tools/utils/sshLibrary";

const action = (recipe: ActionDef["recipe"]): ActionDef => ({
  id: "restart",
  name: "Restart",
  description: "",
  version: "0.1.0",
  policy: "auto",
  inputSchema: {},
  outputSchema: {},
  recipe,
  createdAt: "",
  updatedAt: "",
});

describe("ssh library", () => {
  it("round-trips commands and keeps the rest of the config", () => {
    const stored = writeSshLibrary(
      { host: "app.example", commands: [] },
      [{ id: "disk", name: "Диск", description: "", shell: "df -h" }],
    );
    expect(stored.host).toBe("app.example");
    expect(readSshLibrary(stored).map((item) => item.id)).toEqual(["disk"]);
  });

  it("skips commands with an invalid id", () => {
    expect(readSshLibrary({ commands: [{ id: "Bad", shell: "true" }, { id: "ok", shell: "true" }] })).toEqual([
      { id: "ok", name: "ok", description: "", shell: "true" },
    ]);
  });

  it("builds a recipe the skill can call", () => {
    const recipe = recipeFromCommandIds("ssh_main", ["disk", "restart_nginx"]);
    expect(recipe.map((step) => [step.id, step.command, step.input.command_id])).toEqual([
      ["run_1", "run", "disk"],
      ["run_2", "run", "restart_nginx"],
    ]);
    expect(isSshLibraryAction(action(recipe), "ssh_main")).toBe(true);
    expect(isSshLibraryAction(action([{ ...recipe[0], tool: "text", command: "trim" }]), "ssh_main")).toBe(false);
  });

  it("rejects a port that is not an integer", () => {
    const result = connectionConfigPatch({
      host: "app.example",
      port: "22.5",
      username: "deploy",
      timeoutSec: "30",
      outputLimit: "8000",
      hostKeyPolicy: "accept-new",
    });
    expect(result.ok).toBe(false);
  });
});

describe("mergeSchemaConfig", () => {
  it("keeps the command library when the schema form replaces connection fields", () => {
    const next = mergeSchemaConfig(
      { host: "old", commands: [{ id: "disk" }] },
      { host: "new" },
      [{ id: "host" }],
    );
    expect(next).toEqual({ host: "new", commands: [{ id: "disk" }] });
  });
});
