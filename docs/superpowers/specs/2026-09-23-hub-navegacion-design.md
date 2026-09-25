# Sub-proyecto 1 — Hub de carrera por columnas + copa automática

**Fecha:** 2026-09-23 · **Base:** v2.3.8 (working tree sin commit) · **Serie:** 1 de 6
(2 Mentalidad en partido · 3 Dirección de equipo · 4 Negociaciones · 5 Oficina + Objetivos ·
6 Finanzas + contratos)

## Objetivo

Reemplazar la barra de 11 botones de `league_screen` por pocas columnas (pestañas) que agrupan
las pantallas existentes, y quitar el botón COPA: el partido de copa se juega desde JUGAR cuando
toca. No se agregan sistemas nuevos de juego; se reorganiza la navegación y se pule Inicio.

## Lo que pidió Diego

- Columnas: **INICIO · DIRECCIÓN · NEGOCIACIONES · OFICINA · OPCIONES · GUARDAR**
  (FINANZAS llega en el sub-proyecto 6).
- Columnas con varias opciones → tarjetas grandes en el área principal (estilo FIFA/PES).
  OPCIONES y GUARDAR abren su pantalla directo.
- Sin apartado Copa: JUGAR lanza el partido de copa cuando esté pendiente. Las tablas de copa se
  ven en OFICINA.
- Extras aceptados: panel único de resultados de jornada, alertas antes de jugar, próximo partido
  de copa visible en Inicio, GUARDAR sin salir.

## Diseño

### 1. Barra y pestañas (`ui/league_screen.py`)

- `BARRA_MENU` pasa a 6 columnas: `inicio`, `direccion`, `negociaciones`, `oficina`,
  `opciones`, `guardar`.
- Pestaña activa en `estado['hub_tab']` (default `'inicio'`). Al volver de cualquier sub-pantalla
  a `league_screen` se muestra la misma pestaña.
- Tarjetas por pestaña (tabla `TARJETAS = {tab: [(clave, título, subtítulo, destino)]}`):

  | Pestaña | Tarjeta | Destino |
  |---|---|---|
  | DIRECCIÓN | Formación | `team_screen` (`team_contexto='carrera'`) |
  | NEGOCIACIONES | Negociar | `market_screen` |
  | NEGOCIACIONES | Ofertas (badge rojo con nº pendientes) | `ofertas_screen` |
  | OFICINA | Estadísticas | `stats_screen` |
  | OFICINA | Copa internacional | `copa_screen` |
  | OFICINA | Historial de carrera | `career_screen` |
  | OFICINA | Otras ligas | `otras_ligas_screen` |

  Las tarjetas de sub-proyectos futuros (Plantilla, Historial de pases, Ojeador, Objetivos) **no**
  se muestran hasta que existan.
- OPCIONES → `options_screen` (`options_return='league_screen'`).
  GUARDAR → `save_slots_screen` (`save_slots_return='league_screen'`).
- Si la pestaña DIRECCIÓN tiene una sola tarjeta igual se muestra la tarjeta (en el sub 3 se suma
  Plantilla); no se salta directo a la formación.

### 2. Teclado

- ←/→: cambia de pestaña (sin entrar a OPCIONES/GUARDAR; se entra con Enter). Excepción: si el
  foco está en el panel de jornada de Inicio, ←/→ cambia de jornada; ↑ devuelve el foco a JUGAR.
- ↑/↓: recorre las tarjetas de la pestaña (en Inicio: JUGAR ↔ panel de jornada).
- Enter/Espacio: abre la tarjeta o columna enfocada.
- Esc: si la pestaña no es Inicio, vuelve a Inicio; en Inicio, vuelve al menú (como hoy).
- Atajos que se mantienen: **J** = JUGAR (desde cualquier pestaña), **R** = abre el panel de
  jornada en Inicio.
- Mientras un overlay esté abierto, teclado y clics son del overlay (patrón actual).

### 3. Inicio

Layout sobre el tablero actual:

- **Botón JUGAR grande** con texto de competición y rival:
  - `COPA · <fase> vs <rival>` si `obtener_partido_copa_pendiente(estado)` devuelve partido.
  - `LIGA · J<n> vs <rival>` si no.
  - `AVANZAR TEMPORADA` si la liga terminó (comportamiento actual).
- **Línea de copa:** si el user está en copa y lo pendiente es liga, se muestra
  `Copa: <fase> vs <rival> · J<jornada límite>` (o `Copa: eliminado en <fase>` / `Copa: campeón`).
  Si el rival de la próxima fase aún no está definido, se muestra solo la fase.
