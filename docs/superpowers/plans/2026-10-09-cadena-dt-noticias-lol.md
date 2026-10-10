# Cadena de DTs + núcleo de Noticias + rumores (parte de `lol`) — plan de implementación

> **Para quien ejecuta:** lo implementa la sesión `lol3` (tareas 1 a 7, una por una, con TDD); `lol` lidera,
> revisa y coordina la Tarea 8. Donde el plan dice `lol` como ejecutor, léase `lol3`. La parte de `lol2` está en
> `2026-10-09-noticias-ui-lol2.md`. Los pasos usan casillas `- [ ]`. Cada tarea fija interfaces y casos de
> prueba exactos; el cuerpo de las funciones se escribe al implementar.
> **Imágenes (Tarea 1):** los originales de Diego están en `docs/img/noticias/` (75 JPG); el juego lee copias
> optimizadas (máx. 720 × 1280, JPEG 85) en `alpha_football/assets/noticias/`.

**Objetivo:** núcleo único de noticias, cadena de contrataciones de DT con banco de desempleados, noticias de
mercado y rumores 60/40.

**Arquitectura:** todo el estado en `datos_carrera` como dicts JSON (`noticias`, `dts`, `rumores`). Un solo
punto de publicación (`noticias.publicar`) y un solo enganche por jornada (`noticias.cierre_jornada`). La cadena
de DTs vive dentro de `entrenadores.py`, que ya solo corre en modo carrera.

**Stack:** Python 3, pygame (solo UI), tests como funciones sueltas ejecutables con `pytest tests/<archivo>.py`.

**Spec:** `docs/superpowers/specs/2026-10-09-entrenadores-noticias-design.md`

## Restricciones globales

- Sin commits, stash, checkout ni reset: el árbol tiene trabajo sin commitear de las dos sesiones.
- `Edit` puntual en archivos existentes; nunca `Write` sobre uno que ya existe.
- Avisar a `lol2` antes y después de tocar `retiros.py`, `ui/match_screen.py`, `models.py`, `engine.py`.
- Tests propios en archivos nuevos; la suite se corre **archivo por archivo** (`pytest tests` entero se cuelga
  por los `smoke_*`/`diag_*`).
- Noticias: máximo 50, caducan a las 3 jornadas, titular ≤ 60 caracteres, importancia 1-5, feed ≥ 3.
- Cadena: máximo 4 movimientos por jornada, un DT se mueve una vez por jornada, ningún club de la IA termina sin DT.
- Retirados: OVR ≥ 81 → 20 % al banco. Rumores: 60 % reales, plazo de 1-3 jornadas de mercado, máximo 2 vivos.
- Cada bloque nuevo que corre en el cierre de jornada va en su propio `try/except` con `logger.error`.
- Versiones: 0.4.22.0 (Tarea 1) y 0.4.23.0 (Tarea 2); las sube `lol` al final.

## Foco de revisión

1. **Guardado viejo** con `datos_carrera['noticias']` en formato antiguo (sin `importancia`, con `jugadores`) o sin
   la clave → `noticias.lista` las normaliza y nada revienta (test en Tarea 1).
2. **Guardado viejo** con DTs sin `edad` y banco sin técnicos reales → `asegurar_dts` los completa una sola vez (Tarea 3).
3. **El club del user** nunca es origen ni destino de la cadena, ni recibe DT de la IA (Tarea 4).
4. **Rumor cuyo jugador ya no está** en su club al vencer (vendido, retirado, fichado por el user) → se resuelve
   como humo sin excepción (Tarea 7).
5. **Carpeta de imágenes** inexistente, vacía o con archivos de otra extensión → `noticias.imagen` devuelve `None` (Tarea 1).

---

### Tarea 1: núcleo `noticias.py`

**Archivos:** crear `alpha_football/noticias.py`, `tests/test_noticias_nucleo.py`; modificar
`alpha_football/eventos.py:68-83` (`noticias`, `registrar_noticia`).

**Produce** (lo consume `lol2` y el resto de este plan):

