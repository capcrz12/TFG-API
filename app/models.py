from pydantic import BaseModel

class Route(BaseModel):
    id: int
    user: int
    name: str
    ubication: str
    description: str
    estimated_time: float
    km: float
    speed: float
    min_alt: float
    max_alt: float
    neg_desnivel: float
    pos_desnivel: float
    lat: float
    lon: float

class RouteId(BaseModel):
    id: int

class User(BaseModel):
    id: int
    name: str
    email: str
    password: str

class IdPasswd(BaseModel):
    id: int
    password: str

class IdImage(BaseModel):
    id: int
    image: str