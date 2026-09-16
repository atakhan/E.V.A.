import type { Point } from "@/features/skills/types/fsm";
import type { RectLike } from "@/features/skills/utils/edgeRouting";

export interface Rect extends RectLike {
  id?: string;
}

export function quantize(value: number): number {
  return Math.round(value);
}

export function inflate(rect: RectLike, padding: number): Rect {
  return {
    id: "id" in rect ? (rect as Rect).id : undefined,
    x: rect.x - padding,
    y: rect.y - padding,
    width: rect.width + padding * 2,
    height: rect.height + padding * 2,
  };
}

export function rectRight(rect: RectLike): number {
  return rect.x + rect.width;
}

export function rectBottom(rect: RectLike): number {
  return rect.y + rect.height;
}

export function rectCenter(rect: RectLike): Point {
  return { x: rect.x + rect.width / 2, y: rect.y + rect.height / 2 };
}

export function pointInRectStrict(point: Point, rect: RectLike, epsilon = 0.51): boolean {
  return (
    point.x > rect.x + epsilon &&
    point.x < rectRight(rect) - epsilon &&
    point.y > rect.y + epsilon &&
    point.y < rectBottom(rect) - epsilon
  );
}

export function rectsOverlap(a: RectLike, b: RectLike, epsilon = 0.5): boolean {
  return (
    a.x < rectRight(b) - epsilon &&
    rectRight(a) > b.x + epsilon &&
    a.y < rectBottom(b) - epsilon &&
    rectBottom(a) > b.y + epsilon
  );
}

export function rectsOverlapWithGap(a: RectLike, b: RectLike, gap: number): boolean {
  return (
    a.x < rectRight(b) + gap &&
    rectRight(a) + gap > b.x &&
    a.y < rectBottom(b) + gap &&
    rectBottom(a) + gap > b.y
  );
}

export function unionBounds(rects: RectLike[], padding = 0): Rect {
  if (rects.length === 0) {
    return { x: -padding, y: -padding, width: padding * 2, height: padding * 2 };
  }
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  for (const rect of rects) {
    minX = Math.min(minX, rect.x);
    minY = Math.min(minY, rect.y);
    maxX = Math.max(maxX, rectRight(rect));
    maxY = Math.max(maxY, rectBottom(rect));
  }
  return {
    x: minX - padding,
    y: minY - padding,
    width: maxX - minX + padding * 2,
    height: maxY - minY + padding * 2,
  };
}

/** True if an open orthogonal segment enters the rectangle interior. Border-only contact is allowed. */
export function orthogonalSegmentHitsRectInterior(a: Point, b: Point, rect: RectLike): boolean {
  const left = rect.x;
  const right = rectRight(rect);
  const top = rect.y;
  const bottom = rectBottom(rect);
  const minX = Math.min(a.x, b.x);
  const maxX = Math.max(a.x, b.x);
  const minY = Math.min(a.y, b.y);
  const maxY = Math.max(a.y, b.y);

  if (a.y === b.y) {
    const y = a.y;
    if (y <= top || y >= bottom) return false;
    return maxX > left && minX < right;
  }

  if (a.x === b.x) {
    const x = a.x;
    if (x <= left || x >= right) return false;
    return maxY > top && minY < bottom;
  }

  return false;
}

export function polylineCrossesRect(points: Point[], rect: RectLike): boolean {
  for (let i = 1; i < points.length; i += 1) {
    if (orthogonalSegmentHitsRectInterior(points[i - 1], points[i], rect)) return true;
  }
  return false;
}

export function rangesOverlapOpen(a1: number, a2: number, b1: number, b2: number): boolean {
  const minA = Math.min(a1, a2);
  const maxA = Math.max(a1, a2);
  const minB = Math.min(b1, b2);
  const maxB = Math.max(b1, b2);
  return maxA > minB && minA < maxB;
}

export function orthogonalSegmentsCross(a: Point, b: Point, c: Point, d: Point): boolean {
  const abHorizontal = a.y === b.y;
  const cdHorizontal = c.y === d.y;

  if (abHorizontal && cdHorizontal) {
    if (a.y !== c.y) return false;
    return rangesOverlapOpen(a.x, b.x, c.x, d.x);
  }
  if (!abHorizontal && !cdHorizontal) {
    if (a.x !== c.x) return false;
    return rangesOverlapOpen(a.y, b.y, c.y, d.y);
  }

  const horizontal = abHorizontal ? [a, b] : [c, d];
  const vertical = abHorizontal ? [c, d] : [a, b];
  const hy = horizontal[0].y;
  const vx = vertical[0].x;
  const hMin = Math.min(horizontal[0].x, horizontal[1].x);
  const hMax = Math.max(horizontal[0].x, horizontal[1].x);
  const vMin = Math.min(vertical[0].y, vertical[1].y);
  const vMax = Math.max(vertical[0].y, vertical[1].y);
  return vx > hMin && vx < hMax && hy > vMin && hy < vMax;
}

export function countRouteCrossings(a: Point, b: Point, routes: Point[][]): number {
  let count = 0;
  for (const route of routes) {
    for (let i = 1; i < route.length; i += 1) {
      if (orthogonalSegmentsCross(a, b, route[i - 1], route[i])) count += 1;
    }
  }
  return count;
}

export function polylineSelfIntersects(points: Point[]): boolean {
  for (let i = 1; i < points.length; i += 1) {
    for (let j = i + 2; j < points.length; j += 1) {
      if (i === 1 && j === points.length - 1) continue;
      if (orthogonalSegmentsCross(points[i - 1], points[i], points[j - 1], points[j])) {
        return true;
      }
    }
  }
  return false;
}

export function uniqueSorted(values: number[], epsilon = 0.51): number[] {
  const sorted = [...values].map(quantize).sort((left, right) => left - right);
  const result: number[] = [];
  for (const value of sorted) {
    if (result.length === 0 || Math.abs(result[result.length - 1] - value) > epsilon) {
      result.push(value);
    }
  }
  return result;
}

export function simplifyOrthogonal(points: Point[]): Point[] {
  const deduped: Point[] = [];
  for (const point of points) {
    const prev = deduped[deduped.length - 1];
    if (prev && prev.x === point.x && prev.y === point.y) continue;
    deduped.push(point);
  }

  const simplified: Point[] = [];
  for (const point of deduped) {
    const last = simplified[simplified.length - 1];
    const prev = simplified[simplified.length - 2];
    if (
      last &&
      prev &&
      ((prev.x === last.x && last.x === point.x) || (prev.y === last.y && last.y === point.y))
    ) {
      simplified[simplified.length - 1] = point;
      continue;
    }
    simplified.push(point);
  }
  return simplified;
}

export function pushPointOutOfRects(point: Point, rects: RectLike[]): Point {
  let current = { x: quantize(point.x), y: quantize(point.y) };
  for (let step = 0; step < 8; step += 1) {
    const hit = rects.find((rect) => pointInRectStrict(current, rect));
    if (!hit) return current;
    const dl = current.x - hit.x;
    const dr = rectRight(hit) - current.x;
    const dt = current.y - hit.y;
    const db = rectBottom(hit) - current.y;
    const min = Math.min(dl, dr, dt, db);
    if (min === dl) current = { x: quantize(hit.x - 1), y: current.y };
    else if (min === dr) current = { x: quantize(rectRight(hit) + 1), y: current.y };
    else if (min === dt) current = { x: current.x, y: quantize(hit.y - 1) };
    else current = { x: current.x, y: quantize(rectBottom(hit) + 1) };
  }
  return current;
}
