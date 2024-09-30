from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from fastapi.responses import FileResponse
from app.models import Route, RouteId, IdImage
from app.database import get_connection
from datetime import datetime
from app.user import get_current_user, get_total_km, update_total_km, get_users_followed
import shutil
import os
import json
from typing import List

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

@router.get("/get_routes_and_user")
def get_routes_and_user():
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    # Hacemos un JOIN entre Route y Usuario
    query = """
        SELECT Route.*, Usuario.id AS user_id, Usuario.nombre AS user_name, Usuario.email AS user_email
        FROM Route
        JOIN Usuario ON Route.id_usuario = Usuario.id
    """
    
    cursor.execute(query)
    records = cursor.fetchall()

    # Formatear los datos para que el id_usuario sea un objeto con información del usuario
    for record in records:
        record['id_usuario'] = {
            "id": record.pop('user_id'),  # Eliminamos el campo separado de user_id y lo incluimos en id_usuario
            "nombre": record.pop('user_name'),
            "email": record.pop('user_email')
        }

    cursor.close()
    connection.close()

    return records

@router.get("/get_routes_followed/{id}")
def get_routes_followed(id: int):

    authors = get_users_followed(id)
   
    records = []

    for author in authors:
        res = get_routes_by_author(author['id_usuario_seguido'])
        for result in res:
            if result != []:
                records.append(result)

    return records

@router.get("/get_route/{id}")
def get_route(id):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    cursor = connection.cursor(dictionary=True)

    # Hacemos un JOIN entre Route y Usuario
    query = """
        SELECT Route.*, Usuario.id AS user_id, Usuario.nombre AS user_name, Usuario.email AS user_email, Usuario.photo AS user_photo
        FROM Route
        JOIN Usuario ON Route.id_usuario = Usuario.id
        WHERE Route.id = %s
    """
    
    cursor.execute(query, (id,))
    record = cursor.fetchone()
    cursor.close()
    connection.close()

    base_url = "http://localhost:8000"

    # Formatear los datos para que el id_usuario sea un objeto con información del usuario
    id_usuario = record['user_id']
        
    if (record['user_photo'] != None):
        record['id_usuario'] = {
            "id": record.pop('user_id'),  # Eliminamos el campo separado de user_id y lo incluimos en id_usuario
            "nombre": record.pop('user_name'),
            "email": record.pop('user_email'),
            "photo": f"{base_url}/assets/images/users/{id_usuario}/"+record.pop('user_photo')
        }
    else:
        record['id_usuario'] = {
            "id": record.pop('user_id'),  # Eliminamos el campo separado de user_id y lo incluimos en id_usuario
            "nombre": record.pop('user_name'),
            "email": record.pop('user_email'),
            "photo": ''
        }

    return record

@router.get("/get_route_images/{id}")
def get_route_images(id: str):
    # Carpeta donde se almacenan las imágenes en la API
    image_folder_path = f"./assets/images/routes/{id}/"
    
    if not os.path.exists(image_folder_path):
        raise HTTPException(status_code=404, detail="Carpeta de imágenes no encontrada")

    # Obtener imágenes almacenadas en la base de datos (suponiendo JSON en columna 'images')
    connection = get_connection()
    cursor = connection.cursor()
    
    cursor.execute("SELECT filename, lat, lon FROM ImageRoute WHERE route_id = %s", (id,))
    result = cursor.fetchall()

    cursor.close()
    connection.close()

    if not result:
        raise HTTPException(status_code=404, detail="Imágenes no encontradas para esta ruta")

    image_data = []

    # Genera las URLs de las imágenes
    base_url = "http://localhost:8000"
    for record in result:

        filename, lat, lon = record

        image_path = os.path.join(image_folder_path, filename)
        if os.path.exists(image_path):
            image_dict = {
                "filename": f"{base_url}/assets/images/routes/{id}/{filename}",
                "lat": lat,
                "lon": lon
            }
            image_data.append(image_dict)

    return image_data


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

