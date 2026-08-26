from __future__ import annotations

from pydantic import BaseModel, Field


class FsmTransition(BaseModel):
    id: str = ""
    event: str
    guard: str = ""
    actions: list[str] = Field(default_factory=list)
    to: str


class FsmState(BaseModel):
    id: str
    on_enter: list[str] = Field(default_factory=list)
    final: bool = False
    transitions: list[FsmTransition] = Field(default_factory=list)


class SkillDefinition(BaseModel):
    id: str
    name: str = ""
    description: str = ""
    version: str = "0.1.0"
    initial: str
    states: list[FsmState] = Field(default_factory=list)

    def state_map(self) -> dict[str, FsmState]:
        return {state.id: state for state in self.states}

    def get_state(self, state_id: str) -> FsmState | None:
        return self.state_map().get(state_id)
