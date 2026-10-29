"""Material para compartir en redes: una página y una imagen por provincia, y tres imágenes nacionales.

out/compartir/<versión>/<slug>/index.html   página mínima con su propia previsualización (título, texto e imagen) que
    lleva a la web con la provincia elegida (../?p=<slug>#provincia). Así echarasanchez.ch/cantabria se ve en WhatsApp con
    el dato de Cantabria y no con el logo. Los robots de las previsualizaciones no ejecutan JavaScript: ven esta página.
out/compartir/<versión>/img/<slug>-<huella>.png   1200x630, fotografiada con Chromium como og.png. La huella (del HTML
    de la imagen) va en el nombre: WhatsApp y Facebook guardan la previsualización por URL, y si los datos no cambian la
    imagen no se vuelve a hacer (cada una tarda alrededor de un segundo).
out/compartir/<versión>/img/nacional-{2023,senado,salf}-<huella>.png   los tres mensajes nacionales, para publicarlas sueltas.
<versión>: precampana (hasta el 13-N: «lo que más resta», no «vota»), campana y retirada (del 23-N a las 21:00: las páginas
    solo llevan al aviso y no hay imágenes). A docs/ se copia la que toca por la fecha.
"""
import hashlib, json, os, re, subprocess, sys, tempfile, unicodedata
from html import escape
sys.path.insert(0, os.path.dirname(__file__))
import web

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'out')
DEST = os.path.join(OUT, 'compartir')
NAME = {'PP': 'PP', 'VOX': 'Vox', 'JUNTS': 'Junts', 'UPN': 'UPN'}
COL = {'PP': '#2a6fcb', 'VOX': '#5e9e2e', 'JUNTS': '#15a197', 'UPN': '#2a6fcb'}
LVL = {'alto': 'impacto alto', 'medio': 'impacto medio', 'bajo': 'impacto bajo'}


def slug(s):
    """La misma regla que slug() en report_template.html: 'A Coruña' -> 'a-coruna'."""
    s = unicodedata.normalize('NFD', s)
    return re.sub(r'[^a-z0-9]+', '-', ''.join(c for c in s if not unicodedata.combining(c)).lower())


def nivel(r):
    """Como level() en report_template.html: sobre el porcentaje que se muestra, alto ≥ 8, medio 4-7, bajo < 4."""
    p = round(max(r['valor_mezcla'].values()) * 100)
    return 'alto' if p >= 8 else 'medio' if p >= 4 else 'bajo'


def dato(r):
    """Primera frase de la explicación corta (model/narrativa.py), sin etiquetas. Donde no hay escaño en juego, la
    explicación empieza diciéndolo (ya lo dice la imagen): solo lo que sigue a los dos puntos, si lo hay."""
    t = re.split(r'(?<=\.)\s+(?=[A-ZÁÉÍÓÚ¿])', re.sub(r'<[^>]+>', '', r['explicacion_corta']))[0]
    if r['recomendacion'] == 'Indiferente':
        t = t.split(': ', 1)[1] if ': ' in t else 'Con las encuestas de hoy, ningún escaño está cerca de cambiar de bloque.'
        t = t[0].upper() + t[1:]
    return t


def tras_dos_puntos(t):
    """«Senado: las tres cruces…»: minúscula después de los dos puntos, salvo nombres propios (Vox)."""
    return t[0].lower() + t[1:] if t.split()[0] in ('Lo', 'Las', 'El') else t


