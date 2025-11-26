from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.api.renders import enqueue_render_job
from app.db.models import CosmicEvent, SceneFile, RenderJob
from app.schemas.events import CosmicEventOut, CosmicEventDetail
from app.schemas.renders import RenderJobOut

router = APIRouter(prefix="/events", tags=["events"])


@router.get("", response_model=list[CosmicEventOut])
async def list_events(limit: int = 50, offset: int = 0, s: AsyncSession = Depends(get_session)):
    q = select(CosmicEvent).order_by(CosmicEvent.time_norm).limit(limit).offset(offset)
    return (await s.execute(q)).scalars().all()


@router.get("/{event_id}", response_model=CosmicEventDetail)
async def get_event(event_id: int, s: AsyncSession = Depends(get_session)):
    ev = await s.get(CosmicEvent, event_id)
    if not ev:
        raise HTTPException(status_code=404, detail="event not found")
    return ev


@router.post("/{event_id}/render", response_model=RenderJobOut, status_code=201)
async def render_event(event_id: int, scene_id: int, s: AsyncSession = Depends(get_session)):
    ev = await s.get(CosmicEvent, event_id)
    if not ev:
        raise HTTPException(status_code=404, detail="event not found")

    scene = await s.get(SceneFile, scene_id)
    if not scene:
        raise HTTPException(status_code=404, detail="scene not found")

    job = RenderJob(
        scene_id=scene_id,
        epoch_id=ev.epoch_id,
        time_norm=ev.time_norm,
        status="queued",
        params={"event_title": ev.title, "event_category": ev.category},
        message="코스믹 이벤트 렌더 큐 등록",
    )
    s.add(job)
    await s.commit()
    await s.refresh(job)

    await enqueue_render_job(job.id)
    return job
