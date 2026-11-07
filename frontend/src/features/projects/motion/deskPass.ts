/**
 * Explicit transition pass for the Eva hub ↔ project desk handoff.
 * Replaces the old `hubClear` boolean that meant clear-backdrop + defer burst + exiting.
 */

export type DeskPass =
  | { kind: "idle" }
  | { kind: "evaToProject"; phase: "fly" | "land" }
  | { kind: "projectToEva"; phase: "fly" | "land" };

export const DESK_PASS_IDLE: DeskPass = { kind: "idle" };

/** Transparent hub so the project desk shows through during a cross-desk flight. */
export function passClearsHub(pass: DeskPass): boolean {
  return pass.kind !== "idle";
}

/** Runtime seat is occupied by the hub flyer — keep the desk runtime invisible. */
export function passTakesRuntimeSeat(pass: DeskPass): boolean {
  return pass.kind !== "idle";
}

/** Parent is leaving the project desk toward Eva — do not re-expand members. */
export function passExitsToHub(pass: DeskPass): boolean {
  return pass.kind === "projectToEva";
}

/** Parent orchestrates the open burst — desk stays collapsed until told. */
export function passDefersSatelliteReveal(pass: DeskPass): boolean {
  return pass.kind === "evaToProject";
}
