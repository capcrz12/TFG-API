from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from app.models import User, IdPasswd, IdImage, Follow
from app.database import get_connection
from app.verify import send_verification_email
import os
from fastapi.security import OAuth2PasswordBearer
from dotenv import load_dotenv
from datetime import datetime
from typing import List
import shutil


load_dotenv()

secret_key = os.getenv('SECRET_KEY')
algorithm = os.getenv('ALGORITHM')
token_min = int(os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES'))

router = APIRouter()

# Para gestionar contraseñas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


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

def store_user_temporarily(name: str, email: str, password: str):
    hashed_password = get_password_hash(password)
    terms_accepted = datetime.now()
    total_km = 0

    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("INSERT INTO UsuarioTemp (nombre, email, password, terms_accepted, total_km) VALUES (%s, %s, %s, %s, %s)", (name, email, hashed_password, terms_accepted, total_km))
    connection.commit()
    connection.close()

def create_verification_token(email: str):
    expire = datetime.utcnow() + timedelta(minutes=token_min)
    to_encode = {"email": email, "exp": expire}
    return jwt.encode(to_encode, secret_key, algorithm=algorithm)

@router.post("/check_password")
def check_password(user: IdPasswd):
    userId = get_user_by_id(user.id)

    return verify_password(user.password, userId["password"])
    

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
    store_user_temporarily(user.name, user.email, user.password)
    
    return {"msg": "Se ha enviado un correo de verificación. Por favor, verifica tu cuenta."}

@router.get("/get_user_by_id/{id}")
def get_user_by_id(id: str):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT id, nombre, email, total_km, password, photo FROM Usuario WHERE id = %s", (id,))
    user = cursor.fetchone()
    cursor.close()
    connection.close()

    base_url = "http://localhost:8000"

    if (user['photo'] != None):
        user['photo'] = f"{base_url}/assets/images/users/{id}/{user['photo']}"
    else:
        user['photo'] = ''

    return user

@router.get("/get_current_user")
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


@router.get("/get_followeds/{id}")
def get_followeds(id: int):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    query = """
        SELECT Usuario_Seguimiento.id_usuario_seguido, Usuario.nombre AS user_name, Usuario.email AS user_email, Usuario.photo AS user_photo
        FROM Usuario_Seguimiento
        JOIN Usuario ON Usuario_Seguimiento.id_usuario_seguido = Usuario.id
        WHERE id_usuario_seguidor = %s
    """
    
    cursor.execute(query, (id,))

    records = cursor.fetchall()

    connection.commit()
    cursor.close()

    base_url = "http://localhost:8000"

    for user in records:
        if (user['user_photo'] != None):
            user['user_photo'] = f"{base_url}/assets/images/users/{user['id_usuario_seguido']}/{user['user_photo']}"
        else:
            user['user_photo'] = ''

    return records

@router.get("/get_followers/{id}")
def get_followeds(id: int):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    query = """
        SELECT Usuario_Seguimiento.id_usuario_seguidor, Usuario.nombre AS user_name, Usuario.email AS user_email, Usuario.photo AS user_photo
        FROM Usuario_Seguimiento
        JOIN Usuario ON Usuario_Seguimiento.id_usuario_seguidor = Usuario.id
        WHERE id_usuario_seguido = %s
    """
    
    cursor.execute(query, (id,))

    records = cursor.fetchall()

    connection.commit()
    cursor.close()

    base_url = "http://localhost:8000"

    for user in records:
        if (user['user_photo'] != None):
            user['user_photo'] = f"{base_url}/assets/images/users/{user['id_usuario_seguidor']}/{user['user_photo']}"
        else:
            user['user_photo'] = ''

    return records


@router.post("/follow")
def follow(request: Follow):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("INSERT INTO Usuario_Seguimiento (id_usuario_seguidor, id_usuario_seguido) VALUES (%s, %s)", (request.id_follower,request.id_followed,))

    connection.commit()
    cursor.close()


@router.post("/unfollow")
def unfollow(request: Follow):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("DELETE FROM Usuario_Seguimiento WHERE id_usuario_seguidor = %s AND id_usuario_seguido = %s", (request.id_follower,request.id_followed,))

    connection.commit()
    cursor.close()


@router.post("/update_profile")
def update_profile(user: User):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    if user.password != '':
        hashed_password = get_password_hash(user.password)
        cursor.execute("UPDATE Usuario SET nombre = %s, password = %s WHERE id = %s", (user.name, hashed_password, user.id,))
    else:
        cursor.execute("UPDATE Usuario SET nombre = %s WHERE id = %s", (user.name, user.id,))

    connection.commit()
    cursor.close()

@router.post("/update_profile_photo/{id}")
def update_profile_photo(id: int, image: UploadFile = File(...)):
    try:

        # Eliminamos la foto de perfil antigua de la carpeta assets
        delete_profile_photo(id, image)

        # Añadimos la nueva foto de perfil a la carpeta assets
        add_profile_photo(id, image)

        # Modificamos el nombre del archivo en la base de datos
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("UPDATE Usuario SET photo = %s WHERE id = %s", (image.filename, id,))

        connection.commit()
        cursor.close()

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading image: {str(e)}")    


def delete_profile_photo(id: int, image: UploadFile = File(...)):
    #Carpeta donde se almacenan las imágenes
    image_folder_path = f"./assets/images/users/{id}/"

    # Verificar si la carpeta existe
    if not os.path.exists(image_folder_path):
        raise HTTPException(status_code=404, detail="Carpeta de imágenes no encontrada")

    # Eliminamos todos los archivos de la carpeta
    for archivo in os.listdir(image_folder_path):
        ruta_archivo = os.path.join(image_folder_path, archivo)
        
        # Verificar si es archivo
        if os.path.isfile(ruta_archivo) or os.path.islink(ruta_archivo):
            os.unlink(ruta_archivo)  # Eliminar archivo o enlace simbólico

    
def add_profile_photo(id: int, image: UploadFile = File(...)):
    #Carpeta donde se almacenan las imágenes
    image_folder_path = f"./assets/images/users/{id}/"

    if not os.path.exists(image_folder_path):
        os.makedirs(image_folder_path)

    image_filename = image.filename
    image_path = os.path.join(image_folder_path, image_filename)
        
    # Guardar la imagen en el archivo
    with open(image_path, "wb") as image_file:
        shutil.copyfileobj(image.file, image_file)

def get_total_km(id: int):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT total_km FROM Usuario WHERE id = %s", (id,))
    km = cursor.fetchone()
    cursor.close()
    connection.close()
    return km

def update_total_km(id: int, value: int):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute("UPDATE Usuario SET total_km = %s WHERE id = %s", (value, id,))
    connection.commit()
    cursor.close()

def get_users_followed(id: int):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT id_usuario_seguido FROM Usuario_Seguimiento WHERE id_usuario_seguidor = %s", (id,))
    records = cursor.fetchall()
    cursor.close()
    connection.close()
    return records
