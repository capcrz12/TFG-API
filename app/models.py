from pydantic import BaseModel

class Route(BaseModel):
    name: str
    ubication: str
    km: float
    speed: float
    min_alt: float
    max_alt: float
    min_des: float
    max_des: float