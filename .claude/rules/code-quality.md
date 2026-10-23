# Code Quality Rules (all code)

The bar: a teammate understands the change in five minutes by reading the code.

## Naming and structure
- Names state intent: `require_permission`, `can_manage_all_items`, `ROLE_PERMISSIONS`. No `helper`, `util2`, `data`, `check()`.
- One function, one job. If a function needs a comment to split it into parts, split it into functions.
- Keep a concept in exactly one place. Policy tables, enums and constants have a single source of truth that everything else imports.
- Prefer data over branching: a lookup table beats an `if/elif` chain over roles or types.
- Delete dead code and replaced fields. Do not keep a deprecated path "just in case".

## Comments
- Comment only the non-obvious *why* (a security invariant, a workaround, an ordering requirement). Never narrate what the code does.
- Match the comment density of the surrounding file.

## Consistency
- Follow the existing patterns of the file and layer before inventing new ones. When you introduce a pattern, apply it everywhere it fits in the same change — no half-migrations.
- Match existing formatting, import style, and file layout. Formatters (Ruff, Biome) are the final word: run `.claude/scripts/dev.sh format`.

## Scope
- Keep the change tight. No drive-by refactors, renames, or dependency additions unrelated to the task.
- Reuse libraries already in the project. Adding a dependency needs a stated reason.

## Errors
- Fail loudly and specifically: correct HTTP status, human-readable message, no swallowed exceptions.
- Never leak internals (stack traces, SQL, other users' data) in error responses.

## Tests
- Quality over quantity: a few tests on critical paths, each named for the behavior it proves (`test_member_cannot_list_users`).
- Cover both the allowed and the denied path for anything security-related.
- Tests are code: no copy-paste walls — parametrize.

## Done means
`.claude/scripts/dev.sh check` passes (format, lint, types, tests, frontend typecheck).
