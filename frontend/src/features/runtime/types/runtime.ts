export interface RuntimeRunResponse {
  ok: boolean;
  created: boolean;
  skillRunId: string;
  agentSlug?: string;
  skillId?: string;
  status: string;
  currentState: string;
  publicationVersion?: string;
  conversationId?: string | null;
  error?: string | null;
  history: string[];
  /** Working inputs declared on the skill. Service keys are omitted. */
  params?: Record<string, unknown>;
  /** Run variables without keys that start with `_`. */
  vars?: Record<string, unknown>;
  toolCalls: Array<Record<string, unknown>>;
  createdAt?: string | null;
  updatedAt?: string | null;
}

export interface SkillRunSummary {
  skillRunId: string;
  agentSlug: string;
  skillId: string;
  status: string;
  currentState: string;
  publicationVersion: string;
  conversationId: string | null;
  error: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface SkillRunListResponse {
  ok: boolean;
  items: SkillRunSummary[];
  total: number;
  limit: number;
  offset: number;
}

export interface AgentRuntimeSummary {
  agentSlug: string;
  running: number;
  waiting: number;
  error: number;
  completed: number;
  cancelled: number;
  latestPublicationVersion: string | null;
  latestPublishedAt: string | null;
  isPublished: boolean;
  archived?: boolean;
  /**
   * Agent summary only. Parts runtime reads that the draft changes compared to the latest
   * publication (`skills`, `actions`, `tools`, `defaultSkillId`); `null` before the first one.
   */
  draftChanges?: string[] | null;
}

export interface RuntimeSummaryTotals {
  running: number;
  waiting: number;
  error: number;
  completed24h: number;
}

export interface RuntimeSummary {
  ok: boolean;
  agents: AgentRuntimeSummary[];
  totals: RuntimeSummaryTotals;
}

export interface RuntimeMetrics {
  ok: boolean;
  events_processed: number;
  runs_active: number;
  action_failures: number;
}

export interface SkillRunHistoryEvent {
  id: string;
  eventType: string;
  payload: Record<string, unknown>;
  fromState: string | null;
  toState: string | null;
  toolCalls: Array<Record<string, unknown>>;
  created: boolean;
  createdAt: string;
}

export interface SkillRunHistoryToolExecution {
  id: string;
  toolInstanceId: string;
  command: string;
  status: string;
  durationMs: number | null;
  error: string | null;
}

export interface SkillRunHistoryActionRun {
  id: string;
  actionId: string;
  status: string;
  output: Record<string, unknown>;
  error: string | null;
  toolExecutions: SkillRunHistoryToolExecution[];
}

export interface SkillRunHistory {
  ok: boolean;
  skillRunId: string;
  events: SkillRunHistoryEvent[];
  actionRuns: SkillRunHistoryActionRun[];
}

export interface AgentPublicationSummary {
  id: string;
  version: string;
  publishedAt: string;
}

export interface AgentMemoryEvent {
  id: string;
  skillRunId: string;
  skillId: string;
  eventType: string;
  payload: Record<string, unknown>;
  fromState: string | null;
  toState: string | null;
  createdAt: string;
}

export interface AgentMemoryRun {
  skillRunId: string;
  skillId: string;
  status: string;
  currentState: string;
  params: Record<string, unknown>;
  vars: Record<string, unknown>;
  conversationId: string | null;
  error: string | null;
  updatedAt: string;
}

export interface AgentMemory {
  ok: boolean;
  events: AgentMemoryEvent[];
  runs: AgentMemoryRun[];
}

export type SkillRunStatusFilter = "active" | "waiting" | "completed" | "error" | "cancelled" | "all";

export const TERMINAL_RUN_STATUSES = new Set(["completed", "error", "cancelled"]);

export const ACTIVE_RUN_STATUSES = new Set(["running", "waiting"]);
