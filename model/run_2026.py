"""Ejecuta el modelo 2026 en dos escenarios y genera las recomendaciones por provincia."""
import sys, os, json; sys.path.insert(0, os.path.dirname(__file__))
from model import *

OUT = os.path.join(os.path.dirname(__file__), '..', 'out')
d = load_2023()
w = d.pop_k * VALID_PER_POP * np.where(d.ccaa == 'CAT', 0.88, 1.0)
valid_votes = (w * 1000).round(-3)
B = base_2026(d)
cat = (d.ccaa == 'CAT').values

# CEO (oct-2026) calibrado a escaños: PSC 19, ERC(+Podem) 11, Comuns 2, PP 6, Junts 4, Vox 6
CAT_TARGETS = {'PSOE': 32, 'ERC': 19, 'PP': 12.5, 'VOX': 11, 'JUNTS': 8, 'FA': 5.5}

# Fecha de corte de las encuestas de ENCUESTAS y CAT_TARGETS: es la que sale en la web («Datos a ...»). Cambiarla con ellas.
DATOS_A = '2026-11-12'

# Media de encuestas privadas: la más reciente de cada empresa con campo terminado en las tres semanas anteriores a DATOS_A
# (14-nov: desde el 22-oct; 16 sondeos: oleadas nuevas de 40dB, Sigma Dos, SW Demoscopia y Winston. 12-nov: 16 sondeos: entra DYM/Henneo y la oleada de SW Demoscopia hasta el 10-nov. 9-nov: 15 sondeos: entran SW Demoscopia, GAD3, 40dB, Data10 y Celeste-Tel, y oleadas nuevas de SocioMétrica,
# Sigma Dos, NC Report, Sondaxe, Ateneo del Dato e IMOP). Sin el CIS (escenario B), los paneles de agregadores (EM-Analytics) ni
# los sondeos de partidos (PSOE, 25-oct; el de Vox que publicó The Objective, 27-oct).
# Fuente: Wikipedia, «Opinion polling for the 2026 Spanish general election» (14-nov), contrastada con Demócrata y los medios.
# PP sin UPN (9-nov): en Navarra la lista UPN-PP está en la columna UPN del modelo, así que donde Wikipedia da «PP + UPN» en sus
# notas se toma solo el PP (SocioMétrica, SW, NC Report, Celeste-Tel, Hamalgama; ~0,3 puntos); donde no lo desglosa, la cifra publicada.
# Frente Amplio siempre con Compromís (en el modelo, la lista de Compromís va en la columna FA): sumados cuando la encuesta los da
# aparte (14-nov: SocioMétrica, 40dB y Celeste-Tel; antes solo FA en esas tres; GAD3 ya iba sumado). None: no lo publica; la media es de las que sí.
#            empresa / medio                         campo               PP    PSOE  Vox   FA    Podemos
ENCUESTAS = [('40dB / Prisa',                        '10-12 nov',        31.5, 29.4, 18.8, 5.1, 1.3),
             ('Sigma Dos / El Mundo',                '3-12 nov',         31.0, 25.4, 19.7, 7.3, 1.4),
             ('SW Demoscopia / La Séptima',          '26 oct-12 nov',    28.5, 31.6, 17.1, 7.3, 1.7),
             ('Winston / Artículo14',                '5-8 nov',          31.1, 26.4, 18.7, 8.4, 1.6),
             ('SocioMétrica / El Español',           '1 sep-8 nov',      32.0, 27.7, 18.9, 5.9, 1.2),
             ('IMOP / El Confidencial',              '2-6 nov',          29.8, 25.9, 19.9, 8.1, 1.2),
             ('DYM / Henneo',                        '4-6 nov',          33.1, 27.3, 18.6, 5.6, 1.9),
             ('GAD3 / ABC',                          '3-5 nov',          31.9, 25.9, 18.6, 7.5, 1.4),
             ('Ateneo del Dato / elDiario.es',       '2-5 nov',          31.5, 28.6, 18.6, 6.1, 1.5),
             ('NC Report / La Razón',                '2-5 nov',          32.6, 25.6, 19.3, 6.9, 2.4),
             ('Sondaxe / La Voz de Galicia',         '2-4 nov',          29.7, 27.3, 18.6, 7.1, 2.2),
             ('Data10 / OKDiario',                   '2-3 nov',          32.4, 24.7, 19.8, 6.9, 3.1),
             ('Celeste-Tel / Onda Cero',             '29 oct-3 nov',     31.4, 25.7, 19.2, 8.0, 1.9),
             ('Target Point / El Debate',            '28-30 oct',        31.8, 25.5, 19.9, 6.6, 2.4),
             ('Hamalgama Métrica / Vozpópuli',       '22-28 oct',        32.0, 26.4, 19.9, 5.4, 2.2),
             ('More in Common',                      '21-25 oct',        28.3, 27.6, 20.8, 7.8, 2.6)]
