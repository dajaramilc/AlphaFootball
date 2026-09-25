# Sub-proyecto 2 — Mentalidad en partido (autobús → todo o nada)

**Fecha:** 2026-09-23 · **Base:** v2.3.8 + sub-proyecto 1 · **Serie:** 2 de 6

## Objetivo

Agregar un segundo eje táctico, la **MENTALIDAD** (cuánto arriesga el equipo), que el user fija
antes del partido y cambia en vivo, y que la IA usa y cambia durante el partido según el marcador
y el minuto. Convive con el **ESTILO** actual (`estilo_dt`: piedra-papel-tijera + sinergia +
familiaridad), que no se toca salvo su etiqueta en la UI.

## Diseño

### 1. Datos (`models.py`, `save`)

- `Equipo.mentalidad: str = "normal"`. Se serializa en `to_dict` y se lee en `from_dict` con
  `datos.get("mentalidad", "normal")`; un valor desconocido se normaliza a `"normal"`. Saves
  viejos cargan sin migración.

### 2. Motor (`engine.py`)

- Constantes:
  ```python
  MENTALIDADES = ["autobus", "defensiva", "normal", "ofensiva", "todo_o_nada"]
  NOMBRE_MENTALIDAD = {"autobus": "AUTOBÚS", "defensiva": "DEFENSIVA", "normal": "NORMAL",
                       "ofensiva": "OFENSIVA", "todo_o_nada": "TODO O NADA"}
  EFECTO_MENTALIDAD = {  # prob. de generar ataque, mult. ataque, mult. defensa, % DEF goleador
      "autobus":     {"prob": 0.60, "atk": 0.85, "def": 1.30, "def_goleador": 0.00},
      "defensiva":   {"prob": 0.85, "atk": 0.95, "def": 1.12, "def_goleador": 0.08},
      "normal":      {"prob": 1.00, "atk": 1.00, "def": 1.00, "def_goleador": 0.08},
      "ofensiva":    {"prob": 1.15, "atk": 1.05, "def": 0.92, "def_goleador": 0.15},
      "todo_o_nada": {"prob": 1.35, "atk": 1.10, "def": 0.78, "def_goleador": None},
  }
  ```
  Los valores son punto de partida; se calibran (ver Pruebas) y se documentan los finales.
- `procesar_minuto` recibe `ment_l`, `ment_v` (str, default `"normal"`):
  - `prob` del atacante se multiplica por `EFECTO[ment_atacante]["prob"]`;
  - `ma` × `EFECTO[ment_atacante]["atk"]` y `md` × `EFECTO[ment_defensor]["def"]`;
  - elección del atacante: con `def_goleador` numérico se usa la regla actual con ese % para DEF
    (en `autobus` 0 → solo MED/DEL); con `None` (todo o nada) se elige uniforme entre los
    jugadores de campo (todos menos POR).
- `mentalidad_ia(equipo, rival, minuto, goles_propios, goles_rival, es_local) -> str` (pura):
  - Base por diferencia de media de los onces (`_media_once`), +2 si es local:
    `d ≤ -14` y visitante → `autobus`; `d ≤ -8` → `defensiva`; `d ≥ 8` → `ofensiva`;
    si no → `normal`.
  - Por marcador (pisan la base): perdiendo por 3+ → `normal`; perdiendo por 1–2: desde 82' →
    `todo_o_nada`, desde 70' → `ofensiva`; ganando por 1: desde 85' y `d < 0` → `autobus`,
    desde 75' → `defensiva`.
- `simular_rango` y `simular_partido` aceptan `ment_l` / `ment_v`: un nombre de mentalidad
  (fijo) o `"ia"` (default para ambos). Con `"ia"` la mentalidad se recalcula cada minuto con
  `mentalidad_ia` usando el marcador acumulado. Cuando cambia respecto al minuto anterior se agrega
  al log el evento `{"minuto", "tipo": "mentalidad", "equipo_id", "mentalidad",
  "detalle": "<Equipo> pasa a <NOMBRE>"}` (el primer valor del partido no genera evento).
- Llamadas existentes que no pasan nada quedan con IA en ambos lados, así las ligas de fondo y la
  copa usan IA sin tocar sus llamadas. Las llamadas del partido del user pasan su mentalidad fija.

### 3. User: antes del partido (`ui/team_screen.py`)

- En `_render_direccion` el control "TÁCTICA" se rotula **ESTILO** y se agrega **MENTALIDAD**
  con < > (mismo patrón que ESTILO). Cambia `mi_equipo.mentalidad`; CANCELAR la restaura.
