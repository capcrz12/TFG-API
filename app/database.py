import mysql.connector
import os
from fastapi import HTTPException


"""
* Función para obtener una conexión a la base de datos
* 
* @return Devuelve una conexión a la base de datos

"""
def get_connection():
    try:
        connection = mysql.connector.connect(
            host=os.getenv('HOST'),
            user=os.getenv('USUARIO'),
            passwd=os.getenv('PASSWORD_DB'),
            database=os.getenv('DATABASE'),
            port=os.getenv('PORT')
        )
        return connection
    except mysql.connector.Error as err:
        raise HTTPException(status_code=500, detail=f"Error al conectar a la base de datos: {err}")