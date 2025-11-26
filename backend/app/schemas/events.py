from pydantic import BaseModel, ConfigDict, Field


class CosmicEventBase(BaseModel):
    title: str
    description: str | None = None
    time_norm: float = Field(..., ge=0.0, le=1.0, description="0~1 정규화 시간(빅뱅=0, 현재=1)")
    epoch_id: int | None = None


class CosmicEventOut(CosmicEventBase):
    id: int
    category: str | None = None
    model_config = ConfigDict(from_attributes=True)


class CosmicEventDetail(CosmicEventOut):
    media_url: str | None = None
