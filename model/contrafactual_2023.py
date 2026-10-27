"""¿Cuántos escaños costó en 2023 la división del voto de la derecha?

Con los porcentajes reales del 23J por provincia (data/congreso_2023.csv) y D'Hondt con barrera del 3%:
en cada provincia se mueve una fracción f de los votantes de un partido de la derecha al otro (de Vox a PP o
de PP a Vox, lo que más escaños quite al bloque de investidura) y se repite el reparto. Es lo que habría
hecho un votante táctico siguiendo una recomendación como la de esta web.
Salida: out/contrafactual_2023.json
"""
import json, os
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
d = pd.read_csv(os.path.join(HERE, '..', 'data', 'congreso_2023.csv')).set_index('prov')
P = ['PP', 'PSOE', 'VOX', 'SUMAR', 'ERC', 'JUNTS', 'BILDU', 'PNV', 'BNG', 'CC', 'UPN', 'NC']
BLOC = ['PSOE', 'SUMAR', 'ERC', 'BILDU', 'PNV', 'BNG']          # bloque que invistió a Sánchez (Sumar incluía Podemos)
RIGHT = ['PP', 'VOX', 'UPN']


def seats(shares, n, threshold=3.0):
    """D'Hondt con barrera del 3% (la de model.dhondt, aquí sobre las listas de 2023)."""
    v = np.array([shares[k] if shares[k] >= threshold else 0.0 for k in P], dtype=float)
    won = np.zeros(len(P), dtype=int)
    for _ in range(int(n)):
        won[np.argmax(v / (won + 1))] += 1
    return dict(zip(P, won.tolist()))


def bloc(s): return sum(s[k] for k in BLOC)
def right(s): return sum(s[k] for k in RIGHT)


# Comprobación: los porcentajes reales reproducen los escaños reales
base = {p: seats(d.loc[p, P], d.loc[p, 'seats23']) for p in d.index}
real = {p: {k: int(d.loc[p, 's_' + k]) for k in P if 's_' + k in d.columns} for p in d.index}
mism = [p for p in d.index if any(base[p][k] != real[p].get(k, 0) for k in P)]
assert not mism, f'el reparto no reproduce 2023 en {mism}'

out = {'real': {'bloque': sum(bloc(base[p]) for p in d.index), 'PP_Vox_UPN': sum(right(base[p]) for p in d.index)},
       'escenarios': []}
for f in (0.05, 0.10, 0.20, 1.0):
    tot_b, tot_r, cambios = 0, 0, []
    for p in d.index:
        sh = d.loc[p, P].astype(float)
        best = base[p]
        for src, dst in (('VOX', 'PP'), ('PP', 'VOX')):
            if sh[src] == 0:
                continue
            s2 = sh.copy(); mv = sh[src] * f; s2[src] -= mv; s2[dst] += mv
            st = seats(s2, d.loc[p, 'seats23'])
            if bloc(st) < bloc(best):
                best, how = st, f'{src}->{dst}'
        if bloc(best) < bloc(base[p]):
            perdido = [k for k in BLOC if best[k] < base[p][k]]
            ganado = [k for k in RIGHT if best[k] > base[p][k]]
            cambios.append({'provincia': p, 'movimiento': how, 'pierde': perdido, 'gana': ganado})
        tot_b += bloc(best); tot_r += right(best)
    out['escenarios'].append({'fraccion': f, 'bloque': tot_b, 'PP_Vox_UPN': tot_r, 'provincias': cambios})

json.dump(out, open(os.path.join(HERE, '..', 'out', 'contrafactual_2023.json'), 'w'), ensure_ascii=False, indent=1)
print('real: bloque', out['real']['bloque'], '| PP+Vox+UPN', out['real']['PP_Vox_UPN'])
for e in out['escenarios']:
    print(f"f={e['fraccion']:.0%}: bloque {e['bloque']} | PP+Vox+UPN {e['PP_Vox_UPN']} | {len(e['provincias'])} provincias: "
          + ', '.join(f"{c['provincia']} ({c['movimiento']}: {'/'.join(c['pierde'])}->{'/'.join(c['gana'])})" for c in e['provincias']))
