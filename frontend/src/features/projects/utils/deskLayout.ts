import type { ProjectAgent } from "@/features/projects/types/project";
import {
  layoutPackedOrbit,
  roundOrbit,
  type OrbitAnchor,
  type OrbitBounds,
  type PackedOrbitParams,
} from "@/features/projects/utils/packedOrbit";

/** Agent icon on the desk. The runtime sphere is 1.5× this. */
export const AGENT_ICON = 64;

/** Icon clearance + a small air gap (names sit under the icon). */
export const RUNTIME_MIN_CHORD = AGENT_ICON + 48;
/** Space reserved for the floating top nav. */
export const RUNTIME_TOP_MENU = 88;

/**
 * Project runtime sphere is `size-24` on ProjectDeskView. Create-agent sits on
 * its inner orbit — same metaphor as «Новый» around Eva, closer than the packed ring.
 */
export const RUNTIME_HUB_ICON = 96;
export const CREATE_AGENT_SIZE = 48;
/** Air between runtime rim and the create icon’s rim (a little above it). */
export const CREATE_AGENT_GAP = 36;

export const runtimeOrbitParams: PackedOrbitParams = {
  minChord: RUNTIME_MIN_CHORD,
  maxSpread: Math.PI * 0.72,
  topMenu: RUNTIME_TOP_MENU,
  ringGap: Math.round(AGENT_ICON / 2 + 48 + AGENT_ICON / 2 + 12),
};

export type DeskAnchor = OrbitAnchor;
export type DeskBounds = OrbitBounds;

export interface CreateAgentSlot {
  id: string;
  x: number;
  y: number;
}

/** Icon-box top slots around the project runtime (packed upper orbit). */
export function layoutAroundRuntime(
  agents: ProjectAgent[],
  anchor: DeskAnchor,
  bounds: DeskBounds,
): ProjectAgent[] {
  if (agents.length === 0 || bounds.width <= 0 || bounds.height <= 0) return agents;

  const slots = layoutPackedOrbit(agents.length, anchor, bounds, runtimeOrbitParams);
  return agents.map((agent, index) => {
    const slot = slots[index] ?? slots[slots.length - 1] ?? { x: anchor.x, y: anchor.y };
    return {
      ...agent,
      x: roundOrbit(slot.x),
      y: roundOrbit(slot.y - AGENT_ICON / 2),
    };
  });
}

/**
 * Create-agent control: dead-center above the runtime on an inner radius (same
 * `translateX(-50%)` seat convention as agent slots), closer than the packed ring.
 */
export function layoutCreateAroundRuntime(
  anchor: DeskAnchor,
  bounds: DeskBounds,
): CreateAgentSlot {
  let radius = RUNTIME_HUB_ICON / 2 + CREATE_AGENT_GAP + CREATE_AGENT_SIZE / 2;
  if (bounds.width > 0 && bounds.height > 0) {
    const outer = layoutPackedOrbit(1, anchor, bounds, runtimeOrbitParams)[0];
    if (outer) {
      const outerR = Math.hypot(outer.x - anchor.x, outer.y - anchor.y);
      radius = Math.min(radius, outerR * 0.55);
    }
  }
  radius = Math.max(RUNTIME_HUB_ICON / 2 + CREATE_AGENT_SIZE / 2 + 12, radius);
  return {
    id: "__create__",
    x: roundOrbit(anchor.x),
    y: roundOrbit(anchor.y - radius - CREATE_AGENT_SIZE / 2),
  };
}