```python
MAX_NOTICIAS = 50; JORNADAS_VIDA = 3; IMPORTANCIA_FEED = 3
TIPOS: tuple; CATEGORIA: dict[str, str]; ETIQUETA: dict[str, str]; COLOR: dict[str, tuple]
RUTA_IMAGENES = <alpha_football>/assets/noticias

lista(estado) -> list
publicar(estado, tipo, titular, cuerpo, importancia=3, categoria=None,
         equipos=(), jugadores=(), dts=(), **extra) -> dict
antiguedad(estado, noticia) -> int
activas(estado) -> list;  para_feed(estado) -> list;  ultimas(estado, n=10) -> list
no_leidas(estado) -> int;  marcar_leida(estado, noticia_id) -> None
purgar(estado) -> int;  imagen(noticia) -> Optional[str];  cierre_jornada(estado) -> None
```

- `id` sale de un contador monótono `datos_carrera['noticia_sig_id']` (no se reutilizan ids: `lol2` cachea por id).
- `extra` admite `temporada=`, `jornada=` (pisan a los actuales), `accion={'pantalla', 'texto'}` (botón en la
  pantalla Noticias, misma forma que `correo.accion`) y cualquier otra clave.
- Al pasar de 50 sale primero la de menor importancia y, a igualdad, la más vieja.
- `cierre_jornada`: llama (cada uno en su `try`, con import perezoso) a `rumores.revisar_jornada`,
  `noticias_gen.generar_jornada` y por último `purgar`.

**Casos de prueba** (`tests/test_noticias_nucleo.py`, `estado` mínimo con `liga`/`mi_equipo` falsos):

- [ ] `test_publicar_campos`: devuelve todos los campos del spec, `leida False`, categoría por defecto según el tipo.
- [ ] `test_titular_se_recorta_a_60`.
- [ ] `test_tope_50_conserva_las_importantes`: 60 noticias, 5 de importancia 5 al principio → quedan 50 y las 5 siguen.
- [ ] `test_caducan_a_las_3_jornadas`: jornada 5 → en 7 sigue, en 8 `purgar` la borra.
- [ ] `test_ultima_jornada_vive_al_cambiar_de_temporada`: (t1, j38, N=38) vista desde (t2, j0) tiene antigüedad 0.
- [ ] `test_override_temporada_jornada`.
- [ ] `test_orden_activas`: importancia descendente y, dentro, la más reciente primero; `para_feed` excluye < 3.
- [ ] `test_leidas`: `no_leidas` baja con `marcar_leida`; id inexistente no falla.
- [ ] `test_ids_no_se_reutilizan` tras purgar.
- [ ] `test_formato_viejo_se_normaliza` (foco 1): lista con dicts de `eventos` antiguos → `activas` funciona.
- [ ] `test_imagen_sin_carpeta_es_none` (foco 5) y `test_imagen_estable_por_id` con un directorio temporal.
- [ ] `test_registrar_noticia_de_eventos_pasa_por_el_nucleo`: conserva `evento`, `opcion`, `jugadores`.
- [ ] `test_cierre_jornada_sigue_si_un_generador_falla`.
- [ ] `test_json`: `json.dumps(datos_carrera['noticias'])` funciona.

**Pasos:** - [ ] escribir los tests y verlos fallar · - [ ] implementar · - [ ] `pytest tests/test_noticias_nucleo.py -q`
y `pytest tests/test_eventos.py -q` en verde · - [ ] avisar a `lol2`: "contrato listo".

### Tarea 2: enganche del cierre de jornada

**Archivos:** modificar `alpha_football/ui/match_screen.py` (bloque de cierre de jornada, tras el `try` de premios ~574-578).

- [ ] Avisar a `lol2`. Añadir un `try` con `from alpha_football import noticias as _noticias; _noticias.cierre_jornada(estado)`.
- [ ] Comprobar con Grep que partidos amistosos y modo edición no pasan por ese bloque (si pasan, condicionar a `estado.get('liga')` y `mi_equipo`).
- [ ] `pytest tests/test_dts_v340.py tests/test_eventos.py -q` en verde. Avisar a `lol2`.

