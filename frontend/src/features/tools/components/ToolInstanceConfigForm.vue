<script setup lang="ts">
import { computed } from "vue";
import SchemaDrivenForm from "@/shared/schema/SchemaDrivenForm.vue";
import { getConfigSchema } from "@/features/tools/utils/instanceConfig";

const props = defineProps<{
  toolTypeId: string;
  modelValue: Record<string, unknown>;
}>();

const emit = defineEmits<{
  "update:modelValue": [value: Record<string, unknown>];
}>();

const fields = computed(() => getConfigSchema(props.toolTypeId));
</script>

<template>
  <SchemaDrivenForm
    v-if="fields.length"
    :fields="fields"
    :model-value="modelValue"
    @update:model-value="emit('update:modelValue', $event)"
  />
  <p v-else class="text-xs text-base-content/50">Нет настроек config для этого типа.</p>
</template>
