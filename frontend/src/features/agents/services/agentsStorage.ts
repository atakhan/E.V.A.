import { ref, watch } from "vue";
import type { Agent } from "@/features/agents/types/agent";
import { createEmptyAgentBody } from "@/features/agents/types/agent";
import {
  archiveAgentApi,
  checkApiHealth,
  createAgentApi,
  deleteAgentApi,
  fetchAgent,
  fetchAgentsList,
  saveAgentApi,
  unarchiveAgentApi,
} from "@/features/agents/services/agentsApi";
import { normalizeAction } from "@/features/actions/types/normalize";
import { normalizeToolBinding } from "@/features/tools/types/normalize";
import type { CanvasDocument } from "@/features/skills/types/canvas";
import { normalizeSkill, skillFromLegacyCanvas } from "@/features/skills/types/skill";
import { createId } from "@/shared/utils/id";
import { normalizeAgentSlug, suggestUniqueAgentSlug } from "@/shared/utils/agentSlug";

const STORAGE_KEY = "eva.agents.v2";
const LEGACY_AGENTS_V1_KEY = "eva.agents.v1";
const LEGACY_APPLICATIONS_V2_KEY = "eva.applications.v2";
const LEGACY_APPLICATIONS_V1_KEY = "eva.applications.v1";
const LEGACY_CANVASES_KEY = "eva.canvases.v1";
const LEGACY_FSM_MODULE_ID = "core.fsm";

export const agents = ref<Agent[]>(loadAgentsLocal());
export const apiAvailable = ref(false);
export const storageReady = ref(false);
export type AgentSaveStatus = "idle" | "saving" | "saved" | "error" | "offline";
export const agentSaveStatus = ref<AgentSaveStatus>("idle");

let syncQueue: Promise<void> = Promise.resolve();
let apiInitDone = false;
let saveDebounceTimer: ReturnType<typeof setTimeout> | null = null;
const SAVE_DEBOUNCE_MS = 400;

void bootstrapStorage();

watch(
  agents,
  (value) => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(value));
    if (!apiAvailable.value) {
      agentSaveStatus.value = "offline";
      return;
    }
    agentSaveStatus.value = "saving";
    if (saveDebounceTimer) clearTimeout(saveDebounceTimer);
    saveDebounceTimer = setTimeout(() => {
      syncQueue = syncQueue
        .then(async () => {
          await syncAgentsToApi(value);
          agentSaveStatus.value = "saved";
        })
        .catch(() => {
          agentSaveStatus.value = "error";
        });
    }, SAVE_DEBOUNCE_MS);
  },
  { deep: true },
);

export async function flushAgentsToApi(): Promise<void> {
  if (!apiAvailable.value) {
    agentSaveStatus.value = "offline";
    return;
  }
  if (saveDebounceTimer) {
    clearTimeout(saveDebounceTimer);
    saveDebounceTimer = null;
  }
  agentSaveStatus.value = "saving";
  try {
    await syncAgentsToApi(agents.value);
    agentSaveStatus.value = "saved";
  } catch {
    agentSaveStatus.value = "error";
    throw new Error("Не удалось сохранить агента в API");
  }
}

async function bootstrapStorage() {
  apiAvailable.value = await checkApiHealth();
  if (!apiAvailable.value) {
    storageReady.value = true;
    return;
  }

  try {
    const list = await fetchAgentsList();
    if (list.length === 0) {
      await migrateLocalAgentsToApi();
    } else {
      const loaded: Agent[] = [];
      for (const summary of list) {
        loaded.push(await fetchAgent(summary.slug));
      }
      agents.value = normalizeAgents(loaded);
    }
  } catch {
    apiAvailable.value = false;
  } finally {
    apiInitDone = true;
    storageReady.value = true;
  }
}

async function migrateLocalAgentsToApi() {
  const local = loadAgentsLocal();
  if (local.length === 0) return;

  for (const agent of local) {
    try {
      await createAgentApi({
        name: agent.name,
        slug: agent.slug,
        description: agent.description,
      });
      await saveAgentApi(agent);
    } catch {
      // slug conflict — try save only
      try {
        await saveAgentApi(agent);
      } catch {
        // keep local copy only
      }
    }
  }
  const list = await fetchAgentsList();
  const loaded: Agent[] = [];
  for (const summary of list) {
    loaded.push(await fetchAgent(summary.slug));
  }
  agents.value = normalizeAgents(loaded);
}

