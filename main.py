from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.user import router as user_router
from app.routes import router as routes_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(user_router, prefix="/users")
app.include_router(routes_router, prefix="/routes")

@app.get("/")
def root():
    return {"message": "Welcome to SendaDigital's API!"}
