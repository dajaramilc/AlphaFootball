# Temporadas por continente (sub-proyecto F, v0.4.16.0) — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cada continente tiene su propia temporada (Europa 1 jul–30 jun, Sudamérica 1 ene–31 dic): el otro continente arranca a mitad de la suya, cierra en su fecha mientras tú sigues jugando, y tu cierre solo cierra tu continente.

**Architecture:** Un módulo sin UI, `alpha_football/temporadas.py`, guarda el estado del mundo en `datos_carrera['mundo']` (`'desfase'`, año de cada continente, último campeón y podio congelado) y concentra los pasos por liga que hoy están dentro de `resumen_temporada_screen.avanzar_nueva_temporada`. Las funciones que recorren todas las ligas reciben `paises=None` (sin filtro = comportamiento de hoy). El otro continente avanza y cierra **por fecha**: lo revisa `temporadas.revisar_jornada`, que corre cada día (`dias.revisar_dia`) y, sin reloj, al cerrar tu jornada. Sin la marca `mundo['desfase']` todo el código se comporta como hoy.

**Tech Stack:** Python 3.10, módulos existentes (`calendario`, `temporada`, `competiciones`, `nivel_temporada`, `entrenadores`, `mercado_ia`, `premios`).

**Spec:** `docs/superpowers/specs/2026-10-06-calendario-mercado-actualizador-design.md`, sección «F · Temporadas por continente» (F1–F6). El spec es anterior a G2: las diferencias con el código real están en `docs/superpowers/plans/PROGRESO-PENDIENTES.md` («F — spec contra código»).

**Método de ejecución:** nativo (superpowers:executing-plans), en esta sesión, sin worktree, sin commits, sin subagentes (fijado por Diego en `EJECUCION-PENDIENTES.md`).

## Global Constraints

- **Sin la marca todo se comporta como hoy:** con `datos_carrera['mundo']['desfase']` ausente ningún camino nuevo se activa (los tests actuales siguen valiendo). Todo filtro `paises` es opcional y sin él la función hace lo de siempre.
- **El desfase es por fecha, no por jornadas:** una liga del otro continente está en la jornada cuyo sábado (`calendario.sabados(n, continente, año)`) ya pasó; su temporada termina el 31 dic (Sudamérica) / 30 jun (Europa) y la nueva empieza al día siguiente.
- **Anual y para todos, en TU cierre:** edad y desarrollo pasivo, retiros y regens, contratos, tus finanzas, objetivos, historial y Balón de Oro. El cierre del otro continente no envejece a nadie.
- `estado['temporada']` sigue contando tus cierres; el año de cada continente vive en `mundo['anio']` (lo lee `calendario.anio`).
- Comentarios nuevos `# v0.4.16.0`; textos y comentarios en español; Edit parcial; sin commits; sin tocar `premios.py` (es de la sesión `lol2`: se usan sus funciones públicas).
- Tests: `PYTHONIOENCODING=utf-8 python tests/test_temporadas_continente.py` → `N/N tests pasaron`. Los que cambian de temporada son lentos: de uno en uno.

## Review Focus

1. **Save viejo (sin marca) que cierra su temporada:** todo se cierra junto como hoy y recién después se desfasa; el otro continente queda a mitad de su temporada y no se pierde ningún club ni jugador.
2. **Dos temporadas seguidas:** el desfase no se corre ni se acumula (cada continente cierra una vez por año, el año de cada uno sube de a uno).
3. **Cierre del otro continente con tu club dentro de un ascenso/descenso o de su copa:** imposible por construcción (tu club es de tu continente): comprobar que `cerrar_continente` nunca toca tu liga, tu tabla ni tu copa.
4. **Cambio de continente a mitad de temporada:** sigues en la jornada en que va esa liga, con su calendario y su año; el continente que dejaste sigue cerrando en su fecha.
5. **Un paso que falla dentro del cierre del otro continente** (una liga dañada): se registra y el resto del cierre sigue; el año del continente sube igual (si no, se cerraría de nuevo cada día).

## Estructura de archivos