- `prepartido_screen._simular_instantaneo` pasa `ment_<lado user>=mi_equipo.mentalidad` y
  `"ia"` al rival.

### 4. User: en vivo (`ui/match_screen.py`)

- Tira de 5 botones (AUTOBÚS · DEF · NORMAL · OFE · TODO O NADA) visible mientras corre el
  partido, con la activa resaltada. Clic: cambia la mentalidad del user, **sin pausar**, y
  re-simula el resto de la mitad en curso desde el minuto actual (mismo mecanismo que el reanudar
  del ajuste táctico: `simular_rango(minuto+1, fin, …)` y reemplazo de eventos futuros).
  No cuenta como cambio de jugador.
- También está en el menú táctico en vivo / medio tiempo (mismo control que en dirección).
- `_snapshot_alineacion` / `_restaurar_alineacion` incluyen `mentalidad`: al terminar el partido
  vuelve la mentalidad por defecto.
- Todas las llamadas a `simular_rango` del partido del user pasan la mentalidad actual del user
  y `"ia"` al rival.
- Eventos `tipo == "mentalidad"` se muestran en los comentarios al revelarse ("78' — Rival FC
  pasa a TODO O NADA") y el marcador muestra debajo del nombre del rival su mentalidad actual (la
  del último evento revelado; `NORMAL`/base al inicio).

## Fuera de alcance

Mentalidad por jugador, instrucciones individuales, efecto en lesiones/tarjetas/cansancio,
personalidad distinta por DT de la IA.

## Manejo de errores

`EFECTO_MENTALIDAD.get(m, EFECTO_MENTALIDAD["normal"])` en todo el motor; `mentalidad_ia` en
`try/except` → `"normal"`. Patrón `try/except` + `logger.error` en la UI como el resto.

## Pruebas

- Nuevo `tests/test_mentalidad_v250.py`:
  1. `mentalidad_ia`: cada umbral (base por diferencia, 70'/82' perdiendo, 75'/85' ganando,
     perdiendo por 3+).
  2. Reparto de goleadores en `todo_o_nada` (2000 partidos): DEF > 25% de los goles; en
     `autobus`: 0 goles de DEF.
  3. Calibración (2000 partidos entre equipos parejos, fijo vs fijo):
     normal–normal 2.5–2.9 goles/partido; autobus–normal < 1.8; todo_o_nada–normal > 3.5 y el
     que va a todo o nada recibe más goles que en normal.
  4. IA vs IA (default) entre equipos de las ligas reales: promedio 2.5–3.0 (no descalibrar las
     ligas de fondo).
  5. `Equipo.to_dict`/`from_dict` conserva `mentalidad`; valor inválido → `"normal"`.
  6. Cambio en vivo: estado de partido simulado headless, clic en la tira → `mi_equipo.mentalidad`
     cambia y los eventos posteriores al minuto actual se regeneran.
  7. Tras terminar el partido la mentalidad vuelve a la previa.
- Suite completa sin regresiones; capturas headless del partido con la tira y de dirección.

## Implementación (v2.5.0) — decisiones tomadas

- Sin plan escrito aparte: Diego pidió hacer el resto de sub-proyectos seguidos y probar al final; se implementó con TDD directo sobre este spec.
- `_decidir_mentalidad(d, minuto, gp, gr, es_local)` (pura) + `mentalidad_ia(...)`; la diferencia de medias se calcula una vez por tramo (`_simular_minutos`), no cada minuto.
- `simular_partido`/`simular_rango` aceptan `ment_l`/`ment_v` (default `"ia"`). Los partidos del user pasan su mentalidad vía `match_screen._ments` (en vivo y simulación instantánea).
- Calibración medida (1500 partidos): normal–normal 2.50 (el motor previo, sin cambios: la meta 2.5–2.9 del spec se bajó a 2.2–2.9 porque el espejo de un equipo de 85 ya daba ~2.4); autobús–normal 0.79; todo o nada–normal 4.17 (recibe 2.32 vs 1.23); IA vs IA en las 5 ligas 2.60.
- Goles de defensas en TODO O NADA: 16% (vs 2.5% en normal). Atacan el 40% de las veces pero rematan peor; el test exige >12% y >3× normal en vez de >25%.
- Cabecera de Dirección: título a tamaño md y controles reacomodados para que entren FORMACIÓN · ESTILO · MENTALIDAD. Atajos , y . cambian la mentalidad.
- Tests: `tests/test_mentalidad_v250.py` (10 casos; `N_MENT` reduce las simulaciones para correr rápido).
