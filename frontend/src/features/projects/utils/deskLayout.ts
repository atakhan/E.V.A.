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

export const runtimeOrbitParams: PackedOrbitParams = {
  minChord: RUNTIME_MIN_CHORD,
  maxSpread: Math.PI * 0.72,
  topMenu: RUNTIME_TOP_MENU,
  ringGap: Math.round(AGENT_ICON / 2 + 48 + AGENT_ICON / 2 + 12),
};

export type DeskAnchor = OrbitAnchor;
export type DeskBounds = OrbitBounds;

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