- **Alertas** (lista corta bajo JUGAR, máx. 3 líneas, color rojo/dorado):
  - titulares lesionados (`lesion_partidos > 0`) o sancionados (`partidos_sancion > 0`) en
    `alineacion_activa.titulares` → "Lesionado en tu once: <nombre>";
  - ofertas pendientes (`len(estado['ofertas_recibidas'])`) → "N ofertas sin responder".
  - Solo informativas; no bloquean JUGAR.
- **Panel único de jornada:** reemplaza "OTROS PARTIDOS DE LA FECHA" y el overlay
  `_resumen_jornada`. Muestra todos los resultados de una jornada de la liga del user con < >
  (y ←/→ cuando tiene el foco). Por defecto: la jornada actual si ya tiene partidos jugados; si no,
  la última jugada; en la J1 sin jugar, los cruces de la J1 sin marcador. Se elimina el overlay y
  la clave `estado['league_resumen_j']`; la jornada vista vive en `estado['hub_jornada_vista']`.
- Se mantienen: cabecera (liga, división, temporada, jornada, presupuesto), tabla de posiciones,
  historial de tus partidos con scroll, panel "Tu club".

### 4. Copa automática

- Nueva función `copa_screen.preparar_partido_copa(estado) -> bool`: contiene la lógica que hoy
  está en el clic de JUGAR de `copa_screen` (~líneas 2316-2352: grupos vía
  `partido_copa_dict`; eliminatorias vía `obtener_match_usuario_bracket` +
  `partido_copa_bracket_fase`). Deja listo `estado` para `prepartido_screen` y retorna `False` si
  no pudo resolver el rival (no se navega; se registra el error).
- JUGAR en Inicio: si hay copa pendiente → `preparar_partido_copa`; si retorna `True`,
  `return "prepartido_screen"`. Si no hay copa pendiente → flujo de liga actual.
- Tras el partido de copa, `match_screen` (líneas ~645 y ~1306) y `prepartido_screen`
  (~355 y ~585) vuelven a `league_screen` en vez de `copa_screen`, con `hub_tab='inicio'`.
- `copa_screen` queda de consulta: se quita su botón JUGAR (la rama `jugar_partido_copa` /
  `jugar_copa_*` se reemplaza por la llamada a la función extraída solo desde Inicio). Se mantienen
  pestañas de grupos, bracket, estadísticas y **SIMULAR COPA ENTERA** (modo espectador). VOLVER
  vuelve a la pestaña OFICINA.
- La lógica de *cuándo* toca la copa (`obtener_partido_copa_pendiente`) no se modifica.

### 5. GUARDAR sin salir (`ui/save_slots_screen.py`)

- Al guardar en un slot con éxito: vuelve a `save_slots_return` (Inicio) y deja un aviso
  temporal `estado['hub_toast'] = "Guardado en slot N"` que Inicio muestra ~3 s.
- Se agrega el botón **SALIR AL MENÚ** en esa pantalla (hoy guardar = salir). VOLVER se mantiene.
- Si el guardado falla, el fallback actual sigue igual pero también vuelve con un toast de error
  en vez de ir al menú.

## Fuera de alcance

Plantilla/transferibles (sub 3), buscador/historial/ojeador (sub 4), objetivos de directiva
(sub 5), finanzas y contratos (sub 6); mentalidad en partido (sub 2). No se cambia el aspecto interno de las pantallas
existentes salvo lo indicado (botón JUGAR de copa, destino de VOLVER, save slots).

## Manejo de errores

Se sigue el patrón del proyecto: cada bloque de dibujo en `try/except` con `logger.error` y
fallback visual; si `preparar_partido_copa` falla, JUGAR no navega y se muestra toast
"No se pudo preparar el partido de copa". La pantalla de emergencia de `league_screen` no cambia.

## Pruebas

- Nuevo `tests/test_hub_v240.py` (headless, `SDL_VIDEODRIVER=dummy`):
  1. Clic/teclado en cada pestaña cambia `hub_tab`; Enter en cada tarjeta retorna su destino.
  2. Con copa pendiente, JUGAR retorna `prepartido_screen` con `match_mode='copa'`; sin copa,
     `match_mode='liga'` y `partido_actual` de la jornada.
  3. Tras un partido de copa simulado, la pantalla siguiente es `league_screen`.
  4. `hub_tab` se conserva al ir y volver de `stats_screen`.
  5. Panel de jornada: < > cambia `hub_jornada_vista` dentro de [1, num_jornadas].
  6. Alertas: titular lesionado y ofertas pendientes aparecen en la lista.
  7. Guardar en slot (con `guardar_en_slot` redirigido a carpeta temporal) vuelve a
     `league_screen` y setea `hub_toast`.
- Suite completa de `tests/` sin regresiones (`PYTHONIOENCODING=utf-8`).
- Capturas headless de las 4 pestañas con tarjetas + Inicio con copa pendiente.
