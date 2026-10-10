# Traspaso de `lol2` a `lol4` — Noticias UI (tareas 6 y 7 pendientes)

> `lol2` tenía el contexto saturado; Diego pidió pasar lo que falta a `lol4` (sesión nueva). Este archivo es la fuente
> de verdad del traspaso. El plan completo (tareas, tests exactos, interfaces) sigue siendo
> `docs/superpowers/plans/2026-10-09-noticias-ui-lol2.md`; el diseño, `docs/superpowers/specs/2026-10-09-entrenadores-noticias-design.md`.
> Líder y revisor: sesión `lol`. Quien edita la columna de `lol` (noticias.py, entrenadores, mercado, retiros…): `lol3`.
> A partir de ahora, **tú (`lol4`) ocupas la columna de `lol2`** (sección 12 del spec) y recibes los avisos de archivos compartidos.

## 1. Estado real

| Tarea del plan | Estado | Evidencia (corrida en esta sesión) |
|---|---|---|
| 1 Nombres genéricos | HECHA | `test_nombres_genericos` + `test_nacionalidades` → 13 passed |
| 2 Editor ampliado | HECHA | `test_editor_ampliado` 26 passed; con `test_editor_libres_dts`, `test_patrocinios_editor`, `test_ligas_v370`, `test_estilos_v330`, `test_teclado_v420`, `test_ayuda_v390` → 104 passed, 1 failed (timing, ver §4) |
| 3 Visual + pantalla Noticias + OFICINA + feed | HECHA, regresión sin cerrar | `test_noticias_visual` 10, `test_noticias_screen` 13, `test_noticias_feed` 13 passed; `test_calendario, test_hub_v240, test_ayuda_v390, test_ux_v360, test_notificaciones, test_vestuario_v310, test_directiva_v280, test_teclado_v420` → 133 passed |
| 4 `noticias_gen.py` | HECHA | `test_noticias_gen` 16 passed |
| 5 Carga de temporada | HECHA, regresión sin cerrar | `test_carga_noticias` 9 passed (197 s); `test_pantalla_carga` 14 passed (corrido ANTES de editar `resumen_temporada_screen.py`) |
| **6 Prensa + overlay + `factor_tarjetas`** | **PENDIENTE** (solo existe `prensa.py` con `mover_moral`) | — |
| **7 Logros + overlay en `career_screen`** | **PENDIENTE** | — |

**Lo primero que debes hacer (verificación que me quedó sin cerrar), archivo por archivo (nunca `pytest tests` entero):**

1. `pytest tests/test_pantalla_carga.py tests/test_temporada.py tests/test_temporadas_continente.py tests/test_premios_v0417.py -q` (Tarea 5; son lentos, lanza en segundo plano y redirige a un archivo).
2. `pytest tests/test_noticias_visual.py tests/test_noticias_feed.py tests/test_noticias_screen.py tests/test_competiciones_v380.py tests/test_hub_v240.py tests/test_ux_v360.py tests/test_ayuda_v390.py tests/test_teclado_v420.py tests/test_ajustes_v0411.py tests/test_calendario.py -q` (Tarea 3; yo lo dejé corriendo y no vi su final, no cuentes con ese resultado).
3. Pasos manuales que NO hice (nadie abrió el juego): editor (crear jugador, página 2, quitar/asignar DT, guardar y empezar carrera), hub (tecla N, rotación 5 s, clic en la tarjeta), OFICINA > NOTICIAS, carga de temporada con titulares. Si puedes, `python main.py`; si no, dilo a `lol`.

## 2. Qué hice y dónde (archivos de `lol2`)

