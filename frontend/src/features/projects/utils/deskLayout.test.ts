import { describe, expect, it } from "vitest";
import { layoutAroundRuntime } from "@/features/projects/utils/deskLayout";
import type { ProjectAgent } from "@/features/projects/types/project";

const anchor = { x: 500, y: 680 };
const bounds = { width: 1000, height: 800 };

function agents(count: number): ProjectAgent[] {
  return Array.from({ length: count }, (_, index) => ({
    agentSlug: `agent-${index}`,
    x: 0,
    y: 0,
  }));
}

function centers(placed: ProjectAgent[]): Array<{ x: number; y: number }> {
  return placed.map((agent) => ({ x: agent.x, y: agent.y + 32 }));
}

function expectSymmetric(placed: ProjectAgent[]) {
  const points = centers(placed);
  for (const point of points) {
    const mirrorX = 2 * anchor.x - point.x;
    const mirror = points.find(
      (other) => Math.abs(other.x - mirrorX) < 0.6 && Math.abs(other.y - point.y) < 0.6,
    );
    expect(mirror).toBeTruthy();
  }
}

describe("layoutAroundRuntime", () => {
  it("puts a single agent straight above the runtime", () => {
    const [only] = centers(layoutAroundRuntime(agents(1), anchor, bounds));
    expect(only.x).toBe(anchor.x);
    expect(only.y).toBe(anchor.y - 376);
  });

  it("keeps every count symmetric and closer to the runtime than to the top corners", () => {
    for (const count of [2, 3, 4, 5, 6]) {
      const placed = layoutAroundRuntime(agents(count), anchor, bounds);
      expectSymmetric(placed);
      for (const point of centers(placed)) {
        expect(point.y).toBeLessThan(anchor.y);
        const fromRuntime = Math.hypot(point.x - anchor.x, point.y - anchor.y);
        const fromCorner = Math.hypot(point.x, point.y);
        expect(fromRuntime).toBeLessThan(fromCorner);
      }
    }
  });
});
