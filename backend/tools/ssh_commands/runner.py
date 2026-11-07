from __future__ import annotations

import os
import subprocess
import tempfile
from dataclasses import dataclass


class SshClientError(Exception):
    pass


@dataclass(frozen=True)
class SshRunOutcome:
    exit_code: int
    stdout: str
    stderr: str


def build_ssh_argv(
    *,
    key_path: str,
    port: int,
    username: str,
    host: str,
    shell: str,
    host_key_policy: str,
    connect_timeout: int,
) -> list[str]:
    policy = host_key_policy if host_key_policy in {"accept-new", "yes"} else "accept-new"
    return [
        "ssh",
        "-i",
        key_path,
        "-p",
        str(port),
        "-o",
        "BatchMode=yes",
        "-o",
        f"StrictHostKeyChecking={policy}",
        "-o",
        f"ConnectTimeout={connect_timeout}",
        "-o",
        "IdentitiesOnly=yes",
        f"{username}@{host}",
        shell,
    ]


class OpenSshRunner:
    """Runs one remote command through the OpenSSH client. No local shell."""

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
    ) -> SshRunOutcome:
        key_path: str | None = None
        try:
            fd, key_path = tempfile.mkstemp(prefix="eva-ssh-")
            os.chmod(key_path, 0o600)
            with os.fdopen(fd, "w") as handle:
                handle.write(private_key)
                if not private_key.endswith("\n"):
                    handle.write("\n")
            argv = build_ssh_argv(
                key_path=key_path,
                port=port,
                username=username,
                host=host,
                shell=shell,
                host_key_policy=host_key_policy,
                connect_timeout=min(10, timeout_sec),
            )
            completed = subprocess.run(
                argv,
                input=stdin or None,
                text=True,
                capture_output=True,
                timeout=timeout_sec,
                check=False,
            )
            return SshRunOutcome(
                exit_code=completed.returncode,
                stdout=completed.stdout or "",
                stderr=completed.stderr or "",
            )
        except subprocess.TimeoutExpired as exc:
            raise SshClientError(f"SSH command timed out after {timeout_sec}s") from exc
        except FileNotFoundError as exc:
            raise SshClientError("ssh client is not installed") from exc
        finally:
            if key_path and os.path.exists(key_path):
                os.remove(key_path)
