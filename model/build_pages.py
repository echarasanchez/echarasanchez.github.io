"""Genera las páginas fijas de la web: out/razones.html (desde data/expediente.json) y out/quienes.html.

El dosier de "Razones" se adaptó del hecho por el usuario con otra herramienta (oct-2026). Las dos páginas comparten
colores, fuentes, logo y barra de pestañas con el informe (model/web.py).
"""
import json, os, sys
from html import escape
sys.path.insert(0, os.path.dirname(__file__))
import web

HERE = os.path.dirname(__file__)
OUT = os.path.join(HERE, '..', 'out')


def fill(tpl, current, nav=web.NAV, home='./#provincia', **parts):
    html = (tpl.replace('/*__TOKENS__*/', web.tokens()).replace('/*__TOPBAR_CSS__*/', web.TOPBAR_CSS)
            .replace('/*__TOPBAR__*/', web.topbar(current, nav, home)))
    for k, v in parts.items():
        html = html.replace(f'/*__{k}__*/', v)
    assert '/*__' not in html, 'quedan marcadores sin rellenar'
    return html


# ---------- Razones para echar a Sánchez
d = json.load(open(os.path.join(HERE, '..', 'data', 'expediente.json'), encoding='utf-8'))
JUDICIAL = {'condena', 'no-firme', 'juicio'}
label = d['stamp_label']
all_points = [p for c in d['chapters'] for p in c['points']]
count = {s['id']: (len(all_points) if s['id'] == 'todas' else sum(p['stamp'] == s['id'] for p in all_points)) for s in d['stamps']}


def sources(p):
    if not p.get('sources'):
        return ''
    links = ''.join(f'<li><a href="{escape(s["u"])}" rel="noopener" target="_blank">{escape(s["t"])}</a></li>' for s in p['sources'])
    return f'<details class="src"><summary>Fuentes ({len(p["sources"])})</summary><ul>{links}</ul></details>'


chapters = []
for c in d['chapters']:
    pts = ''.join(f'<article class="point" data-stamp="{p["stamp"]}"><h3>{escape(p["title"])} '
                  f'<span class="stamp{" judicial" if p["stamp"] in JUDICIAL else ""}">{escape(label[p["stamp"]])}</span></h3>'
                  f'<p>{escape(p["body"])}</p>{sources(p)}</article>' for p in c['points'])
    chapters.append(f'<section class="chapter" id="{c["id"]}"><p class="eyebrow red">{c["numeral"]} · {escape(c["kicker"])}</p>'
                    f'<h2>{escape(c["title"])}</h2><p class="clede">{escape(c["lede"])}</p><div class="points">{pts}</div></section>')

razones_tpl = open(os.path.join(HERE, 'razones_template.html'), encoding='utf-8').read()
razones_parts = dict(
            CIERRE=web.fecha(d['cierre']),
            BRIEF=''.join(f'<li><b>{i:02d}</b><span>{escape(t)}</span></li>' for i, t in enumerate(d['brief'], 1)),
            TOC=''.join(f'<li><a href="#{c["id"]}"><span>{c["numeral"]}</span>{escape(c["title"])}</a></li>' for c in d['chapters']),
            OPTIONS=''.join(f'<option value="{c["id"]}">{c["numeral"]} · {escape(c["title"])}</option>' for c in d['chapters']),
            FILTERS=''.join(f'<button type="button" data-f="{s["id"]}" aria-pressed="{str(s["id"] == "todas").lower()}">{escape(s["label"])}<span>{count[s["id"]]}</span></button>'
                            for s in d['stamps']),
            CHAPTERS='\n'.join(chapters))
html = fill(razones_tpl, 'razones', **razones_parts)
RAZONES_DESC = 'El método, las condenas firmes, los contrapesos y las razones económicas para que el bloque de investidura no repita el 29 de noviembre de 2026.'
open(os.path.join(OUT, 'razones.html'), 'w', encoding='utf-8').write(web.page(html, RAZONES_DESC, 'razones.html'))
print('razones ok |', len(d['chapters']), 'capítulos,', len(all_points), 'puntos,', sum(len(p.get('sources', [])) for p in all_points), 'fuentes')

