/**
 * Shared packed upper-orbit layout used by the Eva projects hub and the
 * project runtime desk. Callers pass constants; the packing algorithm is one.
 */

export interface OrbitAnchor {
  x: number;
  y: number;
}

export interface OrbitBounds {
  width: number;
  height: number;
}

export interface OrbitSlot {
  x: number;
  y: number;
}

export interface PackedOrbitParams {
  /** Minimum center-to-center chord between neighbors. */
  minChord: number;
  /** Max angular span of the upper arc (radians). */
  maxSpread: number;
  /** Pixels reserved for the floating top nav. */
  topMenu: number;
  /** Preferred vertical gap between rings. */
  ringGap: number;
  /** Side inset before the arc hits the desk edge. */
  sideLimit?: number;
  /** How far up from the center the preferred radius sits (0–1 of max fit). */
  preferredFit?: number;
}

const DEFAULT_SIDE_LIMIT = 56;
const DEFAULT_PREFERRED_FIT = 0.88;

/** Icon-center slots on a dense upper orbit around `anchor`. */
export function layoutPackedOrbit(
  count: number,
  anchor: OrbitAnchor,
  bounds: OrbitBounds,
  params: PackedOrbitParams,
): OrbitSlot[] {
  if (count <= 0 || bounds.width <= 0 || bounds.height <= 0) {
    return Array.from({ length: count }, () => ({ x: anchor.x, y: anchor.y }));
  }

  const ctx = bindParams(params);
  const radii = ringRadii(count, anchor, bounds, ctx);
  const counts = balance(ringCounts(count, radii, ctx));
  return slotsFor(counts, radii, anchor, ctx);
}

interface Ctx {
  minChord: number;
  maxSpread: number;
  topMenu: number;
  ringGap: number;
  sideLimit: number;
  preferredFit: number;
}

function bindParams(params: PackedOrbitParams): Ctx {
  return {
    minChord: params.minChord,
    maxSpread: params.maxSpread,
    topMenu: params.topMenu,
    ringGap: params.ringGap,
    sideLimit: params.sideLimit ?? DEFAULT_SIDE_LIMIT,
    preferredFit: params.preferredFit ?? DEFAULT_PREFERRED_FIT,
  };
}

function ringCounts(count: number, radii: number[], ctx: Ctx): number[] {
  const counts: number[] = [];
  let remaining = count;
  for (const radius of radii) {
    if (remaining <= 0) break;
    const take = Math.min(remaining, ringCapacity(radius, ctx));
    counts.push(take);
    remaining -= take;
  }
  if (remaining > 0 && counts.length > 0) {
    counts[counts.length - 1] += remaining;
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

/** Cap: ≤ half screen, and closer to the center than to the top menu. */
function maxRadius(anchor: OrbitAnchor, bounds: OrbitBounds, ctx: Ctx): number {
  const halfScreen = bounds.height / 2;
  const closerToCenterThanMenu = (anchor.y - ctx.topMenu) * 0.45;
  const byTop = anchor.y - ctx.topMenu;
  const sideRoom = Math.min(anchor.x, bounds.width - anchor.x) - ctx.sideLimit;
  const bySide = sideRoom / Math.sin(ctx.maxSpread / 2);
  const cap = Math.min(halfScreen, closerToCenterThanMenu, byTop, bySide);
  return Math.max(ctx.minChord * 1.05, cap);
}

function preferredRadius(anchor: OrbitAnchor, bounds: OrbitBounds, ctx: Ctx): number {
  const fit = maxRadius(anchor, bounds, ctx);
  return Math.max(ctx.minChord * 1.05, fit * ctx.preferredFit);
}

function ringsNeeded(count: number, preferred: number, fit: number, ctx: Ctx): number {
  let radius = Math.min(preferred, fit);
  let remaining = count;
  let rings = 0;
  while (remaining > 0 && rings < 6) {
    remaining -= ringCapacity(radius, ctx);
    rings += 1;
    radius = Math.min(radius + ctx.ringGap, fit);
  }
  return Math.max(1, rings);
}

function ringRadii(
  count: number,
  anchor: OrbitAnchor,
  bounds: OrbitBounds,
  ctx: Ctx,
): number[] {
  const fit = maxRadius(anchor, bounds, ctx);
  const preferred = preferredRadius(anchor, bounds, ctx);
  const needed = ringsNeeded(count, preferred, fit, ctx);
  const gap = Math.min(
    ctx.ringGap,
    Math.max(72, (fit - ctx.minChord * 1.05) / Math.max(1, needed - 1)),
  );
  const inner = Math.max(
    ctx.minChord * 1.05,
    Math.min(preferred, fit - (needed - 1) * gap),
  );
  const radii: number[] = [];
  let radius = inner;
  let remaining = count;
  while (remaining > 0 && radii.length < 6) {
    const used = Math.min(radius, fit);
    radii.push(used);
    remaining -= ringCapacity(used, ctx);
    radius = Math.min(fit, radius + gap);
    if (radii.length >= 2 && radii[radii.length - 1] === radii[radii.length - 2]) {
      radii[radii.length - 1] = Math.min(fit, used + Math.max(gap * 0.5, 48));
    }
  }
  return radii.length ? radii : [inner];
}

function chordStep(radius: number, ctx: Ctx): number {
  const ratio = Math.min(1, ctx.minChord / (2 * Math.max(radius, 1)));
  return 2 * Math.asin(ratio);
}

function ringCapacity(radius: number, ctx: Ctx): number {
  const step = chordStep(radius, ctx);
  if (step <= 0) return 1;
  return Math.max(1, Math.floor(ctx.maxSpread / step) + 1);
}

function slotsFor(
  counts: number[],
  radii: number[],
  anchor: OrbitAnchor,
  ctx: Ctx,
): OrbitSlot[] {
  const slots: OrbitSlot[] = [];
  counts.forEach((count, ring) => {
    const radius = radii[ring] ?? radii[radii.length - 1] ?? ctx.minChord * 1.2;
    const previous = ring > 0 ? (counts[ring - 1] ?? count) : count;
    const angles =
      count === previous
        ? packedAngles(count, radius, ctx)
        : gapAngles(previous, count, radius, ctx);
    for (const theta of angles) {
      slots.push({
        x: anchor.x + Math.cos(theta) * radius,
        y: anchor.y + Math.sin(theta) * radius,
      });
    }
  });
  return slots;
}

/** Pack at minChord, centered on straight up — do not stretch to fill the max arc. */
function packedAngles(count: number, radius: number, ctx: Ctx): number[] {
  if (count <= 1) return [-Math.PI / 2];
  const step = chordStep(radius, ctx);
  const span = Math.min(ctx.maxSpread, step * (count - 1));
  const usedStep = count > 1 ? span / (count - 1) : 0;
  const start = -Math.PI / 2 - span / 2;
  return Array.from({ length: count }, (_, index) => start + usedStep * index);
}

function gapAngles(
  innerCount: number,
  count: number,
  radius: number,
  ctx: Ctx,
): number[] {
  const inner = packedAngles(innerCount, radius, ctx);
  const gaps: number[] = [];
  for (let index = 0; index < inner.length - 1 && gaps.length < count; index += 1) {
    gaps.push((inner[index] + inner[index + 1]) / 2);
  }
  return gaps.length === count ? gaps : packedAngles(count, radius, ctx);
}

export function roundOrbit(value: number): number {
  return Math.round(value * 10) / 10;
}
