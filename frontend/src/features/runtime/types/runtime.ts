export interface RuntimeRunResponse {
  ok: boolean;
  created: boolean;
  skillRunId: string;
  status: string;
  currentState: string;
  history: string[];
  toolCalls: Array<Record<string, unknown>>;
}

export interface AgentPublicationSummary {
  id: string;
  version: string;
  publishedAt: string;
}
