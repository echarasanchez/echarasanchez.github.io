"""Piezas comunes a las páginas de la web: barra superior con pestañas, logo y esqueleto HTML.

Las pestañas del informe (index.html) son secciones de la misma página que se muestran según el #hash;
"Razones" y "Quiénes somos" son páginas aparte. La barra es la misma en todas.
"""
import base64, hashlib, os, re
from html import escape

HERE = os.path.dirname(__file__)
# Dirección pública: las etiquetas Open Graph (previsualización en WhatsApp, X...) necesitan URLs absolutas
SITE_URL = 'https://echarasanchez.ch'
ELECCION = '2026-11-29'
MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']


def fecha(iso, corta=False):
    """'2026-10-25' -> '25 oct 2026' (corta) o '25 de octubre de 2026'."""
    y, m, d = (int(x) for x in iso.split('-'))
    return f'{d} {MESES[m - 1][:3]} {y}' if corta else f'{d} de {MESES[m - 1]} de {y}'


def cuenta_atras(hoy):
    """Texto de días hasta la elección; la página lo recalcula al abrirse (misma regla en report_template.html)."""
    import datetime as dt
    n = (dt.date.fromisoformat(ELECCION) - hoy).days
    return f'{n} días para el 29-N' if n > 1 else 'Mañana se vota' if n == 1 else 'Hoy se vota' if n == 0 else 'Elecciones del 29-N'

# (id, texto, enlace). Los cinco primeros son pestañas de index.html.
NAV = [
    ('provincia', 'Tu provincia', './#provincia'),
    ('congreso', 'Congreso', './#congreso'),
    ('senado', 'Senado', './#senado'),
    ('metodo', 'Método', './#metodo'),
    ('razones', 'Razones para echar a Sánchez', 'razones.html'),
    ('quienes', 'Quiénes somos', 'quienes.html'),
]
INDEX_TABS = [k for k, _, href in NAV if href.startswith('./#')]
# Del 24 al 29-N (veda de encuestas, art. 69.7 LOREG) index.html es un aviso: sin las pestañas del informe
NAV_RETIRADA = [('aviso', 'Aviso', './')] + [x for x in NAV if x[0] not in INDEX_TABS]

# Logo: perfil con una pinza de tender en la nariz ("votar con la nariz tapada"). Colores del tema vía clases.
LOGO = ('<svg class="logo" viewBox="0 0 64 64" role="img" aria-label="Logo: perfil con una pinza en la nariz">'
        '<clipPath id="lgc"><rect width="64" height="64" rx="14"/></clipPath><rect class="lg-bg" width="64" height="64" rx="14"/>'
        '<g clip-path="url(#lgc)"><path class="lg-face" d="M0 0 H17 C17 8 18 14 16 19 C15 21 15 22 16.5 23.5 C21 30 29 37 34 42 C37 45 35.5 49 31 48.5 C28 48 25.5 49 24 49.5 C25.5 51 26 52.5 25 54 C24 55 22 55.5 22.5 57 C23.5 58.5 25 60 24 64 H0 Z"/></g>'
        '<g transform="translate(33.5 45) rotate(-26) scale(.68) translate(-13 -32)">'
        '<path class="lg-pin" d="M4 31 L4 26 Q4 23.5 7 23.5 L58 25.5 Q61 25.8 61 28.5 L61 31 L16 31 Q13 27.5 10 31 Z"/>'
        '<path class="lg-pin" d="M4 33 L4 38 Q4 40.5 7 40.5 L58 38.5 Q61 38.2 61 35.5 L61 33 L16 33 Q13 36.5 10 33 Z"/>'
        '<path class="lg-wire" d="M33 27.4 H22 M33 36.6 H22" stroke-width="2.2" stroke-linecap="round"/>'
        '<circle class="lg-coil" cx="38" cy="32" r="6" stroke-width="2.8"/></g></svg>')

