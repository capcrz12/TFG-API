from fastapi import APIRouter, HTTPException, status
import smtplib
from jose import JWTError, jwt
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from app.database import get_connection
import os
from dotenv import load_dotenv
from fastapi.responses import RedirectResponse

load_dotenv()

router = APIRouter()

secret_key = os.getenv('SECRET_KEY')
algorithm = os.getenv('ALGORITHM')
password = os.getenv('PASSWORD')

def send_verification_email(email: str, token: str):
    sender_email = 'SendaDigitalTFG@gmail.com'
    sender_password = password
    receiver_email = email

    # Configura el servidor SMTP
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(sender_email, sender_password)

    # Crea el mensaje
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = "Verificación de cuenta"
    body = f"""
    <html>
        <body style="color: #000000">
            <p>Hola,</p>
            <p>Gracias por registrarse. Por favor, haga clic en el botón de abajo para verificar su correo electrónico. Le redigirá a la página de inicio de sesión</p>
            <p>
                <a href="${os.getenv('URL')}/verify/verify/{token}" style=" <a
                    display: inline-block;
                    padding: 10px 20px;
                    font-size: 16px;
                    color: #ffffff;
                    background-color: #4CAF50;
                    text-align: center;
                    text-decoration: none;
                    border-radius: 5px;
                ">Verificar mi correo</a>
            </p>

            <p>Saludos,<br>El equipo de SendaDigital</p>
        </body>
    </html>
    """
    msg.attach(MIMEText(body, 'html'))

    # Envía el correo
    server.send_message(msg)
    server.quit()

def register_verified_user(email: str):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("INSERT INTO Usuario (nombre, email, password, terms_accepted, total_km) SELECT nombre, email, password, terms_accepted, total_km FROM UsuarioTemp WHERE email=%s", (email,))
    cursor.execute("DELETE FROM UsuarioTemp WHERE email=%s", (email,))
    connection.commit()
    connection.close()

@router.get("/verify/{token}")
async def verify_user(token: str):
    try:
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
        email = payload.get("email")
        
        if email is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token inválido")
        
        # Registrar al usuario en la base de datos
        register_verified_user(email)

        # Redirige al usuario a la página de acceso
        return RedirectResponse(url=f"{os.getenv('URL_FRONT')}/acceso", status_code=302)

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token expirado")
    except jwt.JWTError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token inválido")