# ---------- Quiénes somos
quienes_tpl = open(os.path.join(HERE, 'quienes_template.html'), encoding='utf-8').read()
logo = web.LOGO.replace('class="logo"', 'class="big-logo"').replace('id="lgc"', 'id="lgc2"').replace('url(#lgc)', 'url(#lgc2)')
html = fill(quienes_tpl, 'quienes', LOGO=logo)
QUIENES_DESC = 'Sociedad civil, sin carné ni siglas: quién hace esta web y cómo comprobar lo que dice.'
open(os.path.join(OUT, 'quienes.html'), 'w', encoding='utf-8').write(web.page(html, QUIENES_DESC, 'quienes.html'))
print('quienes ok')


# ---------- Versiones retiradas (las elige tools/publicar.sh por la fecha)
# encuestas: del 24 al 27-N la ley prohíbe difundir sondeos (art. 69.7 LOREG) y las recomendaciones salen de ellos:
#            index.html pasa a ser un aviso; Razones y Quiénes siguen, sin enlaces a lo retirado.
# reflexion: desde el fin de la campaña (27-N, 24:00) no se puede difundir propaganda (art. 53): las tres páginas son el aviso.
def cambia(html, pares, n=-1):
    for a, b in pares:
        assert a in html, f'no está: {a[:60]}'
        html = html.replace(a, b, n)
    return html


AVISO = {
    'encuestas': dict(
        EYEBROW='Veda de encuestas · 24 a 29 de noviembre',
        TITULO='El mapa y las recomendaciones, retirados',
        LEDE='La ley electoral prohíbe publicar, difundir o reproducir sondeos durante los cinco días anteriores a la '
             'votación (artículo 69.7 de la LOREG). Lo que esta web recomienda en cada provincia sale de las encuestas, así '
             'que desde el 24 de noviembre no se muestra: ni el mapa, ni las tablas del Congreso y el Senado, ni los cálculos.',
        CUERPO='<div class="grid"><a class="card" href="razones.html"><h2>Razones para echar a Sánchez</h2>'
               '<p>El método, las condenas firmes, los contrapesos y las razones económicas, cada una con sus fuentes.</p></a>'
               '<a class="card" href="quienes.html"><h2>Quiénes somos</h2>'
               '<p>Sociedad civil, sin carné ni siglas. Sin publicidad, sin donaciones y sin cookies.</p></a></div>'
               '<p class="ley">El código y los datos del modelo también están retirados del repositorio público durante la veda.</p>',
        DESC='Del 24 al 29 de noviembre la ley prohíbe difundir sondeos: el mapa y las recomendaciones de esta web están retirados.'),
    'reflexion': dict(
        EYEBROW='Jornada de reflexión · 28 y 29 de noviembre',
        TITULO='Esta web no muestra nada estos días',
        LEDE='La campaña electoral termina a las 24:00 del 27 de noviembre y desde entonces la ley no permite difundir '
             'propaganda electoral (artículo 53 de la LOREG). Por eso aquí no hay contenido durante la jornada de reflexión '
             'ni el día de la votación.',
        CUERPO='',
        DESC='Jornada de reflexión: esta web no muestra contenido el 28 ni el 29 de noviembre.'),
}
aviso_tpl = open(os.path.join(HERE, 'aviso_template.html'), encoding='utf-8').read()
for modo, a in AVISO.items():
    dest = os.path.join(OUT, 'retirada', modo)
    os.makedirs(dest, exist_ok=True)
    nav = web.NAV_RETIRADA if modo == 'encuestas' else []
    aviso = fill(aviso_tpl, 'aviso', nav, './', MODO=modo, LOGO=logo, **{k: v for k, v in a.items() if k != 'DESC'})
    paginas = {'index.html': web.page(aviso, a['DESC'])}
    if modo == 'encuestas':
        razones = cambia(fill(razones_tpl, 'razones', nav, './', **razones_parts), [
            (': <a href="./#senado">la regla de tu provincia</a> dice cómo, también donde PP y Vox han pactado.', '.'),
            ('\n      <a href="./">Ver qué votar en tu provincia</a>', ''),
            ('← Volver a qué votar en tu provincia', '← Volver al inicio')])
        quienes = cambia(fill(quienes_tpl, 'quienes', nav, './', LOGO=logo), [
            (', y lo contamos en la pestaña <a href="./#metodo">Método</a>, con lo que falló.', '.'),
            ('El código y los datos están <a href="https://github.com/echarasanchez/echarasanchez.github.io" rel="noopener">en abierto en GitHub</a>, para que',
             'El código y los datos están <a href="https://github.com/echarasanchez/echarasanchez.github.io" rel="noopener">en abierto en GitHub</a> '
             '(del 24 al 29 de noviembre, retirados con las recomendaciones), para que'),
            ('<a href="./#provincia">Ver qué votar en tu provincia</a> · ', '')])
        assert './#' not in razones + quienes, 'quedan enlaces a pestañas retiradas'
        paginas |= {'razones.html': web.page(razones, RAZONES_DESC, 'razones.html'),
                    'quienes.html': web.page(quienes, QUIENES_DESC, 'quienes.html')}
    else:
        paginas |= {f: web.page(aviso, a['DESC'], f) for f in ('razones.html', 'quienes.html')}
    for f, h in paginas.items():
        open(os.path.join(dest, f), 'w', encoding='utf-8').write(h)
