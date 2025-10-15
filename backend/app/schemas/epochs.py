from pydantic import BaseModel, ConfigDict

class AnnotationOut(BaseModel):
    id: int
    title: str
    content: str
    time_mark: float
    model_config = ConfigDict(from_attributes=True)

class EpochOut(BaseModel):
    id: int
    name: str
    start_norm: float
    end_norm: float
    description: str | None = None
    model_config = ConfigDict(from_attributes=True)

class EpochDetailOut(EpochOut):
    annotations: list[AnnotationOut] = []