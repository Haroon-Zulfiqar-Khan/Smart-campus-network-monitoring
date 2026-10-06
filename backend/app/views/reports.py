from datetime import datetime
from fastapi import APIRouter, Depends
from fastapi.responses import Response
from ..security import current_user, operator
from ..db import get_db
from ..viewmodels.reports import ReportsViewModel

viewmodel = ReportsViewModel()
router = APIRouter(tags=["Dashboard and analytics"])


@router.get("/dashboard")
def dashboard(
    location_id: str | None = None,
    building_id: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    network_status: str | None = None,
    category: str | None = None,
    complaint_status: str | None = None,
    user=Depends(current_user),
    db=Depends(get_db),
):
    return viewmodel.dashboard(
        location_id=location_id,
        building_id=building_id,
        since=since,
        until=until,
        network_status=network_status,
        category=category,
        complaint_status=complaint_status,
        user=user,
        db=db,
    )


@router.get("/analytics")
def analytics(
    location_id: str | None = None,
    building_id: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    network_status: str | None = None,
    category: str | None = None,
    complaint_status: str | None = None,
    user=Depends(operator),
    db=Depends(get_db),
):
    return viewmodel.analytics(
        location_id=location_id,
        building_id=building_id,
        since=since,
        until=until,
        network_status=network_status,
        category=category,
        complaint_status=complaint_status,
        user=user,
        db=db,
    )


@router.get("/reports/tests.csv")
def export(
    location_id: str | None = None,
    building_id: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    user=Depends(operator),
    db=Depends(get_db),
):
    data = viewmodel.export(
        location_id=location_id, building_id=building_id, since=since, until=until, user=user, db=db
    )
    return Response(
        data["content"],
        media_type=data["media_type"],
        headers={"Content-Disposition": "attachment; filename=campus-tests.csv"},
    )


@router.post("/intelligence/classify")
def classify(data: dict, user=Depends(current_user)):
    return viewmodel.classify(data=data, user=user)