| Archivo | Responsabilidad |
|---|---|
| `alpha_football/temporadas.py` (nuevo) | Mundo (marca, años), continentes, fechas por liga, `poner_al_dia`, `arrancar_desfase`, `cerrar_continente`, `revisar_jornada`, pasos por liga (`ascensos_descensos`, `reiniciar_ligas`), podio congelado. |
| `alpha_football/nivel_temporada.py`, `entrenadores.py`, `mercado_ia.py`, `ui/copa_screen.py`, `ui/league_screen.py` | Filtro `paises=None`. |
| `alpha_football/competiciones.py` | Copas por continente: vigencia por `c['anio']`, jornada de su continente, `tipos=None` en `iniciar_temporada` y `simular_todo`. |
| `alpha_football/ui/resumen_temporada_screen.py` | `avanzar_nueva_temporada` usa los pasos de `temporadas.py`; con desfase solo cierra tu continente; un save sin marca se desfasa al terminar. |
| `alpha_football/ui/match_screen.py`, `alpha_football/dias.py` | Llaman a `temporadas.revisar_jornada`; las ligas de fondo de tu continente siguen a tu jornada. |
| `alpha_football/ui/menu.py` | Paso de carga «El otro continente, a mitad de temporada» al crear la carrera. |
| `alpha_football/directiva.py` | `cambiar_de_club` a otro continente. |
| `tests/test_temporadas_continente.py` (nuevo) | Arranque desfasado, cierre del otro continente, dos temporadas, cambio de continente, save viejo, filtros. |

---

### Task 1: el mundo — marca, continentes, años y fechas por liga

**Files:** Create `alpha_football/temporadas.py`, `tests/test_temporadas_continente.py`.

**Interfaces — Produces:**
- `CONTINENTES = ('europa', 'sudamerica')`; `continente_de(tipo) -> str`; `otro(cont) -> str`; `paises_de(cont) -> tuple`.
- `mundo(estado) -> dict` (crea `datos_carrera['mundo']` si falta, sin marcar); `activo(estado) -> bool`.
- `anio_en(cont, d: date) -> int` (año en que empezó la temporada de ese continente que contiene `d`: Europa `d.year` si `d ≥ 1 jul`, si no `d.year − 1`; Sudamérica `d.year`).
- `anio(estado, cont) -> int` (`mundo['anio'][cont]`; sin dato: el del user por `calendario.anio`, el otro por `anio_en(cont, temporada.fecha(estado))`).
- `fin(estado, cont) -> date` (de `temporada.CALENDARIO[cont]['fin']` con ese año).
- `ligas(estado, paises=None) -> [(liga, tipo, division)]` (= `mercado_ia.ligas_de_la_partida` filtrado).
- `fecha_jornada(estado, liga, j) -> date` (`calendario.sabados(liga.num_jornadas, continente_de(liga.tipo), anio(...))[j − 1]`).
- `jornadas_por_fecha(estado, liga, d) -> int` (cuántas jornadas de esa liga tienen su sábado ≤ `d`).

- [ ] **Step 1: tests que fallan** — `test_continentes_y_anios` (los 8 países se reparten 3 + 5; `otro`; `anio_en('europa', 30 jun 2027) == 2026`, `anio_en('europa', 1 jul 2027) == 2027`, `anio_en('sudamerica', 31 dic 2026) == 2026`); `test_sin_marca_no_hay_desfase` (`activo` False en una carrera de `estado_carrera`; `anio(e, cont user) == calendario.anio(e)`); `test_la_jornada_del_otro_continente_sale_de_la_fecha` (Europa, 1 jul 2026: en una liga sudamericana de 22 jornadas `jornadas_por_fecha` da entre 8 y 11 y coincide con contar `sabados(22, 'sudamerica', 2026) ≤ 1 jul`; 31 dic 2026 → 22; 1 ene 2027 con año 2027 → 0).
- [ ] **Step 2:** correr → FAIL (`No module named temporadas`).
- [ ] **Step 3:** implementar las funciones de arriba (sin efectos fuera de `mundo`).
- [ ] **Step 4:** correr → verde.

### Task 2: filtro de países en lo que recorre todas las ligas

