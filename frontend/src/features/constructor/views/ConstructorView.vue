<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, toRef, useTemplateRef, watch } from "vue";
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
import SshCommandsConstructor from "@/features/constructor/components/SshCommandsConstructor.vue";
import ToolCatalogSheet from "@/features/constructor/components/ToolCatalogSheet.vue";
import SkillPickerDialog from "@/features/constructor/components/SkillPickerDialog.vue";
import { useAgentHubStatus } from "@/features/constructor/composables/useAgentHubStatus";
import { useConstructor } from "@/features/constructor/composables/useConstructor";
import { describeMemoryCard } from "@/features/memory/utils/memoryCard";
import MemoryFacetCards from "@/features/memory/components/MemoryFacetCards.vue";
import { useAgentMemory } from "@/features/memory/composables/useAgentMemory";
import {
  layoutMemoryOrbit,
  MEMORY_SAT_SIZE,
  memoryOrbitItem,
  type MemoryOrbitId,
} from "@/features/memory/utils/memoryOrbit";
import {
  addPluginSlotForCount,
  AGENT_SIZE,
  DEFAULT_SKILL_NODE_HEIGHT,
  DEFAULT_SKILL_NODE_WIDTH,
  layoutWorldKindColumn,
  MEMORY_NODE_HEIGHT,
  MEMORY_NODE_WIDTH,
  PLUGIN_NODE_HEIGHT,
  PLUGIN_NODE_WIDTH,
  pluginNodeCenter,
  SKILL_ORBIT_RADIUS,
  WORLD_ADDRESS_HEIGHT,
  WORLD_ADDRESS_WIDTH,
  WORLD_ADDRESS_X,
  WORLD_KIND_CLUSTER_GAP,
  WORLD_KIND_HEIGHT,
  WORLD_KIND_WIDTH,
  WORLD_KIND_X,
  WORLD_PORT_GAP,
  WORLD_PORT_SIZE,
} from "@/features/constructor/types/constructor";
import SkillDetailGlyph from "@/features/skills/components/SkillDetailGlyph.vue";
import SkillFacetCards from "@/features/skills/components/SkillFacetCards.vue";
import { useSkills } from "@/features/skills/composables/useSkills";
import {
  layoutSkillColumn,
  layoutSkillHubPose,
  SKILL_LABEL_TYPE,
  SKILL_SAT_SIZE,
  skillOrbitItem,
  type SkillOrbitId,
} from "@/features/skills/utils/skillOrbit";
import PluginDetailGlyph from "@/features/tools/components/PluginDetailGlyph.vue";
import PluginFacetCards from "@/features/tools/components/PluginFacetCards.vue";
import { getToolDefinition } from "@/features/tools/registry/builtinTools";
import { fetchCredentials, type ToolCredential } from "@/features/tools/services/credentialsApi";
import { useTools } from "@/features/tools/composables/useTools";
import {
  layoutPluginColumn,
  layoutPluginHubPose,
  PLUGIN_LABEL_TYPE,
  PLUGIN_SAT_SIZE,
  pluginOrbitItem,
  type PluginOrbitId,
} from "@/features/tools/utils/pluginOrbit";
import type { Project } from "@/features/projects/types/project";
import {
  readProjectQuestions,
  writeProjectQuestions,
  type ProjectQuestion,
} from "@/features/projects/utils/projectQuestions";
import { skillPath } from "@/router/paths";
import { SSH_COMMANDS_TOOL_ID } from "@/features/tools/utils/sshLibrary";
import { handoffSeat, useDeskMotion } from "@/features/projects/motion";
import {
  DESK_ASIDE_MS,
  DESK_EASE,
  DESK_EASE_OPEN,
  DESK_MOVE_MS,
} from "@/features/projects/utils/deskMotion";

const props = withDefaults(
  defineProps<{
    agentSlug: string;
    bootPan?: { x: number; y: number } | null;
    satellitesVisible?: boolean;
    clearBackdrop?: boolean;
    hubVisible?: boolean;
    glyphScale?: number;
    glide?: boolean;
    glideEase?: string;
    glideMs?: number;
    glideDelay?: number;
    glideTo?: { x: number; y: number } | null;
    /** Move the hidden canvas here once the icon has arrived, before satellites appear. */
    worldAt?: { x: number; y: number } | null;
    showMeta?: boolean;
    project?: Project | null;
  }>(),
  {
    bootPan: null,
    satellitesVisible: true,
    clearBackdrop: false,
    hubVisible: true,
    glyphScale: 1,
    glide: false,
    glideDelay: 0,
    glideTo: null,
    worldAt: null,
    showMeta: true,
    project: null,
  },
);

const emit = defineEmits<{
  ready: [];
}>();

const router = useRouter();
const { updateInstance } = useTools();
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
const agentPhase = ref<AgentHubPhase>("circle");
const viewport = ref({ panX: 0, panY: 0, zoom: 1 });
const canvasRef = useTemplateRef<InstanceType<typeof InfiniteCanvas>>("canvas");
const embedded = ref(props.bootPan != null);
const hubPan = ref(props.bootPan ?? { x: 0, y: 0 });
const credentials = ref<ToolCredential[]>([]);
const credentialsReady = ref(false);
const rootEl = useTemplateRef<HTMLElement>("constructorRoot");

type ChannelStage = "agent" | "entering" | "channel" | "leaving";
type MemoryStage = "agent" | "entering" | "memory" | "leaving";
type PluginStage = "agent" | "entering" | "plugin" | "leaving";
type SkillStage = "agent" | "entering" | "skill" | "leaving";
interface FlightPose {
  x: number;
  y: number;
  width: number;
  height: number;
  scale: number;
}

const channelStage = ref<ChannelStage>("agent");
const channelToolId = ref<string | null>(null);
const channelParked = ref(false);
const liftedChannelId = ref<string | null>(null);
const channelSatellites = ref(false);
const channelAside = ref(false);
const flight = ref<FlightPose | null>(null);
const flightGlide = ref(false);
const flightEase = ref(DESK_EASE_OPEN);
const layoutScale = ref(1);
const {
  beginPass: beginChannelPass,
  isCurrent: isChannelPass,
  cancelPasses: cancelChannelPasses,
  wait,
  frame,
  reducedMotion,
} = useDeskMotion();

/** Memory desk mode: memory card → center; facets on a circle. */
const memoryStage = ref<MemoryStage>("agent");
const memoryParked = ref(false);
const liftedMemory = ref(false);
const memorySatellites = ref(false);
const memoryFlight = ref<FlightPose | null>(null);
const memoryFlightGlide = ref(false);
const memoryFlightEase = ref(DESK_EASE_OPEN);
const memoryLayoutScale = ref(1);
/** Facet layer: selected shelf → center; others collapse into memory; cards on the right. */
const memoryFacetId = ref<MemoryOrbitId | null>(null);
const memoryFacetStage = ref<"closed" | "entering" | "open" | "leaving">("closed");
const memoryAside = ref(false);
const liftedMemoryFacet = ref<MemoryOrbitId | null>(null);
const memoryFacetPose = ref<FlightPose | null>(null);
const memoryFacetGlide = ref(false);
const memoryFacetEase = ref(DESK_EASE_OPEN);
const memoryFacetCardsShown = ref(false);
const {
  beginPass: beginMemoryPass,
  isCurrent: isMemoryPass,
  cancelPasses: cancelMemoryPasses,
} = useDeskMotion();
const {
  beginPass: beginMemoryFacetPass,
  isCurrent: isMemoryFacetPass,
  cancelPasses: cancelMemoryFacetPasses,
} = useDeskMotion();

/** Plugin desk mode: instance card → center; detail facets on a circle. */
const pluginStage = ref<PluginStage>("agent");
const pluginParked = ref(false);
const liftedPluginId = ref<string | null>(null);
const pluginSatellites = ref(false);
const pluginFlight = ref<FlightPose | null>(null);
const pluginFlightGlide = ref(false);
const pluginFlightEase = ref(DESK_EASE_OPEN);
/** Facet layer: detail icon → center; others collapse into plugin; right = gradient blur. */
const pluginFacetId = ref<PluginOrbitId | null>(null);
const pluginFacetStage = ref<"closed" | "entering" | "open" | "leaving">("closed");
const pluginAside = ref(false);
const liftedPluginFacet = ref<PluginOrbitId | null>(null);
const pluginFacetPose = ref<FlightPose | null>(null);
const pluginFacetGlide = ref(false);
const pluginFacetEase = ref(DESK_EASE_OPEN);
const pluginFacetShown = ref(false);
/** After seat lands, flyer paints at opacity 0 until drop (no double-composite blink). */
const pluginFacetHandoff = ref(false);
const {
  beginPass: beginPluginPass,
  isCurrent: isPluginPass,
  cancelPasses: cancelPluginPasses,
} = useDeskMotion();
const {
  beginPass: beginPluginFacetPass,
  isCurrent: isPluginFacetPass,
  cancelPasses: cancelPluginFacetPasses,
} = useDeskMotion();

/** Skill desk mode: skill card → left hub; detail facets in a vertical column (same as plugin). */
const skillStage = ref<SkillStage>("agent");
const skillParked = ref(false);
const liftedSkillId = ref<string | null>(null);
const selectedSkillId = ref<string | null>(null);
const skillSatellites = ref(false);
const skillFlight = ref<FlightPose | null>(null);
const skillFlightGlide = ref(false);
const skillFlightEase = ref(DESK_EASE_OPEN);
/** Canvas seat pose captured on enter — leave lands here (no remasure drift / ring). */
const skillHomePose = ref<FlightPose | null>(null);
const skillFacetId = ref<SkillOrbitId | null>(null);
const skillFacetStage = ref<"closed" | "entering" | "open" | "leaving">("closed");
const skillAside = ref(false);
const liftedSkillFacet = ref<SkillOrbitId | null>(null);
const skillFacetPose = ref<FlightPose | null>(null);
const skillFacetGlide = ref(false);
const skillFacetEase = ref(DESK_EASE_OPEN);
const skillFacetShown = ref(false);
const skillFacetHandoff = ref(false);
const {
  beginPass: beginSkillPass,
  isCurrent: isSkillPass,
  cancelPasses: cancelSkillPasses,
} = useDeskMotion();
const {
  beginPass: beginSkillFacetPass,
  isCurrent: isSkillFacetPass,
  cancelPasses: cancelSkillFacetPasses,
} = useDeskMotion();

const deskParked = computed(
  () =>
    channelParked.value || memoryParked.value || pluginParked.value || skillParked.value,
);

const PROJECT_ACTION_SIZE = 64;
const PROJECT_ACTIONS = [
  { id: "questions", label: "Вопросы по проекту", caption: "Вопросы" },
  { id: "name", label: "Имя канала", caption: "Имя" },
  { id: "more", label: "Остальное по каналу", caption: "Ещё" },
] as const;
type ProjectLayerId = (typeof PROJECT_ACTIONS)[number]["id"];

const projectLayer = ref<ProjectLayerId | null>(null);
const projectLayerStage = ref<"closed" | "entering" | "open" | "leaving">("closed");
const liftedAction = ref<ProjectLayerId | null>(null);
const layerSatellites = ref(false);
const layerGlide = ref(false);
const layerEase = ref(DESK_EASE_OPEN);
const layerPose = ref<{ x: number; y: number; width: number; height: number; scale: number } | null>(null);
const addressLayerId = ref<string | null>(null);
const pendingAddressId = ref<string | null>(null);
const questions = ref<ProjectQuestion[]>([]);
const nameDraft = ref("");
const nameError = ref<string | null>(null);
const nameField = useTemplateRef<HTMLInputElement>("nameField");
const {
  beginPass: beginLayerPass,
  isCurrent: isLayerPass,
  cancelPasses: cancelLayerPasses,
} = useDeskMotion();

const channelFaceOpen = computed(
  () => channelStage.value === "channel" && channelSatellites.value && !channelAside.value,
);

/** Action icons stay clickable in channel mode, including while a layer / connection view is open. */
const channelActionsOpen = computed(
  () => channelStage.value === "channel" && channelSatellites.value,
);

const agent = computed(() => {
  const current = getAgentBySlug(props.agentSlug);
  if (!current) return null;
  const project = props.project;
  if (
    project &&
    current.kind === "runtime" &&
    project.runtimeAgentSlug === current.slug &&
    project.name &&
    current.name !== project.name
  ) {
    return { ...current, name: project.name };
  }
  return current;
});

const selectedKindLink = computed(() => {
  if (!selectedKindToolId.value) return null;
  return linkStatus(selectedKindToolId.value);
});

const selectedPluginLink = computed(() =>
  selectedPluginId.value ? pluginStatus(selectedPluginId.value) : null,
);

const sshConstructorOpen = computed(() => {
  const instanceId = selectedPluginId.value;
  if (!instanceId || agentPhase.value === "details") return false;
  return agent.value?.tools.some(
    (tool) => tool.id === instanceId && tool.toolId === SSH_COMMANDS_TOOL_ID,
  );
});

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
  nodes.value.map((node) => {
    const skill = getSkill(props.agentSlug, node.skillId);
    return {
      ...node,
      name: skill?.name ?? node.skillId,
      // Same subtitle as the skill-mode flyer — seat handoff stays continuous.
      role: skill?.systemRole ? "системный" : "навык",
    };
  }),
);

