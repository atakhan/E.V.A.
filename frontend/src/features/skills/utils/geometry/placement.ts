import type { RectLike } from "@/features/skills/utils/edgeRouting";
import { ALIGNMENT_THRESHOLD, MIN_NODE_GAP } from "@/features/skills/utils/geometry/config";
import { rectBottom, rectCenter, rectRight, rectsOverlapWithGap } from "@/features/skills/utils/geometry/rects";
import { snap } from "@/features/skills/utils/canvasGeometry";
import { GRID_SIZE } from "@/features/skills/types/fsm";

export interface GuideLine {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
}

export function snapRectToAlignment(
  moving: RectLike,
  others: RectLike[],
  threshold = ALIGNMENT_THRESHOLD,
): { x: number; y: number; guides: GuideLine[] } {
  let nextX = moving.x;
  let nextY = moving.y;
  let bestX = threshold + 1;
  let bestY = threshold + 1;
  const guides: GuideLine[] = [];

  const movingRight = rectRight(moving);
  const movingBottom = rectBottom(moving);
  const movingCenter = rectCenter(moving);

  let xGuide: GuideLine | null = null;
  let yGuide: GuideLine | null = null;

  for (const other of others) {
    const otherRight = rectRight(other);
    const otherBottom = rectBottom(other);
    const otherCenter = rectCenter(other);
    const top = Math.min(moving.y, other.y);
    const bottom = Math.max(movingBottom, otherBottom);
    const left = Math.min(moving.x, other.x);
    const right = Math.max(movingRight, otherRight);

    const xOptions: Array<{ dist: number; x: number; lineX: number }> = [
      { dist: Math.abs(moving.x - other.x), x: other.x, lineX: other.x },
      { dist: Math.abs(moving.x - otherRight), x: otherRight, lineX: otherRight },
      { dist: Math.abs(movingRight - other.x), x: other.x - moving.width, lineX: other.x },
      { dist: Math.abs(movingRight - otherRight), x: otherRight - moving.width, lineX: otherRight },
      { dist: Math.abs(movingCenter.x - otherCenter.x), x: otherCenter.x - moving.width / 2, lineX: otherCenter.x },
    ];
    for (const option of xOptions) {
      if (option.dist < bestX) {
        bestX = option.dist;
        nextX = option.x;
        xGuide = { x1: option.lineX, y1: top - 12, x2: option.lineX, y2: bottom + 12 };
      }
    }

    const yOptions: Array<{ dist: number; y: number; lineY: number }> = [
      { dist: Math.abs(moving.y - other.y), y: other.y, lineY: other.y },
      { dist: Math.abs(moving.y - otherBottom), y: otherBottom, lineY: otherBottom },
      { dist: Math.abs(movingBottom - other.y), y: other.y - moving.height, lineY: other.y },
      { dist: Math.abs(movingBottom - otherBottom), y: otherBottom - moving.height, lineY: otherBottom },
      { dist: Math.abs(movingCenter.y - otherCenter.y), y: otherCenter.y - moving.height / 2, lineY: otherCenter.y },
    ];
    for (const option of yOptions) {
      if (option.dist < bestY) {
        bestY = option.dist;
        nextY = option.y;
        yGuide = { x1: left - 12, y1: option.lineY, x2: right + 12, y2: option.lineY };
      }
    }
  }

  if (bestX <= threshold && xGuide) guides.push(xGuide);
  else nextX = moving.x;
  if (bestY <= threshold && yGuide) guides.push(yGuide);
  else nextY = moving.y;

  return { x: nextX, y: nextY, guides };
}

export function resolveRectOverlap(
  moving: RectLike,
  others: RectLike[],
  minGap = MIN_NODE_GAP,
): { x: number; y: number; conflict: boolean } {
  if (!others.some((other) => rectsOverlapWithGap(moving, other, minGap))) {
    return { x: moving.x, y: moving.y, conflict: false };
  }

  const maxRadius = 48;
  for (let radius = 1; radius <= maxRadius; radius += 1) {
    for (let dy = -radius; dy <= radius; dy += 1) {
      for (let dx = -radius; dx <= radius; dx += 1) {
        if (Math.abs(dx) !== radius && Math.abs(dy) !== radius) continue;
        const candidate = {
          ...moving,
          x: snap(moving.x + dx * GRID_SIZE),
          y: snap(moving.y + dy * GRID_SIZE),
        };
        if (!others.some((other) => rectsOverlapWithGap(candidate, other, minGap))) {
          return { x: candidate.x, y: candidate.y, conflict: false };
        }
      }
    }
  }

  return { x: moving.x, y: moving.y, conflict: true };
}
