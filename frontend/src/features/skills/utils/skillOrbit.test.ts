import { describe, expect, it } from "vitest";
import {
  layoutSkillColumn,
  layoutSkillHubPose,
  SKILL_HUB_GUTTER,
  SKILL_ORBIT_ITEMS,
} from "./skillOrbit";

describe("skill column layout", () => {
  it("exposes the three skill facets", () => {
    expect(SKILL_ORBIT_ITEMS.map((item) => item.id)).toEqual(["about", "states", "needs"]);
  });

  it("seats the hub in the left half against the midline gutter", () => {
    const bounds = { width: 1000, height: 800 };
    const pose = layoutSkillHubPose(bounds, { width: 220, height: 72 });
    const visualW = 220 * pose.scale;
    const centerX = pose.x + 220 / 2;
    const cardRight = centerX + visualW / 2;
    expect(cardRight).toBeCloseTo(bounds.width / 2 - SKILL_HUB_GUTTER, 0);
    expect(centerX).toBeLessThan(bounds.width / 2);
  });

  it("lays out a vertical column just right of the midline gutter", () => {
    const bounds = { width: 1000, height: 800 };
    const slots = layoutSkillColumn({ x: 0, y: 0 }, bounds);
    expect(slots).toHaveLength(SKILL_ORBIT_ITEMS.length);
    expect(slots[0]!.x).toBeCloseTo(bounds.width / 2 + SKILL_HUB_GUTTER, 5);
    for (let i = 1; i < slots.length; i++) {
      expect(slots[i]!.y).toBeGreaterThan(slots[i - 1]!.y);
      expect(slots[i]!.x).toBe(slots[0]!.x);
    }
  });
});
