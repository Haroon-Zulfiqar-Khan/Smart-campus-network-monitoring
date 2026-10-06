from fastapi import APIRouter, Depends, Query
from ..security import admin
from ..db import get_db
from ..viewmodels.ai import AIViewModel, BatchInput

router = APIRouter(prefix="/admin/ai", tags=["Administrator AI"])
viewmodel = AIViewModel()


@router.get("")
def listing(user=Depends(admin), db=Depends(get_db)):
    return viewmodel.listing(user=user, db=db)


@router.post("/classify-pending")
def batch(data: BatchInput, user=Depends(admin), db=Depends(get_db)):
    return viewmodel.batch(data=data, user=user, db=db)


@router.post("/complaints/{id}/classify")
def classify(id: str, user=Depends(admin), db=Depends(get_db)):
    return viewmodel.classify_one(id=id, user=user, db=db)


@router.post("/complaints/{id}/apply")
def apply(id: str, user=Depends(admin), db=Depends(get_db)):
    return viewmodel.apply(id=id, user=user, db=db)


@router.post("/network-summary")
def summary(hours: int = Query(72), user=Depends(admin), db=Depends(get_db)):
    return viewmodel.summary(hours=hours, user=user, db=db)
