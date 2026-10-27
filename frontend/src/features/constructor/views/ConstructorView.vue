<script setup lang="ts">
import { computed, nextTick, ref, toRef, useTemplateRef, watch } from "vue";
import { useRouter } from "vue-router";
import { useAgents } from "@/features/agents/composables/useAgents";
import { usePluginConnections } from "@/features/agents/composables/usePluginConnections";
import { useWorldConnections } from "@/features/agents/composables/useWorldConnections";
import { getAgentBySlug } from "@/features/agents/services/agentsStorage";
import { skillDependencies, toolUsage } from "@/features/agents/utils/agentDependencies";
import { evaluateWorldAddress } from "@/features/agents/utils/evaluateWorldAddress";
import AgentHubCard, {
  type AgentHubPhase,
} from "@/features/constructor/components/AgentHubCard.vue";
import InfiniteCanvas, {
  type CanvasHighlight,
  type CanvasPlugin,
  type CanvasWorldAddress,
  type CanvasWorldKind,
} from "@/features/constructor/components/InfiniteCanvas.vue";
import AddressConfigPanel from "@/features/constructor/components/AddressConfigPanel.vue";
import KindConnectorPanel from "@/features/constructor/components/KindConnectorPanel.vue";
import PluginPanel from "@/features/constructor/components/PluginPanel.vue";
import ToolCatalogSheet from "@/features/constructor/components/ToolCatalogSheet.vue";
import SkillDetailPanel from "@/features/constructor/components/SkillDetailPanel.vue";
import SkillPickerDialog from "@/features/constructor/components/SkillPickerDialog.vue";
import { useAgentHubStatus } from "@/features/constructor/composables/useAgentHubStatus";
import { useConstructor } from "@/features/constructor/composables/useConstructor";
import { describeMemoryCard } from "@/features/memory/utils/memoryCard";
import MemoryPanel from "@/features/memory/components/MemoryPanel.vue";
import { useAgentMemory } from "@/features/memory/composables/useAgentMemory";
import {
  addPluginSlotForCount,
  layoutWorldKindColumn,
  pluginNodeCenter,
  WORLD_ADDRESS_X,
  WORLD_KIND_CLUSTER_GAP,
  WORLD_KIND_HEIGHT,
  WORLD_KIND_X,
} from "@/features/constructor/types/constructor";
import { useSkills } from "@/features/skills/composables/useSkills";
import { fetchCredentials, type ToolCredential } from "@/features/tools/services/credentialsApi";
import { skillPath } from "@/router/paths";

const props = defineProps<{
  agentSlug: string;
}>();

const router = useRouter();
const { updateAgent } = useAgents();
const { createSkill, getSkill, deleteSkill } = useSkills();
const { nodes, placeSkill, addSkillSlot, findNodeBySkillId } = useConstructor(
  () => props.agentSlug,
);
const {
  worldTools,
  connectedToolIds,
  linkStatus,
  connectKind,
  disconnectKind,
  addAddress,
  removeAddress,
  updateAddress,
  getAddress,
  addressesFor,
} = useWorldConnections(() => props.agentSlug);
const {
  pluginTools,
  pluginInstances,
  connectedPluginTypeIds,
  pluginStatus,
  connectPlugin,
  disconnectPlugin,
} = usePluginConnections(() => props.agentSlug);
const {
  status: hubStatus,
  loading: hubStatusLoading,
  error: hubStatusError,
} = useAgentHubStatus(toRef(props, "agentSlug"));
const {
  memory,
  loading: memoryLoading,
  error: memoryError,
} = useAgentMemory(toRef(props, "agentSlug"));

const pickerOpen = ref(false);
const kindCatalogOpen = ref(false);
const pluginCatalogOpen = ref(false);
const selectedNodeId = ref<string | null>(null);
const selectedKindToolId = ref<string | null>(null);
const selectedAddressId = ref<string | null>(null);
const selectedPluginId = ref<string | null>(null);
const memoryOpen = ref(false);
const agentPhase = ref<AgentHubPhase>("circle");
const viewport = ref({ panX: 0, panY: 0, zoom: 1 });
const canvasRef = useTemplateRef<InstanceType<typeof InfiniteCanvas>>("canvas");
const credentials = ref<ToolCredential[]>([]);
const credentialsReady = ref(false);

