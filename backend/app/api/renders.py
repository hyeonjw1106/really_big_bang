import asyncio
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session, SessionLocal
from app.core.storage import ensure_subdir
from app.db.models import SceneFile, RenderJob, Epoch
from app.schemas.renders import SceneOut, RenderJobOut, RenderJobCreate

router = APIRouter(prefix="/renders", tags=["renders"])


async def _save_scene_file(file: UploadFile, name_override: str | None) -> tuple[str, Path, int]:
    if not file.filename:
        raise HTTPException(status_code=400, detail="파일 이름이 비어 있습니다.")

    ext = Path(file.filename).suffix.lower()
    if ext != ".blend":
        raise HTTPException(status_code=400, detail="블렌더(.blend) 파일만 업로드 가능합니다.")

    scene_name = name_override or Path(file.filename).stem
    data = await file.read()
    dest_dir = ensure_subdir("scenes")
    dest_path = dest_dir / f"{uuid4().hex}{ext}"
    await asyncio.to_thread(dest_path.write_bytes, data)
    return scene_name, dest_path, len(data)


async def enqueue_render_job(job_id: int):
    async def _runner():
        async with SessionLocal() as session:
            job = await session.get(RenderJob, job_id)
            if not job:
                return

            job.status = "processing"
            job.message = "블렌더 렌더링 준비"
            job.updated_at = datetime.utcnow()
            await session.commit()

            render_dir = ensure_subdir("renders")
            output_path = render_dir / f"{job.id}.txt"
            payload = {
                "scene_id": job.scene_id,
                "epoch_id": job.epoch_id,
                "time_norm": job.time_norm,
                "params": job.params or {},
            }
            # 실제 블렌더 호출 대신 더미 파일 생성
            content = f"rendered at {datetime.utcnow().isoformat()}Z\n{payload}\n"
            await asyncio.to_thread(output_path.write_text, content)

            job.status = "done"
            job.message = "렌더 완료"
            job.output_path = str(output_path)
            job.updated_at = datetime.utcnow()
            await session.commit()

    asyncio.create_task(_runner())


@router.post("/scenes", response_model=SceneOut)
async def upload_scene(
    file: UploadFile = File(...),
    name: str | None = Form(default=None),
    s: AsyncSession = Depends(get_session),
):
    scene_name, dest_path, size = await _save_scene_file(file, name)
    scene = SceneFile(
        name=scene_name,
        original_name=file.filename,
        file_path=str(dest_path),
        file_size=size,
    )
    s.add(scene)
    await s.commit()
    await s.refresh(scene)
    return scene


@router.get("/scenes", response_model=list[SceneOut])
async def list_scenes(limit: int = 50, offset: int = 0, s: AsyncSession = Depends(get_session)):
    q = select(SceneFile).order_by(SceneFile.uploaded_at.desc()).limit(limit).offset(offset)
    scenes = (await s.execute(q)).scalars().all()
    return scenes


@router.post("", response_model=RenderJobOut, status_code=201)
async def create_render_job(payload: RenderJobCreate, s: AsyncSession = Depends(get_session)):
    scene = await s.get(SceneFile, payload.scene_id)
    if not scene:
        raise HTTPException(status_code=404, detail="scene not found")

    if payload.epoch_id:
        epoch = await s.get(Epoch, payload.epoch_id)
        if not epoch:
            raise HTTPException(status_code=404, detail="epoch not found")

    params = {
        "resolution": {"x": payload.resolution_x, "y": payload.resolution_y},
        "format": payload.format,
        "camera": payload.camera,
    }
    job = RenderJob(
        scene_id=payload.scene_id,
        epoch_id=payload.epoch_id,
        time_norm=payload.time_norm,
        status="queued",
        params=params,
    )
    s.add(job)
    await s.commit()
    await s.refresh(job)

    await enqueue_render_job(job.id)
    return job


@router.get("", response_model=list[RenderJobOut])
async def list_render_jobs(limit: int = 50, offset: int = 0, s: AsyncSession = Depends(get_session)):
    q = select(RenderJob).order_by(RenderJob.created_at.desc()).limit(limit).offset(offset)
    return (await s.execute(q)).scalars().all()


@router.get("/{job_id}", response_model=RenderJobOut)
async def get_render_job(job_id: int, s: AsyncSession = Depends(get_session)):
    job = await s.get(RenderJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="render job not found")
    return job


@router.get("/{job_id}/file")
async def download_render_file(job_id: int, s: AsyncSession = Depends(get_session)):
    job = await s.get(RenderJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="render job not found")
    if job.status != "done" or not job.output_path:
        raise HTTPException(status_code=400, detail="렌더가 아직 완료되지 않았습니다.")

    path = Path(job.output_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="결과 파일을 찾을 수 없습니다.")

    return FileResponse(
        path=path,
        media_type="text/plain",
        filename=path.name,
    )
