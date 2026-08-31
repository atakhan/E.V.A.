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
  isPublished: boolean;
  archived?: boolean;
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

export type SkillRunStatusFilter = "active" | "waiting" | "completed" | "error" | "cancelled" | "all";

export const TERMINAL_RUN_STATUSES = new Set(["completed", "error", "cancelled"]);

export const ACTIVE_RUN_STATUSES = new Set(["running", "waiting"]);