CAMPO = '21 oct-12 nov 2026'   # trabajo de campo, de la última que termina antes a la última (sale en la web)
media = {k: round(float(np.mean([e[i + 2] for e in ENCUESTAS if e[i + 2] is not None])), 1)
         for i, k in enumerate(['PP', 'PSOE', 'VOX', 'FA', 'POD'])}
ERROR_2023 = {'PSOE': 3.4, 'PP': -1.3, 'VOX': -0.6}   # error medio de las encuestas finales de 2023

SCENARIOS = {
    'A_media_privadas': {**media, 'SALF': 1.5},
    # CIS preelectoral (estudio 3584, campo 7-30 oct, N=45.074, publicado el 12-nov). FA = Frente Amplio 4,7 + Compromís 1,6
    # + UPC 0,4 + Ara Més 0,2 (en el modelo van en la columna FA); Podemos, donde va solo (ERC-Podemos, 3,1, cuenta como ERC).
    # Antes, el barómetro de octubre (3582, campo 1-6 oct): PP 22,2 · PSOE 34,0 · Vox 17,1 · FA 6,1 · Podemos 3,1.
    'B_CIS': {'PP': 25.5, 'PSOE': 33.3, 'VOX': 18.4, 'FA': 6.9, 'POD': 1.1, 'SALF': 1.4},
    # A con el error medio de las encuestas finales de 2023. Solo para el panorama nacional.
    'C_fallo_como_2023': {**{k: round(v + ERROR_2023.get(k, 0), 1) for k, v in media.items()}, 'SALF': 1.5},
}

results = {}
for name, tg in SCENARIOS.items():
    S = fit_scenario(B, w, tg, region_mask=cat, region_targets=CAT_TARGETS)
    X = simulate(S, d, 'seats26', n=4000, seed=7)
    sims = seats_all(X, d, 'seats26')
    nat = sims.sum(1)
    bS = bloc_seats(nat)
    right = nat[:, [PARTIES.index(k) for k in ('PP', 'VOX', 'UPN')]].sum(1)
    nonS_all = nat[:, [PARTIES.index(k) for k in ('PP', 'VOX', 'UPN', 'JUNTS')]].sum(1)
    summary = {
        'escanos_medios': {k: round(float(nat[:, i].mean()), 1) for i, k in enumerate(PARTIES) if nat[:, i].mean() > 0.05},
        'bloque_S_media': round(float(bS.mean()), 1),
        'bloque_S_IC90': [int(np.percentile(bS, 5)), int(np.percentile(bS, 95))],
        'P_bloque_S_ge_176': round(float((bS >= 176).mean()), 3),
        'P_PP_VOX_UPN_ge_176': round(float((right >= 176).mean()), 3),
        'P_PP_VOX_UPN_JUNTS_ge_176': round(float((nonS_all >= 176).mean()), 3),
    }
    T = tactical(X, d, 'seats26', delta=1.0)
    R = recommend(T)
    T = T.join(R)
    T['votos_validos_aprox'] = valid_votes
    T['votos_por_punto'] = (valid_votes / 100).round(-2)
    T['shares'] = [json.dumps({k: round(float(v), 1) for k, v in S.loc[p, PARTIES].items() if v >= 0.5}) for p in d.index]
    # Cuánto pueden fallar las encuestas en votos de cada partido (mitad del intervalo del 90% de las simulaciones):
    # la explicación lo usa para decir si un escaño que hoy pelea uno puede acabar peleándolo otro
    T['error90'] = [json.dumps({k: int(round((np.percentile(X[:, j, i], 95) - np.percentile(X[:, j, i], 5)) / 2 * valid_votes[p] / 100, -3))
                                for i, k in enumerate(PARTIES) if k in ('PP', 'VOX', 'JUNTS', 'UPN') and np.median(X[:, j, i]) >= 0.3})
                    for j, p in enumerate(d.index)]
    SEN = senate(X, d)
    results[name] = (summary, T, SEN)
    T.to_csv(os.path.join(OUT, f'tactico_{name}.csv'))
    SEN.to_csv(os.path.join(OUT, f'senado_{name}.csv'))
    print(f'\n######## {name}')
    print(json.dumps(summary, ensure_ascii=False))

