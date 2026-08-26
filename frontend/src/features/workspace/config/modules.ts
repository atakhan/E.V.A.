export interface ModuleSection {
  id: string;
  title: string;
  description: string;
  children?: ModuleSection[];
}

export const moduleSections: ModuleSection[] = [
  {
    id: "core",
    title: "Core",
    description: "Моторчики агента: автоматы, задачи, языковая модель и события.",
    children: [
      {
        id: "core.fsm",
        title: "FSM",
        description:
          "Конечные автоматы: деловой (где дело) и агентский (где работа помощника). Правила переходов без самодеятельности модели.",
      },
      {
        id: "core.tasks",
        title: "Tasks",
        description:
          "Менеджер задач: длинные куски работы агента, которые длятся и видны отдельно от одного поступка.",
      },
      {
        id: "core.llm",
        title: "LLM",
        description:
          "Движок языка: розетка для локальной или облачной модели. Читает и пишет по подсказке, не решает дело сам.",
      },
      {
        id: "core.events",
        title: "Events",
        description:
          "Менеджер событий: факты извне (сообщение, подтверждение, счёт). Событие — не задача и не поступок.",
      },
    ],
  },
  {
    id: "tools-and-actions",
    title: "Tools and Actions",
    description:
      "Руки агента и меню разрешённых поступков: что можно сделать и чем это исполнить снаружи.",
  },
  {
    id: "memory-and-knowledges",
    title: "Memory and Knowledges",
    description: "Запасы: опыт, связи между сущностями и живые деловые данные.",
    children: [
      {
        id: "memory.memory",
        title: "Memory",
        description:
          "Тетрадь опыта: привычки людей, типичные отказы, уроки из похожих случаев — не сырые CRM-цифры.",
      },
      {
        id: "memory.entity-graph",
        title: "Entity Graph",
        description:
          "Граф связей: счёт к запросу, позиция в отгрузке к позиции в счёте. Явные и предположенные связи.",
      },
      {
        id: "memory.business-data",
        title: "Business Data",
        description:
          "Живые данные из рабочих систем: заявки, поставщики, остатки, счета — «открой окно и посмотри сейчас».",
      },
    ],
  },
  {
    id: "context-manager",
    title: "Context manager",
    description:
      "Сборщик «что видно сейчас»: порция мира на один шаг с ярлыками откуда каждый кусок.",
  },
  {
    id: "reflection",
    title: "Reflection",
    description:
      "Разбор после работы: кандидаты в урок из дневника и переписки, без превращения одного случая в закон.",
  },
];

export const defaultModuleSectionId = "core.fsm";

export function flattenModuleSections(sections: ModuleSection[]): ModuleSection[] {
  return sections.flatMap((section) =>
    section.children ? [section, ...flattenModuleSections(section.children)] : [section],
  );
}

export function getLeafModuleSectionIds(): string[] {
  return flattenModuleSections(moduleSections)
    .filter((section) => !section.children)
    .map((section) => section.id);
}

export function findModuleSection(id: string): ModuleSection | undefined {
  return flattenModuleSections(moduleSections).find((section) => section.id === id);
}

export function createEmptyApplicationModules(): Record<string, unknown> {
  const modules: Record<string, unknown> = {};
  for (const id of getLeafModuleSectionIds()) {
    modules[id] = id === defaultModuleSectionId ? { canvases: [] } : {};
  }
  return modules;
}
