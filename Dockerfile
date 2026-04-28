# 1. Usamos una computadora base con Python moderno
FROM python:3.11-slim

# 2. Instalamos FFmpeg y Node.js en el sistema Linux
RUN apt-get update && apt-get install -y ffmpeg nodejs

# 3. Creamos una carpeta de trabajo en el servidor
WORKDIR /app

# 4. Copiamos nuestros archivos a la nube
COPY requirements.txt .
COPY servidor.py .

# 5. Instalamos las librerías de Python
RUN pip install --no-cache-dir -r requirements.txt

# 6. Encendemos el servidor
CMD ["python", "servidor.py"]
