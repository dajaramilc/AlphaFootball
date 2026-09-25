# Sub-proyecto 6 — Competiciones reales y Balón de Oro (v3.8.0)

**Fecha:** 2026-09-23 · **Decidido por Diego:** Champions con fase de liga suiza (rellenando con otros
clubes hasta completarla, con Italia incluida); Libertadores con 8 grupos de 4 "como en la vida real";
1 cupo más por liga; objetivos de copa; Balón de Oro = goles + nota + trofeos. Depende del sub-proyecto 5
(Italia, Uruguay, Ecuador, ligas de 12). Incluye los ítems de UX que dependen de las copas.

## 1. Motor nuevo `alpha_football/competiciones.py`
Lógica pura y serializable; reemplaza la lógica de `ui/copa_screen.py` (que queda solo como pantalla).
Estado por temporada en `datos_carrera['copas'][tipo]` (`tipo ∈ {'champions','libertadores'}`):
`{'temporada', 'equipos': [nombres], 'fase', 'fechas': [...], 'partidos': [...], 'tabla' | 'grupos',
'llaves', 'campeon'}`; cada partido `{'id', 'fecha', 'fase', 'local', 'visitante', 'gl', 'gv',
'jugado', 'penales'?, 'ida_de'?}`. Los equipos se resuelven por nombre a objetos `Equipo` (ligas vivas o
pool internacional).

### Champions (36 clubes)
- Cupos: premier 5, laliga 5, seriea 5 (= 4 reales + 1) → 15; **21 de relleno** europeos de
  `data/internacional.py` (Alemania 5, Francia 4, Portugal 3, Países Bajos 3, Bélgica 1, Escocia 1,
  Turquía 1, Austria 1, Croacia 1, Ucrania 1), con jugadores reales parodiados.
- **Fase de liga:** 4 bombos de 9 por media; cada club juega 8 partidos: 2 rivales de cada bombo (uno
  de local, uno de visitante), nunca contra uno de su mismo país (si el sorteo no cierra, se relaja esa
  regla y se reintenta con otra semilla). Tabla única de 36 (3/1/0, dif., goles a favor).
- 1º-8º → octavos. 9º-24º → **playoff** ida y vuelta (9 v 24, 10 v 23, …, 16 v 17; el mejor
  clasificado cierra de local). 25º-36º eliminados.
- Octavos: 1º-8º contra los 8 ganadores del playoff (cuadro fijo por posición: 1º vs ganador 16-17,
  2º vs 15-18, …). Octavos, cuartos y semis a ida y vuelta; **final única** en campo neutral.
- 8 + 2 + 2 + 2 + 2 + 1 = **17 fechas**.

### Libertadores (32 clubes)
- Cupos: brasil 7, argentina 6, betplay 5, uruguay 5, ecuador 5 → 28; **4 de relleno** (Chile,
  Paraguay, Perú, Bolivia) de `data/internacional.py`.
- **8 grupos de 4** (bombos por media, 1 por bombo en cada grupo, sin dos del mismo país en un grupo
  cuando se pueda), todos contra todos ida y vuelta: 6 fechas. Pasan 1º y 2º.
- Octavos: 1º de un grupo vs 2º de otro (A1-B2, B1-A2, C1-D2, …), ida y vuelta, cierra de local el 1º.
  Cuartos y semis ida y vuelta; **final única**. 6 + 2 + 2 + 2 + 1 = **13 fechas**.

### Reglas comunes
- Ida y vuelta: gana el global; si empata, **penales** (sin gol de visitante). Final única: si empata,
  penales. Penales con la secuencia ronda a ronda que ya existe.
- **Fechas en el calendario de liga (22 jornadas):** la fecha i (0-based) de una copa de N fechas se
  juega después de la jornada de liga `ceil((i + 1) · 21 / N)`; la final siempre tras la jornada 21
  (antes de la última de liga). Varias fechas pueden caer tras la misma jornada; se juegan en orden.
- Clasificación: T1 por media (top N de cada liga); desde T2 por la tabla final de 1ª (`copa_ranking`).
  Ascender no da copa.
- La copa del continente del user se juega con él (JUGAR → prepartido → partido, como hoy); **las dos
  copas se simulan completas cada temporada** (la otra en segundo plano, jornada a jornada).
- Partida vieja a mitad de temporada: la copa en curso se regenera con el motor nuevo desde la jornada
  actual (las fechas ya pasadas se simulan, incluidas las del user).

## 2. Pantalla de copa (`ui/copa_screen.py`, reescrita sobre el motor)
Pestañas: **FASE DE LIGA** (tabla de 36 con zonas 1-8 / 9-24 / 25-36) o **GRUPOS** (8 grupos),
**LLAVES** (playoff → final, con global y penales), **PARTIDOS** (fecha a fecha, tu partido resaltado),
**ESTADÍSTICAS** (goleadores y asistencias de la copa). Selector CHAMPIONS / LIBERTADORES para ver la
otra copa.

## 3. Integraciones
- Hub (INICIO): próxima fecha de copa y línea de estado con la fase ("Copa: eliminado en octavos",
  arregla "eliminado" sin fase). **Tabla completa con pestañas LIGA / COPA** (la de copa = tabla de la
  fase de liga o tu grupo).
- OTRAS LIGAS: pestaña **COPAS** con el estado de las dos (fase actual, tabla/grupos, llaves).
- Objetivo de copa (7a): fases `['Fase de liga'|'Fase de grupos', 'Playoff', 'Octavos', 'Cuartos',
  'Semifinal', 'Finalista', 'Campeón']` (Playoff solo en Champions); `directiva.meta_copa` se ajusta:
  r = 1 con 8+ de ventaja → Campeón; r ≤ n/8 → Finalista; r ≤ n/4 → Semifinal; r ≤ n/2 → Cuartos; si no
  → Octavos.
- Premios de copa (dinero) por fase alcanzada; historial de carrera y resumen de temporada con la fase.

## 4. Balón de Oro (`premios.py`)
Puntaje = goles × 4 + asistencias × 2 + max(0, nota − 6.0) × 10 + trofeos (liga 1ª ganada 15; Champions
o Libertadores ganada 20; porteros: vallas invictas × 1.5), × peso de la liga (Europa 1.0, Brasil y
Argentina 0.85, resto 0.75, 2ª 0.6). Requisito: haber jugado ≥ 50% de la liga. Los goles y
asistencias de la copa suman. Podio de 3 como hoy.

## Pruebas
`tests/test_competiciones_v380.py`: sorteo de la fase de liga (36 equipos, 8 partidos c/u, 2 por bombo,
4 de local, sin mismo país), tabla y cortes 8/24, cruces del playoff y octavos, ida y vuelta con global
y penales, final única; Libertadores (8 grupos de 4 por bombos, sin repetir país cuando se puede, 6
fechas, cruces 1º vs 2º); mapeo de fechas (N=17 y N=13, monotónico, final tras la 21); clasificados por
cupos (15 + 21 y 28 + 4, sin duplicados); temporada completa simulada de ambas copas con campeón;
integración (JUGAR lleva a la copa cuando toca; resultado del user se registra); save viejo regenera;
meta_copa nueva; Balón de Oro con la fórmula nueva.
