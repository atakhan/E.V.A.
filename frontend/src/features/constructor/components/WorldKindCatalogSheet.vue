<script setup lang="ts">
defineProps<{
  open: boolean;
  tools: Array<{ id: string; name: string; description: string }>;
  connectedIds: string[];
}>();

const emit = defineEmits<{
  close: [];
  pick: [toolId: string];
}>();
</script>

<template>
  <Teleport to="body">
    <Transition
      enter-active-class="transition duration-300 ease-out"
      enter-from-class="translate-y-full"
      enter-to-class="translate-y-0"
      leave-active-class="transition duration-200 ease-in"
      leave-from-class="translate-y-0"
      leave-to-class="translate-y-full"
    >
      <div
        v-if="open"
        class="fixed inset-0 z-50 flex flex-col bg-base-100"
        role="dialog"
        aria-modal="true"
        aria-label="Плагины внешнего мира"
      >
        <header class="flex items-start justify-between gap-4 border-b border-base-300 px-6 py-5">
          <div>
            <p class="text-xs uppercase tracking-wide text-base-content/50">Внешний мир</p>
            <h2 class="mt-1 text-xl font-semibold">Добавить канал</h2>
            <p class="mt-1 max-w-xl text-sm text-base-content/60">
              Каналы связи с внешним миром, доступные в E.V.A. Выбранный канал сразу встанет на стол.
              Подключение настраивается по кабелю.
            </p>
          </div>
          <button
            type="button"
            class="btn btn-sm btn-ghost"
            aria-label="Закрыть"
            @click="emit('close')"
          >
            Закрыть
          </button>
        </header>

        <div class="min-h-0 flex-1 overflow-y-auto px-6 py-6">
          <ul class="mx-auto grid max-w-3xl gap-3">
            <li v-for="tool in tools" :key="tool.id">
              <button
                type="button"
                class="flex w-full flex-col items-start rounded-2xl border px-4 py-4 text-left transition"
                :class="
                  connectedIds.includes(tool.id)
                    ? 'cursor-default border-base-300/70 bg-base-200/40 text-base-content/50'
                    : 'border-base-300 bg-base-100 hover:border-primary/50'
                "
                :disabled="connectedIds.includes(tool.id)"
                @click="emit('pick', tool.id)"
              >
                <span class="text-base font-semibold">{{ tool.name }}</span>
                <span v-if="tool.description" class="mt-1 text-sm text-base-content/60">
                  {{ tool.description }}
                </span>
                <span
                  v-if="connectedIds.includes(tool.id)"
                  class="mt-2 text-xs uppercase tracking-wide"
                >
                  Уже на столе
                </span>
              </button>
            </li>
          </ul>
          <p v-if="tools.length === 0" class="text-center text-sm text-base-content/50">
            В E.V.A. пока нет плагинов внешнего мира.
          </p>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
