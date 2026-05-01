import os
import requests
import urllib.parse
import re
import tempfile
import time
import json
from flask import Flask, render_template, request, Response, stream_with_context, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import yt_dlp

# CONFIGURACIÓN DE RUTAS
directorio_base = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__, 
            template_folder=os.path.join(directorio_base, 'templates'),
            static_folder=os.path.join(directorio_base, 'static'))

# 🛡️ ESCUDO ANTI-SPAM (Máximo 5 descargas por minuto por persona)
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
)

# Diccionario temporal para guardar el progreso de cada usuario
progreso_usuarios = {}

@app.route('/')
def index():
    return render_template('index.html')

# 📡 CANAL DE COMUNICACIÓN EN TIEMPO REAL (SSE)
@app.route('/progreso')
def progreso():
    def generar():
        while True:
            # Enviamos el estado actual del progreso al navegador
            usuario_ip = get_remote_address()
            p = progreso_usuarios.get(usuario_ip, 0)
            yield f"data: {json.dumps({'porcentaje': p})}\n\n"
            if p >= 100: 
                progreso_usuarios[usuario_ip] = 0
                break
            time.sleep(0.5)
    return Response(generar(), mimetype='text/event-stream')

@app.route('/procesar', methods=['POST'])
@limiter.limit("5 per minute")
def procesar_enlace():
    url = request.form.get('enlace')
    usuario_ip = get_remote_address()
    progreso_usuarios[usuario_ip] = 5 # Empezamos con un 5% de análisis

    def progress_hook(d):
        if d['status'] == 'downloading':
            p = d.get('_percent_str', '0%').replace('%','')
            try:
                progreso_usuarios[usuario_ip] = float(p)
            except: pass

    opciones = {'quiet': True, 'skip_download': True, 'nocheckcertificate': True}

    try:
        with yt_dlp.YoutubeDL(opciones) as ydl:
            info = ydl.extract_info(url, download=False)
            if 'entries' in info: info = info['entries'][0]
            
            titulo = info.get('title', 'Video_SnapDrop')
            url_final = f"/descargar?url={urllib.parse.quote(url, safe='')}&titulo={urllib.parse.quote(titulo, safe='')}"
            
            progreso_usuarios[usuario_ip] = 100 # Finalizado
            return jsonify({
                'status': 'success',
                'url_descarga': url_final,
                'miniatura': info.get('thumbnail', ''),
                'titulo': titulo
            })
    except Exception as e:
        progreso_usuarios[usuario_ip] = 0
        return jsonify({'status': 'error', 'message': 'No se pudo procesar el enlace.'})

@app.route('/descargar')
def descargar_archivo():
    video_url = urllib.parse.unquote(request.args.get('url'))
    titulo = re.sub(r'[^\w\s-]', '', request.args.get('titulo', 'descarga')).strip().replace(' ', '_')
    
    temp_path = os.path.join(tempfile.gettempdir(), f"{titulo}.mp4")
    
    # Hook de progreso para la descarga real en el servidor
    def hook(d):
        if d['status'] == 'downloading':
            progreso_usuarios[get_remote_address()] = float(d.get('_percent_str', '0%').replace('%',''))

    with yt_dlp.YoutubeDL({'outtmpl': temp_path, 'format': 'best', 'progress_hooks': [hook]}) as ydl:
        ydl.download([video_url])
    
    def stream_and_remove():
        with open(temp_path, 'rb') as f: yield from f
        if os.path.exists(temp_path): os.remove(temp_path)
            
    return Response(stream_with_context(stream_and_remove()), headers={
        "Content-Disposition": f'attachment; filename="{titulo}.mp4"',
        "Content-Type": "application/octet-stream"
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
