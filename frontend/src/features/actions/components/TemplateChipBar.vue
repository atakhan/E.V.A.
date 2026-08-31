<script setup lang="ts">
import { COMMON_TEMPLATE_TOKENS, insertAtCursor } from "@/features/actions/utils/templateTokens";

const props = defineProps<{
  stepIds?: string[];
}>();

const extraTokens = () =>
  (props.stepIds ?? []).map((id) => `{{steps.${id}.result}}`);

function onChip(token: string, event: MouseEvent) {
  const target = event.currentTarget as HTMLElement;
  const field = target.closest("label")?.querySelector("input,textarea") as
    | HTMLInputElement
    | HTMLTextAreaElement
    | null;
  if (field) insertAtCursor(field, token);
}
</script>

<template>
  <div class="flex flex-wrap gap-1">
    <button
      v-for="token in COMMON_TEMPLATE_TOKENS"
      :key="token"
      type="button"
      class="badge badge-ghost badge-sm font-mono"
      @click="onChip(token, $event)"
    >
      {{ token }}
    </button>
    <button
      v-for="token in extraTokens()"
      :key="token"
      type="button"
      class="badge badge-ghost badge-sm font-mono"
      @click="onChip(token, $event)"
    >
      {{ token }}
    </button>
  </div>
</template>
