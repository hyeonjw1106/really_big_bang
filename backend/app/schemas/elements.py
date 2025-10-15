from pydantic import BaseModel, ConfigDict

class ElementOut(BaseModel):
    id: int
    name: str
    type: str
    description: str | None = None
    charge_range: str | None = None
    mass_gev: float | None = None
    genesis_time: str | None = None

    model_config = ConfigDict(from_attributes=True)