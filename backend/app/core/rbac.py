"""Roles, permissions, and which role holds which permission.

This module is the single source of truth for authorization policy. Code elsewhere
asks "does this user have permission X?" and never "is this user role Y?".
"""

from enum import StrEnum


class Role(StrEnum):
    ADMIN = "admin"
    MANAGER = "manager"
    MEMBER = "member"


class Permission(StrEnum):
    USERS_READ = "users:read"
    USERS_CREATE = "users:create"
    USERS_UPDATE = "users:update"
    USERS_DELETE = "users:delete"
    METRICS_READ = "metrics:read"
    SETTINGS_MANAGE = "settings:manage"
    ITEMS_MANAGE_ALL = "items:manage_all"


# Anything not listed here is denied. Every authenticated user may always manage
# their own profile and their own items; those need no permission.
ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.ADMIN: frozenset(Permission),
    Role.MANAGER: frozenset({Permission.USERS_READ, Permission.METRICS_READ}),
    Role.MEMBER: frozenset(),
}


def permissions_for(role: Role) -> frozenset[Permission]:
    return ROLE_PERMISSIONS[role]


def has_permission(role: Role, permission: Permission) -> bool:
    return permission in permissions_for(role)
