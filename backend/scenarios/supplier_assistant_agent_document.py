from __future__ import annotations

import uuid
from datetime import datetime, timezone

from scenarios.conversation_skill import (
    build_razgovor_skill,
    conversation_actions,
)
from scenarios.supplier_agent_document import build_supplier_agent_document


def build_supplier_assistant_agent_document() -> dict:
    """Agent document for ai_supplier assistant: conversation + workspace CRM events."""
    now = datetime.now(timezone.utc).isoformat()
    supplier_doc = build_supplier_agent_document()

    workspace_actions = [
        action
        for action in supplier_doc["actions"]
        if action["id"] in ("parse_request", "confirm_request")
    ]
    workspace_skill = next(
        skill for skill in supplier_doc["skills"] if skill["id"] == "process_supplier_request"
    )

    web_config = (
        '{"healthPath":"/eva/health","sendMessagePath":"/eva/messages",'
        '"getSnapshotPath":"/eva/context","authStyle":"bearer","timeoutSec":30}'
    )

    return {
        "id": str(uuid.uuid4()),
        "slug": "supplier-agent",
        "name": "Ассистент снабженца",
        "description": (
            "ИИ-агент снабжения для ai_supplier: диалог с оператором и "
            "обработка событий workspace через web_client"
        ),
        "defaultSkillId": "razgovor",
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
        "actions": conversation_actions(now) + workspace_actions,
        "skills": [
            build_razgovor_skill(now),
            workspace_skill,
        ],
    }
