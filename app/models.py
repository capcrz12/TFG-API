from pydantic import BaseModel

class Route(BaseModel):
    name: str
    ubication: str
    description: str
    estimated_time: float
    km: float
    speed: float
    min_alt: float
    max_alt: float
    min_des: float
    max_des: float
    lat: float
    lon: float

class User(BaseModel):
    name: str
    email: str
    password: str