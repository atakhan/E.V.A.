import { GRID_SIZE, type FlowDirection } from "@/features/skills/types/fsm";

export type { FlowDirection };

export const MIN_NODE_GAP = 40;
export const NODE_ROUTING_PADDING = 20;
export const OUTER_CORRIDOR = 80;
export const ROUTE_STUB = Math.max(GRID_SIZE * 1.5, NODE_ROUTING_PADDING + GRID_SIZE / 2);

export const BEND_PENALTY = 36;
export const CROSSING_PENALTY = 160;
export const PROXIMITY_PENALTY = 0.15;
export const DIRECTION_PENALTY = 0.22;
export const INTERIOR_PENALTY = 0.7;

export const ALIGNMENT_THRESHOLD = 6;
export const MAX_ROUTE_EXPANSIONS = 14_000;
export const MIN_LABEL_SEGMENT = 48;
