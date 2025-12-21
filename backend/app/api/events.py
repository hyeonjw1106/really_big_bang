from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.api.renders import enqueue_render_job, get_or_create_placeholder_scene
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
async def render_event(event_id: int, scene_id: int | None = None, s: AsyncSession = Depends(get_session)):
    ev = await s.get(CosmicEvent, event_id)
    if not ev:
        raise HTTPException(status_code=404, detail="event not found")

    scene = await _resolve_scene_for_event(s, ev, scene_id)

    job = RenderJob(
        scene_id=scene.id,
        epoch_id=ev.epoch_id,
        time_norm=ev.time_norm,
        status="queued",
        params={
            "event_title": ev.title,
            "event_category": ev.category,
            "event_time_range": ev.time_range,
            "event_description": ev.description,
        },
        message="코스믹 이벤트 렌더 큐 등록",
    )
    s.add(job)
    await s.commit()
    await s.refresh(job)

    await enqueue_render_job(job.id)
    return await s.get(RenderJob, job.id)


# 이벤트 제목별로 씬을 자동 매핑한다.
# 사용자가 scene_id를 주면 우선 사용하고, 없으면 제목 기반 매핑 → default_scene → placeholder 순.
async def _resolve_scene_for_event(session: AsyncSession, ev: CosmicEvent, scene_id: int | None) -> SceneFile:
    if scene_id:
        scene = await session.get(SceneFile, scene_id)
        if scene:
            return scene

    # 키워드 매핑
    title = ev.title
    key_to_scene_name = {
        "쿼크 생성": "Scene 1",
        "전자·쿼크 생성": "Scene 2",
        "양성자/중성자 결합": "Scene 3",
        "양성자·중성자 형성": "Scene 4",
    }
    target_name = None
    for key, name in key_to_scene_name.items():
        if key in title:
            target_name = name
            break

    if target_name:
        q = select(SceneFile).where(SceneFile.name.ilike(f"%{target_name}%")).order_by(SceneFile.id)
        scene = (await session.execute(q)).scalar_one_or_none()
        if scene:
            return scene

    # default_scene_id가 있으면 사용
    if ev.default_scene_id:
        scene = await session.get(SceneFile, ev.default_scene_id)
        if scene:
            return scene

    # 아무것도 없으면 placeholder
    return await get_or_create_placeholder_scene(session)