# Devuelve las rutas segun el autor
@router.get("/get_routes_by_author/{id}")
def get_routes_by_author(id: str):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    # Hacemos un JOIN entre Route y Usuario
    query = """
        SELECT Route.*, Usuario.id AS user_id, Usuario.nombre AS user_name, Usuario.email AS user_email, Usuario.photo AS user_photo
        FROM Route
        JOIN Usuario ON Route.id_usuario = Usuario.id
        WHERE Route.id_usuario = %s
    """
    
    cursor.execute(query, (id,))
    records = cursor.fetchall()

    base_url = "http://localhost:8000"

    # Formatear los datos para que el id_usuario sea un objeto con información del usuario
    for record in records:
        id = record['user_id']
        
        if (record['user_photo'] != None):
            record['id_usuario'] = {
                "id": record.pop('user_id'),  # Eliminamos el campo separado de user_id y lo incluimos en id_usuario
                "nombre": record.pop('user_name'),
                "email": record.pop('user_email'),
                "photo": f"{base_url}/assets/images/users/{id}/"+record.pop('user_photo')
            }
        else:
            record['id_usuario'] = {
                "id": record.pop('user_id'),  # Eliminamos el campo separado de user_id y lo incluimos en id_usuario
                "nombre": record.pop('user_name'),
                "email": record.pop('user_email'),
                "photo": ''
            }

    cursor.close()
    connection.close()

    return records

@router.get("/get_gpx/{filename}")
def get_gpx_file(filename: str):
    file_path = os.path.join("assets/gpx", filename)
    if os.path.isfile(file_path):
        return FileResponse(file_path)
    else:
        raise HTTPException(status_code=404, detail="File not found")

@router.post("/update_route")
def update_route(route: Route):
    try: 
        fecha = datetime.now()

        connection = get_connection()
        cursor = connection.cursor()
        query = """
            UPDATE Route SET name = %s, ubication = %s, description = %s, estimated_time = %s, km = %s, 
            speed = %s, min_alt = %s, max_alt = %s, pos_desnivel = %s, neg_desnivel = %s, fecha = %s, lat = %s, lon = %s
            WHERE id = %s
        """        

        values = (route.name, route.ubication, route.description, route.estimated_time, 
                route.km, route.speed, route.min_alt, route.max_alt, route.pos_desnivel, route.neg_desnivel, 
                fecha, route.lat, route.lon, route.id)
        cursor.execute(query, values)
        connection.commit()
        cursor.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating route: {str(e)}")



@router.post("/delete_route")
def delete_route(request: RouteId):
    connection = get_connection()
    cursor = connection.cursor()

    # Recuperar el nombre del fichero .gpx antes de eliminar la ruta
    cursor.execute("SELECT gpx FROM Route WHERE id = %s", (request.id,))
    result = cursor.fetchone()
    
    if not result:
        cursor.close()
        connection.close()
        raise HTTPException(status_code=404, detail="Route not found")
    
    gpx = result[0]

    cursor.execute("DELETE FROM ImageRoute WHERE route_id = %s", (request.id,))
    connection.commit()

    cursor.execute("DELETE FROM Route WHERE id = %s", (request.id,))
    connection.commit()

    cursor.close()
    connection.close()

    delete_images(request.id)
    delete_file(gpx)


def delete_file(gpx: str):
    try:
        # Ruta completa hacia el fichero .gpx en la carpeta 'assets'
        gpx_file_path = os.path.join('assets/gpx', gpx)
        
        # Eliminar el fichero .gpx si existe
        if os.path.exists(gpx_file_path):
            os.remove(gpx_file_path)
        else:
            print(f"El fichero {gpx_file_path} no existe")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al eliminar el fichero gpx: {str(e)}")

