<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{
  status: string;
}>();

const label = computed(() => {
  switch (props.status) {
    case "running":
      return "running";
    case "waiting":
      return "ждёт событие";
    case "completed":
      return "completed";
    case "error":
      return "error";
    case "cancelled":
      return "cancelled";
    default:
      return props.status;
  }
});

const badgeClass = computed(() => {
  switch (props.status) {
    case "completed":
      return "badge-success";
    case "waiting":
      return "badge-warning";
    case "error":
      return "badge-error";
    case "cancelled":
      return "badge-ghost";
    case "running":
      return "badge-info";
    default:
      return "badge-ghost";
  }
});
</script>

<template>
  <span class="badge badge-sm" :class="badgeClass">{{ label }}</span>
</template>
