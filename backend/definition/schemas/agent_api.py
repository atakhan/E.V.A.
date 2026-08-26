from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ToolCommandDefApi(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    description: str = ""


class ToolEventDefApi(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    description: str = ""


class ToolDefinitionApi(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    name: str
    description: str = ""
    commands: list[ToolCommandDefApi] = Field(default_factory=list)
    events: list[ToolEventDefApi] = Field(default_factory=list)
    states: list[str] = Field(default_factory=list)


class ActionRecipeStepApi(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    tool: str
    command: str
    args: str = ""


class ActionDefApi(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    name: str
    description: str = ""
    recipe: list[ActionRecipeStepApi] = Field(default_factory=list)
    created_at: str = Field(alias="createdAt", default="")
    updated_at: str = Field(alias="updatedAt", default="")


class ToolBindingApi(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    tool_id: str = Field(alias="toolId")
    enabled: bool = True
    credential_id: str | None = Field(default=None, alias="credentialId")
    config_note: str = Field(alias="configNote", default="")


class FsmTransitionApi(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    event: str
    guard: str = ""
    actions: list[str] = Field(default_factory=list)
    to: str


class FsmStateApi(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    on_enter: list[str] = Field(alias="onEnter", default_factory=list)
    final: bool = False
    transitions: list[FsmTransitionApi] = Field(default_factory=list)
    x: float = 0
    y: float = 0
    width: float = 0
    height: float = 0


class SkillParamApi(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    required: bool = False


class SkillApi(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    name: str
    description: str = ""
    version: str = "0.1.0"
    created_at: str = Field(alias="createdAt", default="")
    updated_at: str = Field(alias="updatedAt", default="")
    initial: str | None = None
    params: list[SkillParamApi] = Field(default_factory=list)
    states: list[FsmStateApi] = Field(default_factory=list)
    viewport: dict[str, float] = Field(default_factory=lambda: {"panX": 0, "panY": 0, "zoom": 1})


class AgentApi(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    slug: str
    name: str
    description: str = ""
    created_at: str = Field(alias="createdAt")
    updated_at: str = Field(alias="updatedAt")
    skills: list[SkillApi] = Field(default_factory=list)
    actions: list[ActionDefApi] = Field(default_factory=list)
    tools: list[ToolBindingApi] = Field(default_factory=list)


class AgentSummaryApi(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    slug: str
    name: str
    description: str = ""
    created_at: str = Field(alias="createdAt")
    updated_at: str = Field(alias="updatedAt")


class AgentCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    slug: str
    description: str = ""


class AgentIssueApi(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    severity: str
    code: str
    message: str
    href: str | None = None


class AgentValidationReportApi(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    issues: list[AgentIssueApi]
    errors: int
    warnings: int
    infos: int


class AgentPublicationApi(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    version: str
    published_at: str = Field(alias="publishedAt")
    body: dict[str, Any]


class PublishResponseApi(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    ok: bool = True
    version: str
    publication_id: str = Field(alias="publicationId")
