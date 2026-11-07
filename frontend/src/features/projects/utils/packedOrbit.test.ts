import { describe, expect, it } from "vitest";
import { layoutAroundRuntime, RUNTIME_MIN_CHORD, RUNTIME_TOP_MENU } from "@/features/projects/utils/deskLayout";
import type { ProjectAgent } from "@/features/projects/types/project";
import {
  CREATE_PROJECT_SIZE,
  layoutAroundEva,
  layoutCreateAroundEva,
  PROJECT_LABEL_CLEAR,
  PROJECT_TOP_MENU,
} from "@/features/projects/utils/projectsHubLayout";

function expectSymmetric(
  points: Array<{ x: number; y: number }>,
  anchorX: number,
) {
  for (const point of points) {
    const mirrorX = 2 * anchorX - point.x;
    const mirror = points.find(
      (other) => Math.abs(other.x - mirrorX) < 0.6 && Math.abs(other.y - point.y) < 0.6,
    );
    expect(mirror).toBeTruthy();
  }
}

function nearestNeighbor(points: Array<{ x: number; y: number }>, index: number): number {
  let best = Number.POSITIVE_INFINITY;
  for (let other = 0; other < points.length; other += 1) {
    if (other === index) continue;
    const dist = Math.hypot(points[other].x - points[index].x, points[other].y - points[index].y);
    if (dist < best) best = dist;
  }
  return best;
}

describe("layoutAroundEva (hub orbit)", () => {
  const anchor = { x: 640, y: 820 };
  const bounds = { width: 1280, height: 960 };

  function ids(count: number): string[] {
    return Array.from({ length: count }, (_, index) => `project-${index}`);
  }

  function centers(placed: ReturnType<typeof layoutAroundEva>) {
    return placed.map((slot) => ({ x: slot.x, y: slot.y + 32 }));
  }

  it("puts a single project above Eva, within half the desk and nearer Eva than the menu", () => {
    const [only] = centers(layoutAroundEva(ids(1), anchor, bounds));
    expect(only.x).toBe(anchor.x);
    const toEva = anchor.y - only.y;
    const toMenu = only.y - PROJECT_TOP_MENU;
    expect(toEva).toBeGreaterThan(PROJECT_LABEL_CLEAR * 0.9);
    expect(toEva).toBeLessThanOrEqual(bounds.height / 2);
    expect(toEva).toBeLessThan(toMenu);
  });

  it("seats create dead-center above Eva, closer than the project ring", () => {
    const create = layoutCreateAroundEva(anchor, bounds);
    const createCenter = {
      x: create.x,
      y: create.y + CREATE_PROJECT_SIZE / 2,
    };
    const [project] = centers(layoutAroundEva(ids(1), anchor, bounds));
    const createR = Math.hypot(createCenter.x - anchor.x, createCenter.y - anchor.y);
    const projectR = Math.hypot(project.x - anchor.x, project.y - anchor.y);
    expect(createCenter.x).toBe(anchor.x);
    expect(createCenter.y).toBeLessThan(anchor.y);
    expect(createR).toBeLessThan(projectR * 0.7);
  });

  it("keeps label clearance and stays nearer Eva than the top menu", () => {
    for (const count of [2, 3, 5, 8]) {
      const placed = layoutAroundEva(ids(count), anchor, bounds);
      const points = centers(placed);
      expectSymmetric(points, anchor.x);
      for (let index = 0; index < points.length; index += 1) {
        const point = points[index];
        expect(point.y).toBeLessThan(anchor.y);
        const toEva = Math.hypot(point.x - anchor.x, point.y - anchor.y);
        const toMenu = point.y - PROJECT_TOP_MENU;
        expect(toEva).toBeLessThanOrEqual(bounds.height / 2 + 1);
        expect(toEva).toBeLessThan(toMenu);
        const radius = toEva;
        for (let other = 0; other < points.length; other += 1) {
          if (other === index) continue;
          const otherRadius = Math.hypot(points[other].x - anchor.x, points[other].y - anchor.y);
          if (Math.abs(otherRadius - radius) > 8) continue;
          const dist = Math.hypot(points[other].x - point.x, points[other].y - point.y);
          expect(dist).toBeGreaterThanOrEqual(PROJECT_LABEL_CLEAR - 1);
        }
      }
      if (count >= 2) {
        expect(nearestNeighbor(points, 0)).toBeLessThan(
          Math.hypot(points[0].x - anchor.x, points[0].y - anchor.y),
        );
      }
    }
  });
});

describe("layoutAroundRuntime (desk orbit)", () => {
  const anchor = { x: 500, y: 680 };
  const bounds = { width: 1000, height: 800 };

  function agents(count: number): ProjectAgent[] {
    return Array.from({ length: count }, (_, index) => ({
      agentSlug: `agent-${index}`,
      x: 0,
      y: 0,
    }));
  }

  function centers(placed: ProjectAgent[]) {
    return placed.map((agent) => ({ x: agent.x, y: agent.y + 32 }));
  }

  it("puts a single agent above the runtime, within half the desk and nearer runtime than the menu", () => {
    const [only] = centers(layoutAroundRuntime(agents(1), anchor, bounds));
    expect(only.x).toBe(anchor.x);
    const toRuntime = anchor.y - only.y;
    const toMenu = only.y - RUNTIME_TOP_MENU;
    expect(toRuntime).toBeGreaterThan(RUNTIME_MIN_CHORD * 0.9);
    expect(toRuntime).toBeLessThanOrEqual(bounds.height / 2);
    expect(toRuntime).toBeLessThan(toMenu);
  });

  it("packs neighbors tightly and stays nearer the runtime than the top menu", () => {
    for (const count of [2, 3, 4, 5, 6]) {
      const placed = layoutAroundRuntime(agents(count), anchor, bounds);
      const points = centers(placed);
      expectSymmetric(points, anchor.x);
      for (let index = 0; index < points.length; index += 1) {
        const point = points[index];
        expect(point.y).toBeLessThan(anchor.y);
        const toRuntime = Math.hypot(point.x - anchor.x, point.y - anchor.y);
        const toMenu = point.y - RUNTIME_TOP_MENU;
        expect(toRuntime).toBeLessThanOrEqual(bounds.height / 2 + 1);
        expect(toRuntime).toBeLessThan(toMenu);
        const radius = toRuntime;
        for (let other = 0; other < points.length; other += 1) {
          if (other === index) continue;
          const otherRadius = Math.hypot(points[other].x - anchor.x, points[other].y - anchor.y);
          if (Math.abs(otherRadius - radius) > 8) continue;
          const dist = Math.hypot(points[other].x - point.x, points[other].y - point.y);
          expect(dist).toBeGreaterThanOrEqual(RUNTIME_MIN_CHORD - 1);
        }
      }
      if (count >= 2) {
        expect(nearestNeighbor(points, 0)).toBeLessThan(
          Math.hypot(points[0].x - anchor.x, points[0].y - anchor.y),
        );
      }
    }
  });
});
