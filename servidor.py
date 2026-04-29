import os
import yt_dlp
import requests
from flask import Flask, render_template_string, request, Response, stream_with_context

app = Flask(__name__)

PAGINA_WEB = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Súper Descargador</title>
    <style>
        body { font-family: system-ui, -apple-system, sans-serif; background-color: #fafafa; color: #222; margin: 0; padding: 20px; display: flex; justify-content: center; }
        .contenedor { background: white; max-width: 400px; width: 100%; padding: 40px 30px; border-radius: 16px; box-shadow: 0 4px 24px rgba(0,0,0,0.04); text-align: center; margin-top: 8vh; }
        h1 { font-size: 24px; margin-bottom: 25px; font-weight: 600; letter-spacing: -0.5px; }
        input, select { width: 100%; box-sizing: border-box; padding: 14px; margin-bottom: 16px; font-size: 15px; border: 1px solid #e5e5e5; border-radius: 10px; background-color: #fcfcfc; }
        button { width: 100%; padding: 14px; font-size: 16px; font-weight: 600; border-radius: 10px; border: none; background-color: #111; color: white; cursor: pointer; }
        .mensaje { margin-top: 24px; padding: 16px; border-radius: 10px; font-size: 14px; background-color: #f8f9fa; border: 1px solid #eee; }
        .miniatura { width: 100%; border-radius: 8px; margin-top: 15px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .btn-descarga { display: inline-block; margin-top: 15px; background-color: #28a745; color: white; padding: 12px 20px; text-decoration: none; border-radius: 8px; font-weight: bold; }
    </style>
</head>
<body>
    <div class="contenedor">
        <h1>Súper Descargador</h1>
        <form method="POST">
            <input type="url" name="enlace" placeholder="Pega el enlace aquí..." required>
            <select name="tipo_descarga">
                <option value="video">Video (Alta Calidad)</option>
                <option value="audio">Audio (MP3)</option>
                <option value="imagen">Solo Miniatura</option>
            </select>
            <button type="submit">Generar Enlace</button>
        </form>

        {% if mensaje_resultado %}
            <div class="mensaje">
                {{ mensaje_resultado | safe }}
                {% if miniatura_url %}
                    <img src="{{ miniatura_url }}" class="miniatura">
                {% endif %}
            </div>
        {% endif %}
    </div>
</body>
</html>
"""

@app.route('/', methods=['GET', 'POST'])
def inicio():
    mensaje = ""
    miniatura = None
    if request.method == 'POST':
        url = request.form['enlace']
        tipo = request.form['tipo_descarga']
        formato = 'best' if tipo != 'audio' else 'bestaudio/best'
        
        opciones = {
            'quiet': True,
            'format': formato,
            'skip_download': True,
            'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
        }
        
        try:
            with yt_dlp.YoutubeDL(opciones) as ydl:
                info = ydl.extract_info(url, download=False)
                d_url = info.get('url', None)
                miniatura = info.get('thumbnail', None)
                
            if d_url:
                # Ahora el botón apunta a NUESTRA propia ruta de descarga
                mensaje = f'✨ ¡Listo! <br><br> <a href="/descargar?url={d_url}" class="btn-descarga">Descargar Ahora</a>'
            else:
                mensaje = "⚠️ No se pudo obtener el video."
        except:
            mensaje = "⚠️ Error de conexión o enlace inválido."

    return render_template_string(PAGINA_WEB, mensaje_resultado=mensaje, miniatura_url=miniatura)

# --- ESTA ES LA FUNCIÓN "TÚNEL" ---
@app.route('/descargar')
def descargar():
    video_url = request.args.get('url')
    req = requests.get(video_url, stream=True)
    
    # Creamos una respuesta que va pasando los datos pedacito a pedacito
    def generar():
        for chunk in req.iter_content(chunk_size=1024):
            yield chunk
            
    return Response(stream_with_context(generar()), 
                    headers={"Content-Disposition": "attachment; filename=archivo_descargado.mp4",
                             "Content-Type": req.headers.get('Content-Type')})

if __name__ == '__main__':
    puerto = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=puerto)
