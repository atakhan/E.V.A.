import { computed, watch, type Ref } from "vue";
import { agentSaveStatus, apiAvailable } from "@/features/agents/services/agentsStorage";
import { describeAgentHub } from "@/features/constructor/utils/agentHubStatus";
import { useRuntimeSummary } from "@/features/runtime/composables/useRuntimeSummary";

export function useAgentHubStatus(agentSlug: Ref<string>) {
  const { agentSummary, loading, error, reload } = useRuntimeSummary({
    agentSlug,
    enabled: computed(() => apiAvailable.value && Boolean(agentSlug.value)),
  });

  // The server compares the saved draft with the publication, so ask again after each save.
  watch(agentSaveStatus, (saveStatus) => {
    if (saveStatus === "saved") void reload({ silent: true });
  });

  const status = computed(() => (agentSummary.value ? describeAgentHub(agentSummary.value) : null));

  return { status, loading, error };
}