def senado(s, pre):
    """Regla del Senado en una línea (la ficha de la web la da completa). None donde el modelo no lo cubre."""
    if not s or s.get('fuera_del_modelo'):
        return 'Vox no se presenta: el PP lleva en su lista a un candidato propuesto por Vox.' if s else None
    g, k = s['grupo'], s.get('regla')
    if g == 'sin_vox':
        return ('Vox no se presenta y el PP lleva a un candidato suyo: lo que más resta, las tres cruces a esa lista.' if pre
                else 'Vox no se presenta y el PP lleva a un candidato suyo: las tres cruces a la lista del PP.')
    if g == 'vox_un_candidato':
        dos = {'repartir': 'dos del PP, los que quieras', 'concentrar': 'los dos primeros del PP', 'igual': 'dos del PP'}[k]
        return f'Vox lleva un candidato y el PP, tres. Votantes del PP: sus tres. Votantes de Vox: el suyo y {dos}.'
    if g == 'sin_pp':
        if k == 'igual':
            return 'El PP no se presenta y los cuatro senadores serán del bloque: aquí el Senado no cambia.'
        d = NAME[k[2:]]
        return (f'El PP no se presenta: para su votante, lo que más resta son las tres cruces a {d}.' if pre
                else f'El PP no se presenta: si le votabas, tus tres cruces a {d}.')
    return 'Lo que más resta son las tres cruces a candidatos del mismo partido.' if pre else 'Las tres cruces, a candidatos del mismo partido.'


CSS = """
html,body{margin:0;width:1200px;height:630px;overflow:hidden}
body{background:#f6f7f9;color:#14202e;font-family:"Public Sans",system-ui,sans-serif;position:relative}
.main{position:absolute;left:64px;top:52px;width:740px}
.eye{font-size:22px;font-weight:600;color:#5b6674;letter-spacing:.02em}
h1{font-family:"Archivo",sans-serif;font-weight:800;font-stretch:88%;font-size:88px;line-height:.95;margin:10px 0 22px;letter-spacing:-.01em}
h1.largo{font-size:64px}
.lab{font-size:24px;font-weight:600;color:#5b6674;margin-bottom:2px}
.ver{display:flex;align-items:baseline;gap:18px;flex-wrap:wrap}
.par{font-family:"Archivo",sans-serif;font-weight:800;font-stretch:88%;font-size:76px;line-height:1}
.par .o{color:#5b6674;font-weight:600;font-size:48px}
.par.nada{font-size:52px;color:#5b6674}
.seal{font-size:20px;font-weight:600;border-radius:99px;padding:4px 14px;background:#e6eef8;color:#1f4f8a;align-self:center}
.dato{font-size:27px;line-height:1.3;margin:18px 0 0}
.sen{font-size:22px;line-height:1.35;margin:16px 0 0;padding-top:14px;border-top:2px solid #dfe3e8;color:#14202e}
.sil{position:absolute;right:56px;top:70px;width:330px;height:400px}
.pie{position:absolute;left:0;right:0;bottom:0;height:78px;background:#14202e;color:#e7ecf2;display:flex;align-items:center;gap:18px;padding:0 64px}
.pie .logo{width:50px;height:50px}
.pie .url{font-family:"Archivo",sans-serif;font-weight:700;font-size:28px;white-space:nowrap}
.pie .url.largo{font-size:23px}
.pie .src{margin-left:auto;font-size:16px;color:#9aa6b4;text-align:right;line-height:1.35;max-width:520px}
.logo .lg-bg{fill:#e6eef8} .logo .lg-face{fill:#14202e} .logo .lg-pin{fill:#c23b3b}
.logo .lg-wire{stroke:#14202e} .logo .lg-coil{fill:#e6eef8;stroke:#14202e}
.nac .main{width:1072px}
.big{display:flex;gap:56px;margin-top:22px}
.big div{font-size:21px;color:#5b6674;line-height:1.3;max-width:330px}
.big b{display:block;font-family:"Archivo",sans-serif;font-weight:800;font-stretch:88%;font-size:68px;color:#14202e;line-height:1.05}
.txt{font-size:27px;line-height:1.35;margin:0;max-width:1060px}
"""
FONTS = ('<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@75..125,400..800'
         '&family=Public+Sans:wght@400;600&display=block">')


