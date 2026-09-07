from __future__ import annotations

import uuid
from datetime import datetime, timezone


def build_supplier_agent_document() -> dict:
    """Agent document for ai_supplier: chat + workspace CRM events."""
    now = datetime.now(timezone.utc).isoformat()
    agent_id = str(uuid.uuid4())

    web_config = (
        '{"healthPath":"/eva/health","sendMessagePath":"/eva/messages",'
        '"getSnapshotPath":"/eva/context","authStyle":"bearer","timeoutSec":30}'
    )

    return {
        "id": agent_id,
        "slug": "supplier",
        "name": "AI Supplier Agent",
        "description": "Chat and workspace orchestration for ai_supplier",
        "defaultSkillId": "chat_with_supplier",
        "createdAt": now,
        "updatedAt": now,
        "tools": [
            {
                "id": str(uuid.uuid4()),
                "toolId": "web_client",
                "enabled": True,
                "configNote": web_config,
            },
        ],
        "actions": [
            {
                "id": "reply_to_user",
                "name": "Reply to supplier user",
                "description": "Echo chat message to ai_supplier UI",
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
                            "text": "{{vars.last_message}}",
                        },
                    }
                ],
                "createdAt": now,
                "updatedAt": now,
            },
            {
                "id": "parse_request",
                "name": "Parse request",
                "description": "Mark request as parsed and notify UI",
                "version": "0.1.0",
                "policy": "auto",
                "inputSchema": {},
                "outputSchema": {},
                "recipe": [
                    {
                        "id": str(uuid.uuid4()),
                        "tool": "web_client",
                        "command": "get_snapshot",
                        "input": {"session_id": "{{vars.conversation_id}}"},
                    },
                    {
                        "id": str(uuid.uuid4()),
                        "tool": "web_client",
                        "command": "send_message",
                        "input": {
                            "session_id": "{{vars.conversation_id}}",
                            "text": "Запрос {{vars.request_id}} разобран и отправлен на проверку.",
                            "workspace_update": {
                                "entity": "request",
                                "id": "{{vars.request_id}}",
                                "patch": {
                                    "status": "review",
                                    "confidence": 0.89,
                                    "title": "{{vars.title}}",
                                    "quantity": "{{vars.quantity}}",
                                    "unit": "{{vars.unit}}",
                                },
                            },
                        },
                    },
                ],
                "createdAt": now,
                "updatedAt": now,
            },
            {
                "id": "confirm_request",
                "name": "Confirm request",
                "description": "Approve request after human review",
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
                            "text": "Позиция {{vars.request_id}} подтверждена.",
                            "meta": {
                                "workspace_update": {
                                    "entity": "request",
                                    "id": "{{vars.request_id}}",
                                    "patch": {"status": "ready"},
                                }
                            },
                        },
                    }
                ],
                "createdAt": now,
                "updatedAt": now,
            },
        ],
        "skills": [
            {
                "id": "chat_with_supplier",
                "name": "Chat with supplier",
                "description": "Free-form chat from ai_supplier UI",
                "version": "1.0.0",
                "createdAt": now,
                "updatedAt": now,
                "initial": "READY",
                "params": [{"name": "conversation_id", "type": "string", "required": False}],
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
            },
            {
                "id": "process_supplier_request",
                "name": "Process supplier request",
                "description": "Kanban request workflow events from ai_supplier",
                "version": "1.0.0",
                "createdAt": now,
                "updatedAt": now,
                "initial": "READY",
                "params": [
                    {"name": "conversation_id", "type": "string", "required": False},
                    {"name": "request_id", "type": "string", "required": False},
                ],
                "viewport": {"panX": 220, "panY": 0, "zoom": 1},
                "states": [
                    {
                        "id": "READY",
                        "onEnter": [],
                        "final": False,
                        "transitions": [
                            {
                                "id": str(uuid.uuid4()),
                                "event": "ui.request.parse_requested",
                                "guard": "",
                                "actions": ["parse_request"],
                                "to": "READY",
                            },
                            {
                                "id": str(uuid.uuid4()),
                                "event": "human.request.reviewed",
                                "guard": "payload.decision == 'approve'",
                                "actions": ["confirm_request"],
                                "to": "READY",
                            },
                        ],
                        "x": 0,
                        "y": 0,
                        "width": 180,
                        "height": 80,
                    }
                ],
            },
        ],
    }
