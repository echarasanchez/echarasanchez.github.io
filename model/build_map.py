"""Convierte el GeoJSON de provincias en trazados SVG ligeros (Canarias en recuadro).
Fuente: click_that_hood/spain-provinces.geojson (codeforgermany, GitHub)."""
import json, math, sys, os
from shapely.geometry import shape, Polygon, MultiPolygon

SRC = sys.argv[1]
OUT = os.path.join(os.path.dirname(__file__), '..', 'data', 'mapa_provincias.json')
RENAME = {'Illes Balears': 'Baleares', 'Santa Cruz De Tenerife': 'Santa Cruz de Tenerife', 'Araba/Álava': 'Álava',
          'Alacant/Alicante': 'Alicante', 'Castelló/Castellón': 'Castellón', 'Gipuzkoa/Guipúzcoa': 'Gipuzkoa',
          'València/Valencia': 'Valencia', 'Bizkaia/Vizcaya': 'Bizkaia'}
K = 100.0; C = math.cos(math.radians(40))
LON0, LAT0 = -9.5, 43.9
# Canarias: desplazadas al recuadro inferior izquierdo
CAN_DX, CAN_DY = 9.0, 6.0   # grados que se suman a lon / lat

def proj(lon, lat, can=False):
    if can: lon, lat = lon + CAN_DX, lat + CAN_DY
    return ((lon - LON0) * C * K, (LAT0 - lat) * K)

def ring_d(coords, can):
    pts = [proj(x, y, can) for x, y in coords]
    return 'M' + 'L'.join(f'{x:.1f},{y:.1f}' for x, y in pts) + 'Z'

g = json.load(open(SRC))
out = {}
minx = miny = 1e9; maxx = maxy = -1e9
for f in g['features']:
    name = RENAME.get(f['properties']['name'], f['properties']['name'])
    can = name in ('Las Palmas', 'Santa Cruz de Tenerife')
    geom = shape(f['geometry'])
    polys = list(geom.geoms) if isinstance(geom, MultiPolygon) else [geom]
    tiny = name in ('Ceuta', 'Melilla')
    parts = []
    for p in polys:
        if not tiny and p.area < 0.0015: continue
        s = p.simplify(0.002 if tiny else 0.012, preserve_topology=True)
        if s.is_empty: continue
        parts.append(ring_d(s.exterior.coords, can))
        for x, y in s.exterior.coords:
            X, Y = proj(x, y, can); minx, maxx = min(minx, X), max(maxx, X); miny, maxy = min(miny, Y), max(maxy, Y)
    c = geom.representative_point()
    cx, cy = proj(c.x, c.y, can)
    out[name] = {'d': ''.join(parts), 'cx': round(cx, 1), 'cy': round(cy, 1)}
box = proj(-18.4, 29.6, True)  # esquina sup-izq del recuadro de Canarias
box2 = proj(-13.2, 27.5, True)
json.dump({'provs': out, 'bbox': [round(minx), round(miny), round(maxx), round(maxy)],
           'canbox': [round(box[0]), round(box[1]), round(box2[0]), round(box2[1])]}, open(OUT, 'w'), ensure_ascii=False)
print(len(out), 'bbox', minx, miny, maxx, maxy, 'canbox', box, box2, 'bytes', os.path.getsize(OUT))
