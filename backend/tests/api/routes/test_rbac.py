import logging

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings
from app.core.rbac import ROLE_PERMISSIONS, Permission, Role
from tests.utils.item import create_random_item
from tests.utils.user import create_random_user
from tests.utils.utils import random_email, random_lower_string

API = settings.API_V1_STR

TOKEN_FIXTURE_BY_ROLE = {
    Role.ADMIN: "superuser_token_headers",
    Role.MANAGER: "manager_token_headers",
    Role.MEMBER: "normal_user_token_headers",
}


def auth_headers(request: pytest.FixtureRequest, role: Role) -> dict[str, str]:
    headers: dict[str, str] = request.getfixturevalue(TOKEN_FIXTURE_BY_ROLE[role])
    return headers


# (role, method, path, expected status) — mirrors the README permission matrix.
ACCESS_MATRIX = [
    (Role.ADMIN, "GET", "/users/", 200),
    (Role.MANAGER, "GET", "/users/", 200),
    (Role.MEMBER, "GET", "/users/", 403),
    (Role.ADMIN, "GET", "/metrics/", 200),
    (Role.MANAGER, "GET", "/metrics/", 200),
    (Role.MEMBER, "GET", "/metrics/", 403),
    (Role.ADMIN, "GET", "/users/me", 200),
    (Role.MANAGER, "GET", "/users/me", 200),
    (Role.MEMBER, "GET", "/users/me", 200),
]


@pytest.mark.parametrize(("role", "method", "path", "expected_status"), ACCESS_MATRIX)
def test_endpoint_access_by_role(
    client: TestClient,
    request: pytest.FixtureRequest,
    role: Role,
    method: str,
    path: str,
    expected_status: int,
) -> None:
    response = client.request(
        method, f"{API}{path}", headers=auth_headers(request, role)
    )
    assert response.status_code == expected_status


def test_admin_can_create_user_with_role(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    body = {
        "email": random_email(),
        "password": random_lower_string(),
        "role": "manager",
    }
    response = client.post(f"{API}/users/", headers=superuser_token_headers, json=body)
    assert response.status_code == 200
    assert response.json()["role"] == "manager"


@pytest.mark.parametrize("role", [Role.MANAGER, Role.MEMBER])
def test_non_admin_cannot_create_users(
    client: TestClient, request: pytest.FixtureRequest, role: Role
) -> None:
    body = {"email": random_email(), "password": random_lower_string()}
    response = client.post(
        f"{API}/users/", headers=auth_headers(request, role), json=body
    )
    assert response.status_code == 403


def test_manager_cannot_update_other_users(
    client: TestClient, manager_token_headers: dict[str, str], db: Session
) -> None:
    user = create_random_user(db)
    response = client.patch(
        f"{API}/users/{user.id}", headers=manager_token_headers, json={"role": "admin"}
    )
    assert response.status_code == 403


def test_member_cannot_escalate_via_own_profile(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    response = client.patch(
        f"{API}/users/me",
        headers=normal_user_token_headers,
        json={"full_name": "Still A Member", "role": "admin"},
    )
    assert response.status_code == 200
    assert response.json()["role"] == "member"


def test_signup_always_creates_member(client: TestClient) -> None:
    body = {"email": random_email(), "password": random_lower_string(), "role": "admin"}
    response = client.post(f"{API}/users/signup", json=body)
    assert response.status_code == 200
    assert response.json()["role"] == "member"


def test_admin_cannot_change_own_role(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    me = client.get(f"{API}/users/me", headers=superuser_token_headers).json()
    response = client.patch(
        f"{API}/users/{me['id']}",
        headers=superuser_token_headers,
        json={"role": "member"},
    )
    assert response.status_code == 403


def test_current_user_exposes_role_permissions(
    client: TestClient, manager_token_headers: dict[str, str]
) -> None:
    me = client.get(f"{API}/users/me", headers=manager_token_headers).json()
    assert me["role"] == "manager"
    assert me["permissions"] == sorted(ROLE_PERMISSIONS[Role.MANAGER])


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer not-a-token"}])
def test_unauthenticated_requests_get_401(
    client: TestClient, headers: dict[str, str]
) -> None:
    response = client.get(f"{API}/users/me", headers=headers)
    assert response.status_code == 401


def test_permission_denial_is_logged(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING, logger="app.api.deps"):
        client.get(f"{API}/metrics/", headers=normal_user_token_headers)
    assert Permission.METRICS_READ.value in caplog.text


def test_manager_cannot_send_test_email(
    client: TestClient, manager_token_headers: dict[str, str]
) -> None:
    response = client.post(
        f"{API}/utils/test-email/",
        headers=manager_token_headers,
        params={"email_to": random_email()},
    )
    assert response.status_code == 403


def test_manager_cannot_preview_recovery_email(
    client: TestClient, manager_token_headers: dict[str, str]
) -> None:
    response = client.post(
        f"{API}/password-recovery-html-content/{settings.FIRST_SUPERUSER}",
        headers=manager_token_headers,
    )
    assert response.status_code == 403


def test_manager_cannot_access_other_users_items(
    client: TestClient, manager_token_headers: dict[str, str], db: Session
) -> None:
    item_url = f"{API}/items/{create_random_item(db).id}"
    headers = manager_token_headers

    assert client.get(item_url, headers=headers).status_code == 403
    assert (
        client.put(item_url, headers=headers, json={"title": "Taken"}).status_code
        == 403
    )
    assert client.delete(item_url, headers=headers).status_code == 403


def test_manager_sees_only_own_items(
    client: TestClient, manager_token_headers: dict[str, str], db: Session
) -> None:
    other_users_item = create_random_item(db)
    client.post(f"{API}/items/", headers=manager_token_headers, json={"title": "Mine"})
    manager_id = client.get(f"{API}/users/me", headers=manager_token_headers).json()[
        "id"
    ]

    items = client.get(f"{API}/items/", headers=manager_token_headers).json()["data"]

    assert items
    assert {item["owner_id"] for item in items} == {manager_id}
    assert str(other_users_item.id) not in {item["id"] for item in items}


def test_admin_can_access_any_item(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    item = create_random_item(db)
    response = client.get(f"{API}/items/{item.id}", headers=superuser_token_headers)
    assert response.status_code == 200


def test_admin_holds_every_permission() -> None:
    assert ROLE_PERMISSIONS[Role.ADMIN] == frozenset(Permission)


def test_member_holds_no_elevated_permissions() -> None:
    assert ROLE_PERMISSIONS[Role.MEMBER] == frozenset()
