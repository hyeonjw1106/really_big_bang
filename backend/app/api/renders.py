import asyncio
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from PIL import Image, ImageDraw, ImageFont

from app.core.db import get_session, SessionLocal
from app.core.storage import ensure_subdir
from app.db.models import SceneFile, RenderJob, Epoch
from app.schemas.renders import SceneOut, RenderJobOut, RenderJobCreate

router = APIRouter(prefix="/renders", tags=["renders"])


async def get_or_create_placeholder_scene(session: AsyncSession) -> SceneFile:
    q = select(SceneFile).where(SceneFile.name == "Placeholder Scene")
    existing = (await session.execute(q)).scalar_one_or_none()
    if existing:
        return existing

    scenes_dir = ensure_subdir("scenes")
    placeholder_path = scenes_dir / "placeholder.blend"
    if not placeholder_path.exists():
        placeholder_path.write_text("placeholder blend file (dummy)")
    scene = SceneFile(
        name="Placeholder Scene",
        original_name="placeholder.blend",
        file_path=str(placeholder_path),
        file_size=placeholder_path.stat().st_size,
    )
    session.add(scene)
    await session.commit()
    await session.refresh(scene)
    return scene


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
    async with SessionLocal() as session:
        job = await session.get(RenderJob, job_id)
        if not job:
            return

        job.status = "processing"
        job.message = "블렌더 렌더링 준비"
        job.updated_at = datetime.utcnow()
        await session.commit()

        render_dir = ensure_subdir("renders")
        output_path = render_dir / f"{job.id}.png"
        payload = {
            "scene_id": job.scene_id,
            "epoch_id": job.epoch_id,
            "time_norm": job.time_norm,
            "params": job.params or {},
        }

        res_x = int(job.params.get("resolution", {}).get("x", 1280)) if job.params else 1280
        res_y = int(job.params.get("resolution", {}).get("y", 720)) if job.params else 720
        res_x = max(256, min(res_x, 1920))
        res_y = max(256, min(res_y, 1080))

        # 더미 이미지 생성 (블렌더 렌더 대체)
        def _draw_image():
            import random

            rng = random.Random()
            rng.seed(f"{job.id}-{job.time_norm}")

            img = Image.new("RGB", (res_x, res_y), color=(4, 6, 14))
            draw = ImageDraw.Draw(img)

            # 배경 그라데이션
            for y in range(res_y):
                ratio = y / max(res_y - 1, 1)
                r = int(6 + 10 * ratio)
                g = int(12 + 24 * ratio)
                b = int(24 + 40 * ratio)
                draw.line([(0, y), (res_x, y)], fill=(r, g, b))

            # 별 뿌리기
            star_count = 400
            for _ in range(star_count):
                x = rng.randint(0, res_x - 1)
                y = rng.randint(0, res_y - 1)
                brightness = rng.randint(150, 255)
                size = 1 if rng.random() < 0.9 else 2
                draw.ellipse([(x, y), (x + size, y + size)], fill=(brightness, brightness, brightness))

            # 은하/링 효과
            center = (res_x // 2, res_y // 2)
            ring_color = (80, 180, 255)
            for radius in range(80, min(res_x, res_y) // 2, 60):
                alpha = 50
                draw.ellipse(
                    [
                        (center[0] - radius, center[1] - radius // 2),
                        (center[0] + radius, center[1] + radius // 2),
                    ],
                    outline=ring_color,
                    width=2,
                )

            # 이벤트 마커 (time_norm 기반)
            tn = max(0.0, min(job.time_norm, 1.0))
            marker_x = int(40 + tn * (res_x - 80))
            marker_y = center[1]
            draw.ellipse(
                [(marker_x - 8, marker_y - 8), (marker_x + 8, marker_y + 8)],
                fill=(255, 200, 120),
                outline=(255, 240, 200),
                width=2,
            )
            draw.line([(40, marker_y), (res_x - 40, marker_y)], fill=(90, 140, 220), width=2)

            font = ImageFont.load_default()
            header = f"Render Job #{job.id}"
            sub = f"time_norm={job.time_norm:.4f}  scene={job.scene_id}  epoch={job.epoch_id}"
            event_title = job.params.get("event_title") if job.params else None
            event_cat = job.params.get("event_category") if job.params else None
            event_range = job.params.get("event_time_range") if job.params else None
            event_desc = job.params.get("event_description") if job.params else None
            draw.text((24, 20), header, fill=(255, 255, 255), font=font)
            draw.text((24, 40), sub, fill=(200, 220, 255), font=font)
            if event_title or event_cat:
                draw.text((24, 60), f"event: {event_title or ''} [{event_cat or ''}]", fill=(255, 220, 180), font=font)
            if event_range:
                draw.text((24, 76), f"time: {event_range}", fill=(200, 240, 200), font=font)
            if event_desc:
                draw.text((24, 92), f"{event_desc}", fill=(190, 190, 190), font=font)
            draw.text((24, res_y - 40), datetime.utcnow().isoformat() + "Z", fill=(140, 180, 255), font=font)

            img.save(output_path, format="PNG")

        await asyncio.to_thread(_draw_image)

        job.status = "done"
        job.message = "렌더 완료"
        job.output_path = str(output_path)
        job.updated_at = datetime.utcnow()
        await session.commit()


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
    if not scenes:
        placeholder = await get_or_create_placeholder_scene(s)
        return [placeholder]
    return scenes


@router.post("", response_model=RenderJobOut, status_code=201)
async def create_render_job(payload: RenderJobCreate, s: AsyncSession = Depends(get_session)):
    scene: SceneFile | None = None
    if payload.scene_id:
        scene = await s.get(SceneFile, payload.scene_id)
        if not scene:
            raise HTTPException(status_code=404, detail="scene not found")
    else:
        scene = await get_or_create_placeholder_scene(s)

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
        scene_id=scene.id,
        epoch_id=payload.epoch_id,
        time_norm=payload.time_norm,
        status="queued",
        params=params,
    )
    s.add(job)
    await s.commit()
    await s.refresh(job)

    await enqueue_render_job(job.id)
    return await s.get(RenderJob, job.id)


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

    media_type = "image/png" if path.suffix.lower() == ".png" else "application/octet-stream"
    return FileResponse(path=path, media_type=media_type, filename=path.name)