**Files:** Modify `alpha_football/nivel_temporada.py` (`_ligas`, `preparar`, `aplicar_objetivos`, `aplicar_topes`, `foto_objetivos_ia`), `alpha_football/entrenadores.py` (`cierre_temporada`), `alpha_football/mercado_ia.py` (`ingresos_fin_temporada`), `alpha_football/ui/copa_screen.py` (`guardar_ranking_copas`), `alpha_football/ui/league_screen.py` (`_ligas_de_fondo`, `simular_jornada_segunda_division`, `completar_ligas_de_fondo`).

**Interfaces — Produces:** todas reciben `paises: Optional[Iterable[str]] = None` como último parámetro por nombre. Con filtro: `guardar_ranking_copas` y `foto_objetivos_ia` FUNDEN con lo guardado (no reemplazan los otros países); `entrenadores.cierre_temporada` solo reinicia `despidos_temp` y `ofertas` si el país del user está en el filtro (o no hay filtro).

- [ ] **Step 1: tests que fallan** — `test_los_filtros_de_paises_solo_tocan_esas_ligas`: (a) `completar_ligas_de_fondo(e, paises=SUDAMERICA)` deja las sudamericanas con todo jugado y las europeas de fondo sin tocar; (b) `guardar_ranking_copas(e, paises=SUDAMERICA)` conserva el ranking europeo ya guardado y escribe el sudamericano; (c) `ingresos_fin_temporada(e, paises=SUDAMERICA)` no cambia el saldo de ningún club europeo; (d) `foto_objetivos_ia(e, paises=…)` funde; (e) `nivel_temporada.preparar(e, paises=SUDAMERICA)` solo planifica clubes sudamericanos. `test_sin_filtro_todo_como_hoy`: las mismas funciones sin `paises` tocan las 16 ligas.
- [ ] **Step 2:** FAIL (`unexpected keyword argument 'paises'`).
- [ ] **Step 3:** implementar.
- [ ] **Step 4:** verde + `test_competiciones_v380.py`, `test_dts_v340.py`, `test_finanzas_v460.py`, `test_mercado_v440.py` siguen en verde.

### Task 3: copas por continente

**Files:** Modify `alpha_football/competiciones.py`, `alpha_football/ui/copa_screen.py` (`simular_copa_entera`, `iniciar_copas_temporada` aceptan `tipos=None`).

**Interfaces — Produces:**
- `competiciones.CONTINENTE_COPA = {'champions': 'europa', 'libertadores': 'sudamerica'}`.
- `_vigente(estado, c, tipo) -> bool`: con desfase `c.get('anio') == temporadas.anio(estado, CONTINENTE_COPA[tipo])`; sin desfase `c.get('temporada') == estado['temporada']` (hoy).
- `_jornada_copa(estado, tipo) -> int`: sin desfase o copa del continente del user = `_jornada_actual(estado)`; si no, la jornada de las ligas de 1ª de su continente (todas jugadas = `n + 1`).
- `iniciar_temporada(estado, rng=None, forzar=False, tipos=None)`: solo rehace los `tipos` pedidos (o los no vigentes) y conserva la otra copa; `_nueva_copa` sella `c['anio']` cuando hay desfase.
- `simular_todo(estado, rng=None, tipos=None)`; `avanzar` usa `_jornada_copa` por copa.

- [ ] **Step 1: tests que fallan** — `test_cada_copa_sigue_la_jornada_de_su_continente` (con la marca puesta a mano y las ligas sudamericanas adelantadas a la J11, `CP.avanzar` juega fechas de la Libertadores aunque tu liga esté en la J1, y ninguna de la Champions); `test_rehacer_una_copa_no_toca_la_otra`; `test_sin_marca_las_copas_como_hoy` (`_asegurar` recrea las dos al cambiar `estado['temporada']`).
- [ ] **Step 2:** FAIL. **Step 3:** implementar. **Step 4:** verde + `test_competiciones_v380.py`, `test_copa_v430.py`, `test_copa_integridad.py`.

### Task 4: los pasos por liga salen de `avanzar_nueva_temporada`

**Files:** Modify `alpha_football/temporadas.py`, `alpha_football/ui/resumen_temporada_screen.py`.

