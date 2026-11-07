<script setup lang="ts">
import { computed, ref, useTemplateRef, watch } from "vue";
import { useActions } from "@/features/actions/composables/useActions";
import { getAgentBySlug } from "@/features/agents/services/agentsStorage";
import { useTools } from "@/features/tools/composables/useTools";
import { createCredential, fetchCredentials, type ToolCredential } from "@/features/tools/services/credentialsApi";
import {
  actionsUsingCommand,
  commandFromDraft,
  connectionConfigPatch,
  isSshLibraryAction,
  libraryCommandIds,
  parseConnection,
  readSshLibrary,
  recipeFromCommandIds,
  validateActionDraft,
  validateCommandDraft,
  writeSshLibrary,
  normalizeActionId,
  type SshCommandDraft,
  type SshConnectionDraft,
  type SshLibraryCommand,
} from "@/features/tools/utils/sshLibrary";
import type { ActionPolicy } from "@/features/actions/types/action";
import PluginSettingsSheet from "@/features/constructor/components/PluginSettingsSheet.vue";

const props = defineProps<{
  agentSlug: string;
  instanceId: string;
}>();

const emit = defineEmits<{
  close: [];
}>();

const sheet = useTemplateRef("sheet");

function closeSheet() {
  sheet.value?.requestClose();
}

const { getInstance, updateInstance } = useTools();
const { getActions, getAction, createAction, updateAction, deleteAction } = useActions();

type Panel = "connection" | "command" | "action";

const panel = ref<Panel>("connection");
const editingId = ref<string | null>(null);
const idTouched = ref(false);
const formError = ref<string | null>(null);
const credentialError = ref<string | null>(null);
const credentialBusy = ref(false);
const credentials = ref<ToolCredential[]>([]);
const newKeyName = ref("SSH key");
const newKey = ref("");

const connection = ref<SshConnectionDraft>(parseConnection(undefined));
const commandDraft = ref<SshCommandDraft>(emptyCommand());
const actionDraft = ref({
  id: "",
  name: "",
  description: "",
  policy: "auto" as ActionPolicy,
  commandIds: [] as string[],
});

const instance = computed(() => getInstance(props.agentSlug, props.instanceId) ?? null);
const library = computed(() => readSshLibrary(instance.value?.config));
const actions = computed(() => {
  const agent = getAgentBySlug(props.agentSlug);
  return agent ? getActions(props.agentSlug) : [];
});
const libraryActions = computed(() =>
  actions.value.filter((action) => isSshLibraryAction(action, props.instanceId)),
);
const otherActions = computed(() =>
  actions.value.filter(
    (action) =>
      !isSshLibraryAction(action, props.instanceId) &&
      action.recipe.some((step) => step.tool === props.instanceId),
  ),
);
const sshCredentials = computed(() => credentials.value.filter((item) => item.toolId === "ssh_commands"));

function emptyCommand(): SshCommandDraft {
  return { id: "", name: "", description: "", shell: "", timeoutSec: "" };
}

function loadConnection() {
  connection.value = parseConnection(instance.value?.config);
}

async function loadCredentials() {
  try {
    credentials.value = await fetchCredentials(props.agentSlug, "ssh_commands");
  } catch {
    credentials.value = [];
  }
}

watch(
  () => props.instanceId,
  () => {
    panel.value = "connection";
    editingId.value = null;
    formError.value = null;
    loadConnection();
  },
  { immediate: true },
);

watch(
  () => props.agentSlug,
  () => {
    void loadCredentials();
  },
  { immediate: true },
);

watch(instance, (value) => {
  if (!value) emit("close");
});

function openConnection() {
  panel.value = "connection";
  editingId.value = null;
  formError.value = null;
  loadConnection();
}

function openNewCommand() {
  panel.value = "command";
  editingId.value = null;
  idTouched.value = false;
  formError.value = null;
  commandDraft.value = emptyCommand();
}

function openCommand(commandId: string) {
  const command = library.value.find((item) => item.id === commandId);
  if (!command) return;
  panel.value = "command";
  editingId.value = command.id;
  idTouched.value = true;
  formError.value = null;
  commandDraft.value = {
    id: command.id,
    name: command.name,
    description: command.description,
    shell: command.shell,
    timeoutSec: command.timeoutSec ? String(command.timeoutSec) : "",
  };
}

