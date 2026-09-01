from __future__ import annotations

import argparse
from pathlib import Path

TEMPLATE = '''from __future__ import annotations

from definition.catalog.field_defs import field

TOOL_MANIFEST: dict = {{
    "id": "{name}",
    "name": "{title}",
    "description": "TODO: describe {name} tool",
    "commands": [
        {{
            "id": "{first_command}",
            "description": "TODO",
            "inputSchema": [
                field("example", type="template", required=True, label="Example"),
            ],
            "outputSchema": [
                field("result", type="json", scope="call"),
            ],
        }},
    ],
    "events": [],
    "states": [],
}}
'''


def main() -> None:
    parser = argparse.ArgumentParser(description="Scaffold a new E.V.A. built-in tool")
    parser.add_argument("name", help="tool id, e.g. my_tool")
    parser.add_argument("--commands", default="run", help="comma-separated command ids")
    args = parser.parse_args()

    name = args.name.strip()
    commands = [item.strip() for item in args.commands.split(",") if item.strip()]
    root = Path(__file__).resolve().parents[1] / "tools" / name
    root.mkdir(parents=True, exist_ok=True)

    manifest_path = root / "manifest.py"
    manifest_path.write_text(
        TEMPLATE.format(
            name=name,
            title=name.replace("_", " ").title(),
            first_command=commands[0],
        ),
        encoding="utf-8",
    )

    init_path = root / "__init__.py"
    if not init_path.exists():
        class_name = "".join(part.capitalize() for part in name.split("_")) + "Tool"
        init_path.write_text(
            f'from tools.{name}.tool import {class_name}\n\n__all__ = ["{class_name}"]\n',
            encoding="utf-8",
        )

    tool_path = root / "tool.py"
    if not tool_path.exists():
        class_name = "".join(part.capitalize() for part in name.split("_")) + "Tool"
        cmd_methods = "\n".join(
            f'    def cmd_{cmd}(self, args, context):\n        return ToolResult(ok=True, data={{}})\n'
            for cmd in commands
        )
        tool_path.write_text(
            f'''from __future__ import annotations

from domain.events import ToolResult
from tools.base import BaseTool


class {class_name}(BaseTool):
    id = "{name}"
    commands = {tuple(commands)!r}

{cmd_methods}''',
            encoding="utf-8",
        )

    print(f"Scaffolded tool at {root}")
    print("Next: register in definition_loader.py and definition/catalog/builtin_tools.py")


if __name__ == "__main__":
    main()
