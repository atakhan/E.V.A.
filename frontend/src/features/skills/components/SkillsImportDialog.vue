<script setup lang="ts">
import { computed, ref } from "vue";
import { useRouter } from "vue-router";
import { useAgents } from "@/features/agents/composables/useAgents";
import { useSkills } from "@/features/skills/composables/useSkills";
import { previewSkillPack } from "@/features/skills/utils/skillPackImport";
import { skillPath } from "@/router/paths";

const props = defineProps<{
  agentSlug: string;
}>();

const emit = defineEmits<{
  close: [];
}>();

const router = useRouter();
const { getAgentBySlug } = useAgents();
const { importSkillPack } = useSkills();

const open = ref(true);
const preview = ref<ReturnType<typeof previewSkillPack> | null>(null);
const onConflict = ref<"skip" | "replace">("skip");
const importing = ref(false);
const selectedFiles = ref<File[]>([]);

const agent = computed(() => getAgentBySlug(props.agentSlug));

async function onFilesSelected(event: Event) {
  const input = event.target as HTMLInputElement;
  const files = [...(input.files ?? [])];
  selectedFiles.value = files;
  if (!agent.value || files.length === 0) {
    preview.value = null;
    return;
  }
  const packFiles = await Promise.all(
    files.map(async (file) => ({
      fileName: file.name,
      content: await file.text(),
    })),
  );
  preview.value = previewSkillPack(packFiles, agent.value);
}

const importCount = computed(() => {
  if (!preview.value) return 0;
  return preview.value.entries.filter((entry) => {
    if (!entry.skill || entry.error) return false;
    if (entry.conflict && onConflict.value === "skip") return false;
    return true;
  }).length;
});

async function runImport(openFirst = false) {
  if (!preview.value || importCount.value === 0) return;
  importing.value = true;
  try {
    const skills = importSkillPack(props.agentSlug, preview.value.entries, {
      onConflict: onConflict.value,
    });
    emit("close");
    open.value = false;
    if (openFirst && skills[0]) {
      await router.push(skillPath(props.agentSlug, skills[0].id));
    }
  } finally {
    importing.value = false;
  }
}

function close() {
  open.value = false;
  emit("close");
}
</script>

<template>
  <dialog class="modal" :class="{ 'modal-open': open }">
    <div class="modal-box max-w-4xl">
      <h3 class="text-lg font-semibold">Import skills pack</h3>
      <p class="mt-1 text-sm text-base-content/60">
        Загрузите один или несколько <span class="font-mono">.yaml</span> / <span class="font-mono">.yml</span>.
        Missing actions отображаются в preview — заглушки не создаются.
      </p>

      <input
        type="file"
        class="file-input file-input-bordered file-input-sm mt-4 w-full"
        accept=".yaml,.yml"
        multiple
        @change="onFilesSelected"
      />

      <div v-if="preview" class="mt-4 space-y-3">
        <label class="flex items-center gap-2 text-sm">
          <span class="text-base-content/60">При конфликте id:</span>
          <select v-model="onConflict" class="select select-bordered select-xs">
            <option value="skip">Пропустить</option>
            <option value="replace">Заменить</option>
          </select>
        </label>

        <div class="overflow-x-auto rounded-xl border border-base-300">
          <table class="table table-sm">
            <thead>
              <tr>
                <th>Файл</th>
                <th>Skill id</th>
                <th>States</th>
                <th>Missing actions</th>
                <th>Warnings</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="entry in preview.entries"
                :key="entry.fileName"
                :class="entry.error ? 'bg-error/5' : ''"
              >
                <td class="font-mono text-xs">{{ entry.fileName }}</td>
                <td class="font-mono text-xs">
                  {{ entry.skillId }}
                  <span v-if="entry.conflict" class="badge badge-xs badge-warning ml-1">conflict</span>
                </td>
                <td>{{ entry.error ? "—" : entry.statesCount }}</td>
                <td class="text-xs">
                  <span v-if="entry.error" class="text-error">{{ entry.error }}</span>
                  <span v-else-if="entry.missingActionIds.length" class="text-error font-mono">
                    {{ entry.missingActionIds.join(", ") }}
                  </span>
                  <span v-else class="text-success">—</span>
                </td>
                <td class="text-xs text-warning">
                  {{ entry.warnings.join("; ") || "—" }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="modal-action">
        <button type="button" class="btn btn-ghost" @click="close">Отмена</button>
        <button
          type="button"
          class="btn"
          :disabled="importing || importCount === 0"
          @click="runImport(false)"
        >
          {{ importing ? "Импорт…" : `Импортировать ${importCount}` }}
        </button>
        <button
          type="button"
          class="btn btn-primary"
          :disabled="importing || importCount === 0"
          @click="runImport(true)"
        >
          Импорт и открыть
        </button>
      </div>
    </div>
    <form method="dialog" class="modal-backdrop" @submit.prevent="close">
      <button type="submit">close</button>
    </form>
  </dialog>
</template>
