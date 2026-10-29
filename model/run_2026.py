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
DATOS_A = '2026-10-26'

# Media de encuestas privadas: la más reciente de cada empresa con campo terminado en las tres semanas anteriores a DATOS_A.
# Sin el CIS (escenario B) ni los paneles de agregadores (EM-Analytics). Fuente: Wikipedia, «Opinion polling for the next Spanish
# general election», contrastada con Demócrata, Infobae y los medios (29-oct). Donde no coinciden, Wikipedia/Demócrata: NC Report
# PP 33,1 (Infobae: 32,9); SocioMétrica PP 32,4 y FA 5,2 (Electomanía: 32,0 y 4,8). None: no lo publica; la media es de las que sí.
#            empresa / medio                         campo               PP    PSOE  Vox   FA    Podemos
ENCUESTAS = [('SocioMétrica / El Español',           '1 sep-25 oct',     32.4, 27.0, 18.6, 5.2, 1.8),
             ('NC Report / La Razón',                '22-24 oct',        33.1, 25.8, 19.0, 6.6, 2.6),
             ('Winston / Artículo14',                '21-23 oct',        29.4, 27.1, 19.2, 5.6, None),
             ('Ateneo del Dato / elDiario.es',       '20-22 oct',        31.1, 27.6, 19.8, 6.8, 2.7),
             ('Sigma Dos / El Mundo',                '8-22 oct',         30.6, 26.1, 19.9, 7.4, 2.8),
             ('IMOP / El Confidencial',              '13-16 oct',        28.5, 27.1, 20.0, 8.9, None),
             ('Target Point / El Debate',            '6-9 oct',          32.0, 25.9, 18.7, 6.9, 3.4),
             ('40dB / Prisa',                        '7-8 oct',          31.9, 28.1, 18.9, 5.3, 2.3),
             ('GESOP / Prensa Ibérica',              '6-8 oct',          28.7, 26.1, 18.9, 8.0, 2.6),
             ('GAD3 / Vocento',                      '6-8 oct',          31.4, 26.4, 18.2, 7.4, 2.3),
             ('Hamalgama Métrica / Vozpópuli',       '5-8 oct',          33.4, 25.3, 19.6, 5.4, 3.3),
             ('InvyMark / laSexta',                  '5-8 oct',          32.8, 28.0, 18.8, 6.3, 3.2),
             ('DYM / Henneo',                        '5-7 oct',          34.0, 28.2, 18.2, 3.6, 3.6)]
CAMPO = '5-25 oct 2026'   # trabajo de campo, de la primera a la última (sale en la web)
media = {k: round(float(np.mean([e[i + 2] for e in ENCUESTAS if e[i + 2] is not None])), 1)
         for i, k in enumerate(['PP', 'PSOE', 'VOX', 'FA', 'POD'])}
ERROR_2023 = {'PSOE': 3.4, 'PP': -1.3, 'VOX': -0.6}   # error medio de las encuestas finales de 2023

SCENARIOS = {
    'A_media_privadas': {**media, 'SALF': 1.5},
    # CIS octubre 2026 (campo 1-6 oct)
    'B_CIS': {'PP': 22.2, 'PSOE': 34.0, 'VOX': 17.1, 'FA': 6.1, 'POD': 3.1, 'SALF': 1.5},
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