def doc(body, extra=''):
    logo = web.LOGO.replace('id="lgc"', 'id="lgs"').replace('url(#lgc)', 'url(#lgs)')
    return (f'<!doctype html><html lang="es"><head><meta charset="utf-8">{FONTS}<style>{CSS}</style></head><body>'
            f'{body.replace("__LOGO__", logo)}{extra}</body></html>')


def pie(url, src):
    return (f'<div class="pie">__LOGO__<span class="url{" largo" if len(url) > 30 else ""}">{escape(url)}</span>'
            f'<span class="src">{src}</span></div>')


def foto(html, nombre, carpeta):
    """PNG de 1200x630 con Chromium; el nombre lleva la huella del HTML y, si ya existe, no se rehace."""
    f = f'{nombre}-{hashlib.md5(html.encode()).hexdigest()[:8]}.png'
    png = os.path.join(carpeta, f)
    if not os.path.exists(png):
        with tempfile.NamedTemporaryFile('w', suffix='.html', delete=False, encoding='utf-8') as t:
            t.write(html)
        try:
            subprocess.run(['chromium-headless-shell', '--no-sandbox', '--hide-scrollbars', '--virtual-time-budget=10000',
                            '--window-size=1200,630', f'--screenshot={os.path.abspath(png)}', 'file://' + t.name],
                           check=True, capture_output=True)
        finally:
            os.unlink(t.name)
    return f


def tarjeta(r, s, forma, pre, src):
    """HTML de la imagen de una provincia."""
    p, url = r['provincia'], f"echarasanchez.ch/{slug(r['provincia'])}"
    rec = r['recomendacion']
    if rec == 'Indiferente':
        lab, ver = 'Congreso', '<span class="par nada">Ningún escaño en juego</span>'
        fill, defs = '#8a939e', ''
    else:
        ks = rec.split(' o ')
        lab = ('Lo que más resta' + (', empatados' if len(ks) > 1 else '') if pre else
               'Vota' + (f' cualquiera de los {"dos" if len(ks) == 2 else "tres"}' if len(ks) > 1 else ''))
        ver = ('<span class="par">' + '<span class="o"> o </span>'.join(f'<span style="color:{COL[k]}">{NAME[k]}</span>' for k in ks)
               + f'</span><span class="seal">{LVL[nivel(r)]}</span>')
        if len(ks) == 1:
            fill, defs = COL[ks[0]], ''
        else:   # rayas, como el mapa de la web
            w = 14
            defs = (f'<defs><pattern id="ry" width="{w * len(ks)}" height="10" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
                    + ''.join(f'<rect x="{i * w}" width="{w}" height="10" fill="{COL[k]}"/>' for i, k in enumerate(ks)) + '</pattern></defs>')
            fill = 'url(#ry)'
    sen = senado(s, pre)
    body = (f'<div class="main"><div class="eye">Elecciones del 29-N · Congreso · {r["escanos"]} escaños</div>'
            f'<h1{" class=largo" if len(p) > 14 else ""}>{escape(p)}</h1><div class="lab">{lab}</div><div class="ver">{ver}</div>'
            f'<p class="dato">{escape(dato(r))}</p>'
            + (f'<p class="sen"><b>Senado:</b> {escape(tras_dos_puntos(sen))}</p>' if sen else '') + '</div>'
            f'<svg class="sil" id="sil">{defs}<path d="{forma}" fill="{fill}" stroke="#14202e" stroke-width="1.2" vector-effect="non-scaling-stroke"/></svg>'
            + pie(url, src))
    # El encuadre de la silueta lo calcula el navegador (getBBox), con un margen
    fit = ('<script>const s=document.getElementById("sil"),b=s.getBBox(),m=Math.max(b.width,b.height)*.06;'
           's.setAttribute("viewBox",[b.x-m,b.y-m,b.width+2*m,b.height+2*m].join(" "))</script>')
    return doc(body, fit)


