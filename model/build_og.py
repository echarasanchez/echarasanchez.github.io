"""Imagen para la previsualización en redes y mensajería (Open Graph): out/og.png, 1200x630.

WhatsApp, Telegram, X o Facebook no muestran SVG, así que se dibuja el logo en una página HTML y se fotografía con
Chromium sin interfaz (chromium-headless-shell). Solo el logo: el título y la descripción ya los pone la propia
previsualización. Centrado, para que siga entero si la app recorta un cuadrado del centro. Repetirlo si cambia el logo.
"""
import os, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(__file__))
import web

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'out', 'og.png')
logo = web.LOGO.replace('id="lgc"', 'id="lgo"').replace('url(#lgc)', 'url(#lgo)')

html = f"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<style>
html,body{{margin:0;width:1200px;height:630px;overflow:hidden}}
body{{background:#f6f7f9;display:flex;align-items:center;justify-content:center}}
.logo{{width:540px;height:540px}}
.logo .lg-bg{{fill:#e6eef8}} .logo .lg-face{{fill:#14202e}} .logo .lg-pin{{fill:#c23b3b}}
.logo .lg-wire{{stroke:#14202e}} .logo .lg-coil{{fill:#e6eef8;stroke:#14202e}}
</style></head><body>
{logo}
</body></html>"""

with tempfile.NamedTemporaryFile('w', suffix='.html', delete=False, encoding='utf-8') as f:
    f.write(html)
try:
    subprocess.run(['chromium-headless-shell', '--no-sandbox', '--hide-scrollbars', '--virtual-time-budget=8000',
                    '--window-size=1200,630', f'--screenshot={os.path.abspath(OUT)}', 'file://' + f.name],
                   check=True, capture_output=True)
finally:
    os.unlink(f.name)
print('og ok |', OUT)
