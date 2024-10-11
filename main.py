from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.user import router as user_router
from app.routes import router as routes_router
from app.verify import router as verify_router
from fastapi.staticfiles import StaticFiles
import os

app = FastAPI()

# Monta la carpeta de imágenes para ser servida como estática
app.mount("/assets/images", StaticFiles(directory="./assets/images"), name="images")

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("URL_FRONT")],
    allow_credentials=True,
    allow_methods=["*"],  # Permitir todos los métodos (GET, POST, etc.)
    allow_headers=["*"],  # Permitir todos los headers
)

app.include_router(user_router, prefix="/users")
app.include_router(routes_router, prefix="/routes")
app.include_router(verify_router, prefix="/verify")


@app.get("/")
def root():
    return {"message": "Welcome to SendaDigital's API!"}
