import os
import requests
import urllib.parse
import re
import tempfile
from flask import Flask, render_template, request, Response, stream_with_context, jsonify
import yt_dlp

# --- FIX DEL ERROR 500 (RUTAS ABSOLUTAS) ---
# Le damos a Flask la ubicación matemática exacta de la carpeta 'templates'
directorio_base = os.path.abspath(os.path.dirname(__file__))
directorio_templates = os.path.join(directorio_base, 'templates')

app = Flask(__name__, template_folder=directorio_templates)

# CONFIGURACIÓN Y LÍMITES
LIMITE_DURACION = 1200  
LIMITE_PESO_MB = 150    

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/procesar', methods=['POST'])
def procesar_enlace():
    url = request.form.get('enlace')
    calidad = request.form.get('calidad')
    
    opciones = {
        'quiet': True,
        'skip_download': True,
        'nocheckcertificate': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    try:
        with yt_dlp.YoutubeDL(opciones) as ydl:
            info = ydl.extract_info(url, download=False)
            if 'entries' in info: info = info['entries'][0]

            duracion = info.get('duration', 0)
            if duracion > LIMITE_DURACION:
                return jsonify({'status': 'error', 'message': 'El video supera los 20 minutos permitidos.'})

            d_url = info.get('url')
            url_minuscula = url.lower()
            
            if not d_url or '.m3u8' in d_url or 'tiktok' in url_minuscula:
                modo = 'servidor'
                url_a_empaquetar = url
            else:
                modo = 'directo'
                final_url = d_url if calidad != 'imagen' else info.get('thumbnail', '')
                url_a_empaquetar = final_url if final_url else url
            
            titulo = info.get('title', 'Video_Descargado')
            miniatura = info.get('thumbnail', '')
            ext = 'jpg' if calidad == 'imagen' else ('mp3' if calidad == 'audio' else 'mp4')
            
            safe_url = urllib.parse.quote(url_a_empaquetar, safe='')
            safe_title = urllib.parse.quote(titulo, safe='')
            
            url_final_pdp = f"/descargar?url={safe_url}&titulo={safe_title}&ext={ext}&modo={modo}"
            
            return jsonify({
                'status': 'success',
                'url_descarga': url_final_pdp,
                'miniatura': miniatura,
                'titulo': titulo
            })

    except Exception as e:
        return jsonify({'status': 'error', 'message': 'Plataforma no soportada o enlace no válido.'})

@app.route('/descargar')
def descargar_archivo():
    video_url = urllib.parse.unquote(request.args.get('url'))
    titulo = re.sub(r'[^\w\s-]', '', request.args.get('titulo', 'descarga')).strip().replace(' ', '_')
    ext = request.args.get('ext', 'mp4')
    modo = request.args.get('modo', 'directo')

    if modo == 'directo':
        r = requests.get(video_url, stream=True, headers={'User-Agent': 'Mozilla/5.0'})
        return Response(stream_with_context(r.iter_content(4096)), headers={
            "Content-Disposition": f'attachment; filename="{titulo}.{ext}"',
            "Content-Type": "application/octet-stream"
        })
    else:
        temp_path = os.path.join(tempfile.gettempdir(), f"{titulo}.{ext}")
        opciones_bajada = {
            'outtmpl': temp_path, 
            'format': 'bestvideo+bestaudio/best', 
            'quiet': True,
            'nocheckcertificate': True
        }
        
        with yt_dlp.YoutubeDL(opciones_bajada) as ydl:
            ydl.download([video_url])
        
        def stream_and_remove():
            if os.path.exists(temp_path):
                with open(temp_path, 'rb') as f:
                    yield from f
                os.remove(temp_path)
            else:
                yield b"Hubo un error con la seguridad de la plataforma."
            
        return Response(stream_with_context(stream_and_remove()), headers={
            "Content-Disposition": f'attachment; filename="{titulo}.{ext}"',
            "Content-Type": "application/octet-stream"
        })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
