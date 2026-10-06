from fastapi import APIRouter, Depends, Query
from .. import schemas as S
from ..security import current_user, operator
from ..db import get_db
from ..viewmodels.operations import OperationsViewModel

viewmodel = OperationsViewModel()
router = APIRouter(tags=["Maintenance and notifications"])


@router.post("/maintenance", status_code=201)
def create(data: S.MaintenanceCreate, user=Depends(operator), db=Depends(get_db)):
    return viewmodel.create(data=data, user=user, db=db)


@router.get("/maintenance")
def maintenance(
    location_id: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user=Depends(current_user),
    db=Depends(get_db),
):
    return viewmodel.maintenance(
        location_id=location_id, limit=limit, offset=offset, user=user, db=db
    )


@router.post("/maintenance/{id}/cancel")
def cancel(id: str, user=Depends(operator), db=Depends(get_db)):
    return viewmodel.cancel(id=id, user=user, db=db)


@router.get("/notifications")
def notifications(
    unread_only: bool = False,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user=Depends(current_user),
    db=Depends(get_db),
):
    return viewmodel.notifications(
        unread_only=unread_only, limit=limit, offset=offset, user=user, db=db
    )


@router.patch("/notifications/{id}/read")
def mark_read(id: str, user=Depends(current_user), db=Depends(get_db)):
    return viewmodel.mark_read(id=id, user=user, db=db)