@router.post("/delete_route_image")
def delete_route_image (request: IdImage):
    try:
        # Ruta de la carpeta de imágenes que se desea eliminar
        image_folder_path = f"./assets/images/routes/{request.id}/"
        
        # Verificar si la carpeta existe
        if not os.path.exists(image_folder_path):
            raise HTTPException(status_code=404, detail="Carpeta de imágenes no encontrada")
        
        file_path = os.path.join(image_folder_path, request.image)

        # Eliminar el fichero .gpx si existe
        if os.path.exists(file_path):
            os.remove(file_path)
        else:
            print(f"El fichero {file_path} no existe")
        
        return {"message": "Carpeta de imágenes eliminada exitosamente"}
    

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al eliminar la imagen de la ruta: {str(e)}")

def delete_images(id: int):
    try:
        # Ruta de la carpeta de imágenes que se desea eliminar
        image_folder_path = f"./assets/images/routes/{id}/"
        
        # Verificar si la carpeta existe
        if not os.path.exists(image_folder_path):
            raise HTTPException(status_code=404, detail="Carpeta de imágenes no encontrada")
        
        # Eliminar la carpeta y su contenido
        shutil.rmtree(image_folder_path)

        print(image_folder_path)
        
        return {"message": "Carpeta de imágenes eliminada exitosamente"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al eliminar la carpeta de imágenes: {str(e)}")


@router.post("/add_route")
def add_route(route: str = Form(...), gpx: UploadFile = File(...), id_usuario: int = Depends(get_current_user)):
    if not gpx.filename.endswith('.gpx'):
        raise HTTPException(status_code=400, detail="Solo se permiten archivos GPX")

    try:
        fecha = datetime.now()

        # Convertir el string route en un objeto JSON
        import json
        route_data = json.loads(route)  # Convertir el string JSON a un diccionario

        # Verificar si ya existe una ruta con las mismas coordenadas
        connection = get_connection()
        cursor = connection.cursor(buffered=True, dictionary=True)
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


        # Añadir los km al total realizados por el usuario
        total_km = get_total_km(id_usuario)

        km = total_km['total_km'] + route_data['km']

        update_total_km(id_usuario, km)

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

        id = cursor.lastrowid

        cursor.close()

        print("Ruta añadida exitosamente a la base de datos")
        return {"message": "Route added successfully!", "id":id}
    except Exception as e:
        print(f"Error al añadir la ruta: {e}")
        raise HTTPException(status_code=500, detail=str(e))
        


@router.post("/upload_images/{id}")
async def upload_images(id: int, images: List[UploadFile] = File(...), coords: str = Form(...)):
    try:

        coords_data = json.loads(coords)

        # Carpeta donde se almacenan las imágenes
        image_folder_path = f"./assets/images/routes/{id}/"
        if not os.path.exists(image_folder_path):
            os.makedirs(image_folder_path)

        # Guardar los nombres de las imágenes subidas
        image_names = []
        for image in images:
            base_filename, extension = os.path.splitext(image.filename)
            image_filename = image.filename
            image_path = os.path.join(image_folder_path, image_filename)
            
            # Asegurarse de que el nombre del archivo sea único
            counter = 1
            while os.path.exists(image_path):
                image_filename = f"{base_filename}_{counter}{extension}"
                image_path = os.path.join(image_folder_path, image_filename)
                counter += 1

            # Guardar la imagen en el archivo
            with open(image_path, "wb") as image_file:
                shutil.copyfileobj(image.file, image_file)
                
            image_names.append(image_filename)

        # Insertar los nombres de las imágenes en la base de datos
        connection = get_connection()
        cursor = connection.cursor()

        print(image_names)
        
        for i, image_name in enumerate(image_names):
            print(id)

            lat_value = coords_data[i]['lat'] if coords_data[i] else None
            lon_value = coords_data[i]['lon'] if coords_data[i] else None

            print(lat_value)
            print(lon_value)

            cursor.execute(
                "INSERT INTO ImageRoute (route_id, filename, lat, lon) VALUES (%s, %s, %s, %s)",
                (id, image_name, lat_value, lon_value)
            )
        
        connection.commit()
        cursor.close()
        connection.close()

        return {"message": "Images uploaded and database updated successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading images: {str(e)}")