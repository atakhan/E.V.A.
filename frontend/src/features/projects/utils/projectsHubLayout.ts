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

/**
 * Eva hub sphere is `size-24` on ProjectsListView. Create-project sits on her
 * inner orbit — same metaphor as project satellites, but closer than the packed ring.
 */
export const EVA_HUB_ICON = 96;
export const CREATE_PROJECT_SIZE = 48;
/** Air between Eva’s rim and the create icon’s rim (a little above her). */
export const CREATE_PROJECT_GAP = 36;

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

/**
 * Create-project control: dead-center above Eva on an inner radius (same
 * `translateX(-50%)` seat convention as project slots), closer than the
 * packed project ring.
 */
export function layoutCreateAroundEva(
  anchor: DeskAnchor,
  bounds: DeskBounds,
): HubSlot {
  // Center-to-center: Eva rim + air + half create icon.
  let radius = EVA_HUB_ICON / 2 + CREATE_PROJECT_GAP + CREATE_PROJECT_SIZE / 2;
  if (bounds.width > 0 && bounds.height > 0) {
    const outer = layoutPackedOrbit(1, anchor, bounds, hubOrbitParams)[0];
    if (outer) {
      const outerR = Math.hypot(outer.x - anchor.x, outer.y - anchor.y);
      // Never climb into the project ring; keep a clear inner seat.
      radius = Math.min(radius, outerR * 0.55);
    }
  }
  radius = Math.max(EVA_HUB_ICON / 2 + CREATE_PROJECT_SIZE / 2 + 12, radius);
  return {
    id: "__create__",
    // `orbitPlaceStyle` centers with translateX(-50%) — pass the icon center X,
    // same as layoutAroundEva project slots.
    x: roundOrbit(anchor.x),
    y: roundOrbit(anchor.y - radius - CREATE_PROJECT_SIZE / 2),
  };
}
