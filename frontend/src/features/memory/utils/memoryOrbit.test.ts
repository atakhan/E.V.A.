import { describe, expect, it } from "vitest";
import {
  layoutMemoryOrbit,
  MEMORY_ATTENTION_CAPACITY,
  MEMORY_ORBIT_ITEMS,
  MEMORY_ORBIT_RADIUS,
  MEMORY_SAT_SIZE,
} from "./memoryOrbit";

describe("layoutMemoryOrbit", () => {
  it("places facets on a full circle three icons from the center", () => {
    const anchor = { x: 400, y: 300 };
    const slots = layoutMemoryOrbit(anchor, { width: 900, height: 700 });
    expect(slots).toHaveLength(MEMORY_ORBIT_ITEMS.length);
    expect(MEMORY_ORBIT_RADIUS).toBe(3 * MEMORY_SAT_SIZE);
    expect(MEMORY_ATTENTION_CAPACITY).toBeGreaterThan(0);

    for (const slot of slots) {
      const cx = slot.x + MEMORY_SAT_SIZE / 2;
      const cy = slot.y + MEMORY_SAT_SIZE / 2;
      const dist = Math.hypot(cx - anchor.x, cy - anchor.y);
      expect(dist).toBeCloseTo(MEMORY_ORBIT_RADIUS, 0);
    }
  });
});
