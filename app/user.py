from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from app.models import User
from app.database import get_connection
from app.verify import send_verification_email
import os
from fastapi.security import OAuth2PasswordBearer
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

secret_key = os.getenv('SECRET_KEY')
algorithm = os.getenv('ALGORITHM')
token_min = int(os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES'))

router = APIRouter()

# Para gestionar contraseñas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def authenticate_user(email: str, password: str):
    user = get_user_by_email(email)
    if not user:
        return False
    if not verify_password(password, user["password"]):
        return False
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=algorithm)
    return encoded_jwt

@router.post("/login")
async def login(user: User):
    user_dict = authenticate_user(user.email, user.password)
    if not user_dict:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=token_min)
    access_token = create_access_token(
        data={"sub": user_dict['email'], "id": user_dict['id']}, 
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

def get_user_by_email(email: str):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT id, email, password FROM Usuario WHERE email = %s", (email,))
    user = cursor.fetchone()
    cursor.close()
    connection.close()
    return user

def create_user(email: str, hashed_password: str):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("INSERT INTO Usuario (email, password) VALUES (%s, %s)", (email, hashed_password))
    connection.commit()
    cursor.close()
    connection.close()

def store_user_temporarily(email: str, password: str):
    hashed_password = get_password_hash(password)
    terms_accepted = datetime.now()

    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("INSERT INTO UsuarioTemp (email, password, terms_accepted) VALUES (%s, %s, %s)", (email, hashed_password, terms_accepted))
    connection.commit()
    connection.close()

def create_verification_token(email: str):
    expire = datetime.utcnow() + timedelta(minutes=token_min)
    to_encode = {"email": email, "exp": expire}
    return jwt.encode(to_encode, secret_key, algorithm=algorithm)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
        user_id: str = payload.get("id")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    return user_id

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_user(user: User):
    # Verificar si el usuario ya existe
    if get_user_by_email(user.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario ya está registrado."
        )

    # Generar token de verificación
    token = create_verification_token(user.email)
    send_verification_email(user.email, token)
    
    # Guardar temporalmente el usuario en la base de datos
    store_user_temporarily(user.email, user.password)
    
    return {"msg": "Se ha enviado un correo de verificación. Por favor, verifica tu cuenta."}