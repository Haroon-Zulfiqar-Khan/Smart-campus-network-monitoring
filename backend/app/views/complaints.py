from datetime import datetime
from fastapi import APIRouter, Depends, Query
from .. import schemas as S
from ..security import current_user, operator
from ..db import get_db
from ..viewmodels.complaints import ComplaintsViewModel

viewmodel = ComplaintsViewModel()
router = APIRouter(prefix="/complaints", tags=["Complaints"])


@router.post("", status_code=201)
def create(data: S.ComplaintCreate, user=Depends(current_user), db=Depends(get_db)):
    return viewmodel.create(data=data, user=user, db=db)


@router.get("")
def listing(
    location_id: str | None = None,
    building_id: str | None = None,
    category: S.Category | None = None,
    status: str | None = None,
    assignee_id: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user=Depends(current_user),
    db=Depends(get_db),
):
    return viewmodel.listing(
        location_id=location_id,
        building_id=building_id,
        category=category,
        status=status,
        assignee_id=assignee_id,
        since=since,
        until=until,
        limit=limit,
        offset=offset,
        user=user,
        db=db,
    )


@router.get("/{id}")
def detail(id: str, user=Depends(current_user), db=Depends(get_db)):
    return viewmodel.detail(id=id, user=user, db=db)


@router.patch("/{id}/assignment")
def assign(id: str, data: S.Assignment, user=Depends(operator), db=Depends(get_db)):
    return viewmodel.assign(id=id, data=data, user=user, db=db)


@router.post("/{id}/transitions")
def transition(
    id: str, data: S.ComplaintTransition, user=Depends(current_user), db=Depends(get_db)
):
    return viewmodel.transition(id=id, data=data, user=user, db=db)


@router.post("/{id}/notes", status_code=201)
def note(id: str, data: S.Note, user=Depends(current_user), db=Depends(get_db)):
    return viewmodel.note(id=id, data=data, user=user, db=db)
