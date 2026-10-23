#!/usr/bin/env bash
# End-to-end RBAC smoke test against the running stack.
# Logs in as each seeded account and asserts the permission matrix over real HTTP.
# Usage: .claude/skills/add-rbac/scripts/smoke_test.sh [api_base_url]

set -uo pipefail

ROOT="$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"
API="${1:-http://localhost:8000}/api/v1"

env_value() { grep -E "^$1=" "$ROOT/.env" | tail -1 | cut -d= -f2- | tr -d '"'; }
json_field() { python3 -c "import json,sys; print(json.load(sys.stdin).get('$1', ''))"; }

ADMIN_EMAIL="$(env_value FIRST_SUPERUSER)"
ADMIN_PASSWORD="$(env_value FIRST_SUPERUSER_PASSWORD)"
# Same default as compose.override.yml; export DEMO_USER_PASSWORD to override.
DEMO_PASSWORD="${DEMO_USER_PASSWORD:-changethis}"

failures=0
passes=0

login() {
  curl -s -X POST "$API/login/access-token" \
    --data-urlencode "username=$1" --data-urlencode "password=$2" | json_field access_token
}

expect() {  # expect <label> <expected_status> <curl args...>
  local label="$1" expected="$2"
  shift 2
  local actual
  actual="$(curl -s -o /dev/null -w '%{http_code}' "$@")"
  if [ "$actual" = "$expected" ]; then
    passes=$((passes + 1)); echo "  ok    $label → $actual"
  else
    failures=$((failures + 1)); echo "  FAIL  $label → $actual (expected $expected)"
  fi
}

# Plain variables, not an associative array: macOS ships bash 3.2.
TOKEN_admin="$(login "$ADMIN_EMAIL" "$ADMIN_PASSWORD")"
TOKEN_manager="$(login manager@example.com "$DEMO_PASSWORD")"
TOKEN_member="$(login member@example.com "$DEMO_PASSWORD")"
token() { eval "echo \"\$TOKEN_$1\""; }
for role in admin manager member; do
  [ -n "$(token "$role")" ] || { echo "Could not log in as $role. Is the stack seeded? (.claude/scripts/dev.sh seed)"; exit 1; }
done

auth() { echo "Authorization: Bearer $(token "$1")"; }

echo "Roles reported by /users/me"
for role in admin manager member; do
  actual_role="$(curl -s "$API/users/me" -H "$(auth "$role")" | json_field role)"
  if [ "$actual_role" = "$role" ]; then
    passes=$((passes + 1)); echo "  ok    $role → role=$actual_role"
  else
    failures=$((failures + 1)); echo "  FAIL  $role → role=$actual_role"
  fi
done

echo "Permission matrix"
for spec in "admin 200 200" "manager 200 200" "member 403 403"; do
  read -r role users_status metrics_status <<< "$spec"
  expect "$role GET /users/" "$users_status" "$API/users/" -H "$(auth "$role")"
  expect "$role GET /metrics/" "$metrics_status" "$API/metrics/" -H "$(auth "$role")"
done
for role in manager member; do
  expect "$role POST /users/" 403 -X POST "$API/users/" -H "$(auth "$role")" \
    -H "Content-Type: application/json" -d '{"email":"nope@example.com","password":"password123"}'
done

echo "Authentication and escalation"
expect "no token GET /users/me" 401 "$API/users/me"
expect "bad token GET /users/me" 401 "$API/users/me" -H "Authorization: Bearer invalid"

signup_email="smoke-$RANDOM$RANDOM@example.com"
signup_role="$(curl -s -X POST "$API/users/signup" -H "Content-Type: application/json" \
  -d "{\"email\":\"$signup_email\",\"password\":\"password123\",\"role\":\"admin\"}" | json_field role)"
if [ "$signup_role" = "member" ]; then
  passes=$((passes + 1)); echo "  ok    signup with role=admin → role=member"
else
  failures=$((failures + 1)); echo "  FAIL  signup with role=admin → role=$signup_role"
fi

created_id="$(curl -s -X POST "$API/users/" -H "$(auth admin)" -H "Content-Type: application/json" \
  -d "{\"email\":\"smoke-admin-$RANDOM$RANDOM@example.com\",\"password\":\"password123\",\"role\":\"manager\"}" | json_field id)"
if [ -n "$created_id" ]; then
  passes=$((passes + 1)); echo "  ok    admin POST /users/ with role=manager"
  expect "manager PATCH /users/{id} role=admin" 403 -X PATCH "$API/users/$created_id" \
    -H "$(auth manager)" -H "Content-Type: application/json" -d '{"role":"admin"}'
  curl -s -o /dev/null -X DELETE "$API/users/$created_id" -H "$(auth admin)"
else
  failures=$((failures + 1)); echo "  FAIL  admin POST /users/ with role=manager"
fi

signup_id="$(curl -s "$API/users/?limit=1000" -H "$(auth admin)" | python3 -c "
import json, sys
print(next((u['id'] for u in json.load(sys.stdin)['data'] if u['email'] == '$signup_email'), ''))")"
[ -n "$signup_id" ] && curl -s -o /dev/null -X DELETE "$API/users/$signup_id" -H "$(auth admin)"

echo
echo "$passes passed, $failures failed"
[ "$failures" -eq 0 ] && echo "ALL CHECKS PASSED" || exit 1
