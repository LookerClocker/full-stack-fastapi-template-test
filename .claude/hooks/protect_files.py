"""PreToolUse hook: block edits to generated files and committed migrations.

Exit code 2 blocks the tool call and shows stderr to Claude.
"""

import json
import os
import subprocess
import sys

GENERATED_PREFIXES = (
    "frontend/src/client/",
    "backend/app/email-templates/",
)
GENERATED_FILES = ("frontend/src/routeTree.gen.ts",)
MIGRATIONS_DIR = "backend/app/alembic/versions/"


def relative_path(file_path: str, project_dir: str) -> str:
    return os.path.relpath(os.path.abspath(file_path), project_dir)


def is_tracked_by_git(path: str, project_dir: str) -> bool:
    result = subprocess.run(
        ["git", "ls-files", "--error-unmatch", path],
        cwd=project_dir,
        capture_output=True,
    )
    return result.returncode == 0


def block(reason: str) -> None:
    print(reason, file=sys.stderr)
    sys.exit(2)


def main() -> None:
    event = json.load(sys.stdin)
    file_path = event.get("tool_input", {}).get("file_path")
    if not file_path:
        return
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    path = relative_path(file_path, project_dir)

    if path.startswith(GENERATED_PREFIXES) or path in GENERATED_FILES:
        block(
            f"{path} is generated. Regenerate it instead of editing: "
            "`.claude/scripts/dev.sh client` for the API client, "
            "`.claude/scripts/dev.sh typecheck` for the route tree, "
            "`bun run email:export` for email templates."
        )

    if path.startswith(MIGRATIONS_DIR) and is_tracked_by_git(path, project_dir):
        block(
            f"{path} is a committed migration. Never rewrite history: "
            'create a new one with `.claude/scripts/dev.sh migration "<message>"`.'
        )


if __name__ == "__main__":
    main()
