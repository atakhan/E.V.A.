import { describe, expect, it } from "vitest";
import {
  addPluginSlotForCount,
  addSkillSlotForCount,
  AGENT_SIZE,
  boxesOverlap,
  DEFAULT_SKILL_NODE_HEIGHT,
  DEFAULT_SKILL_NODE_WIDTH,
  layoutWorldKindColumn,
  MEMORY_CENTER_Y,
  MEMORY_NODE_HEIGHT,
  MEMORY_NODE_WIDTH,
  MEMORY_X,
  memoryNodeCenter,
  PLUGIN_NODE_HEIGHT,
  PLUGIN_NODE_WIDTH,
  pluginNodeCenter,
  skillNodePosition,
  SKILL_ORBIT_RADIUS,
  WORLD_ADDRESS_HEIGHT,
  WORLD_ADDRESS_WIDTH,
  WORLD_KIND_HEIGHT,
  WORLD_KIND_WIDTH,
  WORLD_KIND_X,
} from "@/features/constructor/types/constructor";

describe("constructor skill column", () => {
  it("places skills on the right of the agent", () => {
    for (const count of [1, 3, 9]) {
      for (let i = 0; i < count; i += 1) {
        const pos = skillNodePosition(i, count);
        expect(pos.x + DEFAULT_SKILL_NODE_WIDTH / 2).toBeCloseTo(SKILL_ORBIT_RADIUS, 5);
      }
    }
  });

  it("keeps add slot on the right below the last skill", () => {
    const slot = addSkillSlotForCount(3);
    expect(slot.x).toBe(SKILL_ORBIT_RADIUS);
    const last = skillNodePosition(2, 3);
    expect(slot.y).toBeGreaterThan(last.y + DEFAULT_SKILL_NODE_HEIGHT / 2);
  });

  it("does not overlap skill boxes in the column", () => {
    for (const count of [1, 2, 5, 9, 12]) {
      const boxes = Array.from({ length: count }, (_, index) => {
        const pos = skillNodePosition(index, count);
        return {
          x: pos.x,
          y: pos.y,
          width: DEFAULT_SKILL_NODE_WIDTH,
          height: DEFAULT_SKILL_NODE_HEIGHT,
        };
      });
      for (let i = 0; i < boxes.length; i += 1) {
        for (let j = i + 1; j < boxes.length; j += 1) {
          expect(boxesOverlap(boxes[i]!, boxes[j]!)).toBe(false);
        }
      }
    }
  });
});

describe("plugin column", () => {
  function pluginBox(index: number) {
    const center = pluginNodeCenter(index);
    return {
      x: center.x - PLUGIN_NODE_WIDTH / 2,
      y: center.y - PLUGIN_NODE_HEIGHT / 2,
      width: PLUGIN_NODE_WIDTH,
      height: PLUGIN_NODE_HEIGHT,
    };
  }

  it("starts below the agent and keeps plugins apart", () => {
    expect(pluginBox(0).y).toBeGreaterThan(AGENT_SIZE / 2);
    for (let i = 0; i < 8; i += 1) {
      expect(boxesOverlap(pluginBox(i), pluginBox(i + 1))).toBe(false);
    }
    expect(addPluginSlotForCount(3)).toEqual(pluginNodeCenter(3));
  });

  it("stays clear of the skill column and the world column", () => {
    const plugins = Array.from({ length: 10 }, (_, index) => pluginBox(index));
    const skills = Array.from({ length: 12 }, (_, index) => ({
      ...skillNodePosition(index, 12),
      width: DEFAULT_SKILL_NODE_WIDTH,
      height: DEFAULT_SKILL_NODE_HEIGHT,
    }));
    const kinds = [...layoutWorldKindColumn([
      { toolId: "telegram", addressCount: 6 },
      { toolId: "web_client", addressCount: 6 },
    ]).values()].map((slot) => ({
      x: WORLD_KIND_X - WORLD_KIND_WIDTH / 2,
      y: slot.kindY - WORLD_KIND_HEIGHT / 2,
      width: WORLD_KIND_WIDTH,
      height: WORLD_KIND_HEIGHT,
    }));
    for (const plugin of plugins) {
      for (const other of [...skills, ...kinds]) {
        expect(boxesOverlap(plugin, other)).toBe(false);
      }
    }
  });
});

describe("memory card", () => {
  it("sits above the agent and clear of plugins, skills and channels", () => {
    const center = memoryNodeCenter();
    const memory = {
      x: center.x - MEMORY_NODE_WIDTH / 2,
      y: center.y - MEMORY_NODE_HEIGHT / 2,
      width: MEMORY_NODE_WIDTH,
      height: MEMORY_NODE_HEIGHT,
    };
    expect(center).toEqual({ x: MEMORY_X, y: MEMORY_CENTER_Y });
    expect(memory.y + memory.height).toBeLessThan(-AGENT_SIZE / 2);
    const firstPlugin = pluginNodeCenter(0);
    expect(
      boxesOverlap(memory, {
        x: firstPlugin.x - PLUGIN_NODE_WIDTH / 2,
        y: firstPlugin.y - PLUGIN_NODE_HEIGHT / 2,
        width: PLUGIN_NODE_WIDTH,
        height: PLUGIN_NODE_HEIGHT,
      }),
    ).toBe(false);

    const skills = Array.from({ length: 12 }, (_, index) => ({
      ...skillNodePosition(index, 12),
      width: DEFAULT_SKILL_NODE_WIDTH,
      height: DEFAULT_SKILL_NODE_HEIGHT,
    }));
    const kinds = [...layoutWorldKindColumn([
      { toolId: "telegram", addressCount: 6 },
      { toolId: "web_client", addressCount: 6 },
    ]).values()].map((slot) => ({
      x: WORLD_KIND_X - WORLD_KIND_WIDTH / 2,
      y: slot.kindY - WORLD_KIND_HEIGHT / 2,
      width: WORLD_KIND_WIDTH,
      height: WORLD_KIND_HEIGHT,
    }));
    for (const other of [...skills, ...kinds]) {
      expect(boxesOverlap(memory, other)).toBe(false);
    }
  });
});

describe("layoutWorldKindColumn", () => {
  it("spreads kinds so address stacks do not overlap", () => {
    const layout = layoutWorldKindColumn([
      { toolId: "telegram", addressCount: 5 },
      { toolId: "web_client", addressCount: 4 },
    ]);
    const a = layout.get("telegram")!;
    const b = layout.get("web_client")!;
    const boxesA = a.addressYs.map((y) => ({
      x: 0,
      y: y - WORLD_ADDRESS_HEIGHT / 2,
      width: WORLD_ADDRESS_WIDTH,
      height: WORLD_ADDRESS_HEIGHT,
    }));
    const boxesB = b.addressYs.map((y) => ({
      x: 0,
      y: y - WORLD_ADDRESS_HEIGHT / 2,
      width: WORLD_ADDRESS_WIDTH,
      height: WORLD_ADDRESS_HEIGHT,
    }));
    for (const left of boxesA) {
      for (const right of boxesB) {
        expect(boxesOverlap(left, right)).toBe(false);
      }
    }
  });
});
