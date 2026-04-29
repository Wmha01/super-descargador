# Usamos una versión ligera de Python
FROM python:3.11-slim

# Creamos nuestra carpeta de trabajo
WORKDIR /app

# Instalamos FFmpeg (vital para unir video y audio en descargas pesadas)
RUN apt-get update && apt-get install -y ffmpeg curl && rm -rf /var/lib/apt/lists/*

# Copiamos primero los requerimientos y los instalamos
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# LA LÍNEA MÁGICA: Copia TODO tu repositorio (incluyendo la carpeta templates)
COPY . .

# Comando para encender el servidor
CMD ["python", "servidor.py"]
