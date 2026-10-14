import type { Point } from "@/features/skills/types/fsm";
import type { RectLike } from "@/features/skills/utils/edgeRouting";
import { MIN_LABEL_SEGMENT } from "@/features/skills/utils/geometry/config";
import { orthogonalSegmentHitsRectInterior, rectsOverlap, rectsOverlapWithGap } from "@/features/skills/utils/geometry/rects";

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

function segmentsHit(points: Point[], rect: RectLike, skipIndex: number | null): boolean {
  for (let index = 1; index < points.length; index += 1) {
    if (index === skipIndex) continue;
    if (orthogonalSegmentHitsRectInterior(points[index - 1], points[index], rect)) return true;
  }
  return false;
}

function segmentNormal(a: Point, b: Point): Point {
  const length = segmentLength(a, b) || 1;
  return { x: -(b.y - a.y) / length, y: (b.x - a.x) / length };
}

interface LabelCandidate {
  at: Point;
  length: number;
  interior: boolean;
  distance: number;
  hostIndex: number;
}

export function placeLabelOnRoute(
  points: Point[],
  size: LabelSize,
  obstacles: RectLike[],
  existingLabels: RectLike[] = [],
  otherRoutes: Point[][] = [],
): { at: Point; compact: boolean; offset: boolean } {
  if (points.length < 2) {
    return { at: points[0] ?? { x: 0, y: 0 }, compact: true, offset: false };
  }

  const needed = Math.max(MIN_LABEL_SEGMENT, size.width * 0.55, size.height);
  const candidates: LabelCandidate[] = [];

  for (let i = 1; i < points.length; i += 1) {
    const a = points[i - 1];
    const b = points[i];
    const length = segmentLength(a, b);
    const isStub = i === 1 || i === points.length - 1;
    if (length < 8) continue;
    const ratios = length >= needed ? [0.5, 0.35, 0.65] : [0.5];
    const normal = segmentNormal(a, b);
    const step = Math.max(size.height + 8, 28);
    const distances = [0, size.height / 2 + 8, step, step * 2, step * 3, size.width / 2 + 12];
    for (const ratio of ratios) {
      const origin = pointAlong(a, b, ratio);
      for (const distance of distances) {
        const signs = distance === 0 ? [1] : [1, -1];
        for (const sign of signs) {
          candidates.push({
            at: {
              x: origin.x + normal.x * distance * sign,
              y: origin.y + normal.y * distance * sign,
            },
            length,
            interior: !isStub && length >= needed && distance === 0,
            distance,
            hostIndex: i,
          });
        }
      }
    }
  }

  candidates.sort((left, right) => {
    const leftOnRoute = left.distance === 0;
    const rightOnRoute = right.distance === 0;
    if (leftOnRoute !== rightOnRoute) return leftOnRoute ? -1 : 1;
    if (left.interior !== right.interior) return left.interior ? -1 : 1;
    if (left.distance !== right.distance) return left.distance - right.distance;
    return right.length - left.length;
  });

  const fits = (candidate: LabelCandidate) => {
    if (collides(candidate.at, size, obstacles, existingLabels)) return false;
    const rect = labelRect(candidate.at, size);
    if (segmentsHit(points, rect, candidate.hostIndex)) return false;
    return !otherRoutes.some((route) => segmentsHit(route, rect, null));
  };

  for (const candidate of candidates) {
    if (fits(candidate)) {
      return {
        at: candidate.at,
        compact: candidate.distance > 0 || !candidate.interior,
        offset: candidate.distance > 0,
      };
    }
  }

  if (candidates.length > 0) {
    const fallback = candidates[0];
    return { at: fallback.at, compact: true, offset: fallback.distance > 0 };
  }

  return { at: points[Math.floor(points.length / 2)], compact: true, offset: false };
}

export function labelCollisionRect(center: Point, size: LabelSize): RectLike {
  return labelRect(center, size);
}
