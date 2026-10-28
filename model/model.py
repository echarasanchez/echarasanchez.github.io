"""
echaasanchez.es — modelo de voto táctico por circunscripción (Congreso + Senado).

Objetivo: minimizar los escaños del bloque que invistió a Sánchez en 2023
(PSOE, Sumar/Frente Amplio, Podemos, ERC, Bildu, PNV, BNG).
Junts, PP, Vox, UPN, SALF cuentan como "fuera del bloque". CC se trata como neutral.

Método:
 1. Base: resultado 2023 por provincia (o 2019 para el backtest), mapeado a las listas de 2026.
 2. Escenario: media de encuestas nacionales (+ CEO para Cataluña), aplicada con swing
    proporcional y ajuste iterativo (IPF) para que el agregado nacional cuadre con la encuesta.
 3. Monte Carlo: error nacional + autonómico + provincial por partido (log-normal) y un
    componente de bloque correlacionado. D'Hondt con barrera del 3%.
 4. Valor táctico: para cada partido elegible, cuántos escaños pierde en esperanza el bloque
    de Sánchez si ese partido recibe un 1% adicional del voto válido de la provincia.
"""
import numpy as np, pandas as pd, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, '..', 'data')

BLOC_S = ['PSOE', 'FA', 'POD', 'ERC', 'BILDU', 'PNV', 'BNG']      # bloque investidura 2023
NON_S  = ['PP', 'VOX', 'JUNTS', 'UPN', 'SALF', 'CC']
PARTIES = ['PP', 'PSOE', 'VOX', 'FA', 'POD', 'ERC', 'JUNTS', 'BILDU', 'PNV', 'BNG', 'CC', 'UPN', 'SALF', 'OTH']
CANDIDATES = ['PP', 'VOX', 'JUNTS', 'UPN', 'SALF']   # opciones que puede recomendar la web
SALF_NO_VA = ['Cantabria', 'Ciudad Real', 'Gipuzkoa', 'Girona', 'Lleida']   # Congreso: se presenta en 47 (The Objective, 27-oct-2026)
REGIONAL = ['ERC', 'JUNTS', 'BILDU', 'PNV', 'BNG', 'CC', 'UPN']
VALID_PER_POP = 0.51   # votos válidos ≈ 0,51 × población (calibrado con Madrid y total nacional 2023)

# ---------------------------------------------------------------- D'Hondt
def dhondt(shares, seats, threshold=3.0):
    """shares: array (n_parties,) en % del voto válido. Devuelve escaños por partido."""
    s = np.where(shares >= threshold, shares, 0.0)
    s[PARTIES.index('OTH')] = 0.0          # 'otros' es un agregado, no una lista
    out = np.zeros(len(s), dtype=int)
    for _ in range(seats):
        q = s / (out + 1)
        out[np.argmax(q)] += 1
    return out

def dhondt_batch(S, seats, threshold=3.0):
    """S: (n_sims, n_parties). Vectorizado."""
    n, k = S.shape
    s = np.where(S >= threshold, S, 0.0)
    s[:, PARTIES.index('OTH')] = 0.0
    out = np.zeros((n, k), dtype=int)
    idx = np.arange(n)
    for _ in range(seats):
        q = s / (out + 1)
        out[idx, q.argmax(1)] += 1
    return out

# ---------------------------------------------------------------- bases
def load_2023():
    d = pd.read_csv(os.path.join(DATA, 'congreso_2023.csv')).set_index('prov')
    return d

