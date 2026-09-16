import type { Point } from "@/features/skills/types/fsm";
import type { RectLike } from "@/features/skills/utils/edgeRouting";
import { MIN_LABEL_SEGMENT } from "@/features/skills/utils/geometry/config";
import { rectsOverlap, rectsOverlapWithGap } from "@/features/skills/utils/geometry/rects";

export interface LabelSize {
  width: number;
  height: number;
}

function segmentLength(a: Point, b: Point): number {
  return Math.hypot(b.x - a.x, b.y - a.y);
}

function pointAlong(a: Point, b: Point, t: number): Point {
  return { x: a.x + (b.x - a.x) * t, y: a.y + (b.y - a.y) * t };
}

function labelRect(center: Point, size: LabelSize): RectLike {
  return {
    x: center.x - size.width / 2,
    y: center.y - size.height / 2,
    width: size.width,
    height: size.height,
  };
}

function collides(center: Point, size: LabelSize, obstacles: RectLike[], labels: RectLike[]): boolean {
  const rect = labelRect(center, size);
  return (
    obstacles.some((obstacle) => rectsOverlap(rect, obstacle)) ||
    labels.some((item) => rectsOverlapWithGap(rect, item, 4))
  );
}

export function placeLabelOnRoute(
  points: Point[],
  size: LabelSize,
  obstacles: RectLike[],
  existingLabels: RectLike[] = [],
): { at: Point; compact: boolean } {
  if (points.length < 2) {
    return { at: points[0] ?? { x: 0, y: 0 }, compact: true };
  }

  const needed = Math.max(MIN_LABEL_SEGMENT, size.width * 0.55, size.height);
  const candidates: Array<{ at: Point; length: number; interior: boolean }> = [];

  for (let i = 1; i < points.length; i += 1) {
    const a = points[i - 1];
    const b = points[i];
    const length = segmentLength(a, b);
    const isStub = i === 1 || i === points.length - 1;
    if (length < 8) continue;
    const ratios = length >= needed ? [0.5, 0.35, 0.65] : [0.5];
    for (const ratio of ratios) {
      candidates.push({
        at: pointAlong(a, b, ratio),
        length,
        interior: !isStub && length >= needed,
      });
    }
  }

  candidates.sort((left, right) => {
    if (left.interior !== right.interior) return left.interior ? -1 : 1;
    return right.length - left.length;
  });

  for (const candidate of candidates) {
    if (!collides(candidate.at, size, obstacles, existingLabels)) {
      return { at: candidate.at, compact: !candidate.interior };
    }
  }

  if (candidates.length > 0) {
    return { at: candidates[0].at, compact: true };
  }

  return { at: points[Math.floor(points.length / 2)], compact: true };
}

export function labelCollisionRect(center: Point, size: LabelSize): RectLike {
  return labelRect(center, size);
}
