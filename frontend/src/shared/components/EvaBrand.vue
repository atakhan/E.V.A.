<script setup lang="ts">
withDefaults(
  defineProps<{
    size?: "sm" | "md" | "lg";
    showTagline?: boolean;
    titleClass?: string;
  }>(),
  {
    size: "md",
    showTagline: true,
  },
);

const logoSize = {
  sm: 32,
  md: 44,
  lg: 56,
} as const;
</script>

<template>
  <div class="flex items-center gap-3">
    <img
      src="/eva-logo.png"
      alt=""
      :width="logoSize[size]"
      :height="logoSize[size]"
      class="shrink-0 rounded-lg"
      aria-hidden="true"
    />
    <div class="min-w-0">
      <p :class="['font-semibold tracking-wide', titleClass ?? 'text-2xl']">E.V.A.</p>
      <p v-if="showTagline" class="mt-0.5 text-sm text-base-content/60">
        Engine for Versatile Agents
      </p>
    </div>
  </div>
</template>
