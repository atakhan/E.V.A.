<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import type { RuntimeRunResponse } from "@/features/runtime/types/runtime";
import { agentLogsPath } from "@/router/paths";

const props = defineProps<{
  agentSlug: string;
  run: RuntimeRunResponse;
  isTerminal: boolean;
  cancelling?: boolean;
}>();

const emit = defineEmits<{
  cancel: [];
}>();

const router = useRouter();
const confirmOpen = ref(false);

function openLogs() {
  void router.push(agentLogsPath(props.agentSlug, { skillRunId: props.run.skillRunId }));
}

async function copyRunId() {
  await navigator.clipboard.writeText(props.run.skillRunId);
}

function requestCancel() {
  confirmOpen.value = true;
}

function confirmCancel() {
  confirmOpen.value = false;
  emit("cancel");
}
</script>

<template>
  <div class="flex flex-wrap gap-2">
    <button type="button" class="btn btn-sm btn-ghost" @click="copyRunId">
      Copy run id
    </button>
    <button type="button" class="btn btn-sm btn-ghost" @click="openLogs">
      Все логи run →
    </button>
    <button
      type="button"
      class="btn btn-sm btn-error btn-outline"
      :disabled="isTerminal || cancelling"
      @click="requestCancel"
    >
      {{ cancelling ? "Отмена…" : "Cancel run" }}
    </button>
  </div>

  <dialog class="modal" :class="{ 'modal-open': confirmOpen }">
    <div class="modal-box">
      <h3 class="text-lg font-semibold">Отменить skill run?</h3>
      <p class="mt-2 text-sm text-base-content/70">
        Run будет помечен как cancelled. Уже выполненные side effects не откатываются.
      </p>
      <div class="modal-action">
        <button type="button" class="btn btn-ghost" @click="confirmOpen = false">Назад</button>
        <button type="button" class="btn btn-error" @click="confirmCancel">Отменить run</button>
      </div>
    </div>
    <form method="dialog" class="modal-backdrop" @submit.prevent="confirmOpen = false">
      <button type="submit">close</button>
    </form>
  </dialog>
</template>
