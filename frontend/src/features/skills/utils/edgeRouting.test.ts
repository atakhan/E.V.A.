import { describe, expect, it } from "vitest";
import {
  defaultAnchorsForPair,
  EDGE_LABEL_MAX_GAP,
  labelLineGapRadius,
  splitPolylineForLabel,
} from "@/features/skills/utils/edgeRouting";

function hypot(a: { x: number; y: number }, b: { x: number; y: number }): number {
  return Math.hypot(b.x - a.x, b.y - a.y);
}

describe("label line gap", () => {
  it("caps the cut so a wide event badge cannot open a huge hole", () => {
    expect(labelLineGapRadius({ width: 220, height: 44 })).toBe(EDGE_LABEL_MAX_GAP);
    expect(labelLineGapRadius({ width: 80, height: 12 })).toBeLessThanOrEqual(EDGE_LABEL_MAX_GAP);
  });

  it("keeps both stubs of a short vertical edge instead of dropping the segment", () => {
    const points = [
      { x: 100, y: 0 },
      { x: 100, y: 80 },
    ];
    const labelAt = { x: 100, y: 40 };
    const split = splitPolylineForLabel(
      points,
      labelAt,
      labelLineGapRadius({ width: 180, height: 36 }),
    );

    expect(split.before.length).toBeGreaterThanOrEqual(2);
    expect(split.after.length).toBeGreaterThanOrEqual(2);

    const gap = hypot(split.before[split.before.length - 1], split.after[0]);
    expect(gap).toBeGreaterThan(0);
    expect(gap).toBeLessThanOrEqual(EDGE_LABEL_MAX_GAP * 2 + 0.01);

    expect(hypot(points[0], split.before[split.before.length - 1])).toBeGreaterThanOrEqual(8);
    expect(hypot(split.after[0], points[1])).toBeGreaterThanOrEqual(8);
  });

  it("does not erase a stub that is already too short to split", () => {
    const points = [
      { x: 0, y: 10 },
      { x: 16, y: 10 },
    ];
    const split = splitPolylineForLabel(points, { x: 8, y: 10 }, 10);
    expect(split.before).toEqual(points);
    expect(split.after).toEqual([]);
  });
});

describe("default port facing", () => {
  it("leaves from the side that faces the other node", () => {
    const above = { x: 40, y: 40, width: 120, height: 64 };
    const below = { x: 40, y: 280, width: 120, height: 64 };
    expect(defaultAnchorsForPair(above, below, 0, false)).toMatchObject({
      from: { side: "bottom" },
      to: { side: "top" },
    });
    expect(defaultAnchorsForPair(below, above, 0, false)).toMatchObject({
      from: { side: "top" },
      to: { side: "bottom" },
    });

    const left = { x: 40, y: 40, width: 120, height: 64 };
    const right = { x: 400, y: 40, width: 120, height: 64 };
    expect(defaultAnchorsForPair(left, right, 0, false)).toMatchObject({
      from: { side: "right" },
      to: { side: "left" },
    });
    expect(defaultAnchorsForPair(right, left, 0, false)).toMatchObject({
      from: { side: "left" },
      to: { side: "right" },
    });
  });
});
