# Echar a Sánchez — código y datos

Web de voto táctico para las elecciones generales del 29 de noviembre de 2026. Para cada provincia calcula
qué papeleta (PP, Vox, Junts o UPN) quita más escaños, en esperanza, al bloque que invistió a Sánchez en 2023
(PSOE, Frente Amplio, Podemos, ERC, EH Bildu, PNV, BNG), y qué pasa en el Senado si el voto de la derecha se divide.

La web es `docs/` (tres páginas estáticas, sin cookies ni analítica). Todo lo demás sirve para rehacer las
cuentas y llegar a otra conclusión si los datos la dan.

## Cómo rehacer las cuentas

    python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
    .venv/bin/python model/backtest.py            # prueba con 2019 -> 2023
    .venv/bin/python model/run_2026.py            # escenarios A (media de encuestas privadas), B (CIS), C (fallo como en 2023)
    .venv/bin/python model/explain.py             # recomendación por provincia -> out/provincias.json
    .venv/bin/python model/contrafactual_2023.py  # 2023 con la derecha unida
    .venv/bin/python model/build_report.py        # -> out/informe_modelo_29N.html
    .venv/bin/python model/build_pages.py         # -> out/razones.html, out/quienes.html
    .venv/bin/python model/build_og.py            # -> out/og.png, imagen para redes (necesita Chromium)

## Para actualizar con nuevas encuestas

Editar `SCENARIOS` (media de encuestas privadas, CIS) y `CAT_TARGETS` (Cataluña, calibrado con el CEO) en
`model/run_2026.py`, poner en `DATOS_A` la fecha de corte de esas encuestas (es la que muestra la web) y volver a
ejecutar desde `run_2026.py`. La cuenta atrás hasta el 29-N la calcula la página al abrirse. Hasta el 13 de noviembre, antes de la campaña, la web no pide el voto (art. 53 LOREG): mismos cálculos, con textos que dicen qué papeleta resta más (`out/precampana/`). Desde el 24 de noviembre no se pueden difundir
encuestas (art. 69.7 LOREG): el 23-N a las 21:00 la web se sustituye por un aviso y el repositorio deja de llevar el
modelo, los datos y los resultados durante la veda; el 27-N a las 21:00, al acabar la campaña (art. 53), también se
retiran Razones y Quiénes somos. Las versiones de precampaña y retiradas las genera `model/build_pages.py`.

## Método, en corto

1. Resultados de 2023 por provincia, adaptados a las candidaturas de 2026.
2. Ajuste proporcional (IPF) para que la suma nacional cuadre con cada escenario de encuestas.
3. 4.000 simulaciones con error nacional, autonómico, provincial y de bloque; D'Hondt con barrera del 3%.
4. Valor táctico: cuántos escaños pierde el bloque si un partido gana un punto en la provincia.
   Si la diferencia entre los dos mejores es menor que el error del modelo, se dice que es un empate.

Validación: con las encuestas finales de 2023, el modelo asignó bien 324 de 350 escaños.
Los detalles y los supuestos están en la pestaña Método de la web.

## Archivos

- `data/` — resultados 2019 y 2023 por provincia, mapa, y el expediente de «Razones» con sus fuentes
- `model/` — modelo (`model.py`), escenarios, explicación, generación de las páginas
- `out/` — resultados del modelo en CSV y JSON
- `docs/` — la web publicada

## Fuentes

Resultados por circunscripción: Ministerio del Interior (vía Wikipedia, «Results breakdown of the 2023 /
November 2019 Spanish general election»). Encuestas 2026: archivo de Demócrata; CIS; CEO. Geometría de
provincias: github.com/codeforgermany/click_that_hood.

## Licencia

MIT (archivo `LICENSE`): código, datos y textos se pueden usar, copiar y modificar citando la procedencia.
