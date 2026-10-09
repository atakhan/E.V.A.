# Tool Field Schema — v0.1

> Статус: normative draft. Единый контракт полей для `configSchema` (instance) и `command.inputSchema` / `command.outputSchema`.

Связанные документы: [TOOLS_SDK_SPEC_v0.1.md](./TOOLS_SDK_SPEC_v0.1.md)

---

## 1. ToolFieldDef

Один тип поля для всех schema в Tool manifest:

```yaml
id: text
type: template
required: true
default: null
scope: call          # instance | call
enum: null           # для type=enum
ui:
  label: "Текст"
  placeholder: "{{vars.last_message}}"
  group: "Основное"
```

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | string | Ключ в `config` или `step.input` |
| `type` | string | См. §2 |
| `required` | boolean | Обязательное поле |
| `default` | any | Значение по умолчанию |
| `scope` | `instance` \| `call` | `instance` — config tool instance; `call` — аргумент команды |
| `enum` | string[] | Допустимые значения для `type=enum` |
| `ui` | object | Подсказки для Builder UI |

---

## 2. Типы полей

| type | Runtime тип | UI | Примечание |
|------|-------------|-----|------------|
| `string` | string | input | Обычная строка |
| `template` | string | input + chips | Поддерживает `{{input.*}}`, `{{vars.*}}`, `{{steps.*}}` |
| `text` | string | textarea | Многострочный текст |
| `integer` | int | number input | |
| `boolean` | bool | checkbox | |
| `enum` | string | select | Требует `enum[]` |
| `json` | object/array | textarea monospace | Парсится как JSON |
| `string_array` | string[] | textarea / json | Массив строк |

---

## 3. Где используется

| Schema | Уровень | Пример |
|--------|---------|--------|
| `configSchema` | Tool instance | `polza_ai_llm.config.model` |
| `command.inputSchema` | Recipe step input | `text.replace.pattern` |
| `command.outputSchema` | Документация / validation result | `text.replace.text` |

---

## 4. Валидация (v1)

- **Статическая** — без resolve шаблонов `{{ }}`
- **missing required** → error
- **unknown keys** → warning (strict mode в runtime — error)
- **type mismatch** → error после coerce

---

## 5. UI: форма vs Raw JSON

Builder по умолчанию рендерит **SchemaDrivenForm** из `inputSchema`. Toggle «Raw JSON» — escape hatch для power users.

---

## 6. Пример: text.replace

```yaml
commands:
  - id: replace
    description: "Замена literal/regex"
    inputSchema:
      - id: text
        type: template
        required: true
        scope: call
        ui: { label: "Текст", placeholder: "{{steps.clean.result.text}}" }
      - id: pattern
        type: string
        required: true
        scope: call
        ui: { label: "Pattern" }
      - id: replacement
        type: string
        default: ""
        scope: call
      - id: regex
        type: boolean
        default: false
        scope: call
      - id: flags
        type: string
        scope: call
        ui: { placeholder: "im" }
      - id: count
        type: integer
        default: 0
        scope: call
        ui: { label: "Лимит замен (0 = все)" }
    outputSchema:
      - id: text
        type: string
        scope: call
      - id: replacements
        type: integer
        scope: call
```

---

## 7. Manifest layout

```text
backend/tools/<name>/
├── manifest.py    # TEXT_TOOL_MANIFEST — source of truth
├── tool.py
└── __init__.py
```

Каталог: `definition/catalog/builtin_tools.py` агрегирует manifests.
