"""Backtest: base nov-2019 + media de encuestas finales de 2023 -> escaños 2023 por provincia."""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from model import *

d = load_2023()
w = d.pop_k * VALID_PER_POP * np.where(d.ccaa == 'CAT', 0.88, 1.0)

r = pd.read_csv(os.path.join(DATA, 'congreso_2019nov_raw.csv')).replace('−', 0).set_index('constituency')
r = r.apply(pd.to_numeric, errors='coerce').fillna(0)
r.loc['Teruel', ['PRC_pct', 'PRC_seats', 'TE_pct', 'TE_seats']] = [0, 0, 26.7, 1]
r = r.reindex(d.index)

B = pd.DataFrame(0.0, index=d.index, columns=PARTIES)
B['PP'] = r.PP_pct + 0.60 * r.Cs_pct + 0.5 * r.PRC_pct + 0.45 * r.NA_pct
B['PSOE'] = r.PSOE_pct + 0.15 * r.Cs_pct + 0.4 * r.PRC_pct
B['VOX'] = r.Vox_pct + 0.10 * r.Cs_pct
B['FA'] = r.UP_pct + r.MP_pct            # Sumar 2023 = UP + Más País/Compromís
B['ERC'] = r.ERC_pct; B['JUNTS'] = r.Junts_pct; B['BILDU'] = r.Bildu_pct
B['PNV'] = r.PNV_pct; B['BNG'] = r.BNG_pct; B['CC'] = r.CC_pct; B['UPN'] = 0.50 * r.NA_pct
B['OTH'] = (100 - B[PARTIES[:-1]].sum(axis=1)).clip(lower=1.0)

# media de la última encuesta de cada empresa (fin de campo 15-17 jul 2023, Wikipedia)
polls23 = {'PP': 34.4, 'PSOE': 28.3, 'VOX': 13.0, 'FA': 13.1, 'ERC': 2.2, 'JUNTS': 1.9,
           'BILDU': 1.3, 'PNV': 1.3, 'BNG': 0.8, 'CC': 0.35, 'UPN': 0.2}
result23 = {'PP': 33.1, 'PSOE': 31.7, 'VOX': 12.4, 'FA': 12.3, 'ERC': 1.9, 'JUNTS': 1.6,
            'BILDU': 1.4, 'PNV': 1.1, 'BNG': 0.6, 'CC': 0.5, 'UPN': 0.2}

real = pd.DataFrame(0, index=d.index, columns=PARTIES)
for k, c in [('PP', 's_PP'), ('PSOE', 's_PSOE'), ('VOX', 's_VOX'), ('FA', 's_SUMAR'), ('ERC', 's_ERC'),
             ('JUNTS', 's_JUNTS'), ('BILDU', 's_BILDU'), ('PNV', 's_PNV'), ('BNG', 's_BNG'), ('CC', 's_CC'), ('UPN', 's_UPN')]:
    real[k] = d[c]

def run(targets, label):
    S = fit_scenario(B, w, targets)
    point = pd.DataFrame([dhondt(S.loc[p, PARTIES].values.astype(float).copy(), int(d.loc[p, 'seats23'])) for p in d.index],
                         index=d.index, columns=PARTIES)
    X = simulate(S, d, 'seats23', n=3000)
    sims = seats_all(X, d, 'seats23')
    exp = pd.DataFrame(sims.mean(0), index=d.index, columns=PARTIES)
    err = (point - real).abs().sum(axis=1) / 2   # escaños mal asignados por provincia
    # ¿el bloque S real cae dentro del intervalo 90% simulado?
    bS = bloc_seats(sims.sum(axis=1)); realS = real[[k for k in BLOC_S]].sum().sum()
    # calibración: para cada provincia y partido, P(sim == real)
    hit = np.mean([(sims[:, j, PARTIES.index(k)] == real.iloc[j][k]).mean()
                   for j in range(len(d)) for k in ['PP', 'PSOE', 'VOX', 'FA']])
    print(f'\n=== {label} ===')
    print('Escaños nacionales (estimación puntual):', {k: int(point[k].sum()) for k in PARTIES if point[k].sum()})
    print('Escaños reales 2023:                    ', {k: int(real[k].sum()) for k in PARTIES if real[k].sum()})
    print(f'Escaños mal asignados: {int(err.sum())} de 350 ; provincias exactas: {(err == 0).sum()}/52')
    print(f'Bloque investidura real={realS}  simulado: media {bS.mean():.1f}, IC90% [{np.percentile(bS,5):.0f}, {np.percentile(bS,95):.0f}]')
    print(f'P media de acertar el nº exacto de escaños de PP/PSOE/Vox/Sumar por provincia: {hit:.2f}')
    print('Provincias con error:', {p: int(e) for p, e in err.items() if e > 0})
    return point, sims

run(polls23, 'Backtest con encuestas finales 2023')
run(result23, 'Backtest con el resultado nacional real (aisla el error del modelo provincial)')
