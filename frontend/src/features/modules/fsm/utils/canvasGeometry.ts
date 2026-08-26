import {
  GRID_SIZE,
  MIN_RECT_SIZE,
  type DraftRect,
  type Point,
} from "@/features/modules/fsm/types/canvas";

export function snap(value: number, grid = GRID_SIZE): number {
  return Math.round(value / grid) * grid;
}

export function snapPoint(point: Point, grid = GRID_SIZE): Point {
  return { x: snap(point.x, grid), y: snap(point.y, grid) };
}

export function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

export function screenToWorld(
  clientX: number,
  clientY: number,
  viewportRect: DOMRect,
  panX: number,
  panY: number,
  zoom: number,
): Point {
  return {
    x: (clientX - viewportRect.left - panX) / zoom,
    y: (clientY - viewportRect.top - panY) / zoom,
  };
}

export function normalizeRect(start: Point, end: Point): DraftRect {
  const x = Math.min(start.x, end.x);
  const y = Math.min(start.y, end.y);
  const width = Math.abs(end.x - start.x);
  const height = Math.abs(end.y - start.y);

  return { x, y, width, height };
}

export function snapRect(rect: DraftRect, grid = GRID_SIZE): DraftRect {
  const x = snap(rect.x, grid);
  const y = snap(rect.y, grid);
  const right = snap(rect.x + rect.width, grid);
  const bottom = snap(rect.y + rect.height, grid);

  return {
    x,
    y,
    width: Math.max(MIN_RECT_SIZE, right - x),
    height: Math.max(MIN_RECT_SIZE, bottom - y),
  };
}

export function isValidRect(rect: DraftRect): boolean {
  return rect.width >= MIN_RECT_SIZE && rect.height >= MIN_RECT_SIZE;
}
