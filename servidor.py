import os
import yt_dlp
from flask import Flask, render_template_string, request

app = Flask(__name__)

# Tu diseño de la página (lo mantenemos igual)
PAGINA_WEB = """
<! el código de tu variable PAGINA_WEB aquí... mantén todo el HTML que ya tenías >
"""

@app.route('/', methods=['GET', 'POST'])
def inicio():
    mensaje = ""
    miniatura = None
    titulo = None
    
    if request.method == 'POST':
        url = request.form['enlace']
        tipo = request.form['tipo_descarga']
        
        # Esta configuración extrae el link directo sin guardar el archivo en el servidor
        opciones = {
            'quiet': True,
            'js_runtimes': {'node': {}},
            'format': 'best' if tipo != 'audio' else 'bestaudio/best'
        }
        
        try:
            with yt_dlp.YoutubeDL(opciones) as ydl:
                info = ydl.extract_info(url, download=False)
                download_url = info.get('url', None)
                titulo = info.get('title', 'video')
                miniatura = info.get('thumbnail', None)
                
            if download_url:
                # El truco: Creamos un botón que apunta directamente al link de Google/YouTube
                mensaje = f'✨ ¡Enlace listo! <br><br> <a href="{download_url}" target="_blank" style="background-color: #28a745; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Haga clic aquí para Descargar</a>'
            else:
                mensaje = "⚠️ Error: No se pudo generar el link de descarga."
                
        except Exception as e:
            mensaje = f"⚠️ Error: El video no está disponible o el enlace es inválido."

    return render_template_string(PAGINA_WEB, mensaje_resultado=mensaje, miniatura_url=miniatura, titulo_video=titulo)

if __name__ == '__main__':
    # Configuración obligatoria para que Render funcione
    puerto = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=puerto)
