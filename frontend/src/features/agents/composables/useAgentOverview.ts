import { computed, watch, type ComputedRef, type Ref } from "vue";
import type { Agent } from "@/features/agents/types/agent";
import type { AgentValidationReport } from "@/features/agents/utils/validateAgent";
import { useAgentRuntime } from "@/features/runtime/composables/useAgentRuntime";
import { useRuntimeSummary } from "@/features/runtime/composables/useRuntimeSummary";
import {
  agentActionsPath,
  agentRuntimePath,
  agentRuntimeSimulatePath,
  agentSkillsPath,
  agentToolsPath,
} from "@/router/paths";

const INGRESS_TOOLS = [
  { toolId: "web_client", label: "Web" },
  { toolId: "telegram", label: "Telegram" },
] as const;

const CREDENTIAL_INGRESS_TOOLS = new Set(["web_client", "telegram"]);

export interface AgentReadinessItem {
  id: string;
  label: string;
  description: string;
  done: boolean;
  optional?: boolean;
  href: string;
}

export interface AgentIngressBadge {
  toolId: string;
  label: string;
  active: boolean;
}

function hasIngress(agent: Agent, toolId: string): boolean {
  const instance = agent.tools.find((tool) => tool.toolId === toolId && tool.enabled);
  if (!instance) return false;
  if (CREDENTIAL_INGRESS_TOOLS.has(toolId)) {
    return !!instance.credentialId;
  }
  return true;
}

export function useAgentOverview(options: {
  agentSlug: Ref<string>;
  agent: ComputedRef<Agent | undefined>;
  report: ComputedRef<AgentValidationReport | null>;
}) {
  const { agentSlug, agent, report } = options;

  const runtime = useAgentRuntime(() => agent.value);

  watch(
    agentSlug,
    (slug) => {
      void runtime.loadPublications(slug);
    },
    { immediate: true },
  );

  const {
    agentSummary,
    loading: runtimeSummaryLoading,
    reload: reloadRuntimeSummary,
  } = useRuntimeSummary({
    agentSlug,
    enabled: computed(() => !!agentSlug.value),
  });

  const enabledTools = computed(() => agent.value?.tools.filter((tool) => tool.enabled) ?? []);

  const ingressBadges = computed((): AgentIngressBadge[] => {
    const current = agent.value;
    if (!current) return [];
    return INGRESS_TOOLS.map(({ toolId, label }) => ({
      toolId,
      label,
      active: hasIngress(current, toolId),
    }));
  });

  const readinessItems = computed((): AgentReadinessItem[] => {
    const current = agent.value;
    const slug = agentSlug.value;
    if (!current) return [];

    const errors = report.value?.errors ?? 0;

    return [
      {
        id: "tools",
        label: "Подключены Tools",
        description: "Хотя бы один включённый инструмент",
        done: enabledTools.value.length > 0,
        href: agentToolsPath(slug),
      },
      {
        id: "actions",
        label: "Описаны Actions",
        description: "Поступки агента для шагов FSM",
        done: current.actions.length > 0,
        href: agentActionsPath(slug),
      },
      {
        id: "skills",
        label: "Собраны Skills",
        description: "Процессы с FSM на холсте",
        done: current.skills.length > 0,
        href: agentSkillsPath(slug),
      },
      {
        id: "validation",
        label: "Нет блокирующих ошибок",
        description: "Конструктор согласован",
        done: report.value !== null && errors === 0,
        href: agentSkillsPath(slug),
      },
      {
        id: "published",
        label: "Опубликован",
        description: "Runtime исполняет опубликованную версию",
        done: runtime.isPublished.value,
        href: agentRuntimeSimulatePath(slug),
      },
      {
        id: "simulate",
        label: "Протестирован в Simulate",
        description: "Отправьте тестовое событие в runtime",
        done: false,
        optional: true,
        href: agentRuntimeSimulatePath(slug),
      },
    ];
  });

  const requiredReadinessItems = computed(() =>
    readinessItems.value.filter((item) => !item.optional),
  );

  const readinessProgress = computed(() => {
    const required = requiredReadinessItems.value;
    if (!required.length) return 0;
    const done = required.filter((item) => item.done).length;
    return Math.round((done / required.length) * 100);
  });

  const canPublish = computed(
    () => (report.value?.errors ?? 0) === 0 && !!agent.value?.skills.length,
  );

  const blockingIssues = computed(
    () =>
      report.value?.issues.filter(
        (issue) => issue.severity === "error" || issue.severity === "warning",
      ) ?? [],
  );

  const infoIssues = computed(
    () => report.value?.issues.filter((issue) => issue.severity === "info") ?? [],
  );

  async function handlePublish() {
    const result = await runtime.publishDraft(agentSlug.value);
    if (result.ok) {
      await reloadRuntimeSummary({ silent: true });
    }
    return result;
  }

  return {
    ...runtime,
    agentSummary,
    runtimeSummaryLoading,
    reloadRuntimeSummary,
    enabledTools,
    ingressBadges,
    readinessItems,
    requiredReadinessItems,
    readinessProgress,
    canPublish,
    blockingIssues,
    infoIssues,
    handlePublish,
    agentRuntimePath: () => agentRuntimePath(agentSlug.value),
    agentRuntimeSimulatePath: () => agentRuntimeSimulatePath(agentSlug.value),
  };
}