def base_2026(d):
    """Mapea 2023 -> listas 2026. Devuelve DataFrame prov x PARTIES (en %)."""
    B = pd.DataFrame(0.0, index=d.index, columns=PARTIES)
    for c in ['PP', 'PSOE', 'VOX', 'ERC', 'JUNTS', 'BILDU', 'PNV', 'BNG', 'CC', 'UPN']:
        B[c] = d[c]
    left = d['SUMAR'].astype(float)
    for p in d.index:
        cc = d.loc[p, 'ccaa']
        L = left[p]
        if cc == 'CAT':            # Comuns (FA) separados; Podemos dentro de ERC
            B.loc[p, 'FA'] = 0.75 * L; B.loc[p, 'ERC'] += 0.25 * L
        elif cc == 'CV':           # Compromís-Front Valencià: lista unitaria con Podemos
            B.loc[p, 'FA'] = L
        elif cc == 'CAN':          # Unidad del Pueblo Canario (Podemos+IU+Sumar+NC)
            B.loc[p, 'FA'] = L + d.loc[p, 'NC']
        elif cc in ('AND', 'ARA'): # Podemos no se presenta; la mitad de su voto va a FA
            B.loc[p, 'FA'] = 0.70 * L + 0.15 * L
        else:                      # listas separadas
            B.loc[p, 'FA'] = 0.70 * L; B.loc[p, 'POD'] = 0.30 * L
    # Vox no se presentó en S/C de Tenerife en 2023: lo reconstruimos (≈ nivel Las Palmas)
    B.loc['Santa Cruz de Tenerife', 'VOX'] = 12.0
    B.loc['Santa Cruz de Tenerife', 'PP'] -= 10.0
    B['SALF'] = 1.0   # partido nuevo: reparto uniforme, se escala a la encuesta
    B.loc[SALF_NO_VA, 'SALF'] = 0.0
    B['OTH'] = (100 - B[PARTIES[:-1]].sum(axis=1)).clip(lower=1.0)
    return B

def fit_scenario(B, w, targets, region_mask=None, region_targets=None, iters=60):
    """IPF: escala columnas para que el agregado nacional (ponderado por w) cuadre con targets.
    region_targets: dict partido->% para las provincias de region_mask (p.ej. Cataluña/CEO)."""
    S = B.copy()
    for _ in range(iters):
        if region_targets is not None:
            Wr = w[region_mask]
            for k, t in region_targets.items():
                cur = (S.loc[region_mask, k] * Wr).sum() / Wr.sum()
                if cur > 0: S.loc[region_mask, k] *= t / cur
        for k, t in targets.items():
            if region_targets is not None and k in region_targets:
                # el objetivo nacional se reparte: resto de España absorbe la diferencia
                Wr = w[region_mask].sum(); Wn = w[~region_mask].sum()
                reg_val = (S.loc[region_mask, k] * w[region_mask]).sum()
                need = (t * w.sum() - reg_val) / Wn
                cur = (S.loc[~region_mask, k] * w[~region_mask]).sum() / Wn
                if cur > 0 and need > 0: S.loc[~region_mask, k] *= need / cur
            else:
                cur = (S[k] * w).sum() / w.sum()
                if cur > 0: S[k] *= t / cur
        named = [c for c in PARTIES if c != 'OTH']
        tot = S[named].sum(axis=1)
        over = tot > 98.5
        S.loc[over, named] = S.loc[over, named].mul(98.5 / tot[over], axis=0)
        S['OTH'] = 100 - S[named].sum(axis=1)
    return S

# ---------------------------------------------------------------- Monte Carlo
def simulate(S, d, seats_col, n=4000, seed=1, sig_nat=0.09, sig_reg=0.07, sig_prov=0.06, sig_bloc=0.04):
    """Devuelve array (n, n_prov, n_parties) de cuotas simuladas."""
    rng = np.random.default_rng(seed)
    P = len(PARTIES); provs = list(S.index)
    ccaas = sorted(d['ccaa'].unique()); ci = {c: i for i, c in enumerate(ccaas)}
    nat = rng.normal(0, sig_nat, (n, P))
    small = np.array([1.6 if k in ('FA', 'POD', 'SALF') else 1.0 for k in PARTIES])
    nat = nat * small
    reg = rng.normal(0, sig_reg, (n, len(ccaas), P))
    prov = rng.normal(0, sig_prov, (n, len(provs), P))
    bloc = rng.normal(0, sig_bloc, (n, 1))
    sign = np.array([1 if k in BLOC_S else (-1 if k in ('PP', 'VOX', 'UPN', 'SALF') else 0) for k in PARTIES])
    base = S[PARTIES].values  # (n_prov, P)
    reg_idx = np.array([ci[d.loc[p, 'ccaa']] for p in provs])
    logf = nat[:, None, :] + reg[:, reg_idx, :] + prov + (bloc * sign)[:, None, :]
    X = base[None, :, :] * np.exp(logf)
    X = X / X.sum(2, keepdims=True) * 100
    return X