const selectedSkill = computed(() => {
  const modeId = selectedSkillId.value;
  if (modeId) return getSkill(props.agentSlug, modeId) ?? null;
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
    const instance =
      agent.value?.tools.find((item) => item.toolId === tool.id && item.enabled) ??
      agent.value?.tools.find((item) => item.toolId === tool.id);
    return {
      toolId: tool.id,
      name: instance?.name.trim() || tool.name,
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
  // Keep mode ids while constructor modes are open — facet cards mount on them.
  if (pluginStage.value === "agent") {
    selectedPluginId.value = null;
  }
  if (skillStage.value === "agent") {
    selectedSkillId.value = null;
  }
}

function openPicker() {
  pickerOpen.value = true;
}

function closeKindConnector() {
  selectedKindToolId.value = null;
}

function closeAddressConfig() {
  selectedAddressId.value = null;
}

function openPlugin(instanceId: string) {
  if (pluginStage.value !== "agent") {
    selectedPluginId.value = instanceId;
    return;
  }
  clearSelection();
  selectedPluginId.value = instanceId;
  if (agentPhase.value !== "details") agentPhase.value = "circle";
  const instance = agent.value?.tools.find((item) => item.id === instanceId);
  if (instance?.toolId === SSH_COMMANDS_TOOL_ID) return;
  if (channelStage.value !== "agent") resetChannel();
  if (memoryStage.value !== "agent") resetMemory();
  if (skillStage.value !== "agent") resetSkill();
  void enterPlugin(instanceId);
}

function closePlugin() {
  if (pluginStage.value !== "agent") {
    void leavePlugin();
    return;
  }
  selectedPluginId.value = null;
}

function openMemory() {
  if (memoryStage.value !== "agent") return;
  clearSelection();
  if (agentPhase.value !== "details") agentPhase.value = "circle";
  if (channelStage.value !== "agent") resetChannel();
  if (pluginStage.value !== "agent") resetPlugin();
  if (skillStage.value !== "agent") resetSkill();
  void enterMemory();
}

function openSkill(skillId: string) {
  if (skillStage.value !== "agent") {
    selectedSkillId.value = skillId;
    return;
  }
  clearSelection();
  if (agentPhase.value !== "details") agentPhase.value = "circle";
  if (channelStage.value !== "agent") resetChannel();
  if (memoryStage.value !== "agent") resetMemory();
  if (pluginStage.value !== "agent") resetPlugin();
  // enterSkill measures the seat before applying selection ring / lift.
  void enterSkill(skillId);
}

function closeMemory() {
  void leaveMemory();
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
  openSkill(skillId);
}

function onSelectSkill(skillId: string) {
  pickerOpen.value = false;
  const node = placeSkill(skillId);
  if (!node) return;
  openSkill(skillId);
}

async function onCreateSkill() {
  pickerOpen.value = false;
  const skill = createSkill(props.agentSlug);
  if (!skill) return;
  const node = placeSkill(skill.id);
  if (node) {
    openSkill(skill.id);
    return;
  }
  await router.push(skillPath(props.agentSlug, skill.id));
}

function onSelectNode(nodeId: string) {
  const node = nodes.value.find((item) => item.id === nodeId);
  if (!node) return;
  openSkill(node.skillId);
}

function onClearSelection() {
  // Skill / plugin modes leave only via Escape / back — not empty click.
  if (skillStage.value !== "agent") return;
  if (pluginStage.value !== "agent") return;
  if (memoryStage.value !== "agent") {
    if (memoryFacetId.value) {
      void leaveMemoryFacet();
      return;
    }
    void leaveMemory();
    return;
  }
  if (channelStage.value !== "agent") {
    if (addressLayerId.value || projectLayer.value) {
      leaveCurrentLayer();
      return;
    }
    void leaveChannel();
    return;
  }
  clearSelection();
  if (agentPhase.value === "card") agentPhase.value = "circle";
}

function onViewport(payload: { panX: number; panY: number; zoom: number }) {
  viewport.value = payload;
}

watch(
  () => props.bootPan,
  (point) => {
    if (!point) return;
    embedded.value = true;
    hubPan.value = { x: point.x, y: point.y };
    canvasRef.value?.setPan(point.x, point.y);
  },
);

watch(
  () => props.glideTo,
  (target) => {
    if (!target) return;
    embedded.value = true;
    hubPan.value = { x: target.x, y: target.y };
    canvasRef.value?.setPan(target.x, target.y);
  },
);

watch(
  () => props.worldAt,
  async (target) => {
    if (!target) return;
    canvasRef.value?.setPan(target.x, target.y);
    await nextTick();
    embedded.value = false;
  },
);

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
  if (skillStage.value !== "agent") resetSkill();
}

function onInsertKind(toolId: string) {
  const result = connectKind(toolId);
  if (result.ok) kindCatalogOpen.value = false;
}

function onSelectKind(toolId: string) {
  if (channelStage.value !== "agent") return;
  void enterChannel(toolId);
}

function onDisconnectKind(toolId: string) {
  const name = worldTools.value.find((tool) => tool.id === toolId)?.name ?? toolId;
  if (!confirm(`Отключить канал «${name}»?`)) return;
  if (channelToolId.value === toolId) resetChannel();
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
  if (!address) return;
  if (channelStage.value === "channel" && channelToolId.value === toolId) {
    void enterAddressLayer(address.id);
    return;
  }
  pendingAddressId.value = address.id;
  void enterChannel(toolId);
}

function onSelectAddress(addressId: string) {
  const address = getAddress(addressId);
  if (!address) return;
  if (
    channelStage.value === "channel" &&
    channelToolId.value === address.toolId &&
    !projectLayer.value &&
    !addressLayerId.value
  ) {
    void enterAddressLayer(addressId);
    return;
  }
  if (channelStage.value === "agent") {
    pendingAddressId.value = addressId;
    void enterChannel(address.toolId);
  }
}

function onRemoveAddress(addressId: string) {
  const name = getAddress(addressId)?.name ?? "адрес";
  if (!confirm(`Удалить адрес «${name}»?`)) return;
  removeAddress(addressId);
  if (selectedAddressId.value === addressId) closeAddressConfig();
  if (addressLayerId.value === addressId) resetProjectLayer();
}

function onUpdateAddress(
  patch: { name?: string; credentialId?: string; config?: Record<string, unknown> },
) {
  const addressId = addressLayerId.value ?? selectedAddressId.value;
  if (!addressId) return;
  updateAddress(addressId, patch);
}

const channelKind = computed(() =>
  canvasWorldKinds.value.find((kind) => kind.toolId === channelToolId.value) ?? null,
);

const channelAddresses = computed(() =>
  canvasWorldAddresses.value.filter((item) => item.toolId === channelToolId.value),
);

const channelLayout = computed(() => {
  const pose = flight.value;
  const addresses = channelAddresses.value;
  if (!pose) return { port: null, cards: [], empty: null };
  const visualW = pose.width * layoutScale.value;
  const portLeft = -visualW / 2 - WORLD_PORT_GAP - WORLD_PORT_SIZE;
  const port = {
    left: `${portLeft}px`,
    top: `${-WORLD_PORT_SIZE / 2}px`,
    width: `${WORLD_PORT_SIZE}px`,
    height: `${WORLD_PORT_SIZE}px`,
  };
  const gap = 12;
  const rows = Math.max(addresses.length, 1);
  const total = rows * WORLD_ADDRESS_HEIGHT + (rows - 1) * gap;
  const columnLeft = portLeft - 16 - WORLD_ADDRESS_WIDTH;
  const cards = addresses.map((address, index) => ({
    id: address.id,
    name: address.name,
    status: address.status,
    reason: address.reason,
    style: {
      left: `${columnLeft}px`,
      top: `${-total / 2 + index * (WORLD_ADDRESS_HEIGHT + gap)}px`,
      width: `${WORLD_ADDRESS_WIDTH}px`,
      height: `${WORLD_ADDRESS_HEIGHT}px`,
    },
  }));
  const empty = addresses.length
    ? null
    : {
        left: `${columnLeft}px`,
        top: `${-WORLD_ADDRESS_HEIGHT / 2}px`,
        width: `${WORLD_ADDRESS_WIDTH}px`,
      };
  return { port, cards, empty };
});

const channelSpreadStyle = computed(() => {
  const shown = channelSatellites.value;
  const ease = shown ? DESK_EASE_OPEN : DESK_EASE;
  return {
    left: "0px",
    top: "0px",
    width: "0px",
    height: "0px",
    transform: shown ? "scale(1)" : "scale(0)",
    opacity: !shown ? "0" : channelAside.value ? "0.3" : "1",
    transformOrigin: "0 0",
    transition: reducedMotion()
      ? "none"
      : `transform ${DESK_MOVE_MS}ms ${ease}, opacity ${Math.round(DESK_MOVE_MS * 0.55)}ms ease`,
  };
});

const flightStyle = computed(() => {
  const pose = flight.value;
  if (!pose) return {};
  const glide = flightGlide.value && !reducedMotion();
  const move = glide
    ? `left ${DESK_MOVE_MS}ms ${flightEase.value}, top ${DESK_MOVE_MS}ms ${flightEase.value}`
    : "none";
  return {
    left: `${pose.x + pose.width / 2}px`,
    top: `${pose.y + pose.height / 2}px`,
    zIndex: "25",
    transition: move,
  };
});

const cardBoxStyle = computed(() => {
  const pose = flight.value;
  if (!pose) return {};
  const glide = flightGlide.value && !reducedMotion();
  return {
    left: `${-pose.width / 2}px`,
    top: `${-pose.height / 2}px`,
    width: `${pose.width}px`,
    height: `${pose.height}px`,
    transform: `scale(${pose.scale})`,
    transformOrigin: "center center",
    opacity: channelAside.value ? "0" : "1",
    transition: [
      glide ? `transform ${DESK_MOVE_MS}ms ${flightEase.value}` : "",
      reducedMotion() ? "" : `opacity ${DESK_ASIDE_MS}ms ease`,
    ]
      .filter(Boolean)
      .join(", ") || "none",
  };
});

const disconnectStyle = computed(() => {
  const pose = flight.value;
  if (!pose) return { display: "none" };
  const visualH = pose.height * layoutScale.value;
  return {
    left: "0px",
    top: `${visualH / 2 + 8}px`,
    transform: "translateX(-50%)",
  };
});

const backButtonClass =
  "btn absolute top-4 left-[12.75rem] z-40 h-11 border border-base-300/60 bg-base-100/90 shadow-lg backdrop-blur-sm transition-opacity motion-reduce:transition-none";

function centerPose(from: FlightPose): FlightPose {
  const width = rootEl.value?.clientWidth ?? 0;
  const height = rootEl.value?.clientHeight ?? 0;
  const scale = from.height > 0 ? AGENT_SIZE / from.height : 1;
  return {
    x: width / 2 - from.width / 2,
    y: height / 2 - from.height / 2,
    width: from.width,
    height: from.height,
    scale,
  };
}
function cardPose(toolId: string): FlightPose | null {
  const root = rootEl.value;
  if (!root) return null;
  const card = root.querySelector(`[data-channel="${CSS.escape(toolId)}"]`);
  if (!(card instanceof HTMLElement)) return null;
  const rootBox = root.getBoundingClientRect();
  const box = card.getBoundingClientRect();
  if (box.width < 1 || box.height < 1) return null;
  return {
    x: box.left - rootBox.left,
    y: box.top - rootBox.top,
    width: box.width,
    height: box.height,
    scale: 1,
  };
}

function borderClass(status: string): string {
  if (status === "green") return "border-success";
  if (status === "yellow") return "border-warning";
  if (status === "red") return "border-error";
  return "border-base-300";
}

function resetChannel() {
  cancelChannelPasses();
  channelStage.value = "agent";
  channelToolId.value = null;
  channelParked.value = false;
  liftedChannelId.value = null;
  channelSatellites.value = false;
  flight.value = null;
  flightGlide.value = false;
  layoutScale.value = 1;
  resetProjectLayer();
}

function resetMemoryFacet() {
  cancelMemoryFacetPasses();
  memoryFacetId.value = null;
  memoryFacetStage.value = "closed";
  memoryAside.value = false;
  liftedMemoryFacet.value = null;
  memoryFacetPose.value = null;
  memoryFacetGlide.value = false;
  memoryFacetCardsShown.value = false;
}

function resetMemory() {
  cancelMemoryPasses();
  resetMemoryFacet();
  memoryStage.value = "agent";
  memoryParked.value = false;
  liftedMemory.value = false;
  memorySatellites.value = false;
  memoryFlight.value = null;
  memoryFlightGlide.value = false;
  memoryLayoutScale.value = 1;
}

function resetPluginFacet() {
  cancelPluginFacetPasses();
  pluginFacetId.value = null;
  pluginFacetStage.value = "closed";
  pluginAside.value = false;
  liftedPluginFacet.value = null;
  pluginFacetPose.value = null;
  pluginFacetGlide.value = false;
  pluginFacetShown.value = false;
  pluginFacetHandoff.value = false;
}

function resetPlugin() {
  cancelPluginPasses();
  resetPluginFacet();
  pluginStage.value = "agent";
  pluginParked.value = false;
  liftedPluginId.value = null;
  pluginSatellites.value = false;
  pluginFlight.value = null;
  pluginFlightGlide.value = false;
  selectedPluginId.value = null;
}

function resetSkillFacet() {
  cancelSkillFacetPasses();
  skillFacetId.value = null;
  skillFacetStage.value = "closed";
  skillAside.value = false;
  liftedSkillFacet.value = null;
  skillFacetPose.value = null;
  skillFacetGlide.value = false;
  skillFacetShown.value = false;
  skillFacetHandoff.value = false;
}

function resetSkill() {
  cancelSkillPasses();
  resetSkillFacet();
  skillStage.value = "agent";
  skillParked.value = false;
  liftedSkillId.value = null;
  skillSatellites.value = false;
  skillFlight.value = null;
  skillFlightGlide.value = false;
  skillHomePose.value = null;
  selectedSkillId.value = null;
}

function memoryCardPose(): FlightPose | null {
  const root = rootEl.value;
  if (!root) return null;
  const card = root.querySelector("[data-memory-card]");
  if (!(card instanceof HTMLElement)) return null;
  const rootBox = root.getBoundingClientRect();
  const box = card.getBoundingClientRect();
  if (box.width < 1 || box.height < 1) return null;
  return {
    x: box.left - rootBox.left,
    y: box.top - rootBox.top,
    width: box.width,
    height: box.height,
    scale: 1,
  };
}

function centerMemoryPose(from: FlightPose): FlightPose {
  const width = rootEl.value?.clientWidth ?? 0;
  const height = rootEl.value?.clientHeight ?? 0;
  const scale = from.height > 0 ? AGENT_SIZE / from.height : 1;
  return {
    x: width / 2 - from.width / 2,
    y: height / 2 - from.height / 2,
    width: from.width,
    height: from.height,
    scale,
  };
}

async function enterMemory() {
  if (memoryStage.value !== "agent") return;
  const token = beginMemoryPass();
  const start = memoryCardPose();
  memoryStage.value = "entering";
  memorySatellites.value = false;
  memoryFlightGlide.value = false;
  memoryFlightEase.value = DESK_EASE_OPEN;
  resetMemoryFacet();
  memoryLayoutScale.value = start && start.height > 0 ? AGENT_SIZE / start.height : 1;

  if (reducedMotion() || !start) {
    const pose = start ?? {
      x: 0,
      y: 0,
      width: MEMORY_NODE_WIDTH,
      height: MEMORY_NODE_HEIGHT,
      scale: 1,
    };
    memoryParked.value = true;
    liftedMemory.value = true;
    memoryFlight.value = centerMemoryPose(pose);
    memorySatellites.value = true;
    memoryStage.value = "memory";
    return;
  }

  memoryFlight.value = start;
  await nextTick();
  await frame();
  await frame();
  if (!isMemoryPass(token)) return;
  liftedMemory.value = true;
  memoryParked.value = true;
  memoryFlightGlide.value = true;
  memoryFlight.value = centerMemoryPose(start);
  memorySatellites.value = true;
  await wait(DESK_MOVE_MS);
  if (!isMemoryPass(token)) return;
  memoryFlightGlide.value = false;
  memoryStage.value = "memory";
}

async function leaveMemory() {
  if (memoryStage.value === "agent" || memoryStage.value === "leaving") return;
  if (memoryFacetId.value) {
    await leaveMemoryFacet();
    if (memoryFacetId.value) return;
  }
  const token = beginMemoryPass();
  if (reducedMotion() || !memoryFlight.value) {
    resetMemory();
    return;
  }
  memoryStage.value = "leaving";
  memorySatellites.value = false;
  memoryParked.value = false;
  memoryFlightEase.value = DESK_EASE;
  memoryFlightGlide.value = true;
  await nextTick();
  await frame();
  if (!isMemoryPass(token)) return;
  const slot = memoryCardPose();
  if (slot) memoryFlight.value = slot;
  await wait(DESK_MOVE_MS);
  if (!isMemoryPass(token)) return;
  liftedMemory.value = false;
  memoryFlight.value = null;
  memoryFlightGlide.value = false;
  memoryStage.value = "agent";
}

function pluginCardPose(instanceId: string): FlightPose | null {
  const root = rootEl.value;
  if (!root) return null;
  const card = root.querySelector(`[data-plugin="${CSS.escape(instanceId)}"]`);
  if (!(card instanceof HTMLElement)) return null;
  const rootBox = root.getBoundingClientRect();
  const box = card.getBoundingClientRect();
  if (box.width < 1 || box.height < 1) return null;
  return {
    x: box.left - rootBox.left,
    y: box.top - rootBox.top,
    width: box.width,
    height: box.height,
    scale: 1,
  };
}

function centerPluginPose(from: FlightPose): FlightPose {
  const width = rootEl.value?.clientWidth ?? 0;
  const height = rootEl.value?.clientHeight ?? 0;
  return layoutPluginHubPose({ width, height }, from);
}

async function enterPlugin(instanceId: string) {
  if (pluginStage.value !== "agent") return;
  const token = beginPluginPass();
  const start = pluginCardPose(instanceId);
  pluginStage.value = "entering";
  pluginSatellites.value = false;
  pluginFacetId.value = null;
  pluginFlightGlide.value = false;
  pluginFlightEase.value = DESK_EASE_OPEN;
  selectedPluginId.value = instanceId;

  if (reducedMotion() || !start) {
    const pose = start ?? {
      x: 0,
      y: 0,
      width: PLUGIN_NODE_WIDTH,
      height: PLUGIN_NODE_HEIGHT,
      scale: 1,
    };
    pluginParked.value = true;
    liftedPluginId.value = instanceId;
    pluginFlight.value = centerPluginPose(pose);
    pluginSatellites.value = true;
    pluginStage.value = "plugin";
    return;
  }

  pluginFlight.value = start;
  await nextTick();
  await frame();
  await frame();
  if (!isPluginPass(token)) return;
  liftedPluginId.value = instanceId;
  pluginParked.value = true;
  pluginFlightGlide.value = true;
  pluginFlight.value = centerPluginPose(start);
  pluginSatellites.value = true;
  await wait(DESK_MOVE_MS);
  if (!isPluginPass(token)) return;
  pluginFlightGlide.value = false;
  pluginStage.value = "plugin";
}

async function leavePlugin() {
  if (pluginStage.value === "agent" || pluginStage.value === "leaving") return;
  if (pluginFacetId.value) {
    await leavePluginFacet();
    if (pluginFacetId.value) return;
  }
  const token = beginPluginPass();
  if (reducedMotion() || !pluginFlight.value || !selectedPluginId.value) {
    resetPlugin();
    return;
  }
  const instanceId = selectedPluginId.value;
  pluginStage.value = "leaving";
  pluginSatellites.value = false;
  pluginParked.value = false;
  pluginFlightEase.value = DESK_EASE;
  pluginFlightGlide.value = true;
  await nextTick();
  await frame();
  if (!isPluginPass(token)) return;
  const slot = pluginCardPose(instanceId);
  if (slot) pluginFlight.value = slot;
  await wait(DESK_MOVE_MS);
  if (!isPluginPass(token)) return;
  liftedPluginId.value = null;
  pluginFlight.value = null;
  pluginFlightGlide.value = false;
  pluginStage.value = "agent";
  selectedPluginId.value = null;
}

const pluginOrbitTypeDef = computed(() => {
  const instance = selectedPluginId.value
    ? agent.value?.tools.find((item) => item.id === selectedPluginId.value)
    : null;
  return instance ? getToolDefinition(instance.toolId) : undefined;
});

const pluginOrbitSlots = computed(() => {
  const width = rootEl.value?.clientWidth ?? 0;
  const height = rootEl.value?.clientHeight ?? 0;
  return layoutPluginColumn({ x: width / 2, y: height / 2 }, { width, height }, pluginOrbitTypeDef.value);
});

const pluginCenterMeta = computed(() => {
  const instance = selectedPluginId.value
    ? agent.value?.tools.find((item) => item.id === selectedPluginId.value)
    : null;
  if (!instance) return { name: "Плагин", typeId: "" };
  return { name: instance.name || instance.id, typeId: instance.toolId };
});

const pluginFaceOpen = computed(
  () =>
    pluginStage.value === "plugin" &&
    pluginSatellites.value &&
    !pluginAside.value &&
    pluginFacetStage.value === "closed",
);

const pluginFlightStyle = computed(() => {
  const pose = pluginFlight.value;
  if (!pose) return {};
  const glide = pluginFlightGlide.value && !reducedMotion();
  const move = glide
    ? `left ${DESK_MOVE_MS}ms ${pluginFlightEase.value}, top ${DESK_MOVE_MS}ms ${pluginFlightEase.value}`
    : "none";
  return {
    left: `${pose.x + pose.width / 2}px`,
    top: `${pose.y + pose.height / 2}px`,
    zIndex: "25",
    transition: move,
  };
});

const pluginCardBoxStyle = computed(() => {
  const pose = pluginFlight.value;
  if (!pose) return {};
  const glide = pluginFlightGlide.value && !reducedMotion();
  return {
    left: `${-pose.width / 2}px`,
    top: `${-pose.height / 2}px`,
    width: `${pose.width}px`,
    height: `${pose.height}px`,
    transform: `scale(${pose.scale})`,
    transformOrigin: "center center",
    // Plugin stays as the pocket other satellites collapse into; dims when a facet is open.
    opacity: pluginAside.value ? "0.35" : "1",
    transition: [
      glide ? `transform ${DESK_MOVE_MS}ms ${pluginFlightEase.value}` : "",
      reducedMotion() ? "" : `opacity ${DESK_ASIDE_MS}ms ease`,
    ]
      .filter(Boolean)
      .join(", ") || "none",
  };
});

const pluginSpreadStyle = computed(() => {
  const shown = pluginSatellites.value && !pluginAside.value;
  const ease = shown ? DESK_EASE_OPEN : DESK_EASE;
  return {
    left: "0px",
    top: "0px",
    width: "0px",
    height: "0px",
    transform: shown ? "scale(1)" : "scale(0)",
    opacity: shown ? "1" : "0",
    transformOrigin: "0 0",
    transition: reducedMotion()
      ? "none"
      : `transform ${DESK_MOVE_MS}ms ${ease}, opacity ${Math.round(DESK_MOVE_MS * 0.55)}ms ease`,
  };
});

function pluginFlightOrigin(): { x: number; y: number } {
  const pose = pluginFlight.value;
  const width = rootEl.value?.clientWidth ?? 0;
  const height = rootEl.value?.clientHeight ?? 0;
  if (pose) {
    return { x: pose.x + pose.width / 2, y: pose.y + pose.height / 2 };
  }
  return { x: width / 2, y: height / 2 };
}

function pluginSatStyle(slot: { x: number; y: number; id: PluginOrbitId }) {
  const lifted = liftedPluginFacet.value === slot.id;
  const origin = pluginFlightOrigin();
  return {
    left: `${slot.x - origin.x}px`,
    top: `${slot.y - origin.y}px`,
    height: `${PLUGIN_SAT_SIZE}px`,
    // Handoff invariant: seat opacity snaps — never fade on land/drop (end blink).
    opacity: lifted ? 0 : 1,
    transition: "none",
  };
}

function pluginFacetHome(id: PluginOrbitId): FlightPose {
  const width = rootEl.value?.clientWidth ?? 0;
  const height = rootEl.value?.clientHeight ?? 0;
  const origin = pluginFlightOrigin();
  const slot = layoutPluginColumn(
    { x: width / 2, y: height / 2 },
    { width, height },
    pluginOrbitTypeDef.value,
  ).find((item) => item.id === id);
  return {
    x: (slot?.x ?? origin.x - PLUGIN_SAT_SIZE / 2) - origin.x,
    y: (slot?.y ?? origin.y - PLUGIN_SAT_SIZE / 2) - origin.y,
    width: PLUGIN_SAT_SIZE,
    height: PLUGIN_SAT_SIZE,
    scale: 1,
  };
}

function pluginFacetCenter(_home: FlightPose): FlightPose {
  // Same icon+label row as the list; grow around the icon center into the hub seat.
  const scale = PLUGIN_SAT_SIZE > 0 ? AGENT_SIZE / PLUGIN_SAT_SIZE : 1;
  return {
    x: -PLUGIN_SAT_SIZE / 2,
    y: -PLUGIN_SAT_SIZE / 2,
    width: PLUGIN_SAT_SIZE,
    height: PLUGIN_SAT_SIZE,
    scale,
  };
}

const pluginFacetStyle = computed(() => {
  const pose = pluginFacetPose.value;
  if (!pose) return {};
  const glide = pluginFacetGlide.value && !reducedMotion();
  const ease = pluginFacetEase.value;
  const ox = PLUGIN_SAT_SIZE / 2;
  const oy = PLUGIN_SAT_SIZE / 2;
  return {
    left: `${pose.x}px`,
    top: `${pose.y}px`,
    height: `${pose.height}px`,
    transform: `scale(${pose.scale})`,
    // Pivot on the glyph so the side label stays to the right while scaling.
    transformOrigin: `${ox}px ${oy}px`,
    zIndex: "26",
    // Snap hide when seat lands — never fade the flyer on handoff.
    opacity: pluginFacetHandoff.value ? 0 : 1,
    transition: glide
      ? `left ${DESK_MOVE_MS}ms ${ease}, top ${DESK_MOVE_MS}ms ${ease}, transform ${DESK_MOVE_MS}ms ${ease}`
      : "none",
  };
});

const pluginFacetMeta = computed(() =>
  pluginFacetId.value ? pluginOrbitItem(pluginFacetId.value) : null,
);

async function enterPluginFacet(id: PluginOrbitId) {
  if (pluginStage.value !== "plugin") return;
  if (pluginFacetId.value === id && pluginFacetStage.value === "open") return;
  const token = beginPluginFacetPass();
  const home = pluginFacetHome(id);
  const switching = Boolean(pluginFacetId.value) || pluginAside.value;
  pluginFacetId.value = id;
  pluginFacetStage.value = switching ? "open" : "entering";
  pluginFacetEase.value = DESK_EASE_OPEN;

  if (switching || reducedMotion()) {
    liftedPluginFacet.value = id;
    pluginAside.value = true;
    pluginFacetPose.value = pluginFacetCenter(home);
    pluginFacetShown.value = true;
    pluginFacetGlide.value = false;
    pluginFacetStage.value = "open";
    return;
  }

  pluginFacetShown.value = false;
  pluginFacetGlide.value = false;
  pluginFacetPose.value = home;
  // Hide the list seat as soon as the flyer occupies it (no twin blink).
  liftedPluginFacet.value = id;
  await nextTick();
  await frame();
  await frame();
  if (!isPluginFacetPass(token)) return;
  // One pass: collapse other satellites into plugin, fly focus to hub, reveal right stage.
  pluginAside.value = true;
  pluginFacetGlide.value = true;
  pluginFacetPose.value = pluginFacetCenter(home);
  pluginFacetShown.value = true;
  await wait(DESK_MOVE_MS);
  if (!isPluginFacetPass(token)) return;
  pluginFacetGlide.value = false;
  pluginFacetStage.value = "open";
}

async function leavePluginFacet() {
  if (!pluginFacetId.value || pluginFacetStage.value === "leaving" || pluginFacetStage.value === "closed") {
    return;
  }
  const id = pluginFacetId.value;
  const token = beginPluginFacetPass();
  if (reducedMotion()) {
    resetPluginFacet();
    return;
  }
  pluginFacetStage.value = "leaving";
  pluginFacetShown.value = false;
  pluginAside.value = false;
  pluginFacetEase.value = DESK_EASE;
  pluginFacetGlide.value = true;
  await nextTick();
  await frame();
  if (!isPluginFacetPass(token)) return;
  pluginFacetPose.value = pluginFacetHome(id);
  await wait(DESK_MOVE_MS);
  if (!isPluginFacetPass(token)) return;
  pluginFacetGlide.value = false;
  // Seat handoff: land list row + hide flyer (opacity snap) → next frame → unmount flyer.
  const landed = await handoffSeat({
    land: () => {
      liftedPluginFacet.value = null;
      pluginFacetHandoff.value = true;
    },
    drop: () => {
      pluginFacetPose.value = null;
      pluginFacetHandoff.value = false;
      pluginFacetId.value = null;
      pluginFacetStage.value = "closed";
    },
    token,
    isCurrent: isPluginFacetPass,
  });
  if (!landed) return;
}

function skillCardPose(skillId: string): FlightPose | null {
  const root = rootEl.value;
  if (!root) return null;
  const card = root.querySelector(`[data-skill="${CSS.escape(skillId)}"]`);
  if (!(card instanceof HTMLElement)) return null;
  const rootBox = root.getBoundingClientRect();
  const box = card.getBoundingClientRect();
  if (box.width < 1 || box.height < 1) return null;
  return {
    x: box.left - rootBox.left,
    y: box.top - rootBox.top,
    width: box.width,
    height: box.height,
    scale: 1,
  };
}

function centerSkillPose(from: FlightPose): FlightPose {
  const width = rootEl.value?.clientWidth ?? 0;
  const height = rootEl.value?.clientHeight ?? 0;
  return layoutSkillHubPose({ width, height }, from);
}

async function enterSkill(skillId: string) {
  if (skillStage.value !== "agent") return;
  const token = beginSkillPass();
  // Measure before selection ring so home pose matches the resting seat.
  const start = skillCardPose(skillId);
  skillStage.value = "entering";
  skillSatellites.value = false;
  skillFacetId.value = null;
  skillFlightGlide.value = false;
  skillFlightEase.value = DESK_EASE_OPEN;
  selectedSkillId.value = skillId;
  const node = findNodeBySkillId(skillId);
  if (node) selectedNodeId.value = node.id;

  if (reducedMotion() || !start) {
    const pose = start ?? {
      x: 0,
      y: 0,
      width: DEFAULT_SKILL_NODE_WIDTH,
      height: DEFAULT_SKILL_NODE_HEIGHT,
      scale: 1,
    };
    skillHomePose.value = { ...pose, scale: 1 };
    skillParked.value = true;
    liftedSkillId.value = skillId;
    skillFlight.value = centerSkillPose(pose);
    skillSatellites.value = true;
    skillStage.value = "skill";
    return;
  }

  skillHomePose.value = { ...start, scale: 1 };
  skillFlight.value = start;
  await nextTick();
  await frame();
  await frame();
  if (!isSkillPass(token)) return;
  liftedSkillId.value = skillId;
  skillParked.value = true;
  skillFlightGlide.value = true;
  skillFlight.value = centerSkillPose(start);
  skillSatellites.value = true;
  await wait(DESK_MOVE_MS);
  if (!isSkillPass(token)) return;
  skillFlightGlide.value = false;
  skillStage.value = "skill";
}

async function leaveSkill() {
  if (skillStage.value === "agent" || skillStage.value === "leaving") return;
  if (skillFacetId.value) {
    await leaveSkillFacet();
    if (skillFacetId.value) return;
  }
  const token = beginSkillPass();
  if (reducedMotion() || !skillFlight.value || !selectedSkillId.value) {
    resetSkill();
    selectedNodeId.value = null;
    return;
  }
  const id = selectedSkillId.value;
  skillStage.value = "leaving";
  skillSatellites.value = false;
  skillParked.value = false;
  // Drop selection ring before landing so the seat matches the flyer box.
  selectedNodeId.value = null;
  skillFlightEase.value = DESK_EASE;
  skillFlightGlide.value = true;
  await nextTick();
  await frame();
  if (!isSkillPass(token)) return;
  // Prefer live seat (pan/zoom), fall back to enter home pose.
  const slot = skillCardPose(id) ?? skillHomePose.value;
  if (slot) skillFlight.value = { ...slot, scale: 1 };
  await wait(DESK_MOVE_MS);
  if (!isSkillPass(token)) return;
  skillFlightGlide.value = false;
  // Seat handoff: land canvas seat → next frame → drop flyer (no end blink).
  const landed = await handoffSeat({
    land: () => {
      liftedSkillId.value = null;
    },
    drop: () => {
      skillFlight.value = null;
      skillHomePose.value = null;
      skillStage.value = "agent";
      selectedSkillId.value = null;
    },
    token,
    isCurrent: isSkillPass,
  });
  if (!landed) return;
}

const skillOrbitSlots = computed(() => {
  const width = rootEl.value?.clientWidth ?? 0;
  const height = rootEl.value?.clientHeight ?? 0;
  return layoutSkillColumn({ x: width / 2, y: height / 2 }, { width, height });
});

const skillCenterMeta = computed(() => {
  const skill = selectedSkill.value;
  if (!skill) return { name: "Навык", role: "" };
  return {
    name: skill.name || skill.id,
    role: skill.systemRole ? "системный" : "навык",
  };
});

const skillFaceOpen = computed(
  () =>
    skillStage.value === "skill" &&
    skillSatellites.value &&
    !skillAside.value &&
    skillFacetStage.value === "closed",
);

const skillFlightStyle = computed(() => {
  const pose = skillFlight.value;
  if (!pose) return {};
  const glide = skillFlightGlide.value && !reducedMotion();
  const move = glide
    ? `left ${DESK_MOVE_MS}ms ${skillFlightEase.value}, top ${DESK_MOVE_MS}ms ${skillFlightEase.value}`
    : "none";
  return {
    left: `${pose.x + pose.width / 2}px`,
    top: `${pose.y + pose.height / 2}px`,
    zIndex: "25",
    transition: move,
  };
});

const skillCardBoxStyle = computed(() => {
  const pose = skillFlight.value;
  if (!pose) return {};
  const glide = skillFlightGlide.value && !reducedMotion();
  return {
    left: `${-pose.width / 2}px`,
    top: `${-pose.height / 2}px`,
    width: `${pose.width}px`,
    height: `${pose.height}px`,
    transform: `scale(${pose.scale})`,
    transformOrigin: "center center",
    opacity: skillAside.value ? "0.35" : "1",
    transition: [
      glide ? `transform ${DESK_MOVE_MS}ms ${skillFlightEase.value}` : "",
      reducedMotion() ? "" : `opacity ${DESK_ASIDE_MS}ms ease`,
    ]
      .filter(Boolean)
      .join(", ") || "none",
  };
});

const skillSpreadStyle = computed(() => {
  const shown = skillSatellites.value && !skillAside.value;
  const ease = shown ? DESK_EASE_OPEN : DESK_EASE;
  return {
    left: "0px",
    top: "0px",
    width: "0px",
    height: "0px",
    transform: shown ? "scale(1)" : "scale(0)",
    opacity: shown ? "1" : "0",
    transformOrigin: "0 0",
    transition: reducedMotion()
      ? "none"
      : `transform ${DESK_MOVE_MS}ms ${ease}, opacity ${Math.round(DESK_MOVE_MS * 0.55)}ms ease`,
  };
});

function skillFlightOrigin(): { x: number; y: number } {
  const pose = skillFlight.value;
  const width = rootEl.value?.clientWidth ?? 0;
  const height = rootEl.value?.clientHeight ?? 0;
  if (pose) {
    return { x: pose.x + pose.width / 2, y: pose.y + pose.height / 2 };
  }
  return { x: width / 2, y: height / 2 };
}

function skillSatStyle(slot: { x: number; y: number; id: SkillOrbitId }) {
  const lifted = liftedSkillFacet.value === slot.id;
  const origin = skillFlightOrigin();
  return {
    left: `${slot.x - origin.x}px`,
    top: `${slot.y - origin.y}px`,
    height: `${SKILL_SAT_SIZE}px`,
    // Handoff invariant: seat opacity snaps — never fade on land/drop.
    opacity: lifted ? 0 : 1,
    transition: "none",
  };
}

function skillFacetHome(id: SkillOrbitId): FlightPose {
  const width = rootEl.value?.clientWidth ?? 0;
  const height = rootEl.value?.clientHeight ?? 0;
  const origin = skillFlightOrigin();
  const slot = layoutSkillColumn(
    { x: width / 2, y: height / 2 },
    { width, height },
  ).find((item) => item.id === id);
  return {
    x: (slot?.x ?? origin.x - SKILL_SAT_SIZE / 2) - origin.x,
    y: (slot?.y ?? origin.y - SKILL_SAT_SIZE / 2) - origin.y,
    width: SKILL_SAT_SIZE,
    height: SKILL_SAT_SIZE,
    scale: 1,
  };
}

function skillFacetCenter(_home: FlightPose): FlightPose {
  const scale = SKILL_SAT_SIZE > 0 ? AGENT_SIZE / SKILL_SAT_SIZE : 1;
  return {
    x: -SKILL_SAT_SIZE / 2,
    y: -SKILL_SAT_SIZE / 2,
    width: SKILL_SAT_SIZE,
    height: SKILL_SAT_SIZE,
    scale,
  };
}

const skillFacetStyle = computed(() => {
  const pose = skillFacetPose.value;
  if (!pose) return {};
  const glide = skillFacetGlide.value && !reducedMotion();
  const ease = skillFacetEase.value;
  const ox = SKILL_SAT_SIZE / 2;
  const oy = SKILL_SAT_SIZE / 2;
  return {
    left: `${pose.x}px`,
    top: `${pose.y}px`,
    height: `${pose.height}px`,
    transform: `scale(${pose.scale})`,
    transformOrigin: `${ox}px ${oy}px`,
    zIndex: "26",
    opacity: skillFacetHandoff.value ? 0 : 1,
    transition: glide
      ? `left ${DESK_MOVE_MS}ms ${ease}, top ${DESK_MOVE_MS}ms ${ease}, transform ${DESK_MOVE_MS}ms ${ease}`
      : "none",
  };
});

const skillFacetMeta = computed(() =>
  skillFacetId.value ? skillOrbitItem(skillFacetId.value) : null,
);

async function enterSkillFacet(id: SkillOrbitId) {
  if (skillStage.value !== "skill") return;
  if (skillFacetId.value === id && skillFacetStage.value === "open") return;
  const token = beginSkillFacetPass();
  const home = skillFacetHome(id);
  const switching = Boolean(skillFacetId.value) || skillAside.value;
  skillFacetId.value = id;
  skillFacetStage.value = switching ? "open" : "entering";
  skillFacetEase.value = DESK_EASE_OPEN;

  if (switching || reducedMotion()) {
    liftedSkillFacet.value = id;
    skillAside.value = true;
    skillFacetPose.value = skillFacetCenter(home);
    skillFacetShown.value = true;
    skillFacetGlide.value = false;
    skillFacetStage.value = "open";
    return;
  }

  skillFacetShown.value = false;
  skillFacetGlide.value = false;
  skillFacetPose.value = home;
  liftedSkillFacet.value = id;
  await nextTick();
  await frame();
  await frame();
  if (!isSkillFacetPass(token)) return;
  skillAside.value = true;
  skillFacetGlide.value = true;
  skillFacetPose.value = skillFacetCenter(home);
  skillFacetShown.value = true;
  await wait(DESK_MOVE_MS);
  if (!isSkillFacetPass(token)) return;
  skillFacetGlide.value = false;
  skillFacetStage.value = "open";
}

async function leaveSkillFacet() {
  if (!skillFacetId.value || skillFacetStage.value === "leaving" || skillFacetStage.value === "closed") {
    return;
  }
  const id = skillFacetId.value;
  const token = beginSkillFacetPass();
  if (reducedMotion()) {
    resetSkillFacet();
    return;
  }
  skillFacetStage.value = "leaving";
  skillFacetShown.value = false;
  skillAside.value = false;
  skillFacetEase.value = DESK_EASE;
  skillFacetGlide.value = true;
  await nextTick();
  await frame();
  if (!isSkillFacetPass(token)) return;
  skillFacetPose.value = skillFacetHome(id);
  await wait(DESK_MOVE_MS);
  if (!isSkillFacetPass(token)) return;
  skillFacetGlide.value = false;
  const landed = await handoffSeat({
    land: () => {
      liftedSkillFacet.value = null;
      skillFacetHandoff.value = true;
    },
    drop: () => {
      skillFacetPose.value = null;
      skillFacetHandoff.value = false;
      skillFacetId.value = null;
      skillFacetStage.value = "closed";
    },
    token,
    isCurrent: isSkillFacetPass,
  });
  if (!landed) return;
}

const memoryOrbitSlots = computed(() => {
  const width = rootEl.value?.clientWidth ?? 0;
  const height = rootEl.value?.clientHeight ?? 0;
  return layoutMemoryOrbit({ x: width / 2, y: height / 2 }, { width, height });
});

const memorySkillNames = computed(() =>
  (agent.value?.skills ?? []).map((skill) => ({
    id: skill.id,
    name: skill.name || skill.id,
  })),
);

const memoryFaceOpen = computed(
  () =>
    memoryStage.value === "memory" &&
    memorySatellites.value &&
    !memoryAside.value &&
    memoryFacetStage.value === "closed",
);

const memoryFlightStyle = computed(() => {
  const pose = memoryFlight.value;
  if (!pose) return {};
  const glide = memoryFlightGlide.value && !reducedMotion();
  const move = glide
    ? `left ${DESK_MOVE_MS}ms ${memoryFlightEase.value}, top ${DESK_MOVE_MS}ms ${memoryFlightEase.value}`
    : "none";
  return {
    left: `${pose.x + pose.width / 2}px`,
    top: `${pose.y + pose.height / 2}px`,
    zIndex: "25",
    transition: move,
  };
});

const memoryCardBoxStyle = computed(() => {
  const pose = memoryFlight.value;
  if (!pose) return {};
  const glide = memoryFlightGlide.value && !reducedMotion();
  return {
    left: `${-pose.width / 2}px`,
    top: `${-pose.height / 2}px`,
    width: `${pose.width}px`,
    height: `${pose.height}px`,
    transform: `scale(${pose.scale})`,
    transformOrigin: "center center",
    // Memory stays as the pocket other satellites collapse into; dims when a facet is open.
    opacity: memoryAside.value ? "0.35" : "1",
    transition: [
      glide ? `transform ${DESK_MOVE_MS}ms ${memoryFlightEase.value}` : "",
      reducedMotion() ? "" : `opacity ${DESK_ASIDE_MS}ms ease`,
    ]
      .filter(Boolean)
      .join(", ") || "none",
  };
});

const memorySpreadStyle = computed(() => {
  const shown = memorySatellites.value && !memoryAside.value;
  const ease = shown ? DESK_EASE_OPEN : DESK_EASE;
  return {
    left: "0px",
    top: "0px",
    width: "0px",
    height: "0px",
    transform: shown ? "scale(1)" : "scale(0)",
    opacity: shown ? "1" : "0",
    transformOrigin: "0 0",
    transition: reducedMotion()
      ? "none"
      : `transform ${DESK_MOVE_MS}ms ${ease}, opacity ${Math.round(DESK_MOVE_MS * 0.55)}ms ease`,
  };
});

function memorySatStyle(slot: { x: number; y: number; id: MemoryOrbitId }) {
  const lifted = liftedMemoryFacet.value === slot.id;
  return {
    left: `${slot.x - (rootEl.value?.clientWidth ?? 0) / 2}px`,
    top: `${slot.y - (rootEl.value?.clientHeight ?? 0) / 2}px`,
    width: `${MEMORY_SAT_SIZE}px`,
    height: `${MEMORY_SAT_SIZE}px`,
    opacity: lifted ? 0 : undefined,
    transition: lifted ? "none" : `opacity ${DESK_ASIDE_MS}ms ease`,
  };
}

function memoryFacetHome(id: MemoryOrbitId): FlightPose {
  const width = rootEl.value?.clientWidth ?? 0;
  const height = rootEl.value?.clientHeight ?? 0;
  const slot = layoutMemoryOrbit({ x: width / 2, y: height / 2 }, { width, height }).find(
    (item) => item.id === id,
  );
  return {
    x: (slot?.x ?? width / 2 - MEMORY_SAT_SIZE / 2) - width / 2,
    y: (slot?.y ?? height / 2 - MEMORY_SAT_SIZE / 2) - height / 2,
    width: MEMORY_SAT_SIZE,
    height: MEMORY_SAT_SIZE,
    scale: 1,
  };
}

function memoryFacetCenter(home: FlightPose): FlightPose {
  const scale = home.height > 0 ? AGENT_SIZE / home.height : 1;
  return {
    x: -home.width / 2,
    y: -home.height / 2,
    width: home.width,
    height: home.height,
    scale,
  };
}

const memoryFacetStyle = computed(() => {
  const pose = memoryFacetPose.value;
  if (!pose) return {};
  const glide = memoryFacetGlide.value && !reducedMotion();
  const ease = memoryFacetEase.value;
  return {
    left: `${pose.x}px`,
    top: `${pose.y}px`,
    width: `${pose.width}px`,
    height: `${pose.height}px`,
    transform: `scale(${pose.scale})`,
    transformOrigin: "center center",
    zIndex: "26",
    transition: glide
      ? `left ${DESK_MOVE_MS}ms ${ease}, top ${DESK_MOVE_MS}ms ${ease}, transform ${DESK_MOVE_MS}ms ${ease}`
      : "none",
  };
});

const memoryFacetMeta = computed(() =>
  memoryFacetId.value ? memoryOrbitItem(memoryFacetId.value) : null,
);

async function enterMemoryFacet(id: MemoryOrbitId) {
  if (memoryStage.value !== "memory") return;
  if (memoryFacetId.value === id && memoryFacetStage.value === "open") return;
  const token = beginMemoryFacetPass();
  const home = memoryFacetHome(id);
  const switching = Boolean(memoryFacetId.value) || memoryAside.value;
  memoryFacetId.value = id;
  memoryFacetStage.value = switching ? "open" : "entering";
  memoryFacetEase.value = DESK_EASE_OPEN;

  if (switching || reducedMotion()) {
    liftedMemoryFacet.value = id;
    memoryAside.value = true;
    memoryFacetPose.value = memoryFacetCenter(home);
    memoryFacetCardsShown.value = true;
    memoryFacetGlide.value = false;
    memoryFacetStage.value = "open";
    return;
  }

  memoryFacetCardsShown.value = false;
  memoryFacetGlide.value = false;
  memoryFacetPose.value = home;
  await nextTick();
  await frame();
  await frame();
  if (!isMemoryFacetPass(token)) return;
  // One pass: collapse other satellites into memory, fly focus to center, reveal cards.
  liftedMemoryFacet.value = id;
  memoryAside.value = true;
  memoryFacetGlide.value = true;
  memoryFacetPose.value = memoryFacetCenter(home);
  memoryFacetCardsShown.value = true;
  await wait(DESK_MOVE_MS);
  if (!isMemoryFacetPass(token)) return;
  memoryFacetGlide.value = false;
  memoryFacetStage.value = "open";
}

async function leaveMemoryFacet() {
  if (!memoryFacetId.value || memoryFacetStage.value === "leaving" || memoryFacetStage.value === "closed") {
    return;
  }
  const id = memoryFacetId.value;
  const token = beginMemoryFacetPass();
  if (reducedMotion()) {
    resetMemoryFacet();
    return;
  }
  memoryFacetStage.value = "leaving";
  memoryFacetCardsShown.value = false;
  memoryAside.value = false;
  memoryFacetEase.value = DESK_EASE;
  memoryFacetGlide.value = true;
  await nextTick();
  await frame();
  if (!isMemoryFacetPass(token)) return;
  memoryFacetPose.value = memoryFacetHome(id);
  await wait(DESK_MOVE_MS);
  if (!isMemoryFacetPass(token)) return;
  liftedMemoryFacet.value = null;
  memoryFacetPose.value = null;
  memoryFacetGlide.value = false;
  memoryFacetId.value = null;
  memoryFacetStage.value = "closed";
}

async function enterChannel(toolId: string) {
  if (channelStage.value !== "agent") return;
  if (memoryStage.value !== "agent") resetMemory();
  if (pluginStage.value !== "agent") resetPlugin();
  if (skillStage.value !== "agent") resetSkill();
  const token = beginChannelPass();
  const start = cardPose(toolId);
  channelToolId.value = toolId;
  channelStage.value = "entering";
  clearSelection();
  channelSatellites.value = false;
  flightGlide.value = false;
  flightEase.value = DESK_EASE_OPEN;
  layoutScale.value = start && start.height > 0 ? AGENT_SIZE / start.height : 1;

  if (reducedMotion() || !start) {
    const pose = start ?? {
      x: 0,
      y: 0,
      width: WORLD_KIND_WIDTH,
      height: WORLD_KIND_HEIGHT,
      scale: 1,
    };
    channelParked.value = true;
    liftedChannelId.value = toolId;
    flight.value = centerPose(pose);
    channelSatellites.value = true;
    channelStage.value = "channel";
    return;
  }

  flight.value = start;
  await nextTick();
  await frame();
  await frame();
  if (!isChannelPass(token)) return;
  liftedChannelId.value = toolId;
  channelParked.value = true;
  flightGlide.value = true;
  flight.value = centerPose(start);
  channelSatellites.value = true;
  await wait(DESK_MOVE_MS);
  if (!isChannelPass(token)) return;
  flightGlide.value = false;
  channelStage.value = "channel";
}

async function leaveChannel() {
  if (channelStage.value === "agent" || channelStage.value === "leaving") return;
  const toolId = channelToolId.value;
  const token = beginChannelPass();
  closeKindConnector();
  closeAddressConfig();
  if (reducedMotion() || !toolId || !flight.value) {
    resetChannel();
    return;
  }
  channelStage.value = "leaving";
  channelSatellites.value = false;
  channelParked.value = false;
  flightEase.value = DESK_EASE;
  flightGlide.value = true;
  await nextTick();
  await frame();
  if (!isChannelPass(token)) return;
  const slot = cardPose(toolId);
  if (slot) flight.value = slot;
  await wait(DESK_MOVE_MS);
  if (!isChannelPass(token)) return;
  liftedChannelId.value = null;
  flight.value = null;
  flightGlide.value = false;
  channelToolId.value = null;
  channelStage.value = "agent";
}

/** Clear gap between neighbouring icon edges. */
const ACTION_ICON_GAP = 0.75 * PROJECT_ACTION_SIZE;
/** Center-to-center step that leaves that gap. */
const ACTION_GAP = PROJECT_ACTION_SIZE + ACTION_ICON_GAP;
/** Clear gap between an icon edge and the central card. */
const ACTION_CARD_GAP = 1.5 * PROJECT_ACTION_SIZE;
/** Outermost icons stay inside this angle from the right-hand axis, so a longer row moves outward. */
const ACTION_ARC_LIMIT = (72 * Math.PI) / 180;

interface LayerPose {
  x: number;
  y: number;
  width: number;
  height: number;
  scale: number;
}

function cardExtent(angle: number, halfWidth: number, halfHeight: number): number {
  const cos = Math.abs(Math.cos(angle));
  const sin = Math.abs(Math.sin(angle));
  const alongWidth = cos > 1e-6 ? halfWidth / cos : Number.POSITIVE_INFINITY;
  const alongHeight = sin > 1e-6 ? halfHeight / sin : Number.POSITIVE_INFINITY;
  return Math.min(alongWidth, alongHeight);
}

function actionArcRadius(count: number): number {
  const pose = flight.value;
  const halfWidth = pose ? (pose.width * layoutScale.value) / 2 : AGENT_SIZE / 2;
  const halfHeight = pose ? (pose.height * layoutScale.value) / 2 : AGENT_SIZE / 2;
  const iconRadius = PROJECT_ACTION_SIZE / 2;
  let radius = halfWidth + iconRadius + ACTION_CARD_GAP;
  if (count <= 1) return radius;
  const wedge = ACTION_ARC_LIMIT / (count - 1);
  const spread = ACTION_GAP / (2 * Math.sin(wedge));
  radius = Math.max(radius, spread);
  for (let pass = 0; pass < 4; pass += 1) {
    const step = 2 * Math.asin(Math.min(1, ACTION_GAP / (2 * radius)));
    let needed = radius;
    for (let index = 0; index < count; index += 1) {
      const angle = (index - (count - 1) / 2) * step;
      needed = Math.max(needed, cardExtent(angle, halfWidth, halfHeight) + iconRadius + ACTION_CARD_GAP);
    }
    if (needed <= radius + 0.5) break;
    radius = needed;
  }
  return radius;
}

function arcPlacement(index: number, count: number) {
  const radius = actionArcRadius(count);
  if (count <= 1) return { x: radius, y: 0, angle: 0 };
  const step = 2 * Math.asin(Math.min(1, ACTION_GAP / (2 * radius)));
  const angle = (index - (count - 1) / 2) * step;
  return {
    x: Math.cos(angle) * radius,
    y: Math.sin(angle) * radius,
    angle,
  };
}

function actionSlot(index: number) {
  const place = arcPlacement(index, PROJECT_ACTIONS.length);
  const id = PROJECT_ACTIONS[index]?.id;
  const lifted = liftedAction.value === id;
  const active = Boolean(projectLayer.value || addressLayerId.value);
  return {
    left: `${place.x - PROJECT_ACTION_SIZE / 2}px`,
    top: `${place.y - PROJECT_ACTION_SIZE / 2}px`,
    width: `${PROJECT_ACTION_SIZE}px`,
    height: `${PROJECT_ACTION_SIZE}px`,
    // Keep the dock while viewing a channel layer; only the flying copy leaves the arc.
    opacity: lifted ? 0 : active ? 0.45 : undefined,
    transition: lifted ? "none" : `opacity ${DESK_ASIDE_MS}ms ease`,
  };
}

function actionCaptionStyle(index: number) {
  const place = arcPlacement(index, PROJECT_ACTIONS.length);
  return {
    transform: `translate(-50%, -50%) translate(${Math.cos(place.angle) * 52}px, ${Math.sin(place.angle) * 52}px)`,
  };
}

function layerHome(id: ProjectLayerId): LayerPose {
  const index = PROJECT_ACTIONS.findIndex((item) => item.id === id);
  const place = arcPlacement(index, PROJECT_ACTIONS.length);
  return {
    x: place.x - PROJECT_ACTION_SIZE / 2,
    y: place.y - PROJECT_ACTION_SIZE / 2,
    width: PROJECT_ACTION_SIZE,
    height: PROJECT_ACTION_SIZE,
    scale: 1,
  };
}

function layerCenter(home: Pick<LayerPose, "width" | "height">): LayerPose {
  const scale = home.height > 0 ? AGENT_SIZE / home.height : 1;
  return {
    x: -home.width / 2,
    y: -home.height / 2,
    width: home.width,
    height: home.height,
    scale,
  };
}

function addressHome(addressId: string): LayerPose | null {
  const card = channelLayout.value.cards.find((item) => item.id === addressId);
  if (!card) return null;
  return {
    x: Number.parseFloat(card.style.left),
    y: Number.parseFloat(card.style.top),
    width: Number.parseFloat(card.style.width),
    height: Number.parseFloat(card.style.height),
    scale: 1,
  };
}

const layerStyle = computed(() => {
  const pose = layerPose.value;
  if (!pose) return {};
  const glide = layerGlide.value && !reducedMotion();
  const ease = layerEase.value;
  return {
    left: `${pose.x}px`,
    top: `${pose.y}px`,
    width: `${pose.width}px`,
    height: `${pose.height}px`,
    transform: `scale(${pose.scale})`,
    transformOrigin: "center center",
    zIndex: "26",
    transition: glide
      ? `left ${DESK_MOVE_MS}ms ${ease}, top ${DESK_MOVE_MS}ms ${ease}, transform ${DESK_MOVE_MS}ms ${ease}`
      : "none",
  };
});

const layerSpreadStyle = computed(() => {
  const shown = layerSatellites.value;
  const ease = shown ? DESK_EASE_OPEN : DESK_EASE;
  return {
    left: "0px",
    top: "0px",
    width: "0px",
    height: "0px",
    transform: shown ? "scale(1)" : "scale(0)",
    opacity: shown ? "1" : "0",
    transformOrigin: "0 0",
    zIndex: "24",
    transition: reducedMotion()
      ? "none"
      : `transform ${DESK_MOVE_MS}ms ${ease}, opacity ${Math.round(DESK_MOVE_MS * 0.55)}ms ease`,
  };
});

function questionSlot(index: number, count: number) {
  const pitch = 96;
  const rows = count + 1;
  const total = rows * pitch - 24;
  return {
    left: `${SKILL_ORBIT_RADIUS - 110}px`,
    top: `${-total / 2 + index * pitch}px`,
    width: "220px",
    height: "72px",
  };
}

function addQuestionSlot(count: number) {
  const slot = questionSlot(count, count);
  const size = 56;
  const top = Number.parseFloat(slot.top) + (72 - size) / 2;
  return {
    left: `${SKILL_ORBIT_RADIUS - size / 2}px`,
    top: `${top}px`,
    width: `${size}px`,
    height: `${size}px`,
  };
}

const nameFieldStyle = {
  left: "-9rem",
  top: `${AGENT_SIZE / 2 + 28}px`,
  width: "18rem",
};

const channelSettingsSlot = {
  left: "148px",
  top: "-250px",
  width: "22rem",
};

const addressSettingsSlot = {
  left: "168px",
  top: "-220px",
  width: "22rem",
};

function resetProjectLayer() {
  cancelLayerPasses();
  projectLayer.value = null;
  addressLayerId.value = null;
  pendingAddressId.value = null;
  projectLayerStage.value = "closed";
  channelAside.value = false;
  liftedAction.value = null;
  layerSatellites.value = false;
  layerGlide.value = false;
  layerPose.value = null;
  nameError.value = null;
}

function persistQuestions() {
  const slug = props.project?.slug;
  if (!slug) return;
  writeProjectQuestions(slug, questions.value);
}

function addQuestion() {
  const item: ProjectQuestion = { id: crypto.randomUUID(), text: "" };
  questions.value = [...questions.value, item];
  persistQuestions();
}

function onQuestionInput(id: string, event: Event) {
  const target = event.target;
  if (!(target instanceof HTMLInputElement)) return;
  updateQuestion(id, target.value);
}

function updateQuestion(id: string, text: string) {
  questions.value = questions.value.map((item) => (item.id === id ? { ...item, text } : item));
  persistQuestions();
}

function removeQuestion(id: string) {
  questions.value = questions.value.filter((item) => item.id !== id);
  persistQuestions();
}

function commitInstanceName() {
  const instance = channelInstance.value;
  if (!instance) return;
  const name = nameDraft.value.trim();
  if (!name) {
    nameError.value = "Укажите имя канала";
    return;
  }
  nameError.value = null;
  if (name === instance.name) return;
  const result = updateInstance(props.agentSlug, instance.id, { name });
  if (!result.ok) {
    nameError.value = result.error ?? "Не удалось сохранить имя";
    return;
  }
  nameDraft.value = result.instance?.name ?? name;
}

const channelInstance = computed(() => {
  const toolId = channelToolId.value;
  const current = agent.value;
  if (!toolId || !current) return null;
  return (
    current.tools.find((item) => item.toolId === toolId && item.enabled) ??
    current.tools.find((item) => item.toolId === toolId) ??
    null
  );
});

const activeAddress = computed(() =>
  channelLayout.value.cards.find((item) => item.id === addressLayerId.value) ?? null,
);

async function enterProjectLayer(id: ProjectLayerId) {
  if (channelStage.value !== "channel") return;
  if (projectLayer.value === id && projectLayerStage.value === "open" && !addressLayerId.value) return;
  if (projectLayer.value === "name") commitInstanceName();
  addressLayerId.value = null;
  const token = beginLayerPass();
  const home = layerHome(id);
  const switching = Boolean(projectLayer.value) || channelAside.value;
  closeKindConnector();
  closeAddressConfig();
  projectLayer.value = id;
  projectLayerStage.value = switching ? "open" : "entering";
  layerEase.value = DESK_EASE_OPEN;
  if (id === "name") {
    nameDraft.value = channelInstance.value?.name ?? channelKind.value?.name ?? "";
    nameError.value = null;
  }

  if (switching || reducedMotion()) {
    liftedAction.value = id;
    channelAside.value = true;
    layerPose.value = layerCenter(home);
    layerSatellites.value = true;
    layerGlide.value = false;
    projectLayerStage.value = "open";
    return;
  }

  layerSatellites.value = false;
  layerGlide.value = false;
  layerPose.value = home;
  await nextTick();
  await frame();
  await frame();
  if (!isLayerPass(token)) return;
  liftedAction.value = id;
  channelAside.value = true;
  layerGlide.value = true;
  layerPose.value = layerCenter(home);
  layerSatellites.value = true;
  await wait(DESK_MOVE_MS);
  if (!isLayerPass(token)) return;
  layerGlide.value = false;
  projectLayerStage.value = "open";
}

async function leaveProjectLayer() {
  if (!projectLayer.value || projectLayerStage.value === "leaving" || projectLayerStage.value === "closed") return;
  const id = projectLayer.value;
  const token = beginLayerPass();
  if (id === "name") commitInstanceName();
  if (!isLayerPass(token)) return;
  if (reducedMotion()) {
    resetProjectLayer();
    return;
  }
  projectLayerStage.value = "leaving";
  layerSatellites.value = false;
  channelAside.value = false;
  layerEase.value = DESK_EASE;
  layerGlide.value = true;
  await nextTick();
  await frame();
  if (!isLayerPass(token)) return;
  layerPose.value = layerHome(id);
  await wait(DESK_MOVE_MS);
  if (!isLayerPass(token)) return;
  liftedAction.value = null;
  layerPose.value = null;
  layerGlide.value = false;
  projectLayer.value = null;
  projectLayerStage.value = "closed";
}

async function enterAddressLayer(addressId: string) {
  if (channelStage.value !== "channel" || projectLayer.value || addressLayerId.value) return;
  const home = addressHome(addressId);
  if (!home) return;
  const token = beginLayerPass();
  closeKindConnector();
  closeAddressConfig();
  addressLayerId.value = addressId;
  projectLayerStage.value = "entering";
  layerSatellites.value = false;
  layerGlide.value = false;
  layerEase.value = DESK_EASE_OPEN;
  layerPose.value = home;

  if (reducedMotion()) {
    channelAside.value = true;
    layerPose.value = layerCenter(home);
    layerSatellites.value = true;
    projectLayerStage.value = "open";
    return;
  }

  await nextTick();
  await frame();
  await frame();
  if (!isLayerPass(token)) return;
  channelAside.value = true;
  layerGlide.value = true;
  layerPose.value = layerCenter(home);
  layerSatellites.value = true;
  await wait(DESK_MOVE_MS);
  if (!isLayerPass(token)) return;
  layerGlide.value = false;
  projectLayerStage.value = "open";
}

async function leaveAddressLayer() {
  if (!addressLayerId.value || projectLayerStage.value === "leaving" || projectLayerStage.value === "closed") return;
  const addressId = addressLayerId.value;
  const token = beginLayerPass();
  const home = addressHome(addressId);
  if (reducedMotion() || !home) {
    resetProjectLayer();
    return;
  }
  projectLayerStage.value = "leaving";
  layerSatellites.value = false;
  channelAside.value = false;
  layerEase.value = DESK_EASE;
  layerGlide.value = true;
  await nextTick();
  await frame();
  if (!isLayerPass(token)) return;
  layerPose.value = home;
  await wait(DESK_MOVE_MS);
  if (!isLayerPass(token)) return;
  layerPose.value = null;
  layerGlide.value = false;
  addressLayerId.value = null;
  projectLayerStage.value = "closed";
}

function leaveCurrentLayer() {
  if (addressLayerId.value) void leaveAddressLayer();
  else void leaveProjectLayer();
}

function onEmbeddedSelectSkill(skillId: string) {
  resetChannel();
  focusSkill(skillId);
}

watch(
  () => props.project?.slug,
  (slug) => {
    questions.value = slug ? readProjectQuestions(slug) : [];
  },
  { immediate: true },
);

watch(channelStage, (stage) => {
  if (stage !== "channel" || !pendingAddressId.value) return;
  const addressId = pendingAddressId.value;
  pendingAddressId.value = null;
  void enterAddressLayer(addressId);
});

watch(projectLayerStage, async (stage) => {
  if (stage !== "open") return;
  await nextTick();
  if (projectLayer.value === "name") nameField.value?.focus();
});

function onChannelKeydown(event: KeyboardEvent) {
  if (event.key !== "Escape") return;
  if (
    channelStage.value === "agent" &&
    memoryStage.value === "agent" &&
    pluginStage.value === "agent" &&
    skillStage.value === "agent"
  ) {
    return;
  }
  const target = event.target;
  if (
    target instanceof HTMLElement &&
    target.closest("input, textarea, select, [contenteditable='true']")
  ) {
    if (document.activeElement instanceof HTMLElement) document.activeElement.blur();
    event.preventDefault();
    event.stopImmediatePropagation();
    return;
  }
  event.preventDefault();
  event.stopImmediatePropagation();
  if (skillStage.value !== "agent") {
    if (skillFacetId.value) {
      void leaveSkillFacet();
      return;
    }
    void leaveSkill();
    return;
  }
  if (pluginStage.value !== "agent") {
    if (pluginFacetId.value) {
      void leavePluginFacet();
      return;
    }
    void leavePlugin();
    return;
  }
  if (memoryStage.value !== "agent") {
    if (memoryFacetId.value) {
      void leaveMemoryFacet();
      return;
    }
    void leaveMemory();
    return;
  }
  if (selectedAddressId.value) {
    closeAddressConfig();
    return;
  }
  if (selectedKindToolId.value) {
    closeKindConnector();
    return;
  }
  if (addressLayerId.value || projectLayer.value) {
    leaveCurrentLayer();
    return;
  }
  void leaveChannel();
}

watch(
  () => props.satellitesVisible,
  (shown) => {
    if (!shown) {
      resetChannel();
      resetMemory();
      resetPlugin();
      resetSkill();
    }
  },
);

onMounted(() => {
  document.addEventListener("keydown", onChannelKeydown, true);
});

onUnmounted(() => {
  cancelChannelPasses();
  cancelLayerPasses();
  cancelMemoryPasses();
  cancelMemoryFacetPasses();
  cancelPluginPasses();
  cancelPluginFacetPasses();
  cancelSkillPasses();
  cancelSkillFacetPasses();
  document.removeEventListener("keydown", onChannelKeydown, true);
});
</script>

<template>
  <div
    ref="constructorRoot"
    class="relative h-full min-h-0 w-full flex-1 overflow-hidden"
    :data-channel-mode="channelStage !== 'agent' ? 'on' : undefined"
    :data-plugin-mode="pluginStage !== 'agent' ? 'on' : undefined"
    :data-skill-mode="skillStage !== 'agent' ? 'on' : undefined"
    :data-memory-mode="memoryStage !== 'agent' ? 'on' : undefined"
  >
    <InfiniteCanvas
      ref="canvas"
      :nodes="canvasNodes"
      :selected-node-id="selectedNodeId"
      :selected-kind-tool-id="selectedKindToolId"
      :selected-address-id="selectedAddressId"
      :selected-plugin-id="selectedPluginId"
      :lifted-plugin-id="liftedPluginId"
      :lifted-skill-id="liftedSkillId"
      :add-skill-slot="addSkillSlot"
      :add-kind-slot="addKindSlot"
      :add-plugin-slot="addPluginSlot"
      :world-kinds="canvasWorldKinds"
      :world-addresses="canvasWorldAddresses"
      :plugins="canvasPlugins"
      :highlight="highlight"
      :memory-selected="memoryStage !== 'agent'"
      :memory-history-line="memoryLines.historyLine"
      :memory-state-line="memoryLines.stateLine"
      :lifted-memory="liftedMemory"
      :boot-pan="bootPan"
      :satellites-visible="satellitesVisible"
      :parked="deskParked"
      :lifted-channel-id="liftedChannelId"
      :clear-backdrop="clearBackdrop"
      :glide="glide"
      :glide-ease="glideEase"
      :glide-ms="glideMs"
      :glide-delay="glideDelay"
      @ready="emit('ready')"
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
      :pan-x="embedded ? hubPan.x : viewport.panX"
      :pan-y="embedded ? hubPan.y : viewport.panY"
      :zoom="viewport.zoom"
      :visible="hubVisible"
      :glyph-scale="glyphScale"
      :glide="glide"
      :glide-ease="glideEase"
      :glide-ms="glideMs"
      :glide-delay="glideDelay"
      :show-meta="showMeta"
      :parked="deskParked"
      @open="openAgentCard"
      @close-card="closeAgentCard"
      @open-details="openAgentDetails"
      @close-details="closeAgentDetails"
      @update="onUpdateAgent"
    />

    <div
      v-if="flight && channelKind"
      class="pointer-events-none absolute"
      :style="flightStyle"
    >
      <div class="absolute" :style="channelSpreadStyle">
        <button
          v-if="channelLayout.port"
          type="button"
          class="absolute flex items-center justify-center rounded-full border border-base-content/30 bg-base-200/90 text-base-content/45 shadow-sm transition hover:border-primary/50 hover:text-primary"
          :class="channelFaceOpen ? 'pointer-events-auto' : 'pointer-events-none'"
          :style="channelLayout.port"
          title="Добавить адрес"
          aria-label="Добавить адрес"
          @click="onAddAddress(channelKind.toolId)"
        >
          <svg viewBox="0 0 24 24" class="size-2.5" fill="none" stroke="currentColor" stroke-width="3" aria-hidden="true">
            <path stroke-linecap="round" d="M12 5v14M5 12h14" />
          </svg>
        </button>

        <p
          v-if="channelLayout.empty"
          class="absolute text-center text-xs text-base-content/50"
          :style="channelLayout.empty"
        >
          Адресов пока нет
        </p>

        <div
          v-for="address in channelLayout.cards"
          :key="address.id"
          class="group absolute"
          :style="{
            ...address.style,
            opacity: addressLayerId === address.id ? 0 : undefined,
            transition: addressLayerId === address.id ? 'none' : undefined,
          }"
        >
          <button
            type="button"
            class="flex h-full w-full items-center justify-center rounded-xl border-2 bg-base-100/90 px-2 text-center text-[11px] font-medium shadow-sm"
            :class="[
              borderClass(address.status),
              selectedAddressId === address.id ? 'ring-2 ring-primary/40' : '',
              channelFaceOpen ? 'pointer-events-auto' : 'pointer-events-none',
            ]"
            :title="address.reason"
            @click="onSelectAddress(address.id)"
          >
            <span class="line-clamp-2 px-3">{{ address.name }}</span>
          </button>
          <button
            type="button"
            class="absolute -right-1.5 -top-1.5 flex size-5 items-center justify-center rounded-full border border-base-300 bg-base-100 text-[10px] text-base-content/45 opacity-0 shadow-sm transition hover:border-error/50 hover:text-error group-hover:opacity-100"
            :class="channelFaceOpen ? 'pointer-events-auto' : 'pointer-events-none'"
            title="Удалить адрес"
            aria-label="Удалить адрес"
            @click="onRemoveAddress(address.id)"
          >
            ✕
          </button>
        </div>

      </div>

      <div
        class="absolute"
        :style="{
          left: '0px',
          top: '0px',
          width: '0px',
          height: '0px',
          opacity: channelSatellites ? '1' : '0',
          transform: channelSatellites ? 'scale(1)' : 'scale(0)',
          transformOrigin: '0 0',
          transition: reducedMotion()
            ? 'none'
            : `transform ${DESK_MOVE_MS}ms ${channelSatellites ? DESK_EASE_OPEN : DESK_EASE}, opacity ${Math.round(DESK_MOVE_MS * 0.55)}ms ease`,
        }"
      >
        <div
          v-for="(action, index) in PROJECT_ACTIONS"
          :key="action.id"
          class="absolute"
          :style="actionSlot(index)"
        >
          <button
            type="button"
            class="btn btn-circle h-full w-full border border-base-300 bg-base-100 shadow-md"
            :class="[
              channelActionsOpen ? 'pointer-events-auto' : 'pointer-events-none',
              projectLayer === action.id ? 'ring-2 ring-primary/40' : '',
            ]"
            :aria-label="action.label"
            :title="action.label"
            @click="enterProjectLayer(action.id)"
          >
            <svg viewBox="0 0 24 24" class="size-6" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
              <template v-if="action.id === 'questions'">
                <circle cx="12" cy="12" r="9" />
                <path stroke-linecap="round" d="M9.5 9a2.5 2.5 0 1 1 3.5 2.3c-.8.4-1.5 1-1.5 2" />
                <path stroke-linecap="round" d="M12 17h.01" />
              </template>
              <template v-else-if="action.id === 'name'">
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 20h9" />
                <path stroke-linecap="round" stroke-linejoin="round" d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z" />
              </template>
              <template v-else>
                <circle cx="6" cy="12" r="1.2" fill="currentColor" stroke="none" />
                <circle cx="12" cy="12" r="1.2" fill="currentColor" stroke="none" />
                <circle cx="18" cy="12" r="1.2" fill="currentColor" stroke="none" />
              </template>
            </svg>
          </button>
          <span
            class="pointer-events-none absolute left-1/2 top-1/2 w-max text-[11px] font-medium text-base-content/70"
            :style="actionCaptionStyle(index)"
          >
            {{ action.caption }}
          </span>
        </div>
      </div>

      <div class="absolute" :style="cardBoxStyle">
        <div
          class="flex h-full w-full flex-col items-center justify-center rounded-2xl border-2 border-base-300 bg-base-100 px-2 text-center text-xs font-semibold text-base-content shadow-md"
        >
          <span class="line-clamp-2">{{ channelKind.name }}</span>
        </div>
      </div>

      <div v-if="layerPose && (projectLayer || addressLayerId)" class="pointer-events-none absolute" :style="layerStyle">
        <div
          v-if="projectLayer"
          class="flex h-full w-full items-center justify-center rounded-full border border-base-300 bg-base-100 shadow-md"
        >
          <svg viewBox="0 0 24 24" class="size-6" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
            <template v-if="projectLayer === 'questions'">
              <circle cx="12" cy="12" r="9" />
              <path stroke-linecap="round" d="M9.5 9a2.5 2.5 0 1 1 3.5 2.3c-.8.4-1.5 1-1.5 2" />
              <path stroke-linecap="round" d="M12 17h.01" />
            </template>
            <template v-else-if="projectLayer === 'name'">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 20h9" />
              <path stroke-linecap="round" stroke-linejoin="round" d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z" />
            </template>
            <template v-else>
              <circle cx="6" cy="12" r="1.2" fill="currentColor" stroke="none" />
              <circle cx="12" cy="12" r="1.2" fill="currentColor" stroke="none" />
              <circle cx="18" cy="12" r="1.2" fill="currentColor" stroke="none" />
            </template>
          </svg>
        </div>
        <div
          v-else-if="activeAddress"
          class="flex h-full w-full items-center justify-center rounded-xl border-2 bg-base-100 px-2 text-center text-[11px] font-medium shadow-md"
          :class="borderClass(activeAddress.status)"
        >
          <span class="line-clamp-2 px-3">{{ activeAddress.name }}</span>
        </div>
      </div>

      <div v-if="projectLayer || addressLayerId" class="pointer-events-none absolute" :style="layerSpreadStyle">
        <template v-if="projectLayer === 'questions'">
          <div
            v-for="(question, index) in questions"
            :key="question.id"
            class="group absolute"
            :style="questionSlot(index, questions.length)"
          >
            <input
              :value="question.text"
              type="text"
              class="input h-full w-full text-center"
              placeholder="Вопрос"
              :class="layerSatellites ? 'pointer-events-auto' : 'pointer-events-none'"
              @change="onQuestionInput(question.id, $event)"
            />
            <button
              type="button"
              class="absolute -right-1.5 -top-1.5 flex size-5 items-center justify-center rounded-full border border-base-300 bg-base-100 text-[10px] text-base-content/45 opacity-0 shadow-sm transition hover:border-error/50 hover:text-error group-hover:opacity-100"
              :class="layerSatellites ? 'pointer-events-auto' : 'pointer-events-none'"
              title="Удалить вопрос"
              aria-label="Удалить вопрос"
              @click="removeQuestion(question.id)"
            >
              ✕
            </button>
          </div>
          <button
            type="button"
            class="btn btn-circle absolute border border-dashed border-base-content/35 bg-base-100/40 shadow-sm"
            :class="layerSatellites ? 'pointer-events-auto' : 'pointer-events-none'"
            :style="addQuestionSlot(questions.length)"
            title="Добавить вопрос"
            aria-label="Добавить вопрос"
            @click="addQuestion"
          >
            <svg viewBox="0 0 24 24" class="size-5" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <path stroke-linecap="round" d="M12 5v14M5 12h14" />
            </svg>
          </button>
        </template>

        <form
          v-else-if="projectLayer === 'name'"
          class="absolute"
          :style="nameFieldStyle"
          @submit.prevent="commitInstanceName"
        >
          <input
            ref="nameField"
            v-model="nameDraft"
            type="text"
            class="input w-full text-center text-lg font-semibold"
            aria-label="Имя канала"
            :class="layerSatellites ? 'pointer-events-auto' : 'pointer-events-none'"
            @change="commitInstanceName"
          />
          <p v-if="nameError" class="mt-2 text-center text-sm text-error">{{ nameError }}</p>
        </form>

        <div
          v-else-if="projectLayer === 'more' && channelToolId && channelKind"
          class="absolute"
          :class="layerSatellites ? 'pointer-events-auto' : 'pointer-events-none'"
          :style="channelSettingsSlot"
        >
          <KindConnectorPanel
            embedded
            hide-name
            :agent-slug="agentSlug"
            :tool-id="channelToolId"
            :status="channelKind.status"
            :reason="channelKind.reason"
            @select-skill="onEmbeddedSelectSkill"
          />
        </div>

        <div
          v-else-if="addressLayerId && activeAddress"
          class="absolute"
          :class="layerSatellites ? 'pointer-events-auto' : 'pointer-events-none'"
          :style="addressSettingsSlot"
        >
          <AddressConfigPanel
            embedded
            :agent-slug="agentSlug"
            :address-id="addressLayerId"
            :status="activeAddress.status === 'off' ? 'yellow' : activeAddress.status"
            :reason="activeAddress.reason"
            @update="onUpdateAddress"
            @credentials-changed="loadCredentials"
            @remove="onRemoveAddress(addressLayerId)"
          />
        </div>
      </div>

      <button
        v-if="channelStage !== 'agent'"
        type="button"
        class="btn btn-ghost btn-xs absolute text-base-content/50"
        :class="channelFaceOpen ? 'pointer-events-auto opacity-100' : 'pointer-events-none opacity-0'"
        :style="{
          ...disconnectStyle,
          transition: `opacity ${DESK_ASIDE_MS}ms ease`,
        }"
        @click="onDisconnectKind(channelKind.toolId)"
      >
        Отключить
      </button>
    </div>

    <!-- Skill mode: skill → left hub; facets vertical column (same layout as plugin). -->
    <div
      v-if="skillFlight"
      class="pointer-events-none absolute"
      :style="skillFlightStyle"
    >
      <div class="absolute" :style="skillSpreadStyle">
        <button
          v-for="slot in skillOrbitSlots"
          :key="slot.id"
          type="button"
          class="absolute flex items-center gap-3 border-0 bg-transparent p-0 text-left text-inherit hover:text-base-content"
          :class="skillFaceOpen ? 'pointer-events-auto' : 'pointer-events-none'"
          :style="skillSatStyle(slot)"
          :aria-label="slot.label"
          :title="slot.label"
          @click="enterSkillFacet(slot.id)"
        >
          <span
            class="flex shrink-0 items-center justify-center rounded-full border border-base-300 bg-base-100 shadow-md"
            :style="{ width: `${SKILL_SAT_SIZE}px`, height: `${SKILL_SAT_SIZE}px` }"
          >
            <SkillDetailGlyph :id="slot.id" />
          </span>
          <span
            class="whitespace-nowrap font-medium leading-tight text-base-content/75"
            :style="{ fontSize: SKILL_LABEL_TYPE }"
          >
            {{ slot.caption }}
          </span>
        </button>
      </div>

      <div class="absolute" :style="skillCardBoxStyle">
        <div
          class="flex h-full w-full flex-col items-center justify-center rounded-2xl border-2 border-base-300 bg-base-100 px-3 text-center shadow-md"
        >
          <span class="w-full truncate text-xs font-semibold">{{ skillCenterMeta.name }}</span>
          <span class="w-full truncate font-mono text-[10px] text-base-content/70">
            {{ skillCenterMeta.role }}
          </span>
        </div>
      </div>

      <div
        v-if="skillFacetPose && skillFacetId && skillFacetMeta"
        class="pointer-events-none absolute flex items-center gap-3"
        :style="skillFacetStyle"
      >
        <div
          class="flex shrink-0 items-center justify-center rounded-full border border-base-300 bg-base-100 shadow-md"
          :style="{ width: `${SKILL_SAT_SIZE}px`, height: `${SKILL_SAT_SIZE}px` }"
        >
          <SkillDetailGlyph :id="skillFacetId" />
        </div>
        <span
          class="whitespace-nowrap font-medium leading-tight text-base-content/75"
          :style="{ fontSize: SKILL_LABEL_TYPE }"
        >
          {{ skillFacetMeta.caption }}
        </span>
      </div>
    </div>

    <SkillFacetCards
      v-if="skillFacetId && selectedSkill && selectedSkillDependencies"
      :agent-slug="agentSlug"
      :skill="selectedSkill"
      :facet="skillFacetId"
      :dependencies="selectedSkillDependencies"
      :shown="skillFacetShown"
      @open-editor="openSkillEditor"
      @remove="deleteSelectedSkill"
      @select-kind="onSelectKind"
      @select-plugin="openPlugin"
    />

    <!-- Plugin mode: instance → center; facet → center + right gradient-blur stage. -->
    <div
      v-if="pluginFlight"
      class="pointer-events-none absolute"
      :style="pluginFlightStyle"
    >
      <div class="absolute" :style="pluginSpreadStyle">
        <button
          v-for="slot in pluginOrbitSlots"
          :key="slot.id"
          type="button"
          class="absolute flex items-center gap-3 border-0 bg-transparent p-0 text-left text-inherit hover:text-base-content"
          :class="pluginFaceOpen ? 'pointer-events-auto' : 'pointer-events-none'"
          :style="pluginSatStyle(slot)"
          :aria-label="slot.label"
          :title="slot.label"
          @click="enterPluginFacet(slot.id)"
        >
          <span
            class="flex shrink-0 items-center justify-center rounded-full border border-base-300 bg-base-100 shadow-md"
            :style="{ width: `${PLUGIN_SAT_SIZE}px`, height: `${PLUGIN_SAT_SIZE}px` }"
          >
            <PluginDetailGlyph :id="slot.id" />
          </span>
          <span
            class="whitespace-nowrap font-medium leading-tight text-base-content/75"
            :style="{ fontSize: PLUGIN_LABEL_TYPE }"
          >
            {{ slot.caption }}
          </span>
        </button>
      </div>

      <div class="absolute" :style="pluginCardBoxStyle">
        <div
          class="flex h-full w-full flex-col items-center justify-center rounded-2xl border-2 border-base-300 bg-base-100 px-3 text-center shadow-md"
        >
          <span class="w-full truncate text-xs font-semibold">{{ pluginCenterMeta.name }}</span>
          <span class="w-full truncate font-mono text-[10px] text-base-content/70">
            {{ pluginCenterMeta.typeId }}
          </span>
        </div>
      </div>

      <!-- Same icon+label row as the list — flies without restructuring. -->
      <div
        v-if="pluginFacetPose && pluginFacetId && pluginFacetMeta"
        class="pointer-events-none absolute flex items-center gap-3"
        :style="pluginFacetStyle"
      >
        <div
          class="flex shrink-0 items-center justify-center rounded-full border border-base-300 bg-base-100 shadow-md"
          :style="{ width: `${PLUGIN_SAT_SIZE}px`, height: `${PLUGIN_SAT_SIZE}px` }"
        >
          <PluginDetailGlyph :id="pluginFacetId" />
        </div>
        <span
          class="whitespace-nowrap font-medium leading-tight text-base-content/75"
          :style="{ fontSize: PLUGIN_LABEL_TYPE }"
        >
          {{ pluginFacetMeta.caption }}
        </span>
      </div>
    </div>

    <PluginFacetCards
      v-if="pluginFacetId && selectedPluginId && selectedPluginLink"
      :agent-slug="agentSlug"
      :instance-id="selectedPluginId"
      :facet="pluginFacetId"
      :status="selectedPluginLink.status"
      :reason="selectedPluginLink.reason"
      :shown="pluginFacetShown"
      @select-skill="focusSkill"
    />

    <button
      v-if="pluginStage === 'plugin' && selectedPluginId && pluginFaceOpen"
      type="button"
      class="btn btn-ghost btn-xs absolute bottom-6 left-1/2 z-30 -translate-x-1/2 text-error"
      @click="onDisconnectPlugin(selectedPluginId)"
    >
      Отключить плагин
    </button>

    <!-- Memory mode: card → center; facet layer → shelf at center + cards on the right. -->
    <div
      v-if="memoryFlight"
      class="pointer-events-none absolute"
      :style="memoryFlightStyle"
    >
      <div class="absolute" :style="memorySpreadStyle">
        <div
          v-for="slot in memoryOrbitSlots"
          :key="slot.id"
          class="absolute"
          :style="memorySatStyle(slot)"
        >
          <button
            type="button"
            class="btn btn-circle h-full w-full border border-base-300 bg-base-100 shadow-md"
            :class="memoryFaceOpen ? 'pointer-events-auto' : 'pointer-events-none'"
            :aria-label="slot.label"
            :title="slot.label"
            @click="enterMemoryFacet(slot.id)"
          >
            <svg viewBox="0 0 24 24" class="size-5" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
              <template v-if="slot.id === 'self'">
                <circle cx="12" cy="8" r="3" />
                <path stroke-linecap="round" d="M5 19c1.5-4 4-6 7-6s5.5 2 7 6" />
              </template>
              <template v-else-if="slot.id === 'life'">
                <path stroke-linecap="round" stroke-linejoin="round" d="M4 6h16M4 12h10M4 18h14" />
              </template>
              <template v-else-if="slot.id === 'outcomes'">
                <path stroke-linecap="round" stroke-linejoin="round" d="m8 11 2.5 2.5L16 8" />
                <circle cx="12" cy="12" r="9" />
              </template>
              <template v-else-if="slot.id === 'tasks'">
                <circle cx="12" cy="12" r="8" />
                <path stroke-linecap="round" d="M12 8v4l2.5 2.5" />
              </template>
              <template v-else-if="slot.id === 'others'">
                <circle cx="8" cy="12" r="3" />
                <circle cx="16" cy="8" r="2.5" />
                <circle cx="16" cy="16" r="2.5" />
                <path stroke-linecap="round" d="M10.5 10.5 14 9M10.5 13.5 14 15" />
              </template>
              <template v-else-if="slot.id === 'skills'">
                <path stroke-linecap="round" stroke-linejoin="round" d="M7 4h10v4H7zM9 8v12M15 8v12M7 20h10" />
              </template>
              <template v-else>
                <circle cx="12" cy="12" r="3" />
                <circle cx="12" cy="12" r="7" stroke-dasharray="3 3" />
              </template>
            </svg>
          </button>
          <span
            class="pointer-events-none absolute left-1/2 top-full mt-1 -translate-x-1/2 whitespace-nowrap text-[10px] font-medium text-base-content/70"
          >
            {{ slot.caption }}
          </span>
        </div>
      </div>

      <div class="absolute" :style="memoryCardBoxStyle">
        <div
          class="flex h-full w-full flex-col items-center justify-center rounded-2xl border-2 border-base-300 bg-base-100 px-3 text-center shadow-md"
        >
          <span class="w-full truncate text-xs font-semibold">Память</span>
          <span class="w-full truncate font-mono text-[10px] text-base-content/70">
            {{ memoryLines.historyLine }}
          </span>
          <span v-if="memoryLines.stateLine" class="w-full truncate text-[10px] text-base-content/55">
            {{ memoryLines.stateLine }}
          </span>
        </div>
      </div>

      <div
        v-if="memoryFacetPose && memoryFacetId && memoryFacetMeta"
        class="pointer-events-none absolute"
        :style="memoryFacetStyle"
      >
        <div
          class="flex h-full w-full flex-col items-center justify-center rounded-full border border-base-300 bg-base-100 shadow-md"
        >
          <span class="px-1 text-center text-[10px] font-semibold leading-tight">
            {{ memoryFacetMeta.caption }}
          </span>
        </div>
      </div>

      <MemoryFacetCards
        v-if="memoryFacetId"
        :agent-slug="agentSlug"
        :facet="memoryFacetId"
        :memory="memory"
        :loading="memoryLoading"
        :error="memoryError"
        :skill-names="memorySkillNames"
        :shown="memoryFacetCardsShown"
      />
    </div>

    <button
      v-if="channelStage !== 'agent'"
      type="button"
      :class="[
        backButtonClass,
        channelSatellites ? 'opacity-100' : 'pointer-events-none opacity-0',
      ]"
      :style="{ transitionDuration: `${DESK_ASIDE_MS}ms` }"
      @click="addressLayerId || projectLayer ? leaveCurrentLayer() : leaveChannel()"
    >
      {{ addressLayerId || projectLayer ? "К каналу" : "К агенту" }}
    </button>

    <button
      v-if="memoryStage !== 'agent'"
      type="button"
      :class="[
        backButtonClass,
        memorySatellites || memoryFacetId ? 'opacity-100' : 'pointer-events-none opacity-0',
      ]"
      :style="{ transitionDuration: `${DESK_ASIDE_MS}ms` }"
      @click="memoryFacetId ? leaveMemoryFacet() : leaveMemory()"
    >
      {{ memoryFacetId ? "К памяти" : "К агенту" }}
    </button>

    <button
      v-if="pluginStage !== 'agent'"
      type="button"
      :class="[
        backButtonClass,
        pluginSatellites || pluginFacetId ? 'opacity-100' : 'pointer-events-none opacity-0',
      ]"
      :style="{ transitionDuration: `${DESK_ASIDE_MS}ms` }"
      @click="pluginFacetId ? leavePluginFacet() : leavePlugin()"
    >
      {{ pluginFacetId ? "К плагину" : "К агенту" }}
    </button>

    <button
      v-if="skillStage !== 'agent'"
      type="button"
      :class="[
        backButtonClass,
        skillSatellites || skillFacetId ? 'opacity-100' : 'pointer-events-none opacity-0',
      ]"
      :style="{ transitionDuration: `${DESK_ASIDE_MS}ms` }"
      @click="skillFacetId ? leaveSkillFacet() : leaveSkill()"
    >
      {{ skillFacetId ? "К навыку" : "К агенту" }}
    </button>

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

    <SshCommandsConstructor
      v-if="sshConstructorOpen && selectedPluginId"
      :agent-slug="agentSlug"
      :instance-id="selectedPluginId"
      @close="closePlugin"
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
