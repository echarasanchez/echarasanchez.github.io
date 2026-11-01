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
def redondo(x):
    """Hacia abajo, a una cifra significativa (146.000 -> 100.000; 38.000 -> 30.000): «más de» nunca exagera."""
    m = 10 ** (len(str(int(x))) - 1); return int(x) // m * m
def cota(e, dist):
    """El error redondeado hacia abajo pero sin quedar por debajo de la distancia que se compara con él (63.000 -> 60.000;
    58.000 con 56.500 de distancia -> 58.000 y no 50.000, que parecería contradecir la frase)."""
    for m in (redondo(e), int(e) // 10 ** (len(str(int(e))) - 2) * 10 ** (len(str(int(e))) - 2), int(e) // 1000 * 1000):
        if m >= dist: return m
    return int(e)
NUM = {2: 'dos', 3: 'tres', 4: 'cuatro'}
def lista_y(xs): return xs[0] if len(xs) == 1 else ', '.join(xs[:-1]) + ' y ' + xs[-1]
def miles(x): return f'{x:,}'.replace(',', '.')
def cap(t): return t[0].upper() + t[1:]
def lista(xs): return xs[0] if len(xs) == 1 else ', '.join(xs[:-1]) + ' o ' + xs[-1]
def votos(pts, vpp): return f'{max(int(round(pts * vpp, -2)), 100):,}'.replace(',', '.')


def situacion(shares, seats, vpp, opciones, err={}, prov=''):
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
        dist = {}
        for k in opciones:
            if k == L: continue
            pk, _ = points_to_gain(shares, seats, k, max_pts=MAX)
            # Su próximo escaño está a la altura del que se disputa: cerca en puntos o a menos de lo que pueden fallar las
            # encuestas con él (sin esto, en Barcelona quedaba fuera Vox, a 56.500 votos con un error de ±63.000; 1-nov)
            if pk is not None and (pk <= max(2 * pT, 1.0) or pk * vpp <= err.get(k, 0)):
                fr.append(f'{cap(el(k))} está a unos {votos(pk, vpp)} votos de ese escaño (sería su {ordn(n(k) + 1)}).')
                defs.append((k, n(k) + 1)); dist[k] = pk
        amenaza = f'{cap(el(B))} está a unos {votos(pT, vpp)} votos de quitarle {al(L)} su {ordadj(n(L))} escaño.'
        if len(defs) == 1:
            fr.append(f'Cada voto {al(defs[0][0])} lo defiende.')
            c = (f'Cada voto {al(L)} defiende su {ordadj(n(L))} escaño: {el(B)} está a unos {votos(pT, vpp)} votos de quitárselo.'
                 if defs[0][0] == L else f'{amenaza} Cada voto {al(defs[0][0])} lo defiende.')
        elif len({d for _, d in defs}) == 1:
            todos = 'los dos' if len(defs) == 2 else 'todos'
            fr.append(f'Cada voto {lista([al(k) for k, _ in defs])} lo defiende: {todos} pelean su {ordadj(defs[0][1])} escaño.')
            c = f'{amenaza} Cada voto {lista([al(k) for k, _ in defs])} lo defiende igual: {todos} pelean su {ordadj(defs[0][1])} escaño.'
        elif (len(defs) >= 3 and defs[0][0] == L and L in opciones and err.get(L)
              and all(k in opciones and dist[k] * vpp <= err.get(k, 0) for k, _ in defs[1:])):
            # Empate a tres (Barcelona): como el de dos, pero con el error de cada uno, porque son distintos (Junts ±38.000,
            # Vox ±63.000) y uno solo «por partido» quedaría por debajo de alguna distancia
            ks = sorted((k for k, _ in defs[1:]), key=lambda k: dist[k])
            dd = [f'{el(k)} a unos {votos(dist[k], vpp)}' for k in ks]
            ee = [f'{miles(cota(err[k], dist[k] * vpp))} {al(k)}' for k in ks]
            nn = NUM[len(defs)]
            t = (f'Con la media de encuestas, el escaño en juego es {de(L)}: {el(B)} está a unos {votos(pT, vpp)} votos de '
                 f'quitárselo, {lista_y([dd[0] + " de pelearlo"] + dd[1:])}. '
                 f'Pero en {prov} las encuestas pueden fallar en más de {lista_y([ee[0].replace(" ", " votos ", 1)] + ee[1:])}, '
                 f'así que el escaño que se decide puede ser de cualquiera de los {nn}. '
                 f'Por eso aquí {lista_y([el(k) for k, _ in defs])} restan lo mismo.')
            fr[:] = [t]
            c = (f'En {prov} las encuestas pueden fallar en más de {lista_y([ee[0].replace(" ", " votos ", 1)] + ee[1:])}: el '
                 f'escaño en juego puede ser {lista([de(k) for k, _ in defs])}, y los {nn} restan lo mismo.')
        elif len(defs) == 2 and defs[0][0] == L:
            # Dos partidos de la derecha pueden defender el escaño: L, que hoy lo pelea, y k, a dist[k] de pelearlo él.
            # No comparar solo «1/9 frente a 1/16» (confunde: parece contradecir las distancias, decisión del 1-nov).
            (_, dL), (k, dk) = defs
            del fr[1:]                                              # la distancia de k va en la frase de abajo
            vk = votos(dist[k], vpp)
            e = min(err.get(L, 0), err.get(k, 0))                   # lo que pueden fallar las encuestas (90%), el menor
            if k in opciones and L in opciones and e and dist[k] * vpp <= e:
                # Empate: la distancia es menor que el error, así que el escaño que se decide puede ser de cualquiera
                t = (f'Con la media de encuestas, el escaño en juego es {de(L)}: {el(B)} está a unos {votos(pT, vpp)} votos '
                     f'de quitárselo, y {el(k)} a unos {vk} de pelearlo{" él" if k != "JUNTS" else ""}. Pero en {prov} las '
                     f'encuestas pueden fallar en más de {miles(cota(e, dist[k] * vpp))} votos por partido, así que el escaño que se decide '
                     f'puede ser de cualquiera de los dos. Por eso aquí {el(L)} y {el(k)} restan lo mismo.')
                fr[:] = [t]
                # Versión corta = la frase de la imagen para compartir (build_social toma la primera frase): un solo resumen
                c = (f'En {prov} las encuestas pueden fallar en más de {miles(cota(e, dist[k] * vpp))} votos por partido: el escaño en juego '
                     f'puede ser {de(L)} o {de(k)}, y los dos restan lo mismo.')
            elif k in opciones and dk < dL:
                # Solo k (o k por delante): pesa más porque pelea un escaño de número más bajo; es la idea de D'Hondt de la web
                fr.append(f'{cap(el(k))} está a unos {vk} votos de pelearlo él (sería su {ordn(dk)}): cada voto {al(k)} cuenta '
                          f'{peso(dk)}, porque pelea su {ordadj(dk)} escaño; {al(L)}, {peso(dL)}, porque pelea el {ordn(dL)}.')
                c = (f'{amenaza} {cap(el(k))} está a unos {vk} votos de pelearlo él, y entonces cada voto suyo cuenta {peso(dk)} '
                     f'(pelea su {ordadj(dk)} escaño); {al(L)}, {peso(dL)} (pelea el {ordn(dL)}).')
            else:
                fr.append(f'Cada voto {al(L)} lo defiende directamente. {cap(el(k))} está a unos {vk} votos de pelearlo él '
                          f'(sería su {ordn(dk)}).')
                c = f'{amenaza} Cada voto {al(L)} lo defiende directamente.'
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


def explicar(opciones, sh_a, sh_c, seats, vpp_a, vpp_c, rep_cis, impacto, err_a={}, err_c={}, prov=''):
    """Texto de «La aritmética» (HTML sencillo): (versión corta, versión completa).
    opciones: partidos recomendados ([] si es indiferente)."""
    fa, ha, ca = situacion(sh_a, seats, vpp_a, opciones, err_a, prov)
    texto, corto = ' '.join(fa), [c for _, c in ca]
    if opciones and not corto:      # la media de privadas no explica ninguna opción: decirlo antes de ir al CIS
        corto = [f'Con la media de encuestas no hay un escaño cerca para {lista([el(k) for k in opciones])}.']
    falta = [k for k in opciones if k not in ha]
    if falta:
        fc, hc, cc = situacion(sh_c, seats, vpp_c, opciones, err_c, prov)
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
