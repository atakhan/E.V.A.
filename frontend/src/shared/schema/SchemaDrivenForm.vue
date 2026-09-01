<script setup lang="ts">
import { computed } from "vue";
import type { ToolFieldDef } from "@/features/tools/types/tool";
import { fieldValuesToObject, objectToFieldValues } from "@/shared/schema/fieldSchema";

const props = defineProps<{
  fields: ToolFieldDef[];
  modelValue: Record<string, unknown>;
  showBooleanAsCheckbox?: boolean;
}>();

const emit = defineEmits<{
  "update:modelValue": [value: Record<string, unknown>];
}>();

const values = computed(() => objectToFieldValues(props.fields, props.modelValue));

function patchField(field: ToolFieldDef, raw: string | boolean) {
  const nextValues = { ...values.value };
  if (typeof raw === "boolean") {
    nextValues[field.id] = String(raw);
  } else {
    nextValues[field.id] = raw;
  }
  emit("update:modelValue", fieldValuesToObject(props.fields, nextValues));
}

function fieldLabel(field: ToolFieldDef): string {
  return field.ui?.label ?? field.id;
}

function fieldPlaceholder(field: ToolFieldDef): string {
  return field.ui?.placeholder ?? "";
}
</script>

<template>
  <div class="space-y-2">
    <label v-for="field in fields" :key="field.id" class="form-control w-full">
      <span class="label-text text-xs">{{ fieldLabel(field) }}</span>
      <input
        v-if="field.type === 'boolean'"
        type="checkbox"
        class="checkbox checkbox-sm"
        :checked="modelValue[field.id] === true || modelValue[field.id] === 'true'"
        @change="patchField(field, ($event.target as HTMLInputElement).checked)"
      />
      <select
        v-else-if="field.type === 'enum'"
        class="select select-bordered select-sm w-full font-mono text-xs"
        :value="String(modelValue[field.id] ?? '')"
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
        class="input input-bordered input-sm w-full font-mono text-xs"
        :value="String(modelValue[field.id] ?? '')"
        :placeholder="fieldPlaceholder(field)"
        @input="patchField(field, ($event.target as HTMLInputElement).value)"
      />
      <textarea
        v-else-if="field.type === 'json' || field.type === 'text' || field.type === 'string_array'"
        class="textarea textarea-bordered textarea-sm w-full font-mono text-xs"
        rows="2"
        :value="values[field.id] ?? ''"
        :placeholder="fieldPlaceholder(field)"
        @input="patchField(field, ($event.target as HTMLTextAreaElement).value)"
      />
      <input
        v-else
        class="input input-bordered input-sm w-full font-mono text-xs"
        :value="values[field.id] ?? ''"
        :placeholder="fieldPlaceholder(field)"
        @input="patchField(field, ($event.target as HTMLInputElement).value)"
      />
    </label>
  </div>
</template>
