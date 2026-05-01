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

# --- CONFIGURACIÓN DE RUTAS ---
directorio_base = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__, 
            template_folder=os.path.join(directorio_base, 'templates'),
            static_folder=os.path.join(directorio_base, 'static'))

# --- ESCUDO ANTI-SPAM ---
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
)

progreso_usuarios = {}
LIMITE_DURACION = 1200  
LIMITE_PESO_MB = 150    

@app.route('/')
def index():
    return render_template('index.html')

# --- CANAL DE PROGRESO (SSE) ---
@app.route('/progreso')
def progreso():
    def generar():
        usuario_ip = get_remote_address()
        while True:
            p = progreso_usuarios.get(usuario_ip, 0)
            yield f"data: {json.dumps({'porcentaje': p})}\n\n"
            if p >= 100: 
                break
            time.sleep(0.5)
    return Response(generar(), mimetype='text/event-stream')

@app.route('/procesar', methods=['POST'])
@limiter.limit("5 per minute")
def procesar_enlace():
    url = request.form.get('enlace')
    calidad = request.form.get('calidad', 'alta')
    usuario_ip = get_remote_address()
    
    progreso_usuarios[usuario_ip] = 10 
    
    # TRADUCTOR DE CALIDADES
    formato_extraccion = 'best'
    if calidad == 'audio':
        formato_extraccion = 'bestaudio/best'
    elif calidad == 'media':
        formato_extraccion = 'bestvideo[height<=720]+bestaudio/best[height<=720]/best'
    elif calidad == 'baja':
        formato_extraccion = 'bestvideo[height<=360]+bestaudio/best[height<=360]/best'

    opciones = {
        'format': formato_extraccion,
        'quiet': True,
        'skip_download': True,
        'nocheckcertificate': True,
        'socket_timeout': 15,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    try:
        with yt_dlp.YoutubeDL(opciones) as ydl:
            info = ydl.extract_info(url, download=False)
            if 'entries' in info: info = info['entries'][0]

            # DETECCIÓN INTELIGENTE DE IMÁGENES
            es_imagen = False
            if info.get('duration') is None and info.get('vcodec') == 'none':
                es_imagen = True

            duracion = info.get('duration', 0)
            if duracion > LIMITE_DURACION:
                progreso_usuarios[usuario_ip] = 100
                return jsonify({'status': 'error', 'message': 'El video supera los 20 minutos permitidos.'})

            d_url = info.get('url')
            url_minuscula = url.lower()
            titulo = info.get('title', 'SnapDrop_Archivo')
            miniatura = info.get('thumbnail', '')
            
            # RUTA DE DECISIÓN: FOTO VS VIDEO
            if es_imagen or calidad == 'imagen':
                modo = 'directo'
                ext = 'jpg'
                url_a_empaquetar = miniatura if miniatura else d_url
            else:
                ext = 'mp3' if calidad == 'audio' else 'mp4'
                if not d_url or '.m3u8' in d_url or 'tiktok' in url_minuscula:
                    modo = 'servidor'
                    url_a_empaquetar = url
                else:
                    modo = 'directo'
                    url_a_empaquetar = d_url
            
            safe_url = urllib.parse.quote(url_a_empaquetar, safe='')
            safe_title = urllib.parse.quote(titulo, safe='')
            
            url_final_pdp = f"/descargar?url={safe_url}&titulo={safe_title}&ext={ext}&modo={modo}&calidad={calidad}"
            
            progreso_usuarios[usuario_ip] = 100 
            return jsonify({
                'status': 'success',
                'url_descarga': url_final_pdp,
                'miniatura': miniatura,
                'titulo': titulo
            })

    except Exception as e:
        progreso_usuarios[usuario_ip] = 100
        return jsonify({'status': 'error', 'message': 'Plataforma no soportada, enlace privado o post irreconocible.'})

@app.route('/descargar')
def descargar_archivo():
    video_url = urllib.parse.unquote(request.args.get('url'))
    titulo = re.sub(r'[^\w\s-]', '', request.args.get('titulo', 'descarga')).strip().replace(' ', '_')
    ext = request.args.get('ext', 'mp4')
    modo = request.args.get('modo', 'directo')
    calidad = request.args.get('calidad', 'alta')
    usuario_ip = get_remote_address()

    if modo == 'directo':
        r = requests.get(video_url, stream=True, headers={'User-Agent': 'Mozilla/5.0'})
        return Response(stream_with_context(r.iter_content(4096)), headers={
            "Content-Disposition": f'attachment; filename="{titulo}.{ext}"',
            "Content-Type": "application/octet-stream"
        })
    else:
        temp_path = os.path.join(tempfile.gettempdir(), f"{titulo}.{ext}")
        
        def hook(d):
            if d['status'] == 'downloading':
                p = d.get('_percent_str', '0%').replace('%','')
                try: progreso_usuarios[usuario_ip] = float(p)
                except: pass

        formato_bajada = 'bestvideo+bestaudio/best'
        if calidad == 'audio':
            formato_bajada = 'bestaudio/best'
        elif calidad == 'media':
            formato_bajada = 'bestvideo[height<=720]+bestaudio/best[height<=720]/best'
        elif calidad == 'baja':
            formato_bajada = 'bestvideo[height<=360]+bestaudio/best[height<=360]/best'

        opciones_bajada = {
            'outtmpl': temp_path, 
            'format': formato_bajada, 
            'quiet': True,
            'nocheckcertificate': True,
            'progress_hooks': [hook]
        }
        
        # Conversión de audio estricta usando FFmpeg
        if calidad == 'audio':
            opciones_bajada['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
        
        with yt_dlp.YoutubeDL(opciones_bajada) as ydl:
            ydl.download([video_url])
        
        def stream_and_remove():
            try:
                with open(temp_path, 'rb') as f:
                    yield from f
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            
        return Response(stream_with_context(stream_and_remove()), headers={
            "Content-Disposition": f'attachment; filename="{titulo}.{ext}"',
            "Content-Type": "application/octet-stream"
        })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
