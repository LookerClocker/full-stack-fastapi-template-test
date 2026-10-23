import pytest
from sqlmodel import Session

from app import crud
from app.core.config import settings
from app.core.db import DEMO_USER_EMAILS, init_db


def delete_demo_users(db: Session) -> None:
    for email in DEMO_USER_EMAILS.values():
        user = crud.get_user_by_email(session=db, email=email)
        if user:
            db.delete(user)
    db.commit()


def test_demo_users_are_seeded_in_development(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "FASTAPI_ENV", "development")
    monkeypatch.setattr(settings, "DEMO_USER_PASSWORD", "demo-password")
    delete_demo_users(db)

    init_db(db)

    for role, email in DEMO_USER_EMAILS.items():
        user = crud.get_user_by_email(session=db, email=email)
        assert user is not None
        assert user.role == role


def test_demo_users_are_not_seeded_outside_development(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "FASTAPI_ENV", None)
    monkeypatch.setattr(settings, "DEMO_USER_PASSWORD", "demo-password")
    delete_demo_users(db)

    init_db(db)

    for email in DEMO_USER_EMAILS.values():
        assert crud.get_user_by_email(session=db, email=email) is None
