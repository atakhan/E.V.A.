"""Runtime as a tool/plugin — machine that executes the agent's Life FSM.

Implementation deferred (`implemented: False` on the manifest). Engine still lives in
`backend/runtime/`; this package is the declared capability surface.
"""

from tools.runtime.manifest import RUNTIME_TOOL_MANIFEST

__all__ = ["RUNTIME_TOOL_MANIFEST"]
