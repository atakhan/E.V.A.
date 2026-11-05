import type { ProjectAgent } from "@/features/projects/types/project";

/** Agent icon on the desk. The runtime sphere is 1.5× this. */
export const AGENT_ICON = 64;

/** How far icon centers stay apart, so the circles do not touch. */
const MIN_CHORD = AGENT_ICON + 48;

/**
 * Arc above the runtime, narrower than a semicircle,
 * so the icons sit toward the center instead of the corners.
 */
const SPREAD = Math.PI * 0.62;

/** First ring around the runtime. Center-to-center distance from the runtime sphere. */
const PREFERRED_RADIUS = 376;

const RING_GAP = (AGENT_ICON + 52) * 2;

export interface DeskAnchor {
  x: number;
  y: number;
}

export interface DeskBounds {
  width: number;
  height: number;
}

/** Icon-center slots. `x` is the horizontal center, `y` is the icon center. */
export function layoutAroundRuntime(
  agents: ProjectAgent[],
  anchor: DeskAnchor,
  bounds: DeskBounds,
): ProjectAgent[] {
  if (agents.length === 0 || bounds.width <= 0 || bounds.height <= 0) return agents;

  const radii = ringRadii(agents.length, anchor, bounds);
  const counts = balance(ringCounts(agents.length, radii));
  const slots = slotsFor(counts, radii, anchor);

  return agents.map((agent, index) => {
    const slot = slots[index] ?? slots[slots.length - 1];
    return {
      ...agent,
      x: round(slot.x),
      y: round(slot.y - AGENT_ICON / 2),
    };
  });
}

function ringCounts(count: number, radii: number[]): number[] {
  const counts: number[] = [];
  let remaining = count;
  for (const radius of radii) {
    if (remaining <= 0) break;
    const take = Math.min(remaining, ringCapacity(radius));
    counts.push(take);
    remaining -= take;
  }
  while (remaining > 0) {
    counts[counts.length - 1] += 1;
    remaining -= 1;
  }
  return counts;
}

function balance(counts: number[]): number[] {
  const next = [...counts];
  for (let index = next.length - 1; index > 0; index -= 1) {
    while (next[index - 1] - next[index] > 1) {
      next[index - 1] -= 1;
      next[index] += 1;
    }
  }
  return next;
}

function ringRadii(count: number, anchor: DeskAnchor, bounds: DeskBounds): number[] {
  const fit = maxRadius(anchor, bounds);
  const radii: number[] = [];
  let radius = Math.min(PREFERRED_RADIUS, fit);
  let room = count;
  while (room > 0) {
    radii.push(Math.max(96, radius));
    room -= ringCapacity(radius);
    radius = Math.min(radius + RING_GAP, fit);
    if (radii.length > 6) break;
  }
  return radii.length ? radii : [Math.max(96, Math.min(PREFERRED_RADIUS, fit))];
}

function maxRadius(anchor: DeskAnchor, bounds: DeskBounds): number {
  const topLimit = 88;
  const sideLimit = 72;
  const byTop = anchor.y - topLimit;
  const sideRoom = Math.min(anchor.x, bounds.width - anchor.x) - sideLimit;
  const bySide = sideRoom / Math.sin(SPREAD / 2);
  return Math.max(96, Math.min(byTop, bySide));
}

function ringCapacity(radius: number): number {
  const ratio = Math.min(1, MIN_CHORD / (2 * Math.max(radius, 1)));
  const step = 2 * Math.asin(ratio);
  if (step <= 0) return 1;
  return Math.max(1, Math.floor(SPREAD / step) + 1);
}

function slotsFor(
  counts: number[],
  radii: number[],
  anchor: DeskAnchor,
): Array<{ x: number; y: number }> {
  const slots: Array<{ x: number; y: number }> = [];
  counts.forEach((count, ring) => {
    const radius = radii[ring] ?? radii[radii.length - 1];
    const previous = ring > 0 ? counts[ring - 1] : count;
    const angles =
      count === previous ? arcAngles(count) : gapAngles(previous, count);
    for (const theta of angles) {
      slots.push({
        x: anchor.x + Math.cos(theta) * radius,
        y: anchor.y + Math.sin(theta) * radius,
      });
    }
  });
  return slots;
}

/** Evenly along the arc, centered on straight up. One icon sits on the axis. */
function arcAngles(count: number): number[] {
  if (count <= 1) return [-Math.PI / 2];
  const start = -Math.PI / 2 - SPREAD / 2;
  const step = SPREAD / (count - 1);
  return Array.from({ length: count }, (_, index) => start + step * index);
}

/** Midpoints between the previous ring, so the extra ring stays symmetric. */
function gapAngles(innerCount: number, count: number): number[] {
  const inner = arcAngles(innerCount);
  const gaps: number[] = [];
  for (let index = 0; index < inner.length - 1 && gaps.length < count; index += 1) {
    gaps.push((inner[index] + inner[index + 1]) / 2);
  }
  return gaps.length === count ? gaps : arcAngles(count);
}

function round(value: number): number {
  return Math.round(value * 10) / 10;
}