**Interfaces — Produces:**
- `temporadas.ascensos_descensos(estado, paises=None, temporada_libro=None) -> dict` con `{'movimientos': [{'tipo', 'ascendidos', 'descendidos'}], 'user_asc', 'user_des', 'premio_ascenso_user', 'payload_user'}` — el bucle de swap actual (usa `resumen_temporada_screen._swap_promocion`, `mercado_ia.aplicar_ascenso/aplicar_descenso`, deja `estado['_recien_ascendidos']`).
- `temporadas.reiniciar_ligas(lista_de_ligas) -> None` — tablas, estadísticas de temporada, moral ≥ 70, lesiones, sanciones, energía, `calendario = []`, `jornada_actual = 1`. **Sin** desarrollo pasivo.
- `temporadas.envejecer_ligas(lista_de_ligas) -> None` — `desarrollo.progresar_liga_pasivo(liga, 1)` por liga.

`avanzar_nueva_temporada` llama a estas tres en el mismo orden de hoy (reinicio y pasivo por liga, intercalados como hoy: `for liga: reiniciar_ligas([liga]); envejecer_ligas([liga])`). Sin cambio de comportamiento.

- [ ] **Step 1: test de caracterización** — `test_el_cierre_de_un_save_sin_marca_sigue_cerrando_todo`: antes de tocar nada, sobre `estado_carrera()` con las ligas completas, `avanzar_nueva_temporada` deja las 16 ligas en `jornada_actual == 1` con las tablas a cero, 2 ascensos y 2 descensos por país y `estado['temporada'] == 2`. (Se escribe y se ve pasar ANTES de la extracción: es la red de la refactorización; con Task 7 se actualiza la parte del desfase.)
- [ ] **Step 2:** extraer. **Step 3:** el test sigue verde + `test_v236.py`, `test_competiciones_v380.py`, `test_presupuesto_ventanas.py`, `test_premios_v0417.py`, `test_sancion_liga_v0417.py`.

### Task 5: el otro continente por fecha y el arranque desfasado (F1)

**Files:** Modify `alpha_football/temporadas.py`, `alpha_football/ui/menu.py` (paso de carga).

**Interfaces — Produces:**
- `poner_al_dia(estado, fecha, cont=None) -> int`: para cada liga del continente `cont` (por defecto el otro), juega con `league_screen._simular_jornada_liga_fondo` las jornadas cuyo sábado ≤ `fecha` (arma su calendario si falta); después avanza su copa (`competiciones._avanzar_copa` con `_jornada_copa`). Devuelve las jornadas jugadas. Sin desfase: 0.
- `arrancar_desfase(estado) -> bool`: si ya está activo, False. Marca `mundo = {'desfase': True, 'anio': {cont_user: calendario.anio(estado), otro: anio_en(otro, temporada.inicio(estado))}}`, sella `c['anio']` en la copa del continente del user, rehace la del otro, y `poner_al_dia(estado, temporada.inicio(estado))`.
- En `menu.py`, tras «Sorteando las copas»: `pantalla_carga.mostrar("INICIANDO CARRERA", "El otro continente, a mitad de temporada", 0.85)` + `temporadas.arrancar_desfase(estado)`.

- [ ] **Step 1: tests que fallan** — `test_arranque_desfasado_europa` (tras `arrancar_desfase`: marca activa, `mundo['anio'] == {'europa': 2026, 'sudamerica': 2026}`, cada liga sudamericana con `jornada_actual − 1 == jornadas_por_fecha(1 jul 2026)` partidos por club y goleadores con goles, las europeas en la J1 sin partidos, la Libertadores con fechas jugadas y la Champions sin ninguna; segunda llamada devuelve False y no juega nada); `test_arranque_desfasado_sudamerica` (carrera betplay: `{'europa': 2026, 'sudamerica': 2027}`, las europeas adelantadas hasta el 1 ene 2027); `test_el_otro_continente_avanza_con_los_dias` (con reloj, `dias.hasta_el_partido` hasta tu J1 juega las jornadas sudamericanas de julio y agosto; nunca más de las que tocan por fecha); `test_tus_ligas_de_fondo_siguen_tu_jornada` (tras cerrar tu J1 con `finalizar_jornada_liga`, las de tu continente avanzan exactamente una jornada).
- [ ] **Step 2:** FAIL. **Step 3:** implementar + enganchar: `dias.revisar_dia` suma `('temporadas', 'revisar_jornada')` a `pasos`; `match_screen.finalizar_jornada_liga`: `simular_jornada_segunda_division(estado, paises=…tu continente…)` cuando hay desfase y `temporadas.revisar_jornada(estado)` después. **Step 4:** verde + `test_dias.py`, `test_hub_v240.py`.

