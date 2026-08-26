<script setup lang="ts">
import { computed } from "vue";
import { agentUriPreview } from "@/shared/utils/agentSlug";

const name = defineModel<string>("name", { required: true });
const slug = defineModel<string>("slug", { required: true });
const description = defineModel<string>("description", { required: true });

defineProps<{
  error?: string | null;
}>();

const emit = defineEmits<{
  slugInput: [];
}>();

const slugPreview = computed(() => agentUriPreview(slug.value));
</script>

<template>
  <div class="space-y-3">
    <label class="form-control w-full">
      <span class="label-text">Название</span>
      <input
        v-model="name"
        class="input input-bordered w-full"
        placeholder="Например, Снабжение"
      />
    </label>

    <label class="form-control w-full">
      <span class="label-text">Agent name (URI)</span>
      <input
        v-model="slug"
        class="input input-bordered w-full font-mono"
        placeholder="supply"
        @input="emit('slugInput')"
      />
      <span class="label-text-alt mt-1 font-mono text-xs">{{ slugPreview }}</span>
    </label>

    <label class="form-control w-full">
      <span class="label-text">Описание</span>
      <textarea
        v-model="description"
        class="textarea textarea-bordered w-full"
        rows="3"
        placeholder="Кратко о назначении агента"
      />
    </label>

    <p v-if="error" class="text-sm text-error">{{ error }}</p>
  </div>
</template>