def seats_all(X, d, seats_col):
    n, NP, P = X.shape
    out = np.zeros((n, NP, P), dtype=int)
    for j, p in enumerate(d.index):
        out[:, j, :] = dhondt_batch(X[:, j, :], int(d.loc[p, seats_col]))
    return out

def bloc_seats(seat_arr):
    m = np.array([k in BLOC_S for k in PARTIES])
    return seat_arr[..., m].sum(-1)

# ---------------------------------------------------------------- análisis táctico
def tactical(X, d, seats_col, delta=1.0):
    """Para cada provincia y partido candidato: escaños esperados que pierde el bloque S
    si el partido recibe +delta puntos (votos nuevos, p.ej. de abstencionistas o de partidos
    que no obtienen escaño). Usa números aleatorios comunes."""
    rows = []
    for j, p in enumerate(d.index):
        seats = int(d.loc[p, seats_col]); Xp = X[:, j, :]
        base = dhondt_batch(Xp, seats); bs = bloc_seats(base)
        res = {'prov': p, 'seats': seats, 'E_bloc': bs.mean()}
        for k in PARTIES: res['E_' + k] = base[:, PARTIES.index(k)].mean()
        for k in CANDIDATES:
            ki = PARTIES.index(k)
            if np.median(Xp[:, ki]) < 0.3:  # no se presenta en la provincia
                res['v_' + k] = np.nan; continue
            Y = Xp.copy(); Y[:, ki] += delta
            Y = Y / Y.sum(1, keepdims=True) * 100
            res['v_' + k] = bs.mean() - bloc_seats(dhondt_batch(Y, seats)).mean()
        # trasvases dentro del bloque no-S
        for a, b in [('PP', 'VOX'), ('VOX', 'PP'), ('PP', 'JUNTS'), ('VOX', 'JUNTS')]:
            ai, bi = PARTIES.index(a), PARTIES.index(b)
            if np.median(Xp[:, ai]) < 0.3 or np.median(Xp[:, bi]) < 0.3:
                res[f't_{a}_{b}'] = np.nan; continue
            Y = Xp.copy(); mv = np.minimum(delta, Y[:, ai]); Y[:, ai] -= mv; Y[:, bi] += mv
            res[f't_{a}_{b}'] = bs.mean() - bloc_seats(dhondt_batch(Y, seats)).mean()
        rows.append(res)
    return pd.DataFrame(rows).set_index('prov')

def recommend(T, eps=0.02):
    """Recomendación por provincia a partir de los valores v_* (escaños por +1 punto)."""
    recs = []
    for p, r in T.iterrows():
        vals = {k: r['v_' + k] for k in CANDIDATES if not np.isnan(r['v_' + k]) and k != 'SALF'}
        best = max(vals, key=vals.get); vbest = vals[best]
        close = [k for k, v in vals.items() if v >= vbest - max(eps, 0.25 * vbest)]
        if vbest < eps: rec = 'INDIFERENTE (no hay escaño en juego entre bloques)'
        elif len(close) > 1: rec = 'EMPATE: ' + ' / '.join(sorted(close, key=lambda k: -vals[k]))
        else: rec = best
        recs.append((p, best, vbest, rec))
    return pd.DataFrame(recs, columns=['prov', 'best', 'v_best', 'rec']).set_index('prov')