### Task 6: el cierre del otro continente (F2)

**Files:** Modify `alpha_football/temporadas.py`.

**Interfaces — Produces:**
- `cerrar_continente(estado, cont) -> dict` (`{'campeones': {tipo: club}, 'copa': club, 'movimientos': [...]}`), en este orden y cada paso bajo su `try` (un paso que falla se registra y el cierre sigue): 1) completar sus ligas (`completar_ligas_de_fondo(paises)`), terminar su copa (`simular_todo(tipos)`) y guardar su campeón en `mundo['campeones'][tipo_copa]`; 2) podio congelado del Balón (`premios.calcular_balon_de_oro` con sus ligas → `mundo['balon'][cont]`) y, si es Sudamérica y no es tu continente, el Sudamericano del Año queda pendiente (`premios._pendientes` + `premios.fecha_entrega`); 3) `guardar_ranking_copas(paises)`; 4) `nivel_temporada.preparar(paises)` y `entrenadores.cierre_temporada(paises)`; 5) `ascensos_descensos(paises)` + `aplicar_objetivos(paises)`; 6) `reiniciar_ligas` (sin envejecer) + `aplicar_topes(paises)`; 7) `ingresos_fin_temporada(paises)`, `foto_objetivos_ia(paises)`, `mundo['anio'][cont] += 1` y sorteo de su copa nueva; 8) correo de Prensa «Terminó la temporada en Sudamérica / Europa» con campeones de cada 1ª, campeón de su copa, ascensos y descensos.
- `revisar_jornada(estado) -> None`: con desfase, para el otro continente: `poner_al_dia(fecha)`; si `fecha > fin(estado, otro)`: `cerrar_continente` y `poner_al_dia` otra vez. Idempotente; nunca toca tu continente.

- [ ] **Step 1: tests que fallan** — `test_cierre_del_otro_continente_a_mitad_de_tu_temporada` (Europa: con el reloj en el 31 dic 2026 no cierra; al pasar al 1 ene 2027: `mundo['anio']['sudamerica'] == 2027`, campeón de la Libertadores guardado, ligas sudamericanas en la J1 con tablas a cero y 2 ascensos + 2 descensos por país, correo de Prensa con esos nombres, y tu liga, tu tabla, la Champions y la edad de todos los jugadores intactas); `test_el_cierre_no_se_repite` (otro día después: nada cambia); `test_un_paso_roto_no_bloquea_el_cierre` (con `entrenadores.cierre_temporada` lanzando, el año sube igual y las ligas se reinician).
- [ ] **Step 2:** FAIL. **Step 3:** implementar. **Step 4:** verde.

### Task 7: tu cierre de temporada (F3) y los saves viejos (F6)

**Files:** Modify `alpha_football/ui/resumen_temporada_screen.py`, `alpha_football/temporadas.py`.

Con desfase, `avanzar_nueva_temporada`: cierra solo la copa de tu continente (`simular_copa_entera(tipos)`), arma `campeones_copas` con tu copa + `mundo['campeones']` de la otra, sube `mundo['anio'][tu continente]` junto con `estado['temporada']`, y pasa `paises = paises_de(tu continente)` a `completar_ligas_de_fondo`, `nivel_temporada.*`, `guardar_ranking_copas`, `ascensos_descensos`, `entrenadores.cierre_temporada`, `ingresos_fin_temporada`, `foto_objetivos_ia`; reinicia solo las ligas de tu continente y **envejece todas**; `premios.cerrar_temporada` recibe solo tus ligas y después `temporadas.fundir_balon(estado)` mezcla por puntaje el podio congelado del otro continente; sortea solo tu copa. Retiros, contratos y finanzas: todos, como hoy. Sin desfase: todo como hoy y, **al final**, `temporadas.arrancar_desfase(estado)` (F6).

**Interfaces — Produces:** `temporadas.fundir_balon(estado) -> None`; `temporadas.paises_cierre(estado) -> Optional[tuple]` (None sin desfase).

