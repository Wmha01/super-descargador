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
        .btn-descarga { display: inline-block; margin-top: 15px; background-color: #28a745; color: white; padding: 12px 20px; text-decoration: none; border-radius: 8px; font-weight: bold; }
        .miniatura { width: 100%; border-radius: 8px; margin-top: 15px; }
    </style>
</head>
<body>
    <div class="contenedor">
        <h1>Súper Descargador</h1>
        <form method="POST">
            <input type="url" name="enlace" placeholder="Pega el enlace aquí..." required>
            <select name="tipo_descarga">
                <option value="video">Video / Audio</option>
                <option value="imagen">Solo Miniatura</option>
            </select>
            <button type="submit">Generar Descarga</button>
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
        
        opciones = {
            'quiet': True,
            'format': 'best',
            'skip_download': True,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        try:
            with yt_dlp.YoutubeDL(opciones) as ydl:
                info = ydl.extract_info(url, download=False)
                d_url = info.get('url', None)
                miniatura = info.get('thumbnail', None)
                
            if d_url:
                # El secreto: Enviamos la URL a nuestra propia ruta /bypass
                mensaje = f'✨ ¡Listo! <br><br> <a href="/bypass?url={d_url}" class="btn-descarga">Descargar Ahora</a>'
            else:
                mensaje = "⚠️ No se encontró un enlace compatible."
        except:
            mensaje = "⚠️ Error al procesar. Prueba con otro link."

    return render_template_string(PAGINA_WEB, mensaje_resultado=mensaje, miniatura_url=miniatura)

@app.route('/bypass')
def bypass():
    video_url = request.args.get('url')
    # Añadimos cabeceras de "identidad falsa" para engañar al servidor del video
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://x.com/'
    }
    
    r = requests.get(video_url, stream=True, headers=headers)
    
    def stream():
        for chunk in r.iter_content(chunk_size=1024):
            yield chunk
            
    return Response(stream_with_context(stream()), 
                    headers={
                        "Content-Disposition": "attachment; filename=descarga.mp4",
                        "Content-Type": r.headers.get('Content-Type')
                    })

if __name__ == '__main__':
    puerto = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=puerto)
