import { describe, expect, it } from "vitest";
import {
  addSkillSlotForCount,
  boxesOverlap,
  DEFAULT_SKILL_NODE_HEIGHT,
  DEFAULT_SKILL_NODE_WIDTH,
  layoutWorldKindColumn,
  skillNodePosition,
  SKILL_ORBIT_RADIUS,
  WORLD_ADDRESS_HEIGHT,
  WORLD_ADDRESS_WIDTH,
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