async function syncAgentsToApi(value: Agent[]) {
  if (!apiInitDone || !apiAvailable.value) return;
  for (const agent of value) {
    if (agent.archivedAt) continue;
    await saveAgentApi(agent);
  }
}

function normalizeAgents(rawAgents: unknown[]): Agent[] {
  const usedSlugs = new Set<string>();

  return rawAgents.map((raw) => {
    const migrated = migrateAgentRecord(raw);
    const name = migrated.name?.trim() || "Агент";
    let slug = migrated.slug ? normalizeAgentSlug(migrated.slug) : "";

    if (!slug || usedSlugs.has(slug)) {
      slug = suggestUniqueAgentSlug(name, (candidate) => !usedSlugs.has(candidate));
    }

    usedSlugs.add(slug);

    return {
      ...migrated,
      name,
      slug,
      description: migrated.description ?? "",
      archivedAt: migrated.archivedAt ?? null,
      skills: migrated.skills.map(normalizeSkill),
      actions: Array.isArray(migrated.actions)
        ? migrated.actions
            .map((action) => normalizeAction(action))
            .filter((action): action is NonNullable<typeof action> => action !== null)
        : [],
      tools: Array.isArray(migrated.tools)
        ? migrated.tools
            .map((tool) => normalizeToolBinding(tool))
            .filter((tool): tool is NonNullable<typeof tool> => tool !== null)
        : [],
    };
  });
}

function migrateAgentRecord(raw: unknown): Agent {
  const record = (raw ?? {}) as Partial<Agent> & {
    modules?: Record<string, unknown>;
  };

  const body = createEmptyAgentBody();
  let skills = Array.isArray(record.skills) ? record.skills.map(normalizeSkill) : [];

  if (skills.length === 0 && record.modules) {
    const fsm = record.modules[LEGACY_FSM_MODULE_ID] as { canvases?: CanvasDocument[] } | undefined;
    if (fsm && Array.isArray(fsm.canvases)) {
      skills = fsm.canvases.map(skillFromLegacyCanvas);
    }
  }

  return {
    id: record.id || createId(),
    slug: record.slug || "",
    name: record.name || "Агент",
    description: record.description ?? "",
    archivedAt: record.archivedAt ?? null,
    createdAt: record.createdAt || new Date().toISOString(),
    updatedAt: record.updatedAt || new Date().toISOString(),
    skills,
    actions: Array.isArray(record.actions) ? record.actions : body.actions,
    tools: Array.isArray(record.tools) ? record.tools : body.tools,
  };
}

function loadAgentsLocal(): Agent[] {
  migrateLegacyStorage();

  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as unknown[];
    return Array.isArray(parsed) ? normalizeAgents(parsed) : [];
  } catch {
    return [];
  }
}

function migrateLegacyStorage() {
  if (localStorage.getItem(STORAGE_KEY)) return;

  for (const legacyKey of [
    LEGACY_AGENTS_V1_KEY,
    LEGACY_APPLICATIONS_V2_KEY,
    LEGACY_APPLICATIONS_V1_KEY,
  ]) {
    const legacyRaw = localStorage.getItem(legacyKey);
    if (!legacyRaw) continue;

    try {
      const legacyAgents = JSON.parse(legacyRaw) as unknown[];
      if (Array.isArray(legacyAgents) && legacyAgents.length > 0) {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(normalizeAgents(legacyAgents)));
        return;
      }
    } catch {
      // try next legacy key
    }
  }

  migrateLegacyCanvases();
}

function migrateLegacyCanvases() {
  try {
    const raw = localStorage.getItem(LEGACY_CANVASES_KEY);
    if (!raw) return;

    const canvases = JSON.parse(raw) as CanvasDocument[];
    if (!Array.isArray(canvases) || canvases.length === 0) return;

    const now = new Date().toISOString();
    const agent: Agent = {
      id: createId(),
      slug: suggestUniqueAgentSlug("agent-1", () => true),
      name: "Агент 1",
      description: "",
      createdAt: now,
      updatedAt: now,
      skills: canvases.map(skillFromLegacyCanvas),
      actions: [],
      tools: [],
    };

    localStorage.setItem(STORAGE_KEY, JSON.stringify([agent]));
  } catch {
    // ignore broken legacy data
  }
}

