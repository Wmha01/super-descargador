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

# ==========================================
# 1. CONFIGURACIÓN INICIAL
# ==========================================
directorio_base = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__, 
            template_folder=os.path.join(directorio_base, 'templates'),
            static_folder=os.path.join(directorio_base, 'static'))

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
)

progreso_usuarios = {}
LIMITE_DURACION = 1200  # 20 minutos máximos para no saturar la RAM

@app.route('/')
def index():
    return render_template('index.html')

# ==========================================
# 2. CANAL SSE (BARRA DE PROGRESO)
# ==========================================
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

# ==========================================
# 3. PROCESAMIENTO E INTELIGENCIA
# ==========================================
@app.route('/procesar', methods=['POST'])
@limiter.limit("5 per minute")
def procesar_enlace():
    url = request.form.get('enlace')
    calidad = request.form.get('calidad', 'alta')
    usuario_ip = get_remote_address()
    
    progreso_usuarios[usuario_ip] = 10 
    
    # Selector de calidad dinámico
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
        'noplaylist': True,          # ESCUDO: Evita descargar listas de reproducción enteras
        'playlist_items': '1',       # ESCUDO: Solo procesa el primer ítem si es una galería
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    try:
        with yt_dlp.YoutubeDL(opciones) as ydl:
            info = ydl.extract_info(url, download=False)
            if 'entries' in info: 
                info = info['entries'][0] # Extraemos el video real de la lista

            # DETECCIÓN DE IMAGEN (Evita colapso en galerías de fotos)
            es_imagen = False
            if info.get('duration') is None and info.get('vcodec') == 'none':
                es_imagen = True

            # ESCUDO MATEMÁTICO: Forzamos a 0 si viene vacío o nulo
            duracion = info.get('duration') or 0
            
            if duracion > LIMITE_DURACION:
                progreso_usuarios[usuario_ip] = 100
                return jsonify({'status': 'error', 'message': 'El video supera los 20 minutos permitidos.'})

            # ESCUDO DE DATOS: Valores por defecto si la red social bloquea metadatos
            d_url = info.get('url')
            url_minuscula = url.lower()
            titulo_crudo = info.get('title') or 'SnapDrop_Media'
            miniatura = info.get('thumbnail') or ''
            
            # Limpiador estricto de títulos (Quita emojis, caracteres raros y limita el largo a 50 letras)
            titulo_limpio = re.sub(r'[^\w\s-]', '', titulo_crudo).strip().replace(' ', '_')
            titulo_limpio = titulo_limpio[:50] if titulo_limpio else 'Descarga'

            # DECISIÓN DE RUTAS Y FORMATOS
            if es_imagen or calidad == 'imagen':
                modo = 'directo'
                ext = 'jpg'
                url_a_empaquetar = miniatura or d_url or url
            else:
                ext = 'mp3' if calidad == 'audio' else 'mp4'
                # M3U8 y Tiktok suelen requerir que el servidor procese los fragmentos
                if not d_url or '.m3u8' in d_url or 'tiktok' in url_minuscula:
                    modo = 'servidor'
                    url_a_empaquetar = url
                else:
                    modo = 'directo'
                    url_a_empaquetar = d_url
            
            # Empaquetamos las variables para mandarlas al enlace de descarga
            safe_url = urllib.parse.quote(url_a_empaquetar, safe='')
            safe_title = urllib.parse.quote(titulo_limpio, safe='')
            
            url_final_pdp = f"/descargar?url={safe_url}&titulo={safe_title}&ext={ext}&modo={modo}&calidad={calidad}"
            
            progreso_usuarios[usuario_ip] = 100 
            return jsonify({
                'status': 'success',
                'url_descarga': url_final_pdp,
                'miniatura': miniatura,
                'titulo': titulo_crudo[:60] + "..." # Título legible para el usuario en la tarjeta
            })

    except Exception as e:
        print(f"Error interno (Ignorar si es por privacidad): {e}")
        progreso_usuarios[usuario_ip] = 100
        return jsonify({'status': 'error', 'message': 'Plataforma no soportada, enlace privado o post irreconocible.'})

# ==========================================
# 4. MOTOR DE DESCARGA FINAL
# ==========================================
@app.route('/descargar')
def descargar_archivo():
    video_url = urllib.parse.unquote(request.args.get('url'))
    titulo = request.args.get('titulo', 'descarga')
    ext = request.args.get('ext', 'mp4')
    modo = request.args.get('modo', 'directo')
    calidad = request.args.get('calidad', 'alta')
    usuario_ip = get_remote_address()

    # MODO DIRECTO (Imágenes o videos de servidores amigables como FB/X)
    if modo == 'directo':
        r = requests.get(video_url, stream=True, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        return Response(stream_with_context(r.iter_content(chunk_size=8192)), headers={
            "Content-Disposition": f'attachment; filename="{titulo}.{ext}"',
            "Content-Type": "application/octet-stream"
        })
        
    # MODO SERVIDOR (TikTok, Audio y Redes complejas)
    else:
        temp_path_base = os.path.join(tempfile.gettempdir(), titulo)
        expected_file = f"{temp_path_base}.{ext}"
        
        # Conexión con la barra de progreso
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
            'outtmpl': f"{temp_path_base}.%(ext)s", 
            'format': formato_bajada, 
            'quiet': True,
            'nocheckcertificate': True,
            'progress_hooks': [hook]
        }
        
        # FORZADO DE FFMPEG (Asegura que siempre obtengas el formato correcto)
        if ext == 'mp3':
            opciones_bajada['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
        else:
            opciones_bajada['merge_output_format'] = 'mp4'
            opciones_bajada['postprocessors'] = [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4'
            }]
        
        # Ejecutamos la descarga real
        with yt_dlp.YoutubeDL(opciones_bajada) as ydl:
            ydl.download([video_url])
        
        # Generador de streaming que se autodestruye al terminar
        def stream_and_remove():
            try:
                with open(expected_file, 'rb') as f:
                    yield from f
            finally:
                if os.path.exists(expected_file):
                    os.remove(expected_file)
            
        return Response(stream_with_context(stream_and_remove()), headers={
            "Content-Disposition": f'attachment; filename="{titulo}.{ext}"',
            "Content-Type": "application/octet-stream"
        })

if __name__ == '__main__':
    # Puerto dinámico para Render
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
