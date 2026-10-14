export interface ConstructorSkillNode {
  id: string;
  skillId: string;
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface ConstructorLayout {
  nodes: ConstructorSkillNode[];
}

export const DEFAULT_SKILL_NODE_WIDTH = 220;
export const DEFAULT_SKILL_NODE_HEIGHT = 72;

/** Baseline orbit / column distance from agent hub. */
export const SKILL_ORBIT_RADIUS = 280;

/** Extra space between adjacent skill boxes. */
export const ORBIT_NODE_GAP = 32;

/** World-axis X positions (agent at origin). Connected kinds share one column. */
export const WORLD_ADDRESS_X = -480;
export const WORLD_KIND_X = -300;
export const WORLD_ROW_GAP = 88;
export const WORLD_KIND_WIDTH = 160;
export const WORLD_KIND_HEIGHT = 56;
export const WORLD_ADDRESS_WIDTH = 140;
export const WORLD_ADDRESS_HEIGHT = 44;
/** Center-to-center pitch for addresses stacked beside a kind. */
export const WORLD_ADDRESS_ROW_GAP = 52;
/** Extra space between kind clusters (after packing addresses). */
export const WORLD_KIND_CLUSTER_GAP = 36;
/** Cable port offset from agent rim / kind edge. */
export const WORLD_PORT_GAP = 14;
export const WORLD_PORT_SIZE = 18;

export interface WorldKindColumnSlot {
  kindY: number;
  /** Parallel to the kind's address list order. */
  addressYs: number[];
}

/** @deprecated Prefer dynamic add slot on the skill column. */
export const ADD_SKILL_SLOT = { x: SKILL_ORBIT_RADIUS, y: 0 } as const;

export function createEmptyConstructorLayout(): ConstructorLayout {
  return { nodes: [] };
}

/**
 * Skills sit on the right of the agent in a vertical column (world axis occupies the left).
 * Index 0 is nearest to the horizontal axis going upward/downward alternating, then expand.
 * Simpler: top-to-bottom centered on y=0.
 */
export function skillColumnCenterY(skillIndex: number, skillCount: number): number {
  const pitch = DEFAULT_SKILL_NODE_HEIGHT + ORBIT_NODE_GAP;
  const totalHeight = skillCount * pitch - ORBIT_NODE_GAP;
  const startY = -totalHeight / 2 + DEFAULT_SKILL_NODE_HEIGHT / 2;
  return startY + skillIndex * pitch;
}

export function skillNodePosition(
  skillIndex: number,
  skillCount: number,
): { x: number; y: number } {
  const count = Math.max(1, skillCount);
  return {
    x: SKILL_ORBIT_RADIUS - DEFAULT_SKILL_NODE_WIDTH / 2,
    y: skillColumnCenterY(skillIndex, count) - DEFAULT_SKILL_NODE_HEIGHT / 2,
  };
}

export function addSkillSlotForCount(skillCount: number): { x: number; y: number } {
  if (skillCount === 0) {
    return { x: SKILL_ORBIT_RADIUS, y: 0 };
  }
  const lastCenterY = skillColumnCenterY(skillCount - 1, skillCount);
  const pitch = DEFAULT_SKILL_NODE_HEIGHT + ORBIT_NODE_GAP;
  return {
    x: SKILL_ORBIT_RADIUS,
    y: lastCenterY + pitch,
  };
}

/** Vertical stack centered on y=0 for `count` rows. */
export function worldStackCenterY(index: number, count: number, rowGap = WORLD_ROW_GAP): number {
  if (count <= 0) return 0;
  const total = (count - 1) * rowGap;
  return -total / 2 + index * rowGap;
}

/**
 * Pack world kinds in one column so each kind's address stack does not overlap neighbors.
 * `addressCount` is 0 for idle (unconnected) kinds.
 */
export function layoutWorldKindColumn(
  kinds: Array<{ toolId: string; addressCount: number }>,
): Map<string, WorldKindColumnSlot> {
  const blocks = kinds.map(({ toolId, addressCount }) => {
    const count = Math.max(0, addressCount);
    const addressSpan =
      count <= 0
        ? 0
        : (count - 1) * WORLD_ADDRESS_ROW_GAP + WORLD_ADDRESS_HEIGHT;
    const half = Math.max(WORLD_KIND_HEIGHT, addressSpan) / 2;
    return { toolId, addressCount: count, half, height: half * 2 };
  });

  let total = 0;
  for (let i = 0; i < blocks.length; i += 1) {
    total += blocks[i]!.height;
    if (i < blocks.length - 1) total += WORLD_KIND_CLUSTER_GAP;
  }

  let cursor = -total / 2;
  const result = new Map<string, WorldKindColumnSlot>();
  for (const block of blocks) {
    const kindY = cursor + block.half;
    const addressYs =
      block.addressCount <= 0
        ? []
        : Array.from({ length: block.addressCount }, (_, index) =>
            kindY + worldStackCenterY(index, block.addressCount, WORLD_ADDRESS_ROW_GAP),
          );
    result.set(block.toolId, { kindY, addressYs });
    cursor += block.height + WORLD_KIND_CLUSTER_GAP;
  }
  return result;
}

export function boxesOverlap(
  a: { x: number; y: number; width: number; height: number },
  b: { x: number; y: number; width: number; height: number },
): boolean {
  return (
    a.x < b.x + b.width &&
    a.x + a.width > b.x &&
    a.y < b.y + b.height &&
    a.y + a.height > b.y
  );
}

/** Kept for tests / legacy orbit math callers. */
export function orbitRadiusForCount(_skillCount: number): number {
  return SKILL_ORBIT_RADIUS;
}

export function orbitCenter(
  slotIndex: number,
  totalSlots: number,
  radius = SKILL_ORBIT_RADIUS,
): { x: number; y: number } {
  const total = Math.max(1, totalSlots);
  const angle = (2 * Math.PI * slotIndex) / total;
  return {
    x: Math.cos(angle) * radius,
    y: Math.sin(angle) * radius,
  };
}

export function normalizeConstructorLayout(raw: unknown): ConstructorLayout {
  if (!raw || typeof raw !== "object") return createEmptyConstructorLayout();
  const record = raw as Partial<ConstructorLayout>;
  const nodes = Array.isArray(record.nodes)
    ? record.nodes
        .filter((node): node is ConstructorSkillNode => {
          if (!node || typeof node !== "object") return false;
          const item = node as Partial<ConstructorSkillNode>;
          return typeof item.id === "string" && typeof item.skillId === "string";
        })
        .map((node) => ({
          id: node.id,
          skillId: node.skillId,
          x: Number(node.x) || 0,
          y: Number(node.y) || 0,
          width: Number(node.width) || DEFAULT_SKILL_NODE_WIDTH,
          height: Number(node.height) || DEFAULT_SKILL_NODE_HEIGHT,
        }))
    : [];
  return { nodes };
}