def nacional(eye, h1, txt, big, url, src):
    cifras = ''.join(f'<div><b>{a}</b>{b}</div>' for a, b in big)
    return doc(f'<div class="nac"><div class="main"><div class="eye">{eye}</div><h1>{h1}</h1><p class="txt">{txt}</p>'
               f'<div class="big">{cifras}</div></div></div>' + pie(url, src))


def y_lista(a):
    return a[0] if len(a) < 2 else ', '.join(a[:-1]) + ' y ' + a[-1]


def pagina(p, titulo, desc, img, destino):
    """Página de una provincia: su previsualización y, para las personas, salto a la web con la provincia elegida."""
    t, d = escape(titulo, quote=True), escape(desc, quote=True)
    s = slug(p)
    og = (f'<meta property="og:type" content="website">\n<meta property="og:site_name" content="Echar a Sánchez">\n'
          f'<meta property="og:locale" content="es_ES">\n<meta property="og:url" content="{web.SITE_URL}/{s}/">\n'
          f'<meta property="og:title" content="{t}">\n<meta property="og:description" content="{d}">\n'
          f'<meta property="og:image" content="{web.SITE_URL}/{img}">\n<meta property="og:image:width" content="1200">\n'
          f'<meta property="og:image:height" content="630">\n<meta property="og:image:alt" content="{t}">\n'
          f'<meta name="twitter:card" content="summary_large_image">\n')
    return (f'<!doctype html>\n<html lang="es">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            f'<title>{t}</title>\n<meta name="description" content="{d}">\n<meta name="robots" content="noindex">\n{og}'
            f'<script>location.replace("{destino}")</script>\n</head>\n<body style="font-family:system-ui,sans-serif;padding:24px">\n'
            f'<p><a href="{destino}">{escape(p)}: ver en Echar a Sánchez</a></p>\n</body>\n</html>\n')


