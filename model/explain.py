"""Tabla final: recomendación combinada (70% media privadas / 30% CIS) + aritmética explicable."""
import sys, os, json; sys.path.insert(0, os.path.dirname(__file__))
from model import *
import narrativa
OUT = os.path.join(os.path.dirname(__file__), '..', 'out')
W_A, W_C = 0.7, 0.3
d = load_2023()
A = pd.read_csv(f'{OUT}/tactico_A_media_privadas.csv').set_index('prov')
C = pd.read_csv(f'{OUT}/tactico_B_CIS.csv').set_index('prov')
SA = pd.read_csv(f'{OUT}/senado_A_media_privadas.csv').set_index('prov')
SC = pd.read_csv(f'{OUT}/senado_B_CIS.csv').set_index('prov')
PACTO = SENADO_PACTO
pct = lambda x: f'{x:.1f}'.replace('.', ',') + '%'
def porque_sin_pp(p, dests, best):
    """Por qué el voto del PP resta más en una lista que en otra donde el PP no se presenta (estimación central, media
    de privadas): con listas de tres candidatos, la primera se lleva 3 senadores y la segunda, 1."""
    sh = json.loads(A.loc[p, 'shares'])
    izq = 'PSC y Comuns' if d.loc[p, 'ccaa'] == 'CAT' else 'PSOE y Frente Amplio'
    ls = {'IZQ': sh.get('PSOE', 0) + sh.get('FA', 0), **{k: sh.get(k, 0) for k in ('ERC', 'JUNTS', 'VOX', 'BILDU', 'PNV')}}
    orden = sorted(ls, key=ls.get, reverse=True)
    if orden[0] != 'IZQ' or orden[1] not in BLOC_S: return '', ''
    seg = orden[1]; pp = sh.get('PP', 0)
    t = (f'La izquierda ({izq}) se lleva 3 senadores; el cuarto es para la segunda lista más votada, hoy {narrativa.NAME[seg]} '
         f'({pct(ls[seg])}).')
    corto = 'Con el voto del PP, '
    for i, k in enumerate(sorted(dests, key=lambda k: k != best)):
        n = ls[k] + pp; dif = n - ls[seg]
        res = ('le quitaría ese senador con margen' if dif > 3 else 'se lo quitaría por muy poco' if dif > 0
               else 'se quedaría justo por detrás' if dif > -1.5 else 'se quedaría lejos')
        t += (f' {narrativa.NAME[k]} ({pct(ls[k])}) con el voto del PP ({pct(pp)}) sumaría {pct(n)} y {res}' if i == 0
              else f'; {narrativa.NAME[k]} ({pct(ls[k])}) sumaría {pct(n)} y {res}')
        # Versión corta (a la vista en la ficha, antes de «Ver más»)
        if i == 0: corto += (f'{narrativa.NAME[k]} le quitaría a {narrativa.NAME[seg]} el cuarto senador'
                             + (' con margen' if dif > 3 else ' por muy poco' if dif > 0 else ' en algunos casos'))
        else: corto += f'; {narrativa.NAME[k]} ' + ('también, con margen' if dif > 3 else 'también, pero por muy poco' if dif > 0 else
                       'se quedaría justo por detrás' if dif > -1.5 else 'se quedaría lejos')
    return t + '.', corto + '.'
MARGEN_SEN = 0.03      # senadores (70/30): por debajo, la regla del Senado es «da igual»
mix = lambda col, p: W_A * float(SA.loc[p, col]) + W_C * float(SC.loc[p, col])
def senado(p):
    """Senado en la ficha: grupo del pacto PP-Vox, regla para el votante y senadores esperados del bloque (de 4)."""
    if p not in SA.index:      # islas, Ceuta y Melilla: otro sistema, fuera del modelo
        return {'grupo': 'sin_vox', 'fuera_del_modelo': True} if p in PACTO['sin_vox'] else None
    a, c = SA.loc[p], SC.loc[p]; g = a.grupo
    if g == 'normal': regla = 'mismo_partido'
    elif g == 'sin_vox': regla = 'lista_pp'
    elif g == 'vox_un_candidato':    # ¿ayuda que una parte de los votantes de Vox no marque siempre a los dos primeros del PP?
        dlt = mix('E_reparto_25', p) - mix('E_senadores_bloqueS', p)
        regla = 'repartir' if dlt < -MARGEN_SEN else 'concentrar' if dlt > MARGEN_SEN else 'igual'
    else:
        # Al votante del PP, la lista que más resta al bloque (también Junts: es el enfoque de la web), con el porqué.
        # La referencia es no votar: en blanco, nulo o abstención no cuentan en el Senado.
        dest = {k[7:]: mix(k, p) for k in SA.columns if k.startswith('E_si_a_') and not np.isnan(a[k])}
        best = min(dest, key=dest.get)
        regla = 'a_' + best if mix('E_si_no_vota', p) - dest[best] >= MARGEN_SEN else 'igual'
    r2 = lambda col: [round(float(a[col]), 2), round(float(c[col]), 2)]
    out = {'grupo': g, 'regla': regla, 'a': round(float(a.P_izq_1a), 2), 'c': round(float(c.P_izq_1a), 2),
           'antes': r2('E_antes_pacto'), 'pacto': r2('E_senadores_bloqueS'), 'max': r2('E_max_derecha')}
    if g == 'vox_un_candidato': out['reparto_todos'] = r2('E_reparto_todos')
    if g == 'sin_pp':
        out['dest'] = {k[7:]: r2(k) for k in SA.columns if k.startswith('E_si_a_') and not np.isnan(a[k])}
        out['blanco'] = r2('E_si_no_vota')
        if regla != 'igual': out['porque'], out['porque_corto'] = porque_sin_pp(p, list(out['dest']), regla[2:])
    return out