function openNewAction() {
  panel.value = "action";
  editingId.value = null;
  idTouched.value = false;
  formError.value = null;
  const only = library.value.length === 1 ? library.value[0].id : "";
  actionDraft.value = {
    id: "",
    name: "",
    description: "",
    policy: "auto",
    commandIds: library.value.length ? [only] : [],
  };
}

function openAction(actionId: string) {
  const action = libraryActions.value.find((item) => item.id === actionId);
  if (!action) return;
  panel.value = "action";
  editingId.value = action.id;
  idTouched.value = true;
  formError.value = null;
  actionDraft.value = {
    id: action.id,
    name: action.name,
    description: action.description,
    policy: action.policy,
    commandIds: libraryCommandIds(action),
  };
}

function onCommandName(value: string) {
  commandDraft.value.name = value;
  if (editingId.value === null && !idTouched.value) {
    commandDraft.value.id = normalizeActionId(value);
  }
}

function onActionName(value: string) {
  actionDraft.value.name = value;
  if (editingId.value === null && !idTouched.value) {
    actionDraft.value.id = normalizeActionId(value);
  }
}

function saveConnection() {
  if (!instance.value) return;
  const parsed = connectionConfigPatch(connection.value);
  if (!parsed.ok) {
    formError.value = parsed.error;
    return;
  }
  formError.value = null;
  updateInstance(props.agentSlug, instance.value.id, {
    config: { ...instance.value.config, ...parsed.patch },
  });
}

function saveCommand(): SshLibraryCommand | null {
  const current = instance.value;
  if (!current) return null;
  const previousId = editingId.value;
  const libraryNow = readSshLibrary(current.config);
  const existingIds = libraryNow.map((item) => item.id).filter((id) => id !== previousId);
  const errorText = validateCommandDraft(commandDraft.value, existingIds);
  if (errorText) {
    formError.value = errorText;
    return null;
  }
  const command = commandFromDraft(commandDraft.value);
  const index = previousId ? libraryNow.findIndex((item) => item.id === previousId) : -1;
  const next = libraryNow.filter((item) => item.id !== previousId);
  if (index >= 0) next.splice(index, 0, command);
  else next.push(command);
  updateInstance(props.agentSlug, current.id, {
    config: writeSshLibrary(current.config, next),
  });
  if (previousId && previousId !== command.id) retargetCommand(previousId, command.id);
  editingId.value = command.id;
  idTouched.value = true;
  formError.value = null;
  return command;
}

function retargetCommand(fromId: string, toId: string) {
  for (const action of getActions(props.agentSlug)) {
    let changed = false;
    const recipe = action.recipe.map((step) => {
      if (step.tool !== props.instanceId || step.input.command_id !== fromId) return step;
      changed = true;
      return { ...step, input: { ...step.input, command_id: toId } };
    });
    if (changed) updateAction(props.agentSlug, action.id, { recipe });
  }
}

function removeCommand(commandId: string) {
  const users = actionsUsingCommand(getActions(props.agentSlug), props.instanceId, commandId);
  if (users.length) {
    formError.value = `Команду вызывают действия: ${users.map((item) => item.name).join(", ")}. Сначала уберите её из них.`;
    return;
  }
  const command = library.value.find((item) => item.id === commandId);
  if (!command || !instance.value) return;
  if (!confirm(`Удалить команду «${command.name}» из библиотеки?`)) return;
  updateInstance(props.agentSlug, instance.value.id, {
    config: writeSshLibrary(
      instance.value.config,
      readSshLibrary(instance.value.config).filter((item) => item.id !== commandId),
    ),
  });
  formError.value = null;
  openConnection();
}

