import os
import yt_dlp
import requests
from flask import Flask, render_template_string, request, Response, stream_with_context

app = Flask(__name__)

# --- DISEÑO "PRO" CON MODO OSCURO E HISTORIAL ---
PAGINA_WEB = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Súper Descargador Pro</title>
    <style>
        :root {
            --bg: #ffffff; --text: #111; --box: #f8f9fa; --border: #e5e5e5; --accent: #007bff;
        }
        body.dark-mode {
            --bg: #121212; --text: #e0e0e0; --box: #1e1e1e; --border: #333; --accent: #375a7f;
        }
        body { font-family: 'Inter', system-ui, sans-serif; background-color: var(--bg); color: var(--text); margin: 0; padding: 20px; transition: 0.3s; }
        .contenedor { max-width: 500px; margin: 40px auto; background: var(--box); padding: 30px; border-radius: 20px; border: 1px solid var(--border); box-shadow: 0 10px 30px rgba(0,0,0,0.1); }
        h1 { text-align: center; font-size: 28px; margin-bottom: 20px; letter-spacing: -1px; }
        
        .dark-mode-toggle { position: fixed; top: 20px; right: 20px; cursor: pointer; padding: 10px; border-radius: 50%; background: var(--box); border: 1px solid var(--border); font-size: 20px; }
        
        input, select { width: 100%; padding: 14px; margin-bottom: 12px; border-radius: 12px; border: 1px solid var(--border); background: var(--bg); color: var(--text); box-sizing: border-box; font-size: 16px; }
        button { width: 100%; padding: 15px; border: none; border-radius: 12px; background: #000; color: #fff; font-weight: bold; cursor: pointer; font-size: 16px; transition: 0.2s; }
        body.dark-mode button { background: #fff; color: #000; }
        
        .resultado { margin-top: 25px; padding: 20px; border-radius: 15px; background: var(--bg); border: 1px solid var(--border); text-align: center; }
        .miniatura { width: 100%; border-radius: 12px; margin-top: 15px; }
        .btn-descarga { display: block; margin-top: 15px; background: #28a745; color: white; padding: 12px; text-decoration: none; border-radius: 10px; font-weight: bold; }
        
        .historial { margin-top: 40px; }
        .historial h2 { font-size: 18px; border-bottom: 1px solid var(--border); padding-bottom: 10px; }
        .historial-lista { list-style: none; padding: 0; }
        .historial-item { padding: 10px; border-bottom: 1px solid var(--border); font-size: 14px; display: flex; justify-content: space-between; }
        .historial-item a { color: var(--accent); text-decoration: none; }
    </style>
</head>
<body id="cuerpo">
    <button class="dark-mode-toggle" onclick="toggleDarkMode()">🌓</button>
    
    <div class="contenedor">
        <h1>Súper Descargador <span style="color: #28a745;">Pro</span></h1>
        
        <form method="POST">
            <input type="url" name="enlace" placeholder="Pega el enlace aquí..." required>
            <select name="calidad">
                <option value="alta">Alta Calidad (1080p/720p)</option>
                <option value="media">Calidad Media (480p)</option>
                <option value="baja">Calidad Baja (360p)</option>
                <option value="audio">Solo Audio (MP3)</option>
                <option value="imagen">Solo Miniatura (JPG)</option>
            </select>
            <button type="submit">Generar Descarga</button>
        </form>

        {% if mensaje %}
            <div class="resultado">
                {{ mensaje | safe }}
                {% if mini %}<img src="{{ mini }}" class="miniatura">{% endif %}
                <script>
                    // Guardar en historial de JS
                    let hist = JSON.parse(localStorage.getItem('descargas') || '[]');
                    hist.unshift({titulo: "{{ tit }}", fecha: new Date().toLocaleDateString()});
                    localStorage.setItem('descargas', JSON.stringify(hist.slice(0, 5)));
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
            document.getElementById('cuerpo').classList.toggle('dark-mode');
            localStorage.setItem('dark', document.getElementById('cuerpo').classList.contains('dark-mode'));
        }
        if(localStorage.getItem('dark') === 'true') toggleDarkMode();

        // Cargar historial
        const lista = document.getElementById('lista-historial');
        const datos = JSON.parse(localStorage.getItem('descargas') || '[]');
        datos.forEach(item => {
            lista.innerHTML += `<li class="historial-item"><span>${item.titulo}</span> <small>${item.fecha}</small></li>`;
        });
    </script>
</body>
</html>
"""

@app.route('/', methods=['GET', 'POST'])
def inicio():
    res, mini, tit = None, None, "Video"
    if request.method == 'POST':
        url = request.form['enlace']
        cal = request.form['calidad']
        
        # Mapeo de calidades
        f_map = {
            'alta': 'best',
            'media': 'best[height<=480]',
            'baja': 'best[height<=360]',
            'audio': 'bestaudio/best'
        }
        
        opciones = {
            'quiet': True, 'skip_download': True,
            'format': f_map.get(cal, 'best'),
            # ESTRATEGIA DEFINITIVA PARA YT EN LA NUBE: Usar cliente iOS/Android
            'extractor_args': {'youtube': {'player_client': ['ios', 'android', 'web']}},
            'user_agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'
        }
        
        try:
            with yt_dlp.YoutubeDL(opciones) as ydl:
                info = ydl.extract_info(url, download=False)
                d_url = info.get('url', None)
                mini = info.get('thumbnail', None)
                tit = info.get('title', 'Video descargado')
                
            if d_url:
                final_url = d_url if cal != 'imagen' else mini
                res = f'✨ ¡Listo! <br> <a href="/tunel?url={final_url}" class="btn-descarga">Descargar Ahora</a>'
            else:
                res = "⚠️ YouTube bloqueó la IP. Prueba con Facebook/X o un video de YT menos popular."
        except:
            res = "⚠️ Error al procesar el enlace."

    return render_template_string(PAGINA_WEB, mensaje=res, mini=mini, tit=tit)

@app.route('/tunel')
def tunel():
    v_url = request.args.get('url')
    # Fingimos ser un navegador para el bypass final
    h = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    r = requests.get(v_url, stream=True, headers=h)
    def s():
        for chunk in r.iter_content(chunk_size=4096): yield chunk
    return Response(stream_with_context(s()), headers={
        "Content-Disposition": "attachment; filename=archivo_pdp.mp4",
        "Content-Type": r.headers.get('Content-Type')
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
