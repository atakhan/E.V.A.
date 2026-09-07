from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any

from domain.agent import SkillRun, SkillRunStatus
from domain.events import Event
from runtime.skill_routing import find_skills_for_event, run_accepts_event
from runtime.stores.skill_run_store import store_find_waiting_runs


class DispatchClass(str, Enum):
    pass_through = "pass_through"
    resume = "resume"
    amend = "amend"
    start = "start"
    side_question = "side_question"
    cancel = "cancel"
    underspecified = "underspecified"


PARSE_EVENT = "ui.request.parse_requested"
REVIEW_EVENT = "human.request.reviewed"
CHAT_EVENT = "channel.message.received"

_PARSE_RE = re.compile(r"(разбер\w*|распарс\w*|\bparse\b)", re.IGNORECASE)
_REVIEW_RE = re.compile(r"(подтверд\w*|одобр\w*|\bapprove\b|\bconfirm\b)", re.IGNORECASE)
_CANCEL_RE = re.compile(r"(\bстоп\b|\bstop\b|отмен\w*|\bcancel\b|хватит|не надо)", re.IGNORECASE)
_AMEND_RE = re.compile(r"(\bсначала\b|\bтолько\b|не трогай)", re.IGNORECASE)
_AFFIRM_RE = re.compile(r"^(да|ок|okay|ok|хорошо|подтверждаю|yes|ага)([.!…]*)$", re.IGNORECASE)
_DENY_RE = re.compile(r"^(нет|не то|не надо|no)([.!…]*)$", re.IGNORECASE)
_QUESTION_RE = re.compile(
    r"(\?|^\s*(кто|что|где|когда|почему|зачем|сколько|как)\b)",
    re.IGNORECASE,
)
_DEICTIC_RE = re.compile(r"\b(это|этот|эти|эту|ту|той|те)\b", re.IGNORECASE)
_ENTITY_RE = re.compile(r"\b(?:REQ-|TG-)[A-Za-z0-9-]+\b")

_INTENT_EVENTS = {
    "parse": PARSE_EVENT,
    "parse_request": PARSE_EVENT,
    "review": REVIEW_EVENT,
    "approve": REVIEW_EVENT,
    "confirm": REVIEW_EVENT,
}

_GESTURE_EVENTS = {PARSE_EVENT, REVIEW_EVENT}


@dataclass
class DispatchDecision:
    kind: DispatchClass
    event: Event
    skill_id: str | None = None
    resume_run_id: str | None = None
    cancel_run_ids: tuple[str, ...] = ()
    note: str = ""
    follow_with_chat: bool = False


def conversation_skill_ids(agent_body: dict[str, Any]) -> list[str]:
    return find_skills_for_event(agent_body, CHAT_EVENT)


def work_skill_ids(agent_body: dict[str, Any]) -> list[str]:
    chat = set(conversation_skill_ids(agent_body))
    ordered: list[str] = []
    for event_type in (PARSE_EVENT, REVIEW_EVENT):
        for skill_id in find_skills_for_event(agent_body, event_type):
            if skill_id not in chat and skill_id not in ordered:
                ordered.append(skill_id)
    return ordered


def _text(event: Event) -> str:
    return str(event.payload.get("text") or event.payload.get("message") or "").strip()


def _conversation_id(event: Event) -> str | None:
    value = event.payload.get("conversation_id") or event.correlation.conversation_id
    return value if isinstance(value, str) and value else None


def _entity_ids(event: Event) -> list[str]:
    raw = event.payload.get("entity_ids")
    ids: list[str] = []
    if isinstance(raw, list):
        ids.extend(str(item) for item in raw if item)
    entity_id = event.payload.get("entity_id") or event.correlation.entity_id
    request_id = event.payload.get("request_id") or event.correlation.request_id
    for item in (entity_id, request_id):
        if isinstance(item, str) and item and item not in ids:
            ids.append(item)
    focus = event.payload.get("focus") or event.metadata.get("focus")
    if isinstance(focus, dict):
        selected = focus.get("selectedEntityIds") or []
        if isinstance(selected, list):
            for item in selected:
                if item and str(item) not in ids:
                    ids.append(str(item))
        open_id = focus.get("openEntityId")
        if open_id and str(open_id) not in ids:
            ids.append(str(open_id))
    for match in _ENTITY_RE.findall(_text(event)):
        if match not in ids:
            ids.append(match)
    return ids


def _intent(event: Event) -> str | None:
    value = event.payload.get("intent")
    return str(value) if value else None


def _is_human_inbound(event: Event) -> bool:
    if event.skill_run_id:
        return False
    if event.type.startswith("action.") or event.type == "runtime.continue":
        return False
    return True


def _annotate(event: Event, *, kind: DispatchClass, extra: dict[str, Any] | None = None) -> Event:
    metadata = dict(event.metadata)
    metadata["dispatch"] = {"class": kind.value, **(extra or {})}
    return event.model_copy(update={"metadata": metadata})