function saveAction() {
  const current = instance.value;
  if (!current) return;
  const previousId = editingId.value;
  const existingIds = getActions(props.agentSlug)
    .map((item) => item.id)
    .filter((id) => id !== previousId);
  const errorText = validateActionDraft(actionDraft.value, existingIds);
  if (errorText) {
    formError.value = errorText;
    return;
  }
  const id = normalizeActionId(actionDraft.value.id || actionDraft.value.name);
  const recipe = recipeFromCommandIds(props.instanceId, actionDraft.value.commandIds);
  const payload = {
    id,
    name: actionDraft.value.name.trim(),
    description: actionDraft.value.description.trim(),
    policy: actionDraft.value.policy,
    recipe,
  };
  const result = previousId
    ? updateAction(props.agentSlug, previousId, payload)
    : createAction(props.agentSlug, payload);
  if (!result.ok) {
    formError.value = result.error;
    return;
  }
  editingId.value = result.action.id;
  idTouched.value = true;
  formError.value = null;
}

function removeAction(actionId: string) {
  const action = getAction(props.agentSlug, actionId);
  if (!action) return;
  if (!confirm(`Удалить действие «${action.name}»? Навыки, которые его вызывают, потеряют этот шаг.`)) return;
  deleteAction(props.agentSlug, actionId);
  formError.value = null;
  openConnection();
}

function makeActionFromCommand() {
  const command = saveCommand();
  if (!command) return;
  const existing = getAction(props.agentSlug, command.id);
  if (existing) {
    if (isSshLibraryAction(existing, props.instanceId)) openAction(existing.id);
    else formError.value = `Действие «${existing.id}» уже есть и собрано не только из этой библиотеки.`;
    return;
  }
  const result = createAction(props.agentSlug, {
    id: command.id,
    name: command.name,
    description: command.description,
    recipe: recipeFromCommandIds(props.instanceId, [command.id]),
  });
  if (!result.ok) {
    formError.value = result.error;
    return;
  }
  openAction(result.action.id);
}

function addActionStep() {
  const only = library.value.length === 1 ? library.value[0].id : "";
  actionDraft.value.commandIds = [...actionDraft.value.commandIds, only];
}

function removeActionStep(index: number) {
  actionDraft.value.commandIds = actionDraft.value.commandIds.filter((_, itemIndex) => itemIndex !== index);
}

function moveActionStep(index: number, direction: -1 | 1) {
  const next = index + direction;
  const ids = [...actionDraft.value.commandIds];
  if (next < 0 || next >= ids.length) return;
  const [item] = ids.splice(index, 1);
  ids.splice(next, 0, item);
  actionDraft.value.commandIds = ids;
}

function commandName(commandId: string): string {
  return library.value.find((item) => item.id === commandId)?.name ?? commandId;
}

function patchName(value: string) {
  if (!instance.value) return;
  updateInstance(props.agentSlug, instance.value.id, { name: value });
}

function patchCredential(credentialId: string) {
  if (!instance.value) return;
  updateInstance(props.agentSlug, instance.value.id, {
    credentialId: credentialId || undefined,
  });
}

async function saveKey() {
  const key = newKey.value.trim();
  if (!key) {
    credentialError.value = "Вставьте приватный ключ";
    return;
  }
  if (key.includes("ENCRYPTED")) {
    credentialError.value = "Нужен ключ без пароля: зашифрованный ключ спросить некого";
    return;
  }
  credentialBusy.value = true;
  credentialError.value = null;
  try {
    const credential = await createCredential(props.agentSlug, {
      toolId: "ssh_commands",
      name: newKeyName.value.trim() || "SSH key",
      privateKey: key,
    });
    await loadCredentials();
    patchCredential(credential.id);
    newKey.value = "";
  } catch (error) {
    credentialError.value = error instanceof Error ? error.message : "Не удалось сохранить ключ";
  } finally {
    credentialBusy.value = false;
  }
}

const templateInput = "{{input.*}}";
const templateVars = "{{vars.*}}";
const templateStepStdout = "{{steps.run_1.result.stdout}}";

function railClass(active: boolean): string {
  return active
    ? "btn btn-sm btn-active w-full justify-start"
    : "btn btn-sm btn-ghost w-full justify-start";
}
</script>

