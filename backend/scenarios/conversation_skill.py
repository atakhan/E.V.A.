from __future__ import annotations

import uuid
from datetime import datetime

CONVERSATION_SYSTEM_PROMPT = (
    "Ты ассистент снабженца в приложении ai_supplier. "
    "Отвечай кратко и по делу на русском языке. "
    "Помогаешь с закупками: материалы, заявки, поставщики, сроки, цены. "
    "Если не хватает данных — задай один уточняющий вопрос. "
    "Не выдумывай факты о складе и договорах, которых нет в сообщении пользователя."
)


def build_draft_reply_action(now: str) -> dict:
    """Draft a conversational reply via PolzaAI_LLM."""
    return {
        "id": "draft_reply",
        "name": "Подготовить ответ",
        "description": "Сгенерировать ответ пользователю через PolzaAI_LLM",
        "version": "0.1.0",
        "policy": "auto",
        "inputSchema": {},
        "outputSchema": {},
        "recipe": [
            {
                "id": "draft",
                "tool": "polza_ai_llm",
                "command": "run",
                "input": {
                    "messages": [
                        {"role": "system", "content": CONVERSATION_SYSTEM_PROMPT},
                        {"role": "user", "content": "{{vars.last_message}}"},
                    ],
                    "temperature": 0.3,
                },
            }
        ],
        "createdAt": now,
        "updatedAt": now,
    }


def build_send_reply_action(now: str) -> dict:
    """Send the drafted reply to the ai_supplier UI."""
    return {
        "id": "send_reply",
        "name": "Отправить ответ",
        "description": "Отправить ответ пользователю через web_client",
        "version": "0.1.0",
        "policy": "auto",
        "inputSchema": {},
        "outputSchema": {},
        "recipe": [
            {
                "id": str(uuid.uuid4()),
                "tool": "web_client",
                "command": "send_message",
                "input": {
                    "session_id": "{{vars.conversation_id}}",
                    "text": "{{vars.text}}",
                },
            }
        ],
        "createdAt": now,
        "updatedAt": now,
    }


def build_razgovor_skill(now: str) -> dict:
    """Variant B: IDLE → THINKING → REPLIED conversation FSM."""
    return {
        "id": "razgovor",
        "name": "Разговор",
        "description": "Диалог с пользователем ai_supplier: LLM готовит ответ, web_client отправляет его в UI",
        "version": "1.0.0",
        "createdAt": now,
        "updatedAt": now,
        "initial": "IDLE",
        "params": [{"name": "conversation_id", "type": "string", "required": False}],
        "viewport": {"panX": 0, "panY": 0, "zoom": 1},
        "states": [
            {
                "id": "IDLE",
                "onEnter": [],
                "final": False,
                "transitions": [
                    {
                        "id": str(uuid.uuid4()),
                        "event": "channel.message.received",
                        "guard": "",
                        "actions": ["draft_reply"],
                        "to": "THINKING",
                    }
                ],
                "x": 0,
                "y": 0,
                "width": 160,
                "height": 80,
            },
            {
                "id": "THINKING",
                "onEnter": [],
                "final": False,
                "transitions": [
                    {
                        "id": str(uuid.uuid4()),
                        "event": "action.draft_reply.completed",
                        "guard": "",
                        "actions": ["send_reply"],
                        "to": "REPLIED",
                    }
                ],
                "x": 220,
                "y": 0,
                "width": 160,
                "height": 80,
            },
            {
                "id": "REPLIED",
                "onEnter": [],
                "final": False,
                "transitions": [
                    {
                        "id": str(uuid.uuid4()),
                        "event": "action.send_reply.completed",
                        "guard": "",
                        "actions": [],
                        "to": "IDLE",
                    }
                ],
                "x": 440,
                "y": 0,
                "width": 160,
                "height": 80,
            },
        ],
    }


def conversation_actions(now: str | None = None) -> list[dict]:
    stamp = now or datetime.now().astimezone().isoformat()
    return [
        build_draft_reply_action(stamp),
        build_send_reply_action(stamp),
    ]
