# Usa una imagen base de Python adecuada
FROM python:3.9-slim

# Establece el directorio de trabajo
WORKDIR /app

# Copia y instala las dependencias de Python
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copia el resto de los archivos de la aplicación
COPY . /app

# Expone el puerto (Railway usará su propia variable de puerto)
EXPOSE 8000

# Comando para iniciar la aplicación FastAPI
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
