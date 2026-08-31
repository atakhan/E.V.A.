<script setup lang="ts">
import { computed } from "vue";
import type { ToolConfigFieldDef } from "@/features/tools/types/tool";
import { getConfigSchema } from "@/features/tools/utils/instanceConfig";

const props = defineProps<{
  toolTypeId: string;
  modelValue: Record<string, unknown>;
}>();

const emit = defineEmits<{
  "update:modelValue": [value: Record<string, unknown>];
}>();

const fields = computed(() => getConfigSchema(props.toolTypeId));

function patchField(field: ToolConfigFieldDef, raw: string) {
  const next = { ...props.modelValue };
  if (field.type === "integer") {
    next[field.id] = raw === "" ? undefined : Number(raw);
  } else if (field.type === "boolean") {
    next[field.id] = raw === "true";
  } else {
    next[field.id] = raw;
  }
  emit("update:modelValue", next);
}

function fieldValue(field: ToolConfigFieldDef): string {
  const value = props.modelValue[field.id];
  if (value === undefined || value === null) return "";
  return String(value);
}
</script>

<template>
  <div v-if="fields.length" class="space-y-2">
    <label v-for="field in fields" :key="field.id" class="form-control w-full">
      <span class="label-text text-xs">{{ field.ui?.label ?? field.id }}</span>
      <select
        v-if="field.type === 'enum'"
        class="select select-bordered select-sm w-full"
        :value="fieldValue(field)"
        @change="patchField(field, ($event.target as HTMLSelectElement).value)"
      >
        <option value="">—</option>
        <option v-for="option in field.enum ?? []" :key="option" :value="option">
          {{ option || "(пусто)" }}
        </option>
      </select>
      <input
        v-else-if="field.type === 'integer'"
        type="number"
        class="input input-bordered input-sm w-full"
        :value="fieldValue(field)"
        @input="patchField(field, ($event.target as HTMLInputElement).value)"
      />
      <input
        v-else
        class="input input-bordered input-sm w-full font-mono text-xs"
        :value="fieldValue(field)"
        @input="patchField(field, ($event.target as HTMLInputElement).value)"
      />
    </label>
  </div>
  <p v-else class="text-xs text-base-content/50">Нет настроек config для этого типа.</p>
</template>
