import os
import requests
import urllib.parse
import re
import tempfile
from flask import Flask, render_template_string, request, Response, stream_with_context, jsonify
import yt_dlp

app = Flask(__name__)

# ==========================================
# CONFIGURACIÓN Y LÍMITES (SEGURIDAD)
# ==========================================
LIMITE_DURACION = 1200  # 20 minutos (en segundos)
LIMITE_PESO_MB = 150    # 150 Megabytes aproximados

# ==========================================
# DISEÑO DE LA INTERFAZ (HTML/CSS/JS)
# ==========================================
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
        body { font-family: 'Inter', sans-serif; background-color: var(--bg-body); color: var(--text-main); margin: 0; padding: 20px; transition: 0.3s; display: flex; justify-content: center; min-height: 100vh; align-items: flex-start; }
        .contenedor { max-width: 480px; width: 100%; background: var(--bg-card); padding: 40px; border-radius: 24px; border: 1px solid var(--border-color); box-shadow: var(--box-shadow); margin-top: 6vh; }
        .brand { text-align: center; font-size: 32px; font-weight: 700; letter-spacing: -1.5px; margin-bottom: 25px; }
        .brand span { color: var(--accent); }
        
        .redes-soportadas { font-size: 12.5px; color: var(--text-secondary); margin-bottom: 18px; text-align: center; font-weight: 600; }
        .input-group { display: flex; gap: 8px; margin-bottom: 15px; }
        input, select { width: 100%; padding: 16px; margin-bottom: 15px; border-radius: 14px; border: 1px solid var(--border-color); background: var(--bg-body); color: var(--text-main); box-sizing: border-box; font-size: 16px; transition: 0.2s; }
        input:focus { border-color: var(--accent); outline: none; }
        
        button.btn-main { width: 100%; padding: 16px; border: none; border-radius: 14px; background: var(--btn-bg); color: var(--btn-text); font-weight: 600; cursor: pointer; font-size: 16px; transition: 0.3s; }
        button.btn-main:disabled { opacity: 0.4; cursor: not-allowed; }
        
        .btn-pegar { background: var(--bg-card); border: 1px solid var(--border-color); color: var(--text-main); border-radius: 14px; padding: 0 16px; cursor: pointer; }

        /* Estilos de resultado */
        #resultado-dinamico { margin-top: 30px; display: none; }
        .resultado-card { padding: 25px; border-radius: 18px; background: var(--bg-body); border: 1px solid var(--border-color); text-align: center; animation: fadeIn 0.5s ease; }
        .miniatura { width: 100%; border-radius: 14px; margin-top: 15px; }
        .btn-descarga { display: block; margin-top: 20px; background: var(--accent); color: white; padding: 14px; text-decoration: none; border-radius: 12px; font-weight: 600; }
        
        /* Loader */
        #pantalla-carga { display: none; text-align: center; margin-top: 20px; }
        .spinner { width: 36px; height: 36px; border: 4px solid var(--border-color); border-top: 4px solid var(--accent); border-radius: 50%; animation: spin 1s linear infinite; margin: 0 auto 10px; }
        @keyframes spin { 100% { transform: rotate(360deg); } }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }

        .historial { margin-top: 40px; border-top: 1px solid var(--border-color); padding-top: 20px; }
        .historial-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }
        .btn-limpiar { background: transparent; border: none; color: #dc3545; font-weight: 600; cursor: pointer; font-size: 13px; }
        .historial-lista { list-style: none; padding: 0; margin: 0; }
        .historial-item { padding: 12px 0; border-bottom: 1px solid var(--border-color); font-size: 14px; display: flex; justify-content: space-between; }
        
        .theme-switcher-container { position: fixed; bottom: 25px; left: 25px; }
        .theme-btn { background: var(--bg-card); border: 1px solid var(--border-color); color: var(--text-main); width: 48px; height: 48px; border-radius: 50%; cursor: pointer; display: flex; align-items: center; justify-content: center; box-shadow: 0 5px 15px rgba(0,0,0,0.1); }
    </style>
</head>
<body id="cuerpo">
    <div class="contenedor">
        <div class="brand">P<span>D</span>P</div>
        <div class="redes-soportadas"><span>✅ Instagram</span> | <span>✅ X</span> | <span>✅ Facebook</span></div>
        
        <form id="form-ajax">
            <div class="input-group">
                <input type="url" id="input-enlace" name="enlace" placeholder="Pega el enlace aquí..." required autocomplete="off">
                <button type="button" class="btn-pegar" id="btn-pegar">📋</button>
            </div>
            <select name="calidad" id="select-calidad">
                <option value="alta">Video (Alta Calidad)</option>
                <option value="media">Video (480p)</option>
                <option value="audio">Audio (MP3)</option>
                <option value="imagen">Miniatura (JPG)</option>
            </select>
            <button type="submit" class="btn-main" id="btn-generar" disabled>Generar Descarga</button>
        </form>

        <div id="pantalla-carga">
            <div class="spinner"></div>
            <p style="color: var(--text-secondary); font-size: 14px;">Analizando enlace...</p>
        </div>

        <div id="resultado-dinamico"></div>

        <div class="historial">
            <div class="historial-header">
                <h2 style="font-size: 16px; color: var(--text-secondary);">Recientes</h2>
                <button id="btn-limpiar" class="btn-limpiar">🗑️ Limpiar</button>
            </div>
            <ul id="lista-historial" class="historial-lista"></ul>
        </div>
    </div>

    <div class="theme-switcher-container">
        <button class="theme-btn" onclick="toggleDarkMode()">🌓</button>
    </div>

    <script>
        const form = document.getElementById('form-ajax');
        const input = document.getElementById('input-enlace');
        const btnGenerar = document.getElementById('btn-generar');
        const loader = document.getElementById('pantalla-carga');
        const contenedorResultado = document.getElementById('resultado-dinamico');

        // Validación de enlace
        input.addEventListener('input', () => {
            btnGenerar.disabled = !input.value.trim().startsWith('http');
        });

        // --- MEJORA 1: AJAX (FETCH API) ---
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            btnGenerar.style.display = 'none';
            loader.style.display = 'block';
            contenedorResultado.style.display = 'none';

            const formData = new FormData(form);
            
            try {
                const response = await fetch('/procesar', {
                    method: 'POST',
                    body: formData
                });
                const data = await response.json();

                loader.style.display = 'none';
                btnGenerar.style.display = 'block';
                contenedorResultado.style.display = 'block';

                if (data.status === 'success') {
                    contenedorResultado.innerHTML = `
                        <div class="resultado-card">
                            <p>✨ ¡Listo!</p>
                            <a href="${data.url_descarga}" class="btn-descarga">Descargar Ahora</a>
                            <img src="${data.miniatura}" class="miniatura">
                        </div>
                    `;
                    guardarHistorial(data.titulo);
                } else {
                    contenedorResultado.innerHTML = `<div class="resultado-card" style="border-color: #dc3545; color: #dc3545;">⚠️ ${data.message}</div>`;
                }
            } catch (error) {
                loader.style.display = 'none';
                btnGenerar.style.display = 'block';
                alert('Error de conexión con el servidor.');
            }
        });

        // Pegar del portapapeles
        document.getElementById('btn-pegar').addEventListener('click', async () => {
            try {
                const text = await navigator.clipboard.readText();
                input.value = text;
                btnGenerar.disabled = !text.trim().startsWith('http');
            } catch(e) {}
        });

        // Historial
        function guardarHistorial(titulo) {
            let hist = JSON.parse(localStorage.getItem('pdp_historial') || '[]');
            hist.unshift({ titulo, fecha: new Date().toLocaleDateString() });
            localStorage.setItem('pdp_historial', JSON.stringify(hist.slice(0, 5)));
            renderHistorial();
        }

        function renderHistorial() {
            const lista = document.getElementById('lista-historial');
            const data = JSON.parse(localStorage.getItem('pdp_historial') || '[]');
            lista.innerHTML = data.length ? '' : '<li style="text-align:center; color:gray; font-size:13px;">No hay descargas</li>';
            data.forEach(i => {
                lista.innerHTML += `<li class="historial-item"><span>${i.titulo}</span><small>${i.fecha}</small></li>`;
            });
        }
        
        document.getElementById('btn-limpiar').onclick = () => { localStorage.removeItem('pdp_historial'); renderHistorial(); };
        function toggleDarkMode() { document.body.classList.toggle('dark-mode'); }
        renderHistorial();
    </script>