def _rewrite(
    event: Event,
    *,
    event_type: str,
    kind: DispatchClass,
    entity_ids: list[str] | None = None,
    extra_payload: dict[str, Any] | None = None,
) -> Event:
    payload = dict(event.payload)
    ids = entity_ids if entity_ids is not None else _entity_ids(event)
    if ids:
        payload["entity_ids"] = ids
        payload.setdefault("entity_id", ids[0])
        payload.setdefault("request_id", ids[0])
    if extra_payload:
        payload.update(extra_payload)
    metadata = dict(event.metadata)
    metadata["dispatch"] = {"class": kind.value, "rewritten_from": event.type}
    updates: dict[str, Any] = {"type": event_type, "payload": payload, "metadata": metadata}
    return event.model_copy(update=updates)


def _active_runs(store: Any, conversation_id: str) -> list[SkillRun]:
    return [
        run
        for run in store_find_waiting_runs(store, "conversation_id", conversation_id)
        if run.status in (SkillRunStatus.waiting, SkillRunStatus.running)
    ]


def _work_runs(runs: list[SkillRun], agent_body: dict[str, Any]) -> list[SkillRun]:
    work = set(work_skill_ids(agent_body))
    return [run for run in runs if run.skill_id in work]


def _chat_runs(runs: list[SkillRun], agent_body: dict[str, Any]) -> list[SkillRun]:
    chat = set(conversation_skill_ids(agent_body))
    return [run for run in runs if run.skill_id in chat]


def _skill_for_event(agent_body: dict[str, Any], event_type: str) -> str | None:
    matches = find_skills_for_event(agent_body, event_type)
    chat = set(conversation_skill_ids(agent_body))
    work = [skill_id for skill_id in matches if skill_id not in chat]
    if work:
        return work[0]
    return matches[0] if matches else None


def _run_matches_entities(run: SkillRun, entity_ids: list[str]) -> bool:
    if not entity_ids:
        return True
    owned = {
        str(run.vars.get("entity_id") or ""),
        str(run.vars.get("request_id") or ""),
        str(run.params.get("entity_id") or ""),
        str(run.params.get("request_id") or ""),
    }
    owned.update(str(item) for item in (run.vars.get("entity_ids") or []) if item)
    return any(item in owned for item in entity_ids)


