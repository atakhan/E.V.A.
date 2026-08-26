from __future__ import annotations

import uuid
from datetime import datetime, timezone


def build_foreman_agent_document() -> dict:
    """Frontend-compatible Agent document for the foreman happy-path scenario."""
    now = datetime.now(timezone.utc).isoformat()
    agent_id = str(uuid.uuid4())
    skill_id = "process_foreman_request"

    return {
        "id": agent_id,
        "slug": "foreman",
        "name": "Procurement Agent",
        "description": "Foreman request processing demo",
        "createdAt": now,
        "updatedAt": now,
        "tools": [
            {
                "id": str(uuid.uuid4()),
                "toolId": "llm",
                "enabled": True,
                "configNote": "",
            },
            {
                "id": str(uuid.uuid4()),
                "toolId": "telegram",
                "enabled": True,
                "configNote": "",
            },
        ],
        "actions": [
            {
                "id": "parse_request",
                "name": "Parse foreman request",
                "description": "",
                "recipe": [
                    {
                        "id": str(uuid.uuid4()),
                        "tool": "llm",
                        "command": "parse_request",
                        "args": '{"text": "${vars.last_message}"}',
                    }
                ],
                "createdAt": now,
                "updatedAt": now,
            },
            {
                "id": "clarify",
                "name": "Clarify with foreman",
                "description": "",
                "recipe": [
                    {
                        "id": str(uuid.uuid4()),
                        "tool": "telegram",
                        "command": "send_message",
                        "args": (
                            '{"chat_id": "${vars.conversation_id}", '
                            '"text": "Уточните, пожалуйста: что именно нужно по грибкам?"}'
                        ),
                    }
                ],
                "createdAt": now,
                "updatedAt": now,
            },
        ],
        "skills": [
            {
                "id": skill_id,
                "name": "Process foreman request",
                "description": "",
                "version": "0.1.0",
                "createdAt": now,
                "updatedAt": now,
                "initial": "NEW",
                "params": [],
                "viewport": {"panX": 0, "panY": 0, "zoom": 1},
                "states": [
                    {
                        "id": "NEW",
                        "onEnter": [],
                        "final": False,
                        "transitions": [
                            {
                                "id": str(uuid.uuid4()),
                                "event": "channel.message.received",
                                "guard": "",
                                "actions": ["parse_request"],
                                "to": "ANALYZING",
                            }
                        ],
                        "x": 0,
                        "y": 0,
                        "width": 160,
                        "height": 80,
                    },
                    {
                        "id": "ANALYZING",
                        "onEnter": [],
                        "final": False,
                        "transitions": [
                            {
                                "id": str(uuid.uuid4()),
                                "event": "runtime.continue",
                                "guard": "needs_clarification == true",
                                "actions": [],
                                "to": "CLARIFYING",
                            },
                            {
                                "id": str(uuid.uuid4()),
                                "event": "runtime.continue",
                                "guard": "needs_clarification == false",
                                "actions": [],
                                "to": "READY",
                            },
                        ],
                        "x": 200,
                        "y": 0,
                        "width": 160,
                        "height": 80,
                    },
                    {
                        "id": "CLARIFYING",
                        "onEnter": ["clarify"],
                        "final": False,
                        "transitions": [
                            {
                                "id": str(uuid.uuid4()),
                                "event": "runtime.continue",
                                "guard": "",
                                "actions": [],
                                "to": "WAITING_FOR_FOREMAN",
                            }
                        ],
                        "x": 400,
                        "y": 0,
                        "width": 160,
                        "height": 80,
                    },
                    {
                        "id": "WAITING_FOR_FOREMAN",
                        "onEnter": [],
                        "final": False,
                        "transitions": [
                            {
                                "id": str(uuid.uuid4()),
                                "event": "channel.message.received",
                                "guard": "payload.conversation_id == vars.conversation_id",
                                "actions": [],
                                "to": "READY",
                            }
                        ],
                        "x": 600,
                        "y": 0,
                        "width": 160,
                        "height": 80,
                    },
                    {
                        "id": "READY",
                        "onEnter": [],
                        "final": True,
                        "transitions": [],
                        "x": 800,
                        "y": 0,
                        "width": 160,
                        "height": 80,
                    },
                ],
            }
        ],
    }
