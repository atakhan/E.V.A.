import { describe, expect, it } from "vitest";
import { focusIconShift } from "@/features/projects/utils/deskMotion";

describe("focusIconShift", () => {
  it("moves the icon center to the desk center and scales it to the hub", () => {
    const shift = focusIconShift({ x: 200, y: 120 }, { width: 1000, height: 800 }, 64, 88);
    expect(shift.dx).toBe(300);
    expect(shift.dy).toBe(280);
    expect(shift.scale).toBeCloseTo(88 / 64);
  });
});