### Tarea 3: banco de técnicos

**Archivos:** modificar `alpha_football/data/entrenadores.py`, `alpha_football/entrenadores.py`,
`alpha_football/retiros.py` (solo `procesar_retiros`); crear `tests/test_cadena_dt.py`.

**Produce:**

```python
# data/entrenadores.py
DT_LIBRES_REALES: list[tuple[str, str, int, str, int]]   # (nombre parodia, estilo, calif, nacionalidad, edad), ~24
NOMBRES, APELLIDOS                                        # de 20 a 60 cada una

# entrenadores.py
MIN_BANCO = 8; MAX_BANCO = 40; OVR_RETIRADO_DT = 81; PROB_RETIRADO_DT = 0.2
ESTILOS_POR_POSICION: dict[str, tuple]
prestigio(dt) -> str                                      # 'bajo' < 50 · 'medio' 50-69 · 'alto' >= 70
mantener_banco(estado, rng=None) -> None                  # rellena a N_LIBRES si < MIN_BANCO; recorta a MAX_BANCO
retirados_a_banco(estado, retiros, rng=None) -> list      # devuelve los DTs creados
```

- `_nuevo` acepta `edad` (por defecto 38-68 sembrado por el nombre) y `ex_jugador`.
- `asegurar_dts` lee `dt_nacionalidad`, `dt_edad`, `dt_sin` del club y `nacionalidad`/`edad` de `_dts_libres`;
  siembra `DT_LIBRES_REALES` una vez (`libres_reales_ok`), saltando nombres que ya dirigen un club; completa `edad` en saves viejos.
- Retirado → DT: calificación `min(65, 45 + (ovr − 81) × 2)`, estilo al azar entre los de su posición, publica
  "{nombre} se convierte en entrenador" (`dt_cambio`, importancia 4). El dict de cada retiro gana `nacionalidad`.

**Casos de prueba:**

- [ ] `test_prestigio_por_calificacion` (49 / 50 / 69 / 70).
- [ ] `test_reales_sin_club_entran_una_vez` y no duplican a un DT que ya dirige.
- [ ] `test_save_viejo_completa_edad_y_reales` (foco 2).
- [ ] `test_banco_se_rellena_bajo_el_minimo` y `test_banco_tope_40_salen_los_peores`.
- [ ] `test_retirado_81_entra_con_20pct` (rng fijo: entra / no entra) y `test_retirado_80_nunca_entra`.
- [ ] `test_retirado_publica_noticia` y conserva nombre, nacionalidad y edad.
- [ ] `test_editor_dt_sin_y_nacionalidad` (club con `dt_sin` arranca con DT generado, no el de `DT_REALES`).

**Pasos:** - [ ] tests en rojo · - [ ] implementar (avisar a `lol2` antes y después de `retiros.py`) ·
- [ ] `pytest tests/test_cadena_dt.py tests/test_dts_v340.py tests/test_editor_libres_dts.py -q` en verde.

### Tarea 4: cadena de contrataciones

**Archivos:** modificar `alpha_football/entrenadores.py`; ampliar `tests/test_cadena_dt.py`; ajustar en
`tests/test_dts_v340.py` las aserciones que esperen el correo "Cambio de DT".

**Produce:**

```python
MAX_CADENA = 4; INTENTOS_ROBO = 3; PROB_ACEPTA_ROBO = 0.6; SUBE_SUELDO_ROBO = 1.2
cubrir_vacante(estado, equipo, liga, rng=None, motivo='', ofrecer=True) -> Optional[dict]   # DT que llega (None si interino)
```

- Estado de la jornada en `dts['cadena'] = {'clave': [temporada, jornada], 'mov': int, 'movidos': [ids]}`; se
  reinicia cuando cambia la clave.
