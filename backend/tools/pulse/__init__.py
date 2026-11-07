from tools.pulse.ensure import ensure_pulse_tool, pulse_tool_instance
from tools.pulse.manifest import PULSE_TOOL_ID, PULSE_TOOL_MANIFEST

__all__ = [
    "PULSE_TOOL_ID",
    "PULSE_TOOL_MANIFEST",
    "PulseTool",
    "ensure_pulse_tool",
    "pulse_tool_instance",
]


def __getattr__(name: str):
    if name == "PulseTool":
        from tools.pulse.tool import PulseTool

        return PulseTool
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
