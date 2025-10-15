from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.db import get_session
from app.db.models import Epoch, Annotation
from app.schemas.epochs import EpochOut, EpochDetailOut, AnnotationOut

router = APIRouter(prefix="/epochs", tags=["epochs"])

@router.get("", response_model=list[EpochOut])
async def list_epochs(limit: int = 50, offset: int = 0, s: AsyncSession = Depends(get_session)):
    q = select(Epoch).order_by(Epoch.start_norm).limit(limit).offset(offset)
    rows = (await s.execute(q)).scalars().all()
    return rows

@router.get("/{epoch_id}", response_model=EpochDetailOut)
async def get_epoch(epoch_id: int, s: AsyncSession = Depends(get_session)):
    ep = await s.get(Epoch, epoch_id)
    if not ep:
        raise HTTPException(404, "epoch not found")
    # 관계 로딩 (annotations)
    await s.refresh(ep, attribute_names=["annotations"])
    return ep

@router.get("/{epoch_id}/annotations", response_model=list[AnnotationOut])
async def list_annotations(epoch_id: int, s: AsyncSession = Depends(get_session)):
    q = select(Annotation).where(Annotation.epoch_id == epoch_id).order_by(Annotation.time_mark)
    return (await s.execute(q)).scalars().all()