# --------- combinación de escenarios: recomendación robusta
A = results['A_media_privadas'][1]; Bc = results['B_CIS'][1]
rows = []
for p in d.index:
    ra, rb = A.loc[p, 'rec'], Bc.loc[p, 'rec']
    if ra == rb: final = ra; robust = 'sí'
    elif ra.startswith('INDIF') and not rb.startswith('INDIF'): final = rb + ' (solo importa si aciertan el CIS)'; robust = 'parcial'
    elif rb.startswith('INDIF') and not ra.startswith('INDIF'): final = ra + ' (solo importa con la media de privadas)'; robust = 'parcial'
    else: final = f'A: {ra} | CIS: {rb}'; robust = 'no'
    def vfmt(T, k):
        v = T.loc[p, 'v_' + k]; return None if np.isnan(v) else round(float(v), 3)
    rows.append({'provincia': p, 'escanos': int(d.loc[p, 'seats26']),
                 'recomendacion': final, 'robusta': robust,
                 'rec_A': ra, 'rec_CIS': rb,
                 **{f'A_v_{k}': vfmt(A, k) for k in CANDIDATES},
                 **{f'CIS_v_{k}': vfmt(Bc, k) for k in CANDIDATES},
                 'A_trasvase_PP_a_VOX': None if np.isnan(A.loc[p, 't_PP_VOX']) else round(float(A.loc[p, 't_PP_VOX']), 3),
                 'votos_por_punto': int(A.loc[p, 'votos_por_punto']),
                 'A_E_bloqueS': round(float(A.loc[p, 'E_bloc']), 2), 'CIS_E_bloqueS': round(float(Bc.loc[p, 'E_bloc']), 2)})
F = pd.DataFrame(rows).set_index('provincia')
F.to_csv(os.path.join(OUT, 'recomendaciones_congreso.csv'))
pd.set_option('display.width', 250); pd.set_option('display.max_rows', 60); pd.set_option('display.max_colwidth', 60)
print(F[['escanos', 'recomendacion', 'robusta', 'A_v_PP', 'A_v_VOX', 'A_v_JUNTS', 'CIS_v_PP', 'CIS_v_VOX', 'A_v_SALF']].to_string())

json.dump({k: v[0] for k, v in results.items()}, open(os.path.join(OUT, 'resumen_nacional.json'), 'w'), ensure_ascii=False, indent=1)
json.dump({'datos_a': DATOS_A, 'campo': CAMPO, 'n_encuestas': len(ENCUESTAS), 'media': media,
           'encuestas': [dict(zip(['empresa', 'campo', 'PP', 'PSOE', 'VOX', 'FA', 'POD'], e)) for e in ENCUESTAS]},
          open(os.path.join(OUT, 'meta.json'), 'w'), ensure_ascii=False, indent=1)
