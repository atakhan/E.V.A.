"""Агент письма заказчику по сдерживающему фактору.

Стол — СОУС. Агент не считает очередь и не отправляет почту.
Числа остова приходят в событии (их посчитала очередь захватки).
Модель пишет только текст. Список правил в этом срезе пустой.

Вход черновика — жест стола ``ui.request.parse_requested``
(тот же, что у разбора заявки; отдельный тип события диспетчер не ждёт).

Payload:

- conversation_id: ``sous:object:<object_id>``
- factor_id, entity_id, request_id: один и тот же id фактора
- object_name, section_name, work_name
- factor_title, factor_description
- planned_days, work_start, work_finish_before, work_finish_after
- instruction: суждение на это письмо, может быть пустым

Решение человека — ``human.request.reviewed`` с тем же conversation_id
и тем же factor_id / entity_id / request_id.

- decision ``approve`` | ``correct`` | ``defer``
- letter_text: письмо, как его оставил человек

``approve`` просит стол записать письмо при факторе (``workspace_update``
entity ``letter``, status ``recorded``) и завершает дело.
``correct`` и ``defer`` оставляют дело ждать. Почту наружу стол шлёт сам.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

_LETTER_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "text": {"type": "string"},
    },
    "required": ["text"],
    "additionalProperties": False,
}

_SYSTEM = (
    "Ты пишешь письмо заказчику о сдвиге одной работы из-за сдерживающего фактора. "
    "Верни только текст письма в поле text. "
    "Имена, даты и число дней бери из блока «Факты» и не меняй их. "
    "Не упоминай следующие работы захватки. Не называй новую дату сдачи объекта. "
    "Не выдумывай номер договора, адресата и причины сверх описания фактора. "
    "Инструкция на это письмо меняет формулировку и не меняет факты. "
    "Если снимок стола расходится с фактами, верны факты."
)


def _user_prompt() -> str:
    return (
        "Факты:\n"
        "Объект: {{vars.object_name}}\n"
        "Захватка: {{vars.section_name}}\n"
        "Работа: {{vars.work_name}}\n"
        "Фактор: {{vars.factor_title}}\n"
        "Описание: {{vars.factor_description}}\n"
        "Сдвиг работы, дней: {{vars.planned_days}}\n"
        "Начало работы: {{vars.work_start}}\n"
        "Окончание до фактора: {{vars.work_finish_before}}\n"
        "Окончание после фактора: {{vars.work_finish_after}}\n"
        "Инструкция на это письмо: {{vars.instruction}}\n\n"
        "Снимок стола:\n"
        "{{vars._desk_text}}"
    )


def _skeleton_patch(*, status: str) -> dict:
    return {
        "entity": "letter",
        "id": "{{vars.factor_id}}",
        "patch": {
            "status": status,
            "text": "{{vars.letter_text}}",
            "factor_id": "{{vars.factor_id}}",
            "object_name": "{{vars.object_name}}",
            "section_name": "{{vars.section_name}}",
            "work_name": "{{vars.work_name}}",
            "factor_title": "{{vars.factor_title}}",
            "planned_days": "{{vars.planned_days}}",
            "work_start": "{{vars.work_start}}",
            "work_finish_before": "{{vars.work_finish_before}}",
            "work_finish_after": "{{vars.work_finish_after}}",
        },
    }


def _action(now: str, *, action_id: str, name: str, description: str, recipe: list[dict]) -> dict:
    return {
        "id": action_id,
        "name": name,
        "description": description,
        "version": "0.1.0",
        "policy": "auto",
        "inputSchema": {},
        "outputSchema": {},
        "recipe": recipe,
        "createdAt": now,
        "updatedAt": now,
    }


def _step(step_id: str, tool: str, command: str, step_input: dict) -> dict:
    return {
        "id": step_id,
        "tool": tool,
        "command": command,
        "input": step_input,
    }


def _state(
    state_id: str,
    *,
    x: int,
    transitions: list[dict],
    final: bool = False,
) -> dict:
    return {
        "id": state_id,
        "onEnter": [],
        "final": final,
        "transitions": transitions,
        "x": x,
        "y": 0,
        "width": 200,
        "height": 88,
    }


def _transition(event: str, *, actions: list[str], to: str, guard: str = "") -> dict:
    return {
        "id": str(uuid.uuid4()),
        "event": event,
        "guard": guard,
        "actions": actions,
        "to": to,
    }


def build_letter_agent_document() -> dict:
    """Agent document: one skill, draft from a factor, human decides."""
    now = datetime.now(timezone.utc).isoformat()
    web_config = (
        '{"healthPath":"/eva/health","sendMessagePath":"/eva/messages",'
        '"getSnapshotPath":"/eva/context","authStyle":"bearer","timeoutSec":30}'
    )
    return {
        "id": str(uuid.uuid4()),
        "slug": "sous-letter",
        "name": "Письмо заказчику",
        "description": (
            "Черновик письма по сдерживающему фактору в СОУС. "
            "Остов (работа, захватка, дни, даты) приходит со стола. "
            "Модель пишет текст. Человек подтверждает, правит или откладывает."
        ),
        "defaultSkillId": "compose_letter",
        "createdAt": now,
        "updatedAt": now,
        "tools": [
            {
                "id": "web_client",
                "toolId": "web_client",
                "name": "Web Client",
                "enabled": True,
                "configNote": web_config,
            },
            {
                "id": "polza_ai_llm",
                "toolId": "polza_ai_llm",
                "name": "PolzaAI_LLM",
                "enabled": True,
                "configNote": '{"model":"openai/gpt-4o-mini"}',
            },
        ],
        "actions": [
            _action(
                now,
                action_id="compose_draft",
                name="Собрать черновик письма",
                description="Снимок стола, текст письма по фактам остова, предложение на стол.",
                recipe=[
                    _step(
                        "snapshot",
                        "web_client",
                        "get_snapshot",
                        {"session_id": "{{vars.conversation_id}}"},
                    ),
                    _step(
                        "write",
                        "polza_ai_llm",
                        "run_structured",
                        {
                            "model": "openai/gpt-4o-mini",
                            "temperature": "0.2",
                            "schema_name": "letter_draft",
                            "schema": _LETTER_SCHEMA,
                            "messages": [
                                {"role": "system", "content": _SYSTEM},
                                {"role": "user", "content": _user_prompt()},
                            ],
                        },
                    ),
                    _step(
                        "propose",
                        "web_client",
                        "send_message",
                        {
                            "session_id": "{{vars.conversation_id}}",
                            "text": "{{steps.write.result.structured.text}}",
                            "ui_proposal": {
                                "kind": "letter_draft",
                                "factor_id": "{{vars.factor_id}}",
                                "rules_applied": [],
                                "instruction": "{{vars.instruction}}",
                                "text": "{{steps.write.result.structured.text}}",
                                "skeleton": {
                                    "object_name": "{{vars.object_name}}",
                                    "section_name": "{{vars.section_name}}",
                                    "work_name": "{{vars.work_name}}",
                                    "factor_title": "{{vars.factor_title}}",
                                    "factor_description": "{{vars.factor_description}}",
                                    "planned_days": "{{vars.planned_days}}",
                                    "work_start": "{{vars.work_start}}",
                                    "work_finish_before": "{{vars.work_finish_before}}",
                                    "work_finish_after": "{{vars.work_finish_after}}",
                                },
                            },
                        },
                    ),
                ],
            ),
            _action(
                now,
                action_id="record_letter",
                name="Записать письмо",
                description="Попросить стол сохранить подтверждённое письмо при факторе.",
                recipe=[
                    _step(
                        "record",
                        "web_client",
                        "send_message",
                        {
                            "session_id": "{{vars.conversation_id}}",
                            "text": "{{vars.letter_text}}",
                            "workspace_update": _skeleton_patch(status="recorded"),
                        },
                    )
                ],
            ),
            _action(
                now,
                action_id="note_correction",
                name="Записать правку",
                description="Черновик изменён и снова ждёт человека.",
                recipe=[
                    _step(
                        "note",
                        "web_client",
                        "send_message",
                        {
                            "session_id": "{{vars.conversation_id}}",
                            "text": "{{vars.letter_text}}",
                            "workspace_update": _skeleton_patch(status="draft"),
                        },
                    )
                ],
            ),
            _action(
                now,
                action_id="defer_letter",
                name="Отложить письмо",
                description="Черновик остаётся в очереди.",
                recipe=[
                    _step(
                        "defer",
                        "web_client",
                        "send_message",
                        {
                            "session_id": "{{vars.conversation_id}}",
                            "text": "{{vars.letter_text}}",
                            "workspace_update": _skeleton_patch(status="deferred"),
                        },
                    )
                ],
            ),
        ],
        "skills": [
            {
                "id": "compose_letter",
                "name": "Составить письмо",
                "description": "Один фактор → черновик на столе → запись при факторе.",
                "version": "1.0.0",
                "createdAt": now,
                "updatedAt": now,
                "initial": "queued",
                "params": [
                    {"name": "conversation_id", "type": "string", "required": True},
                    {"name": "factor_id", "type": "string", "required": True},
                ],
                "viewport": {"panX": 0, "panY": 0, "zoom": 1},
                "states": [
                    _state(
                        "queued",
                        x=0,
                        transitions=[
                            _transition(
                                "ui.request.parse_requested",
                                actions=["compose_draft"],
                                to="waiting_for_human",
                            )
                        ],
                    ),
                    _state(
                        "waiting_for_human",
                        x=280,
                        transitions=[
                            _transition(
                                "human.request.reviewed",
                                guard="payload.decision == 'approve'",
                                actions=["record_letter"],
                                to="recorded",
                            ),
                            _transition(
                                "human.request.reviewed",
                                guard="payload.decision == 'correct'",
                                actions=["note_correction"],
                                to="waiting_for_human",
                            ),
                            _transition(
                                "human.request.reviewed",
                                guard="payload.decision == 'defer'",
                                actions=["defer_letter"],
                                to="waiting_for_human",
                            ),
                        ],
                    ),
                    _state("recorded", x=560, transitions=[], final=True),
                ],
            }
        ],
    }
