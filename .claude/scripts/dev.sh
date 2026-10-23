#!/usr/bin/env bash
# Docker-only developer toolchain. No local uv or bun needed.
# Usage: .claude/scripts/dev.sh <command> [args]   (run with no args for help)

set -euo pipefail

ROOT="$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"
cd "$ROOT"

FRONTEND_CONTAINER=frontend-dev

# One-off backend container with the host ./backend mounted, so edits, new
# migrations and coverage reports land on the host.
be() {
  docker compose run --rm -T -v "$ROOT/backend:/app/backend" backend "$@"
}

ensure_frontend_container() {
  if [ -n "$(docker ps -q -f "name=^${FRONTEND_CONTAINER}$")" ]; then
    return
  fi
  if [ -n "$(docker ps -aq -f "name=^${FRONTEND_CONTAINER}$")" ]; then
    docker start "$FRONTEND_CONTAINER" >/dev/null
  else
    # node_modules live in anonymous volumes so host and container never share native binaries.
    docker run -d --name "$FRONTEND_CONTAINER" -p 5173:5173 \
      -v "$ROOT":/app -v /app/node_modules -v /app/frontend/node_modules \
      -v /app/packages/react-email/node_modules \
      -w /app oven/bun:1 sh -c "bun install && cd frontend && bun run dev --host 0.0.0.0" >/dev/null
  fi
  echo "Waiting for the Vite dev server (first start installs dependencies)..." >&2
  until curl -sf -o /dev/null http://localhost:5173; do sleep 3; done
}

fe() {
  ensure_frontend_container
  docker exec -w /app/frontend "$FRONTEND_CONTAINER" "$@"
}

seed() { be bash scripts/prestart.sh; }

case "${1:-help}" in
  up)
    docker compose build backend
    docker compose up -d --wait db mailpit adminer proxy
    seed
    docker compose up -d --wait backend
    ensure_frontend_container
    echo "Frontend: http://localhost:5173  API: http://localhost:8000/docs"
    ;;
  be) shift; be "$@" ;;
  fe) shift; fe "$@" ;;
  migration)
    shift
    be alembic revision -m "${1:?usage: dev.sh migration \"<message>\"}"
    ;;
  migrate) be alembic upgrade head ;;
  seed) seed ;;
  test)
    shift
    status=0
    if [ "$#" -gt 0 ]; then
      be pytest "$@" || status=$?
    else
      be bash scripts/tests-start.sh || status=$?
    fi
    # The test session deletes every user; restore the seeded accounts.
    seed >/dev/null 2>&1
    exit "$status"
    ;;
  format)
    be bash scripts/format.sh
    fe sh -c "cd /app && bun run lint"
    ;;
  lint)
    be bash scripts/lint.sh
    fe bunx biome check --no-errors-on-unmatched --files-ignore-unknown=true ./
    ;;
  client)
    be python -c "import json, app.main; print(json.dumps(app.main.app.openapi()))" \
      > frontend/openapi.json
    fe bun run generate-client
    fe sh -c "cd /app && bun run lint" >/dev/null
    echo "Frontend client regenerated in frontend/src/client"
    ;;
  typecheck)
    # vite build regenerates routeTree.gen.ts, which tsc needs to be current.
    fe bunx vite build --logLevel error
    fe bunx tsc -p tsconfig.build.json --noEmit
    echo "Frontend type check passed"
    ;;
  check)
    "$0" format
    "$0" lint
    "$0" test
    "$0" typecheck
    echo "All checks passed"
    ;;
  rebuild)
    docker compose build backend
    docker compose up -d --wait backend
    ;;
  *)
    echo "Commands:"
    sed -n '/^case/,/^esac/p' "$0" | grep -oE '^  [a-z]+\)' | tr -d ' )' | sed 's/^/  /'
    ;;
esac