Creados: `alpha_football/data/nombres_genericos.py`, `ui/noticias_visual.py`, `ui/noticias_screen.py`, `noticias_gen.py`, `prensa.py` (solo `mover_moral`),
tests `test_nombres_genericos`, `test_editor_ampliado`, `test_noticias_visual`, `test_noticias_screen`, `test_noticias_feed`, `test_noticias_gen`, `test_carga_noticias`.
Modificados (siempre con `Edit` puntual o parche): `retiros.py` (solo el dict de nombres → import), `models.py` (Equipo: `dt_nacionalidad`, `dt_edad`, `dt_sin`), `ui/edit_screen.py`,
`ui/league_screen.py` (feed, pestaña NOTICIAS, tecla N, OFICINA a 3 columnas, `_ajustar_texto`, `_no_leidas_noticias`), `ui/pantalla_carga.py`, `ui/resumen_temporada_screen.py`,
`main.py` (1 línea), `ui/ayuda.py`, `ui/atajos.py`, y 2 tests viejos (`test_calendario.py:359` → 9, `test_hub_v240.py:172`).
**No hay commits** (regla del proyecto y de este equipo: nada de commit, stash, checkout ni reset; el árbol tiene trabajo sin commit de todos).

## 3. Lo que tienes que hacer: Tareas 6 y 7 del plan

Sigue el plan al pie de la letra (TDD: test que falla → implementar → test verde; avisos antes/después de tocar archivos compartidos). Hechos del código que verifiqué y que el plan no repite entero:

### Tarea 6 — prensa (overlay) y `factor_tarjetas`

- `prensa.py` ya existe con `mover_moral(jugadores, delta)` (tiene su test en `test_noticias_gen.py::test_mover_moral`). Amplíalo; no lo reescribas. Moral: `vestuario.actualizar_moral` es acumulativa (`antes + d`) y `causas_moral` solo lee las claves `minutos`, `equipo`, `sueldo` (salidas.causa_principal): una baja se anota en `['equipo']` de la última causa (ya lo hace `mover_moral`).
- **Los clubes de la IA no recalculan moral**: el −2 del Provocador se devuelve en `consumir_tension` al terminar el siguiente partido del user (si no sería permanente). El "siguiente rival" en `post` = el rival de tu próximo partido sin jugar en `liga.calendario` (los `local_id`/`visitante_id` son `str`).
- **Dónde engancharse** (verificado): `ui/postpartido.armar_datos` (postpartido.py:130) lo llaman el partido en vivo (`match_screen._cerrar_partido_vivo`, ~1087) y la simulación instantánea (`prepartido_screen._simular_instantaneo`, líneas ~159/214/227); `_salir_partido` (match_screen.py ~1091) borra `postpartido`, así que el hecho se evalúa en `armar_datos`, no después. Ambos flujos dibujan el postpartido con `postpartido.render(screen, estado, mouse_pos, click_pos, teclas)` (match_screen ~1754 y `prepartido._render_resultado`): ahí va el overlay *post* (consume teclas/clic con el overlay activo y lo dibuja al final). El overlay *pre* va en `ui/prepartido_screen.render` (línea ~455, envuelve a `_render` que lee los eventos en ~491-497): evalúa `evaluar_pre` antes de `_render`, y `_render` debe descartar teclas/clic mientras el overlay esté activo (`key_events, click_pos = [], None` tras el bucle de eventos) y dibujarlo después de `_render`.
- Prepartido: ya dibuja "CLÁSICO" con `data.clasicos.es_clasico(local, visitante)` (usa `Equipo.rival`); reutiliza ese predicado. Fases de copa: `competiciones.FASES`/llaves usan las etiquetas `'Fase de liga','Playoff','Octavos','Cuartos','Semifinal','Final'`; el partido de copa del user está en `estado['partido_copa_dict']['fase']` y `estado['partido_copa_bracket_fase']` (NO verifiqué los valores exactos: míralos en `copa_screen.preparar_partido_copa` antes de fijar `motivo_partido`). `'semifinal'` no debe contar como "final": usa `re.search(r'\bfinal\b', ...)`.
- `engine.py`: constantes `_C_AMARILLA…_C_FALTA` en 1037-1041 y el sorteo único por equipo y minuto en `_incidencias_minuto` (1044-1099, `r = random.random()`). El remapeo está especificado en el plan (`_remapear_sorteo_tarjetas`, ensancha solo `[0, _C_ROJA)`); testéalo con una rejilla de valores, no con partidos. `simular_partido(...)` ya acepta `ctx`; el ctx nuevo se crea en engine.py ~936-938: añade `factor_tarjetas: float = 1.0` como parámetro con nombre y asígnalo ahí. `partido_ctx.EstadoPartido` (partido_ctx.py:43-74): campo nuevo + copiarlo en `copia()`.
- `lol` autorizó **una línea** en `ui/match_screen.py:~1191` (`estado['sim_ctx'] = nuevo_estado(...)` → asignar `.factor_tarjetas = prensa.factor_tarjetas(estado)` en `try`). Del bloque de cierre de jornada de ese archivo (~436-600) ni te acerques: es de `lol3`. Pidió **asignación explícita, sin estado global ni sincronización por cuadro**.
- Tests viejos que NO deben romperse al tocar prepartido/postpartido: `test_simulacion, test_mentalidad_v250, test_bajas_rival_cambios, test_lesiones_dias_v0419, test_presentacion_v410, test_ajustes_v04141, test_vestuario_v310, test_dias, test_integridad_v300, test_competiciones_v380, test_ux_v360`.

