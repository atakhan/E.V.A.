<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import AgentForm from "@/features/agents/components/AgentForm.vue";
import { useAgents } from "@/features/agents/composables/useAgents";
import type { Agent } from "@/features/agents/types/agent";
import { agentHomePath, agentSectionPath } from "@/router/paths";
import { findWorkspaceSection } from "@/features/workspace/config/nav";

const props = defineProps<{
  agent?: Agent | null;
  mode: "create" | "edit";
}>();

const emit = defineEmits<{
  saved: [agent: Agent];
  closed: [];
}>();

const route = useRoute();
const router = useRouter();
const { createAgent, updateAgent, suggestUniqueAgentSlug } = useAgents();

const isOpen = ref(false);
const formName = ref("");
const formSlug = ref("");
const formDescription = ref("");
const formError = ref<string | null>(null);
const slugTouched = ref(false);
const connectTelegram = ref(false);
const telegramToken = ref("");
const telegramCredentialName = ref("Telegram bot");
const saving = ref(false);

const title = computed(() =>
  props.mode === "create" ? "Новый агент" : "Редактировать агента",
);

const submitLabel = computed(() => (props.mode === "create" ? "Создать" : "Сохранить"));

function resetFromAgent(agent: Agent | null | undefined) {
  formName.value = agent?.name ?? "";
  formSlug.value = agent?.slug ?? "";
  formDescription.value = agent?.description ?? "";
  formError.value = null;
  slugTouched.value = false;
  connectTelegram.value = false;
  telegramToken.value = "";
  telegramCredentialName.value = "Telegram bot";
  saving.value = false;
}

function open() {
  resetFromAgent(props.agent);
  if (props.mode === "create") {
    formSlug.value = suggestUniqueAgentSlug("agent");
  }
  isOpen.value = true;
}

function close() {
  isOpen.value = false;
  formError.value = null;
  emit("closed");
}

watch(
  () => props.agent,
  (agent) => {
    if (isOpen.value) {
      resetFromAgent(agent);
    }
  },
);

watch(formName, (name) => {
  if (props.mode !== "create" || !isOpen.value || slugTouched.value) return;
  formSlug.value = suggestUniqueAgentSlug(name || "agent");
});

async function save() {
  formError.value = null;
  saving.value = true;

  try {
    if (props.mode === "create") {
      const result = await createAgent({
        name: formName.value,
        slug: formSlug.value,
        description: formDescription.value,
        telegram: connectTelegram.value
          ? {
              botToken: telegramToken.value,
              credentialName: telegramCredentialName.value,
            }
          : undefined,
      });

      if (!result.ok) {
        formError.value = result.error;
        return;
      }

      close();
      emit("saved", result.agent);
      await router.push(agentHomePath(result.agent.slug));
      return;
    }

    if (!props.agent) return;

    const previousSlug = props.agent.slug;
    const result = updateAgent(props.agent.id, {
      name: formName.value,
      slug: formSlug.value,
      description: formDescription.value,
    });

    if (!result.ok) {
      formError.value = result.error;
      return;
    }

    close();
    emit("saved", result.agent);

    if (result.agent.slug !== previousSlug && route.params.agentSlug === previousSlug) {
      const section =
        findWorkspaceSection(String(route.path.split("/").filter(Boolean)[1] ?? ""))?.slug ??
        "overview";
      await router.replace(agentSectionPath(result.agent.slug, section));
    }
  } finally {
    saving.value = false;
  }
}

defineExpose({ open, close });
</script>

<template>
  <dialog class="modal" :class="{ 'modal-open': isOpen }">
    <div class="modal-box">
      <h3 class="text-lg font-semibold">{{ title }}</h3>

      <div class="mt-4">
        <AgentForm
          v-model:name="formName"
          v-model:slug="formSlug"
          v-model:description="formDescription"
          :error="formError"
          @slug-input="slugTouched = true"
        />

        <div
          v-if="mode === 'create'"
          class="mt-4 space-y-3 rounded-xl border border-base-300 bg-base-200/20 p-4"
        >
          <label class="label cursor-pointer justify-start gap-3 p-0">
            <input v-model="connectTelegram" type="checkbox" class="checkbox checkbox-sm" />
            <span class="label-text font-medium">Подключить Telegram</span>
          </label>

          <template v-if="connectTelegram">
            <label class="form-control w-full">
              <span class="label-text">Bot token</span>
              <input
                v-model="telegramToken"
                type="password"
                class="input input-bordered input-sm w-full font-mono"
                placeholder="123456:ABC..."
                autocomplete="off"
              />
            </label>
            <label class="form-control w-full">
              <span class="label-text">Название credential</span>
              <input
                v-model="telegramCredentialName"
                class="input input-bordered input-sm w-full"
                placeholder="Production bot"
              />
            </label>
            <p class="text-xs text-base-content/55">
              Token сохраняется на backend в credentials, не в draft агента.
            </p>
          </template>
        </div>
      </div>

      <div class="modal-action">
        <button type="button" class="btn btn-ghost" :disabled="saving" @click="close">
          Отмена
        </button>
        <button type="button" class="btn" :disabled="saving" @click="save">
          {{ saving ? "Сохранение…" : submitLabel }}
        </button>
      </div>
    </div>
    <form method="dialog" class="modal-backdrop" @submit.prevent="close">
      <button type="submit">close</button>
    </form>
  </dialog>
</template>
