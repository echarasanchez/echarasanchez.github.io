"""Explicación en palabras de la recomendación de cada provincia («La aritmética» de la web).

Con D'Hondt, quien suma votos solo puede quitar el último escaño del reparto, así que todo se explica con dos
cuentas en la estimación central: cuántos votos le faltan a cada opción para quitarle un escaño al bloque
(ataque) y cuántos le faltan al bloque para quitárselo a la derecha (defensa). En la defensa importa qué escaño
pelea cada partido: un voto a quien pelea su primer escaño cuenta entero; a quien pelea el tercero, un tercio
(por eso en La Rioja defiende más Vox que el PP). Primero con la media de privadas; si alguna opción
recomendada no queda explicada, con el CIS; y si tampoco, se dice que su impacto viene del error de las encuestas.

Hay dos versiones: la corta (una frase por opción recomendada, con el dato decisivo) y la completa («Ver más»:
con la comparación con el otro partido grande de la derecha, el número de escaño de cada uno y el CIS).
"""
from model import PARTIES, BLOC_S, dhondt, points_to_flip, points_to_gain, points_to_lose

NAME = {'PP': 'PP', 'PSOE': 'PSOE', 'VOX': 'Vox', 'FA': 'Frente Amplio', 'POD': 'Podemos', 'ERC': 'ERC',
        'JUNTS': 'Junts', 'BILDU': 'EH Bildu', 'PNV': 'PNV', 'BNG': 'BNG', 'CC': 'CC', 'UPN': 'UPN', 'SALF': 'SALF'}
CON_ART = {'PP', 'PSOE', 'FA', 'BNG', 'PNV'}           # «el PP», «al PSOE», «del BNG»; «Vox», «a ERC», «de Junts»
ORD = ['', 'primero', 'segundo', 'tercero', 'cuarto', 'quinto', 'sexto', 'séptimo', 'octavo', 'noveno', 'décimo']
ORD_ADJ = ['', 'primer', 'segundo', 'tercer'] + ORD[4:]                       # «su primer escaño»
PESO = {1: 'entero', 2: 'la mitad', 3: 'un tercio', 4: 'un cuarto', 5: 'un quinto'}
CERCA = 6.0         # puntos: más allá, no se cuenta como escaño en juego (mismo límite que la cuenta anterior)
MAX = 15.0          # hasta dónde se busca
ALTERNATIVAS = ('PP', 'VOX', 'JUNTS', 'UPN')


def el(k): return f'el {NAME[k]}' if k in CON_ART else NAME[k]
def al(k): return f'al {NAME[k]}' if k in CON_ART else f'a {NAME[k]}'
def de(k): return f'del {NAME[k]}' if k in CON_ART else f'de {NAME[k]}'
def ordn(n): return ORD[n] if n < len(ORD) else f'{n}.º'
def ordadj(n): return ORD_ADJ[n] if n < len(ORD_ADJ) else f'{n}.º'
def peso(d): return PESO.get(d, f'1/{d}')
def cap(t): return t[0].upper() + t[1:]
def lista(xs): return xs[0] if len(xs) == 1 else ', '.join(xs[:-1]) + ' o ' + xs[-1]
def votos(pts, vpp): return f'{max(int(round(pts * vpp, -2)), 100):,}'.replace(',', '.')


