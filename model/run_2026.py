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

# Fecha de corte de las encuestas de SCENARIOS y CAT_TARGETS: es la que sale en la web («Datos a ...»). Cambiarla con ellas.
DATOS_A = '2026-10-25'

SCENARIOS = {
    # media simple de 12 encuestas publicadas con campo 5-16 oct 2026 (IMOP x2, Sigma Dos x2, SocioMétrica,
    # Target Point, 40dB, GAD3, GESOP, Hamalgama, InvyMark, DYM)
    'A_media_privadas': {'PP': 31.6, 'PSOE': 26.5, 'VOX': 19.0, 'FA': 6.7, 'POD': 2.9, 'SALF': 1.5},
    # CIS octubre 2026 (campo 1-6 oct)
    'B_CIS': {'PP': 22.2, 'PSOE': 34.0, 'VOX': 17.1, 'FA': 6.1, 'POD': 3.1, 'SALF': 1.5},
    # A con el error medio de las encuestas finales de 2023 (PSOE +3,4, PP -1,3, Vox -0,6). Solo para el panorama nacional.
    'C_fallo_como_2023': {'PP': 30.3, 'PSOE': 29.9, 'VOX': 18.4, 'FA': 6.7, 'POD': 2.9, 'SALF': 1.5},
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
json.dump({'datos_a': DATOS_A}, open(os.path.join(OUT, 'meta.json'), 'w'))