export function touchAgent(agent: Agent): Agent {
  return { ...agent, updatedAt: new Date().toISOString() };
}

export function replaceAgent(next: Agent) {
  const index = agents.value.findIndex((agent) => agent.id === next.id);
  if (index === -1) return;

  agents.value = [
    ...agents.value.slice(0, index),
    next,
    ...agents.value.slice(index + 1),
  ];
}

export function getAgentById(id: string): Agent | undefined {
  return agents.value.find((agent) => agent.id === id);
}

export function getAgentBySlug(slug: string): Agent | undefined {
  const normalized = normalizeAgentSlug(slug);
  return agents.value.find((agent) => agent.slug === normalized);
}

export function isSlugAvailable(slug: string, excludeAgentId?: string): boolean {
  const normalized = normalizeAgentSlug(slug);
  return !agents.value.some(
    (agent) => agent.slug === normalized && agent.id !== excludeAgentId,
  );
}

export async function removeAgentFromStorage(agent: Agent) {
  agents.value = agents.value.filter((item) => item.id !== agent.id);
  if (apiAvailable.value) {
    try {
      await deleteAgentApi(agent.slug);
    } catch {
      apiAvailable.value = false;
    }
  }
}

export async function archiveAgentInStorage(agent: Agent) {
  if (apiAvailable.value) {
    const result = await archiveAgentApi(agent.slug);
    const index = agents.value.findIndex((item) => item.id === agent.id);
    if (index >= 0) {
      agents.value[index] = { ...agents.value[index], archivedAt: result.archivedAt };
    }
    return;
  }
  const index = agents.value.findIndex((item) => item.id === agent.id);
  if (index >= 0) {
    agents.value[index] = { ...agents.value[index], archivedAt: new Date().toISOString() };
  }
}

export async function unarchiveAgentInStorage(agent: Agent) {
  if (apiAvailable.value) {
    await unarchiveAgentApi(agent.slug);
    const loaded = await fetchAgent(agent.slug);
    const index = agents.value.findIndex((item) => item.id === agent.id);
    if (index >= 0) {
      agents.value[index] = normalizeAgents([loaded])[0];
    } else {
      agents.value = normalizeAgents([...agents.value, loaded]);
    }
    return;
  }
  const index = agents.value.findIndex((item) => item.id === agent.id);
  if (index >= 0) {
    agents.value[index] = { ...agents.value[index], archivedAt: null };
  }
}

export async function fetchArchivedAgentSummaries(): Promise<Agent[]> {
  if (!apiAvailable.value) {
    return agents.value.filter((agent) => Boolean(agent.archivedAt));
  }
  const summaries = await fetchAgentsList({ includeArchived: true });
  const archived = summaries.filter((item) => item.archivedAt);
  const loaded: Agent[] = [];
  for (const summary of archived) {
    loaded.push(await fetchAgent(summary.slug));
  }
  const normalized = normalizeAgents(loaded);
  for (const agent of normalized) {
    const index = agents.value.findIndex((item) => item.id === agent.id);
    if (index >= 0) {
      agents.value[index] = agent;
    } else {
      agents.value.push(agent);
    }
  }
  return normalized;
}

export async function createAgentOnApi(agent: Agent) {
  if (!apiAvailable.value) return;
  try {
    await createAgentApi({
      name: agent.name,
      slug: agent.slug,
      description: agent.description,
    });
    await saveAgentApi(agent);
  } catch {
    apiAvailable.value = false;
  }
}

export async function createAgentWithStorage(input: {
  name: string;
  slug: string;
  description?: string;
}): Promise<Agent> {
  const name = input.name.trim();
  const slug = normalizeAgentSlug(input.slug);
  const description = input.description?.trim() ?? "";

  const now = new Date().toISOString();
  const agent: Agent = {
    id: createId(),
    slug,
    name,
    description,
    createdAt: now,
    updatedAt: now,
    ...createEmptyAgentBody(),
  };
  agents.value = [agent, ...agents.value];
  void createAgentOnApi(agent);
  return agent;
}
