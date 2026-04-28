from flask import Flask, request, render_template_string
import yt_dlp

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
        input, select { width: 100%; box-sizing: border-box; padding: 14px; margin-bottom: 16px; font-size: 15px; border: 1px solid #e5e5e5; border-radius: 10px; background-color: #fcfcfc; transition: all 0.3s ease; }
        input:focus, select:focus { outline: none; border-color: #bbb; background-color: #fff; }
        button { width: 100%; padding: 14px; font-size: 16px; font-weight: 600; border-radius: 10px; border: none; background-color: #111; color: white; cursor: pointer; transition: transform 0.1s, background-color 0.3s; }
        button:hover { background-color: #333; }
        button:active { transform: scale(0.98); }
        .mensaje { margin-top: 24px; padding: 16px; border-radius: 10px; font-size: 14px; font-weight: 500; background-color: #f8f9fa; border: 1px solid #eee; }
        
        /* --- NUEVOS ESTILOS PARA LA MINIATURA --- */
        .miniatura { width: 100%; border-radius: 8px; margin-top: 15px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .titulo-video { font-weight: 600; margin-top: 10px; font-size: 15px; color: #111; }
    </style>
    
    <script>
        function iniciarDescarga() {
            var boton = document.getElementById('btn-descargar');
            boton.innerHTML = 'Procesando...';
            boton.style.backgroundColor = '#999';
            boton.style.pointerEvents = 'none';
        }
    </script>
</head>
<body>
    <div class="contenedor">
        <h1>Súper Descargador</h1>
        
        <form method="POST" onsubmit="iniciarDescarga()">
            <input type="url" name="enlace" placeholder="Pega el enlace aquí..." required>
            <select name="tipo_descarga">
                <option value="video">Video (Alta Calidad)</option>
                <option value="ligero">Video (Ligero)</option>
                <option value="audio">Audio (MP3)</option>
                <option value="imagen">Solo Imagen</option>
            </select>
            <button type="submit" id="btn-descargar">Descargar</button>
        </form>

        {% if mensaje_resultado %}
            <div class="mensaje">
                {{ mensaje_resultado }}
                
                {% if titulo_video %}
                    <div class="titulo-video">{{ titulo_video }}</div>
                {% endif %}
                
                {% if miniatura_url %}
                    <img src="{{ miniatura_url }}" alt="Miniatura del video" class="miniatura">
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
    # Preparamos las variables vacías por defecto
    miniatura = None
    titulo = None
    
    if request.method == 'POST':
        url = request.form['enlace']
        tipo = request.form['tipo_descarga']
        
        opciones = {
            'outtmpl': '%(title)s.%(ext)s', 
            'quiet': True,
            'js_runtimes': {'node': {}} 
        }
        
        if tipo == 'audio':
            opciones['format'] = 'bestaudio/best'
            opciones['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
        elif tipo == 'ligero':
            opciones['format'] = 'best[height<=480]'
        elif tipo == 'imagen':
            opciones['writethumbnail'] = True
            opciones['skip_download'] = True
        else:
            opciones['format'] = 'best'
            
        try:
            # 1. Usamos extract_info con download=True para descargar y extraer datos a la vez
            with yt_dlp.YoutubeDL(opciones) as ydl:
                info = ydl.extract_info(url, download=True)
                
                # 2. Rescatamos el título y la portada del diccionario que nos devuelve
                miniatura = info.get('thumbnail', None)
                titulo = info.get('title', 'Video desconocido')
                
            mensaje = "✨ ¡Descarga completada con éxito!"
        except Exception as e:
            mensaje = f"⚠️ Error: No se pudo procesar el enlace."

    # 3. Enviamos los datos a la página web
    return render_template_string(PAGINA_WEB, mensaje_resultado=mensaje, miniatura_url=miniatura, titulo_video=titulo)

if __name__ == '__main__':
    app.run(debug=True, port=5000)