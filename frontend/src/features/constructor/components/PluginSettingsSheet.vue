<script setup lang="ts">
import { onMounted, onUnmounted, ref } from "vue";

defineProps<{
  labelledBy?: string;
}>();

const emit = defineEmits<{
  close: [];
}>();

/** EvaHomeLink sits at `top-4` and is `size-11`. The sheet starts at the logo midline. */
const sheetTop = "calc(1rem + 2.75rem / 2)";

const visible = ref(true);

function requestClose() {
  visible.value = false;
}

function onAfterLeave() {
  emit("close");
}

function onKeydown(event: KeyboardEvent) {
  if (event.key !== "Escape" || !visible.value) return;
  event.preventDefault();
  requestClose();
}

defineExpose({ requestClose });

onMounted(() => {
  document.addEventListener("keydown", onKeydown);
});

onUnmounted(() => {
  document.removeEventListener("keydown", onKeydown);
});
</script>

<template>
  <Teleport to="body">
    <Transition
      appear
      enter-active-class="transition duration-300 ease-out motion-reduce:duration-0"
      enter-from-class="translate-y-16 opacity-0"
      enter-to-class="translate-y-0 opacity-100"
      leave-active-class="transition duration-300 ease-in motion-reduce:duration-0"
      leave-from-class="translate-y-0 opacity-100"
      leave-to-class="translate-y-16 opacity-0"
      @after-leave="onAfterLeave"
    >
      <section
        v-if="visible"
        class="fixed inset-x-0 bottom-0 z-30 flex flex-col overflow-hidden border-t border-base-300 bg-base-100 pt-12 shadow-2xl"
        :style="{ top: sheetTop }"
        role="dialog"
        data-canvas-ui
        :aria-labelledby="labelledBy"
      >
        <slot />
      </section>
    </Transition>
  </Teleport>
</template>
