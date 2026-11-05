from definition.validation.validate_agent import validate_agent
from tools.ssh_commands.library import parse_library
from tools.ssh_commands.runner import SshRunOutcome, build_ssh_argv
from tools.ssh_commands.tool import SshCommandsTool


class _Runner:
    def __init__(self, outcome: SshRunOutcome | None = None) -> None:
        self.outcome = outcome or SshRunOutcome(exit_code=0, stdout="ok", stderr="")
        self.calls: list[dict] = []

    def run(self, **kwargs) -> SshRunOutcome:
        self.calls.append(kwargs)
        return self.outcome


def _tool(runner: _Runner, **config) -> SshCommandsTool:
    base = {
        "host": "app.example",
        "port": 22,
        "username": "deploy",
        "commands": [
            {"id": "restart_nginx", "name": "Restart", "shell": "systemctl restart {{input.unit}}"},
        ],
    }
    base.update(config)
    return SshCommandsTool(config=base, private_key="-----BEGIN OPENSSH PRIVATE KEY-----\nabc\n", runner=runner)


def test_run_resolves_library_shell_and_returns_output():
    runner = _Runner(SshRunOutcome(exit_code=3, stdout="done", stderr=""))
    result = _tool(runner).handle(
        "run",
        {"command_id": "restart_nginx"},
        {"action_input": {"unit": "nginx"}, "vars": {}, "steps": {}},
    )

    assert result.ok is True
    assert result.data["exit_code"] == 3
    assert result.data["stdout"] == "done"
    assert result.data["truncated"] is False
    assert runner.calls[0]["shell"] == "systemctl restart nginx"
    assert runner.calls[0]["username"] == "deploy"


def test_unknown_library_command_fails():
    result = _tool(_Runner()).handle("run", {"command_id": "missing"}, {})
    assert result.ok is False
    assert "not in the library" in (result.error or "")


def test_output_is_truncated():
    runner = _Runner(SshRunOutcome(exit_code=0, stdout="a" * 300, stderr=""))
    result = _tool(runner, outputLimit=256).handle("run", {"command_id": "restart_nginx"}, {})
    assert result.data["stdout"] == "a" * 256
    assert result.data["truncated"] is True


def test_missing_host_does_not_call_runner():
    runner = _Runner()
    result = _tool(runner, host="").handle("run", {"command_id": "restart_nginx"}, {})
    assert result.ok is False
    assert runner.calls == []


def test_encrypted_key_is_rejected():
    tool = _tool(_Runner())
    tool.private_key = "-----BEGIN OPENSSH PRIVATE KEY-----\nProc-Type: 4,ENCRYPTED\n"
    result = tool.handle("run", {"command_id": "restart_nginx"}, {})
    assert result.ok is False
    assert "passphrase" in (result.error or "")


def test_parse_library_skips_invalid_entries():
    commands = parse_library(
        {
            "commands": [
                {"id": "ok_cmd", "shell": "true"},
                {"id": "Bad", "shell": "true"},
                {"id": "empty", "shell": "  "},
                "nope",
            ]
        }
    )
    assert [item.id for item in commands] == ["ok_cmd"]


def test_ssh_argv_is_a_direct_exec():
    argv = build_ssh_argv(
        key_path="/tmp/key",
        port=2222,
        username="deploy",
        host="app.example",
        shell="echo hi",
        host_key_policy="yes",
        connect_timeout=5,
    )
    assert argv[0] == "ssh"
    assert argv[-1] == "echo hi"
    assert "IdentitiesOnly=yes" in argv
    assert "deploy@app.example" in argv


def test_ssh_instance_without_credential_is_validation_error():
    report = validate_agent(
        {
            "slug": "demo",
            "skills": [],
            "actions": [],
            "tools": [{"id": "ssh_commands", "toolId": "ssh_commands", "name": "SSH", "enabled": True}],
        }
    )
    assert any(item["code"] == "missing_credential" for item in report["issues"])


def test_unknown_library_command_in_action_is_warning():
    report = validate_agent(
        {
            "slug": "demo",
            "skills": [],
            "actions": [
                {
                    "id": "restart",
                    "name": "Restart",
                    "version": "0.1.0",
                    "policy": "auto",
                    "recipe": [
                        {
                            "id": "run_1",
                            "tool": "ssh_commands",
                            "command": "run",
                            "input": {"command_id": "missing"},
                        }
                    ],
                }
            ],
            "tools": [
                {
                    "id": "ssh_commands",
                    "toolId": "ssh_commands",
                    "name": "SSH",
                    "enabled": True,
                    "credentialId": "cred-1",
                    "config": {"commands": []},
                }
            ],
        }
    )
    assert any(item["code"] == "unknown_ssh_command" for item in report["issues"])