const agent = computed(() => getAgentBySlug(props.agentSlug));

const selectedKindLink = computed(() => {
  if (!selectedKindToolId.value) return null;
  return linkStatus(selectedKindToolId.value);
});

const selectedPluginLink = computed(() =>
  selectedPluginId.value ? pluginStatus(selectedPluginId.value) : null,
);

const selectedAddress = computed(() =>
  selectedAddressId.value ? getAddress(selectedAddressId.value) ?? null : null,
);

const selectedAddressEvaluation = computed(() => {
  const address = selectedAddress.value;
  if (!address) return null;
  const credential = credentials.value.find((item) => item.id === address.credentialId) ?? null;
  return evaluateWorldAddress(address, credential, { credentialsReady: credentialsReady.value });
});

async function loadCredentials() {
  try {
    credentials.value = await fetchCredentials(props.agentSlug);
  } catch {
    credentials.value = [];
  } finally {
    credentialsReady.value = true;
  }
}

watch(
  () => props.agentSlug,
  () => {
    credentialsReady.value = false;
    void loadCredentials();
  },
  { immediate: true },
);

const canvasNodes = computed(() =>
  nodes.value.map((node) => ({
    ...node,
    name: getSkill(props.agentSlug, node.skillId)?.name ?? node.skillId,
  })),
);

const selectedSkill = computed(() => {
  const node = nodes.value.find((item) => item.id === selectedNodeId.value);
  if (!node) return null;
  return getSkill(props.agentSlug, node.skillId) ?? null;
});

const selectedSkillDependencies = computed(() => {
  const current = agent.value;
  const skill = selectedSkill.value;
  return current && skill ? skillDependencies(current, skill) : null;
});

const connectedWorldTools = computed(() =>
  worldTools.value.filter((tool) => connectedToolIds.value.includes(tool.id)),
);

const worldColumnLayout = computed(() =>
  layoutWorldKindColumn(
    connectedWorldTools.value.map((tool) => ({
      toolId: tool.id,
      addressCount: addressesFor(tool.id).length,
    })),
  ),
);

const addKindSlot = computed(() => {
  const slots = [...worldColumnLayout.value.values()];
  if (slots.length === 0) return { x: WORLD_KIND_X, y: 0 };
  const bottom = Math.max(...slots.map((slot) => slot.kindY));
  return {
    x: WORLD_KIND_X,
    y: bottom + WORLD_KIND_HEIGHT / 2 + WORLD_KIND_CLUSTER_GAP + 24,
  };
});

const canvasWorldKinds = computed((): CanvasWorldKind[] => {
  const layout = worldColumnLayout.value;
  return connectedWorldTools.value.map((tool) => {
    const evaluation = linkStatus(tool.id);
    return {
      toolId: tool.id,
      name: tool.name,
      connected: true,
      status: evaluation.status,
      reason: evaluation.reason,
      x: WORLD_KIND_X,
      y: layout.get(tool.id)?.kindY ?? 0,
    };
  });
});

const canvasWorldAddresses = computed((): CanvasWorldAddress[] => {
  const layout = worldColumnLayout.value;
  const items: CanvasWorldAddress[] = [];
  for (const tool of connectedWorldTools.value) {
    const slot = layout.get(tool.id);
    if (!slot) continue;
    const addresses = addressesFor(tool.id);
    addresses.forEach((address, addressIndex) => {
      const credential = credentials.value.find((item) => item.id === address.credentialId) ?? null;
      const evaluation = evaluateWorldAddress(address, credential, {
        credentialsReady: credentialsReady.value,
      });
      items.push({
        id: address.id,
        toolId: tool.id,
        name: address.name,
        status: evaluation.status,
        reason: evaluation.reason,
        x: WORLD_ADDRESS_X,
        y: slot.addressYs[addressIndex] ?? slot.kindY,
      });
    });
  }
  return items;
});

