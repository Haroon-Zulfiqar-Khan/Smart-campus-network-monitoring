from datetime import datetime
from fastapi import APIRouter, Depends, Query
from .. import schemas as S
from ..security import current_user
from ..db import get_db
from ..viewmodels.tests import TestsViewModel

viewmodel = TestsViewModel()
router = APIRouter(tags=["Speed tests"])


@router.post("/test-sessions", status_code=201)
def start(data: S.StartTest, user=Depends(current_user), db=Depends(get_db)):
    return viewmodel.start(data=data, user=user, db=db)


@router.post("/test-sessions/{id}/result")
def result(id: str, data: S.TestOutcome, user=Depends(current_user), db=Depends(get_db)):
    return viewmodel.result(id=id, data=data, user=user, db=db)


@router.get("/tests")
def history(
    location_id: str | None = None,
    building_id: str | None = None,
    status: str | None = None,
    health: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    mine: bool = True,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user=Depends(current_user),
    db=Depends(get_db),
):
    return viewmodel.history(
        location_id=location_id,
        building_id=building_id,
        status=status,
        health=health,
        since=since,
        until=until,
        mine=mine,
        limit=limit,
        offset=offset,
        user=user,
        db=db,
    )


@router.get("/tests/{id}")
def test(id: str, user=Depends(current_user), db=Depends(get_db)):
    return viewmodel.test(id=id, user=user, db=db)