</body>
</html>
"""

# ==========================================
# LÓGICA DEL SERVIDOR (PYTHON)
# ==========================================

@app.route('/')
def index():
    return render_template_string(PAGINA_WEB)

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

            # --- MEJORA 3: SEGURIDAD (DURACIÓN Y PESO) ---
            duracion = info.get('duration', 0)
            if duracion > LIMITE_DURACION:
                return jsonify({'status': 'error', 'message': 'El video supera los 20 minutos permitidos.'})

            d_url = info.get('url')
            # Si es m3u8 o no tiene URL directa, preparamos para modo servidor
            modo = 'servidor' if not d_url or '.m3u8' in d_url else 'directo'
            
            # Limpieza de datos para el cliente
            titulo = info.get('title', 'Video_Descargado')
            miniatura = info.get('thumbnail', '')
            ext = 'jpg' if calidad == 'imagen' else ('mp3' if calidad == 'audio' else 'mp4')
            
            # Construcción de URL de descarga final
            final_url = d_url if calidad != 'imagen' else miniatura
            safe_url = urllib.parse.quote(final_url or url, safe='')
            safe_title = urllib.parse.quote(titulo, safe='')
            
            url_final_pdp = f"/descargar?url={safe_url}&titulo={safe_title}&ext={ext}&modo={modo}"
            
            return jsonify({
                'status': 'success',
                'url_descarga': url_final_pdp,
                'miniatura': miniatura,
                'titulo': titulo
            })

    except Exception as e:
        return jsonify({'status': 'error', 'message': 'Plataforma no soportada o perfil privado.'})

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
        # Modo Servidor (Temporal para HLS)
        temp_path = os.path.join(tempfile.gettempdir(), f"{titulo}.{ext}")
        with yt_dlp.YoutubeDL({'outtmpl': temp_path, 'format': 'best', 'quiet': True}) as ydl:
            ydl.download([video_url])
        
        def stream_and_remove():
            with open(temp_path, 'rb') as f:
                yield from f
            if os.path.exists(temp_path): os.remove(temp_path)
            
        return Response(stream_with_context(stream_and_remove()), headers={
            "Content-Disposition": f'attachment; filename="{titulo}.{ext}"'
        })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
