"""Genera el informe HTML del modelo con los datos incrustados."""
import datetime as dt, json, os, sys, pandas as pd, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
import web

OUT = os.path.join(os.path.dirname(__file__), '..', 'out')
rows = json.load(open(f'{OUT}/provincias.json'))
res = json.load(open(f'{OUT}/resumen_nacional.json'))
SA = pd.read_csv(f'{OUT}/senado_A_media_privadas.csv').set_index('prov')
SC = pd.read_csv(f'{OUT}/senado_B_CIS.csv').set_index('prov')
senado = [{'p': r['provincia'], **r['senado']} for r in rows if r['senado']]     # explain.py
# Totales (47 provincias de 4 senadores): con el pacto, antes del pacto y con toda la derecha en tres candidatos
sen_tot = {k: [round(S.E_senadores_bloqueS.sum()), round(S.E_antes_pacto.sum()), round(S.E_max_derecha.sum())]
           for k, S in (('A', SA), ('C', SC))}
for r in rows:
    r['v_best'] = max(r['valor_mezcla'].values())
rows.sort(key=lambda r: -r['v_best'])
mapa = json.load(open(os.path.join(os.path.dirname(__file__), '..', 'data', 'mapa_provincias.json')))
cf = json.load(open(f'{OUT}/contrafactual_2023.json'))   # model/contrafactual_2023.py
data = {'prov': rows, 'nac': res, 'senado': senado, 'sen_tot': sen_tot, 'map': mapa, 'cf': cf}
tpl = open(os.path.join(os.path.dirname(__file__), 'report_template.html'), encoding='utf-8').read()
html = tpl.replace('/*__DATA__*/null', json.dumps(data, ensure_ascii=False))
html = (html.replace('/*__TOPBAR_CSS__*/', web.TOPBAR_CSS).replace('/*__TOPBAR__*/', web.topbar())
        .replace('/*__TABS__*/[]', json.dumps(web.INDEX_TABS)).replace("/*__SITE__*/''", json.dumps(web.SITE_URL)))
meta = json.load(open(f'{OUT}/meta.json'))   # run_2026.py: fecha de corte de las encuestas
coma = lambda x: f'{x:.1f}'.replace('.', ',')
lista = '; '.join(f"{e['empresa']} ({e['campo']})" for e in meta['encuestas'])
html = (html.replace('/*__N_ENC__*/', str(meta['n_encuestas'])).replace('/*__CAMPO__*/', meta['campo'].replace('-', '–'))
        .replace('/*__LISTA_ENC__*/', lista)
        .replace('/*__MEDIA_A__*/', ' · '.join(f"{n} {coma(meta['media'][k])}" for k, n in (('PP', 'PP'), ('PSOE', 'PSOE'), ('VOX', 'Vox')))))
html = (html.replace('/*__DATOS_A__*/', web.fecha(meta['datos_a'], corta=True))
        .replace('/*__CUENTA__*/', web.cuenta_atras(dt.date.today())).replace('/*__ELECCION__*/', web.ELECCION))
# La plantilla es un fragmento (formato artifact); para servirlo fuera de claude.ai necesita doctype, charset y favicon.
html = web.page(html, 'Qué votar en cada provincia el 29-N para quitar escaños al bloque de investidura: D\'Hondt, encuestas y escenarios.')
open(f'{OUT}/informe_modelo_29N.html', 'w', encoding='utf-8').write(html)
print('ok', len(html))