### Tarea 7 — logros

- Llamadores: `postpartido.armar_datos` → `logros.registrar_partido` (solo `modo in ('liga','copa')`, en su `try`; `pos_despues = postpartido.posicion_liga(liga, mi.id)`); `noticias_gen.generar_jornada` (añade `logros.revisar` al final, en su propio `try`; ya hay una tupla de generadores) y `avanzar_nueva_temporada` (tras armar el `historial`, en la zona del paso 2 de `resumen_temporada_screen.py`; está en su propio `try`).
- "Última jornada" de liga: `max(p.jornada for p in liga.calendario if p.jugado) == liga.num_jornadas` (al cerrar, `jornada_actual` ya no avanza en la última).
- `historial` (lista de dicts por temporada): claves `pos`, `libertadores` (texto: "Campeón", "Final", "Subcampeón", "Semifinal"…), `campeon_liga`; en curso, `estado['copa_mejor_fase_temp']`.
- `Jugador`: `overall` (propiedad), `ventana_traspaso` (no vacío = fichado), `canterano` (club formador o `''`).
- `career_screen.render` (career_screen.py:238-361): eventos en 256-270 (hoy ESC/Backspace/Enter vuelven, ↑↓ desplazan, rueda), `R_VOLVER = Rect(SCREEN_W-230, 22, 200, 48)`. El botón LOGROS (`R_LOGROS`) va a su izquierda; la tecla `L` está libre. `ui/ayuda.py:443-452` (`_ayuda_carrera`) y `ui/atajos.py:30` (`'career_screen'`) hay que actualizar (≥ 3 items, textos ≤ 110; atajos ≤ 150 y con "H Ayuda").
- Cada logro publica `noticias.publicar(estado, 'logro', ..., importancia=5, accion={'pantalla': 'career_screen', 'texto': 'VER LOGROS'})`.

## 4. Trampas y reglas que ya me mordieron