- [ ] **Step 1: tests que fallan** — `test_tu_cierre_solo_cierra_tu_continente` (carrera desfasada llevada al 30 jun: tras el cierre las ligas europeas están en la J1 y a cero, las sudamericanas conservan su tabla y su jornada, todos los jugadores tienen un año más, `mundo['anio'] == {'europa': 2027, 'sudamerica': 2027}`, Champions nueva y Libertadores intacta, `campeones_copas[-1]` con los dos campeones); `test_dos_temporadas_seguidas_sin_perder_el_desfase` (dos ciclos completos por reloj: Sudamérica cierra dos veces, Europa dos, los años quedan en 2028/2028 y la jornada sudamericana al 1 jul 2028 vuelve a ser la que toca por fecha); `test_un_save_viejo_se_desfasa_al_terminar_su_cierre` (sin marca: tras `avanzar_nueva_temporada` la marca está, el otro continente a mitad de temporada y tu continente en la J1). Actualizar `test_el_cierre_de_un_save_sin_marca_sigue_cerrando_todo` (Task 4): las de tu continente en la J1; las del otro, adelantadas por fecha.
- [ ] **Step 2:** FAIL. **Step 3:** implementar. **Step 4:** verde + los tests de cambio de temporada de Task 4 (ajustar, sin debilitar, los que dieran por hecho que TODAS las ligas quedan en la J1 tras tu cierre: anotarlos).

### Task 8: cambiar de continente (F5)

**Files:** Modify `alpha_football/directiva.py` (`cambiar_de_club`), `alpha_football/temporadas.py`.

**Interfaces — Produces:** `temporadas.al_cambiar_de_club(estado, cont_anterior) -> None`: si el continente cambió y hay desfase, arma el calendario de la liga nueva si falta y deja las ligas del continente que dejas al día por fecha (pasan a «otro continente»); las del nuevo quedan en la jornada del user. Sin desfase (todas las ligas a la par): nada.

- [ ] **Step 1: tests que fallan** — `test_cambiar_de_continente_sigue_en_la_jornada_de_esa_liga` (Europa, reloj en marzo de 2027, `cambiar_de_club` a un club de betplay: `calendario.continente == 'sudamerica'`, `calendario.anio == 2027`, tu próximo partido es de una jornada no jugada de esa liga y su fecha no es anterior a hoy, `estado['temporada']` no cambia, y al llegar al 1 jul 2027 Europa cierra como «otro continente»).
- [ ] **Step 2:** FAIL. **Step 3:** implementar. **Step 4:** verde + `test_carrera_dt_v320.py`, `test_dts_v340.py`.

### Task 9: cierre del sub-proyecto

- [ ] `py_compile` de todo lo tocado; tests vecinos de uno en uno (`test_v236`, `test_competiciones_v380`, `test_copa_v430`, `test_copa_integridad`, `test_dias`, `test_temporada`, `test_calendario`, `test_hub_v240`, `test_presupuesto_ventanas`, `test_premios_v0417`, `test_sancion_liga_v0417`, `test_simulacion`).
- [ ] Comprobación sin pantalla (scratchpad): carrera europea y sudamericana desfasadas, una temporada entera con `simulacion.paso` hasta el fin, cierre y segunda temporada; sin excepciones ni líneas ERROR; capturas del hub y de la tabla de otra liga.
- [ ] Bitácora en `context.md`; línea por tarea en `PROGRESO-PENDIENTES.md`. La suite completa, una sola vez al final (instrucción de Diego).

## Autorrevisión del plan

- **Cobertura del spec:** F1 → Task 5; F2 → Task 6; F3 → Task 7 (+ Task 4 extracción y Task 2 filtros); F4 → Task 3; F5 → Task 8; F6 → Task 7.
- **Decisiones tomadas al planificar (rulings):** (1) el otro continente avanza y cierra por fecha con el reloj de días, y su cierre llega como correo de Prensa sin detener CONTINUAR; (2) el Sudamericano del Año se calcula al cerrar Sudamérica cuando no es tu continente; el Balón funde tu continente con el podio congelado del otro; (3) el mercado sigue usando las ventanas de tu continente para todos los clubes; (4) este plan fija firmas, orden y tests; el código de cada paso se escribe al ejecutar (el de F es en su mayoría mover bloques que ya existen).
