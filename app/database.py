import mysql.connector

def get_connection():
    connection = mysql.connector.connect(
        host="localhost",
        user="root",
        passwd="carlosmacael",
        database="sendaDigitalDB"
    )
    return connection
