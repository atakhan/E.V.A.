from __future__ import annotations

from definition.catalog.field_defs import field

_TEXT_IN = field
_TEXT_OUT = lambda fid, **kw: field(fid, scope="call", **kw)

TEXT_TOOL_MANIFEST: dict = {
    "id": "text",
    "name": "Text",
    "description": "Детерминированные операции со строками: trim, regex, split/join.",
    "commands": [
        {
            "id": "trim",
            "description": "Убрать символы с краёв",
            "inputSchema": [
                _TEXT_IN("text", type="template", required=True, label="Текст", placeholder="{{vars.last_message}}"),
                _TEXT_IN("chars", label="Символы для удаления"),
                _TEXT_IN("side", type="enum", enum=["left", "right", "both"], default="both", label="Сторона"),
            ],
            "outputSchema": [_TEXT_OUT("text", type="string")],
        },
        {
            "id": "normalize",
            "description": "Нормализация пробелов и unicode",
            "inputSchema": [
                _TEXT_IN("text", type="template", required=True, label="Текст"),
                _TEXT_IN("collapse_whitespace", type="boolean", default=False, label="Схлопнуть пробелы"),
                _TEXT_IN("strip_empty_lines", type="boolean", default=False, label="Убрать пустые строки"),
                _TEXT_IN("unicode_form", type="enum", enum=["none", "NFC", "NFKC"], default="none"),
                _TEXT_IN("case", type="enum", enum=["none", "lower", "upper"], default="none"),
            ],
            "outputSchema": [_TEXT_OUT("text", type="string")],
        },
        {
            "id": "truncate",
            "description": "Обрезка до max_length",
            "inputSchema": [
                _TEXT_IN("text", type="template", required=True, label="Текст"),
                _TEXT_IN("max_length", type="integer", required=True, label="Макс. длина"),
                _TEXT_IN("suffix", default="…", label="Суффикс"),
                _TEXT_IN("word_boundary", type="boolean", default=False, label="По границе слова"),
            ],
            "outputSchema": [
                _TEXT_OUT("text", type="string"),
                _TEXT_OUT("truncated", type="boolean"),
                _TEXT_OUT("original_length", type="integer"),
            ],
        },
        {
            "id": "match",
            "description": "Regex match + groups",
            "inputSchema": [
                _TEXT_IN("text", type="template", required=True, label="Текст"),
                _TEXT_IN("pattern", required=True, label="Pattern"),
                _TEXT_IN("flags", placeholder="im"),
            ],
            "outputSchema": [
                _TEXT_OUT("matched", type="boolean"),
                _TEXT_OUT("match", type="string"),
                _TEXT_OUT("groups", type="json"),
                _TEXT_OUT("named_groups", type="json"),
            ],
        },
        {
            "id": "extract",
            "description": "Извлечь capture group",
            "inputSchema": [
                _TEXT_IN("text", type="template", required=True, label="Текст"),
                _TEXT_IN("pattern", required=True, label="Pattern"),
                _TEXT_IN("group", default=0, label="Group"),
                _TEXT_IN("flags", placeholder="im"),
                _TEXT_IN("default", label="Default если не найдено"),
            ],
            "outputSchema": [
                _TEXT_OUT("text"),
                _TEXT_OUT("found", type="boolean"),
            ],
        },
        {
            "id": "find_all",
            "description": "Все совпадения regex",
            "inputSchema": [
                _TEXT_IN("text", type="template", required=True, label="Текст"),
                _TEXT_IN("pattern", required=True, label="Pattern"),
                _TEXT_IN("flags", placeholder="im"),
                _TEXT_IN("limit", type="integer", default=100, label="Лимит"),
            ],
            "outputSchema": [
                _TEXT_OUT("matches", type="json"),
                _TEXT_OUT("count", type="integer"),
            ],
        },
        {
            "id": "contains",
            "description": "Проверка вхождения",
            "inputSchema": [
                _TEXT_IN("text", type="template", required=True, label="Текст"),
                _TEXT_IN("needle", required=True, label="Искать"),
                _TEXT_IN("regex", type="boolean", default=False),
                _TEXT_IN("flags", placeholder="im"),
                _TEXT_IN("case_sensitive", type="boolean", default=True),
            ],
            "outputSchema": [_TEXT_OUT("matched", type="boolean")],
        },
        {
            "id": "replace",
            "description": "Замена literal/regex",
            "inputSchema": [
                _TEXT_IN("text", type="template", required=True, label="Текст", placeholder="{{steps.clean.result.text}}"),
                _TEXT_IN("pattern", required=True, label="Pattern"),
                _TEXT_IN("replacement", default="", label="Replacement"),
                _TEXT_IN("regex", type="boolean", default=False),
                _TEXT_IN("flags", placeholder="im"),
                _TEXT_IN("count", type="integer", default=0, label="Лимит замен (0 = все)"),
            ],
            "outputSchema": [
                _TEXT_OUT("text", type="string"),
                _TEXT_OUT("replacements", type="integer"),
            ],
        },
        {
            "id": "remove_lines",
            "description": "Удалить строки по regex",
            "inputSchema": [
                _TEXT_IN("text", type="template", required=True, label="Текст"),
                _TEXT_IN("pattern", required=True, label="Pattern (на строку)"),
                _TEXT_IN("flags", default="m"),
                _TEXT_IN("invert", type="boolean", default=False),
            ],
            "outputSchema": [
                _TEXT_OUT("text", type="string"),
                _TEXT_OUT("removed_count", type="integer"),
            ],
        },
        {
            "id": "split",
            "description": "Разбить строку",
            "inputSchema": [
                _TEXT_IN("text", type="template", required=True, label="Текст"),
                _TEXT_IN("separator", default="\n", label="Separator"),
                _TEXT_IN("regex", type="boolean", default=False),
                _TEXT_IN("limit", type="integer", default=0),
                _TEXT_IN("trim_parts", type="boolean", default=True),
                _TEXT_IN("skip_empty", type="boolean", default=False),
            ],
            "outputSchema": [
                _TEXT_OUT("parts", type="json"),
                _TEXT_OUT("count", type="integer"),
            ],
        },
        {
            "id": "join",
            "description": "Склеить массив строк",
            "inputSchema": [
                _TEXT_IN("parts", type="json", required=True, label="Parts (JSON array)"),
                _TEXT_IN("separator", default="\n", label="Separator"),
                _TEXT_IN("skip_empty", type="boolean", default=True),
            ],
            "outputSchema": [_TEXT_OUT("text", type="string")],
        },
    ],
    "events": [],
    "states": [],
}