print('retirada ok |', ', '.join(AVISO))


# ---------- Versión de precampaña (hasta el 13-N a las 00:00; la elige tools/publicar.sh por la fecha)
# Antes de la campaña la ley no permite hacer propaganda electoral (art. 53 LOREG) y la JEC (Instrucción 3/2011) admite webs
# sin contratación «siempre que no incluyan una petición expresa del voto». Mismos datos y cálculos; cambian los textos que
# piden el voto («Vota», «conviene votar») por los que describen qué papeleta resta más, y un aviso en las tres páginas.
# Necesita out/informe_modelo_29N.html: build_report.py tiene que ir antes.
PRE_CSS = """
.precampana{background:var(--accent-soft);border-bottom:1px solid var(--rule);font-size:13.5px;line-height:1.4}
.precampana p{max-width:1180px;margin:0 auto;padding:7px max(16px,env(safe-area-inset-right,0px)) 7px max(16px,env(safe-area-inset-left,0px))}
.nota-ley{margin-top:14px;padding:12px 14px;border-left:3px solid var(--accent);background:var(--paper);font-size:15px;line-height:1.5;max-width:70ch}
"""
PRE_BANDA = ('<div class="precampana" data-modo="precampana"><p><strong>Precampaña:</strong> hasta el 12 de noviembre incluido '
             'esta web analiza, no pide el voto para nadie (art. 53 de la LOREG).</p></div>')
PRE_NOTA = ('<p class="nota-ley"><strong>Hasta el 12 de noviembre incluido, análisis; no petición de voto.</strong> La campaña '
            'empieza a las 00:00 del 13 de noviembre y hasta entonces la ley no permite hacer propaganda electoral (art. 53 de la LOREG). Esta web no '
            'pide el voto para ningún partido: calcula qué papeleta le quita más escaños al bloque de investidura en cada '
            'provincia. Qué votar lo decide cada uno.</p>')
