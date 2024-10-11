import mysql.connector
import os

"""
* Función para obtener una conexión a la base de datos
* 
* @return Devuelve una conexión a la base de datos

"""
def get_connection():
    connection = mysql.connector.connect(
        host=os.getenv('HOST'),
        user=os.getenv('USUARIO'),
        passwd=os.getenv('PASSWORD_DB'),
        database=os.getenv('DATABASE')
    )
    return connection
