"""Helpers to materialize scenario documents in integration tests (replaces startup seeds)."""

from __future__ import annotations

from typing import Any

from definition.services.agent_service import AgentService
from definition.services.credential_service import CredentialService
from definition.validation.validate_agent import validate_agent
from infrastructure.models.tables import ToolCredentialRow


def _patch_tool_credential(doc: dict[str, Any], tool_id: str, credential_id: str) -> dict[str, Any]:
    tools: list[dict[str, Any]] = []
    for tool in doc.get("tools", []):
        if not isinstance(tool, dict):
            continue
        entry = dict(tool)
        if entry.get("toolId") == tool_id:
            entry["credentialId"] = credential_id
        tools.append(entry)
    return {**doc, "tools": tools}


def publish_scenario_agent(
    session,
    doc: dict[str, Any],
    *,
    tool_id: str,
    credential_secret: dict[str, Any],
    credential_name: str = "integration test",
    credential_meta: dict[str, Any] | None = None,
) -> str:
    """Create or replace draft from a scenario document, attach credential, publish."""
    slug = str(doc["slug"])
    service = AgentService(session)
    cred_service = CredentialService(session)

    if service.get_agent_by_slug(slug) is None:
        service.create_agent(
            name=str(doc.get("name", slug)),
            slug=slug,
            description=str(doc.get("description", "")),
        )

    credentials = cred_service.list_credentials(slug, tool_id=tool_id)
    if not credentials:
        created = cred_service.create_credential(
            slug,
            tool_id=tool_id,
            name=credential_name,
            secret=credential_secret,
        )
        credential_id = created["id"]
        if credential_meta:
            row = session.get(ToolCredentialRow, credential_id)
            if row is not None:
                row.meta = credential_meta
                session.flush()
    else:
        credential_id = credentials[0]["id"]

    body = _patch_tool_credential(doc, tool_id, credential_id)
    service.upsert_draft(slug, body)

    draft = service.get_agent_by_slug(slug) or body
    report = validate_agent(draft)
    if report["errors"] != 0:
        raise AssertionError(f"Scenario agent '{slug}' invalid: {report}")

    service.publish(slug)
    return slug


def minimal_web_chat_document(slug: str, credential_id: str) -> dict[str, Any]:
    return {
        "slug": slug,
        "defaultSkillId": "chat",
        "tools": [
            {
                "id": "web-client-instance",
                "toolId": "web_client",
                "enabled": True,
                "credentialId": credential_id,
                "configNote": (
                    '{"healthPath":"/eva/health","sendMessagePath":"/eva/messages",'
                    '"authStyle":"bearer","timeoutSec":30}'
                ),
            }
        ],
        "actions": [
            {
                "id": "echo",
                "name": "echo",
                "version": "0.1.0",
                "policy": "auto",
                "recipe": [
                    {
                        "id": "send",
                        "tool": "web_client",
                        "command": "send_message",
                        "input": {
                            "session_id": "{{vars.conversation_id}}",
                            "text": "{{vars.last_message}}",
                        },
                    }
                ],
            }
        ],
        "skills": [
            {
                "id": "chat",
                "name": "chat",
                "version": "1.0.0",
                "initial": "READY",
                "params": [{"name": "conversation_id", "type": "string", "required": False}],
                "states": [
                    {
                        "id": "READY",
                        "onEnter": [],
                        "final": False,
                        "transitions": [
                            {
                                "id": "t1",
                                "event": "channel.message.received",
                                "guard": "",
                                "actions": ["echo"],
                                "to": "READY",
                            }
                        ],
                    }
                ],
            }
        ],
    }


def publish_minimal_web_chat_agent(session, slug: str, credential_id: str) -> str:
    doc = minimal_web_chat_document(slug, credential_id)
    service = AgentService(session)
    service.upsert_draft(slug, doc)
    draft = service.get_agent_by_slug(slug) or doc
    report = validate_agent(draft)
    if report["errors"] != 0:
        raise AssertionError(f"Minimal web chat agent '{slug}' invalid: {report}")
    service.publish(slug)
    return slug


def publish_supplier_agent(session) -> str:
    from scenarios.supplier_agent_document import build_supplier_agent_document

    doc = build_supplier_agent_document()
    return publish_scenario_agent(
        session,
        doc,
        tool_id="web_client",
        credential_name="ai_supplier dev",
        credential_secret={
            "backend_base_url": "http://host.docker.internal:3000",
            "outbound_api_key": "dev-outbound-key",
            "inbound_api_key": "dev-inbound-key",
        },
        credential_meta={"dev_stub": True, "source": "ai_supplier"},
    )


def publish_foreman_agent(session) -> str:
    from scenarios.foreman_agent_document import build_foreman_agent_document

    doc = build_foreman_agent_document()
    return publish_scenario_agent(
        session,
        doc,
        tool_id="telegram",
        credential_name="Foreman dev bot",
        credential_secret={"bot_token": "000000:TEST-DEV-TOKEN"},
        credential_meta={"dev_stub": True},
    )


def publish_supplier_assistant_agent(session) -> str:
    from scenarios.supplier_assistant_agent_document import build_supplier_assistant_agent_document

    doc = build_supplier_assistant_agent_document()
    return publish_scenario_agent(
        session,
        doc,
        tool_id="web_client",
        credential_name="ai_supplier dev",
        credential_secret={
            "backend_base_url": "http://host.docker.internal:3000",
            "outbound_api_key": "dev-outbound-key",
            "inbound_api_key": "dev-inbound-key",
        },
        credential_meta={"dev_stub": True, "source": "ai_supplier"},
    )