def classify_act(event: Event, store: Any, agent_body: dict[str, Any] | None) -> DispatchDecision:
    """Classify a human act. Does not mutate the store (cancel is applied by the caller)."""
    if not agent_body or not _is_human_inbound(event):
        return DispatchDecision(kind=DispatchClass.pass_through, event=event, note="not a human inbound")

    conversation_id = _conversation_id(event)
    active = _active_runs(store, conversation_id) if conversation_id else []
    work = _work_runs(active, agent_body)
    chat_runs = _chat_runs(active, agent_body)
    chat_skill = (conversation_skill_ids(agent_body) or [None])[0]
    entity_ids = _entity_ids(event)
    intent = _intent(event)
    text = _text(event)

    if event.type in _GESTURE_EVENTS or (intent and intent in _INTENT_EVENTS and event.type != CHAT_EVENT):
        target_type = event.type
        skill_id = _skill_for_event(agent_body, target_type)
        matching = [run for run in work if run_accepts_event(run, target_type, agent_body)]
        if matching:
            chosen = matching[0]
            return DispatchDecision(
                kind=DispatchClass.resume,
                event=_annotate(event, kind=DispatchClass.resume, extra={"run_id": chosen.id}),
                skill_id=chosen.skill_id,
                resume_run_id=chosen.id,
                note="gesture resumes waiting work",
            )
        return DispatchDecision(
            kind=DispatchClass.start,
            event=_annotate(event, kind=DispatchClass.start, extra={"skill_id": skill_id}),
            skill_id=skill_id,
            note="gesture starts work",
        )

    if event.type != CHAT_EVENT:
        return DispatchDecision(kind=DispatchClass.pass_through, event=event, note=f"unclassified {event.type}")

    if _CANCEL_RE.search(text):
        targets = [run for run in work if _run_matches_entities(run, entity_ids)] if entity_ids else list(work)
        if not targets:
            targets = list(work)
        resume_chat = chat_runs[0].id if chat_runs else None
        return DispatchDecision(
            kind=DispatchClass.cancel,
            event=_annotate(event, kind=DispatchClass.cancel, extra={"cancel": [run.id for run in targets]}),
            skill_id=chat_skill,
            resume_run_id=resume_chat,
            cancel_run_ids=tuple(run.id for run in targets),
            follow_with_chat=True,
            note="cancel work, then chat",
        )

    if _AMEND_RE.search(text) and work:
        if not entity_ids:
            return DispatchDecision(
                kind=DispatchClass.underspecified,
                event=_annotate(event, kind=DispatchClass.underspecified),
                skill_id=chat_skill,
                resume_run_id=chat_runs[0].id if chat_runs else None,
                note="amend without entities",
            )
        rewritten = _rewrite(
            event,
            event_type=PARSE_EVENT,
            kind=DispatchClass.amend,
            entity_ids=entity_ids,
            extra_payload={"intent": "parse"},
        )
        return DispatchDecision(
            kind=DispatchClass.amend,
            event=rewritten,
            skill_id=_skill_for_event(agent_body, PARSE_EVENT),
            cancel_run_ids=tuple(run.id for run in work),
            note="amend = cancel + start narrowed",
        )

    parse_intent = intent in {"parse", "parse_request"} or bool(_PARSE_RE.search(text))
    review_intent = intent in {"review", "approve", "confirm"} or bool(_REVIEW_RE.search(text))

    if parse_intent:
        if _DEICTIC_RE.search(text) and not entity_ids:
            return DispatchDecision(
                kind=DispatchClass.underspecified,
                event=_annotate(event, kind=DispatchClass.underspecified),
                skill_id=chat_skill,
                resume_run_id=chat_runs[0].id if chat_runs else None,
                note="parse this without focus",
            )
        rewritten = _rewrite(
            event,
            event_type=PARSE_EVENT,
            kind=DispatchClass.start,
            entity_ids=entity_ids,
            extra_payload={"intent": "parse"},
        )
        matching = [run for run in work if run_accepts_event(run, PARSE_EVENT, agent_body)]
        if matching:
            chosen = matching[0]
            rewritten = rewritten.model_copy(update={"skill_run_id": chosen.id})
            return DispatchDecision(
                kind=DispatchClass.resume,
                event=rewritten,
                skill_id=chosen.skill_id,
                resume_run_id=chosen.id,
                note="parse phrase resumes work",
            )
        return DispatchDecision(
            kind=DispatchClass.start,
            event=rewritten,
            skill_id=_skill_for_event(agent_body, PARSE_EVENT),
            note="parse phrase starts work",
        )

    if review_intent or (_AFFIRM_RE.match(text) and work and entity_ids):
        rewritten = _rewrite(
            event,
            event_type=REVIEW_EVENT,
            kind=DispatchClass.resume if work else DispatchClass.start,
            entity_ids=entity_ids,
            extra_payload={"intent": "review", "decision": "approve"},
        )
        matching = [run for run in work if run_accepts_event(run, REVIEW_EVENT, agent_body)]
        if matching:
            focused = [run for run in matching if _run_matches_entities(run, entity_ids)] or matching
            chosen = focused[0]
            rewritten = rewritten.model_copy(update={"skill_run_id": chosen.id})
            return DispatchDecision(
                kind=DispatchClass.resume,
                event=rewritten,
                skill_id=chosen.skill_id,
                resume_run_id=chosen.id,
                note="affirm/review resumes work",
            )
        return DispatchDecision(
            kind=DispatchClass.start,
            event=rewritten,
            skill_id=_skill_for_event(agent_body, REVIEW_EVENT),
            note="review phrase starts work",
        )

    if _DENY_RE.match(text) and work:
        targets = [run for run in work if _run_matches_entities(run, entity_ids)] or work
        return DispatchDecision(
            kind=DispatchClass.cancel,
            event=_annotate(event, kind=DispatchClass.cancel),
            skill_id=chat_skill,
            resume_run_id=chat_runs[0].id if chat_runs else None,
            cancel_run_ids=tuple(run.id for run in targets),
            follow_with_chat=True,
            note="deny cancels focused work",
        )

    waiting_for_chat = [run for run in work if run_accepts_event(run, CHAT_EVENT, agent_body)]
    if waiting_for_chat and not _QUESTION_RE.search(text):
        chosen = waiting_for_chat[0]
        annotated = _annotate(event, kind=DispatchClass.resume, extra={"run_id": chosen.id})
        annotated = annotated.model_copy(update={"skill_run_id": chosen.id})
        return DispatchDecision(
            kind=DispatchClass.resume,
            event=annotated,
            skill_id=chosen.skill_id,
            resume_run_id=chosen.id,
            note="short reply to work waiting for chat",
        )

    resume_chat = chat_runs[0].id if chat_runs else None
    annotated = _annotate(event, kind=DispatchClass.side_question)
    if resume_chat:
        annotated = annotated.model_copy(update={"skill_run_id": resume_chat})
    return DispatchDecision(
        kind=DispatchClass.side_question,
        event=annotated,
        skill_id=chat_skill,
        resume_run_id=resume_chat,
        note="side question / default chat",
    )


# re-export for tests
__all__ = [
    "DispatchClass",
    "DispatchDecision",
    "classify_act",
    "conversation_skill_ids",
    "work_skill_ids",
]