# ---------------------------------------------------------------- Senado
SENADO_PACTO = json.load(open(os.path.join(DATA, 'senado_pacto_2026.json'), encoding='utf-8'))

def senate_seats(lists, s_names):
    """Senado a nivel de candidato: salen los 4 candidatos más votados. lists: {lista: [votos de cada candidato]}
    (arrays por simulación). Devuelve los senadores de las listas de s_names en cada simulación."""
    names = [k for k, cs in lists.items() for _ in cs]
    M = np.vstack([c for cs in lists.values() for c in cs]).T
    M = M + np.arange(M.shape[1]) * -1e-9          # empates dentro de una lista: decide el orden
    top = np.argsort(-M, 1)[:, :4]
    return np.isin(np.array(names), list(s_names))[top].sum(1)

def senate(X, d, left_joint=True, pacto=SENADO_PACTO):
    """Provincias peninsulares (4 senadores, 3 votos por elector): salen los 4 candidatos más votados.
    En 2026 PSOE+Sumar+socios van en listas conjuntas (Senat de Progrés/PSOE+FA). Proxy: votos al Senado ≈ votos
    al Congreso por partido; cada elector marca a los tres candidatos de su lista salvo lo que diga el pacto PP-Vox
    (data/senado_pacto_2026.json):
      sin_vox: los votantes de Vox votan a la lista del PP, que lleva un independiente propuesto por Vox;
      vox_un_candidato: PP con 3 candidatos y Vox con 1; los de Vox marcan al suyo y a dos del PP: a los dos primeros
        (E_senadores_bloqueS) o, una parte, a dos al azar (E_reparto_25: uno de cada cuatro; E_reparto_todos);
      sin_pp: E_si_a_VOX / E_si_a_JUNTS: el voto del PP va a esa lista; E_si_no_vota: en blanco, nulo o abstención
        (en el Senado no cuentan para nada).
    E_antes_pacto: cada partido con sus tres candidatos. E_max_derecha: toda la derecha (PP+Vox) en tres candidatos."""
    S_names = {'IZQ', 'ERC', 'BILDU', 'PNV', 'BNG'}
    rows = []
    for j, p in enumerate(d.index):
        if d.loc[p, 'ccaa'] in ('BAL', 'CAN', 'CEU', 'MEL'): continue
        Xp = X[:, j, :]
        g = lambda k: Xp[:, PARTIES.index(k)]
        L = g('PSOE') + (g('FA') if left_joint else 0)
        P, V = g('PP'), g('VOX')
        base = {'IZQ': [L] * 3}
        for k in ('ERC', 'JUNTS', 'BILDU', 'PNV', 'BNG', 'UPN'):
            if np.median(g(k)) > 0.3: base[k] = [g(k)] * 3
        E = lambda **ls: senate_seats({**base, **{k: v for k, v in ls.items() if v}}, S_names)
        antes = E(PP=[P] * 3, VOX=[V] * 3)
        r = {'prov': p, 'grupo': 'normal', 'E_antes_pacto': antes.mean()}
        if p in pacto['sin_vox']:
            r['grupo'] = 'sin_vox'; s = E(PP=[P + V] * 3); right = P + V
            smax = s
        elif p in pacto['vox_un_candidato']:
            r['grupo'] = 'vox_un_candidato'
            reparto = lambda f: E(PP=[P + V - f * V / 3] * 2 + [P + 2 * f * V / 3], VOX=[V])
            s = reparto(0); right = P + V
            r['E_reparto_25'] = reparto(0.25).mean(); r['E_reparto_todos'] = reparto(1).mean()
            smax = E(PP=[P + V] * 3)
        elif p in pacto['sin_pp']:
            r['grupo'] = 'sin_pp'
            dest = {'VOX': E(VOX=[V + P] * 3)}
            if 'JUNTS' in base: dest['JUNTS'] = E(VOX=[V] * 3, JUNTS=[g('JUNTS') + P] * 3)
            for k, v in dest.items(): r['E_si_a_' + k] = v.mean()
            r['E_si_no_vota'] = E(VOX=[V] * 3).mean()
            s = dest['VOX']; right = V + P
            smax = min(dest.values(), key=np.mean)
        else:
            s = antes; right = np.maximum(P, V)
            smax = E(PP=[P + V] * 3)
        others = [cs[0] for k, cs in base.items() if k != 'IZQ']
        r['P_izq_1a'] = float((L > np.max(np.vstack([right] + others), 0)).mean())
        r['E_senadores_bloqueS'] = s.mean(); r['E_max_derecha'] = smax.mean()
        r['ganancia_max_derecha'] = r['E_senadores_bloqueS'] - r['E_max_derecha']
        rows.append(r)
    return pd.DataFrame(rows).set_index('prov')

