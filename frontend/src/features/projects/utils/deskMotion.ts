/** Shared timing so the desk icon and the agent constructor stay in step. */
export const DESK_EASE = "cubic-bezier(0.22, 1, 0.36, 1)";
/** Open leaves the desk icon from rest, then settles in the center. */
export const DESK_EASE_OPEN = "cubic-bezier(0.4, 0, 0.2, 1)";
export const DESK_DIM_MS = 280;
export const DESK_MOVE_MS = 680;
export const DESK_HANDOFF_MS = 220;
export const DESK_REVEAL_MS = 480;
/** Other elements join the icon flight this far into it (0 = together with the icon). */
export const DESK_SPREAD_AT = 0;
/** How long desk chrome takes to step aside or return, matching the rest of the flight. */
export const DESK_ASIDE_MS = Math.round(DESK_MOVE_MS * (1 - DESK_SPREAD_AT));

/** Move an icon center onto the desk center and scale it to the agent hub. */
export function focusIconShift(
  iconCenter: { x: number; y: number },
  desk: { width: number; height: number },
  iconSize: number,
  hubSize: number,
): { dx: number; dy: number; scale: number } {
  return {
    dx: desk.width / 2 - iconCenter.x,
    dy: desk.height / 2 - iconCenter.y,
    scale: iconSize > 0 ? hubSize / iconSize : 1,
  };
}
