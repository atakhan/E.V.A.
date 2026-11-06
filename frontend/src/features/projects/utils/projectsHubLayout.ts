import { AGENT_ICON, type DeskAnchor, type DeskBounds } from "@/features/projects/utils/deskLayout";
import {
  layoutPackedOrbit,
  roundOrbit,
  type PackedOrbitParams,
} from "@/features/projects/utils/packedOrbit";

/**
 * Pack project runtimes on an upper half-orbit around Eva.
 * Neighbors clear max-w-48 names; the orbit stays within half the desk
 * and closer to Eva than to the top menu.
 */
/** Matches ProjectsDesk `max-w-48` label column + a small air gap. */
export const PROJECT_LABEL_CLEAR = 192 + 24;
/** Space reserved for the floating top nav. */
export const PROJECT_TOP_MENU = 88;

export const hubOrbitParams: PackedOrbitParams = {
  minChord: PROJECT_LABEL_CLEAR,
  maxSpread: Math.PI * 0.72,
  topMenu: PROJECT_TOP_MENU,
  ringGap: Math.round(AGENT_ICON / 2 + 48 + AGENT_ICON / 2 + 12),
};

export interface HubSlot {
  id: string;
  x: number;
  y: number;
}

/** Icon-box top slots on a dense upper orbit around Eva. */
export function layoutAroundEva(
  ids: string[],
  anchor: DeskAnchor,
  bounds: DeskBounds,
): HubSlot[] {
  if (ids.length === 0 || bounds.width <= 0 || bounds.height <= 0) {
    return ids.map((id) => ({ id, x: anchor.x, y: anchor.y }));
  }

  const slots = layoutPackedOrbit(ids.length, anchor, bounds, hubOrbitParams);
  return ids.map((id, index) => {
    const slot = slots[index] ?? slots[slots.length - 1] ?? { x: anchor.x, y: anchor.y };
    return {
      id,
      x: roundOrbit(slot.x),
      y: roundOrbit(slot.y - AGENT_ICON / 2),
    };
  });
}
