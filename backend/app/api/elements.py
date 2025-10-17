from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.db import get_session
from app.db.models import Element
from app.schemas.elements import ElementOut

router = APIRouter(prefix="/elements", tags=["elements"])

@router.get("", response_model=list[ElementOut])
async def list_elements(limit: int = 50, offset: int = 0, s: AsyncSession = Depends(get_session)):
    q = select(Element).order_by(Element.name).limit(limit).offset(offset)
    return (await s.execute(q)).scalars().all()

@router.get("/{element_id}", response_model=ElementOut)
async def get_element(element_id: int, s: AsyncSession = Depends(get_session)):
    el = await s.get(Element, element_id)
    if not el:
        raise HTTPException(404, "element not found")
    return el