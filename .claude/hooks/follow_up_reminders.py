"""PostToolUse hook: remind Claude of follow-up work implied by the file it just edited.

Reminders are injected as additional context; they never block.
"""

import json
import os
import sys

REMINDERS = (
    (
        "backend/app/models.py",
        "models.py changed: if a table column changed, create a migration "
        '(`.claude/scripts/dev.sh migration "<msg>"`), then run '
        "`.claude/scripts/dev.sh client` so the frontend types match.",
    ),
    (
        "backend/app/api/",
        "API surface changed: every endpoint must declare its authorization "
        "(see .claude/rules/rbac.md). Run `.claude/scripts/dev.sh client` "
        "before touching frontend code that calls it.",
    ),
    (
        "backend/app/core/rbac.py",
        "Roles/permissions changed: update the permission matrix in README.md, "
        "ROLE_LABELS in frontend/src/lib/roles.ts, the tests in "
        "backend/tests/api/routes/test_rbac.py, then run `.claude/scripts/dev.sh client`.",
    ),
)


def main() -> None:
    event = json.load(sys.stdin)
    file_path = event.get("tool_input", {}).get("file_path")
    if not file_path:
        return
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    path = os.path.relpath(os.path.abspath(file_path), project_dir)

    messages = [message for prefix, message in REMINDERS if path.startswith(prefix)]
    if not messages:
        return
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": " ".join(messages),
        }
    }
    print(json.dumps(output))


if __name__ == "__main__":
    main()
