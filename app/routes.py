from fastapi import APIRouter, HTTPException
from app.models import Route
from app.database import get_connection

router = APIRouter()

@router.get("/get_routes")
def get_routes():
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Route")
    records = cursor.fetchall()
    cursor.close()
    connection.close()

    return records

@router.get("/get_route/{id}")
def get_route(id):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Route WHERE id = %s", (id,))
    record = cursor.fetchone()  # Usamos fetchone porque solo esperamos una fila
    cursor.close()
    connection.close()

    return record



@router.post("/add_route")
def add_route(route: Route):
    try:
        connection = get_connection()    
        cursor = connection.cursor()
        query = "INSERT INTO Route (name, ubication, km, speed, min_alt, max_alt, min_des, max_des) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
        values = (route.name, route.ubication, route.km, route.speed, route.min_alt, route.max_alt, route.min_des, route.max_des)
        cursor.execute(query, values)
        connection.commit()
        cursor.close()
        return {"message": "Route added successfully!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
