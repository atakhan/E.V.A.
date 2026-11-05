from __future__ import annotations

from typing import Any, Protocol

from domain.events import ToolResult
from tools.base import BaseTool
from tools.ssh_commands.library import SshLibraryCommand, clamp_int, parse_library
from tools.ssh_commands.runner import OpenSshRunner, SshClientError, SshRunOutcome


class SshRunner(Protocol):
    def run(
        self,
        *,
        host: str,
        port: int,
        username: str,
        private_key: str,
        shell: str,
        stdin: str,
        timeout_sec: int,
        host_key_policy: str,
    ) -> SshRunOutcome: ...


def _clip(text: str, limit: int) -> tuple[str, bool]:
    if len(text) <= limit:
        return text, False
    return text[:limit], True


class SshCommandsTool(BaseTool):
    """Executes a named command from the instance library. The shell stays in config, not in the recipe."""

    id = "ssh_commands"
    commands = ("run",)

    def __init__(
        self,
        *,
        config: dict[str, Any] | None = None,
        private_key: str = "",
        runner: SshRunner | None = None,
    ) -> None:
        raw = config or {}
        self.library: list[SshLibraryCommand] = parse_library(raw)
        self.host = str(raw.get("host") or "").strip()
        self.username = str(raw.get("username") or "").strip()
        self.port = clamp_int(raw.get("port"), 22, 1, 65535)
        self.timeout_sec = clamp_int(raw.get("timeoutSec"), 30, 1, 300)
        self.output_limit = clamp_int(raw.get("outputLimit"), 8000, 256, 100_000)
        policy = str(raw.get("hostKeyPolicy") or "accept-new")
        self.host_key_policy = policy if policy in {"accept-new", "yes"} else "accept-new"
        self.private_key = private_key
        self.runner = runner or OpenSshRunner()

    def cmd_run(self, args: dict[str, Any], context: dict[str, Any]) -> ToolResult:
        command_id = str(args.get("command_id") or "").strip()
        entry = next((item for item in self.library if item.id == command_id), None)
        if entry is None:
            return ToolResult(ok=False, error=f"SSH command '{command_id}' is not in the library")
        if "ENCRYPTED" in self.private_key:
            return ToolResult(ok=False, error="Encrypted SSH keys are not supported; use a key without a passphrase")
        if not self.host or not self.username:
            return ToolResult(ok=False, error="SSH host and username are not configured")
        if not self.private_key.strip():
            return ToolResult(ok=False, error="SSH private key is not configured")

        from runtime.expression_resolver import resolve_value

        scope = {
            "input": context.get("action_input") or {},
            "vars": context.get("vars") or {},
            "steps": context.get("steps") or {},
        }
        shell = str(resolve_value(entry.shell, scope) or "").strip()
        if not shell:
            return ToolResult(ok=False, error=f"SSH command '{command_id}' is empty")

        timeout_sec = entry.timeout_sec or self.timeout_sec
        try:
            outcome = self.runner.run(
                host=self.host,
                port=self.port,
                username=self.username,
                private_key=self.private_key,
                shell=shell,
                stdin=str(args.get("stdin") or ""),
                timeout_sec=timeout_sec,
                host_key_policy=self.host_key_policy,
            )
        except SshClientError as exc:
            return ToolResult(ok=False, error=str(exc))

        stdout, stdout_cut = _clip(outcome.stdout, self.output_limit)
        stderr, stderr_cut = _clip(outcome.stderr, self.output_limit)
        return ToolResult(
            ok=True,
            data={
                "command_id": command_id,
                "exit_code": outcome.exit_code,
                "stdout": stdout,
                "stderr": stderr,
                "truncated": stdout_cut or stderr_cut,
            },
        )