- Candidato a robo: DT de otro club de la IA (nunca el del user), no interino, no movido, de un club con
  `ovr_promedio` al menos 0,5 por debajo, con mejor calificación que el mejor libre que `equipo` puede pagar y cuyo
  sueldo nuevo (`max(sueldo × 1.2, sueldo_pedido)`) cumpla `puede_pagar`. Orden: misma liga → mismo país → mismo
  continente (otros continentes, no); luego mismo estilo que el DT saliente; luego calificación.
- Robo logrado: noticia "{DT} deja el {origen} y firma por el {club}"; el origen llama a `cubrir_vacante`.
- Sin robo o con el cupo agotado: banco (`contratar`) + noticia "{DT}, nuevo técnico del {club}".
- `despedir` publica "El {club} despide a {DT}" y deja de enviar el correo. Importancia 4 en 1ª división o en tu
  liga; 2 en 2ª de otros países (no entra al feed).
- `revisar_jornada`, `cierre_temporada`, `rechazar_oferta` y el vencimiento de ofertas usan `cubrir_vacante`
  (los dos últimos con `ofrecer=False`). `revisar_jornada` termina con `mantener_banco`.

**Casos de prueba** (rng falso que devuelve valores fijos):

- [ ] `test_robo_viene_de_un_club_menor_de_la_misma_liga`.
- [ ] `test_origen_queda_cubierto`: tras la cadena todo club de la IA tiene DT no nulo.
- [ ] `test_tope_de_4_movimientos` con aceptación forzada.
- [ ] `test_un_dt_no_se_mueve_dos_veces_en_la_jornada`.
- [ ] `test_contador_se_reinicia_en_la_jornada_siguiente`.
- [ ] `test_sin_aceptacion_va_al_banco` (el banco pierde uno).
- [ ] `test_club_del_user_fuera_de_la_cadena` (foco 3).
- [ ] `test_club_que_no_puede_pagar_no_roba`.
- [ ] `test_vacante_de_cadena_puede_ofrecerse_al_user` (club en banda → interino + oferta).
- [ ] `test_noticias_de_despido_y_fichaje` y `test_despido_ya_no_envia_correo`.
- [ ] `test_cierre_temporada_no_deja_clubes_sin_dt`.

**Pasos:** - [ ] tests en rojo · - [ ] implementar · - [ ] `pytest tests/test_cadena_dt.py tests/test_dts_v340.py
tests/test_temporadas_continente.py -q` en verde.

### Tarea 5: Prensa → Noticias

**Archivos:** modificar `alpha_football/mercado_ia.py:172-183` y `:234-240`, `alpha_football/premios.py:197-207`,
`alpha_football/cantera.py:321-324`, `alpha_football/temporadas.py:355-356`; actualizar `tests/test_cantera.py:250`,
`tests/test_finanzas_v460.py:111`, `tests/test_premios_v0417.py:94`, `tests/test_remates_libres_v0421.py:43`,
`tests/test_temporadas_continente.py:320`.

| Antes (correo de Prensa) | Ahora (`publicar`) |
|---|---|
| Quiebra en {club} | `economia`, importancia 4, `accion` → buscador |
| Remate de {club} | `economia`, importancia 3, `accion` → buscador |
| {Premio}: {ganador} | `premio`, importancia 5, `accion` → carrera |
| {club} presenta a una joya | `cantera`, importancia 3 |
| Terminó la temporada en {continente} | una noticia `campeon` de importancia 5 por la copa y otra de importancia 4 con el resumen de campeones, ascensos y descensos |

- [ ] Cambiar cada `C.enviar(estado, 'prensa', …)` por `publicar` con el mismo texto (el titular se acorta a 60).
- [ ] Reescribir las 5 aserciones para leer `noticias.lista(estado)` en vez de la bandeja.
- [ ] Correr esos 5 archivos de tests en verde.

Los eventos de vestuario con remitente `'prensa'` (`eventos.py:308`, `:430`) piden una decisión y **siguen** siendo correo.

### Tarea 6: noticias de fichajes