<template>
  <PluginSettingsSheet ref="sheet" labelled-by="ssh-commands-title" @close="emit('close')">
        <header class="flex items-start justify-between gap-3 border-b border-base-300 px-4 py-3">
          <div class="min-w-0">
            <p class="text-xs uppercase tracking-wide text-base-content/50">Инструмент</p>
            <h2 id="ssh-commands-title" class="text-lg font-semibold">SSH Commands</h2>
            <p class="mt-1 max-w-2xl text-sm text-base-content/65">
              Библиотека возможностей этого подключения. Команда — что выполнить на машине.
              Действие — операция, которую видит навык.
            </p>
          </div>
          <button type="button" class="btn btn-sm btn-square btn-ghost" aria-label="Закрыть" @click="closeSheet()">
            ✕
          </button>
        </header>

        <div v-if="instance" class="grid min-h-0 min-w-0 flex-1 grid-cols-1 sm:grid-cols-[15rem_minmax(0,1fr)]">
          <aside class="min-w-0 space-y-4 overflow-y-auto border-b border-base-300 p-3 sm:min-h-0 sm:border-r sm:border-b-0">
            <label class="form-control w-full">
              <span class="label-text text-xs">Имя подключения</span>
              <input
                class="input input-sm"
                :value="instance.name"
                @change="patchName(($event.target as HTMLInputElement).value)"
              />
            </label>

            <button type="button" :class="railClass(panel === 'connection')" @click="openConnection">
              Подключение
            </button>

            <section class="space-y-1">
              <div class="flex items-center justify-between gap-2 px-1">
                <p class="text-xs font-medium text-base-content/50">Команды</p>
                <span class="text-xs text-base-content/45">{{ library.length }}</span>
              </div>
              <button type="button" class="btn btn-sm btn-ghost w-full justify-start" @click="openNewCommand">
                + команда
              </button>
              <button
                v-for="command in library"
                :key="command.id"
                type="button"
                :class="railClass(panel === 'command' && editingId === command.id)"
                @click="openCommand(command.id)"
              >
                <span class="truncate">{{ command.name }}</span>
              </button>
              <p
                v-if="panel === 'command' && editingId === null"
                class="px-2 text-xs text-base-content/55"
              >
                Новая команда
              </p>
            </section>

            <section class="space-y-1">
              <div class="flex items-center justify-between gap-2 px-1">
                <p class="text-xs font-medium text-base-content/50">Действия</p>
                <span class="text-xs text-base-content/45">{{ libraryActions.length }}</span>
              </div>
              <button type="button" class="btn btn-sm btn-ghost w-full justify-start" @click="openNewAction">
                + действие
              </button>
              <button
                v-for="action in libraryActions"
                :key="action.id"
                type="button"
                :class="railClass(panel === 'action' && editingId === action.id)"
                @click="openAction(action.id)"
              >
                <span class="truncate">{{ action.name }}</span>
              </button>
              <p v-if="panel === 'action' && editingId === null" class="px-2 text-xs text-base-content/55">
                Новое действие
              </p>
            </section>

            <section v-if="otherActions.length" class="space-y-1 px-1">
              <p class="text-xs font-medium text-base-content/50">Ещё вызывают этот инструмент</p>
              <p v-for="action in otherActions" :key="action.id" class="truncate text-xs">
                {{ action.name }}
              </p>
              <p class="text-xs text-base-content/50">Их рецепт собран в разделе Actions.</p>
            </section>
          </aside>

          <section class="min-h-0 min-w-0 overflow-y-auto p-4">
            <p v-if="formError" class="mb-3 text-sm text-error">{{ formError }}</p>

            <form v-if="panel === 'connection'" class="max-w-3xl space-y-3" @submit.prevent="saveConnection">
              <h3 class="text-base font-semibold">Подключение</h3>
              <p class="text-sm text-base-content/65">
                Хост и ключ общие для всех команд этой библиотеки. Ключ хранится отдельно и не попадает в рецепт.
              </p>
              <label class="form-control w-full">
                <span class="label-text text-xs">Хост</span>
                <input v-model="connection.host" class="input input-sm font-mono" placeholder="app.example" />
              </label>
              <div class="grid gap-3 sm:grid-cols-2">
                <label class="form-control w-full">
                  <span class="label-text text-xs">Порт</span>
                  <input v-model="connection.port" type="number" class="input input-sm font-mono" />
                </label>
                <label class="form-control w-full">
                  <span class="label-text text-xs">Пользователь</span>
                  <input v-model="connection.username" class="input input-sm font-mono" placeholder="deploy" />
                </label>
              </div>
              <div class="grid gap-3 sm:grid-cols-2">
                <label class="form-control w-full">
                  <span class="label-text text-xs">Таймаут, сек</span>
                  <input v-model="connection.timeoutSec" type="number" class="input input-sm font-mono" />
                </label>
                <label class="form-control w-full">
                  <span class="label-text text-xs">Лимит вывода, символов</span>
                  <input v-model="connection.outputLimit" type="number" class="input input-sm font-mono" />
                </label>
              </div>
              <label class="form-control w-full">
                <span class="label-text text-xs">Проверка host key</span>
                <select v-model="connection.hostKeyPolicy" class="select select-sm">
                  <option value="accept-new">accept-new — запомнить новый ключ</option>
                  <option value="yes">yes — только уже известный ключ</option>
                </select>
              </label>
              <button type="submit" class="btn btn-sm">Сохранить подключение</button>

              <div class="mt-6 space-y-3 border-t border-base-300 pt-4">
                <h3 class="text-base font-semibold">Ключ</h3>
                <label class="form-control w-full">
                  <span class="label-text text-xs">Сохранённый ключ</span>
                  <select
                    class="select select-sm"
                    :value="instance.credentialId ?? ''"
                    @change="patchCredential(($event.target as HTMLSelectElement).value)"
                  >
                    <option value="">— не выбран —</option>
                    <option v-for="item in sshCredentials" :key="item.id" :value="item.id">
                      {{ item.name }}
                    </option>
                  </select>
                </label>
                <label class="form-control w-full">
                  <span class="label-text text-xs">Имя нового ключа</span>
                  <input v-model="newKeyName" class="input input-sm" />
                </label>
                <label class="form-control w-full">
                  <span class="label-text text-xs">Приватный ключ без пароля</span>
                  <textarea
                    v-model="newKey"
                    class="textarea textarea-sm font-mono text-xs"
                    rows="5"
                    spellcheck="false"
                    autocomplete="off"
                    placeholder="-----BEGIN OPENSSH PRIVATE KEY-----"
                  />
                </label>
                <button type="button" class="btn btn-sm" :disabled="credentialBusy" @click="saveKey">
                  Сохранить ключ
                </button>
                <p v-if="credentialError" class="text-sm text-error">{{ credentialError }}</p>
              </div>
            </form>

            <form v-else-if="panel === 'command'" class="max-w-3xl space-y-3" @submit.prevent="saveCommand">
              <h3 class="text-base font-semibold">
                {{ editingId ? "Команда" : "Новая команда" }}
              </h3>
              <label class="form-control w-full">
                <span class="label-text text-xs">Название</span>
                <input
                  class="input input-sm"
                  :value="commandDraft.name"
                  @input="onCommandName(($event.target as HTMLInputElement).value)"
                />
              </label>
              <label class="form-control w-full">
                <span class="label-text text-xs">ID латиницей</span>
                <input
                  v-model="commandDraft.id"
                  class="input input-sm font-mono"
                  @input="idTouched = true"
                />
              </label>
              <label class="form-control w-full">
                <span class="label-text text-xs">Зачем</span>
                <input v-model="commandDraft.description" class="input input-sm" />
              </label>
              <label class="form-control w-full">
                <span class="label-text text-xs">Команда на машине</span>
                <textarea
                  v-model="commandDraft.shell"
                  class="textarea textarea-sm font-mono text-xs"
                  rows="6"
                  spellcheck="false"
                  placeholder="systemctl restart nginx"
                />
              </label>
              <p class="text-xs text-base-content/55">
                Можно подставить <span class="font-mono" v-text="templateInput" />,
                <span class="font-mono" v-text="templateVars" /> и вывод предыдущего шага
                <span class="font-mono" v-text="templateStepStdout" />.
              </p>
              <label class="form-control w-full max-w-xs">
                <span class="label-text text-xs">Свой таймаут, сек</span>
                <input
                  v-model="commandDraft.timeoutSec"
                  class="input input-sm font-mono"
                  placeholder="как у подключения"
                />
              </label>
              <div class="flex flex-wrap gap-2">
                <button type="submit" class="btn btn-sm">Сохранить команду</button>
                <button type="button" class="btn btn-sm btn-ghost" @click="makeActionFromCommand">
                  Сделать действием
                </button>
                <button
                  v-if="editingId"
                  type="button"
                  class="btn btn-sm btn-ghost text-error"
                  @click="removeCommand(editingId)"
                >
                  Удалить
                </button>
              </div>
            </form>

            <form v-else class="max-w-3xl space-y-3" @submit.prevent="saveAction">
              <h3 class="text-base font-semibold">
                {{ editingId ? "Действие" : "Новое действие" }}
              </h3>
              <p class="text-sm text-base-content/65">
                Навык вызывает действие по id. Команды внутри выполняются по порядку, результат последней
                становится результатом действия.
              </p>
              <p v-if="library.length === 0" class="text-sm text-base-content/65">
                Сначала добавьте команду в библиотеку.
              </p>
              <label class="form-control w-full">
                <span class="label-text text-xs">Название</span>
                <input
                  class="input input-sm"
                  :value="actionDraft.name"
                  @input="onActionName(($event.target as HTMLInputElement).value)"
                />
              </label>
              <label class="form-control w-full">
                <span class="label-text text-xs">ID латиницей</span>
                <input
                  v-model="actionDraft.id"
                  class="input input-sm font-mono"
                  @input="idTouched = true"
                />
              </label>
              <label class="form-control w-full">
                <span class="label-text text-xs">Зачем</span>
                <input v-model="actionDraft.description" class="input input-sm" />
              </label>
              <label class="form-control w-full max-w-xs">
                <span class="label-text text-xs">Подтверждение</span>
                <select v-model="actionDraft.policy" class="select select-sm">
                  <option value="auto">при ошибке — остановить</option>
                  <option value="needs_human">при ошибке — ждать человека</option>
                </select>
              </label>

              <div class="space-y-2">
                <p class="text-xs font-medium text-base-content/50">Команды по порядку</p>
                <div
                  v-for="(commandId, index) in actionDraft.commandIds"
                  :key="`${commandId}-${index}`"
                  class="flex items-center gap-2"
                >
                  <span class="w-12 shrink-0 font-mono text-xs text-base-content/45">run_{{ index + 1 }}</span>
                  <select v-model="actionDraft.commandIds[index]" class="select select-sm min-w-0 flex-1">
                    <option value="">— команда —</option>
                    <option v-for="command in library" :key="command.id" :value="command.id">
                      {{ command.name }}
                    </option>
                  </select>
                  <button type="button" class="btn btn-sm btn-square btn-ghost" aria-label="Выше" @click="moveActionStep(index, -1)">
                    ↑
                  </button>
                  <button type="button" class="btn btn-sm btn-square btn-ghost" aria-label="Ниже" @click="moveActionStep(index, 1)">
                    ↓
                  </button>
                  <button type="button" class="btn btn-sm btn-square btn-ghost" aria-label="Убрать шаг" @click="removeActionStep(index)">
                    ✕
                  </button>
                </div>
                <button type="button" class="btn btn-sm btn-ghost" :disabled="library.length === 0" @click="addActionStep">
                  + команда в действие
                </button>
                <p v-if="actionDraft.commandIds.length" class="text-xs text-base-content/55">
                  Сейчас: {{ actionDraft.commandIds.map((id) => commandName(id) || "…").join(" → ") }}
                </p>
              </div>

              <div class="flex flex-wrap gap-2">
                <button type="submit" class="btn btn-sm" :disabled="library.length === 0">Сохранить действие</button>
                <button
                  v-if="editingId"
                  type="button"
                  class="btn btn-sm btn-ghost text-error"
                  @click="removeAction(editingId)"
                >
                  Удалить
                </button>
              </div>
            </form>
          </section>
        </div>

        <p v-else class="p-4 text-sm text-error">Подключение не найдено</p>
  </PluginSettingsSheet>
</template>
