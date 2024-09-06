from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from fastapi.responses import FileResponse
from app.models import Route
from app.database import get_connection
from datetime import datetime
from app.user import get_current_user
import shutil
import os

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

# Devuelve las rutas cuyo nombre o ubicacion contengan la cadena {name}
@router.get("/get_routes/{name}")
def get_route(name: str):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    
    query = """
        SELECT * FROM Route 
        WHERE LOWER(name) LIKE LOWER(%s) 
        OR LOWER(ubication) LIKE LOWER(%s)
    """
    cursor.execute(query, ('%' + name + '%', '%' + name + '%'))
    record = cursor.fetchall()
    
    cursor.close()
    connection.close()

    return record

# Asegúrate de que este endpoint esté definido en el archivo principal de tu API
@router.get("/get_gpx/{filename}")
def get_gpx_file(filename: str):
    file_path = os.path.join("assets/gpx", filename)
    if os.path.isfile(file_path):
        return FileResponse(file_path)
    else:
        raise HTTPException(status_code=404, detail="File not found")


@router.post("/add_route")
def add_route(route: str = Form(...), gpx: UploadFile = File(...), id_usuario: int = Depends(get_current_user)):
    if not gpx.filename.endswith('.gpx'):
        raise HTTPException(status_code=400, detail="Solo se permiten archivos GPX")

    try:
        fecha = datetime.now()

        print(f"Nombre del archivo GPX: {gpx.filename}")

        # Convertir el string route en un objeto JSON
        import json
        route_data = json.loads(route)  # Convertir el string JSON a un diccionario
        print(f"Datos de la ruta: {route_data}")

        # Verificar si ya existe una ruta con las mismas coordenadas
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT * FROM Route
            WHERE ABS(lat - %s) < 0.0001 AND ABS(lon - %s) < 0.0001
        """, (route_data['lat'], route_data['lon']))
        existing_route = cursor.fetchone()
        cursor.close()

        # Ajustar las coordenadas si se encuentra una coincidencia
        if existing_route:
            print("Ruta existente con coordenadas similares encontrada, ajustando las coordenadas...")
            route_data['lat'] += 0.0001  # Ajustar la latitud
            # route_data['lon'] += 0.0001  # También podrías ajustar la longitud si es necesario


        # Directorio donde se guardará el archivo GPX
        directory = "assets/gpx"
        
        # Crear el directorio si no existe
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"Directorio {directory} creado")

        # Generar un nombre único para el archivo GPX
        base_filename, extension = os.path.splitext(gpx.filename)
        new_filename = gpx.filename
        counter = 1
        while os.path.exists(os.path.join(directory, new_filename)):
            new_filename = f"{base_filename}_{counter}{extension}"
            counter += 1

        # Guardar el archivo en una carpeta específica
        file_location = os.path.join(directory, new_filename)
        with open(file_location, "wb") as file_object:
            shutil.copyfileobj(gpx.file, file_object)
            print(f"Archivo guardado en {file_location}")

        connection = get_connection()    
        cursor = connection.cursor()
        query = """
            INSERT INTO Route (gpx, name, ubication, description, estimated_time, km, speed, min_alt, max_alt, pos_desnivel, neg_desnivel, fecha, lat, lon, id_usuario) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        values = (new_filename, route_data['name'], route_data['ubication'], route_data['description'], route_data['estimated_time'], 
                  route_data['km'], route_data['speed'], route_data['min_alt'], route_data['max_alt'], route_data['pos_desnivel'], route_data['neg_desnivel'], 
                  fecha, route_data['lat'], route_data['lon'], id_usuario)
        cursor.execute(query, values)
        connection.commit()
        cursor.close()
        print("Ruta añadida exitosamente a la base de datos")
        return {"message": "Route added successfully!"}
    except Exception as e:
        print(f"Error al añadir la ruta: {e}")
        raise HTTPException(status_code=500, detail=str(e))
        
