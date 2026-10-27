import type { AgentRuntimeSummary } from "@/features/runtime/types/runtime";

export type AgentHubTone = "neutral" | "success" | "warning";

export type AgentHubRunStatus = "running" | "waiting" | "error" | "completed" | "cancelled";

export interface AgentHubRunCount {
  status: AgentHubRunStatus;
  label: string;
  count: number;
}

/** What the center of the table says about the agent as an executing system. */
export interface AgentHubStatus {
  tone: AgentHubTone;
  published: boolean;
  version: string | null;
  publishedAt: string | null;
  /** «Опубликован 0.1.1» / «Черновик новее 0.1.1» / «Не опубликован». */
  headline: string;
  /** Human names of the draft parts that are not published yet; empty when the draft matches. */
  unpublishedParts: string[];
  activeRuns: number;
  /** One line for the circle: version, draft and active runs. */
  compactLine: string;
  runs: AgentHubRunCount[];
}

const DRAFT_PART_LABEL: Record<string, string> = {
  skills: "навыки",
  actions: "Actions",
  tools: "плагины и каналы",
  defaultSkillId: "навык по умолчанию",
};

const RUN_LABEL: Record<AgentHubRunStatus, string> = {
  running: "Идут",
  waiting: "Ждут",
  error: "С ошибкой",
  completed: "Завершены",
  cancelled: "Отменены",
};

const RUN_ORDER: AgentHubRunStatus[] = ["running", "waiting", "error", "completed", "cancelled"];

export function describeAgentHub(summary: AgentRuntimeSummary): AgentHubStatus {
  const published = summary.isPublished && Boolean(summary.latestPublicationVersion);
  const version = summary.latestPublicationVersion;
  const unpublishedParts = (summary.draftChanges ?? []).map((part) => DRAFT_PART_LABEL[part] ?? part);
  const draftAhead = published && unpublishedParts.length > 0;
  const activeRuns = summary.running + summary.waiting;

  const headline = !published
    ? "Не опубликован"
    : draftAhead
      ? `Черновик новее ${version}`
      : `Опубликован ${version}`;

  const compact = published ? [version ?? ""] : ["не опубликован"];
  if (draftAhead) compact.push("черновик новее");
  if (summary.running) compact.push(`идут ${summary.running}`);
  if (summary.waiting) compact.push(`ждут ${summary.waiting}`);

  return {
    tone: !published ? "neutral" : draftAhead ? "warning" : "success",
    published,
    version,
    publishedAt: summary.latestPublishedAt,
    headline,
    unpublishedParts: draftAhead ? unpublishedParts : [],
    activeRuns,
    compactLine: compact.join(" · "),
    runs: RUN_ORDER.map((status) => ({ status, label: RUN_LABEL[status], count: summary[status] })),
  };
}
