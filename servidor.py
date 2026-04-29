import os
import requests
import urllib.parse
import re
from flask import Flask, render_template_string, request, Response, stream_with_context
import yt_dlp

app = Flask(__name__)

PAGINA_WEB = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PDP - Descarga Pro</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-body: #f4f7f6; --bg-card: #ffffff; --text-main: #1a1a1a; --text-secondary: #6c757d; 
            --border-color: #e9ecef; --accent: #28a745; --btn-bg: #1a1a1a; --btn-text: #ffffff; 
            --box-shadow: 0 10px 30px rgba(0,0,0,0.05);
        }
        body.dark-mode {
            --bg-body: #121212; --bg-card: #1e1e1e; --text-main: #e0e0e0; --text-secondary: #a0a0a0; 
            --border-color: #333333; --btn-bg: #f8f9fa; --btn-text: #1a1a1a; --box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        body { font-family: 'Inter', system-ui, sans-serif; background-color: var(--bg-body); color: var(--text-main); margin: 0; padding: 20px; transition: 0.3s; display: flex; justify-content: center; min-height: 100vh; align-items: flex-start; }
        .contenedor { max-width: 480px; width: 100%; background: var(--bg-card); padding: 40px; border-radius: 24px; border: 1px solid var(--border-color); box-shadow: var(--box-shadow); margin-top: 6vh; position: relative; }
        .brand { text-align: center; font-size: 32px; font-weight: 700; letter-spacing: -1.5px; margin-bottom: 25px; }
        .brand span { color: var(--accent); }
        
        .redes-soportadas { font-size: 12.5px; color: var(--text-secondary); margin-bottom: 18px; text-align: center; font-weight: 600; }
        .redes-soportadas span { margin: 0 5px; }

        input, select { width: 100%; padding: 16px; margin-bottom: 15px; border-radius: 14px; border: 1px solid var(--border-color); background: var(--bg-body); color: var(--text-main); box-sizing: border-box; font-size: 16px; transition: 0.2s; }
        input:focus, select:focus { border-color: var(--accent); outline: none; }
        button.btn-main { width: 100%; padding: 16px; border: none; border-radius: 14px; background: var(--btn-bg); color: var(--btn-text); font-weight: 600; cursor: pointer; font-size: 16px; transition: 0.2s; }
        button.btn-main:hover { opacity: 0.9; }
        
        .resultado { margin-top: 30px; padding: 25px; border-radius: 18px; background: var(--bg-body); border: 1px solid var(--border-color); text-align: center; }
        .miniatura { width: 100%; border-radius: 14px; margin-top: 15px; box-shadow: 0 5px 15px rgba(0,0,0,0.1); }
        .btn-descarga { display: block; margin-top: 20px; background: var(--accent); color: white; padding: 14px; text-decoration: none; border-radius: 12px; font-weight: 600; font-size: 15px; }
        
        .historial { margin-top: 40px; border-top: 1px solid var(--border-color); padding-top: 20px; }
        .historial h2 { font-size: 18px; font-weight: 600; margin-bottom: 15px; color: var(--text-secondary); }
        .historial-lista { list-style: none; padding: 0; margin: 0; }
        .historial-item { padding: 12px 0; border-bottom: 1px solid var(--border-color); font-size: 14px; display: flex; justify-content: space-between; align-items: center; }
        .historial-item span { font-weight: 500; color: var(--text-main); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 70%; }
        .historial-item small { color: var(--text-secondary); font-size: 12px; }

        .theme-switcher-container { position: fixed; bottom: 25px; left: 25px; z-index: 100; }
        .theme-btn { background: var(--bg-card); border: 1px solid var(--border-color); color: var(--text-main); width: 48px; height: 48px; border-radius: 50%; cursor: pointer; display: flex; align-items: center; justify-content: center; box-shadow: 0 5px 15px rgba(0,0,0,0.1); transition: 0.3s; }
        .theme-btn .sun-icon { display: none; }
        .theme-btn .moon-icon { display: block; }
        body.dark-mode .theme-btn .sun-icon { display: block; }
        body.dark-mode .theme-btn .moon-icon { display: none; }
        .theme-icon { fill: currentColor; width: 22px; height: 22px; }
    </style>
</head>
<body id="cuerpo">
    <div class="theme-switcher-container">
        <button id="theme-btn" class="theme-btn" onclick="toggleDarkMode()">
            <svg class="theme-icon moon-icon" viewBox="0 0 24 24"><path d="M12.3 22h-.1c-3.3 0-6.4-1.3-8.7-3.6C1.2 16.1 0 13 0 9.7 0 6.1 2 2.8 5.2 1.2c.3-.2.6-.1.8.1.3.3.3.6.1.9C5.2 4 4.8 5.3 4.8 6.7c0 3.9 3.2 7.1 7.1 7.1.9 0 1.7-.2 2.5-.5.3-.1.6 0 .8.2.2.3.6.1.8-1.2 1.9-3.4 3-5.7 3H9.7c.3 2.1 2.1 3.7 4.2 3.7 1 0 2-.4 2.8-1.1.2-.2.6-.2.8 0 .3.2.3.6.1.8-1.2 1.1-2.9 1.7-4.6 1.7-.1.1-.1.1-.1.1z"/></svg>
            <svg class="theme-icon sun-icon" viewBox="0 0 24 24"><path d="M12 18c-3.3 0-6-2.7-6-6s2.7-6 6-6 6 2.7 6 6-2.7 6-6 6zm0-10c-2.2 0-4 1.8-4 4s1.8 4 4 4 4-1.8 4-4-1.8-4-4-4zM12 4c.6 0 1-.4 1-1V1c0-.6-.4-1-1-1s-1 .4-1 1v2c0 .6.4 1 1 1zM12 20c-.6 0-1 .4-1 1v2c0 .6.4 1 1 1s1-.4 1-1v2c0-.6-.4-1-1-1zM23 11h-2c-.6 0-1 .4-1 1s.4 1 1 1h2c.6 0 1-.4 1-1s-.4-1-1-1zM4 12c0-.6-.4-1-1-1H1c-.6 0-1 .4-1 1s.4 1 1 1h2c.6 0 1-.4 1-1zM19.8 18.4l-1.4 1.4c-.4.4-.4 1 0 1.4.2.2.5.3.7.3s.5-.1.7-.3l1.4-1.4c.4-.4.4-1 0-1.4s-1-.4-1.4 0zM4.2 5.6l-1.4 1.4c-.4.4-.4 1 0 1.4.2.2.5.3.7.3s.5-.1.7-.3L5.6 7c.4-.4.4-1 0-1.4s-1-.4-1.4 0zM18.4 4.2l1.4 1.4c.4.4.4 1 0 1.4s-1 .4-1.4 0L17 5.6c-.4-.4-.4-1 0-1.4s1-.4 1.4 0zM5.6 17L4.2 18.4c-.4.4-.4 1 0 1.4.2.2.5.3.7.3s.5-.1.7-.3l1.4-1.4c.4-.4.4-1 0-1.4s-1-.4-1.4 0z"/></svg>
        </button>
    </div>
    
    <div class="contenedor">
        <div class="brand">P<span>D</span>P</div>
        
        <div class="redes-soportadas">
            <span>✅ Instagram</span> | <span>✅ X</span> | <span>✅ Facebook</span> | <span>✅ Pinterest</span>
        </div>
        
        <form method="POST">
            <input type="url" name="enlace" placeholder="Pega el enlace del video o imagen..." required>
            <select name="calidad">
                <option value="alta">Video (Alta Calidad)</option>
                <option value="media">Video (Media 480p)</option>
                <option value="baja">Video (Baja 360p)</option>
                <option value="audio">Audio (MP3)</option>
                <option value="imagen">Solo Miniatura (JPG)</option>
            </select>
            <button type="submit" class="btn-main">Generar Descarga</button>
        </form>

        {% if mensaje_resultado %}
            <div class="resultado">
                {{ mensaje_resultado | safe }}
                {% if miniatura_url %}
                    <img src="{{ miniatura_url }}" class="miniatura">
                {% endif %}
                <script>
                    let hist = JSON.parse(localStorage.getItem('pdp_historial') || '[]');
                    const nuevo = { titulo: "{{ titulo_v }}", fecha: new Date().toLocaleDateString() };
                    if(hist.length === 0 || hist[0].titulo !== nuevo.titulo) {
                        hist.unshift(nuevo);
                        localStorage.setItem('pdp_historial', JSON.stringify(hist.slice(0, 5)));
                    }
                </script>
            </div>
        {% endif %}

        <div class="historial">
            <h2>Recientes</h2>
            <ul id="lista-historial" class="historial-lista"></ul>
        </div>
    </div>

    <script>
        function toggleDarkMode() {
            const body = document.getElementById('cuerpo');
            body.classList.toggle('dark-mode');
            localStorage.setItem('pdp_theme', body.classList.contains('dark-mode') ? 'dark' : 'light');
        }
        if(localStorage.getItem('pdp_theme') === 'dark') { document.getElementById('cuerpo').classList.add('dark-mode'); }

        const listaHist = document.getElementById('lista-historial');
        const datosHist = JSON.parse(localStorage.getItem('pdp_historial') || '[]');
        if(datosHist.length === 0) {
            listaHist.innerHTML = '<li class="historial-item" style="color: var(--text-secondary); justify-content: center;">No hay descargas recientes.</li>';
        } else {
            datosHist.forEach(item => {
                listaHist.innerHTML += `<li class="historial-item"><span>${item.titulo}</span> <small>${item.fecha}</small></li>`;
            });
        }
    </script>
</body>
</html>
"""

@app.route('/', methods=['GET', 'POST'])
def inicio():
    mensaje = ""
    miniatura = None
    titulo_v = "Archivo Multimedia"
    info = None
    
    if request.method == 'POST':
        url = request.form['enlace']
        calidad = request.form['calidad']
        
        f_map = {
            'alta': 'best',
            'media': 'best[height<=480]/best',
            'baja': 'best[height<=360]/best',
            'audio': 'bestaudio/best'
        }
        
        opciones_principales = {
            'quiet': True,
            'format': f_map.get(calidad, 'best'),
            'skip_download': True,
            'nocheckcertificate': True,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        try:
            with yt_dlp.YoutubeDL(opciones_principales) as ydl:
                info = ydl.extract_info(url, download=False)
        except Exception as e:
            opciones_supervivencia = {
                'quiet': True,
                'skip_download': True,
                'nocheckcertificate': True,
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            try:
                with yt_dlp.YoutubeDL(opciones_supervivencia) as ydl:
                    info = ydl.extract_info(url, download=False)
            except Exception as e2:
                error_msg = str(e2)
                mensaje = f"⚠️ No se pudo extraer el video. <br><br><small style='color: #dc3545;'>Detalle: {error_msg[:100]}...</small>"
                return render_template_string(PAGINA_WEB, mensaje_resultado=mensaje)

        if info:
            if 'entries' in info and len(info['entries']) > 0:
                info = info['entries'][0]
            
            d_url = info.get('url')
            
            if not d_url and 'formats' in info:
                for formato in reversed(info['formats']):
                    if formato.get('url') and 'manifest' not in formato.get('url'):
                        d_url = formato.get('url')
                        break
                        
            miniatura = info.get('thumbnail')
            titulo_v = info.get('title', 'Video_Descargado')
            
            if d_url:
                final_url = d_url if calidad != 'imagen' else miniatura
                
                # PREPARACIÓN SEGURA PARA EL TÚNEL
                # 1. Empaquetamos la URL para que no se corte con símbolos raros
                safe_url = urllib.parse.quote(final_url, safe='')
                # 2. Empaquetamos el título
                safe_title = urllib.parse.quote(titulo_v, safe='')
                
                # Asignamos la extensión correcta
                ext = 'jpg' if calidad == 'imagen' else ('mp3' if calidad == 'audio' else 'mp4')
                
                mensaje = f'✨ ¡Listo! <br><br> <a href="/descargar?url={safe_url}&titulo={safe_title}&ext={ext}" class="btn-descarga">Descargar Ahora</a>'
            else:
                mensaje = "⚠️ El formato de este post es extraño. Intenta con otro enlace."

    return render_template_string(PAGINA_WEB, mensaje_resultado=mensaje, miniatura_url=miniatura, titulo_v=titulo_v)

@app.route('/descargar')
def proceso_descarga():
    video_url = request.args.get('url')
    titulo_raw = request.args.get('titulo', 'Descarga_PDP')
    ext = request.args.get('ext', 'mp4')
    
    # LIMPIEZA DEL NOMBRE DE ARCHIVO
    # Solo dejamos letras, números y espacios para que el sistema no explote
    titulo_limpio = re.sub(r'[^\w\s-]', '', titulo_raw).strip()
    # Cambiamos espacios por guiones bajos para que se vea profesional
    titulo_limpio = titulo_limpio.replace(' ', '_')
    
    if not titulo_limpio:
        titulo_limpio = "Video_PDP"
        
    nombre_final = f"{titulo_limpio}.{ext}"
    
    h = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    r = requests.get(video_url, stream=True, headers=h)
    
    def stream():
        for chunk in r.iter_content(chunk_size=4096): 
            if chunk:
                yield chunk
                
    return Response(stream_with_context(stream()), headers={
        "Content-Disposition": f'attachment; filename="{nombre_final}"',
        # Aseguramos que se transfiera como un archivo normal
        "Content-Type": r.headers.get('Content-Type', 'application/octet-stream')
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