TOPBAR_CSS = """
/* Barra superior común: logo + pestañas. La pestaña activa lleva aria-current. */
.topbar{position:sticky;top:0;z-index:20;background:var(--bg);border-bottom:1px solid var(--rule)}
.topbar .in{max-width:1180px;margin:0 auto;padding:10px max(16px,env(safe-area-inset-right,0px)) 0 max(16px,env(safe-area-inset-left,0px));display:flex;align-items:center;gap:6px 14px;flex-wrap:wrap}
.home{display:flex;align-items:center;gap:10px;text-decoration:none;color:var(--ink);font-family:var(--display);font-weight:800;font-stretch:88%;font-size:18px;padding-bottom:10px}
.home .logo{width:44px;height:auto}
.vh{position:absolute;width:1px;height:1px;overflow:hidden;clip-path:inset(50%);white-space:nowrap}
.logo .lg-bg{fill:var(--accent-soft)} .logo .lg-face{fill:var(--ink)} .logo .lg-pin{fill:var(--inv)}
.logo .lg-wire{stroke:var(--ink)} .logo .lg-coil{fill:var(--accent-soft);stroke:var(--ink)}
.tabs{display:flex;gap:2px;overflow-x:auto;scrollbar-width:none;flex:1 1 auto;margin:0;padding:0;list-style:none;max-width:none}
.tabs::-webkit-scrollbar{display:none}
.tabs a{display:block;white-space:nowrap;text-decoration:none;color:var(--muted);font-size:15.5px;font-weight:600;padding:8px 10px 12px;border-bottom:3px solid transparent}
.tabs a:hover{color:var(--ink)}
.tabs a[aria-current="page"]{color:var(--ink);border-bottom-color:var(--inv)}
.tabs a:focus-visible{outline:2px solid var(--accent);outline-offset:-2px}
.tabs li.sep{width:1px;background:var(--rule);margin:8px 6px 12px}
.tabs .sh,.tabs li.br{display:none}
/* Móvil: las mismas pestañas en dos filas (logo + provincia, panorama, Congreso, Senado / método, Razones,
   quiénes somos); con scroll lateral las de la derecha no se veían */
@media (max-width:760px){
  .topbar .in{flex-wrap:nowrap;align-items:flex-start;gap:0 4px;padding-top:4px}
  .home{padding:6px 0}
  .home .logo{width:clamp(34px,calc(12vw - 10px),44px)}  /* crecen con el ancho: caben dos filas desde 360 px */
  .tabs{flex:1 1 auto;min-width:0;flex-wrap:wrap;overflow:visible}
  .tabs li.br{display:block;flex-basis:100%;height:0}
  .tabs a{font-size:clamp(14px,calc(4vw - 0.5px),16px);padding:6px 5px 8px;border-bottom-width:2px}
  .tabs li.sep{display:none}
  .tabs .lg{display:none} .tabs .sh{display:inline}
}
"""


def topbar(current=None, nav=NAV, home='./#provincia'):
    items = []
    for k, label, href in nav:
        if k == 'razones':
            items.append('<li class="sep" aria-hidden="true"></li>')
        cur = ' aria-current="page"' if k == current else ''
        text = f'<span class="lg">{label}</span><span class="sh">Razones</span>' if k == 'razones' else label
        items.append(f'<li><a href="{href}" data-tab="{k}"{cur}>{text}</a></li>')
        if k == 'metodo':
            items.append('<li class="br" aria-hidden="true"></li>')  # en el móvil, segunda fila desde aquí
    return (f'<nav class="topbar" aria-label="Secciones"><div class="in"><a class="home" href="{home}">{LOGO}'
            f'<span class="vh">Echar a Sánchez</span></a><ul class="tabs">{"".join(items)}</ul></div></nav>')


def page(body, description='', path=''):
    """Esqueleto HTML completo con charset, favicon (la pinza) y Open Graph (imagen out/og.png de build_og.py)."""
    fav = open(os.path.join(HERE, 'favicon.svg'), encoding='utf-8').read().strip()
    fav = 'data:image/svg+xml;base64,' + base64.b64encode(fav.encode()).decode()
    m = re.search(r'<title>(.*?)</title>', body)
    title = escape(m.group(1) if m else 'Echar a Sánchez', quote=True)
    d = escape(description, quote=True)
    # Huella de la imagen en la URL: WhatsApp y Facebook guardan la previsualización por URL y así ven la nueva
    og_png = os.path.join(HERE, '..', 'out', 'og.png')
    v = hashlib.md5(open(og_png, 'rb').read()).hexdigest()[:8] if os.path.exists(og_png) else '1'
    og = (f'<meta property="og:type" content="website">\n<meta property="og:site_name" content="Echar a Sánchez">\n'
          f'<meta property="og:locale" content="es_ES">\n<meta property="og:url" content="{SITE_URL}/{path}">\n'
          f'<meta property="og:title" content="{title}">\n<meta property="og:description" content="{d}">\n'
          f'<meta property="og:image" content="{SITE_URL}/og.png?v={v}">\n<meta property="og:image:width" content="1200">\n'
          f'<meta property="og:image:height" content="630">\n'
          f'<meta property="og:image:alt" content="Perfil con una pinza en la nariz: Echar a Sánchez">\n'
          f'<meta name="twitter:card" content="summary_large_image">\n')
    desc = f'<meta name="description" content="{d}">\n' if description else ''
    return ('<!doctype html>\n<html lang="es" data-theme="light">\n<head>\n<meta charset="utf-8">\n<meta name="color-scheme" content="light">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1">\n' + desc + og +
            f'<link rel="icon" type="image/svg+xml" href="{fav}">\n</head>\n<body>\n' + body + '\n</body>\n</html>\n')


def tokens():
    """Colores y fuentes del informe (de ':root{' a la regla 'body{' de report_template.html)."""
    report = open(os.path.join(HERE, 'report_template.html'), encoding='utf-8').read()
    return report[report.index(':root{'):report.index('\nbody{')]