PRE_INFORME = [
    ('Qué votar en tu provincia el 29-N', 'Qué voto resta más en tu provincia el 29-N'),   # <title> y og:title (vista previa en redes)
    ('content="Qué votar en cada provincia el 29-N para quitar escaños', 'content="Qué papeleta quita más escaños en cada provincia el 29-N'),
    ('Que tu voto le quite un escaño a Sánchez.', 'Dónde un voto le quita un escaño a Sánchez.'),
    ('y verás a qué partido conviene votar para quitarle escaños al bloque que invistió a Sánchez.',
     'y verás qué papeleta le quita más escaños al bloque que invistió a Sánchez.'),
    ('con la nariz tapada.</p>', 'con la nariz tapada.</p>' + PRE_NOTA),
    ('pulsa una para ver qué votar', 'pulsa una para ver qué papeleta resta más'),
    ('Donde PP y Vox van por separado, las tres al mismo partido:',
     'Donde PP y Vox van por separado, lo que más resta es ponerlas las tres al mismo partido:'),
    ('Qué votar en cada provincia para quitar escaños al', 'Qué papeleta quita más escaños en cada provincia al'),
    ('se suma a la opción recomendada', 'se suma a la opción que más resta'),
    ('veces menos que la opción recomendada', 'veces menos que la opción que más resta'),
    ('<th>Vota</th>', '<th>Resta más</th>'),
    ('Congreso · ${r.escanos} escaños</span>', 'Congreso · ${r.escanos} escaños · resta más</span>'),
    ('para ver qué votar al Congreso y al Senado.', 'para ver qué papeleta resta más en el Congreso y en el Senado.'),
    ("a_VOX: 'Si votabas al PP: Vox', a_JUNTS: 'Si votabas al PP: Junts'",
     "a_VOX: 'Sin el PP, resta más Vox', a_JUNTS: 'Sin el PP, resta más Junts'"),
    ('Qué marcar', 'Qué resta más'),
    ('<b>Si votabas al PP, tus tres cruces a los candidatos de ${NAME[k]}.</b>',
     '<b>Para el votante del PP, lo que más resta: las tres cruces a los candidatos de ${NAME[k]}.</b>'),
    ('<b>La recomendación.</b>', '<b>Lo que más resta.</b>'),
    ('La opción que más escaños quita es la recomendada.', 'La opción que más escaños quita es la que señala el mapa.'),
    ('no decimos «vota X»: decimos «empate»', 'no señalamos una sola: decimos «empate»'),
    ('retira el mapa, las tablas y las recomendaciones', 'retira el mapa, las tablas y los cálculos por provincia'),
    ('(Junts se recomienda donde es lo más eficaz)', '(Junts sale donde es lo que más resta)')]
PRE_ENLACE = [('Ver qué votar en tu provincia', 'Ver qué resta más en tu provincia')]
PRE_RAZONES = PRE_ENLACE + [
    ('Y vota como si el último escaño de tu provincia fuera el de la investidura. Puede serlo.',
     'El último escaño de tu provincia puede ser el de la investidura.'),
    ('Esto no se rebate con un hilo. Se rebate con un escaño menos.', 'Esto no se rebate con un hilo: se decide en las urnas.'),
    ('En el Congreso, no partas el voto por debajo del último cociente de tu provincia. En el Senado, que la derecha no disperse '
     'sus tres cruces: <a href="./#senado">la regla de tu provincia</a> dice cómo,',
     'En el Congreso, un voto que se parte por debajo del último cociente de la provincia no suma escaños. En el Senado, tres '
     'cruces dispersas pueden regalar el 3-1: <a href="./#senado">la tabla del Senado</a> calcula qué resta más,'),
    ('← Volver a qué votar en tu provincia', '← Volver al mapa de tu provincia')]
PRE_QUIENES = PRE_ENLACE + [('Tampoco a las que esta web recomienda votar.', 'Tampoco a las que salen en el mapa como las que más restan.'),
                             ('No te pedimos que te guste a quien votas: a nosotros tampoco nos gusta del todo. Te pedimos que tu voto cuente.',
                             'No hace falta que te guste a quien votas: a nosotros tampoco nos gusta del todo. Lo que importa es que el voto cuente.')]


def precampana(html, pares):
    html = cambia(html, [('</style>', PRE_CSS + '</style>'), ('</nav>', '</nav>' + PRE_BANDA)], 1)   # la primera: la barra
    return cambia(html, pares)


dest = os.path.join(OUT, 'precampana')
os.makedirs(dest, exist_ok=True)
for f, src, pares in (('index.html', 'informe_modelo_29N.html', PRE_INFORME), ('razones.html', 'razones.html', PRE_RAZONES),
                      ('quienes.html', 'quienes.html', PRE_QUIENES)):
    html = precampana(open(os.path.join(OUT, src), encoding='utf-8').read(), pares)
    assert 'Si votabas al PP' not in html and '<th>Vota</th>' not in html, f'{f}: queda una petición de voto'
    open(os.path.join(dest, f), 'w', encoding='utf-8').write(html)
print('precampaña ok')
