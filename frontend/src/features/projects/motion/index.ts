export {
  DESK_PASS_IDLE,
  passClearsHub,
  passDefersSatelliteReveal,
  passExitsToHub,
  passTakesRuntimeSeat,
  type DeskPass,
} from "@/features/projects/motion/deskPass";
export {
  HANDOFF_PHASES,
  handoffSeat,
  runHandoff,
  type HandoffActions,
  type HandoffPhase,
} from "@/features/projects/motion/handoff";
export {
  holdForLeave,
  holdFromRoute,
  type LeaveHold,
} from "@/features/projects/motion/leaveHold";
export {
  createConstructorReadyGate,
  deskFrame,
  prefersReducedDeskMotion,
  useDeskMotion,
  waitDesk,
} from "@/features/projects/motion/useDeskMotion";
export { flightIdentity, flightTo, type Flight } from "@/features/projects/motion/types";