# ---------------------------------------------------------------- aritmética explicable
def points_to_flip(shares, seats, k, max_pts=6.0, step=0.02):
    """Puntos adicionales que necesita el partido k (en la estimación central) para que el bloque S
    pierda un escaño. Devuelve (puntos, partido S que pierde el escaño) o (None, None)."""
    base = dhondt(shares.copy(), seats); bS0 = sum(base[PARTIES.index(x)] for x in BLOC_S)
    ki = PARTIES.index(k)
    for dlt in np.arange(step, max_pts + step, step):
        y = shares.copy(); y[ki] += dlt; y = y / y.sum() * 100
        s = dhondt(y, seats)
        if sum(s[PARTIES.index(x)] for x in BLOC_S) < bS0:
            loser = [x for x in BLOC_S if s[PARTIES.index(x)] < base[PARTIES.index(x)]]
            return round(float(dlt), 2), (loser[0] if loser else None)
    return None, None

def points_to_lose(shares, seats, max_pts=6.0, step=0.02):
    """Puntos que necesitaría el mejor partido del bloque S para arrebatar un escaño al bloque no-S."""
    base = dhondt(shares.copy(), seats); nS0 = sum(base[PARTIES.index(x)] for x in NON_S)
    best = (None, None, None)
    for k in BLOC_S:
        ki = PARTIES.index(k)
        if shares[ki] < 0.3: continue
        for dlt in np.arange(step, max_pts + step, step):
            y = shares.copy(); y[ki] += dlt; y = y / y.sum() * 100
            s = dhondt(y, seats)
            if sum(s[PARTIES.index(x)] for x in NON_S) < nS0:
                loser = [x for x in NON_S if s[PARTIES.index(x)] < base[PARTIES.index(x)]]
                if best[0] is None or dlt < best[0]: best = (round(float(dlt), 2), k, loser[0] if loser else None)
                break
    return best


def points_to_gain(shares, seats, k, max_pts=15.0, tol=0.01):
    """Puntos que necesita el partido k (en la estimación central) para ganar un escaño más, sea a quien sea.
    El escaño que se gana es siempre el último del reparto. Devuelve (puntos, partido que lo pierde) o (None, None)."""
    base = dhondt(shares.copy(), seats); ki = PARTIES.index(k)
    def plus(dlt):
        y = shares.copy(); y[ki] += dlt; return dhondt(y / y.sum() * 100, seats)
    if plus(max_pts)[ki] <= base[ki]: return None, None
    lo, hi = 0.0, max_pts
    while hi - lo > tol:
        mid = (lo + hi) / 2
        if plus(mid)[ki] > base[ki]: hi = mid
        else: lo = mid
    s = plus(hi); losers = [PARTIES[i] for i in range(len(PARTIES)) if s[i] < base[i]]
    return round(hi, 2), (losers[0] if losers else None)