const canvasPlugins = computed((): CanvasPlugin[] =>
  pluginInstances.value.map((instance, index) => {
    const evaluation = pluginStatus(instance.id);
    const center = pluginNodeCenter(index);
    return {
      instanceId: instance.id,
      typeId: instance.toolId,
      name: instance.name,
      status: evaluation.status,
      reason: evaluation.reason,
      x: center.x,
      y: center.y,
    };
  }),
);

const addPluginSlot = computed(() => addPluginSlotForCount(pluginInstances.value.length));

const memoryLines = computed(() =>
  describeMemoryCard(memory.value, {
    loading: memoryLoading.value,
    failed: Boolean(memoryError.value),
  }),
);

const highlight = computed((): CanvasHighlight | null => {
  const current = agent.value;
  if (!current || agentPhase.value === "details") return null;

  const skill = selectedSkill.value;
  const deps = selectedSkillDependencies.value;
  if (skill && deps) {
    return {
      skillIds: [skill.id],
      kindToolIds: deps.channels.map((item) => item.typeId),
      pluginIds: deps.plugins.map((item) => item.instanceId),
    };
  }

  if (selectedPluginId.value) {
    const usage = toolUsage(current, { kind: "instance", instanceId: selectedPluginId.value });
    return {
      skillIds: usage.skills.map((item) => item.skill.id),
      kindToolIds: [],
      pluginIds: [selectedPluginId.value],
    };
  }

  if (selectedKindToolId.value) {
    const usage = toolUsage(current, { kind: "type", typeId: selectedKindToolId.value });
    return {
      skillIds: usage.skills.map((item) => item.skill.id),
      kindToolIds: [selectedKindToolId.value],
      pluginIds: [],
    };
  }

  return null;
});

function clearSelection() {
  selectedNodeId.value = null;
  selectedKindToolId.value = null;
  selectedAddressId.value = null;
  selectedPluginId.value = null;
  memoryOpen.value = false;
}

function openPicker() {
  pickerOpen.value = true;
}

function openKindConnector(toolId: string) {
  clearSelection();
  selectedKindToolId.value = toolId;
  if (agentPhase.value !== "details") agentPhase.value = "circle";
}

function closeKindConnector() {
  selectedKindToolId.value = null;
}

function openAddressConfig(addressId: string) {
  clearSelection();
  selectedAddressId.value = addressId;
  if (agentPhase.value !== "details") agentPhase.value = "circle";
}

function closeAddressConfig() {
  selectedAddressId.value = null;
}

function openPlugin(instanceId: string) {
  clearSelection();
  selectedPluginId.value = instanceId;
  if (agentPhase.value !== "details") agentPhase.value = "circle";
}

function closePlugin() {
  selectedPluginId.value = null;
}

function openMemory() {
  clearSelection();
  memoryOpen.value = true;
  if (agentPhase.value !== "details") agentPhase.value = "circle";
}

function closeMemory() {
  memoryOpen.value = false;
}

async function focusNode(nodeId: string) {
  clearSelection();
  selectedNodeId.value = nodeId;
  agentPhase.value = "circle";
  await nextTick();
  const node = nodes.value.find((item) => item.id === nodeId);
  if (node) canvasRef.value?.centerOnNode(node);
}

function focusSkill(skillId: string) {
  const node = findNodeBySkillId(skillId);
  if (node) void focusNode(node.id);
}

function onSelectSkill(skillId: string) {
  pickerOpen.value = false;
  const node = placeSkill(skillId);
  if (!node) return;
  void focusNode(node.id);
}

async function onCreateSkill() {
  pickerOpen.value = false;
  const skill = createSkill(props.agentSlug);
  if (!skill) return;
  const node = placeSkill(skill.id);
  if (node) {
    await focusNode(node.id);
    return;
  }
  await router.push(skillPath(props.agentSlug, skill.id));
}

function onSelectNode(nodeId: string) {
  clearSelection();
  selectedNodeId.value = nodeId;
  if (agentPhase.value !== "details") agentPhase.value = "circle";
}

function onClearSelection() {
  clearSelection();
  if (agentPhase.value === "card") agentPhase.value = "circle";
}

function onViewport(payload: { panX: number; panY: number; zoom: number }) {
  viewport.value = payload;
}

