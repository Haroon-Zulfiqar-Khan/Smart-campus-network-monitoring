from fastapi import APIRouter, Depends, Query
from .. import schemas as S
from ..security import current_user, operator
from ..db import get_db
from ..viewmodels.incidents import IncidentsViewModel

viewmodel = IncidentsViewModel()
router = APIRouter(prefix="/incidents", tags=["Incidents"])


@router.get("")
def listing(
    location_id: str | None = None,
    status: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user=Depends(current_user),
    db=Depends(get_db),
):
    return viewmodel.listing(
        location_id=location_id, status=status, limit=limit, offset=offset, user=user, db=db
    )


@router.get("/{id}")
def detail(id: str, user=Depends(current_user), db=Depends(get_db)):
    return viewmodel.detail(id=id, user=user, db=db)


@router.patch("/{id}/assignment")
def assign(id: str, data: S.IncidentAssignment, user=Depends(operator), db=Depends(get_db)):
    return viewmodel.assign(id=id, data=data, user=user, db=db)


@router.post("/{id}/transitions")
def transition(id: str, data: S.IncidentTransition, user=Depends(operator), db=Depends(get_db)):
    return viewmodel.transition(id=id, data=data, user=user, db=db)


@router.post("/{id}/notes", status_code=201)
def note(id: str, data: S.Note, user=Depends(operator), db=Depends(get_db)):
    return viewmodel.note(id=id, data=data, user=user, db=db)
