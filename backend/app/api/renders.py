import asyncio
import subprocess
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
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
        job.message = "GLTF(.glb) 변환 준비"
        job.updated_at = datetime.utcnow()
        await session.commit()

        render_dir = ensure_subdir("renders")
        scene = await session.get(SceneFile, job.scene_id)
        
        if not scene:
            job.status = "failed"
            job.message = f"원본 Scene 파일(id:{job.scene_id})을 찾을 수 없습니다."
            job.updated_at = datetime.utcnow()
            await session.commit()
            return

        export_ok, output_path = await _export_glb_with_blender(job, scene, render_dir)

        if export_ok and output_path:
            job.status = "done"
            job.message = "GLB 변환 완료"
            job.output_path = str(output_path)
        else:
            job.status = "failed"
            job.message = "GLB 변환 실패"

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
        "format": "glb",
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

    media_type = "application/octet-stream"
    if path.suffix.lower() == ".png":
        media_type = "image/png"
    elif path.suffix.lower() == ".glb":
        media_type = "model/gltf-binary"
        
    return FileResponse(path=path, media_type=media_type, filename=path.name)


async def _export_glb_with_blender(job: RenderJob, scene: SceneFile, render_dir: Path) -> tuple[bool, Path | None]:
    """Blender CLI를 호출하여 .glb 파일을 익스포트합니다. 성공 시 (True, output_path), 실패 시 (False, None)"""
    blender_bin = settings.BLENDER_BIN or "blender"
    scene_path = Path(scene.file_path).resolve()
    render_dir = render_dir.resolve()
    output_path = render_dir / f"{job.id}.glb"
    
    # core/export_gltf.py 스크립트의 경로를 찾습니다.
    exporter_script_path = Path(__file__).parent.parent / "core" / "export_gltf.py"
    
    if not scene_path.exists():
        print(f"Blender export failed for job {job.id}: Scene file not found at {scene_path}")
        return False, None
    
    if not exporter_script_path.exists():
        print(f"Blender export failed for job {job.id}: Exporter script not found at {exporter_script_path}")
        return False, None

    cmd = [
        blender_bin,
        "-b",  # 백그라운드 모드
        str(scene_path),
        "--python",
        str(exporter_script_path),
        "--",
        str(output_path),
    ]

    try:
        print(f"Executing Blender command for job {job.id}: {' '.join(cmd)}")
        result = await asyncio.to_thread(
            subprocess.run, 
            cmd, 
            check=True, 
            capture_output=True, 
            text=True
        )
        if result.stdout:
            print(f"[blender stdout] job {job.id}:\n{result.stdout}")
        if result.stderr:
            print(f"[blender stderr] job {job.id}:\n{result.stderr}")
        
        if output_path.exists():
            return True, output_path
        else:
            print(f"Blender export failed for job {job.id}: Output file not found after execution.")
            return False, None
            
    except subprocess.CalledProcessError as exc:
        print(f"Blender export subprocess failed for job {job.id} with exit code {exc.returncode}")
        print(f"  command: {' '.join(exc.cmd)}")
        print(f"  stdout: {exc.stdout}")
        print(f"  stderr: {exc.stderr}")
    except Exception as exc:
        print(f"An unexpected error occurred during Blender export for job {job.id}: {exc}")
        
    return False, None