function openAgentCard() {
  clearSelection();
  agentPhase.value = "card";
}

function closeAgentCard() {
  if (agentPhase.value === "card") agentPhase.value = "circle";
}

function openAgentDetails() {
  clearSelection();
  agentPhase.value = "details";
}

function closeAgentDetails() {
  agentPhase.value = "card";
}

function onUpdateAgent(patch: { name?: string; description?: string; icon?: string }) {
  const current = agent.value;
  if (!current) return;
  updateAgent(current.id, patch);
}

async function openSkillEditor() {
  const skill = selectedSkill.value;
  if (!skill) return;
  await router.push(skillPath(props.agentSlug, skill.id));
}

function deleteSelectedSkill() {
  const skill = selectedSkill.value;
  if (!skill) return;
  if (!confirm(`Удалить навык «${skill.name}»?`)) return;
  deleteSkill(props.agentSlug, skill.id);
  selectedNodeId.value = null;
}

function onInsertKind(toolId: string) {
  const result = connectKind(toolId);
  if (result.ok) kindCatalogOpen.value = false;
}

function onSelectKind(toolId: string) {
  openKindConnector(toolId);
}

function onDisconnectKind(toolId: string) {
  const name = worldTools.value.find((tool) => tool.id === toolId)?.name ?? toolId;
  if (!confirm(`Отключить канал «${name}»?`)) return;
  disconnectKind(toolId);
  if (selectedKindToolId.value === toolId) closeKindConnector();
  if (selectedAddress.value?.toolId === toolId) closeAddressConfig();
}

function onInsertPlugin(typeId: string) {
  const result = connectPlugin(typeId);
  if (!result.ok || !result.instanceId) return;
  pluginCatalogOpen.value = false;
  openPlugin(result.instanceId);
}

function onDisconnectPlugin(instanceId: string) {
  const current = agent.value;
  if (!current) return;
  const name = current.tools.find((tool) => tool.id === instanceId)?.name ?? instanceId;
  const callers = toolUsage(current, { kind: "instance", instanceId }).actions.map(
    (item) => item.action.name,
  );
  const warning = callers.length
    ? `\n\nЕго вызывают: ${callers.join(", ")}. Без плагина агент не опубликуется.`
    : "";
  if (!confirm(`Отключить плагин «${name}»?${warning}`)) return;
  disconnectPlugin(instanceId);
  if (selectedPluginId.value === instanceId) closePlugin();
}

function onAddAddress(toolId: string) {
  const address = addAddress(toolId, toolId === "web_client" ? "Приложение" : undefined);
  if (address) openAddressConfig(address.id);
}

function onSelectAddress(addressId: string) {
  openAddressConfig(addressId);
}

function onRemoveAddress(addressId: string) {
  const name = getAddress(addressId)?.name ?? "адрес";
  if (!confirm(`Удалить адрес «${name}»?`)) return;
  removeAddress(addressId);
  if (selectedAddressId.value === addressId) closeAddressConfig();
}

function onUpdateAddress(
  patch: { name?: string; credentialId?: string; config?: Record<string, unknown> },
) {
  if (!selectedAddressId.value) return;
  updateAddress(selectedAddressId.value, patch);
}
</script>