**Archivos:** modificar `alpha_football/negociacion.py` (`registrar_pase`, :288); crear `tests/test_noticias_mercado.py`.

- `registrar_pase(..., confirmado: bool = False)`. Publica `fichaje` cuando el destino no es "Libre":
  media ≥ 85 → importancia 5; ≥ 80 → 4; ≥ 76 o fichaje/venta del user → 3; el resto no publica.
  Con `confirmado=True` el titular empieza por "Confirmado:".

**Casos:** - [ ] `test_fichaje_grande_publica_importancia_5` · - [ ] `test_fichaje_menor_de_la_ia_no_publica` ·
- [ ] `test_fichaje_del_user_siempre_publica` · - [ ] `test_liberado_no_publica` · - [ ] `test_fallo_al_publicar_no_rompe_el_pase`.

**Pasos:** - [ ] tests en rojo · - [ ] implementar · - [ ] `pytest tests/test_noticias_mercado.py
tests/test_remates_libres_v0421.py -q` en verde.

### Tarea 7: rumores

**Archivos:** crear `alpha_football/rumores.py`, `tests/test_rumores.py`.

**Produce:**

```python
PROB_RUMOR = 0.35; MAX_VIVOS = 2; PROB_REAL = 0.6; PLAZO = (1, 3); PROB_DESMENTIDO = 0.5; PROB_SOBRE_USER = 0.3
vivos(estado) -> list
generar(estado, rng) -> Optional[dict]
revisar_jornada(estado, rng=None) -> None      # resuelve los vencidos y, con el mercado abierto, puede crear uno
```

- Rumor = `{id, clase: 'ia'|'user', jugador_id, jugador, origen, destino, precio, real, vence, noticia_id}` (solo
  ids y nombres: va al JSON).
- Clase `ia`: el objetivo sale de `mercado_ia._buscar_refuerzo` (mismo criterio que un fichaje real). Al vencer,
  si es real y sigue viable → `_traspasar` + `registrar_pase(..., confirmado=True)`.
- Clase `user`: jugador del user (no cedido, no traspasado en esta ventana) y club de la IA que puede pagarlo.
  Al vencer, si es real → oferta formal por el cauce de `ofertas_recibidas` con su correo.
- Humo o inviable → 50 % noticia "{jugador} desmiente su salida al {destino}", 50 % nada.
- Mercado cerrado → todos los vivos se resuelven como humo.

**Casos:** - [ ] `test_rumor_real_ejecuta_el_traspaso` · - [ ] `test_rumor_humo_no_mueve_a_nadie` ·
- [ ] `test_jugador_ya_no_esta_se_resuelve_como_humo` (foco 4) · - [ ] `test_comprador_sin_dinero_no_ejecuta` ·
- [ ] `test_rumor_del_user_real_trae_oferta` · - [ ] `test_maximo_dos_vivos` ·
- [ ] `test_mercado_cerrado_los_apaga` · - [ ] `test_plazo_baja_solo_con_mercado_abierto` ·
- [ ] `test_proporcion_60_40` (1000 rumores con semilla: entre 55 % y 65 % reales) · - [ ] `test_json`.

**Pasos:** - [ ] tests en rojo · - [ ] implementar · - [ ] `pytest tests/test_rumores.py tests/test_noticias_nucleo.py -q` en verde.

### Tarea 8: integración y cierre

- [ ] Recibir de `lol2` su lista de archivos tocados y su sección de bitácora.
- [ ] Correr **todos** los `tests/test_*.py` uno por uno (script en el scratchpad que los recorre y resume fallos).
- [ ] Arrancar el juego (`python main.py`) y jugar una jornada con mercado abierto: aparece el feed, la pantalla
  Noticias y al menos una noticia de DT o de fichaje; cambio de temporada con la carga nueva.
- [ ] `alpha_football/__init__.py` → 0.4.23.0; README y `context.md` con las bitácoras de 0.4.22.0 y 0.4.23.0.
- [ ] Actualizar la memoria `numeracion-versiones` (próxima libre 0.4.24.0).