def situacion(shares, seats, vpp, opciones):
    """Frases sobre una estimación central y las opciones que quedan explicadas en ellas.
    Devuelve (frases, opciones explicadas, versión corta: [(opciones que explica, frase)])."""
    base = dhondt(shares.copy(), seats)
    n = lambda k: int(base[PARTIES.index(k)])
    sh = lambda k: shares[PARTIES.index(k)]
    # Ataque: las opciones recomendadas y, para comparar, el otro partido grande de la derecha
    cand = list(opciones)
    alt = [k for k in ALTERNATIVAS if k not in cand and sh(k) >= 3]
    if alt: cand.append(alt[0])
    att = sorted((p, k, l) for k in cand for p, l in [points_to_flip(shares, seats, k, max_pts=MAX)] if p is not None)
    # Defensa: el partido del bloque que antes le quitaría un escaño a la derecha
    pT, B, L = points_to_lose(shares, seats, max_pts=MAX)
    frases, hechas = [], set()
    bloques = []
    if att and att[0][0] <= CERCA:
        fr = [f'con unos {votos(p, vpp)} votos más, {el(k)} le quitaría {al(l)} su {ordadj(n(l))} escaño (sería el {ordn(n(k) + 1)} {de(k)})'
              for p, k, l in att]
        corto = {k: f'Con unos {votos(p, vpp)} votos más, {el(k)} le quitaría {al(l)} su {ordadj(n(l))} escaño.'
                 for p, k, l in att if p <= CERCA and k in opciones}
        bloques.append((att[0][0], ' '.join(cap(f) + '.' for f in fr), {k for p, k, l in att if p <= CERCA}, corto))
    if pT is not None and pT <= CERCA:
        fr = [f'{cap(el(B))} está a unos {votos(pT, vpp)} votos de quitarle {al(L)} su {ordadj(n(L))} escaño (sería el {ordn(n(B) + 1)} {de(B)}).']
        defs = [(L, n(L))] if L in ALTERNATIVAS else []
        for k in opciones:
            if k == L: continue
            pk, _ = points_to_gain(shares, seats, k, max_pts=MAX)
            if pk is not None and pk <= max(2 * pT, 1.0):     # su próximo escaño está a la altura del que se disputa
                fr.append(f'{cap(el(k))} está a unos {votos(pk, vpp)} votos de ese escaño (sería su {ordn(n(k) + 1)}).')
                defs.append((k, n(k) + 1))
        amenaza = f'{cap(el(B))} está a unos {votos(pT, vpp)} votos de quitarle {al(L)} su {ordadj(n(L))} escaño.'
        if len(defs) == 1:
            fr.append(f'Cada voto {al(defs[0][0])} lo defiende.')
            c = (f'Cada voto {al(L)} defiende su {ordadj(n(L))} escaño: {el(B)} está a unos {votos(pT, vpp)} votos de quitárselo.'
                 if defs[0][0] == L else f'{amenaza} Cada voto {al(defs[0][0])} lo defiende.')
        elif len({d for _, d in defs}) == 1:
            todos = 'los dos' if len(defs) == 2 else 'todos'
            fr.append(f'Cada voto {lista([al(k) for k, _ in defs])} lo defiende: {todos} pelean su {ordadj(defs[0][1])} escaño.')
            c = f'{amenaza} Cada voto {lista([al(k) for k, _ in defs])} lo defiende igual: {todos} pelean su {ordadj(defs[0][1])} escaño.'
        elif defs:
            defs.sort(key=lambda x: x[1])
            (k0, d0), resto = defs[0], defs[1:]
            fr.append(f'Para que no se lo lleve {el(B)}, cada voto {al(k0)} cuenta {peso(d0)}, porque pelea su {ordadj(d0)} escaño; '
                      + '; '.join(f'{al(k)}, {peso(d)}, porque pelea el {ordn(d)}' for k, d in resto) + '.')
            c = (f'{amenaza} Para impedirlo, cada voto {al(k0)} cuenta {peso(d0)} (pelea su {ordadj(d0)} escaño); '
                 + '; '.join(f'{al(k)}, {peso(d)} (pelea el {ordn(d)})' for k, d in resto) + '.')
        else:
            c = amenaza
        bloques.append((pT, ' '.join(fr), {k for k, _ in defs}, {k: c for k, _ in defs} or {None: c}))
    if not bloques:
        if pT is not None and (not att or pT <= att[0][0]):
            frases.append(f'Ningún escaño está cerca de cambiar de bloque: {al(B)} le harían falta unos {votos(pT, vpp)} votos más '
                          f'para quitarle un escaño {al(L)}.')
        elif att:
            p, k, l = att[0]
            frases.append(f'Ningún escaño está cerca de cambiar de bloque: {el(k)} necesitaría unos {votos(p, vpp)} votos más '
                          f'para quitarle un escaño {al(l)}.')
        else:
            frases.append('Ningún escaño está cerca de cambiar de bloque.')
    cortos = [(set(), f) for f in frases]
    # El más cercano primero; el otro solo si no está mucho más lejos o si explica alguna opción más
    bloques.sort(key=lambda b: b[0])
    for i, (p, t, ks, corto) in enumerate(bloques):
        if i == 0 or p <= 3 * bloques[0][0] + 1 or ks - hechas:
            frases.append(t)
            # En la versión corta, cada opción se explica una sola vez (una frase puede explicar varias)
            for c in dict.fromkeys(c for k, c in corto.items() if k is None or k not in hechas):
                cortos.append(({k for k, x in corto.items() if x == c and k is not None}, c))
            hechas |= ks
    return frases, hechas, cortos


def explicar(opciones, sh_a, sh_c, seats, vpp_a, vpp_c, rep_cis, impacto):
    """Texto de «La aritmética» (HTML sencillo): (versión corta, versión completa).
    opciones: partidos recomendados ([] si es indiferente)."""
    fa, ha, ca = situacion(sh_a, seats, vpp_a, opciones)
    texto, corto = ' '.join(fa), [c for _, c in ca]
    if opciones and not corto:      # la media de privadas no explica ninguna opción: decirlo antes de ir al CIS
        corto = [f'Con la media de encuestas no hay un escaño cerca para {lista([el(k) for k in opciones])}.']
    falta = [k for k in opciones if k not in ha]
    if falta:
        fc, hc, cc = situacion(sh_c, seats, vpp_c, opciones)
        if any(k in hc for k in falta) and fc != fa:       # en Cataluña los dos escenarios coinciden
            t = ' '.join(fc)
            texto += f' <b>Si acierta el CIS</b> ({rep_cis}): {t[0].lower()}{t[1:]}'
            corto += [f'<b>Si acierta el CIS</b>, {c[0].lower()}{c[1:]}' for ks, c in cc if ks & set(falta)]
            falta = [k for k in falta if k not in hc]
    if falta:
        if len(opciones) == 1:
            fin = (' Tampoco con el CIS' if texto.startswith('Ningún') else ' Ni con la media de encuestas ni con el CIS hay un escaño cerca') \
                  + f': el impacto ({impacto}%) viene de los casos en que las encuestas fallan.'
        else:
            fin = (f' Para {lista([NAME[k] for k in falta])} no hay un escaño cerca ni con la media de encuestas ni con el CIS: '
                   f'su impacto viene de los casos en que las encuestas fallan.')
        texto += fin
        corto.append(fin.strip())
    return ' '.join(corto), texto