def main():
    P = json.load(open(f'{OUT}/provincias.json', encoding='utf-8'))
    mapa = json.load(open(os.path.join(HERE, '..', 'data', 'mapa_provincias.json')))['provs']
    datos_a = web.fecha(json.load(open(f'{OUT}/meta.json'))['datos_a'], corta=True)
    cf = json.load(open(f'{OUT}/contrafactual_2023.json'))
    import pandas as pd
    SA = pd.read_csv(f'{OUT}/senado_A_media_privadas.csv')
    sen_tot = [round(SA.E_antes_pacto.sum()), round(SA.E_senadores_bloqueS.sum()), round(SA.E_max_derecha.sum())]
    hechas = 0
    for v in ('precampana', 'campana'):
        pre = v == 'precampana'
        d = os.path.join(DEST, v); img = os.path.join(d, 'img')
        os.makedirs(img, exist_ok=True)
        antes = set(os.listdir(img)); usadas = set()
        src = (f'Estimación con la media de encuestas privadas y el CIS, datos a {datos_a}. Método y fuentes en la web.'
               + (' Precampaña: análisis, no petición de voto (art. 53 LOREG).' if pre else ''))
        for r in P:
            p = r['provincia']; s = slug(p)
            f = foto(tarjeta(r, r['senado'], mapa[p]['d'], pre, src), s, img); usadas.add(f)
            rec = r['recomendacion']
            nm = ' o '.join(NAME[k] for k in rec.split(' o ')) if rec != 'Indiferente' else None
            titulo = (f'{p}: ningún escaño del Congreso en juego' if not nm else
                      f'{p}: lo que más resta el 29-N es {nm}' if pre else f'{p}: el 29-N, vota {nm}')
            sen = senado(r['senado'], pre)
            desc = dato(r) + (f' Senado: {tras_dos_puntos(sen)}' if sen else '')
            os.makedirs(os.path.join(d, s), exist_ok=True)
            open(os.path.join(d, s, 'index.html'), 'w', encoding='utf-8').write(
                pagina(p, titulo, desc, f'img/{f}', f'../?p={s}#provincia'))
        # Nacionales
        e05 = next(e for e in cf['escenarios'] if e['fraccion'] == 0.05)
        e1 = next(e for e in cf['escenarios'] if e['fraccion'] == 1.0)
        src23 = 'Votos reales de 2023 por provincia (Ministerio del Interior), moviendo voto entre PP y Vox. Método en la web.'
        usadas.add(foto(nacional(
            'Elecciones de 2023, con los votos reales', 'Bastaba 1 de cada 20',
            f'Si en {len(e05["provincias"])} provincias 1 de cada 20 votantes del PP o de Vox se hubiera pasado al otro partido ({y_lista([x["provincia"] for x in e05["provincias"]])}), '
            f'el bloque que invistió a Sánchez se habría quedado en {e05["bloque"]} escaños.',
            [(f'{cf["real"]["bloque"]} → {e05["bloque"]}', 'escaños del bloque de investidura'),
             (f'{cf["real"]["PP_Vox_UPN"]} → {e1["PP_Vox_UPN"]}', f'PP + Vox + UPN con todo el voto de Vox al PP en {len(e1["provincias"])} provincias: mayoría absoluta')],
            'echarasanchez.ch', src23), 'nacional-2023', img))
        usadas.add(foto(nacional(
            'Senado · 29-N', 'Lo que más resta: tres cruces a la misma lista' if pre else 'Tres cruces, a la misma lista',
            'Salen los 4 candidatos más votados y cada votante marca hasta 3. La izquierda va unida; '
            'si la derecha reparte sus cruces, la izquierda puede llevarse 3 de los 4.',
            [(str(sen_tot[0]), 'senadores del bloque sin el pacto PP-Vox'), (str(sen_tot[1]), 'con el pacto'),
             (str(sen_tot[2]), 'si PP y Vox marcan a los mismos tres candidatos')],
            'echarasanchez.ch/#senado', src.replace('Estimación', 'En las 47 provincias que eligen 4 senadores. Estimación')), 'nacional-senado', img))
        va = [r for r in P if r['valor_SALF_vs_mejor'] is not None]
        algo = [r for r in va if r['valor_SALF_vs_mejor'] > 0.001]
        veces = sorted(round(max(r['valor_mezcla'].values()) / r['valor_SALF_vs_mejor']) for r in algo)
        n_veces = f'{veces[0]} veces' if veces[0] == veces[-1] else f'entre {veces[0]} y {veces[-1]} veces'
        usadas.add(foto(nacional(
            'Congreso · SALF', f'{len(va) - len(algo)} de {len(va)}',
            f'SALF se presenta al Congreso en {len(va)} provincias. En {len(va) - len(algo)} de ellas, un voto a SALF no le quita '
            f'ningún escaño al bloque de investidura. En {y_lista([r["provincia"] for r in algo])} algo resta, pero '
            f'{n_veces} menos que la opción que más resta.',
            [(n_veces.replace('entre ', '').replace(' y ', '-'), f'menos que la opción que más resta, en {y_lista([r["provincia"] for r in algo])}'),
             ('0', 'candidatos de SALF al Senado')], 'echarasanchez.ch/#metodo', src), 'nacional-salf', img))
        for f in antes - usadas:
            os.remove(os.path.join(img, f))
        hechas += len(usadas - antes)
    # Retirada (del 23-N a las 21:00): los enlaces ya compartidos llevan al aviso, sin dato ni imagen de la provincia
    d = os.path.join(DEST, 'retirada')
    for r in P:
        s = slug(r['provincia']); os.makedirs(os.path.join(d, s), exist_ok=True)
        open(os.path.join(d, s, 'index.html'), 'w', encoding='utf-8').write(
            pagina(r['provincia'], 'Echar a Sánchez', 'Aviso: del 24 al 29 de noviembre la ley no permite difundir encuestas.',
                   'og.png', '../'))
    print(f'compartir ok | {len(P)} provincias × 2 versiones + 3 nacionales; imágenes nuevas: {hechas}')


if __name__ == '__main__':
    main()