rows = []
for p in d.index:
    seats = int(d.loc[p, 'seats26']); vpp = float(A.loc[p, 'votos_por_punto'])
    sh = json.loads(A.loc[p, 'shares']); shares = np.array([sh.get(k, 0.0) for k in PARTIES], float)
    shares[PARTIES.index('OTH')] = max(0.0, 100 - shares.sum() + shares[PARTIES.index('OTH')])
    cent = dhondt(shares.copy(), seats)
    vals = {}
    for k in ['PP', 'VOX', 'JUNTS', 'UPN']:
        a, c = A.loc[p, 'v_' + k], C.loc[p, 'v_' + k]
        if not (np.isnan(a) or np.isnan(c)): vals[k] = W_A * a + W_C * c
    best = max(vals, key=vals.get); vb = vals[best]
    second = sorted(vals.values())[-2] if len(vals) > 1 else 0
    if vb < 0.02: rec, nivel = 'Indiferente', 'sin escaño en juego entre bloques'
    elif vb - second < max(0.01, 0.2 * vb): rec, nivel = ' o '.join(k for k in sorted(vals, key=lambda k: -vals[k]) if vals[k] >= vb - max(0.01, 0.2 * vb)), 'empate técnico'
    else: rec, nivel = best, ('clara' if vb - second > 0.5 * vb else 'ligera')
    flip = {k: points_to_flip(shares, seats, k) for k in vals}
    # Estimación central del CIS: la explicación la usa si con la media de privadas alguna opción no queda explicada
    shc = json.loads(C.loc[p, 'shares']); sc = np.array([shc.get(k, 0.0) for k in PARTIES], float)
    sc[PARTIES.index('OTH')] = max(0.0, 100 - sc.sum() + sc[PARTIES.index('OTH')])
    cent_c = dhondt(sc.copy(), seats); vpp_c = float(C.loc[p, 'votos_por_punto'])
    rep_c = ', '.join(f'{narrativa.NAME[PARTIES[i]]} {int(cent_c[i])}' for i in np.argsort(-cent_c, kind='stable') if cent_c[i])
    corto, texto = narrativa.explicar([] if rec == 'Indiferente' else rec.split(' o '), shares, sc, seats, vpp, vpp_c, rep_c, round(vb * 100))
    lose = points_to_lose(shares, seats)
    rows.append({
        'provincia': p, 'escanos': seats, 'recomendacion': rec, 'ventaja': nivel,
        'valor_mezcla': {k: round(v, 3) for k, v in vals.items()},
        'escanos_centrales': {k: int(cent[i]) for i, k in enumerate(PARTIES) if cent[i]},
        'votos_para_quitar_escano_al_bloque': {k: (None if f[0] is None else int(round(f[0] * vpp, -2))) for k, f in flip.items()},
        'escano_que_cambiaria': {k: f[1] for k, f in flip.items()},
        'votos_para_que_el_bloque_gane_uno': None if lose[0] is None else int(round(lose[0] * vpp, -2)),
        'quien_lo_ganaria_y_a_quien': None if lose[0] is None else f'{lose[1]} a {lose[2]}',
        'cis_escanos_centrales': {k: int(cent_c[i]) for i, k in enumerate(PARTIES) if cent_c[i]},
        'explicacion_corta': corto,   # «La aritmética» de la web (model/narrativa.py); la completa, con «Ver más»
        'explicacion': texto,
        'valor_SALF_vs_mejor': None if np.isnan(A.loc[p, 'v_SALF']) else round(float(W_A * A.loc[p, 'v_SALF'] + W_C * C.loc[p, 'v_SALF']), 3),   # None: no se presenta
        'senado': senado(p),        # pacto PP-Vox: data/senado_pacto_2026.json
        'votos_validos_aprox': int(A.loc[p, 'votos_validos_aprox']),
    })
json.dump(rows, open(f'{OUT}/provincias.json', 'w'), ensure_ascii=False, indent=1)
F = pd.DataFrame(rows).set_index('provincia')
F.to_csv(f'{OUT}/recomendaciones_final.csv')
pd.set_option('display.width', 300); pd.set_option('display.max_rows', 60); pd.set_option('display.max_colwidth', 80)
print(F[['escanos', 'recomendacion', 'ventaja', 'escanos_centrales', 'votos_para_quitar_escano_al_bloque', 'escano_que_cambiaria', 'votos_para_que_el_bloque_gane_uno', 'quien_lo_ganaria_y_a_quien']].to_string())
