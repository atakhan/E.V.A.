import { describe, expect, it } from "vitest";
import {
  layoutPluginColumn,
  layoutPluginHubPose,
  PLUGIN_HUB_GUTTER,
  PLUGIN_SAT_SIZE,
  pluginOrbitItemsFor,
} from "./pluginOrbit";
import type { ToolDefinition } from "@/features/tools/types/tool";

function def(partial: Partial<ToolDefinition>): ToolDefinition {
  return {
    id: "demo",
    name: "Demo",
    description: "",
    world: false,
    implemented: true,
    commands: [],
    events: [],
    states: [],
    ...partial,
  };
}

describe("plugin column layout", () => {
  it("drops credential facet when type has no credentialKind", () => {
    const ids = pluginOrbitItemsFor(def({})).map((item) => item.id);
    expect(ids).not.toContain("credential");
    expect(ids).toContain("commands");
  });

  it("keeps credential facet when credentialKind is set", () => {
    const ids = pluginOrbitItemsFor(def({ credentialKind: "telegram_bot" })).map((item) => item.id);
    expect(ids).toContain("credential");
  });

  it("seats the hub in the left half against the midline gutter", () => {
    const bounds = { width: 1000, height: 800 };
    const pose = layoutPluginHubPose(bounds, { width: 176, height: 56 });
    const visualW = 176 * pose.scale;
    const centerX = pose.x + 176 / 2;
    const cardRight = centerX + visualW / 2;
    expect(cardRight).toBeCloseTo(bounds.width / 2 - PLUGIN_HUB_GUTTER, 0);
    expect(centerX).toBeLessThan(bounds.width / 2);
  });

  it("lays out a vertical column just right of the midline gutter", () => {
    const bounds = { width: 1000, height: 800 };
    const slots = layoutPluginColumn({ x: 0, y: 0 }, bounds, def({}));
    expect(slots.length).toBeGreaterThan(1);
    expect(slots[0]!.x).toBeCloseTo(bounds.width / 2 + PLUGIN_HUB_GUTTER, 5);
    for (let i = 1; i < slots.length; i++) {
      expect(slots[i]!.y).toBeGreaterThan(slots[i - 1]!.y);
      expect(slots[i]!.x).toBe(slots[0]!.x);
    }
  });
});
