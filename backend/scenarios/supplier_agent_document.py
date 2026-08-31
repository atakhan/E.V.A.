from __future__ import annotations

import uuid
from datetime import datetime, timezone


def build_supplier_agent_document() -> dict:
    """Agent document for ai_supplier chat via web_client tool."""
    now = datetime.now(timezone.utc).isoformat()
    agent_id = str(uuid.uuid4())
    skill_id = "chat_with_supplier"

    return {
        "id": agent_id,
        "slug": "supplier",
        "name": "AI Supplier Agent",
        "description": "Chat agent for ai_supplier web UI via web_client",
        "createdAt": now,
        "updatedAt": now,
        "tools": [
            {
                "id": str(uuid.uuid4()),
                "toolId": "web_client",
                "enabled": True,
                "configNote": '{"healthPath":"/eva/health","sendMessagePath":"/eva/messages","getSnapshotPath":"/eva/context","authStyle":"bearer","timeoutSec":30}',
            },
        ],
        "actions": [
            {
                "id": "reply_to_user",
                "name": "Reply to supplier user",
                "description": "Echo user message back to ai_supplier chat",
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
                            "text": "Вы написали: {{vars.last_message}}",
                        },
                    }
                ],
                "createdAt": now,
                "updatedAt": now,
            },
        ],
        "skills": [
            {
                "id": skill_id,
                "name": "Chat with supplier",
                "description": "Handle chat commands from ai_supplier UI",
                "version": "1.0.0",
                "createdAt": now,
                "updatedAt": now,
                "initial": "READY",
                "params": [
                    {"name": "conversation_id", "type": "string", "required": False},
                ],
                "viewport": {"panX": 0, "panY": 0, "zoom": 1},
                "states": [
                    {
                        "id": "READY",
                        "onEnter": [],
                        "final": False,
                        "transitions": [
                            {
                                "id": str(uuid.uuid4()),
                                "event": "channel.message.received",
                                "guard": "",
                                "actions": ["reply_to_user"],
                                "to": "READY",
                            }
                        ],
                        "x": 0,
                        "y": 0,
                        "width": 160,
                        "height": 80,
                    }
                ],
            }
        ],
    }