<template>
  <div class="relative h-full min-h-0 w-full flex-1 overflow-hidden">
    <InfiniteCanvas
      ref="canvas"
      :nodes="canvasNodes"
      :selected-node-id="selectedNodeId"
      :selected-kind-tool-id="selectedKindToolId"
      :selected-address-id="selectedAddressId"
      :selected-plugin-id="selectedPluginId"
      :add-skill-slot="addSkillSlot"
      :add-kind-slot="addKindSlot"
      :add-plugin-slot="addPluginSlot"
      :world-kinds="canvasWorldKinds"
      :world-addresses="canvasWorldAddresses"
      :plugins="canvasPlugins"
      :highlight="highlight"
      :memory-selected="memoryOpen"
      :memory-history-line="memoryLines.historyLine"
      :memory-state-line="memoryLines.stateLine"
      @create-skill="openPicker"
      @select-node="onSelectNode"
      @clear-selection="onClearSelection"
      @viewport="onViewport"
      @add-kind="kindCatalogOpen = true"
      @select-kind="onSelectKind"
      @disconnect-kind="onDisconnectKind"
      @add-address="onAddAddress"
      @select-address="onSelectAddress"
      @remove-address="onRemoveAddress"
      @add-plugin="pluginCatalogOpen = true"
      @select-plugin="openPlugin"
      @disconnect-plugin="onDisconnectPlugin"
      @select-memory="openMemory"
    />

    <AgentHubCard
      v-if="agent"
      :phase="agentPhase"
      :agent="agent"
      :status="hubStatus"
      :status-loading="hubStatusLoading"
      :status-error="hubStatusError"
      :pan-x="viewport.panX"
      :pan-y="viewport.panY"
      :zoom="viewport.zoom"
      @open="openAgentCard"
      @close-card="closeAgentCard"
      @open-details="openAgentDetails"
      @close-details="closeAgentDetails"
      @update="onUpdateAgent"
    />

    <AddressConfigPanel
      v-if="selectedAddress && selectedAddressEvaluation && agentPhase !== 'details'"
      :agent-slug="agentSlug"
      :address-id="selectedAddress.id"
      :status="selectedAddressEvaluation.status"
      :reason="selectedAddressEvaluation.reason"
      @close="closeAddressConfig"
      @update="onUpdateAddress"
      @credentials-changed="loadCredentials"
      @remove="onRemoveAddress(selectedAddress.id)"
    />

    <KindConnectorPanel
      v-else-if="selectedKindToolId && selectedKindLink && agentPhase !== 'details'"
      :agent-slug="agentSlug"
      :tool-id="selectedKindToolId"
      :status="selectedKindLink.status"
      :reason="selectedKindLink.reason"
      @close="closeKindConnector"
      @select-skill="focusSkill"
    />

    <PluginPanel
      v-else-if="selectedPluginId && selectedPluginLink && agentPhase !== 'details'"
      :agent-slug="agentSlug"
      :instance-id="selectedPluginId"
      :status="selectedPluginLink.status"
      :reason="selectedPluginLink.reason"
      @close="closePlugin"
      @disconnect="onDisconnectPlugin(selectedPluginId)"
      @select-skill="focusSkill"
    />

    <SkillDetailPanel
      v-else-if="selectedSkill && selectedSkillDependencies && agentPhase !== 'details'"
      :agent-slug="agentSlug"
      :skill="selectedSkill"
      :dependencies="selectedSkillDependencies"
      @close="onClearSelection"
      @open-editor="openSkillEditor"
      @remove="deleteSelectedSkill"
      @select-kind="openKindConnector"
      @select-plugin="openPlugin"
    />

    <MemoryPanel
      v-else-if="memoryOpen && agentPhase !== 'details'"
      :agent-slug="agentSlug"
      :memory="memory"
      :loading="memoryLoading"
      :error="memoryError"
      @close="closeMemory"
    />

    <ToolCatalogSheet
      :open="kindCatalogOpen"
      eyebrow="Внешний мир"
      title="Добавить канал"
      description="Каналы связи с внешним миром, доступные в E.V.A. Выбранный канал сразу встанет на стол. Подключение настраивается по кабелю."
      empty-text="В E.V.A. пока нет плагинов внешнего мира."
      :tools="worldTools"
      :connected-ids="connectedToolIds"
      @close="kindCatalogOpen = false"
      @pick="onInsertKind"
    />

    <ToolCatalogSheet
      :open="pluginCatalogOpen"
      eyebrow="Плагины"
      title="Добавить плагин"
      description="Инструменты, которые вызывают Actions агента: модели, обработка текста и другое. Плагин встанет под агентом, а навыки будут пользоваться им через Actions."
      empty-text="В каталоге E.V.A. пока нет плагинов."
      :tools="pluginTools"
      :connected-ids="connectedPluginTypeIds"
      @close="pluginCatalogOpen = false"
      @pick="onInsertPlugin"
    />

    <SkillPickerDialog
      v-model:open="pickerOpen"
      :agent-slug="agentSlug"
      @select="onSelectSkill"
      @create="onCreateSkill"
    />
  </div>
</template>
