from __future__ import annotations

from typing import Any

from app.config import get_settings
from definition.mappers.action_mapper import normalize_action_document
from definition.mappers.skill_mapper import skill_from_document
from domain.action import ActionDefinition
from domain.skill import SkillDefinition
from runtime.event_router import RuntimeCatalog
from runtime.tool_instance_resolver import credential_by_instance, enabled_instances, normalize_tool_instance
from tools.credential_resolver import (
    get_polza_api_key_for_binding,
    get_telegram_token_for_binding,
    get_web_client_secret_for_binding,
)
from tools.instance_config import merge_config_defaults, parse_instance_config
from tools.llm import LlmStubTool
from tools.polza import PolzaAiLlmTool
from tools.registry import ToolRegistry
from tools.telegram import TelegramStubTool, TelegramTool
from tools.text import TextTool
from tools.web_client import (
    WebClientHttp,
    WebClientTool,
    parse_web_client_binding_config,
)


def actions_from_document(actions_doc: list[dict[str, Any]]) -> dict[str, ActionDefinition]:
    actions: dict[str, ActionDefinition] = {}
    for action_doc in actions_doc:
        normalized = normalize_action_document(action_doc)
        if normalized.id:
            actions[normalized.id] = normalized
    return actions


def credential_bindings(agent_body: dict[str, Any]) -> dict[str, str]:
    """Map tool instance id → credential id (for API logs)."""
    return credential_by_instance(agent_body)


def _stamp_instance(tool: Any, *, instance_id: str, tool_type: str, credential_id: str | None) -> Any:
    tool.id = instance_id
    tool.tool_type = tool_type
    tool.credential_id = credential_id
    return tool


def _binding_dict(binding: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize_tool_instance(binding)
    if normalized is None:
        raise ValueError(f"Invalid tool instance binding: {binding}")
    return normalized


def _build_tool_for_binding(
    binding: dict[str, Any],
    *,
    agent_body: dict[str, Any],
    agent_id: str,
    session,
    settings,
) -> Any | None:
    item = _binding_dict(binding)
    instance_id = item["id"]
    tool_type = item["toolId"]
    credential_id = item.get("credentialId")
    config = merge_config_defaults(tool_type, parse_instance_config(item))

    if tool_type == "llm":
        return _stamp_instance(LlmStubTool(), instance_id=instance_id, tool_type=tool_type, credential_id=credential_id)

    if tool_type == "polza_ai_llm":
        default_model = str(config.get("model") or settings.polza_default_model)
        if settings.polza_mode == "stub":
            stub = LlmStubTool()
            stub.commands = ("run", "run_structured", "parse_request")  # type: ignore[misc]
            return _stamp_instance(stub, instance_id=instance_id, tool_type=tool_type, credential_id=credential_id)
        api_key = get_polza_api_key_for_binding(session, agent_id, item)
        if not api_key:
            raise KeyError(f"Polza instance '{instance_id}' enabled but credential api_key not found")
        return _stamp_instance(
            PolzaAiLlmTool(
                api_key=api_key,
                default_model=default_model,
                base_url=settings.polza_api_base,
                agent_id=agent_id,
                credential_id=credential_id,
                session=session,
            ),
            instance_id=instance_id,
            tool_type=tool_type,
            credential_id=credential_id,
        )

    if tool_type == "telegram":
        if settings.telegram_mode == "stub":
            return _stamp_instance(TelegramStubTool(), instance_id=instance_id, tool_type=tool_type, credential_id=credential_id)
        token = get_telegram_token_for_binding(session, agent_id, item)
        if not token:
            raise KeyError(f"Telegram instance '{instance_id}' enabled but credential bot_token not found")
        return _stamp_instance(TelegramTool(token), instance_id=instance_id, tool_type=tool_type, credential_id=credential_id)

    if tool_type == "text":
        return _stamp_instance(TextTool(), instance_id=instance_id, tool_type=tool_type, credential_id=credential_id)

    if tool_type == "web_client":
        secret = get_web_client_secret_for_binding(session, agent_id, item)
        if not secret or not secret.get("backend_base_url"):
            raise KeyError(f"Web Client instance '{instance_id}' enabled but credential backend_base_url not found")
        wc_config = parse_web_client_binding_config(item)
        http = WebClientHttp(
            base_url=str(secret["backend_base_url"]),
            outbound_api_key=str(secret.get("outbound_api_key") or ""),
            config=wc_config,
            docker_rewrite=settings.web_client_docker_rewrite,
            docker_host=settings.web_client_docker_host,
        )
        return _stamp_instance(
            WebClientTool(
                http=http,
                agent_id=agent_id,
                agent_slug=agent_body.get("slug", ""),
                credential_id=credential_id,
                session=session,
            ),
            instance_id=instance_id,
            tool_type=tool_type,
            credential_id=credential_id,
        )

    return None


def build_tool_registry(
    agent_body: dict[str, Any],
    *,
    agent_id: str,
    session,
) -> ToolRegistry:
    settings = get_settings()
    tools = []
    for binding in enabled_instances(agent_body):
        tool = _build_tool_for_binding(
            binding,
            agent_body=agent_body,
            agent_id=agent_id,
            session=session,
            settings=settings,
        )
        if tool is not None:
            tools.append(tool)
    return ToolRegistry(tools)


def load_runtime_catalog(agent_body: dict[str, Any], skill_id: str) -> RuntimeCatalog:
    skill_doc = next((skill for skill in agent_body.get("skills", []) if skill.get("id") == skill_id), None)
    if skill_doc is None:
        raise KeyError(f"Skill '{skill_id}' not found in agent document")

    skill = skill_from_document(skill_doc)
    actions = actions_from_document(agent_body.get("actions", []))
    return RuntimeCatalog(skill=skill, actions=actions)