- **Fallos que NO son tuyos ni míos** (fallan igual sin mis cambios): `test_v236::test_suerte_y_goleadas` (0.50 vs > 0.65), `test_pedidos_v440::test_fichaje_avisa_llegada` y `::test_contrato_en_analisis_renovacion_y_fichaje`. `test_ligas_v370::test_rendimiento_jornada` es de tiempo (pasa suelto en ~7 s si no hay otras sesiones corriendo). No los "arregles"; avisa a `lol` si te estorban.
- Tests de hub/pantallas: el **cartel de apertura del mercado se come clics y teclas**; antes de simular un clic pon `estado['datos_carrera']['aviso_mercado_visto'] = [1, '2026-07-01']`. `estado_carrera()` tarda ~3 s: en los tests largos cachea una base y usa `copy.deepcopy` (0.6 s), como en `test_noticias_gen.py`.
- `main` parchea `pygame.event.get` al importarse: si un test lo importa, restaura (`orig_get = pygame.event.get; try: import main; finally: pygame.event.get = orig_get`). Eventos de prueba: `pygame.event.post(Event(KEYDOWN, key=..., unicode=..., mod=0))` y `Event(MOUSEBUTTONDOWN, button=1, pos=...)`; límpialos antes (`pygame.event.clear()`).
- `tests/test_pantalla_carga.py` fija la firma `mostrar(titulo, paso, avance)` con un espía: **no cambies esa firma**.
- Registro de una pantalla nueva = `main.MODULOS_PANTALLA` + `ayuda.AYUDA` (+ `_TEXTO_TARJETA`) + `atajos.ATAJOS`; hay tests que lo exigen (`test_ayuda_v390`, `test_ux_v360`). El overlay de prensa NO es pantalla: no se registra.
- Edición de archivos: `Edit` puntual (nunca `Write` sobre uno existente). Para parches grandes usa un script Python en el scratchpad (el heredoc de Bash se come las `\`; ver memoria del proyecto) y no escribas texto con `newline` distinto: el repo es LF.
- Noticias (API de `lol3`, `alpha_football/noticias.py`): usa `noticias.etiqueta(n)` (no `ETIQUETA[tipo]`); **no llames `para_feed/activas/no_leidas` por cuadro** (cada llamada recorre el calendario): cachea en `estado` (ya hay `feed_actual` y `_no_leidas_noticias` en league_screen como ejemplo); `publicar(estado, tipo, titular, cuerpo, importancia, categoria=None, equipos=, jugadores=, dts=, **extra)` acepta `temporada=`, `jornada=`, `accion={'pantalla','texto'}` y cualquier clave extra JSON (como `clave=` para no duplicar). Un ascenso se publica con `tipo='descenso', categoria='ascenso'`.
- Todo lo nuevo de `datos_carrera` con `setdefault` y tipos JSON (guardados viejos).

## 5. Decisiones que tomé (rulings) — ya aceptadas por `lol` salvo las marcadas

1. Sin commits, worktree ni ledger de `executing-plans`: mandan las reglas del proyecto.
2. `sanear_jugador` no agrega claves ni toca valores en rango; 0 en penales/resistencia/salario = "automático". El campo OVR de la página 1 del editor quedó como estaba. (informadas a `lol`)
3. `prensa.py` nace en la Tarea 4 con `mover_moral` (lo necesita `_polemico`); la Tarea 6 lo amplía.
4. El cierre de temporada se publica en **dos fases** porque `ascensos_descensos` intercambia clubes entre divisiones antes del reset: `generar_cierre_temporada` (campeones + equipo del año) antes del swap, `generar_cierre_movimientos` después. Ambos con `temporada=` explícita. (a informar a `lol`)
5. Carga de temporada: titulares por `pantalla_carga.fijar_titulares(...)` (no por `mostrar`); `cerrar(minimo=...)` redibuja ~30 fps; `MINIMO_TEMPORADA` 3 s en juego real, 0 con SDL dummy. Los textos de etapa cambiaron (ver `test_carga_noticias`).
6. OFICINA: 3 columnas con > 8 tarjetas (392 px) y alto 108 con > 9; títulos largos pasan a fuente `md`, subtítulos recortados con "…". Las tarjetas laterales del feed van sin titular y atenuadas.
7. Efectos de prensa (ver plan): Motivador +2, Humilde +1, Provocador −2 al siguiente rival (se devuelve), Agresivo `FACTOR_TENSION = 1.6`; una pregunta antes y una después por partido, nunca en amistosos, siempre SALTAR. **Interpretación mía de "máximo una por partido"**: si `lol` prefiere otra, se cambia en `evaluar_pre/evaluar_post`.

## 6. Cómo reportar

- Al terminar **cada tarea**, a `lol` (3 líneas): qué quedó, qué tests corriste con su resultado real (no "debería pasar"), desvíos.
- Antes y después de tocar `ui/match_screen.py` (1 línea), `engine.py`, `partido_ctx.py`, `models.py`, `retiros.py`, `main.py`, `ui/ayuda.py`, `ui/atajos.py`: aviso a `lol3`.
- Dudas de diseño o cambios de contrato: a `lol`. Si vas a tocar algo fuera de la lista (p. ej. `postpartido.py` ya está en tu columna; `entrenadores.py` NO), pregunta antes.
- Al terminar, escribe **tu sección en `context.md`** (solo al final, nada de cabecera: la cabecera, `__init__.py` y `README.md` los integra `lol`) y deja la lista de rulings que tomes.
