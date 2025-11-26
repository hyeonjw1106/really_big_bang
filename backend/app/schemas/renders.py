from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class SceneOut(BaseModel):
    id: int
    name: str
    original_name: str
    file_size: int | None = None
    uploaded_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RenderJobCreate(BaseModel):
    scene_id: int
    epoch_id: int | None = Field(default=None, description="어느 epoch에 대응하는 렌더인지 선택")
    time_norm: float = Field(..., ge=0.0, le=1.0, description="0~1 정규화된 시간 값")
    resolution_x: int = Field(default=1280, ge=256, le=7680)
    resolution_y: int = Field(default=720, ge=256, le=4320)
    format: str = Field(default="PNG", description="렌더 결과 포맷")
    camera: str | None = Field(default=None, description="블렌더 씬 카메라 이름")


class RenderJobOut(BaseModel):
    id: int
    scene_id: int
    epoch_id: int | None
    time_norm: float
    status: str
    message: str | None = None
    output_path: str | None = None
    params: dict | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
