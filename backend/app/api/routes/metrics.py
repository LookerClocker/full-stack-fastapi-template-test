from fastapi import APIRouter, Depends
from sqlmodel import Session, col, func, select

from app.api.deps import SessionDep, require_permission
from app.core.rbac import Permission, Role
from app.models import Item, MetricsPublic, User

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get(
    "/",
    dependencies=[Depends(require_permission(Permission.METRICS_READ))],
    response_model=MetricsPublic,
)
def read_metrics(session: SessionDep) -> MetricsPublic:
    """
    Aggregate user and item counts for the insights page.
    """
    return MetricsPublic(
        total_users=session.exec(select(func.count()).select_from(User)).one(),
        active_users=session.exec(
            select(func.count()).select_from(User).where(col(User.is_active))
        ).one(),
        total_items=session.exec(select(func.count()).select_from(Item)).one(),
        users_by_role=count_users_by_role(session),
    )


def count_users_by_role(session: Session) -> dict[Role, int]:
    rows = session.exec(
        select(col(User.role), func.count()).group_by(col(User.role))
    ).all()
    counts = {Role(role): count for role, count in rows}
    return {role: counts.get(role, 0) for role in Role}
